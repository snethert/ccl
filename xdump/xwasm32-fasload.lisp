;;; Wasm registration counterpart of U1 xx8632-fasload.lisp.
;;; The Stage 1E heap/code writer is deliberately not implemented by this slice.
(in-package "CCL")
(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "XFASLOAD" "ccl:xdump;xfasload"))
(defun wasm32-xload-unavailable (&rest arguments)
  (declare (ignore arguments))
  (wasm32-compiler::refuse :coordinated-heap-code-writer))
(defvar *wasm32-xload-backend*
  (make-backend-xload-info
   :name :wasm32 :compiler-target-name :wasm32
   :macro-apply-code-function 'wasm32-xload-unavailable
   :static-space-init-function 'wasm32-xload-unavailable
   ;; No native instruction word, trampoline, image address or image filename
   ;; is a valid Wasm substitute. Refuse before the native writer is entered.
   :closure-trampoline-code nil :udf-code nil
   :default-image-name nil :default-startup-file-name nil
   :subdirs '("ccl:level-0;WASM32;") :nil-relative-symbols nil
   :image-base-address nil :static-space-address nil :purespace-reserve nil))
(when (and (find-xload-backend :wasm32)
           (not (eq (find-xload-backend :wasm32) *wasm32-xload-backend*)))
  (error "Conflicting WASM32 cross-loader"))
(add-xload-backend *wasm32-xload-backend*)
(defun wasm32-cross-load (&rest arguments)
  (apply #'wasm32-xload-unavailable arguments))
(provide "XWASM32FASLOAD")
