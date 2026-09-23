;;; Target definitions of native LAP entries.  The 64-bit image supplies the
;;; oracle for the entries whose contract does not depend on word size; the
;;; others are compared through arch probes with a native reference.
(let ((previous *core-records*))
  (core-compile-file "ccl:level-0;WASM32;w32-lap.lisp")
  (loop for tail on *core-records* until (eq tail previous) do
    (let ((name (second (car tail))))
      (when (and name (symbolp name)
                 (member name '(ccl::%ilogcount ccl::%fixnum-intlen ccl::%iash
                                ccl::%fixnum-truncate ccl::fast-mod
                                ccl::%init-gvector ccl::%copy-gvector-to-gvector

                                ccl::%symptr->symbol ccl::true ccl::false
                                ccl::single-float-bits ccl::double-float-bits
                                ccl::double-float-from-bits
                                ccl::%double-float-sign ccl::%short-float-sign
                                ccl::%double-float-exp ccl::set-%double-float-exp
                                ccl::%short-float-exp
                                ccl::%%double-float-abs! ccl::%double-float-negate!
                                ccl::%integer-decode-double-float
                                ccl::%make-float-from-fixnums ccl::%%scale-dfloat!
                                ccl::%short-float->double-float
                                ccl::%truncate-double-float->fixnum
                                ccl::%truncate-short-float->fixnum
                                ccl::%round-nearest-double-float->fixnum
                                ccl::%round-nearest-short-float->fixnum
                                ccl::%double-float-sqrt! ccl::%set-hash-table-vector-key))
                 (fboundp name))
        (setf (gethash name *core-native-functions*) (fdefinition name))))))
