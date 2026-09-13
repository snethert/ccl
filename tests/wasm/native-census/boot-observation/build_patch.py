#!/usr/bin/env python3
"""Generate early-boot observation only, from pristine U1 source blobs."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
_spec = importlib.util.spec_from_file_location('boot_patch_form_reader', HERE.parent / 'rich-observation/build_patch.py')
_reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reader)
form_end = _reader.form_end

U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
FILES = ('level-0/l0-def.lisp', 'level-0/nfasload.lisp', 'level-1/level-1.lisp')
STATE = "(and (boundp '*boot-census-state*) (%sym-global-value '*boot-census-state*))"


def cell(index, root='census-state'):
    for _ in range(index): root = '(%cdr ' + root + ')'
    return root


def emit(kind, values='nil'):
    # No special bindings, callbacks, hash tables, printing or locking in the
    # early window. Only the owner TCR writes the list. Any foreign writer sets
    # a sticky refusal flag; export refuses that observation.
    return f'''(let* ((census-state {STATE}))
  (when (and census-state (%car census-state))
    (if (eql (%current-tcr) (%car {cell(3)}))
      (let* ((census-sequence (1+ (%car {cell(1)}))))
        (%rplaca {cell(1)} census-sequence)
        (%rplaca {cell(2)} (cons (list census-sequence :{kind} {values}) (%car {cell(2)}))))
      (%rplaca {cell(4)} t))))'''


def first_binding(name, old):
    # Separate first-touch checkpoint. It lets the replay check the first
    # transition too, even if that binding is overwritten later in startup.
    # Use primitive cons traversal: no hash table or replaceable lookup helper
    # is called inside a binding removal's unsafe interval.
    return f'''(let* ((census-state {STATE}))
  (when (and census-state (%car census-state)
             (eql (%current-tcr) (%car {cell(3)})))
    (let* ((census-bindings (%car {cell(6)})) (census-scan census-bindings))
      (tagbody census-find-binding
        (if (null census-scan)
          (progn (%rplaca {cell(6)} (cons (cons {name} {old}) census-bindings))
                 (go census-binding-done)))
        (if (eq {name} (%car (%car census-scan))) (go census-binding-done))
        (setq census-scan (%cdr census-scan))
        (go census-find-binding)
        census-binding-done))))'''


def build():
    original = {p: subprocess.check_output(['git', '-C', str(ROOT), 'show', U1 + ':' + p]) for p in FILES}
    texts = {p: b.decode() for p, b in original.items()}
    def replace(path, old, new):
        if texts[path].count(old) != 1: raise ValueError('nonunique U1 patch site: ' + path + ': ' + old[:50])
        texts[path] = texts[path].replace(old, new)

    path = 'level-0/l0-def.lisp'
    store = '(setf (%svref (symptr->symvector (%symbol->symptr fname)) target::symbol.fcell-cell) def)'
    old_cell = '(%svref (symptr->symvector (%symbol->symptr fname)) target::symbol.fcell-cell)'
    replace(path, store, '(let* ((census-old ' + old_cell + ')) (multiple-value-prog1 ' + store + '\n' +
            first_binding('fname', 'census-old') + '\n' + emit('binding-installed', '(list fname census-old def)') + '))')
    store = '(setf (%svref symvec target::symbol.fcell-cell) unbound)'
    replace(path, store, first_binding('sym', 'old') + '\n' + emit('binding-removing', '(list sym old unbound)') + '\n' + store)

    path = 'level-0/nfasload.lisp'
    queued = '''(dolist (f (prog1 *xload-cold-load-functions* (setq *xload-cold-load-functions* nil)))
        (funcall f))'''
    replace(path, queued, '''(%set-sym-global-value '*boot-census-state*
        (list t 0 nil (%current-tcr) nil *xload-cold-load-functions* nil))
      ''' + emit('boot-start', '(list *xload-cold-load-functions* *xload-startup-file*)') + '''
      (dolist (f (prog1 *xload-cold-load-functions* (setq *xload-cold-load-functions* nil)))
        ''' + emit('cold-enter', '(list f)') + '''
        (funcall f)
        ''' + emit('cold-return', '(list f)') + ')')
    invoke = '''(funcall (svref (faslstate.fasldispatch s) (logand op (lognot (ash 1 $fasl-epush-bit)))) 
           s)'''
    context = '(list (faslstate.faslfname s) (1- (%fasl-get-file-pos s)) op census-reader (faslstate.fasldispatch s))'
    replace(path, invoke, '''(let* ((census-reader (svref (faslstate.fasldispatch s)
                           (logand op (lognot (ash 1 $fasl-epush-bit))))))
    (if (= (logand op (lognot (ash 1 $fasl-epush-bit))) $fasl-lfuncall)
      (progn ''' + emit('reader-enter', context) + '''
        (multiple-value-prog1 (funcall census-reader s)
          ''' + emit('reader-return', '(list census-reader)') + '''))
      (funcall census-reader s)))''')
    invoke = '(%epushval s (funcall fun))'
    replace(path, invoke, '''(progn ''' + emit('call-enter', '(list fun)') + '''
       (let* ((census-value (funcall fun)))
         ''' + emit('call-return', '(list fun)') + '''
         (%epushval s census-value)))''')
    text = texts[path]; start = text.index('(defun %fasload '); end = form_end(text, start)
    args = text.index('(', start + len('(defun %fasload ')); body = form_end(text, args)
    texts[path] = (text[:body] + '\n' + emit('load-enter', '(list string table)') +
                   '\n(multiple-value-prog1 (progn' + text[body:end - 1] + ')\n' +
                   emit('load-return', '(list string table)') + '))' + text[end:])
    path = 'level-1/level-1.lisp'
    # Keep one load-time form at the original TOPLEVEL site. Separate forms
    # allocate extra compiler-generated initializer names and shift gensyms
    # in subsequently compiled, otherwise unchanged files.
    replace(path, '  (toplevel))', '''  (let* ((census-handoff-state ''' + STATE + '''))
    ''' + emit('handoff') + '''
    (when census-handoff-state (%rplaca census-handoff-state nil))
    (toplevel)))''')
    patch = ''.join(''.join(difflib.unified_diff(original[p].decode().splitlines(True), texts[p].splitlines(True),
                       fromfile='a/' + p, tofile='b/' + p)) for p in FILES)
    (HERE / 'observation.patch').write_text(patch)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = {'version': 1, 'source_revision': U1, 'patch_sha256': sha(patch.encode()),
                'scope': 'Early boot owner-thread observation; no compiler emission or runtime behavior changes.',
                'files': [{'path': p, 'original_sha256': sha(original[p]), 'observed_sha256': sha(texts[p].encode())} for p in FILES]}
    (HERE / 'patch.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Generated reversible three-file boot observation patch.')


if __name__ == '__main__': build()
