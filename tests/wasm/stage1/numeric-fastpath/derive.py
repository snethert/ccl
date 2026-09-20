"""Derive the runtime-only fast-path proposal from the integrated LL16 runtime."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def replace(s,a,b):
 assert s.count(a)==1, a
 return s.replace(a,b)
def derive(out):
 out.mkdir(parents=True,exist_ok=True)
 s=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
 s=replace(s,' #memory;#collector;', ' #roles=new Map();\n #memory;#collector;')
 s=replace(s," #region(role){const rows=this.#layout.regions.filter(r=>r.role===role);need(rows.length===1,'region '+role);return rows[0];}"," #region(role){if(this.#roles.has(role))return this.#roles.get(role);const rows=this.#layout.regions.filter(r=>r.role===role);need(rows.length===1,'region '+role);this.#roles.set(role,rows[0]);return rows[0];}")
 start=s.index(' #validate(){');end=s.index('  const slots=this.#imageSlots();',start)
 live=s[start:end].replace(' #validate(){',' #validateLive(){').replace('this.#refresh();const spaces=', 'this.#refresh();const view=this.#view,t=o=>view.getUint32(this.#layout.tcr+o,true);const spaces=').replace('this.#t(', 't(').replace('this.view.byteLength','view.byteLength')
 s=s[:start]+live+"  return active;\n }\n #validate(){\n  const active=this.#validateLive();\n"+s[end:]
 s=replace(s,'collect(){this.#requireBoundary();const {active}=this.#validate();','collect(){this.#requireBoundary();const active=this.#validateLive();')
 s=replace(s,"this.#requireBoundary();need(integer(bytes)&&bytes>0&&bytes%8===0,'allocation request');this.#validate();", "this.#requireBoundary();need(integer(bytes)&&bytes>0&&bytes%8===0,'allocation request');\n  // No root enumeration is needed until copying. Mutable owner state is still\n  // checked before a fast assurance; collection re-inventories the live image.\n  this.#validateLive();")
 (out/'collector-owner.mjs').write_text(s)
 s=(ROOT/'runtime/wasm32/float-service.mjs').read_text()
 s=replace(s,' const view=()=>new DataView(memory.buffer),get=', ' let cachedView=new DataView(memory.buffer);\n const view=()=>{const b=memory.buffer;if(cachedView.buffer!==b)cachedView=new DataView(b);return cachedView;},get=')
 (out/'float-service.mjs').write_text(s)
 s=(ROOT/'runtime/wasm32/service.mjs').read_text()
 s=replace(s,' const get=p=>new DataView(memory.buffer).getUint32(p,true),set=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);', ' const limits={32:1n<<128n,64:1n<<1024n};\n let cachedView=new DataView(memory.buffer);\n const view=()=>{const b=memory.buffer;if(cachedView.buffer!==b)cachedView=new DataView(b);return cachedView;};\n const get=p=>view().getUint32(p,true),set=(p,v)=>view().setUint32(p,v,true);')
 s=s.replace('new DataView(memory.buffer).getFloat','view().getFloat')
 s=replace(s,'  const limit=1n<<BigInt(width===32?128:1024);','  const limit=limits[width];')
 (out/'service.mjs').write_text(s)
if __name__=='__main__':
 import sys
 derive(Path(sys.argv[1]))
