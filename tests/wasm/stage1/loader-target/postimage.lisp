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
(format t "~&LOADER-POSTIMAGE-PASS ~s~%" *loader-postimage-observations*)
(write-string "stdout λ😀" *standard-output*)
(terpri *standard-output*)
(force-output *standard-output*)
(write-string "stderr λ😀" *error-output*)
(terpri *error-output*)
(finish-output *error-output*)
