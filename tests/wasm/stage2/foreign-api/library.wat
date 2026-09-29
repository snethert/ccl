(module
 (import "host" "collect" (func $collect))
 (import "host" "observe" (func $observe (param i32)))
 (memory (export "memory") 1 4)
 (global $next (mut i32) (i32.const 1024))
 (global $releases (mut i32) (i32.const 0))
 (global $mode (mut i32) (i32.const 0))
 (tag $error (param i32))
 (func (export "initialize") call $collect i32.const 1 call $observe)
 (func (export "echo") (param i32 i64 f32 f64) (result i32 i64 f32 f64)
  call $collect local.get 0 local.get 1 local.get 2 local.get 3)
 (func (export "mode") (param i32) local.get 0 global.set $mode)
 (func (export "allocate") (param $n i32) (result i32) (local $p i32)
  call $collect global.get $next local.set $p
  global.get $next local.get $n i32.add global.set $next local.get $p)
 (func (export "release") (param i32)
  call $collect i32.const 2 call $observe
  global.get $releases i32.const 1 i32.add global.set $releases
  global.get $mode i32.const 2 i32.eq if i32.const 7 throw $error end
  global.get $mode if unreachable end)
 (func (export "releases") (result i32) global.get $releases)
 (func (export "run") (param $p i32) (param $n i32) (param $mode i32) (result i32)
  (local $sum i32) (local $i i32)
  call $collect
  local.get $mode i32.const 1 i32.eq if i32.const 7 throw $error end
  local.get $mode i32.const 2 i32.eq if unreachable end
  i32.const 1 memory.grow drop
  local.get $n if local.get $p local.get $p i32.load8_u i32.const 1 i32.add i32.store8 end
  block $done loop $again
   local.get $i local.get $n i32.ge_u br_if $done
   local.get $sum local.get $p local.get $i i32.add i32.load8_u i32.add local.set $sum
   local.get $i i32.const 1 i32.add local.set $i br $again
  end end local.get $sum)
  (type $integer (func (param i32) (result i32)))
  (type $scalars (func (param i32 i64 f32 f64) (result i32 i64 f32 f64)))
  (type $void (func))
  (table (export "callbacks") 1 128 funcref)
  (global $saved (mut i32) (i32.const 0))
  (global $after (mut i32) (i32.const 0))
  (func $call (export "cb-call") (param i32 i32) (result i32)
    local.get 0 global.set $saved
    local.get 1 local.get 0 call_indirect (type $integer)
    call $collect
    global.get $after i32.const 1 i32.add global.set $after)
  (func (export "cb-twice") (param i32 i32) (result i32)
    local.get 1 local.get 0 call_indirect (type $integer) drop
    local.get 1 local.get 0 call_indirect (type $integer)
    call $collect
    global.get $after i32.const 1 i32.add global.set $after)
  (func (export "cb-saved") (param i32) (result i32)
    local.get 0 global.get $saved call_indirect (type $integer))
  (func (export "cb-trap") (param i32 i32) (result i32)
    local.get 1 local.get 0 call_indirect (type $integer) drop unreachable)
  (func (export "cb-scalars") (param i32 i32 i64 f32 f64) (result i32 i64 f32 f64)
    local.get 1 local.get 2 local.get 3 local.get 4 local.get 0 call_indirect (type $scalars))
  (func (export "cb-void") (param i32)
    local.get 0 call_indirect (type $void))
  (func (export "cb-after") (result i32) global.get $after)
)
