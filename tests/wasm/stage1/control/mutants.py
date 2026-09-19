"""Single-site semantic controls; each uses a focused source/resource oracle."""
def variants(s,replace):
 def one(a,b):return replace(s,a,b)
 yield 'type-path',one('(call $implicit_error_details (i32.const 5) (local.get $top) ~a ~a) unreachable','(throw $call_error (i32.const 5)) unreachable'),'r_basic',None
 yield 'bounds-class',one('(then (i32.const 124)) (else','(then (i32.const 156)) (else'),'r_bounds_class',None
 yield 'condition-datum',one('(i32.store offset=8 (local.get $slots) (local.get $datum))','(i32.store offset=8 (local.get $slots) (i32.const 77825))'),'r_datum',None
 yield 'unbound-name',one('(call $implicit_error_details (i32.const 10) (local.get $top) (local.get $symbol) (i32.const 77825))','(call $implicit_error_details (i32.const 10) (local.get $top) (i32.const 77825) (i32.const 77825))'),'r_cell',None
 yield 'debugger-mask',one('(b-bind-symbol symbol "(i32.const 77825)")','(b-bind-symbol symbol hook)'),'d_mask',None
 yield 'debugger-depth',one('(local.set ~a) (i32.store offset=184 (global.get $tcr) (local.get ~a)) (throw_ref (local.get ~a))','(local.set ~a) (drop (local.get ~a)) (throw_ref (local.get ~a))'),'d_type',None
 yield 'expired-restart',one(' (if (local.get $required) (then (call $implicit_error (i32.const 8)', ' (if (i32.and (local.get $required) (i32.eq (i32.and (local.get $name) (i32.const 7)) (i32.const 6))) (then (return (local.get $name))))\n (if (local.get $required) (then (call $implicit_error (i32.const 8)'),'r_expired',None
 yield 'control-stack-retirement',one('(i32.store offset=88 (global.get $tcr) (local.get $p)))','(drop (local.get $p)))'),'o_nested',None
 yield 'soft-limit-disabled',one('(i32.and (i32.ne (local.get $reserve) (i32.const 0)) (i32.eqz','(i32.and (local.get $reserve) (i32.eqz'),'rr_value','soft-vsp'
 yield 'reserve-not-rearmed',one('(i32.store offset=180 (global.get $tcr) (local.get $flags))','(drop (local.get $flags))'),'rr_value','soft-vsp'
 yield 'interrupt-mask-bypassed',one('(if (i32.ge_s (call $special_read ~a) (i32.const 0)) (then','(if (i32.or (i32.const 1) (call $special_read ~a)) (then'),'irq_nested','pending-irq_nested'
 yield 'gc-service-skipped',one('(if (i32.and (i32.atomic.load offset=36 (global.get $tcr)) (i32.const 1)) (then ~a))','(if (i32.and (i32.atomic.load offset=36 (global.get $tcr)) (i32.const 0)) (then ~a))'),'irq_nested','pending-irq_nested'
 yield 'pending-bits-erased',one('(i32.atomic.rmw.and offset=36 (global.get $tcr) (i32.const -3))','(i32.atomic.rmw.and offset=36 (global.get $tcr) (i32.const 0))'),'irq_nested','pending-irq_nested'
