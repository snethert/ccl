(in-package "CCL")
(ccl::in-development-mode
(dolist (name '(wasm32-arch wasm32-backend xwasm32fasload))
  (multiple-value-bind (binary sources) (find-module name (backend-name *host-backend*))
    (load (compile-file (car sources) :output-file binary))))
)
