;;; Portable reference for a loader-owned resource name. These definitions
;;; are read as private LABELS bodies, not installed in global function cells.
(defun install-kernel-resource (resource)
  (when *kernel-resource-ready*
    (error "KERNEL-RESOURCE-ALREADY-INSTALLED"))
  (unless (and (stringp resource) (plusp (length resource))
               (not (find (code-char 0) resource)))
    (error "INVALID-KERNEL-RESOURCE"))
  (let ((saved (copy-seq resource)))
    (setq *kernel-resource-name* saved)
    (setq *kernel-resource-ready* t)
    (length saved)))

(defun kernel-resource-identity ()
  (unless *kernel-resource-ready*
    (error "KERNEL-RESOURCE-NOT-INSTALLED"))
  (copy-seq *kernel-resource-name*))
