;;; Explicit target replacement for the pinned U1 KERNEL-PATH body.
;;; Read through the census front end; never LOAD this into native CCL.
(defun kernel-path ()
  (wasm-census-services::kernel-resource-identity))
