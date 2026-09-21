import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'termination-exclusion';ROOT=HERE.parents[3]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def entries():
 s=(PARENT/'entries.lisp').read_text()
 for name,args in [('cancel','object &optional callback'),('lookup','object'),('drain','')]:
  s=replace(s,f'''("termination_{name}"
  (lambda ({args})
    (declare (special termination_unavailable))
    (error termination_unavailable)))''',f'''("termination_{name}" (lambda ({args}) nil))''')
 s=replace(s,'''(declare (special automatic_termination_enabled))
    (if automatic_termination_enabled (termination_drain) nil)''','''(declare (special automatic_termination_enabled termination_unavailable))
    (if automatic_termination_enabled (error termination_unavailable) nil)''')
 return s.rstrip()[:-1]+'''\n ("termination_flush" (lambda (done) (rplaca done 11)))
 ("termination_close" (lambda (done) (rplacd done (car done)) (rplaca done 22)))
 ("termination_fd_close_path"
  (lambda (stream flush close done)
   (termination_cancel stream)
   (funcall flush done)
   (funcall close done)
   (values (car done) (cdr done))))
 ("termination_file_cleanup"
  (lambda (stream flush close done)
   (unwind-protect (progn (rplaca done 7) 7)
     (termination_fd_close_path stream flush close done)))))\n'''
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module(PARENT/'derive.py','termination_r1_derive')
SCENARIOS=old.SCENARIOS+[
 ('cancel-default','termination_cancel',['object']),
 ('cancel-explicit','termination_cancel',['object','callback']),
 ('lookup-direct','termination_lookup',['object']),
 ('drain-direct','termination_drain',[]),
 ('fd-close-path','termination_fd_close_path',['object','termination_flush','termination_close','done']),
 ('file-cleanup','termination_file_cleanup',['object','termination_flush','termination_close','done']),
]
def compile_source(forms=None):
 # Keep the reference implementation independent of both the proposed empty
 # bodies and every compiled fault. Only registration/invalid enabled mode use
 # the explicitly chosen Stage 1 exclusion rather than native semantics.
 old.SCENARIOS=SCENARIOS
 s=old.compile_source(forms or entries())
 original=(PARENT/'entries.lisp').read_text()
 s=replace(s,"(native-cases '"+original+")", "(native-cases '"+entries()+")")
 s=replace(s,' (dolist (row cases)\n', ''' (setf (fdefinition 'termination_cancel) #'ccl:cancel-terminate-when-unreachable
       (fdefinition 'termination_lookup) #'ccl:termination-function
       (fdefinition 'termination_drain) #'ccl:drain-termination-queue)
 (assert (null (ccl::population.data ccl::*termination-population*)))
 (assert (null (ccl::population.termination-list ccl::*termination-population*)))
 (assert (zerop (hash-table-count ccl::*termination-functions*)))
 (dolist (row cases)
''')
 return s

def native():
 s=(PARENT/'native.lisp').read_text()
 return replace(s,'(quit)',(HERE/'native-extra.lisp').read_text()+'\n(quit)')

def check_source():
 return replace(old.check_source(),'function integer(p){if(p===N)return null;', 'function integer(p){if(p===T)return true;if(p===N)return null;')
