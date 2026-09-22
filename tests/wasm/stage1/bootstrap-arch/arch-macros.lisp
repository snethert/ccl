(cl:in-package :wasm32)

(cl:defconstant single-float.element-count 1)
(cl:defconstant double-float.element-count 3)
(cl:defconstant ratio.numer-cell 0)
(cl:defconstant ratio.denom-cell 1)

(cl:in-package :wasm32-compiler)

(arch::defarchmacro :wasm32 ccl::%make-sfloat ()
  `(ccl::%alloc-misc wasm32::single-float.element-count
                    wasm32::subtag-single-float))

(arch::defarchmacro :wasm32 ccl::%make-dfloat ()
  `(ccl::%alloc-misc wasm32::double-float.element-count
                    wasm32::subtag-double-float))

(arch::defarchmacro :wasm32 ccl::%numerator (x)
  `(ccl::%svref ,x wasm32::ratio.numer-cell))

(arch::defarchmacro :wasm32 ccl::%denominator (x)
  `(ccl::%svref ,x wasm32::ratio.denom-cell))

(arch::defarchmacro :wasm32 ccl::immediate-p-macro (thing)
  (let ((tag (gensym)))
    `(let ((,tag (ccl::lisptag ,thing)))
       (declare (fixnum ,tag))
       (or (= ,tag wasm32::tag-fixnum) (= ,tag wasm32::tag-imm)))))

(arch::defarchmacro :wasm32 ccl::hashed-by-identity (thing)
  (let ((typecode (gensym)))
    `(let ((,typecode (ccl::typecode ,thing)))
       (declare (fixnum ,typecode))
       (or (= ,typecode wasm32::tag-fixnum)
           (= ,typecode wasm32::tag-imm)
           (= ,typecode wasm32::subtag-symbol)
           (= ,typecode wasm32::subtag-instance)))))

;;; Native function vectors interleave code and immediates. Returning the
;;; D1 object here would expose metadata words as native LFUN fields.
(arch::defarchmacro :wasm32 ccl::lfun-vector (function)
  (declare (ignore function))
  (refuse :function-immediate-layout))

(arch::defarchmacro :wasm32 ccl::function-to-function-vector (function)
  (declare (ignore function))
  (refuse :function-immediate-layout))

;;; Native kernel globals have no address in the portable owner. Keep this
;;; an explicit admission refusal until the corresponding owner entry exists.
(arch::defarchmacro :wasm32 ccl::%get-kernel-global (name)
  (declare (ignore name))
  (wasm32-compiler::refuse :kernel-global-capability))

(arch::defarchmacro :wasm32 ccl::%get-kernel-global-ptr (name destination)
  (declare (ignore name destination))
  (wasm32-compiler::refuse :kernel-global-capability))

;;; Keep the native 32-bit macro's binding and initialization order. The
;;; current allocator puts these objects on the moving heap; dynamic extent
;;; remains a lifetime declaration, not a claim of stack allocation.
(defmacro wasm32::with-stack-short-floats (specs &body body)
  (ccl::collect ((binds) (inits) (names))
    (dolist (spec specs)
      (let ((name (first spec)))
        (binds `(,name (ccl::%make-sfloat)))
        (names name)
        (when (second spec)
          (inits `(ccl::%short-float ,(second spec) ,name)))))
    `(let* ,(binds)
       (declare (dynamic-extent ,@(names)) (short-float ,@(names)))
       ,@(inits)
       ,@body)))
