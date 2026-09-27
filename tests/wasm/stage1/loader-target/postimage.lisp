;;; This file is compiled after the boot image and loaded by STARTUP-CCL.
;;; Its definitions and effects must never be supplied by the image producer.
(in-package "CCL")

(defparameter *loader-instance-state* (list :cold 0))
(assert (equal *loader-instance-state* '(:cold 0)))

(assert (null (multiple-value-list (funcall (symbol-function 'values)))))
(assert (equal (multiple-value-list (values-list '(:first nil t))) '(:first nil t)))
(let ((many (loop for i below 32 collect i)))
  (assert (equal (multiple-value-list (apply #'values many)) many)))

(defclass loader-postimage-object ()
  ((value :initarg :value :reader loader-postimage-value)))

(defmethod loader-postimage-result ((object loader-postimage-object))
  (+ 7 (loader-postimage-value object)))

(defun loader-postimage-gc-locks ()
  (let (outer inner released)
    (setq outer (%lock-gc-lock))
    (unwind-protect
         (progn
           (setq inner (%lock-gc-lock))
           (setq released (%unlock-gc-lock)))
      (%unlock-gc-lock))
    (list (abs outer) (abs inner) (abs released))))

(defun loader-postimage-observations (invalid-list)
  (declare (optimize (safety 3)))
  (let ((table (make-hash-table :test 'equal))
        (object (make-instance 'loader-postimage-object :value 35)))
    (setf (gethash (copy-seq "key") table) (list 1 2 3))
    (list (loader-postimage-result object)
          (gethash "key" table)
          (handler-case (car invalid-list)
            (type-error (condition)
              (and (typep condition 'condition)
                   (eql (type-error-datum condition) 17))))
          (read-from-string "(alpha 42 #\\Space)")
          (mapcar #'namestring
                  (list (merge-pathnames "child.w32fsl" (pathname "/ccl/bin/"))
                        (make-pathname :name "sibling" :defaults (pathname "/ccl/bin/child.w32fsl"))))
          (multiple-value-list (decode-universal-time 2208988800 0))
          (multiple-value-list (get-saved-register-values))
          (multiple-value-list (call-check-regs #'values 3 4 nil))
          (loader-postimage-gc-locks)
          (function-source-note 17))))

(defparameter *loader-postimage-observations* (loader-postimage-observations 17))
(assert (equal *loader-postimage-observations*
               '(42 (1 2 3) t (alpha 42 #\Space)
                 ("/ccl/bin/child.w32fsl" "/ccl/bin/sibling.w32fsl")
                 (0 0 0 1 1 1970 3 nil 0) nil (3 4 nil) (1 2 1) nil)))
#+wasm32-target
(assert (eq *current-process* *initial-process*))
#+wasm32-target
(progn
  (assert (= (%address-of -17) -17))
  (assert (= (%address-of nil) 77825))
  (assert (= (%address-of t) 77838))
  (assert (= (%address-of #\A) (logior (ash 65 8) target::subtag-character)))
  (assert (= (logand (%address-of (list 1)) 7) 1))
  ;; Exercise the actual Lisp adapters, not only their host service controls.
  ;; Wall time, timezone history and CPU usage are host-dependent observations.
  (assert (typep (get-universal-time) '(integer 0 *)))
  (multiple-value-bind (minutes daylight) (get-timezone -1)
    (assert (typep minutes '(integer -1440 1440)))
    (assert (member daylight '(nil t))))
  (multiple-value-bind (user system) (%internal-run-time)
    (assert (typep user '(integer 0 *)))
    (assert (typep system '(integer 0 *))))
  (assert (<= 0 (get-internal-run-time) (get-internal-run-time)))
  (let ((fd (%open-dir "/ccl/bin/")) (names nil))
    (assert fd)
    (unwind-protect
         (loop for name = (%read-dir fd) while name do (push name names))
      (assert (zerop (close-dir fd))))
    (assert (member "loader-postimage.w32fsl" names :test #'string=)))
  (assert (= (%mkdir "/ccl/new-directory" #o755) (- target::io-error-read-only-filesystem)))
  (assert (= (%rmdir "/ccl/bin") (- target::io-error-read-only-filesystem)))
  (multiple-value-bind (success error) (unix-rename "/ccl/old" "/ccl/new")
    (assert (null success))
    (assert (= error (- target::io-error-read-only-filesystem))))
  (assert (equal (car (command-line-arguments)) (heap-image-name)))
  (assert (equal (cadr (command-line-arguments)) "--no-init"))
  (assert (null *load-lisp-init-file*))
  (assert (null *total-gc-microseconds*))
  (assert (null *total-bytes-freed*))
  (assert (= *host-page-size* 65536))
  (assert (= (cpu-count) 1))
  (assert (= *ticks-per-second* 1000))
  (assert (= *ns-per-tick* 1000000))
  (assert (eql (lisp-thread.tcr *initial-lisp-thread*) (%current-tcr)))
  (assert (= (lisp-thread.vs-size *initial-lisp-thread*) (%wasm-area-size 5)))
  (assert (equal (list *initial-listener-default-control-stack-size*
                       *initial-listener-default-value-stack-size*
                       *initial-listener-default-temp-stack-size*)
                 (list *default-control-stack-size* *default-value-stack-size*
                       *default-temp-stack-size*)))
  (assert (equal (namestring (ccl-directory)) "/ccl/")))
#+wasm32-target
(assert (handler-case (join-process *current-process*)
          (simple-error () t)))
;; Native CCL serializes the raw lambda for globally inline definitions,
;; dropping MACROLET's environment. Compare the native function call with
;; the Wasm producer's retained, lexical cross-file expansion.
#+wasm32-target (declaim (inline loader-cross-file-inline))
#-wasm32-target (declaim (notinline loader-cross-file-inline))
(macrolet ((local-offset (x) `(+ ,x 17)))
  (defun loader-cross-file-inline (x) (local-offset x)))

;;; Startup execution optimizations: these same assertions run in native
;;; CCL when the post-image witness is compiled, then through ordinary LOAD.
(defun loader-predicates (x)
  (list (not (null (listp x))) (not (null (fixnump x)))
        (not (null (symbolp x))) (not (null (integerp x)))
        (not (null (stringp x)))))
(assert (equal (mapcar #'loader-predicates (list nil t '(1) 7 (ash 1 80) "abc" #() #\A))
               '((t nil t nil nil) (nil nil t nil nil) (t nil nil nil nil)
                 (nil t nil t nil) (nil nil nil t nil) (nil nil nil nil t)
                 (nil nil nil nil nil) (nil nil nil nil nil))))
(defun loader-length (x) (length x))
(defun loader-memq (x list) (memq x list))
(assert (equal (mapcar #'loader-length (list nil '(1 2 3) "abc" #(1 2))) '(0 3 3 2)))
(let ((v (make-array 5 :fill-pointer 2 :initial-element nil)))
  (assert (= 2 (loader-length v))))
(assert (handler-case (loader-length '(1 . 2)) (type-error () t)))
(let* ((tail (list :found :last)) (list (cons :first tail)) (calls 0))
  (assert (eq (memq (progn (incf calls) :found) (progn (incf calls) list)) tail))
  (assert (= calls 2))
  (assert (null (loader-memq :absent list))))
(assert (handler-case (loader-memq :absent '(1 . 2)) (type-error () t)))

(defclass loader-cache-parent () ())
(defclass loader-cache-other () ())
(defclass loader-cache-child (loader-cache-parent) ())
(defmethod loader-cache-dispatch ((x loader-cache-parent)) :parent)
(defmethod loader-cache-dispatch ((x loader-cache-other)) :other)
(defparameter *loader-cache-object* (make-instance 'loader-cache-child))
(dotimes (i 3) (assert (eq (loader-cache-dispatch *loader-cache-object*) :parent)))
(defun loader-redefine-cache-child ()
  (defclass loader-cache-child (loader-cache-other) ()))
(loader-redefine-cache-child)
(dotimes (i 3) (assert (eq (loader-cache-dispatch *loader-cache-object*) :other)))
(defmethod loader-cache-dispatch ((x loader-cache-child)) (list :child (call-next-method)))
(dotimes (i 3) (assert (equal (loader-cache-dispatch *loader-cache-object*) '(:child :other))))
(remove-method #'loader-cache-dispatch
               (find-method #'loader-cache-dispatch nil (list (find-class 'loader-cache-child))))
(assert (eq (loader-cache-dispatch *loader-cache-object*) :other))
(clear-gf-cache #'loader-cache-dispatch)
(assert (eq (loader-cache-dispatch *loader-cache-object*) :other))

#+wasm32-target
(let* ((gf #'loader-cache-dispatch) (old (%gf-dispatch-table gf))
       (compact (%cons-gf-dispatch-table 0)))
  (dotimes (i %gf-dispatch-table-first-data)
    (setf (svref compact i) (svref old i)))
  (unwind-protect
       (progn
         (setf (%gf-dispatch-table gf) compact)
         (compute-dcode gf)
         (dotimes (i 3)
           (assert (eq (loader-cache-dispatch *loader-cache-object*) :other)))
         (assert (eq (svref compact %gf-dispatch-table-first-data) (%unbound-marker))))
    (setf (%gf-dispatch-table gf) old)
    (compute-dcode gf)))

(defmethod loader-cache-eql ((x integer)) :integer)
(defmethod loader-cache-eql ((x (eql 7))) :seven)
(dotimes (i 3)
  (assert (eq (loader-cache-eql 7) :seven))
  (assert (eq (loader-cache-eql 8) :integer)))
(defmethod loader-cache-zero () :zero)
(dotimes (i 3) (assert (eq (loader-cache-zero) :zero)))
(remove-method #'loader-cache-zero (find-method #'loader-cache-zero nil nil))
(assert (handler-case (loader-cache-zero) (error () t)))
(defmethod loader-cache-keywords ((x integer) &key value) (list x value))
(dotimes (i 3)
  (assert (equal (loader-cache-keywords 1 :value i) (list 1 i)))
  (assert (handler-case (loader-cache-keywords 1 :invalid i) (error () t))))

#+wasm32-target
(progn
  (let* ((name "LOADER-FASL-CACHE") (nickname "LOADER-FASL-NICK")
         (p (make-package name :nicknames (list nickname) :use nil)))
    (unwind-protect
         (progn
           (assert (eq (%fasl-find-pkg nickname (length nickname)) p))
           (assert (eq (%fasl-find-pkg nickname (length nickname)) p))
           (rename-package p name nil)
           (assert (null (%fasl-find-pkg nickname (length nickname))))
           (assert (eq (%fasl-find-pkg name (length name)) p))
           (delete-package p)
           (assert (null (%fasl-find-pkg name (length name)))))
      (when (package-name p) (delete-package p))))
  (let* ((*istruct-cells* nil) (name (gensym))
         (cell (register-istruct-cell name)))
    (assert (eq cell (register-istruct-cell name)))
    (let ((*istruct-cells* nil))
      (assert (not (eq cell (register-istruct-cell name)))))
    (assert (eq cell (register-istruct-cell name)))))

(format t "~&LOADER-POSTIMAGE-PASS ~s~%" *loader-postimage-observations*)
(write-string "stdout λ😀" *standard-output*)
(terpri *standard-output*)
(force-output *standard-output*)
(write-string "stderr λ😀" *error-output*)
(terpri *error-output*)
(finish-output *error-output*)
