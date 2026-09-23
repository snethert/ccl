(in-package :ccl)

;; Capture the population before formatting any report. This is the pinned
;; native bootstrap image's requirement inventory, not a cross-dumped census.
(let ((standard 0) (uninitialized 0) (other nil) (methods 0))
  (dolist (gf (copy-list (population-data %all-gfs%)))
    (handler-case
        (let ((combination (%gf-method-combination gf)))
          (if (eq combination *standard-method-combination*)
            (progn (incf standard) (incf methods (length (%gf-methods gf))))
            (push (list (function-name gf) combination) other)))
      (unbound-slot () (incf uninitialized))))
  (assert (null other))
  (with-open-file (stream (getenv "GENERIC_CENSUS_OUTPUT")
                         :direction :output :if-exists :supersede)
    (format stream "{~s:~d,~s:~d,~s:~d,~s:0}~%"
            "standard_generic_functions" standard "methods" methods
            "uninitialized_prototypes" uninitialized "other_combinations")))
(quit)
