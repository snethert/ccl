;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 predicates.
;;; On ARM these are fast LAP paths. On WASM they are pure Lisp fallbacks.
;;; The compiler may inline %ptr-eql and other comparison intrinsics for
;;; direct calls; these definitions handle dynamic (funcall) dispatch.

(in-package "CCL")

;;; Pre-initialize type system variables that l1-typesys.lisp defines
;;; via defvar.  On WASM, the runtime module installs compiled L1 type
;;; functions (TYPE-EXPAND, VALUES-SPECIFIER-TYPE, etc.) into the
;;; function table BEFORE l1-typesys.lafsl loads.  Those functions
;;; reference these variables through symbol value cells; if the cells
;;; are unbound we get $xwrongtype trying to GETHASH on unbound_marker.
;;; defvar won't rebind them when l1-typesys loads later.

(defvar %deftype-expanders% (make-hash-table :test #'eq))
(defvar *type-translators* (make-hash-table :test #'eq))
(defvar *builtin-type-info* (make-hash-table :test #'equal))
(defvar %builtin-type-cells% (make-hash-table :test 'equal))
(defvar *use-implementation-types* t)

;;; *type-kind-info* is defined in l1-clos-boot.lisp; used by
;;; info-type-kind which values-specifier-type-internal calls.
(defvar *type-kind-info* (make-hash-table :test #'equal))

;;; WASM-specific type cache variables (used by the #+wasm32-target
;;; version of VALUES-SPECIFIER-TYPE in l1-typesys.lisp).
(defvar *%type-cache-specs% (make-array 4096))
(defvar *%type-cache-ctypes% (make-array 4096))
(defvar *%type-cache-probes% 0)
(defvar *%type-cache-hits% 0)
(defvar *%type-cache-ncleared% 0)
(defvar *%type-cache-locked* nil)

;;; Bootstrap guard: L1 TYPEP checks this before falling through to
;;; %TYPEP/specifier-type.  Set to T from JS after l1-typesys.lafsl loads.
(defvar *wasm-type-system-ready* nil)

;;; Pre-initialize FORMAT machinery.  l1-format.lisp defines these via
;;; defparameter (which will overwrite), but the runtime module's compiled
;;; sub-format/bootstrapping-format reference them through symbol value
;;; cells.  If cold-load drain hasn't run l1-format's defparameter yet,
;;; these prevent unbound_marker crashes.
(defvar *format-char-table* (make-array 128 :initial-element nil))
(defvar *format-original-arguments* nil)
(defvar *format-arguments* nil)
(defvar *format-control-string* "")
(defvar *format-index* 0)
(defvar *format-length* 0)
(defvar *format-pprint* nil)
(defvar *format-justification-semi* nil)

;;; Bootstrap stubs for stream operations that are defined in lib/streams.lisp
;;; (not cross-compiled).  The runtime module's error handler calls FORMAT,
;;; FORMAT stream=nil creates a string-output-stream, and stream cleanup
;;; calls FINISH-OUTPUT etc.  If these are UDF → error → FORMAT → recursion.
;;; Real definitions from lib/streams.lafsl replace these later.
(defun finish-output (&optional stream)
  (declare (ignore stream))
  nil)
(defun force-output (&optional stream)
  (declare (ignore stream))
  nil)
(defun clear-output (&optional stream)
  (declare (ignore stream))
  nil)

;;; Pre-register type-predicates for all types whose predicate functions
;;; are defined in level-0.  L1 TYPEP (installed by runtime module before
;;; FASL loading) checks type-predicate FIRST — if found, it short-circuits
;;; without touching %TYPEP/specifier-type/values-specifier-type.
;;; On native ARM, sysutils.lisp:init-type-predicates does this, but it
;;; runs when sysutils.lafsl loads — too late for WASM bootstrap.

(setf (type-predicate 'array) 'arrayp)
(setf (type-predicate 'base-string) 'base-string-p)
(setf (type-predicate 'bignum) 'bignump)
(setf (type-predicate 'bit-vector) 'bit-vector-p)
(setf (type-predicate 'character) 'characterp)
(setf (type-predicate 'compiled-function) 'compiled-function-p)
(setf (type-predicate 'complex) 'complexp)
(setf (type-predicate 'cons) 'consp)
(setf (type-predicate 'double-float) 'double-float-p)
(setf (type-predicate 'fixnum) 'fixnump)
(setf (type-predicate 'float) 'floatp)
(setf (type-predicate 'function) 'functionp)
;;; hash-table already registered in l0-hash.lisp
(setf (type-predicate 'integer) 'integerp)
(setf (type-predicate 'real) 'realp)
(setf (type-predicate 'list) 'listp)
(setf (type-predicate 'long-float) 'double-float-p)
(setf (type-predicate 'number) 'numberp)
(setf (type-predicate 'package) 'packagep)
(setf (type-predicate 'pathname) 'pathnamep)
(setf (type-predicate 'ratio) 'ratiop)
(setf (type-predicate 'rational) 'rationalp)
(setf (type-predicate 'short-float) 'short-float-p)
(setf (type-predicate 'signed-byte) 'integerp)
(setf (type-predicate 'simple-array) 'simple-array-p)
(setf (type-predicate 'simple-base-string) 'simple-base-string-p)
(setf (type-predicate 'simple-bit-vector) 'simple-bit-vector-p)
(setf (type-predicate 'simple-string) 'simple-string-p)
(setf (type-predicate 'simple-vector) 'simple-vector-p)
(setf (type-predicate 'single-float) 'short-float-p)
(setf (type-predicate 'string) 'stringp)
(setf (type-predicate 'base-char) 'base-char-p)
(setf (type-predicate 'structure-object) 'structurep)
(setf (type-predicate 'symbol) 'symbolp)
(setf (type-predicate 't) 'true)
(setf (type-predicate 'nil) 'false)
(setf (type-predicate 'vector) 'vectorp)

(defun eql (x y)
  "Return T if OBJ1 and OBJ2 represent the same object, otherwise NIL."
  (or (eq x y)
      (and (typep x 'double-float)
           (typep y 'double-float)
           (= x y))
      (and (typep x 'short-float)
           (typep y 'short-float)
           (= x y))
      (and (typep x 'bignum)
           (typep y 'bignum)
           (= x y))
      (and (typep x 'ratio)
           (typep y 'ratio)
           (= x y))
      (and (typep x 'complex)
           (typep y 'complex)
           (= x y))))

(defun equal (x y)
  "Return T if X and Y are EQL or if they are structured components
  whose elements are EQUAL. Strings and bit-vectors are EQUAL if they
  are the same length and have identical components. Other arrays must be
  EQ to be EQUAL.  Pathnames are EQUAL if their components are."
  (cond
    ((eql x y) t)
    ((and (consp x) (consp y))
     (and (equal (car x) (car y))
          (equal (cdr x) (cdr y))))
    ((and (stringp x) (stringp y))
     (string= x y))
    ((and (bit-vector-p x) (bit-vector-p y))
     (let ((len (length x)))
       (and (= len (length y))
            (dotimes (i len t)
              (unless (eql (aref x i) (aref y i))
                (return nil))))))
    ((and (pathnamep x) (pathnamep y))
     (hairy-equal x y))
    (t nil)))
