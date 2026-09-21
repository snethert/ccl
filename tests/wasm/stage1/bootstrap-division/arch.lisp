(cl:in-package :wasm32)

(arch::defarchmacro :wasm32 ccl::symptr->symvector (s)
  s)

(arch::defarchmacro :wasm32 ccl::symvector->symptr (s)
  s)

(cl:in-package :ccl)

(defun wasm32-array-type-name-from-ctype (ctype)
  (when (typep ctype 'array-ctype)
    (let ((element-type (array-ctype-element-type ctype)))
      (typecase element-type
        (class-ctype
         (when (member (class-ctype-class element-type)
                       (list *character-class* *base-char-class* *standard-char-class*))
           :simple-string))
        (numeric-ctype
         (when (and (eq (numeric-ctype-class element-type) 'integer)
                    (not (eq (numeric-ctype-complexp element-type) :complex))
                    (integerp (numeric-ctype-low element-type))
                    (integerp (numeric-ctype-high element-type))
                    (<= 0 (numeric-ctype-low element-type))
                    (<= (numeric-ctype-high element-type) 255))
           (if (<= (numeric-ctype-high element-type) 1)
             :bit-vector
             :unsigned-8-bit-vector)))
        (named-ctype
         (when (eq element-type *universal-type*) :simple-vector))))))

(setf (arch::target-array-type-name-from-ctype-function wasm32::*target-arch*)
      #'wasm32-array-type-name-from-ctype)

(cl:in-package :wasm32)

;;; DEFINE-FIXEDSIZED-OBJECT publishes these indices on the native targets.
;;; D1's raw offsets already include the header; node access starts after it.
(cl:defconstant symbol.pname-cell 0)
(cl:defconstant symbol.vcell-cell 1)
(cl:defconstant symbol.fcell-cell 2)
(cl:defconstant symbol.package-predicate-cell 3)
(cl:defconstant symbol.flags-cell 4)
(cl:defconstant symbol.plist-cell 5)
(cl:defconstant symbol.binding-index-cell 6)
(cl:defconstant symbol.element-count 7)
