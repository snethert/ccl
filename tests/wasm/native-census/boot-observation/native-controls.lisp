;;; Mutate the actual retained recorder state in a fresh process, never the
;;; evidence image on disk. The independent exporter/replay must reject it.
(in-package :cl-user)
(defun boot-observation-control ()
  (let ((state (ccl::%sym-global-value 'ccl::*boot-census-state*))
        (mode (ccl:getenv "CCL_BOOT_CONTROL")))
    (cond
      ((string= mode "active") (setf (first state) t))
      ((string= mode "foreign-owner")
       ;; Exercise the actual %FHAVE recorder's owner check. A different TCR
       ;; identity must set the sticky flag without appending an event.
       (let ((count (second state)))
         (setf (fourth state) (1+ (ccl::%current-tcr)) (first state) t)
         (ccl::%fhave 'boot-control-victim (lambda () 17))
         (setf (first state) nil)
         (assert (and (fifth state) (= count (second state))))))
      ((string= mode "omit-cold-return")
       (let* ((events (reverse (third state)))
              (victim (find :cold-return events :key #'second)))
         (assert victim)
         (setq events (remove victim events :test #'eq :count 1))
         (loop for event in events for sequence from 1 do (setf (first event) sequence))
         (setf (third state) (reverse events) (second state) (length events))))
      (t (error "Unknown control ~s" mode))))
  (format t "BOOT-CONTROL-MUTATED ~a~%" (ccl:getenv "CCL_BOOT_CONTROL"))
  (finish-output)
  (export-boot-census))
