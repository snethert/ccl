;;; A separate clean host process reconstructs the producer from its FASL only.
(in-package :ccl)
(in-development-mode
  (load "ccl:lib;systems.lisp")
  (load "ccl:lib;compile-ccl.lisp")
  (dolist (name '("wasm32-arch" "wasm32-backend" "nfcomp" "xfasload" "xwasm32fasload"))
    (load (concatenate 'string "ccl:bin;" name ".dx64fsl"))))
(let ((out (getenv "CROSS_LOAD_OUTPUT")))
  (with-cross-compilation-target (:wasm32)
    (let ((*target-backend* (find-backend :wasm32)))
      (xfasload (concatenate 'string out "producer/")
                (concatenate 'string out "fixture.w32fsl")))))
(format t "CROSS-LOAD-PASS~%")
(quit)
