(in-package :wasm32-compiler)

(defun namespace-root-check ()
  (let ((root ccl::*wasm-namespace-ccl-root*)
        (defaults *default-pathname-defaults*)
        (translations ccl::%logical-host-translations%))
    (labels ((refused (name)
               (handler-case
                   (progn (ccl::%wasm-namespace-initialize name) nil)
                 (error ()
                   (and (eq root ccl::*wasm-namespace-ccl-root*)
                        (eq defaults *default-pathname-defaults*)
                        (eq translations ccl::%logical-host-translations%))))))
      (unwind-protect
           (let ((missing (refused "/missing-root"))
                 (file (refused "/ccl/a.bin")))
             (ccl::%wasm-namespace-initialize "/other")
             (vector missing file (namestring (ccl::ccl-directory))
                     (namestring (truename "ccl:a.bin"))
                     (namestring *default-pathname-defaults*)))
        (ccl::%wasm-namespace-initialize root)))))

(defun namespace-byte-copy (source start destination to count)
  (ccl::%copy-ivector-to-ivector source start destination to count))

(defun namespace-vector-allocate (count tag value)
  (ccl::%make-uvector count tag value))

(defun namespace-table-refusals ()
  (mapcar (lambda (arguments)
            (handler-case
                (progn (apply #'make-hash-table arguments) nil)
              (error () t)))
          '((:size -1) (:size :invalid)
            (:rehash-size 0) (:rehash-size 1.0) (:rehash-size :invalid)
            (:rehash-threshold -1) (:rehash-threshold 2) (:rehash-threshold :invalid)
            (:hash-function eq) (:weak t) (:finalizeable t) (:test :invalid))))
