(in-package "COMMON-LISP")
(locally
  (declare (special ccl::*loader-package-sequence*))
  (setq ccl::*loader-package-sequence* (list *package*)))
