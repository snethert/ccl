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
