;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 CLOS operations.
;;; On ARM these are LAP functions that reference function-vector
;;; constants via nfn.  On WASM they are pure Lisp with explicit
;;; map/table parameters.
;;;
;;; Slot-ID structure: an istruct with (nil name index).
;;;   slot-id.index returns the numeric index used for lookup.
;;;
;;; Map/table layout (from setup-slot-lookup in l1-clos.lisp):
;;;   map: a (simple-array (unsigned-byte 8) (*)) for small classes
;;;        or (simple-array (unsigned-byte 32) (*)) for large classes.
;;;        Indexed by slot-id.index.  The value at that index is a
;;;        1-based index into table.  0 means "not found".
;;;   table: a simple-vector.  Element 0 is NIL (sentinel).
;;;        Elements 1..N are slot-definition objects.
;;;
;;; The setup-slot-lookup mechanism in l1-clos.lisp needs a
;;; WASM-specific path to create closures binding map/table/class
;;; rather than gvector-based clones.

(in-package "CCL")


;;; ---------------------------------------------------------------
;;; Slot-ID lookup: map a slot-id to a slot-definition or NIL.
;;; table is a simple-vector of slot-definitions (element 0 = nil).
;;; ---------------------------------------------------------------

;;; For a "small" map (vector of (unsigned-byte 8)).
;;; Linear search: index into map by slot-id.index.
;;; If in bounds, the byte is a 1-based index into table.
;;; If out of bounds or the byte is 0, return nil (table element 0).
(defun %small-map-slot-id-lookup (slot-id table)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map))
         (table-index 0))
    (declare (fixnum index map-len table-index))
    (when (< index map-len)
      (setq table-index (aref map index)))
    (if (eql table-index 0)
      nil
      (%svref defs table-index))))

;;; For a "large" map (vector of (unsigned-byte 32)).
;;; Same algorithm; the map uses 32-bit entries for classes
;;; with 255 or more slots.
(defun %large-map-slot-id-lookup (slot-id table)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map))
         (table-index 0))
    (declare (fixnum index map-len table-index))
    (when (< index map-len)
      (setq table-index (aref map index)))
    (if (eql table-index 0)
      nil
      (%svref defs table-index))))


;;; ---------------------------------------------------------------
;;; Slot-ID value access: look up slot-id, return slot value.
;;; On hit: call %maybe-std-slot-value-using-class(class, instance, slotd).
;;; On miss: call %slot-id-ref-missing(instance, slot-id).
;;; ---------------------------------------------------------------

;;; Small map version.
(defun %small-slot-id-value (instance slot-id table)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map)))
    (declare (fixnum index map-len))
    (if (< index map-len)
      (let ((table-index (aref map index)))
        (declare (fixnum table-index))
        (if (not (eql table-index 0))
          (let ((slotd (%svref defs table-index)))
            (%maybe-std-slot-value-using-class
             (class-of instance) instance slotd))
          (%slot-id-ref-missing instance slot-id)))
      (%slot-id-ref-missing instance slot-id))))

;;; Large map version.
(defun %large-slot-id-value (instance slot-id table)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map)))
    (declare (fixnum index map-len))
    (if (< index map-len)
      (let ((table-index (aref map index)))
        (declare (fixnum table-index))
        (if (not (eql table-index 0))
          (let ((slotd (%svref defs table-index)))
            (%maybe-std-slot-value-using-class
             (class-of instance) instance slotd))
          (%slot-id-ref-missing instance slot-id)))
      (%slot-id-ref-missing instance slot-id))))


;;; ---------------------------------------------------------------
;;; Set slot-ID value: look up slot-id, set slot value.
;;; On hit: call %maybe-std-setf-slot-value-using-class(class, instance, slotd, new-value).
;;; On miss: call %slot-id-set-missing(instance, slot-id, new-value).
;;; ---------------------------------------------------------------

;;; Small map version.
(defun %small-set-slot-id-value (instance slot-id table new-value)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map)))
    (declare (fixnum index map-len))
    (if (< index map-len)
      (let ((table-index (aref map index)))
        (declare (fixnum table-index))
        (if (not (eql table-index 0))
          (let ((slotd (%svref defs table-index)))
            (%maybe-std-setf-slot-value-using-class
             (class-of instance) instance slotd new-value))
          (%slot-id-set-missing instance slot-id new-value)))
      (%slot-id-set-missing instance slot-id new-value))))

;;; Large map version.
(defun %large-set-slot-id-value (instance slot-id table new-value)
  (let* ((map (uvref table 0))
         (defs (uvref table 1))
         (index (slot-id.index slot-id))
         (map-len (length map)))
    (declare (fixnum index map-len))
    (if (< index map-len)
      (let ((table-index (aref map index)))
        (declare (fixnum table-index))
        (if (not (eql table-index 0))
          (let ((slotd (%svref defs table-index)))
            (%maybe-std-setf-slot-value-using-class
             (class-of instance) instance slotd new-value))
          (%slot-id-set-missing instance slot-id new-value)))
      (%slot-id-set-missing instance slot-id new-value))))


;;; ---------------------------------------------------------------
;;; Slot-ID access stubs for WASM from-scratch cold boot.
;;; On native CCL these are defined in l1-clos-boot.lisp and dispatch
;;; through the instance's class wrapper.  For the WASM from-scratch
;;; build, CLOS infrastructure (wrappers, class-of, generic dispatch)
;;; is not yet set up when cold-boot-init runs, so we provide no-op
;;; stubs.  Level-1 will override these with real implementations.
;;;
;;; The compiler optimizer transforms (SETF (SLOT-VALUE obj 'name) val)
;;; into (SET-SLOT-ID-VALUE obj (ensure-slot-id 'name) val), and
;;; cold-boot-init may execute code compiled with that expansion.
;;; ---------------------------------------------------------------

(defun slot-id-value (instance slot-id)
  (declare (ignore instance slot-id))
  nil)

(defun set-slot-id-value (instance slot-id value)
  (declare (ignore instance slot-id))
  value)


;;; ---------------------------------------------------------------
;;; Instance wrapper / slots stubs for WASM from-scratch cold boot.
;;; The compiler macro for INSTANCE-CLASS-WRAPPER (optimizers.lisp)
;;; expands to a typecode check: for subtag-instance it inlines
;;; INSTANCE.CLASS-WRAPPER; for everything else it calls
;;; NON-STANDARD-INSTANCE-CLASS-WRAPPER.  Similarly INSTANCE-SLOTS
;;; expands to call %NON-STANDARD-INSTANCE-SLOTS.
;;; These functions are normally defined in l1-clos-boot.lisp (level-1),
;;; which is not yet loaded during cold boot.
;;;
;;; Returning nil from non-standard-instance-class-wrapper causes
;;; XNOTFUN because callers funcall wrapper slots (e.g.
;;; %wrapper-slot-id-value at slot 8).  So we return a dummy wrapper
;;; whose funcallable slots point to safe no-op functions.
;;;
;;; Wrapper layout (class-wrapper istruct, 13 slots including type):
;;;   0: type marker ('class-wrapper)
;;;   1: %wrapper-hash-index
;;;   2: %wrapper-class
;;;   3: %wrapper-instance-slots
;;;   4: %wrapper-class-slots
;;;   5: %wrapper-slot-id->slotd
;;;   6: %wrapper-slot-id-map
;;;   7: %wrapper-slot-definition-table
;;;   8: %wrapper-slot-id-value       (funcalled: instance slot-id → value)
;;;   9: %wrapper-set-slot-id-value   (funcalled: instance slot-id value → value)
;;;  10: %wrapper-cpl-bits
;;;  11: %wrapper-cpl-ordinal
;;;  12: %wrapper-unused
;;; ---------------------------------------------------------------

;;; Dummy wrapper for cold-boot.  Slot 8 references SLOT-ID-VALUE
;;; (our no-op stub above), slot 9 references SET-SLOT-ID-VALUE.
(defvar *cold-boot-dummy-wrapper*
  (%istruct 'class-wrapper
    0                             ; 1: hash-index
    nil                           ; 2: class
    nil                           ; 3: instance-slots
    nil                           ; 4: class-slots
    nil                           ; 5: slot-id->slotd
    nil                           ; 6: slot-id-map
    nil                           ; 7: slot-definition-table
    #'slot-id-value               ; 8: slot-id-value  (instance slot-id → nil)
    #'set-slot-id-value           ; 9: set-slot-id-value (instance slot-id val → val)
    nil                           ; 10: cpl-bits
    0                             ; 11: cpl-ordinal
    nil))                         ; 12: unused

;;; Return the dummy wrapper for any non-standard instance.
;;; class-of causes infinite recursion during cold boot.
;;; Level-1 (l1-clos-boot.lisp) replaces this.
(defun non-standard-instance-class-wrapper (instance)
  (declare (ignore instance))
  *cold-boot-dummy-wrapper*)

;;; For non-standard instances, return nil (no accessible slots).
;;; The real version (l1-clos-boot.lisp) handles macptrs and GFs.
(defun %non-standard-instance-slots (instance typecode)
  (declare (ignore instance typecode))
  nil)


;;; ---------------------------------------------------------------
;;; Generic function dispatch trampolines.
;;; ---------------------------------------------------------------

;;; Trampoline for funcallable instances.
;;; The GF's dcode function is at gf.dcode.  Tail-call it.
(defun funcallable-trampoline (gf &rest args)
  (apply (gf.dcode gf) args))

;;; Error trampoline for uninitialized funcallable instances.
;;; Signals $XNOFINFUNCTION with the GF as context.
(defun unset-fin-trampoline (gf &rest args)
  (declare (ignore args))
  (%err-disp $xnofinfunction gf))

;;; One-argument GF discrimination stub.
;;; On ARM this prepends the dispatch-table and tail-calls dcode.
;;; On WASM, return nil; GF dispatch is handled by the runtime.
(defun gag-one-arg (arg)
  (declare (ignore arg))
  nil)

;;; Two-argument GF discrimination stub.
(defun gag-two-arg (arg1 arg2)
  (declare (ignore arg1 arg2))
  nil)

;;; Full GF prototype.
;;; On ARM this is an nfunction with LAP that gathers &lexpr args,
;;; sets up the lexpr-return protocol, and tail-calls dcode with
;;; (args, dispatch-table).  On WASM, a placeholder whose code-vector
;;; is shared across all GF clones.
(defparameter *gf-proto*
  #'(lambda (&rest args)
      (declare (ignore args))
      (error "GF prototype called directly -- should be cloned")))

;;; Combined-method prototype.
;;; On ARM this gathers &lexpr args and calls the combined-method's
;;; dcode with (args, thing).  Placeholder for WASM.
(defparameter *cm-proto*
  #'(lambda (&rest args)
      (declare (ignore args))
      (error "CM prototype called directly -- should be cloned")))
