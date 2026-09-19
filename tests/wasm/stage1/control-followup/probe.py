import json,sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'd_decline':'(lambda (x p) (let ((*debugger-hook* (lambda (c h) (rplaca p (type-error-datum c)) (values)))) (rplacd p (car x))))',
 'd_decline_many':'(lambda (x p) (let ((*debugger-hook* (lambda (c h) (rplaca p (type-error-datum c)) (values '+ ' '.join(map(str,range(130)))+')))) (rplacd p (car x))))',
 'd_no_hook':'(lambda (x p) (let ((*debugger-hook* nil)) (rplacd p (car x))))',
 'd_handler_then_hook':'(lambda (x p) (let ((*debugger-hook* (lambda (c h) (rplacd p (car p)) (values 1 2 3 4)))) (handler-bind ((type-error (lambda (c) (rplaca p 271)))) (rplacd p (car x)))))',
}
def cases():
 return [dict(id=name,function=name,args=[7,'n0'],nodes=[[3,5]],bindings={},capacity=4,expected=dict(status='TYPE',values=[],nodes=[after],specials=[101,103,'unbound'])) for name,after in [('d_decline',[7,5]),('d_decline_many',[7,5]),('d_no_hook',[3,5]),('d_handler_then_hook',[271,271])]]
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
