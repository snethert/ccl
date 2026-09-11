;;; Driver for the unmodified, pinned upstream ccl-tests corpus.
(load (merge-pathnames "load.lisp" (pathname (ccl:getenv "CCL_GATE0_TESTS"))))
(load-tests :ansi t :ccl t)
(in-package :rt)

(defun cl-user::run-gate0-tests ()
(let* ((output (pathname (ccl:getenv "CCL_GATE0_OUTPUT")))
       (entries (copy-list (cdr *entries*)))
       (disabled (remove-if-not #'has-disabled-note entries))
       (eligible (remove-if #'has-disabled-note entries))
       (expected (mapcar #'name eligible)))
  ;; Freeze the evaluated corpus before running it. Preserve upstream exclusions.
  (with-open-file (s (merge-pathnames "test-inventory.sexp" output)
                     :direction :output :if-exists :error)
    (let ((*print-circle* t) (*print-pretty* nil))
      (write (list :eligible expected
                   :disabled (mapcar (lambda (e) (list (name e) (entry-notes e))) disabled)
                   :expected-failures *expected-failures*) :stream s)
      (terpri s)))
  ;; Match upstream RUN-TESTS: verbose mode changes warning-output assertions.
  (time (do-tests :compile t :verbose nil :catch-errors t))
  (let* ((missing (set-difference expected (append *passed-tests* *failed-tests*) :test #'equal))
         (unexpected (set-difference (append *passed-tests* *failed-tests*) expected :test #'equal))
         (success (and (plusp (length expected)) (null *failed-tests*)
                       (null (pending-tests)) (null missing) (null unexpected)
                       (= (length expected) (length *passed-tests*)))))
    (with-open-file (s (merge-pathnames "test-results.sexp" output)
                       :direction :output :if-exists :error)
      (let ((*print-circle* t) (*print-pretty* nil))
        (write (list :passed *passed-tests* :failed *failed-tests*
                     :missing missing :unexpected unexpected) :stream s)
        (terpri s)))
    (with-open-file (s (merge-pathnames "test-summary.json" output)
                       :direction :output :if-exists :error)
      (format s "{~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~d,~%  ~s: ~a~%}~%"
              "registered" (length entries) "eligible" (length expected)
              "upstream_disabled" (length disabled) "passed" (length *passed-tests*)
              "failed" (length *failed-tests*) "missing" (length missing)
              "unexpected" (length unexpected) "success" (if success "true" "false")))
    (format t "~&CCL-GATE0-TESTS-COMPLETE ~a~%" (if success "PASS" "FAIL"))
    (finish-output)
    (ccl:quit (if success 0 1))))

)
