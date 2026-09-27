(in-package "CCL")
(load "ccl:compiler;WASM32;wasm32-bundle.lisp")
(defun target-fixture-literal (value)
  (cond ((and value (not (eq value t)) (symbolp value))
         (list :object (cons "symbol" (symbol-name value))
               (cons "package" (package-name (symbol-package value)))))
        ((consp value) (mapcar #'target-fixture-literal value))
        ((and (vectorp value) (not (stringp value)))
         (map 'vector #'target-fixture-literal value))
        (t value)))
(let ((out (getenv "LOADER_OUTPUT")))
  ;; Compile the entire production reader, including the new opcode handler.
  (multiple-value-bind (path modules warnings failure)
      (wasm32-compiler::wasm32-compile-file "ccl:level-0;nfasload.lisp"
        :output-file (concatenate 'string out "nfasload.w32fsl"))
    (declare (ignore path warnings))
    (assert (not failure))
    (format t "TARGET-READER-COMPILED ~d~%" (length modules)))
  (multiple-value-bind (path records warnings modules)
      (wasm32-compiler::wasm32-compile-bundle-records
       "ccl:tests;wasm;stage1;loader-target;smoke.lisp"
       (concatenate 'string out "smoke.w32fsl")
       (concatenate 'string out "records.json"))
    (declare (ignore path records warnings))
    (with-open-file (s (concatenate 'string out "fixture-functions.json")
                       :direction :output :if-exists :supersede)
      (wasm32-compiler::wasm32-bundle-json
       (cons :object
             (loop for module in modules
                   for table = (make-array 8 :adjustable t :fill-pointer 0)
                   do (wasm32-compiler::wasm32-code-record module table)
                   collect (cons (getf module :name)
                                 (list :object
                                       (cons "name" (target-fixture-literal (svref (getf module :pool) 5)))
                                       (cons "arity" (target-fixture-literal (svref (getf module :pool) 0)))
                                       (cons "symbols" (target-fixture-literal table)))))) s))
    (with-open-file (s (concatenate 'string out "fixture-pools.json")
                       :direction :output :if-exists :supersede)
      (wasm32-compiler::wasm32-bundle-json
       (cons :object (loop for module in modules
                          when (null (getf module :children))
                          collect (cons (getf module :name)
                                        (target-fixture-literal
                                         (subseq (getf module :pool) 6))))) s)))
  ;; Produce the native oracle after target compilation, so native definitions
  ;; cannot influence the target compiler's view of this file.
  (load (compile-file "ccl:tests;wasm;stage1;loader-target;smoke.lisp"
          :output-file (concatenate 'string out "smoke.dx64fsl")))
  (with-open-file (s (concatenate 'string out "values-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (loop for count in '(0 1 3 4 16 32)
           for args = (loop for i below count collect (if (oddp i) nil i))
           collect (list args (multiple-value-list (apply #'target-loader-values args)))) s))
  (with-open-file (s (concatenate 'string out "assq-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (loop for args in '((1 nil) (1 ((1 10) (2 20)))
                        (2 (nil (1 10) nil (2 20)))
                        (3 ((1 10) (2 20))) (nil (nil (nil 30)))
                        (1 17) (1 (17)))
           collect (list args (handler-case (apply #'target-loader-assq args)
                                (type-error () "TYPE-ERROR")))) s))
  (with-open-file (s (concatenate 'string out "extrema-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (loop for args in '((0 0) (7 -3) (-3 7) (-8 -9)
                        (-536870912 536870911) (536870911 -536870912))
           collect (list args (multiple-value-list (apply #'target-loader-extrema args))))
     s))
  (with-open-file (s (concatenate 'string out "keyword-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (list (target-loader-ordinary-keys 40 :amount 2)
           (%apply-with-method-context nil #'target-loader-method-keys '(40 :amount 2 :other 9))
           (%apply-with-method-context nil #'target-loader-method-keys '(40 :other 9))
           (handler-case (progn (target-loader-ordinary-keys 40 :other 9) nil)
             (program-error () t))) s))
  (with-open-file (s (concatenate 'string out "type-member-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json (mapcar #'target-loader-type-member '(* :other other nil 17)) s))
  (with-open-file (s (concatenate 'string out "require-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-compiler::wasm32-bundle-json
     (loop for (kind value) in
             '((0 -536870912) (0 536870911) (0 nil)
               (1 nil) (1 :other) (1 0) (2 nil) (2 (1 2)) (2 0)
               (3 -1) (3 nil) (4 "abc") (4 nil) (5 #()) (5 nil)
               (6 #\a) (6 97) (7 1) (7 nil) (8 -1) (8 nil)
               (9 -128) (9 127) (9 -129) (9 128)
               (10 0) (10 255) (10 -1) (10 256)
               (11 -32768) (11 32767) (11 -32769) (11 32768)
               (12 0) (12 65535) (12 -1) (12 65536)
               (13 -536870912) (13 536870911) (13 nil)
               (14 0) (14 536870911) (14 -1)
               (15 -536870912) (15 536870911) (15 nil)
               (16 0) (16 536870911) (16 -1))
           collect (list (list kind
                               (cond ((characterp value)
                                      (list :object (cons "character" (char-code value))))
                                     ((and (vectorp value) (not (stringp value)))
                                      (list :object (cons "vector" value)))
                                     (t (target-fixture-literal value))))
                         (handler-case
                             (eq value (target-loader-require kind value))
                           (type-error () "TYPE-ERROR")))) s))
  (with-open-file (s (concatenate 'string out "vector-init-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (loop for kind below 4 collect
       (list (list 13 kind) (multiple-value-list (target-loader-vector-init 13 kind)))) s))
  (with-open-file (s (concatenate 'string out "reset-binding-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json (multiple-value-list (target-loader-reset-binding 99)) s))
  (with-open-file (s (concatenate 'string out "structure-init-native.json")
                     :direction :output :if-exists :supersede)
    (wasm32-json
     (loop for kind below 2 append
       (loop for value in '(0 nil 42) collect
         (list (list 13 value kind)
               (multiple-value-list (target-loader-structure-init 13 value kind))))) s)))
(format t "TARGET-BUNDLE-COMPILED~%")
(quit)
