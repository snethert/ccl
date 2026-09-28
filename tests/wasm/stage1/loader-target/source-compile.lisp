;;; Compile an additional ordinary source file for a pinned post-image fixture.
(in-package "CCL")
(load "ccl:compiler;WASM32;wasm32-bundle.lisp")
(let ((out (getenv "LOADER_OUTPUT"))
      (source "ccl:tests;wasm;stage1;loader-target;benchmark.lisp"))
  (multiple-value-bind (path records warnings modules)
      (wasm32-compiler::wasm32-compile-bundle-records
       source (concatenate 'string out "benchmark.w32fsl")
       (concatenate 'string out "benchmark.records.json"))
    (declare (ignore path records warnings))
    (with-open-file (s (concatenate 'string out "function-names.json")
                       :direction :output :if-exists :supersede)
      (wasm32-compiler::wasm32-bundle-json
       (mapcar (lambda (module)
                 (list :object (cons "wire" (getf module :name))
                       (cons "name" (prin1-to-string (svref (getf module :pool) 5)))))
               modules) s))
    (with-open-file (s (concatenate 'string out "bundles.json")
                       :direction :output :if-exists :supersede)
      (wasm32-compiler::wasm32-bundle-json
       (list :object
             (cons "files"
                   (vector (list :object (cons "source" source)
                                 (cons "stem" "benchmark")
                                 (cons "path" "/ccl/bin/loader-benchmark.w32fsl")
                                 (cons "modules" (length modules)))))
             (cons "compilation_stop" nil)) s)))
  (multiple-value-bind (path warnings failure)
      (compile-file source :output-file (concatenate 'string out "benchmark.dx64fsl"))
    (declare (ignore warnings))
    (assert (and path (not failure)))))
(quit)
