;;; Reuse the reviewed per-form source traversal without modifying it.
(in-package :ccl-census-descriptions)

(defun run ()
  (let* ((path (pathname (ccl:getenv "CCL_TRAVERSE_SOURCE")))
         (text (ccl-source-traversal::source-text path))
         (before (ccl-source-traversal::state))
         (bindings nil) (rows nil) (during nil) (types nil)
         (*expansions* nil) (*initializers* nil) (*initializer-guards* nil) (*initializer-links* nil)
         (*mode* (or (ccl:getenv "CCL_DESCRIPTION_MODE") "normal"))
         (original-types (arch::target-uvector-subtags wasm-census::*census-arch*))
         (old-pass2 (ccl::backend-p2-compile ccl-census-stub::*backend*))
         (macros (arch::target-target-macros wasm-census::*census-arch*))
         (old-macro (gethash 'ccl::%get-kernel-global macros)))
    (multiple-value-bind (index tail-start eof) (ccl-source-traversal::index-source text nil)
      (multiple-value-bind (suppressed ignored suppressed-eof) (ccl-source-traversal::index-source text t)
        (declare (ignore ignored))
        (unless (and (= eof suppressed-eof)
                     (equal (mapcar (lambda (r) (list (ccl-source-traversal::field r "start")
                                                     (ccl-source-traversal::field r "end"))) index)
                            (mapcar (lambda (r) (list (ccl-source-traversal::field r "start")
                                                     (ccl-source-traversal::field r "end"))) suppressed)))
          (error "INDEPENDENT-READER-BOUNDARIES-DIFFER")))
      (dolist (r index)
        (when (equal (ccl-source-traversal::field r "operator") "COMMON-LISP::DEFUN")
          (let* ((*package* (find-package "CCL"))
                 (name (read-from-string (ccl-source-traversal::field r "name"))))
            (push (cons name (fboundp name)) bindings))))
      ;; Exercise an actual nonlocal escape through the temporary descriptor.
      (let ((tag (gensym)))
        (unless (eq :escaped (catch tag (with-descriptions (lambda () (throw tag :escaped)))))
          (error "DESCRIPTION-ESCAPE-FAILED")))
      (unless (and (eq original-types (arch::target-uvector-subtags wasm-census::*census-arch*))
                   (eq old-pass2 (ccl::backend-p2-compile ccl-census-stub::*backend*))
                   (eq old-macro (gethash 'ccl::%get-kernel-global macros)))
        (error "DESCRIPTION-NONLOCAL-STATE-NOT-RESTORED"))
      (with-descriptions
        (lambda ()
          (ccl-census-stub::with-target-state
            (lambda ()
              (setf during (ccl-source-traversal::context)
                    types (loop for (name . value) in (arch::target-uvector-subtags wasm-census::*census-arch*)
                                collect (ccl-source-traversal::obj "name" (ccl-source-traversal::label name) "subtag" value))
                    rows (ccl-source-traversal::traverse path text index))))))
      (unless (and (equal before (ccl-source-traversal::state))
                   (eq original-types (arch::target-uvector-subtags wasm-census::*census-arch*))
                   (eq old-pass2 (ccl::backend-p2-compile ccl-census-stub::*backend*))
                   (eq old-macro (gethash 'ccl::%get-kernel-global macros)))
        (error "DESCRIPTION-STATE-NOT-RESTORED"))
      (unless (every (lambda (b) (eq (cdr b) (fboundp (car b)))) bindings)
        (error "SOURCE-FUNCTION-INSTALLED"))
      (with-open-file (out (ccl:getenv "CCL_TRAVERSE_OUTPUT") :direction :output :if-exists :error :external-format :utf-8)
        (ccl-startup-census::json
          (ccl-source-traversal::obj
            "version" 1 "source" "lib/dumplisp.lisp" "characters" (length text)
            "index" index "tail_start" tail-start "eof" eof "target" during "rows" rows
            "native_state_restored" :true "source_bindings_unchanged" :true
            "description_state_restored" :true "nonlocal_description_state_restored" :true
            "types" types "expansions" (nreverse *expansions*)
            "load_time_initializers" (nreverse *initializers*)
            "load_time_links" (nreverse *initializer-links*)
            "constants" (loop for name in '(wasm-census::subtag-basic-stream wasm-census::subtag-instance
                                            wasm-census::subtag-struct wasm-census::subtag-istruct
                                            wasm-census::min-cl-ivector-subtag wasm-census::subtag-arrayH
                                            wasm-census::subtag-vectorH wasm-census::subtag-simple-vector)
                              collect (ccl-source-traversal::obj "name" (symbol-name name) "value" (symbol-value name)))
            "scope" "D1 subtype metadata and a symbolic startup-batch input. Runtime implementation, native boundary replacement and macro qualification remain open.") out)
        (terpri out))
      (format t "TARGET-DESCRIPTIONS-COMPLETE ~d/~d~%" (length rows) (length index)))))
