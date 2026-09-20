"""Native U1 bit/value witness; retain divergences instead of relabelling them."""
import json,math,shutil
from corpus import OPS,expected,value,coerce

def run(e,out,rows,driver):
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 pins=json.loads((e/'2026-09-16-stage1-1a-r2/packet.json').read_text())['files'];assert driver.sha(image)==next(r['sha256'] for r in pins if r['path']=='native/baseline.image')
 assert driver.sha(kernel)==json.loads((e/'2026-09-16-stage1-1a-r2/native/run.json').read_text())['kernel_sha256']
 driver.save(out/'native-inputs.json',{str(p.relative_to(e)):driver.sha(p) for p in [kernel,image]})
 selected=[];seen=set()
 for r in rows:
  key=json.dumps([r['op'],r['a'],r['b']],sort_keys=True)
  if key in seen:continue
  seen.add(key)
  # NaN signaling and payloads are governed by the approved explicit policy,
  # not by x86's signaling-NaN handling. Preserve the native finite/special set.
  if any(x['kind']!='integer' and math.isnan(value(x)) for x in [r['a'],r['b']]):continue
  selected.append(dict(r,expected=expected(r['op'],r['a'],r['b'],0,0)))
 def form(x):
  if x['kind']=='integer':return x['value']
  bits=int(x['bits'],16)
  return f'(ccl::host-single-float-from-unsigned-byte-32 {bits})' if x['kind']=='32' else f'(ccl::double-float-from-bits {bits>>32} {bits&0xffffffff})'
 (out/'native-input.lisp').write_text('(list\n'+'\n'.join(f'(list {OPS.index(r["op"])} {form(r["a"])} {form(r["b"])})' for r in selected)+')\n')
 source='''(ccl:set-fpu-mode :rounding-mode :nearest :invalid nil :division-by-zero nil :overflow nil :underflow nil :inexact nil)
(defun fp-printed (x)
 (cond ((null x) "NIL") ((eq x t) "T")
 ((typep x 'single-float) (let ((bits (logand #xffffffff (ccl::single-float-bits x))))
  (if (and (= (ldb (byte 8 23) bits) 255) (not (zerop (ldb (byte 23 0) bits)))) "nan" (string-downcase (format nil "~8,'0x" bits)))))
 ((typep x 'double-float) (multiple-value-bind (hi lo) (ccl::double-float-bits x)
   (let ((bits (logior (ash (logand #xffffffff hi) 32) (logand #xffffffff lo))))
    (if (and (= (ldb (byte 11 52) bits) 2047) (not (zerop (ldb (byte 52 0) bits)))) "nan" (string-downcase (format nil "~16,'0x" bits))))))
 (t (error "Unexpected result ~s" x))))
(let ((pairs (load (ccl:getenv "FLOAT_INPUT")))
      (fns (mapcar (lambda (body) (compile nil `(lambda (a b) (declare (optimize (safety 0) (speed 3))) ,body)))
                   '((+ a b) (- a b) (* a b) (/ a b) (< a b) (<= a b) (= a b) (/= a b) (>= a b) (> a b) (float a 1.0s0) (float a 1.0d0)))))
 (with-open-file (s (ccl:getenv "FLOAT_OUTPUT") :direction :output :if-exists :error)
  (dolist (row pairs)
   (handler-case (write-line (fp-printed (funcall (nth (first row) fns) (second row) (third row))) s)
    (arithmetic-error (c) (format s "condition:~a~%" (class-name (class-of c))))))))
(format t "FLOAT-NATIVE-PASS~%")
(ccl:quit)
'''
 # LOAD returns T, so read/evaluate the fixture-owned input expression directly.
 source=source.replace('(load (ccl:getenv "FLOAT_INPUT"))','(with-open-file (i (ccl:getenv "FLOAT_INPUT")) (eval (read i)))')
 (out/'native.lisp').write_text(source)
 executable=out/'dx86cl64';shutil.copyfile(kernel,executable);executable.chmod(0o755)
 driver.command([executable,'--image-name',image,'--no-init','--batch','--load',out/'native.lisp'],out/'native.log',{'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','FLOAT_INPUT':str(out/'native-input.lisp'),'FLOAT_OUTPUT':str(out/'native-results.txt')})
 got=(out/'native-results.txt').read_text().splitlines();assert len(got)==len(selected)
 differences=[]
 for r,native in zip(selected,got):
  if native!=r['expected']['value']:differences.append(dict(name=r['name'],op=r['op'],a=r['a'],b=r['b'],native=native,primitive=r['expected']['value']))
 for diff in differences:
  w=32 if diff['op']=='single' else 64 if diff['op']=='double' or '64' in [diff['a']['kind'],diff['b']['kind']] else 32
  if diff['native']=='condition:FLOATING-POINT-OVERFLOW':
   assert any(x['kind']=='integer' and coerce(x,w,True,1)[1]==20 for x in [diff['a'],diff['b']]),diff
   diff['category']='native-integer-conversion-overflow-even-masked'
  else:
   assert diff['op'] in OPS[4:10] and any(x['kind']!='integer' and math.isinf(value(x)) for x in [diff['a'],diff['b']]) and any(x['kind']=='integer' for x in [diff['a'],diff['b']]),diff
   diff['category']='native-integer-infinity-order'
 driver.save(out/'native.json',dict(status='OBSERVED',cases=len(got),equal=len(got)-len(differences),differences=differences))
 return differences
