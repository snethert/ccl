import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'integer-calls/corpus.py';s=importlib.util.spec_from_file_location('numeric_prior_corpus',p);prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
SOURCES=dict(prior.SOURCES)
SOURCES.update({
 'e_short':'(lambda (a b) (multiple-value-bind (q r missing) (truncate a b) (values q r missing)))',
 'e_one_short':'(lambda (a b) (multiple-value-bind (x y z) (+ a b) (values x y z)))',
 'e_zero':'(lambda (a) (handler-case (truncate a 0) (division-by-zero (e) (values (eq (arithmetic-error-operation e) (quote truncate)) (car (arithmetic-error-operands e)) (car (cdr (arithmetic-error-operands e)))))))',
 'e_ancestry':'(lambda (a) (handler-case (truncate a 0) (type-error () 90) (arithmetic-error () 7) (error () 91)))',
 'e_error':'(lambda (a) (handler-case (truncate a 0) (error () 8)))',
 'e_decline':'(lambda (a cell) (handler-case (handler-bind ((division-by-zero (lambda (e) (rplaca cell (car (arithmetic-error-operands e)))))) (truncate a 0)) (arithmetic-error () (car cell))))',
 'e_cleanup':'(lambda (a cell) (handler-case (unwind-protect (truncate a 0) (rplaca cell (+ (car cell) 1))) (division-by-zero (e) (values (car cell) (car (arithmetic-error-operands e))))))',
 'e_restart':'(lambda (a) (handler-bind ((division-by-zero (lambda (e) (invoke-restart (quote use-value) (car (arithmetic-error-operands e)))))) (restart-case (truncate a 0) (use-value (value) (values value 17)))))',
 'e_nested':'(lambda (a) (handler-case (handler-bind ((division-by-zero (lambda (e) (truncate (car (arithmetic-error-operands e)) 0)))) (truncate a 0)) (division-by-zero (e) (car (arithmetic-error-operands e)))))',
 'e_collect':'(lambda (a b) (handler-case (handler-bind ((division-by-zero (lambda (e) (* a b) (signal e)))) (truncate a 0)) (division-by-zero (e) (car (arithmetic-error-operands e)))))',
 'e_dynamic':'(lambda (a) (multiple-value-call (lambda (&rest args) (values (car args) (car (cdr args)))) (handler-case (truncate a 0) (division-by-zero () (values a 19)))) )',
 'e_type_left':'(lambda (a) (handler-case (+ a 1) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote number))))))',
 'e_type_right':'(lambda (a) (handler-case (- 1 a) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote number))))))',
 'e_type_shift':'(lambda (a) (handler-case (ash 1 a) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote integer))))))',
 'e_type_length':'(lambda (a) (handler-case (integer-length a) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote integer))))))',
 'e_type_truncate':'(lambda (a) (handler-case (truncate a 3) (type-error (e) (type-error-datum e))))',
 'e_effects':'(lambda (cell) (handler-case (+ (progn (rplaca cell 7) nil) (progn (rplaca cell 11) 1)) (type-error () (car cell))))',
 'e_pending':'(lambda (a b) (multiple-value-prog1 (truncate a b) (handler-case (truncate a 0) (division-by-zero () (* a b)))))',
 'e_keep':'(lambda (a b) (let ((x (* a b))) (setq x (+ x 1)) (values x (* x b) x)))',
 'e_shadow':'(lambda (a b) (labels ((+ (x y) (- x y)) (other (x y) (+ x y))) (other a b)))',
})
def cases():
 rows=prior.cases()
 def add(n,args):rows.append(dict(id=str(len(rows)),function=n,args=[x if isinstance(x,dict) else str(x) for x in args]))
 for a,b in [(7,3),(-7,3),(2**80+7,2**70+3),(-(2**128+11),2**65+5)]:
  for n in ['e_short','e_one_short','e_collect','e_pending','e_keep','e_shadow']:add(n,[a,b])
  for n in ['e_zero','e_ancestry','e_error','e_restart','e_nested','e_dynamic']:add(n,[a])
  for n in ['e_cleanup','e_decline']:add(n,[a,dict(cons='3')])
 for a in ['nil','t']:
  for n in ['e_type_left','e_type_right','e_type_shift','e_type_length','e_type_truncate']:add(n,[a])
 add('e_effects',[dict(cons='3')])
 return rows

review_prior_cases=cases
SOURCES.update({
 'e_review_nil':'(lambda (a b) (truncate a b))',
 'e_review_nil_short':'(lambda (a b) (multiple-value-bind (q r x) (truncate a b) (values q r x)))',
 'e_review_nil_dynamic':'(lambda (a b) (multiple-value-call (lambda (&rest xs) (values (car xs) (car (cdr xs)))) (truncate a b)))',
 'e_review_nil_effects':'(lambda (cell) (values (truncate (progn (rplaca cell 7) (car cell)) (progn (rplaca cell 9) nil)) (car cell)))',
 'e_review_priority':'(lambda (a b) (handler-case (truncate a b) (type-error (e) (values 1 (type-error-datum e) (eq (type-error-expected-type e) (quote real)))) (division-by-zero () (values 2 nil nil))))',
 'e_review_ash':'(lambda (a b) (handler-case (ash a b) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote integer))))))',
 'e_review_add':'(lambda (a b) (handler-case (+ a b) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote number))))))',
 'e_review_sub':'(lambda (a b) (handler-case (- a b) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote number))))))',
 'e_review_mul':'(lambda (a b) (handler-case (* a b) (type-error (e) (values (type-error-datum e) (eq (type-error-expected-type e) (quote number))))))',
 'e_review_ash_effects':'(lambda (cell) (handler-case (ash (progn (rplaca cell 7) nil) (progn (rplaca cell 9) t)) (type-error (e) (values (car cell) (type-error-datum e)))))',
 'e_review_wrong_operation':'(lambda (a) (handler-case (handler-case (+ a 1) (type-error (e) (arithmetic-error-operation e))) (error () 73)))',
 'e_review_wrong_operands':'(lambda (a) (handler-case (handler-case (+ a 1) (type-error (e) (arithmetic-error-operands e))) (error () 74)))',
})
def cases():
 rows=review_prior_cases()
 def add(n,args):rows.append(dict(id=str(len(rows)),function=n,args=[x if isinstance(x,dict) else str(x) for x in args]))
 for a in [0,7,-7,536870911,-536870912,2**80+7,-(2**160+3)]:
  for n in ['e_review_nil','e_review_nil_short','e_review_nil_dynamic']:add(n,[a,'nil'])
 for a,b in [('nil',0),('t',0),('nil','nil'),('t','nil'),(7,'t'),(2**80,'t'),('nil','t'),('t','t')]:add('e_review_priority',[a,b])
 for a,b in [('nil','t'),('t','nil'),('nil',7),(7,'t')]:
  for n in ['e_review_ash','e_review_add','e_review_sub','e_review_mul']:add(n,[a,b])
 for n in ['e_review_nil_effects','e_review_ash_effects']:add(n,[dict(cons='3')])
 for a in ['nil','t']:
  for n in ['e_review_wrong_operation','e_review_wrong_operands']:add(n,[a])
 return rows
