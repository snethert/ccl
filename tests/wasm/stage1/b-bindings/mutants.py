def mutations(source):
 def one(old,new):
  assert source.count(old)==1,(old,source.count(old));return source.replace(old,new)
 edits={
 'optional-presence':('(i32.gt_u (local.get $nargs) (i32.const ~d)) (then ~a ~a)', '(i32.ge_u (local.get $nargs) (i32.const ~d)) (then ~a ~a)'),
 'optional-stride':('i (b-bind-value var (b-wat "(i32.load offset=~d (local.get $incoming))" (* 4 i)))', 'i (b-bind-value var (b-wat "(i32.load offset=~d (local.get $incoming))" (* 8 i)))'),
 'optional-supplied':('(b-bind-value sp "(i32.const 77838)")\n        (b-bind-value var (b-scalar init))','(b-bind-value sp "(i32.const 77825)")\n        (b-bind-value var (b-scalar init))'),
 'optional-default':('(b-bind-value var (b-scalar init)) (b-bind-value sp "(i32.const 77825)")','(b-bind-value var "(i32.const 77825)") (b-bind-value sp "(i32.const 77825)")'),
 'key-last-wins':('(if (i32.eq (i32.load ~a) (i32.const 77825)) (then ~a ~a))', '(if (i32.or (i32.const 1) (i32.eq (i32.load ~a) (i32.const 77825))) (then ~a ~a))'),
 'key-value':('(b-bind-value var (b-local value)) (b-bind-value sp "(i32.const 77838)")','(b-bind-value var (b-local key)) (b-bind-value sp "(i32.const 77838)")'),
 'key-match':('key (b-keyword name) known', 'key (b-keyword :allow-other-keys) known'),
 'allow-last-wins':('(if (i32.eqz (local.get ~a)) (then (local.set ~a (i32.const 1)) (local.set ~a (local.get ~a))))))','(if (i32.or (i32.const 1) (i32.eqz (local.get ~a))) (then (local.set ~a (i32.const 1)) (local.set ~a (local.get ~a))))))'),
 'unknown-key':('(i32.and (local.get ~a) (i32.eq (local.get ~a) (i32.const 77825)))','(i32.and (i32.const 0) (i32.and (local.get ~a) (i32.eq (local.get ~a) (i32.const 77825))))'),
 'lambda-allow':('(unless allow\n            (write-string', '(when t\n            (write-string'),
 'odd-key-count':('(i32.and (i32.gt_u (local.get $nargs) (i32.const ~d)) (i32.and (i32.sub (local.get $nargs) (i32.const ~d)) (i32.const 1)))', '(i32.and (i32.const 0) (i32.and (i32.gt_u (local.get $nargs) (i32.const ~d)) (i32.and (i32.sub (local.get $nargs) (i32.const ~d)) (i32.const 1))))'),
 'key-default-order':('(loop for var in vars for sp in supplied for init in inits do', '(loop for var in (reverse vars) for sp in (reverse supplied) for init in (reverse inits) do'),
 'bound-roots':('(b-initialize-roots "(local.get $frame)" (+ 64 (length *b-bound-vars*)))','(b-initialize-roots "(local.get $frame)" 64)'),
 'bound-frame-capacity':('(b-reserve (* 16 (ceiling (+ 264 (* 4 (length *b-bound-vars*))) 16)))','(b-reserve 272)'),
 'dynamic-argument-extent':('(i32.mul (local.get $nargs) (i32.const 4)) (i32.const 15)', '(i32.mul (i32.const 0) (i32.const 4)) (i32.const 15)'),
 'binding-exception-root':('(b-store wasm32::tcr.root_head "(local.get $root)")','(b-store wasm32::tcr.root_head "(i32.const 0)")'),
 }
 return {name:one(old,new) for name,(old,new) in edits.items()}
