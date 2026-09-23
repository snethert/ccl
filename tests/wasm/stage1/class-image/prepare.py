"""Join the cold image boundary to the written accepted execution harness."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
VALIDATION=HERE.parent/'bootstrap-validation'


def prepare(out):
    out=Path(out)
    # One explicitly checked boundary replacement. All oracle comparison,
    # mutation and TCR restoration checks remain in the written harness.
    text=(VALIDATION/'worker.mjs').read_text()
    text="import {imageArguments} from './image-input.mjs';\nimport {checkBootClasses} from './class-boot.mjs';\n"+text
    anchor='  const {base,dir}=workerData,NIL=77825,T=77838,tcr=1024,root=131064;'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n  const imageLoads=[];let loadedImage,saveReady;')
    anchor='if(x?.graph){currentGraph=x.graph;'
    assert text.count(anchor)==1
    text=text.replace(anchor,"if(x?.graph){assert.notEqual(workerData.imageMode,'read','cold loader cannot project graphs');currentGraph=x.graph;")
    anchor="    resetCase();\n    function globals()"
    assert text.count(anchor)==1
    helper='''    function initializeArguments(){
      currentGraph=expected.args.find(x=>x?.graph)?.graph;
      const loaded=imageArguments({memory,base,limit:base+size,tcr,root,get,put,gen,
        conditionSlots:initialConditionClasses.map(([p])=>p),expected,
        materialize:()=>{globals();return expected.args.map(encode);},dir,
        mode:workerData.imageMode,imageDir:workerData.imageDir,codeDigest:workerData.codeDigest,bootstrap:workerData.bootstrap});
      loadedImage=loaded.image;
      saveReady=loaded.saveReady;
      put(config+76,gen.extraRoots.length);
      gen.extraRoots.forEach((slot,i)=>put(4600000+4*i,slot));
      imageLoads.push({caseId:expected.caseId,digest:loaded.record,bytes:loaded.bytes,objects:loaded.objects});
      return loaded.args;
    }
    resetCase();
    function globals()'''
    text=text.replace(anchor,helper)
    for old,new in [('globals();const args=expected.args.map(encode);','const args=initializeArguments();'),
                    ('globals();const fresh=expected.args.map(encode);','const fresh=initializeArguments();')]:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    anchor='      const priorIntegerCalls=integerCalls'
    assert text.count(anchor)==1
    text=text.replace(anchor,'''      if(workerData.bootstrap){
        const values=checkBootClasses({gen,owners:ownerNames,get,put,root,collect});
        assert.deepEqual(values,expected.values);
        loadedImage.initialize(()=>true);
        rows.push({caseId:expected.caseId,name:expected.name,moved:move,values,ready:loadedImage.state});
        continue;
      }
'''+anchor)
    anchor='      rows.push({caseId:expected.caseId,name:expected.name,moved:move,values,after:recordedAfter'
    assert text.count(anchor)==1
    text=text.replace(anchor,'''      if(expected.definition==='CORE-CONDITION-OWN-TABLE'){
        assert.deepEqual(checkBootClasses({gen,owners:ownerNames,get,put,root,collect,initialize:true}),expected.values);
        if(workerData.imageMode==='write')saveReady();
      }
      loadedImage.initialize(()=>true);
      assert.equal(loadedImage.state,'READY');
'''+anchor)
    # READY is reached after the generated entry's values, mutations, globals
    # and TCR have been compared, not after merely copying image bytes.
    text=text.replace('parentPort.postMessage({','parentPort.postMessage({imageLoads,')
    (out/'image-worker.mjs').write_text(text)
    shutil.copyfile(HERE/'image-input.mjs',out/'image-input.mjs')
    shutil.copyfile(HERE/'class-boot.mjs',out/'class-boot.mjs')
    runtime=(HERE/'heap-image.mjs').read_text().replace("'../../../../runtime/wasm32/sha256.mjs'","'./sha256.mjs'")
    (out/'runtime/heap-image.mjs').write_text(runtime)
    modules=json.loads((out/'compiled/modules.json').read_text())
    names=['compiled/modules.json','compiled/symbols.json','compiled/pools.json']
    names+=['compiled/'+('collector_probe_hook' if r['name']=='collector_probe' else r['name'])+'.wasm' for r in modules]
    names+=sorted(p.name for p in out.glob('*.wasm'))
    names+=['install.mjs']+sorted(str(p.relative_to(out)) for p in (out/'runtime').glob('*.mjs'))
    hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}
    encoded=json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()
    (out/'class-image-code.json').write_bytes(encoded)
    (out/'class-image-code.sha256').write_text(hashlib.sha256(encoded).hexdigest()+'\n')


if __name__=='__main__':
    import sys
    prepare(sys.argv[1])
