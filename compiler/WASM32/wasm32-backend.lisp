;;; First production backend slice. Unsupported acode is refused, never sent to a native pass 2.
(defpackage "WASM32-COMPILER" (:use "CL"))
(defpackage "WASM32-OS" (:use))
(in-package "WASM32-COMPILER")
(defvar *b-callable-metadata* nil)
;; D2 template mode changes only the imported memory's shared bit. It is
;; dynamically bound around compilation, including every nested module.
(defvar *wasm32-template-memory* nil)
(defvar *pool-layouts* nil)
(defvar *pool-current* nil)
(defvar *module-result-tag* nil)
(defvar *module-name* nil)
(defvar *required-vars* nil)
(defvar *temporary-count* 0)
(defvar *cons-used* nil)
(define-condition unsupported-wasm32-code (error)
  ((operation :initarg :operation :reader unsupported-operation))
  (:report (lambda (c s) (format s "WASM32 lowering not implemented: ~s" (unsupported-operation c)))))
(defun refuse (operation) (error 'unsupported-wasm32-code :operation operation))
(defvar *primitive-signature* nil)
(defvar *b-call-links* nil)
(defvar *b-allocation-retry* nil)
(defvar *b-integer-service* nil)
(defvar *b-float-service* nil)
(defvar *b-float-safety* 1)
(defvar *b-call-mode* nil)
(defun wasm32-pass2 (afunc &rest ignored)
  (declare (ignore ignored))
  (unless *module-result-tag* (refuse :native-fasl-publication))
  (when *b-call-mode* (return-from wasm32-pass2 (b-call-pass2 afunc)))
  (when *primitive-signature* (return-from wasm32-pass2 (primitive-pass2 afunc)))
  (let* ((ir (ccl::afunc-acode afunc)) (args (ccl::acode-operands ir)))
    (unless (and (eq (ccl::acode-operator-name (ccl::acode-operator ir)) 'ccl::lambda-list)
                 (null (second args)) (null (third args)) (null (fourth args))
                 (equal (fifth args) '(nil nil)))
      (refuse :lambda-list))
    (let* ((*required-vars* (first args))
           (*temporary-count* 0) (*cons-used* nil)
           (body (emit-expression (sixth args)))
           (arity (length *required-vars*))
           (wat (format nil "(module~% (import ~s ~s (memory 1 32769~a))~% (import ~s ~s (global $tcr i32))~%~a (func (export ~s) (param $self i32) (param $nargs i32) (result i32 i32) (local $value i32)~a~%  (if (i32.ne (local.get $nargs) (i32.const ~d)) (then unreachable))~%  (local.set $value ~a)~%  (i32.store (i32.load offset=~d (global.get $tcr)) (local.get $value))~%  (i32.store offset=~d (global.get $tcr) (i32.const 1))~%  (local.get $value) (i32.const 1)))~%"
             "env" "memory" (if *wasm32-template-memory* "" " shared") "env" "tcr"
             (if *cons-used* " (import \"env\" \"type_error\" (tag $type_error (param i32 i32)))" "")
             "entry" (with-output-to-string (s) (dotimes (i *temporary-count*) (format s " (local $tmp~d i32)" i)))
             arity body wasm32::tcr.mv_base wasm32::tcr.mv_count)))
      (throw *module-result-tag* (list :version 1 :name *module-name* :arity arity :wat wat)))))
(defun emit-expression (ir)
  (unless (ccl::acode-p ir) (refuse :malformed-acode))
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
        (args (ccl::acode-operands ir)))
    (case op
      ((nil) (format nil "(i32.const ~d)" wasm32::canonical-nil-value))
      ((t) (format nil "(i32.const ~d)" wasm32::canonical-t-value))
      (ccl::fixnum
       (let ((n (first args)))
         (unless (<= wasm32::target-most-negative-fixnum n wasm32::target-most-positive-fixnum) (refuse :fixnum-range))
         (format nil "(i32.const ~d)" (ash n wasm32::fixnumshift))))
      (ccl::immediate
       (cond ((null (first args)) (format nil "(i32.const ~d)" wasm32::canonical-nil-value))
             ((eq (first args) t) (format nil "(i32.const ~d)" wasm32::canonical-t-value))
             (t (refuse :heap-constant))))
      (ccl::lexical-reference
       (let ((index (position (first args) *required-vars* :test #'eq)))
         (unless index (refuse :non-argument-lexical))
         (format nil "(i32.load offset=~d (i32.load offset=~d (global.get $tcr)))" (* 4 index) wasm32::tcr.vsp)))
      ((car cdr ccl::%car ccl::%cdr)
       (emit-cons-read (member op '(car ccl::%car)) (first args)))
      ((rplaca rplacd ccl::%rplaca ccl::%rplacd)
       (emit-cons-write (member op '(rplaca ccl::%rplaca)) (first args) (second args)))
      (ccl::if
       (format nil "(if (result i32) (i32.ne ~a (i32.const ~d)) (then ~a) (else ~a))"
         (emit-expression (first args)) wasm32::canonical-nil-value
         (emit-expression (second args)) (emit-expression (third args))))
      (t (refuse op)))))
;;; Each nested operand owns a separate local. No calls, polls or allocation
;;; occur while these unspilled tagged temporaries are live in this slice.
(defun temporary () (prog1 (format nil "$tmp~d" *temporary-count*) (incf *temporary-count*)))
(defun cons-check (local expected)
  (format nil "(if (i32.ne (i32.and (local.get ~a) (i32.const ~d)) (i32.const ~d)) (then (throw $type_error (local.get ~a) (i32.const ~d))))"
    local wasm32::fulltagmask wasm32::fulltag-cons local expected))
(defun emit-cons-read (car-p operand)
  (setq *cons-used* t)
  (let* ((ptr (temporary)) (value (emit-expression operand))
         (offset (if car-p wasm32::cons.car wasm32::cons.cdr)))
    (format nil "(block (result i32) (local.set ~a ~a) (if (result i32) (i32.eq (local.get ~a) (i32.const ~d)) (then (i32.const ~d)) (else ~a (i32.load (i32.add (local.get ~a) (i32.const ~d))))))"
      ptr value ptr wasm32::canonical-nil-value wasm32::canonical-nil-value
      (cons-check ptr 1) ptr offset)))
(defun emit-cons-write (car-p pair value)
  (setq *cons-used* t)
  (let* ((ptr (temporary)) (new (temporary))
         (pair-code (emit-expression pair)) (value-code (emit-expression value))
         (offset (if car-p wasm32::cons.car wasm32::cons.cdr)))
    (format nil "(block (result i32) (local.set ~a ~a) (local.set ~a ~a) (if (i32.eq (local.get ~a) (i32.const ~d)) (then (throw $type_error (local.get ~a) (i32.const 2)))) ~a (i32.store (i32.add (local.get ~a) (i32.const ~d)) (local.get ~a)) (local.get ~a))"
      ptr pair-code new value-code ptr wasm32::canonical-nil-value ptr
      (cons-check ptr 2) ptr offset new ptr)))
;;; The next unused three-bit CPU discriminator; no existing target changes.
(defconstant ccl::platform-cpu-wasm32 (ash 4 3))
(defconstant ccl::platform-os-wasm 7)
(defvar *backend*
  (ccl::make-backend :name :wasm32 :num-arg-regs 0 :target-arch-name :wasm32
    :target-arch wasm32::*target-arch* :target-platform (logior ccl::platform-cpu-wasm32 ccl::platform-os-wasm ccl::platform-word-size-32) :target-os :wasm
    :target-specific-features '(:wasm-target :wasm32-target :32-bit-target :little-endian-target)
    :target-fasl-pathname (make-pathname :type "w32fsl")
    :p2-dispatch (make-array 1024 :initial-element nil) :p2-compile 'wasm32-pass2 :p2-vinsn-templates (make-hash-table :test #'eq)
    :target-foreign-type-data (ccl::make-ftd :interface-package-name "WASM32-OS" :attributes '(:bits-per-word 32) :ff-call-expand-function (lambda (&rest args) (declare (ignore args)) (refuse :native-ffi-excluded)))))
(when (and (ccl::find-backend :wasm32) (not (eq *backend* (ccl::find-backend :wasm32))))
  (error "Conflicting WASM32 backend"))
(when (find (ccl::backend-target-platform *backend*) ccl::*known-backends* :key #'ccl::backend-target-platform :test #'=)
  (unless (member *backend* ccl::*known-backends*) (error "WASM32 platform discriminator collision")))
(pushnew *backend* ccl::*known-backends* :key #'ccl::backend-name)
(defun call-with-target (thunk)
  (let* ((ccl::*target-backend* *backend*) (ccl::*fasl-target* :wasm32)
         (*features* (ccl::setup-target-features *backend* *features*)))
    (ccl::with-cross-compilation-target (:wasm32) (funcall thunk))))
;;; Until target macro/helper qualification is integrated, the source API admits
;;; only the syntax this leaf slice implements. Pass-2 refusal alone is too late:
;;; a host compiler macro can fold an unsupported call to an apparently safe IR
;;; constant. This is a declared subset boundary, not an implementation of TYPEP.
(defun validate-leaf-source (form)
  (let ((budget 4096) (active (make-hash-table :test #'eq)))
    (labels ((items (x)
               (let ((seen (make-hash-table :test #'eq)) (result nil))
                 (loop while (consp x) do
                   (when (or (gethash x seen) (minusp (decf budget))) (refuse :source-shape))
                   (setf (gethash x seen) t) (push (car x) result) (setq x (cdr x)))
                 (when x (refuse :source-shape)) (nreverse result)))
             (literal (x)
               (or (null x) (eq x t)
                   (and (integerp x) (<= wasm32::target-most-negative-fixnum x wasm32::target-most-positive-fixnum))))
             (walk (x vars depth)
               (when (or (> depth 128) (minusp (decf budget))) (refuse :source-shape))
               (cond ((literal x) t)
                     ((and (symbolp x) (member x vars :test #'eq)) t)
                     ((consp x)
                      (when (gethash x active) (refuse :source-shape))
                      (setf (gethash x active) t)
                      (unwind-protect
                        (let ((xs (items x)))
                          (cond ((and (eq (car xs) 'if) (member (length xs) '(3 4)))
                                 (dolist (part (cdr xs)) (walk part vars (1+ depth))))
                                ((and (member (car xs) '(car cdr)) (= (length xs) 2))
                                 (walk (second xs) vars (1+ depth)))
                                ((and (member (car xs) '(rplaca rplacd)) (= (length xs) 3))
                                 (walk (second xs) vars (1+ depth)) (walk (third xs) vars (1+ depth)))
                                ((and (eq (car xs) 'quote) (= (length xs) 2) (literal (second xs))) t)
                                (t (refuse :source-subset))))
                        (remhash x active)))
                     (t (refuse :source-subset)))))
      (let ((parts (items form)))
        (unless (and (= (length parts) 3) (eq (first parts) 'lambda)) (refuse :source-subset))
        (let ((vars (items (second parts))))
          (unless (and (every (lambda (v) (and (symbolp v) v (not (eq v t)) (not (keywordp v))
                                                (not (member v lambda-list-keywords)))) vars)
                       (= (length vars) (length (remove-duplicates vars :test #'eq))))
            (refuse :source-subset))
          (walk (third parts) vars 0))))))
(defun compile-module (source-text name)
  (unless (and (stringp source-text) (stringp name)) (error "Source and logical name must be strings"))
  (call-with-target
    (lambda ()
      (let* ((*module-result-tag* (gensym "WASM32-PASS2")) (*module-name* name)
             (*package* (find-package "WASM32-COMPILER")) (*read-eval* nil))
        (multiple-value-bind (form end) (read-from-string source-text)
          (unless (every (lambda (c) (find c '(#\Space #\Tab #\Newline #\Return))) (subseq source-text end))
            (error "Trailing source after the lambda"))
          (validate-leaf-source form)
          (catch *module-result-tag*
            (ccl::compile-named-function form :name name :target :wasm32 :policy ccl::*default-compiler-policy*)
            (error "WASM32 pass 2 failed to publish a module")))))))
(provide "WASM32-BACKEND")

;;; Typed internal primitives. These use raw Wasm parameters, not Lisp B's
;;; node stack. Static representation checking happens on the real front-end
;;; IR before any code is published. All checked failures precede writes.
(defparameter *primitive-operations*
  '((%box-s32 (:s32) :node) (%unbox-fixnum (:node) :s32)
    (%address-fixnum (:address) :node) (%fixnum-address (:node) :address)
    (%tag-misc (:address) :node) (%untag-misc (:node) :address)
    (%effective-address (:address :s32) :address)
    (%header-word (:node) :u32) (%array-bytes (:u32 :u32) :u32)
    (%issue-code (:address) :code-id) (%validate-code (:node :address) :code-id)
    (%code-index (:code-id) :u32)
    (%validate-slot (:u32 :u32 :u32 :u32 :address) :slot)
    (%slot-index (:slot) :u32)))
(defun primitive-signature (name) (assoc name *primitive-operations* :test #'eq))
(defun primitive-check (condition reason)
  (format nil "(if ~a (then (throw $conversion_error (i32.const ~d))))" condition reason))
(defun primitive-span (ptr bytes)
  (primitive-check
    (format nil "(i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.const ~d)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" ptr bytes) 4))
(defun primitive-op (name values)
  ;; Materialize operands exactly once, left to right, in disjoint locals.
  (let* ((locals (mapcar (lambda (v) (declare (ignore v)) (temporary)) values))
         (v (mapcar (lambda (x) (format nil "(local.get ~a)" x)) locals))
         (a (first v)) (b (second v)) (c (third v)) (d (fourth v)) (e (fifth v)))
    (with-output-to-string (s)
      (write-string "(block (result i32) " s)
      (loop for local in locals for value in values do (format s "(local.set ~a ~a) " local value))
      (labels ((check (condition reason) (write-string (primitive-check condition reason) s))
               (word (base offset) (format nil "(i32.load offset=~d ~a)" offset base)))
        (case name
          (%box-s32
           (check (format nil "(i32.or (i32.lt_s ~a (i32.const -536870912)) (i32.gt_s ~a (i32.const 536870911)))" a a) 1)
           (format s "(i32.shl ~a (i32.const 2))" a))
          (%unbox-fixnum
           (check (format nil "(i32.and ~a (i32.const 3))" a) 2)
           (format s "(i32.shr_s ~a (i32.const 2))" a))
          (%address-fixnum
           (check (format nil "(i32.gt_u ~a (i32.const 536870911))" a) 1)
           (format s "(i32.shl ~a (i32.const 2))" a))
          (%fixnum-address
           (check (format nil "(i32.and ~a (i32.const 3))" a) 2)
           (check (format nil "(i32.lt_s ~a (i32.const 0))" a) 1)
           (format s "(i32.shr_u ~a (i32.const 2))" a))
          (%tag-misc
           (check (format nil "(i32.and ~a (i32.const 7))" a) 3)
           (format s "(i32.add ~a (i32.const 6))" a))
          ((%untag-misc %header-word)
           (check (format nil "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" a) 2)
           (let ((base (format nil "(i32.sub ~a (i32.const 6))" a)))
             (if (eq name '%header-word)
               (progn (write-string (primitive-span base 4) s) (format s "(i32.load ~a)" base))
               (write-string base s))))
          (%effective-address
           (format s "(local.set $wide (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_s ~a)))" a b)
           (check "(i64.gt_u (local.get $wide) (i64.const 4294967295))" 4)
           (write-string "(i32.wrap_i64 (local.get $wide))" s))
          (%array-bytes
           (check (format nil "(i32.ge_u ~a (i32.const 16777216))" a) 1)
           (check (format nil "(i32.eqz ~a)" b) 1)
           (format s "(local.set $wide (i64.mul (i64.extend_i32_u ~a) (i64.extend_i32_u ~a)))" a b)
           (check "(i64.gt_u (local.get $wide) (i64.const 4294967295))" 4)
           (write-string "(i32.wrap_i64 (local.get $wide))" s))
          ((%issue-code %validate-code)
           (let* ((registry (if (eq name '%issue-code) a b))
                  (first (word registry 0)) (next (word registry 4)) (limit (word registry 8)))
             (write-string (primitive-span registry 12) s)
             (check (format nil "(i32.or (i32.gt_u ~a ~a) (i32.or (i32.gt_u ~a ~a) (i32.gt_u ~a (i32.const 536870912))))" first next next limit limit) 7)
             (if (eq name '%issue-code)
               (progn
                 (check (format nil "(i32.ge_u ~a ~a)" next limit) 6)
                 (format s "(local.set $scratch ~a) (i32.store offset=4 ~a (i32.add (local.get $scratch) (i32.const 1))) (i32.shl (local.get $scratch) (i32.const 2))" next registry))
               (progn
                 (check (format nil "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" a a) 2)
                 (format s "(local.set $scratch (i32.shr_u ~a (i32.const 2)))" a)
                 (check (format nil "(i32.or (i32.lt_u (local.get $scratch) ~a) (i32.ge_u (local.get $scratch) ~a))" first next) 5)
                 (write-string a s)))))
          (%code-index (format s "(i32.shr_u ~a (i32.const 2))" a))
          (%validate-slot
           ;; Registry: capacity, reserved prefix, then (signature, role) rows.
           ;; The imported table's actual size is authoritative for capacity.
           (write-string (primitive-span e 8) s)
           (check (format nil "(i32.ne ~a (i32.const 3))" b) 9)
           (check (format nil "(i32.or (i32.gt_u ~a (table.size $slots)) (i32.gt_u ~a ~a))" (word e 0) (word e 4) (word e 0)) 7)
           (check (format nil "(i32.ge_u ~a ~a)" a (word e 0)) 7)
           (check (format nil "(i32.lt_u ~a ~a)" a (word e 4)) 8)
           (format s "(local.set $wide (i64.add (i64.extend_i32_u ~a) (i64.add (i64.const 8) (i64.mul (i64.extend_i32_u ~a) (i64.const 8)))))" e a)
           (check "(i64.gt_u (i64.add (local.get $wide) (i64.const 8)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" 4)
           (write-string "(local.set $scratch (i32.wrap_i64 (local.get $wide)))" s)
           (check (format nil "(i32.or (i32.eqz ~a) (i32.ne ~a ~a))" c (word "(local.get $scratch)" 0) c) 10)
           (check (format nil "(i32.or (i32.eqz ~a) (i32.ne ~a ~a))" d (word "(local.get $scratch)" 4) d) 11)
           (check (format nil "(ref.is_null (table.get $slots ~a))" a) 12)
           (write-string a s))
          (%slot-index (write-string a s))
          (t (refuse :primitive-operation))))
      (write-char #\) s))))
(defun primitive-expression (ir)
  (unless (ccl::acode-p ir) (refuse :primitive-ir))
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir))) (args (ccl::acode-operands ir)))
    (case op
      (ccl::lexical-reference
       (let ((n (position (first args) *required-vars* :test #'eq)))
         (unless n (refuse :primitive-variable))
         (values (format nil "(local.get $arg~d)" n) (nth n (first *primitive-signature*)))))
      (ccl::call
       (let* ((callee (first args)) (arguments (second args))
              (name (and (ccl::acode-p callee)
                         (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)
                         (first (ccl::acode-operands callee))))
              (sig (primitive-signature name)))
         (unless (and sig (null (second arguments)) (= (length (first arguments)) (length (second sig))))
           (refuse :primitive-call))
         (let ((codes nil))
           (loop for arg in (first arguments) for kind in (second sig) do
             (multiple-value-bind (code actual) (primitive-expression arg)
               (unless (eq kind actual) (refuse (list :representation name kind actual)))
               (push code codes)))
           (values (primitive-op name (nreverse codes)) (third sig)))))
      (t (refuse (list :primitive-ir op))))))
(defun primitive-pass2 (afunc)
  (let* ((ir (ccl::afunc-acode afunc)) (args (ccl::acode-operands ir)))
    (unless (and (eq (ccl::acode-operator-name (ccl::acode-operator ir)) 'ccl::lambda-list)
                 (null (second args)) (null (third args)) (null (fourth args)) (equal (fifth args) '(nil nil))
                 (= (length (first args)) (length (first *primitive-signature*)))) (refuse :primitive-lambda))
    (let ((*required-vars* (first args)) (*temporary-count* 0))
      (multiple-value-bind (body kind) (primitive-expression (sixth args))
        (unless (eq kind (second *primitive-signature*)) (refuse :primitive-result))
        (throw *module-result-tag*
          (list :version 1 :name *module-name* :abi :typed-internal :signature *primitive-signature*
                :wat (format nil "(module (import ~s ~s (memory 1 32769~a)) (import ~s ~s (table $slots 0 funcref)) (import ~s ~s (tag $conversion_error (param i32))) (func (export ~s) ~a (result i32) (local $wide i64) (local $scratch i32) ~a ~a))~%"
                       "env" "memory" (if *wasm32-template-memory* "" " shared") "env" "slots" "env" "conversion_error" "entry"
                       (with-output-to-string (s) (dotimes (i (length *required-vars*)) (format s "(param $arg~d i32)" i)))
                       (with-output-to-string (s) (dotimes (i *temporary-count*) (format s "(local $tmp~d i32)" i))) body)))))))
(defun compile-primitive-module (source-text name argument-kinds result-kind)
  (let ((kinds '(:s32 :u32 :node :address :code-id :slot)))
    ;; Code IDs and slots may only be produced by checked operations, never
    ;; admitted as unvalidated entry parameters.
    (unless (and (every (lambda (x) (member x '(:s32 :u32 :node :address))) argument-kinds)
                 (member result-kind kinds)) (refuse :primitive-signature)))
  (call-with-target
    (lambda ()
      (let* ((*primitive-signature* (list argument-kinds result-kind))
             (*module-result-tag* (gensym "WASM32-PRIMITIVE")) (*module-name* name)
             (*package* (find-package "WASM32-COMPILER")) (*read-eval* nil))
        (multiple-value-bind (form end) (read-from-string source-text)
          (unless (every (lambda (c) (find c '(#\Space #\Tab #\Newline #\Return))) (subseq source-text end))
            (refuse :primitive-source))
          ;; Bounded, no macro/control/type declarations admitted. All calls
          ;; remain ordinary acode CALLs to this exact private symbol set.
          (let ((budget 4096))
            (labels ((items (x)
                       (let ((seen (make-hash-table :test #'eq)) (out nil))
                         (loop while (consp x) do
                           (when (or (gethash x seen) (minusp (decf budget))) (refuse :primitive-source))
                           (setf (gethash x seen) t) (push (car x) out) (setq x (cdr x)))
                         (when x (refuse :primitive-source)) (nreverse out)))
                     (walk (x vars depth)
                       (when (or (> depth 128) (minusp (decf budget))) (refuse :primitive-source))
                       (unless (member x vars :test #'eq)
                         (let* ((xs (items x)) (sig (primitive-signature (first xs))))
                           (unless (and sig (= (length xs) (1+ (length (second sig))))) (refuse :primitive-source))
                           (dolist (v (cdr xs)) (walk v vars (1+ depth))))) t))
              (let* ((parts (items form)) (vars (items (second parts))))
                (unless (and (= (length parts) 3) (eq (first parts) 'lambda)
                             (= (length vars) (length argument-kinds))
                             (every (lambda (v) (and (symbolp v) v (not (constantp v)) (not (member v lambda-list-keywords)))) vars)
                             (= (length vars) (length (remove-duplicates vars))))
                  (refuse :primitive-source))
                (walk (third parts) vars 0))))
          (catch *module-result-tag*
            (ccl::compile-named-function form :name name :target :wasm32 :policy ccl::*default-compiler-policy*)
            (refuse :primitive-no-output)))))))

;;; First B call unit: required arguments, ordered evaluation and complete
(defstruct b-raw-code text)
(defvar *b-condition-used* nil)
(defvar *b-restart-used* nil)
(defvar *b-restart-names* nil)
(defvar *b-producer-target* nil)
;;; multiple values, owned allocation and lexical closures. No collection or
;;; tail-call claim in this slice.
(defvar *b-stack-closure* nil)
(defvar *b-tail-position* nil)
(defvar *b-function-vars* nil)
(defvar *b-environments* nil)
(defvar *b-captured* nil)
(defvar *b-functions* nil)
(defvar *b-inherited* nil)
(defvar *b-code-imports* nil)
(defvar *b-imports* nil)
(defvar *b-bound-vars* nil)
(defvar *b-keywords* nil)
(defvar *b-symbols* nil)
(defvar *b-special-names* nil)
(defun b-symbol (name)
  (when *bootstrap-front-end*
    (pushnew name *bootstrap-callees*)
    (return-from b-symbol (bootstrap-symbol name)))
  (let ((entry (assoc name *b-call-links* :test #'eq)))
    (unless entry (refuse :b-symbol-identity))
    (pushnew (second entry) *b-symbols* :test #'equal)
    (b-wat "(global.get $symbol_~a)" (second entry))))
(defun b-keyword (key)
  (when *bootstrap-front-end*
    (return-from b-keyword (bootstrap-symbol key)))
  (unless (keywordp key) (refuse :b-keyword-identity))
  (let ((name (string-downcase (symbol-name key))))
    (unless (and (string= (symbol-name key) (string-upcase name))
                 (<= 1 (length name) 64)
                 (every (lambda (c) (find c "abcdefghijklmnopqrstuvwxyz0123456789_-")) name))
      (refuse :b-keyword-name))
    (pushnew name *b-keywords* :test #'equal)
    (b-wat "(global.get $key_~a)" name)))
(defun b-special-p (var)
  (and var (logbitp ccl::$vbitspecial (ccl::nx-var-bits var))))
(defun b-special-symbol (symbol)
  (when *bootstrap-front-end*
    (return-from b-special-symbol (bootstrap-symbol symbol)))
  (let ((pair (assoc symbol '((ccl::*interrupt-level* . "interrupt_level") (ccl::%wasm-gc-service% . "gc_service") (ccl::%wasm-interrupt-service% . "interrupt_service")))))
    (when pair (pushnew (cdr pair) *b-symbols* :test #'equal)
      (return-from b-special-symbol (b-wat "(global.get $symbol_~a)" (cdr pair)))))
  (when (eq symbol '*debugger-hook*)
    (pushnew "debugger_hook" *b-symbols* :test #'equal)
    (return-from b-special-symbol "(global.get $symbol_debugger_hook)"))
  (when (eq symbol 'ccl::%restarts%)
    (pushnew "condition_restarts" *b-symbols* :test #'equal)
    (return-from b-special-symbol "(global.get $symbol_condition_restarts)"))
  (when (eq symbol 'ccl::%handlers%)
    (pushnew "condition_handlers" *b-symbols* :test #'equal)
    (return-from b-special-symbol "(global.get $symbol_condition_handlers)"))
  (unless (member symbol *b-special-names* :test #'eq) (refuse :b-undeclared-special))
  (unless (eq (symbol-package symbol) (find-package "WASM32-COMPILER")) (refuse :b-special-package))
  (let ((name (string-downcase (symbol-name symbol))))
    (unless (and (string= (symbol-name symbol) (string-upcase name))
                 (<= 1 (length name) 64)
                 (every (lambda (c) (find c "abcdefghijklmnopqrstuvwxyz0123456789_-")) name))
      (refuse :b-special-name))
    (pushnew name *b-symbols* :test #'equal)
    (b-wat "(global.get $symbol_~a)" name)))
(defun b-special-bind (var code)
  (b-bind-symbol (b-special-symbol (ccl::var-name var)) code))
(defun b-bind-symbol (symbol code)
 (if *b-allocation-retry* (progn 
  (let ((value (temporary)) (base (temporary)) (slot (temporary)))
    (with-output-to-string (s)
      ;; Stage in the eventual binding record before vector growth can collect.
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top))" value code base)
      (write-string (b-reserve-runtime "(i64.const 32)") s)
      (write-string (b-runtime-roots (b-at (b-local base) 8) "(i32.const 2)") s)
      (format s "(i32.store offset=16 (local.get ~a) ~a) (i32.store offset=20 (local.get ~a) (local.get ~a)) (local.set ~a (call $dynamic_slot (i32.load offset=16 (local.get ~a))))"
        base symbol base value slot base)
      ;; No call between reading the moved value and publishing the binding.
      (format s "(local.set ~a (i32.load offset=20 (local.get ~a))) (i32.store (local.get ~a) ~a) (i32.store offset=4 (local.get ~a) (i32.load offset=22 (i32.load offset=16 (local.get ~a)))) (i32.store offset=24 (local.get ~a) (i32.const 1112425521)) (i32.store offset=28 (local.get ~a) (i32.const 0)) (i32.store offset=20 (local.get ~a) (i32.load (local.get ~a)))"
        value base base (b-load wasm32::tcr.db_link) base base base base base slot)
      (write-string (b-store wasm32::tcr.db_link (b-local base)) s)
      (format s "(i32.store (local.get ~a) (local.get ~a))" slot value)))
) (progn 
  (let ((value (temporary)) (base (temporary)) (slot (temporary)))
    (with-output-to-string (s)
      (format s "(local.set ~a ~a) (local.set ~a (call $dynamic_slot ~a)) (local.set ~a (local.get $top))" value code slot symbol base)
      (write-string (b-reserve-runtime "(i64.const 32)") s)
      (format s "(i32.store (local.get ~a) ~a) (i32.store offset=4 (local.get ~a) (i32.load offset=22 ~a)) (i32.store offset=24 (local.get ~a) (i32.const 1112425521)) (i32.store offset=28 (local.get ~a) (i32.const 0))" base (b-load wasm32::tcr.db_link) base symbol base base)
      (write-string (b-runtime-roots (b-at (b-local base) 8) "(i32.const 2)") s)
      (format s "(i32.store offset=16 (local.get ~a) ~a) (i32.store offset=20 (local.get ~a) (i32.load (local.get ~a)))" base symbol base slot)
      (write-string (b-store wasm32::tcr.db_link (b-local base)) s)
      (format s "(i32.store (local.get ~a) (local.get ~a))" slot value))))))
(defun b-special-extent (producer)
  (let* ((head (temporary)) (top (temporary)) (root (temporary))
         (exception (b-exception-local))
         (body (let ((*b-tail-position* nil)) (funcall producer))))
    (with-output-to-string (s)
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top)) (local.set ~a ~a)" head (b-load wasm32::tcr.db_link) top root (b-load wasm32::tcr.root_head))
      (format s "(block $bindings_normal (block $bindings_error (result exnref) (try_table (catch_all_ref $bindings_error) ~a (br $bindings_normal)) unreachable) (local.set ~a) (call $unbind_to (local.get ~a)) ~a (local.set $top (local.get ~a)) (throw_ref (local.get ~a)))" body exception head (b-store wasm32::tcr.root_head (b-local root)) top exception)
      (format s "(call $unbind_to (local.get ~a)) ~a (local.set $top (local.get ~a))" head (b-store wasm32::tcr.root_head (b-local root)) top))))
(defun b-let (op args)
  (b-frame (length (first args))
    (lambda (base)
      (flet ((body ()
        (with-output-to-string (s)
          (loop for var in (first args) for init in (second args) for i from 0 do
            (if (eq op 'ccl::let*) (write-string (b-bind-value var (b-scalar init)) s)
              (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) base (b-scalar init))))
          (when (eq op 'ccl::let)
            (loop for var in (first args) for i from 0 do
              (write-string (b-bind-value var (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) base)) s)))
          (write-string (b-multiple (third args)) s))))
        (if (some #'b-special-p (first args)) (b-special-extent #'body) (body))))))
(defun b-dynamic-runtime ()
 (if *b-allocation-retry* (progn 
 "(func $binding_index (param $symbol i32) (result i32) (local $index i32)
 (if (i32.or (i32.ne (i32.and (local.get $symbol) (i32.const 7)) (i32.const 6)) (i32.lt_u (local.get $symbol) (i32.const 6))) (then (throw $call_error (i32.const 11))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $symbol)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 11))))
 (if (i32.ne (i32.load (i32.sub (local.get $symbol) (i32.const 6))) (i32.const 1850)) (then (throw $call_error (i32.const 11))))
 (local.set $index (i32.load offset=22 (local.get $symbol)))
 (if (i32.or (i32.and (local.get $index) (i32.const 3)) (i32.lt_s (local.get $index) (i32.const 0))) (then (throw $call_error (i32.const 11))))
 (i32.shr_u (local.get $index) (i32.const 2)))
(func $binding_vector_check (param $base i32) (param $cap i32)
 (if (i32.or (i32.gt_u (local.get $cap) (i32.const 16777215)) (i32.and (local.get $base) (i32.const 3))) (then (throw $call_error (i32.const 11))))
 (if (i32.and (i32.ne (local.get $cap) (i32.const 0)) (i32.eqz (local.get $base))) (then (throw $call_error (i32.const 11))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $base)) (i64.mul (i64.extend_i32_u (local.get $cap)) (i64.const 4))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 11)))))
(func $dynamic_slot (param $symbol i32) (result i32)
 (local $index i32) (local $base i32) (local $cap i32) (local $newcap i32) (local $p i32) (local $i i32) (local $end i64)
 (local.set $index (call $binding_index (local.get $symbol)))
 (if (i32.eqz (local.get $index)) (then (throw $call_error (i32.const 11))))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.ge_u (local.get $index) (local.get $cap)) (then
  ;; No calls or polls from allocation preflight through publication. The TCR
  ;; roots the old vector throughout. Failure writes nothing; collection only
  ;; sees either complete old state or complete new state at a legal safepoint.
  (if (i32.ge_u (local.get $index) (i32.const 16777215)) (then (throw $call_error (i32.const 3))))
  (local.set $newcap (i32.const 16))
  (block $capacity_done (loop $capacity_loop
   (br_if $capacity_done (i32.gt_u (local.get $newcap) (local.get $index)))
   (local.set $newcap (i32.shl (local.get $newcap) (i32.const 1)))
   (if (i32.gt_u (local.get $newcap) (i32.const 16777215)) (then (local.set $newcap (i32.const 16777215))))
   (br $capacity_loop)))
  (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.extend_i32_u (i32.and (i32.add (i32.mul (local.get $newcap) (i32.const 4)) (i32.const 11)) (i32.const -8)))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.and (i32.add (i32.mul (local.get $newcap) (i32.const 4)) (i32.const 11)) (i32.const -8)))))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
  (local.set $p (i32.load offset=48 (global.get $tcr)))
  (local.set $end (i64.and (i64.add (i64.extend_i32_u (local.get $p)) (i64.add (i64.mul (i64.extend_i32_u (local.get $newcap)) (i64.const 4)) (i64.const 11))) (i64.const -8)))
  (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 3))))
  (if (i32.or (i64.gt_u (local.get $end) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (i64.gt_u (local.get $end) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))) (then (throw $call_error (i32.const 3))))
  ;; An owner must not alias the allocation area with its existing vector.
  (if (i32.and (i64.lt_u (i64.extend_i32_u (local.get $p)) (i64.add (i64.extend_i32_u (local.get $base)) (i64.mul (i64.extend_i32_u (local.get $cap)) (i64.const 4)))) (i64.gt_u (local.get $end) (i64.extend_i32_u (local.get $base)))) (then (throw $call_error (i32.const 11))))
  (i32.store (local.get $p) (i32.or (i32.shl (local.get $newcap) (i32.const 8)) (i32.const 250)))
  (memory.copy (i32.add (local.get $p) (i32.const 4)) (local.get $base) (i32.mul (local.get $cap) (i32.const 4)))
  (local.set $i (local.get $cap))
  (block $fill_done (loop $fill
   (br_if $fill_done (i32.ge_u (local.get $i) (local.get $newcap)))
   (i32.store (i32.add (local.get $p) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4)))) (i32.const 243))
   (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $fill)))
  (i32.store (i32.sub (i32.wrap_i64 (local.get $end)) (i32.const 4)) (i32.const 243))
  (i32.store offset=48 (global.get $tcr) (i32.wrap_i64 (local.get $end)))
  (local.set $base (i32.add (local.get $p) (i32.const 4)))
  (i32.store offset=104 (global.get $tcr) (local.get $base))
  (i32.store offset=108 (global.get $tcr) (local.get $newcap))))
 (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
(func $existing_dynamic_slot (param $symbol i32) (result i32) (local $index i32) (local $base i32) (local $cap i32)
 (local.set $index (call $binding_index (local.get $symbol)))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.or (i32.eqz (local.get $index)) (i32.ge_u (local.get $index) (local.get $cap))) (then (throw $call_error (i32.const 11))))
 (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
(func $special_location (param $symbol i32) (result i32) (local $index i32) (local $base i32) (local $cap i32) (local $slot i32)
 (local.set $index (call $binding_index (local.get $symbol)))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.and (i32.ne (local.get $index) (i32.const 0)) (i32.lt_u (local.get $index) (local.get $cap))) (then
  (local.set $slot (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
  (if (i32.ne (i32.load (local.get $slot)) (i32.const 243)) (then (return (local.get $slot))))))
 (i32.add (local.get $symbol) (i32.const 2)))
(func $special_read (param $symbol i32) (result i32) (local $value i32)
 (local.set $value (i32.load (call $special_location (local.get $symbol))))
 (if (i32.eq (local.get $value) (i32.const 51)) (then (throw $call_error (i32.const 10)))) (local.get $value))
  (func $unbind_to (param $stop i32) (local $p i32) (local $slot i32)
    (block $done (loop $pop
      (local.set $p (i32.load offset=112 (global.get $tcr))) (br_if $done (i32.eq (local.get $p) (local.get $stop)))
      (if (i32.or (i32.eqz (local.get $p)) (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.lt_u (local.get $p) (i32.load offset=68 (global.get $tcr))))) (then (throw $call_error (i32.const 11))))
      (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 32)) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 11))))
      (if (i32.or (i32.ne (i32.load offset=24 (local.get $p)) (i32.const 1112425521)) (i32.ge_u (i32.load (local.get $p)) (local.get $p))) (then (throw $call_error (i32.const 11))))
      (local.set $slot (call $existing_dynamic_slot (i32.load offset=16 (local.get $p))))
      (if (i32.ne (i32.load offset=4 (local.get $p)) (i32.load offset=22 (i32.load offset=16 (local.get $p)))) (then (throw $call_error (i32.const 11))))
      (i32.store (local.get $slot) (i32.load offset=20 (local.get $p)))
      (i32.store offset=112 (global.get $tcr) (i32.load (local.get $p))) (br $pop))))") (progn 
 "(func $binding_index (param $symbol i32) (result i32) (local $index i32)
 (if (i32.or (i32.ne (i32.and (local.get $symbol) (i32.const 7)) (i32.const 6)) (i32.lt_u (local.get $symbol) (i32.const 6))) (then (throw $call_error (i32.const 11))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $symbol)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 11))))
 (if (i32.ne (i32.load (i32.sub (local.get $symbol) (i32.const 6))) (i32.const 1850)) (then (throw $call_error (i32.const 11))))
 (local.set $index (i32.load offset=22 (local.get $symbol)))
 (if (i32.or (i32.and (local.get $index) (i32.const 3)) (i32.lt_s (local.get $index) (i32.const 0))) (then (throw $call_error (i32.const 11))))
 (i32.shr_u (local.get $index) (i32.const 2)))
(func $binding_vector_check (param $base i32) (param $cap i32)
 (if (i32.or (i32.gt_u (local.get $cap) (i32.const 16777215)) (i32.and (local.get $base) (i32.const 3))) (then (throw $call_error (i32.const 11))))
 (if (i32.and (i32.ne (local.get $cap) (i32.const 0)) (i32.eqz (local.get $base))) (then (throw $call_error (i32.const 11))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $base)) (i64.mul (i64.extend_i32_u (local.get $cap)) (i64.const 4))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 11)))))
(func $dynamic_slot (param $symbol i32) (result i32)
 (local $index i32) (local $base i32) (local $cap i32) (local $newcap i32) (local $p i32) (local $i i32) (local $end i64)
 (local.set $index (call $binding_index (local.get $symbol)))
 (if (i32.eqz (local.get $index)) (then (throw $call_error (i32.const 11))))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.ge_u (local.get $index) (local.get $cap)) (then
  ;; No calls or polls from allocation preflight through publication. The TCR
  ;; roots the old vector throughout. Failure writes nothing; collection only
  ;; sees either complete old state or complete new state at a legal safepoint.
  (if (i32.ge_u (local.get $index) (i32.const 16777215)) (then (throw $call_error (i32.const 3))))
  (local.set $newcap (i32.const 16))
  (block $capacity_done (loop $capacity_loop
   (br_if $capacity_done (i32.gt_u (local.get $newcap) (local.get $index)))
   (local.set $newcap (i32.shl (local.get $newcap) (i32.const 1)))
   (if (i32.gt_u (local.get $newcap) (i32.const 16777215)) (then (local.set $newcap (i32.const 16777215))))
   (br $capacity_loop)))
  (local.set $p (i32.load offset=48 (global.get $tcr)))
  (local.set $end (i64.and (i64.add (i64.extend_i32_u (local.get $p)) (i64.add (i64.mul (i64.extend_i32_u (local.get $newcap)) (i64.const 4)) (i64.const 11))) (i64.const -8)))
  (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 3))))
  (if (i32.or (i64.gt_u (local.get $end) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (i64.gt_u (local.get $end) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))) (then (throw $call_error (i32.const 3))))
  ;; An owner must not alias the allocation area with its existing vector.
  (if (i32.and (i64.lt_u (i64.extend_i32_u (local.get $p)) (i64.add (i64.extend_i32_u (local.get $base)) (i64.mul (i64.extend_i32_u (local.get $cap)) (i64.const 4)))) (i64.gt_u (local.get $end) (i64.extend_i32_u (local.get $base)))) (then (throw $call_error (i32.const 11))))
  (i32.store (local.get $p) (i32.or (i32.shl (local.get $newcap) (i32.const 8)) (i32.const 250)))
  (memory.copy (i32.add (local.get $p) (i32.const 4)) (local.get $base) (i32.mul (local.get $cap) (i32.const 4)))
  (local.set $i (local.get $cap))
  (block $fill_done (loop $fill
   (br_if $fill_done (i32.ge_u (local.get $i) (local.get $newcap)))
   (i32.store (i32.add (local.get $p) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4)))) (i32.const 243))
   (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $fill)))
  (i32.store (i32.sub (i32.wrap_i64 (local.get $end)) (i32.const 4)) (i32.const 243))
  (i32.store offset=48 (global.get $tcr) (i32.wrap_i64 (local.get $end)))
  (local.set $base (i32.add (local.get $p) (i32.const 4)))
  (i32.store offset=104 (global.get $tcr) (local.get $base))
  (i32.store offset=108 (global.get $tcr) (local.get $newcap))))
 (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
(func $existing_dynamic_slot (param $symbol i32) (result i32) (local $index i32) (local $base i32) (local $cap i32)
 (local.set $index (call $binding_index (local.get $symbol)))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.or (i32.eqz (local.get $index)) (i32.ge_u (local.get $index) (local.get $cap))) (then (throw $call_error (i32.const 11))))
 (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
(func $special_location (param $symbol i32) (result i32) (local $index i32) (local $base i32) (local $cap i32) (local $slot i32)
 (local.set $index (call $binding_index (local.get $symbol)))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.and (i32.ne (local.get $index) (i32.const 0)) (i32.lt_u (local.get $index) (local.get $cap))) (then
  (local.set $slot (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
  (if (i32.ne (i32.load (local.get $slot)) (i32.const 243)) (then (return (local.get $slot))))))
 (i32.add (local.get $symbol) (i32.const 2)))
(func $special_read (param $symbol i32) (result i32) (local $value i32)
 (local.set $value (i32.load (call $special_location (local.get $symbol))))
 (if (i32.eq (local.get $value) (i32.const 51)) (then (throw $call_error (i32.const 10)))) (local.get $value))
  (func $unbind_to (param $stop i32) (local $p i32) (local $slot i32)
    (block $done (loop $pop
      (local.set $p (i32.load offset=112 (global.get $tcr))) (br_if $done (i32.eq (local.get $p) (local.get $stop)))
      (if (i32.or (i32.eqz (local.get $p)) (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.lt_u (local.get $p) (i32.load offset=68 (global.get $tcr))))) (then (throw $call_error (i32.const 11))))
      (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 32)) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 11))))
      (if (i32.or (i32.ne (i32.load offset=24 (local.get $p)) (i32.const 1112425521)) (i32.ge_u (i32.load (local.get $p)) (local.get $p))) (then (throw $call_error (i32.const 11))))
      (local.set $slot (call $existing_dynamic_slot (i32.load offset=16 (local.get $p))))
      (if (i32.ne (i32.load offset=4 (local.get $p)) (i32.load offset=22 (i32.load offset=16 (local.get $p)))) (then (throw $call_error (i32.const 11))))
      (i32.store (local.get $slot) (i32.load offset=20 (local.get $p)))
      (i32.store offset=112 (global.get $tcr) (i32.load (local.get $p))) (br $pop))))")))

(defun b-progv (checked-symbols values body)
 (if *b-allocation-retry* (progn 
  ;; U1 inserts CHECK-SYMBOL-LIST before evaluating the values form. Require
  ;; that exact IR shape; replace only this compiler-inserted intrinsic.
  (let* ((a (ccl::acode-operands checked-symbols)) (callee (first a)))
    (unless (and (eq (ccl::acode-operator-name (ccl::acode-operator checked-symbols)) 'ccl::call)
                 (ccl::acode-p callee)
                 (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)
                 (eq (first (ccl::acode-operands callee)) 'ccl::check-symbol-list)
                 (null (third a)) (= (length (second a)) 2) (null (second (second a))) (= (length (first (second a))) 1)) (refuse :b-progv-guard))
    (b-frame 2 (lambda (base)
      (with-output-to-string (s)
        (format s "(i32.store offset=8 ~a ~a) (drop (call $progv_symbols (i32.load offset=8 ~a) (local.get $top))) (i32.store offset=12 ~a ~a)"
          base (b-scalar (first (first (second a)))) base base (b-scalar values))
        (write-string (b-special-extent
          (lambda ()
            (let ((symbols (temporary)) (vals (temporary)) (symbol (temporary)) (value (temporary)) (next-value (temporary)))
              (with-output-to-string (out)
                ;; Values evaluation may have mutated the symbols list.
                (format out "(local.set ~a (i32.load offset=8 ~a)) (local.set ~a (i32.load offset=12 ~a)) (drop (call $progv_symbols (local.get ~a) (local.get $top)))"
                  symbols base vals base symbols)
                (format out "(block $progv_done (loop $progv_bind (br_if $progv_done (i32.eq (local.get ~a) (i32.const 77825))) (local.set ~a (i32.load offset=3 (local.get ~a))) (local.set ~a (i32.const 51)) (if (i32.ne (local.get ~a) (i32.const 77825)) (then (local.set ~a ~a) (local.set ~a (i32.load offset=3 (local.get ~a))) (local.set ~a (local.get ~a))))"
                  symbols symbol symbols value vals next-value (b-checked-cdr (b-local vals)) value vals vals next-value)
                ;; Symbol cursor reload from the rooted list after the value step;
                ;; the temporary above held only the next values pointer.
                (format out "(i32.store offset=12 ~a (local.get ~a))" base vals)
                (write-string (b-bind-symbol (b-local symbol) (b-local value)) out)
                (format out "(local.set ~a (i32.load offset=12 ~a))" vals base)
                (format out "(local.set ~a (i32.load offset=8 ~a)) (local.set ~a ~a) (i32.store offset=8 ~a (local.get ~a)) (br $progv_bind)))"
                  symbols base symbols (b-checked-cdr (b-local symbols)) base symbols)
                (write-string (b-multiple body) out))))) s)))))) (progn 
  ;; U1 inserts CHECK-SYMBOL-LIST before evaluating the values form. Require
  ;; that exact IR shape; replace only this compiler-inserted intrinsic.
  (let* ((a (ccl::acode-operands checked-symbols)) (callee (first a)))
    (unless (and (eq (ccl::acode-operator-name (ccl::acode-operator checked-symbols)) 'ccl::call)
                 (ccl::acode-p callee)
                 (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)
                 (eq (first (ccl::acode-operands callee)) 'ccl::check-symbol-list)
                 (null (third a)) (= (length (second a)) 2) (null (second (second a))) (= (length (first (second a))) 1)) (refuse :b-progv-guard))
    (b-frame 2 (lambda (base)
      (with-output-to-string (s)
        (format s "(i32.store offset=8 ~a ~a) (drop (call $progv_symbols (i32.load offset=8 ~a) (local.get $top))) (i32.store offset=12 ~a ~a)"
          base (b-scalar (first (first (second a)))) base base (b-scalar values))
        (write-string (b-special-extent
          (lambda ()
            (let ((symbols (temporary)) (vals (temporary)) (symbol (temporary)) (value (temporary)) (next-value (temporary)))
              (with-output-to-string (out)
                ;; Values evaluation may have mutated the symbols list.
                (format out "(local.set ~a (i32.load offset=8 ~a)) (local.set ~a (i32.load offset=12 ~a)) (drop (call $progv_symbols (local.get ~a) (local.get $top)))"
                  symbols base vals base symbols)
                (format out "(block $progv_done (loop $progv_bind (br_if $progv_done (i32.eq (local.get ~a) (i32.const 77825))) (local.set ~a (i32.load offset=3 (local.get ~a))) (local.set ~a (i32.const 51)) (if (i32.ne (local.get ~a) (i32.const 77825)) (then (local.set ~a ~a) (local.set ~a (i32.load offset=3 (local.get ~a))) (local.set ~a (local.get ~a))))"
                  symbols symbol symbols value vals next-value (b-checked-cdr (b-local vals)) value vals vals next-value)
                ;; Symbol cursor reload from the rooted list after the value step;
                ;; the temporary above held only the next values pointer.
                (write-string (b-bind-symbol (b-local symbol) (b-local value)) out)
                (format out "(local.set ~a (i32.load offset=8 ~a)) (local.set ~a ~a) (i32.store offset=8 ~a (local.get ~a)) (br $progv_bind)))"
                  symbols base symbols (b-checked-cdr (b-local symbols)) base symbols)
                (write-string (b-multiple body) out))))) s))))))))
(defun b-progv-runtime ()
 (if *b-allocation-retry* (progn 
  "(func $progv_slot (param $symbol i32) (result i32) (local $bits i32)
     (if (i32.or (i32.ne (i32.and (local.get $symbol) (i32.const 7)) (i32.const 6)) (i32.lt_u (local.get $symbol) (i32.const 6))) (then (throw $call_error (i32.const 12))))
     (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $symbol)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 12))))
     (if (i32.ne (i32.load (i32.sub (local.get $symbol) (i32.const 6))) (i32.const 1850)) (then (throw $call_error (i32.const 12))))
     (local.set $bits (i32.load offset=14 (local.get $symbol)))
     (if (i32.or (i32.and (local.get $bits) (i32.const 3)) (i32.and (local.get $bits) (i32.const 24))) (then (throw $call_error (i32.const 12))))
     (if (i32.eqz (call $binding_index (local.get $symbol))) (then (throw $call_error (i32.const 11))))
     (call $binding_index (local.get $symbol)))
   (func $progv_cdr (param $p i32) (result i32)
     (if (i32.ne (i32.and (local.get $p) (i32.const 7)) (i32.const 1)) (then (throw $call_error (i32.const 5))))
     (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 7)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 5))))
     (i32.load (i32.sub (local.get $p) (i32.const 1))))
   (func $progv_symbols (param $p i32) (param $top i32) (result i32) (local $slow i32) (local $n i32)
     (local.set $slow (local.get $p))
     (block $done (loop $scan (br_if $done (i32.eq (local.get $p) (i32.const 77825)))
       (drop (call $progv_cdr (local.get $p))) (drop (call $progv_slot (i32.load offset=3 (local.get $p))))
       (local.set $p (call $progv_cdr (local.get $p))) (local.set $n (i32.add (local.get $n) (i32.const 1)))
       (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 32))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))
       (if (i32.eqz (i32.and (local.get $n) (i32.const 1))) (then (local.set $slow (call $progv_cdr (local.get $slow)))))
       (if (i32.and (i32.ne (local.get $p) (i32.const 77825)) (i32.eq (local.get $p) (local.get $slow))) (then (throw $call_error (i32.const 12))))
       (br $scan))) (local.get $n))") (progn 
  "(func $progv_slot (param $symbol i32) (result i32) (local $bits i32)
     (if (i32.or (i32.ne (i32.and (local.get $symbol) (i32.const 7)) (i32.const 6)) (i32.lt_u (local.get $symbol) (i32.const 6))) (then (throw $call_error (i32.const 12))))
     (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $symbol)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 12))))
     (if (i32.ne (i32.load (i32.sub (local.get $symbol) (i32.const 6))) (i32.const 1850)) (then (throw $call_error (i32.const 12))))
     (local.set $bits (i32.load offset=14 (local.get $symbol)))
     (if (i32.or (i32.and (local.get $bits) (i32.const 3)) (i32.and (local.get $bits) (i32.const 24))) (then (throw $call_error (i32.const 12))))
     (call $dynamic_slot (local.get $symbol)))
   (func $progv_cdr (param $p i32) (result i32)
     (if (i32.ne (i32.and (local.get $p) (i32.const 7)) (i32.const 1)) (then (throw $call_error (i32.const 5))))
     (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 7)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 5))))
     (i32.load (i32.sub (local.get $p) (i32.const 1))))
   (func $progv_symbols (param $p i32) (param $top i32) (result i32) (local $slow i32) (local $n i32)
     (local.set $slow (local.get $p))
     (block $done (loop $scan (br_if $done (i32.eq (local.get $p) (i32.const 77825)))
       (drop (call $progv_cdr (local.get $p))) (drop (call $progv_slot (i32.load offset=3 (local.get $p))))
       (local.set $p (call $progv_cdr (local.get $p))) (local.set $n (i32.add (local.get $n) (i32.const 1)))
       (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 32))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))
       (if (i32.eqz (i32.and (local.get $n) (i32.const 1))) (then (local.set $slow (call $progv_cdr (local.get $slow)))))
       (if (i32.and (i32.ne (local.get $p) (i32.const 77825)) (i32.eq (local.get $p) (local.get $slow))) (then (throw $call_error (i32.const 12))))
       (br $scan))) (local.get $n))")))

(defun b-bound-address (var)
  (let ((n (position var *b-bound-vars* :test #'eq)))
    (unless n (refuse :b-bound-variable))
    (b-wat "(i32.add (local.get $bindings) (i32.const ~d))" (+ 0 (* 4 n)))))
(defun b-bind-value (var value)
  (cond ((b-special-p var) (b-special-bind var value)) (var (if (b-captured-p var)
    (let ((staged (temporary)))
      ;; Evaluation may collect. The cell address must be read afterwards.
      ;; Address lookup itself has no call, allocation or poll.
      (b-wat "(local.set ~a ~a) (i32.store ~a (local.get ~a))"
        staged value (b-variable-address var) staged))
    (b-wat "(i32.store ~a ~a)" (b-variable-address var) value))) (t "")))
(defun b-stage-value (var value)
  (if (b-special-p var) (b-wat "(i32.store ~a ~a)" (b-bound-address var) value) (b-bind-value var value)))
(defun b-stage-read (var)
  (if (b-special-p var) (b-wat "(i32.load ~a)" (b-bound-address var)) (b-read-variable var)))
(defun b-keyword-scan (required opt keys)
  ;; Validate and stage before publishing parameter bindings. A handler for
  ;; malformed keyword arguments must still see the caller's dynamic values.
  (when keys
    (destructuring-bind (allow vars supplied inits names) keys
      (declare (ignore inits))
      (with-output-to-string (s)
        (let* ((start (+ required (length (first opt)))) (cursor (temporary)) (key (temporary))
               (value (temporary)) (known (temporary)) (unknown (temporary))
               (allow-seen (temporary)) (allow-value (temporary)))
          (format s "(local.set ~a (i32.const ~d)) (local.set ~a (i32.const 0)) (local.set ~a (i32.const 0)) (local.set ~a (i32.const 77825))"
            cursor start unknown allow-seen allow-value)
          (write-string (b-condition (b-wat "(i32.and (i32.gt_u (local.get $nargs) (i32.const ~d)) (i32.and (i32.sub (local.get $nargs) (i32.const ~d)) (i32.const 1)))" start start) 16) s)
          (format s "(block $keys_done (loop $keys_scan (br_if $keys_done (i32.ge_u (local.get ~a) (local.get $nargs))) (local.set ~a (i32.load (i32.add (local.get $incoming) (i32.mul (local.get ~a) (i32.const 4))))) (local.set ~a (i32.load offset=4 (i32.add (local.get $incoming) (i32.mul (local.get ~a) (i32.const 4))))) (local.set ~a (i32.const 0))" cursor key cursor value cursor known)
          (loop for var in vars for sp in supplied for name across names
                for index from 0
                when (= index (position name names :test #'eq)) do
            (format s "(if (i32.eq (local.get ~a) ~a) (then (local.set ~a (i32.const 1)) (if (i32.eq ~a (i32.const 77825)) (then ~a ~a))))"
              key (b-keyword name) known (b-stage-read sp)
              (b-stage-value var (b-local value)) (b-stage-value sp "(i32.const 77838)")))
          ;; :ALLOW-OTHER-KEYS is itself a recognized keyword, with first-wins
          ;; semantics even when the lambda also binds that named keyword.
          (format s "(if (i32.eq (local.get ~a) ~a) (then (local.set ~a (i32.const 1)) (if (i32.eqz (local.get ~a)) (then (local.set ~a (i32.const 1)) (local.set ~a (local.get ~a))))))"
            key (b-keyword :allow-other-keys) known allow-seen allow-seen allow-value value)
          (format s "(if (i32.eqz (local.get ~a)) (then (local.set ~a (i32.const 1)))) (local.set ~a (i32.add (local.get ~a) (i32.const 2))) (br $keys_scan)))" known unknown cursor cursor)
          (unless allow
            (write-string (b-condition (b-wat "(i32.and (local.get ~a) (i32.eq (local.get ~a) (i32.const 77825)))" unknown allow-value) 16) s))
)))))
(defun b-binding-code (required opt keys rest)
  ;; Input values remain in the caller's root record. Bound values and the
  ;; supplied-p flags occupy the callee's published frame before defaults call.
  (with-output-to-string (s)
    (loop for var in (first opt) for init in (second opt) for sp in (third opt)
          for i from required do
      (format s "(if (i32.gt_u (local.get $nargs) (i32.const ~d)) (then ~a ~a) (else ~a ~a))"
        i (b-bind-value var (b-wat "(i32.load offset=~d (local.get $incoming))" (* 4 i)))
        (b-bind-value sp "(i32.const 77838)")
        (b-bind-value var (b-scalar init)) (b-bind-value sp "(i32.const 77825)")))
    (when rest (write-string (b-rest-binding rest (+ required (length (first opt)))) s))
    (when keys
      (destructuring-bind (allow vars supplied inits names) keys
        (loop for var in vars for sp in supplied for init in inits do
          (format s "(if (i32.eq ~a (i32.const 77825)) (then ~a) (else ~a))"
            (b-stage-read sp) (b-bind-value var (b-scalar init))
            (if (b-special-p var) (b-bind-value var (b-stage-read var)) ""))
          (when (b-special-p sp) (write-string (b-bind-value sp (b-stage-read sp)) s)))))))
(defun b-wat (control &rest args) (apply #'format nil control args))
(defun b-load (offset) (b-wat "(i32.load offset=~d (global.get $tcr))" offset))
(defun b-store (offset value) (b-wat "(i32.store offset=~d (global.get $tcr) ~a)" offset value))
(defun b-local (name) (b-wat "(local.get ~a)" name))
(defun b-at (base offset) (b-wat "(i32.add ~a (i32.const ~d))" base offset))
(defun b-condition (test kind)
  (if (member kind '(1 4 16))
    (b-wat "(if ~a (then (call $implicit_error (i32.const ~d) (local.get $top)) unreachable))" test kind)
    (b-wat "(if ~a (then (throw $call_error (i32.const ~d))))" test kind)))
(defun b-reserve (bytes)
  (concatenate 'string
    (b-wat "(call $stack_guard (i64.add (i64.extend_i32_u (local.get $top)) (i64.const ~d)) (local.get $top) (i32.const 18))" bytes)
    (b-wat "(local.set $top (i32.add (local.get $top) (i32.const ~d)))" bytes)))
(defun b-initialize-roots (frame count)
  (with-output-to-string (s)
    (format s "(i32.store ~a ~a) (i32.store offset=4 ~a (i32.const ~d))" frame (b-load wasm32::tcr.root_head) frame count)
    (dotimes (i count) (format s "(i32.store offset=~d ~a (i32.const ~d))" (+ 8 (* 4 i)) frame wasm32::canonical-nil-value))
    (write-string (b-store wasm32::tcr.root_head frame) s)))
(defun b-frame (count body-function)
  (let* ((base (temporary)) (old-root (temporary)) (bytes (* 16 (ceiling (+ 8 (* 4 count)) 16)))
         (body (funcall body-function (b-local base))))
    (b-wat "(local.set ~a (local.get $top)) (local.set ~a ~a) ~a ~a ~a ~a (local.set $top (local.get ~a))"
      base old-root (b-load wasm32::tcr.root_head) (b-reserve bytes)
      (b-initialize-roots (b-local base) count) body
      (b-store wasm32::tcr.root_head (b-local old-root)) base)))
(defun b-reserve-runtime (bytes)
  ;; All extent arithmetic precedes narrowing and any frame write.
  (b-wat "(local.set $wide ~a) ~a (local.set $top (i32.wrap_i64 (i64.add (i64.extend_i32_u (local.get $top)) (local.get $wide))))"
    bytes (b-wat "(call $stack_guard (i64.add (i64.extend_i32_u (local.get $top)) (local.get $wide)) (local.get $top) (i32.const 18))")))
(defun b-runtime-roots (frame count)
  (let ((i (temporary)))
    (b-wat "(i32.store ~a ~a) (i32.store offset=4 ~a ~a) (local.set ~a (i32.const 0)) (block $roots_done (loop $roots_fill (br_if $roots_done (i32.ge_u (local.get ~a) ~a)) (i32.store (i32.add ~a (i32.add (i32.const 8) (i32.mul (local.get ~a) (i32.const 4)))) (i32.const 77825)) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $roots_fill))) ~a"
      frame (b-load wasm32::tcr.root_head) frame count i i count frame i i i (b-store wasm32::tcr.root_head frame))))
(defun b-retained-frame (count body-function)
  (let* ((base (temporary)) (root (temporary)) (body (funcall body-function (b-local base))))
    (b-wat "(local.set ~a (local.get $top)) (local.set ~a ~a) ~a ~a ~a ~a (local.set $top (local.get ~a))"
      base root (b-load wasm32::tcr.root_head)
      (b-reserve-runtime (b-wat "(i64.and (i64.add (i64.mul (i64.extend_i32_u ~a) (i64.const 4)) (i64.const 23)) (i64.const -16))" count))
      (b-runtime-roots (b-local base) count) body (b-store wasm32::tcr.root_head (b-local root)) base)))
(defun b-call (callee argument-list &optional local-self)
  ;; U1 splits positional arguments into stack and reversed register lists.
  ;; Wasm has one argument vector, but retains U1's source evaluation order.
  (when (and *bootstrap-front-end* (second argument-list))
    (setq argument-list (list (append (first argument-list) (reverse (second argument-list))) nil)))
  (when (and *bootstrap-front-end* (not local-self)
             (null (second argument-list))
             (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate))
    (let ((code (bootstrap-numeric-call (first (ccl::acode-operands callee))
                                       (first argument-list))))
      (when code (return-from b-call code))))
  (when (and *bootstrap-front-end* (not local-self)
             (not (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)))
    (setq *bootstrap-dynamic-call* t))
  (unless *b-tail-position* (return-from b-call (b-internal-call callee argument-list local-self)))
  (unless (null (second argument-list)) (refuse :b-arguments))
  (let* ((args (first argument-list)) (n (length args)) (arg-slots (* 4 (ceiling n 4)))
         (base (temporary)) (root (temporary)) (mv (temporary)) (owner (temporary)) (vsp (temporary)) (old-count (temporary))
         (out-offset (+ 16 (* 4 arg-slots)))
         (op (and callee (ccl::acode-operator-name (ccl::acode-operator callee))))
         (name (and (eq op 'ccl::immediate) (first (ccl::acode-operands callee))))
         (direct (and (eq op 'ccl::immediate) (symbolp name)
                      (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))
         (self (or local-self (if direct (b-symbol name) (b-scalar callee))))
         (codes (mapcar #'b-scalar args)))
    (when (and name (not direct)) (refuse :b-unlinked-function))

    (with-output-to-string (s)
      (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
        base root (b-load wasm32::tcr.root_head) mv (b-load wasm32::tcr.mv_base)
        owner (b-load wasm32::tcr.mv_owner_top) vsp (b-load wasm32::tcr.vsp) old-count (b-load wasm32::tcr.mv_count))
      (write-string (b-reserve-runtime (b-wat "(i64.add (i64.const ~d) (i64.extend_i32_u (local.get $result_bytes)))" out-offset)) s)
      (write-string (b-initialize-roots (b-local base) (+ 2 arg-slots)) s)
      (format s "(i32.store offset=8 (local.get ~a) ~a)" base self)
      (loop for code in codes for i from 0 do (format s "(i32.store offset=~d (local.get ~a) ~a)" (+ 16 (* 4 i)) base code))
      (write-string (b-store wasm32::tcr.vsp (b-at (b-local base) 16)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-at (b-local base) out-offset)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top "(local.get $top)") s)
      (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
      (format s "(call $resolve_lisp (i32.load offset=8 (local.get ~a)) (local.get $top)) (local.set $dispatch_slot) (local.set $dispatch_self) (i32.store offset=8 (local.get ~a) (local.get $dispatch_self))" base base)
      (write-string (if *b-tail-position*
                      (b-tail-transfer (b-at (b-local base) 16) (b-wat "(i32.const ~d)" n))
                      (b-wat "(call_indirect (type $b_entry) (local.get $dispatch_self) (i32.const ~d) (local.get $dispatch_slot))" n)) s)
      (write-string "(local.set $count) (local.set $value)" s)
      (write-string (b-ensure-results "(local.get $count)") s)
      (format s "(memory.copy (local.get $results) (i32.add (local.get ~a) (i32.const ~d)) (i32.mul (local.get $count) (i32.const 4)))" base out-offset)
      (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
      (write-string (b-store wasm32::tcr.mv_count (b-local old-count)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" base))))

;;; Compiled ordinary calls own their continuation directly. The result
;;; reservation precedes it, so a later tail transfer can reuse/resize arguments.
;;; The caller keeps its restoration state in Wasm locals across the body call.
(defun b-prepare-context (context output previous-root argument-slots)
  (with-output-to-string (s)
    (format s "(i32.store offset=20 ~a (local.get $dynamic_results)) (i32.store offset=28 ~a (local.get $result_descriptor))" context context)
    (format s "(i32.store ~a ~a) (i32.store offset=4 ~a ~a) (i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) (i32.store offset=16 ~a ~a) (i32.store offset=24 ~a (i32.const 0))"
      context (b-load wasm32::tcr.vsp) context output context context
      context previous-root context (b-load wasm32::tcr.mv_count) context)
    (write-string (b-runtime-roots (b-at context 32) (b-wat "(i32.add (i32.const 2) ~a)" argument-slots)) s)
    ;; b-runtime-roots publishes the current chain; an APPLY may retire its
    ;; evaluation roots once their values are copied, immediately before entry.
    (format s "(i32.store offset=32 ~a ~a)" context previous-root)))
(defun b-internal-dispatch (context count)
  (concatenate 'string
    (b-condition "(i32.ge_u (local.get $dispatch_slot) (table.size $tail_slots))" 4)
    (b-condition "(ref.is_null (table.get $tail_slots (local.get $dispatch_slot)))" 4)
    (b-wat "(call_indirect $tail_slots (type $tail_entry) (local.get $dispatch_self) ~a ~a (local.get $dispatch_slot))" count context)))
(defun b-internal-call (callee argument-list local-self)
  ;; U1 splits positional arguments into stack and reversed register lists.
  ;; Wasm has one argument vector, but retains U1's source evaluation order.
  (when (and *bootstrap-front-end* (second argument-list))
    (setq argument-list (list (append (first argument-list) (reverse (second argument-list))) nil)))
  (unless (null (second argument-list)) (refuse :b-arguments))
  (let* ((args (first argument-list)) (n (length args)) (arg-slots (* 4 (ceiling n 4)))
         (base (temporary)) (context (temporary)) (root (temporary)) (mv (temporary))
         (owner (temporary)) (vsp (temporary)) (old-count (temporary))
         (op (and callee (ccl::acode-operator-name (ccl::acode-operator callee))))
         (name (and (eq op 'ccl::immediate) (first (ccl::acode-operands callee))))
         (direct (and (eq op 'ccl::immediate) (symbolp name)
                      (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))
         (self (or local-self (if direct (b-symbol name) (b-scalar callee))))
         (codes (mapcar #'b-scalar args)))
    (when (and name (not direct)) (refuse :b-unlinked-function))
    (with-output-to-string (s)
      (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
        base root (b-load wasm32::tcr.root_head) mv (b-load wasm32::tcr.mv_base)
        owner (b-load wasm32::tcr.mv_owner_top) vsp (b-load wasm32::tcr.vsp) old-count (b-load wasm32::tcr.mv_count))
      (write-string (b-reserve-runtime (b-wat "(i64.add (i64.const ~d) (i64.extend_i32_u (local.get $result_bytes)))" (+ 48 (* 4 arg-slots)))) s)
      (format s "(local.set ~a (i32.add (local.get ~a) (local.get $result_bytes)))" context base)
      (write-string (b-prepare-context (b-local context) (b-local base) (b-local root) (b-wat "(i32.const ~d)" arg-slots)) s)
      (format s "(i32.store offset=40 (local.get ~a) ~a)" context self)
      (loop for code in codes for i from 0 do (format s "(i32.store offset=~d (local.get ~a) ~a)" (+ 48 (* 4 i)) context code))
      (format s "(call $resolve_lisp (i32.load offset=40 (local.get ~a)) (local.get $top)) (local.set $dispatch_slot) (local.set $dispatch_self) (i32.store offset=40 (local.get ~a) (local.get $dispatch_self))" context context)
      (write-string (b-store wasm32::tcr.vsp (b-at (b-local context) 48)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local base)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local context)) s)
      (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
      (when *b-producer-target*
        (format s "(i32.store offset=28 (local.get ~a) ~a)" context *b-producer-target*))
      (write-string (b-internal-dispatch (b-local context) (b-wat "(i32.const ~d)" n)) s)
      (write-string "(local.set $count) (local.set $value)" s)
      (if *b-producer-target*
        (format s "(local.set $results (i32.load offset=8 ~a))" *b-producer-target*)
        (write-string (b-ensure-results "(local.get $count)") s))
      (format s "(if (i32.eqz (local.get $dynamic_results)) (then (memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))))" base)
      (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
      (write-string (b-store wasm32::tcr.mv_count (b-local old-count)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" base))))

(defvar *b-exception-count* 0)

(defun b-exception-local ()
  (format nil "$cleanup_exception~d" (prog1 *b-exception-count* (incf *b-exception-count*))))

(defun b-control-frame (kind tag body-function)
  (let* ((base (temporary)) (root (temporary)) (head (temporary)) (value (temporary))
         (exception (b-exception-local)) (body (funcall body-function (b-local base))))
    (with-output-to-string (s)
      ;; CATCH evaluates its tag before establishing the extent.
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a)"
        value tag base root (b-load wasm32::tcr.root_head) head (b-load wasm32::tcr.handler_checkpoint))
      (write-string (b-reserve-runtime "(if (result i64) (local.get $dynamic_results) (then (i64.const 96)) (else (i64.and (i64.add (i64.extend_i32_u (local.get $result_bytes)) (i64.const 63)) (i64.const -16))))") s)
      (format s "(i32.store (local.get ~a) (local.get ~a)) (i32.store offset=4 (local.get ~a) (i32.const ~d)) (i32.store offset=8 (local.get ~a) (if (result i32) (local.get $dynamic_results) (then (i32.const 0)) (else (local.get $capacity)))) (i32.store offset=12 (local.get ~a) (i32.const 0)) (i32.store offset=16 (local.get ~a) (i32.add (local.get ~a) (i32.const 32))) (i32.store offset=20 (local.get ~a) ~a) (i32.store offset=24 (local.get ~a) (i32.const 1128483889)) (i32.store offset=28 (local.get ~a) (i32.const 0))"
        base head base kind base base base base base (b-load wasm32::tcr.unwind_state) base base)
      (write-string (b-runtime-roots (b-at (b-local base) 32) "(if (result i32) (local.get $dynamic_results) (then (i32.const 2)) (else (i32.add (local.get $capacity) (i32.const 2))))") s)
      (format s "(i32.store offset=40 (local.get ~a) (local.get ~a))" base value)
      (write-string "(if (local.get $dynamic_results) (then" s)
      (format s "(i32.store offset=28 (local.get ~a) (i32.add (local.get ~a) (i32.const 48)))" base base)
      (write-string (b-result-descriptor (b-at (b-local base) 48) "(local.get $result_scope)") s)
      (write-string "))" s)
      (format s "(call $control_push (local.get ~a) (local.get $top))" base)
      (write-string (b-store wasm32::tcr.handler_checkpoint (b-local base)) s)
      (format s "(block $control_normal (block $control_error (result exnref) (try_table (catch_all_ref $control_error) ~a (br $control_normal)) unreachable) (local.set ~a)" body exception)
      (format s "(call $control_pop (local.get ~a))" base)
      (write-string (b-store wasm32::tcr.handler_checkpoint (b-local head)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (write-string (b-store wasm32::tcr.unwind_state (b-wat "(call $exit_state (local.get ~a))" exception)) s)
      (format s "(local.set $top (local.get ~a)) (throw_ref (local.get ~a)))" base exception)
      (format s "(call $control_pop (local.get ~a))" base)
      (write-string (b-store wasm32::tcr.handler_checkpoint (b-local head)) s)
      (write-string (b-store wasm32::tcr.unwind_state (b-wat "(i32.load offset=20 (local.get ~a))" base)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" base))))

(defvar *b-local-tags* nil)
(defvar *b-blocks* nil)
(defun b-catch (tag body)
  (b-exit-frame 1 (b-scalar tag) (lambda (record) (declare (ignore record)) (b-multiple body))))
(defun b-local-block (identity body)
  ;; Match CCL's identity cell, never its printed block name. Closed returns
  ;; already use U1's fresh cons tag and CATCH inside this local boundary.
  (labels ((referenced (x)
             (cond ((ccl::acode-p x)
                    (or (and (eq (ccl::acode-operator-name (ccl::acode-operator x)) 'ccl::local-return-from)
                             (eq (first (ccl::acode-operands x)) identity))
                        (some #'referenced (ccl::acode-operands x))))
                   ((consp x) (some #'referenced x)))))
    (if (not (referenced body)) (b-multiple body)
      (b-exit-frame 3 "(i32.const 77825)"
        (lambda (record)
          (let ((*b-blocks* (acons identity record *b-blocks*))) (b-multiple body)))))))
(defun b-local-return (identity values)
  (let ((record (cdr (or (assoc identity *b-blocks* :test #'eq) (refuse :b-block-identity)))))
    (concatenate 'string
      (let ((*b-tail-position* nil)) (b-multiple values))
      (b-save-control record)
      (b-wat "(i32.store offset=12 ~a (local.get $count))" record)
      (b-store wasm32::tcr.unwind_state "(i32.const 1)")
      (b-wat "(throw $nonlocal_exit ~a)" record))))
(defun b-cons (car-form cdr-form)
  (b-wat "(block (result i32) ~a)" (b-frame 2 (lambda (root)
    (b-wat "(block (result i32) (i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) ~a)"
      root (b-scalar car-form) root (b-scalar cdr-form)
      (b-at (b-heap-block 8 (lambda (p)
        (b-wat "(i32.store ~a (i32.load offset=12 ~a)) (i32.store offset=4 ~a (i32.load offset=8 ~a))" p root p root))) 1))))))
(defun b-exit-frame (kind tag producer)
  (b-control-frame kind tag
    (lambda (record)
      (let* ((top (temporary)) (root (temporary)) (vsp (temporary)) (mv (temporary)) (owner (temporary)) (count (temporary))
             (target (temporary)) (exception (b-exception-local))
             (code (let ((*b-tail-position* nil)) (funcall producer record))))
        (with-output-to-string (s)
          (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
            top root (b-load wasm32::tcr.root_head) vsp (b-load wasm32::tcr.vsp) mv (b-load wasm32::tcr.mv_base) owner (b-load wasm32::tcr.mv_owner_top) count (b-load wasm32::tcr.mv_count))
          (format s "(block $catch_normal (block $catch_exit (result i32 exnref) (try_table (catch_ref $nonlocal_exit $catch_exit) ~a (br $catch_normal)) unreachable) (local.set ~a) (local.set ~a) (if (i32.ne (local.get ~a) ~a) (then (throw_ref (local.get ~a))))"
            code exception target target record exception)
          (format s "(local.set $top (local.get ~a))" top)
          (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
          (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
          (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
          (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
          (write-string (b-store wasm32::tcr.mv_count (b-local count)) s)
          (format s "(local.set $count (i32.load offset=12 ~a))" record)
          (write-string (b-load-control record) s)
          (write-string ")" s))))))

(defun b-throw (tag values)
  (b-frame 1
    (lambda (root)
      (let ((target (temporary)))
        (concatenate 'string
          (b-wat "(i32.store offset=8 ~a ~a)" root (b-scalar tag))
          (let ((*b-tail-position* nil)) (b-multiple values))
          (b-wat "(local.set ~a (call $find_catch (i32.load offset=8 ~a) (local.get $top)))" target root)
          (b-save-control (b-local target))
          (b-wat "(i32.store offset=12 (local.get ~a) (local.get $count))" target)
          (b-store wasm32::tcr.unwind_state "(i32.const 1)")
          (b-wat "(throw $nonlocal_exit (local.get ~a))" target))))))

(defun b-control-runtime ()
  "(func $exit_state (param $exception exnref) (result i32)
    (block $nonlocal (result i32)
      (block $ordinary
        (try_table (catch $nonlocal_exit $nonlocal) (catch_all $ordinary) (throw_ref (local.get $exception))) unreachable)
      (return (i32.const 2))) drop (i32.const 1))
  (func $find_catch (param $tag i32) (param $top i32) (result i32) (local $p i32) (local $previous i32) (local $capacity i32)
    (local.set $p (i32.load offset=140 (global.get $tcr)))
    (block $missing (loop $search
      (br_if $missing (i32.eqz (local.get $p)))
      (if (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.lt_u (local.get $p) (i32.load offset=68 (global.get $tcr)))) (then (throw $call_error (i32.const 9))))
      (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 48)) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 9))))
      (if (i32.ne (i32.load offset=24 (local.get $p)) (i32.const 1128483889)) (then (throw $call_error (i32.const 9))))
      (local.set $capacity (i32.load offset=8 (local.get $p)))
      (if (i64.gt_u (i64.add (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 48)) (i64.mul (i64.extend_i32_u (local.get $capacity)) (i64.const 4))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 9))))
      (if (i32.or (i32.ne (i32.load offset=16 (local.get $p)) (i32.add (local.get $p) (i32.const 32))) (i32.ne (i32.load offset=36 (local.get $p)) (i32.add (local.get $capacity) (i32.const 2)))) (then (throw $call_error (i32.const 9))))
      (if (i32.or (i32.lt_u (i32.load offset=4 (local.get $p)) (i32.const 1)) (i32.gt_u (i32.load offset=4 (local.get $p)) (i32.const 3))) (then (throw $call_error (i32.const 9))))
      (local.set $previous (i32.load (local.get $p)))
      (if (i32.ge_u (local.get $previous) (local.get $p)) (then (throw $call_error (i32.const 9))))
      (if (i32.and (i32.eq (i32.load offset=4 (local.get $p)) (i32.const 1)) (i32.eq (i32.load offset=40 (local.get $p)) (local.get $tag))) (then (return (local.get $p))))
      (local.set $p (local.get $previous)) (br $search)))
    (call $implicit_error (i32.const 8) (local.get $top)) unreachable)")

(defun b-unwind-protect (protected cleanup)
  ;; Reserve the result-retention root before entering the dynamic extent.
  ;; Calls in either arm are ordinary: pending cleanup forbids tail transfer.
  (let* ((exception (format nil "$cleanup_exception~d" (prog1 *b-exception-count* (incf *b-exception-count*))))
         (saved-count (temporary)))
    (b-control-frame 2 "(i32.const 77825)"
      (lambda (retained)
        (let* ((top (temporary)) (root (temporary)) (vsp (temporary))
               (mv (temporary)) (owner (temporary)) (count (temporary))
               (protected-code (let ((*b-tail-position* nil)) (b-multiple protected)))
               (cleanup-code (let ((*b-tail-position* nil)) (b-multiple cleanup)))
               (restore (concatenate 'string
                          (b-wat "(local.set $top (local.get ~a))" top)
                          (b-store wasm32::tcr.root_head (b-local root))
                          (b-store wasm32::tcr.vsp (b-local vsp))
                          (b-store wasm32::tcr.mv_base (b-local mv))
                          (b-store wasm32::tcr.mv_owner_top (b-local owner))
                          (b-store wasm32::tcr.mv_count (b-local count))
                          (b-store wasm32::tcr.handler_checkpoint retained))))
          (with-output-to-string (out)
            (format out "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
              top root (b-load wasm32::tcr.root_head) vsp (b-load wasm32::tcr.vsp)
              mv (b-load wasm32::tcr.mv_base) owner (b-load wasm32::tcr.mv_owner_top) count (b-load wasm32::tcr.mv_count))
            ;; Only the protected form is caught here. Cleanup's own exception
            ;; replaces this one and goes to the next enclosing extent.
            (format out "(block $protected_normal (block $protected_error (result exnref) (try_table (catch_all_ref $protected_error) ~a (br $protected_normal)) unreachable) (local.set ~a) ~a ~a (throw_ref (local.get ~a)))"
              protected-code exception (concatenate 'string restore (b-store wasm32::tcr.unwind_state (b-wat "(call $exit_state (local.get ~a))" exception))) cleanup-code exception)
            (format out "(local.set ~a (local.get $count))" saved-count)
            (write-string (b-save-control retained) out)
            (write-string restore out)
            (write-string cleanup-code out)
            (format out "(local.set $count (local.get ~a)) ~a" saved-count (b-load-control retained))))))))

(defvar *bootstrap-front-end* nil)
(defvar *bootstrap-self-call* nil)
(defvar *bootstrap-emitted* nil)
(defvar *bootstrap-symbols* nil)
(defvar *bootstrap-callees* nil)
(defvar *bootstrap-dynamic-call* nil)

(defun b-scalar (ir)
  (when (and *bootstrap-front-end* (ccl::acode-p ir)) (setf (gethash ir *bootstrap-emitted*) t))
  (when (b-raw-code-p ir) (return-from b-scalar (b-raw-code-text ir)))
  (let ((*b-tail-position* nil) (*b-producer-target* nil)) (b-scalar-inner ir)))
(defun b-scalar-inner (ir)
  (when *bootstrap-front-end*
    (let ((code (bootstrap-operator ir)))
      (when code (return-from b-scalar-inner code))))
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir))) (args (ccl::acode-operands ir)))
    (case op
      ((not)
       (unless (and *bootstrap-front-end* (= (length args) 2)
                    (member (ccl::acode-immediate-operand (first args)) '(:eq :ne)))
         (refuse :bootstrap-not))
       (b-wat "(if (result i32) (i32.~a ~a (i32.const 77825)) (then (i32.const 77838)) (else (i32.const 77825)))"
              (if (eq (ccl::acode-immediate-operand (first args)) :eq) "eq" "ne")
              (b-scalar (second args))))
      (ccl::list
       (b-raw-code-text (reduce (lambda (a b) (make-b-raw-code :text (b-cons a b))) (first args) :from-end t :initial-value (make-b-raw-code :text "(i32.const 77825)"))))
      (ccl::typed-form
       (when *bootstrap-front-end*
         ;; NX1's optional third operand requests a runtime type check.
         ;; Do not erase a check which the target cannot yet implement.
         (when (third args) (refuse :bootstrap-typecheck))
         (return-from b-scalar-inner (b-scalar (second args))))
       (unless (and (eq (first args) 'list)
                    (member (ccl::acode-operator-name (ccl::acode-operator (second args))) '(ccl::special-ref ccl::bound-special-ref))
                    (member (first (ccl::acode-operands (second args))) '(ccl::%handlers% ccl::%restarts% *debugger-hook* ccl::*interrupt-level*))) (refuse :b-condition-typed-form))
       (b-scalar (second args)))
      (ccl::eq
       (when *bootstrap-front-end* (return-from b-scalar-inner (bootstrap-eq args)))
       (unless (and (= (length args) 3) (eq (ccl::acode-immediate-operand (first args)) :eq)) (refuse :b-condition-comparison))
       (b-wat "(block (result i32) ~a)" (b-frame 2 (lambda (root)
         (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) (if (result i32) (i32.eq (i32.load offset=8 ~a) (i32.load offset=12 ~a)) (then (i32.const 77838)) (else (i32.const 77825)))"
           root (b-scalar (second args)) root (b-scalar (third args)) root root)))))
      ((ccl::special-ref ccl::bound-special-ref) (b-wat "(call $special_read_lisp ~a (local.get $top))" (b-special-symbol (first args))))
      (ccl::cons (b-cons (first args) (second args)))
      (ccl::setq-special
       (let ((value (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) (i32.store (call $special_location ~a) (local.get ~a)) (local.get ~a))" value (b-scalar (second args)) (b-special-symbol (first args)) value value)))
      (ccl::lexical-reference (b-read-variable (first args)))
      (ccl::setq-lexical
       (let ((value (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) ~a (local.get ~a))"
           value (b-scalar (second args)) (b-bind-value (first args) (b-local value)) value)))
      ((ccl::closed-function ccl::simple-function) (b-make-closure (first args)))
      (ccl::immediate
       (cond ((and *bootstrap-front-end* (pool-literal-p (first args)))
              (pool-load (first args)))
             ((member (first args) '(condition serious-condition error simple-condition simple-error type-error control-error warning simple-warning program-error undefined-function unbound-variable storage-condition ccl::no-applicable-method-exists arithmetic-error division-by-zero)) (b-wat "(i32.const ~d)" (* 4 (b-condition-mask (first args)))))
             ((and *b-float-service* (member (first args) '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact))) (b-wat "(i32.const ~d)" (* 4 (b-condition-mask (first args)))))
             ((keywordp (first args)) (b-keyword (first args)))
             ((assoc (first args) *b-call-links*) (b-symbol (first args)))
             ((member (first args) *b-special-names*) (b-special-symbol (first args)))
             ((pool-literal-p (first args)) (pool-load (first args)))
             ((member (first args) *b-restart-names*) (b-restart-symbol (first args)))
             (t (emit-expression ir))))
      (ccl::%function
       (when *bootstrap-front-end* (pushnew (first args) *bootstrap-callees*))
       (b-wat "(call $function_value_lisp ~a (local.get $top))" (b-symbol (first args))))
      ((ccl::builtin-call ccl::call ccl::values ccl::progn ccl::multiple-value-prog1 ccl::prog1 ccl::or ccl::if ccl::let ccl::let* ccl::flet ccl::labels ccl::lambda-bind ccl::self-call ccl::lexical-function-call ccl::unwind-protect ccl::catch ccl::throw ccl::progv ccl::local-block ccl::local-return-from ccl::local-tagbody ccl::local-go ccl::multiple-value-call ccl::multiple-value-list ccl::multiple-value-bind ccl::%decls-body)
       (b-wat "(block (result i32) ~a (if (result i32) (local.get $count) (then (i32.load (local.get $results))) (else (i32.const ~d))))" (b-multiple ir) wasm32::canonical-nil-value))
      ((car cdr ccl::%car ccl::%cdr rplaca rplacd ccl::%rplaca ccl::%rplacd ccl::set-car ccl::set-cdr)
       (b-wat "(block (result i32) ~a (i32.load (local.get $results)))" (b-checked-cons-operation op args)))
      (t (emit-expression ir)))))
;;; Multiple-value arguments grow directly in a rooted continuation. Each
;;; producer finishes before its values are appended; no Lisp call or poll
;;; occurs while extending and publishing the argument root range.
(defun b-multiple-call (callee forms)
  (when *bootstrap-front-end* (setq *bootstrap-dynamic-call* t))
  (let* ((base (temporary)) (output (temporary)) (callable (temporary)) (context (temporary)) (root (temporary))
         (mv (temporary)) (owner (temporary)) (vsp (temporary)) (old-count (temporary))
         (n (temporary)) (slots (temporary)) (next-slots (temporary)) (i (temporary))
         (source (temporary)) (scope (temporary)) (target (temporary)) (producer-root (temporary))
         (literal (member (ccl::acode-operator-name (ccl::acode-operator callee)) '(ccl::closed-function ccl::simple-function)))
         (ephemeral-bytes (if literal (b-ephemeral-bytes (first (ccl::acode-operands callee))) 0))
         (self (let ((*b-stack-closure* literal)) (b-scalar callee)))
         (codes (mapcar (lambda (form) (b-producer form source scope (b-local target) (b-local producer-root))) forms)))
    (with-output-to-string (s)
      (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
        base root (b-load wasm32::tcr.root_head) mv (b-load wasm32::tcr.mv_base)
        owner (b-load wasm32::tcr.mv_owner_top) vsp (b-load wasm32::tcr.vsp) old-count (b-load wasm32::tcr.mv_count))
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top))" callable self target)
      (write-string (b-reserve 32) s)
      (format s "(local.set ~a (local.get $top))" producer-root)
      (write-string (b-reserve 48) s)
      (format s "(local.set ~a (local.get $top))" output)
      (write-string (b-reserve-runtime (if *b-tail-position* "(i64.const 48)" "(i64.add (i64.const 48) (i64.extend_i32_u (local.get $result_bytes)))")) s)
      (format s "(local.set ~a ~a)" context (if *b-tail-position* (b-local output) (b-wat "(i32.add (local.get ~a) (local.get $result_bytes))" output)))
      (write-string (b-prepare-context (b-local context) (b-local output) (b-local root) "(i32.const 0)") s)
      (format s "(i32.store offset=40 (local.get ~a) ~a) (local.set ~a (i32.const 0)) (local.set ~a (i32.const 0))" context (b-local callable) n slots)
      (dolist (code codes)
        (format s "(i32.store offset=8 (local.get ~a) (i32.add (local.get ~a) (i32.add (i32.const 48) (i32.mul (local.get ~a) (i32.const 4))))) (i32.store offset=12 (local.get ~a) (i32.const 0)) (i32.store offset=20 (local.get ~a) (i32.const 1))" target context n target target)
        (format s "(i32.store offset=24 (local.get ~a) (local.get ~a))" target producer-root)
        (write-string code s)
        ;; Add unsigned counts and align in i64, before narrowing or writes.
        (format s "(local.set $wide (i64.and (i64.add (i64.mul (i64.add (i64.extend_i32_u (local.get ~a)) (i64.extend_i32_u (local.get $count))) (i64.const 4)) (i64.const 15)) (i64.const -16)))" n)
        (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const 48)) (local.get $wide)) (i64.extend_i32_u ~a))" context (b-load wasm32::tcr.vsp_limit)) 2) s)
        (format s "(local.set ~a (i32.wrap_i64 (i64.shr_u (local.get $wide) (i64.const 2)))) (local.set $top (i32.add (local.get ~a) (i32.add (i32.const 48) (i32.wrap_i64 (local.get $wide)))))" next-slots context)
        (format s "(local.set ~a (i32.add (local.get ~a) (local.get $count))) (block $mv_fill_done (loop $mv_fill (br_if $mv_fill_done (i32.ge_u (local.get ~a) (local.get ~a))) (i32.store (i32.add (local.get ~a) (i32.add (i32.const 48) (i32.mul (local.get ~a) (i32.const 4)))) (i32.const 77825)) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $mv_fill)))" i n i next-slots context i i i)
        (format s "(if (i32.ne (local.get ~a) (i32.load offset=8 (local.get ~a))) (then (memory.copy (i32.load offset=8 (local.get ~a)) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))))" source target target source)
        (write-string (b-store wasm32::tcr.root_head (b-at (b-local context) 32)) s)
        (format s "(local.set ~a (i32.add (local.get ~a) (local.get $count))) (local.set ~a (local.get ~a)) (i32.store offset=36 (local.get ~a) (i32.add (i32.const 2) (local.get ~a)))" n n slots next-slots context slots)
        (format s "(call $rv_release (local.get ~a))" scope))
      (format s "(call $resolve_lisp (i32.load offset=40 (local.get ~a)) (local.get $top)) (local.set $dispatch_slot) (local.set $dispatch_self) (i32.store offset=40 (local.get ~a) (local.get $dispatch_self))" context context)
      (if *b-tail-position*
        (progn
          (when (plusp ephemeral-bytes) (write-string (b-reserve ephemeral-bytes) s))
          (write-string (b-tail-transfer (b-at (b-local context) 48) (b-local n) ephemeral-bytes) s))
        (progn
          (write-string (b-store wasm32::tcr.vsp (b-at (b-local context) 48)) s)
          (write-string (b-store wasm32::tcr.mv_base (b-local output)) s)
          (write-string (b-store wasm32::tcr.mv_owner_top (b-local context)) s)
          (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
          (write-string (b-internal-dispatch (b-local context) (b-local n)) s)))
      (write-string "(local.set $count) (local.set $value)" s)
      (write-string (b-ensure-results "(local.get $count)") s)
      (format s "(if (i32.eqz (local.get $dynamic_results)) (then (memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))))" output)
      (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
      (write-string (b-store wasm32::tcr.mv_count (b-local old-count)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" base))))

(defun b-multiple-bind (args)
  (let ((values (let ((*b-tail-position* nil)) (b-multiple (second args)))))
    (concatenate 'string values
      (b-frame (length (first args))
        (lambda (base)
          (with-output-to-string (s)
            (loop for var in (first args) for i from 0 do
              (format s "(i32.store offset=~d ~a (if (result i32) (i32.gt_u (local.get $count) (i32.const ~d)) (then (i32.load offset=~d (local.get $results))) (else (i32.const 77825))))" (+ 8 (* 4 i)) base i (* 4 i)))
            (flet ((body ()
                     (with-output-to-string (s)
                       (loop for var in (first args) for i from 0 do
                         (write-string (b-bind-value var (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) base)) s))
                       (write-string (b-multiple (third args)) s))))
              (write-string (if (some #'b-special-p (first args)) (b-special-extent #'body) (body)) s))))))))

(defun b-multiple (ir)
  (when (and *bootstrap-front-end* (ccl::acode-p ir)) (setf (gethash ir *bootstrap-emitted*) t))
  (when (b-raw-code-p ir)
    (return-from b-multiple (b-wat "(local.set $value ~a) ~a (i32.store (local.get $results) (local.get $value)) (local.set $count (i32.const 1))" (b-raw-code-text ir) (b-ensure-results "(i32.const 1)"))))
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir))) (args (ccl::acode-operands ir)))
    (case op
      (ccl::typed-form
       (if *bootstrap-front-end*
         (progn
           (when (third args) (refuse :bootstrap-typecheck))
           (b-multiple (second args)))
         (b-multiple (make-b-raw-code :text (b-scalar ir)))))
      (ccl::%decls-body (b-multiple (first args)))
      (ccl::or
       (unless *bootstrap-front-end* (refuse :or))
       (bootstrap-or (first args)))
      (ccl::unwind-protect (b-unwind-protect (first args) (second args)))
      (ccl::catch (b-catch (first args) (second args)))
      (ccl::throw (b-throw (first args) (second args)))
      (ccl::local-tagbody (b-tagbody (first args) (second args)))
      (ccl::local-go (b-go (first args)))
      (ccl::local-block (b-local-block (first args) (second args)))
      (ccl::local-return-from (b-local-return (first args) (second args)))
      (ccl::multiple-value-call (b-multiple-call (first args) (second args)))
      (ccl::multiple-value-list
       (b-multiple-call (ccl::make-acode (ccl::%nx1-operator ccl::%function) 'list) args))
      (ccl::multiple-value-bind (b-multiple-bind args))
      (ccl::progv (b-progv (first args) (second args) (third args)))
      ((ccl::flet ccl::labels)
       (with-output-to-string (s)
         (loop for v in (first args) for f in (second args) do
           (write-string (b-bind-value v (b-make-closure f)) s))
         (write-string (b-multiple (third args)) s)))
      (ccl::lambda-bind (b-inline-lambda args))
      (ccl::self-call
       (or (and *bootstrap-front-end*
                (null (ccl::afunc-parent *pool-current*))
                (null (second args)) (null (second (first args)))
                (bootstrap-numeric-call (ccl::afunc-name *pool-current*)
                                        (first (first args))))
           (progn
             (when *bootstrap-front-end* (setq *bootstrap-self-call* t))
             (b-local-call 'b-self nil (first args) (second args)))))
      (ccl::lexical-function-call
       (b-local-call 'b-local-function (first args) (second args) (third args)))
      ((ccl::let ccl::let*) (b-let op args))
      (ccl::builtin-call
       (unless *bootstrap-front-end* (refuse :bootstrap-builtin))
       (let ((index (ccl::acode-fixnum-form-p (first args))))
         (unless (and index (<= 0 index) (< index (length ccl::%builtin-functions%)))
           (refuse :bootstrap-builtin-index))
         (b-call (ccl::make-acode (ccl::%nx1-operator ccl::immediate)
                                 (elt ccl::%builtin-functions% index))
                 (second args))))
      (ccl::call
       (when (and *b-float-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
         (member (first (ccl::acode-operands (first args))) '(%float-add %float-sub %float-mul %float-div %float-lt %float-le %float-eq %float-ne %float-ge %float-gt %float-single %float-double)))
        (unless (and (null (third args)) (null (second (second args)))) (refuse :float-spread))
        (return-from b-multiple (b-float-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when (and *b-integer-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%numeric-operation %numeric-operands)))
         (return-from b-multiple (b-numeric-field (first (ccl::acode-operands (first args))) (first (second args)))))
       (when (and *b-integer-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :integer-spread))
         (return-from b-multiple (b-integer-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(gd_condition gd_condition_gf gd_condition_args)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :gd-constructor-spread))
         (return-from b-multiple (gd-condition-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%wasm-symbol-value %wasm-set)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :symbol-access-spread))
         (return-from b-multiple (b-symbol-access (first (ccl::acode-operands (first args))) (first (second args)))))
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (eq (first (ccl::acode-operands (first args))) '%wasm-poll))
         (unless (and (null (third args)) (equal (second args) '(nil nil))) (refuse :poll-arity))
         (return-from b-multiple (b-poll)))
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%wasm-make-restart %wasm-find-restart %wasm-invoke-restart %wasm-restart-name %wasm-svref %wasm-condition-datum %wasm-condition-expected %wasm-cell-name)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :b-restart-spread))
         (return-from b-multiple (if (eq (first (ccl::acode-operands (first args))) '%wasm-svref) (b-svref (first (second args))) (if (member (first (ccl::acode-operands (first args))) '(%wasm-condition-datum %wasm-condition-expected %wasm-cell-name)) (b-condition-field (first (ccl::acode-operands (first args))) (first (second args))) (b-restart-call (first (ccl::acode-operands (first args))) (first (second args)))))))
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(signal error)))
         (when *bootstrap-front-end*
           (unless (and (null (third args)) (null (second (second args))))
             (refuse :bootstrap-signal-spread))
           (return-from b-multiple
             (bootstrap-signal (first (second args))
                               (eq (first (ccl::acode-operands (first args))) 'error))))
         (unless (and (null (third args)) (null (second (second args))) (= (length (first (second args))) 1)) (refuse :b-signal-arity))
         (return-from b-multiple (b-signal (first (first (second args))) (eq (first (ccl::acode-operands (first args))) 'error))))
       (if (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                (eq (first (ccl::acode-operands (first args))) '%wasm-literal-apply))
         (b-literal-apply (second args))
         (if (third args)
           (if (or (eq (third args) t) (and *bootstrap-front-end* (eql (third args) 0)))
             (b-apply (first args) (second args) nil 0 (third args)) (refuse :b-spread-kind))
           (b-call (first args) (second args)))))
      (ccl::values
       (let* ((forms (first args)) (n (length forms)))
         ;; Capacity is a runtime resource, not a fixed language limit.
         (b-frame n (lambda (base)
           (with-output-to-string (s)
             (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) base (b-scalar f)))
             (write-string (b-ensure-results (b-wat "(i32.const ~d)" n)) s)
             (format s "(memory.copy (local.get $results) ~a (i32.const ~d)) (local.set $count (i32.const ~d))" (b-at base 8) (* 4 n) n))))))
      (ccl::progn
       (with-output-to-string (s)
         (loop for rest on (first args) do
           (write-string (if (cdr rest) (b-wat "(drop ~a)" (b-scalar (car rest))) (b-multiple (car rest))) s))))
      (ccl::if
       (b-wat "(if (i32.ne ~a (i32.const ~d)) (then ~a) (else ~a))" (b-scalar (first args)) wasm32::canonical-nil-value (b-multiple (second args)) (b-multiple (third args))))
      ((ccl::multiple-value-prog1 ccl::prog1)
       (let ((forms (first args)) (saved (temporary)))
         (concatenate 'string
           (if (eq op 'ccl::prog1)
             (b-wat "(local.set $value ~a) ~a (i32.store (local.get $results) (local.get $value)) (local.set ~a (i32.const 1))" (b-scalar (first forms)) (b-ensure-results "(i32.const 1)") saved)
             (b-wat "~a (local.set ~a (local.get $count))" (let ((*b-tail-position* nil)) (b-multiple (first forms))) saved))
           (b-retained-frame (b-local saved) (lambda (base)
             (with-output-to-string (s)
               (format s "(memory.copy ~a (local.get $results) (i32.mul (local.get ~a) (i32.const 4)))" (b-at base 8) saved)
               (dolist (f (cdr forms)) (format s "(drop ~a)" (b-scalar f)))
               (format s "(local.set $count (local.get ~a)) ~a (memory.copy (local.get $results) ~a (i32.mul (local.get $count) (i32.const 4)))" saved (b-ensure-results "(local.get $count)") (b-at base 8))))))))
      (t (b-wat "(local.set $value ~a) ~a (i32.store (local.get $results) (local.get $value)) (local.set $count (i32.const 1))" (b-scalar ir) (b-ensure-results "(i32.const 1)"))))))
;;; A callee may use ordinary four-word scratch even when its caller requests
;;; dynamic delivery. Prove the storage bound from this function's own IR;
;;; never infer a named callee's behavior from its current function cell.
(defun b-small-result-scratch-p (ir)
  (labels ((walk (x)
             (cond ((ccl::acode-p x)
                    (let ((op (ccl::acode-operator-name (ccl::acode-operator x)))
                          (a (ccl::acode-operands x)))
                      (and (member op '(nil t ccl::fixnum ccl::lambda-list ccl::immediate ccl::lexical-reference
                                        ccl::special-ref ccl::bound-special-ref ccl::setq-lexical
                                        ccl::setq-special ccl::%function ccl::closed-function
                                        ccl::simple-function ccl::cons ccl::list ccl::eq
                                        ccl::typed-form ccl::%decls-body
                                        ccl::car ccl::cdr ccl::%car ccl::%cdr
                                        ccl::rplaca ccl::rplacd ccl::%rplaca ccl::%rplacd
                                        ccl::values ccl::progn ccl::if ccl::let ccl::let*
                                        ccl::multiple-value-prog1 ccl::prog1))
                           (or (not (eq op 'ccl::values)) (<= (length (first a)) 4))
                           (or (eq op 'ccl::immediate) (every #'walk a)))))
                   ((consp x) (every #'walk x))
                   (t t))))
    (walk ir)))
(defun b-one-module (afunc)
  (let* ((*pool-current* afunc) (ir (ccl::afunc-acode afunc)) (args (ccl::acode-operands ir))
         (small-result-scratch (b-small-result-scratch-p ir))
         (delivery-mode (if small-result-scratch "(i32.load offset=20 (local.get $context))" "(local.get $dynamic_results)")))
    (unless (and (eq (ccl::acode-operator-name (ccl::acode-operator ir)) 'ccl::lambda-list)
                 (or *bootstrap-front-end* (not (consp (third args)))) (or *bootstrap-front-end* (equal (fifth args) '(nil nil)))) (refuse :b-lambda))
    (let* ((*required-vars* (first args)) (*temporary-count* 0) (*b-exception-count* 0) (*b-condition-used* nil) (*b-restart-used* nil) (*b-imports* nil) (*b-keywords* nil) (*b-symbols* nil) (*b-code-imports* nil)
           (*b-inherited* (cdr (assoc afunc *b-environments* :test #'eq)))
           (opt (second args)) (keys (fourth args)) (lexpr (consp (third args))) (rest (if lexpr (car (third args)) (third args))) (aux (fifth args))
           (*b-bound-vars* (remove-duplicates
             (append (first aux) (remove nil (append (first opt) (third opt) (list rest) (second keys) (third keys)))
                     (b-local-variables ir)
                     (remove-if-not #'b-captured-p *required-vars*)) :test #'eq))
           (*b-blocks* nil) (*b-local-tags* nil)
           (implicit-runtime (b-implicit-runtime))
           (arity (length *required-vars*)) (maximum (+ arity (length (first opt))))
           (dynamic-parameters (some #'b-special-p (remove nil (append *required-vars* (first aux) (first opt) (third opt) (list rest) (second keys) (third keys)))))
           (code (let ((prepare (concatenate 'string (metadata-entry afunc) (or (b-environment-entry) "") (b-initialize-cells)))
                       (key-scan (or (b-keyword-scan arity opt keys) "")))
                   (flet ((emit-body () (concatenate 'string
                      (with-output-to-string (s)
                        (loop for v in *required-vars* for i from 0 when (or (b-special-p v) (member v *b-bound-vars* :test #'eq)) do
                          (write-string (b-bind-value v (b-wat "(i32.load offset=~d (local.get $incoming))" (* 4 i))) s)))
                      (b-binding-code arity opt keys (unless lexpr rest))
                      (with-output-to-string (s)
                        (loop for var in (first aux) for init in (second aux) do
                          (write-string (b-bind-value var (b-scalar init)) s)))
                      (let ((*b-tail-position* (not (or dynamic-parameters lexpr)))) (if lexpr (b-multiple (make-b-raw-code :text (b-scalar (sixth args)))) (b-multiple (sixth args)))))))
                   (concatenate 'string prepare key-scan (flet ((emit-arguments () (if lexpr (bootstrap-lexpr rest maximum #'emit-body) (emit-body)))) (if dynamic-parameters (b-special-extent #'emit-arguments) (emit-arguments)))))))
           (restore (concatenate 'string (b-store wasm32::tcr.vsp "(local.get $incoming)")
                     (b-store wasm32::tcr.mv_base "(local.get $output)") (b-store wasm32::tcr.mv_owner_top "(local.get $owner)")
                     (b-store wasm32::tcr.root_head "(local.get $root)")))
           (restart-runtime (when *b-restart-used* (b-restart-runtime)))
           (entry-roots (b-runtime-roots "(local.get $frame)" (b-wat "(i32.add (local.get $capacity) (i32.const ~d))" (length *b-bound-vars*))))
           (wat (with-output-to-string (s)
             (format s "(module (type $b_entry (func (param i32 i32) (result i32 i32))) (type $tail_entry (func (param i32 i32 i32) (result i32 i32))) (import \"env\" \"memory\" (memory 1 32769~a)) (import \"env\" \"tcr\" (global $tcr i32)) (import \"env\" \"table\" (table 0 funcref)) (import \"env\" \"tail_table\" (table $tail_slots 0 funcref)) (import \"env\" \"code_registry\" (global $code_registry i32)) (import \"env\" \"call_error\" (tag $call_error (param i32))) (import \"env\" \"type_error\" (tag $type_error (param i32 i32))) (import \"env\" \"nonlocal_exit\" (tag $nonlocal_exit (param i32)))" (if *wasm32-template-memory* "" " shared"))
             (when *b-float-service* (write-string "(import \"floating\" \"calculate\" (func $float_slow (param i32 i32 i32) (result i32)))" s))
             (when *b-integer-service* (write-string "(import \"integer\" \"calculate\" (func $integer_slow (param i32 i32) (result i32)))" s))
             (when *b-allocation-retry* (write-string "(import \"owner\" \"ensure\" (func $owner_ensure (param i32)))" s))
             (dolist (name (sort *b-keywords* #'string<))
               (format s "(import \"keywords\" ~s (global $key_~a i32))" name name))
             (dolist (name (sort *b-symbols* #'string<))
               (format s "(import \"symbols\" ~s (global $symbol_~a i32))" name name))
             (dolist (entry *b-code-imports*)
               (format s "(import \"codes\" ~s (global $code_~a i32))" (second entry) (second entry)))
             (when *b-allocation-retry* (write-string (b-allocation-runtime) s))
             (when *b-integer-service* (write-string (b-integer-runtime) s))
             (when *b-float-service* (write-string (b-float-runtime) s))
             (write-string (b-object-runtime) s)
             (write-string implicit-runtime s)
             (when restart-runtime (write-string restart-runtime s))
             (when *b-condition-used* (write-string (b-condition-runtime) s))
             (write-string (b-control-runtime) s) (write-string (b-stacks-runtime) s)
             (write-string (b-dynamic-runtime) s) (write-string (b-unbound-runtime) s)
             (write-string (b-progv-runtime) s)
             (write-string (b-result-runtime) s)
             (write-string "(func $body (export \"tail_entry\") (type $tail_entry) (param $self i32) (param $nargs i32) (param $context i32) (result i32 i32) (local $incoming i32) (local $output i32) (local $owner i32) (local $root i32) (local $old_count i32) (local $frame i32) (local $results i32) (local $top i32) (local $count i32) (local $value i32) (local $exception exnref) (local $wide i64) (local $capacity i32) (local $result_bytes i32) (local $bindings i32) (local $dispatch_self i32) (local $dispatch_slot i32) (local $closure_env i32) (local $dynamic_results i32) (local $result_descriptor i32) (local $result_scope i32)" s)
             (dotimes (i *temporary-count*) (format s "(local $tmp~d i32)" i))
             (dotimes (i *b-exception-count*) (format s "(local $cleanup_exception~d exnref)" i))
             (format s "(local.set $incoming ~a) (local.set $output ~a) (local.set $owner ~a) (local.set $root ~a) (local.set $old_count ~a) (local.set $top (i32.add (local.get $context) (i32.add (i32.const 48) (i32.and (i32.add (i32.mul (local.get $nargs) (i32.const 4)) (i32.const 15)) (i32.const -16))))) (local.set $top (i32.add (local.get $top) (i32.load offset=24 (local.get $context))))"
               (b-load wasm32::tcr.vsp) (b-load wasm32::tcr.mv_base) (b-load wasm32::tcr.mv_owner_top) (b-load wasm32::tcr.root_head) (b-load wasm32::tcr.mv_count))
             (write-string (b-condition (b-wat "(i32.or (i32.lt_u (local.get $nargs) (i32.const ~d)) (i32.gt_u (local.get $nargs) (i32.const ~d)))" arity (if (or keys rest) #xffffffff maximum)) 1) s)
             (write-string (b-condition "(i32.or (i32.lt_u (local.get $incoming) (i32.load offset=68 (global.get $tcr))) (i32.and (i32.or (local.get $incoming) (i32.or (local.get $output) (local.get $owner))) (i32.const 15)))" 2) s)
             (write-string (b-condition "(i32.or (i32.gt_u (local.get $output) (local.get $owner)) (i32.gt_u (local.get $owner) (i32.load offset=72 (global.get $tcr))))" 2) s)
             (write-string (b-condition "(i64.gt_u (i64.extend_i32_u (i32.load offset=72 (global.get $tcr))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" 2) s)
             (write-string (b-condition "(i32.or (i32.ne (local.get $incoming) (i32.add (local.get $context) (i32.const 48))) (i32.ne (local.get $root) (i32.add (local.get $context) (i32.const 32))))" 2) s)
             (write-string "(block $caught (result exnref) (try_table (catch_all_ref $caught) (local.set $frame (local.get $top))" s)
             (write-string (if small-result-scratch "(local.set $dynamic_results (i32.const 0))" "(local.set $dynamic_results (i32.load offset=20 (local.get $context)))") s)
             ;; At least four scratch words permit scalar evaluation even with an
             ;; empty final reservation. Child reservations inherit this budget.
             (format s "(local.set $result_bytes (if (result i32) ~a (then (i32.const 16)) (else (i32.sub (local.get $owner) (local.get $output))))) (if (i32.lt_u (local.get $result_bytes) (i32.const 16)) (then (local.set $result_bytes (i32.const 16)))) (local.set $capacity (i32.div_u (local.get $result_bytes) (i32.const 4)))" delivery-mode)
             (write-string (b-reserve-runtime (b-wat "(i64.and (i64.add (i64.extend_i32_u (local.get $result_bytes)) (i64.const ~d)) (i64.const -16))" (+ 23 (* 4 (length *b-bound-vars*))))) s)
             (write-string entry-roots s)
             (write-string "(local.set $bindings (i32.add (local.get $frame) (i32.add (i32.const 8) (local.get $result_bytes))))" s)
             (write-string "(local.set $result_scope (local.get $frame)) (local.set $results (i32.add (local.get $frame) (i32.const 8)))" s)
             (write-string "(if (local.get $dynamic_results) (then (local.set $result_descriptor (local.get $top))" s)
             (write-string (b-reserve 48) s)
             (write-string (b-result-descriptor "(local.get $result_descriptor)" "(local.get $frame)") s)
             (write-string "))" s)
             (write-string code s)
             (format s "(if ~a (then (if (i32.load offset=20 (i32.load offset=28 (local.get $context))) (then (local.set $root (i32.load offset=24 (i32.load offset=28 (local.get $context)))))) (local.set $output (call $rv_deliver (i32.load offset=28 (local.get $context)) (local.get $results) (local.get $count) (local.get $top)))) (else" delivery-mode)
             (write-string (b-condition "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $output)) (i64.mul (i64.extend_i32_u (local.get $count)) (i64.const 4))) (i64.extend_i32_u (local.get $owner)))" 3) s)
             (write-string "))" s)
             (format s "(local.set $value (if (result i32) (local.get $count) (then (i32.load (local.get $results))) (else (i32.const 77825)))) (if (i32.eqz ~a) (then (memory.copy (local.get $output) (local.get $results) (i32.mul (local.get $count) (i32.const 4)))))" delivery-mode)
             (write-string "(if (local.get $dynamic_results) (then (call $rv_release (local.get $frame))))" s)
             (write-string restore s)
             (write-string (b-store wasm32::tcr.mv_count "(local.get $count)") s)
             (write-string "(return (local.get $value) (local.get $count))) unreachable) (local.set $exception)" s)
             (write-string "(if (local.get $dynamic_results) (then (call $rv_release (local.get $frame))))" s)
             (write-string restore s)
             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)
             (write-string "(throw_ref (local.get $exception)))" s)
             (write-string (b-entry-wrapper arity maximum (or keys rest) (length *b-bound-vars*)) s)
             (write-char #\) s))))
      (list :symbols (copy-list *bootstrap-symbols*)
            :callees (copy-list *bootstrap-callees*)
            :pool (cdr (assoc afunc *pool-layouts* :test #'eq)) :name *module-name* :arity arity :wat wat :imports *b-imports* :bound-words (length *b-bound-vars*) :captures (length *b-inherited*)))))
;;; Rest/APPLY sequences execute without calls, polls or collection while
;;; traversing or initializing heap cells. The allocator is a checked bump
;;; pointer in the thread-owned TCR area; exhaustion never publishes a list.
(defun b-rest-binding (var start)
  (let ((n (temporary)) (cursor (temporary)) (head (temporary)) (index (temporary)))
    (with-output-to-string (s)
      (format s "(local.set ~a (if (result i32) (i32.gt_u (local.get $nargs) (i32.const ~d)) (then (i32.sub (local.get $nargs) (i32.const ~d))) (else (i32.const 0)))) (local.set ~a (i32.const 77825))" n start start head)
      (format s "(if (local.get ~a) (then " n)
      (when *b-allocation-retry*
        (write-string (b-condition (b-wat "(i64.gt_u (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 8)) (i64.const 4294967295))" n) 6) s)
        (format s "(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 8))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.mul (local.get ~a) (i32.const 8)))))" n n))
      (format s "(local.set ~a ~a)" cursor (b-load wasm32::tcr.alloc_pointer))
      (write-string (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) ~a) (i32.and (local.get ~a) (i32.const 7)))" cursor (b-load wasm32::tcr.alloc_base) cursor) 6) s)
      (write-string (b-condition (b-wat "(i64.gt_u (i64.extend_i32_u ~a) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" (b-load wasm32::tcr.alloc_limit)) 6) s)
      (format s "(local.set $wide (i64.add (i64.extend_i32_u (local.get ~a)) (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 8))))" cursor n)
      (write-string (b-condition (b-wat "(i64.gt_u (local.get $wide) (i64.extend_i32_u ~a))" (b-load wasm32::tcr.alloc_limit)) 6) s)
      ;; Allocate backwards through the argument sequence, with CDR first.
      (format s "(local.set ~a (local.get $nargs)) (loop $rest_cells (local.set ~a (i32.sub (local.get ~a) (i32.const 1))) (i32.store (local.get ~a) (local.get ~a)) (i32.store offset=4 (local.get ~a) (i32.load (i32.add (local.get $incoming) (i32.mul (local.get ~a) (i32.const 4))))) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (local.set ~a (i32.add (local.get ~a) (i32.const 8))) (br_if $rest_cells (i32.gt_u (local.get ~a) (i32.const ~d))))"
        index index index cursor head cursor index head cursor cursor cursor index start)
      (write-string (b-store wasm32::tcr.alloc_pointer (b-local cursor)) s)
      (write-string "))" s)
      (write-string (b-bind-value var (b-local head)) s))))
(defun b-checked-cdr (node &optional whole-list) (when whole-list (pushnew "expected_proper_list" *b-symbols* :test #'equal))
  (b-wat "(block (result i32) ~a ~a (i32.load (i32.sub ~a (i32.const 1))))"
    (b-wat "(if (i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d)) (then ~a))" node wasm32::fulltagmask wasm32::fulltag-cons (if whole-list (b-wat "(call $implicit_error_details (i32.const 5) (local.get $top) ~a (global.get $symbol_expected_proper_list)) unreachable" whole-list) (b-type-failure node 'list)))
    (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.const 7)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" node) 5) node))
(defun b-apply (callee argument-list &optional local-self (ephemeral-bytes 0) (spread-kind t))
  (when (and *bootstrap-front-end* (not local-self)
             (not (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)))
    (setq *bootstrap-dynamic-call* t))
  (unless *b-tail-position* (return-from b-apply (b-internal-apply callee argument-list local-self spread-kind)))
  (unless (= (length (second argument-list)) 1) (refuse :b-apply-shape))
  (let* ((prefix (first argument-list)) (n (length prefix))
         (evaluated (temporary)) (base (temporary)) (root (temporary))
         (mv (temporary)) (owner (temporary)) (vsp (temporary)) (old-count (temporary))
         (cursor (temporary)) (slow (temporary)) (length (temporary)) (total (temporary))
         (output (temporary)) (roots (temporary)) (index (temporary))
         (op (and callee (ccl::acode-operator-name (ccl::acode-operator callee))))
         (name (and (eq op 'ccl::immediate) (first (ccl::acode-operands callee))))
         (direct (and (eq op 'ccl::immediate) (symbolp name)
                      (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))
         (self (or local-self (if direct (b-symbol name) (b-scalar callee))))
         (codes (mapcar #'b-scalar prefix)) (tail (b-scalar (first (second argument-list)))))
    (when (and name (not direct)) (refuse :b-unlinked-function))

    (with-output-to-string (s)
      (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
        evaluated root (b-load wasm32::tcr.root_head) mv (b-load wasm32::tcr.mv_base)
        owner (b-load wasm32::tcr.mv_owner_top) vsp (b-load wasm32::tcr.vsp) old-count (b-load wasm32::tcr.mv_count))
      (write-string (b-reserve (* 16 (ceiling (+ 16 (* 4 n)) 16))) s)
      (write-string (b-initialize-roots (b-local evaluated) (+ 2 n)) s)
      (format s "(i32.store offset=8 (local.get ~a) ~a)" evaluated self)
      (loop for code in codes for i from 0 do (format s "(i32.store offset=~d (local.get ~a) ~a)" (+ 16 (* 4 i)) evaluated code))
      (format s "(i32.store offset=12 (local.get ~a) ~a) (local.set ~a (i32.load offset=12 (local.get ~a))) (local.set ~a (local.get ~a)) (local.set ~a (i32.const 0))"
        evaluated tail cursor evaluated slow cursor length)
      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-count (b-local cursor) length) s)
        (progn
      ;; Ordinary list spread: one cursor advances on every step, the other on alternate steps.
      ;; Check against the available stack on every step as well as detecting
      ;; cycles: finite malformed input cannot wrap the count or exhaust JS.
      (format s "(block $list_done (loop $list_check (br_if $list_done (i32.eq (local.get ~a) (i32.const 77825))) (local.set ~a ~a) (local.set ~a (i32.add (local.get ~a) (i32.const 1)))"
        cursor cursor (b-checked-cdr (b-local cursor) (b-wat "(i32.load offset=12 (local.get ~a))" evaluated)) length length)
      (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.mul (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.const 4))) (i64.extend_i32_u ~a))" length n (b-load wasm32::tcr.vsp_limit)) 2) s)
      (format s "(if (i32.eqz (i32.and (local.get ~a) (i32.const 1))) (then (local.set ~a ~a)))" length slow (b-checked-cdr (b-local slow) (b-wat "(i32.load offset=12 (local.get ~a))" evaluated)))
      (write-string (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (local.get ~a) (local.get ~a)))" cursor cursor slow) 5) s)
      (write-string "(br $list_check)))" s)))
      (format s "(local.set ~a (i32.add (local.get ~a) (i32.const ~d))) (local.set ~a (local.get $top)) (local.set $wide (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 4)) (i64.const 31)) (i64.const -16)))" total length n base total)
      ;; $wide is the output offset (header/self/padding plus aligned args).
      (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.add (i64.add (local.get $wide) (i64.const ~d)) (i64.extend_i32_u (local.get $result_bytes)))) (i64.extend_i32_u ~a))" ephemeral-bytes (b-load wasm32::tcr.vsp_limit)) 2) s)
      (format s "(local.set ~a (i32.add (local.get $top) (i32.add (i32.wrap_i64 (local.get $wide)) (i32.const ~d)))) (local.set ~a (i32.div_u (i32.sub (i32.wrap_i64 (local.get $wide)) (i32.const 8)) (i32.const 4))) (local.set $top (i32.add (local.get ~a) (local.get $result_bytes)))"
        output ephemeral-bytes roots output)
      (format s "(i32.store (local.get ~a) ~a) (i32.store offset=4 (local.get ~a) (local.get ~a)) (local.set ~a (i32.const 0)) (loop $apply_roots (i32.store (i32.add (local.get ~a) (i32.add (i32.const 8) (i32.mul (local.get ~a) (i32.const 4)))) (i32.const 77825)) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br_if $apply_roots (i32.lt_u (local.get ~a) (local.get ~a))))"
        base (b-load wasm32::tcr.root_head) base roots index base index index index index roots)
      (write-string (b-store wasm32::tcr.root_head (b-local base)) s)
      (format s "(i32.store offset=8 (local.get ~a) (i32.load offset=8 (local.get ~a))) (memory.copy ~a ~a (i32.const ~d)) (local.set ~a (i32.load offset=12 (local.get ~a))) (local.set ~a (i32.const ~d))"
        base evaluated (b-at (b-local base) 16) (b-at (b-local evaluated) 16) (* 4 n) cursor evaluated index n)
      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-copy cursor length index n base 16) s)
      (format s "(block $spread_done (loop $spread_copy (br_if $spread_done (i32.eq (local.get ~a) (i32.const 77825))) (i32.store (i32.add (local.get ~a) (i32.add (i32.const 16) (i32.mul (local.get ~a) (i32.const 4)))) (i32.load offset=3 (local.get ~a))) (local.set ~a (i32.load (i32.sub (local.get ~a) (i32.const 1)))) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $spread_copy)))"
        cursor base index cursor cursor cursor index index))
      (write-string (b-store wasm32::tcr.vsp (b-at (b-local base) 16)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local output)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top "(local.get $top)") s)
      (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
      (format s "(call $resolve_lisp (i32.load offset=8 (local.get ~a)) (local.get $top)) (local.set $dispatch_slot) (local.set $dispatch_self) (i32.store offset=8 (local.get ~a) (local.get $dispatch_self))" base base)
      (write-string (if *b-tail-position*
                      (b-tail-transfer (b-at (b-local base) 16) (b-local total) ephemeral-bytes)
                      (b-wat "(call_indirect (type $b_entry) (local.get $dispatch_self) ~a (local.get $dispatch_slot))" (b-local total))) s)
      (write-string "(local.set $count) (local.set $value)" s)
      (write-string (b-ensure-results "(local.get $count)") s)
      (format s "(if (i32.eqz (local.get $dynamic_results)) (then (memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))))" output)
      (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
      (write-string (b-store wasm32::tcr.mv_count (b-local old-count)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" evaluated))))

(defun b-internal-apply (callee argument-list local-self &optional (spread-kind t))
  (when (and *bootstrap-front-end* (not local-self)
             (not (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)))
    (setq *bootstrap-dynamic-call* t))
  (unless (= (length (second argument-list)) 1) (refuse :b-apply-shape))
  (let* ((prefix (first argument-list)) (n (length prefix))
         (evaluated (temporary)) (base (temporary)) (root (temporary))
         (mv (temporary)) (owner (temporary)) (vsp (temporary)) (old-count (temporary))
         (cursor (temporary)) (slow (temporary)) (length (temporary)) (total (temporary))
         (output (temporary)) (context (temporary)) (roots (temporary)) (index (temporary))
         (op (and callee (ccl::acode-operator-name (ccl::acode-operator callee))))
         (name (and (eq op 'ccl::immediate) (first (ccl::acode-operands callee))))
         (direct (and (eq op 'ccl::immediate) (symbolp name)
                      (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))
         (self (or local-self (if direct (b-symbol name) (b-scalar callee))))
         (codes (mapcar #'b-scalar prefix)) (tail (b-scalar (first (second argument-list)))))
    (when (and name (not direct)) (refuse :b-unlinked-function))

    (with-output-to-string (s)
      (format s "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a) (local.set ~a ~a)"
        evaluated root (b-load wasm32::tcr.root_head) mv (b-load wasm32::tcr.mv_base)
        owner (b-load wasm32::tcr.mv_owner_top) vsp (b-load wasm32::tcr.vsp) old-count (b-load wasm32::tcr.mv_count))
      (write-string (b-reserve (* 16 (ceiling (+ 16 (* 4 n)) 16))) s)
      (write-string (b-initialize-roots (b-local evaluated) (+ 2 n)) s)
      (format s "(i32.store offset=8 (local.get ~a) ~a)" evaluated self)
      (loop for code in codes for i from 0 do (format s "(i32.store offset=~d (local.get ~a) ~a)" (+ 16 (* 4 i)) evaluated code))
      (format s "(i32.store offset=12 (local.get ~a) ~a) (local.set ~a (i32.load offset=12 (local.get ~a))) (local.set ~a (local.get ~a)) (local.set ~a (i32.const 0))"
        evaluated tail cursor evaluated slow cursor length)
      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-count (b-local cursor) length) s)
        (progn
      ;; Ordinary list spread: one cursor advances on every step, the other on alternate steps.
      ;; Check against the available stack on every step as well as detecting
      ;; cycles: finite malformed input cannot wrap the count or exhaust JS.
      (format s "(block $list_done (loop $list_check (br_if $list_done (i32.eq (local.get ~a) (i32.const 77825))) (local.set ~a ~a) (local.set ~a (i32.add (local.get ~a) (i32.const 1)))"
        cursor cursor (b-checked-cdr (b-local cursor) (b-wat "(i32.load offset=12 (local.get ~a))" evaluated)) length length)
      (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.mul (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.const 4))) (i64.extend_i32_u ~a))" length n (b-load wasm32::tcr.vsp_limit)) 2) s)
      (format s "(if (i32.eqz (i32.and (local.get ~a) (i32.const 1))) (then (local.set ~a ~a)))" length slow (b-checked-cdr (b-local slow) (b-wat "(i32.load offset=12 (local.get ~a))" evaluated)))
      (write-string (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (local.get ~a) (local.get ~a)))" cursor cursor slow) 5) s)
      (write-string "(br $list_check)))" s)))

      (format s "(local.set ~a (i32.add (local.get ~a) (i32.const ~d))) (local.set ~a (local.get $top)) (local.set ~a (i32.add (local.get $top) (local.get $result_bytes)))"
        total length n output context)
      (write-string (b-reserve-runtime (b-wat "(i64.add (i64.extend_i32_u (local.get $result_bytes)) (i64.add (i64.const 48) (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 4)) (i64.const 15)) (i64.const -16))))" total)) s)
      (format s "(local.set ~a (i32.div_u (i32.and (i32.add (i32.mul (local.get ~a) (i32.const 4)) (i32.const 15)) (i32.const -16)) (i32.const 4)))" roots total)
      ;; Keep the evaluation frame linked through the copy. No calls/polls occur
      ;; until SELF, prefix and spread list values occupy their final root slots.
      (write-string (b-prepare-context (b-local context) (b-local output) (b-local evaluated) (b-local roots)) s)
      (format s "(i32.store offset=40 (local.get ~a) (i32.load offset=8 (local.get ~a))) (memory.copy ~a ~a (i32.const ~d)) (local.set ~a (i32.load offset=12 (local.get ~a))) (local.set ~a (i32.const ~d))"
        context evaluated (b-at (b-local context) 48) (b-at (b-local evaluated) 16) (* 4 n) cursor evaluated index n)
      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-copy cursor length index n context 48) s)
      (format s "(block $spread_done (loop $spread_copy (br_if $spread_done (i32.eq (local.get ~a) (i32.const 77825))) (i32.store (i32.add (local.get ~a) (i32.add (i32.const 48) (i32.mul (local.get ~a) (i32.const 4)))) (i32.load offset=3 (local.get ~a))) (local.set ~a (i32.load (i32.sub (local.get ~a) (i32.const 1)))) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $spread_copy)))"
        cursor context index cursor cursor cursor index index))
      (format s "(i32.store offset=12 (local.get ~a) (local.get ~a)) (i32.store offset=32 (local.get ~a) (local.get ~a)) (call $resolve_lisp (i32.load offset=40 (local.get ~a)) (local.get $top)) (local.set $dispatch_slot) (local.set $dispatch_self) (i32.store offset=40 (local.get ~a) (local.get $dispatch_self))" context root context root context context)
      (write-string (b-store wasm32::tcr.vsp (b-at (b-local context) 48)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local output)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local context)) s)
      (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
      (when *b-producer-target*
        (format s "(i32.store offset=28 (local.get ~a) ~a)" context *b-producer-target*))
      (write-string (b-internal-dispatch (b-local context) (b-local total)) s)
      (write-string "(local.set $count) (local.set $value)" s)
      (if *b-producer-target*
        (format s "(local.set $results (i32.load offset=8 ~a))" *b-producer-target*)
        (write-string (b-ensure-results "(local.get $count)") s))
      (format s "(if (i32.eqz (local.get $dynamic_results)) (then (memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))))" output)
      (write-string (b-store wasm32::tcr.vsp (b-local vsp)) s)
      (write-string (b-store wasm32::tcr.mv_base (b-local mv)) s)
      (write-string (b-store wasm32::tcr.mv_owner_top (b-local owner)) s)
      (write-string (b-store wasm32::tcr.mv_count (b-local old-count)) s)
      (write-string (b-store wasm32::tcr.root_head (b-local root)) s)
      (format s "(local.set $top (local.get ~a))" evaluated))))

;;; Logical callable-object proposal v1. Function fields are tagged; registry
;;; metadata is raw. Symbol layout is D1's seven-slot object. No native code
;;; vector, host pointer or name-based resolver is admitted.
(defun b-object-runtime ()
  (b-wat "(func $span (param $p i32) (param $n i32)
    (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 4)))))
  (func $object_base (param $node i32) (param $bytes i32) (param $header i32) (result i32) (local $p i32)
    (if (i32.ne (i32.and (local.get $node) (i32.const 7)) (i32.const 6)) (then (throw $call_error (i32.const 4))))
    (local.set $p (i32.sub (local.get $node) (i32.const 6)))
    (call $span (local.get $p) (local.get $bytes))
~a    (if (i32.ne (i32.load (local.get $p)) (local.get $header)) (then (throw $call_error (i32.const 4)))) (local.get $p))
  (func $function_value (param $symbol i32) (result i32) (local $node i32)
    (local.set $node (i32.load offset=12 (call $object_base (local.get $symbol) (i32.const 32) (i32.const 1850))))
    (drop (call $object_base (local.get $node) (i32.const 32) (i32.const 1578))) (local.get $node))
  (func $resolve (param $node i32) (result i32 i32) (local $p i32) (local $id i32) (local $row i32) (local $slot i32) (local $cap i32) (local $version i32) (local $wide i64)
    (if (i32.ne (i32.and (local.get $node) (i32.const 7)) (i32.const 6)) (then (throw $call_error (i32.const 4))))
    (call $span (i32.sub (local.get $node) (i32.const 6)) (i32.const 4))
    (if (i32.eq (i32.load (i32.sub (local.get $node) (i32.const 6))) (i32.const 1850)) (then (local.set $node (call $function_value (local.get $node)))))
    (local.set $p (call $object_base (local.get $node) (i32.const 32) (i32.const 1578)))
    (local.set $id (i32.load offset=4 (local.get $p)))
    (if (i32.or (i32.and (local.get $id) (i32.const 3)) (i32.le_s (local.get $id) (i32.const 0))) (then (throw $call_error (i32.const 4))))
    (local.set $id (i32.shr_u (local.get $id) (i32.const 2)))
    (local.set $version (i32.load offset=12 (local.get $p)))
    (if (i32.or (i32.and (local.get $version) (i32.const 3)) (i32.le_s (local.get $version) (i32.const 0))) (then (throw $call_error (i32.const 4))))
    (if (i32.and (global.get $code_registry) (i32.const 7)) (then (throw $call_error (i32.const 4))))
    (call $span (global.get $code_registry) (i32.const 8))
    (local.set $cap (i32.load (global.get $code_registry)))
    (if (i32.or (i32.ge_u (local.get $id) (local.get $cap)) (i32.ne (i32.load offset=4 (global.get $code_registry)) (i32.const 1))) (then (throw $call_error (i32.const 4))))
    (local.set $wide (i64.add (i64.extend_i32_u (global.get $code_registry)) (i64.add (i64.const 8) (i64.mul (i64.extend_i32_u (local.get $id)) (i64.const 16)))))
    (if (i64.gt_u (i64.add (local.get $wide) (i64.const 16)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 4))))
    (local.set $row (i32.wrap_i64 (local.get $wide)))
    (if (i32.or (i32.ne (i32.load offset=12 (local.get $p)) (i32.load offset=4 (local.get $row))) (i32.or (i32.ne (i32.load offset=8 (local.get $row)) (i32.const 17)) (i32.ne (i32.load offset=12 (local.get $row)) (i32.const 23)))) (then (throw $call_error (i32.const 4))))
    (local.set $slot (i32.load (local.get $row)))
    (if (i32.or (i32.eqz (local.get $slot)) (i32.ge_u (local.get $slot) (table.size))) (then (throw $call_error (i32.const 4))))
    (if (ref.is_null (table.get (local.get $slot))) (then (throw $call_error (i32.const 4))))
    (local.get $node) (local.get $slot))"
    (if *bootstrap-front-end*
      "(if (i32.and (i32.eq (local.get $header) (i32.const 1578))
                    (i32.eq (i32.load (local.get $p)) (i32.const 1834)))
        (then (call $span (local.get $p) (i32.const 32))
              (drop (call $object_base (i32.load offset=28 (local.get $p)) (i32.const 32) (i32.const 2042)))
              (local.set $header (i32.const 1834))))
"
      "")))

;;; Closure proposal: function.environment -> D1 simple-vector of shared cons
;;; cells. A cell's CAR is its mutable value; CDR is NIL. No code is in the heap.
;;; Allocation/publication after assurance contains no calls or polls.
(defun b-captured-p (var) (member (ccl::nx-root-var var) *b-captured* :test #'eq))
(defun b-local-variables (ir)
  (let ((vars nil))
    (labels ((walk (x)
               (cond ((ccl::acode-p x)
                      (let ((op (ccl::acode-operator-name (ccl::acode-operator x))) (args (ccl::acode-operands x)))
                        (when (member op '(ccl::let ccl::let* ccl::flet ccl::labels ccl::multiple-value-bind)) (dolist (v (first args)) (pushnew v vars :test #'eq)))
                        (when (eq op 'ccl::lambda-bind)
                          (dolist (v (append (second args) (list (third args)) (first (fifth args))))
                            (when v (pushnew v vars :test #'eq))))
                        (when (eq op 'ccl::setq-lexical)
                          (let ((v (ccl::nx-root-var (first args))))
                            (when (member v *required-vars* :test #'eq) (pushnew v vars :test #'eq))))
                        (unless (eq op 'ccl::immediate) (mapc #'walk args))))
                     ((consp x) (mapc #'walk x)))))
      (walk ir))
    (nreverse vars)))
(defun b-cell-reference (var)
  (let* ((root (ccl::nx-root-var var)) (n (position root *b-inherited* :test #'eq)))
    (if n (b-wat "(i32.load offset=~d (i32.sub (i32.load offset=2 (i32.load offset=40 (local.get $context))) (i32.const 6)))" (+ 4 (* 4 n)))
      (b-wat "(i32.load ~a)" (b-bound-address root)))))
(defun b-variable-address (var)
  (let* ((root (ccl::nx-root-var var)) (n (position root *required-vars* :test #'eq)))
    (cond ((b-captured-p root) (b-at (b-cell-reference root) 3))
          ((member root *b-bound-vars* :test #'eq) (b-bound-address root))
          (n (b-at "(local.get $incoming)" (* 4 n)))
          (t (refuse :b-variable-identity)))))
(defun b-read-variable (var) (b-wat "(i32.load ~a)" (b-variable-address var)))
(defun b-heap-block (bytes emit)
  (let* ((p (temporary)) (body (funcall emit (b-local p))))
    (b-wat "(block (result i32) ~a(local.set ~a ~a) ~a ~a ~a ~a ~a (local.get ~a))"
      (if *b-allocation-retry* (b-wat "(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.const ~d)) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.const ~d)))) " bytes bytes) "")
      p (b-load wasm32::tcr.alloc_pointer)
      (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) ~a) (i32.and (local.get ~a) (i32.const 7)))" p (b-load wasm32::tcr.alloc_base) p) 6)
      (b-condition (b-wat "(i64.gt_u (i64.extend_i32_u ~a) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" (b-load wasm32::tcr.alloc_limit)) 6)
      (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.extend_i32_u ~a))" p bytes (b-load wasm32::tcr.alloc_limit)) 6)
      body (b-store wasm32::tcr.alloc_pointer (b-at (b-local p) bytes)) p)))
(defun b-initialize-cells ()
  (let ((vars (remove-if-not #'b-captured-p *b-bound-vars*)))
    (if (null vars) ""
      (b-wat "(drop ~a)"
        (b-heap-block (* 8 (length vars))
          (lambda (base)
            (with-output-to-string (s)
              (loop for v in vars for i from 0 do
                (format s "(i32.store offset=~d ~a (i32.const 77825)) (i32.store offset=~d ~a (i32.const 77825)) (i32.store ~a ~a)"
                  (* 8 i) base (+ 4 (* 8 i)) base (b-bound-address v) (b-at base (+ 1 (* 8 i))))))))))))
(defun b-environment-entry ()
  (when *b-inherited*
    (with-output-to-string (s)
      (format s "(local.set $closure_env (call $object_base (i32.load offset=8 (call $object_base (local.get $self) (i32.const 32) (i32.const 1578))) (i32.const ~d) (i32.const ~d)))"
        (* 8 (ceiling (+ 4 (* 4 (length *b-inherited*))) 8)) (+ 250 (* 256 (length *b-inherited*))))
      (dolist (v *b-inherited*)
        (let ((cell (b-cell-reference v)))
          (write-string (b-condition (b-wat "(i32.or (i32.eq ~a (i32.const 77825)) (i32.ne (i32.and ~a (i32.const 7)) (i32.const 1)))" cell cell) 4) s)
          (format s "(call $span (i32.sub ~a (i32.const 1)) (i32.const 8))" cell))))))
(defun b-make-closure (afunc)
  (let* ((entry (assoc afunc *b-functions* :test #'eq))
         (vars (cdr (assoc afunc *b-environments* :test #'eq)))
         (n (length vars)) (bytes (+ 32 (if (zerop n) 0 (* 8 (ceiling (+ 4 (* 4 n)) 8))))))
    (unless entry (refuse :b-closure-code))
    (pushnew entry *b-code-imports* :test #'eq)
    (b-at (funcall (if *b-stack-closure* #'b-stack-block #'b-heap-block) bytes
      (lambda (base)
        (with-output-to-string (s)
          (format s "(i32.store ~a (i32.const 1578)) (i32.store offset=4 ~a (global.get $code_~a)) (i32.store offset=8 ~a ~a) (i32.store offset=12 ~a (i32.const 4)) (i32.store offset=16 ~a ~a) (i32.store offset=20 ~a ~a)"
            base base (second entry) base (if (zerop n) "(i32.const 77825)" (b-at base 38)) base base (metadata-child-load afunc 0) base (metadata-child-load afunc 1))
          (format s "(i32.store offset=24 ~a ~a) (i32.store offset=28 ~a (i32.const 0))" base (pool-child-load afunc) base)
          (when (plusp n)
            (format s "(i32.store offset=32 ~a (i32.const ~d))" base (+ 250 (* 256 n)))
            (loop for v in vars for i from 0 do
              (format s "(i32.store offset=~d ~a ~a)" (+ 36 (* 4 i)) base (b-cell-reference v)))
            (when (evenp n) (format s "(i32.store offset=~d ~a (i32.const 77825))" (+ 36 (* 4 n)) base)))))) 6)))
(defun b-call-pass2 (root)
  (let ((*pool-layouts* nil) (*b-functions* nil) (*b-captured* nil) (*b-function-vars* nil) (*b-environments* nil) (counter 0) (name *module-name*))
    (labels ((collect (f)
               (push (list f (if (eq f root) name (format nil "~a_inner_~d" name (incf counter)))) *b-functions*)
               (dolist (v (ccl::afunc-inherited-vars f)) (pushnew (ccl::nx-root-var v) *b-captured* :test #'eq))
               (mapc #'collect (reverse (ccl::afunc-inner-functions f)))))
      (collect root))
    (setq *b-functions* (nreverse *b-functions*))
    (dolist (entry (rest *b-functions*))
      (when (find (second entry) *b-call-links* :key #'second :test #'equal) (refuse :b-closure-name-collision)))
    (when *b-callable-metadata* (b-plan-local-environments))
    (pool-plan)
    (unless *b-callable-metadata* (b-plan-local-environments))
    (let ((modules (mapcar (lambda (entry) (let ((*module-name* (second entry))) (b-one-module (first entry)))) *b-functions*)))
      (setf (getf (first modules) :children) (rest modules))
      (when *bootstrap-front-end*
        (setf (getf (first modules) :dependencies) (copy-list *bootstrap-callees*)
              (getf (first modules) :dynamic-call) *bootstrap-dynamic-call*
              (getf (first modules) :self-call) *bootstrap-self-call*
              (getf (first modules) :operators) (bootstrap-emitted-operators)))
      (throw *module-result-tag* (first modules)))))

(defun validate-b-source (form)
  (let ((budget 8192) (local-names nil) (blocks nil) (tags nil))
    (labels ((items (x)
               (let ((seen (make-hash-table :test #'eq)) (out nil))
                 (loop while (consp x) do
                   (when (or (gethash x seen) (minusp (decf budget))) (refuse :b-source))
                   (setf (gethash x seen) t) (push (car x) out) (setq x (cdr x)))
                 (when x (refuse :b-source)) (nreverse out)))
             (variable (v)
               (unless (and (symbolp v) v (not (constantp v)) (not (member v lambda-list-keywords))) (refuse :b-source)))
             (body-forms (forms vars depth)
               (let ((scope vars))
                 (loop while (and (consp (car forms)) (eq (caar forms) 'declare)) do
                   (dolist (declaration (cdr (pop forms)))
                     (unless (and (consp declaration) (eq (car declaration) 'special)) (refuse :b-declaration))
                     (dolist (name (cdr declaration)) (variable name) (pushnew name *b-special-names* :test #'eq) (pushnew name scope :test #'eq))))
                 (dolist (form forms) (walk form scope depth))))
             (walk (x vars depth)
               (when (or (> depth 128) (minusp (decf budget))) (refuse :b-source))
               (cond ((or (null x) (eq x t) (and (keywordp x) (b-keyword x))
                          (and (integerp x) (<= -536870912 x 536870911)) (and (atom x) (pool-literal-p x)) (member x vars)) t)
                     ((consp x)
                      (let* ((xs (items x)) (head (car xs)) (n (length (cdr xs))))
                        (case head
                          (lambda (lambda-form xs vars (1+ depth)))
                          (tagbody
                           (let ((new nil) (saved tags))
                             (dolist (part (cdr xs))
                               (when (atom part)
                                 (unless (or (symbolp part) (integerp part)) (refuse :b-tag-source))
                                 (when (member part new :test #'eql) (refuse :b-tag-source))
                                 (push part new)))
                             (unwind-protect
                               (progn (setq tags (append new tags))
                                 (dolist (part (cdr xs)) (when (consp part) (walk part vars (1+ depth)))))
                               (setq tags saved))))
                          (go (unless (and (= n 1) (member (second xs) tags :test #'eql)) (refuse :b-go-source)))
                          (block
                           (unless (and (>= n 1) (symbolp (second xs))) (refuse :b-block-source))
                           (let ((saved blocks)) (unwind-protect (progn (push (second xs) blocks) (dolist (x (cddr xs)) (walk x vars (1+ depth)))) (setq blocks saved))))
                          (return-from
                           (unless (and (member n '(1 2)) (member (second xs) blocks :test #'eq)) (refuse :b-return-source))
                           (when (= n 2) (walk (third xs) vars (1+ depth))))
                          (locally (body-forms (cdr xs) vars (1+ depth)))
                          (function
                           (unless (= n 1) (refuse :b-source))
                           (if (and (consp (second xs)) (eq (car (second xs)) 'lambda))
                             (lambda-form (items (second xs)) vars (1+ depth))
                             (unless (or (member (second xs) local-names) (assoc (second xs) *b-call-links*)) (refuse :b-source))))
                          (quote (unless (and (= n 1) (or (null (second xs)) (eq (second xs) t) (and (integerp (second xs)) (<= -536870912 (second xs) 536870911)) (pool-literal-p (second xs)) (member (second xs) *b-restart-names*) (assoc (second xs) *b-call-links*) (member (second xs) *b-special-names*) (and *b-float-service* (member (second xs) '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact))) (member (second xs) '(condition serious-condition error simple-condition simple-error type-error control-error warning simple-warning program-error undefined-function unbound-variable storage-condition ccl::no-applicable-method-exists arithmetic-error division-by-zero)))) (refuse :b-source)))
                          ((flet labels)
                           (unless (= n 2) (refuse :b-source))
                           (let* ((definitions (items (second xs))) (names nil) (old local-names))
                             (dolist (definition definitions)
                               (let ((parts (items definition)))
                                 (unless (>= (length parts) 2) (refuse :b-source))
                                 (variable (first parts))
                                 (when (or (member (first parts) names) (special-operator-p (first parts))
                                           (macro-function (first parts))) (refuse :b-source))
                                 (push (first parts) names)))
                             (unwind-protect
                               (progn
                                 (when (eq head 'labels) (setq local-names (append names old)))
                                 (dolist (definition definitions) (let ((saved blocks)) (unwind-protect (progn (push (first definition) blocks) (lambda-form (cons 'lambda (cdr definition)) vars (1+ depth))) (setq blocks saved))))
                                 (setq local-names (append names old))
                                 (walk (third xs) vars (1+ depth)))
                               (setq local-names old))))
                          (multiple-value-bind
                           (unless (>= n 2) (refuse :b-mv-bind-source))
                           (let ((names (items (second xs))))
                             (mapc #'variable names)
                             (unless (= (length names) (length (remove-duplicates names :test #'eq))) (refuse :b-mv-bind-source))
                             (walk (third xs) vars (1+ depth))
                             (body-forms (cdddr xs) (append names vars) (1+ depth))))
                          ((let let*)
                           (unless (>= n 1) (refuse :b-source))
                           (let ((scope vars) (bound nil))
                             (dolist (binding (items (second xs)))
                               (let* ((pair (if (consp binding) (items binding) (list binding))) (v (first pair)))
                                 (unless (<= 1 (length pair) 2) (refuse :b-source)) (variable v)
                                 (when (and (eq head 'let) (member v bound)) (refuse :b-source))
                                 (walk (second pair) (if (eq head 'let*) scope vars) (1+ depth))
                                 (push v scope) (push v bound)))
                             (body-forms (cddr xs) scope (1+ depth))))
                          (setq
                           (unless (evenp n) (refuse :b-source))
                           (loop for (v value) on (cdr xs) by #'cddr do
                             (unless (member v vars) (refuse :b-source)) (walk value vars (1+ depth))))
                          (t
                           (unless (or (and (member head '(car cdr)) (= n 1))
                                       (and (member head '(rplaca rplacd cons eq)) (= n 2))
                                       (and (member head '(signal error)) (= n 1))
                                       (and (eq head '%wasm-poll) (zerop n)) (and *b-float-service* (member head '(%float-add %float-sub %float-mul %float-div %float-lt %float-le %float-eq %float-ne %float-ge %float-gt %float-single %float-double))) (and *b-integer-service* (member head '(%numeric-operation %numeric-operands %integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate))) (member head '(%wasm-symbol-value %wasm-set %wasm-make-restart %wasm-find-restart %wasm-invoke-restart %wasm-restart-name %wasm-svref %wasm-condition-datum %wasm-condition-expected %wasm-cell-name))
                                       (and (eq head 'if) (member n '(2 3))) (member head '(values progn))
                                       (and (eq head 'prog2) (<= 2 n)) (and (member head '(prog1 multiple-value-prog1 unwind-protect catch)) (<= 1 n)) (and (eq head 'throw) (= n 2)) (and (eq head 'progv) (<= 2 n))
                                       (and (member head '(funcall multiple-value-call)) (<= 1 n)) (and (eq head 'apply) (<= 2 n))
                                       (member head local-names) (assoc head *b-call-links*)
                                       (and (consp head) (eq (car head) 'lambda))) (refuse :b-source))
                           (when (consp head) (lambda-form (items head) vars (1+ depth)))
                           (dolist (part (cdr xs)) (walk part vars (1+ depth)))))))
                     (t (refuse :b-source))))
             (lambda-form (parts outer depth)
               (unless (and (>= (length parts) 2) (eq (first parts) 'lambda)) (refuse :b-source))
               (let ((vars nil) (mode :required) (keys nil))
                 (labels ((add-var (v) (variable v) (when (member v vars) (refuse :b-source)) (push v vars)))
                   (dolist (parameter (items (second parts)))
                     (cond ((eq parameter '&optional) (unless (eq mode :required) (refuse :b-source)) (setq mode :optional))
                           ((eq parameter '&rest) (unless (member mode '(:required :optional)) (refuse :b-source)) (setq mode :rest))
                           ((eq mode :rest) (add-var parameter) (setq mode :after-rest))
                           ((eq parameter '&key) (unless (member mode '(:required :optional :after-rest)) (refuse :b-source)) (setq mode :key))
                           ((eq parameter '&allow-other-keys) (unless (eq mode :key) (refuse :b-source)) (setq mode :end))
                           ((eq mode :required) (add-var parameter))
                           ((member mode '(:optional :key))
                            (let* ((pair (if (consp parameter) (items parameter) (list parameter))) (v (first pair)) (sp (third pair)))
                              (unless (<= 1 (length pair) 3) (refuse :b-source))
                              (when (eq mode :key)
                                (let ((key (if (consp v)
                                             (let ((alias (items v))) (unless (= (length alias) 2) (refuse :b-source)) (setq v (second alias)) (first alias))
                                             (and (symbolp v) (intern (symbol-name v) "KEYWORD")))))
                                  (unless (keywordp key) (refuse :b-source)) (b-keyword key) (push key keys)))
                              (walk (second pair) (append vars outer) (1+ depth)) (add-var v) (when sp (add-var sp))))
                           (t (refuse :b-source)))))
                 (when (eq mode :rest) (refuse :b-source))
                 (body-forms (cddr parts) (append vars outer) (1+ depth)))))
      (lambda-form (items form) '(ccl::%handlers% ccl::%restarts% *debugger-hook* ccl::*interrupt-level*) 0))))

;;; Local calls use lexical function cells. CCL omits function-cell captures
;;; when a native backend can call a local entry directly; the Wasm environment
;;; plan adds those identities and propagates them through closure creators.
(defun b-plan-local-environments ()
  (let ((owners nil) (needed nil))
    (labels ((visit (x fn)
               (cond ((ccl::acode-p x) (funcall fn x) (unless (eq (ccl::acode-operator-name (ccl::acode-operator x)) 'ccl::immediate) (mapc (lambda (v) (visit v fn)) (ccl::acode-operands x))))
                     ((consp x) (mapc (lambda (v) (visit v fn)) x)))))
      (dolist (entry *b-functions*)
        (let* ((f (first entry)) (ir (ccl::afunc-acode f)) (args (ccl::acode-operands ir))
               (*required-vars* (first args)))
          (push (cons f (mapcar #'ccl::nx-root-var (ccl::afunc-inherited-vars f))) *b-environments*)
          (dolist (v (append (first args) (first (second args)) (third (second args))
                            (list (third args)) (second (fourth args)) (third (fourth args)) (b-local-variables ir)))
            (when v (push (cons (ccl::nx-root-var v) f) owners)))
          (visit ir (lambda (node)
            (let ((op (ccl::acode-operator-name (ccl::acode-operator node))) (a (ccl::acode-operands node)))
              (when (member op '(ccl::flet ccl::labels))
                (loop for var in (first a) for target in (second a) do
                  (push (cons target (ccl::nx-root-var var)) *b-function-vars*)))
              (when (eq op 'ccl::lexical-function-call) (push (cons f (first a)) needed)))))))
      (labels ((add (f var)
                 (unless (eq f (cdr (or (assoc var owners :test #'eq) (refuse :b-local-owner))))
                   (let ((row (or (assoc f *b-environments* :test #'eq) (refuse :b-local-environment))))
                     (unless (member var (cdr row) :test #'eq)
                       (setf (cdr row) (append (cdr row) (list var)))
                       t)))))
        (dolist (call (reverse needed))
          (add (car call) (cdr (or (assoc (cdr call) *b-function-vars* :test #'eq) (refuse :b-local-function-identity)))))
        ;; A child is constructed by its lexical parent, which must possess
        ;; every cell it forwards, even when it never reads that cell itself.
        (loop with changed = t while changed do
          (setq changed nil)
          (dolist (entry (reverse *b-functions*))
            (let* ((f (first entry)) (parent (ccl::afunc-parent f)))
              (when (assoc parent *b-environments* :test #'eq)
                (dolist (v (cdr (assoc f *b-environments* :test #'eq)))
                  (when (add parent v) (setq changed t))))))))
      (setq *b-captured* (remove-duplicates (mapcan (lambda (row) (copy-list (cdr row))) *b-environments*) :test #'eq)))))
(defun b-local-call (op afunc args spread)
  (let ((self (if (eq op 'b-self) "(i32.load offset=40 (local.get $context))"
                (b-read-variable (cdr (or (assoc afunc *b-function-vars* :test #'eq) (refuse :b-local-function-identity)))))))
    (if spread (if (or (eq spread t) (and *bootstrap-front-end* (eql spread 0)))
                   (b-apply nil args self 0 spread) (refuse :b-spread-kind))
      (b-call nil args self))))
(defun b-inline-lambda (args)
  (destructuring-bind (vals required rest keys auxiliary body policy) args
    (declare (ignore policy))
    (when (or keys (< (length vals) (length required))) (refuse :b-inline-shape))
    (b-frame (length vals)
      (lambda (base)
        (with-output-to-string (s)
          (loop for val in vals for i from 0 do
            (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) base (b-scalar val)))
          (write-string
            (funcall (if (some #'b-special-p (append required (list rest) (first auxiliary))) #'b-special-extent #'funcall)
              (lambda () (with-output-to-string (s)
          (loop for var in required for i from 0 do
            (write-string (b-bind-value var (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) base)) s))
          (when rest
            (let ((count (- (length vals) (length required))))
              (write-string (b-bind-value rest
                (if (zerop count) "(i32.const 77825)"
                  (b-at (b-heap-block (* 8 count)
                    (lambda (heap)
                      (with-output-to-string (list-code)
                        (dotimes (i count)
                          (format list-code "(i32.store offset=~d ~a ~a) (i32.store offset=~d ~a (i32.load offset=~d ~a))"
                            (* 8 i) heap (if (= i (1- count)) "(i32.const 77825)" (b-at heap (+ 9 (* 8 i))))
                            (+ 4 (* 8 i)) heap (+ 8 (* 4 (+ (length required) i))) base))))) 1))) s)))
          (loop for var in (first auxiliary) for init in (second auxiliary) do
            (write-string (b-bind-value var
              (if (integerp init)
                (progn (unless (<= 0 init (1- (length vals))) (refuse :b-inline-index))
                       (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 init)) base))
                (b-scalar init))) s))
          (write-string (b-multiple body) s)))) s))))))
(defun b-normalize-literal-apply (form)
  ;; Rewrite expression positions only: binding names and lambda-list syntax
  ;; are data even when a variable is named APPLY. Validation runs first.
  (labels ((lambda-list (items)
             (let ((mode :required))
               (mapcar (lambda (item)
                         (cond ((member item '(&optional &key &rest &allow-other-keys))
                                (setf mode item) item)
                               ((and (member mode '(&optional &key)) (consp item))
                                (if (cdr item)
                                  (cons (first item) (cons (walk (second item)) (cddr item))) item))
                               (t item))) items)))
           (walk (x)
             (if (atom x) x
               (case (car x)
                 (quote x)
                 (lambda `(lambda ,(lambda-list (second x)) ,@(mapcar #'walk (cddr x))))
                 (function `(function ,(if (consp (second x)) (walk (second x)) (second x))))
                 ((let let*)
                  `(,(car x) ,(mapcar (lambda (binding)
                                       (if (atom binding) binding
                                         (cons (first binding) (mapcar #'walk (cdr binding))))) (second x))
                    ,@(mapcar #'walk (cddr x))))
                 ((flet labels)
                  `(,(car x) ,(mapcar (lambda (definition)
                                       `(,(first definition) ,(lambda-list (second definition))
                                         ,@(mapcar #'walk (cddr definition)))) (second x))
                    ,@(mapcar #'walk (cddr x))))
                 (setq `(setq ,@(loop for (name value) on (cdr x) by #'cddr
                                     append (list name (walk value)))))
                 (otherwise
                  (let ((parts (cons (if (consp (car x)) (walk (car x)) (car x))
                                     (mapcar #'walk (cdr x)))))
                    (if (and (eq (first parts) 'apply)
                             (let ((callee (second parts)))
                               (or (and (consp callee) (eq (car callee) 'lambda))
                                   (and (consp callee) (eq (car callee) 'function)
                                        (consp (second callee)) (eq (car (second callee)) 'lambda)))))
                      `(%wasm-literal-apply ,(second parts) ,@(cddr parts))
                      parts)))))))
    (walk form)))

;;; One continuation context per ordinary B call. Tail entries reuse its
;;; argument/root area; the public B entry alone restores the caller's state.
;;; Raw saved words 0..31, root header 32..39, SELF/padding 40..47, args 48+.
(defun b-entry-wrapper (arity maximum open bound-words)
  (with-output-to-string (s)
    (write-string "(func (export \"entry\") (type $b_entry) (param $self i32) (param $nargs i32) (result i32 i32) (local $incoming i32) (local $output i32) (local $owner i32) (local $root i32) (local $old_count i32) (local $bytes i32) (local $i i32) (local $value i32) (local $count i32) (local $exception exnref) (local $old_handler i32) (local $old_unwind i32)" s)
    (format s "(local.set $incoming ~a) (local.set $output ~a) (local.set $owner ~a) (local.set $root ~a) (local.set $old_count ~a)"
      (b-load wasm32::tcr.vsp) (b-load wasm32::tcr.mv_base) (b-load wasm32::tcr.mv_owner_top) (b-load wasm32::tcr.root_head) (b-load wasm32::tcr.mv_count))
    (write-string (b-wat "(local.set $old_handler ~a) (local.set $old_unwind ~a)" (b-load wasm32::tcr.handler_checkpoint) (b-load wasm32::tcr.unwind_state)) s)
    (write-string (b-condition "(i32.or (i32.lt_u (local.get $incoming) (i32.load offset=68 (global.get $tcr))) (i32.and (i32.or (local.get $incoming) (i32.or (local.get $output) (local.get $owner))) (i32.const 15)))" 2) s)
    (write-string (b-condition "(i32.or (i32.gt_u (local.get $output) (local.get $owner)) (i32.gt_u (local.get $owner) (i32.load offset=72 (global.get $tcr))))" 2) s)
    (write-string (b-condition "(i64.gt_u (i64.extend_i32_u (i32.load offset=72 (global.get $tcr))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" 2) s)
    (write-string (b-condition "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $incoming)) (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get $nargs)) (i64.const 4)) (i64.const 15)) (i64.const -16))) (i64.extend_i32_u (local.get $output)))" 2) s)
    (write-string (b-condition "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $owner)) (i64.add (i64.const 48) (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get $nargs)) (i64.const 4)) (i64.const 15)) (i64.const -16)))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr))))" 2) s)
    (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $owner)) (i64.add (i64.const 48) (i64.add (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get $nargs)) (i64.const 4)) (i64.const 15)) (i64.const -16)) (i64.and (i64.add (if (result i64) (i32.lt_u (i32.sub (local.get $owner) (local.get $output)) (i32.const 16)) (then (i64.const 16)) (else (i64.extend_i32_u (i32.sub (local.get $owner) (local.get $output))))) (i64.const ~d)) (i64.const -16))))) (i64.extend_i32_u ~a))" (+ 23 (* 4 bound-words)) (b-load wasm32::tcr.vsp_limit)) 2) s)
    (write-string "(local.set $bytes (i32.and (i32.add (i32.mul (local.get $nargs) (i32.const 4)) (i32.const 15)) (i32.const -16))) (i32.store (local.get $owner) (local.get $incoming)) (i32.store offset=4 (local.get $owner) (local.get $output)) (i32.store offset=8 (local.get $owner) (local.get $owner)) (i32.store offset=12 (local.get $owner) (local.get $root)) (i32.store offset=16 (local.get $owner) (local.get $old_count)) (i32.store offset=20 (local.get $owner) (i32.const 0)) (i32.store offset=28 (local.get $owner) (i32.const 0)) (i32.store offset=24 (local.get $owner) (i32.const 0)) (i32.store offset=32 (local.get $owner) (local.get $root)) (i32.store offset=36 (local.get $owner) (i32.add (i32.const 2) (i32.div_u (local.get $bytes) (i32.const 4)))) (i32.store offset=40 (local.get $owner) (local.get $self)) (i32.store offset=44 (local.get $owner) (i32.const 77825)) (local.set $i (i32.const 0)) (block $pad_done (loop $pad (br_if $pad_done (i32.ge_u (local.get $i) (local.get $bytes))) (i32.store (i32.add (local.get $owner) (i32.add (i32.const 48) (local.get $i))) (i32.const 77825)) (local.set $i (i32.add (local.get $i) (i32.const 4))) (br $pad))) (memory.copy (i32.add (local.get $owner) (i32.const 48)) (local.get $incoming) (i32.mul (local.get $nargs) (i32.const 4)))" s)
    (write-string (b-store wasm32::tcr.vsp "(i32.add (local.get $owner) (i32.const 48))") s)
    (write-string (b-store wasm32::tcr.root_head "(i32.add (local.get $owner) (i32.const 32))") s)
    (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
    (write-string "(block $caught (result exnref) (try_table (catch_all_ref $caught) (call $body (local.get $self) (local.get $nargs) (local.get $owner)) (local.set $count) (local.set $value)" s)
    (write-string (b-wrapper-restore nil) s)
    (write-string "(return (local.get $value) (local.get $count))) unreachable) (local.set $exception)" s)
    (write-string (b-wrapper-restore t) s)
    (write-string "(throw_ref (local.get $exception)))" s)))
(defun b-wrapper-restore (exceptional)
  (concatenate 'string
    (b-store wasm32::tcr.handler_checkpoint "(local.get $old_handler)")
    (b-store wasm32::tcr.unwind_state "(local.get $old_unwind)")
    (b-store wasm32::tcr.vsp "(local.get $incoming)")
    (b-store wasm32::tcr.mv_base "(local.get $output)")
    (b-store wasm32::tcr.mv_owner_top "(local.get $owner)")
    (b-store wasm32::tcr.root_head "(local.get $root)")
    (b-store wasm32::tcr.mv_count (if exceptional "(local.get $old_count)" "(local.get $count)"))))
(defun b-tail-transfer (arguments count &optional (ephemeral-bytes 0))
  (let ((n (temporary)) (bytes (temporary)) (i (temporary)))
    (with-output-to-string (s)
      (format s "(local.set ~a ~a)" n count)
      (write-string (b-condition "(i32.ge_u (local.get $dispatch_slot) (table.size $tail_slots))" 4) s)
      (write-string (b-condition "(ref.is_null (table.get $tail_slots (local.get $dispatch_slot)))" 4) s)
      (format s "(local.set ~a (i32.and (i32.add (i32.mul (local.get ~a) (i32.const 4)) (i32.const 15)) (i32.const -16)))" bytes n)
      ;; The staged argument area already bounds N. Recheck the reusable
      ;; destination extent in i64 before overwriting any retired frame.
      (write-string (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $context)) (i64.add (i64.const ~d) (i64.extend_i32_u (local.get ~a)))) (i64.extend_i32_u ~a))" (+ 48 ephemeral-bytes) bytes (b-load wasm32::tcr.vsp_limit)) 2) s)
      (when (plusp ephemeral-bytes)
        (format s "(memory.copy (i32.add ~a (local.get ~a)) (i32.sub (local.get $dispatch_self) (i32.const 6)) (i32.const ~d))" arguments bytes ephemeral-bytes))
      (format s "(memory.copy (i32.add (local.get $context) (i32.const 48)) ~a ~a) (local.set ~a (i32.mul (local.get ~a) (i32.const 4))) (block $tail_pad_done (loop $tail_pad (br_if $tail_pad_done (i32.ge_u (local.get ~a) (local.get ~a))) (i32.store (i32.add (local.get $context) (i32.add (i32.const 48) (local.get ~a))) (i32.const 77825)) (local.set ~a (i32.add (local.get ~a) (i32.const 4))) (br $tail_pad)))"
        arguments (if (plusp ephemeral-bytes) (b-wat "(i32.add (local.get ~a) (i32.const ~d))" bytes ephemeral-bytes) (b-wat "(i32.mul (local.get ~a) (i32.const 4))" n)) i n i bytes i i i)
      (format s "(i32.store offset=24 (local.get $context) (i32.const ~d))" ephemeral-bytes)
      (when (plusp ephemeral-bytes)
        (format s "(local.set $dispatch_self (i32.add (local.get $context) (i32.add (i32.const 54) (local.get ~a)))) (if (i32.ne (i32.load offset=2 (local.get $dispatch_self)) (i32.const 77825)) (then (i32.store offset=2 (local.get $dispatch_self) (i32.add (local.get $dispatch_self) (i32.const 32)))))" bytes))
      (format s "(i32.store offset=36 (local.get $context) (i32.add (i32.const 2) (i32.div_u (local.get ~a) (i32.const 4)))) (i32.store offset=40 (local.get $context) (local.get $dispatch_self)) (i32.store offset=44 (local.get $context) (i32.const 77825))" bytes)
      (write-string (b-store wasm32::tcr.vsp "(i32.add (local.get $context) (i32.const 48))") s)
      (write-string (b-store wasm32::tcr.mv_base "(i32.load offset=4 (local.get $context))") s)
      (write-string (b-store wasm32::tcr.mv_owner_top "(i32.load offset=8 (local.get $context))") s)
      (write-string (b-store wasm32::tcr.root_head "(i32.add (local.get $context) (i32.const 32))") s)
      (write-string (b-store wasm32::tcr.mv_count "(i32.const 0)") s)
      (write-string "(if (local.get $dynamic_results) (then (call $rv_release (local.get $frame))))" s)
      (format s "(return_call_indirect $tail_slots (type $tail_entry) (local.get $dispatch_self) (local.get ~a) (local.get $context) (local.get $dispatch_slot))" n))))
(defun b-stack-block (bytes writer)
  (let* ((p (temporary)) (size (* 16 (ceiling bytes 16))) (body (funcall writer (b-local p))))
    (b-wat "(block (result i32) (local.set ~a (local.get $top)) ~a (memory.fill (local.get ~a) (i32.const 0) (i32.const ~d)) ~a (local.get ~a))"
      p (b-reserve size) p size body p)))
(defun b-literal-apply (arguments)
  (unless (and (null (second arguments)) (>= (length (first arguments)) 2)) (refuse :literal-apply-shape))
  (let* ((forms (first arguments)) (literal (first forms))
         (op (ccl::acode-operator-name (ccl::acode-operator literal)))
         (afunc (first (ccl::acode-operands literal))))
    (unless (member op '(ccl::closed-function ccl::simple-function)) (refuse :literal-apply-function))
    (let* ((n (length (cdr (assoc afunc *b-environments* :test #'eq))))
           (bytes (* 16 (ceiling (+ 32 (if (zerop n) 0 (* 8 (ceiling (+ 4 (* 4 n)) 8)))) 16)))
           (self (let ((*b-stack-closure* t)) (b-make-closure afunc))))
      (b-apply nil (list (butlast (rest forms)) (last forms)) self bytes))))

(defun b-result-runtime () "(func $rv_alloc (param $n i32) (param $owner i32) (param $top i32) (result i32)
 (local $p i32) (local $size i32) (local $need i32) (local $next i32) (local $end i32) (local $wide i64) (local $i i32)
 (call $rv_check)
 (local.set $p (i32.load offset=80 (global.get $tcr)))
 (local.set $end (i32.load offset=76 (global.get $tcr)))
 (if (i32.or (i32.eqz (local.get $p)) (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.or (i32.lt_u (local.get $end) (local.get $p)) (i32.gt_u (local.get $end) (i32.load offset=84 (global.get $tcr)))))) (then (throw $call_error (i32.const 13))))
 (if (i64.gt_u (i64.extend_i32_u (i32.load offset=84 (global.get $tcr))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 13))))
 (local.set $wide (i64.and (i64.add (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4)) (i64.const 31)) (i64.const -16)))
 (if (i64.gt_u (local.get $wide) (i64.const 4294967295)) (then (throw $call_error (i32.const 13))))
 (local.set $need (i32.wrap_i64 (local.get $wide)))
 (block $found (loop $scan
  (br_if $found (i32.eq (local.get $p) (local.get $end)))
  (local.set $size (i32.load (local.get $p)))
  (if (i32.or (i32.lt_u (local.get $size) (i32.const 16)) (i32.and (local.get $size) (i32.const 15))) (then (throw $call_error (i32.const 13))))
  (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $size))) (i64.extend_i32_u (local.get $end))) (then (throw $call_error (i32.const 13))))
  (if (i32.eqz (i32.load offset=4 (local.get $p))) (then
   (local.set $next (i32.add (local.get $p) (local.get $size)))
   (if (i32.lt_u (local.get $next) (local.get $end)) (then
    (if (i32.eqz (i32.load offset=4 (local.get $next))) (then
     (i32.store (local.get $p) (i32.add (local.get $size) (call $rv_block_size (local.get $next) (local.get $end)))) (br $scan)))))
   (br_if $found (i32.ge_u (local.get $size) (local.get $need)))))
  (local.set $p (i32.add (local.get $p) (local.get $size))) (br $scan)))
 (call $stack_guard (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $need))) (local.get $top) (i32.const 19))
 (if (i32.eq (local.get $p) (local.get $end))
  (then
   (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $end)) (local.get $wide)) (i64.extend_i32_u (i32.load offset=84 (global.get $tcr)))) (then (throw $call_error (i32.const 13))))
   (i32.store offset=76 (global.get $tcr) (i32.add (local.get $end) (local.get $need))))
  (else (if (i32.gt_u (local.get $size) (local.get $need)) (then
   (local.set $next (i32.add (local.get $p) (local.get $need)))
   (i32.store (local.get $next) (i32.sub (local.get $size) (local.get $need))) (i32.store offset=4 (local.get $next) (i32.const 0))))))
 (i32.store (local.get $p) (local.get $need)) (i32.store offset=4 (local.get $p) (local.get $owner))
 (i32.store offset=8 (local.get $p) (local.get $n)) (i32.store offset=12 (local.get $p) (i32.const 1381384241))
 (local.set $i (i32.const 16)) (block $filled (loop $fill (br_if $filled (i32.ge_u (local.get $i) (local.get $need)))
  (i32.store (i32.add (local.get $p) (local.get $i)) (i32.const 77825)) (local.set $i (i32.add (local.get $i) (i32.const 4))) (br $fill)))
 (i32.add (local.get $p) (i32.const 16)))
(func $rv_ensure (param $d i32) (param $n i32) (param $top i32) (result i32) (local $p i32) (local $old i32) (local $cap i32)
 (local.set $old (i32.load offset=8 (local.get $d))) (local.set $cap (i32.load offset=12 (local.get $d)))
 (if (i32.load offset=20 (local.get $d)) (then
  (if (i64.gt_u (i64.and (i64.add (i64.add (i64.extend_i32_u (local.get $old)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4))) (i64.const 15)) (i64.const -16)) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))
  (call $stack_guard (i64.and (i64.add (i64.add (i64.extend_i32_u (local.get $old)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4))) (i64.const 15)) (i64.const -16)) (local.get $top) (i32.const 18))
  (i32.store offset=12 (local.get $d) (local.get $n)) (return (local.get $old))))
 (if (i32.le_u (local.get $n) (local.get $cap)) (then (return (local.get $old))))
 (if (i32.le_u (local.get $n) (i32.const 4)) (then
  (local.set $p (i32.add (local.get $d) (i32.const 32)))
  (i32.store offset=8 (local.get $d) (local.get $p)) (i32.store offset=12 (local.get $d) (i32.const 4)) (return (local.get $p))))
 (local.set $p (call $rv_alloc (local.get $n) (i32.load offset=16 (local.get $d)) (local.get $top)))
 (if (local.get $cap) (then (memory.copy (local.get $p) (local.get $old) (i32.mul (local.get $cap) (i32.const 4)))
  (if (i32.ne (local.get $old) (i32.add (local.get $d) (i32.const 32))) (then (i32.store (i32.sub (local.get $old) (i32.const 12)) (i32.const 0))))))
 (i32.store offset=8 (local.get $d) (local.get $p)) (i32.store offset=12 (local.get $d) (local.get $n)) (local.get $p))
(func $rv_deliver (param $d i32) (param $src i32) (param $n i32) (param $top i32) (result i32) (local $dst i32)
 (if (i32.load offset=20 (local.get $d)) (then
  (local.set $dst (call $rv_ensure (local.get $d) (local.get $n) (local.get $top)))
  (i32.store offset=128 (global.get $tcr) (i32.load offset=24 (local.get $d)))
  (memory.copy (local.get $dst) (local.get $src) (i32.mul (local.get $n) (i32.const 4)))
  (return (local.get $dst))))
 (if (i32.and (i32.ne (local.get $src) (i32.const 0)) (i32.and (i32.ge_u (local.get $src) (i32.load offset=68 (global.get $tcr))) (i32.lt_u (local.get $src) (i32.load offset=72 (global.get $tcr))))) (then
  (if (i32.gt_u (local.get $n) (i32.const 4)) (then (throw $call_error (i32.const 13))))
  (local.set $dst (call $rv_ensure (local.get $d) (local.get $n) (local.get $top)))
  (if (i32.ne (local.get $dst) (local.get $src)) (then (memory.copy (local.get $dst) (local.get $src) (i32.mul (local.get $n) (i32.const 4)))))
  (return (local.get $dst))))
 (local.set $dst (i32.load offset=8 (local.get $d)))
 (if (i32.and (i32.ne (local.get $dst) (i32.add (local.get $d) (i32.const 32))) (i32.and (i32.ne (local.get $dst) (i32.const 0)) (i32.ne (local.get $dst) (local.get $src))))
  (then (i32.store (i32.sub (local.get $dst) (i32.const 12)) (i32.const 0))))
 (if (local.get $src) (then
  (i32.store (i32.sub (local.get $src) (i32.const 12)) (i32.load offset=16 (local.get $d)))
  (i32.store offset=12 (local.get $d) (i32.load (i32.sub (local.get $src) (i32.const 8)))))
  (else (i32.store offset=12 (local.get $d) (i32.const 0))))
 (i32.store offset=8 (local.get $d) (local.get $src)) (local.get $src))
(func $rv_release (param $owner i32) (local $p i32) (local $end i32) (local $keep i32) (local $size i32)
 (call $rv_check)
 (local.set $p (i32.load offset=80 (global.get $tcr))) (local.set $end (i32.load offset=76 (global.get $tcr))) (local.set $keep (local.get $p))
 (block $done (loop $scan (br_if $done (i32.eq (local.get $p) (local.get $end)))
  (local.set $size (call $rv_block_size (local.get $p) (local.get $end)))
  (if (i32.eq (i32.load offset=4 (local.get $p)) (local.get $owner)) (then (i32.store offset=4 (local.get $p) (i32.const 0))))
  (if (i32.load offset=4 (local.get $p)) (then (local.set $keep (i32.add (local.get $p) (local.get $size)))))
  (local.set $p (i32.add (local.get $p) (local.get $size))) (br $scan)))
 (i32.store offset=76 (global.get $tcr) (local.get $keep)))
(func $rv_check (local $b i32) (local $e i32) (local $l i32)
 (local.set $b (i32.load offset=80 (global.get $tcr))) (local.set $e (i32.load offset=76 (global.get $tcr))) (local.set $l (i32.load offset=84 (global.get $tcr)))
 (if (i32.or (i32.eqz (local.get $b)) (i32.or (i32.and (i32.or (local.get $b) (i32.or (local.get $e) (local.get $l))) (i32.const 15)) (i32.or (i32.lt_u (local.get $e) (local.get $b)) (i32.gt_u (local.get $e) (local.get $l))))) (then (throw $call_error (i32.const 13))))
 (if (i64.gt_u (i64.extend_i32_u (local.get $l)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 13))))
 (if (i32.and (i32.lt_u (local.get $b) (i32.load offset=72 (global.get $tcr))) (i32.gt_u (local.get $l) (i32.load offset=68 (global.get $tcr)))) (then (throw $call_error (i32.const 13)))))
(func $rv_block_size (param $p i32) (param $end i32) (result i32) (local $size i32)
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 16)) (i64.extend_i32_u (local.get $end))) (then (throw $call_error (i32.const 13))))
 (local.set $size (i32.load (local.get $p)))
 (if (i32.or (i32.lt_u (local.get $size) (i32.const 16)) (i32.and (local.get $size) (i32.const 15))) (then (throw $call_error (i32.const 13))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $size))) (i64.extend_i32_u (local.get $end))) (then (throw $call_error (i32.const 13))))
 (local.get $size))
")

(defun b-result-descriptor (descriptor owner)
 (b-wat "(i32.store ~a ~a) (i32.store offset=4 ~a (i32.const -1)) (i32.store offset=8 ~a ~a) (i32.store offset=12 ~a (i32.const 4)) (i32.store offset=16 ~a ~a) (i32.store offset=20 ~a (i32.const 0)) (i32.store offset=32 ~a (i32.const 77825)) (i32.store offset=36 ~a (i32.const 77825)) (i32.store offset=40 ~a (i32.const 77825)) (i32.store offset=44 ~a (i32.const 77825)) ~a"
  descriptor (b-load wasm32::tcr.root_head) descriptor descriptor (b-at descriptor 32) descriptor descriptor owner descriptor descriptor descriptor descriptor descriptor (b-store wasm32::tcr.root_head descriptor)))
(defun b-ensure-results (count)
 (b-wat "(if (local.get $dynamic_results) (then (local.set $results (call $rv_ensure (local.get $result_descriptor) ~a (local.get $top))) (local.set $capacity (i32.load offset=12 (local.get $result_descriptor)))) (else ~a))"
 count (b-condition (b-wat "(i32.gt_u ~a (local.get $capacity))" count) 3)))

(defun b-control-ensure (record)
 (b-wat "(if (i32.load offset=28 ~a) (then (drop (call $rv_ensure (i32.load offset=28 ~a) (local.get $count) (local.get $top)))) (else ~a))"
  record record (b-condition (b-wat "(i32.gt_u (local.get $count) (i32.load offset=8 ~a))" record) 3)))
(defun b-control-values (record)
 (b-wat "(if (result i32) (i32.load offset=28 ~a) (then (i32.load offset=8 (i32.load offset=28 ~a))) (else (i32.add ~a (i32.const 48))))" record record record))

(defun b-producer (form destination scope target stable-root)
 (let ((mode (temporary)) (descriptor (temporary)) (results (temporary)) (capacity (temporary))
       (saved-scope (temporary)) (local-descriptor (temporary)) (exception (b-exception-local)))
  (let* ((op (ccl::acode-operator-name (ccl::acode-operator form)))
         (body (let ((*b-tail-position* nil)
                     (*b-producer-target* (when (member op '(ccl::call ccl::self-call ccl::lexical-function-call)) target)))
                  (if (eq op 'ccl::values) (b-direct-producer-values form target) (b-multiple form))))
         (restore (b-wat "(local.set $dynamic_results (local.get ~a)) (local.set $result_descriptor (local.get ~a)) (local.set $results (local.get ~a)) (local.set $capacity (local.get ~a)) (local.set $result_scope (local.get ~a))" mode descriptor results capacity saved-scope)))
   (b-wat "(local.set ~a (local.get $dynamic_results)) (local.set ~a (local.get $result_descriptor)) (local.set ~a (local.get $results)) (local.set ~a (local.get $capacity)) (local.set ~a (local.get $result_scope)) (local.set ~a ~a) ~a (local.set $dynamic_results (i32.const 1)) (local.set $result_descriptor (local.get ~a)) (local.set $result_scope (local.get ~a)) (block $producer_ok (block $producer_failed (result exnref) (try_table (catch_all_ref $producer_failed) ~a ~a (local.set ~a (local.get $results)) (local.set ~a (local.get $result_scope)) (br $producer_ok)) unreachable) (local.set ~a) (call $rv_release (local.get ~a)) ~a (throw_ref (local.get ~a))) ~a"
    mode descriptor results capacity saved-scope local-descriptor stable-root
    (b-result-descriptor (b-local local-descriptor) (b-local local-descriptor)) local-descriptor local-descriptor
    "(local.set $results (i32.const 0)) (local.set $capacity (i32.const 0))" body destination scope exception local-descriptor restore exception restore))))

(defun b-ephemeral-bytes (afunc)
 (let ((n (length (cdr (assoc afunc *b-environments* :test #'eq)))))
  (* 16 (ceiling (+ 32 (if (zerop n) 0 (* 8 (ceiling (+ 4 (* 4 n)) 8)))) 16))))

(defun b-direct-producer-values (form target)
 (let* ((forms (first (ccl::acode-operands form))) (n (length forms)))
  (b-frame n (lambda (base)
   (with-output-to-string (s)
    (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) base (b-scalar f)))
    (format s "(local.set $results (call $rv_ensure ~a (i32.const ~d) (local.get $top))) (i32.store offset=128 (global.get $tcr) (i32.load offset=24 ~a)) (memory.copy (local.get $results) ~a (i32.const ~d)) (local.set $count (i32.const ~d))" target n target (b-at base 8) (* 4 n) n))))))

(defun b-save-control (record)
 (b-wat "(if (i32.load offset=28 ~a) (then ~a (drop (call $rv_deliver (i32.load offset=28 ~a) (local.get $results) (local.get $count) (local.get $top))) (i32.store offset=8 (local.get $result_descriptor) (i32.const 0)) (i32.store offset=12 (local.get $result_descriptor) (i32.const 0)) (local.set $results (i32.const 0)) (local.set $capacity (i32.const 0))) (else ~a (memory.copy ~a (local.get $results) (i32.mul (local.get $count) (i32.const 4)))))"
 record (b-condition "(i32.eqz (local.get $dynamic_results))" 9) record (b-control-ensure record) (b-at record 48)))
(defun b-load-control (record)
 (b-wat "(if (i32.load offset=28 ~a) (then (local.set $results (call $rv_deliver (local.get $result_descriptor) ~a (local.get $count) (local.get $top))) (local.set $capacity (i32.load offset=12 (local.get $result_descriptor))) (i32.store offset=8 (i32.load offset=28 ~a) (i32.const 0)) (i32.store offset=12 (i32.load offset=28 ~a) (i32.const 0))) (else ~a (memory.copy (local.get $results) ~a (i32.mul (local.get $count) (i32.const 4)))))"
 record (b-control-values record) record record (b-ensure-results "(local.get $count)") (b-at record 48)))

;;; Explicit condition dispatch over owner-supplied condition proxies. Class
;;; construction, restarts, the debugger and implicit trap-to-condition mapping
;;; are separate runtime obligations. HANDLER macros are expanded by U1 itself.
(defun b-condition-mask (type)
  (when (and (not *bootstrap-front-end*) (member type '(stream-error end-of-file file-error package-error ccl::simple-package-error ccl::stream-is-closed-error ccl::bad-slot-type ccl::inactive-restart ccl::restart-failure))) (refuse :b-condition-type))
  (when (and (member type '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact)) (not *b-float-service*)) (refuse :float-condition-mode))
  (or (cdr (assoc type '((condition . 1) (serious-condition . 2) (error . 4)
                         (simple-condition . 8) (simple-error . 16) (type-error . 32) (program-error . 512) (undefined-function . 1024) (unbound-variable . 2048) (storage-condition . 4096) (ccl::no-applicable-method-exists . 8192) (arithmetic-error . 16384) (division-by-zero . 32768) (floating-point-invalid-operation . 65536) (floating-point-overflow . 131072) (floating-point-underflow . 262144) (floating-point-inexact . 524288)
                         (control-error . 64) (warning . 128) (simple-warning . 256) (stream-error . 1048576) (end-of-file . 2097152) (file-error . 4194304) (package-error . 8388608) (ccl::simple-package-error . 16777216) (ccl::stream-is-closed-error . 33554432) (ccl::bad-slot-type . 67108864) (ccl::inactive-restart . 134217728) (ccl::restart-failure . 268435456))))
      (refuse :b-condition-type)))
(defun b-expand-conditions (form) (setq *b-restart-names* (if *b-float-service* '(list cons function simple-vector integer fixnum or number real truncate + - * / < <= = /= >= > float) (if *b-integer-service* '(list cons function simple-vector integer fixnum or number real truncate) '(list cons function simple-vector integer fixnum or))))
  ;; Check the input graph before any native macro sees it. Shared/cyclic reader
  ;; objects and dotted lists are outside this source API.
  (let ((work (list (cons form 0))) (seen (make-hash-table :test #'eq)) (left 32768))
    (loop while work do
      (let* ((entry (pop work)) (node (car entry)) (depth (cdr entry)))
        (when (or (> depth 128) (minusp (decf left))) (refuse :b-condition-source))
        (when (and (consp node) (not (and (eq (car node) 'quote) (consp (cdr node)) (null (cddr node)))))
          (when (gethash node seen) (refuse :b-condition-source))
          (setf (gethash node seen) t)
          (unless (listp (cdr node)) (refuse :b-condition-source))
          (push (cons (cdr node) depth) work)
          (push (cons (car node) (1+ depth)) work)))))
  (let ((budget 32768) (expanding nil) (condition-source-depth 0) (symbol-access-shadows nil))
    (declare (special expanding condition-source-depth symbol-access-shadows))
    (labels ((lambda-list (items)
             (let ((mode :required))
               (mapcar (lambda (item)
                         (cond ((member item '(&optional &key &rest &allow-other-keys))
                                (setf mode item) item)
                               ((and (member mode '(&optional &key)) (consp item))
                                (if (cdr item)
                                  (cons (first item) (cons (walk (second item)) (cddr item))) item))
                               (t item))) items)))
           (walk (x)
             (let ((condition-source-depth (1+ condition-source-depth)))
               (declare (special condition-source-depth))
               (when (> condition-source-depth 128) (refuse :b-condition-source))
               (when (minusp (decf budget)) (refuse :b-condition-source))
               (when (consp x)
                 (let ((seen (make-hash-table :test #'eq)))
                   (do ((p x (cdr p))) ((null p))
                     (unless (consp p) (refuse :b-condition-source))
                     (when (gethash p seen) (refuse :b-condition-source))
                     (setf (gethash p seen) t))))
               (if (atom x) x
                 (case (car x)
                   (quote x)
                 (lambda `(lambda ,(lambda-list (second x)) ,@(mapcar #'walk (cddr x))))
                 (function `(function ,(if (consp (second x)) (walk (second x)) (second x))))
                 ((let let*)
                  `(,(car x) ,(mapcar (lambda (binding)
                                       (if (atom binding) binding
                                         (cons (first binding) (mapcar #'walk (cdr binding))))) (second x))
                    ,@(mapcar #'walk (cddr x))))
                 ((flet labels)
                  (let ((names (mapcar #'first (second x))))
                   `(,(car x) ,(mapcar (lambda (definition)
                     (let ((symbol-access-shadows (if (eq (car x) 'labels) (append names symbol-access-shadows) symbol-access-shadows)))
                      (declare (special symbol-access-shadows))
                      `(,(first definition) ,(lambda-list (second definition)) ,@(mapcar #'walk (cddr definition))))) (second x))
                     ,@(let ((symbol-access-shadows (append names symbol-access-shadows)))
                         (declare (special symbol-access-shadows)) (mapcar #'walk (cddr x))))))
                 (setq `(setq ,@(loop for (name value) on (cdr x) by #'cddr
                                     append (list name (walk value)))))
                 (multiple-value-bind `(multiple-value-bind ,(second x) ,@(mapcar #'walk (cddr x))))
                 ((block return-from) `(,(car x) ,(second x) ,@(mapcar #'walk (cddr x))))
                   ((restart-case restart-bind)
                    (walk (b-expand-restart x #'walk #'lambda-list)))
                   ((arithmetic-error-operation arithmetic-error-operands) (cons (if (eq (car x) 'arithmetic-error-operation) '%numeric-operation '%numeric-operands) (mapcar #'walk (cdr x))))
                   ((type-error-datum type-error-expected-type cell-error-name) (cons (case (car x) (type-error-datum '%wasm-condition-datum) (type-error-expected-type '%wasm-condition-expected) (cell-error-name '%wasm-cell-name)) (mapcar #'walk (cdr x))))
                   ((ccl::without-interrupts ccl::with-interrupts-enabled)
                    (walk `(unwind-protect (let* ((ccl::*interrupt-level* ,(if (eq (car x) 'ccl::without-interrupts) -1 0))) ,@(mapcar #'walk (cdr x))) (%wasm-poll))))
                   (ccl::%interrupt-poll (unless (null (cdr x)) (refuse :poll-arity)) '(%wasm-poll))
                   ((/ < <= = /= >= > float)
                    (if (and *b-float-service* (not (member (car x) symbol-access-shadows)))
                     (progn
                      (unless (= (length (cdr x)) 2) (refuse :float-arity))
                      (if (eq (car x) 'float)
                       (progn (unless (typep (third x) 'float) (refuse :float-prototype))
                        (cons (if (typep (third x) 'single-float) '%float-single '%float-double) (mapcar #'walk (cdr x))))
                       (cons (cdr (assoc (car x) '((/ . %float-div) (< . %float-lt) (<= . %float-le) (= . %float-eq) (/= . %float-ne) (>= . %float-ge) (> . %float-gt)))) (mapcar #'walk (cdr x)))))
                     (cons (car x) (mapcar #'walk (cdr x)))))
                   ((+ - * ash integer-length truncate)
                    (if (and *b-integer-service* (not (member (car x) symbol-access-shadows)))
                      (progn
                        (unless (= (length (cdr x)) (if (eq (car x) 'integer-length) 1 2)) (refuse :integer-arity))
                        (cons (or (and *b-float-service* (cdr (assoc (car x) '((+ . %float-add) (- . %float-sub) (* . %float-mul))))) (cdr (assoc (car x) '((+ . %integer-add) (- . %integer-sub) (* . %integer-mul) (ash . %integer-ash) (integer-length . %integer-length) (truncate . %integer-truncate))))) (mapcar #'walk (cdr x))))
                      (cons (car x) (mapcar #'walk (cdr x)))))
                   ((symbol-value set) (cons (if (member (car x) symbol-access-shadows) (car x) (if (eq (car x) 'set) '%wasm-set '%wasm-symbol-value)) (mapcar #'walk (cdr x))))
                   (svref (cons '%wasm-svref (mapcar #'walk (cdr x))))
                   ((find-restart invoke-restart restart-name)
                    (when (and (consp (second x)) (eq (first (second x)) 'quote)) (pushnew (second (second x)) *b-restart-names*))
                    (cons (case (car x) (find-restart '%wasm-find-restart)
                                (invoke-restart '%wasm-invoke-restart) (restart-name '%wasm-restart-name))
                          (mapcar #'walk (cdr x))))
                   ((handler-bind handler-case)
                    ;; Validate type specifiers before invoking a native macro.
                    ;; The source reader has disabled read-time evaluation.
                    (dolist (clause (if (eq (car x) 'handler-bind) (second x) (cddr x)))
                      (unless (and (listp clause) (consp clause)) (refuse :b-handler-clause))
                      (unless (eq (car clause) :no-error) (b-condition-mask (car clause))))
                    ;; Process user expressions with expansion privileges off,
                    ;; BEFORE the macro can embed them in generated scaffolding.
                    ;; A dynamic EXPANDING flag alone would admit user CASE in
                    ;; a handler body or a :NO-ERROR/default expression.
                    (let* ((input
                            (let ((expanding nil))
                              (declare (special expanding))
                              (if (eq (car x) 'handler-bind)
                                `(handler-bind
                                   ,(mapcar (lambda (clause)
                                              (unless (= (length clause) 2) (refuse :b-handler-clause))
                                              (list (first clause) (walk (second clause)))) (second x))
                                   ,@(mapcar #'walk (cddr x)))
                                `(handler-case ,(walk (second x))
                                   ,@(mapcar (lambda (clause)
                                               `(,(first clause) ,(lambda-list (second clause))
                                                 ,@(mapcar #'walk (cddr clause)))) (cddr x))))))
                           (expanding t))
                      (declare (special expanding))
                      (walk (macroexpand-1 input))))
                   (the (unless (and expanding (eq (second x) 'list) (= (length x) 3)) (refuse :b-condition-assertion)) (walk (third x)))
                   (declare
                    `(declare ,@(remove-if (lambda (d) (eq (car d) 'dynamic-extent)) (cdr x))))
                   (list (unless expanding (refuse :b-condition-generated-form)) (reduce (lambda (a b) `(cons ,(walk a) ,b)) (cdr x) :from-end t :initial-value nil))
                   (pop (unless expanding (refuse :b-condition-generated-form)) (walk (macroexpand-1 x)))
                   (case
                    (unless expanding (refuse :b-condition-generated-form))
                    (let ((v (gensym "CONDITION-CASE")))
                      `(let ((,v ,(walk (second x))))
                         ,(reduce (lambda (clause rest)
                                    (if (member (first clause) '(t otherwise)) `(progn ,@(mapcar #'walk (cdr clause)))
                                      `(if (eq ,v ,(first clause)) (progn ,@(mapcar #'walk (cdr clause))) ,rest)))
                                  (cddr x) :from-end t :initial-value nil))))
                   (t (mapcar #'walk x)))))))
      (walk form))))
(defun b-signal (form fatal)
  (when (and (ccl::acode-p form) (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::immediate) (stringp (first (ccl::acode-operands form)))) (refuse :b-signal-format-string))
  (setq *b-condition-used* t)
  (let ((*b-tail-position* nil) (*b-producer-target* nil))
    (b-frame 4
      (lambda (root)
        (let* ((condition (b-wat "(i32.load offset=8 ~a)" root))
               (cluster (b-wat "(i32.load offset=12 ~a)" root))
               (handlers (b-wat "(i32.load offset=16 ~a)" root))
               (handler (b-wat "(i32.load offset=20 ~a)" root))
               (symbol (b-special-symbol 'ccl::%handlers%))
               (raw-condition (make-b-raw-code :text condition))
               (raw-cluster (make-b-raw-code :text cluster)))
          (with-output-to-string (s)
            (write-string (b-wat "(i32.store offset=8 ~a ~a) (drop (call $condition_mask ~a))" root (b-scalar form) condition) s)
            (write-string
              (b-special-extent
                (lambda ()
                  (with-output-to-string (s)
                    (write-string (b-bind-symbol symbol (b-wat "(call $special_read ~a)" symbol)) s)
                    (format s "(block $signal_done (loop $signal_clusters (br_if $signal_done (i32.eq (call $special_read ~a) (i32.const 77825)))" symbol)
                    (format s "(i32.store offset=12 ~a (i32.load offset=4 (call $handler_cons (call $special_read ~a))))" root symbol)
                    ;; Mask the entire current cluster before calling a handler.
                    (format s "(i32.store (call $special_location ~a) (i32.load (call $handler_cons (call $special_read ~a))))" symbol symbol)
                    (format s "(i32.store offset=16 ~a ~a) (block $signal_next (loop $signal_handlers (br_if $signal_next (i32.eq ~a (i32.const 77825)))" root cluster handlers)
                    (write-string
                      (b-wat "(if (i32.and (call $condition_mask ~a) ~a) (then"
                        condition
                        (if *bootstrap-front-end*
                          (bootstrap-handler-mask
                           (b-wat "(i32.load offset=4 (call $handler_cons ~a))" handlers))
                          (b-wat "(i32.shr_u (i32.load offset=4 (call $handler_cons ~a)) (i32.const 2))" handlers))) s)
                    (format s "(i32.store offset=20 ~a (call $handler_second ~a))" root handlers)
                    (format s "(if (i32.eq ~a (i32.const 77825)) (then ~a))" handler (b-throw raw-cluster raw-condition))
                    (format s "(if (i32.eqz (i32.and ~a (i32.const 3))) (then ~a))" handler
                      (b-throw raw-cluster (make-b-raw-code :text (b-cons (make-b-raw-code :text handler) raw-condition))))
                    (write-string (b-discard-handler handler raw-condition) s)
                    (write-string "))" s)
                    (format s "(i32.store offset=16 ~a (call $handler_rest ~a)) (br $signal_handlers))) (br $signal_clusters)))" root handlers)))) s)
            (write-string (if fatal (concatenate 'string (b-debugger condition) "(throw $call_error (i32.const 15))") (b-multiple (make-b-raw-code :text "(i32.const 77825)"))) s)))))))
(defun b-handler-runtime ()
 "(func $handler_cons (param $x i32) (result i32)
   (if (i32.or (i32.eq (local.get $x) (i32.const 77825)) (i32.ne (i32.and (local.get $x) (i32.const 7)) (i32.const 1))) (then (throw $call_error (i32.const 12))))
   (call $span (i32.sub (local.get $x) (i32.const 1)) (i32.const 8)) (i32.sub (local.get $x) (i32.const 1)))
 (func $handler_second (param $x i32) (result i32) (local $tail i32)
   (local.set $tail (i32.load (call $handler_cons (local.get $x))))
   (if (result i32) (i32.eq (local.get $tail) (i32.const 77825)) (then (i32.const 77825)) (else (i32.load offset=4 (call $handler_cons (local.get $tail))))))
 (func $handler_rest (param $x i32) (result i32) (local $tail i32)
   (local.set $tail (i32.load (call $handler_cons (local.get $x))))
   (if (result i32) (i32.eq (local.get $tail) (i32.const 77825)) (then (i32.const 77825)) (else (i32.load (call $handler_cons (local.get $tail))))))
")
(defun b-discard-handler (handler condition &optional second-argument no-arguments)
  ;; A handler's values are discarded, so its result count cannot be limited by
  ;; the caller's final output reservation. Use the reviewed inline/spill shape.
  (let ((base (temporary)) (root (temporary)) (mode (temporary))
        (descriptor (temporary)) (results (temporary)) (capacity (temporary))
        (scope (temporary)) (exception (b-exception-local)))
    (let* ((call (let ((*b-producer-target* nil) (*b-tail-position* nil))
                   (b-call nil (list (if no-arguments nil (if second-argument (list condition second-argument) (list condition))) nil) handler)))
           (restore (b-wat "~a (call $rv_release (local.get ~a)) (local.set $dynamic_results (local.get ~a)) (local.set $result_descriptor (local.get ~a)) (local.set $results (local.get ~a)) (local.set $capacity (local.get ~a)) (local.set $result_scope (local.get ~a)) (local.set $top (local.get ~a))"
                      (b-store wasm32::tcr.root_head (b-local root)) base mode descriptor results capacity scope base)))
      (b-wat "(local.set ~a (local.get $top)) (local.set ~a ~a) (local.set ~a (local.get $dynamic_results)) (local.set ~a (local.get $result_descriptor)) (local.set ~a (local.get $results)) (local.set ~a (local.get $capacity)) (local.set ~a (local.get $result_scope)) ~a ~a (local.set $dynamic_results (i32.const 1)) (local.set $result_descriptor (local.get ~a)) (local.set $result_scope (local.get ~a)) (local.set $results (i32.const 0)) (local.set $capacity (i32.const 0)) (block $handler_done (block $handler_failed (result exnref) (try_table (catch_all_ref $handler_failed) ~a (br $handler_done)) unreachable) (local.set ~a) ~a (throw_ref (local.get ~a))) ~a"
        base root (b-load wasm32::tcr.root_head) mode descriptor results capacity scope
        (b-reserve-runtime "(i64.const 48)") (b-result-descriptor (b-local base) (b-local base)) base base call exception restore exception restore))))

;;; Checked call failures signal before unwinding. The private helper owns its
;;; scratch and restores the interrupted TCR state on every transfer. Conditions
;;; are newly allocated D1 vectors under the current condition representation;
;;; production CLOS layout and condition slot access are separate obligations.
(defun prior-numeric-b-implicit-runtime ()
 (if *b-allocation-retry* (progn 
  (pushnew "error_message" *b-symbols* :test #'equal)
  (pushnew "expected_function" *b-symbols* :test #'equal)
  (let ((*temporary-count* 0) (*b-exception-count* 0)
        (*b-tail-position* nil) (*b-producer-target* nil))
    (let* ((symbol (progn (pushnew "condition_registry" *b-symbols* :test #'equal) (b-special-symbol 'ccl::%handlers%)))
           (signal (b-signal (make-b-raw-code :text "(i32.load offset=24 (local.get $frame))") nil))
           (debugger (b-debugger "(i32.load offset=24 (local.get $frame))")))
      (with-output-to-string (s)
        (write-string "(func $implicit_error (param $kind i32) (param $top i32) (call $implicit_error_details (local.get $kind) (local.get $top) (i32.const 77825) (i32.const 77825)))
 (func $implicit_error_details (param $kind i32) (param $top i32) (param $datum i32) (param $expected i32)
          (local $incoming i32) (local $output i32) (local $owner i32) (local $root i32) (local $old_count i32)
          (local $frame i32) (local $results i32) (local $count i32) (local $value i32)
          (local $exception exnref) (local $wide i64) (local $capacity i32) (local $result_bytes i32)
          (local $dispatch_self i32) (local $dispatch_slot i32) (local $dynamic_results i32)
          (local $result_descriptor i32) (local $result_scope i32) (local $condition i32) (local $heap i32)" s)
        (dotimes (i *temporary-count*) (format s "(local $tmp~d i32)" i))
        (dotimes (i *b-exception-count*) (format s "(local $cleanup_exception~d exnref)" i))
        ;; With no handlers there is no Lisp continuation to invoke. Preserve
        ;; the structured fatal code rather than pretending a debugger exists.
        (format s "(if (i32.and (i32.ne (i32.load offset=192 (global.get $tcr)) (i32.const 1)) (i32.eq (call $special_read ~a) (i32.const 77825))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 1)) (else (local.get $kind))))))))" symbol)
        (format s "(local.set $incoming ~a) (local.set $output ~a) (local.set $owner ~a) (local.set $root ~a) (local.set $old_count ~a)"
          (b-load wasm32::tcr.vsp) (b-load wasm32::tcr.mv_base) (b-load wasm32::tcr.mv_owner_top) (b-load wasm32::tcr.root_head) (b-load wasm32::tcr.mv_count))
        (write-string "(local.set $frame (local.get $top)) (local.set $capacity (i32.const 4)) (local.set $result_bytes (i32.const 16)) (local.set $results (i32.add (local.get $frame) (i32.const 8)))" s)
        (write-string (b-reserve 32) s)
        (write-string "(block $implicit_failed (result exnref) (try_table (catch_all_ref $implicit_failed)" s)
        (write-string (b-initialize-roots "(local.get $frame)" 6) s)
        (write-string "(local.set $dynamic_results (i32.const 1)) (local.set $result_descriptor (local.get $top)) (local.set $result_scope (local.get $frame))" s)
        (write-string (b-reserve 48) s)
        (write-string (b-result-descriptor "(local.get $result_descriptor)" "(local.get $frame)") s)
        (write-string "(i32.store offset=8 (local.get $frame) (local.get $datum)) (i32.store offset=12 (local.get $frame) (local.get $expected))" s)
        (write-string "(local.set $condition (call $condition_new (if (result i32) (i32.eq (local.get $kind) (i32.const 1)) (then (i32.const 2076)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4124)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 2108)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 8)) (then (i32.const 284)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 17)) (then (i32.const 124)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 10)) (then (i32.const 8220)) (else (if (result i32) (i32.and (i32.ge_u (local.get $kind) (i32.const 18)) (i32.le_u (local.get $kind) (i32.const 20))) (then (i32.const 16396)) (else (i32.const 156))))))))))))))) (i32.add (local.get $frame) (i32.const 8)))) (i32.store (local.get $results) (local.get $condition)) (i32.store offset=24 (local.get $frame) (local.get $condition))" s)
        (write-string signal s) (write-string debugger s)
        (write-string "(throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 1)) (else (local.get $kind))))))) unreachable) (local.set $exception)" s)
        (dolist (row (list (cons wasm32::tcr.vsp "$incoming") (cons wasm32::tcr.mv_base "$output") (cons wasm32::tcr.mv_owner_top "$owner") (cons wasm32::tcr.root_head "$root") (cons wasm32::tcr.mv_count "$old_count")))
          (write-string (b-store (car row) (b-local (cdr row))) s))
        (write-string "(call $rv_release (local.get $frame)) (throw_ref (local.get $exception)))
          (func $resolve_lisp (param $node i32) (param $top i32) (result i32 i32) (local $code i32)
            (block $bad (result i32) (try_table (catch $call_error $bad) (return (call $resolve (local.get $node)))) unreachable)
            (local.set $code)
            (if (i32.ne (local.get $code) (i32.const 4)) (then (throw $call_error (local.get $code))))
            (call $implicit_error_details (call $designator_error_kind (local.get $node)) (local.get $top) (local.get $node) (i32.load offset=2 (global.get $symbol_expected_function))) unreachable)
          (func $function_value_lisp (param $node i32) (param $top i32) (result i32) (local $code i32)
            (block $bad (result i32) (try_table (catch $call_error $bad) (return (call $function_value (local.get $node)))) unreachable)
            (local.set $code)
            (if (i32.ne (local.get $code) (i32.const 4)) (then (throw $call_error (local.get $code))))
            (call $implicit_error_details (i32.const 14) (local.get $top) (local.get $node) (i32.const 77825)) unreachable)
          (func $designator_error_kind (param $node i32) (result i32)
            (if (i32.eq (local.get $node) (i32.const 77838)) (then (return (i32.const 14))))
            (if (i32.eq (i32.and (local.get $node) (i32.const 7)) (i32.const 6)) (then
              (if (i64.le_u (i64.add (i64.extend_i32_u (local.get $node)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then
                (if (i32.eq (i32.load (i32.sub (local.get $node) (i32.const 6))) (i32.const 1850)) (then (return (i32.const 14))))))))
            (i32.const 4))" s))))) (progn 
  (pushnew "error_message" *b-symbols* :test #'equal)
  (pushnew "expected_function" *b-symbols* :test #'equal)
  (let ((*temporary-count* 0) (*b-exception-count* 0)
        (*b-tail-position* nil) (*b-producer-target* nil))
    (let* ((symbol (progn (pushnew "condition_registry" *b-symbols* :test #'equal) (b-special-symbol 'ccl::%handlers%)))
           (signal (b-signal (make-b-raw-code :text "(i32.load offset=24 (local.get $frame))") nil))
           (debugger (b-debugger "(i32.load offset=24 (local.get $frame))")))
      (with-output-to-string (s)
        (write-string "(func $implicit_error (param $kind i32) (param $top i32) (call $implicit_error_details (local.get $kind) (local.get $top) (i32.const 77825) (i32.const 77825)))
 (func $implicit_error_details (param $kind i32) (param $top i32) (param $datum i32) (param $expected i32)
          (local $incoming i32) (local $output i32) (local $owner i32) (local $root i32) (local $old_count i32)
          (local $frame i32) (local $results i32) (local $count i32) (local $value i32)
          (local $exception exnref) (local $wide i64) (local $capacity i32) (local $result_bytes i32)
          (local $dispatch_self i32) (local $dispatch_slot i32) (local $dynamic_results i32)
          (local $result_descriptor i32) (local $result_scope i32) (local $condition i32) (local $heap i32)" s)
        (dotimes (i *temporary-count*) (format s "(local $tmp~d i32)" i))
        (dotimes (i *b-exception-count*) (format s "(local $cleanup_exception~d exnref)" i))
        ;; With no handlers there is no Lisp continuation to invoke. Preserve
        ;; the structured fatal code rather than pretending a debugger exists.
        (format s "(if (i32.and (i32.ne (i32.load offset=192 (global.get $tcr)) (i32.const 1)) (i32.eq (call $special_read ~a) (i32.const 77825))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 1)) (else (local.get $kind))))))))" symbol)
        (format s "(local.set $incoming ~a) (local.set $output ~a) (local.set $owner ~a) (local.set $root ~a) (local.set $old_count ~a)"
          (b-load wasm32::tcr.vsp) (b-load wasm32::tcr.mv_base) (b-load wasm32::tcr.mv_owner_top) (b-load wasm32::tcr.root_head) (b-load wasm32::tcr.mv_count))
        (write-string "(local.set $frame (local.get $top)) (local.set $capacity (i32.const 4)) (local.set $result_bytes (i32.const 16)) (local.set $results (i32.add (local.get $frame) (i32.const 8)))" s)
        (write-string (b-reserve 32) s)
        (write-string "(block $implicit_failed (result exnref) (try_table (catch_all_ref $implicit_failed)" s)
        (write-string (b-initialize-roots "(local.get $frame)" 6) s)
        (write-string "(local.set $dynamic_results (i32.const 1)) (local.set $result_descriptor (local.get $top)) (local.set $result_scope (local.get $frame))" s)
        (write-string (b-reserve 48) s)
        (write-string (b-result-descriptor "(local.get $result_descriptor)" "(local.get $frame)") s)
        (write-string "(i32.store offset=8 (local.get $frame) (local.get $datum)) (i32.store offset=12 (local.get $frame) (local.get $expected))" s)
        (write-string "(local.set $condition (call $condition_new (if (result i32) (i32.eq (local.get $kind) (i32.const 1)) (then (i32.const 2076)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4124)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 2108)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 8)) (then (i32.const 284)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 17)) (then (i32.const 124)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 10)) (then (i32.const 8220)) (else (if (result i32) (i32.and (i32.ge_u (local.get $kind) (i32.const 18)) (i32.le_u (local.get $kind) (i32.const 20))) (then (i32.const 16396)) (else (i32.const 156))))))))))))))) (local.get $datum) (local.get $expected))) (i32.store (local.get $results) (local.get $condition)) (i32.store offset=24 (local.get $frame) (local.get $condition))" s)
        (write-string signal s) (write-string debugger s)
        (write-string "(throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 14)) (then (i32.const 4)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 16)) (then (i32.const 1)) (else (local.get $kind))))))) unreachable) (local.set $exception)" s)
        (dolist (row (list (cons wasm32::tcr.vsp "$incoming") (cons wasm32::tcr.mv_base "$output") (cons wasm32::tcr.mv_owner_top "$owner") (cons wasm32::tcr.root_head "$root") (cons wasm32::tcr.mv_count "$old_count")))
          (write-string (b-store (car row) (b-local (cdr row))) s))
        (write-string "(call $rv_release (local.get $frame)) (throw_ref (local.get $exception)))
          (func $resolve_lisp (param $node i32) (param $top i32) (result i32 i32) (local $code i32)
            (block $bad (result i32) (try_table (catch $call_error $bad) (return (call $resolve (local.get $node)))) unreachable)
            (local.set $code)
            (if (i32.ne (local.get $code) (i32.const 4)) (then (throw $call_error (local.get $code))))
            (call $implicit_error_details (call $designator_error_kind (local.get $node)) (local.get $top) (local.get $node) (i32.load offset=2 (global.get $symbol_expected_function))) unreachable)
          (func $function_value_lisp (param $node i32) (param $top i32) (result i32) (local $code i32)
            (block $bad (result i32) (try_table (catch $call_error $bad) (return (call $function_value (local.get $node)))) unreachable)
            (local.set $code)
            (if (i32.ne (local.get $code) (i32.const 4)) (then (throw $call_error (local.get $code))))
            (call $implicit_error_details (i32.const 14) (local.get $top) (local.get $node) (i32.const 77825)) unreachable)
          (func $designator_error_kind (param $node i32) (result i32)
            (if (i32.eq (local.get $node) (i32.const 77838)) (then (return (i32.const 14))))
            (if (i32.eq (i32.and (local.get $node) (i32.const 7)) (i32.const 6)) (then
              (if (i64.le_u (i64.add (i64.extend_i32_u (local.get $node)) (i64.const 26)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then
                (if (i32.eq (i32.load (i32.sub (local.get $node) (i32.const 6))) (i32.const 1850)) (then (return (i32.const 14))))))))
            (i32.const 4))" s)))))))

;;; Isolated LL10 pass-2 extension, appended to the reviewed B backend.
(in-package "WASM32-COMPILER")
(defun pool-literal-p (x)
  (and (not (or (null x) (eq x t)
                (and (integerp x) (<= -536870912 x 536870911))))
       (or (and *bootstrap-front-end* (symbolp x))
           (integerp x) (floatp x) (characterp x) (consp x)
           (typep x 'simple-array))))
(defun pool-plan ()
  (setf *pool-layouts* nil)
  (dolist (entry (reverse *b-functions*))
    (let ((values (when *b-callable-metadata* (list (metadata-arity (first entry)) (metadata-debug (first entry))))) (children nil))
      (when *bootstrap-front-end*
        (setq values (append values (list #x574153 (bootstrap-lfun-bits (first entry))
          (let ((keys (fourth (ccl::acode-operands (ccl::afunc-acode (first entry))))))
            (and keys (copy-seq (or (fifth keys) #()))))))))
      (labels ((visit (x)
                 (cond ((ccl::acode-p x)
                        (let ((op (ccl::acode-operator-name (ccl::acode-operator x)))
                              (args (ccl::acode-operands x)))
                          (cond ((eq op 'ccl::immediate)
                                 (when (pool-literal-p (first args))
                                   (unless (member (first args) values :test #'eq)
                                     (setq values (append values (list (first args)))))))
                                ((member op '(ccl::closed-function ccl::simple-function))
                                 (pushnew (first args) children :test #'eq))
                                (t (when (member op '(ccl::flet ccl::labels))
                                     (dolist (child (second args)) (pushnew child children :test #'eq)))
                                   (mapc #'visit args)))))
                       ((consp x) (mapc #'visit x)))))
        (visit (ccl::afunc-acode (first entry))))
      (dolist (child children)
        (let ((pool (cdr (assoc child *pool-layouts* :test #'eq))))
          (when pool (setq values (append values (list pool))))))
      (push (cons (first entry) (and values (coerce values 'simple-vector))) *pool-layouts*))))
(defun pool-load (value)
  (let* ((pool (cdr (assoc *pool-current* *pool-layouts* :test #'eq)))
         (index (position value pool :test #'eq)) (tmp (temporary)))
    (unless index (refuse :constant-pool-identity))
    (b-wat "(block (result i32) (local.set ~a (call $object_base (i32.load offset=24 (call $object_base (i32.load offset=40 (local.get $context)) (i32.const 32) (i32.const 1578))) (i32.const ~d) (i32.const ~d))) (i32.load offset=~d (local.get ~a)))"
      tmp (* 8 (ceiling (+ 4 (* 4 (length pool))) 8)) (+ 250 (* 256 (length pool))) (+ 4 (* 4 index)) tmp)))
(defun pool-child-load (afunc)
  (let ((pool (cdr (assoc afunc *pool-layouts* :test #'eq))))
    (if pool (pool-load pool) "(i32.const 77825)")))
(defun compile-call-form (form name links)
  (unless (and (every (lambda (s) (and (stringp s) (<= 1 (length s) 64)
                    (every (lambda (c) (find c "abcdefghijklmnopqrstuvwxyz0123456789_-")) s))) links)
               (= (length links) (length (remove-duplicates links :test #'equal)))) (refuse :b-link-names))
  (call-with-target
    (lambda ()
      (let* ((*b-call-mode* t) (*b-special-names* '(ccl::%handlers% ccl::%restarts% *debugger-hook* ccl::*interrupt-level*)) (*b-keywords* nil)
             (*module-result-tag* (gensym "B-CALL")) (*module-name* name)
             (*package* (find-package "WASM32-COMPILER"))
             (*b-call-links* (mapcar (lambda (x) (list (intern (string-upcase x) *package*) x)) links)))
        (setq form (b-expand-conditions form))
        (validate-b-source form)
        (catch *module-result-tag*
          (ccl::compile-named-function (b-normalize-literal-apply form) :name name :target :wasm32 :policy ccl::*default-compiler-policy*)
          (refuse :b-no-output))))))
(defun compile-call-module (source-text name links)
  (let ((*read-eval* nil) (*package* (find-package "WASM32-COMPILER")))
    (multiple-value-bind (form end) (read-from-string source-text)
      (unless (every (lambda (c) (find c '(#\Space #\Tab #\Newline #\Return))) (subseq source-text end)) (refuse :b-source))
      (compile-call-form form name links))))

(in-package :wasm32-compiler)
(defun b-debugger (condition)
  (let ((symbol (b-special-symbol '*debugger-hook*)))
    (b-wat "(if (i32.eq ~a (i32.const 1)) (then ~a))" (b-load wasm32::tcr.error_service_mode)
      (b-frame 2
        (lambda (root)
          (let ((c (b-wat "(i32.load offset=8 ~a)" root))
                (hook (b-wat "(i32.load offset=12 ~a)" root))
                (depth (temporary)) (exception (b-exception-local)))
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a (call $special_read ~a))
              (if (i32.ne ~a (i32.const 77825)) (then
                (local.set ~a ~a)
                (if (i32.eq (local.get ~a) (i32.const -1)) (then (throw $call_error (i32.const 15))))
                (i32.store offset=184 (global.get $tcr) (i32.add (local.get ~a) (i32.const 1)))
                (block $debug_ok (block $debug_failed (result exnref) (try_table (catch_all_ref $debug_failed) ~a (br $debug_ok)) unreachable)
                  (local.set ~a) (i32.store offset=184 (global.get $tcr) (local.get ~a)) (throw_ref (local.get ~a)))
                (i32.store offset=184 (global.get $tcr) (local.get ~a))))"
              root condition root symbol hook depth (b-load wasm32::tcr.scratch1) depth depth
              (b-special-extent (lambda ()
                (concatenate 'string (b-bind-symbol symbol "(i32.const 77825)")
                  (b-discard-handler hook (make-b-raw-code :text c) (make-b-raw-code :text hook)))))
              exception depth exception depth)))))))

(in-package :wasm32-compiler)
(defun b-checked-cons-operation (op forms)
  (let* ((readp (member op '(car cdr ccl::%car ccl::%cdr)))
         (carp (member op '(car rplaca ccl::%car ccl::%rplaca ccl::set-car)))
         (offset (if carp wasm32::cons.car wasm32::cons.cdr)))
    (b-frame (length forms)
      (lambda (root)
        (let* ((p (b-wat "(i32.load offset=8 ~a)" root))
               (v (b-wat "(i32.load offset=12 ~a)" root))
               (bad (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 1))" p)))
          (with-output-to-string (s)
            (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar f)))
            (write-string (b-multiple (make-b-raw-code :text
              (b-wat "(if (result i32) (i32.eq ~a (i32.const 77825)) (then ~a) (else (if ~a (then ~a)) (call $span (i32.sub ~a (i32.const 1)) (i32.const 8)) ~a))"
                p (if readp "(i32.const 77825)" (b-type-failure p 'cons t)) bad (b-type-failure p (if readp 'list 'cons) t) p
                (if readp (b-wat "(i32.load (i32.add ~a (i32.const ~d)))" p offset)
                  (b-wat "(i32.store (i32.add ~a (i32.const ~d)) ~a) ~a" p offset v (if (member op '(ccl::set-car ccl::set-cdr)) v p)))))) s)))))))
(defun b-unbound-runtime ()
 "(func $special_read_lisp (param $symbol i32) (param $top i32) (result i32) (local $value i32)
 (local.set $value (i32.load (call $special_location (local.get $symbol))))
 (if (i32.eq (local.get $value) (i32.const 51)) (then (call $implicit_error_details (i32.const 10) (local.get $top) (local.get $symbol) (i32.const 77825)) unreachable))
 (local.get $value))")
(defun b-svref (forms)
  (unless (= (length forms) 2) (refuse :b-svref-arity))
  (b-frame 2 (lambda (root)
    (let* ((v (b-wat "(i32.load offset=8 ~a)" root)) (i (b-wat "(i32.load offset=12 ~a)" root)))
      (with-output-to-string (s)
        (format s "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)" root (b-scalar (first forms)) root (b-scalar (second forms)))
        (write-string (b-multiple (make-b-raw-code :text
          (b-wat "(block (result i32)
            (if (i32.ne (i32.and ~a (i32.const 7)) (i32.const 6)) (then ~a))
            (call $span (i32.sub ~a (i32.const 6)) (i32.const 4))
            (if (i32.ne (i32.and (i32.load (i32.sub ~a (i32.const 6))) (i32.const 255)) (i32.const 250)) (then ~a))
            (if (i32.and ~a (i32.const 3)) (then ~a))
            (if (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (i32.load (i32.sub ~a (i32.const 6))) (i32.const 8))) (then (call $implicit_error (i32.const 17) (local.get $top)) unreachable))
            (call $span (i32.sub ~a (i32.const 6)) (i32.add (i32.const 4) (i32.mul (i32.shr_u (i32.load (i32.sub ~a (i32.const 6))) (i32.const 8)) (i32.const 4))))
            (i32.load (i32.add (i32.sub ~a (i32.const 2)) ~a)))" v (b-type-failure v 'simple-vector) v v (b-type-failure v 'simple-vector) i (b-type-failure i 'fixnum) i v v v v i))) s))))))
(defun b-condition-field (name forms)
  (unless (= (length forms) 1) (refuse :b-condition-reader-arity))
  (b-frame 1 (lambda (root)
    (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar (first forms))
      (b-multiple (make-b-raw-code :text
        (b-wat "(call $condition_field (i32.load offset=8 ~a) (i32.const ~d) (i32.const ~d) (local.get $top))"
          root (if (eq name '%wasm-cell-name) 3072 32) (if (eq name '%wasm-condition-expected) 12 8))))))))
(defun b-type-failure (datum expected &optional legacy-cons-p)
  (concatenate 'string
    (when legacy-cons-p
      (b-wat "(if (i32.and (i32.ne ~a (i32.const 1)) (i32.eq (call $special_read ~a) (i32.const 77825))) (then (throw $type_error ~a (i32.const 1))))"
        (b-load wasm32::tcr.error_service_mode) (b-special-symbol 'ccl::%handlers%) datum))
    (b-wat "(call $implicit_error_details (i32.const 5) (local.get $top) ~a ~a) unreachable" datum (b-restart-symbol expected))))

(in-package :wasm32-compiler)
(defun b-restart-list (forms)
  (reduce (lambda (a b) `(cons ,a ,b)) forms :from-end t :initial-value nil))
(defun b-expand-restart (form walk lambda-list)
  (let* ((casep (eq (car form) 'restart-case))
         (clauses (if casep (cddr form) (second form)))
         (block (gensym "RESTART-BLOCK")) (tag (gensym "RESTART-TAG"))
         (packet (gensym "RESTART-VALUES")) (bindings nil) (dispatch nil))
    (loop for clause in clauses for index from 0 do
      (unless (and (consp clause) (and (symbolp (first clause)) (first clause)) (>= (length clause) 2)) (refuse :b-restart-clause))
      (pushnew (first clause) *b-restart-names*)
      ;; Owner-registered keyword names for the initial interface; arbitrary
      ;; package symbol installation belongs to the symbol namespace unit.
      (when (and casep (keywordp (third clause))) (refuse :b-restart-options))
      (unless (or casep (= (length clause) 2)) (refuse :b-restart-options))
      (let* ((name (gensym "RESTART")) (args (gensym "RESTART-ARGS"))
             (action (if casep `(lambda (&rest ,args) (throw ,tag (cons ,index ,args))) (funcall walk (second clause)))))
        (push (list name `(%wasm-make-restart (quote ,(first clause)) ,(if casep `(function ,action) action))) bindings)
        (when casep
          (push `(if (eq (car ,packet) ,index)
                   (apply (function (lambda ,(funcall lambda-list (second clause)) ,@(mapcar walk (cddr clause)))) (cdr ,packet))) dispatch))))
    (setq bindings (nreverse bindings) dispatch (nreverse dispatch))
    (if casep
      `(block ,block
         (let* ((,tag (cons nil nil))
                (,packet (let* (,@bindings
                                (ccl::%restarts% (cons ,(b-restart-list (mapcar #'first bindings)) ccl::%restarts%)))
                           (catch ,tag (return-from ,block ,(funcall walk (second form)))))))
           ,(reduce (lambda (item rest) `(if ,(second item) ,(third item) ,rest)) dispatch :from-end t :initial-value nil)))
      `(let* (,@bindings (ccl::%restarts% (cons ,(b-restart-list (mapcar #'first bindings)) ccl::%restarts%)))
         ,@(mapcar walk (cddr form))))))
(defun b-restart-call (name forms)
 (if *b-allocation-retry* (progn 
  (setq *b-restart-used* t)
  (unless (case name (%wasm-make-restart (= (length forms) 2))
                    (%wasm-find-restart (<= 1 (length forms) 2))
                    (%wasm-restart-name (= (length forms) 1))
                    (%wasm-invoke-restart (>= (length forms) 1))) (refuse :b-restart-arity))
  (let ((*b-tail-position* nil))
    (b-frame (length forms)
      (lambda (root)
        (with-output-to-string (s)
          (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar f)))
          (flet ((arg (i) (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) root)))
            (if (eq name '%wasm-invoke-restart)
              (write-string (b-call nil (list (loop for i from 1 below (length forms) collect (make-b-raw-code :text (arg i))) nil)
                                   (b-wat "(i32.load offset=12 (call $restart_base (call $restart_find ~a (i32.const 1) (local.get $top))))" (arg 0))) s)
              (write-string (b-multiple (make-b-raw-code :text
                 (case name
                   (%wasm-make-restart (b-wat "(call $restart_make (i32.add ~a (i32.const 8)))" root))
                   (%wasm-find-restart
                    (when (= (length forms) 2) (refuse :b-restart-condition-association))
                    (b-wat "(call $restart_find ~a (i32.const 0) (local.get $top))" (arg 0)))
                   (%wasm-restart-name (b-wat "(i32.load offset=8 (call $restart_base ~a))" (arg 0)))))) s)))))))) (progn 
  (setq *b-restart-used* t)
  (unless (case name (%wasm-make-restart (= (length forms) 2))
                    (%wasm-find-restart (<= 1 (length forms) 2))
                    (%wasm-restart-name (= (length forms) 1))
                    (%wasm-invoke-restart (>= (length forms) 1))) (refuse :b-restart-arity))
  (let ((*b-tail-position* nil))
    (b-frame (length forms)
      (lambda (root)
        (with-output-to-string (s)
          (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar f)))
          (flet ((arg (i) (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) root)))
            (if (eq name '%wasm-invoke-restart)
              (write-string (b-call nil (list (loop for i from 1 below (length forms) collect (make-b-raw-code :text (arg i))) nil)
                                   (b-wat "(i32.load offset=12 (call $restart_base (call $restart_find ~a (i32.const 1) (local.get $top))))" (arg 0))) s)
              (write-string (b-multiple (make-b-raw-code :text
                 (case name
                   (%wasm-make-restart (b-wat "(call $restart_make ~a ~a (local.get $top))" (arg 0) (arg 1)))
                   (%wasm-find-restart
                    (when (= (length forms) 2) (refuse :b-restart-condition-association))
                    (b-wat "(call $restart_find ~a (i32.const 0) (local.get $top))" (arg 0)))
                   (%wasm-restart-name (b-wat "(i32.load offset=8 (call $restart_base ~a))" (arg 0)))))) s))))))))))
(defun b-restart-runtime ()
 (if *b-allocation-retry* (progn 
  (pushnew "restart_type" *b-symbols* :test #'equal)
  (let ((registry (b-special-symbol 'ccl::%restarts%)))
    (b-wat "
(func $restart_base (param $x i32) (result i32)
 (local $p i32)
 (local.set $p (call $object_base (local.get $x) (i32.const 32) (i32.const 1666)))
 (if (i32.ne (i32.load offset=4 (local.get $p)) (global.get $symbol_restart_type)) (then (throw $call_error (i32.const 4))))
 (local.get $p))
(func $restart_make (param $arguments i32) (result i32) (local $name i32) (local $action i32) (local $p i32)
 (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.extend_i32_u (i32.const 32))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.const 32))))
 (local.set $name (i32.load (local.get $arguments))) (local.set $action (i32.load offset=4 (local.get $arguments)))
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 32)) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (call $span (local.get $p) (i32.const 32))
 (i32.store (local.get $p) (i32.const 1666))
 (i32.store offset=4 (local.get $p) (global.get $symbol_restart_type))
 (i32.store offset=8 (local.get $p) (local.get $name))
 (i32.store offset=12 (local.get $p) (local.get $action))
 (i32.store offset=16 (local.get $p) (i32.const 77825))
 (i32.store offset=20 (local.get $p) (i32.const 77825))
 (i32.store offset=24 (local.get $p) (i32.const 77825))
 (i32.store offset=28 (local.get $p) (i32.const 77825))
 (i32.store offset=48 (global.get $tcr) (i32.add (local.get $p) (i32.const 32)))
 (i32.add (local.get $p) (i32.const 6)))
(func $restart_find (param $name i32) (param $required i32) (param $top i32) (result i32)
 (local $clusters i32) (local $items i32) (local $restart i32) (local $base i32)
 (local.set $clusters (call $special_read ~a))
 (block $absent (loop $clusters_loop
  (br_if $absent (i32.eq (local.get $clusters) (i32.const 77825)))
  (local.set $items (i32.load offset=4 (call $handler_cons (local.get $clusters))))
  (block $cluster_done (loop $items_loop
   (br_if $cluster_done (i32.eq (local.get $items) (i32.const 77825)))
   (local.set $restart (i32.load offset=4 (call $handler_cons (local.get $items))))
   (local.set $base (call $restart_base (local.get $restart)))
   (if (i32.or (i32.eq (local.get $name) (local.get $restart)) (i32.eq (local.get $name) (i32.load offset=8 (local.get $base)))) (then (return (local.get $restart))))
   (local.set $items (i32.load (call $handler_cons (local.get $items)))) (br $items_loop)))
  (local.set $clusters (i32.load (call $handler_cons (local.get $clusters)))) (br $clusters_loop)))
 (if (local.get $required) (then (call $implicit_error (i32.const 8) (local.get $top)) unreachable))
 (i32.const 77825))" registry))) (progn 
  (pushnew "restart_type" *b-symbols* :test #'equal)
  (let ((registry (b-special-symbol 'ccl::%restarts%)))
    (b-wat "
(func $restart_base (param $x i32) (result i32)
 (local $p i32)
 (local.set $p (call $object_base (local.get $x) (i32.const 32) (i32.const 1666)))
 (if (i32.ne (i32.load offset=4 (local.get $p)) (global.get $symbol_restart_type)) (then (throw $call_error (i32.const 4))))
 (local.get $p))
(func $restart_make (param $name i32) (param $action i32) (param $top i32) (result i32) (local $p i32)
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 32)) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (call $span (local.get $p) (i32.const 32))
 (i32.store (local.get $p) (i32.const 1666))
 (i32.store offset=4 (local.get $p) (global.get $symbol_restart_type))
 (i32.store offset=8 (local.get $p) (local.get $name))
 (i32.store offset=12 (local.get $p) (local.get $action))
 (i32.store offset=16 (local.get $p) (i32.const 77825))
 (i32.store offset=20 (local.get $p) (i32.const 77825))
 (i32.store offset=24 (local.get $p) (i32.const 77825))
 (i32.store offset=28 (local.get $p) (i32.const 77825))
 (i32.store offset=48 (global.get $tcr) (i32.add (local.get $p) (i32.const 32)))
 (i32.add (local.get $p) (i32.const 6)))
(func $restart_find (param $name i32) (param $required i32) (param $top i32) (result i32)
 (local $clusters i32) (local $items i32) (local $restart i32) (local $base i32)
 (local.set $clusters (call $special_read ~a))
 (block $absent (loop $clusters_loop
  (br_if $absent (i32.eq (local.get $clusters) (i32.const 77825)))
  (local.set $items (i32.load offset=4 (call $handler_cons (local.get $clusters))))
  (block $cluster_done (loop $items_loop
   (br_if $cluster_done (i32.eq (local.get $items) (i32.const 77825)))
   (local.set $restart (i32.load offset=4 (call $handler_cons (local.get $items))))
   (local.set $base (call $restart_base (local.get $restart)))
   (if (i32.or (i32.eq (local.get $name) (local.get $restart)) (i32.eq (local.get $name) (i32.load offset=8 (local.get $base)))) (then (return (local.get $restart))))
   (local.set $items (i32.load (call $handler_cons (local.get $items)))) (br $items_loop)))
  (local.set $clusters (i32.load (call $handler_cons (local.get $clusters)))) (br $clusters_loop)))
 (if (local.get $required) (then (call $implicit_error (i32.const 8) (local.get $top)) unreachable))
 (i32.const 77825))" registry)))))
(defun b-restart-symbol (symbol)
  (when *bootstrap-front-end*
    (return-from b-restart-symbol (bootstrap-symbol symbol)))
  (when (eq symbol 'or) (pushnew "expected_or" *b-symbols* :test #'equal) (return-from b-restart-symbol "(global.get $symbol_expected_or)"))
  (when (eq symbol 'function) (pushnew "expected_function" *b-symbols* :test #'equal) (return-from b-restart-symbol "(global.get $symbol_expected_function)"))
  (unless (and (symbolp symbol) symbol (symbol-package symbol)) (refuse :b-restart-symbol))
  (let ((name (with-output-to-string (s)
                (write-string "restart_name_" s)
                (loop for c across (package-name (symbol-package symbol)) do (format s "~6,'0x" (char-code c)))
                (write-char #\_ s)
                (loop for c across (symbol-name symbol) do (format s "~6,'0x" (char-code c))))))
    (pushnew name *b-symbols* :test #'equal)
    (b-wat "(global.get $symbol_~a)" name)))

(defun prior-numeric-b-condition-runtime ()
 (if *b-allocation-retry* (progn  (concatenate 'string (b-handler-runtime) ";; Sealed bootstrap classes. Registry rows are [wrapper, ancestry mask,
;; slot defaults]. Instances and slot vectors use U1's D1 CLOS layouts.
(func $condition_row (param $key i32) (param $by_wrapper i32) (result i32)
 (local $table i32) (local $row i32) (local $i i32) (local $n i32)
 (local.set $table (i32.sub (global.get $symbol_condition_registry) (i32.const 6)))
 (if (i32.ne (i32.and (global.get $symbol_condition_registry) (i32.const 7)) (i32.const 6)) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $table)) (i32.const 8)))
 (if (i32.or (i32.ne (i32.and (i32.load (local.get $table)) (i32.const 255)) (i32.const 250)) (i32.and (i32.ne (local.get $n) (i32.const 12)) (i32.ne (local.get $n) (i32.const 13)))) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))
 (loop $rows
  (if (i32.ge_u (local.get $i) (local.get $n)) (then (throw $call_error (i32.const 5))))
  (local.set $row (call $object_base (i32.load (i32.add (local.get $table) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4))))) (i32.const 16) (i32.const 1018)))
  (if (i32.eq (i32.load (i32.add (local.get $row) (if (result i32) (local.get $by_wrapper) (then (i32.const 4)) (else (i32.const 8))))) (local.get $key)) (then (return (local.get $row))))
  (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $rows)) unreachable)
(func $condition_slots (param $x i32) (result i32)
 (local $p i32) (local $row i32) (local $slots i32) (local $defaults i32) (local $n i32)
 (local.set $p (call $object_base (local.get $x) (i32.const 16) (i32.const 882)))
 (local.set $row (call $condition_row (i32.load offset=8 (local.get $p)) (i32.const 1)))
 (drop (call $object_base (i32.load offset=4 (local.get $row)) (i32.const 56) (i32.const 3578)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (call $span (local.get $defaults) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $defaults)) (i32.const 8)))
 (if (i32.or (i32.gt_u (local.get $n) (i32.const 4)) (i32.ne (i32.and (i32.load (local.get $defaults)) (i32.const 255)) (i32.const 250))) (then (throw $call_error (i32.const 5))))
 (local.set $slots (call $object_base (i32.load offset=12 (local.get $p)) (i32.mul (i32.add (local.get $n) (i32.const 2)) (i32.const 4)) (i32.add (i32.shl (i32.add (local.get $n) (i32.const 1)) (i32.const 8)) (i32.const 106))))
 (if (i32.ne (i32.load offset=4 (local.get $slots)) (local.get $x)) (then (throw $call_error (i32.const 5))))
 (local.get $slots))
(func $condition_mask (param $x i32) (result i32)
 (drop (call $condition_slots (local.get $x)))
 (i32.shr_u (i32.load offset=8 (call $condition_row (i32.load offset=2 (local.get $x)) (i32.const 1))) (i32.const 2)))
(func $condition_new (param $mask i32) (param $arguments i32) (result i32) (local $datum i32) (local $expected i32)
 (local $row i32) (local $defaults i32) (local $n i32) (local $bytes i32) (local $p i32) (local $slots i32) (local $i i32)
 (local.set $row (call $condition_row (local.get $mask) (i32.const 0)))
 (drop (call $object_base (i32.load offset=4 (local.get $row)) (i32.const 56) (i32.const 3578)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (call $span (local.get $defaults) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $defaults)) (i32.const 8)))
 (if (i32.or (i32.gt_u (local.get $n) (i32.const 4)) (i32.ne (i32.and (i32.load (local.get $defaults)) (i32.const 255)) (i32.const 250))) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $defaults) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))
 (local.set $bytes (i32.and (i32.add (i32.mul (local.get $n) (i32.const 4)) (i32.const 31)) (i32.const -8)))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.extend_i32_u (local.get $bytes))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (local.get $bytes))))
 (local.set $row (call $condition_row (local.get $mask) (i32.const 0)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (local.set $datum (i32.load (local.get $arguments))) (local.set $expected (i32.load offset=4 (local.get $arguments)))
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $bytes))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (call $span (local.get $p) (local.get $bytes))
 (local.set $slots (i32.add (local.get $p) (i32.const 16)))
 (i32.store (local.get $p) (i32.const 882))
 (i32.store offset=4 (local.get $p) (i32.and (local.get $p) (i32.const 2147483644)))
 (i32.store offset=8 (local.get $p) (i32.load offset=4 (local.get $row)))
 (i32.store offset=12 (local.get $p) (i32.add (local.get $slots) (i32.const 6)))
 (i32.store (local.get $slots) (i32.add (i32.shl (i32.add (local.get $n) (i32.const 1)) (i32.const 8)) (i32.const 106)))
 (i32.store offset=4 (local.get $slots) (i32.add (local.get $p) (i32.const 6)))
 (block $copied (loop $copy
  (br_if $copied (i32.ge_u (local.get $i) (local.get $n)))
  (i32.store (i32.add (local.get $slots) (i32.add (i32.const 8) (i32.mul (local.get $i) (i32.const 4)))) (i32.load (i32.add (local.get $defaults) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4))))))
  (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $copy)))
 (if (i32.or (i32.eq (local.get $mask) (i32.const 156)) (i32.or (i32.eq (local.get $mask) (i32.const 4124)) (i32.eq (local.get $mask) (i32.const 8220)))) (then (i32.store offset=8 (local.get $slots) (local.get $datum))))
 (if (i32.eq (local.get $mask) (i32.const 156)) (then (i32.store offset=12 (local.get $slots) (local.get $expected))))
 (if (i32.eq (local.get $mask) (i32.const 32796)) (then (i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (local.get $expected))))
 (if (i32.or (i32.eq (local.get $mask) (i32.const 124)) (i32.eq (local.get $mask) (i32.const 2108))) (then (i32.store offset=8 (local.get $slots) (global.get $symbol_error_message))))
 (i32.store offset=48 (global.get $tcr) (i32.add (local.get $p) (local.get $bytes)))
 (i32.add (local.get $p) (i32.const 6)))
(func $condition_field (param $x i32) (param $mask i32) (param $offset i32) (param $top i32) (result i32)
 (if (i32.eqz (i32.and (call $condition_mask (local.get $x)) (local.get $mask))) (then (call $implicit_error (i32.const 5) (local.get $top)) unreachable))
 (i32.load (i32.add (call $condition_slots (local.get $x)) (local.get $offset))))
")) (progn  (concatenate 'string (b-handler-runtime) ";; Sealed bootstrap classes. Registry rows are [wrapper, ancestry mask,
;; slot defaults]. Instances and slot vectors use U1's D1 CLOS layouts.
(func $condition_row (param $key i32) (param $by_wrapper i32) (result i32)
 (local $table i32) (local $row i32) (local $i i32) (local $n i32)
 (local.set $table (i32.sub (global.get $symbol_condition_registry) (i32.const 6)))
 (if (i32.ne (i32.and (global.get $symbol_condition_registry) (i32.const 7)) (i32.const 6)) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $table)) (i32.const 8)))
 (if (i32.or (i32.ne (i32.and (i32.load (local.get $table)) (i32.const 255)) (i32.const 250)) (i32.and (i32.ne (local.get $n) (i32.const 12)) (i32.ne (local.get $n) (i32.const 13)))) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))
 (loop $rows
  (if (i32.ge_u (local.get $i) (local.get $n)) (then (throw $call_error (i32.const 5))))
  (local.set $row (call $object_base (i32.load (i32.add (local.get $table) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4))))) (i32.const 16) (i32.const 1018)))
  (if (i32.eq (i32.load (i32.add (local.get $row) (if (result i32) (local.get $by_wrapper) (then (i32.const 4)) (else (i32.const 8))))) (local.get $key)) (then (return (local.get $row))))
  (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $rows)) unreachable)
(func $condition_slots (param $x i32) (result i32)
 (local $p i32) (local $row i32) (local $slots i32) (local $defaults i32) (local $n i32)
 (local.set $p (call $object_base (local.get $x) (i32.const 16) (i32.const 882)))
 (local.set $row (call $condition_row (i32.load offset=8 (local.get $p)) (i32.const 1)))
 (drop (call $object_base (i32.load offset=4 (local.get $row)) (i32.const 56) (i32.const 3578)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (call $span (local.get $defaults) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $defaults)) (i32.const 8)))
 (if (i32.or (i32.gt_u (local.get $n) (i32.const 4)) (i32.ne (i32.and (i32.load (local.get $defaults)) (i32.const 255)) (i32.const 250))) (then (throw $call_error (i32.const 5))))
 (local.set $slots (call $object_base (i32.load offset=12 (local.get $p)) (i32.mul (i32.add (local.get $n) (i32.const 2)) (i32.const 4)) (i32.add (i32.shl (i32.add (local.get $n) (i32.const 1)) (i32.const 8)) (i32.const 106))))
 (if (i32.ne (i32.load offset=4 (local.get $slots)) (local.get $x)) (then (throw $call_error (i32.const 5))))
 (local.get $slots))
(func $condition_mask (param $x i32) (result i32)
 (drop (call $condition_slots (local.get $x)))
 (i32.shr_u (i32.load offset=8 (call $condition_row (i32.load offset=2 (local.get $x)) (i32.const 1))) (i32.const 2)))
(func $condition_new (param $mask i32) (param $datum i32) (param $expected i32) (result i32)
 (local $row i32) (local $defaults i32) (local $n i32) (local $bytes i32) (local $p i32) (local $slots i32) (local $i i32)
 (local.set $row (call $condition_row (local.get $mask) (i32.const 0)))
 (drop (call $object_base (i32.load offset=4 (local.get $row)) (i32.const 56) (i32.const 3578)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (call $span (local.get $defaults) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $defaults)) (i32.const 8)))
 (if (i32.or (i32.gt_u (local.get $n) (i32.const 4)) (i32.ne (i32.and (i32.load (local.get $defaults)) (i32.const 255)) (i32.const 250))) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $defaults) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))
 (local.set $bytes (i32.and (i32.add (i32.mul (local.get $n) (i32.const 4)) (i32.const 31)) (i32.const -8)))
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $bytes))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (throw $call_error (i32.const 6))))
 (call $span (local.get $p) (local.get $bytes))
 (local.set $slots (i32.add (local.get $p) (i32.const 16)))
 (i32.store (local.get $p) (i32.const 882))
 (i32.store offset=4 (local.get $p) (i32.and (local.get $p) (i32.const 2147483644)))
 (i32.store offset=8 (local.get $p) (i32.load offset=4 (local.get $row)))
 (i32.store offset=12 (local.get $p) (i32.add (local.get $slots) (i32.const 6)))
 (i32.store (local.get $slots) (i32.add (i32.shl (i32.add (local.get $n) (i32.const 1)) (i32.const 8)) (i32.const 106)))
 (i32.store offset=4 (local.get $slots) (i32.add (local.get $p) (i32.const 6)))
 (block $copied (loop $copy
  (br_if $copied (i32.ge_u (local.get $i) (local.get $n)))
  (i32.store (i32.add (local.get $slots) (i32.add (i32.const 8) (i32.mul (local.get $i) (i32.const 4)))) (i32.load (i32.add (local.get $defaults) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4))))))
  (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $copy)))
 (if (i32.or (i32.eq (local.get $mask) (i32.const 156)) (i32.or (i32.eq (local.get $mask) (i32.const 4124)) (i32.eq (local.get $mask) (i32.const 8220)))) (then (i32.store offset=8 (local.get $slots) (local.get $datum))))
 (if (i32.eq (local.get $mask) (i32.const 156)) (then (i32.store offset=12 (local.get $slots) (local.get $expected))))
 (if (i32.eq (local.get $mask) (i32.const 32796)) (then (i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (local.get $expected))))
 (if (i32.or (i32.eq (local.get $mask) (i32.const 124)) (i32.eq (local.get $mask) (i32.const 2108))) (then (i32.store offset=8 (local.get $slots) (global.get $symbol_error_message))))
 (i32.store offset=48 (global.get $tcr) (i32.add (local.get $p) (local.get $bytes)))
 (i32.add (local.get $p) (i32.const 6)))
(func $condition_field (param $x i32) (param $mask i32) (param $offset i32) (param $top i32) (result i32)
 (if (i32.eqz (i32.and (call $condition_mask (local.get $x)) (local.get $mask))) (then (call $implicit_error (i32.const 5) (local.get $top)) unreachable))
 (i32.load (i32.add (call $condition_slots (local.get $x)) (local.get $offset))))
"))))

(defun b-stacks-runtime () "(func $stack_guard (param $end i64) (param $top i32) (param $kind i32)
 (local $base i32) (local $limit i32) (local $reserve i32) (local $flags i32) (local $exception exnref)
 (if (i32.eq (local.get $kind) (i32.const 18))
  (then (local.set $base (i32.load offset=68 (global.get $tcr))) (local.set $limit (i32.load offset=72 (global.get $tcr))))
  (else (if (i32.eq (local.get $kind) (i32.const 19))
   (then (local.set $base (i32.load offset=80 (global.get $tcr))) (local.set $limit (i32.load offset=84 (global.get $tcr))))
   (else (local.set $base (i32.load offset=92 (global.get $tcr))) (local.set $limit (i32.load offset=96 (global.get $tcr)))))))
 (local.set $reserve (i32.load offset=100 (global.get $tcr)))
 (if (i32.or (i32.and (i32.or (local.get $base) (i32.or (local.get $limit) (local.get $reserve))) (i32.const 15))
             (i32.or (i32.gt_u (local.get $base) (local.get $limit)) (i32.gt_u (local.get $reserve) (i32.sub (local.get $limit) (local.get $base))))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 19)) (then (i32.const 13)) (else (i32.const 2))))))
 (if (i64.gt_u (i64.extend_i32_u (local.get $limit)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 19)) (then (i32.const 13)) (else (i32.const 2))))))
 (if (i64.gt_u (local.get $end) (i64.extend_i32_u (local.get $limit))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 19)) (then (i32.const 13)) (else (i32.const 2))))))
 (if (i64.lt_u (local.get $end) (i64.extend_i32_u (local.get $base))) (then (throw $call_error (if (result i32) (i32.eq (local.get $kind) (i32.const 19)) (then (i32.const 13)) (else (i32.const 2))))))
 (local.set $flags (i32.load offset=180 (global.get $tcr)))
 (if (i32.and (i32.ne (local.get $reserve) (i32.const 0)) (i32.eqz (i32.and (local.get $flags) (i32.const 1)))) (then
  (if (i64.gt_u (local.get $end) (i64.extend_i32_u (i32.sub (local.get $limit) (local.get $reserve)))) (then
   (i32.store offset=180 (global.get $tcr) (i32.or (local.get $flags) (i32.const 1)))
   (block $stack_failed (result exnref) (try_table (catch_all_ref $stack_failed)
    (call $implicit_error (local.get $kind) (local.get $top)) unreachable) unreachable)
   (local.set $exception)
   (i32.store offset=180 (global.get $tcr) (local.get $flags))
   (throw_ref (local.get $exception)))))))
(func $control_push (param $record i32) (param $top i32) (local $p i32)
 (if (i32.eqz (i32.load offset=92 (global.get $tcr))) (then (return)))
 (local.set $p (i32.load offset=88 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.lt_u (local.get $p) (i32.load offset=92 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))
 (call $stack_guard (i64.add (i64.extend_i32_u (local.get $p)) (i64.const 16)) (local.get $top) (i32.const 20))
 (i32.store (local.get $p) (local.get $record))
 (i32.store offset=4 (local.get $p) (i32.const 1129533489))
 (i32.store offset=8 (local.get $p) (i32.const 0)) (i32.store offset=12 (local.get $p) (i32.const 0))
 (i32.store offset=88 (global.get $tcr) (i32.add (local.get $p) (i32.const 16))))
(func $control_pop (param $record i32) (local $p i32)
 (if (i32.eqz (i32.load offset=92 (global.get $tcr))) (then (return)))
 (local.set $p (i32.load offset=88 (global.get $tcr)))
 (if (i32.or (i32.and (local.get $p) (i32.const 15)) (i32.le_u (local.get $p) (i32.load offset=92 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))
 (local.set $p (i32.sub (local.get $p) (i32.const 16))) (call $span (local.get $p) (i32.const 16))
 (if (i32.or (i32.ne (i32.load (local.get $p)) (local.get $record)) (i32.ne (i32.load offset=4 (local.get $p)) (i32.const 1129533489))) (then (throw $call_error (i32.const 2))))
 (i32.store offset=88 (global.get $tcr) (local.get $p)))
")

(in-package :wasm32-compiler)
(defun b-poll ()
  (let ((*b-tail-position* nil)
        (level (b-special-symbol 'ccl::*interrupt-level*))
        (gc (b-special-symbol 'ccl::%wasm-gc-service%))
        (interrupt (b-special-symbol 'ccl::%wasm-interrupt-service%)))
    (b-wat "(if (i32.and (i32.atomic.load offset=36 (global.get $tcr)) (i32.const 1)) (then ~a))
      (if (i32.ge_s (call $special_read ~a) (i32.const 0)) (then
        (if (i32.and (i32.atomic.rmw.and offset=36 (global.get $tcr) (i32.const -3)) (i32.const 2)) (then ~a)))) ~a"
      (b-discard-handler (b-wat "(call $special_read ~a)" gc) nil nil t) level
      (b-discard-handler (b-wat "(call $special_read ~a)" interrupt) nil nil t)
      (b-multiple (make-b-raw-code :text "(i32.const 77825)")))))

(in-package :wasm32-compiler)
(defun b-symbol-access (name forms)
 (let ((readp (eq name '%wasm-symbol-value)))
  (unless (= (length forms) (if readp 1 2)) (refuse :symbol-access-arity))
  (b-frame (length forms) (lambda (root)
   (let ((symbol (b-wat "(i32.load offset=8 ~a)" root))
         (value (b-wat "(i32.load offset=12 ~a)" root)))
    (with-output-to-string (s)
     (loop for f in forms for i from 0 do (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar f)))
     (write-string (b-multiple (make-b-raw-code :text
       (b-wat "(block (result i32)
        (if (i32.or (i32.eq ~a (i32.const 77825)) (i32.eq ~a (i32.const 77838))) (then ~a))
        (if (i32.ne (i32.and ~a (i32.const 7)) (i32.const 6)) (then ~a))
        (call $span (i32.sub ~a (i32.const 6)) (i32.const 32))
        (if (i32.ne (i32.load (i32.sub ~a (i32.const 6))) (i32.const 1850)) (then ~a))
        ~a)"
        symbol symbol
        (if readp (b-wat "(br 1 ~a)" symbol) "(call $implicit_error (i32.const 17) (local.get $top)) unreachable")
        symbol (b-type-failure symbol 'symbol) symbol symbol (b-type-failure symbol 'symbol)
        (if readp (b-wat "(call $special_read_lisp ~a (local.get $top))" symbol)
            (b-wat "(if (i32.and (i32.load offset=14 ~a) (i32.const 8)) (then (call $implicit_error (i32.const 17) (local.get $top)) unreachable)) (i32.store (call $special_location ~a) ~a) ~a" symbol symbol value value))))) s))))))
)

(in-package :wasm32-compiler)
(defun b-allocation-runtime () "(func $heap_ensure (param $bytes i32)
 (local $p i32) (local $limit i32)
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (local.set $limit (i32.load offset=52 (global.get $tcr)))
 (if (i32.or (i32.eqz (local.get $bytes)) (i32.and (local.get $bytes) (i32.const 7))) (then (throw $call_error (i32.const 6))))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.or (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr))) (i32.gt_u (local.get $p) (local.get $limit)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.extend_i32_u (local.get $limit)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $bytes))) (i64.extend_i32_u (local.get $limit)))
  (then (call $owner_ensure (local.get $bytes)))))")
(defun compile-retrying-call-module (source-text name links)
 (let ((*b-allocation-retry* t)) (compile-call-module source-text name links)))
(defun compile-retrying-call-form (form name links)
 (let ((*b-allocation-retry* t)) (compile-call-form form name links)))

(in-package :wasm32-compiler)

;;; GO uses the existing checked exit record so lexical/dynamic frames and
;;; cleanup extents retire before the next segment. A local branch alone would
;;; bypass their restoration. Program counters are untagged, never GC roots.
(defun b-unwinding-tagbody (tags forms)
  (let ((pc (temporary)) (segments (list nil)) (positions nil) (index 0))
    (dolist (form forms)
      (if (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::tag-label)
        (progn (incf index) (push nil segments)
               (push (cons (first (ccl::acode-operands form)) index) positions))
        (push form (car segments))))
    (unless (every (lambda (tag) (assoc tag positions :test #'eq)) tags)
      (refuse :b-tag-identity))
    (setq segments (mapcar #'reverse (reverse segments)))
    (let ((code
           (b-exit-frame 3 "(i32.const 77825)"
             (lambda (record)
               (let ((*b-local-tags* (append (mapcar (lambda (p) (list (car p) pc (cdr p) record)) positions) *b-local-tags*)))
                 (with-output-to-string (s)
                   (loop for segment in segments for n from 0 do
                     (format s "(if (i32.le_u (local.get ~a) (i32.const ~d)) (then " pc n)
                     (dolist (form segment) (format s "(drop ~a)" (b-scalar form)))
                     (write-string "))" s))
                   (format s "(local.set ~a (i32.const -1))" pc)
                   (write-string (b-multiple (make-b-raw-code :text "(i32.const 77825)")) s)))))))
      (b-wat "(local.set ~a (i32.const 0)) (block $tagbody_done (loop $tagbody_loop ~a (br_if $tagbody_done (i32.eq (local.get ~a) (i32.const -1))) (br $tagbody_loop))) ~a"
        pc code pc (b-multiple (make-b-raw-code :text "(i32.const 77825)"))))))

(defun b-go (tag)
  (let* ((entry (or (assoc tag *b-local-tags* :test #'eq) (refuse :b-go-identity)))
         (record (fourth entry)))
    (when (fifth entry)
      (return-from b-go
        (b-wat "(local.set ~a (i32.const ~d)) (br ~a)"
          (second entry) (third entry) (fifth entry))))
    (concatenate 'string
      (b-wat "(local.set ~a (i32.const ~d)) (i32.store offset=12 ~a (i32.const 0))" (second entry) (third entry) record)
      (b-store wasm32::tcr.unwind_state "(i32.const 1)")
      (b-wat "(throw $nonlocal_exit ~a)" record))))

(in-package :wasm32-compiler)

;;; A branch is legal only in a statement/IF-arm position beneath this
;;; TAGBODY, with no intervening emitter-owned root or dynamic extent.
;;; Other operators may execute freely, but must contain no local GO.
;;; In particular a GO in IF's test, call operands, LET, PROG1, cleanup,
;;; binding, or another TAGBODY takes the existing addressed-exit path.
(defun b-branch-tagbody-p (tags forms)
  (labels ((no-go (x)
             (cond ((ccl::acode-p x)
                    (let ((op (ccl::acode-operator-name (ccl::acode-operator x))))
                      (case op
                        (ccl::local-go nil)
                        ((ccl::tag-label ccl::immediate ccl::closed-function ccl::simple-function) t)
                        (t (every #'no-go (ccl::acode-operands x))))))
                   ((consp x) (and (no-go (car x)) (no-go (cdr x))))
                   (t t)))
           (statement (x)
             (if (not (ccl::acode-p x)) (no-go x)
               (let ((op (ccl::acode-operator-name (ccl::acode-operator x)))
                     (args (ccl::acode-operands x)))
                 (case op
                   (ccl::local-go (member (first args) tags :test #'eq))
                   (ccl::tag-label t)
                   (ccl::%decls-body (statement (first args)))
                   (ccl::progn (every #'statement (first args)))
                   (ccl::if (and (no-go (first args)) (statement (second args)) (statement (third args))))
                   (t (no-go x)))))))
    (every #'statement forms)))

(defun b-tagbody (tags forms)
  (unless (b-branch-tagbody-p tags forms)
    (return-from b-tagbody (b-unwinding-tagbody tags forms)))
  (let* ((pc (temporary)) (label (concatenate 'string "$tag_branch_" (subseq pc 1)))
         (segments (list nil)) (positions nil) (index 0))
    (dolist (form forms)
      (if (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::tag-label)
        (progn (incf index) (push nil segments)
               (push (cons (first (ccl::acode-operands form)) index) positions))
        (push form (car segments))))
    (unless (every (lambda (tag) (assoc tag positions :test #'eq)) tags)
      (refuse :b-tag-identity))
    (setq segments (mapcar #'reverse (reverse segments)))
    (let* ((*b-tail-position* nil)
           (*b-local-tags* (append (mapcar (lambda (p) (list (car p) pc (cdr p) nil label)) positions) *b-local-tags*))
           (body (with-output-to-string (s)
             (loop for segment in segments for n from 0 do
               (format s "(if (i32.le_u (local.get ~a) (i32.const ~d)) (then " pc n)
               (dolist (form segment) (format s "(drop ~a)" (b-scalar form)))
               (write-string "))" s)))))
      (b-wat "(local.set ~a (i32.const 0)) (loop ~a ~a) ~a"
        pc label body (b-multiple (make-b-raw-code :text "(i32.const 77825)"))))))

(in-package :wasm32-compiler)
;;; All data uses the existing graph encoder; names retain package identity.
(defun metadata-symbol (s)
  (vector (and (symbol-package s) (package-name (symbol-package s))) (symbol-name s)))
(defun metadata-arity (afunc)
  (let* ((args (ccl::acode-operands (ccl::afunc-acode afunc)))
         (keys (fourth args)))
    (vector 1 (length (first args)) (length (first (second args)))
            (not (null (third args))) (not (null keys)) (not (null (first keys)))
            (copy-seq (or (fifth keys) #())))))
(defun metadata-debug (afunc)
  (let ((entry (assoc afunc *b-functions* :test #'eq))
        (vars (cdr (assoc afunc *b-environments* :test #'eq))))
    (vector 1 (second entry)
            (coerce (loop for v in vars for i from 0 collect
                      (vector i (metadata-symbol (ccl::var-name (ccl::nx-root-var v))))) 'vector))))
(defun metadata-child-load (afunc index)
  (if (not *b-callable-metadata*) "(i32.const 77825)"
    (let ((pool (cdr (assoc afunc *pool-layouts* :test #'eq))))
      (unless (and pool (>= (length pool) 2)) (refuse :callable-metadata-pool))
      (b-wat "(i32.load offset=~d (call $object_base ~a (i32.const ~d) (i32.const ~d)))"
        (+ 4 (* 4 index)) (pool-child-load afunc)
        (* 8 (ceiling (+ 4 (* 4 (length pool))) 8)) (+ 250 (* 256 (length pool)))))))
(defun metadata-entry (afunc)
  (if (not *b-callable-metadata*) ""
    (let* ((pool (cdr (assoc afunc *pool-layouts* :test #'eq)))
           (self (temporary)) (p (temporary)) (arity (temporary)) (debug (temporary))
           (a (metadata-arity afunc)))
      (b-wat "(local.set ~a (call $object_base (i32.load offset=40 (local.get $context)) (i32.const 32) (i32.const 1578)))
        (local.set ~a (call $object_base (i32.load offset=24 (local.get ~a)) (i32.const ~d) (i32.const ~d)))
        (if (i32.or (i32.ne (i32.load offset=16 (local.get ~a)) (i32.load offset=4 (local.get ~a))) (i32.ne (i32.load offset=20 (local.get ~a)) (i32.load offset=8 (local.get ~a)))) (then (throw $call_error (i32.const 4))))
        (local.set ~a (call $object_base (i32.load offset=16 (local.get ~a)) (i32.const 32) (i32.const 2042)))
        (local.set ~a (call $object_base (i32.load offset=20 (local.get ~a)) (i32.const 16) (i32.const 1018)))
        (if (i32.or (i32.ne (i32.load offset=4 (local.get ~a)) (i32.const 4)) (i32.ne (i32.load offset=4 (local.get ~a)) (i32.const 4))) (then (throw $call_error (i32.const 4))))
        (if (i32.or (i32.ne (i32.load offset=8 (local.get ~a)) (i32.const ~d)) (i32.ne (i32.load offset=12 (local.get ~a)) (i32.const ~d))) (then (throw $call_error (i32.const 4))))"
        self p self (* 8 (ceiling (+ 4 (* 4 (length pool))) 8)) (+ 250 (* 256 (length pool)))
        self p self p arity self debug self arity debug arity (* 4 (aref a 1)) arity (* 4 (aref a 2))))))
(defun compile-metadata-call-form (form name links)
  (let ((*b-callable-metadata* t)) (compile-call-form form name links)))
(defun compile-metadata-call-module (source name links)
  (let ((*b-callable-metadata* t)) (compile-call-module source name links)))

(in-package :wasm32-compiler)
(defun gd-condition-call (name forms)
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (if (eq name 'gd_condition)
    (progn
      (unless (= (length forms) 2) (refuse :gd-constructor-arity))
      (let ((*b-tail-position* nil) (*b-producer-target* nil))
        (b-frame 2
          (lambda (root)
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) ~a"
              root (b-scalar (first forms)) root (b-scalar (second forms))
              (b-multiple (make-b-raw-code :text
                (if *b-allocation-retry*
                  (b-wat "(call $condition_new (i32.const 32796) (i32.add ~a (i32.const 8)))" root)
                  (b-wat "(call $condition_new (i32.const 32796) (i32.load offset=8 ~a) (i32.load offset=12 ~a))" root root)))))))))
    (progn
      (unless (= (length forms) 1) (refuse :gd-reader-arity))
      (b-frame 1
        (lambda (root)
          (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar (first forms))
            (b-multiple (make-b-raw-code :text
              (b-wat "(call $condition_field (i32.load offset=8 ~a) (i32.const 8192) (i32.const ~d) (local.get $top))"
                root (if (eq name 'gd_condition_gf) 8 12))))))))))

(in-package :wasm32-compiler)
(defun b-integer-call (name forms)
 (let ((op (position name '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate))))
  (unless (= (length forms) (if (= op 4) 1 2)) (refuse :integer-arity))
  (b-frame 2 (lambda (root)
   (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)
    (local.set $count (call $integer (i32.const ~d) ~a)) ~a
    (i32.store (local.get $results) (i32.load offset=8 ~a))
    (if (i32.eq (local.get $count) (i32.const 2)) (then (i32.store offset=4 (local.get $results) (i32.load offset=12 ~a))))"
    root (b-scalar (first forms)) root (if (= op 4) "(i32.const 0)" (b-scalar (second forms))) op root
    (b-ensure-results "(local.get $count)") root root)))))
(defun compile-integer-call-form (form name links)
 (let ((*b-integer-service* t) (*b-callable-metadata* t)) (compile-call-form form name links)))
(defun b-integer-runtime ()
 "(func $integer (param $op i32) (param $root i32) (result i32)
 (local $a i32) (local $b i32) (local $r i64) (local $rem i64) (local $count i32)
 (local.set $a (i32.load offset=8 (local.get $root)))
 (local.set $b (i32.load offset=12 (local.get $root)))
 (block $slow
  (br_if $slow (i32.and (i32.or (local.get $a) (local.get $b)) (i32.const 3)))
  (local.set $a (i32.shr_s (local.get $a) (i32.const 2)))
  (local.set $b (i32.shr_s (local.get $b) (i32.const 2)))
  (local.set $count (i32.const 1))
  (if (i32.eq (local.get $op) (i32.const 0)) (then (local.set $r (i64.add (i64.extend_i32_s (local.get $a)) (i64.extend_i32_s (local.get $b))))))
  (if (i32.eq (local.get $op) (i32.const 1)) (then (local.set $r (i64.sub (i64.extend_i32_s (local.get $a)) (i64.extend_i32_s (local.get $b))))))
  (if (i32.eq (local.get $op) (i32.const 2)) (then (local.set $r (i64.mul (i64.extend_i32_s (local.get $a)) (i64.extend_i32_s (local.get $b))))))
  (if (i32.eq (local.get $op) (i32.const 3)) (then
   (if (i32.lt_s (local.get $b) (i32.const 0))
    (then (local.set $r (i64.extend_i32_s (i32.shr_s (local.get $a) (select (i32.const 31) (i32.sub (i32.const 0) (local.get $b)) (i32.le_s (local.get $b) (i32.const -31)))))))
    (else (if (local.get $a) (then (br_if $slow (i32.gt_u (local.get $b) (i32.const 29)))
     (local.set $r (i64.shl (i64.extend_i32_s (local.get $a)) (i64.extend_i32_u (local.get $b))))))))))
  (if (i32.eq (local.get $op) (i32.const 4)) (then
   (local.set $r (i64.extend_i32_u (i32.sub (i32.const 32) (i32.clz (i32.xor (local.get $a) (i32.shr_s (local.get $a) (i32.const 31)))))))))
  (if (i32.eq (local.get $op) (i32.const 5)) (then
   (br_if $slow (i32.eqz (local.get $b)))
   (local.set $r (i64.div_s (i64.extend_i32_s (local.get $a)) (i64.extend_i32_s (local.get $b))))
   (local.set $rem (i64.rem_s (i64.extend_i32_s (local.get $a)) (i64.extend_i32_s (local.get $b))))
   (local.set $count (i32.const 2))))
  (br_if $slow (i32.or (i64.lt_s (local.get $r) (i64.const -536870912)) (i64.gt_s (local.get $r) (i64.const 536870911))))
  (i32.store offset=8 (local.get $root) (i32.shl (i32.wrap_i64 (local.get $r)) (i32.const 2)))
  (i32.store offset=12 (local.get $root) (i32.shl (i32.wrap_i64 (local.get $rem)) (i32.const 2)))
  (return (local.get $count)))
 (call $integer_slow (local.get $op) (local.get $root)))")

(in-package :wasm32-compiler)
(defun numeric-text (text old new)
 (let ((p (search old text)))
  (unless (and p (not (search old text :start2 (+ p (length old))))) (error "Numeric runtime anchor"))
  (concatenate 'string (subseq text 0 p) new (subseq text (+ p (length old))))))
(defun prior-float-b-condition-runtime ()
 (let ((s (prior-numeric-b-condition-runtime)))
  (if *b-integer-service*
   (numeric-text
    (numeric-text s "(i32.ne (local.get $n) (i32.const 13))" "(i32.and (i32.ne (local.get $n) (i32.const 13)) (i32.ne (local.get $n) (i32.const 15)))")
    "(i32.eq (local.get $mask) (i32.const 32796))"
    "(i32.or (i32.eq (local.get $mask) (i32.const 32796)) (i32.eq (local.get $mask) (i32.const 196636)))") s)))
(defun prior-float-b-implicit-runtime ()
 (let ((s (prior-numeric-b-implicit-runtime)))
  (if *b-integer-service*
   (numeric-text s "(else (i32.const 156))" "(else (if (result i32) (i32.eq (local.get $kind) (i32.const 34)) (then (i32.const 196636)) (else (i32.const 156))))") s)))
(defun b-numeric-field (name forms)
 (unless (= (length forms) 1) (refuse :numeric-reader-arity))
 (b-frame 1 (lambda (root)
  (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar (first forms))
   (b-multiple (make-b-raw-code :text (b-wat "(call $condition_field (i32.load offset=8 ~a) (i32.const 16384) (i32.const ~d) (local.get $top))" root (if (eq name '%numeric-operation) 8 12))))))))
(defun b-integer-call (name forms)
 (let ((op (position name '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate))))
  (unless (= (length forms) (if (= op 4) 1 2)) (refuse :integer-arity))
  (b-frame 2 (lambda (root)
   (let ((a (b-wat "(i32.load offset=8 ~a)" root)) (b (b-wat "(i32.load offset=12 ~a)" root)))
    (concatenate 'string
     (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)" root (b-scalar (first forms)) root (if (= op 4) "(i32.const 0)" (b-scalar (second forms))))
     ;; Native CCL treats an explicit NIL divisor like the omitted default.
     ;; Evaluation is already complete; normalize only the private operand root.
     (when (= op 5) (b-wat "(if (i32.eq ~a (i32.const 77825)) (then (i32.store offset=12 ~a (i32.const 4))))" b root))
     (with-output-to-string (s)
      (dolist (value (cond ((= op 4) (list a)) ((= op 3) (list b a)) (t (list a b))))
       ;; Recognised noninteger numbers stay at the unsupported-numeric boundary;
       ;; they must not signal TYPE-ERROR with NUMBER as their expected type.
       (write-string (b-wat "(if (i32.eqz (call $integer_operand ~a)) (then ~a))" value (b-type-failure value (cond ((< op 3) 'number) ((= op 5) 'real) (t 'integer)))) s)))
     (when (= op 5)
      (b-wat "(if (i32.eqz ~a) (then ~a))" b
       (b-frame 1 (lambda (pair)
        (b-wat "(i32.store offset=8 ~a ~a) (call $implicit_error_details (i32.const 34) (local.get $top) ~a (i32.load offset=8 ~a)) unreachable"
         pair (b-cons (make-b-raw-code :text a) (make-b-raw-code :text (b-cons (make-b-raw-code :text b) (make-b-raw-code :text "(i32.const 77825)")))) (b-restart-symbol 'truncate) pair)))))
     (b-wat "(local.set $count (call $integer (i32.const ~d) ~a)) ~a
      (i32.store (local.get $results) (i32.load offset=8 ~a))
      (if (i32.eq (local.get $count) (i32.const 2)) (then (i32.store offset=4 (local.get $results) (i32.load offset=12 ~a))))"
      op root (b-ensure-results "(local.get $count)") root root)))))))
;; Keep the accepted arithmetic helper unchanged; add a checked classification
;; of admitted operands before entering it.
(setf (symbol-function 'prior-numeric-integer-runtime) (symbol-function 'b-integer-runtime))
(defun b-integer-runtime ()
 (concatenate 'string (prior-numeric-integer-runtime)
 "(func $integer_operand (param $x i32) (result i32) (local $p i32) (local $tag i32)
 (if (i32.eqz (i32.and (local.get $x) (i32.const 3))) (then (return (i32.const 1))))
 (if (i32.ne (i32.and (local.get $x) (i32.const 7)) (i32.const 6)) (then (return (i32.const 0))))
 (local.set $p (i32.sub (local.get $x) (i32.const 6))) (call $span (local.get $p) (i32.const 4))
 (local.set $tag (i32.and (i32.load (local.get $p)) (i32.const 255)))
 (if (i32.eq (local.get $tag) (i32.const 7)) (then (return (i32.const 1))))
 (if (i32.or (i32.or (i32.eq (local.get $tag) (i32.const 10)) (i32.eq (local.get $tag) (i32.const 26)))
  (i32.or (i32.or (i32.eq (local.get $tag) (i32.const 15)) (i32.eq (local.get $tag) (i32.const 23)))
   (i32.or (i32.eq (local.get $tag) (i32.const 71)) (i32.eq (local.get $tag) (i32.const 79)))))
  (then (throw $call_error (i32.const 32))))
 (i32.const 0))"))

(in-package :wasm32-compiler)
(defun compile-float-call-form (form name links &optional (safety 1))
 (unless (member safety '(0 1)) (refuse :float-safety))
 (let ((*b-float-service* t) (*b-float-safety* safety) (*b-integer-service* t) (*b-callable-metadata* t) (*b-allocation-retry* t))
  (compile-call-form form name links)))
(defun b-condition-runtime ()
 (let ((s (prior-float-b-condition-runtime)))
  (when *bootstrap-front-end*
    (setq s (with-output-to-string (out)
              (loop with old = "(i32.gt_u (local.get $n) (i32.const 4))"
                    for start = 0 then (+ end (length old))
                    for end = (search old s :start2 start) do
                (write-string s out :start start :end end)
                (unless end (return))
                (write-string "(i32.gt_u (local.get $n) (i32.const 5))" out))))
    (setq s (numeric-text s "(i32.ne (local.get $n) (i32.const 15))"
                             "(i32.and (i32.ne (local.get $n) (i32.const 28)) (i32.ne (local.get $n) (i32.const 15)))")))
  (if *b-float-service*
   (numeric-text (numeric-text s "(i32.ne (local.get $n) (i32.const 15))" "(i32.and (i32.ne (local.get $n) (i32.const 15)) (i32.ne (local.get $n) (i32.const 19)))")
    "(i32.eq (local.get $mask) (i32.const 196636))" "(i32.ne (i32.and (local.get $mask) (i32.const 65536)) (i32.const 0))") s)))
(defun b-implicit-runtime ()
 (let ((s (prior-float-b-implicit-runtime)))
  (if *b-float-service*
   (numeric-text s "(else (i32.const 156))"
    "(else (if (result i32) (i32.eq (local.get $kind) (i32.const 35)) (then (i32.const 327708)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 36)) (then (i32.const 589852)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 37)) (then (i32.const 1114140)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 38)) (then (i32.const 2162716)) (else (i32.const 156))))))))))") s)))
(defun b-float-call (name forms)
 (let* ((names '(%float-add %float-sub %float-mul %float-div %float-lt %float-le %float-eq %float-ne %float-ge %float-gt %float-single %float-double %libm-expt64 %libm-expt32 %libm-sin64 %libm-sin32 %libm-cos64 %libm-cos32 %libm-acos64 %libm-acos32 %libm-asin64 %libm-asin32 %libm-cosh64 %libm-cosh32 %libm-log64 %libm-log32 %libm-tan64 %libm-tan32 %libm-atan64 %libm-atan32 %libm-atan264 %libm-atan232 %libm-exp64 %libm-exp32 %libm-sinh64 %libm-sinh32 %libm-tanh64 %libm-tanh32 %libm-asinh64 %libm-asinh32 %libm-acosh64 %libm-acosh32 %libm-atanh64 %libm-atanh32 %libm-sqrt64 %libm-sqrt32))
        (op (position name names)) (operation (nth op '(+ - * / < <= = /= >= > float float expt expt sin sin cos cos acos acos asin asin cosh cosh log log tan tan atan atan atan atan exp exp sinh sinh tanh tanh asinh asinh acosh acosh atanh atanh sqrt sqrt))) (unary (and (>= op 10) (not (member op '(12 13 30 31))))))
  (unless (= (length forms) 2) (refuse :float-arity))
  (b-frame 4 (lambda (root)
   (let ((a (b-wat "(i32.load offset=8 ~a)" root)) (b (b-wat "(i32.load offset=12 ~a)" root)) (status (temporary)))
    (let ((prefix (concatenate 'string
     (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)" root (b-scalar (first forms)) root (b-scalar (second forms)))
     (with-output-to-string (s)
      (dolist (v (if unary (list a) (list a b)))
       (write-string (b-wat "(if (i32.eqz (call $real_operand ~a)) (then ~a))" v (b-type-failure v (if (< op 4) 'number 'real))) s))))))
     (let ((floating (concatenate 'string
     (b-wat "(local.set ~a (call $float_slow (i32.const ~d) ~a (i32.const ~d)))" status op root *b-float-safety*)
     (b-wat "(if (i32.and (local.get ~a) (i32.const 31)) (then ~a))" status
      (b-frame 1 (lambda (pair)
       (b-wat "(i32.store offset=8 ~a ~a) (call $implicit_error_details ~a (local.get $top) ~a (i32.load offset=8 ~a)) unreachable"
        pair (b-cons (make-b-raw-code :text a) (make-b-raw-code :text (if unary "(i32.const 77825)" (b-cons (make-b-raw-code :text b) (make-b-raw-code :text "(i32.const 77825)")))))
        (b-wat "(call $float_kind (i32.and (local.get ~a) (i32.const 31)))" status) (b-restart-symbol operation) pair))))
     (b-multiple (make-b-raw-code :text (b-wat "(i32.load offset=16 ~a)" root))))))
      (concatenate 'string prefix
       (if (or (< op 3) (and *bootstrap-front-end* (= op 3)))
        (b-wat "(if (i32.and (i32.eq (call $real_operand ~a) (i32.const 1)) (i32.eq (call $real_operand ~a) (i32.const 1))) (then ~a) (else ~a))"
         a b (if (= op 3) (bootstrap-integer-division root) (b-integer-call (nth op '(%integer-add %integer-sub %integer-mul)) (list (make-b-raw-code :text a) (make-b-raw-code :text b)))) floating)
        floating)))))))))
(defun b-float-runtime ()
 "(func $float_kind (param $flags i32) (result i32)
 (if (i32.eq (local.get $flags) (i32.const 1)) (then (return (i32.const 35))))
 (if (i32.eq (local.get $flags) (i32.const 2)) (then (return (i32.const 34))))
 (if (i32.eq (local.get $flags) (i32.const 4)) (then (return (i32.const 36))))
 (if (i32.eq (local.get $flags) (i32.const 8)) (then (return (i32.const 37))))
 (i32.const 38))
 (func $real_operand (param $x i32) (result i32) (local $p i32) (local $tag i32)
 (if (i32.eqz (i32.and (local.get $x) (i32.const 3))) (then (return (i32.const 1))))
 (if (i32.ne (i32.and (local.get $x) (i32.const 7)) (i32.const 6)) (then (return (i32.const 0))))
 (local.set $p (i32.sub (local.get $x) (i32.const 6))) (call $span (local.get $p) (i32.const 4))
 (local.set $tag (i32.and (i32.load (local.get $p)) (i32.const 255)))
 (if (i32.eq (local.get $tag) (i32.const 7)) (then (return (i32.const 1))))
 (if (i32.eq (i32.load (local.get $p)) (i32.const 271)) (then (call $span (local.get $p) (i32.const 8)) (return (i32.const 32))))
 (if (i32.eq (i32.load (local.get $p)) (i32.const 791)) (then (call $span (local.get $p) (i32.const 16)) (return (i32.const 64))))
 (if (i32.or (i32.eq (local.get $tag) (i32.const 10)) (i32.or (i32.eq (local.get $tag) (i32.const 26)) (i32.or (i32.eq (local.get $tag) (i32.const 71)) (i32.eq (local.get $tag) (i32.const 79))))) (then (throw $call_error (i32.const 32))))
 (i32.const 0))")

;;; Bootstrap source is trusted CCL source, read in the target environment.
;;; CCL's front end handles lexical macro scope and declarations. Unsupported
;;; acode still refuses in the Wasm emitter; the legacy source API is unchanged.
(in-package :wasm32-compiler)

(defun compile-bootstrap-form (form name links &optional env)
  (unless (and (every (lambda (entry)
                       (and (listp entry) (= (length entry) 2)
                            (symbolp (first entry)) (first entry)
                            (stringp (second entry))
                            (<= 1 (length (second entry)) 64)
                            (every (lambda (c)
                                     (find c "abcdefghijklmnopqrstuvwxyz0123456789_-"))
                                   (second entry))))
                     links)
               (= (length links) (length (remove-duplicates links :key #'first)))
               (= (length links) (length (remove-duplicates links :key #'second :test #'equal))))
    (refuse :bootstrap-links))
  (let ((*bootstrap-front-end* t)
        (*b-integer-service* t)
        (*b-float-service* t)
        (*bootstrap-self-call* nil)
        (*bootstrap-emitted* (make-hash-table :test #'eq))
        (*bootstrap-symbols* nil)
        (*bootstrap-callees* nil)
        (*bootstrap-dynamic-call* nil)
        (*b-call-mode* t)
        (*b-special-names* '(ccl::%handlers% ccl::%restarts% *debugger-hook* ccl::*interrupt-level*))
        (*b-keywords* nil)
        (*b-call-links* links)
        (*module-name* name)
        (*module-result-tag* (gensym "BOOTSTRAP"))
        ;; Native compiler macros may fold using host representation facts.
        ;; Ordinary macros and NX1's target-aware operators remain available.
        (ccl::*nx-compile-time-compiler-macros* nil)
        (ccl::*compiler-macros* (make-hash-table :test #'eq))
        (*macroexpand-hook* (bootstrap-macroexpand-hook))
        (ccl::*nx1-alphatizers* (bootstrap-alphatizers)))
    (catch *module-result-tag*
      (ccl::compile-named-function (bootstrap-function-form form)
                                  :name (if (eq (car form) 'defun) (second form) name)
                                  :target :wasm32
                                  :policy ccl::*default-compiler-policy* :env env)
      (refuse :b-no-output))))

(defun compile-bootstrap-source (source name links &optional (package "CCL"))
  (call-with-target
   (lambda ()
     (let ((*read-eval* nil) (*package* (or (find-package package)
                                         (refuse :bootstrap-package))))
       (with-input-from-string (stream source)
         (let ((form (read stream)) (end (gensym "EOF")))
           (unless (eq end (read stream nil end)) (refuse :bootstrap-source))
           (compile-bootstrap-form form name links)))))))

(defun bootstrap-function-form (form)
  (if (eq (car form) 'defun)
    (let* ((expansion (macroexpand-1 form))
           (definition (second expansion))
           (function (second definition)))
      ;; Extract the function from CCL's own DEFUN expansion. In particular,
      ;; keep GLOBAL-FUNCTION-NAME, declarations and the implicit BLOCK.
      (unless (and (eq (car expansion) 'progn)
                   (eq (car definition) 'ccl::%defun)
                   (eq (car function) 'ccl::nfunction)
                   (equal (second function) (second form)))
        (refuse :bootstrap-defun-expansion))
      (third function))
    form))

(defun bootstrap-eq (args)
  (unless (and (= (length args) 3)
               (member (ccl::acode-immediate-operand (first args)) '(:eq :ne)))
    (refuse :bootstrap-comparison))
  (b-wat "(block (result i32) ~a)"
         (b-frame 2
                  (lambda (root)
                    (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) (if (result i32) (i32.~a (i32.load offset=8 ~a) (i32.load offset=12 ~a)) (then (i32.const 77838)) (else (i32.const 77825)))"
                           root (b-scalar (second args))
                           root (b-scalar (third args))
                           (if (eq (ccl::acode-immediate-operand (first args)) :eq) "eq" "ne")
                           root root)))))

(defun bootstrap-no-load-time-value (context form environment)
  (declare (ignore context form environment))
  ;; NX1 recursively compiles this form before emitting LOAD-TIME-VALUE.
  ;; It must not escape through the enclosing module's pass-2 result tag.
  (refuse :bootstrap-load-time-value))

(defun bootstrap-macroexpand-hook ()
  ;; Validate the native handler macros wherever NX1 encounters them, including
  ;; inside local macros. A lexical macro with the same name is not this API.
  (let ((hook *macroexpand-hook*)
        (bind (macro-function 'handler-bind))
        (case (macro-function 'handler-case)) (bits (macro-function 'ccl::lfun-bits-known-function)))
    (lambda (expander form environment)
      (when (or (eq expander bind) (eq expander case))
        (dolist (clause (if (eq expander bind) (second form) (cddr form)))
          (unless (and (consp clause) (listp clause))
            (refuse :b-handler-clause))
          (unless (and (eq expander case) (eq (car clause) :no-error))
            (b-condition-mask (car clause)))))
      (if (eq expander bits)
          (progn
            (unless (= (length form) 2) (refuse :function-bits-arity))
            (list 'ccl::lfun-bits (second form)))
          (funcall hook expander form environment)))))

(defun bootstrap-alphatizers ()
  (let ((table (make-hash-table :test #'eq)))
    (maphash (lambda (name function) (setf (gethash name table) function))
             ccl::*nx1-alphatizers*)
    (setf (gethash 'load-time-value table) #'bootstrap-no-load-time-value)
    table))

(in-package :wasm32-compiler)

(defun bootstrap-symbol (symbol)
  ;; Imports name owner-supplied identities, not package lookups at run time.
  ;; The module record retains the actual symbol, including uninterned ones.
  (unless (symbolp symbol) (refuse :bootstrap-symbol))
  (let ((entry (assoc symbol *bootstrap-symbols*)))
    (unless entry
      (setq entry (list symbol (format nil "bootstrap_~d" (length *bootstrap-symbols*))))
      (push entry *bootstrap-symbols*))
    (pushnew (second entry) *b-symbols* :test #'equal)
    (b-wat "(global.get $symbol_~a)" (second entry))))

(in-package :wasm32-compiler)

(defun bootstrap-or (forms)
  (if (null (cdr forms))
    (b-multiple (car forms))
    (let ((value (temporary)))
      ;; Only the last operand inherits tail position and multiple values.
      ;; No call or safepoint intervenes between testing and publishing a
      ;; successful primary value. Result assurance cannot collect.
      (b-wat "(local.set ~a ~a) (if (i32.ne (local.get ~a) (i32.const 77825)) (then ~a) (else ~a))"
             value (let ((*b-tail-position* nil)) (b-scalar (car forms)))
             value
             (b-multiple (make-b-raw-code :text (b-local value)))
             (bootstrap-or (cdr forms))))))

(in-package :wasm32-compiler)

(defun bootstrap-boolean (test &optional (condition :eq))
  (unless (member condition '(:eq :ne)) (refuse :bootstrap-condition))
  (b-wat "(if (result i32) ~a (then (i32.const ~d)) (else (i32.const ~d)))"
         test (if (eq condition :eq) 77838 77825)
         (if (eq condition :eq) 77825 77838)))

(defun bootstrap-operands (forms function)
  ;; Every operand remains rooted while later operands run.
  (b-wat "(block (result i32) ~a)"
         (b-frame (length forms)
                  (lambda (base)
                    (with-output-to-string (s)
                      (loop for form in forms for i from 0 do
                        (format s "(i32.store offset=~d ~a ~a)"
                                (+ 8 (* 4 i)) base (b-scalar form)))
                      (write-string
                       (funcall function
                                (loop for i below (length forms)
                                      collect (b-wat "(i32.load offset=~d ~a)"
                                                     (+ 8 (* 4 i)) base)))
                       s))))))

(defun bootstrap-typecode (value)
  (let ((x (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a) (if (result i32) (i32.eq (i32.and (local.get ~a) (i32.const 3)) (i32.const 2)) (then (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4)) (i32.shl (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 2))) (else (i32.shl (i32.and (local.get ~a) (i32.const 3)) (i32.const 2)))))"
           x value x x x x)))

(defun bootstrap-node-access (op args)
  (bootstrap-operands
   args
   (lambda (values)
     (destructuring-bind (object index &optional value) values
       (let* ((base (temporary)) (header (temporary)) (answer (temporary))
              (subtag (case op
                        ((ccl::svref ccl::svset) wasm32::subtag-simple-vector)
                        ((ccl::struct-ref ccl::struct-set) wasm32::subtag-struct)))
              (address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" base index)))
         (with-output-to-string (s)
           (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
           (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
           (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 2))" header) 4) s)
           (when subtag
             (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d))" header subtag) 4) s))
           (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
           (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shl (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 2))))" base header)
           (if value
             (format s "(i32.store ~a ~a) ~a" address value value)
             (progn
               (format s "(local.set ~a (i32.load ~a))" answer address)
               (when (eq op 'ccl::%slot-ref)
                 (write-string (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const ~d))" answer wasm32::subtag-slot-unbound) 4) s))
               (format s "(local.get ~a)" answer)))))))))

(defun bootstrap-gvector (forms)
  (unless forms (refuse :bootstrap-gvector))
  (let ((subtag (ccl::acode-fixnum-form-p (car forms)))
        (n (length (cdr forms))))
    (unless (and subtag (<= 0 subtag 255)
                 (= (logand subtag 7) wasm32::fulltag-nodeheader))
      (refuse :bootstrap-gvector-subtag))
    (bootstrap-operands
     (cdr forms)
     (lambda (values)
       (b-wat "(i32.add ~a (i32.const 6))"
              (b-heap-block (* 8 (ceiling (1+ n) 2))
                            (lambda (base)
                              (with-output-to-string (s)
                                (format s "(i32.store ~a (i32.const ~d))" base (+ subtag (* 256 n)))
                                (loop for value in values for i from 1 do
                                  (format s "(i32.store offset=~d ~a ~a)" (* 4 i) base value))
                                (when (evenp n)
                                  (format s "(i32.store offset=~d ~a (i32.const 0))" (* 4 (1+ n)) base))))))))))

(defun bootstrap-fixnum-operator (op forms &optional condition)
  (bootstrap-operands
   forms
   (lambda (values)
     (let ((a (first values)) (b (second values)))
       (with-output-to-string (s)
         (dolist (x values)
           (write-string (b-condition (b-wat "(i32.and ~a (i32.const 3))" x) 5) s))
         (write-string
          (case op
            (ccl::%i<>
             (bootstrap-boolean
              (b-wat "(i32.~a ~a ~a)"
                     (ecase condition (:eq "eq") (:ne "ne") (:lt "lt_s")
                            (:le "le_s") (:gt "gt_s") (:ge "ge_s")) a b)))
            ((ccl::%i+ ccl::fixnum-add-no-overflow)
             (b-wat "(i32.add ~a ~a)" a b))
            ((ccl::%i- ccl::fixnum-sub-no-overflow)
             (b-wat "(i32.sub ~a ~a)" a b))
            (ccl::%ilogand2 (b-wat "(i32.and ~a ~a)" a b))
            (ccl::%ilogior2 (b-wat "(i32.or ~a ~a)" a b))
            (ccl::%ilogxor2 (b-wat "(i32.xor ~a ~a)" a b))
            (ccl::%ilognot (b-wat "(i32.xor ~a (i32.const -4))" a))
            (t (refuse op)))
          s))))))



(defun bootstrap-emitted-operators ()
  (let ((counts nil))
    (maphash (lambda (ir emitted)
               (declare (ignore emitted))
               (let* ((name (ccl::acode-operator-name (ccl::acode-operator ir)))
                      (entry (assoc name counts)))
                 (if entry (incf (cdr entry)) (push (cons name 1) counts))))
             *bootstrap-emitted*)
    (sort counts #'string< :key (lambda (entry) (symbol-name (car entry))))))

(setf (aref (ccl::backend-p2-dispatch *backend*) (logand ccl::operator-id-mask (ccl::%nx1-operator ccl::%ilognot))) 'bootstrap-operator)

(in-package :wasm32-compiler)

;;; The existing condition constructor owns the class layout and the existing
;;; dispatcher owns handler masking and transfers. Keep the new arguments in
;;; the caller's roots until the constructor has finished allocating.
(defun bootstrap-condition (mask values)
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (b-wat "(block (result i32) ~a)"
    (b-frame (max 2 (length values))
      (lambda (root)
        (let ((object (temporary)))
          (with-output-to-string (s)
            ;; NIL means an omitted initarg here. Leave its native default
            ;; in the instance; every supplied value is rooted before growth.
            (loop for value in values for offset from 8 by 4
                  when value do
              (format s "(i32.store offset=~d ~a ~a)" offset root value))
            (format s "(local.set ~a ~a)" object
                    (if *b-allocation-retry*
                      (b-wat "(call $condition_new (i32.const ~d) (i32.add ~a (i32.const 8)))"
                             mask root)
                      (b-wat "(call $condition_new (i32.const ~d) (i32.load offset=8 ~a) (i32.load offset=12 ~a))"
                             mask root root)))
            (loop for value in values for offset from 8 by 4
                  when value do
              (format s "(i32.store offset=~d (call $condition_slots (local.get ~a)) (i32.load offset=~d ~a))"
                      offset object offset root))
            (format s "(local.get ~a)" object)))))))

(defun bootstrap-immediate (form)
  (when (and (ccl::acode-p form)
             (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::immediate))
    (values (first (ccl::acode-operands form)) t)))

(defun bootstrap-signal (forms fatal &optional construct-only)
  (unless forms (refuse :bootstrap-signal-arity))
  (multiple-value-bind (designator constant) (bootstrap-immediate (car forms))
    (let* ((class (and constant (symbolp designator) designator))
           (schema (assoc class '((simple-condition 36 :format-control :format-arguments)
                                  (simple-error 124 :format-control :format-arguments)
                                  (ccl::simple-program-error 2108 :format-control :format-arguments)
                                  (type-error 156 :datum :expected-type)
                                  (ccl::no-applicable-method-exists 32796 :gf :args) (program-error 2076)
                                  (arithmetic-error 65564 :operation :operands)
                                  (division-by-zero 196636 :operation :operands)
                                  (stream-error 4194332 :stream)
                                  (end-of-file 12582940 :stream)
                                  (file-error 16777244 :pathname :error-type)
                                  (package-error 33554460 :package)
                                  (ccl::simple-package-error 100663356 :format-control :format-arguments :package)
                                  (ccl::stream-is-closed-error 138412060 :stream)
                                  (ccl::bad-slot-type 268435612 :datum :expected-type :format-control :slot-definition :instance)
                                  (ccl::inactive-restart 536871196 :restart-name)
                                  (ccl::restart-failure 1073742108 :restart))))
           (*b-tail-position* nil) (*b-producer-target* nil))
      (when (and class (not schema)) (refuse :bootstrap-condition-class))
      (when class
        (unless (evenp (length (cdr forms))) (refuse :bootstrap-condition-initargs))
        (loop for tail on (cdr forms) by #'cddr for key = (car tail) do
          (unless (member (bootstrap-immediate key) (cddr schema))
            (refuse :bootstrap-condition-initarg))))
      (b-frame (length forms)
        (lambda (root)
          (let ((values (loop for i below (length forms)
                             collect (b-wat "(i32.load offset=~d ~a)" (+ 8 (* i 4)) root))))
            (with-output-to-string (s)
              (loop for form in forms for i from 0 do
                (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* i 4)) root (b-scalar form)))
              (let* ((arguments
                       (if class
                         (loop for key in (cddr schema) collect
                           (or (loop for (k v) on (cdr forms) by #'cddr
                                     for i from 2 by 2
                                     when (eq (bootstrap-immediate k) key) return (nth i values))
                               (if (> (second schema) 2162716) nil
                                 (if (member key '(:format-control :datum :expected-type))
                                 "(i32.const 83)" "(i32.const 77825)"))))
                         (list (car values)
                               (reduce (lambda (value tail)
                                         (b-cons (make-b-raw-code :text value)
                                                 (make-b-raw-code :text tail)))
                                       (cdr values) :from-end t :initial-value "(i32.const 77825)"))))
                     (condition
                       (if class
                         (bootstrap-condition (second schema) arguments)
                         (b-wat "(if (result i32) (i32.eq ~a (i32.const 764))
                                  (then ~a) (else ~a ~a))"
                                (bootstrap-typecode (car values))
                                (bootstrap-condition (if fatal 124 36) arguments)
                                (if (cdr forms) (b-condition "(i32.const 1)" 4) "")
                                (car values)))))
                (write-string (if construct-only
                                  (b-multiple (make-b-raw-code :text condition))
                                  (b-signal (make-b-raw-code :text condition) fatal)) s)))))))))

(defun bootstrap-condition-reader (name forms)
  (unless (= (length forms) 1) (refuse :bootstrap-condition-reader-arity))
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (let* ((simple (member name '(simple-condition-format-control simple-condition-format-arguments)))
         (class (case name
                  (stream-error-stream 'stream-error)
                  (file-error-pathname 'file-error)
                  (package-error-package 'package-error)
                  (t (if simple 'simple-condition 'type-error))))
         (offset (if (member name '(simple-condition-format-arguments type-error-expected-type)) 12 8)))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((value (temporary)) (condition (car values)))
             (b-wat "(local.set ~a (call $condition_field ~a (i32.const ~d) ~a (local.get $top))) ~a (local.get ~a)"
                    value condition (b-condition-mask class)
                    (if (eq name 'package-error-package)
                      (b-wat "(if (result i32) (i32.and (call $condition_mask ~a) (i32.const ~d)) (then (i32.const 16)) (else (i32.const 8)))"
                             condition (b-condition-mask 'ccl::simple-package-error))
                      (b-wat "(i32.const ~d)" offset))
                    (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const 83))" value) 4)
                    value))))))))

(defun bootstrap-character (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((x (car values)))
        (case op
          ((ccl::char-code ccl::%char-code)
           (b-wat "~a (i32.shl (i32.shr_u ~a (i32.const 8)) (i32.const 2))"
                  (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" x) 5) x))
          (t
           (b-wat "~a (if (result i32) (i32.and (i32.lt_u ~a (i32.const 4456448))
                      (i32.or (i32.lt_u ~a (i32.const 221184)) (i32.ge_u ~a (i32.const 229376))))
                    (then (i32.or (i32.shl ~a (i32.const 6)) (i32.const 75))) (else (i32.const 77825)))"
                  (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 4456448)))" x x) 5) x x x x)))))))

(defun bootstrap-string-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (object index &optional value) values
        (let* ((base (temporary)) (header (temporary))
               (address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" base index)))
          (with-output-to-string (s)
            (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
            (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
            (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 191))" header) 4) s)
            (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
            (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shl (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 2))))" base header)
            (if value
              (progn
                (write-string
                 (b-condition
                  (if (eq op 'ccl::%set-scharcode)
                    (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 4456448)))" value value)
                    (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" value)) 5) s)
                (format s "(i32.store ~a (i32.shr_u ~a (i32.const ~d))) ~a"
                        address value (if (eq op 'ccl::%set-scharcode) 2 8) value))
              (format s "(i32.or (i32.shl (i32.load ~a) (i32.const ~d)) (i32.const ~d))"
                      address (if (eq op 'ccl::%scharcode) 2 8)
                      (if (eq op 'ccl::%scharcode) 0 75)))))))))


(defun bootstrap-symbol-pointer (form)
  (bootstrap-operands (list form)
    (lambda (values)
      (let ((x (car values)))
        (b-wat "(if (result i32) (i32.eq ~a (i32.const 77825))
                 (then (i32.const ~d))
                 (else ~a (drop (call $object_base ~a (i32.const 32) (i32.const 1850))) ~a))"
               x (+ wasm32::canonical-nil-value wasm32::nilsym-offset)
               (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" x) 5) x x)))))

(defun bootstrap-symbol-operator (op args)
  (case op
    (ccl::%unbound-marker "(i32.const 51)")
    (ccl::%symbol->symptr (bootstrap-symbol-pointer (car args)))
    ((ccl::%symptr->symvector ccl::%symvector->symptr) (b-scalar (car args)))))


;;; Operands are rooted before a later operand can allocate. Accessors below
;;; perform their checks before storing, and contain no intervening safepoint.
(defun bootstrap-shift (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (count value) values
        (b-wat "~a ~a ~a"
               (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 5)
               (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
               (if (eq op 'ccl::%ilsl)
                 (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 120)) (then (i32.const 0)) (else (i32.shl ~a (i32.shr_u ~a (i32.const 2)))))" count value count)
                 (b-wat "(i32.and (if (result i32) (i32.ge_u ~a (i32.const 128)) (then ~a) (else (i32.~a ~a (i32.shr_u ~a (i32.const 2))))) (i32.const -4))"
                        count (if (eq op 'ccl::%iasr) (b-wat "(i32.shr_s ~a (i32.const 31))" value) "(i32.const 0)")
                        (if (eq op 'ccl::%iasr) "shr_s" "shr_u") value count)))))))

(defun bootstrap-uvector-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let* ((object (first values)) (value (third values))
             (tag (temporary))
             (raw (mapcar (lambda (x) (make-b-raw-code :text x)) values)))
        (flet ((typed (kind)
                 (bootstrap-typed-access
                   (if value 'ccl::%typed-uvset 'ccl::%typed-uvref)
                   (cons (bootstrap-constant kind) raw))))
          (b-wat "(local.set ~a ~a)
                   (if (result i32) (i32.eq (local.get ~a) (i32.const 764))
                     (then ~a)
                     (else (if (result i32) (i32.eq (local.get ~a) (i32.const 796))
                       (then ~a)
                       (else (if (result i32) (i32.eq (local.get ~a) (i32.const 28))
                         (then ~a) (else ~a))))))"
                 tag (bootstrap-typecode object) tag
                 (bootstrap-string-access (if value 'ccl::%set-sbchar 'ccl::%sbchar) raw)
                 tag (typed :unsigned-8-bit-vector)
                 tag (typed :bignum)
                 (bootstrap-node-access
                   (if (eq op 'ccl::uvset) 'ccl::%svset 'ccl::%svref) raw)))))))

(defun bootstrap-heap-block (bytes emit)
  (let ((size (temporary)) (base (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a) ~a
             (local.set ~a ~a) ~a ~a ~a ~a ~a (local.get ~a))"
           size bytes
           (if *b-allocation-retry*
             (b-wat "(if (i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u (local.get ~a))) (i64.extend_i32_u ~a)) (then (call $heap_ensure (local.get ~a))))"
                    (b-load wasm32::tcr.alloc_pointer) size (b-load wasm32::tcr.alloc_limit) size) "")
           base (b-load wasm32::tcr.alloc_pointer)
           (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) ~a) (i32.and (local.get ~a) (i32.const 7)))" base (b-load wasm32::tcr.alloc_base) base) 6)
           (b-condition (b-wat "(i64.gt_u (i64.extend_i32_u ~a) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" (b-load wasm32::tcr.alloc_limit)) 6)
           (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.extend_i32_u (local.get ~a))) (i64.extend_i32_u ~a))" base size (b-load wasm32::tcr.alloc_limit)) 6)
           (funcall emit (b-local base) (b-local size))
           (b-store wasm32::tcr.alloc_pointer (b-wat "(i32.add (local.get ~a) (local.get ~a))" base size)) base)))

(defun bootstrap-allocate-float (forms)
  (let* ((count (ccl::acode-fixnum-form-p (first forms)))
         (subtag (ccl::acode-fixnum-form-p (second forms)))
         (bytes (cond ((and (eql count 1)
                           (eql subtag wasm32::subtag-single-float)) 8)
                      ((and (eql count 3)
                           (eql subtag wasm32::subtag-double-float)) 16))))
    (when (and bytes (= (length forms) 2))
      (b-wat "(i32.add ~a (i32.const 6))"
             (b-heap-block bytes
               (lambda (base)
                 (b-wat "(memory.fill ~a (i32.const 0) (i32.const ~d))
                          (i32.store ~a (i32.const ~d))"
                        base bytes base (+ (ash count 8) subtag))))))))

;;; Funcallable instances retain the ordinary callable prefix. Their final
;;; word points to the seven Lisp immediates described by LISPEQU.
;;; Ordinary functions keep keyword names in their accepted arity metadata.
(defun bootstrap-metadata-keyvect (forms)
  (unless (= (length forms) 1) (refuse :function-keyvect-arity))
  (bootstrap-operands forms
    (lambda (values)
      (let ((function (temporary)) (pool (temporary)) (arity (temporary))
            (keys (temporary)) (header (temporary)))
        (with-output-to-string (s)
          (format s "(local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))"
                  function (first values))
          ;; A funcallable's class wrapper must never become a key vector.
          (write-string (b-condition (b-wat "(i32.ne (i32.load (local.get ~a)) (i32.const 1578))" function) 4) s)
          (format s "(local.set ~a (i32.load offset=24 (local.get ~a)))" pool function)
          (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" pool) 4) s)
          (format s "(local.set ~a (i32.sub (local.get ~a) (i32.const 6)))
                     (call $span (local.get ~a) (i32.const 12))
                     (local.set ~a (i32.load (local.get ~a)))" pool pool pool header pool)
          (write-string (b-condition (b-wat "(i32.or (i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 250)) (i32.lt_u (local.get ~a) (i32.const 762)))" header header) 4) s)
          (write-string (b-condition (b-wat "(i32.ne (i32.load offset=16 (local.get ~a)) (i32.load offset=4 (local.get ~a)))" function pool) 4) s)
          (format s "(local.set ~a (call $object_base (i32.load offset=16 (local.get ~a)) (i32.const 32) (i32.const 2042)))" arity function)
          (write-string (b-condition (b-wat "(i32.ne (i32.load offset=4 (local.get ~a)) (i32.const 4))" arity) 4) s)
          (dolist (offset '(8 12))
            (write-string (b-condition (b-wat "(i32.or (i32.and (i32.load offset=~d (local.get ~a)) (i32.const 3)) (i32.lt_s (i32.load offset=~d (local.get ~a)) (i32.const 0)))" offset arity offset arity) 4) s))
          (dolist (offset '(16 20 24))
            (write-string (b-condition (b-wat "(i32.and (i32.ne (i32.load offset=~d (local.get ~a)) (i32.const 77825)) (i32.ne (i32.load offset=~d (local.get ~a)) (i32.const 77838)))" offset arity offset arity) 4) s))
          (format s "(local.set ~a (i32.load offset=28 (local.get ~a)))" keys arity)
          (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" keys) 4) s)
          (format s "(call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4))
                     (local.set ~a (i32.load (i32.sub (local.get ~a) (i32.const 6))))" keys header keys)
          (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 250))" header) 4) s)
          (format s "(call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.add (i32.const 4) (i32.shl (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 2))))" keys header)
          (write-string (b-condition (b-wat "(i32.and (i32.eq (i32.load offset=20 (local.get ~a)) (i32.const 77825)) (i32.ne (local.get ~a) (i32.const 250)))" arity header) 4) s)
          (format s "(if (result i32) (i32.eq (i32.load offset=20 (local.get ~a)) (i32.const 77825)) (then (i32.const 77825)) (else (local.get ~a)))" arity keys))))))

(defun bootstrap-function-immediate (forms storep)
  (unless (= (length forms) (if storep 3 2))
    (refuse :funcallable-immediate-arity))
  (bootstrap-operands forms
    (lambda (values)
      (let* ((function (first values)) (index (second values))
             (value (third values)) (vector (temporary)))
        (b-wat "(block (result i32)
                 (local.set ~a (call $object_base
                   (i32.load offset=28 (call $object_base ~a (i32.const 32) (i32.const 1834)))
                   (i32.const 32) (i32.const 2042)))
                 ~a ~a)"
          vector function
          (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 28)))" index index) 4)
          (let ((address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" vector index)))
            (if storep (b-wat "(i32.store ~a ~a) ~a" address value value)
                (b-wat "(i32.load ~a)" address))))))))

(defun bootstrap-make-funcallable (forms)
  (unless (= (length forms) 2) (refuse :funcallable-constructor-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (function immediates) values
        (b-wat "(block (result i32)
          (drop (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (drop (call $object_base ~a (i32.const 32) (i32.const 2042)))
          (i32.add ~a (i32.const 38)))"
          function immediates
          (b-heap-block 64
            (lambda (base)
              ;; Assurance precedes these loads. Both operands are rooted,
              ;; and every field is initialized before publication.
              (b-wat "(memory.copy ~a (i32.sub ~a (i32.const 6)) (i32.const 32))
                      (memory.copy (i32.add ~a (i32.const 32)) (i32.sub ~a (i32.const 6)) (i32.const 32))
                      (i32.store (i32.add ~a (i32.const 32)) (i32.const 1834))
                      (i32.store (i32.add ~a (i32.const 60)) (i32.add ~a (i32.const 6)))"
                     base immediates base function base base base))))))))

(defun bootstrap-make-vector (forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (count tag &optional initial) values
        (let ((i (temporary)) (n (temporary)) (kind (temporary)))
          (with-output-to-string (s)
            (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.gt_u ~a (i32.const 67108860)))" count count) 6) s)
            (format s "(local.set ~a (i32.shr_u ~a (i32.const 2))) (local.set ~a ~a)" n count kind tag)
            (write-string (b-condition (b-wat "(i32.and (i32.ne ~a (i32.const 424)) (i32.and (i32.ne ~a (i32.const 1000)) (i32.and (i32.ne ~a (i32.const 764)) (i32.ne ~a (i32.const 796)))))" tag tag tag tag) 4) s)
            (when initial
              (format s "(if (i32.eq (local.get ~a) (i32.const 764)) (then ~a)) (if (i32.eq (local.get ~a) (i32.const 796)) (then ~a))"
                      kind (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" initial) 5)
                      kind (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 1024)))" initial initial) 5)))
            (write-string
             (b-wat "(i32.add ~a (i32.const 6))"
               (bootstrap-heap-block
                (b-wat "(i32.and (i32.add (if (result i32) (i32.eq (local.get ~a) (i32.const 796)) (then (local.get ~a)) (else (i32.shl (local.get ~a) (i32.const 2)))) (i32.const 11)) (i32.const -8))" kind n n)
                (lambda (base bytes)
                  (b-wat "(memory.fill ~a (i32.const 0) ~a)
                           (i32.store ~a (i32.or (i32.shl (local.get ~a) (i32.const 8)) (i32.shr_u (local.get ~a) (i32.const 2))))
                           (local.set ~a (i32.const 0))
                           (block $vector_done (loop $vector_fill
                             (br_if $vector_done (i32.ge_u (local.get ~a) (local.get ~a)))
                             (if (i32.eq (local.get ~a) (i32.const 796))
                               (then (i32.store8 (i32.add ~a (i32.add (i32.const 4) (local.get ~a))) ~a))
                               (else (i32.store (i32.add ~a (i32.add (i32.const 4) (i32.shl (local.get ~a) (i32.const 2)))) ~a)))
                             (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $vector_fill)))"
                         base bytes base n kind i i n kind base i
                         (if initial (b-wat "(i32.shr_u ~a (i32.const 2))" initial) "(i32.const 0)")
                         base i
                         (b-wat "(if (result i32) (i32.or (i32.eq (local.get ~a) (i32.const 1000)) (i32.eq (local.get ~a) (i32.const 424))) (then ~a) (else ~a))"
                                kind kind (or initial "(i32.const 77825)")
                                (if initial (b-wat "(i32.shr_u ~a (i32.const 8))" initial) "(i32.const 0)")) i i)))) s)))))))

(defun bootstrap-make-list (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((count (first values)) (value (second values))
            (i (temporary)) (head (temporary)))
        (b-wat "~a (local.set ~a (i32.const 77825)) (drop ~a) (local.get ~a)"
               (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 6)
               head
               (bootstrap-heap-block (b-wat "(i32.shl ~a (i32.const 1))" count)
                 (lambda (base bytes)
                   (b-wat "(local.set ~a (i32.const 0))
                            (block $list_done (loop $list_fill
                              (br_if $list_done (i32.ge_u (local.get ~a) ~a))
                              (i32.store (i32.add ~a (local.get ~a)) (local.get ~a))
                              (i32.store offset=4 (i32.add ~a (local.get ~a)) ~a)
                              (local.set ~a (i32.add (i32.add ~a (local.get ~a)) (i32.const 1)))
                              (local.set ~a (i32.add (local.get ~a) (i32.const 8))) (br $list_fill)))"
                          i i bytes base i head base i value head base i i i))) head)))))

(defun bootstrap-lexpr (var start body)
  (when (b-captured-p var) (refuse :escaping-lexpr))
  (let ((count (temporary)) (i (temporary)))
    (b-wat "(local.set ~a (if (result i32) (i32.gt_u (local.get $nargs) (i32.const ~d)) (then (i32.sub (local.get $nargs) (i32.const ~d))) (else (i32.const 0)))) ~a"
           count start start
           (b-retained-frame (b-wat "(i32.add (local.get ~a) (i32.const 1))" count)
             (lambda (root)
               (concatenate 'string
                 (b-wat "(i32.store offset=8 ~a (i32.shl (local.get ~a) (i32.const 2)))
                          (local.set ~a (i32.const 0))
                          (block $lexpr_done (loop $lexpr_copy
                            (br_if $lexpr_done (i32.ge_u (local.get ~a) (local.get ~a)))
                            (i32.store (i32.add ~a (i32.add (i32.const 8) (i32.shl (i32.sub (local.get ~a) (local.get ~a)) (i32.const 2))))
                              (i32.load (i32.add (local.get $incoming) (i32.shl (i32.add (local.get ~a) (i32.const ~d)) (i32.const 2)))))
                            (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $lexpr_copy)))"
                        root count i i count root count i i start i i)
                 (b-bind-value var (b-at root 8))
                 (funcall body)))))))

(defun bootstrap-box-word (word signed)
  (let ((n (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a)
             (if (result i32) ~a
               (then (i32.shl (local.get ~a) (i32.const 2)))
               (else ~a)))"
           n word
           (if signed
             (b-wat "(i32.and (i32.ge_s (local.get ~a) (i32.const -536870912)) (i32.le_s (local.get ~a) (i32.const 536870911)))" n n)
             (b-wat "(i32.le_u (local.get ~a) (i32.const 536870911))" n)) n
           (let ((one (b-wat "(i32.add ~a (i32.const 6))"
                        (b-heap-block 8 (lambda (base)
                          (b-wat "(i32.store ~a (i32.const 263)) (i32.store offset=4 ~a (local.get ~a))" base base n))))))
             (if signed one
               (b-wat "(if (result i32) (i32.lt_u (local.get ~a) (i32.const 2147483648)) (then ~a) (else (i32.add ~a (i32.const 6))))"
                      n one (b-heap-block 16 (lambda (base)
                              (b-wat "(i32.store ~a (i32.const 519)) (i32.store offset=4 ~a (local.get ~a)) (i32.store offset=8 ~a (i32.const 0)) (i32.store offset=12 ~a (i32.const 0))" base base n base base)))))))))

(defun bootstrap-typed-access (op args)
  (let* ((kind (ccl::acode-immediate-operand (car args)))
         (layout (assoc kind '((:unsigned-8-bit-vector 1 nil 199 0 255)
                              (:signed-8-bit-vector 1 t 207 -128 127)
                              (:unsigned-16-bit-vector 2 nil 215 0 65535)
                              (:signed-16-bit-vector 2 t 223 -32768 32767)
                              (:unsigned-32-bit-vector 4 nil 167 0 536870911)
                              (:bignum 4 nil 7 0 536870911)
                              (:signed-32-bit-vector 4 t 175 -536870912 536870911)
                              (:fixnum-vector 4 t 183 -536870912 536870911)))))
    (case kind
      (:simple-vector
       (return-from bootstrap-typed-access
         (bootstrap-node-access (if (eq op 'ccl::%typed-uvset) 'ccl::svset 'ccl::svref) (cdr args))))
      (:simple-string
       (return-from bootstrap-typed-access
         (bootstrap-string-access (if (eq op 'ccl::%typed-uvset) 'ccl::%set-sbchar 'ccl::%sbchar) (cdr args)))))
    (unless layout (refuse :bootstrap-array-kind))
    (destructuring-bind (kind width signed subtag low high) layout
      (bootstrap-operands (cdr args)
        (lambda (values)
          (destructuring-bind (object index &optional value) values
            (let ((base (temporary)) (header (temporary)))
              (with-output-to-string (s)
                (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
                (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
                ;; %SCHARCODE deliberately uses CCL's unsigned-word view of a
                ;; string. Both representations have exactly four bytes per cell.
                (write-string (b-condition
                  (if (eq kind :unsigned-32-bit-vector)
                    (b-wat "(i32.and (i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d)) (i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 191)))" header subtag header)
                    (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d))" header subtag)) 4) s)
                (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
                (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.mul (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const ~d))))" base header width)
                (let ((address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) (i32.mul (i32.shr_u ~a (i32.const 2)) (i32.const ~d))))" base index width)))
                  (if value
                    (progn
                      (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.lt_s ~a (i32.const ~d)) (i32.gt_s ~a (i32.const ~d))))" value value (* 4 low) value (* 4 high)) 5) s)
                      (format s "(i32.store~a ~a ~a) ~a" (case width (1 "8") (2 "16") (t "")) address
                              (if (eq kind :fixnum-vector) value (b-wat "(i32.shr_s ~a (i32.const 2))" value)) value))
                    (let ((read (b-wat "(i32.load~a ~a)" (case width (1 (if signed "8_s" "8_u")) (2 (if signed "16_s" "16_u")) (t "")) address)))
                      (write-string (cond ((eq kind :fixnum-vector) read)
                                          ((= width 4) (bootstrap-box-word read signed))
                                          (t (b-wat "(i32.shl ~a (i32.const 2))" read))) s))))))))))))

;;; Natural shifts operate on one unsigned target word, not a tagged fixnum.
(defun bootstrap-unbox-word (value)
  (let ((p (temporary)) (h (temporary)) (w (temporary)))
    (b-wat "(block (result i32)
      (if (result i32) (i32.eqz (i32.and ~a (i32.const 3)))
        (then ~a (i32.shr_u ~a (i32.const 2)))
        (else ~a (local.set ~a (i32.sub ~a (i32.const 6)))
          (call $span (local.get ~a) (i32.const 8))
          (local.set ~a (i32.load (local.get ~a)))
          (local.set ~a (i32.load offset=4 (local.get ~a)))
          (if (i32.eq (local.get ~a) (i32.const 263))
            (then ~a)
            (else ~a (call $span (local.get ~a) (i32.const 16)) ~a))
          (local.get ~a))))"
      value (b-condition (b-wat "(i32.lt_s ~a (i32.const 0))" value) 32) value
      (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" value) 32)
      p value p h p w p h
      (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) (i32.const 536870912)) (i32.gt_u (local.get ~a) (i32.const 2147483647)))" w w) 32)
      (b-condition (b-wat "(i32.ne (local.get ~a) (i32.const 519))" h) 32) p
      (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) (i32.const 2147483648)) (i32.load offset=8 (local.get ~a)))" w p) 32) w)))

(defun bootstrap-natural-shift (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (value count) values
        (let ((word (temporary)))
          (b-wat "~a (local.set ~a ~a) ~a"
                 (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 5)
                 word (bootstrap-unbox-word value)
                 (bootstrap-box-word
                  (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 128)) (then (i32.const 0)) (else (i32.~a (local.get ~a) (i32.shr_u ~a (i32.const 2)))))"
                         count (if (eq op 'ccl::natural-shift-left) "shl" "shr_u") word count) nil)))))))

(defun bootstrap-word-logical (name forms)
  (when (and (= (length forms) 2)
             (every (lambda (form)
                      (or (ccl::acode-form-typep form '(unsigned-byte 32) t)
                          (and (ccl::acode-p form)
                               (member (ccl::acode-operator-name (ccl::acode-operator form))
                                       '(ccl::fixnum ccl::immediate))
                               (typep (car (ccl::acode-operands form)) '(unsigned-byte 32)))))
                    forms))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (bootstrap-box-word
            (b-wat "(i32.~a ~a ~a)" (ecase name (logand "and") (logior "or") (logxor "xor"))
                   (bootstrap-unbox-word (first values)) (bootstrap-unbox-word (second values))) nil)))))))

;;; The result argument of the native destructive float primitives is rooted
;;; across calculation. Copy only after both operands have been evaluated.
;;; Raw words of a float object.  Word 0 of a single float is its value;
;;; a double float has its low word at 0 and its high word at 1.  Reads box
;;; the word as an (UNSIGNED-BYTE 32); stores unbox one.  The object and
;;; the index are checked before any access, and nothing allocates between
;;; the check and the access.
(defun bootstrap-float-word (name forms)
  (let ((storep (eq name 'ccl::%wasm-set-float-word)))
    (unless (= (length forms) (if storep 3 2)) (refuse :bootstrap-float-word-arity))
    (bootstrap-operands forms
      (lambda (values)
        (destructuring-bind (object index &optional word) values
          (let ((kind (temporary)) (address (temporary)))
            (b-wat "(block (result i32)
                     (local.set ~a (call $real_operand ~a)) ~a ~a
                     (local.set ~a (i32.add (i32.sub ~a (i32.const 6))
                                    (i32.add (if (result i32) (i32.eq (local.get ~a) (i32.const 32))
                                               (then (i32.const 4)) (else (i32.const 8)))
                                             ~a)))
                     ~a)"
                   kind object
                   (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 32)) (i32.ne (local.get ~a) (i32.const 64)))" kind kind) 4)
                   (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (if (result i32) (i32.eq (local.get ~a) (i32.const 32)) (then (i32.const 4)) (else (i32.const 8)))))" index index kind) 4)
                   address object kind index
                   (if storep
                     (let ((value (temporary)))
                       (b-wat "(local.set ~a ~a) (i32.store (local.get ~a) (local.get ~a)) ~a"
                              value (bootstrap-unbox-word word) address value word))
                     (bootstrap-box-word (b-wat "(i32.load (local.get ~a))" address) nil)))))))))

;;; Signed fixnum division.  The divisor has been checked against zero and
;;; -1 by the Lisp caller; the quotient of two 30-bit values always fits.
(defun bootstrap-fixnum-division (name forms)
  (unless (= (length forms) 2) (refuse :bootstrap-fixnum-division-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (dividend divisor) values
        (let ((a (temporary)) (b (temporary)))
          (b-wat "(block (result i32) ~a ~a
                   (local.set ~a (i32.shr_s ~a (i32.const 2)))
                   (local.set ~a (i32.shr_s ~a (i32.const 2))) ~a ~a
                   (i32.shl (~a (local.get ~a) (local.get ~a)) (i32.const 2)))"
                 (b-condition (b-wat "(i32.and ~a (i32.const 3))" dividend) 5)
                 (b-condition (b-wat "(i32.and ~a (i32.const 3))" divisor) 5)
                 a dividend b divisor
                 (b-condition (b-wat "(i32.eqz (local.get ~a))" b) 5)
                 (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const -1))" b) 5)
                 (if (eq name 'ccl::%wasm-fixnum-quotient) "i32.div_s" "i32.rem_s")
                 a b))))))

;;; A float converted to a fixnum: MODE 0 truncates, MODE 1 rounds to
;;; nearest even.  The exponent is checked before the conversion so that no
;;; Wasm trap is reachable: a magnitude below 2^30 rounds to at most 2^30,
;;; inside the conversion's range, while NaN and infinity fail the check.
;;; The converted value is then checked against the fixnum range.
(defun bootstrap-float-to-fixnum (forms)
  (let ((mode (ccl::acode-fixnum-form-p (second forms))))
    (unless (and (= (length forms) 2) (member mode '(0 1))) (refuse :bootstrap-float-to-fixnum-mode))
    (bootstrap-operands (list (first forms))
      (lambda (values)
        (let ((object (first values)) (kind (temporary)) (base (temporary)) (result (temporary)))
          (b-wat "(block (result i32)
                   (local.set ~a (call $real_operand ~a)) ~a
                   (local.set ~a (i32.sub ~a (i32.const 6)))
                   ~a
                   (local.set ~a (if (result i32) (i32.eq (local.get ~a) (i32.const 32))
                     (then (i32.trunc_f32_s ~a))
                     (else (i32.trunc_f64_s ~a))))
                   ~a
                   (i32.shl (local.get ~a) (i32.const 2)))"
                 kind object
                 (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 32)) (i32.ne (local.get ~a) (i32.const 64)))" kind kind) 4)
                 base object
                 (b-condition (b-wat "(if (result i32) (i32.eq (local.get ~a) (i32.const 32))
                                        (then (i32.ge_u (i32.and (i32.load offset=4 (local.get ~a)) (i32.const 2139095040)) (i32.const ~d)))
                                        (else (i32.ge_u (i32.and (i32.load offset=12 (local.get ~a)) (i32.const 2146435072)) (i32.const ~d))))"
                                     kind base (ash (+ 127 30) 23) base (ash (+ 1023 30) 20)) 5)
                 result kind
                 (let ((single (b-wat "(f32.load offset=4 (local.get ~a))" base))
                       (double (b-wat "(f64.load offset=8 (local.get ~a))" base)))
                   (if (eql mode 1) (b-wat "(f32.nearest ~a)" single) single))
                 (let ((double (b-wat "(f64.load offset=8 (local.get ~a))" base)))
                   (if (eql mode 1) (b-wat "(f64.nearest ~a)" double) double))
                 (b-condition (b-wat "(i32.or (i32.gt_s (local.get ~a) (i32.const 536870911)) (i32.lt_s (local.get ~a) (i32.const -536870912)))" result result) 5)
                 result))))))

;;; The tag bits of a non-fixnum object, as a fixnum: what the native
;;; STRIP-TAG-TO-FIXNUM computes with AND and a shift.
(defun bootstrap-strip-tag (forms)
  (unless (= (length forms) 1) (refuse :bootstrap-strip-tag-arity))
  (bootstrap-operands forms
    (lambda (values)
      (let ((object (first values)))
        (b-wat "(if (result i32) (i32.and ~a (i32.const 3))
                  (then (i32.shr_u (i32.and ~a (i32.const -8)) (i32.const 1)))
                  (else ~a))" object object object)))))

(defun bootstrap-float-store (forms)
  (unless (= (length forms) 2) (refuse :bootstrap-float-store-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (result value) values
        (let ((kind (temporary)) (dst (temporary)) (src (temporary)))
          (b-wat "(local.set ~a (call $real_operand ~a)) ~a ~a
                   (local.set ~a (i32.sub ~a (i32.const 6)))
                   (local.set ~a (i32.sub ~a (i32.const 6)))
                   (if (i32.eq (local.get ~a) (i32.const 32))
                     (then (i32.store offset=4 (local.get ~a) (i32.load offset=4 (local.get ~a))))
                     (else (i64.store offset=8 (local.get ~a) (i64.load offset=8 (local.get ~a))))) ~a"
                 kind result
                 (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 32)) (i32.ne (local.get ~a) (i32.const 64)))" kind kind) 4)
                 (b-condition (b-wat "(i32.ne (call $real_operand ~a) (local.get ~a))" value kind) 4)
                 dst result src value kind dst src dst src result))))))

(defun bootstrap-operator (ir)
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
        (args (ccl::acode-operands ir)))
    (case op
      ((ccl::%setf-double-float ccl::%setf-short-float)
       (bootstrap-float-store args))
      ((ccl::%single-float ccl::%double-float)
       (bootstrap-primary
        (b-float-call (if (eq op 'ccl::%single-float) '%float-single '%float-double)
                      (list (car args) (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))))
      ((ccl::natural-shift-left ccl::natural-shift-right)
       (bootstrap-natural-shift op args))
      (ccl::minus1
       (bootstrap-primary (bootstrap-subtract args)))
      (ccl::global-setq
       (let ((value (temporary)) (symbol (b-special-symbol (first args))))
         (b-wat "(block (result i32) (local.set ~a ~a)
                  (drop (call $object_base ~a (i32.const 32) (i32.const 1850)))
                  (i32.store offset=2 ~a (local.get ~a)) (local.get ~a))"
                value (b-scalar (second args)) symbol symbol value value)))
      (ccl::list*
       (reduce (lambda (head tail) (b-cons head (make-b-raw-code :text tail)))
               (first (first args)) :from-end t
               :initial-value (b-scalar (car (second (first args))))))
      (ccl::vector
       (bootstrap-gvector (cons (bootstrap-constant wasm32::subtag-simple-vector) (car args))))
      (ccl::%make-uvector (or (bootstrap-allocate-bignum args) (bootstrap-allocate-float args)
                                 (bootstrap-make-vector args)))
      (ccl::make-list (bootstrap-make-list args))
      (ccl::nth-value
       (let ((*b-tail-position* nil) (*b-producer-target* nil))
         (b-wat "(block (result i32) ~a)"
           (b-frame 1 (lambda (root)
             (let ((index (b-wat "(i32.load offset=8 ~a)" root)))
               (b-wat "(i32.store offset=8 ~a ~a) ~a ~a
                        (if (result i32) (i32.lt_u (i32.shr_u ~a (i32.const 2)) (local.get $count))
                          (then (i32.load (i32.add (local.get $results) ~a))) (else (i32.const 77825)))"
                      root (b-scalar (first args))
                      (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" index index) 5)
                      (b-multiple (second args)) index index)))))))
      (ccl::logbitp
       (bootstrap-operands args
         (lambda (values)
           (destructuring-bind (index value) values
             (b-wat "~a ~a ~a"
                    (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" index index) 5)
                    (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
                    (bootstrap-boolean
                     (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 116)) (then (i32.lt_s ~a (i32.const 0))) (else (i32.and (i32.shr_s ~a (i32.add (i32.shr_u ~a (i32.const 2)) (i32.const 2))) (i32.const 1))))" index value value index)))))))
      ((ccl::%ilsl ccl::%ilsr ccl::%iasr)
       (bootstrap-shift op args))
      ((ccl::uvref ccl::uvset)
       (bootstrap-uvector-access op args))
      ((ccl::%aref1 ccl::aset1 ccl::realpart ccl::imagpart ccl::complex)
       (bootstrap-primary
        (b-call (bootstrap-constant (if (eq op 'ccl::aset1) 'ccl::%aset1 op))
                (list args nil))))
      (ccl::%slot-unbound-marker (b-wat "(i32.const ~d)" wasm32::slot-unbound-marker))
      (ccl::eq
       (let* ((left (second args)) (right (third args))
              (form (cond ((eql (ccl::acode-fixnum-form-p left) 0) right)
                          ((eql (ccl::acode-fixnum-form-p right) 0) left))))
         (when (and form (ccl::acode-form-typep form 'fixnum t))
           (b-scalar (ccl::make-acode (ccl::%nx1-operator ccl::%izerop) (first args) form)))))
      ((ccl::logand2 ccl::logior2)
       (bootstrap-primary (bootstrap-logical-call (if (eq op 'ccl::logand2) 'logand 'logior) args)))
      ((ccl::char-code ccl::%char-code ccl::code-char ccl::%code-char ccl::%valid-code-char)
       (bootstrap-character op args))
      ((ccl::%sbchar ccl::%scharcode ccl::%set-sbchar ccl::%set-scharcode)
       (bootstrap-string-access op args))
      ((ccl::%typed-uvref ccl::%typed-uvset) (bootstrap-typed-access op args))
      ((ccl::%unbound-marker ccl::%symbol->symptr ccl::%symptr->symvector ccl::%symvector->symptr)
       (bootstrap-symbol-operator op args))
      (ccl::neq
       (bootstrap-operands (cdr args)
         (lambda (values)
           (bootstrap-boolean (b-wat "(i32.eq ~a ~a)" (first values) (second values))
                              (ccl::acode-immediate-operand (car args))))))
      ((ccl::int>0-p ccl::%izerop)
       (bootstrap-operands (cdr args)
         (lambda (values)
           (b-wat "~a ~a"
                  (b-condition (b-wat "(i32.and ~a (i32.const 3))" (car values)) 5)
                  (bootstrap-boolean
                   (b-wat "(i32.~a ~a (i32.const 0))"
                          (if (eq op 'ccl::%izerop) "eq" "gt_s") (car values))
                   (if (eq op 'ccl::%izerop)
                     (ccl::acode-immediate-operand (car args)) :eq))))))
      ((ccl::add2 ccl::sub2 ccl::mul2 ccl::div2)
       (bootstrap-primary
        (bootstrap-numeric-call
         (ecase op (ccl::add2 '+) (ccl::sub2 '-) (ccl::mul2 '*) (ccl::div2 '/)) args)))
      (ccl::numcmp
       (if (every (lambda (x) (ccl::acode-form-typep x 'fixnum t)) (cdr args))
         (b-scalar (ccl::make-acode (ccl::%nx1-operator ccl::%i<>)
                                   (first args) (second args) (third args)))
         (bootstrap-primary
          (bootstrap-numeric-call
           (ecase (ccl::acode-immediate-operand (car args))
             (:lt '<) (:le '<=) (:eq '=) (:ne '/=) (:ge '>=) (:gt '>)) (cdr args)))))
      ((ccl::lisptag ccl::fulltag)
       (b-wat "(i32.shl (i32.and ~a (i32.const ~d)) (i32.const 2))"
              (b-scalar (first args)) (if (eq op 'ccl::lisptag) 3 7)))
      (ccl::typecode (bootstrap-typecode (b-scalar (first args))))
      ((ccl::%err-disp ccl::%badarg2 ccl::%debug-trap)
       ;; These entries remain calls to CCL's own error/debugger machinery.
       ;; They are dependencies, never counted as installed primitives.
       (let ((code (and (eq op 'ccl::%err-disp)
                        (bootstrap-error-call (first (first args))))))
         (when code (return-from bootstrap-operator (bootstrap-primary code))))
       (let ((name (case op (ccl::%badarg2 'ccl::%badarg)
                           (ccl::%debug-trap 'ccl::dbg) (t 'ccl::%err-disp))))
         (b-wat "(block (result i32) ~a (i32.load (local.get $results)))"
                (let ((*b-tail-position* nil))
                  (b-call (ccl::make-acode (ccl::%nx1-operator ccl::immediate) name)
                          (if (eq op 'ccl::%err-disp) (car args) (list args nil)))))))
      ((ccl::free-reference ccl::global-ref)
       (b-wat "(call $special_read_lisp ~a (local.get $top))"
              (b-special-symbol (first args))))
      (ccl::uvsize
       (let ((x (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) ~a (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4)) (i32.shl (i32.shr_u (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.const 2)))"
                x (b-scalar (car args))
                (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" x) 4) x x)))
      (ccl::%lisp-word-ref
       (bootstrap-operands
        args
        (lambda (values)
          (destructuring-bind (base offset) values
            (b-wat "~a (i32.load (i32.add ~a ~a))"
                   (b-condition
                    (b-wat "(i64.gt_u (i64.add (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u ~a)) (i64.const 4)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" base offset) 4)
                   base offset)))))
      (ccl::istruct-typep
       (bootstrap-operands
        (cdr args)
        (lambda (values)
          (let* ((object (first values)) (cell (second values))
                 (zero (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))
            (bootstrap-boolean
             (b-wat "(if (result i32) (i32.eq ~a (i32.const ~d)) (then (i32.eq ~a ~a)) (else (i32.const 0)))"
                    (bootstrap-typecode object) (* 4 wasm32::subtag-istruct)
                    (bootstrap-node-access 'ccl::%svref (list (make-b-raw-code :text object) zero)) cell)
             (ccl::acode-immediate-operand (car args)))))))
      ((ccl::consp ccl::characterp ccl::base-char-p ccl::endp)
       (let ((x (temporary)) (cc (ccl::acode-immediate-operand (first args))))
         (b-wat "(block (result i32) (local.set ~a ~a) ~a ~a)"
                x (b-scalar (second args))
                (if (eq op 'ccl::endp)
                  (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 1))" x) 5) "")
                (bootstrap-boolean
                 (case op
                   (ccl::consp (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (i32.and (local.get ~a) (i32.const 7)) (i32.const 1)))" x x))
                   (ccl::endp (b-wat "(i32.eq (local.get ~a) (i32.const 77825))" x))
                   (t (b-wat "(i32.eq (i32.and (local.get ~a) (i32.const 255)) (i32.const 75))" x))) cc))))
      ((ccl::%svref ccl::svref ccl::struct-ref ccl::%slot-ref
        ccl::%svset ccl::svset ccl::struct-set)
       (bootstrap-node-access op args))
      (ccl::%gvector
       (unless (null (second (first args))) (refuse :bootstrap-gvector-spread))
       (bootstrap-gvector (first (first args))))
      ((ccl::ivector-typecode-p ccl::gvector-typecode-p)
       (let ((x (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) (if (result i32) (i32.eq (i32.and (local.get ~a) (i32.const 31)) (i32.const ~d)) (then (local.get ~a)) (else (i32.const 0))))"
                x (b-scalar (car args)) x
                (* 4 (if (eq op 'ccl::ivector-typecode-p) 7 2)) x)))
      (ccl::%ilogbitp
       (bootstrap-operands
        (cdr args)
        (lambda (values)
          (destructuring-bind (index value) values
            (b-wat "~a ~a ~a"
                   (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 120)))" index index) 5)
                   (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
                   (bootstrap-boolean
                    (b-wat "(i32.eqz (i32.and (i32.shr_s ~a (i32.add (i32.shr_u ~a (i32.const 2)) (i32.const 2))) (i32.const 1)))" value index)
                    (ccl::acode-immediate-operand (car args))))))))
      (ccl::ash
       (b-wat "(block (result i32) ~a (i32.load (local.get $results)))"
              (b-integer-call '%integer-ash args)))
      (ccl::%i<> (bootstrap-fixnum-operator op (cdr args) (ccl::acode-immediate-operand (car args))))
      ((ccl::%i+ ccl::%i- ccl::fixnum-add-no-overflow ccl::fixnum-sub-no-overflow
        ccl::%ilogand2 ccl::%ilogior2 ccl::%ilogxor2 ccl::%ilognot)
       (bootstrap-fixnum-operator op args)))))

(defun bootstrap-numeric-call (name forms)
  (let ((entry (assoc name '((+ . %float-add) (- . %float-sub) (* . %float-mul)
                             (/ . %float-div) (< . %float-lt) (<= . %float-le)
                             (= . %float-eq) (/= . %float-ne) (>= . %float-ge)
                             (> . %float-gt)))))
    (cond ((and (eq name 'ccl::%function) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms (lambda (values)
               (b-wat "(call $function_value_lisp ~a (local.get $top))" (first values)))))))
          ((member name '(ccl::lfun-bits ccl::inner-lfun-bits ccl::lfun-bits-known-function))
           (when (member (length forms) '(1 2))
             (b-multiple (make-b-raw-code :text (if (cdr forms) (bootstrap-set-function-bits forms) (bootstrap-function-bits forms))))))
          ((and (eq name 'make-array)
                      (or (= (length forms) 1)
                          (and (= (length forms) 3)
                               (eq (bootstrap-immediate (second forms)) :initial-element))))
           (b-multiple (make-b-raw-code :text
             (bootstrap-make-vector
               (list (first forms) (bootstrap-constant wasm32::subtag-simple-vector)
                     (if (cdr forms) (third forms) (bootstrap-constant nil)))))))
          ((and (eq name 'ccl::%ilogcount) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms (lambda (values)
               (let ((value (car values)))
                 (b-wat "~a (i32.shl (i32.popcnt (i32.shr_s ~a (i32.const 2))) (i32.const 2))"
                   (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 4) value)))))))
          ((and (eq name 'assoc) (= (length forms) 2))
           (b-call (bootstrap-constant 'ccl::asseql) (list forms nil)))
          ((eq name 'ccl::signal-program-error)
           (multiple-value-bind (control constant) (bootstrap-immediate (car forms))
             (when (and constant (stringp control))
               (let ((*b-tail-position* nil) (*b-producer-target* nil))
                 (b-wat "(drop ~a)"
                   (bootstrap-operands forms
                     (lambda (values)
                       (let ((arguments
                               (reduce (lambda (value tail)
                                         (b-cons (make-b-raw-code :text value)
                                                 (make-b-raw-code :text tail)))
                                       (cdr values) :from-end t
                                       :initial-value "(i32.const 77825)")))
                         (b-signal (make-b-raw-code :text
                                     (bootstrap-condition 2108
                                       (list (car values) arguments))) t)))))))))
          ((eq name 'make-condition)
           (multiple-value-bind (class constant) (bootstrap-immediate (car forms))
             (when (and constant (symbolp class))
               (unless class (refuse :bootstrap-condition-class))
               (bootstrap-signal forms nil t))))
          ((eq name 'ccl::condition-arg)
           (when (= (length forms) 3)
             (multiple-value-bind (class constant) (bootstrap-immediate (first forms))
               (multiple-value-bind (default defaultp) (bootstrap-immediate (third forms))
                 (when (and constant (symbolp class) defaultp
                            (member default '(simple-error simple-condition simple-warning)))
                   (unless class (refuse :bootstrap-condition-class))
                   (let ((args (second forms)))
                     (when (and (ccl::acode-p args)
                                (eq (ccl::acode-operator-name (ccl::acode-operator args)) 'ccl::list))
                       (bootstrap-signal (cons (first forms) (first (ccl::acode-operands args))) nil t))))))))
          ((member name '(ccl::%double-float-sign ccl::%short-float-sign))
           (bootstrap-float-sign name forms))
          ((eq name 'ccl::%wasm-current-function)
           (unless (null forms) (refuse :current-function-arity))
           (b-multiple (make-b-raw-code :text "(i32.load offset=40 (local.get $context))")))
          ((member name '(ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set ccl::%wasm-bignum-length-set ccl::%copy-ivector-to-ivector))
           (b-multiple (make-b-raw-code :text (bootstrap-bignum-call name forms))))
          ((eq name 'ccl::%wasm-function-keyvect)
           (b-multiple (make-b-raw-code :text (bootstrap-function-keyvect forms))))
          ((eq name 'ccl::%wasm-function-immediate)
           (b-multiple (make-b-raw-code :text (bootstrap-function-immediate forms nil))))
          ((eq name 'ccl::%wasm-set-function-immediate)
           (b-multiple (make-b-raw-code :text (bootstrap-function-immediate forms t))))
          ((eq name 'ccl::%wasm-make-funcallable-instance)
           (b-multiple (make-b-raw-code :text (bootstrap-make-funcallable forms))))
          ((member name '(ccl::%wasm-float-word ccl::%wasm-set-float-word))
           (b-multiple (make-b-raw-code :text (bootstrap-float-word name forms))))
          ((member name '(ccl::%wasm-fixnum-quotient ccl::%wasm-fixnum-remainder))
           (b-multiple (make-b-raw-code :text (bootstrap-fixnum-division name forms))))
          ((eq name 'ccl::%wasm-float-to-fixnum)
           (b-multiple (make-b-raw-code :text (bootstrap-float-to-fixnum forms))))
          ((eq name 'ccl::%wasm-strip-tag)
           (b-multiple (make-b-raw-code :text (bootstrap-strip-tag forms))))
          ((member name '(ccl::%copy-double-float ccl::%copy-short-float
                          ccl::%int-to-dfloat ccl::%int-to-sfloat!))
           (unless (= (length forms) 2) (refuse :bootstrap-float-store-arity))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands forms
                (lambda (values)
                  (let* ((source (make-b-raw-code :text (first values)))
                         (destination (make-b-raw-code :text (second values)))
                         (conversion (member name '(ccl::%int-to-dfloat ccl::%int-to-sfloat!))))
                    (when conversion
                      (setq source
                            (make-b-raw-code :text
                              (b-wat "~a ~a"
                                     (b-condition (b-wat "(i32.and ~a (i32.const 3))" (first values)) 5)
                                     (bootstrap-primary
                                      (b-float-call (if (eq name 'ccl::%int-to-dfloat)
                                                     '%float-double '%float-single)
                                                    (list source (bootstrap-constant 0))))))))
                    (bootstrap-float-store (list destination source))))))))
          ((eq name 'ccl::%wasm-float-store)
           (b-multiple (make-b-raw-code :text (bootstrap-float-store forms))))
          ((eq name 'ccl::%wasm-float-transcend)
           (let ((op (ccl::acode-fixnum-form-p (car forms))))
             (unless (and op (<= 12 op 45) (= (length forms) 3))
               (refuse :bootstrap-transcend-operation))
             (b-float-call (nth (- op 12) '(%libm-expt64 %libm-expt32 %libm-sin64 %libm-sin32 %libm-cos64 %libm-cos32 %libm-acos64 %libm-acos32 %libm-asin64 %libm-asin32 %libm-cosh64 %libm-cosh32 %libm-log64 %libm-log32 %libm-tan64 %libm-tan32 %libm-atan64 %libm-atan32 %libm-atan264 %libm-atan232 %libm-exp64 %libm-exp32 %libm-sinh64 %libm-sinh32 %libm-tanh64 %libm-tanh32 %libm-asinh64 %libm-asinh32 %libm-acosh64 %libm-acosh32 %libm-atanh64 %libm-atanh32 %libm-sqrt64 %libm-sqrt32)) (cdr forms))))
          ((and (eq name 'truncate) (= (length forms) 2)
                (every (lambda (form) (ccl::acode-form-typep form 'fixnum t)) forms))
           (b-integer-call '%integer-truncate forms))
          ((eq name 'ldb) (bootstrap-ldb forms))
          ((member name '(logand logior logxor)) (or (bootstrap-word-logical name forms) (bootstrap-logical-call name forms)))
          ((eq name '-) (bootstrap-subtract forms))
          ((member name '(typep ccl::require-type)) (bootstrap-type-call name forms))
          ((eq name 'ccl::%err-disp) (bootstrap-error-call forms))
          ((member name '(ccl::%symptr-value ccl::%set-symptr-value))
           (unless (= (length forms) (if (eq name 'ccl::%symptr-value) 1 2))
             (refuse :bootstrap-symbol-arity))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands forms
                (lambda (values)
                  (let ((location (b-wat "(call $special_location ~a)" (first values))))
                    (if (eq name 'ccl::%symptr-value)
                      (b-wat "(i32.load ~a)" location)
                      (b-wat "(i32.store ~a ~a) ~a" location (second values) (second values)))))))))
          ((member name '(type-error-datum type-error-expected-type
                         simple-condition-format-control simple-condition-format-arguments
                         stream-error-stream file-error-pathname package-error-package))
           (bootstrap-condition-reader name forms))
          ((and (member name '(1+ 1-)) (= (length forms) 1))
           (bootstrap-numeric-call (if (eq name '1+) '+ '-)
             (append forms (list (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 1)))))
          ((and (member name '(zerop ccl::%short-float-zerop ccl::%double-float-zerop))
                (= (length forms) 1))
           (bootstrap-numeric-call '=
             (append forms (list (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))))

          ((and (member name '(functionp ccl::lfunp)) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-boolean
              (b-wat "(i32.eq ~a (i32.const 168))"
                     (bootstrap-typecode (b-scalar (car forms))))))))
          ((and (member name '(< <= = /= >= >)) (= (length forms) 2))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands
               forms
               (lambda (values)
                 (destructuring-bind (a b) values
                   (b-wat "(if (result i32) (i32.eqz (i32.and (i32.or ~a ~a) (i32.const 3))) (then ~a) (else (block (result i32) ~a (i32.load (local.get $results)))))"
                          a b
                          (bootstrap-boolean
                           (b-wat "(i32.~a ~a ~a)"
                                  (ecase name (< "lt_s") (<= "le_s") (= "eq")
                                         (/= "ne") (>= "ge_s") (> "gt_s")) a b))
                          (b-float-call (cdr entry)
                                        (list (make-b-raw-code :text a)
                                              (make-b-raw-code :text b))))))))))
          ((and entry (= (length forms) 2))
           (b-float-call (cdr entry) forms))
          ((and (eq name 'ash) (= (length forms) 2))
           (b-integer-call '%integer-ash forms))
          ((and (eq name 'integer-length) (= (length forms) 1))
           (b-integer-call '%integer-length forms))
          ((and (member name '(logand logior logxor)) (= (length forms) 2)
                (every (lambda (form) (ccl::acode-form-typep form 'fixnum t)) forms))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-fixnum-operator
               (ecase name (logand 'ccl::%ilogand2) (logior 'ccl::%ilogior2)
                      (logxor 'ccl::%ilogxor2)) forms)))))))

(defun bootstrap-primary (code)
  (b-wat "(block (result i32) ~a (i32.load (local.get $results)))" code))

(defun bootstrap-integer-division (root)
  ;; B-FLOAT-CALL has evaluated, rooted and checked both operands as integers.
  ;; The integer capability requires a two-slot frame at the root-chain head.
  (b-frame 2
    (lambda (operands)
      (let ((a (b-wat "(i32.load offset=8 ~a)" operands))
            (b (b-wat "(i32.load offset=12 ~a)" operands)))
        (concatenate
         'string
         (b-wat "(i32.store offset=8 ~a (i32.load offset=8 ~a))
                 (i32.store offset=12 ~a (i32.load offset=12 ~a))"
                operands root operands root)
         (b-wat "(if (i32.eqz ~a) (then ~a))" b
           (b-frame 1
             (lambda (pair)
               (b-wat "(i32.store offset=8 ~a ~a)
                       (call $implicit_error_details (i32.const 34) (local.get $top)
                             ~a (i32.load offset=8 ~a)) unreachable"
                      pair
                      (b-cons (make-b-raw-code :text a)
                              (make-b-raw-code :text
                                (b-cons (make-b-raw-code :text b)
                                        (make-b-raw-code :text "(i32.const 77825)"))))
                      (b-restart-symbol '/) pair))))
         (b-wat "(drop (call $integer (i32.const 5) ~a))" operands)
         ;; A ratio result remains outside this subset. Never return truncation.
         (b-condition (b-wat "(i32.ne ~a (i32.const 0))" b) 45)
         (b-multiple (make-b-raw-code :text a)))))))

(defun bootstrap-handler-mask (value)
  ;; Native HANDLER-BIND expansions retain their quoted class symbols.
  ;; Compare symbol identities; their addresses are not condition bitmasks.
  (let ((x (temporary)))
    (with-output-to-string (s)
      (format s "(block (result i32) (local.set ~a ~a)" x value)
      (format s "(if (i32.eqz (i32.and (local.get ~a) (i32.const 3))) (then (br 1 (i32.shr_u (local.get ~a) (i32.const 2)))))" x x)
      (dolist (name '(condition serious-condition error simple-condition simple-error
                     type-error control-error warning simple-warning program-error
                     undefined-function unbound-variable storage-condition
                     ccl::no-applicable-method-exists arithmetic-error division-by-zero
                     floating-point-invalid-operation floating-point-overflow
                     floating-point-underflow floating-point-inexact stream-error end-of-file file-error package-error ccl::simple-package-error ccl::stream-is-closed-error ccl::bad-slot-type ccl::inactive-restart ccl::restart-failure))
        (format s "(if (i32.eq (local.get ~a) ~a) (then (br 1 (i32.const ~d))))"
                x (b-restart-symbol name) (b-condition-mask name)))
      (write-string "(throw $call_error (i32.const 12)))" s))))

;;; Open-code target primitives and constant type tests. Native callers and
;;; their macro expansions remain unchanged. Dynamic type specifiers still
;;; call the full Lisp type system and remain real link dependencies.
(defparameter *bootstrap-type-predicates*
  '((null . null) (cons . consp) (list . listp) (atom . atom)
    (symbol . symbolp) (keyword . keywordp) (fixnum . ccl::fixnump)
    (bignum . ccl::bignump) (integer . integerp) (ratio . ccl::ratiop)
    (rational . rationalp) (real . realp) (number . numberp)
    (float . floatp) (short-float . ccl::short-float-p)
    (single-float . ccl::short-float-p) (double-float . ccl::double-float-p)
    (long-float . ccl::double-float-p) (complex . complexp)
    (character . characterp) (base-char . ccl::base-char-p)
    (string . stringp) (simple-string . ccl::simple-string-p)
    (simple-base-string . ccl::simple-base-string-p)
    (simple-vector . simple-vector-p) (simple-bit-vector . simple-bit-vector-p)
    (vector . vectorp) (array . arrayp) (sequence . ccl::sequencep)
    (function . functionp) (package . packagep)
    (ccl::eql-specializer . ccl::eql-specializer-p)
    (class . ccl::classp) (ccl::standard-method . ccl::standard-method-p)
    (ccl::macptr . ccl::macptrp)
    (standard-generic-function . ccl::standard-generic-function-p)
    (ccl::funcallable-standard-object . ccl::funcallable-instance-p) (restart . ccl::restartp)
    (ccl::istruct . ccl::istructp) (structure-object . ccl::structurep)))

(defun bootstrap-constant (value)
  (if (and (integerp value) (<= -536870912 value 536870911))
    (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) value)
    (ccl::make-acode (ccl::%nx1-operator ccl::immediate) value)))

(defun bootstrap-predicate-call (name forms)
  (bootstrap-primary
   (let ((*b-tail-position* nil) (*b-producer-target* nil))
     (b-call (bootstrap-constant name) (list forms nil)))))

(defun bootstrap-true-p (code)
  (b-wat "(i32.ne ~a (i32.const 77825))" code))

(defun bootstrap-small-literal-p (x)
  (or (null x) (eq x t) (and (integerp x) (<= -536870912 x 536870911))))

(defun bootstrap-type-supported-p (type)
  (cond ((symbolp type) (or (member type '(nil t bit signed-byte unsigned-byte))
                            (assoc type *bootstrap-type-predicates*)))
        ((consp type)
         (case (car type)
           ((or and) (every #'bootstrap-type-supported-p (cdr type)))
           (not (and (= (length type) 2) (bootstrap-type-supported-p (second type))))
           (eql (and (= (length type) 2) (bootstrap-small-literal-p (second type))))
           (member (every #'bootstrap-small-literal-p (cdr type)))
           (integer (and (<= (length type) 3)
                         (every (lambda (x) (or (eq x '*) (and (integerp x) (<= -536870912 x 536870911))
                                               (and (consp x) (null (cdr x)) (and (integerp (car x)) (<= -536870912 (car x) 536870911)))))
                                (cdr type))))
           ((signed-byte unsigned-byte)
            (and (= (length type) 2)
                 (or (eq (second type) '*)
                     (and (integerp (second type)) (<= 1 (second type) 28)))))
           (mod (and (= (length type) 2) (integerp (second type)) (<= 1 (second type) 536870911)))))))

(defun bootstrap-type-test (value type)
  (flet ((predicate (name)
           (bootstrap-true-p
            (bootstrap-predicate-call name (list (make-b-raw-code :text value))))))
    (cond ((null type) "(i32.const 0)")
          ((eq type t) "(i32.const 1)")
          ((eq type 'bit) (bootstrap-type-test value '(integer 0 1)))
          ((eq type 'signed-byte) (bootstrap-type-test value 'integer))
          ((eq type 'unsigned-byte) (bootstrap-type-test value '(integer 0 *)))
          ((assoc type *bootstrap-type-predicates*)
           (let ((name (cdr (assoc type *bootstrap-type-predicates*))))
             (case name
               (null (b-wat "(i32.eq ~a (i32.const 77825))" value))
               (t (predicate name)))))
          ((member (car type) '(or and))
           (reduce (lambda (part tail)
                     (if (eq (car type) 'or)
                       (b-wat "(if (result i32) ~a (then (i32.const 1)) (else ~a))"
                              (bootstrap-type-test value part) tail)
                       (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                              (bootstrap-type-test value part) tail)))
                   (cdr type) :from-end t
                   :initial-value (if (eq (car type) 'or) "(i32.const 0)" "(i32.const 1)")))
          ((eq (car type) 'not) (b-wat "(i32.eqz ~a)" (bootstrap-type-test value (second type))))
          ((member (car type) '(eql member))
           (reduce (lambda (item tail)
                     (b-wat "(if (result i32) ~a (then (i32.const 1)) (else ~a))"
                            (bootstrap-true-p
                             (bootstrap-predicate-call 'eql
                               (list (make-b-raw-code :text value) (bootstrap-constant item)))) tail))
                   (cdr type) :from-end t :initial-value "(i32.const 0)"))
          ((eq (car type) 'mod) (bootstrap-type-test value `(integer 0 (,(second type)))))
          ((member (car type) '(signed-byte unsigned-byte))
           (let ((bits (second type)))
             (bootstrap-type-test value
               (if (eq bits '*)
                 (if (eq (car type) 'signed-byte) 'integer '(integer 0 *))
                 (if (eq (car type) 'signed-byte)
                   `(integer ,(- (ash 1 (1- bits))) (,(ash 1 (1- bits))))
                   `(integer 0 (,(ash 1 bits))))))))
          ((eq (car type) 'integer)
           (let ((test "(i32.const 1)"))
             (loop for bound in (cdr type) for lower = t then nil do
               (unless (eq bound '*)
                 (let* ((exclusive (consp bound)) (n (if exclusive (car bound) bound))
                        (op (if lower (if exclusive '> '>=) (if exclusive '< '<=))))
                   (setq test
                         (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                                (bootstrap-true-p
                                 (bootstrap-primary
                                  (bootstrap-numeric-call op
                                    (list (make-b-raw-code :text value) (bootstrap-constant n))))) test)))))
             (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                    (predicate 'integerp) test))))))

(defun bootstrap-type-call (name forms)
  (when (and (member (length forms) '(2 3))
             (or (= (length forms) 2)
                 (and (eq name 'typep)
                      (multiple-value-bind (env constant) (bootstrap-immediate (third forms))
                        (and constant (null env))))))
    (multiple-value-bind (type constant) (bootstrap-immediate (second forms))
      (when (and constant (bootstrap-type-supported-p type))
        (b-multiple
         (make-b-raw-code :text
           (bootstrap-operands forms
             (lambda (values)
               (let ((object (first values)) (test (bootstrap-type-test (first values) type)))
                 (if (eq name 'typep)
                   (bootstrap-boolean test)
                   (b-wat "(if (i32.eqz ~a) (then
                             (call $implicit_error_details (i32.const 5) (local.get $top) ~a ~a) unreachable)) ~a"
                          test object (second values) object)))))))))))

;;; Fixnum operands combine in one word each.  When any operand is not a
;;; fixnum at run time, the rooted operands go two at a time to CCL's own
;;; LOGAND-2, LOGIOR-2 or LOGXOR-2, whose bignum cases are the integrated
;;; Lisp definitions.  The operands are evaluated once, into the root frame,
;;; and reloaded from it after each call.
(defun bootstrap-logical-call (name forms)
  (let ((entry (ecase name (logand 'ccl::logand-2) (logior 'ccl::logior-2) (logxor 'ccl::logxor-2)))
        (initial (if (eq name 'logand) "(i32.const -4)" "(i32.const 0)")))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((fast (reduce (lambda (a b) (b-wat "(i32.~a ~a ~a)" (ecase name (logand "and") (logior "or") (logxor "xor")) a b))
                               values :initial-value initial)))
             (if (null values)
               fast
               (let ((slow (let ((*b-tail-position* nil) (*b-producer-target* nil))
                             (reduce (lambda (a b)
                                       (bootstrap-primary
                                        (b-call (ccl::make-acode (ccl::%nx1-operator ccl::immediate) entry)
                                                (list (list (make-b-raw-code :text a) (make-b-raw-code :text b)) nil))))
                                     values))))
                 (b-wat "(if (result i32) (i32.eqz ~a) (then ~a) (else ~a ~a))"
                        (reduce (lambda (a b) (b-wat "(i32.or ~a ~a)" a b))
                                (mapcar (lambda (v) (b-wat "(i32.and ~a (i32.const 3))" v)) values))
                        fast
                        (with-output-to-string (s)
                          (dolist (value values)
                            (write-string (b-wat "(if (i32.and ~a (i32.const 3)) (then (if (i32.ne ~a (i32.const 28)) (then ~a))))"
                                                 value (bootstrap-typecode value) (b-type-failure value 'integer)) s)))
                        slow))))))))))

(defun bootstrap-subtract (forms)
  (when forms
    (b-frame (length forms)
      (lambda (root)
        (with-output-to-string (s)
          (loop for form in forms for i from 0 do
            (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar form)))
          (let ((a (make-b-raw-code :text (b-wat "(i32.load offset=8 ~a)" root))))
            (if (null (cdr forms))
              (write-string (b-float-call '%float-mul (list a (bootstrap-constant -1))) s)
              (loop for i from 1 below (length forms) do
                (write-string
                 (b-float-call '%float-sub
                   (list a (make-b-raw-code :text (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) root)))) s)
                (format s "(i32.store offset=8 ~a (i32.load (local.get $results)))" root)))))))))

(defun bootstrap-error-call (forms)
  (when (and (= (length forms) 1)
             (eql (ccl::acode-fixnum-form-p (first forms)) ccl::$xtminps))
    (return-from bootstrap-error-call
      (b-call (bootstrap-constant 'ccl::%wasm-too-many-arguments) '(nil nil))))
  ;; An improper list is outside this packet's proper-sequence domain.
  (when (and (= (length forms) 2)
             (ccl::acode-p (first forms))
             (member (ccl::acode-operator-name (ccl::acode-operator (first forms)))
                     '(ccl::fixnum ccl::immediate))
             (eql (first (ccl::acode-operands (first forms))) ccl::$ximproperlist))
    (return-from bootstrap-error-call
      (b-multiple (make-b-raw-code :text
        (bootstrap-operands (cdr forms)
          (lambda (values) (declare (ignore values))
            "(throw $call_error (i32.const 45)) unreachable"))))))
  (when (= (length forms) 3)
    (let* ((code (first forms)) (op (and (ccl::acode-p code) (ccl::acode-operator-name (ccl::acode-operator code))))
           (n (and (member op '(ccl::fixnum ccl::immediate)) (first (ccl::acode-operands code)))))
      (when (eql n ccl::$xwrongtype)
        (b-frame 2
          (lambda (root)
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)
                    (i32.store offset=12 ~a ~a)
                    (call $implicit_error_details (i32.const 5) (local.get $top)
                          (i32.load offset=8 ~a) (i32.load offset=12 ~a)) unreachable"
                   root (b-scalar (second forms)) root (b-scalar (third forms)) root
                   (bootstrap-predicate-call 'ccl::%type-error-type
                     (list (make-b-raw-code :text (b-wat "(i32.load offset=12 ~a)" root))))
                   root root)))))))

(defun bootstrap-ldb (forms)
  (when (= (length forms) 2)
    (let* ((form (first forms))
           (op (and (ccl::acode-p form) (ccl::acode-operator-name (ccl::acode-operator form))))
           (spec (and (member op '(ccl::fixnum ccl::immediate)) (first (ccl::acode-operands form)))))
      (when (and (integerp spec) (<= 0 spec))
        (let ((size (byte-size spec)) (position (byte-position spec)))
          (when (<= size 29)
            (b-multiple
             (make-b-raw-code :text
               (bootstrap-operands forms
                 (lambda (values)
                   (let ((x (second values)))
                     (b-wat "(if (i32.and ~a (i32.const 3)) (then
                               (throw $call_error (i32.const 32))))
                             (i32.shl (i32.and (i32.shr_s (i32.shr_s ~a (i32.const 2))
                                                       (i32.const ~d)) (i32.const ~d)) (i32.const 2))"
                            x x (min position 31) (1- (ash 1 size))))))))))))))


;;; A lexpr points at the count word of a retained root frame. Validate that
;;; frame before reading the count; an arbitrary fixnum is not a stack pointer.
(defun bootstrap-lexpr-count (pointer length)
  (let ((frame (temporary)) (limit (temporary)) (count (temporary)))
    (with-output-to-string (s)
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top))"
        frame (b-load wasm32::tcr.root_head) limit)
      (write-string "(block $lexpr_found (loop $lexpr_search" s)
      (write-string
        (b-condition
          (b-wat "(i32.or (i32.or (i32.eqz (local.get ~a)) (i32.and (local.get ~a) (i32.const 3))) (i32.or (i32.lt_u (local.get ~a) ~a) (i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const 12)) (i64.extend_i32_u (local.get ~a)))))"
            frame frame frame (b-load wasm32::tcr.vsp_base) frame limit) 5) s)
      (format s "(local.set ~a (i32.load offset=4 (local.get ~a)))" count frame)
      (write-string
        (b-condition
          (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.add (i64.const 8) (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 4)))) (i64.extend_i32_u (local.get ~a)))"
            frame count limit) 5) s)
      (format s "(br_if $lexpr_found (i32.eq ~a (i32.add (local.get ~a) (i32.const 8)))) (local.set ~a (local.get ~a)) (local.set ~a (i32.load (local.get ~a))) (br $lexpr_search)))"
        pointer frame limit frame frame frame)
      (format s "(local.set ~a (i32.load ~a))" length pointer)
      (write-string
        (b-condition
          (b-wat "(i32.or (i32.or (i32.and (local.get ~a) (i32.const 3)) (i32.lt_s (local.get ~a) (i32.const 0))) (i32.ne (i32.add (i32.shr_u (local.get ~a) (i32.const 2)) (i32.const 1)) (local.get ~a)))"
            length length length count) 5) s)
      (format s "(local.set ~a (i32.shr_u (local.get ~a) (i32.const 2)))" length length))))

(defun bootstrap-lexpr-copy (cursor length index prefix destination offset)
  ;; Source arguments run backwards after the tagged count. No call can move
  ;; them between this load and publication in the ordinary APPLY root frame.
  (b-wat "(block $lexpr_done (loop $lexpr_copy (br_if $lexpr_done (i32.ge_u (local.get ~a) (i32.add (local.get ~a) (i32.const ~d)))) (i32.store (i32.add (local.get ~a) (i32.add (i32.const ~d) (i32.mul (local.get ~a) (i32.const 4)))) (i32.load (i32.add (local.get ~a) (i32.mul (i32.sub (i32.add (local.get ~a) (i32.const ~d)) (local.get ~a)) (i32.const 4))))) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $lexpr_copy)))"
    index length prefix destination offset index cursor length prefix index index index))

(in-package :wasm32-compiler)

;;; Raw digit access is the target equivalent of the native bignum LAP entries.
;;; No allocation or callback follows validation and precedes a digit store.
(defun bootstrap-bignum-base (object)
  (let ((base (temporary)) (count (temporary)))
    (b-wat "(block (result i32) ~a
      (local.set ~a (i32.sub ~a (i32.const 6)))
      (call $span (local.get ~a) (i32.const 4))
      (local.set ~a (i32.shr_u (i32.load (local.get ~a)) (i32.const 8))) ~a ~a
      (call $span (local.get ~a) (i32.and (i32.add (i32.shl (local.get ~a) (i32.const 2)) (i32.const 11)) (i32.const -8)))
      (local.get ~a))"
      (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4)
      base object base count base
      (b-condition (b-wat "(i32.ne (i32.load8_u (local.get ~a)) (i32.const 7))" base) 4)
      (b-condition (b-wat "(i32.eqz (local.get ~a))" count) 4)
      base count base)))

(defun bootstrap-bignum-index (base index)
  (b-condition
   (b-wat "(i32.or (i32.and ~a (i32.const 3))
             (i32.ge_u (i32.shr_u ~a (i32.const 2))
                       (i32.shr_u (i32.load ~a) (i32.const 8))))" index index base) 4))

(defun bootstrap-bignum-call (name forms)
  (let ((arity (case name (ccl::%wasm-bignum-half-ref 3) (ccl::%wasm-bignum-set 4)
                         (ccl::%wasm-bignum-length-set 2) (t 5))))
    (unless (= (length forms) arity) (refuse :bignum-primitive-arity)))
  (bootstrap-operands forms
    (lambda (values)
      (let ((base (temporary)))
        (with-output-to-string (s)
          (format s "(local.set ~a ~a)" base (bootstrap-bignum-base (first values)))
          (case name
            ((ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set)
             (destructuring-bind (object index high &optional low) values
               (write-string (bootstrap-bignum-index (b-local base) index) s)
               (if low
                 (progn
                   (dolist (part (list high low))
                     (write-string (b-condition (b-wat "(i32.and ~a (i32.const 3))" part) 5) s))
                   (format s "(i32.store (i32.add (local.get ~a) (i32.add (i32.const 4) ~a))
                     (i32.or (i32.shl ~a (i32.const 14)) (i32.and (i32.shr_u ~a (i32.const 2)) (i32.const 65535)))) ~a"
                     base index high low object))
                 (format s "(i32.shl (i32.load16_u (i32.add (local.get ~a)
                   (i32.add ~a (if (result i32) (i32.eq ~a (i32.const 77825)) (then (i32.const 4)) (else (i32.const 6)))))) (i32.const 2))"
                   base index high))))
            (ccl::%wasm-bignum-length-set
             (let ((count (second values)) (old (temporary)) (end (temporary)) (cursor (temporary)))
               (format s "(local.set ~a (i32.shr_u (i32.load (local.get ~a)) (i32.const 8)))" old base)
               (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.eqz ~a) (i32.gt_u (i32.shr_u ~a (i32.const 2)) (local.get ~a))))" count count count old) 4) s)
               ;; Shrinking a header leaves whole aligned objects, never a gap
               ;; that the collector could mistake for an unrecognized header.
               (format s "(local.set ~a (i32.add (local.get ~a) (i32.and (i32.add (i32.shl (local.get ~a) (i32.const 2)) (i32.const 11)) (i32.const -8))))
                 (local.set ~a (i32.add (local.get ~a) (i32.and (i32.add ~a (i32.const 11)) (i32.const -8))))
                 (block $padding_done (loop $padding
                   (br_if $padding_done (i32.ge_u (local.get ~a) (local.get ~a)))
                   (i32.store (local.get ~a) (i32.const 250))
                   (i32.store offset=4 (local.get ~a) (i32.const 0))
                   (local.set ~a (i32.add (local.get ~a) (i32.const 8))) (br $padding)))
                 (if (i32.eqz (i32.and ~a (i32.const 4)))
                   (then (i32.store (i32.add (local.get ~a) (i32.add ~a (i32.const 4))) (i32.const 0))))
                 (i32.store (local.get ~a) (i32.or (i32.shl ~a (i32.const 6)) (i32.const 7))) ~a"
                 end base old cursor base count cursor end cursor cursor cursor cursor count base count base count (first values))))
            (ccl::%copy-ivector-to-ivector
             (destructuring-bind (source start destination to count) values
               (declare (ignore source))
               (let ((dest (temporary)))
                 (format s "(local.set ~a ~a)" dest (bootstrap-bignum-base destination))
                 (dolist (x (list start to count))
                   (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" x x) 4) s))
                 (loop for object in (list (b-local base) (b-local dest))
                       for offset in (list start to) do
                   (write-string (b-condition
                     (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u ~a))
                        (i64.shl (i64.extend_i32_u (i32.shr_u (i32.load ~a) (i32.const 8))) (i64.const 4)))" offset count object) 4) s))
                 (format s "(memory.copy (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
                   (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
                   (i32.shr_u ~a (i32.const 2))) ~a" dest to base start count destination))))))))))

(defun bootstrap-allocate-bignum (forms)
  (when (and (= (length forms) 2) (eql (ccl::acode-fixnum-form-p (second forms)) 7))
    (bootstrap-operands (list (first forms))
      (lambda (values)
        (let ((count (first values)))
          (b-wat "~a (i32.add ~a (i32.const 6))"
            (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.eqz ~a) (i32.gt_u ~a (i32.const 67108860))))" count count count) 6)
            (bootstrap-heap-block
              (b-wat "(i32.and (i32.add ~a (i32.const 11)) (i32.const -8))" count)
              (lambda (base bytes)
                (b-wat "(memory.fill ~a (i32.const 0) ~a) (i32.store ~a (i32.or (i32.shl ~a (i32.const 6)) (i32.const 7)))"
                  base bytes base count)))))))))

(in-package :wasm32-compiler)

(defun bootstrap-float-sign (name forms)
  (unless (= (length forms) 1) (refuse :float-sign-arity))
  (let ((doublep (eq name 'ccl::%double-float-sign)))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((object (first values)))
             (b-wat "~a ~a"
               (b-condition (b-wat "(i32.ne (call $real_operand ~a) (i32.const ~d))"
                                  object (if doublep 64 32)) 4)
               (bootstrap-boolean
                (b-wat "(i32.shr_u (i32.load offset=~d (i32.sub ~a (i32.const 6))) (i32.const 31))"
                       (if doublep 12 4) object))))))))))

(in-package :wasm32-compiler)

;;; Match the logical argument and method bits computed by native pass 2.
;;; The bootstrap pool prefix is versioned by its magic word. Unlike native
;;; instruction immediates it remains a traced, portable part of the function.
(defun bootstrap-next-method-args-p (afunc)
  (let ((seen (make-hash-table :test #'eq)))
    (labels ((visit (form)
               (cond ((gethash form seen) nil)
                     ((typep form 'ccl::afunc)
                      (setf (gethash form seen) t)
                      (visit (ccl::afunc-acode form)))
                     ((ccl::acode-p form)
                      (setf (gethash form seen) t)
                      (let ((op (ccl::acode-operator-name (ccl::acode-operator form)))
                            (args (ccl::acode-operands form)))
                        (or (and (eq op 'ccl::%function)
                                 (eq (car args) 'ccl::%call-next-method-with-args))
                            (and (eq op 'ccl::call)
                                 (eq (bootstrap-immediate (car args))
                                     'ccl::%call-next-method-with-args))
                            (some #'visit args))))
                     ((consp form) (or (visit (car form)) (visit (cdr form)))))))
      (visit afunc))))

(defun bootstrap-lfun-bits (afunc)
  (let* ((args (ccl::acode-operands (ccl::afunc-acode afunc)))
         (methodp (logbitp ccl::$fbitmethodp (ccl::afunc-bits afunc)))
         (keys (fourth args))
         (bits (dpb (min 63 (- (length (first args)) (if methodp 1 0))) ccl::$lfbits-numreq 0)))
    (setq bits (dpb (min 31 (length (first (second args)))) ccl::$lfbits-numopt bits))
    (setq bits (dpb (min 63 (length (ccl::afunc-inherited-vars afunc))) ccl::$lfbits-numinh bits))
    (when (or (some (lambda (value) (not (ccl::nx-null value))) (second (second args)))
              (some #'identity (third (second args))))
      (setq bits (logior bits (ash 1 ccl::$lfbits-optinit-bit))))
    (when (third args)
      (setq bits (logior bits (ash 1 (if (consp (third args)) ccl::$lfbits-restv-bit ccl::$lfbits-rest-bit)))))
    (when keys (setq bits (logior bits (ash 1 ccl::$lfbits-keys-bit))))
    (when (first keys) (setq bits (logior bits (ash 1 ccl::$lfbits-aok-bit))))
    (when methodp
      (setq bits (logior bits (ash 1 ccl::$lfbits-method-bit)))
      (when (logbitp ccl::$fbitnextmethp (ccl::afunc-bits afunc))
        (setq bits (logior bits (ash 1 ccl::$lfbits-nextmeth-bit))))
      (when (or (logbitp ccl::$fbitnextmethargsp (ccl::afunc-bits afunc))
                (bootstrap-next-method-args-p afunc))
        (setq bits (logior bits (ash 1 ccl::$lfbits-nextmeth-with-args-bit)))))
    bits))

(defun bootstrap-function-info (value index)
  (let ((function (temporary)) (pool (temporary)) (offset (temporary)))
    (b-wat "(block (result i32)
      (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
      (local.set ~a (i32.load offset=24 (local.get ~a)))
      ~a
      (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4))
      ~a
      (local.set ~a (if (result i32) (i32.eq (i32.load offset=16 (local.get ~a)) (i32.const 77825))
                         (then (i32.const 0)) (else (i32.const 8))))
      ~a
      (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.add (local.get ~a) (i32.const 16)))
      ~a
      (i32.load offset=~d (i32.add (local.get ~a) (local.get ~a))))"
      function value pool function
      (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" pool) 4)
      pool
      (b-condition (b-wat "(i32.ne (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 250))" pool) 4)
      offset function
      (b-condition (b-wat "(i32.lt_u (i32.shr_u (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.add (i32.shr_u (local.get ~a) (i32.const 2)) (i32.const 3)))" pool offset) 4)
      pool offset
      (b-condition (b-wat "(i32.ne (i32.load (i32.add (local.get ~a) (i32.sub (local.get ~a) (i32.const 2)))) (i32.const ~d))" pool offset (* 4 #x574153)) 4)
      (- (* 4 index) 2) pool offset)))

(defun bootstrap-function-bits (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((function (temporary)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (if (result i32) (i32.eq (i32.load (local.get ~a)) (i32.const 1834))
            (then (i32.load offset=28
                    (call $object_base (i32.load offset=28 (local.get ~a))
                      (i32.const 32) (i32.const 2042))))
            (else ~a)))"
          function (first values) function function
          (bootstrap-function-info (first values) 1))))))

(defun bootstrap-set-function-bits (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((side (temporary)) (function (first values)) (bits (second values)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base
            (i32.load offset=28 (call $object_base ~a (i32.const 32) (i32.const 1834)))
            (i32.const 32) (i32.const 2042)))
          ~a
          (i32.store offset=28 (local.get ~a) ~a) ~a)"
          side function
          (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" bits bits) 4)
          side bits bits)))))

(defun bootstrap-function-keyvect (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((value (first values)) (function (temporary)) (keys (temporary)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (if (result i32) (i32.eq (i32.load (local.get ~a)) (i32.const 1834))
            (then (i32.const 77825))
            (else
          (if (result i32) (i32.eq (i32.load offset=16 (local.get ~a)) (i32.const 77825))
            (then
              (local.set ~a ~a)
              (if (i32.ne (local.get ~a) (i32.const 77825))
                (then
                  (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4))
                  ~a
                  (call $span (i32.sub (local.get ~a) (i32.const 6))
                    (i32.add (i32.const 4) (i32.shl (i32.shr_u
                      (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.const 2))))))
              (local.get ~a))
            (else ~a)))))"
          function value function function keys (bootstrap-function-info value 2)
          keys keys
          (b-condition (b-wat "(i32.or (i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6)) (i32.ne (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 250)))" keys keys) 4)
          keys keys keys
          (bootstrap-metadata-keyvect (list (make-b-raw-code :text value))))))))
