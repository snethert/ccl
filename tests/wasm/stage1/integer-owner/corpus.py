import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'integer-condition-review/corpus.py'
s=importlib.util.spec_from_file_location('owner_prior_corpus',p);prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
SOURCES=dict(prior.SOURCES)
SOURCES.update({
 'e_owner_restart':'(lambda (a b) (handler-bind ((division-by-zero (lambda (e) (invoke-restart (quote use-value) (* (car (arithmetic-error-operands e)) b))))) (restart-case (truncate a 0) (use-value (v) (values v a)))))',
 'e_owner_special':'(lambda (a b) (let ((dyn_a a)) (declare (special dyn_a)) (values (* a b) dyn_a)))',
 'e_owner_binding':'(lambda (a b) (handler-case (let ((x (* a b))) (handler-bind ((division-by-zero (lambda (e) (* x b) (signal e)))) (truncate x 0))) (division-by-zero (e) (car (arithmetic-error-operands e)))))',
 'e_owner_progv':'(lambda (a b sym) (progv (cons sym nil) (cons a nil) (values (* a b) (symbol-value sym))))',
 'e_owner_cleanup':'(lambda (a b) (multiple-value-prog1 (values (cons a nil) (cons b nil)) (* a b)))',
 'e_owner_closure':'(lambda (a b) (let ((cell a)) (let ((f (lambda () cell))) (setq cell (* a b)) (values (funcall f) (* a b) (funcall f)))))',
 'e_owner_handler_values':'(lambda (a b) (multiple-value-call (lambda (&rest xs) (values (car xs) (car (cdr xs)))) (handler-case (truncate a 0) (division-by-zero (e) (values (* (car (arithmetic-error-operands e)) b) a)))))',
})
# A pending cons is checked through its contents so the integer/NIL decoder
# need not gain a graph oracle in this composition unit.
SOURCES['e_owner_cleanup']='(lambda (a b) (multiple-value-bind (x y) (multiple-value-prog1 (values (cons a nil) (cons b nil)) (* a b)) (values (car x) (car y))))'
def cases():
 rows=prior.cases()
 for a,b in [(7,3),(2**80+7,2**70+3),(-(2**160+11),2**90+5)]:
  for name in SOURCES:
   if name.startswith('e_owner_'):rows.append(dict(id=str(len(rows)),function=name,args=[str(a),str(b)]+(["dyn_a"] if name=="e_owner_progv" else [])))
 return rows
