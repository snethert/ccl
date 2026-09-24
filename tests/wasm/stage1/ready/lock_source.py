"""Place target lock branches at their native definition boundaries."""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sources(root):
    result={}
    name='level-0/l0-aprims.lisp'
    text=(root/name).read_text()
    anchor='(defun %make-recursive-lock-ptr ()'
    assert text.count(anchor)==1
    text=text.replace(anchor,'#-wasm32-target\n'+anchor)
    # Each addition is reader-conditional; existing target forms stay identical.
    block=(HERE/'locks.lisp').read_text()
    split=block.index('#+wasm32-target\n(defun %wasm-recursive-lock-state')
    text+='\n'+block[:split]
    result[name]=text
    name='level-0/l0-misc.lisp';text=(root/name).read_text()
    for function in ('%lock-recursive-lock-ptr','%try-recursive-lock-object','%unlock-recursive-lock-ptr'):
        anchor='(defun '+function+' '
        assert text.count(anchor)==2, function
        for feature, replacement in (('#-futex','#-(or futex wasm32-target)'),('#+futex','#+(and futex (not wasm32-target))')):
            old=feature+'\n'+anchor
            assert text.count(old)==1
            text=text.replace(old,replacement+'\n'+anchor)
    text+='\n'+block[split:]
    result[name]=text
    name='compiler/WASM32/wasm32-arch.lisp';text=(root/name).read_text()
    anchor='(:basic-stream . 50)'
    assert text.count(anchor)==1
    result[name]=text.replace(anchor,anchor+' (:lock . 66)')
    return result
