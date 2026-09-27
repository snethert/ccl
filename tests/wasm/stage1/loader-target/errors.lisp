;;; Error and restart paths that used to call an absent native frame primitive.
(in-package "CCL")

(dolist (code (list $xnotfasl $xfaslvers))
  (assert (handler-case (%err-disp code)
            (undefined-function () nil)
            (simple-error () t))))
(assert (handler-case (%errno-disp (logior (ash 2 16) 12) "/ccl/error-probe")
          (file-error (condition)
            (equal (file-error-pathname condition) "/ccl/error-probe"))))

(let ((value :bad) (calls 0))
  (handler-bind ((type-error (lambda (condition)
                              (assert (eq (type-error-datum condition) :bad))
                              (incf calls)
                              (store-value 17 condition))))
    (check-type value integer)
    (assert (= value 17))
    (assert (= 17 (ensure-value-of-type :bad 'integer 'value)))
    (assert (= calls 2))))

(let ((condition (make-condition 'simple-error :format-control "debugger witness")))
  (assert (eq :caught
              (catch 'debugger-witness
                (let ((*debugger-hook*
                        (lambda (observed hook)
                          (assert (eq observed condition))
                          (assert (functionp hook))
                          (assert (null *debugger-hook*))
                          (throw 'debugger-witness :caught))))
                  (invoke-debugger condition))))))
(assert (eq :muffled
            (block warning-witness
              (handler-bind ((warning (lambda (condition) (muffle-warning condition))))
                (warn "frame-free warning")
                (return-from warning-witness :muffled)))))

(let ((first (make-package "LOADER-ERROR-FIRST" :use nil))
      (second (make-package "LOADER-ERROR-SECOND" :use nil))
      (user (make-package "LOADER-ERROR-USER" :use nil)))
  (unwind-protect
       (progn
         (assert (equal "LOADER-ERROR-NEW"
                        (handler-bind ((simple-error
                                         (lambda (condition)
                                           (invoke-restart (find-restart 'new-name condition)
                                                           "LOADER-ERROR-NEW"))))
                          (new-package-name "LOADER-ERROR-FIRST"))))
         (assert (null
                  (handler-bind ((package-error (lambda (condition) (continue condition))))
                    (new-package-nickname "LOADER-ERROR-FIRST" second))))
         (let ((a (intern "CONFLICT" first)) (b (intern "CONFLICT" second)))
           (use-package (list first second) user)
           (export a first)
           (assert (handler-case (progn (export b second) nil)
                     (package-error () t)))))
    (delete-package user)
    (delete-package second)
    (delete-package first)))

#+wasm32-target
(progn
  (assert (null (%get-frame-ptr)))
  (assert (null (%last-fn-on-stack)))
  (assert (null (%last-fn-on-stack 3)))
  (assert (equal (%real-err-fn-name nil) "Unknown")))

(format t "~&LOADER-ERROR-PATHS-PASS~%")
