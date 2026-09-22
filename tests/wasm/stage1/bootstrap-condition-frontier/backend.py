"""Condition construction over the pending, pinned introspection proposal."""
from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('introspection_backend',HERE.parent/'bootstrap-introspection/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
base_generate=prior.generate
BACKEND=prior.BACKEND;ARCH=prior.ARCH;PACKET=prior.PACKET
arch=prior.arch;runtime_files=prior.runtime_files
base_source_files=prior.source_files
def source_files(root):
 result=base_source_files(root)
 for name,functions in json.loads((HERE/'exclusions.json').read_text()).items():
  text=result.get(name,(root/name).read_text())
  for function in functions:
   marker='(defun '+function+' '
   assert text.count(marker)==1,(name,function)
   text=text.replace(marker,'#-wasm32-target\n'+marker)
  result[name]=text
 return result
# Each tuple binds the distinct class bit, full native CPL mask and slot order.
CLASSES=[
 ('stream-error',20,7|1<<20,['stream']),
 ('end-of-file',21,7|1<<20|1<<21,['stream']),
 ('file-error',22,7|1<<22,['pathname','error-type']),
 ('package-error',23,7|1<<23,['package']),
 ('ccl::simple-package-error',24,15|1<<23|1<<24,['format-control','format-arguments','package']),
 ('ccl::stream-is-closed-error',25,7|1<<20|1<<25,['stream']),
 ('ccl::bad-slot-type',26,39|1<<26,['datum','expected-type','format-control','slot-definition','instance']),
 ('ccl::inactive-restart',27,71|1<<27,['restart-name']),
 ('ccl::restart-failure',28,71|1<<28,['restart'])]
def replace(s,a,b,count=1):
 assert s.count(a)==count,(a,s.count(a));return s.replace(a,b)
def generate():
 s=base_generate()
 s=replace(s,'(defun b-condition-mask (type)',
    '(defun b-condition-mask (type)\n  (when (and (not *bootstrap-front-end*) (member type \'('+ ' '.join(c[0] for c in CLASSES)+'))) (refuse :b-condition-type))')
 s=replace(s,'(control-error . 64) (warning . 128) (simple-warning . 256))))',
 '(control-error . 64) (warning . 128) (simple-warning . 256)'+''.join(' ('+name+' . '+str(1<<bit)+')' for name,bit,mask,slots in CLASSES)+')))')
 s=replace(s,'floating-point-underflow floating-point-inexact))\n        (format s',
    'floating-point-underflow floating-point-inexact '+ ' '.join(c[0] for c in CLASSES)+'))\n        (format s')
 start=s.index('(defun bootstrap-condition (mask values)');end=s.index('(defun bootstrap-immediate',start)
 s=s[:start]+(HERE/'constructor.lisp').read_text()+'\n'+s[end:]
 old='(division-by-zero 196636 :operation :operands))))'
 rows=''.join('\n                                  ('+name+' '+str(mask*4)+' '+ ' '.join(':'+x for x in slots)+')' for name,bit,mask,slots in CLASSES)
 s=replace(s,old,'(division-by-zero 196636 :operation :operands)'+rows+')))')
 # Omitted new-class initargs retain the defaults supplied by the class owner.
 s=replace(s,"(if (member key '(:format-control :datum :expected-type))\n                                 ","(if (> (second schema) 2162716) nil\n                                 (if (member key '(:format-control :datum :expected-type))\n                                 ")
 s=replace(s,'"(i32.const 83)" "(i32.const 77825)")))','"(i32.const 83)" "(i32.const 77825)"))))')
 # Extend only the bootstrap entry's registry and bounded slot count.
 marker=' (let ((s (prior-float-b-condition-runtime)))'
 s=replace(s,marker,''' (let ((s (prior-float-b-condition-runtime)))
  (when *bootstrap-front-end*
    (setq s (with-output-to-string (out)
              (loop with old = "(i32.gt_u (local.get $n) (i32.const 4))"
                    for start = 0 then (+ end (length old))
                    for end = (search old s :start2 start) do
                (write-string s out :start start :end end)
                (unless end (return))
                (write-string "(i32.gt_u (local.get $n) (i32.const 5))" out))))
    (setq s (numeric-text s "(i32.ne (local.get $n) (i32.const 15))"
                             "(i32.and (i32.ne (local.get $n) (i32.const 28)) (i32.ne (local.get $n) (i32.const 15)))")))''')
 # Reader cases belong in the existing dispatcher.
 s=replace(s,'simple-condition-format-control simple-condition-format-arguments))\n           (bootstrap-condition-reader',
             'simple-condition-format-control simple-condition-format-arguments\n                         stream-error-stream file-error-pathname package-error-package))\n           (bootstrap-condition-reader')
 start=s.index('(defun bootstrap-condition-reader');end=s.index('(defun bootstrap-character',start)
 s=s[:start]+(HERE/'readers.lisp').read_text()+'\n'+s[end:]
 return s

def proposal(src,out):
 prior.generate=generate
 prior.source_files=source_files
 return prior.proposal(src,out)
