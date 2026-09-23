(in-package :wasm32-compiler)

(defun validation-probe-cases ()
  (list (list 'validation-helper '((0) (-5)))
        (list 'validation-file-environment '((0) (-5) (536870910)))
        (list 'validation-condition (list (list 0) (list 7) (list (ash 1 70))))
        (list 'validation-global '((0) (7)) (list (cons '*validation-counter* 11)))))
