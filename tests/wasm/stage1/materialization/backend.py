"""Opt-in canonical templates; legacy entry points retain their exact text."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def generate():
 s=(ROOT/'compiler/wasm32/wasm32-backend.lisp').read_text()
 s=replace(s,'(defvar *b-callable-metadata* nil)', '''(defvar *b-callable-metadata* nil)
;; D2 template mode changes only the imported memory's shared bit. It is
;; dynamically bound around compilation, including every nested module.
(defvar *wasm32-template-memory* nil)''')
 # Both legacy leaf and typed primitive FORMAT strings share this prefix.
 a='(memory 1 32769 shared))';b='(memory 1 32769~a))'
 assert s.count(a)==3
 # The B emitter uses WRITE-STRING, so give it its own FORMAT argument.
 start=s.index('             (write-string "(module (type $b_entry')
 end=s.index('" s)',start)+4
 old=s[start:end]
 new=old.replace('(write-string ', '(format s ').replace(a,b).replace('" s)', '" (if *wasm32-template-memory* "" " shared"))')
 s=replace(s,old,new)
 assert s.count(a)==2
 s=s.replace(a,b)
 s=replace(s,'"env" "memory" "env" "tcr"','"env" "memory" (if *wasm32-template-memory* "" " shared") "env" "tcr"')
 s=replace(s,'"env" "memory" "env" "slots"','"env" "memory" (if *wasm32-template-memory* "" " shared") "env" "slots"')
 return s
if __name__=='__main__':print(generate(),end='')
