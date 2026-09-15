;;; Flat IR reader adapted from the reviewed source-closure reader. Shared strong EQ IDs.
(in-package :ccl-registry-flow)

(defun native-code (function)
  ;; U1 X86 code-words counts the complete unboxed code prefix. Copy it with
  ;; the same primitive used by %COPY-FUNCTION; never decode pointer constants.
  (let* ((size (* 8 (ccl::%function-code-words function)))
         (bytes (make-array size :element-type '(unsigned-byte 8)))
         (hex (make-string (* 2 size))) (digits "0123456789abcdef"))
    (ccl::%copy-ivector-to-ivector (ccl::%function-to-function-vector function) 0 bytes 0 size)
    (dotimes (i size hex)
      (setf (char hex (* 2 i)) (char digits (ash (aref bytes i) -4))
            (char hex (1+ (* 2 i))) (char digits (logand (aref bytes i) 15))))))

(defun flow-graph (root)
  ;; Flat graph: list length and nesting do not consume the Lisp/JSON stack.
  ;; Opaque runtime objects stay explicit dependencies, not invented contents.
  (let ((pending (list root)) (seen (make-hash-table :test #'eq)) (rows nil))
    (labels ((ref (x)
               (cond ((null x) :null)
                     ((or (integerp x) (stringp x)) x)
                     ((symbolp x) (object "symbol" (name-key x) "identity" (oid x)))
                     (t (unless (gethash x seen) (push x pending)) (object "ref" (oid x))))))
      (loop while pending for x = (pop pending) do
        (unless (gethash x seen)
          (setf (gethash x seen) t)
          (push
            (cond
              ((ccl::acode-p x)
               (object "id" (oid x) "kind" "acode"
                    "operator" (name-key (ccl::acode-operator-name (ccl::acode-operator x)))
                    "operator_id" (logand (ccl::acode-operator x) ccl::operator-id-mask)
                    "operands" (ref (ccl::acode-operands x))))
              ((typep x 'ccl::afunc)
               (object "id" (oid x) "kind" "function" "name" (name-key (ccl::afunc-name x))
                    "body" (ref (ccl::afunc-acode x))
                    "children" (mapcar #'ref (ccl::afunc-inner-functions x))))
              ((typep x 'ccl::var)
               (object "id" (oid x) "kind" "variable" "root" (oid (ccl::nx-root-var x))
                    "name" (name-key (ccl::var-name x))
                    "assigned" (if (logbitp ccl::$vbitsetq (ccl::nx-var-bits (ccl::nx-root-var x))) :true :false)))
              ((consp x) (object "id" (oid x) "kind" "cons" "car" (ref (car x)) "cdr" (ref (cdr x))))
              ((functionp x)
               (object "id" (oid x) "kind" "native-function"
                    "function_id" (fn x)
                    "name" (name-key x)))
              (t (object "id" (oid x) "kind" "opaque-object" "type" (name-key (type-of x))))) rows)))
      (object "root" (oid root) "objects" (nreverse rows)))))
