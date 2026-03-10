;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Canonical WASM startup order for level-1/bin FASLs.

(in-package "CCL")

(defparameter *wasm-runtime-startup-module-specs*
  '(("l1-cl-package" "l1-fasls")
    ("l1-utils" "l1-fasls")
    ("l1-init" "l1-fasls")
    ("l1-symhash" "l1-fasls")
    ("l1-numbers" "l1-fasls")
    ("l1-aprims" "l1-fasls")
    ("l1-callbacks" "l1-fasls")
    ("l1-sort" "l1-fasls")
    ("lists" "bin")
    ("sequences" "bin")
    ("l1-dcode" "l1-fasls")
    ("l1-clos-boot" "l1-fasls")
    ("hash" "bin")
    ("l1-clos" "l1-fasls")
    ("defstruct" "bin")
    ("dll-node" "bin")
    ("l1-unicode" "l1-fasls")
    ("l1-streams" "l1-fasls")
    ("linux-files" "l1-fasls")
    ("chars" "bin")
    ("l1-files" "l1-fasls")
    ("l1-typesys" "l1-fasls")
    ("sysutils" "l1-fasls")
    ("l1-lisp-threads" "l1-fasls")
    ("l1-application" "l1-fasls")
    ("l1-processes" "l1-fasls")
    ("l1-io" "l1-fasls")
    ("l1-reader" "l1-fasls")
    ("l1-readloop" "l1-fasls")
    ("l1-error-signal" "l1-fasls")
    ("l1-readloop-lds" "l1-fasls")
    ("l1-error-system" "l1-fasls")
    ("l1-events" "l1-fasls")
    ("l1-format" "l1-fasls")
    ("l1-sysio" "l1-fasls")
    ("l1-pathnames" "l1-fasls")
    ("l1-boot-lds" "l1-fasls")
    ("l1-boot-1" "l1-fasls")
    ("l1-boot-2" "l1-fasls")
    ("l1-boot-3" "l1-fasls")
    ("dumplisp" "bin"))
  "Canonical WASM startup/module load order for root-image bootstrapping.")

(defparameter *wasm-runtime-extra-compile-modules*
  '("level-1" "version" "l1-sockets")
  "Modules still compiled into the runtime bundle, but not part of startup order.")

(defparameter *wasm-runtime-level-1-insertions*
  '(("l1-readloop" ("l1-error-signal" "l1-fasls")))
  "WASM-specific startup insertions anchored to the native level-1 sequence.")

(defparameter *wasm-runtime-level-1-tail-specs*
  '(("dumplisp" "bin"))
  "WASM-only modules intentionally loaded after the native level-1 sequence.")

(defun wasm-startup-order-root ()
  (let ((script (or *load-truename*
                    (probe-file "scripts/wasm/wasm-startup-order.lisp"))))
    (unless script
      (error "Cannot determine repository root for WASM startup order"))
    (truename (merge-pathnames "../../"
                               (make-pathname :name nil :type nil :defaults script)))))

(defun wasm-level-1-source-path ()
  (merge-pathnames "level-1/level-1.lisp" (wasm-startup-order-root)))

(defun wasm-minimal-target-features ()
  (remove nil
          (list (find-symbol "WASM32-TARGET" "CCL")
                (find-symbol "WASM-TARGET" "CCL"))))

(defun collect-wasm-level-1-module-specs (form)
  (cond
    ((atom form) nil)
    ((eq (car form) 'macrolet)
     (mapcan #'collect-wasm-level-1-module-specs (cddr form)))
    ((eq (car form) 'l1-load)
     (let ((name (cadr form)))
       (unless (stringp name)
         (error "Unexpected l1-load form in level-1.lisp: ~s" form))
       (list (list name "l1-fasls"))))
    ((eq (car form) 'bin-load)
     (let ((name (cadr form)))
       (unless (stringp name)
         (error "Unexpected bin-load form in level-1.lisp: ~s" form))
       (list (list name "bin"))))
    (t nil)))

(defun native-wasm-runtime-startup-module-specs ()
  (let ((path (wasm-level-1-source-path))
        (eof (cons nil nil))
        (specs nil))
    (with-open-file (in path :direction :input)
      (let ((*package* (find-package "CCL"))
            (*features* (wasm-minimal-target-features)))
        (loop for form = (read in nil eof)
              until (eq form eof)
              do (setf specs (nconc specs (collect-wasm-level-1-module-specs form))))))
    specs))

(defun copy-module-specs (specs)
  (mapcar #'copy-list specs))

(defun insert-module-spec-after (specs anchor new-spec)
  (let ((result nil)
        (inserted nil))
    (dolist (spec specs)
      (push spec result)
      (when (string= (first spec) anchor)
        (push (copy-list new-spec) result)
        (setf inserted t)))
    (unless inserted
      (error "Cannot insert ~s after missing startup anchor ~s" new-spec anchor))
    (nreverse result)))

(defun expected-wasm-runtime-startup-module-specs ()
  (let ((specs (copy-module-specs (native-wasm-runtime-startup-module-specs))))
    (dolist (insertion *wasm-runtime-level-1-insertions*)
      (setf specs
            (insert-module-spec-after specs
                                      (first insertion)
                                      (second insertion))))
    (nconc specs (copy-module-specs *wasm-runtime-level-1-tail-specs*))))

(defun wasm-runtime-startup-module-symbols ()
  (mapcar (lambda (spec)
            (intern (string-upcase (first spec)) "CCL"))
          *wasm-runtime-startup-module-specs*))

(defun wasm-runtime-extra-compile-module-symbols ()
  (mapcar (lambda (name)
            (intern (string-upcase name) "CCL"))
          *wasm-runtime-extra-compile-modules*))

(defun validate-wasm-runtime-startup-module-specs ()
  (let ((expected (expected-wasm-runtime-startup-module-specs))
        (actual *wasm-runtime-startup-module-specs*))
    (unless (equal expected actual)
      (error "WASM startup order drifted from level-1.lisp.~%Expected: ~s~%Actual: ~s"
             expected actual))
    (let ((all-names (append (mapcar #'first actual)
                             *wasm-runtime-extra-compile-modules*)))
      (unless (= (length all-names)
                 (length (remove-duplicates all-names :test #'string=)))
        (error "Duplicate entries in WASM runtime module order: ~s" all-names)))
    t))
