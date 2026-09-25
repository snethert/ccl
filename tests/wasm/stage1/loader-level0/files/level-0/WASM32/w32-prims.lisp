;;; -*- Mode: Lisp; Package: CCL; -*-
;;; Wasm entry points for primitives open-coded by its pass 2.
;;; Like the native LAP entries, these remain callable through function cells.
(in-package "CCL")

(defun lisptag (object)
  (lisptag object))

(defun fulltag (object)
  (fulltag object))

(defun typecode (object)
  (typecode object))

(defun %slot-ref (instance index)
  (%slot-ref instance index))

;;; The native targets implement this entry in LAP.
(defun assq (item alist)
  (dolist (pair alist)
    (when (and pair (eq item (car pair)))
      (return pair))))

;;; Half-digit arithmetic keeps every temporary inside the target fixnum range.
(defun %bignum-ref (bignum index)
  (values (%wasm-bignum-half-ref bignum index t)
          (%wasm-bignum-half-ref bignum index nil)))

(defun %bignum-ref-hi (bignum index)
  (%wasm-bignum-half-ref bignum index t))

(defun %bignum-set (bignum index high low)
  (%wasm-bignum-set bignum index high low))

(defun %bignum-sign (bignum)
  (if (logbitp 15 (%bignum-ref-hi bignum (1- (uvsize bignum)))) -1 0))

(defun bignum-minusp (bignum)
  (< (%bignum-sign bignum) 0))

(defun bignum-plusp (bignum)
  (not (< (%bignum-sign bignum) 0)))

(defun %bignum-oddp (bignum)
  (logbitp 0 (%wasm-bignum-half-ref bignum 0 nil)))

(defun %digit-0-or-plusp (bignum index)
  (not (logbitp 15 (%bignum-ref-hi bignum index))))

(defun %digits-sign-bits (high low)
  (when (logbitp 15 high)
    (setq high (logxor high #xffff) low (logxor low #xffff)))
  (if (zerop high)
    (- 32 (integer-length low))
    (- 16 (integer-length high))))

(defun %bignum-sign-bits (bignum)
  (multiple-value-bind (high low) (%bignum-ref bignum (1- (uvsize bignum)))
    (%digits-sign-bits high low)))

(defun %wasm-bignum-operand (object index)
  (if index
    (%bignum-ref object index)
    (values (logand (ash object -16) #xffff) (logand object #xffff))))

(defun %add-with-carry (result k carry a i b j)
  (multiple-value-bind (ah al) (%wasm-bignum-operand a i)
    (multiple-value-bind (bh bl) (%wasm-bignum-operand b j)
      (let* ((low (+ al bl carry))
             (high (+ ah bh (ash low -16))))
        (%bignum-set result k (logand high #xffff) (logand low #xffff))
        (ash high -16)))))

;;; As on x8632, one means no borrow; zero means an incoming borrow.
(defun %subtract-with-borrow (result k borrow a i b j)
  (multiple-value-bind (ah al) (%wasm-bignum-operand a i)
    (multiple-value-bind (bh bl) (%wasm-bignum-operand b j)
      (multiple-value-bind (high low next) (%subtract-with-borrow-1 ah al bh bl borrow)
        (%bignum-set result k high low)
        next))))

(defun %subtract-with-borrow-1 (ah al bh bl borrow)
  (let* ((low (+ (- al bl) borrow -1))
         (high (+ (- ah bh) (ash low -16))))
    (values (logand high #xffff) (logand low #xffff) (if (< high 0) 0 1))))

(defun %subtract-one (high low)
  (let* ((low (1- low)) (high (+ high (ash low -16))))
    (values (logand high #xffff) (logand low #xffff))))

(defun %add-the-carry (high low carry)
  (let* ((low (+ low carry))
         (high (logand (+ high (ash low -16)) #xffff)))
    ;; The native entry returns its high half sign-extended.
    (values (if (logbitp 15 high) (- high #x10000) high) (logand low #xffff))))

(defun %compare-digits (a b index)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (cond ((> ah bh) 1) ((< ah bh) -1)
            ((> al bl) 1) ((< al bl) -1) (t 0)))))

(defun %normalize-bignum-2 (return-fixnum-p bignum)
  (let ((length (uvsize bignum)))
    (loop while (> length 1) do
      (multiple-value-bind (high low) (%bignum-ref bignum (1- length))
        (let ((sign (if (logbitp 15 (%bignum-ref-hi bignum (- length 2))) #xffff 0)))
          (unless (and (= high sign) (= low sign)) (return))
          (decf length))))
    (%wasm-bignum-length-set bignum length)
    (if (and return-fixnum-p (= length 1))
      (multiple-value-bind (high low) (%bignum-ref bignum 0)
        (if (or (< high #x2000) (>= high #xe000))
          (%ilogior2 (%ilsl 16 high) low)
          bignum))
      bignum)))

(defun %bignum-lognot (index source destination)
  (multiple-value-bind (high low) (%bignum-ref source index)
    (%bignum-set destination index (logxor high #xffff) (logxor low #xffff))))

(defun %bignum-count-trailing-zero-bits (bignum)
  (let ((zeros 0))
    (dotimes (i (uvsize bignum) zeros)
      (multiple-value-bind (high low) (%bignum-ref bignum i)
        (dolist (half (list low high))
          (if (zerop half)
            (incf zeros 16)
            (progn
              (loop until (logbitp 0 half) do (incf zeros) (setq half (ash half -1)))
              (return-from %bignum-count-trailing-zero-bits zeros))))))))

(defun %bignum-logand (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand ah bh)
                                      (logand al bl)))))

(defun %bignum-logior (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logior ah bh)
                                      (logior al bl)))))

(defun %bignum-logxor (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logxor ah bh)
                                      (logxor al bl)))))

(defun %bignum-logandc1 (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand (logxor ah #xffff) bh)
                                      (logand (logxor al #xffff) bl)))))

(defun %bignum-logandc2 (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand ah (logxor bh #xffff))
                                      (logand al (logxor bl #xffff))))))

(defun %fixnum-to-bignum-set (bignum fixnum)
  (%bignum-set bignum 0 (ash fixnum -16) fixnum)
  fixnum)

(defun bignum-negate-loop-really (bignum length result)
  (let ((carry 1))
    (dotimes (i length carry)
      (multiple-value-bind (high low) (%bignum-ref bignum i)
        (let* ((low (+ (logxor low #xffff) carry))
               (high (+ (logxor high #xffff) (ash low -16))))
          (%bignum-set result i high low)
          (setq carry (ash high -16)))))))

(defun %wasm-half-logcount (half)
  (let ((count 0))
    (loop until (zerop half) do
      (incf count)
      (setq half (logand half (1- half))))
    count))

(defun %logcount (bignum index)
  (multiple-value-bind (high low) (%bignum-ref bignum index)
    (+ (%wasm-half-logcount high) (%wasm-half-logcount low))))

(defun %logcount-complement (bignum index)
  (- 32 (%logcount bignum index)))

(defun %wasm-bignum-half-at (bignum index)
  (cond ((< index 0) 0)
        ((>= index (* 2 (uvsize bignum)))
         (if (bignum-minusp bignum) #xffff 0))
        (t (%wasm-bignum-half-ref bignum (ash index -1) (oddp index)))))

(defun %wasm-bignum-shift-half (bignum index bits leftp)
  (declare (fixnum index bits))
  (multiple-value-bind (words shift) (truncate bits 16)
    (let* ((index (if leftp (- index words) (+ index words)))
           (half (%wasm-bignum-half-at bignum index)))
      (if (zerop shift)
        half
        (logand #xffff
                (if leftp
                  (%ilogior2 (%ilsl shift half)
                             (%ilsr (- 16 shift) (%wasm-bignum-half-at bignum (1- index))))
                  (%ilogior2 (%ilsr shift half)
                             (%ilsl (- 16 shift) (%wasm-bignum-half-at bignum (1+ index))))))))))

(defun bignum-shift-left-loop (nbits result bignum res-len-1 j)
  (let ((digits (1- j)))
    (do ((i digits (1+ i))) ((> i res-len-1) res-len-1)
      (let ((half (* 2 (- i digits))))
        (%bignum-set result i
                     (%wasm-bignum-shift-half bignum (1+ half) nbits t)
                     (%wasm-bignum-shift-half bignum half nbits t))))))

(defun bignum-shift-right-loop-1 (nbits result bignum res-len-1 start)
  (dotimes (i (1+ res-len-1) (+ start res-len-1))
    (let ((half (* 2 (+ start i))))
      (%bignum-set result i
                   (%wasm-bignum-shift-half bignum (1+ half) nbits nil)
                   (%wasm-bignum-shift-half bignum half nbits nil)))))

;;; Dcode is an ordinary callable object in D1. The trampoline uses the
;;; current function's traced immediate vector, just as the native LAP entry.
(defun funcallable-trampoline (&rest args)
  (apply (gf.dcode (%wasm-current-function)) args))

;;; NX1 puts the method context first in the method's lambda-list IR. D1
;;; carries that word in the ordinary rooted argument frame instead of a
;;; native register or an untraced TCR spill slot.
(defun %apply-with-method-context (context function args)
  (apply function context args))

(defun %apply-lexpr-with-method-context (context function args)
  (%apply-lexpr function context args))

(defun %apply-lexpr-tail-wise (function args)
  (%apply-lexpr function args))

;;; Products of eight-bit pieces keep intermediate arithmetic in fixnums.
(defun %wasm-multiply-halves (a b)
  (let* ((al (logand a #xff)) (ah (ash a -8))
         (bl (logand b #xff)) (bh (ash b -8))
         (low (* al bl))
         (middle (+ (* ah bl) (* al bh) (ash low -8))))
    (values (+ (* ah bh) (ash middle -8))
            (logior (ash (logand middle #xff) 8) (logand low #xff)))))

(defun %multiply-and-add-1 (xh xl yh yl ch cl)
  (multiple-value-bind (hh hl) (%wasm-multiply-halves xh yh)
    (multiple-value-bind (mh ml) (%wasm-multiply-halves xh yl)
      (multiple-value-bind (nh nl) (%wasm-multiply-halves xl yh)
        (multiple-value-bind (lh ll) (%wasm-multiply-halves xl yl)
          (let* ((low (+ ll cl))
                 (middle (+ lh ml nl ch (ash low -16)))
                 (high (+ mh nh hl (ash middle -16))))
            (values (+ hh (ash high -16)) (logand high #xffff)
                    (logand middle #xffff) (logand low #xffff))))))))

(defun %multiply-and-add-fixnum-loop (length x y result)
  (multiple-value-bind (yh yl)
      (if (fixnump y)
        (values (logand (ash y -16) #xffff) (logand y #xffff))
        (%bignum-ref y 0))
    (let ((ch 0) (cl 0))
      (dotimes (i length)
        (multiple-value-bind (xh xl) (%bignum-ref x i)
          (multiple-value-bind (high low rh rl) (%multiply-and-add-1 xh xl yh yl ch cl)
            (%bignum-set result i rh rl)
            (setq ch high cl low))))
      (%bignum-set result length ch cl)
      result)))

(defun %multiply-and-add-harder-loop-2 (x y result i ylen)
  (multiple-value-bind (xh xl) (%bignum-ref x i)
    (let ((ch 0) (cl 0))
      (dotimes (j ylen)
        (multiple-value-bind (yh yl) (%bignum-ref y j)
          (multiple-value-bind (high low rh rl) (%multiply-and-add-1 xh xl yh yl ch cl)
            (multiple-value-bind (oldh oldl) (%bignum-ref result (+ i j))
              (let* ((lo (+ rl oldl))
                     (hi (+ rh oldh (ash lo -16)))
                     (carry (+ low (ash hi -16))))
                (%bignum-set result (+ i j) hi lo)
                (setq ch (+ high (ash carry -16)) cl (logand carry #xffff)))))))
      (%bignum-set result (+ i ylen) ch cl)
      0)))

;;; The unsigned digit operations keep each half in a fixnum.
(defun %wasm-digit-less-p (ah al bh bl)
  (or (< ah bh) (and (= ah bh) (< al bl))))

(defun %wasm-divide-digit (rh rl nh nl dh dl)
  (when (or (and (zerop dh) (zerop dl))
            (not (%wasm-digit-less-p rh rl dh dl)))
    (error "Invalid digit division."))
  (let ((qh 0) (ql 0))
    (dotimes (i 32)
      (let* ((bit (if (< i 16) (if (logbitp (- 15 i) nh) 1 0)
                       (if (logbitp (- 31 i) nl) 1 0)))
             (low (+ (ash rl 1) bit)))
        (setq rh (+ (ash rh 1) (ash low -16))
              rl (logand low #xffff)
              qh (logior (ash qh 1) (ash ql -15))
              ql (logand (ash ql 1) #xffff))
        (unless (%wasm-digit-less-p rh rl dh dl)
          (let ((low (- rl dl)))
            (setq rh (+ (- rh dh) (ash low -16))
                  rl (logand low #xffff)
                  ql (logior ql 1))))))
    (values qh ql rh rl)))

(defun %floor-loop-quo (x result dh dl)
  (let ((rh 0) (rl 0))
    (do ((i (1- (uvsize x)) (1- i)))
        ((< i 0) (values rh rl))
      (multiple-value-bind (nh nl) (%bignum-ref x i)
        (multiple-value-bind (qh ql high low)
            (%wasm-divide-digit rh rl nh nl dh dl)
          (%bignum-set result i qh ql)
          (setq rh high rl low))))))

(defun %floor-loop-no-quo (x dh dl)
  (let ((rh 0) (rl 0))
    (do ((i (1- (uvsize x)) (1- i)))
        ((< i 0) (values rh rl))
      (multiple-value-bind (nh nl) (%bignum-ref x i)
        (multiple-value-bind (qh ql high low)
            (%wasm-divide-digit rh rl nh nl dh dl)
          (declare (ignore qh ql))
          (setq rh high rl low))))))

(defun %floor-99 (x xidx y yidx)
  (multiple-value-bind (rh rl) (%bignum-ref x xidx)
    (multiple-value-bind (dh dl) (%bignum-ref y yidx)
      (if (and (= rh dh) (= rl dl))
        (values #xffff #xffff)
        (multiple-value-bind (nh nl) (%bignum-ref x (1- xidx))
          (multiple-value-bind (qh ql) (%wasm-divide-digit rh rl nh nl dh dl)
            (values qh ql)))))))

(defun truncate-guess-loop (gh gl x xidx y yidx)
  (loop
    (multiple-value-bind (yh yl) (%bignum-ref y yidx)
      (multiple-value-bind (ah al bh bl) (%multiply-and-add-1 gh gl yh yl 0 0)
        (multiple-value-bind (xh xl) (%bignum-ref x (1- xidx))
          (multiple-value-bind (mh ml borrow) (%subtract-with-borrow-1 xh xl bh bl 1)
            (multiple-value-bind (xh xl) (%bignum-ref x xidx)
              (multiple-value-bind (hh hl) (%subtract-with-borrow-1 xh xl ah al borrow)
                (unless (and (zerop hh) (zerop hl))
                  (return (values gh gl)))
                (multiple-value-bind (yh yl) (%bignum-ref y (1- yidx))
                  (multiple-value-bind (ph pl qh ql) (%multiply-and-add-1 gh gl yh yl 0 0)
                    (multiple-value-bind (xh xl) (%bignum-ref x (- xidx 2))
                      (unless (or (%wasm-digit-less-p mh ml ph pl)
                                  (and (= mh ph) (= ml pl)
                                       (%wasm-digit-less-p xh xl qh ql)))
                        (return (values gh gl))))))))))))
    (multiple-value-setq (gh gl) (%subtract-one gh gl))))

(defun %fixnum-gcd (a b)
  (declare (fixnum a b))
  (loop until (zerop b) do
    (multiple-value-bind (quotient remainder) (truncate a b)
      (declare (ignore quotient))
      (setq a b b remainder)))
  a)

(defun bignum-add-loop-+ (index a b length)
  (let ((carry 0))
    (dotimes (j length)
      (setq carry (%add-with-carry a index carry a index b j))
      (incf index))
    (%add-with-carry a index carry a index 0 nil))
  0)

(in-package "CCL")

;;; The portable definition is the same one used by x8632-array.lisp.
(defun %init-misc (val uvector)
  (dotimes (i (uvsize uvector) uvector)
    (setf (uvref uvector i) val)))

;;; Numeric dispatch uses canonical numeric type names. Other type specifiers
;;; still need the full type system and must not be silently accepted here.
(defun %wasm-numeric-type-p (value typespec)
  (case typespec
    (number (typep value 'number))
    (real (typep value 'real))
    (rational (typep value 'rational))
    (integer (typep value 'integer))
    (fixnum (typep value 'fixnum))
    (bignum (typep value 'bignum))
    (ratio (typep value 'ratio))
    (float (typep value 'float))
    ((short-float single-float) (typep value 'single-float))
    ((long-float double-float) (typep value 'double-float))
    (complex (typep value 'complex))
    (t (error "This numeric restart type is not supported."))))

(defun %wasm-require-numeric-type (value typespec)
  (loop
    (when (%wasm-numeric-type-p value typespec)
      (return value))
    (setq value (%wasm-numeric-type-restart value typespec))))

(defun %wasm-numeric-type-restart (value typespec)
  (restart-case (error 'type-error :datum value :expected-type typespec)
    (use-value (newval)
      (%wasm-require-numeric-type newval typespec))))

(defun %wasm-kernel-restart (error-type args)
  (dolist (entry *kernel-restarts*)
    (when (eq (car entry) error-type)
      ;; There is no native machine frame pointer on this target.
      (return-from %wasm-kernel-restart (apply (cdr entry) nil args))))
  (if (and (eql error-type $xwrongtype) (= (length args) 2))
    (%wasm-numeric-type-restart (car args) (cadr args))
    (error "This kernel restart is not supported.")))

;;; $XTMINPS in l0-error.lisp. Preserve the native condition and its payload.
(defun %wasm-too-many-arguments ()
  (error "Too many arguments."))

(in-package :ccl)

;;; Lisp counterpart of x8632's CLASS-OF LAP entry. The image supplies the
;;; same typecode-indexed class table, containing classes or discriminator
;;; functions. No host class or host typecode participates in target lookup.
(defun class-of (object)
  (let ((entry (%svref *class-table*
                       (if (characterp object) target::subtag-character (typecode object)))))
    (cond ((null entry) (no-class-error object))
          ((functionp entry) (funcall entry object))
          (t entry))))

(defun %class-of-instance (instance)
  (%wrapper-class (instance.class-wrapper instance)))

(defun %wasm-class-of-list (object)
  (if object *cons-class* *null-class*))

(defun macptrp (object)
  (= (typecode object) target::subtag-macptr))

;;; EQL-SPECIALIZER's standard reader. Its OBJECT slot follows DIRECT-METHODS;
;;; the native class-slot inventory qualifies this index with the image.
(defun %wasm-eql-specializer-reader (&method context specializer)
  (declare (ignore context))
  (%slot-ref (instance-slots specializer) 2))

;;; Unlike the native assembly dcode, D1's entry is an ordinary closure.
;;; Applicability and combination are still the original Lisp algorithms.
;;; Recomputing from the current method list also avoids a stale dcode after
;;; removing the final method. A cache can be added without changing this ABI.
(defun %wasm-standard-generic-call (gf args)
  (let* ((bits (inner-lfun-bits gf))
         (required (ldb $lfbits-numreq bits))
         (optional (ldb $lfbits-numopt bits))
         (count (length args)))
    (when (< count required) (signal-program-error "Too few args to ~s" gf))
    (unless (or (<= count (+ required optional))
                (logbitp $lfbits-rest-bit bits)
                (logbitp $lfbits-restv-bit bits)
                (logbitp $lfbits-keys-bit bits))
      (signal-program-error "Too many args to ~s" gf))
    (let* ((methods (%compute-applicable-methods* gf args))
           (combination (%gf-method-combination gf)))
      (unless methods
        (return-from %wasm-standard-generic-call (apply #'no-applicable-method gf args)))
      (unless (eq combination *standard-method-combination*)
        (return-from %wasm-standard-generic-call
          (apply (compute-effective-method-function gf combination methods) args)))
      (let* ((keywords (compute-allowable-keywords-vector gf methods))
             (method-list (compute-method-list methods)))
        (unless method-list
          (return-from %wasm-standard-generic-call (no-applicable-primary-method gf methods)))
        (when (atom method-list) (setq method-list (list method-list)))
        (let* ((key-index (+ required optional))
               (key-info (when keywords (vector key-index keywords gf)))
               (context (vector gf methods key-info
                                (when keywords #'x-%%check-keywords) method-list))
               (combined (lambda (&rest args)
                           (%%cnm-with-args-combined-method-dcode context args))))
          (if keywords
            (%%check-keywords (vector key-index keywords combined gf) args)
            (apply combined args)))))))

(defun compute-dcode (gf &optional dt)
  (setq dt (or dt (%gf-dispatch-table gf)))
  (clear-gf-dispatch-table dt)
  (setf (%gf-dispatch-table-argnum dt) -1)
  (setf (gf.dcode gf)
        (lambda (&rest args) (%wasm-standard-generic-call gf args))))

;;; The native EQUAL entry is LAP. Retain its Lisp calls for recursive conses
;;; and non-EQL uvectors; EQL remains the shared numeric identity operation.
(defun equal (x y)
  (cond ((eq x y) t)
        ((consp x) (and (consp y) (cons-equal x y)))
        ((and (miscobjp x) (miscobjp y))
         (or (eql x y) (hairy-equal x y)))))

(defun false (&rest args)
  (declare (ignore args))
  nil)

(in-package :ccl)

;;; The condition protocol uses the same classes as ordinary instances.
;;; SUBTYPEP's condition-designator case needs no representation-specific
;;; ancestry word: both names and class objects resolve to the real CPL.
(defun %wasm-condition-subtypep (name)
  (let ((class (if (classp name) name (find-class name))))
    (values (not (null (memq (find-class 'condition)
                            (%inited-class-cpl class))))
            t)))

(defun %wasm-signal (datum &rest arguments)
  (declare (dynamic-extent arguments))
  (%wasm-signal-condition (condition-arg datum arguments 'simple-condition)))

(defun %wasm-error (datum &rest arguments)
  (declare (dynamic-extent arguments))
  (%wasm-error-condition (condition-arg datum arguments 'simple-error)))

(in-package :ccl)

(defun %wasm-class-writeable (table)
  (unless (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (error "The bootstrap class table must be an EQ hash table."))
  (when (nhash.read-only table)
    (error "Cannot modify a read-only hash table."))
  table)

(defun %wasm-grow-class-table (table)
  (let* ((old (nhash.vector table))
         (size (nhash.vector.size old)))
    (when (>= size 16384)
      (error "The bootstrap class table has reached its capacity limit."))
    (let ((new (%alloc-misc (+ 14 (* 4 size)) target::subtag-hash-vector)))
      (dotimes (i size)
        (let* ((index (+ 14 (* 2 i)))
               (key (%svref old index)))
          (when (%wasm-eq-hash-key-p key)
            (%wasm-eq-table-set new key (%svref old (1+ index))))))
      ;; OLD remains published until allocation and all stores have succeeded.
      (setf (nhash.vector table) new))))

;;; The class owner uses the same wrapper shape as the admitted image tables.
;;; It is synchronous and strong; no process lock or weak state is installed.
(defun %wasm-make-class-table (size)
  (setq size (require-type size '(integer 0 16384)))
  (let ((capacity 4))
    (loop while (< capacity size) do (setq capacity (* 2 capacity)))
    (%istruct 'hash-table nil 0 nil
              (%alloc-misc (+ 14 (* 2 capacity)) target::subtag-hash-vector)
              nil nil nil nil nil nil nil nil nil nil nil)))

;;; These are checked-boundary reason codes, not condition-class masks.
;;; All objects are made by MAKE-CONDITION from the live class table.
(defun %wasm-implicit-condition (kind datum expected)
  (case kind
    (1 (make-condition 'program-error))
    (8 (make-condition 'control-error))
    (10 (make-condition 'unbound-variable :name datum))
    (14 (make-condition 'undefined-function :name datum))
    (16 (make-condition 'simple-program-error
          :format-control "Checked Lisp runtime operation failed."
          :format-arguments nil))
    (17 (make-condition 'simple-error
          :format-control "Checked Lisp runtime operation failed."
          :format-arguments nil))
    ((18 19 20) (make-condition 'storage-condition))
    ((34 35 36 37 38)
     (make-condition (case kind
                       (34 'division-by-zero)
                       (35 'floating-point-invalid-operation)
                       (36 'floating-point-overflow)
                       (37 'floating-point-underflow)
                       (38 'floating-point-inexact))
                     :operation datum :operands expected))
    (t (make-condition 'type-error :datum datum :expected-type expected))))


;;; A D1 closure stores its compiled entry and callable metadata in the same
;;; function object as its environment. There is no native closure wrapper
;;; to unwrap; LFUN-BITS and LFUN-VECTOR-NAME address that object's metadata.
(defun closure-function (function)
  function)

(in-package :ccl)

;;; Return bytes after the D1 header, including the alignment word of double
;;; and complex float vectors, but excluding trailing allocation padding.
(defun subtag-bytes (subtag element-count)
  (unless (and (integerp element-count) (>= element-count 0))
    (error "Invalid vector element count: ~s" element-count))
  (case subtag
    ((#.target::subtag-u8-vector #.target::subtag-s8-vector) element-count)
    ((#.target::subtag-u16-vector #.target::subtag-s16-vector) (* element-count 2))
    ((#.target::subtag-single-float-vector #.target::subtag-u32-vector
      #.target::subtag-s32-vector #.target::subtag-fixnum-vector
      #.target::subtag-simple-base-string) (* element-count 4))
    ((#.target::subtag-double-float-vector #.target::subtag-complex-single-float-vector)
     (+ 4 (* element-count 8)))
    (#.target::subtag-complex-double-float-vector (+ 4 (* element-count 16)))
    (#.target::subtag-bit-vector (ash (+ element-count 7) -3))
    (t (error "Not an ivector subtag: ~s" subtag))))

;;; Inverse of the Wasm array-element representation chosen by
;;; ELEMENT-TYPE-SUBTYPE. All thirteen specialized vector tags are covered.
(defun element-subtype-type (subtype)
  (case subtype
    (#.target::subtag-simple-vector t)
    (#.target::subtag-single-float-vector 'single-float)
    (#.target::subtag-u32-vector '(unsigned-byte 32))
    (#.target::subtag-s32-vector '(signed-byte 32))
    (#.target::subtag-fixnum-vector 'fixnum)
    (#.target::subtag-simple-base-string 'base-char)
    (#.target::subtag-u8-vector '(unsigned-byte 8))
    (#.target::subtag-s8-vector '(signed-byte 8))
    (#.target::subtag-u16-vector '(unsigned-byte 16))
    (#.target::subtag-s16-vector '(signed-byte 16))
    (#.target::subtag-double-float-vector 'double-float)
    (#.target::subtag-complex-single-float-vector '(complex single-float))
    (#.target::subtag-complex-double-float-vector '(complex double-float))
    (#.target::subtag-bit-vector 'bit)
    (t 'bogus)))

(in-package :ccl)

;;; SXHASH is implementation-dependent. Hash semantic contents without native
;;; addresses, so EQUAL keys retain their hash when the collector moves them.
;;; Opaque objects and non-integral numbers share a bucket; collisions are
;;; resolved by the caller's equality test. Bounded cons descent handles cycles.
(defun %wasm-sxhash (object)
  (labels ((mix (hash value)
             ;; Two 24-bit operands keep the result within a 29-bit fixnum.
             (+ (* 31 (logand hash #xffffff)) (logand value #xffffff)))
           (walk (object depth)
             (cond ((zerop depth) 0)
                   ((integerp object) (logand object target::target-most-positive-fixnum))
                   ((characterp object) (char-code object))
                   ((symbolp object) (walk (symbol-name object) depth))
                   ((stringp object)
                    (let ((hash 17))
                      (dotimes (i (length object) hash)
                        (setq hash (mix hash (char-code (aref object i)))))))
                   ((typep object 'bit-vector)
                    (let ((hash 19))
                      (dotimes (i (length object) hash)
                        (setq hash (mix hash (aref object i))))))
                   ((consp object)
                    (mix (walk (car object) (1- depth))
                         (walk (cdr object) (1- depth))))
                   (t 23))))
    (walk object 7)))

;;; Existing generated callers enter these representation-boundary functions
;;; directly. Keep their strong EQ leaf and dispatch other admitted tests to
;;; the traced pair representation below.
(defun %wasm-class-gethash (key table &optional default)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-eq-table-get (nhash.vector table) key default)
    (%wasm-gethash key table default)))

(defun %wasm-class-puthash (key table default &optional (value default))
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn
      (%wasm-class-writeable table)
      (let ((vector (nhash.vector table)))
        (when (= (nhash.vector.count vector) (nhash.vector.size vector))
          (unless (nth-value 1 (%wasm-eq-table-get vector key nil))
            (%wasm-grow-class-table table))))
      (%wasm-eq-table-set (nhash.vector table) key value))
    (%wasm-puthash key table value)))

(defun %wasm-class-remhash (key table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn (%wasm-class-writeable table)
           (%wasm-eq-table-remove (nhash.vector table) key nil))
    (%wasm-remhash key table)))

(defun %wasm-class-clrhash (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn
      (%wasm-class-writeable table)
      (setf (nhash.vector table)
            (%alloc-misc (+ 14 (* 2 (nhash.vector.size (nhash.vector table))))
                         target::subtag-hash-vector))
      table)
    (%wasm-clrhash table)))

;;; Strong, synchronous tables used while the target initializes its type
;;; environment. EQ retains the collector's existing address-hash leaf.
;;; Other tests keep traced key/value pairs: collection cannot invalidate an
;;; index computed from an object's address. These tables need no native lock.
(defun %wasm-make-hash-table (&key (test 'eql) (size 60)
                                 (rehash-size 1.5) (rehash-threshold .85)
                                 hash-function weak finalizeable
                                 (address-based t) lock-free shared)
  (declare (ignore address-based lock-free shared))
  (unless (and (integerp size) (>= size 0))
    (error "Invalid hash table size: ~s" size))
  (unless (or (and (integerp rehash-size) (> rehash-size 0))
              (and (floatp rehash-size) (> rehash-size 1)))
    (error "Invalid hash table rehash size: ~s" rehash-size))
  (unless (and (realp rehash-threshold) (<= 0 rehash-threshold 1))
    (error "Invalid hash table rehash threshold: ~s" rehash-threshold))
  (when (or hash-function weak finalizeable)
    (error "This target does not support custom hash functions or weak tables."))
  (let ((name (cond ((or (eq test 'eq) (eq test #'eq)) 'eq)
                    ((or (eq test 'eql) (eq test #'eql)) 'eql)
                    ((or (eq test 'equal) (eq test #'equal)) 'equal)
                    ((or (eq test 'equalp) (eq test #'equalp)) 'equalp)
                    (t (error "Invalid hash table test: ~s" test)))))
    (if (eq name 'eq)
      (%wasm-make-class-table (min size 16384))
      (%istruct 'hash-table nil name nil (vector nil 0 size rehash-size rehash-threshold)
                nil nil nil nil nil nil nil nil nil nil nil))))

(defun %wasm-table-pairs (table)
  (unless (and (hash-table-p table) (memq (nhash.comparef table) '(eql equal equalp)))
    (error "Invalid target hash table: ~s" table))
  (nhash.vector table))

(defun %wasm-gethash (key table &optional default)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-gethash key table default)
    (let ((pair (assoc key (svref (%wasm-table-pairs table) 0) :test (nhash.comparef table))))
      (if pair (values (cdr pair) t) (values default nil)))))

(defun %wasm-puthash (key table default &optional (value default))
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-puthash key table value)
    (let* ((state (%wasm-table-pairs table))
           (pair (assoc key (svref state 0) :test (nhash.comparef table))))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (if pair
        (setf (cdr pair) value)
        (progn
          (push (cons key value) (svref state 0))
          (incf (svref state 1))))
      value)))

(defun %wasm-remhash (key table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-remhash key table)
    (let* ((state (%wasm-table-pairs table))
           (pair (assoc key (svref state 0) :test (nhash.comparef table))))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (when pair
        (setf (svref state 0) (delq pair (svref state 0)))
        (decf (svref state 1)))
      (not (null pair)))))

(defun %wasm-clrhash (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-clrhash table)
    (let ((state (%wasm-table-pairs table)))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (setf (svref state 0) nil (svref state 1) 0)
      table)))

(defun %wasm-hash-table-count (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (nhash.vector.count (nhash.vector table))
    (svref (%wasm-table-pairs table) 1)))

(defun %wasm-maphash (function table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (let* ((vector (nhash.vector table)) (size (nhash.vector.size vector)))
      (dotimes (i size)
        (let* ((index (+ 14 (* 2 i))) (key (%svref vector index)))
          (when (%wasm-eq-hash-key-p key)
            (funcall function key (%svref vector (1+ index)))))))
    (dolist (pair (svref (%wasm-table-pairs table) 0))
      (funcall function (car pair) (cdr pair))))
  nil)

(in-package :ccl)

;;; The linker resolves package literals by name in its admitted package set.
;;; No native package object or native address enters a target constant pool.
(defvar *wasm-package-literals* nil)

(defun %wasm-package-literal (name)
  (or (cdr (assoc (string name) *wasm-package-literals* :test #'string=))
      (error "Package is absent from the linked symbol set: ~s" name)))

(defun %wasm-intern (name &optional (package *package*))
  (check-type name string)
  (unless (packagep package)
    (setq package (%wasm-package-literal (string package))))
  (%wasm-symbol-intern (ensure-simple-string name) package nil))

(defun %wasm-find-symbol (name &optional (package *package*))
  (check-type name string)
  (unless (packagep package)
    (setq package (%wasm-package-literal (string package))))
  (%wasm-symbol-find (ensure-simple-string name) package nil))
