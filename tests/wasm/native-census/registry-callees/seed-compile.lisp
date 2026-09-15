;;; Compile the seed-bearing units in the same process as their object witness.
(in-package :ccl-seed-functions)

(defun compiler-inputs ()
  (let* ((token ccl::cfasl-load-time-eval-sym) (macro (fboundp token)))
    (unless (and (simple-vector-p macro) (= (length macro) 2) (functionp (svref macro 1)))
      (error "SEED-MARKER-WRAPPER"))
    (ccl-complete-census::function-id (svref macro 1))
    (ccl-complete-census::emit "deferred-marker-read"
      "symbol" (ccl-startup-census::dependency-id token)
      "symbol_description" (ccl-rich-census::describe-value token)
      "macro" (ccl-rich-census::describe-value macro)))
  (ccl-complete-census::emit "seed-runtime-inputs"
    "callbacks"
    (ccl::with-lock-grabbed (ccl::*callback-lock*)
      (loop for entry across ccl::%pascal-functions% for slot from 0 when entry collect
        (ccl-startup-census::object "slot" slot
          "symbol" (ccl-rich-census::describe-value (ccl::pfe.sym entry))
          "function" (ccl-complete-census::function-id (ccl::pfe.lisp-function entry)))))
    "dcode_prototypes"
    (loop for (dcode . proto) in ccl::dcode-proto-alist collect
      (ccl-startup-census::object "dcode" (ccl-complete-census::function-id dcode)
        "prototype" (ccl-complete-census::function-id proto)))
    "default_gf_prototype" (ccl-complete-census::function-id #'ccl::funcallable-trampoline)))

(defun final-functions ()
  ;; Source information can be attached after pass 2 returns. Read the same
  ;; function objects again, rather than treating the earlier drain as final.
  (let ((original (symbol-function 'ccl-complete-census::emit))
        (ccl-complete-census::*pending-functions* nil)
        (ccl::*warn-if-redefine* nil) (ccl::*warn-if-redefine-kernel* nil))
    (maphash (lambda (fn present) (declare (ignore present))
               (push fn ccl-complete-census::*pending-functions*))
             ccl-complete-census::*native-functions*)
    (unwind-protect
      (progn
        (setf (symbol-function 'ccl-complete-census::emit)
              (lambda (kind &rest fields)
                (unless (equal kind "function") (error "SEED-FINAL-EVENT"))
                (apply original "final-function" fields)))
        (ccl-complete-census::drain-functions))
      (setf (symbol-function 'ccl-complete-census::emit) original))))

(defun compile-seed-units ()
  (let* ((directory (ccl:getenv "SEED_COMPILE_OUTPUT"))
         (mode (ccl:getenv "SEED_COMPILE_MODE"))
         (units (with-open-file (s (ccl:getenv "SEED_COMPILE_UNITS"))
                  (let ((*read-eval* nil)) (read s))))
         (observed (equal mode "observed"))
         (*inspection-functions* nil))
    ;; Both modes run the identical private inspector before compilation.
    (run)
    (labels ((compile-units ()
               (loop for unit in units for index from 0 do
                 (format t "SEED-COMPILE ~d ~a~%" index unit)
                 (force-output)
                 (let ((ccl-lap-census::*unit* unit))
                   (ccl-cold-bodies::compile-one (pathname unit)
                     (format nil "~a/outputs-~3,'0d.json" directory index) observed)))))
      (if observed
        (ccl-complete-census::with-build-observation
         (concatenate 'string directory "/build.jsonl")
         (concatenate 'string directory "/registries.jsonl")
         (lambda ()
           (ccl-complete-census::emit
            "inspection-map" "entries"
            (loop for (id . fn) in *inspection-functions* collect
              (ccl-startup-census::object "inspection_id" id
                "function" (ccl-complete-census::function-id fn))))
           (compiler-inputs)
           (ccl-lap-census::with-assembler-observation #'compile-units)
           (final-functions)))
        (compile-units)))
    (format t "SEED-COMPILE-PASS ~d~%" (length units))))
