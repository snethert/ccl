#!/usr/bin/env python3
"""Derive the removable observation patch from pinned U1, without editing the checkout."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
FILES = ('level-0/l0-def.lisp', 'level-0/nfasload.lisp', 'level-1/l1-readloop.lisp',
         'compiler/nx.lisp', 'compiler/nx0.lisp', 'compiler/nx2.lisp',
         'compiler/vinsn.lisp', 'lib/nfcomp.lisp', 'lib/dumplisp.lisp')
GUARD = "(and (boundp '*startup-census-hook*) *startup-census-hook*)"


def hook(phase, value):
    return f'(when {GUARD} (funcall *startup-census-hook* :{phase} {value}))'


def paired(expression, entry, returned, aborted, before, after=None):
    return ('(let ((census-observation-returned nil))\n  ' + hook(entry, before) +
            '\n  (unwind-protect\n      (multiple-value-prog1\n          ' + expression +
            '\n        ' + hook(returned, after or before) + '\n        (setq census-observation-returned t))\n    '
            '(unless census-observation-returned\n      ' + hook(aborted, before) + ')))')


def form_end(text, start):
    """Find selected source forms; account for strings, comments and character literals."""
    depth, block, pos = 0, 0, start
    while pos < len(text):
        if text.startswith('#|', pos):
            block += 1; pos += 2; continue
        if block:
            if text.startswith('|#', pos): block -= 1; pos += 2
            else: pos += 1
            continue
        char = text[pos]
        if char == ';':
            end = text.find('\n', pos); pos = len(text) if end < 0 else end + 1; continue
        if char == '"':
            pos += 1
            while pos < len(text):
                if text[pos] == '\\': pos += 2
                elif text[pos] == '"': pos += 1; break
                else: pos += 1
            continue
        if text.startswith('#\\', pos):
            pos += 3
            while pos < len(text) and not text[pos].isspace() and text[pos] not in '()': pos += 1
            continue
        if char == '(': depth += 1
        if char == ')':
            depth -= 1
            if depth == 0: return pos + 1
        pos += 1
    raise ValueError('unterminated selected source form')


def build():
    original = {p: subprocess.check_output(['git', '-C', str(ROOT), 'show', U1 + ':' + p]) for p in FILES}
    with tempfile.TemporaryDirectory(prefix='ccl-rich-patch-') as directory:
        tree = Path(directory)
        for name, data in original.items():
            p = tree / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        # Retain the reviewed three-file observation hooks and extend their data.
        subprocess.run(['git', 'apply', str(HERE.parent / 'observation.patch')], cwd=tree, check=True)
        texts = {name: (tree / name).read_text() for name in FILES}
    def replace(path, old, new):
        if texts[path].count(old) != 1:
            raise ValueError('source recipe context is not unique: ' + path + ': ' + old[:55])
        texts[path] = texts[path].replace(old, new)
    def wrap(path, name, payload):
        text = texts[path]
        start = text.index('(defun ' + name + ' ')
        end = form_end(text, start)
        args_start = text.index('(', start + len('(defun ' + name))
        body = form_end(text, args_start)
        # Declarations must remain at the beginning of the function body.
        while text[body:].lstrip().startswith('(declare '):
            body = form_end(text, text.index('(declare ', body))
        wrapped = (text[start:body] + '\n  ' + hook('lower-enter', payload) +
                   '\n  (unwind-protect\n      (progn' + text[body:end - 1] + ')\n    ' +
                   hook('lower-leave', payload) + '))')
        texts[path] = text[:start] + wrapped + text[end:]

    replace('compiler/nx.lisp', '(let* ((f (afunc-lfun def)))',
            '(let* ((f (afunc-lfun def)))\n            ' + hook('function-materialized', 'def'))
    old = '(setf (%svref (symptr->symvector (%symbol->symptr fname)) target::symbol.fcell-cell) def)'
    replace('level-0/l0-def.lisp', old,
            '(multiple-value-prog1\n      ' + old + '\n      ' +
            hook('binding-installed', '(list fname def)') + ')')
    old = '(setf (%svref symvec target::symbol.fcell-cell) unbound)'
    # No observer is called in the unbound interval: the victim may be any
    # helper used by logging itself. This event witnesses removal intent just
    # before the primitive store, not completed removal.
    replace('level-0/l0-def.lisp', old, hook('binding-removing', '(list sym old unbound)') + '\n    ' + old)

    # Inline observation at the three real hook calls. Adding a DEFUN to the
    # rebuilt sources consumes compiler gensyms and changes later FASL names.
    # Explicit lexical bindings preserve argument evaluation and all values
    # without adding a top-level definition or changing compilation inputs.
    sites = [
        ('level-1/l1-readloop.lisp', '(constantly expansion)', 'sym'),
        ('level-1/l1-readloop.lisp', 'fn', 'form'),
        ('compiler/nx0.lisp', 'expander', 'form')]
    for path, expander, form in sites:
        text = texts[path]; prefix = '(funcall *macroexpand-hook*'
        starts = [i for i in range(len(text)) if text.startswith(prefix, i)]
        matches = [(i, form_end(text, i)) for i in starts
                   if ' '.join(text[i:form_end(text, i)].split()) ==
                   f'(funcall *macroexpand-hook* {expander} {form} env)']
        if len(matches) != 1: raise ValueError('macro hook call-site inventory changed')
        start, end = matches[0]
        bindings = ('(let ((census-hook *macroexpand-hook*) (census-expander ' + expander +
                    ') (census-form ' + form + ') (census-env env) (census-results nil))\n  ')
        values = '(list census-hook census-expander census-form census-env'
        body = paired('(progn (setq census-results (multiple-value-list (funcall census-hook census-expander census-form census-env))) (values-list census-results))',
                      'expander-enter', 'expander-return', 'expander-abort', values + ')',
                      values + ' census-results)')
        texts[path] = text[:start] + bindings + body + ')' + text[end:]

    old = '''(funcall (compile-named-function
                lambda
                :compile-code-coverage nil
                :source-notes *fcomp-source-note-map*
                :env *fasl-compile-time-env*
                :policy *compile-time-evaluation-policy*))'''
    compile_fn = old[len('(funcall '):-1]
    new = ('(let* ((function ' + compile_fn + '))\n        ' +
           hook('compile-effect-call', '(list form function)') +
           '\n        (let ((results (multiple-value-list (funcall function))))\n          ' +
           hook('compile-effect-values', '(list form function results)') + '\n          (values-list results)))')
    # Rebuild this function from U1 rather than stacking an unbalanced normal-
    # return-only hook around it. Native handled errors need explicit aborts.
    clean = original['lib/nfcomp.lisp'].decode()
    start = clean.index('(defun %compile-time-eval '); end = form_end(clean, start)
    definition = clean[start:end].replace(old, new)
    body = definition.index('(let* ')
    definition = definition[:body] + paired(definition[body:-1], 'compile-initializer-enter',
        'compile-initializer-return', 'compile-initializer-abort', 'form') + ')'
    current = texts['lib/nfcomp.lisp']; start = current.index('(defun %compile-time-eval '); end = form_end(current, start)
    texts['lib/nfcomp.lisp'] = current[:start] + definition + current[end:]
    # Loader effects: identify the callable object after deserialization, before
    # invoking it. This is a real loader run, not a compiler-emission surrogate.
    old = '(%epushval s (funcall fun))'
    replace('level-0/nfasload.lisp', old,
            '(let ((result nil))\n       (%epushval s ' + paired('(setq result (funcall fun))',
                'load-effect-call', 'load-effect-value', 'load-effect-abort',
                '(list (faslstate.faslfname s) fun)', '(list (faslstate.faslfname s) fun result)') + '))')
    # Capture all effect opcodes, including direct DEFUN/DEFPARAMETER forms that
    # do not go through $FASL-LFUNCALL. Nested deserialization is retained.
    old = '''(funcall (svref (faslstate.fasldispatch s) (logand op (lognot (ash 1 $fasl-epush-bit)))) 
           s)'''
    effect_test = '(member (logand op (lognot (ash 1 $fasl-epush-bit))) (list $fasl-lfuncall $fasl-defun $fasl-macro $fasl-defconstant $fasl-defparameter $fasl-defvar $fasl-defvar-init))'
    call = '(list (faslstate.faslfname s) (logand op (lognot (ash 1 $fasl-epush-bit))) (%fasl-get-file-pos s))'
    done = '(list (faslstate.faslfname s) (logand op (lognot (ash 1 $fasl-epush-bit))) (%fasl-get-file-pos s) (faslstate.faslval s))'
    # The same dispatcher also constructs the boot image: those returns are
    # target image words, not callable host functions or executed initializers.
    mode = '(cond ((eq (faslstate.fasldispatch s) *fasl-dispatch-table*) :native) ((and (boundp \'*xload-fasl-dispatch-table*) (eq (faslstate.fasldispatch s) *xload-fasl-dispatch-table*)) :cross-dump) (t :other))'
    reader = '(svref (faslstate.fasldispatch s) (logand op (lognot (ash 1 $fasl-epush-bit))))'
    call = call[:-1] + ' census-reader-mode census-reader)'
    done = done[:-1] + ' census-reader-mode census-reader)'
    invoke = '(funcall census-reader s)'
    replace('level-0/nfasload.lisp', old,
            '(let* ((census-reader ' + reader + ') (census-reader-mode ' + mode + '))\n  (if (and ' + GUARD + ' ' + effect_test + ')\n      ' +
            paired(invoke, 'fasl-effect-enter', 'fasl-effect-return', 'fasl-effect-abort', call, done) +
            '\n      (if (and ' + GUARD + ' (= (logand op (lognot (ash 1 $fasl-epush-bit))) $fasl-clfun))\n          ' +
            paired(invoke, 'fasl-function-enter', 'fasl-function-return', 'fasl-function-abort', call, done) + '\n          ' + invoke + ')))')
    replace('lib/nfcomp.lisp', '(defun fasl-out-opcode (opcode form)',
            '(defun fasl-out-opcode (opcode form)\n  (when (functionp form)\n    ' +
            hook('fasl-function-write', '(list (namestring *fasdump-stream*) (fasl-filepos) opcode form)') + ')')
    replace('lib/nfcomp.lisp', '(defun fcomp-output-form (opcode env &rest args)',
            '(defun fcomp-output-form (opcode env &rest args)\n  ' +
            hook('load-operation-emitted', '(list opcode args)'))
    replace('compiler/vinsn.lisp', '(append-dll-node vinsn vlist)))',
            hook('vinsn-emitted', 'vinsn') + '\n    (append-dll-node vinsn vlist)))')
    for path, name, payload in [
        ('compiler/nx2.lisp', 'backend-use-operator', '(list op forms)'),
        ('compiler/nx2.lisp', 'backend-apply-acode', 'acode')]:
        wrap(path, name, payload)
    patch = ''.join(''.join(difflib.unified_diff(original[p].decode().splitlines(True), texts[p].splitlines(True),
                                                fromfile='a/' + p, tofile='b/' + p)) for p in FILES)
    (HERE / 'observation.patch').write_text(patch)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {'version': 1, 'source_revision': U1, 'scope': 'Observation-only, removable nine-file unit in a disposable U1 archive.',
                'patch_sha256': sha(patch.encode()), 'files': [{'path': p, 'original_sha256': sha(original[p]),
                'observed_sha256': sha(texts[p].encode())} for p in FILES]}
    (HERE / 'patch.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Generated observation-only patch for', len(FILES), 'U1 files; checkout source untouched.')


if __name__ == '__main__':
    build()
