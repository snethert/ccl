(in-package :wasm32-compiler)

(defun frontend-links (form)
  (let ((symbols nil))
    (labels ((walk (x)
               (cond ((symbolp x)
                      (when (and x (fboundp x)
                                 (not (macro-function x))
                                 (not (special-operator-p x)))
                        (pushnew x symbols)))
                     ((consp x)
                      (unless (eq (car x) 'quote)
                        (walk (car x))
                        (walk (cdr x)))))))
      (walk form))
    (loop for symbol in (nreverse symbols)
          for i from 0
          collect (list symbol (format nil "link_~d" i)))))

(defvar *frontend-message* nil)
(defvar *frontend-result* nil)

(defun frontend-outcome (thunk)
  (setq *frontend-message* nil *frontend-result* nil)
  (handler-case (progn (setq *frontend-result* (funcall thunk)) "admitted")
    (unsupported-wasm32-code (c) (symbol-name (unsupported-operation c)))
    (error (c)
      (setq *frontend-message* (format nil "~a" c))
      (format nil "~a" (type-of c)))))

(defun frontend-json-string (string stream)
  (write-char #\" stream)
  (loop for c across string do
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

(defun frontend-file-macros (form)
  (when (consp form)
    (case (car form)
      (defmacro (list (second form)))
      ((progn eval-when)
       (mapcan #'frontend-file-macros
               (if (eq (car form) 'eval-when) (cddr form) (cdr form)))))))

(defun frontend-local-macro-calls (form names)
  (when (consp form)
    (unless (eq (car form) 'quote)
      (union (and (member (car form) names) (list (car form)))
             (union (frontend-local-macro-calls (car form) names)
                    (frontend-local-macro-calls (cdr form) names))))))

(defvar *frontend-functions* nil)
(defun measure-frontend (chunks out)
  (let ((functions nil) (skips nil) (macros nil))
    (call-with-target
     (lambda ()
       (dolist (row chunks)
         (destructuring-bind (file unused text) row
           (declare (ignore unused))
           (let ((*package* (find-package "CCL")) (*read-eval* nil))
             (with-input-from-string (stream text)
               (loop
                 (let ((offset (file-position stream)) (end (gensym "EOF")))
                   (handler-case
                       (let ((form (read stream nil end)))
                         (when (eq form end) (return))
                         (dolist (name (frontend-file-macros form))
                           (push (cons file name) macros))
                         (cond ((and (consp form) (eq (car form) 'in-package))
                                (setq *package* (or (find-package (second form))
                                                    (error "Unknown source package"))))
                               ((and (consp form) (eq (car form) 'defun))
                                (if (symbolp (second form))
                                  (push (list file offset form) functions)
                                  (push (list file offset "compound-function-name") skips)))))
                     (error (c)
                       (push (list file offset (format nil "~a" (type-of c))) skips)
                       ;; Retain the read failure. Recovery is only a diagnostic
                       ;; census aid, never an input to the execution corpus.
                       (let ((next (loop for i from (max (1+ offset) (file-position stream))
                                         below (length text)
                                         when (and (char= (char text i) #\()
                                                   (char= (char text (1- i)) #\Newline))
                                         return i)))
                         (if next (file-position stream next) (return)))))))))))))
    (setq functions (nreverse functions) *frontend-functions* functions)
    (with-open-file (s (concatenate 'string out "throughput.json")
                       :direction :output :if-exists :error)
      (format s "{\"functions\":[")
      (loop for row in functions for i from 0 do
        (destructuring-bind (file offset form) row
          (let* ((links (frontend-links form))
                 (lambda-form `(lambda ,(third form) ,@(cdddr form)))
                 (old (frontend-outcome
                       (lambda () (compile-call-form lambda-form "probe" nil))))
                 (new (frontend-outcome
                       (lambda ()
                         (call-with-target
                          (lambda () (compile-bootstrap-form form "probe" links)))))))
            (unless (zerop i) (write-char #\, s))
            (format s "{\"file\":~s,\"offset\":~d,\"package\":~s,\"name\":~s,\"baseline\":~s,\"proposal\":~s"
                    file offset (package-name (symbol-package (second form)))
                    (symbol-name (second form)) old new)
            (write-string ",\"message\":" s)
            (if *frontend-message* (frontend-json-string *frontend-message* s)
                (write-string "null" s))
            (format s ",\"dynamic_call\":~a,\"callees\":["
                    (if (or (getf *frontend-result* :dynamic-call)
                            (assoc 'apply links) (assoc 'funcall links)) "true" "false"))
            (loop for symbol in (getf *frontend-result* :dependencies) for j from 0 do
              (unless (zerop j) (write-char #\, s))
              (format s "[~s,~s]" (and (symbol-package symbol)
                                       (package-name (symbol-package symbol)))
                      (symbol-name symbol)))
            (format s "],\"file_macro_calls\":[")
            (loop for name in (frontend-local-macro-calls
                              form (mapcar #'cdr (remove file macros :key #'car :test-not #'equal)))
                  for j from 0 do
              (unless (zerop j) (write-char #\, s))
              (format s "~s" (symbol-name name)))
            (format s "]}"))))
      (format s "],\"skips\":[")
      (loop for (file offset reason) in (nreverse skips) for i from 0 do
        (unless (zerop i) (write-char #\, s))
        (format s "{\"file\":~s,\"offset\":~d,\"reason\":~s}" file offset reason))
      (format s "]}"))))
