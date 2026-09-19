from pathlib import Path
import json
HERE=Path(__file__).resolve().parent

def append_call_arg(s,name):
 start=0;ends=[]
 while True:
  i=s.find('(call $'+name+' ',start)
  if i<0:break
  depth=1;j=i+1
  while depth:
   if s[j]=='(':depth+=1
   if s[j]==')':depth-=1
   j+=1
  ends.append(j-1);start=j
 for i in reversed(ends):s=s[:i]+' (local.get $top)'+s[i:]
 return s

def patch(s,replace):
 s=replace(s,'(unbound-variable . 2048)', '(unbound-variable . 2048) (storage-condition . 4096)')
 s=s.replace('undefined-function unbound-variable)', 'undefined-function unbound-variable storage-condition)')
 s=replace(s,'(then (i32.const 8220)) (else (i32.const 156))', '(then (i32.const 8220)) (else (if (result i32) (i32.and (i32.ge_u (local.get $kind) (i32.const 18)) (i32.le_u (local.get $kind) (i32.const 20))) (then (i32.const 16396)) (else (i32.const 156))))')
 s=replace(s,'(b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.const ~d)) (i64.extend_i32_u ~a))" bytes (b-load wasm32::tcr.vsp_limit)) 2)', '(b-wat "(call $stack_guard (i64.add (i64.extend_i32_u (local.get $top)) (i64.const ~d)) (local.get $top) (i32.const 18))" bytes)')
 s=replace(s,'(b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (local.get $wide)) (i64.extend_i32_u ~a))" (b-load wasm32::tcr.vsp_limit)) 2)', '(b-wat "(call $stack_guard (i64.add (i64.extend_i32_u (local.get $top)) (local.get $wide)) (local.get $top) (i32.const 18))")')
 s=replace(s,'(write-string (b-control-runtime) s)', '(write-string (b-control-runtime) s) (write-string (b-stacks-runtime) s)')
 # The VSP control root owns Lisp references; the CSP entry is a raw link to
 # that record. It is pushed before publishing the handler and popped exactly
 # once in either generated exit arm.
 s=replace(s,'(write-string (b-store wasm32::tcr.handler_checkpoint (b-local base)) s)', '(format s "(call $control_push (local.get ~a) (local.get $top))" base)\n      (write-string (b-store wasm32::tcr.handler_checkpoint (b-local base)) s)')
 anchor='(write-string (b-store wasm32::tcr.handler_checkpoint (b-local head)) s)'
 assert s.count(anchor)==2
 s=s.replace(anchor,'(format s "(call $control_pop (local.get ~a))" base)\n      '+anchor)
 for name in ['rv_alloc','rv_ensure','rv_deliver']:
  s=append_call_arg(s,name)
  a=s.index('(func $'+name);b=s.index('(result i32)',a)
  s=s[:b]+'(param $top i32) '+s[b:]
 s=replace(s,' (if (i32.eq (local.get $p) (local.get $end))\n  (then', ' (call $stack_guard (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $need))) (local.get $top) (i32.const 19))\n (if (i32.eq (local.get $p) (local.get $end))\n  (then')
 s=replace(s,'(i32.store offset=12 (local.get $d) (local.get $n)) (return (local.get $old))', '(call $stack_guard (i64.and (i64.add (i64.add (i64.extend_i32_u (local.get $old)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4))) (i64.const 15)) (i64.const -16)) (local.get $top) (i32.const 18))\n  (i32.store offset=12 (local.get $d) (local.get $n)) (return (local.get $old))')
 s+='\n(defun b-stacks-runtime () '+json.dumps((HERE/'stacks.wat').read_text()).replace('\\n','\n')+')\n'
 return s
