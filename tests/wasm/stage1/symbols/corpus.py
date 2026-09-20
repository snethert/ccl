import json,random

def hash_name(s):
 h=2166136261
 for c in s:h=((h^ord(c))*16777619)&0xffffffff
 return h

def trace():
 names=['SAME','same','','NIL','T','EXPORTED','HIDDEN','λ','名字','😀','a\x00b']
 # Deliberately retain a cluster wrapping bucket 127 to zero.
 names += [f'COLLIDE-{i}' for i in range(10000) if hash_name(f'COLLIDE-{i}')%128==127][:24]
 rows=[]
 for name in names:
  for pkg in ['A','B','KEYWORD']:
   rows.extend([[0,name,pkg],[1,name,pkg],[1,name,pkg],[0,name,pkg]])
 for pkg in ['CL','USER','A','KEYWORD']:
  for name in ['NIL','T','EXPORTED','HIDDEN','ABSENT']:rows.append([0,name,pkg])
 for name in names[:11]:rows.extend([[2,name,'A'],[2,name,'A']])
 rng=random.Random(109)
 for _ in range(120):rows.append([rng.choice([0,1]),rng.choice(names),rng.choice(['A','B','KEYWORD'])])
 return rows

def native_source(rows):
 def string(s):return '(coerce (mapcar #\'code-char \''+str([ord(c) for c in s]).replace('[','(').replace(']',')').replace(',','')+") 'string)"
 data='\n'.join(f'(list {op} {string(name)} {json.dumps(pkg)})' for op,name,pkg in rows)
 return '''(let* ((a (make-package "LL09-A" :use nil)) (b (make-package "LL09-B" :use nil))
 (cl (make-package "LL09-CL" :use nil)) (user (make-package "LL09-USER" :use nil))
 (kw (find-package "KEYWORD")) (ids (list nil t)) (next 2))
 (dolist (name (list '''+' '.join(string(n) for n in dict.fromkeys(r[1] for r in rows if r[2]=='KEYWORD'))+'''))
  (format t "INITIAL-KW ~d~%" (if (find-symbol name kw) 1 0)))
 ;; Use a private CL-shaped namespace, importing real canonical identities.
 (import '(nil t) cl) (export '(nil t) cl)
 (export (intern "EXPORTED" cl) cl) (intern "HIDDEN" cl) (use-package cl user)
 (labels ((id (s) (or (position s ids :test #'eq) (prog1 next (incf next) (setf ids (append ids (list s)))))))
 (dolist (r (list '''+data+'''))
  (destructuring-bind (op name p) r
   (let ((pkg (cond ((equal p "A") a) ((equal p "B") b) ((equal p "CL") cl) ((equal p "USER") user) (t kw))))
    (multiple-value-bind (s status) (case op (0 (find-symbol name pkg)) (1 (intern name pkg)) (2 (make-symbol name)))
     (format t "SYMBOL-ROW ~d ~d~%" (id s) (case status (:internal 1) (:external 2) (:inherited 3) (t 0)))))))
 (let ((s (make-symbol "BIND")))
  (set s 7)
  (format t "BIND-ROW ~d ~d ~d ~d~%" (symbol-value s)
   (progv (list s) (list 9) (symbol-value s))
   (progv (list s s) (list 11 13) (symbol-value s)) (symbol-value s)))))
(ccl:quit)
'''
