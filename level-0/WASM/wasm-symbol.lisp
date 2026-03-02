;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 symbol operations.
;;; Hash functions MUST match native CCL output exactly, or symbol
;;; lookup silently fails after image save/load.

(in-package "CCL")

;;; CRITICAL: Hash algorithm must match x86-64 LAP exactly.
;;; Algorithm: accum = 0; for each 32-bit word w in str:
;;;   accum = ror32(accum, 27) ^ w
;;; Return bottom 29 bits of accum (= target most-positive-fixnum).
;;;
;;; x86-64 LAP returns the full 32-bit accumulator as a 62-bit fixnum.
;;; ARM LAP returns the bottom 27 bits (32-bit shift drops top 5 bits).
;;; During cross-compilation, mixup-hash-code masks to target fixnum range:
;;;   (logand hash target::target-most-positive-fixnum)
;;; On WASM32, target most-positive-fixnum = #x1FFFFFFF (29 bits).
;;; So we must return 29 bits to match the cross-compiled boot image's
;;; hash tables. 29 bits fits exactly in a WASM32 fixnum.
;;;
;;; ror32(x, 27) = (x >> 27) | ((x & 0x7FFFFFF) << 5)
;;; All arithmetic is 32-bit unsigned.

(defun %pname-hash (str len)
  (declare (fixnum len)
           (optimize (speed 3) (safety 0)))
  (if (eql len 0)
    0
    ;; Split 32-bit accumulator into hi16/lo16 halves to avoid bignums.
    ;; WASM32 fixnums are 30 bits; 32-bit intermediates would overflow.
    ;; Algorithm: accum = ror32(accum, 27) ^ char_code per character.
    (let ((hi 0) (lo 0))
      (declare (fixnum hi lo))
      (dotimes (i len)
        (let* ((w (char-code (uvref str i)))
               ;; ror32(hi:lo, 27) = (accum >> 27) | ((accum << 5) & 0xFFFFFFFF)
               (rot-lo (logior (logand (ash lo 5) #xFFFF)
                               (ash hi -11)))
               (rot-hi (logior (ash (logand hi #x7FF) 5)
                               (ash lo -11))))
          (setq lo (logxor rot-lo (logand w #xFFFF)))
          (setq hi (logxor rot-hi (logand (ash w -16) #xFFFF)))))
      ;; Bottom 29 bits of accum = lo | (hi & 0x1FFF) << 16
      (logior lo (ash (logand hi #x1FFF) 16)))))

(defun %string-hash (start str len)
  (declare (fixnum start len)
           (optimize (speed 3) (safety 0)))
  (if (eql len 0)
    0
    (let ((hi 0) (lo 0))
      (declare (fixnum hi lo))
      (dotimes (i len)
        (let* ((w (char-code (uvref str (the fixnum (+ start i)))))
               (rot-lo (logior (logand (ash lo 5) #xFFFF)
                               (ash hi -11)))
               (rot-hi (logior (ash (logand hi #x7FF) 5)
                               (ash lo -11))))
          (setq lo (logxor rot-lo (logand w #xFFFF)))
          (setq hi (logxor rot-hi (logand (ash w -16) #xFFFF)))))
      (logior lo (ash (logand hi #x1FFF) 16)))))

;;; On ARM, %function checks the fcell of a symbol and traps if not
;;; a function. The WASM compiler handles this as an intrinsic
;;; (wasm2-%function, line 3223), so this is a dynamic-call fallback.
(defun %function (sym)
  (let* ((symptr (if (null sym)
                   (%symbol->symptr nil)
                   (progn
                     (unless (symbolp sym)
                       (%err-disp $xnotfun sym))
                     sym)))
         (def (%svref symptr target::symbol.fcell-cell)))
    (if (functionp def)
      def
      (%err-disp $xnotfun sym))))

;;; Map NIL to nilsym proxy, pass other symbols through.
;;; Compiler intrinsic (wasm2-%symbol->symptr), this is fallback.
(defun %symbol->symptr (sym)
  (if (null sym)
    (%incf-ptr (%null-ptr) target::nilsym-offset)
    (progn
      (unless (symbolp sym)
        (report-bad-arg sym 'symbol))
      sym)))

;;; Map nilsym back to NIL, pass other symbols through.
(defun %symptr->symbol (symptr)
  (if (eq symptr (%symbol->symptr nil))
    nil
    (progn
      (unless (symbolp symptr)
        (report-bad-arg symptr 'symbol))
      symptr)))

;;; Thread-local value of a symbol. On ARM calls .SPspecref.
;;; On single-threaded WASM, just return the symbol's value cell directly.
;;; Must NOT call symbol-value here — symbol-value calls %sym-value which
;;; calls %symptr-value, creating an infinite recursion.
(defun %symptr-value (symptr)
  (%svref (symptr->symvector symptr) target::symbol.vcell-cell))

(defun %set-symptr-value (symptr val)
  (setf (%svref (symptr->symvector symptr) target::symbol.vcell-cell) val))

;;; Return the binding address for a symbol in the current thread.
;;; On ARM, checks TLB. On WASM single-threaded, return the symbol's
;;; vcell location.
(defun %symptr-binding-address (symptr)
  (values symptr target::symbol.vcell))

;;; Return the TLB location for a symbol in a given TCR.
;;; On WASM single-threaded, return NIL (no per-thread bindings).
(defun %tcr-binding-location (tcr sym)
  (declare (ignore tcr sym))
  nil)

;;; Ensure the TLB has room for binding index IDX.
;;; On WASM single-threaded, return the TLB pointer.
;;; On ARM, traps to grow TLB if needed.
(defun %ensure-tlb-index (idx)
  (declare (ignore idx))
  (%fixnum-ref (%current-tcr) target::tcr.tlb-pointer))

;;; Closure-free binding-index counter.
;;;
;;; l0-symbol.lisp defines %set-binding-index and next-binding-index as
;;; closures over a shared (let* ((next-binding-index 0) ...) ...) block.
;;; On WASM32 the xloader does not populate inner-lambda environment slots,
;;; so the closure environment (function slot 2) remains NIL at Phase D.
;;; Calling %set-binding-index then crashes: _SPmisc_set(NIL, ...) → trap.
;;;
;;; Fix: override both functions with top-level defuns backed by a defvar.
;;; These are compiled into the boot image after l0-symbol.lisp loads,
;;; overwriting the closure fcells whether Phase C succeeded or not.
(defvar *%next-binding-index* 0)

(defun %set-binding-index (val)
  (setq *%next-binding-index* val))

(defun next-binding-index ()
  (1+ *%next-binding-index*))
