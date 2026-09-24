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
