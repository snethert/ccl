(in-package :wasm32-compiler)
(load (concatenate 'string (ccl:getenv "NAMESPACE_SOURCE") "../namespace-primitives/json.lisp"))
(load (compile-file "ccl:compiler;WASM32;wasm32-backend.lisp"
                    :output-file (concatenate 'string (ccl:getenv "PROBE_OUTPUT") "backend.dx64fsl")
                    :verbose nil :print nil))
(load (concatenate 'string (ccl:getenv "PROBE_OUTPUT") "whole-file.lisp"))
(setq *core-modules* nil *core-records* nil *core-files* nil
      *validation-wire-prefix* "namespace" *b-cpl-conditions* t *b-allocation-retry* t)
(dolist (path '("ccl:level-0;WASM32;w32-prims.lisp"
                "ccl:level-0;l0-def.lisp" "ccl:level-0;l0-misc.lisp"
                "ccl:level-1;l1-files.lisp" "ccl:level-1;l1-pathnames.lisp"
                "ccl:level-1;l1-streams.lisp" "ccl:level-1;l1-sysio.lisp" "ccl:level-1;l1-io.lisp"
                "ccl:level-1;l1-typesys.lisp" "ccl:level-1;WASM32;w32-files.lisp"))
  (core-compile-file path))
(core-compile-file (concatenate 'string (ccl:getenv "NAMESPACE_SOURCE") "../ready/startup.lisp"))
(ccl:save-application (concatenate 'string (ccl:getenv "PROBE_OUTPUT") "core.image")
                      :purify nil :clear-clos-caches nil)
