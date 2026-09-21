from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def generate():
    s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
    def edit(old,new):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new)
    edit('(defun compile-bootstrap-form (form name links)', '(defun compile-bootstrap-form (form name links &optional env)')
    edit(':policy ccl::*default-compiler-policy*)\n      (refuse :b-no-output)', ':policy ccl::*default-compiler-policy* :env env)\n      (refuse :b-no-output)')
    edit('(defvar *bootstrap-front-end* nil)', '(defvar *bootstrap-front-end* nil)\n(defvar *bootstrap-self-call* nil)\n(defvar *bootstrap-emitted* nil)')
    edit('(let ((*bootstrap-front-end* t)', '(let ((*bootstrap-front-end* t)\n        (*b-integer-service* t)\n        (*b-float-service* t)\n        (*bootstrap-self-call* nil)\n        (*bootstrap-emitted* (make-hash-table :test #\'eq))')
    edit('(defun b-scalar (ir)\n', '(defun b-scalar (ir)\n  (when (and *bootstrap-front-end* (ccl::acode-p ir)) (setf (gethash ir *bootstrap-emitted*) t))\n')
    edit('(defun b-multiple (ir)\n', '(defun b-multiple (ir)\n  (when (and *bootstrap-front-end* (ccl::acode-p ir)) (setf (gethash ir *bootstrap-emitted*) t))\n')
    edit('(defun b-call (callee argument-list &optional local-self)\n', """(defun b-call (callee argument-list &optional local-self)
  (when (and *bootstrap-front-end* (not local-self)
             (null (second argument-list))
             (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate))
    (let ((code (bootstrap-numeric-call (first (ccl::acode-operands callee))
                                       (first argument-list))))
      (when code (return-from b-call code))))
""")
    edit('(ccl::self-call\n       (b-local-call', '(ccl::self-call\n       (when *bootstrap-front-end* (setq *bootstrap-self-call* t))\n       (b-local-call')
    edit('(getf (first modules) :dynamic-call) *bootstrap-dynamic-call*', '(getf (first modules) :dynamic-call) *bootstrap-dynamic-call*\n              (getf (first modules) :self-call) *bootstrap-self-call*\n              (getf (first modules) :operators) (bootstrap-emitted-operators)')
    edit(':p2-dispatch #()', ':p2-dispatch (make-array 1024 :initial-element nil)')
    if (HERE/'operators.lisp').exists():
        edit('(defun b-scalar-inner (ir)\n', '(defun b-scalar-inner (ir)\n  (when *bootstrap-front-end*\n    (let ((code (bootstrap-operator ir)))\n      (when code (return-from b-scalar-inner code))))\n')
        s+='\n'+(HERE/'operators.lisp').read_text()
    s=s.replace("(direct (and (symbolp name) (assoc name *b-call-links* :test #'eq)))", "(direct (and (symbolp name) (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))")
    s+='\n(setf (aref (ccl::backend-p2-dispatch *backend*) (logand ccl::operator-id-mask (ccl::%nx1-operator ccl::%ilognot))) \'bootstrap-operator)\n'
    return s

def source_files(src):
    pred=(src/'level-0/l0-pred.lisp').read_text()
    for signature,body in [
      ('(defun symbolp (thing)', '(if thing (= (the fixnum (typecode thing)) target::subtag-symbol) t)'),
      ('(defun gvectorp (x)', '(= (logand (the fixnum (typecode x)) target::fulltagmask) target::fulltag-nodeheader)'),
      ('(defun ivectorp (x)', '(= (logand (the fixnum (typecode x)) target::fulltagmask) target::fulltag-immheader)'),
      ('(defun miscobjp (x)', '(= (the fixnum (lisptag x)) target::tag-misc)')]:
        assert pred.count(signature)==1
        # Insert after any documentation string, before the native branches.
        start=pred.index(signature)+len(signature)
        end=pred.index('#+',start)
        pred=pred[:end]+'#+wasm32-target\n  '+body+'\n  '+pred[end:]
    for name,arg,body in [
      ('listp','x','(= (the fixnum (lisptag x)) target::tag-list)'),
      ('vectorp','x','(let ((code (typecode x)))\n    (or (= code target::subtag-vectorH)\n        (= code target::subtag-simple-vector)\n        (>= (the fixnum (ivector-typecode-p code)) target::min-cl-ivector-subtag)))'),
      ('arrayp','x','(let ((code (typecode x)))\n    (or (= code target::subtag-arrayH)\n        (= code target::subtag-vectorH)\n        (= code target::subtag-simple-vector)\n        (>= (the fixnum (ivector-typecode-p code)) target::min-cl-ivector-subtag)))')]:
        start=pred.index('(defun '+name+' ')
        old='('+name+' '+arg+'))'
        pos=pred.index(old,start)
        pred=pred[:pos]+'#-wasm32-target\n  '+old[:-1]+'\n  #+wasm32-target\n  '+body+')'+pred[pos+len(old):]
    utils=(src/'level-0/l0-utils.lisp').read_text()
    assert utils.count('(funcall f (lfun-vector-lfun obj))')==1
    utils=utils.replace('(funcall f (lfun-vector-lfun obj))', '(funcall f #+wasm32-target obj\n                                              #-wasm32-target (lfun-vector-lfun obj))')
    for name,arg,kind,test,adjust in [
      ('s32->u32','s32','signed-byte','(< s32 0)','(+ s32 #x100000000)'),
      ('u32->s32','u32','unsigned-byte','(>= u32 #x80000000)','(- u32 #x100000000)')]:
        start=utils.index('(defun '+name+' ')
        stop=utils.index('\n\n',start)
        original=utils[start:stop]
        split=original.index('\n')
        original=original[:split]+'\n  #-wasm32-target'+original[split:]
        original=original[:-1]+"\n  #+wasm32-target\n  (let (("+arg+" (require-type "+arg+" '("+kind+" 32))))\n    (if "+test+" "+adjust+" "+arg+")))"
        utils=utils[:start]+original+utils[stop:]
    definitions=(src/'level-0/l0-def.lisp').read_text()
    old="(defun lfunp (arg)\n  (functionp arg))"
    assert definitions.count(old)==1
    definitions=definitions.replace(old, "(defun lfunp (arg)\n  #-wasm32-target (functionp arg)\n  #+wasm32-target (= (the fixnum (typecode arg)) target::subtag-function))")
    return {'level-0/l0-def.lisp':definitions, 'level-0/l0-pred.lisp':pred, 'level-0/l0-utils.lisp':utils,
            'level-0/WASM32/w32-prims.lisp':(HERE/'w32-prims.lisp').read_text()}



def proposal(src,out):
    import sys
    sys.path.insert(0,str(HERE.parent/'registration'))
    import unit
    m=unit.proposal(src,out)
    arch=out/'files/compiler/WASM32/wasm32-arch.lisp'
    text=arch.read_text()
    assert '(defconstant subtag-function ' not in text
    arch.write_text(text+"\n(cl:in-package :wasm32)\n(cl:defconstant subtag-function 42)\n")
    for row in m['added']:
        if row['path']=='compiler/WASM32/wasm32-arch.lisp':row['sha256']=unit.sha(arch)
    for name,text in source_files(src).items():
        p=out/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        if (src/name).exists():m['modified'].append(dict(path=name,before=unit.sha(src/name),after=unit.sha(p)))
        else:m['added'].append(dict(path=name,sha256=unit.sha(p)))
    unit.save(out/'unit.json',m)
    return m

def runtime_files():
    rows={}
    for name,old,new in [
        ('collector.c','t==106||t==114||t==250','t==106||t==114||t==122||t==250'),
        ('collector-owner.mjs','[10,26,42,58,106,114,250]','[10,26,42,58,106,114,122,250]')]:
        text=(ROOT/'runtime/wasm32'/name).read_text()
        assert text.count(old)==1
        rows[name]=text.replace(old,new)
    return rows
