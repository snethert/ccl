from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CORE=HERE.parent/'bootstrap-core'

def generate():
    s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
    def edit(old,new):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new)
    edit('(defun bootstrap-operator (ir)', '(defun library-prior-operator (ir)')
    edit('(defun bootstrap-numeric-call (name forms)', '(defun library-prior-call (name forms)')
    old="         (unless (and (null (third args)) (null (second (second args))) (= (length (first (second args))) 1)) (refuse :b-signal-arity))"
    edit(old,'''         (when *bootstrap-front-end*
           (unless (and (null (third args)) (null (second (second args))))
             (refuse :bootstrap-signal-spread))
           (return-from b-multiple
             (bootstrap-signal (first (second args))
                               (eq (first (ccl::acode-operands (first args))) 'error))))
'''+old)
    start=s.index('(defun bootstrap-gvector ')
    stop=s.index('(defun bootstrap-fixnum-operator ',start)
    part=s[start:stop]
    assert part.count('(i32.const 77825)')==1
    s=s[:start]+part.replace('(i32.const 77825)','(i32.const 0)')+s[stop:]
    return s+'\n'+(HERE/'operators.lisp').read_text()

def source_files(src):
    names=['level-0/l0-def.lisp','level-0/l0-pred.lisp','level-0/l0-utils.lisp','level-0/WASM32/w32-prims.lisp']
    rows={name:(ROOT/name).read_text() for name in names}
    name='level-0/l0-symbol.lisp'
    rows[name]=(ROOT/name).read_text().replace('#+(or ppc32-target x8632-target x8664-target arm-target)', '#+(or ppc32-target x8632-target x8664-target arm-target wasm32-target)')
    return rows

def proposal(src,out):
    sys.path.insert(0,str(HERE.parent/'registration'))
    import unit
    m=unit.proposal(src,out)
    arch=out/'files/compiler/WASM32/wasm32-arch.lisp'
    arch.write_text((ROOT/'compiler/WASM32/wasm32-arch.lisp').read_text()+'\n'+(HERE/'arch.lisp').read_text())
    for row in m['added']:
        if row['path']=='compiler/WASM32/wasm32-arch.lisp':row['sha256']=unit.sha(arch)
    for name,text in source_files(src).items():
        p=out/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        if (src/name).exists():m['modified'].append(dict(path=name,before=unit.sha(src/name),after=unit.sha(p)))
        else:m['added'].append(dict(path=name,sha256=unit.sha(p)))
    name='xdump/xwasm32-fasload.lisp'
    p=out/'files'/name
    text=(ROOT/name).read_text()
    assert text.count(':subdirs nil')==1
    p.write_text(text.replace(':subdirs nil', """:subdirs '("ccl:level-0;WASM32;")"""))
    next(row for row in m['added'] if row['path']==name)['sha256']=unit.sha(p)
    unit.save(out/'unit.json',m)
    return m

def runtime_files():
    return {'collector.c':(ROOT/'runtime/wasm32/collector.c').read_text()}
