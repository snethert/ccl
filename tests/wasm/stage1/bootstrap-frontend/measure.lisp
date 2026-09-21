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

(defun frontend-outcome (thunk)
  (handler-case (progn (funcall thunk) "admitted")
    (unsupported-wasm32-code (c) (symbol-name (unsupported-operation c)))
    (error (c) (format nil "~a" (type-of c)))))

(defvar *frontend-functions* nil)
(defun measure-frontend (chunks out)
  (let ((functions nil) (skips nil))
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
            (format s "{\"file\":~s,\"offset\":~d,\"package\":~s,\"name\":~s,\"baseline\":~s,\"proposal\":~s}"
                    file offset (package-name (symbol-package (second form)))
                    (symbol-name (second form)) old new))))
      (format s "],\"skips\":[")
      (loop for (file offset reason) in (nreverse skips) for i from 0 do
        (unless (zerop i) (write-char #\, s))
        (format s "{\"file\":~s,\"offset\":~d,\"reason\":~s}" file offset reason))
      (format s "]}"))))
