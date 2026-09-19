import sys
from pathlib import Path
import conditions
conditions.SOURCES={'identity_probe':'(lambda (x) x)'}
conditions.cases=lambda:[]
conditions.REFUSALS=[
 ('prog2-arity','(lambda () (prog2 1))'),
 ('duplicate-tag','(lambda () (tagbody a a))'),
 ('missing-tag','(lambda () (tagbody (go nowhere)))'),
 ('invalid-tag','(lambda () (tagbody #\\a))'),
 ('cross-function-go','(lambda () (tagbody a (funcall (lambda () (go a)))))'),
 ('local-function-go','(lambda () (tagbody a (flet ((f () (go a))) (f))))'),
 ('go-arity','(lambda () (tagbody a (go a b)))'),
 ('escaping-tag','(lambda () (tagbody a) (go a))'),
]
if __name__=='__main__':conditions.compile_conditions(*map(Path,sys.argv[1:4]))
