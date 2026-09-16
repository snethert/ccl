"""Single-site compiler mutations; each must fail the unchanged semantic oracle."""
from support import require

def mutations(text):
 result={}
 def edit(name,old,new,which=0,total=1):
  require(text.count(old)==total,'MUTANT_ANCHOR '+name)
  start=-1
  for _ in range(which+1):start=text.index(old,start+1)
  result[name]=text[:start]+new+text[start+len(old):]
 pair='(offset (if car-p wasm32::cons.car wasm32::cons.cdr)))'
 swap='(offset (if car-p wasm32::cons.cdr wasm32::cons.car)))'
 edit('read-swap',pair,swap,total=2)
 edit('write-swap',pair,swap,which=1,total=2)
 test='(i32.eq (local.get ~a) (i32.const ~d))'
 disabled='(i32.eq (i32.and (local.get ~a) (i32.const 0)) (i32.const ~d))'
 edit('nil-read',test,disabled,total=2)
 edit('nil-write',test,disabled,which=1,total=2)
 edit('tag-mask','local wasm32::fulltagmask wasm32::fulltag-cons local expected','local wasm32::fixnummask wasm32::fulltag-cons local expected')
 edit('type-guard','local wasm32::fulltagmask wasm32::fulltag-cons local expected','local wasm32::fulltagmask wasm32::fulltag-misc local expected')
 edit('mutator-result','(cons-check ptr 2) ptr offset new ptr','(cons-check ptr 2) ptr offset new new')
 edit('operand-order','ptr pair-code new value-code ptr','new value-code ptr pair-code ptr')
 edit('temporary-alias','(format nil "$tmp~d" *temporary-count*)','(format nil "$tmp~d" 0)')
 edit('store-omitted','(i32.store (i32.add (local.get ~a) (i32.const ~d)) (local.get ~a))','(drop (i32.add (local.get ~a) (i32.const ~d))) (drop (local.get ~a))')
 edit('cdr-displacement',pair,'(offset (if car-p wasm32::cons.car 0)))',total=2)
 edit('high-bit-truncation','(i32.load (i32.add (local.get ~a) (i32.const ~d)))','(i32.load (i32.add (i32.and (local.get ~a) (i32.const 2147483647)) (i32.const ~d)))')
 edit('count-publication','(i32.store offset=~d (global.get $tcr) (i32.const 1))','(i32.store offset=~d (global.get $tcr) (i32.const 0))')
 edit('exception-publication','(local.set $value ~a)','(i32.store offset=116 (global.get $tcr) (i32.const 1)) (local.set $value ~a)')
 edit('condition-kind','(cons-check ptr 1)','(cons-check ptr 2)')
 return result
