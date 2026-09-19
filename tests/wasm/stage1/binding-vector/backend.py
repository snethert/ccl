"""LL17 isolated proposal derived from the accepted LL19 compiler."""
import sys,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'control'))
spec=importlib.util.spec_from_file_location('ll17_control_backend',HERE.parent/'control/backend.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
replace=base.replace

def generate():
 s=base.generate()
 a=s.index('(defun b-dynamic-runtime ()');b=s.index('\n(defun b-progv',a)
 unbind=s[s.index('  (func $unbind_to',a):b]
 s=s[:a]+'(defun b-dynamic-runtime ()\n "'+(HERE/'runtime.wat').read_text()+unbind+s[b:]
 s=replace(s,"                   (svref (cons", "                   ((symbol-value set) (cons (if (member (car x) symbol-access-shadows) (car x) (if (eq (car x) 'set) '%wasm-set '%wasm-symbol-value)) (mapcar #'walk (cdr x))))\n                   (svref (cons")
 s=replace(s,"(member head '(%wasm-make-restart", "(member head '(%wasm-symbol-value %wasm-set %wasm-make-restart")
 anchor='      (ccl::call\n       (when'
 s=replace(s,anchor,'''      (ccl::call
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%wasm-symbol-value %wasm-set)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :symbol-access-spread))
         (return-from b-multiple (b-symbol-access (first (ccl::acode-operands (first args))) (first (second args)))))
       (when''')
 s=replace(s,'(condition-source-depth 0))','(condition-source-depth 0) (symbol-access-shadows nil))')
 s=replace(s,'(declare (special expanding condition-source-depth))','(declare (special expanding condition-source-depth symbol-access-shadows))')
 old="""                 ((flet labels)
                  `(,(car x) ,(mapcar (lambda (definition)
                                       `(,(first definition) ,(lambda-list (second definition))
                                         ,@(mapcar #'walk (cddr definition)))) (second x))
                    ,@(mapcar #'walk (cddr x))))"""
 new="""                 ((flet labels)
                  (let ((names (mapcar #'first (second x))))
                   `(,(car x) ,(mapcar (lambda (definition)
                     (let ((symbol-access-shadows (if (eq (car x) 'labels) (append names symbol-access-shadows) symbol-access-shadows)))
                      (declare (special symbol-access-shadows))
                      `(,(first definition) ,(lambda-list (second definition)) ,@(mapcar #'walk (cddr definition))))) (second x))
                     ,@(let ((symbol-access-shadows (append names symbol-access-shadows)))
                         (declare (special symbol-access-shadows)) (mapcar #'walk (cddr x))))))"""
 a=s.index("(defun b-expand-conditions");b=s.index("(defun ",a+1)
 s=s[:a]+replace(s[a:b],old,new)+s[b:]
 s+='\n'+(HERE/'symbols.lisp').read_text()
 return s
