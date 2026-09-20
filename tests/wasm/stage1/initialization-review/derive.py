"""Small anchored changes to the reviewed initialization owner and harness."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'initialization'
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def owner():
 s=(BASE/'owner.mjs').read_text()
 s=replace(s,'constructor({memory,layout,layoutDigest,modules})','constructor({memory,layout,layoutDigest,modules,table,tail_table})')
 anchor="  need(modules.length===l.modules.length,'MODULE_SET');"
 s=replace(s,anchor,"  need(table instanceof WebAssembly.Table&&tail_table instanceof WebAssembly.Table&&table.length>=l.tableCapacity&&tail_table.length>=l.tableCapacity,'ACTUAL_TABLE_CAPACITY');\n"+anchor)
 anchor=' #initialize(owner){'
 extra=""" // Reserved control words are immutable zero throughout this protocol.
 #reserved(state){
  for(let i=1;i<state.length;i++)if(!(i>=2&&i<10)&&!(i>=16&&i<16+this.#layout.workers.length))need(Atomics.load(state,i)===0,'CONTROL_RESERVED');
 }
 #fresh(state){
  need(Atomics.load(state,0)===0,'PROCESS_STATE');
  // Read-only admission precedes the atomic claim. A competing winner can
  // cause a busy/freshness refusal; the scheduler owns retry policy.
  for(let i=1;i<state.length;i++)need(Atomics.load(state,i)===0,'CONTROL_NOT_FRESH');
 }
"""
 s=replace(s,anchor,extra+anchor)
 s=replace(s,"need(id===0,'BOOTSTRAP_WORKER');const state=this.#state();","need(id===0,'BOOTSTRAP_WORKER');const state=this.#state();this.#reserved(state);")
 s=replace(s,"  need(Atomics.compareExchange(state,0,0,1)===0,'PROCESS_STATE');","  this.#fresh(state);\n  need(Atomics.compareExchange(state,0,0,1)===0,'PROCESS_STATE');")
 s=replace(s,"need(Atomics.load(state,0)===2,'PROCESS_NOT_READY');this.#identity();","need(Atomics.load(state,0)===2,'PROCESS_NOT_READY');this.#identity();this.#reserved(state);")
 return s
def harness():
 s=(BASE/'check.mjs').read_text()
 s="import {fileURLToPath} from 'node:url';\n"+s
 s=replace(s,'function modules(dir){','export function modules(dir){')
 s=replace(s,'function layout(dir,base,mods){','export function layout(dir,base,mods){')
 s=replace(s,"function makeOwner(memory,l,mods){return new InitializationOwner({memory,layout:l,layoutDigest:sha(JSON.stringify(l)),modules:mods});}","function makeOwner(memory,l,mods,table=new WebAssembly.Table({element:'anyfunc',initial:8}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:8})){return new InitializationOwner({memory,layout:l,layoutDigest:sha(JSON.stringify(l)),modules:mods,table,tail_table});}")
 s=replace(s,'if(!isMainThread){',"if(!isMainThread&&process.argv[1]===fileURLToPath(import.meta.url)){")
 s=replace(s,',owner=makeOwner(memory,l,mods),w=l.workerInfo[id]',',w=l.workerInfo[id]')
 s=replace(s," const reserve=new WebAssembly.Instance", " const owner=makeOwner(memory,l,mods,table,tail_table);\n const reserve=new WebAssembly.Instance")
 s=replace(s,'}else{\n const dir=process.argv[2]',"}else if(process.argv[1]===fileURLToPath(import.meta.url)){\n const dir=process.argv[2]")
 return s
