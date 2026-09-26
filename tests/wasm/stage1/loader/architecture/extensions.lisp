
(cl:in-package :wasm32)
(cl:defconstant subtag-function 42)

(cl:in-package :wasm32)

(arch::defarchmacro :wasm32 ccl::symptr->symvector (s)
  s)

(arch::defarchmacro :wasm32 ccl::symvector->symptr (s)
  s)

(cl:in-package :ccl)

(defun wasm32-array-type-name-from-ctype (ctype)
  (when (typep ctype 'ccl::array-ctype)
    (let* ((element-type (ccl::array-ctype-element-type ctype)))
      (typecase element-type
        (ccl::class-ctype
         (let* ((class (ccl::class-ctype-class element-type)))
           (if (or (eq class ccl::*character-class*)
                   (eq class ccl::*base-char-class*)
                   (eq class ccl::*standard-char-class*))
             :simple-string
             :simple-vector)))
        (ccl::numeric-ctype
         (if (eq (ccl::numeric-ctype-complexp element-type) :complex)
           (case (ccl::numeric-ctype-format element-type)
             (single-float :complex-single-float-vector)
             (double-float :complex-double-float-vector)
             (t :simple-vector))
           (case (ccl::numeric-ctype-class element-type)
             (integer
              (let* ((low (ccl::numeric-ctype-low element-type))
                     (high (ccl::numeric-ctype-high element-type)))
                (cond ((or (null low) (null high)) :simple-vector)
                      ((and (>= low 0) (<= high 1) :bit-vector))
                      ((and (>= low 0) (<= high 255)) :unsigned-8-bit-vector)
                      ((and (>= low 0) (<= high 65535)) :unsigned-16-bit-vector)
                      ((and (>= low 0) (<= high #xffffffff) :unsigned-32-bit-vector))
                      ((and (>= low -128) (<= high 127)) :signed-8-bit-vector)
                      ((and (>= low -32768) (<= high 32767) :signed-16-bit-vector))
                      ((and (>= low wasm32::target-most-negative-fixnum)
                            (<= high wasm32::target-most-positive-fixnum))
                       :fixnum-vector)
                      ((and (>= low (ash -1 31)) (<= high (1- (ash 1 31))))
                       :signed-32-bit-vector)
                      (t :simple-vector))))
             (float
              (case (ccl::numeric-ctype-format element-type)
                ((double-float long-float) :double-float-vector)
                ((single-float short-float) :single-float-vector)
                (t :simple-vector)))
             (t :simple-vector))))
        (ccl::unknown-ctype)
        (ccl::named-ctype
         (if (eq element-type ccl::*universal-type*)
           :simple-vector))
        (t nil)))))

(setf (arch::target-array-type-name-from-ctype-function wasm32::*target-arch*)
      #'wasm32-array-type-name-from-ctype)

(cl:in-package :wasm32)

;;; DEFINE-FIXEDSIZED-OBJECT publishes these indices on the native targets.
;;; D1's raw offsets already include the header; node access starts after it.
(cl:defconstant symbol.pname-cell 0)
(cl:defconstant symbol.vcell-cell 1)
(cl:defconstant symbol.fcell-cell 2)
(cl:defconstant symbol.package-predicate-cell 3)
(cl:defconstant symbol.flags-cell 4)
(cl:defconstant symbol.plist-cell 5)
(cl:defconstant symbol.binding-index-cell 6)
(cl:defconstant symbol.element-count 7)

;;; D1 node indices match the 32-bit CCL object definitions in x8632-arch.lisp.
;;; Describing a lock does not implement its kernel operations.
(cl:in-package :wasm32)
(cl:defconstant subtag-lock 66)
(cl:defconstant lock._value-cell 0)
(cl:defconstant lock.kind-cell 1)
(cl:defconstant lock.writer-cell 2)
(cl:defconstant lock.name-cell 3)
(cl:defconstant lock.whostate-cell 4)
(cl:defconstant lock.whostate-2-cell 5)
(cl:defconstant vectorH.logsize-cell 0)
(cl:defconstant vectorH.physsize-cell 1)
(cl:defconstant vectorH.data-vector-cell 2)
(cl:defconstant vectorH.displacement-cell 3)
(cl:defconstant vectorH.flags-cell 4)
(cl:defconstant arrayH.rank-cell 0)
(cl:defconstant arrayH.physsize-cell 1)
(cl:defconstant arrayH.data-vector-cell 2)
(cl:defconstant arrayH.displacement-cell 3)
(cl:defconstant arrayH.flags-cell 4)
(cl:defconstant arrayH.dim0-cell 5)
(cl:defconstant arrayH.flags-cell-subtag-byte (cl:byte 8 8))

;;; Target provider protocol; not native OS constants or implemented capabilities.
(cl:defconstant io-seek-set 0)
(cl:defconstant io-seek-cur 1)
(cl:defconstant os-seek-end 2)
(cl:defconstant os-eperm 1)
(cl:defconstant os-enoent 2)
(cl:defconstant os-esrch 3)
(cl:defconstant io-error-interrupted 4)
(cl:defconstant io-error-file-exists 17)
(cl:defconstant io-error-system-file-limit 23)
(cl:defconstant io-error-process-file-limit 24)
(cl:defconstant os-eisdir 21)
(cl:defconstant os-erange 34)
(cl:defconstant os-etimedout 110)
(cl:defconstant os-o-rdonly 0)
(cl:defconstant os-o-wronly 1)
(cl:defconstant os-o-rdwr 2)
(cl:defconstant os-o-creat 64)
(cl:defconstant os-o-excl 128)
(cl:defconstant os-o-trunc 512)
(cl:defconstant os-o-nonblock 2048)
(cl:defconstant os-path-max 4096)
(cl:defconstant os-s-ifmt 61440)
(cl:defconstant os-s-ififo 4096)
(cl:defconstant os-s-ifchr 8192)
(cl:defconstant os-s-ifdir 16384)
(cl:defconstant os-s-ifreg 32768)
(cl:defconstant os-s-iflnk 40960)
(cl:defconstant os-s-ifsock 49152)
(cl:defconstant os-ex-usage 64)
(cl:defconstant os-ex-software 70)
(cl:defconstant os-ex-oserr 71)

(cl:defpackage "WASM32-COMPILER" (:use "CL"))
(cl:in-package "WASM32-COMPILER")
;;; The native function's interleaved code/immediates are not the Wasm D1
;;; function object. Funcallable instances hold their seven Lisp immediates
;;; in a separate traced vector; ordinary functions expose no native literals.
(arch::defarchmacro :wasm32 ccl::nth-immediate (function index)
  `(ccl::%wasm-function-immediate ,function ,index))

(arch::defarchmacro :wasm32 ccl::set-nth-immediate (function index value)
  `(ccl::%wasm-set-function-immediate ,function ,index ,value))

(cl:in-package :wasm32)

(cl:defconstant single-float.element-count 1)
(cl:defconstant double-float.element-count 3)
(cl:defconstant ratio.element-count 2)
(cl:defconstant ratio.numer-cell 0)
(cl:defconstant ratio.denom-cell 1)
(cl:defconstant complex.realpart-cell 0)
(cl:defconstant complex.imagpart-cell 1)

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

;;; Collector-owner successful-copy count; raw, never scanned.
(cl:defconstant wasm32::tcr.gc_count 204)
