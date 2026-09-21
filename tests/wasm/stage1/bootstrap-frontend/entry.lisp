;;; Bootstrap source is trusted CCL source, read in the target environment.
;;; CCL's front end handles lexical macro scope and declarations. Unsupported
;;; acode still refuses in the Wasm emitter; the legacy source API is unchanged.
(in-package :wasm32-compiler)

(defun compile-bootstrap-form (form name links)
  (unless (and (every (lambda (entry)
                       (and (listp entry) (= (length entry) 2)
                            (symbolp (first entry)) (first entry)
                            (stringp (second entry))
                            (<= 1 (length (second entry)) 64)
                            (every (lambda (c)
                                     (find c "abcdefghijklmnopqrstuvwxyz0123456789_-"))
                                   (second entry))))
                     links)
               (= (length links) (length (remove-duplicates links :key #'first)))
               (= (length links) (length (remove-duplicates links :key #'second :test #'equal))))
    (refuse :bootstrap-links))
  (let ((*bootstrap-front-end* t)
        (*b-call-mode* t)
        (*b-special-names* '(ccl::%handlers% ccl::%restarts% *debugger-hook* ccl::*interrupt-level*))
        (*b-keywords* nil)
        (*b-call-links* links)
        (*module-name* name)
        (*module-result-tag* (gensym "BOOTSTRAP"))
        ;; Native compiler macros may fold using host representation facts.
        ;; Ordinary macros and NX1's target-aware operators remain available.
        (ccl::*nx-compile-time-compiler-macros* nil)
        (ccl::*compiler-macros* (make-hash-table :test #'eq))
        (ccl::*nx1-alphatizers* (bootstrap-alphatizers)))
    (catch *module-result-tag*
      (ccl::compile-named-function (bootstrap-function-form form)
                                  :name (if (eq (car form) 'defun) (second form) name)
                                  :target :wasm32
                                  :policy ccl::*default-compiler-policy*)
      (refuse :b-no-output))))

(defun compile-bootstrap-source (source name links &optional (package "CCL"))
  (call-with-target
   (lambda ()
     (let ((*read-eval* nil) (*package* (or (find-package package)
                                         (refuse :bootstrap-package))))
       (with-input-from-string (stream source)
         (let ((form (read stream)) (end (gensym "EOF")))
           (unless (eq end (read stream nil end)) (refuse :bootstrap-source))
           (compile-bootstrap-form form name links)))))))

(defun bootstrap-function-form (form)
  (if (eq (car form) 'defun)
    (let* ((expansion (macroexpand-1 form))
           (definition (second expansion))
           (function (second definition)))
      ;; Extract the function from CCL's own DEFUN expansion. In particular,
      ;; keep GLOBAL-FUNCTION-NAME, declarations and the implicit BLOCK.
      (unless (and (eq (car expansion) 'progn)
                   (eq (car definition) 'ccl::%defun)
                   (eq (car function) 'ccl::nfunction)
                   (equal (second function) (second form)))
        (refuse :bootstrap-defun-expansion))
      (third function))
    form))

(defun bootstrap-eq (args)
  (unless (and (= (length args) 3)
               (member (ccl::acode-immediate-operand (first args)) '(:eq :ne)))
    (refuse :bootstrap-comparison))
  (b-wat "(block (result i32) ~a)"
         (b-frame 2
                  (lambda (root)
                    (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) (if (result i32) (i32.~a (i32.load offset=8 ~a) (i32.load offset=12 ~a)) (then (i32.const 77838)) (else (i32.const 77825)))"
                           root (b-scalar (second args))
                           root (b-scalar (third args))
                           (if (eq (ccl::acode-immediate-operand (first args)) :eq) "eq" "ne")
                           root root)))))

(defun bootstrap-no-load-time-value (context form environment)
  (declare (ignore context form environment))
  ;; NX1 recursively compiles this form before emitting LOAD-TIME-VALUE.
  ;; It must not escape through the enclosing module's pass-2 result tag.
  (refuse :bootstrap-load-time-value))

(defun bootstrap-alphatizers ()
  (let ((table (make-hash-table :test #'eq)))
    (maphash (lambda (name function) (setf (gethash name table) function))
             ccl::*nx1-alphatizers*)
    (setf (gethash 'load-time-value table) #'bootstrap-no-load-time-value)
    table))
