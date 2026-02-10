;;;-*- Mode: Lisp; Package: (WASM :use CL) -*-
;;;
;;; WASM32 target arch description.

(defpackage "WASM"
  (:use "CL")
  #+wasm-target
  (:nicknames "TARGET"))

(in-package "WASM")

(eval-when (:compile-toplevel :load-toplevel :execute)
  ;; Transitional bootstrap: keep legacy constant surface available while
  ;; wasm-owned constants/mappings are landed.
  (require (coerce '(#\A #\R #\M #\- #\A #\R #\C #\H) 'string)))

(eval-when (:compile-toplevel :load-toplevel :execute)
  ;; Transitional constant/macro surface for shared compiler forms.
  (let ((arm (find-package "ARM"))
        (wasm (find-package "WASM")))
    (when (and arm wasm)
      (do-symbols (sym arm)
        (when (eq (symbol-package sym) arm)
          (shadowing-import sym wasm))))))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (defparameter *wasm-subprims-shift* 0)
  (defparameter *wasm-subprims-base* 0))

(defconstant +wasm-subprims-count+ 132)

(defparameter *wasm-subprim-names*
  '(
    .SPfix-nfn-entrypoint
    .SPbuiltin-plus
    .SPbuiltin-minus
    .SPbuiltin-times
    .SPbuiltin-div
    .SPbuiltin-eq
    .SPbuiltin-ne
    .SPbuiltin-gt
    .SPbuiltin-ge
    .SPbuiltin-lt
    .SPbuiltin-le
    .SPbuiltin-eql
    .SPbuiltin-length
    .SPbuiltin-seqtype
    .SPbuiltin-assq
    .SPbuiltin-memq
    .SPbuiltin-logbitp
    .SPbuiltin-logior
    .SPbuiltin-logand
    .SPbuiltin-ash
    .SPbuiltin-negate
    .SPbuiltin-logxor
    .SPbuiltin-aref1
    .SPbuiltin-aset1
    .SPfuncall
    .SPmkcatch1v
    .SPmkcatchmv
    .SPmkunwind
    .SPbind
    .SPconslist
    .SPconslist-star
    .SPmakes32
    .SPmakeu32
    .SPfix-overflow
    .SPmakeu64
    .SPmakes64
    .SPmvpass
    .SPvalues
    .SPnvalret
    .SPthrow
    .SPnthrowvalues
    .SPnthrow1value
    .SPbind-self
    .SPbind-nil
    .SPbind-self-boundp-check
    .SPrplaca
    .SPrplacd
    .SPgvset
    .SPset-hash-key
    .SPstore-node-conditional
    .SPset-hash-key-conditional
    .SPstkconslist
    .SPstkconslist-star
    .SPmkstackv
    .SPsetqsym
    .SPprogvsave
    .SPstack-misc-alloc
    .SPgvector
    .SPfitvals
    .SPnthvalue
    .SPdefault-optional-args
    .SPopt-supplied-p
    .SPheap-rest-arg
    .SPreq-heap-rest-arg
    .SPheap-cons-rest-arg
    .SPcheck-fpu-exception
    .SPdiscard-stack-object
    .SPksignalerr
    .SPstack-rest-arg
    .SPreq-stack-rest-arg
    .SPstack-cons-rest-arg
    .SPcall-closure
    .SPspreadargz
    .SPtfuncallgen
    .SPtfuncallslide
    .SPjmpsym
    .SPtcallsymgen
    .SPtcallsymslide
    .SPtcallnfngen
    .SPtcallnfnslide
    .SPmisc-ref
    .SPsubtag-misc-ref
    .SPmakestackblock
    .SPmakestackblock0
    .SPmakestacklist
    .SPstkgvector
    .SPmisc-alloc
    .SPatomic-incf-node
    .SPunused1
    .SPunused2
    .SPrecover-values
    .SPinteger-sign
    .SPsubtag-misc-set
    .SPmisc-set
    .SPspread-lexprz
    .SPreset
    .SPmvslide
    .SPsave-values
    .SPadd-values
    .SPmisc-alloc-init
    .SPstack-misc-alloc-init
    .SPpopj
    .SPudiv64by32
    .SPgetu64
    .SPgets64
    .SPspecref
    .SPspecrefcheck
    .SPspecset
    .SPgets32
    .SPgetu32
    .SPmvpasssym
    .SPunbind
    .SPunbind-n
    .SPunbind-to
    .SPprogvrestore
    .SPbind-interrupt-level-0
    .SPbind-interrupt-level-m1
    .SPbind-interrupt-level
    .SPunbind-interrupt-level
    .SParef2
    .SParef3
    .SPaset2
    .SPaset3
    .SPkeyword-bind
    .SPudiv32
    .SPsdiv32
    .SPeabi-ff-call-simple
    .SPdebind
    .SPeabi-callback
    .SPeabi-ff-callhf
    .SPwasm-macro-apply-stub
    .SPwasm-udf-stub
    ))

(defvar *wasm-subprims* #())

(defun wasm-build-subprims-table (&optional (names *wasm-subprim-names*))
  (let* ((count (length names))
         (table (make-array count)))
    (dotimes (i count table)
      (let* ((name (nth i names)))
        (setf (aref table i)
              (ccl::make-subprimitive-info :name (string name) :offset i))))))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (unless (= (length *wasm-subprim-names*) +wasm-subprims-count+)
    (error "WASM subprim table size mismatch: expected ~d, got ~d"
           +wasm-subprims-count+
           (length *wasm-subprim-names*)))
  (setf *wasm-subprims* (wasm-build-subprims-table)))

(defun wasm-fpr-mask (value mode)
  (ecase (ccl::fpr-mode-value-name mode)
    (:single-float (ash 1 value))
    ((:double-float :complex-single-float) (ash 3 (ash value 1)))
    (:complex-double-float (ash 15 (ash value 2)))))

(defparameter *wasm-target-uvector-subtags*
  `((:bignum . ,subtag-bignum)
    (:ratio . ,subtag-ratio)
    (:single-float . ,subtag-single-float)
    (:double-float . ,subtag-double-float)
    (:complex . ,subtag-complex)
    (:complex-single-float . ,subtag-complex-single-float)
    (:complex-double-float . ,subtag-complex-double-float)
    (:symbol . ,subtag-symbol)
    (:function . ,subtag-function)
    (:code-vector . ,subtag-code-vector)
    (:xcode-vector . ,subtag-xcode-vector)
    (:macptr . ,subtag-macptr)
    (:catch-frame . ,subtag-catch-frame)
    (:struct . ,subtag-struct)
    (:istruct . ,subtag-istruct)
    (:pool . ,subtag-pool)
    (:population . ,subtag-weak)
    (:hash-vector . ,subtag-hash-vector)
    (:package . ,subtag-package)
    (:value-cell . ,subtag-value-cell)
    (:instance . ,subtag-instance)
    (:lock . ,subtag-lock)
    (:slot-vector . ,subtag-slot-vector)
    (:basic-stream . ,subtag-basic-stream)
    (:simple-string . ,subtag-simple-base-string)
    (:bit-vector . ,subtag-bit-vector)
    (:signed-8-bit-vector . ,subtag-s8-vector)
    (:unsigned-8-bit-vector . ,subtag-u8-vector)
    (:signed-16-bit-vector . ,subtag-s16-vector)
    (:unsigned-16-bit-vector . ,subtag-u16-vector)
    (:signed-32-bit-vector . ,subtag-s32-vector)
    (:fixnum-vector . ,subtag-fixnum-vector)
    (:unsigned-32-bit-vector . ,subtag-u32-vector)
    (:single-float-vector . ,subtag-single-float-vector)
    (:double-float-vector . ,subtag-double-float-vector)
    (:complex-single-float-vector . ,subtag-complex-single-float-vector)
    (:complex-double-float-vector . ,subtag-complex-double-float-vector)
    (:simple-vector . ,subtag-simple-vector)
    (:vector-header . ,subtag-vectorH)
    (:array-header . ,subtag-arrayH)
    (:xfunction . ,subtag-xfunction)
    (:pseudofunction . ,subtag-pseudofunction)
    (:min-cl-ivector-subtag . ,min-cl-ivector-subtag)))

(defun wasm-array-type-name-from-ctype (ctype)
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
                      ((and (>= low target-most-negative-fixnum)
                            (<= high target-most-positive-fixnum))
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

(defun wasm-misc-byte-count (subtag element-count)
  (declare (fixnum subtag))
  (if (or (= fulltag-nodeheader (logand subtag fulltagmask))
          (<= subtag max-32-bit-ivector-subtag))
    (ash element-count 2)
    (if (<= subtag max-8-bit-ivector-subtag)
      element-count
      (if (<= subtag max-16-bit-ivector-subtag)
        (ash element-count 1)
        (if (= subtag subtag-bit-vector)
          (ash (+ element-count 7) -3)
          (if (= subtag subtag-complex-double-float-vector)
            (+ 4 (ash element-count 4))
            (+ 4 (ash element-count 3))))))))

(defparameter *wasm32-target-arch*
  (arch::make-target-arch
   :name :wasm32
   :lisp-node-size 4
   :nil-value canonical-nil-value
   :fixnum-shift fixnumshift
   :most-positive-fixnum target-most-positive-fixnum
   :most-negative-fixnum target-most-negative-fixnum
   :misc-data-offset misc-data-offset
   :misc-dfloat-offset misc-dfloat-offset
   :nbits-in-word 32
   :ntagbits ntagbits
   :nlisptagbits nlisptagbits
   :uvector-subtags *wasm-target-uvector-subtags*
   :max-64-bit-constant-index max-64-bit-constant-index
   :max-32-bit-constant-index max-32-bit-constant-index
   :max-16-bit-constant-index max-16-bit-constant-index
   :max-8-bit-constant-index max-8-bit-constant-index
   :max-1-bit-constant-index max-1-bit-constant-index
   :word-shift word-shift
   :code-vector-prefix ()
   :gvector-types '(:ratio :complex :symbol :function
                    :catch-frame :struct :istruct
                    :pool :population :hash-vector
                    :package :value-cell :instance
                    :lock :slot-vector
                    :simple-vector :xfunction
                    :pseudofunction)
   :1-bit-ivector-types '(:bit-vector)
   :8-bit-ivector-types '(:signed-8-bit-vector
                          :unsigned-8-bit-vector)
   :16-bit-ivector-types '(:signed-16-bit-vector
                           :unsigned-16-bit-vector)
   :32-bit-ivector-types '(:signed-32-bit-vector
                           :unsigned-32-bit-vector
                           :single-float-vector
                           :fixnum-vector
                           :single-float
                           :double-float
                           :bignum
                           :simple-string)
   :64-bit-ivector-types '(:double-float-vector :complex-single-float-vector)
   :array-type-name-from-ctype-function #'wasm-array-type-name-from-ctype
   :package-name "WASM"
   :t-offset t-offset
   :array-data-size-function #'wasm-misc-byte-count
   :fpr-mask-function 'wasm-fpr-mask
   :subprims-base *wasm-subprims-base*
   :subprims-shift *wasm-subprims-shift*
   :subprims-table *wasm-subprims*
   :primitive->subprims `(((0 . 23) . ,(ccl::%subprim-name->offset '.SPbuiltin-plus *wasm-subprims*)))
   :unbound-marker-value unbound-marker
   :slot-unbound-marker-value slot-unbound-marker
   :fixnum-tag tag-fixnum
   :single-float-tag subtag-single-float
   :single-float-tag-is-subtag t
   :double-float-tag subtag-double-float
   :cons-tag fulltag-cons
   :null-tag fulltag-nil
   :symbol-tag subtag-symbol
   :symbol-tag-is-subtag t
   :function-tag subtag-function
   :function-tag-is-subtag t
   :big-endian nil
   :misc-subtag-offset misc-subtag-offset
   :car-offset cons.car
   :cdr-offset cons.cdr
   :subtag-char subtag-character
   :charcode-shift charcode-shift
   :fulltagmask fulltagmask
   :fulltag-misc fulltag-misc
   :char-code-limit #x110000))

(defmacro defwasmarchmacro (name lambda-list &body body)
  `(arch::defarchmacro :wasm32 ,name ,lambda-list ,@body))

(defwasmarchmacro ccl::%make-sfloat ()
  `(ccl::%alloc-misc wasm::single-float.element-count wasm::subtag-single-float))

(defwasmarchmacro ccl::%make-dfloat ()
  `(ccl::%alloc-misc wasm::double-float.element-count wasm::subtag-double-float))

(defwasmarchmacro ccl::%numerator (x)
  `(ccl::%svref ,x wasm::ratio.numer-cell))

(defwasmarchmacro ccl::%denominator (x)
  `(ccl::%svref ,x wasm::ratio.denom-cell))

(defwasmarchmacro ccl::%get-kernel-global (name)
  `(ccl::%fixnum-ref (ash (+ (- wasm::nil-value wasm::fulltag-nil)
                             ,(wasm::%kernel-global
                               (if (ccl::quoted-form-p name)
                                 (cadr name)
                                 name)))
                      (- wasm::fixnumshift))))

(defwasmarchmacro ccl::%get-kernel-global-ptr (name dest)
  `(ccl::%setf-macptr
    ,dest
    (ccl::%fixnum-ref-macptr (ash (+ (- wasm::nil-value wasm::fulltag-nil)
                                     ,(wasm::%kernel-global
                                       (if (ccl::quoted-form-p name)
                                         (cadr name)
                                         name)))
                              (- wasm::fixnumshift)))))

(defwasmarchmacro ccl::%target-kernel-global (name)
  `(wasm::%kernel-global ,name))

(defwasmarchmacro ccl::lfun-vector (fun)
  fun)

(defwasmarchmacro ccl::lfun-vector-lfun (lfv)
  lfv)

(defwasmarchmacro ccl::area-code ()
  area.code)

(defwasmarchmacro ccl::area-succ ()
  area.succ)

(defwasmarchmacro ccl::symptr->symvector (s)
  s)

(defwasmarchmacro ccl::symvector->symptr (s)
  s)

(defwasmarchmacro ccl::function-to-function-vector (f)
  f)

(defwasmarchmacro ccl::function-vector-to-function (v)
  v)

(defwasmarchmacro ccl::with-ffcall-results ((buf) &body body)
  (let* ((size (+ (* 8 4) (* 31 8))))
    `(%stack-block ((,buf ,size))
      ,@body)))

;; Transitional helper used by shared macros.
(defwasmarchmacro ccl::%get-single-float-from-double-ptr (ptr offset)
  `(ccl::%double-float->short-float (ccl::%get-double-float ,ptr ,offset)
    (ccl::%alloc-misc 1 wasm::subtag-single-float)))

(defwasmarchmacro ccl::codevec-header-p (word)
  `(eql wasm::subtag-code-vector
    (logand ,word wasm::subtag-mask)))

(defwasmarchmacro ccl::immediate-p-macro (thing)
  (let* ((tag (gensym)))
    `(let* ((,tag (ccl::lisptag ,thing)))
      (declare (fixnum ,tag))
      (or (= ,tag wasm::tag-fixnum)
       (= ,tag wasm::tag-imm)))))

(defwasmarchmacro ccl::hashed-by-identity (thing)
  (let* ((typecode (gensym)))
    `(let* ((,typecode (ccl::typecode ,thing)))
      (declare (fixnum ,typecode))
      (or
       (= ,typecode wasm::tag-fixnum)
       (= ,typecode wasm::tag-imm)
       (= ,typecode wasm::subtag-symbol)
       (= ,typecode wasm::subtag-instance)))))

;; Mirror function-vector immediate indexing used by shared macros.
(defwasmarchmacro ccl::nth-immediate (f i)
  `(ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))))

(defwasmarchmacro ccl::set-nth-immediate (f i new)
  `(setf (ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))) ,new))

(provide "WASM-ARCH")
