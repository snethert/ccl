;;; The native function's interleaved code/immediates are not the Wasm D1
;;; function object. Refuse reflection until its Lisp callers have a target
;;; implementation; do not expose code ids or arity words as native literals.
(arch::defarchmacro :wasm32 ccl::nth-immediate (function index)
  (declare (ignore function index))
  (refuse :function-immediate-layout))

(arch::defarchmacro :wasm32 ccl::set-nth-immediate (function index value)
  (declare (ignore function index value))
  (refuse :function-immediate-layout))
