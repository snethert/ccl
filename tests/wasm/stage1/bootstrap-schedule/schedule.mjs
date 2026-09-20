// Synchronous trusted-owner initializer schedule. This does not select a closure.
import {sha,validate} from './loader.mjs';
import {snapshotBytes} from './bytes.mjs';
const need=(value,reason)=>{if(!value)throw Error(reason);};
const uint=x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff;
export class BootstrapSchedule {
  #memory; #plan; #modules; #order; #state='NEW'; #events=[];
  constructor({memory,plan,digest,modules}) {
    need(memory instanceof WebAssembly.Memory,'MEMORY');
    const p=structuredClone(plan);
    need(sha(JSON.stringify(p))===digest,'PLAN_DIGEST');
    need(p.version===1&&p.initializers.length>0&&p.initializers.length<=4096,'PLAN_VERSION');
    const extent=(a,n)=>uint(a)&&a%4===0&&Number.isSafeInteger(n)&&n>0&&a+n<=memory.buffer.byteLength;
    need(extent(p.state.start,p.state.size)&&p.state.size%4===0,'STATE_EXTENT');
    const address=a=>extent(a,4)&&a>=p.state.start&&a+4<=p.state.start+p.state.size;
    need(extent(p.ready,12)&&(p.ready+12<=p.state.start||p.ready>=p.state.start+p.state.size),'READY_EXTENT');
    const names=new Set(),ids=new Map(),cells=new Set(),tokens=new Set();
    for(const r of p.initializers){
      need(typeof r.id==='string'&&r.id.length>0&&!ids.has(r.id),'INITIALIZER_ID');ids.set(r.id,r);
      need(typeof r.module==='string'&&!names.has(r.module),'MODULE_UNIQUE');names.add(r.module);
      need(Number.isInteger(r.phase)&&r.phase>=0&&r.phase<=2,'PHASE');
      need(Array.isArray(r.prerequisites)&&new Set(r.prerequisites).size===r.prerequisites.length,'PREREQUISITE_SET');
      need(address(r.completion.address)&&uint(r.completion.value)&&r.completion.value!==0&&!cells.has(r.completion.address)&&!tokens.has(r.completion.value),'COMPLETION');
      cells.add(r.completion.address);tokens.add(r.completion.value);
      for(const list of [r.before,r.after]){
        need(Array.isArray(list)&&new Set(list.map(x=>x.address)).size===list.length,'STATE_ASSERTIONS');
        for(const x of list)need(address(x.address)&&uint(x.value),'STATE_ASSERTION');
      }
    }
    for(const r of p.initializers){
      for(const x of [...r.before,...r.after])need(!cells.has(x.address),'STATE_COMPLETION_ALIAS');
      for(const id of r.prerequisites)need(ids.has(id)&&ids.get(id).phase<=r.phase,'PREREQUISITE');
    }
    need(p.initializers.some(r=>r.phase===0)&&p.initializers.some(r=>r.phase===2),'PHASE_SET');
    // Stable topological ordering within each phase, never source order alone.
    const ordered=[],done=new Set();
    for(let phase=0;phase<=2;phase++){
      let pending=p.initializers.filter(r=>r.phase===phase);
      while(pending.length){
        const next=pending.find(r=>r.prerequisites.every(id=>done.has(id)));
        need(next,'INITIALIZER_CYCLE');ordered.push(next);done.add(next.id);pending=pending.filter(r=>r!==next);
      }
    }
    need(modules.length===names.size,'MODULE_SET');
    const copy=new Map();
    for(const m of modules){
      need(names.has(m.name)&&!copy.has(m.name)&&m.record.name===m.name,'MODULE_SET');
      const record=structuredClone(m.record),bytes=snapshotBytes(m.bytes);
      const r=p.initializers.find(r=>r.module===m.name);
      need(record.sha256===r.sha256,'MODULE_IDENTITY');validate(bytes,record);
      copy.set(m.name,{name:m.name,record,bytes});
    }
    this.#memory=memory;this.#plan=p;this.#modules=copy;this.#order=ordered;
  }
  get state(){return this.#state;}
  get events(){return structuredClone(this.#events);}
  run(install) {
    need(this.#state==='NEW','SCHEDULE_STATE');
    need(typeof install==='function','INSTALLER');
    const p=this.#plan,completed=[],persistent=new Map(),get=a=>new DataView(this.#memory.buffer).getUint32(a,true);
    const assertWords=(rows,reason)=>{for(const x of rows)need(get(x.address)===x.value,reason);};
    const intact=()=>{
      for(const r of completed)need(get(r.completion.address)===r.completion.value,'COMPLETION_CLOBBER');
      for(const [address,value]of persistent)need(get(address)===value,'STATE_CLOBBER');
      need([0,4,8].every(o=>get(p.ready+o)===0),'EARLY_READY');
    };
    this.#state='RUNNING';
    try {
      need(p.initializers.every(r=>get(r.completion.address)===0)&&[0,4,8].every(o=>get(p.ready+o)===0),'NOT_FRESH');
      for(const r of this.#order){
        intact();
        if(r.phase>0)need(p.initializers.filter(x=>x.phase===0).every(x=>completed.includes(x)),'LOADER_NOT_SEEDED');
        need(r.prerequisites.every(id=>completed.some(x=>x.id===id)),'PREREQUISITE_INCOMPLETE');
        assertWords(r.before,'PRECONDITION');
        // Only installation for this phase is permitted. Bytes are private copies.
        const m=this.#modules.get(r.module);
        const invoke=install({name:m.name,record:structuredClone(m.record),bytes:snapshotBytes(m.bytes)},structuredClone(r));
        need(typeof invoke==='function','INSTALL_RESULT');
        this.#events.push({id:r.id,phase:r.phase,event:'installed'});
        intact();assertWords(r.before,'PRECONDITION');
        need(get(r.completion.address)===0,'PREWRITTEN_COMPLETION');
        this.#events.push({id:r.id,phase:r.phase,event:'entered'});
        const result=invoke();
        need(result===undefined,'SYNCHRONOUS_INITIALIZER');
        need(get(r.completion.address)===r.completion.value,'COMPLETION_MISSING');
        assertWords(r.after,'POSTCONDITION');
        for(const x of r.after)persistent.set(x.address,x.value);
        completed.push(r);intact();
        this.#events.push({id:r.id,phase:r.phase,event:'completed'});
      }
      need(completed.length===p.initializers.length,'INCOMPLETE');intact();
      const view=new DataView(this.#memory.buffer);
      view.setUint32(p.ready+4,completed.length,true);
      view.setUint32(p.ready+8,parseInt(sha(JSON.stringify(p)).slice(0,8),16),true);
      view.setUint32(p.ready,1,true); // publish last, synchronous single-Worker boundary
      this.#state='READY';return this.events;
    }catch(error){this.#state='FAILED';this.#events.push({event:'failed',reason:error.message??'WASM_EXCEPTION'});throw error;}
  }
}
