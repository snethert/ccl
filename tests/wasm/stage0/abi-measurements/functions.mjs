export function imports(k,minimum) {
  return `(import "env" "memory" (memory 8 16 shared)) (import "env" "table" (table ${minimum} funcref))
    (type $G (func (param i32 i32 ${'i32 '.repeat(k)}) (result i32 i32)))
    (import "abi" "enter" (func $enter (param i32 i32 ${'i32 '.repeat(k)}) (result i32)))
    ${Object.entries({arg:[2,1],self:[1,1],car:[1,1],cdr:[1,1],cons:[2,1],payload:[1,1],state:[0,1],set_result:[3,0],get_result:[2,1],
      temp_set:[3,0],temp_get:[2,1],count:[2,0],error:[1,0],inspect:[1,0],collect:[0,1],poll:[0,0],pause:[2,0],finish:[2,2],
      inspect_binding:[0,0],tail_exit:[1,0],input:[1,1],prepare:[1,0],nested_call:[3,2],site:[2,0]}).map(([name,[p,r]])=>`(import "abi" "${name}" (func $${name} ${p?'(param '+ 'i32 '.repeat(p)+')':''} ${r?'(result '+ 'i32 '.repeat(r)+')':''}))`).join('\n')}
    (import "kernel" "get_tcr" (func $tcr (result i32)))
    (import "loader" "lookup" (func $lookup (param i32 i32) (result i32)))`;
}
const params=k=>`(param $self i32) (param $n i32) ${Array.from({length:k},(_,i)=>`(param $a${i} i32)`).join(' ')}`;
const args=k=>`(local.get $self) (local.get $n) ${Array.from({length:k},(_,i)=>`(local.get $a${i})`).join(' ')}`;
export function functionWat(runtime,schema,k,slots,entry,mut={}) {
  const f=runtime.tcr,s=schema.state,code=entry.code;
  const state=n=>`(i32.load offset=${s[n]} (call $state))`;
  const frame='(local.get $f)';
  const set=(i,v)=>`(call $set_result ${frame} (i32.const ${i}) ${v})`;
  const fold=`
      (local.set $sum (i32.add (i32.const ${entry.version*1000}) (call $payload (call $cdr (call $self ${frame})))))
      (local.set $i (i32.const 0))
      (block $fold_done (loop $fold
        (br_if $fold_done (i32.ge_u (local.get $i) (local.get $n)))
        (local.set $sum (i32.add (local.get $sum) (i32.mul (i32.add (local.get $i) (i32.const 1)) (call $payload (call $arg ${frame} (local.get $i))))))
        (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $fold)))
      ${set(0,'(i32.shl (local.get $sum) (i32.const 2))')}
      ${set(1,mut.wrongSelf?'(i32.const 65)':`(call $self ${frame})`)}
      ${set(2,`(if (result i32) (local.get $n) (then (call $arg ${frame} (i32.const 0))) (else (i32.const 65)))`)}
      ${set(3,`(if (result i32) (local.get $n) (then (call $arg ${frame} (i32.sub (local.get $n) (i32.const 1)))) (else (i32.const 65)))`)}
      ${set(4,`(call $cdr (call $self ${frame}))`)} ${set(5,'(i32.shl (local.get $n) (i32.const 2))')}`;
  let body=fold;
  if(code===20)body=`
      (call $site ${frame} (i32.const 2007))
      ;; @site 2007 optional-binding-and-allocation
      ${set(0,`(call $arg ${frame} (i32.const 0))`)} ${set(1,`(call $arg ${frame} (i32.const 1))`)}
      ${set(2,`(if (result i32) (i32.gt_u (local.get $n) (i32.const 2)) (then (call $arg ${frame} (i32.const 2))) (else (i32.const 396)))`)}
      ${set(3,`(if (result i32) (i32.gt_u (local.get $n) (i32.const 3)) (then (call $arg ${frame} (i32.const 3))) (else (i32.const 308)))`)}
      (call $temp_set ${frame} (i32.const 0) (i32.const 65))
      (local.set $i (local.get $n))
      (block $rest_done (loop $rest
        (br_if $rest_done (i32.le_u (local.get $i) (i32.const 4)))
        (local.set $i (i32.sub (local.get $i) (i32.const 1)))
        (call $temp_set ${frame} (i32.const 0) (call $cons (call $arg ${frame} (local.get $i)) (call $temp_get ${frame} (i32.const 0)))) (br $rest)))
      ${set(4,`(call $temp_get ${frame} (i32.const 0))`)}
      ${set(5,'(i32.shl (i32.add (i32.gt_u (local.get $n) (i32.const 2)) (i32.mul (i32.gt_u (local.get $n) (i32.const 3)) (i32.const 2))) (i32.const 2))')}`;
  if(code===21)body=`
      (if (i32.and (local.get $n) (i32.const 1)) (then (call $error (i32.const 918))))
      ${set(0,'(i32.const 396)')} ${set(1,'(i32.const 308)')}
      (local.set $i (i32.const 0))
      (block $keys_done (loop $keys
        (br_if $keys_done (i32.ge_u (local.get $i) (local.get $n)))
        (local.set $key (call $arg ${frame} (local.get $i)))
        (local.set $v (call $arg ${frame} (i32.add (local.get $i) (i32.const 1))))
        (if (i32.eq (local.get $key) (i32.const 4000)) (then
          (if (i32.eqz (local.get $seen_a)) (then ${set(0,'(local.get $v)')} (local.set $seen_a (i32.const 1)))))
        (else (if (i32.eq (local.get $key) (i32.const 4004)) (then
          (if (i32.eqz (local.get $seen_b)) (then ${set(1,'(local.get $v)')} (local.set $seen_b (i32.const 1)))))
        (else (if (i32.eq (local.get $key) (i32.const 4008)) (then
          (if (i32.eqz (local.get $seen_allow)) (then (local.set $allow (i32.ne (local.get $v) (i32.const 65))) (local.set $seen_allow (i32.const 1)))))
          (else (local.set $unknown (i32.const 1))))))))
        (local.set $i (i32.add (local.get $i) (i32.const 2))) (br $keys)))
      (if (i32.and (local.get $unknown) (i32.eqz (local.get $allow))) (then (call $error (i32.const 918))))
      ${set(2,'(if (result i32) (local.get $seen_a) (then (i32.const 4)) (else (i32.const 65)))')}
      ${set(3,'(if (result i32) (local.get $seen_b) (then (i32.const 4)) (else (i32.const 65)))')}
      ${set(4,'(if (result i32) (local.get $allow) (then (i32.const 4)) (else (i32.const 65)))')}
      ${set(5,'(i32.shl (local.get $n) (i32.const 2))')}`;
  if(code===40)body=`
      (i32.store offset=${s.effects} (call $state) (i32.const 1))
      (call $site ${frame} (i32.const 4004))
      ;; @site 4004 first-nested-call
      (call $nested_call ${frame} (i32.const 0) (local.get $n)) (drop) (drop)
      ${Array.from({length:6},(_,i)=>mut.losePreservedValues?'':`(call $temp_set ${frame} (i32.const ${i}) (call $get_result ${frame} (i32.const ${i})))`).join('\n')}
      (i32.store offset=${s.effects} (call $state) (i32.const 12))
      (call $site ${frame} (i32.const 4006))
      ;; @site 4006 second-nested-call
      (call $nested_call ${frame} (i32.const 1) (local.get $n)) (drop) (drop)
      ${[0,1,2].map(i=>set(i+3,`(call $get_result ${frame} (i32.const ${i}))`)).join('\n')}
      ${[0,1,2].map(i=>set(i,`(call $temp_get ${frame} (i32.const ${i}))`)).join('\n')}`;
  const tail=code===30||code===31;
  if(tail)body=`
      (local.set $steps (i32.shr_u (call $arg ${frame} (i32.const 0)) (i32.const 2)))
      (if (local.get $steps) (then
        (call $site ${frame} (i32.const ${code*100+6}))
        ;; @site ${code*100+6} tail-poll-and-transfer
        ${mut.loseBinding?'(i32.store (i32.sub (i32.load offset=32 (local.get $f)) (i32.const 4)) (i32.const 0))':''}
        (call $inspect_binding)
        (call $poll)
        (if (i32.eqz (i32.rem_u (local.get $steps) (i32.const 2000))) (then (drop (call $collect))))
        (i32.store offset=${s.tail_count} (call $state) (i32.add ${state('tail_count')} (i32.const 1)))
        (local.set $self (i32.load offset=${(code===30?6:5)*4} (i32.load offset=${s.anchors} (call $state))))
        (local.set $n (i32.const ${code===30?32:2}))
        ${mut.tailLeak?'':`(call $tail_exit ${frame})`}
        (local.set $i (i32.const ${k}))
        (block $tail_done (loop $tail_copy (br_if $tail_done (i32.ge_u (local.get $i) (local.get $n)))
          (i32.store (i32.add (i32.load offset=${f.vsp} (call $tcr)) (i32.mul (i32.sub (local.get $i) (i32.const ${k})) (i32.const 4)))
            (if (result i32) (i32.eqz (local.get $i)) (then (i32.shl (i32.sub (local.get $steps) (i32.const 1)) (i32.const 2)))
              (else (i32.mul (i32.add (local.get $i) (i32.const 1)) (i32.const 4)))))
          (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $tail_copy)))
        (return_call_indirect (type $G) (local.get $self) (local.get $n)
          ${Array.from({length:k},(_,i)=>`(if (result i32) (i32.gt_u (local.get $n) (i32.const ${i})) (then ${i===0?'(i32.shl (i32.sub (local.get $steps) (i32.const 1)) (i32.const 2))':`(i32.const ${(i+1)*4})`}) (else (i32.const 65)))`).join(' ')}
          (call $lookup (i32.shr_u (call $car (local.get $self)) (i32.const 2)) (i32.const 0)))))
      ${fold}`;
  return `(module ${imports(k,slots.minimum)}
    (func $G (export "G") ${params(k)} (result i32 i32)
      (local $f i32) (local $sum i32) (local $i i32) (local $v i32) (local $key i32) (local $cached i32) (local $steps i32)
      (local $seen_a i32) (local $seen_b i32) (local $allow i32) (local $seen_allow i32) (local $unknown i32)
      (if (i32.or (i32.lt_u (local.get $n) (i32.const ${entry.minimum})) (i32.gt_u (local.get $n) (i32.const ${entry.maximum}))) (then (call $error (i32.const 917))))
      ;; @site ${code*100+1} generic-entry
      (local.set $f (call $enter ${args(k)}))
      (local.set $cached (call $self ${frame}))
      (if (i32.load offset=76 (call $state)) (then (drop (call $collect))))
      ${tail?'':`(call $inspect (i32.const 4))`}
      ${[10,11,12].includes(code)?`;; @site ${code*100+2},${code*100+3} suspend-and-resume
      (if (i32.and ${state('suspend')} (i32.const 1)) (then (call $pause ${frame} (i32.const 1))))`:''}
      ${mut.staleRoot?'(drop (call $car (local.get $cached)))':''}
      ${body}
      (call $site ${frame} (i32.const ${code*100+8}))
      ;; @site ${code*100+8} complete-return-values
      (call $count ${frame} ${state('value_count')}) (call $inspect (i32.const 5))
      (call $finish ${frame} ${state('value_count')}))
    (func (export "direct") ${params(k)} (result i32 i32) (call $G ${args(k)}))
    (func (export "adapter") (param $self i32) (param $n i32) (param $tcr i32) (result i32 i32)
      (if (i32.ne (local.get $tcr) (call $tcr)) (then (call $error (i32.const 920))))
      (call $prepare (local.get $n))
      (return_call $G (local.get $self) (local.get $n) ${Array.from({length:k},(_,i)=>`(if (result i32) (i32.gt_u (local.get $n) (i32.const ${i})) (then (call $input (i32.const ${i}))) (else (i32.const 65)))`).join(' ')})))`;
}

export function stubWat(runtime,schema,k,slots,mut={}) {
  const s=schema.state,f=runtime.tcr;
  return `(module ${imports(k,slots.minimum)}
    (func $G (export "G") ${params(k)} (result i32 i32)
      (local $f i32) (local $i i32) (local $cached i32)
      ;; @stub-site 90 generic-stub-entry
      (local.set $f (call $enter ${args(k)})) (local.set $cached (local.get $self))
      (call $site (local.get $f) (i32.add (i32.mul (i32.shr_u (call $car (local.get $self)) (i32.const 2)) (i32.const 100)) (i32.const 90)))
      (i32.store offset=${s.lazy_code} (call $state) (i32.shr_u (call $car (local.get $self)) (i32.const 2)))
      ;; @stub-site 92,93 installation-suspend-and-resume
      (call $pause (local.get $f) (i32.const 2))
      (local.set $self ${mut.staleStub?'(local.get $cached)':'(call $self (local.get $f))'})
      ${Array.from({length:k},(_,i)=>`(local.set $a${i} (if (result i32) (i32.gt_u (local.get $n) (i32.const ${i})) (then (call $arg (local.get $f) (i32.const ${i}))) (else (i32.const 65))))`).join('\n')}
      (call $tail_exit (local.get $f))
      (local.set $i (i32.const ${k}))
      (block $done (loop $copy (br_if $done (i32.ge_u (local.get $i) (local.get $n)))
        (i32.store (i32.add (i32.load offset=${f.vsp} (call $tcr)) (i32.mul (i32.sub (local.get $i) (i32.const ${k})) (i32.const 4))) (call $arg (local.get $f) (local.get $i)))
        (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $copy)))
      (return_call_indirect (type $G) ${args(k)} (call $lookup (i32.shr_u (call $car (local.get $self)) (i32.const 2)) (i32.const 0))))
    (func (export "adapter") (param $self i32) (param $n i32) (param $thread i32) (result i32 i32)
      (if (i32.ne (local.get $thread) (call $tcr)) (then (call $error (i32.const 920))))
      (call $prepare (local.get $n))
      (return_call $G (local.get $self) (local.get $n) ${Array.from({length:k},(_,i)=>`(if (result i32) (i32.gt_u (local.get $n) (i32.const ${i})) (then (call $input (i32.const ${i}))) (else (i32.const 65)))`).join(' ')})))`;
}
