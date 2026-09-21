(in-package :ccl)

;;; Only architecture constants are needed. These are CCL's source modules,
;;; not mock target values or cross-compiled machine code.
(require-modules '(ppc-arch ppc32-arch ppc64-arch x8632-arch x8664-arch arm-arch))

(defun reader-backends ()
  (let ((*features* (append '(:linuxppc-target :darwinppc-target :linuxx86-target
                             :darwinx86-target :freebsdx86-target :solarisx86-target
                             :win64-target :windows-target :solaris-target :freebsd-target)
                           *features*))
        (*package* (find-package :ccl))
        (backends nil))
    (labels ((visit (form)
               (when (consp form)
                 (if (eq (car form) 'make-backend)
                   (let* ((args (cdr form)) (features (getf args :target-specific-features)))
                     (assert (eq (car features) 'quote))
                     (push (list (getf args :name) (getf args :target-arch-name)
                                 (second features) (getf args :target-arch)) backends))
                   (progn (visit (car form)) (visit (cdr form)))))))
      (dolist (source '(("PPC/PPC32/ppc32-backend.lisp" 2) ("PPC/PPC64/ppc64-backend.lisp" 2)
                        ("X86/X8632/x8632-backend.lisp" 5) ("X86/X8664/x8664-backend.lisp" 5)
                        ("ARM/arm-backend.lisp" 3)))
        (let ((limit (+ (length backends) (second source))))
          (with-open-file (s (merge-pathnames (first source) (merge-pathnames "compiler/" (getenv "READER_U1"))))
            (loop while (< (length backends) limit) for form = (read s nil :eof)
                  do (assert (not (eq form :eof))) (visit form))))))
    (assert (= (length backends) 17))
    (assert (= (length (remove-duplicates backends :key #'car)) 17))
    (sort backends #'string< :key (lambda (row) (symbol-name (car row))))))

(defun same-reader-forms (a b)
  ;; EQUALP alone would hide string case and numeric representation changes.
  (cond ((consp a) (and (consp b) (same-reader-forms (car a) (car b))
                       (same-reader-forms (cdr a) (cdr b))))
        ((vectorp a) (and (vectorp b)
                          (equal (array-element-type a) (array-element-type b))
                          (= (length a) (length b))
                          (every #'same-reader-forms a b)))
        (t (eql a b))))

(assert (same-reader-forms '(x #(1 "abc")) '(x #(1 "abc"))))
(assert (not (same-reader-forms '(x "abc") '(x "ABC"))))
(assert (not (same-reader-forms '(x 1) '(x 1.0))))

(defun reader-forms (path)
  (let ((*package* (find-package :ccl)) (*read-eval* t))
    (with-open-file (s path)
      (loop for form = (read s nil :eof) until (eq form :eof)
            collect form
            do (when (and (consp form) (eq (car form) 'in-package))
                 (setq *package* (find-package (second form))))))))

(let ((rows nil))
  (dolist (profile (reader-backends))
    (destructuring-bind (name arch features target-arch) profile
      ;; Use CCL's own feature substitution and TARGET nickname discipline.
      (let* ((backend (if (eq name (backend-name *host-backend*)) *host-backend*
                       (let ((copy (copy-backend *host-backend*)))
                         (setf (backend-name copy) name
                               (backend-target-arch-name copy) arch
                               (backend-target-arch copy) (eval target-arch)
                               (backend-target-specific-features copy) features)
                         copy)))
             (*target-backend* backend)
             (*features* (setup-target-features backend *features*)))
        (with-cross-compilation-package ("TARGET" (symbol-name arch))
          (dolist (stem '("l0-def" "l0-pred" "l0-utils"))
            (let* ((relative (concatenate 'string "level-0/" stem ".lisp"))
                   (before (reader-forms (merge-pathnames relative (getenv "READER_U1"))))
                   (after (reader-forms (merge-pathnames relative (getenv "READER_PROPOSAL"))))
                   (equal (same-reader-forms before after)))
              (assert equal () "Existing-target reader changed: ~s ~a" name relative)
              (let ((*print-pretty* nil) (*print-circle* t) (*package* (find-package :cl-user)))
                (with-open-file (s (merge-pathnames (format nil "~(~a~)-~a.forms" name stem)
                                                   (getenv "READER_OUTPUT"))
                                   :direction :output :if-exists :error)
                  (prin1 before s) (terpri s)))
              (push (ccl-startup-census::object
                     "target" (string-downcase name) "architecture" (string-downcase arch)
                     "file" relative "forms" (length before) "equal" :true
                     "features" (mapcar #'string-downcase (sort (copy-list *features*) #'string<))) rows)))))))
  (with-open-file (s (merge-pathnames "readers.json" (getenv "READER_OUTPUT"))
                     :direction :output :if-exists :error)
    (ccl-startup-census::json
     (ccl-startup-census::object "status" "PASS" "rows" (nreverse rows)) s)))
(format t "READER-EQUIVALENCE-PASS~%")
(quit)
