(in-package :wasm32-compiler)

;;; Observe CCL's file compiler, including its ordinary compile-time effects.
;;; Target output is retained, never installed in the native image or dumped
;;; as a native FASL. Every input file runs in a fresh process.
(defvar *file-definitions* nil)
(defvar *file-records* nil)
(defvar *file-current-definition* nil)
(defvar *file-output* nil)

(defun file-json-string (value stream)
  (write-char #\" stream)
  (loop for c across value do
    (case c
      (#\" (write-string "\\\"" stream))
      (#\\ (write-string "\\\\" stream))
      (#\Newline (write-string "\\n" stream))
      (#\Return (write-string "\\r" stream))
      (#\Tab (write-string "\\t" stream))
      (t (if (< (char-code c) 32)
           (format stream "\\u~4,'0x" (char-code c))
           (write-char c stream)))))
  (write-char #\" stream))

(defun file-name-string (name)
  (let ((*package* (find-package "CCL")) (*print-gensym* nil))
    (prin1-to-string name)))

(defun file-check-body (form module)
  (when (and form (eq (car form) 'defun))
    (let ((body (cdddr form)))
      (when (stringp (car body)) (pop body))
      (loop while (and (consp (car body)) (eq (caar body) 'declare)) do (pop body))
      (when (null body) (refuse :bootstrap-empty-target-body))
      (when (and (= (length body) 1) (consp (car body))
                 (eq (caar body) (second form))
                 (or (getf module :dependencies) (getf module :self-call)))
        (refuse :bootstrap-self-only-body)))))

(defun file-compile-function (definition name env)
  (let* ((number (length *file-records*))
         (wire (format nil "file_~d" number))
         (source (and *file-current-definition*
                      (equal name (getf *file-current-definition* :name))
                      *file-current-definition*))
         (module nil) (message nil) (macros nil) (hook *macroexpand-hook*)
         (outcome (handler-case
                      (progn
                        (let ((*macroexpand-hook*
                               (lambda (expander form environment)
                                 (when (and (consp form) (symbolp (car form)))
                                   (pushnew (car form) macros))
                                 (funcall hook expander form environment))))
                          (setq module (compile-bootstrap-form definition wire nil env)))
                        (file-check-body (getf source :form) module)
                        :admitted)
                    (unsupported-wasm32-code (c) (unsupported-operation c))
                    (error (c)
                      (setq message (format nil "~a" c))
                      (type-of c)))))
    (when source (setf (getf source :outcome) outcome))
    (push (list :name name :wire wire :outcome outcome :message message
                :definition (and source (getf source :index))
                :symbols (and module (mapcar #'car (getf module :symbols)))
                :macros (sort macros #'string< :key #'file-name-string)
                :dependencies (and (eq outcome :admitted) (getf module :dependencies)))
          *file-records*)
    (when (and module (eq outcome :admitted))
      (dolist (part (cons module (getf module :children)))
        (with-open-file (s (merge-pathnames (concatenate 'string (getf part :name) ".wat")
                                           *file-output*)
                           :direction :output :if-exists :error)
          (write-string (getf part :wat) s))))
    ;; FCOMP will not execute these load-time records. No placeholder function
    ;; is installed, and the file sink stops before the native fasl writer.
    (list :wasm-record wire outcome)))

(defun file-write-result (path complete failure)
  (with-open-file (s (merge-pathnames "result.json" *file-output*)
                     :direction :output :if-exists :error)
    (write-string "{\"file\":" s) (file-json-string (if (typep path 'logical-pathname)
                            (namestring path) (file-namestring path)) s)
    (format s ",\"complete\":~a,\"failure\":" (if complete "true" "false"))
    (if failure (file-json-string failure s) (write-string "null" s))
    (write-string ",\"definitions\":[" s)
    (loop for row in (reverse *file-definitions*) for i from 0 do
      (unless (zerop i) (write-char #\, s))
      (format s "{\"index\":~d,\"offset\":~d,\"name\":"
              (getf row :index) (or (getf row :offset) 0))
      (file-json-string (file-name-string (getf row :name)) s)
      (write-string ",\"outcome\":" s)
      (file-json-string (symbol-name (or (getf row :outcome) :not-compiled)) s)
      (write-char #\} s))
    (write-string "],\"records\":[" s)
    (loop for row in (reverse *file-records*) for i from 0 do
      (unless (zerop i) (write-char #\, s))
      (write-string "{\"name\":" s)
      (file-json-string (file-name-string (getf row :name)) s)
      (format s ",\"module\":~s,\"definition\":~a,\"outcome\":"
              (getf row :wire) (or (getf row :definition) "null"))
      (file-json-string (symbol-name (getf row :outcome)) s)
      (write-string ",\"message\":" s)
      (if (getf row :message) (file-json-string (getf row :message) s)
          (write-string "null" s))
      (write-string ",\"symbols\":[" s)
      (loop for name in (getf row :symbols) for j from 0 do
        (unless (zerop j) (write-char #\, s))
        (file-json-string (file-name-string name) s))
      (write-char #\] s)
      (write-string ",\"macros\":[" s)
      (loop for name in (getf row :macros) for j from 0 do
        (unless (zerop j) (write-char #\, s))
        (file-json-string (file-name-string name) s))
      (write-char #\] s)
      (write-string ",\"dependencies\":[" s)
      (loop for dep in (getf row :dependencies) for j from 0 do
        (unless (zerop j) (write-char #\, s))
        (file-json-string (file-name-string dep) s))
      (write-string "]}" s))
    (write-string "]}" s)))

(defun file-measure (path output)
  (let* ((ccl:*warn-if-redefine-kernel* nil)
         (*file-output* output) (*file-definitions* nil) (*file-records* nil)
         (*file-current-definition* nil)
         (form-compiler (fdefinition 'ccl::fcomp-form))
         (function-compiler (fdefinition 'ccl::fcomp-named-function))
         (file-compiler (fdefinition 'ccl::fcomp-file))
         (done (gensym "FILE")) (complete nil) (failure nil))
    (unwind-protect
        (progn
          (setf (fdefinition 'ccl::fcomp-form)
                (lambda (form env mode)
                  (if (and (eq ccl::*fasl-target* :wasm32)
                           (consp form) (eq (car form) 'defun))
                    (let ((*file-current-definition*
                           (list :index (length *file-definitions*) :name (second form)
                                 :offset ccl::*fcomp-stream-position* :form form :outcome nil)))
                      (push *file-current-definition* *file-definitions*)
                      (funcall form-compiler form env mode))
                    (funcall form-compiler form env mode))))
          (setf (fdefinition 'ccl::fcomp-named-function)
                (lambda (definition name env &optional source-note)
                  (if (eq ccl::*fasl-target* :wasm32)
                    (file-compile-function definition name env)
                    (funcall function-compiler definition name env source-note))))
          (setf (fdefinition 'ccl::fcomp-file)
                (lambda (&rest args)
                  (if (eq ccl::*fasl-target* :wasm32)
                    (let ((records (apply file-compiler args)))
                      (setq complete t)
                      (throw done records))
                    (apply file-compiler args))))
          (handler-case
              (call-with-target
               (lambda ()
                 (catch done
                   (compile-file path :target :wasm32 :verbose nil :print nil
                                 :output-file (merge-pathnames "unused.w32fsl" output)))))
            (error (c) (setq failure (format nil "~s: ~a" (type-of c) c)))))
      (setf (fdefinition 'ccl::fcomp-form) form-compiler
            (fdefinition 'ccl::fcomp-named-function) function-compiler
            (fdefinition 'ccl::fcomp-file) file-compiler))
    (file-write-result path complete failure)))
