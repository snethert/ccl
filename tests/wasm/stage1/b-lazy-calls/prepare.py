"""Adapt only installation in the accepted tail harness; keep its semantic oracle."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def one(text,before,after):
    assert text.count(before)==1,before[:90]
    return text.replace(before,after)

def harness():
    original=(HERE.parent/'b-tail-calls/execute.mjs').read_text()
    s="import {LazyLoader} from './loader.mjs';\n"+original
    s=one(s,"const dir=workerData,read=", "const dir=workerData,read=")
    s=one(s,"const compiled=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')))]));", "const compiled={get:name=>new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',name+'.wasm')))};\nconst lazyRuns=[];")
    start=s.index(' for(const m of mods){\n  const codes=')
    end=s.index('\n function installObjects(){',start)
    old=s[start:end]
    # Reuse the independent ownership observers literally from the old harness.
    b=old[old.index('observe:self=>'):old.index('}}}}).exports.entry:entry;')]
    b=b.removeprefix('observe:')+'}'
    t=old[old.index('observe:(self,n,context)=>'):old.index('}}}}).exports.entry:tail);')]
    t=t.removeprefix('observe:')+'}'
    # The slices close the nested callback body (and its final if) separately.
    b+='}'
    t+='}'
    replacement=''' const loader=new LazyLoader({catalog:read('catalog.json'),memory,table,tail_table,call_error,
  stub:new WebAssembly.Module(fs.readFileSync(path.join(dir,'lazy-stub.wasm'))),observer,tailObserver,
  readBytes:name=>fs.readFileSync(path.join(dir,'installed',name+'.wasm'))});
 for(const m of mods){
  const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)]));
  const imports={env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error},symbols,keywords,codes};
  const pair=loader.defer(m.name,imports,observed?{entry:ENTRY_OBSERVER,tail_entry:TAIL_OBSERVER}:null);
  functions.set(m.name,pair.host_entry);
 }
'''.replace('ENTRY_OBSERVER',b).replace('TAIL_OBSERVER',t)
    s=s[:start]+replacement+s[end:]
    # A separate loader per observed mode owns empty tables at construction.
    s=one(s,' const functions=new Map();',' for(let i=0;i<table.length;i++){table.set(i,null);tail_table.set(i,null);}\n const functions=new Map();')
    s=one(s,' function installObjects(){',' function installObjects(){\n  loader.reset();')
    # Report loader activity only; the inherited execution result remains exact.
    s=one(s,"\n }\n}\nparentPort.postMessage", "\n }\n lazyRuns.push({observed,events:loader.events,states:loader.snapshot()});\n}\nparentPort.postMessage")
    s=one(s,"{status:'PASS',tail_runs:tailRuns", "{status:'PASS',lazy_runs:lazyRuns,tail_runs:tailRuns")
    return s

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(harness())
