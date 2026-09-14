;;; D1 data classification only. Native execution state is deliberately absent.
(in-package :ccl-source-closure)
(defvar *layout-source* nil)
(defvar *layout-facts* nil)
(defvar *layout-values* nil)
(defvar *layout-fields* nil)
(defvar *layout-macros* nil)
(defparameter *data-objects*
  '("ratio" "single-float" "double-float" "complex-single-float" "complex-double-float"
    "complex" "symbol" "vectorH" "value-cell"))
(defparameter *data-types*
  '((:bignum . "bignum") (:ratio . "ratio") (:single-float . "single-float")
    (:double-float . "double-float") (:complex . "complex")
    (:complex-single-float . "complex-single-float") (:complex-double-float . "complex-double-float")
    (:symbol . "symbol") (:function . "function") (:struct . "struct") (:istruct . "istruct")
    (:pool . "pool") (:population . "weak") (:hash-vector . "hash-vector")
    (:package . "package") (:value-cell . "value-cell") (:instance . "instance")
    (:lock . "lock") (:slot-vector . "slot-vector") (:basic-stream . "basic-stream")
    (:simple-string . "simple-base-string") (:bit-vector . "bit-vector")
    (:signed-8-bit-vector . "s8-vector") (:unsigned-8-bit-vector . "u8-vector")
    (:signed-16-bit-vector . "s16-vector") (:unsigned-16-bit-vector . "u16-vector")
    (:signed-32-bit-vector . "s32-vector") (:unsigned-32-bit-vector . "u32-vector")
    (:fixnum-vector . "fixnum-vector") (:single-float-vector . "single-float-vector")
    (:double-float-vector . "double-float-vector") (:simple-vector . "simple-vector")
    (:complex-single-float-vector . "complex-single-float-vector")
    (:complex-double-float-vector . "complex-double-float-vector")
    (:vector-header . "vectorH") (:array-header . "arrayH")))
(defparameter *data-fields*
  '((arch::target-null-tag . "fulltag-cons")
    (arch::target-symbol-tag . "subtag-symbol")
    (arch::target-function-tag . "subtag-function")
    (arch::target-single-float-tag . "subtag-single-float")
    (arch::target-double-float-tag . "subtag-double-float")
    (arch::target-subtag-char . "subtag-character")
    (arch::target-charcode-shift . "charcode-shift")
    (arch::target-unbound-marker-value . "unbound-marker")
    (arch::target-slot-unbound-marker-value . "slot-unbound-marker")
    (arch::target-misc-subtag-offset . "misc-subtag-offset")
    (arch::target-misc-dfloat-offset . "misc-dfloat-offset")))

(defun layout-form (marker &optional (package "X8632"))
  (let* ((needle (string-downcase marker)) (haystack (string-downcase *layout-source*))
         (start (search needle haystack)))
    (when start
      (when (search needle haystack :start2 (1+ start)) (error "D1-AMBIGUOUS-FORM ~a" marker))
      (let ((*package* (find-package package)) (*read-eval* nil))
        (multiple-value-bind (form end) (read-from-string *layout-source* t nil :start start)
          (pushnew (obj "start" start "end" end "text" (subseq *layout-source* start end))
                   *layout-facts* :test #'equal)
          form)))))

(defun layout-number (name &optional (stack nil))
  ;; Evaluate only integer representation definitions, with no Lisp EVAL and
  ;; no host-symbol-value fallback. Every leaf points back to U1 source text.
  (let* ((key (string-upcase name)) (cached (assoc key *layout-values* :test #'equal)))
    (when cached (return-from layout-number (cdr cached)))
    (when (member key stack :test #'equal) (error "D1-CONSTANT-CYCLE ~a" key))
    (labels ((number-form (form)
               (cond ((integerp form) form)
                     ((symbolp form) (layout-number (symbol-name form) (cons key stack)))
                     ((and (consp form) (member (car form) '(+ - * ash logior logand 1- 1+)))
                      (apply (car form) (mapcar #'number-form (cdr form))))
                     (t (error "D1-NONINTEGER-FORM ~s" form)))))
      (let* ((definition (layout-form (format nil "(defconstant ~a " key)))
             (value
               (if definition (number-form (third definition))
                 (if (and (> (length key) 7) (string= key "SUBTAG-" :end1 7))
                   (let* ((suffix (subseq key 7))
                          (node (layout-form (format nil "(define-node-subtag ~a " suffix)))
                          (imm (layout-form (format nil "(define-imm-subtag ~a " suffix)))
                          (generic (layout-form (format nil "(define-subtag ~a " suffix)))
                          (tag (cond (node "fulltag-nodeheader") (imm "fulltag-immheader")
                                     (generic (symbol-name (third generic)))
                                     (t (error "D1-MISSING-SUBTAG ~a" key))))
                          (index (if generic (fourth generic) (third (or node imm)))))
                     (unless (integerp index) (error "D1-SUBTAG-INDEX"))
                     (logior (layout-number tag (cons key stack))
                             (ash index (layout-number "ntagbits" (cons key stack)))))
                   (error "D1-MISSING-CONSTANT ~a" key)))))
        (push (cons key value) *layout-values*) value))))

(defun derive-object (name)
  (let* ((form (or (layout-form (format nil "(define-fixedsized-object ~a~%" name))
                   (error "D1-OBJECT-SOURCE ~a" name)))
         (cells (cddr form)) (word (layout-number "node-size")) (tag (layout-number "fulltag-misc")))
    (loop for cell in (cons 'header cells) for offset from 0 do
      (push (cons (string-upcase (format nil "~a.~a" name cell)) (- (* word offset) tag)) *layout-values*))
    (loop for cell in cells for index from 0 do
      (push (cons (string-upcase (format nil "~a.~a-cell" name cell)) index) *layout-values*))
    (push (cons (string-upcase (format nil "~a.size" name)) (* word (1+ (length cells)))) *layout-values*)
    (push (cons (string-upcase (format nil "~a.element-count" name)) (length cells)) *layout-values*)))

(defun retarget-data-symbols (form)
  (cond ((and (symbolp form) (eq (symbol-package form) (find-package "X8632")))
         (let ((entry (assoc (symbol-name form) *layout-values* :test #'equal)))
           (unless entry (error "D1-MACRO-NONDATA-REFERENCE ~s" form))
           ;; Numeric leaves are literal target constants, not runtime globals.
           (cdr entry)))
        ((consp form) (cons (retarget-data-symbols (car form)) (retarget-data-symbols (cdr form))))
        (t form)))

(defun with-data-layout (thunk)
  (let* ((arch (ccl::backend-target-arch ccl-census-stub::*backend*))
         (*layout-source* (ccl-source-traversal::source-text
             (merge-pathnames "compiler/X86/X8632/x8632-arch.lisp"
               (pathname (concatenate 'string (ccl:getenv "CCL_DEFAULT_DIRECTORY") "/")))))
         (saved nil) (symbols nil) (macros nil)
         (table (arch::target-target-macros arch))
         (old-dispatch (ccl::backend-p2-dispatch ccl-census-stub::*backend*)))
    (labels ((install-field (accessor value)
               (push (cons accessor (funcall accessor arch)) saved)
               (funcall (fdefinition (list 'setf accessor)) value arch)
               (push (obj "accessor" (label accessor) "value"
                          (cond ((integerp value) value) ((eq value t) :true)
                                ((eq accessor 'arch::target-uvector-subtags)
                                 (mapcar (lambda (r) (obj "name" (label (car r)) "value" (cdr r))) value))
                                ((functionp value) (obj "kind" "source-rebuilt-helper" "function_id" (ident value)))
                                (t (error "D1-UNRECORDED-FIELD ~s" accessor)))) *layout-fields*)))
      (unwind-protect
        (progn
          ;; NX1-%ILOGNOT probes this optional lowering. NIL means absent;
          ;; an empty vector incorrectly traps before reaching that fallback.
          (setf (ccl::backend-p2-dispatch ccl-census-stub::*backend*)
                (make-array (length ccl::*next-nx-operators*) :initial-element nil))
          (install-field 'arch::target-uvector-subtags
            (append (loop for (key . name) in *data-types* collect
                       (cons key (layout-number (concatenate 'string "subtag-" name))))
                    (list (cons :min-cl-ivector-subtag (layout-number "min-cl-ivector-subtag")))))
          (dolist (r *data-fields*) (install-field (car r) (layout-number (cdr r))))
          (dolist (accessor '(arch::target-symbol-tag-is-subtag arch::target-function-tag-is-subtag
                             arch::target-single-float-tag-is-subtag)) (install-field accessor t))
          (dolist (name '("num-subtag-bits" "subtagmask" "tagmask" "tag-fixnum" "tag-imm"
                          "max-numeric-subtag" "max-real-subtag" "max-rational-subtag" "min-float-subtag"
                          "max-float-subtag" "min-numeric-subtag" "dnode-size" "dnode-shift"
                          "fixnumone" "word-shift" "fixnummask")) (layout-number name))
          (dolist (name *data-objects*) (derive-object name))
          ;; Rebuild the pure data-classification helper, substituting its two
          ;; numeric X8632 leaves from the source evaluator above.
          (let* ((form (layout-form "(defun x8632-array-type-name-from-ctype "))
                 (body (copy-tree (cddr form))))
            (dolist (name '(x8632::target-most-negative-fixnum x8632::target-most-positive-fixnum))
              (setf body (subst (layout-number (symbol-name name)) name body)))
            (install-field 'arch::target-array-type-name-from-ctype-function
                           (ccl-census-macros::native-function `(lambda ,@body))))
          (dolist (name '(ccl::%make-sfloat ccl::%make-dfloat ccl::%numerator ccl::%denominator
                          ccl::immediate-p-macro ccl::hashed-by-identity
                          ccl::symptr->symvector ccl::symvector->symptr))
            (let* ((form (layout-form (format nil "(defx8632archmacro ccl::~a " (symbol-name name)) "CCL"))
                   ;; The x8632 macro's parameter symbols belong to X8632 too.
                   ;; Alpha-rename those before substituting numeric leaves.
                   (renamings (mapcar (lambda (s) (cons s (make-symbol (symbol-name s)))) (third form)))
                   (body (sublis renamings (cdddr form)))
                   (lambda-list (mapcar #'cdr renamings))
                   (expander (ccl-census-macros::native-function
                              (ccl::parse-macro-1 name lambda-list (retarget-data-symbols body)))))
              (multiple-value-bind (old present) (gethash name table)
                (push (list name old present) macros))
              (setf (gethash name table) expander)
              (push (obj "name" (label name) "source" (label (second form)) "function_id" (ident expander)) *layout-macros*)))
          ;; Publish only the constants actually derived above, in the private
          ;; census package. No TCR, native address, code vector or trap layout.
          (dolist (r *layout-values*)
            (let ((sym (intern (car r) "WASM-CENSUS")))
              (when (and (boundp sym) (/= (symbol-value sym) (cdr r))) (error "D1-CONSTANT-CONFLICT"))
              (unless (boundp sym)
                (push (list sym nil nil) symbols)
                (setf (symbol-value sym) (cdr r)))))
          (funcall thunk))
        (dolist (r symbols) (if (second r) (setf (symbol-value (first r)) (third r)) (makunbound (first r))))
        (dolist (r macros) (if (third r) (setf (gethash (first r) table) (second r)) (remhash (first r) table)))
        (setf (ccl::backend-p2-dispatch ccl-census-stub::*backend*) old-dispatch)
        (dolist (r saved) (funcall (fdefinition (list 'setf (car r))) (cdr r) arch))))))
