;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 level-0 overrides live here.

(in-package "CCL")

;; WASM32 uses ARM layout but entrypoints are fixnum table indices.
(defun %fix-fn-entrypoint (func)
  (let* ((codev (uvref func 1)))
    (cond
      ((and (uvectorp codev)
            (> (uvsize codev) 0))
       (setf (uvref func 0) (uvref codev 0)))
      ((fixnump codev)
       (setf (uvref func 0) codev)))
    func))

;; Minimal macptr->fixnum for WASM. The macptr address slot stores the raw
;; pointer (untagged). Convert to a fixnum that represents the byte address.
(defun macptr->fixnum (ptr)
  (declare (optimize (speed 3) (safety 0)))
  (let ((raw (uvref ptr 1)))
    (ash raw 2)))

;;; On native backends this is a LAP function that atomically prepends ptr
;;; to the gcable-pointers kernel global (a linked list through xmacptr.link).
;;; WASM is single-threaded and lacks LAP, so this is a no-op stub for now.
;;; The consequence: gcable macptrs won't have their foreign memory freed
;;; by the GC finalizer.  Acceptable during bootstrap; proper implementation
;;; requires writing to the gcable-pointers kernel global.
(defun set-%gcable-macptrs% (ptr)
  (declare (ignore ptr))
  nil)

;;;=========================================================================
;;; Compiler-intrinsic fallbacks
;;;
;;; %fixnum-ref, %fixnum-set, and %current-tcr are compiler intrinsics on
;;; WASM.  These defuns provide callable versions for dynamic dispatch
;;; (e.g. via FUNCALL / APPLY) where the compiler cannot open-code them.
;;;=========================================================================

(defun %fixnum-ref (fixnum &optional (offset 0))
  (%fixnum-ref fixnum offset))

(defun %fixnum-ref-natural (fixnum &optional (offset 0))
  (%fixnum-ref-natural fixnum offset))

(defun %fixnum-set (fixnum offset &optional (new-value offset))
  (%fixnum-set fixnum offset new-value))

(defun %fixnum-set-natural (fixnum offset &optional (new-value offset))
  (%fixnum-set-natural fixnum offset new-value))

;;; WASM has no hardware frame pointer; return 0.
(defun %current-frame-ptr ()
  0)

;;;=========================================================================
;;; Kernel globals  (stored relative to NIL, accessed via byte offset)
;;;=========================================================================

;;; Read a kernel global from the negative-offset region below NIL.
;;; On native backends this is a single LAP load.  On WASM the kernel
;;; globals live at fixed offsets from the NIL pointer so %fixnum-ref
;;; with suitable arithmetic suffices — but at bootstrap time the
;;; infrastructure for that may not yet be wired up.  Stub returns NIL.
(defun %get-kernel-global-from-offset (offset)
  (declare (ignore offset))
  nil)

;;; Write a kernel global.  Stub returns new-value.
(defun %set-kernel-global-from-offset (offset new-value)
  (declare (ignore offset))
  new-value)

;;; Read a kernel global into a macptr.  Stub — sets nothing, returns ptr.
(defun %get-kernel-global-ptr-from-offset (offset ptr)
  (declare (ignore offset))
  ptr)

;;;=========================================================================
;;; Stack / frame operations
;;;
;;; WASM uses a spill-stack model managed by the microkernel.  There are
;;; no hardware stack frames to walk, so frame-oriented accessors return
;;; stubs (0 or NIL).
;;;=========================================================================

(defun %current-vsp ()
  0)

(defun %set-current-vsp (new-vsp)
  (declare (ignore new-vsp))
  nil)

(defun %%frame-backlink (p)
  (declare (ignore p))
  0)

(defun %%frame-savefn (p)
  (declare (ignore p))
  nil)

(defun %cfp-lfun (p)
  (declare (ignore p))
  (values nil nil))

(defun %%frame-savevsp (p)
  (declare (ignore p))
  0)

;;;=========================================================================
;;; Memory address operations
;;;=========================================================================

;;; Return a fixnum pointing to the first data element of a uvector.
(defun %uvector-data-fixnum (uv)
  (+ uv target::misc-data-offset))

;;; Read the top catch frame from the TCR.  Returns NIL when there is none.
(defun %catch-top (tcr)
  (let ((val (%fixnum-ref tcr target::tcr.catch-top)))
    (if (eql val 0) nil val)))

;;; Box the raw address of x.  On ARM this left-shifts by fixnumshift.
;;; On WASM everything is already fixnum-tagged, so return x directly.
(defun %fixnum-address-of (x)
  x)

;;; Clear the tag bits to obtain the dnode-aligned address.
(defun %dnode-address-of (x)
  (logand x (lognot target::fulltagmask)))

;;;=========================================================================
;;; Binding list  (single-threaded, simplified)
;;;=========================================================================

(defun %save-standard-binding-list (bindings)
  (declare (ignore bindings))
  nil)

(defun %saved-bindings-address ()
  0)

;;;=========================================================================
;;; Code vector
;;;=========================================================================

(defun %code-vector-pc (code-vector pcptr)
  (declare (ignore code-vector pcptr))
  nil)

;;;=========================================================================
;;; Foreign function call  (WASM — not yet supported)
;;;=========================================================================

(defun %do-ff-call (tag result entry)
  (declare (ignore tag result entry))
  (error "FF-call not supported on WASM"))

(defun %ff-call (entry &rest specs-and-vals)
  (declare (ignore entry specs-and-vals))
  (error "FF-call not supported on WASM"))

;;;=========================================================================
;;; Method dispatch
;;;=========================================================================

;;; On native backends these use LAP to thread the method-context through
;;; a special register.  On WASM we simply delegate to APPLY; the method
;;; context (next-method-list) is ignored at this level because CLOS
;;; will have already closed over it.

(defun %apply-lexpr-with-method-context (magic function args)
  (declare (ignore magic))
  (apply function args))

(defun %apply-with-method-context (magic function args)
  (declare (ignore magic))
  (apply function args))

(defun %apply-lexpr-tail-wise (method args)
  (apply method args))

;;;=========================================================================
;;; Miscellaneous
;;;=========================================================================

;;; Copy a function object.  Pure Lisp — identical to arm-def.lisp.
(defun %copy-function (proto &optional target)
  (let* ((total-size (uvsize proto))
         (new (or target (allocate-typed-vector :function total-size))))
    (declare (fixnum total-size))
    (when target
      (unless (eql total-size (uvsize target))
        (error "Wrong size target ~s" target)))
    (%copy-gvector-to-gvector proto 0 new 0 total-size)
    (%fix-fn-entrypoint new)))

;;; Replace the code of target-fn with that of proto-fn.
;;; On WASM the code-vector is slot 1 and the entrypoint is slot 0.
;;; We copy the code vector and re-fix the entrypoint.
(defun replace-function-code (target-fn proto-fn)
  (if (typep target-fn 'function)
    (if (typep proto-fn 'function)
      (progn
        (setf (uvref target-fn 1) (uvref proto-fn 1))
        (%fix-fn-entrypoint target-fn))
      (report-bad-arg proto-fn 'function))
    (report-bad-arg target-fn 'function)))

;;; Walk through combined-method / closure wrappers to find the
;;; underlying compiled function.  Pure Lisp — identical to arm-def.lisp.
(defun closure-function (fun)
  (while (and (functionp fun) (not (compiled-function-p fun)))
    (setq fun (%svref fun 2))
    (when (vectorp fun)
      (setq fun (svref fun 0))))
  fun)

;;; For use by (setf (apply ...) ...)
;;; (apply+ f butlast last) = (apply f (append butlast (list last)))
(defun apply+ (fn &rest args)
  (apply fn args))

;;; Look up a subprimitive address.  On WASM subprims are table indices
;;; managed by the microkernel; return 0 as a stub.
(defun %lookup-subprim-address (subp)
  (declare (ignore subp))
  0)

;;; ARM hard-float predicate.  Not ARM, so always NIL.
(defun arm-hard-float-p ()
  nil)

;;; Flush instruction cache for a code vector.  No-op on WASM — there
;;; is no hardware instruction cache to invalidate.
(defun %make-code-executable (codev)
  (declare (ignore codev))
  nil)

;;;=========================================================================
;;; Object access through macptr
;;;=========================================================================

;;; Read a tagged Lisp object from macptr + offset.
;;; On native backends this is a single LAP load.  On WASM the macptr
;;; holds a fixnum byte-address; use %fixnum-ref.
(defun %get-object (macptr offset)
  (%fixnum-ref (macptr->fixnum macptr) offset))

;;; Write a tagged Lisp object to macptr + offset.
(defun %set-object (macptr offset value)
  (%fixnum-set (macptr->fixnum macptr) offset value))
