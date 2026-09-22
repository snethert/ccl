(in-package :wasm32-compiler)
(file-measure (merge-pathnames (ccl:getenv "RECOUNT_FILE") "ccl:")
              (pathname (ccl:getenv "RECOUNT_FILE_OUTPUT")))
(ccl:quit)
