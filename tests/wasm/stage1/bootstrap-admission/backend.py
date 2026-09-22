"""Compiler and source proposal over the integrated backend; runtime unchanged."""
from pathlib import Path
import hashlib
import json
import shutil
from sources import derive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKET = ROOT.parent / 'ccl-evidence/2026-09-21-stage1-bootstrap-witnesses-r1/execution/compiled/proposal'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'
PRIMS = 'level-0/WASM32/w32-prims.lisp'


def generate():
    text = (ROOT / BACKEND).read_text()
    def edit(old, new):
        nonlocal text
        assert text.count(old) == 1, old[:100]
        text = text.replace(old, new)
    edit(":attributes '(:bits-per-word 32)",
         ":attributes '(:bits-per-word 32) :ff-call-expand-function (lambda (&rest args) (declare (ignore args)) (refuse :native-ffi-excluded))")
    edit("(not (consp (third args))) (equal (fifth args) '(nil nil))",
         "(not (consp (third args))) (or *bootstrap-front-end* (equal (fifth args) '(nil nil)))")
    edit('(opt (second args)) (keys (fourth args)) (rest (third args))',
         '(opt (second args)) (keys (fourth args)) (rest (third args)) (aux (fifth args))')
    edit('(append (remove nil (append (first opt)',
         '(append (first aux) (remove nil (append (first opt)')
    edit('(append *required-vars* (first opt) (third opt) (list rest) (second keys) (third keys))',
         '(append *required-vars* (first aux) (first opt) (third opt) (list rest) (second keys) (third keys))')
    edit('(b-binding-code arity opt keys rest)\n                      (let',
         '(b-binding-code arity opt keys rest)\n                      (with-output-to-string (s)\n                        (loop for var in (first aux) for init in (second aux) do\n                          (write-string (b-bind-value var (b-scalar init)) s)))\n                      (let')
    edit('(defun bootstrap-operator (ir)', (HERE / 'operators.lisp').read_text() + '\n(defun bootstrap-operator (ir)')
    edit('(case op\n      (ccl::eq', '(case op\n' + (HERE / 'operator-cases.lisp').read_text() + '      (ccl::eq')
    edit('(not (consp (third args))) (or *bootstrap-front-end*',
         '(or *bootstrap-front-end* (not (consp (third args)))) (or *bootstrap-front-end*')
    edit('(rest (third args)) (aux (fifth args))',
         '(lexpr (consp (third args))) (rest (if lexpr (car (third args)) (third args))) (aux (fifth args))')
    edit('(b-binding-code arity opt keys rest)', '(b-binding-code arity opt keys (unless lexpr rest))')
    edit('(not dynamic-parameters))) (b-multiple (sixth args))',
         '(not (or dynamic-parameters lexpr)))) (b-multiple (sixth args))')
    edit("(if dynamic-parameters (b-special-extent #'emit-body) (emit-body))",
         "(flet ((emit-arguments () (if lexpr (bootstrap-lexpr rest maximum #'emit-body) (emit-body)))) (if dynamic-parameters (b-special-extent #'emit-arguments) (emit-arguments)))")
    edit('(bootstrap-array-operator op args)', '(bootstrap-typed-access op args)')
    start=text.index('(defun bootstrap-array-operator (op args)')
    end=text.index(';;; Operands are rooted before',start)
    text=text[:start]+text[end:]
    edit('(let ((*b-tail-position* (not (or dynamic-parameters lexpr)))) (b-multiple (sixth args)))',
         '(let ((*b-tail-position* (not (or dynamic-parameters lexpr)))) (if lexpr (b-multiple (make-b-raw-code :text (b-scalar (sixth args)))) (b-multiple (sixth args))))')
    edit("""(ccl::self-call
       (when *bootstrap-front-end* (setq *bootstrap-self-call* t))
       (b-local-call 'b-self nil (first args) (second args)))""",
         """(ccl::self-call
       (or (and *bootstrap-front-end*
                (null (ccl::afunc-parent *pool-current*))
                (null (second args)) (null (second (first args)))
                (bootstrap-numeric-call (ccl::afunc-name *pool-current*)
                                        (first (first args))))
           (progn
             (when *bootstrap-front-end* (setq *bootstrap-self-call* t))
             (b-local-call 'b-self nil (first args) (second args)))))""")
    edit("((member name '(logand logior)) (bootstrap-logical-call name forms))",
         "((member name '(logand logior logxor)) (bootstrap-logical-call name forms))")
    edit('''(if (eq name 'logand) "and" "or")''',
         '(ecase name (logand "and") (logior "or") (logxor "xor"))')
    text += "\n" + (HERE / 'target-macros.lisp').read_text()
    return text


def source_files(src):
    result = {row['path']: (ROOT / row['path']).read_text()
              for key in ('added', 'modified')
              for row in json.loads((PACKET / 'unit.json').read_text())[key]
              if row['path'].startswith('level-0/')}
    result.update(derive(ROOT))
    return result


def proposal(src, out):
    shutil.copytree(PACKET, out)
    manifest = json.loads((out / 'unit.json').read_text())
    changed = {BACKEND: generate(), **source_files(src)}
    arch = 'compiler/WASM32/wasm32-arch.lisp'
    changed[arch] = arch_source()
    known = {row['path'] for row in manifest['added'] + manifest['modified']}
    for name in sorted(changed.keys() - known):
        manifest['modified'].append(dict(path=name, before=hashlib.sha256((src/name).read_bytes()).hexdigest()))
    for row in manifest['added'] + manifest['modified']:
        p = out / 'files' / row['path']
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(changed[row['path']].encode() if row['path'] in changed
                      else (ROOT / row['path']).read_bytes())
        row['sha256' if 'sha256' in row else 'after'] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / 'unit.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def runtime_files():
    return {name: (ROOT / 'runtime/wasm32' / name).read_text()
            for name in ('collector.c', 'collector-owner.mjs')}

def arch_source():
    text=(ROOT / 'compiler/WASM32/wasm32-arch.lisp').read_text()
    source=(ROOT / 'compiler/X86/X8632/x8632-arch.lisp').read_text()
    a=source.index('(defun x8632-array-type-name-from-ctype')
    b=source.index('(defun x8632-misc-byte-count',a)
    function=source[a:b].replace('x8632-array-type-name-from-ctype','wasm32-array-type-name-from-ctype').replace('target-most-negative-fixnum','wasm32::target-most-negative-fixnum').replace('target-most-positive-fixnum','wasm32::target-most-positive-fixnum')
    a=text.index('(defun wasm32-array-type-name-from-ctype')
    b=text.index('(setf (arch::target-array-type-name-from-ctype-function',a)
    return text[:a]+function+text[b:]+(HERE / 'io-constants.lisp').read_text()
