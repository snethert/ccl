(in-package :wasm32-compiler)

(defun validation-probe-cases ()
  (let ((image (cpl-image 'cpl-left)))
    ;; This recipe asks CLASS-OF about its NHASH object. The inherited generic
    ;; fixture leaves ISTRUCT unclassified; provide the native class for this
    ;; deliberately narrow owner graph, rather than pretending it is absent.
    (setf (svref (svref image 0) wasm32::subtag-istruct) (find-class 'hash-table))
    (loop for name in '(validation-class-error validation-class-type-error
                       validation-class-capacity validation-class-allocate)
          collect (list name (list (list image))))))
