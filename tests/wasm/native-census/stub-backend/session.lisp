;;; Run in a fresh native process. Sources are compiled through registered module entries.
(in-package "CCL")
(load (compile-file "ccl:lib;systems.lisp"))
(when (equal (getenv "CCL_CENSUS_MODE") "missing-registration")
  (setf *ccl-system* (remove 'wasm-census-arch *ccl-system* :key #'car)))
(dolist (name '(wasm-census-arch wasm-census-backend))
  (multiple-value-bind (binary sources) (find-module name (backend-name *host-backend*))
    (load (compile-file (car sources) :output-file binary))))
(in-package "CCL-CENSUS-STUB")

(defun state ()
  (list ccl::*target-backend* ccl::*target-ftd* ccl::*fasl-target* *features*
        (find-package "TARGET") (find-package "OS")))

(defun literals (afunc)
  (let ((seen (make-hash-table :test #'eq)) (todo (list (ccl::afunc-acode afunc))) (result nil))
    (loop while todo for node = (pop todo) do
      (cond ((ccl::acode-p node)
             (unless (gethash node seen)
               (setf (gethash node seen) t)
               (let ((op (ccl::acode-operator-name (ccl::acode-operator node))))
                 (when (member op '(ccl::fixnum ccl::immediate))
                   (push (list (ccl-startup-census::label-of op)
                               (ccl-startup-census::label-of (car (ccl::acode-operands node)))) result)))
             (push (ccl::acode-operands node) todo)))
            ((consp node)
             (unless (gethash node seen)
               (setf (gethash node seen) t) (push (car node) todo) (push (cdr node) todo)))))
    (nreverse result)))

(defun argument-partitions (afunc)
  (let ((todo (list (ccl::afunc-acode afunc))) (seen (make-hash-table :test #'eq)) (result nil) (access-flags nil))
    (loop while todo for node = (pop todo) do
      (when (and (or (consp node) (ccl::acode-p node)) (not (gethash node seen)))
        (setf (gethash node seen) t)
        (if (ccl::acode-p node)
          (progn
            (when (eq (ccl::acode-operator-name (ccl::acode-operator node)) 'ccl::immediate-get-xxx)
              (push (car (ccl::acode-operands node)) access-flags))
            (when (eq (ccl::acode-operator-name (ccl::acode-operator node)) 'ccl::call)
              (let ((args (cadr (ccl::acode-operands node))))
                (push (list (length (first args)) (length (second args))) result)))
            (push (ccl::acode-operands node) todo))
          (progn (push (car node) todo) (push (cdr node) todo)))))
    (values (nreverse result) (nreverse access-flags))))

(defun read-corpus (path)
  (let ((*package* (find-package "CCL-CENSUS-STUB")))
    (with-open-file (s path)
      (loop for form = (read s nil s) until (eq form s) collect form))))

(defun run-session ()
  (let* ((mode (or (ccl:getenv "CCL_CENSUS_MODE") "normal"))
         (*features* (if (string= mode "dirty-features") (cons :x8632-target *features*) *features*))
         (before (state))
         (fixture (ccl:getenv "CCL_CENSUS_FIXTURE"))
         (macro-path (concatenate 'string fixture "/target-macro.lisp"))
         (corpus-path (concatenate 'string fixture "/corpus.lisp"))
         (early (when (string= mode "late-package") (read-corpus corpus-path)))
         (old-args (ccl::backend-num-arg-regs *backend*))
         (arch (ccl::backend-target-arch *backend*))
         (old-bits (arch::target-nbits-in-word arch))
         (rows nil) (macro-expansion nil) (during nil))
    (when (string= mode "cached-host-macro")
      (load (compile-file macro-path :output-file (ccl:getenv "CCL_CENSUS_CACHE"))))
    (unwind-protect
      (progn
        (when (string= mode "wrong-args") (setf (ccl::backend-num-arg-regs *backend*) 3))
        (when (string= mode "wrong-width") (setf (arch::target-nbits-in-word arch) 64))
        (with-target-state
          (lambda ()
            (let ((*features* (if (string= mode "host-features") (fourth before) *features*))
                  (ccl::*target-backend* (if (string= mode "host-backend") (first before) ccl::*target-backend*)))
              (setf during (list (ccl-startup-census::label-of (ccl::backend-name ccl::*target-backend*))
                                 (package-name (find-package "TARGET"))
                                 (package-name (find-package "OS"))
                                 (ccl-startup-census::label-of ccl::*fasl-target*)
                                 (if (eq ccl::*target-ftd* (ccl::backend-target-foreign-type-data *backend*)) :true :false)))
              (unless (string= mode "cached-host-macro") (load macro-path))
              (setf macro-expansion
                    (ccl-startup-census::label-of (car (macroexpand-1 '(ccl::%get-natural p)))))
              (dolist (record (or early (read-corpus corpus-path)))
                (let* ((name (first record)) (afunc (capture-lambda (second record) name)))
                  (multiple-value-bind (partitions access-flags) (argument-partitions afunc)
                    (push (ccl-startup-census::object
                         "name" (symbol-name name) "literals" (literals afunc)
                         "argument_partitions" partitions "memory_access_flags" access-flags
                         "function" (ccl-startup-census::function-observation afunc)) rows))))))))
      (setf (ccl::backend-num-arg-regs *backend*) old-args
            (arch::target-nbits-in-word arch) old-bits))
    (unless (equal before (state)) (error "Target state was not restored"))
    ;; The same wrapper must restore global nicknames and dynamic state on escape.
    (catch 'escape (with-target-state (lambda () (throw 'escape t))))
    (unless (equal before (state)) (error "Target state leaked on escape"))
    (with-open-file (s (ccl:getenv "CCL_CENSUS_REPORT") :direction :output :if-exists :error)
      (ccl-startup-census::json
       (ccl-startup-census::object "version" 1 "mode" mode "during" during
                                 "natural_macro_operator" macro-expansion "rows" (nreverse rows)
                                 "restored_normal_and_escape" :true
                                 "native_snapshot_after" (ccl-startup-census::snapshot)) s)
      (terpri s))
    (format t "CENSUS-STUB-CAPTURE-COMPLETE~%")
    (ccl:quit)))
(run-session)
