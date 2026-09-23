(in-package :wasm32-compiler)

(defvar *validation-phase-start* (get-internal-real-time))

(defun validation-phase-complete (name)
  (let ((now (get-internal-real-time)))
    (with-open-file (stream (concatenate 'string (ccl:getenv "POOL_OUTPUT")
                                        name "-phase.json")
                            :direction :output :if-exists :error)
      (format stream "{~s:~s,~s:~s,~s:~d,~s:~d}~%"
              "status" "PASS" "phase" name "ticks"
              (- now *validation-phase-start*)
              "ticks_per_second" internal-time-units-per-second))
    (setq *validation-phase-start* now)))
