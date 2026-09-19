"""Replace temporary condition proxies with the D1 bootstrap CLOS representation."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent

def patch(s,replace):
 s=replace(s,"(symbol (b-special-symbol 'ccl::%handlers%))\n           (signal", "(symbol (progn (pushnew \"condition_registry\" *b-symbols* :test #'equal) (b-special-symbol 'ccl::%handlers%)))\n           (signal")
 start=s.index(' (func $condition_mask')
 end=s.index('(defun b-discard-handler',start)
 s=s[:start]+')")\n'+s[end:] if False else s[:start]+'")\n'+s[end:]
 # Preserve the existing handler-cons helpers and append the instance runtime.
 s=replace(s,'(defun b-condition-runtime ()','(defun b-handler-runtime ()')
 s+='\n(defun b-condition-runtime () (concatenate \'string (b-handler-runtime) '+json.dumps((HERE/'condition-runtime.wat').read_text()).replace('\\n','\n')+'))\n'
 # Details are arguments, not unrooted global scratch. The compatibility entry
 # retains the original failure code when the caller has no additional datum.
 s=replace(s,'(func $implicit_error (param $kind i32) (param $top i32)', '(func $implicit_error (param $kind i32) (param $top i32) (call $implicit_error_details (local.get $kind) (local.get $top) (i32.const 77825) (i32.const 77825)))\n (func $implicit_error_details (param $kind i32) (param $top i32) (param $datum i32) (param $expected i32)')
 start=s.index('        (format s "(local.set $heap ~a)"',s.index('(defun b-implicit-runtime'))
 end=s.index('        (write-string signal s)',start)
 # Extract the reviewed classification expression, retaining every kind.
 a=s.index('(if (result i32) (i32.eq (local.get $kind) (i32.const 1)) (then (i32.const 2076))',start)
 b=s.index('\n          (i32.store offset=8 (local.get $heap)',a)
 mask=s[a:b][:-1] # remove store's closing parenthesis
 new='''        (write-string "(i32.store offset=8 (local.get $frame) (local.get $datum)) (i32.store offset=12 (local.get $frame) (local.get $expected))" s)
        (write-string "(local.set $condition (call $condition_new '''+mask+''' (local.get $datum) (local.get $expected))) (i32.store (local.get $results) (local.get $condition))" s)
'''
 s=s[:start]+new+s[end:]
 return s
