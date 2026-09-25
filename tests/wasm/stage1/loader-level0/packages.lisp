;;; These observers call the original package functions compiled above.
(defvar *loader-package-sequence* nil)

(defun loader-eql (x y) (eql x y))

(defun loader-eql-immediates ()
  (let ((cell (cons 1 nil)) (box "same"))
    (values (loader-eql 7 7) (loader-eql 7 -7)
            (loader-eql #\A #\A) (loader-eql #\A #\B)
            (loader-eql #\A 65) (loader-eql nil nil)
            (loader-eql cell cell) (loader-eql cell (cons 1 nil))
            (loader-eql box box) (loader-eql box 1) (loader-eql 1 box))))

(defun loader-eql-evaluation ()
  (let ((n 0))
    (values (eql (incf n) (incf n)) n)))

(defun loader-boxed-eql ()
  ;; The full numeric EQL entry remains an explicit dependency of this
  ;; incomplete image. Bind its reporting context so the refusal is primary.
  (let ((%handlers% nil)) (loader-eql "first" "second")))

(defun loader-package-sequence ()
  (values (package-name (car *loader-package-sequence*))
          (package-name (cadr *loader-package-sequence*))))

(defun loader-package-cl ()
  (set-package "CL")
  (values (package-name *package*) (eq *package* (find-package "COMMON-LISP"))))

(defun loader-package-keyword ()
  (set-package :keyword)
  (values (package-name *package*) (eq *package* (find-package "KEYWORD"))))

(defun loader-package-object ()
  (set-package (find-package "CCL"))
  (values (package-name *package*) (eq *package* (find-package "CCL"))))

(defun loader-package-missing ()
  (values (find-package "LOADER-NONEXISTENT-PACKAGE") (package-name *package*)))

(defun loader-package-bound ()
  (values (let ((*package* (find-package "KEYWORD")))
            (set-package "CL")
            (package-name *package*))
          (package-name *package*)))
