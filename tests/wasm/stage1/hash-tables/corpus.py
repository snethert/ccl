"""Deterministic operation trace; expected values come from native CCL."""
import random

def trace():
    r=random.Random(0x18b)
    rows=[]
    def emit(*x):rows.append(list(x))
    # Distinct equal conses plus NIL, T and two immediate fixnums.
    for k in range(24):emit('set',k,(k+7)%40)
    emit('set',40,4);emit('set',41,5);emit('set',42,6);emit('set',43,7)
    for round in range(12):
        emit('get',round%24,40)  # leave a live cache across movement
        emit('gc')
        if round%3==0:emit('gc')
        emit('set',round%24,(round+13)%40) # replacement via the former cache
        emit('count')
        for k in range(44):emit('get',k,40)
        emit('get',(round+3)%24,40);emit('del',(round+3)%24)
        emit('get',(round+3)%24,41);emit('del',(round+3)%24);emit('count')
        emit('set',(round+3)%24,(round+19)%40)
        for i in range(35):
            op=r.choice(['set','get','get','del','count']);k=r.randrange(44)
            emit(op,*([] if op=='count' else [k] if op=='del' else [k,r.randrange(44)]))
        emit('count')
    # Empty tables, tombstones, repeated deletion and rebuilding.
    for k in range(44):emit('del',k)
    emit('gc');emit('count')
    for k in range(44):emit('get',k,41)
    for k in reversed(range(44)):emit('set',k,(k+1)%44)
    emit('gc')
    for k in range(44):emit('get',k,40)
    emit('count')
    return rows

def native_source(rows):
    forms='\n'.join('('+r[0]+' '+ ' '.join(map(str,r[1:]))+')' for r in rows)
    return '''(in-package :cl-user)
(let* ((keys (concatenate 'vector (loop repeat 40 collect (cons 7 nil)) (vector nil t 0 -1)))
       (table (make-hash-table :test 'eq))
       (rows '(%s)))
 (labels ((identity (v) (or (position v keys :test #'eq) (error "unexpected native value"))))
  (dolist (row rows)
   (let* ((op (first row)) (key (and (second row) (aref keys (second row))))
          (value (and (third row) (aref keys (third row)))))
    (case op
     (set (format t "HASH-ROW ~d~%%" (identity (setf (gethash key table) value))))
     (get (multiple-value-bind (v p) (gethash key table value) (format t "HASH-ROW ~d ~d~%%" (identity v) (if p 1 0))))
     (del (format t "HASH-ROW ~d~%%" (if (remhash key table) 1 0)))
     (count (format t "HASH-ROW ~d~%%" (hash-table-count table)))
     (gc (ccl:gc) (format t "HASH-ROW -1~%%")))))))
(ccl:quit)
'''%forms
