;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Copyright 2026 Clozure Associates
;;;
;;; Licensed under the Apache License, Version 2.0 (the "License");
;;; you may not use this file except in compliance with the License.
;;; You may obtain a copy of the License at
;;;
;;;     http://www.apache.org/licenses/LICENSE-2.0
;;;
;;; Unless required by applicable law or agreed to in writing, software
;;; distributed under the License is distributed on an "AS IS" BASIS,
;;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;;; See the License for the specific language governing permissions and
;;; limitations under the License.

;;; level-0;WASM;wasm-misc.lisp
;;;
;;; WASM equivalents of the ARM LAP functions in level-0/ARM/arm-misc.lisp.
;;; WASM is single-threaded, so all atomic operations (ldrex/strex on ARM)
;;; become simple read-modify-write sequences.  Threading/process control
;;; functions are no-ops.  Macptr<->raw-memory functions that require FFI
;;; are stubbed.
;;;
;;; Uses defun (not defarmlapfunction).  Memory access via %fixnum-ref /
;;; %fixnum-set compiler intrinsics.  Architecture constants use the
;;; target:: prefix.

(in-package "CCL")

;;; ======================================================================
;;; Ivector copy — pure Lisp dispatch functions (same as ARM)
;;; ======================================================================

;;; Copy N bytes from pointer SRC (starting at SRC-BYTE-OFFSET) to
;;; ivector DEST (starting at DEST-BYTE-OFFSET).
(defun %copy-ptr-to-ivector (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (let* ((ptr-align (logand 7 (%ptr-to-int src))))
    (declare (type (mod 8) ptr-align))
    (if (and (>= nbytes 32)
             (= 0 (logand nbytes 3))
             (= 0 (logand dest-byte-offset 3))
             (= 0 (logand (the fixnum (+ ptr-align src-byte-offset)) 3)))
      (%copy-ptr-to-ivector-32bit src src-byte-offset dest dest-byte-offset nbytes)
      (%copy-ptr-to-ivector-8bit src src-byte-offset dest dest-byte-offset nbytes))
    dest))

;;; Copy N bytes from ivector SRC to pointer DEST.
(defun %copy-ivector-to-ptr (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (let* ((ptr-align (logand (the (unsigned-byte 32) (%ptr-to-int dest)) 7)))
    (declare (type (mod 8) ptr-align))
    (if (or (< nbytes 32)
            (not (= 0 (logand nbytes 3)))
            (not (= 0 (logand src-byte-offset 3)))
            (not (= 0 (logand (the fixnum (+ ptr-align dest-byte-offset)) 3))))
      (%copy-ivector-to-ptr-8bit src src-byte-offset dest dest-byte-offset nbytes)
      (%copy-ivector-to-ptr-32bit src src-byte-offset dest dest-byte-offset nbytes))
    dest))

;;; Copy N bytes from ivector SRC to ivector DEST, choosing direction.
(defun %copy-ivector-to-ivector (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes))
  (if (or (not (eq src dest))
          (< dest-byte-offset src-byte-offset)
          (>= dest-byte-offset (the fixnum (+ src-byte-offset nbytes))))
    (%copy-ivector-to-ivector-postincrement src src-byte-offset dest dest-byte-offset nbytes)
    (if (and (eq src dest)
             (eql src-byte-offset dest-byte-offset))
      dest
      (%copy-ivector-to-ivector-predecrement src
                                             (the fixnum (+ src-byte-offset nbytes))
                                             dest
                                             (the fixnum (+ dest-byte-offset nbytes))
                                             nbytes)))
  dest)

;;; Forward copy with alignment optimization.
(defun %copy-ivector-to-ivector-postincrement (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes))
  (cond ((or (< nbytes 8)
             (not (= (logand src-byte-offset 3)
                     (logand dest-byte-offset 3))))
         (%copy-ivector-to-ivector-postincrement-8bit src src-byte-offset dest dest-byte-offset nbytes))
        (t
         (let* ((prefix-size (- 4 (logand src-byte-offset 3))))
           (declare (fixnum prefix-size))
           (unless (= 4 prefix-size)
             (%copy-ivector-to-ivector-postincrement-8bit src src-byte-offset dest dest-byte-offset prefix-size)
             (incf src-byte-offset prefix-size)
             (incf dest-byte-offset prefix-size)
             (decf nbytes prefix-size)))
         (let* ((tail-size (logand nbytes 3))
                (fullword-size (- nbytes tail-size)))
           (declare (fixnum tail-size fullword-size))
           (unless (zerop fullword-size)
             (%copy-ivector-to-ivector-postincrement-32bit src src-byte-offset dest dest-byte-offset fullword-size))
           (unless (zerop tail-size)
             (%copy-ivector-to-ivector-postincrement-8bit src (the fixnum (+ src-byte-offset fullword-size)) dest (the fixnum (+ dest-byte-offset fullword-size)) tail-size))))))

;;; Backward copy with alignment optimization.
(defun %copy-ivector-to-ivector-predecrement (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes))
  (cond ((or (< nbytes 8)
             (not (= (logand src-byte-offset 3)
                     (logand dest-byte-offset 3))))
         (%copy-ivector-to-ivector-predecrement-8bit src src-byte-offset dest dest-byte-offset nbytes))
    (t
      (let* ((suffix-size (logand src-byte-offset 3)))
        (declare (fixnum suffix-size))
        (unless (zerop suffix-size)
          (%copy-ivector-to-ivector-predecrement-8bit src src-byte-offset dest dest-byte-offset suffix-size)
          (decf src-byte-offset suffix-size)
          (decf dest-byte-offset suffix-size)
          (decf nbytes suffix-size)))
      (let* ((head-size (logand nbytes 3))
             (fullword-size (- nbytes head-size)))
        (declare (fixnum head-size fullword-size))
        (unless (zerop fullword-size)
          (%copy-ivector-to-ivector-predecrement-32bit src src-byte-offset dest dest-byte-offset fullword-size))
        (unless (zerop head-size)
          (%copy-ivector-to-ivector-predecrement-8bit src (the fixnum (- src-byte-offset fullword-size)) dest (the fixnum (- dest-byte-offset fullword-size)) head-size))))))

;;; Copy gvector elements, honoring write barrier via %svref/setf.
(defun %copy-gvector-to-gvector (src src-element dest dest-element nelements)
  (declare (fixnum src-element dest-element nelements)
           (optimize (speed 3) (safety 0)))
  (if (or (not (eq src dest))
          (< dest-element src-element)
          (>= dest-element (the fixnum (+ src-element nelements))))
    (do* ()
         ((<= nelements 0) dest)
      (setf (%svref dest dest-element)
            (%svref src src-element))
      (incf dest-element)
      (incf src-element)
      (decf nelements))
    (do* ((src-element (+ src-element nelements))
          (dest-element (+ dest-element nelements)))
         ((<= nelements 0) dest)
      (declare (fixnum src-element dest-element))
      (decf src-element)
      (decf dest-element)
      (setf (%svref dest dest-element)
            (%svref src src-element))
      (decf nelements))))

;;; ======================================================================
;;; Ivector copy — byte-level and word-level primitives
;;; ======================================================================

;;; Ptr-to-ivector copies: these require reading from a raw macptr address.
;;; On WASM, FFI/raw-memory access is deferred.  Stub with error.

(defun %copy-ptr-to-ivector-8bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (ignore src src-byte-offset dest dest-byte-offset nbytes))
  (error "%copy-ptr-to-ivector-8bit: raw pointer access not yet implemented on WASM"))

(defun %copy-ptr-to-ivector-32bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (ignore src src-byte-offset dest dest-byte-offset nbytes))
  (error "%copy-ptr-to-ivector-32bit: raw pointer access not yet implemented on WASM"))

;;; Ivector-to-ptr copies: same situation — require writing to raw memory.

(defun %copy-ivector-to-ptr-8bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (ignore src src-byte-offset dest dest-byte-offset nbytes))
  (error "%copy-ivector-to-ptr-8bit: raw pointer access not yet implemented on WASM"))

(defun %copy-ivector-to-ptr-32bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (ignore src src-byte-offset dest dest-byte-offset nbytes))
  (error "%copy-ivector-to-ptr-32bit: raw pointer access not yet implemented on WASM"))

;;; Ivector-to-ivector byte copy (forward).
;;; uvref on a u8 ivector uses element indices (header skipped automatically).
(defun %copy-ivector-to-ivector-postincrement-8bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (dotimes (i nbytes dest)
    (declare (fixnum i))
    (setf (uvref dest (the fixnum (+ dest-byte-offset i)))
          (uvref src (the fixnum (+ src-byte-offset i))))))

;;; Ivector-to-ivector word copy (forward).
;;; Operates on 32-bit words.  Byte offsets must be word-aligned.
(defun %copy-ivector-to-ivector-postincrement-32bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (let* ((src-word-offset (ash src-byte-offset -2))
         (dest-word-offset (ash dest-byte-offset -2))
         (nwords (ash nbytes -2)))
    (declare (fixnum src-word-offset dest-word-offset nwords))
    (dotimes (i nwords dest)
      (declare (fixnum i))
      (setf (uvref dest (the fixnum (+ dest-word-offset i)))
            (uvref src (the fixnum (+ src-word-offset i)))))))

;;; Ivector-to-ivector byte copy (backward / predecrement).
;;; SRC-BYTE-OFFSET and DEST-BYTE-OFFSET point one past the last byte.
(defun %copy-ivector-to-ivector-predecrement-8bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (dotimes (i nbytes dest)
    (declare (fixnum i))
    (let ((si (the fixnum (- src-byte-offset (the fixnum (1+ i)))))
          (di (the fixnum (- dest-byte-offset (the fixnum (1+ i))))))
      (declare (fixnum si di))
      (setf (uvref dest di)
            (uvref src si)))))

;;; Ivector-to-ivector word copy (backward / predecrement).
;;; Byte offsets point one past the last byte and must be word-aligned.
(defun %copy-ivector-to-ivector-predecrement-32bit (src src-byte-offset dest dest-byte-offset nbytes)
  (declare (fixnum src-byte-offset dest-byte-offset nbytes)
           (optimize (speed 3) (safety 0)))
  (let* ((src-word-offset (ash src-byte-offset -2))
         (dest-word-offset (ash dest-byte-offset -2))
         (nwords (ash nbytes -2)))
    (declare (fixnum src-word-offset dest-word-offset nwords))
    (dotimes (i nwords dest)
      (declare (fixnum i))
      (setf (uvref dest (the fixnum (- dest-word-offset (the fixnum (1+ i)))))
            (uvref src (the fixnum (- src-word-offset (the fixnum (1+ i)))))))))

;;; ======================================================================
;;; Heap / allocation
;;; ======================================================================

(defun %heap-bytes-allocated ()
  0)

;;; The compiler handles (values ...) forms specially and inlines them.
;;; This definition exists for (funcall #'values ...) and similar
;;; indirect calls.  The &rest/apply pattern is intentional — the
;;; compiler's special handling of VALUES prevents infinite recursion
;;; when the call is direct.
(defun values (&rest vals)
  (declare (dynamic-extent vals))
  (apply #'values vals))

;;; ======================================================================
;;; Macptr operations
;;; ======================================================================

;;; Store OBJECT (any Lisp object) in MACPTR's address slot.
;;; On ARM this writes the raw tagged pointer into macptr.address;
;;; on WASM we use the cell accessor.
(defun %setf-macptr-to-object (macptr object)
  (%fixnum-set macptr target::macptr.address object)
  object)

;;; Read the macptr address as a fixnum.
(defun %fixnum-from-macptr (macptr)
  (let ((val (%fixnum-ref macptr target::macptr.address)))
    val))

;;; 64-bit integer access through macptrs — requires raw memory access.
;;; Stubbed for WASM (FFI deferred).
(defun %%get-unsigned-longlong (ptr offset)
  (declare (ignore ptr offset))
  0)

(defun %%get-signed-longlong (ptr offset)
  (declare (ignore ptr offset))
  0)

(defun %%set-unsigned-longlong (ptr offset val)
  (declare (ignore ptr offset))
  val)

(defun %%set-signed-longlong (ptr offset val)
  (declare (ignore ptr offset))
  val)

;;; Change a macptr's subtag to dead-macptr so the GC won't follow it.
(defun %macptr->dead-macptr (macptr)
  ;; Write the dead-macptr subtag byte into the header's subtag position.
  ;; misc-subtag-offset is the offset (from the tagged pointer) of the
  ;; low byte of the header word, which holds the subtag.
  ;; On a 32-bit little-endian system, we read the header word, replace
  ;; the low 8 bits, and write it back.
  (let* ((header (%fixnum-ref macptr target::misc-subtag-offset))
         (new-header (logior (logand header (lognot #xff))
                             target::subtag-dead-macptr)))
    (%fixnum-set macptr target::misc-subtag-offset new-header))
  macptr)

;;; Store the address of VECT's data in PTR (a macptr).
;;; For double-float and double-float-vector the data offset is
;;; misc-dfloat-offset; for all others it is misc-data-offset.
(defun %vect-data-to-macptr (vect ptr)
  (let* ((subtag (logand #xff (%fixnum-ref vect target::misc-subtag-offset)))
         (offset (if (or (= subtag target::subtag-double-float-vector)
                         (= subtag target::subtag-double-float))
                   target::misc-dfloat-offset
                   target::misc-data-offset)))
    ;; Store (vect + offset) as the macptr address.  Since vect is a
    ;; tagged pointer and offset adjusts past the header, (+ vect offset)
    ;; gives the address of the first data byte.
    (%fixnum-set ptr target::macptr.address (+ vect offset)))
  ptr)

;;; Recover an ivector from a macptr that points to the first byte of
;;; its data (e.g. created by %vect-data-to-macptr).
(defun %ivector-from-macptr (ptr)
  (let* ((addr (%fixnum-ref ptr target::macptr.address))
         ;; The data address is (ivector + misc-data-offset) for normal
         ;; ivectors.  Subtract misc-data-offset and add back fulltag-misc
         ;; to recover the tagged pointer.  For double-float aligned
         ;; vectors the alignment bit helps: test bit 2 (node-size).
         (node-bit (logand addr target::node-size))
         (align-adjust (logxor node-bit target::node-size)))
    (- (+ addr (- target::fulltag-misc target::node-size)) align-adjust)))

;;; Read through SRC macptr, store result in DEST macptr.
;;; Should be called with interrupts disabled.
(defun %safe-get-ptr (src dest)
  ;; On native platforms this reads through the macptr address and
  ;; stores the result.  On WASM, raw pointer dereferencing is not
  ;; available.  Store 0 as a safe fallback.
  (let ((addr (%fixnum-ref src target::macptr.address)))
    (declare (ignore addr))
    (%fixnum-set dest target::macptr.address 0))
  dest)

;;; ======================================================================
;;; Interrupt level / TCR
;;; ======================================================================

;;; Read the current interrupt level from the thread-local bindings.
(defun interrupt-level ()
  (%fixnum-ref (%fixnum-ref (%current-tcr) target::tcr.tlb-pointer)
               target::interrupt-level-binding-index))

;;; Set the current interrupt level in the thread-local bindings.
(defun set-interrupt-level (new)
  (%fixnum-set (%fixnum-ref (%current-tcr) target::tcr.tlb-pointer)
               target::interrupt-level-binding-index
               new))

;;; %current-tcr is a compiler intrinsic.  This fallback should never
;;; be called — if it is, something went wrong with compilation.
(defun %current-tcr ()
  (error "%current-tcr must be compiled as an intrinsic on WASM"))

;;; Read the toplevel function from a TCR's value stack area.
(defun %tcr-toplevel-function (tcr)
  (let* ((vs-area (%fixnum-ref tcr target::tcr.vs-area))
         (high (%fixnum-ref vs-area target::area.high))
         (active (if (eq tcr (%current-tcr))
                   ;; Current TCR: active is the live vsp, but we
                   ;; can't easily get it from Lisp.  Use the saved value.
                   (%fixnum-ref vs-area target::area.active)
                   (%fixnum-ref vs-area target::area.active))))
    (if (eql high active)
      nil
      ;; The toplevel function is the last thing pushed on the vstack,
      ;; i.e. at (high - node-size).
      (%fixnum-ref high (- target::node-size)))))

;;; Set the toplevel function for a TCR.
(defun %set-tcr-toplevel-function (tcr fun)
  (let* ((vs-area (%fixnum-ref tcr target::tcr.vs-area))
         (high (%fixnum-ref vs-area target::area.high))
         (active (if (eq tcr (%current-tcr))
                   (%fixnum-ref vs-area target::area.active)
                   (%fixnum-ref vs-area target::area.active))))
    (when (eql high active)
      ;; Need to push a word: decrement active
      (let ((new-active (- high target::node-size)))
        (%fixnum-set vs-area target::area.active new-active)
        (%fixnum-set tcr target::tcr.save-vsp new-active)))
    (%fixnum-set high (- target::node-size) fun))
  fun)

;;; Return the head of the dynamic binding chain.
(defun %current-db-link ()
  (%fixnum-ref (%current-tcr) target::tcr.db-link))

;;; Return the marker value that indicates no thread-local binding.
(defun %no-thread-local-binding-marker ()
  target::subtag-no-thread-local-binding)

;;; On WASM there are no callee-saved registers, so no values to return.
(defun get-saved-register-values ()
  (values))

;;; ======================================================================
;;; Atomics — simple read-modify-write (WASM is single-threaded)
;;; ======================================================================

;;; Conditional store: if the word at (object + offset) is EQ to OLD,
;;; write NEW and return T; otherwise return NIL.
;;; OFFSET is a fixnum byte offset (as passed from Lisp, already shifted).
(defun %store-node-conditional (offset object old new)
  (let ((current (%fixnum-ref object offset)))
    (if (eq current old)
      (progn
        (%fixnum-set object offset new)
        t)
      nil)))

;;; Lock/unlock the GC lock — no-ops on single-threaded WASM.
(defun %lock-gc-lock ()
  nil)

(defun %unlock-gc-lock ()
  nil)

;;; Atomically increment the node at (NODE + DISP) by BY.
;;; Return the OLD value (before increment).
(defun %atomic-incf-node (by node disp)
  (let ((old (%fixnum-ref node disp)))
    (%fixnum-set node disp (+ old by))
    old))

;;; Increment the word at macptr address; return new value as fixnum.
;;; Stubbed: raw pointer arithmetic requires FFI.
(defun %atomic-incf-ptr (ptr)
  (declare (ignore ptr))
  (error "%atomic-incf-ptr: raw pointer access not yet implemented on WASM"))

;;; Increment by a fixnum amount.
(defun %atomic-incf-ptr-by (ptr by)
  (declare (ignore ptr by))
  (error "%atomic-incf-ptr-by: raw pointer access not yet implemented on WASM"))

;;; Decrement the word at macptr address.
(defun %atomic-decf-ptr (ptr)
  (declare (ignore ptr))
  (error "%atomic-decf-ptr: raw pointer access not yet implemented on WASM"))

;;; Decrement only if the result would be >= 0.
(defun %atomic-decf-ptr-if-positive (ptr)
  (declare (ignore ptr))
  (error "%atomic-decf-ptr-if-positive: raw pointer access not yet implemented on WASM"))

;;; Exchange the word at macptr address with NEWVAL, return old as fixnum.
(defun %atomic-swap-ptr (ptr newval)
  (declare (ignore ptr newval))
  (error "%atomic-swap-ptr: raw pointer access not yet implemented on WASM"))

;;; Compare-and-swap on macptr address (unboxed fixnum values).
(defun %ptr-store-conditional (ptr expected-oldval newval)
  (declare (ignore ptr expected-oldval newval))
  (error "%ptr-store-conditional: raw pointer access not yet implemented on WASM"))

;;; Compare-and-swap on macptr address (boxed fixnum comparison).
(defun %ptr-store-fixnum-conditional (ptr expected-oldval newval)
  (declare (ignore ptr expected-oldval newval))
  (error "%ptr-store-fixnum-conditional: raw pointer access not yet implemented on WASM"))

;;; Same pattern as %store-node-conditional, used for hash table keys.
(defun %set-hash-table-vector-key-conditional (offset vector old new)
  (let ((current (%fixnum-ref vector offset)))
    (if (eq current old)
      (progn
        (%fixnum-set vector offset new)
        t)
      nil)))

;;; Pop from the static cons freelist.
;;; Stub: static cons allocation is not yet implemented on WASM.
(defun %atomic-pop-static-cons ()
  nil)

;;; Exchange word at macptr address, return old value as fixnum.
(defun xchgl (newval ptr)
  (declare (ignore newval ptr))
  (error "xchgl: raw pointer access not yet implemented on WASM"))

;;; ======================================================================
;;; Thread control — all no-ops on single-threaded WASM
;;; ======================================================================

(defun %%tcr-interrupt (target)
  (declare (ignore target))
  0)

(defun %suspend-tcr (target)
  (declare (ignore target))
  nil)

(defun %suspend-other-threads ()
  t)

(defun %resume-tcr (target)
  (declare (ignore target))
  nil)

(defun %resume-other-threads ()
  nil)

(defun %kill-tcr (target)
  (declare (ignore target))
  nil)

(defun pending-user-interrupt ()
  nil)

(defun %check-deferred-gc ()
  nil)

;;; ======================================================================
;;; Misc
;;; ======================================================================

;;; Return the fixnum address of the data portion of a misc object.
;;; (tagged-pointer + misc-data-offset) is already a fixnum on a 32-bit
;;; system since misc-data-offset cancels the tag and adds 4.
(defun %misc-address-fixnum (misc-object)
  (+ misc-object target::misc-data-offset))

;;; Align a raw pointer, write a vector header, return a tagged ivector.
;;; Stub: requires raw pointer manipulation.
(defun fudge-heap-pointer (ptr subtype len)
  (declare (ignore ptr subtype len))
  (error "fudge-heap-pointer: not yet implemented on WASM"))

;;; Recover the original (pre-fudge) pointer from a fudged vector.
;;; Stub: inverse of fudge-heap-pointer.
(defun %%make-disposable (ptr vector)
  (declare (ignore ptr vector))
  (error "%%make-disposable: not yet implemented on WASM"))

;;; Save the current image.
;;; Stub: proper implementation will use wasm_save_image_direct.
(defun %%save-application (flags fd)
  (declare (ignore flags fd))
  nil)

;;; end of wasm-misc.lisp
