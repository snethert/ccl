;;; Fixture class: unsupported reader dispatch.

(in-package "CCL")

#~(unsupported-reader-dispatch)

(defun fixture-after-dispatch-error ()
  :unreachable)
