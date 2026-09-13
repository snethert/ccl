;;; Read evaluated native tables after a clean or observed image startup.
(in-package :cl-user)
(defun boot-native-snapshot ()
  (with-open-file (s (ccl:getenv "CCL_BOOT_SNAPSHOT_OUTPUT") :direction :output
                     :if-exists :error :external-format :utf-8)
    (ccl-startup-census::json (ccl-startup-census::snapshot) s)
    (terpri s))
  (format t "BOOT-SNAPSHOT-COMPLETE~%"))
