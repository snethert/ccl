"""Prepare the focused namespace Worker from the qualified graph encoder."""
from pathlib import Path
import sys,shutil
HERE=Path(__file__).resolve().parent

def prepare(out):
    install=(out/'install.mjs').read_text()
    if 'namespace binding extent' not in install:
        install=install.replace("const bindings=Array.from({length:4096},(_,i)=>get(680000+4*i));",
          "const bindingCount=get(tcr+108),bindings=Array.from({length:bindingCount},(_,i)=>get(get(tcr+104)+4*i));")
        install=install.replace('[48,52,56,116]','[48,52,56,104,108,116]')
        install=install.replace("assert.deepEqual(Array.from({length:4096},(_,i)=>get(680000+4*i)),bindings,name+' restored bindings');",
          "assert(get(tcr+108)>=bindingCount,'namespace binding extent');\n"
          "   assert.deepEqual(Array.from({length:bindingCount},(_,i)=>get(get(tcr+104)+4*i)),bindings,name+' restored bindings');\n"
          "   for(let i=bindingCount;i<get(tcr+108);i++)assert.equal(get(get(tcr+104)+4*i),243,name+' restored grown binding');")
        (out/'install.mjs').write_text(install)
    text=(HERE.parent/'ready/worker.mjs').read_text()
    text=text[text.index('  const {base,dir}=workerData'):text.index('  const supportChecks=[]')]
    text=text.replace('Math.max(320,','Math.max(432,')
    text=text.replace('[2097152,gen.imageEnd]].entries()', '[2097152,gen.imageEnd],[23068672,25165824]].entries()')
    text=text.replace('  function decode(x){', '''  const decoding=[];
  function decode(x){
    if(decoding.includes(x))throw Error('cyclic observation '+JSON.stringify({word:x,header:get(x-6),path:decoding.map(p=>({word:p,header:get(p-6),words:Array.from({length:10},(_,i)=>get(p-6+4*i))}))}));
    decoding.push(x);try{return decodeValue(x);}finally{decoding.pop();}
  }
  function decodeValue(x){''')
    text=text.replace("  const gen=await install", "  let serviceFailure;\n  const recordFailure=(kind,e,args)=>{serviceFailure={kind,args};if(!get(6009300)){put(6009300,get(6000000));bytes(6005200,4096).set(bytes(6000016,4096));bytes(6009400,32).set(bytes(get(tcr+64),32));}throw e;};\n  const gen=await install")
    text=text.replace("return integer(...a);", "try{return integer(...a);}catch(e){return recordFailure('integer',e,a);}")
    text=text.replace("return floating(...a);", "try{return floating(...a);}catch(e){return recordFailure('float',e,a);}")
    text=text.replace("assert.equal(collector.collect(config),0,'internal collection');",
      "const status=collector.collect(config);if(status)serviceFailure={kind:'collector',status,config:Array.from({length:24},(_,i)=>get(config+4*i)),heap:[get(tcr+56),get(tcr+48),get(tcr+52)]};assert.equal(status,0,'internal collection');")
    imports='''import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parentPort,workerData} from 'node:worker_threads';
import {encodeGraph,decodeGraph} from './graph.mjs';
import {install} from './install.mjs';
import {CollectorOwner} from './runtime/collector-owner.mjs';
import {integerService} from './runtime/integer-service.mjs';
import {floatService} from './runtime/float-service.mjs';
import {sha256} from './runtime/sha256.mjs';
import {fileClient} from './client.mjs';
import {packages} from './packages.mjs';
import {checkBoundaries} from './namespace-controls.mjs';
'''
    (out/'namespace-worker.mjs').write_text(imports+text+(HERE/'worker-tail.mjs').read_text())

if __name__=='__main__':prepare(Path(sys.argv[1]))
