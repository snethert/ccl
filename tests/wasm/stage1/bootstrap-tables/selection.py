import hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
# Definition sites, not a claim that all are reached in the startup worklist.
FILES=['level-0/l0-def.lisp','level-0/l0-symbol.lisp','level-0/l0-misc.lisp','level-1/l1-aprims.lisp','level-1/l1-utils.lisp','level-1/l1-clos-boot.lisp','level-1/l1-clos.lisp','level-1/l1-dcode.lisp','level-1/l1-symhash.lisp','lib/foreign-types.lisp','lib/describe.lisp','lib/encapsulate.lisp','lib/edit-callers.lisp','lib/ppc-backtrace.lisp']
def selection():
 rows=[]
 for name in FILES:
  raw=(ROOT/name).read_bytes();s=raw.decode();hits=list(re.finditer(r'\(make-hash-table\s+[^()]*?:weak\s+[^()]*\)',s,re.I))
  assert len(hits)==len(re.findall(r':weak\b',s,re.I)),name
  for m in hits:
   form=m.group();test=re.search(r":test\s+#?'(eq|eql|equal)\b",form,re.I).group(1).lower()
   weak=re.search(r':weak\s+(t|:key|:value)\b',form,re.I).group(1).lower()
   assert len(re.findall(':weak',form,re.I))==1
   strong=re.sub(r'(:weak\s+)(?:t|:key|:value)\b',r'\1nil',form,flags=re.I)
   opt=lambda n,default:float(re.search(':'+n+r'\s+([.0-9]+)',form).group(1)) if re.search(':'+n+r'\s+([.0-9]+)',form) else default
   line=s.count('\n',0,m.start())+1
   rows.append(dict(id=f'{name}:{line}',source=name,source_sha256=hashlib.sha256(raw).hexdigest(),offset=m.start(),form=form,strong=strong,test=test,weak='value' if weak==':value' else 'key',size=int(opt('size',60)),rehashSize=opt('rehash-size',1.5),rehashThreshold=opt('rehash-threshold',.85)))
 assert len(rows)==21
 return rows

def native_source(rows):
 # Forms are checked-in U1 source, evaluated only in the disposable pinned image.
 text=['(in-package :ccl)']
 for i,r in enumerate(rows):
  text.append(f'''(let* ((old {r['form']}) (new {r['strong']}) (key (cons 1 2)) (value (cons 3 4)))
 (assert (equal (hash-table-test old) (hash-table-test new)))
 (assert (equal (hash-table-weak-p old) :{r['weak']}))
 (assert (null (hash-table-weak-p new)))
 (assert (= (hash-table-rehash-size old) (hash-table-rehash-size new)))
 (assert (= (hash-table-rehash-threshold old) (hash-table-rehash-threshold new)))
 (setf (gethash key new) value)
 (gc)
 (assert (eq (gethash key new) value))
 ;; Equal-but-distinct keys distinguish the retained equality predicate.
 (let ((a (copy-seq "identity")) (b (copy-seq "identity")))
  (setf (gethash a new) 19)
  (assert (eq (nth-value 1 (gethash b new)) {'t' if r['test']=='equal' else 'nil'})))
 (let ((a (parse-integer (copy-seq "1237940039285380274899124241"))) (b (parse-integer (copy-seq "1237940039285380274899124241"))))
  (assert (not (eq a b))) (setf (gethash a new) 23)
  (assert (eq (nth-value 1 (gethash b new)) {'nil' if r['test']=='eq' else 't'})))
 (format t "STRONG-ROW {i} ~a ~a~%" (hash-table-test new) (hash-table-weak-p new)))''')
 text.extend(['(format t "STRONG-NATIVE-PASS~%")','(quit)'])
 return '\n'.join(text)+'\n'
