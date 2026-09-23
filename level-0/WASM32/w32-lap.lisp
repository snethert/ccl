;;; -*- Mode: Lisp; Package: CCL; -*-
;;;
;;; Target definitions of native LAP entries.
;;;
;;; The native targets define these functions in LAP (level-0/X86/X8632 is
;;; the 32-bit reference).  On this target they are ordinary Lisp definitions
;;; over the same tagged objects, written so that every intermediate stays a
;;; fixnum or a declared 32-bit word.  Each definition names the native entry
;;; it replaces.  They are callable through their function cells exactly as
;;; the LAP entries are.
;;;
;;; The backend lowers LOGAND, LOGIOR and LOGXOR as word operations only
;;; when both operands are word-sized constants or forms declared
;;; (UNSIGNED-BYTE 32); its generic path does not take a bignum operand.
;;; Every word expression below is therefore written two operands at a time
;;; with THE on each.
;;;
;;; Definitions that read or write the raw words of a float object use two
;;; target primitives, %WASM-FLOAT-WORD and %WASM-SET-FLOAT-WORD, which the
;;; backend must lower (see the "Float words" section).  Definitions that
;;; need bignum digit access use %BIGNUM-REF and %BIGNUM-SET from the pending
;;; numeric-dispatch proposal and are grouped at the end.

(in-package "CCL")

;;;; Fixnum arithmetic (x8632-numbers.lisp)
;;;
;;; %ILOGCOUNT is lowered by the backend and needs no definition here.

;;; Number of significant bits in the absolute value of a fixnum: the
;;; position of the highest bit that differs from the sign bit, plus one.
(defun %fixnum-intlen (number)
  (declare (fixnum number))
  (let ((bits (if (< number 0) (%ilognot number) number))
        (length 0))
    (declare (fixnum bits length))
    (loop
      (when (zerop bits) (return length))
      (setq bits (%ilsr 1 bits)
            length (%i+ length 1)))))

;;; Arithmetic shift of a fixnum by a fixnum count.  A left shift wraps in
;;; the fixnum word, as the native entry's SHL does.
(defun %iash (number count)
  (declare (fixnum number count))
  (if (< count 0)
    (%iasr (%i- 0 count) number)
    (%ilsl count number)))

;;; Native LAP divides with IDIV; the target divides in the backend, one
;;; instruction for the quotient and one for the remainder.  The case a
;;; division instruction cannot express is the most negative fixnum divided
;;; by -1, whose quotient is a bignum.
(defun %fixnum-truncate (dividend divisor)
  (declare (fixnum dividend divisor))
  (cond ((eql divisor -1)
         (if (eql dividend most-negative-fixnum)
           (values *least-positive-bignum* 0)
           (values (%i- 0 dividend) 0)))
        ((eql divisor 0)
         (error 'division-by-zero :operation 'truncate
                :operands (list dividend divisor)))
        (t
         (values (%wasm-fixnum-quotient dividend divisor)
                 (%wasm-fixnum-remainder dividend divisor)))))

;;; Unsigned remainder of two non-negative fixnums.  The native entry
;;; divides the boxed words; the reciprocal argument of FAST-MOD-3 is a
;;; multiplication shortcut for the same remainder.
(defun fast-mod (number divisor)
  (declare (fixnum number divisor))
  (nth-value 1 (%fixnum-truncate number divisor)))

(defun fast-mod-3 (number divisor recip)
  (declare (fixnum number divisor) (ignore recip))
  (nth-value 1 (%fixnum-truncate number divisor)))

;;;; Hashing (x8632-hash.lisp, x8632-symbol.lisp)

;;; The native entries rotate a 32-bit accumulator left by five and XOR in
;;; each character code, then return the low 27 bits as a fixnum.  Every
;;; operand of the word operations is a declared (UNSIGNED-BYTE 32) or a
;;; word-sized constant, which is what the backend lowers without calling
;;; generic arithmetic.
(defun %string-hash (start str len)
  (declare (fixnum start len) (simple-string str)
           (optimize (speed 3) (safety 0)))
  (let ((accum 0))
    (declare (type (unsigned-byte 32) accum))
    (dotimes (i len)
      (declare (fixnum i))
      (setq accum (logxor (the (unsigned-byte 32)
                            (logior (the (unsigned-byte 32)
                                      (ash (logand accum #x07ffffff) 5))
                                    (the (unsigned-byte 32) (ash accum -27))))
                          (the (unsigned-byte 32)
                            (%scharcode str (%i+ start i))))))
    (logand accum #x07ffffff)))

(defun %pname-hash (str len)
  (declare (fixnum len) (simple-string str))
  (%string-hash 0 str len))

;;; The native entries fold the raw words of a float into a fixnum.  Any
;;; deterministic fold serves; this one keeps the sum in the fixnum range.
(defun %dfloat-hash (key)
  (declare (double-float key))
  (logand (logxor (the (unsigned-byte 32) (%wasm-float-word key 0))
                  (the (unsigned-byte 32) (%wasm-float-word key 1)))
          most-positive-fixnum))

(defun %sfloat-hash (key)
  (declare (single-float key))
  (logand (the (unsigned-byte 32) (%wasm-float-word key 0))
          most-positive-fixnum))

;;;; Conditional stores (x8632-misc.lisp)

;;; OFFSET is a byte offset from the tagged object, as the native subprims
;;; take it; the node lives in cell (OFFSET - MISC-DATA-OFFSET) / 4.  The
;;; owner runs Lisp on one Worker, so the compare and the store cannot be
;;; interleaved with another mutator; that is what makes these atomic here.
(defun %store-node-conditional (offset object old new)
  (declare (fixnum offset))
  (let ((cell (%ilsr 2 (%i- offset target::misc-data-offset))))
    (declare (fixnum cell))
    (if (eq (%svref object cell) old)
      (progn (setf (%svref object cell) new) t)
      nil)))

(defun %atomic-incf-node (by node disp)
  (declare (fixnum by disp))
  (let ((cell (%ilsr 2 (%i- disp target::misc-data-offset))))
    (declare (fixnum cell))
    (setf (%svref node cell) (%i+ (%svref node cell) by))))

;;;; Vectors (x8632-array.lisp, x8632-misc.lisp)

;;; Follow displaced array headers to the underlying data vector, summing
;;; the displacements on the way.
(defun %array-header-data-and-offset (a)
  (let ((offset 0))
    (declare (fixnum offset))
    (loop
      (let ((typecode (typecode a)))
        (declare (fixnum typecode))
        (unless (or (eql typecode target::subtag-vectorh)
                    (eql typecode target::subtag-arrayh))
          (return (values a offset)))
        (setq offset (%i+ offset (%svref a target::arrayh.displacement-cell))
              a (%svref a target::arrayh.data-vector-cell))))))

(defun %init-gvector (len value vector)
  (declare (fixnum len))
  (dotimes (i len vector)
    (declare (fixnum i))
    (setf (%svref vector i) value)))

;;; Copy NELEMENTS nodes, choosing the direction so that an overlapping
;;; copy within one vector is correct.
(defun %copy-gvector-to-gvector (src src-element dest dest-element nelements)
  (declare (fixnum src-element dest-element nelements))
  (if (and (eq src dest) (< dest-element src-element))
    (dotimes (k nelements)
      (declare (fixnum k))
      (setf (%svref dest (%i+ dest-element k))
            (%svref src (%i+ src-element k))))
    (let ((i (%i+ src-element nelements))
          (j (%i+ dest-element nelements)))
      (declare (fixnum i j))
      (dotimes (k nelements)
        (declare (fixnum k))
        (setq i (%i- i 1) j (%i- j 1))
        (setf (%svref dest j) (%svref src i)))))
  dest)

;;; The native entry allocates the conses in the kernel; consing them here
;;; is the same list.
(defun %allocate-list (initial-element nconses)
  (declare (fixnum nconses))
  (let ((list nil))
    (dotimes (i nconses list)
      (declare (fixnum i))
      (setq list (cons initial-element list)))))

;;;; Functions and symbols (x8632-def.lisp, x8632-symbol.lisp, x8632-utils.lisp)

;;; Native code keeps no register-usage information on this target either.
(defun %function-register-usage (f)
  (unless (functionp f) (report-bad-arg f 'function))
  (values nil nil))

;;; Symbols are their own symbol pointers here, except that NIL's symbol
;;; pointer is a separate address (NILSYM-OFFSET past canonical NIL), which
;;; the native entry also recognizes before its ordinary symbol check.
(defun %symptr->symbol (symptr)
  (cond ((eq symptr (%symbol->symptr nil)) nil)
        ((symbolp symptr) symptr)
        (t (report-bad-arg symptr 'symbol))))

(defun true (&rest ignore)
  (declare (ignore ignore))
  t)

;;;; Slot-id accessors (x8632-clos.lisp)
;;;
;;; The native entries are LAP prototypes that L1-CLOS clones with a class's
;;; map, table and class stored as immediates.  On this target each
;;; prototype is a closure constructor taking the same values; L1-CLOS calls
;;; the constructor where the other targets clone.

(defun %make-small-map-slot-id-lookup (map table)
  (declare (type (simple-array (unsigned-byte 8) (*)) map)
           (simple-vector table))
  (lambda (slot-id)
    (let ((index (slot-id.index slot-id)))
      (declare (fixnum index))
      (%svref table (if (< index (length map)) (aref map index) 0)))))

(defun %make-large-map-slot-id-lookup (map table)
  (declare (type (simple-array (unsigned-byte 32) (*)) map)
           (simple-vector table))
  (lambda (slot-id)
    (let ((index (slot-id.index slot-id)))
      (declare (fixnum index))
      (%svref table (if (< index (length map)) (aref map index) 0)))))

(defun %make-small-slot-id-value (map table class)
  (declare (type (simple-array (unsigned-byte 8) (*)) map)
           (simple-vector table))
  (lambda (instance slot-id)
    (let* ((index (slot-id.index slot-id))
           (offset (if (< index (length map)) (aref map index) 0)))
      (declare (fixnum index offset))
      (if (eql offset 0)
        (%slot-id-ref-missing instance slot-id)
        (%maybe-std-slot-value-using-class class instance (%svref table offset))))))

(defun %make-large-slot-id-value (map table class)
  (declare (type (simple-array (unsigned-byte 32) (*)) map)
           (simple-vector table))
  (lambda (instance slot-id)
    (let* ((index (slot-id.index slot-id))
           (offset (if (< index (length map)) (aref map index) 0)))
      (declare (fixnum index offset))
      (if (eql offset 0)
        (%slot-id-ref-missing instance slot-id)
        (%maybe-std-slot-value-using-class class instance (%svref table offset))))))

(defun %make-small-set-slot-id-value (map table class)
  (declare (type (simple-array (unsigned-byte 8) (*)) map)
           (simple-vector table))
  (lambda (instance slot-id new-value)
    (let* ((index (slot-id.index slot-id))
           (offset (if (< index (length map)) (aref map index) 0)))
      (declare (fixnum index offset))
      (if (eql offset 0)
        (%slot-id-set-missing instance slot-id new-value)
        (%maybe-std-setf-slot-value-using-class
         class instance (%svref table offset) new-value)))))

(defun %make-large-set-slot-id-value (map table class)
  (declare (type (simple-array (unsigned-byte 32) (*)) map)
           (simple-vector table))
  (lambda (instance slot-id new-value)
    (let* ((index (slot-id.index slot-id))
           (offset (if (< index (length map)) (aref map index) 0)))
      (declare (fixnum index offset))
      (if (eql offset 0)
        (%slot-id-set-missing instance slot-id new-value)
        (%maybe-std-setf-slot-value-using-class
         class instance (%svref table offset) new-value)))))

;;;; Float words (x8632-float.lisp)
;;;
;;; (%WASM-FLOAT-WORD float index) reads word INDEX of a float object as an
;;; (UNSIGNED-BYTE 32): a single float has word 0; a double float has its
;;; low word at 0 and its high word at 1.  (%WASM-SET-FLOAT-WORD float
;;; index word) stores one.  Both check the object and the index.

(defun single-float-bits (f)
  (declare (single-float f))
  (%wasm-float-word f 0))

(defun double-float-bits (f)
  (declare (double-float f))
  (values (%wasm-float-word f 1) (%wasm-float-word f 0)))

(defun double-float-from-bits (high low)
  (let ((f (%make-dfloat)))
    (%wasm-set-float-word f 1 high)
    (%wasm-set-float-word f 0 low)
    f))

;;; The sign is the top bit of the high word.  A word above the fixnum
;;; range is boxed, so the bit is read with a shift rather than LOGBITP.
(defun %double-float-sign (n)
  (declare (double-float n))
  (eql 1 (ash (the (unsigned-byte 32) (%wasm-float-word n 1)) -31)))

(defun %short-float-sign (n)
  (declare (single-float n))
  (eql 1 (ash (the (unsigned-byte 32) (%wasm-float-word n 0)) -31)))

;;; The biased exponent occupies the eleven bits below the sign.
(defun %double-float-exp (n)
  (declare (double-float n))
  (logand (1- (ash 1 IEEE-double-float-exponent-width))
          (ash (the (unsigned-byte 32) (%wasm-float-word n 1))
               (- (- IEEE-double-float-exponent-offset 32)))))

(defun set-%double-float-exp (dfloat exp)
  (declare (double-float dfloat) (fixnum exp))
  (%wasm-set-float-word
   dfloat 1
   (logior (the (unsigned-byte 32)
             (logand #x800fffff (the (unsigned-byte 32) (%wasm-float-word dfloat 1))))
           (the (unsigned-byte 32)
             (ash (logand exp (1- (ash 1 IEEE-double-float-exponent-width)))
                  (- IEEE-double-float-exponent-offset 32)))))
  exp)

(defun %short-float-exp (n)
  (declare (single-float n))
  (logand (1- (ash 1 IEEE-single-float-exponent-width))
          (ash (the (unsigned-byte 32) (%wasm-float-word n 0))
               (- IEEE-single-float-exponent-offset))))

(defun set-%short-float-exp (sfloat exp)
  (declare (single-float sfloat) (fixnum exp))
  (%wasm-set-float-word
   sfloat 0
   (logior (the (unsigned-byte 32)
             (logand #x807fffff (the (unsigned-byte 32) (%wasm-float-word sfloat 0))))
           (the (unsigned-byte 32)
             (ash (logand exp (1- (ash 1 IEEE-single-float-exponent-width)))
                  IEEE-single-float-exponent-offset))))
  exp)

;;; Copy N into RESULT and clear or complement the sign bit.
(defun %%double-float-abs! (n result)
  (declare (double-float n result))
  (%wasm-set-float-word result 0 (%wasm-float-word n 0))
  (%wasm-set-float-word result 1
                        (logand #x7fffffff
                                (the (unsigned-byte 32) (%wasm-float-word n 1))))
  result)

(defun %double-float-negate! (src res)
  (declare (double-float src res))
  (%wasm-set-float-word res 0 (%wasm-float-word src 0))
  (%wasm-set-float-word res 1
                        (logxor #x80000000
                                (the (unsigned-byte 32) (%wasm-float-word src 1))))
  res)

;;; Returns four values: HI (the top 25 bits of the fraction with the hidden
;;; bit when the number is normalized), LO (the low 28 bits), the biased
;;; exponent, and the sign as 1 or -1.  The split keeps both halves fixnums.
(defun %integer-decode-double-float (n)
  (declare (double-float n))
  (let* ((high (%wasm-float-word n 1))
         (low (%wasm-float-word n 0))
         (sign (if (eql 1 (ash high -31)) -1 1))
         (exp (logand (1- (ash 1 IEEE-double-float-exponent-width))
                      (ash high (- (- IEEE-double-float-exponent-offset 32)))))
         (hi (logior (the (unsigned-byte 32) (ash (logand high #x000fffff) 4))
                     (the (unsigned-byte 32) (ash low -28))))
         (lo (logand low #x0fffffff)))
    (declare (type (unsigned-byte 32) high low) (fixnum sign exp)
             (type (unsigned-byte 25) hi) (type (unsigned-byte 28) lo))
    (unless (eql exp 0)
      (setq hi (logior (the (unsigned-byte 32) hi)
                       (ash 1 (- IEEE-double-float-hidden-bit 28)))))
    (values hi lo exp sign)))

;;; The inverse of %INTEGER-DECODE-DOUBLE-FLOAT: HI supplies the top 24
;;; fraction bits (its hidden bit is dropped), LO the low 28, EXP the
;;; biased exponent and the sign of SIGN the sign bit.
(defun %make-float-from-fixnums (float hi lo exp sign)
  (declare (double-float float) (fixnum hi lo exp sign))
  (let ((hi (logand hi (1- (ash 1 24)))))
    (declare (type (unsigned-byte 24) hi))
    (%wasm-set-float-word
     float 1
     (logior (the (unsigned-byte 32)
               (logior (the (unsigned-byte 32) (if (< sign 0) #x80000000 0))
                       (the (unsigned-byte 32)
                         (ash (logand exp (1- (ash 1 IEEE-double-float-exponent-width)))
                              (- IEEE-double-float-exponent-offset 32)))))
             (the (unsigned-byte 32) (ash hi -4))))
    (%wasm-set-float-word
     float 0
     (logior (the (unsigned-byte 32) (ash (logand hi #xf) 28))
             (the (unsigned-byte 32) (logand lo (1- (ash 1 28))))))
    float))

;;; SIGNIFICAND supplies the 23 fraction bits, BIASED-EXP the exponent and
;;; the sign of SIGN the sign bit.
(defun %make-short-float-from-fixnums (sfloat significand biased-exp sign)
  (declare (single-float sfloat) (fixnum significand biased-exp sign))
  (%wasm-set-float-word
   sfloat 0
   (logior (the (unsigned-byte 32)
             (logior (the (unsigned-byte 32) (if (< sign 0) #x80000000 0))
                     (the (unsigned-byte 32)
                       (ash (logand biased-exp (1- (ash 1 IEEE-single-float-exponent-width)))
                            IEEE-single-float-exponent-offset))))
           (the (unsigned-byte 32)
             (logand significand (1- (ash 1 IEEE-single-float-hidden-bit))))))
  sfloat)

;;; Multiply DFLOAT by two raised to INT, given as the biased exponent of
;;; the power, storing the product in RESULT.
(defun %%scale-dfloat! (dfloat int result)
  (declare (double-float dfloat result) (fixnum int))
  (let ((scale (double-float-from-bits
                (ash (logand int (1- (ash 1 IEEE-double-float-exponent-width)))
                     (- IEEE-double-float-exponent-offset 32))
                0)))
    (declare (double-float scale))
    (%setf-double-float result (* dfloat scale))))

(defun %short-float->double-float (src result)
  (declare (single-float src) (double-float result))
  (%setf-double-float result (%double-float src)))

;;; Conversion to a fixnum.  The native entries convert with CVTTSD2SI and
;;; CVTSD2SI; the backend converts after checking that the value fits.
(defun %truncate-double-float->fixnum (arg)
  (declare (double-float arg))
  (%wasm-float-to-fixnum arg 0))

(defun %truncate-short-float->fixnum (arg)
  (declare (single-float arg))
  (%wasm-float-to-fixnum arg 0))

(defun %round-nearest-double-float->fixnum (arg)
  (declare (double-float arg))
  (%wasm-float-to-fixnum arg 1))

(defun %round-nearest-short-float->fixnum (arg)
  (declare (single-float arg))
  (%wasm-float-to-fixnum arg 1))

;;; Square roots go through the float service, as the transcendental
;;; entries of L1-NUMBERS do.  A negative argument signals an invalid
;;; operation there.
(defun %double-float-sqrt! (n result)
  (declare (double-float n result))
  (%wasm-float-store result (%wasm-float-transcend 44 n 0)))

(defun %single-float-sqrt! (n result)
  (declare (single-float n result))
  (%wasm-float-store result (%wasm-float-transcend 45 n 0)))

;;;; Hash-table stores (x8632-hash.lisp)
;;;
;;; The native subprims store the key and then record the store for the
;;; ephemeral collector.  This collector has no remembered set, so the
;;; store is the whole operation.

(defun %set-hash-table-vector-key (vector index value)
  (declare (fixnum index))
  (setf (%svref vector index) value))

(defun %set-hash-table-vector-key-conditional (offset vector old new)
  (declare (fixnum offset))
  (%store-node-conditional offset vector old new))

;;;; Tags and calling context (x8632-hash.lisp, x8632-numbers.lisp)

;;; A fixnum is returned as it is; any other object yields its address
;;; bits above the tag as a fixnum.
(defun strip-tag-to-fixnum (x)
  (%wasm-strip-tag x))

;;; The native entry compares the return address with the kernel's
;;; multiple-value return address.  The call protocol here does not tell a
;;; callee how many values its caller wants; answering T makes every caller
;;; compute all of its values, which is always correct.
(defun called-for-mv-p ()
  t)

;;;; Bignum digits (x8632-bignum.lisp)
;;;
;;; These use the half-digit accessors of the numeric-dispatch proposal.

;;; Logical AND of a fixnum with the low digit of BIG, returned as a fixnum
;;; when DEST is NIL, otherwise stored as the low digit of DEST.
(defun fix-digit-logand (fix big dest)
  (declare (fixnum fix))
  (multiple-value-bind (high low) (%bignum-ref big 0)
    (declare (fixnum high low))
    (let ((high (logand high (logand (ash fix -16) #xffff)))
          (low (logand low (logand fix #xffff))))
      (declare (fixnum high low))
      (if (null dest)
        (if (logbitp 15 high)
          (%ilogior2 (%ilsl 16 (logior high #x3fff0000)) low)
          (%ilogior2 (%ilsl 16 high) low))
        (progn (%bignum-set dest 0 high low) dest)))))

;;; The two complementing variants of FIX-DIGIT-LOGAND, and the complement
;;; of one digit moved from SOURCE to DEST.
(defun fix-digit-logandc1 (fix big dest)
  (declare (fixnum fix))
  (fix-digit-logand (%ilognot fix) big dest))

(defun fix-digit-logandc2 (fix big dest)
  (declare (fixnum fix))
  (multiple-value-bind (high low) (%bignum-ref big 0)
    (declare (fixnum high low))
    (let ((high (logand (logxor high #xffff) (logand (ash fix -16) #xffff)))
          (low (logand (logxor low #xffff) (logand fix #xffff))))
      (declare (fixnum high low))
      (if (null dest)
        (if (logbitp 15 high)
          (%ilogior2 (%ilsl 16 (logior high #x3fff0000)) low)
          (%ilogior2 (%ilsl 16 high) low))
        (progn (%bignum-set dest 0 high low) dest)))))

(defun digit-lognot-move (index source dest)
  (declare (fixnum index))
  (%bignum-lognot index source dest))

;;; True when any of the first COUNT digit pairs share a set bit.
(defun bignum-logtest-loop (count s1 s2)
  (declare (fixnum count))
  (dotimes (i count nil)
    (declare (fixnum i))
    (multiple-value-bind (h1 l1) (%bignum-ref s1 i)
      (declare (fixnum h1 l1))
      (multiple-value-bind (h2 l2) (%bignum-ref s2 i)
        (declare (fixnum h2 l2))
        (unless (and (eql 0 (logand h1 h2)) (eql 0 (logand l1 l2)))
          (return t))))))

;;; Rotate-and-combine over the digits, as the native hash does.  The
;;; native entry adds; XOR keeps every step inside one word without a carry.
(defun %bignum-hash (key)
  (let ((hash 0))
    (declare (type (unsigned-byte 32) hash))
    (dotimes (i (uvsize key))
      (declare (fixnum i))
      (multiple-value-bind (high low) (%bignum-ref key i)
        (declare (type (unsigned-byte 16) high low))
        (setq hash (logxor (the (unsigned-byte 32)
                             (logior (the (unsigned-byte 32)
                                       (ash (logand hash #x0007ffff) 13))
                                     (the (unsigned-byte 32) (ash hash -19))))
                           (the (unsigned-byte 32)
                             (logior (the (unsigned-byte 32) (ash high 16))
                                     (the (unsigned-byte 32) low)))))))
    (logand hash most-positive-fixnum)))
