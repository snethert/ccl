
;;; Ordinary public lock calls; both native and Wasm create their own state.
(defun loader-rwlock-packages ()
  (let ((ccl (pkg.lock (find-package "CCL")))
        (cl (pkg.lock (find-package "COMMON-LISP")))
        (keyword (pkg.lock (find-package "KEYWORD"))))
    (values (read-write-lock-p ccl) (read-write-lock-p cl)
            (read-write-lock-p keyword) (not (eq ccl cl)) (not (eq cl keyword))
            (read-lock-rwlock ccl) (unlock-rwlock ccl)
            (write-lock-rwlock keyword) (unlock-rwlock keyword))))

(defun loader-rwlock-basic ()
  (let ((lock (make-read-write-lock)) (other (make-read-write-lock))
        (flag (make-lock-acquisition)))
    (values (read-write-lock-p lock) (not (eq lock other))
            (read-lock-rwlock lock flag) (lock-acquisition-status flag)
            (read-lock-rwlock lock) (unlock-rwlock lock) (unlock-rwlock lock)
            (write-lock-rwlock lock flag) (lock-acquisition-status flag)
            (write-lock-rwlock lock) (unlock-rwlock lock) (unlock-rwlock lock))))

(defun loader-rwlock-promote ()
  (let ((lock (make-read-write-lock)) (flag (make-lock-acquisition)))
    (values (read-lock-rwlock lock) (%promote-rwlock lock flag)
            (lock-acquisition-status flag) (unlock-rwlock lock))))

(defun loader-rwlock-allocate (n)
  (let ((cell (cons -1 27)))
    (dotimes (i n) (setq cell (cons i (cdr cell))))
    (values (car cell) (cdr cell))))

(defun loader-rwlock-cleanup (n)
  (let ((lock (make-read-write-lock)) (trace nil))
    (values
     (catch 'done
       (with-write-lock (lock)
         (push 1 trace)
         (with-write-lock (lock)
           (push (loader-rwlock-allocate n) trace)
           (throw 'done 71))))
     (with-read-lock (lock)
       (with-read-lock (lock) (push 2 trace))
       (car trace))
     (write-lock-rwlock lock) (unlock-rwlock lock) trace)))

;;; Keep a held lock in a Lisp global across an owner-driven moving collection.
(defvar *loader-rwlock* nil)
(defun loader-rwlock-hold ()
  (setq *loader-rwlock* (make-read-write-lock))
  (write-lock-rwlock *loader-rwlock*)
  (write-lock-rwlock *loader-rwlock*))
(defun loader-rwlock-release ()
  (values (read-write-lock-p *loader-rwlock*)
          (unlock-rwlock *loader-rwlock*) (unlock-rwlock *loader-rwlock*)
          (read-lock-rwlock *loader-rwlock*) (unlock-rwlock *loader-rwlock*)))

;;; The diagnostic image has the declared early error service, not class-mode
;;; conditions. Refusal controls observe its checked error and preserved state.
(defun loader-rwlock-operation (operation lock flag)
  (let ((%handlers% nil))
    (case operation
      (0 (make-read-write-lock))
      (1 (read-lock-rwlock lock flag))
      (2 (write-lock-rwlock lock flag))
      (3 (unlock-rwlock lock))
      (4 (%promote-rwlock lock flag))
      (5 (%wasm-rwlock-state flag lock))
      (6 (%revive-system-locks))
      (7 (make-semaphore))
      (8 (%cstr-pointer "x" lock))
      (9 (%cstr-segment-pointer "x" lock 0 1))
      (10 (make-gcable-macptr 0))
      (11 (with-write-lock (lock) (error "Read/write lock cleanup witness.")))
      (12 1.0d0))))
