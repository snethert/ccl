from pathlib import Path
import importlib.util,shutil
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('allocation_fastpath',HERE.parent/'numeric-fastpath/derive.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
replace=base.replace
def derive(out):
 base.derive(out)
 p=out/'collector-owner.mjs';s=p.read_text()
 s=replace(s,' #roles=new Map();',' #roles=new Map();\n #scalarBoundary=new WebAssembly.Global({value:"i32",mutable:true},0);')
 getter=''' get scalarAdmission(){
  const bounds={maximum:this.#layout.maximumPages};
  for(const [prefix,role] of [['v','vstack'],['t','temp'],['c','control'],['l','bindings']]){
   const r=this.#region(role);bounds[prefix+'0']=r.start;bounds[prefix+'1']=r.end;
  }
  return Object.freeze({boundary:this.#scalarBoundary,bounds:Object.freeze(bounds)});
 }
'''
 s=replace(s,' get tcr(){',getter+' get tcr(){')
 s=replace(s,'this.#boundary=true;try{','this.#boundary=true;this.#scalarBoundary.value=1;try{')
 s=replace(s,'finally{this.#boundary=false;}','finally{this.#boundary=false;this.#scalarBoundary.value=0;}')
 p.write_text(s)
 s=(ROOT/'runtime/wasm32/floating-capabilities.mjs').read_text()
 s=replace(s,"import {lispFloatService} from './service.mjs';","import {lispFloatService} from './service.mjs';\nimport {scalarFloatService} from './scalar-service.mjs';")
 s=replace(s,'floating:lispFloatService(floating)','floating:options.scalarBytes?scalarFloatService(floating):lispFloatService(floating)')
 (out/'floating-capabilities.mjs').write_text(s)
 shutil.copy(HERE/'scalar-service.mjs',out/'scalar-service.mjs')
if __name__=='__main__':
 import sys
 derive(Path(sys.argv[1]))
