(in-package :wasm32-compiler)

(defun core-host-env (key)
  (if (eq (schar key 0) #\P) "value" nil))

(defun core-host-count () 4)
(defun core-host-time () 4000000000)
(defvar *core-host-events* nil)

(defun core-host-action (&rest args)
  (push args *core-host-events*)
  (values :provider args))

(defun host-os-name-p (name)
  (member name '(ccl::wasm-host-service ccl:getenv cl:get-universal-time
                 ccl::cpu-count ccl:signal-semaphore ccl:wait-on-semaphore
                 ccl:timed-wait-on-semaphore ccl::yield)))
