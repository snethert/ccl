;;; Read-only namespace primitives.  This file follows l0-io on wasm32.
;;; A target buffer is a simple octet vector, never a foreign pointer.
(in-package "CCL")











(defun fd-tell (fd)
  (fd-lseek fd 0 1))

(defun %realpath (path)
  (declare (simple-string path))
  (when (eq (uvsize path) 0)
    (setq path "."))
  (%wasm-file-request 5 path nil nil))

(defun %unix-file-kind (path &optional check-for-link)
  ;; The namespace contains no links; checking for one still evaluates the
  ;; argument, but does not change the kind of an admitted entry.
  (let ((kind (%wasm-file-request 6 path check-for-link nil)))
    (cond ((eq kind 1) :file)
          ((eq kind 2) :directory)
          (t nil))))



;;; The virtual namespace owns the current directory; no process cwd leaks in.
(defun current-directory-name ()
  (%realpath "."))

(defun %probe-file-x (namestring)
  (let* ((realpath (%realpath namestring))
         (kind (if realpath (%unix-file-kind realpath))))
    (if kind (values realpath kind) (values nil nil))))

(defun fd-input-available-p (fd timeout)
  (declare (ignore timeout))
  ;; All admitted regular byte sources are ready, including EOF.
  (>= (fd-size fd) 0))

;;; The owner passes the admitted manifest's CCL root. The current directory
;;; comes from the same namespace session through %REALPATH.
(defvar *wasm-namespace-ccl-root* nil)

(defun %wasm-namespace-support-initialize ()
  ;; Install the target's table and package representation boundaries before
  ;; the original type, foreign-type and stream initializers run.
  (fset 'make-hash-table #'%wasm-make-hash-table)
  (fset 'gethash #'%wasm-gethash)
  (fset 'puthash #'%wasm-puthash)
  (fset 'remhash #'%wasm-remhash)
  (fset 'clrhash #'%wasm-clrhash)
  (fset 'maphash #'%wasm-maphash)
  (fset 'hash-table-count #'%wasm-hash-table-count)
  (fset 'sxhash #'%wasm-sxhash)
  (fset 'intern #'%wasm-intern)
  (fset 'find-symbol #'%wasm-find-symbol)
  (setq *lfun-names* (%wasm-make-class-table 16))
  t)

(defun %wasm-namespace-initialize (ccl-root)
  (let ((root (%realpath ccl-root))
        (cwd (%realpath ".")))
    (unless (and root cwd
                 (eq (%unix-file-kind root) :directory)
                 (eq (%unix-file-kind cwd) :directory))
      (error "The namespace roots must name directories."))
    (let* ((defaults (native-to-directory-pathname cwd))
           (translations
             (let ((*wasm-namespace-ccl-root* root)
                   (*default-pathname-defaults* defaults)
                   (%logical-host-translations% nil))
               (setup-initial-translations)
               %logical-host-translations%)))
      ;; Build and validate the complete translation list before publication.
      (setq *wasm-namespace-ccl-root* root
            *default-pathname-defaults* defaults
            %logical-host-translations% translations)
      t)))

(defun %wasm-file-error-string (errno)
  (case errno
    (2 "No such file or directory : ~s")
    (9 "Bad file descriptor : ~s")
    (17 "File exists : ~s")
    (20 "Not a directory : ~s")
    (21 "Is a directory : ~s")
    (22 "Invalid argument : ~s")
    (24 "Too many open files : ~s")
    (30 "Read-only file system : ~s")
    (t "File operation failed : ~s")))

(defun %wasm-native-ffi-excluded (&rest arguments)
  (declare (ignore arguments))
  (error "Native foreign calls are excluded from the Wasm target."))
