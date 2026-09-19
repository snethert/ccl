;; Disposable reference image only. Observe the first native boundary after a
;; returning/NIL debugger hook; do not enter an interactive terminal debugger.
(defvar *ll19-declined-boundary* nil)
(let ((ccl:*warn-if-redefine-kernel* nil) (original (symbol-function 'ccl::%break-message)))
  (setf (symbol-function 'ccl::%break-message)
        (lambda (message condition &rest args)
          (if *ll19-declined-boundary*
              (funcall *ll19-declined-boundary* condition nil)
              (apply original message condition args)))))
