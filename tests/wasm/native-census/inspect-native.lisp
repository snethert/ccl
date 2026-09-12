;;; Readable before/after evidence for every function changed by the patch.
(with-open-file (s (ccl:getenv "CCL_CENSUS_DISASSEMBLY")
                   :direction :output :if-exists :error)
  (let ((*standard-output* s) (*print-pretty* nil))
    (dolist (name '(ccl::compile-named-function ccl::%compile-time-eval
                   ccl::fcomp-read-loop ccl::fcomp-macroexpand-1
                   ccl::fcomp-compile-toplevel-forms ccl::restore-lisp-pointers))
      (format t "~&FUNCTION ~s~%" name)
      (disassemble (fdefinition name)))))
(format t "CENSUS-DISASSEMBLY-COMPLETE~%")
(ccl:quit)
