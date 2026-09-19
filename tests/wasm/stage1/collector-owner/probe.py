import sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={'make':'(lambda (a b) (cons a b))','read_pair':'(lambda (x) (values (car x) (cdr x)))'}
def cases():
 return [dict(id='make',function='make',args=[7,11],nodes=[],bindings={},capacity=4,expected=dict(status='RETURN',values=['n0'],nodes=[[7,11]],specials=[101,103,'unbound'])),dict(id='read_pair',function='read_pair',args=['n0'],nodes=[[7,11]],bindings={},capacity=4,expected=dict(status='RETURN',values=[7,11],nodes=[[7,11]],specials=[101,103,'unbound']))]
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
