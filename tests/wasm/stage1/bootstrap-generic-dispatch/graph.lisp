(in-package :wasm32-compiler)

;;; Project native CLOS graphs without losing identity. The represented fields
;;; are the fields the dispatcher uses; native caches and MOP bookkeeping are
;;; not imported as if they were target code or target addresses.
(defun generic-graph-json (root stream)
  (let ((ids (make-hash-table :test #'eq))
        (nodes (make-array 16 :adjustable t :fill-pointer 0))
        (wrapper-cell (cons 'ccl::class-wrapper nil))
        (allowed-methods
          (append (svref root 1)
                  (when (> (length root) 9) (list (svref root 9)))
                  (when (and (> (length root) 10) (typep (svref root 10) 'standard-method))
                    (list (svref root 10)))
                  (when (> (length root) 8)
                    (loop for gf in (svref root 8) append (ccl::%gf-methods gf))))))
    ;; The native reader is a copied LAP accessor. D1 installs its ordinary
    ;; method entry at the same generic function, retaining method dispatch.
    (let* ((gf #'ccl::eql-specializer-object)
           (method (car (ccl::%gf-methods gf))))
      (assert (= (length (ccl::%gf-methods gf)) 1))
      (assert (equalp (ccl::%wrapper-instance-slots (ccl::%class.own-wrapper
                      (find-class 'ccl::eql-specializer))) #(ccl::direct-methods ccl::object)))
      (setf (gethash (ccl::%method-function method) *accessor-function-names*)
            'ccl::%wasm-eql-specializer-reader
            (gethash gf *generic-bindings*) 'ccl::eql-specializer-object))
    (labels ((reference (object)
               (multiple-value-bind (id found) (gethash object ids)
                 (when found (return-from reference (list :ref id))))
               (cond ((or (consp object) (simple-vector-p object)
                          (ccl::%standard-instance-p object)
                          (and (ccl::istructp object)
                               (eq (ccl::istruct-type-name object) 'ccl::class-wrapper))
                          (and (functionp object)
                               (or (gethash object *accessor-function-names*)
                                   (typep object 'standard-generic-function))))
                      (let ((id (length nodes)))
                        (setf (gethash object ids) id)
                        (vector-push-extend nil nodes)
                        (setf (aref nodes id) (description object))
                        (list :ref id)))
                     (t (list :value object))))
             (node (tag fields)
               (list tag (map 'list #'reference fields)))
             (slots (object native-slots classp)
               (let ((id (length nodes))
                     (fields (make-array (ccl::uvsize native-slots) :initial-element nil)))
                 (setf (gethash native-slots ids) id)
                 (vector-push-extend nil nodes)
                 (setf (svref fields 0) object)
                 (loop for i from 1 below (length fields) do
                   (when (and classp (= i 1))
                     (setf (svref fields i)
                           (remove-if-not (lambda (method) (member method allowed-methods))
                                          (ccl::%svref native-slots i))))
                   (when (or (not classp) (member i '(3 4 5 6)))
                     (setf (svref fields i) (ccl::%svref native-slots i))))
                 (setf (aref nodes id) (node 106 fields))
                 (list :ref id)))
             (description (object)
               (cond ((consp object) (node 1 (list (car object) (cdr object))))
                     ((simple-vector-p object) (node 250 object))
                     ((and (functionp object) (typep object 'standard-generic-function))
                      (let* ((native-table (ccl::%gf-dispatch-table object))
                             (table (make-array 8 :initial-element nil))
                             (slot-ref (slots object (ccl::gf.slots object) nil)))
                        (dotimes (i 3) (setf (svref table i) (ccl::%svref native-table i)))
                        (setf (svref table 3) -1 (svref table 4) object (svref table 5) 0
                              (svref table 6) (ccl::%unbound-marker))
                        (list :generic (reference (ccl::gf.instance.class-wrapper object))
                              slot-ref (reference table) (logand #x1f7fffff (ccl::lfun-bits object)) (gethash object *generic-bindings*))))
                     ((functionp object)
                      (list :function (gethash object *accessor-function-names*)
                            (logand #x1f7fffff (ccl::lfun-bits object))))
                     ((ccl::istructp object)
                      (node 130 (vector wrapper-cell 1 (ccl::%wrapper-class object)
                                        (ccl::%wrapper-instance-slots object)
                                        nil nil nil nil nil nil
                                        (ccl::%wrapper-cpl object)
                                        (ccl::%wrapper-class-ordinal object) nil)))
                     (t
                      (let* ((classp (typep object 'class))
                             (wrapper (reference (ccl::instance.class-wrapper object)))
                             (slots (slots object (ccl::instance.slots object) classp)))
                        (list 114 (list (list :value (if classp (ccl::instance.hash object) 1048576))
                                        wrapper slots))))))
             (write-reference (ref)
               (ecase (first ref)
                 (:ref (format stream "{\"ref\":~d}" (second ref)))
                 (:value (write-string "{\"value\":" stream)
                         (core-json-value (second ref) stream) (write-char #\} stream)))))
      (let* ((entry (reference root))
             (reader (reference #'ccl::eql-specializer-object))
             (conditions
               (when (> (length root) 8)
                 (loop for name in '(condition simple-condition simple-error type-error control-error
                    simple-warning program-error ccl::simple-program-error undefined-function
                    unbound-variable storage-condition error ccl::no-applicable-method-exists
                    arithmetic-error division-by-zero floating-point-invalid-operation
                    floating-point-overflow floating-point-underflow floating-point-inexact
                    stream-error end-of-file file-error package-error ccl::simple-package-error
                    ccl::stream-is-closed-error ccl::bad-slot-type ccl::inactive-restart ccl::restart-failure)
                       collect (cons (symbol-name name) (reference (find-class name)))))))
        (write-string "{\"graph\":{\"root\":" stream) (write-reference entry)
        (multiple-value-bind (id found) (gethash ccl::*standard-method-combination* ids)
          (when found (format stream ",\"standardCombination\":~d" id)))
        (write-string ",\"reader\":" stream) (write-reference reader)
        (when conditions
          (write-string ",\"conditions\":[" stream)
          (loop for (name . ref) in conditions for i from 0 do
            (unless (zerop i) (write-char #\, stream))
            (format stream "[~s," name) (write-reference ref) (write-char #\] stream))
          (write-char #\] stream))
        (write-string ",\"nodes\":[" stream)
        (loop for row across nodes for i from 0 do
          (unless (zerop i) (write-char #\, stream))
          (case (first row)
            (:function
             (format stream "{\"function\":~s,\"bits\":~d}"
                     (frontend-owner (second row)) (third row)))
            (:generic
             (write-string "{\"generic\":[" stream)
             (loop for ref in (subseq row 1 4) for j from 0 do
               (unless (zerop j) (write-char #\, stream)) (write-reference ref))
             (format stream "],\"bits\":~d" (fifth row))
             (when (sixth row) (format stream ",\"binding\":~s" (frontend-owner (sixth row))))
             (write-char #\} stream))
            (t
             (format stream "{\"tag\":~d,\"fields\":[" (first row))
             (loop for ref in (second row) for j from 0 do
               (unless (zerop j) (write-char #\, stream)) (write-reference ref))
             (write-string "]}" stream))))
        (write-string "]}}" stream)))))
