;;; Observes native U1 only. Never edits acode, operators, target state or results.
(defpackage :ccl-startup-census (:use :cl))
(in-package :ccl-startup-census)

(defvar *stream* nil)
(defvar *sequence* 0)
(defvar *busy* nil)
(defvar *event-lock* (ccl:make-lock "native startup census events"))
(defvar ccl::*startup-census-hook* nil)

(defun object (&rest fields) (cons :object fields))
(defun label-of (value)
  (typecase value
    (null "NIL")
    (symbol (concatenate 'string (if (symbol-package value)
                                  (package-name (symbol-package value)) "#")
                         "::" (symbol-name value)))
    (string value)
    (pathname (namestring value))
    (function (label-of (ccl:function-name value)))
    (t (let ((*print-circle* t) (*print-pretty* nil) (*print-readably* nil)
             (*print-level* 6) (*print-length* 24) (*package* (find-package :keyword)))
         (write-to-string value)))))

(defun json-string (value stream)
  (write-char #\" stream)
  (loop for c across value do
    (case c
      (#\" (write-string "\\\"" stream))
      (#\\ (write-string "\\\\" stream))
      (t (if (< (char-code c) 32)
           (format stream "\\u~4,'0x" (char-code c)) (write-char c stream)))))
  (write-char #\" stream))

(defun json (value stream)
  (cond ((eq value :null) (write-string "null" stream))
        ((eq value :true) (write-string "true" stream))
        ((eq value :false) (write-string "false" stream))
        ((stringp value) (json-string value stream))
        ((integerp value) (princ value stream))
        ((and (consp value) (eq (car value) :object))
         (write-char #\{ stream)
         (loop for (key val) on (cdr value) by #'cddr for first = t then nil do
           (unless first (write-char #\, stream))
           (json-string key stream) (write-char #\: stream) (json val stream))
         (write-char #\} stream))
        ((listp value)
         (write-char #\[ stream)
         (loop for v in value for first = t then nil do
           (unless first (write-char #\, stream)) (json v stream))
         (write-char #\] stream))
        (t (error "Not a census JSON value: ~s" value))))

(defun log-stream ()
  (or *stream*
      (setf *stream* (open (or (ccl:getenv "CCL_CENSUS_EVENTS")
                              (error "CCL_CENSUS_EVENTS is required"))
                          :direction :output :if-exists :error
                          :external-format :utf-8 :sharing :external))))

(defun emit (kind payload)
  (ccl:with-lock-grabbed (*event-lock*)
    (json (object "sequence" (incf *sequence*) "kind" kind
                  "source" (if *compile-file-truename* (namestring *compile-file-truename*) :null)
                  "source_position" (if (and (boundp 'ccl::*fcomp-stream-position*)
                                              (integerp ccl::*fcomp-stream-position*))
                                       ccl::*fcomp-stream-position* :null)
                  "loading_source" (if (boundp 'ccl::*loading-file-source-file*)
                                        (label-of ccl::*loading-file-source-file*) :null)
                  "payload" payload) (log-stream))
    (terpri (log-stream))))

(defun snapshot ()
  (let* ((backend ccl::*target-backend*)
         (dispatch (ccl::backend-p2-dispatch backend))
         (operators
           (loop for entry in (reverse ccl::*next-nx-operators*) for id from 0 collect
             (object "id" id "name" (if entry (label-of (car entry)) :null)
                     "flags" (if entry (cadr entry) 0)
                     "encoded" (if entry (gethash (car entry) ccl::*nx1-operators*) :null)
                     "handler" (if (< id (length dispatch))
                                   (label-of (svref dispatch id)) :null))))
         (templates (sort (loop for key being the hash-keys of
                               (ccl::backend-p2-vinsn-templates backend) collect (label-of key)) #'string<)))
    (object "backend" (label-of (ccl::backend-name backend))
            "host_backend" (label-of (ccl::backend-name ccl::*host-backend*))
            "target_features" (sort (mapcar #'label-of (ccl::setup-target-features backend *features*)) #'string<)
            "word_bits" (if (logtest ccl::platform-word-size-mask (ccl::backend-target-platform backend)) 64 32)
            "operators" operators "vinsn_templates" templates
            "startup_groups"
            (loop for (group functions) in
                  (list (list "system_pointers" (reverse ccl::*lisp-system-pointer-functions*))
                        (list "restore_lisp" ccl::*restore-lisp-functions*)
                        (list "user_pointers" (reverse ccl::*lisp-user-pointer-functions*))
                        (list "startup" (reverse ccl:*lisp-startup-functions*)))
                  collect (object "group" group "functions" (mapcar #'label-of functions))))))

(defun literal-label (node)
  (when (ccl::acode-p node)
    (let ((name (ccl::acode-operator-name (ccl::acode-operator node))))
      (when (member name '(ccl::immediate ccl::fixnum ccl::nil ccl::t))
        (label-of (car (ccl::acode-operands node)))))))

(defun function-observation (afunc)
  (let ((seen (make-hash-table :test #'eq)) (counts (make-hash-table))
        (stack (list (ccl::afunc-acode afunc))) (calls nil))
    (loop while stack for node = (pop stack) do
      (cond
        ((ccl::acode-p node)
         (unless (gethash node seen)
           (setf (gethash node seen) t)
           (let* ((id (logand (ccl::acode-operator node) ccl::operator-id-mask))
                  (name (ccl::acode-operator-name id)) (operands (ccl::acode-operands node)))
             (incf (gethash id counts 0))
             (when (member name '(ccl::call ccl::builtin-call ccl::lexical-function-call ccl::self-call))
               (push (object "operator" (label-of name)
                             "target" (or (literal-label (car operands)) :null)
                             "resolution" "observed-form-only") calls))
             ;; Literal object graphs are data, not expression children.
             (unless (member name '(ccl::immediate ccl::fixnum ccl::nil ccl::t))
               (push operands stack)))))
        ((consp node)
         (unless (gethash node seen)
           (setf (gethash node seen) t)
           (push (cdr node) stack) (push (car node) stack)))))
    (object "name" (label-of (ccl::afunc-name afunc))
            "operators" (loop for id in (sort (loop for k being the hash-keys of counts collect k) #'<)
                              collect (object "id" id "count" (gethash id counts)))
            "calls" (nreverse calls)
            "inner_functions" (mapcar #'function-observation (ccl::afunc-inner-functions afunc)))))

(defun observe (phase value)
  (unless *busy*
    (let ((*busy* t) (*gensym-counter* *gensym-counter*))
      (emit (string-downcase (symbol-name phase))
            (if (member phase '(:frontend :before-pass2))
              (function-observation value) (label-of value))))))

(defun start ()
  (setf ccl::*startup-census-hook* #'observe)
  (emit "snapshot" (snapshot)))

(defun finish ()
  (emit "complete" (object "events_before_complete" *sequence*))
  (ccl:with-lock-grabbed (*event-lock*)
    (finish-output (log-stream)) (close *stream*) (setf *stream* nil))
  (setf ccl::*startup-census-hook* nil))

(defun prepare-observed-image (path)
  ;; The disposable saved image opens its own new log after restart.
  (when *stream* (close *stream*))
  (setf *stream* nil *sequence* 0 ccl::*startup-census-hook* #'observe)
  (ccl:save-application path :prepend-kernel nil))
