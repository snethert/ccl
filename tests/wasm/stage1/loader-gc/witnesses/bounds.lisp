(in-package "CCL")

(defun loader-gc-allocate-hash (cells)
  (%alloc-misc cells target::subtag-hash-vector (%unbound-marker)))
