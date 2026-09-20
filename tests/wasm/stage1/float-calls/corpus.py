SOURCES={
 'f_add':'(lambda (a b) (+ a b))','f_sub':'(lambda (a b) (- a b))','f_mul':'(lambda (a b) (* a b))','f_div':'(lambda (a b) (/ a b))',
 **{f'f_{n}':f'(lambda (a b) ({op} a b))' for n,op in [('lt','<'),('le','<='),('eq','='),('ne','/='),('ge','>='),('gt','>')]},
 'f_single':'(lambda (a b) (float a 1.0s0))','f_double':'(lambda (a b) (float a 1.0d0))',
 'f_nested':'(lambda (a b) (+ (* a b) (- a b)))',
 'f_mv':'(lambda (a b) (multiple-value-prog1 (values (+ a b) (* a b)) (float a 1.0d0)))',
 'f_capture':'(lambda (a b) (let ((x (+ a b))) (funcall (lambda () (+ x (* a b))))))',
 'f_special':'(lambda (a b) (let ((dyn_a (+ a b))) (declare (special dyn_a)) (+ dyn_a (* a b))))',
 'f_cleanup':'(lambda (a b) (unwind-protect (values (+ a b) (- a b)) (* a b)))',
 'f_throw':'(lambda (a b) (catch t (throw t (values (+ a b) (* a b)))))',
 'f_shadow':'(lambda (a b) (flet ((+ (x y) (values y x))) (+ a b)))',
 'f_identity':'(lambda (a b) (values (eq (float a 1.0d0) a) (eq (float b 1.0s0) b)))',
 'f_short':'(lambda (a b) (multiple-value-bind (x y) (+ a b) (values x y)))',
}
for op in ['add','sub','mul','div','single','double']:
 body={'add':'(+ a b)','sub':'(- a b)','mul':'(* a b)','div':'(/ a b)','single':'(float a 1.0s0)','double':'(float a 1.0d0)'}[op]
 SOURCES['h_'+op]='(lambda (a b) (handler-case '+body+' (floating-point-invalid-operation () 101) (division-by-zero () 102) (floating-point-overflow () 104) (floating-point-underflow () 108) (floating-point-inexact () 116) (type-error () 132)))'
SOURCES['h_restart']='(lambda (a b) (handler-bind ((division-by-zero (lambda (c) (invoke-restart :use)))) (restart-case (/ a b) (:use () (+ a 2.0d0)))))'
SOURCES['h_collect']='(lambda (a b) (handler-case (/ a b) (arithmetic-error (c) (let ((ignored (* a 2.0d0))) (values (eq (arithmetic-error-operation c) (quote /)) (car (arithmetic-error-operands c)))))))'
# Datum is checked against the operand that failed; all source arguments finish first.
SOURCES['h_type']='(lambda (a b) (handler-case (+ a b) (type-error (c) (values (eq (type-error-datum c) a) (eq (type-error-expected-type c) (quote number))))))'
def cases():
 rows=[]
 def add(f,a,b,mask=7,safe=1,policy=False):rows.append(dict(id=len(rows),function=f,args=[a,b],mask=mask,safe=safe,policy=policy))
 inputs=[['1.5d0','2.25d0'],['1.5s0','-2.25s0'],['7','1.5d0'],['1208925819614629174706183','3.0s0'],['-0.0d0','0.0d0'],['1.0d-300','2.0d0']]
 for f in SOURCES:
  if f.startswith('h_'):continue
  for a,b in inputs:
   if f=='f_div' and b in ['0.0d0']:continue
   for mask in [0,7]:add(f,a,b,mask)
 for f in ['f_add','f_sub','f_mul']:
  for a,b in [('7','9'),('536870911','1'),('1208925819614629174706183','-7')]:add(f,a,b)
 for a in ['-4.67d-95','1.401298464324817d-45','1.7976931348623157d308','-0.0d0','340282366920938463463374607431768211456','179769313486231590772930519078902473361797697894230657273430081157732675805500963132708477322407536021120113879871393357658789768814416622492847430639474124377767893424865485276302219601246094119453082952085005768838150682342462881473913110540827237163350510684586298239947245938479716304835356329624224137216']:
  for mask in [0,7,31]:
   add('h_single',a,'0',mask,policy=True);add('h_double',a,'0',mask,policy=True)
 for f,a,b in [('h_div','1.0d0','0.0d0'),('h_div','0.0d0','0.0d0'),('h_mul','1.7976931348623157d308','2.0d0'),('h_div','1.0d0','3.0d0'),('h_mul','1.401298464324817s-45','0.5s0')]:
  for mask in [0,1,2,4,8,16,7,31]:
   for safe in [0,1]:add(f,a,b,mask,safe,True)
 add('h_restart','7.0d0','0.0d0');add('h_collect','7.0d0','0.0d0');add('h_type','nil','7');add('h_type','(cons 7 nil)','9')
 for n in [(1<<1024)-1,1<<1024,(1<<1024)+1,1<<1025]:
  for sign in [-1,1]:
   value=str(sign*n);inf='(ccl::double-float-from-bits '+str(0x7ff00000 if sign>0 else 0xfff00000)+' 0)'
   for op in ['lt','le','eq','ne','ge','gt']:
    add('f_'+op,value,inf);add('f_'+op,inf,value)
 return rows
