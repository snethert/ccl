(in-package :wasm32-compiler)
(defun b-poll ()
  (let ((*b-tail-position* nil)
        (level (b-special-symbol 'ccl::*interrupt-level*))
        (gc (b-special-symbol 'ccl::%wasm-gc-service%))
        (interrupt (b-special-symbol 'ccl::%wasm-interrupt-service%)))
    (b-wat "(if (i32.and (i32.atomic.load offset=36 (global.get $tcr)) (i32.const 1)) (then ~a))
      (if (i32.ge_s (call $special_read ~a) (i32.const 0)) (then
        (if (i32.and (i32.atomic.rmw.and offset=36 (global.get $tcr) (i32.const -3)) (i32.const 2)) (then ~a)))) ~a"
      (b-discard-handler (b-wat "(call $special_read ~a)" gc) nil nil t) level
      (b-discard-handler (b-wat "(call $special_read ~a)" interrupt) nil nil t)
      (b-multiple (make-b-raw-code :text "(i32.const 77825)")))))
