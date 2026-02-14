;;; -*- Mode: Lisp; Package: CCL -*-

(in-package "CCL")

(defvar *wasm-startup-truth-schema-version* "startup_truth_v1")
(defvar *wasm-startup-truth-enabled* nil)
(defvar *wasm-startup-truth-seq* 0)
(defvar *wasm-startup-truth-sink* nil)
(defvar *wasm-startup-truth-path* "doc/wasm/startup_truth_v1.jsonl")
(defvar *wasm-startup-truth-stdout-mirror* nil)
(defvar *wasm-startup-truth-session-start-emitted* nil)

(unless (fboundp '%wasm-startup-truth-note-event)
  (defun %wasm-startup-truth-json-escape-string (value)
    (let ((string (if (stringp value) value (princ-to-string value))))
      (with-output-to-string (out)
        (dotimes (i (length string))
          (let ((ch (char string i)))
            (case ch
              (#\" (write-string "\\\"" out))
              (#\\ (write-string "\\\\" out))
              (#\Newline (write-string "\\n" out))
              (#\Return (write-string "\\r" out))
              (#\Tab (write-string "\\t" out))
              (t (write-char ch out))))))))

  (defun %wasm-startup-truth-json-write-string (out value)
    (write-char #\" out)
    (write-string (%wasm-startup-truth-json-escape-string value) out)
    (write-char #\" out))

  (defun %wasm-startup-truth-json-write-object (out pairs)
    (write-char #\{ out)
    (do ((rest pairs (cdr rest))
         (first t nil))
        ((null rest))
      (unless first
        (write-char #\, out))
      (let ((pair (car rest)))
        (%wasm-startup-truth-json-write-string out (car pair))
        (write-char #\: out)
        (%wasm-startup-truth-json-write-value out (cdr pair))))
    (write-char #\} out))

  (defun %wasm-startup-truth-json-write-array (out values)
    (write-char #\[ out)
    (do ((rest values (cdr rest))
         (first t nil))
        ((null rest))
      (unless first
        (write-char #\, out))
      (%wasm-startup-truth-json-write-value out (car rest)))
    (write-char #\] out))

  (defun %wasm-startup-truth-json-write-value (out value)
    (cond
      ((stringp value) (%wasm-startup-truth-json-write-string out value))
      ((integerp value) (princ value out))
      ((floatp value) (princ value out))
      ((eq value :json-true) (write-string "true" out))
      ((eq value :json-false) (write-string "false" out))
      ((null value) (write-string "null" out))
      ((and (consp value) (eq (car value) :object))
       (%wasm-startup-truth-json-write-object out (cdr value)))
      ((and (consp value) (eq (car value) :array))
       (%wasm-startup-truth-json-write-array out (cdr value)))
      (t
       (%wasm-startup-truth-json-write-string out (princ-to-string value)))))

  (defun %wasm-startup-truth-json-key (key)
    (let* ((name
            (cond
              ((keywordp key) (symbol-name key))
              ((symbolp key) (symbol-name key))
              (t (princ-to-string key))))
           (lower (string-downcase name)))
      (substitute #\_ #\- lower)))

  (defun %wasm-startup-truth-keyword-plist-p (value)
    (and (listp value)
         (do ((rest value (cddr rest)))
             ((null rest) t)
           (unless (and (keywordp (car rest))
                        (consp (cdr rest)))
             (return nil)))))

  (defun %wasm-startup-truth-symbol-json (value)
    (let ((pkg (symbol-package value)))
      (cons :object
            (list
             (cons "kind" "symbol")
             (cons "name" (symbol-name value))
             (cons "package" (if pkg (package-name pkg) nil))))))

  (defun %wasm-startup-truth-package-json (value)
    (let ((name (ignore-errors (package-name value))))
      (if (stringp name)
        (cons :object
              (list
               (cons "kind" "package")
               (cons "name" name)))
        nil)))

  (defun %wasm-startup-truth-normalize-list (value)
    (if (%wasm-startup-truth-keyword-plist-p value)
      (let ((pairs nil))
        (do ((rest value (cddr rest)))
            ((null rest))
          (push (cons (%wasm-startup-truth-json-key (car rest))
                      (%wasm-startup-truth-normalize-value (cadr rest)))
                pairs))
        (cons :object (nreverse pairs)))
      (let ((items nil))
        (do ((rest value (cdr rest)))
            ((null rest))
          (push (%wasm-startup-truth-normalize-value (car rest)) items))
        (cons :array (nreverse items)))))

  (defun %wasm-startup-truth-normalize-vector (value)
    (let ((items nil))
      (dotimes (i (length value))
        (push (%wasm-startup-truth-normalize-value (aref value i)) items))
      (cons :array (nreverse items))))

  (defun %wasm-startup-truth-normalize-value (value)
    (cond
      ((and (consp value) (eq (car value) :object)) value)
      ((and (consp value) (eq (car value) :array)) value)
      ((stringp value) value)
      ((integerp value) value)
      ((floatp value) value)
      ((eq value t) :json-true)
      ((null value) nil)
      ((symbolp value)
       (if (keywordp value)
         (string-downcase (symbol-name value))
         (%wasm-startup-truth-symbol-json value)))
      ((vectorp value)
       (%wasm-startup-truth-normalize-vector value))
      ((listp value)
       (%wasm-startup-truth-normalize-list value))
      (t
       (or (%wasm-startup-truth-package-json value)
           (princ-to-string value)))))

  (defun %wasm-startup-truth-plist->json-object (payload)
    (let ((pairs nil))
      (do ((rest payload (cddr rest)))
          ((null rest))
        (push (cons (%wasm-startup-truth-json-key (car rest))
                    (%wasm-startup-truth-normalize-value (cadr rest)))
              pairs))
      (cons :object (nreverse pairs))))

  (defun %wasm-startup-truth-phase-string (value)
    (cond
      ((stringp value) value)
      ((symbolp value) (string-downcase (symbol-name value)))
      ((integerp value)
       (case value
         (0 "early")
         (1 "l0-ready")
         (2 "runtime")
         (t (format nil "phase-~d" value))))
      (t "unknown")))

  (defun %wasm-startup-truth-next-seq ()
    (prog1 *wasm-startup-truth-seq*
      (setq *wasm-startup-truth-seq* (1+ *wasm-startup-truth-seq*))))

  (defun %wasm-startup-truth-write-record (record)
    (let ((sink *wasm-startup-truth-sink*))
      (when (streamp sink)
        (%wasm-startup-truth-json-write-value sink record)
        (terpri sink)
        (finish-output sink)
        (when *wasm-startup-truth-stdout-mirror*
          (%wasm-startup-truth-json-write-value *standard-output* record)
          (terpri *standard-output*)
          (finish-output *standard-output*))
        t)))

  (defun %wasm-startup-truth-emit-event-internal (event-type payload phase)
    (let ((record
           (cons :object
                 (list
                  (cons "schema_version" *wasm-startup-truth-schema-version*)
                  (cons "event_type"
                        (string-downcase
                         (if (stringp event-type)
                           event-type
                           (symbol-name event-type))))
                  (cons "phase" (%wasm-startup-truth-phase-string phase))
                  (cons "monotonic_seq" (%wasm-startup-truth-next-seq))
                  (cons "payload" payload)))))
      (%wasm-startup-truth-write-record record)))

  (defun %wasm-startup-truth-open-sink-if-needed ()
    (when (and *wasm-startup-truth-enabled*
               (not (streamp *wasm-startup-truth-sink*))
               (stringp *wasm-startup-truth-path*)
               (> (length *wasm-startup-truth-path*) 0))
      (ignore-errors
        (setf *wasm-startup-truth-sink*
              (open *wasm-startup-truth-path*
                    :direction :output
                    :if-exists :supersede
                    :if-does-not-exist :create
                    :element-type 'character)
              *wasm-startup-truth-seq* 0)))
    (streamp *wasm-startup-truth-sink*))

  (defun %wasm-startup-truth-ensure-ready ()
    (when (%wasm-startup-truth-open-sink-if-needed)
      (unless *wasm-startup-truth-session-start-emitted*
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           "session-start"
           (%wasm-startup-truth-plist->json-object
            (list :output_path *wasm-startup-truth-path*))
           "collect-start")
          (setf *wasm-startup-truth-session-start-emitted* t)))
      t))

  (defun wasm-startup-truth-close-sink ()
    (when (streamp *wasm-startup-truth-sink*)
      (ignore-errors
        (finish-output *wasm-startup-truth-sink*)
        (close *wasm-startup-truth-sink*)))
    (setf *wasm-startup-truth-sink* nil)
    t)

  (defun %wasm-startup-truth-remove-plist-key (plist key)
    (let ((out nil))
      (do ((rest plist (cddr rest)))
          ((null rest) (nreverse out))
        (unless (eq (car rest) key)
          (push (cadr rest) out)
          (push (car rest) out)))))

  (defun %wasm-startup-truth-note-event (event-type &rest payload)
    (let* ((phase (or (getf payload :phase) "unknown"))
           (payload-no-phase (%wasm-startup-truth-remove-plist-key payload :phase)))
      (when (%wasm-startup-truth-ensure-ready)
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           event-type
           (%wasm-startup-truth-plist->json-object payload-no-phase)
           phase))))
    nil)

  (defun %wasm-startup-truth-intern-status-name (status-code)
    (case status-code
      (0 "none")
      (1 "ok")
      (2 "arg-invalid")
      (3 "intern-unavailable")
      (4 "name-alloc-failed")
      (5 "throw")
      (6 "result-non-symbol")
      (7 "existing-symbol")
      (8 "symbol-missing")
      (9 "symbol-synthesized")
      (t "unknown")))

  (defun %wasm-startup-truth-intern-event (resolved-symbol package intern-name intern-status-code phase-code)
    (let ((phase (%wasm-startup-truth-phase-string phase-code)))
      (when (%wasm-startup-truth-ensure-ready)
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           "intern"
           (%wasm-startup-truth-plist->json-object
            (list :intern_name intern-name
                  :intern_status_code intern-status-code
                  :intern_status (%wasm-startup-truth-intern-status-name intern-status-code)
                  :package package
                  :resolved_symbol resolved-symbol))
           phase)
          (when (symbolp resolved-symbol)
            (%wasm-startup-truth-emit-event-internal
             "symbol-identity-observe"
             (%wasm-startup-truth-plist->json-object
              (list :symbol resolved-symbol
                    :package package
                    :source "intern"))
             phase)))))
    nil))

(defun %wasm-startup-truth-output-arg-from-argv (&optional (argv *command-line-argument-list*))
  (do ((rest argv (cdr rest)))
      ((null rest) nil)
    (let ((arg (car rest)))
      (when (and (stringp arg)
                 (string= arg "--output")
                 (consp (cdr rest))
                 (stringp (cadr rest))
                 (> (length (cadr rest)) 0))
        (return (cadr rest))))))

(defun %wasm-startup-truth-init-config-from-argv ()
  (let ((output-path (%wasm-startup-truth-output-arg-from-argv)))
    (when output-path
      (setf *wasm-startup-truth-path* output-path
            *wasm-startup-truth-enabled* t
            *wasm-startup-truth-session-start-emitted* nil)))
  t)

(ignore-errors
  (%wasm-startup-truth-init-config-from-argv))

(values)
