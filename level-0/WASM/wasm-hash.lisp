;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 hash operations.
;;; On ARM these are LAP functions; on WASM they are pure Lisp.
;;; Hash algorithms MUST match the native CCL output exactly.

(in-package "CCL")

(eval-when (:compile-toplevel :execute)
  (require "HASHENV" "ccl:xdump;hashenv"))


;;; Equivalent to cl:mod when both args are positive fixnums.
;;; Uses binary doubling+subtraction to avoid mod/rem/%fixnum-truncate,
;;; whose pure-Lisp binary long division (using integer-length and large
;;; ash shifts) compiles incorrectly on WASM.  O(log(n/d)) iterations.
(defun fast-mod (number divisor)
  (declare (fixnum number divisor)
           (optimize (speed 3) (safety 0)))
  (let ((n number))
    (declare (fixnum n))
    (when (< n divisor) (return-from fast-mod n))
    ;; Phase 1: double divisor to largest power-of-2 multiple <= n
    (let ((d divisor))
      (declare (fixnum d))
      (loop
        (let ((d2 (the fixnum (+ d d))))
          (if (or (<= d2 0) (> d2 n))
            (return)
            (setq d d2))))
      ;; Phase 2: subtract from largest down to divisor
      (loop
        (when (>= n d) (setq n (the fixnum (- n d))))
        (when (eql d divisor) (return-from fast-mod n))
        (setq d (the fixnum (ash d -1)))))))

;;; Faster mod using reciprocal multiplication.
;;; On WASM, just use the binary reduction above.
(defun fast-mod-3 (number divisor recip)
  (declare (ignore recip))
  (fast-mod number divisor))

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

;;; ---------------------------------------------------------------
;;; Hash vector initialization — WASM override.
;;; The generic %init-nhash-vector computes:
;;;   (floor (ash 1 (- nbits-in-word fixnumshift)) size)
;;; which is (floor 2^30 size) — a bignum division.
;;; On WASM, fast-mod-3 ignores the reciprocal (uses binary reduction
;;; instead), so the value is never read.  Skip the bignum arithmetic
;;; which crashes during early boot when bignum support is fragile.
;;; ---------------------------------------------------------------

(defun %init-nhash-vector (vector flags)
  (let ((size (vector-index->index (uvsize vector))))
    (declare (fixnum size))
    (setf (nhash.vector.link vector) 0
          (nhash.vector.flags vector) flags
          (nhash.vector.gc-count vector) (%get-gc-count)
          (nhash.vector.free-alist vector) nil
          (nhash.vector.finalization-alist vector) nil
          (nhash.vector.hash vector) nil
          (nhash.vector.deleted-count vector) 0
          (nhash.vector.count vector) 0
          (nhash.vector.cache-key vector) free-hash-marker
          (nhash.vector.cache-value vector) nil
          (nhash.vector.cache-idx vector) nil
          (nhash.vector.size vector) size
          ;; Reciprocal unused on WASM (fast-mod-3 ignores it).
          ;; Set to 0 to avoid (floor 2^30 size) bignum arithmetic.
          (nhash.vector.size-reciprocal vector) 0)))

;;; ---------------------------------------------------------------
;;; Hash table locking — single-threaded WASM needs no locking.
;;; The generic versions in l0-hash.lisp reference *CURRENT-PROCESS*
;;; which is only defined in level-1 (l1-processes.lisp) and therefore
;;; unbound during cold-boot.  Override them here to avoid XUNBND.
;;; ---------------------------------------------------------------

(defun read-lock-hash-table (hash)
  (if (nhash.read-only hash) :readonly nil))

(defun write-lock-hash-table (hash)
  (if (nhash.read-only hash)
    (signal-read-only-hash-table-error hash)
    nil))

(defun unlock-hash-table (hash was-readonly)
  (declare (ignore hash was-readonly))
  nil)

;;; end of wasm-hash.lisp
