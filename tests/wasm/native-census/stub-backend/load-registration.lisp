(in-package "CCL")
(dolist (name '(wasm-census-arch wasm-census-backend))
  (multiple-value-bind (binary sources) (find-module name (backend-name *host-backend*))
    (load (compile-file (car sources) :output-file binary))))
