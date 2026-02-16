;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 symbol operations.
;;; Hash functions MUST match native CCL output exactly, or symbol
;;; lookup silently fails after image save/load.

(in-package "CCL")

;;; CRITICAL: Hash algorithm must match ARM LAP exactly.
;;; Algorithm: accum = 0; for each 32-bit word w in str:
;;;   accum = ror32(accum, 27) ^ w
;;; return (accum << 5) >>> (5 - fixnumshift) as fixnum
;;;
;;; ror32(x, 27) = (x >> 27) | ((x & 0x7FFFFFF) << 5)
;;; All arithmetic is 32-bit unsigned.

(defun %pname-hash (str len)
  (declare (fixnum len)
           (optimize (speed 3) (safety 0)))
  (if (eql len 0)
    0
    (let ((accum 0))
      (dotimes (i len)
        (let* ((w (uvref str i))
               (rotated (logand #xFFFFFFFF
                          (logior (ash accum -27)
                                  (ash (logand accum #x7FFFFFF) 5)))))
          (setq accum (logand #xFFFFFFFF (logxor rotated w)))))
      ;; (accum << 5) then unsigned >> (5 - fixnumshift)
      ;; fixnumshift = 2, so >> 3
      (ash (logand #xFFFFFFFF (ash accum 5)) -3))))

(defun %string-hash (start str len)
  (declare (fixnum start len)
           (optimize (speed 3) (safety 0)))
  (if (eql len 0)
    0
    (let ((accum 0))
      (dotimes (i len)
        (let* ((w (uvref str (the fixnum (+ start i))))
               (rotated (logand #xFFFFFFFF
                          (logior (ash accum -27)
                                  (ash (logand accum #x7FFFFFF) 5)))))
          (setq accum (logand #xFFFFFFFF (logxor rotated w)))))
      (ash (logand #xFFFFFFFF (ash accum 5)) -3))))

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
;;; On single-threaded WASM, just return the symbol's value cell.
(defun %symptr-value (symptr)
  (symbol-value (%symptr->symbol symptr)))

(defun %set-symptr-value (symptr val)
  (set (%symptr->symbol symptr) val))

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
