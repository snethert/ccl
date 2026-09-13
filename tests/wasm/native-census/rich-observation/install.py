"""Select changed definitions without replaying destructive level-0 boot aliases."""
from pathlib import Path
from build_patch import form_end

DEFINITIONS = {
    'level-1/l1-readloop.lisp': ['%symbol-macroexpand-1', 'macroexpand-1'],
    'compiler/nx.lisp': ['compile-named-function'],
    'compiler/nx0.lisp': ['compiler-macroexpand-1'],
    'compiler/nx2.lisp': ['backend-use-operator', 'backend-apply-acode'],
    'compiler/vinsn.lisp': ['%emit-vinsn'],
    'lib/nfcomp.lisp': ['%compile-time-eval', 'fcomp-read-loop', 'fcomp-macroexpand-1', 'fcomp-compile-toplevel-forms',
                       'fasl-out-opcode', 'fcomp-output-form'],
    'lib/dumplisp.lisp': ['restore-lisp-pointers'],
    'level-0/nfasload.lisp': ['%fasl-dispatch', '$fasl-lfuncall'],
    'level-0/l0-def.lisp': ['%fhave', '%unfhave'],
}


def write_install(source, destination):
    forms = ['(in-package :ccl)', '(setq *warn-if-redefine-kernel* nil)',
             '(load "ccl:xdump;faslenv.lisp")']
    # Install the original loader registration macro if absent in the image.
    text = (source / 'xdump/faslenv.lisp').read_text()
    start = text.index('(defmacro deffaslop ')
    forms.append(text[start:form_end(text, start)])
    for path, names in DEFINITIONS.items():
        text = (source / path).read_text()
        for name in names:
            prefix = ('(deffaslop ' if name.startswith('$') else '(defun ') + name + ' '
            start = text.index(prefix)
            forms.append(text[start:form_end(text, start)])
    destination.write_text('\n\n'.join(forms) + '\n')
    return len(forms) - 3
