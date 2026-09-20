SOURCES={
 'n_add':'(lambda (a b) (+ a b))', 'n_sub':'(lambda (a b) (- a b))',
 'n_mul':'(lambda (a b) (* a b))','n_ash':'(lambda (a b) (ash a b))',
 'n_length':'(lambda (a) (integer-length a))','n_truncate':'(lambda (a b) (truncate a b))',
 'n_nested':'(lambda (a b) (+ (* a b) (- a b)))',
 'n_mv':'(lambda (a b) (multiple-value-bind (q r) (truncate a b) (values r q (+ q r))))',
 'n_scalar':'(lambda (a b) (+ (truncate a b) 7))',
 'n_cleanup':'(lambda (a b cell) (multiple-value-bind (q r) (unwind-protect (truncate a b) (rplaca cell (+ (car cell) 1))) (values q r (car cell))))',
 'n_effects':'(lambda (cell) (values (+ (progn (rplaca cell (+ (car cell) 1)) (car cell)) (progn (rplaca cell (* (car cell) 2)) (car cell))) (car cell)))',
 'n_capture':'(lambda (a b) (let ((f (lambda (x) (+ a x)))) (funcall f (* a b))))',
 'n_local':'(lambda (a b) (flet ((+ (x y) (- x y))) (+ a b)))',
 'n_local_body':'(lambda (a b) (flet ((+ (x y) (+ x y))) (+ a b)))',
 'n_default':'(lambda (a &optional (b (+ a 1))) (* a b))',
 'n_dynamic':'(lambda (a b) (multiple-value-call (lambda (&rest args) (values (car args) (car (cdr args)) (car (cdr (cdr args))))) (truncate a b) (values (+ a b))))',
 'n_retained':'(lambda (a b) (multiple-value-prog1 (truncate a b) (* a b)))',
 'n_throw':'(lambda (a b) (catch 7 (throw 7 (truncate a b))))',
 'n_alias':'(lambda (a) (+ a (progn (* a a) a)))',
 'n_pending':'(lambda (a b) (values a (* a b) a))',
}
SOURCES['n_literal']='(lambda () (* '+str((1<<256)+7)+' '+str((1<<256)+13)+'))'
def cases():
 import random
 rows=[]
 def add(name,args):rows.append(dict(id=str(len(rows)),function=name,args=[x if isinstance(x,dict) else str(x) for x in args]))
 for a,b in [(0,0),(1,-1),(7,3),(-7,3),(7,-3),(-536870912,-1),(536870911,1),(2**29,2**29+1),(-(2**64+3),2**32+7),(2**127+5,-(2**64+1)),(2**255-1,2**129+17)]:
  for n in ['n_add','n_sub','n_mul','n_length','n_default']:
   add(n,[a] if n in ['n_length','n_default'] else [a,b])
  for n in ['n_truncate','n_nested','n_mv','n_scalar','n_capture','n_local','n_local_body','n_dynamic','n_retained','n_throw','n_pending']:
   if b:add(n,[a,b])
  add('n_alias',[a])
 for a in [0,1,-1,536870911,-536870912,2**128+1,-(2**128+1)]:
  for b in [-2**70,-1024,-32,-31,-1,0,1,29,30,32,130]:add('n_ash',[a,b])
 rng=random.Random(16161)
 for i in range(48):
  a=rng.getrandbits(rng.randrange(1,513))*rng.choice([-1,1]);b=rng.getrandbits(rng.randrange(1,257))*rng.choice([-1,1]) or 1
  add(['n_add','n_sub','n_mul','n_truncate'][i%4],[a,b])
 add('n_effects',[dict(cons='1')])
 add('n_effects',[dict(cons=str(2**80+3))])
 add('n_cleanup',[2**130+17,2**65+7,dict(cons=str(2**90+5))])
 add('n_literal',[])
 return rows
