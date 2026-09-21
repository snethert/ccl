"""Move audit 149's selection step into the existing operator CASE."""
import hashlib

def fold(source):
    def edit(old,new):
        nonlocal source
        assert source.count(old)==1,old
        source=source.replace(old,new)
    edit('''    (let ((test (bootstrap-fixnum-test ir)))
      (when test (return-from b-scalar-inner (b-scalar test))))
''','')
    start=source.index('(defun bootstrap-operator (ir)')
    pos=source.index('    (case op\n',start)
    source=source[:pos]+source[pos:].replace('    (case op\n','''    (case op
      (ccl::eq
       (let* ((left (second args)) (right (third args))
              (form (cond ((eql (ccl::acode-fixnum-form-p left) 0) right)
                          ((eql (ccl::acode-fixnum-form-p right) 0) left))))
         (when (and form (ccl::acode-form-typep form 'fixnum t))
           (b-scalar (ccl::make-acode (ccl::%nx1-operator ccl::%izerop) (first args) form)))))
''',1)
    edit('''      (ccl::numcmp
       (bootstrap-primary
        (bootstrap-numeric-call
         (ecase (ccl::acode-immediate-operand (car args))
           (:lt '<) (:le '<=) (:eq '=) (:ne '/=) (:ge '>=) (:gt '>)) (cdr args))))''','''      (ccl::numcmp
       (if (every (lambda (x) (ccl::acode-form-typep x 'fixnum t)) (cdr args))
         (b-scalar (ccl::make-acode (ccl::%nx1-operator ccl::%i<>)
                                   (first args) (second args) (third args)))
         (bootstrap-primary
          (bootstrap-numeric-call
           (ecase (ccl::acode-immediate-operand (car args))
             (:lt '<) (:le '<=) (:eq '=) (:ne '/=) (:ge '>=) (:gt '>)) (cdr args)))))''')
    start=source.index(';;; Select the existing checked fixnum tests')
    assert source[start:].count('(defun ')==1
    source=source[:start].rstrip()+'\n'
    assert 'bootstrap-fixnum-test' not in source
    return source
