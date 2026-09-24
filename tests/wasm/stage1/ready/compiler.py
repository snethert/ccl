"""READY-required lowerings over the integrated compiler; isolated build only."""
from pathlib import Path
import hashlib
import build as builder
import common as c

HERE=Path(__file__).resolve().parent
BACKEND='compiler/WASM32/wasm32-backend.lisp'
HELPER='''(defun bootstrap-make-string (forms)
  ;; CCL's MAKE-STRING calls itself with a known character element type.
  ;; As in its compiler macro, only constant keyword shapes open-code here.
  ;; Other calls use the unchanged Lisp argument checks first.
  (when (and forms (evenp (length (cdr forms))))
    (let ((initial nil) (seen nil))
      (loop for (key value) on (cdr forms) by #'cddr do
        (multiple-value-bind (name constant) (bootstrap-immediate key)
          (unless (and constant (member name '(:element-type :initial-element))
                       (not (member name seen)))
            (return-from bootstrap-make-string nil))
          (push name seen)
          (if (eq name :initial-element)
            (setq initial value)
            (multiple-value-bind (type constant) (bootstrap-immediate value)
              (unless (and constant (member type '(character base-char standard-char)))
                (return-from bootstrap-make-string nil))))))
      (b-multiple
       (make-b-raw-code :text
         (bootstrap-make-vector
          (append (list (first forms) (bootstrap-constant wasm32::subtag-simple-base-string))
                  (when initial (list initial)))))))))

'''


def generate():
    text=(c.ROOT/BACKEND).read_text()
    needle='(defun bootstrap-numeric-call (name forms)\n'
    assert text.count(needle)==1
    text=text.replace(needle,HELPER+needle)
    old="""                (bootstrap-numeric-call (ccl::afunc-name *pool-current*)
                                        (first (first args))))"""
    new="""                (if (eq (ccl::afunc-name *pool-current*) 'make-string)
                  (bootstrap-make-string (first (first args)))
                  (bootstrap-numeric-call (ccl::afunc-name *pool-current*)
                                          (first (first args)))))"""
    assert text.count(old)==1
    text=text.replace(old,new)
    start=text.index('(defun bootstrap-type-call (name forms)')
    end=text.index(';;; Fixnum operands',start)
    helper="""(defun bootstrap-type-literal (form)
  ;; TYPEP's T and NIL type specifiers have dedicated NX1 operators.
  (when (ccl::acode-p form)
    (case (ccl::acode-operator-name (ccl::acode-operator form))
      ((nil) (values nil t))
      ((t) (values t t))
      (otherwise (bootstrap-immediate form)))))

"""
    block=text[start:end]
    assert block.count('(bootstrap-immediate ')==2
    text=text[:start]+helper+block.replace('(bootstrap-immediate ', '(bootstrap-type-literal ')+text[end:]
    old_slot='''               (when (eq op 'ccl::%slot-ref)
                 (write-string (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const ~d))" answer wasm32::subtag-slot-unbound) 4) s))'''
    new_slot='''               (when (eq op 'ccl::%slot-ref)
                 (if *b-cpl-conditions*
                   (format s "(if (i32.eq (local.get ~a) (i32.const ~d)) (then (local.set ~a ~a)))"
                           answer wasm32::subtag-slot-unbound answer
                           (let ((*b-tail-position* nil) (*b-producer-target* nil))
                             (bootstrap-primary
                              (b-call (bootstrap-constant 'ccl::%slot-unbound-trap)
                                      (list (list (make-b-raw-code :text object)
                                                  (make-b-raw-code :text index)
                                                  (bootstrap-constant nil)) nil)))))
                   (write-string (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const ~d))" answer wasm32::subtag-slot-unbound) 4) s)))'''
    assert text.count(old_slot)==1
    return text.replace(old_slot,new_slot)




def install():
    if getattr(builder,'ready_proposal',False):return
    environment,prepare=builder.environment,builder.prepare
    def identity():
        return dict(**environment(),ready_compiler=dict(
            base=c.sha(c.ROOT/BACKEND),proposal=hashlib.sha256(generate().encode()).hexdigest(),
            derivation=c.sha(Path(__file__)),
            class_driver=c.sha(HERE/'numeric-files.lisp'),
            clos_methods=c.sha(HERE/'clos-methods.lisp'),
            condition_methods=c.sha(HERE/'condition-methods.lisp'),
            graph=c.sha(HERE/'graph.lisp')))
    def proposed(parent,stage):
        prepare(parent,stage)
        (stage/'driver/numeric-files.lisp').write_bytes((HERE/'numeric-files.lisp').read_bytes())
        (stage/'driver/graph.lisp').write_bytes((HERE/'graph.lisp').read_bytes())
        (stage/'driver/ready-clos-methods.lisp').write_bytes((HERE/'clos-methods.lisp').read_bytes())
        (stage/'driver/condition-methods.lisp').write_bytes((HERE/'condition-methods.lisp').read_bytes())
        c.save(stage/'driver-manifest.json',c.inventory(stage/'driver'))
        path=stage/'compiled/proposal/files'/BACKEND
        assert path.read_bytes()==(c.ROOT/BACKEND).read_bytes(), 'READY compiler base differs'
        path.write_text(generate())
        manifest=stage/'compiled/proposal/unit.json'
        record=c.read(manifest)
        row=next(r for r in record['added'] if r['path']==BACKEND)
        row['sha256']=c.sha(path);c.save(manifest,record)
    builder.environment,builder.prepare=identity,proposed
    builder.ready_proposal=True
