;;; The native targets implement this entry in LAP.
(defun assq (item alist)
  (dolist (pair alist)
    (when (and pair (eq item (car pair)))
      (return pair))))
