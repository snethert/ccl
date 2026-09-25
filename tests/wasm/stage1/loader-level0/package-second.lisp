(cl:in-package "KEYWORD")
(cl:locally
  (cl:declare (cl:special ccl::*loader-package-sequence*))
  (cl:setq ccl::*loader-package-sequence*
           (cl:cons cl:*package* ccl::*loader-package-sequence*)))
(cl:in-package "CCL")
