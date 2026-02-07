;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Build the WASM32 boot image via cross-xload.

(in-package "CCL")

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/build-wasm-boot.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun ensure-ccl-logical-host (root)
  (setf (logical-pathname-translations "ccl")
        `(("l1;**;*.*" ,(merge-pathnames "level-1/**/*.*" root))
          ("l1f;**;*.*" ,(merge-pathnames "l1-fasls/**/*.*" root))
          ("ccl;*.*" ,(merge-pathnames "*.*" root))
          ("**;*.*" ,(merge-pathnames "**/*.*" root)))))

(let* ((root (repo-root-from-script)))
  (ensure-ccl-logical-host root))

(let* ((root (repo-root-from-script)))
  (load (merge-pathnames "xdump/xfasload.lisp" root)))

(defun parse-argv (argv)
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (cond
          ((string= arg "--")
           (setf seen-delimiter t))
          ((or (string= arg "-h") (string= arg "--help"))
           (push (cons :help t) out))
          ((string= arg "--force")
           (push (cons :force t) out))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/build-wasm-boot.lisp [-- --force]~%")
  (format t "Builds wasm-boot.image via cross-xload-level-0.~%"))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (force (cdr (assoc :force argv))))
    (when (cdr (assoc :help argv))
      (usage)
      (quit 0))
    (format t "~&Building wasm-boot.image...~%")
    (cross-xload-level-0 :wasm32 (if force :force t))
    (finish-output)))

(main)
(ccl:quit)
