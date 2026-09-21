"""Reader-conditional source additions; existing targets retain their forms."""
import re

CONSTANTS = {
    'SEEK_SET': 'io-seek-set', 'SEEK_CUR': 'io-seek-cur',
    'EINTR': 'io-error-interrupted', 'EEXIST': 'io-error-file-exists',
    'ENFILE': 'io-error-system-file-limit', 'EMFILE': 'io-error-process-file-limit'}
FILES = ('level-0/l0-io.lisp', 'level-0/nfasload.lisp',
         'level-1/l1-files.lisp', 'level-1/l1-lisp-threads.lisp',
         'level-1/l1-streams.lisp', 'level-1/l1-boot-2.lisp', 'level-1/l1-sysio.lisp')
MODULE_ANCHOR = '  (append *level-1-modules*'
MODULE_ADDITION = """  (when (eq target :wasm32)
    (return-from target-level-1-modules (remove 'linux-files *level-1-modules*)))
"""


def derive(root):
    result = {}
    for name in FILES:
        text = (root / name).read_text()
        text, n = re.subn(r'#\$(' + '|'.join(CONSTANTS) + r')\b',
                          lambda m: '#+wasm32-target target::' + CONSTANTS[m[1]] +
                                    ' #-wasm32-target ' + m[0], text)
        assert n, name
        result[name] = text
    name = 'level-1/level-1.lisp'
    text = (root / name).read_text()
    assert text.count('(l1-load "linux-files")') == 1
    result[name] = text.replace('(l1-load "linux-files")', '#-wasm32-target (l1-load "linux-files")')
    name = 'lib/compile-ccl.lisp'
    text = (root / name).read_text()
    assert text.count(MODULE_ANCHOR) == 1
    result[name] = text.replace(MODULE_ANCHOR, MODULE_ADDITION + MODULE_ANCHOR)
    return result
