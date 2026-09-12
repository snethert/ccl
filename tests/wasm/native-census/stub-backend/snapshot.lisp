(in-package "CCL-STARTUP-CENSUS")
(with-open-file (s (ccl:getenv "CCL_CENSUS_REPORT") :direction :output :if-exists :error)
  (json (object "snapshot" (snapshot)
                "modules" (loop for entry in ccl::*ccl-system* collect
                            (object "name" (label-of (car entry)) "binary" (label-of (cadr entry))
                                    "sources" (mapcar #'label-of (caddr entry))))) s)
  (terpri s))
(format t "CENSUS-SNAPSHOT-COMPLETE~%")
(ccl:quit)
