;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 hash operations.
;;; On ARM these are LAP functions; on WASM they are pure Lisp.
;;; Hash algorithms MUST match the native CCL output exactly.

(in-package "CCL")

(eval-when (:compile-toplevel :execute)
  (require "HASHENV" "ccl:xdump;hashenv"))


;;; Equivalent to cl:mod when both args are positive fixnums.
(defun fast-mod (number divisor)
  (mod number divisor))

;;; Faster mod using reciprocal multiplication.
;;; On WASM, just fall back to simple mod.
(defun fast-mod-3 (number divisor recip)
  (declare (ignore recip))
  (mod number divisor))

;;; Hash a double-float.
;;; Double-float layout on WASM32: (header pad val-low val-high).
;;; XOR the high and low 32-bit words of the value, masked to fixnum.
(defun %dfloat-hash (key)
  (let* ((lo (uvref key target::double-float.val-low-cell))
         (hi (uvref key target::double-float.val-high-cell)))
    (logand (logxor lo hi)
            (lognot target::fixnummask))))

;;; Hash a single-float.
;;; Single-float layout on WASM32: (header value).
;;; Return the raw value word, masked to fixnum.
(defun %sfloat-hash (key)
  (logand (uvref key target::single-float.value-cell)
          (lognot target::fixnummask)))

;;; Hash a macptr.
;;; Macptr layout on WASM32: (header address domain type).
;;; Mix the address value and mask to fixnum.
(defun %macptr-hash (key)
  (let* ((addr (uvref key target::macptr.address-cell))
         (mixed (logand #xFFFFFFFF (+ addr (ash addr -24)))))
    (logand mixed (lognot target::fixnummask))))

;;; Hash a bignum.
;;; Algorithm: hash <- digit + rotate-right(hash, 19) for each digit.
;;; ror32(x, 19) = (x >> 19) | ((x & #x7FFFF) << 13)
;;; All arithmetic is 32-bit unsigned.
;;; MUST match native ARM LAP exactly.
(defun %bignum-hash (key)
  (let* ((ndigits (%bignum-length key))
         (hash 0))
    (declare (fixnum ndigits) (type (unsigned-byte 32) hash))
    (dotimes (i ndigits)
      (let* ((digit (%bignum-ref key i))
             (rotated (logand #xFFFFFFFF
                              (logior (ash hash -19)
                                      (ash (logand hash #x7FFFF) 13)))))
        (setq hash (logand #xFFFFFFFF (+ digit rotated)))))
    (logand hash (lognot target::fixnummask))))

;;; Get the forwarding epoch number from the kernel global.
;;; On WASM, GC forwarding is not yet implemented; stub returns 0.
(defun %get-fwdnum ()
  0)

;;; Get the GC count from the kernel global.
;;; On WASM, GC is not yet implemented; stub returns 0.
(defun %get-gc-count ()
  0)


;;; ---------------------------------------------------------------
;;; Hash table key operations.
;;; On native backends, these call subprims that handle EGC
;;; memoization (write-barrier).  On WASM, there is no EGC,
;;; so these are simple writes.
;;; ---------------------------------------------------------------

;;; Set a hash table vector key.  The vector is a general vector
;;; (simple-vector).  index is the slot index.
(defun %set-hash-table-vector-key (vector index value)
  (setf (%svref vector index) value))

;;; Compare-and-swap a hash table vector key.
;;; On WASM, single-threaded: compare and write if old matches.
;;; Returns T if the swap succeeded, NIL otherwise.
(defun %set-hash-table-vector-key-conditional (offset vector old new)
  ;; offset is a byte offset including misc-data-offset and word-shift.
  ;; Convert back to a slot index.
  (let* ((index (ash (- offset target::misc-data-offset) (- target::word-shift)))
         (current (%svref vector index)))
    (when (eq current old)
      (setf (%svref vector index) new)
      t)))

;;; Strip the tag bits to turn x into a fixnum.
;;; Clear the full tag bits, then shift to account for the difference
;;; between tag width and fixnum shift.
(defun strip-tag-to-fixnum (x)
  (if (fixnump x)
    x
    (ash (logand x (lognot target::fulltagmask))
         (- target::fixnumshift target::ntagbits))))

;;; end of wasm-hash.lisp
