;;; Fixture class: reader conditionals.

(in-package "CCL")

#+wasm32-target
(defun fixture-reader-conditional-enabled ()
  :enabled)

#-wasm32-target
(defun fixture-reader-conditional-disabled ()
  :disabled)
