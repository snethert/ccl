"""Unchanged forms translate exactly; crossing even a pure insertion refuses."""
import difflib
from source_map import apply_file,span
from payloads import require


def run():
    original=b'(defun before () 1)\n(defun after () 2)\n'
    inserted=b'(defun before () 1)\n(observer)\n(defun after () 2)\n'
    patch=list(difflib.diff_bytes(difflib.unified_diff,original.splitlines(True),inserted.splitlines(True)))[2:]
    got,regions=apply_file(original,patch);require(got==inserted,'INSERTION_BYTES')
    records={'test.lisp':dict(original_sha256='original',observed_sha256='observed',unchanged_regions=regions)}
    start=original.index(b'(defun after');end=len(original)-1
    mapped,witness=span(records,'test.lisp',start,end)
    require(mapped==(inserted.index(b'(defun after'),len(inserted)-1)
            and original[start:end]==inserted[mapped[0]:mapped[1]],'UNCHANGED_FORM_OFFSET')
    require(span(records,'test.lisp',0,len(original))==(None,None),'CROSS_INSERTION_REFUSAL')
    replacement=original.replace(b'after () 2',b'after () 3')
    p=list(difflib.diff_bytes(difflib.unified_diff,original.splitlines(True),replacement.splitlines(True)))[2:]
    got,regions=apply_file(original,p);require(got==replacement,'REPLACEMENT_BYTES')
    records['test.lisp']['unchanged_regions']=regions
    require(span(records,'test.lisp',start,end)==(None,None),'CHANGED_FORM_REFUSAL')
    try:apply_file(original.replace(b'before () 1',b'before () 0'),patch)
    except ValueError as e:require(str(e)=='PATCH_EXACT_CONTEXT','CONTEXT_FAILURE_REASON')
    else:raise ValueError('CONTEXT_SUBSTITUTION_ESCAPED')
    return dict(status='PASS',unchanged_form=True,crossing_insertion_refused=True,
                edited_form_refused=True,wrong_original_refused=True)


if __name__=='__main__':print(run())
