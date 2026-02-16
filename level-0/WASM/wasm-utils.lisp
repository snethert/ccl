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

;;; WASM32 level-0 utility functions.
;;; On ARM these are LAP (defarmlapfunction).  On WASM they are pure Lisp
;;; using compiler intrinsics (%fixnum-ref, %fixnum-set) and target::
;;; arch constants.
;;;
;;; GC operations are stubbed out: WASM uses a host-managed allocator
;;; and has no in-process GC.  Area walking is implemented correctly
;;; since it is used during bootstrap.

(in-package "CCL")

;;;=========================================================================
;;; Address / area operations
;;;=========================================================================

;;; %address-of a fixnum is a fixnum, just for spite.
;;; %address-of anything else is the address of that thing as an integer.
;;; On ARM, SPmakeu32 boxes the raw tagged pointer as an unsigned integer.
;;; On WASM we lack direct access to machine-level pointer values from
;;; Lisp, so non-fixnum objects are not yet supported.
(defun %address-of (arg)
  (if (fixnump arg)
    arg
    (error "%address-of non-fixnum objects not yet implemented on WASM")))

;;; The nilreg-relative global all-areas is a doubly-linked-list header
;;; that describes nothing.  Its successor describes the current/active
;;; dynamic heap.  Return a fixnum which "points to" that area, after
;;; ensuring that the "active" pointers associated with the current
;;; thread's stacks are correct.
;;;
;;; On WASM we skip the stack-pointer updates (no hardware SP/VSP to
;;; snapshot) and just return the successor of all-areas.
(defun %normalize-areas ()
  (let* ((all-areas (%get-kernel-global 'all-areas)))
    (%fixnum-ref all-areas target::area.succ)))

(defun %active-dynamic-area ()
  (let* ((all-areas (%get-kernel-global 'all-areas)))
    (%fixnum-ref all-areas target::area.succ)))

;;; Check if object's address falls between area.active and area.high
;;; (i.e. it is in the active portion of a stack area).
(defun %object-in-stack-area-p (object area)
  (let* ((active (%fixnum-ref area target::area.active))
         (high (%fixnum-ref area target::area.high)))
    (and (>= (the fixnum object) (the fixnum active))
         (< (the fixnum object) (the fixnum high)))))

;;; Check if object's address falls between area.low and area.active
;;; (i.e. it is in the used portion of a heap area).
(defun %object-in-heap-area-p (object area)
  (let* ((low (%fixnum-ref area target::area.low))
         (active (%fixnum-ref area target::area.active)))
    (and (>= (the fixnum object) (the fixnum low))
         (< (the fixnum object) (the fixnum active)))))

;;;=========================================================================
;;; Area walking
;;;=========================================================================

;;; Compute the size in bytes of a misc (uvector) object given its header
;;; word.  The header encodes the subtag (type) in the low 8 bits and the
;;; element count above that.  The total padded size includes the 4-byte
;;; header and is aligned to the 8-byte dnode boundary.
(defun %misc-object-size-in-bytes (header)
  (let* ((subtag (logand header target::subtag-mask))
         (tag (logand subtag target::fulltagmask))
         (element-count (ash header (- target::num-subtag-bits)))
         (byte-count
          (cond
            ;; Node headers: each element is one word (4 bytes).
            ((= tag target::fulltag-nodeheader)
             (ash element-count target::word-shift))
            ;; 32-bit immutable vectors (including simple-base-string
            ;; on 32-bit): each element is 4 bytes.
            ((<= subtag target::max-32-bit-ivector-subtag)
             (ash element-count target::word-shift))
            ;; 8-bit vectors: one byte per element.
            ((<= subtag target::max-8-bit-ivector-subtag)
             element-count)
            ;; 16-bit vectors: two bytes per element.
            ((<= subtag target::max-16-bit-ivector-subtag)
             (ash element-count 1))
            ;; complex-double-float-vector: 16 bytes per element + 4 pad.
            ((= subtag target::subtag-complex-double-float-vector)
             (+ 4 (ash element-count 4)))
            ;; bit-vector: ceil(count/8) bytes.
            ((= subtag target::subtag-bit-vector)
             (ash (+ element-count 7) -3))
            ;; double-float-vector (and complex-single-float-vector):
            ;; 8 bytes per element + 4 pad.
            (t
             (+ 4 (ash element-count 3))))))
    ;; Total size = header word (4) + data bytes, aligned up to 8.
    (logand (+ byte-count 4 7) (lognot target::fulltagmask))))

;;; Walk a static area, calling FUNCTION on each object found between
;;; area.low and area.active.  Objects are either conses (8 bytes, no
;;; header -- identified by the first word NOT being a header) or misc
;;; objects (header word + data).
(defun walk-static-area (area function)
  (let* ((obj (%fixnum-ref area target::area.low))
         (limit (%fixnum-ref area target::area.active)))
    (loop
      (when (>= (the fixnum obj) (the fixnum limit))
        (return))
      (let* ((header (%fixnum-ref obj 0))
             (tag (logand header target::fulltagmask)))
        (cond
          ;; Header word indicates a misc (uvector) object.
          ((or (= tag target::fulltag-immheader)
               (= tag target::fulltag-nodeheader))
           ;; Tag the raw address as a misc-tagged pointer and call.
           (funcall function (+ obj target::fulltag-misc))
           ;; Advance past the object.  Re-read header in case GC moved
           ;; things (unlikely on WASM, but mirrors the ARM pattern).
           (let* ((h (%fixnum-ref obj 0)))
             (setq obj (+ obj (%misc-object-size-in-bytes h)))))
          ;; Otherwise it is a cons cell (2 words, 8 bytes).
          (t
           (funcall function (+ obj target::fulltag-cons))
           (setq obj (+ obj target::cons.size))))))))

;;; Walk the active dynamic area.  On ARM this allocates a sentinel cons
;;; to know when to stop (since the function might cons and move the
;;; allocation pointer).  On WASM the host manages allocation so we use
;;; the simpler approach: snapshot the limit, walk from area.low to
;;; the snapshot.  If the function conses, new objects beyond the snapshot
;;; will simply not be visited (which is fine -- the ARM version has the
;;; same semantic with its sentinel).
(defun %walk-dynamic-area (area function)
  (let* ((tenured (%get-kernel-global 'tenured-area)))
    ;; If there is a tenured area, walk from there instead.
    (unless (eql tenured 0)
      (setq area tenured)))
  (let* ((obj (%fixnum-ref area target::area.low))
         (limit (%fixnum-ref area target::area.active)))
    (loop
      (when (>= (the fixnum obj) (the fixnum limit))
        (return))
      (let* ((header (%fixnum-ref obj 0))
             (tag (logand header target::fulltagmask)))
        (cond
          ((or (= tag target::fulltag-immheader)
               (= tag target::fulltag-nodeheader))
           (funcall function (+ obj target::fulltag-misc))
           (let* ((h (%fixnum-ref obj 0)))
             (setq obj (+ obj (%misc-object-size-in-bytes h)))))
          (t
           (funcall function (+ obj target::fulltag-cons))
           (setq obj (+ obj target::cons.size))))))))

;;; On ARM, walk-dynamic-area suspends other threads first.
;;; WASM is single-threaded, so no suspension needed.
(defun walk-dynamic-area (area func)
  (%walk-dynamic-area area func))

;;;=========================================================================
;;; Class system
;;;=========================================================================

;;; Fast path: extract class from an instance via its class wrapper.
;;; instance.class-wrapper and %wrapper-class are %svref accessor macros
;;; defined in lispequ.lisp.  This is equivalent to:
;;;   (%wrapper-class (instance.class-wrapper instance))
;;; which is the expansion of %instance-class.
(defun %class-of-instance (instance)
  (%wrapper-class (instance.class-wrapper instance)))

;;; Full class-of.  Look up in *class-table* by typecode.
;;; If the table entry is a function, call it on x (for special dispatch).
;;; If it is a class, return it directly.
;;; This mirrors the ARM LAP but in pure Lisp.
(defun class-of (x)
  (let* ((typecode (typecode x))
         (class-table *class-table*))
    (unless class-table
      (error "class-of: *class-table* not initialized"))
    (let* ((entry (svref class-table typecode)))
      (cond
        ((null entry) (no-class-error x))
        ((functionp entry) (funcall entry x))
        (t entry)))))

;;;=========================================================================
;;; GC control  (all stubs on WASM)
;;;=========================================================================

(defun full-gccount ()
  "Return the number of full GCs that have occurred."
  (let* ((tenured (%get-kernel-global 'tenured-area)))
    (if (and tenured (not (eql tenured 0)))
      (%fixnum-ref tenured target::area.gc-count)
      (%get-kernel-global 'gc-count))))

(defun gc ()
  "Invoke the GC.  No-op on WASM -- the host manages memory."
  nil)

;;; Make a list of NCONSES conses, each initialized to INITIAL-ELEMENT.
;;; On ARM this is a kernel service for efficiency.  On WASM we just
;;; use MAKE-LIST.
(defun %allocate-list (initial-element nconses)
  (make-list nconses :initial-element initial-element))

(defun egc (arg)
  "Enable or disable the EGC.  No-op on WASM (no ephemeral GC)."
  (declare (ignore arg))
  nil)

(defun %configure-egc (e0size e1size e2size)
  "Configure EGC generation sizes.  No-op on WASM."
  (declare (ignore e0size e1size e2size))
  nil)

(defun purify ()
  "Move impure objects to pure space.  No-op on WASM."
  nil)

(defun impurify ()
  "Move pure objects to impure space.  No-op on WASM."
  nil)

(defun lisp-heap-gc-threshold ()
  "Return the value of the kernel variable that specifies the amount
of free space to leave in the heap after full GC."
  0)

(defun set-lisp-heap-gc-threshold (new)
  "Set the value of the kernel variable that specifies the amount of free
space to leave in the heap after full GC to new-value, which should be a
non-negative fixnum. Returns the value of that kernel variable (which may
be somewhat larger than what was specified)."
  (declare (ignore new))
  0)

(defun use-lisp-heap-gc-threshold ()
  "Try to grow or shrink lisp's heap space, so that the free space is
(approximately) equal to the current heap threshold. Return NIL"
  nil)

(defun allow-heap-allocation (arg)
  "If ARG is false, signal an ALLOCATION-DISABLED condition on attempts
at heap allocation."
  (declare (ignore arg))
  nil)

(defun heap-allocation-allowed-p ()
  "Return T if heap allocation is allowed, NIL otherwise."
  t)

(defun %ensure-static-conses ()
  nil)

(defun set-gc-notification-threshold (threshold)
  "Set the value of the kernel variable that can be used to trigger
GC notifications."
  (declare (ignore threshold))
  0)

(defun get-gc-notification-threshold ()
  "Get the value of the kernel variable that can be used to trigger
GC notifications."
  0)

;;;=========================================================================
;;; Kernel imports
;;;=========================================================================

(defparameter *kernel-import-table* nil)

(defun %kernel-import (offset)
  (declare (fixnum offset)
           (optimize (speed 3) (safety 0)))
  (let* ((table (or *kernel-import-table*
                    (setq *kernel-import-table*
                          (make-array target::num-kernel-imports))))
         (idx (ash offset -2))
         (p (svref table idx)))
    (declare (simple-vector table) (fixnum idx))
    (if (typep p 'macptr)
      p
      (setf (svref table idx) (%kernel-import-internal offset)))))

;;; On ARM this is a LAP function that reads from the kernel-imports
;;; global and wraps the result in a macptr.  On WASM stub to nil.
(defun %kernel-import-internal (offset)
  (declare (ignore offset))
  nil)

;;;=========================================================================
;;; Macptr utilities
;;;=========================================================================

;;; Read through a macptr to get another pointer.  On ARM this
;;; dereferences the macptr address.  Stub on WASM.
(defun %get-unboxed-ptr (macptr)
  (declare (ignore macptr))
  (%null-ptr))

;;; Revive a dead macptr by changing its subtag back to macptr.
;;; Read the header word, replace the low 8 bits (subtag), write back.
;;; Mirrors the pattern in %macptr->dead-macptr (wasm-misc.lisp).
(defun %revive-macptr (p)
  (let* ((header (%fixnum-ref p target::misc-subtag-offset))
         (new-header (logior (logand header (lognot #xff))
                             target::subtag-macptr)))
    (%fixnum-set p target::misc-subtag-offset new-header))
  p)

;;; Read macptr type cell.
(defun %macptr-type (p)
  (%svref p target::macptr.type-cell))

;;; Read macptr domain cell.
(defun %macptr-domain (p)
  (%svref p target::macptr.domain-cell))

;;; Set macptr type cell.
(defun %set-macptr-type (p new)
  (setf (%svref p target::macptr.type-cell) new))

;;; Set macptr domain cell.
(defun %set-macptr-domain (p new)
  (setf (%svref p target::macptr.domain-cell) new))

;;;=========================================================================
;;; Constant functions
;;;=========================================================================

;;; Always return T, regardless of arguments.
(defun true (&rest ignore)
  (declare (ignore ignore))
  t)

;;; Always return NIL, regardless of arguments.
(defun false (&rest ignore)
  (declare (ignore ignore))
  nil)

;;; Return a stored constant.  On ARM this reads from the function
;;; object's immediate data.  Stub returns NIL.
(defun constant-ref (&rest ignore)
  (declare (ignore ignore))
  nil)

;;;=========================================================================
;;; Watch (not supported on WASM)
;;;=========================================================================

(defun %watch (uvector)
  (declare (ignore uvector))
  (error "Watching objects is not supported on WASM"))

(defun %unwatch (watched new)
  (declare (ignore watched new))
  (error "Watching objects is not supported on WASM"))

;;; end
