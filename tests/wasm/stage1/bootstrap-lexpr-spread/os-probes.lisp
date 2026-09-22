(in-package :wasm32-compiler)

(defun core-host-env (key)
  (if (eq (schar key 0) #\P) "value" nil))

(defun core-host-count () (push :cpu-count *core-host-events*) 4)
(defun core-host-time () 4000000000)
(defvar *core-host-events* nil)

(defun core-host-action (&rest args)
  (push args *core-host-events*)
  (values :provider args))

(defun host-os-name-p (name)
  (member name '(ccl::wasm-host-service ccl:getenv cl:get-universal-time
                 ccl::cpu-count ccl:signal-semaphore ccl:wait-on-semaphore
                 ccl:timed-wait-on-semaphore ccl::yield)))

(defun core-host-cpu-cache (getter)
  (values (funcall getter) (funcall getter)))

(defun core-host-cpu-warm (getter)
  (setq ccl::*cpu-count* 2)
  (values (funcall getter) ccl::*cpu-count*))

(defun core-host-wait-caller (wait semaphore)
  (funcall wait semaphore))

(defun core-host-timed-caller (wait semaphore)
  (funcall wait semaphore 3))
