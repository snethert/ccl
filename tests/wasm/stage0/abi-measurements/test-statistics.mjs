import assert from 'node:assert/strict';
import fs from 'node:fs';
import {summarize} from './statistics.mjs';
const policy=JSON.parse(fs.readFileSync(new URL('../../../../doc/WASM/stage0/benchmarks.json',import.meta.url)));
const make=(n=30)=>Array.from({length:n},(_,trial)=>['C','C4','B'].map(candidate=>({trial,candidate,
  workloads:Array.from({length:8},(_,workload)=>({workload,ns_per_iteration:(workload+1)*(trial+1)*({C:2,C4:3,B:1}[candidate]),warmup_ms:1000,sample_ms:250}))}))).flat();
const checks=[];
function check(name,body){body();checks.push({name,status:'PASS'});}
check('known paired ratios despite common trial drift',()=>{
  const r=summarize(make(),policy,11);assert.equal(r.point_best,'B');
  for(const [c,want] of Object.entries({C:2,C4:3,B:1}))for(const x of [r.estimates[c].runtime_ratio_to_point_best,...r.estimates[c].confidence_interval])assert.ok(Math.abs(x-want)<1e-10);
  assert.deepEqual(r.statistical_gaps,[]);assert.equal(r.selection,'NO_SELECTION');assert.ok(r.selection_gaps.length);
});
check('seeded bootstrap reproduction',()=>assert.deepEqual(summarize(make(),policy,17),summarize(make(),policy,17)));
check('missing candidate rejected',()=>assert.throws(()=>summarize(make().slice(1),policy,1),/missing paired candidate/));
check('duplicate candidate rejected',()=>assert.throws(()=>summarize([...make(),make()[0]],policy,1),/duplicate trial candidate/));
check('missing workload rejected',()=>{const a=make();a[0].workloads.pop();assert.throws(()=>summarize(a,policy,1));});
check('nonpositive timing rejected',()=>{const a=make();a[0].workloads[0].ns_per_iteration=0;assert.throws(()=>summarize(a,policy,1));});
check('invalid timing rejected',()=>{const a=make();a[0].workloads[0].ns_per_iteration=NaN;assert.throws(()=>summarize(a,policy,1));});
check('inner iterations cannot replace independent trials',()=>assert.ok(summarize(make(3),policy,1).statistical_gaps.some(x=>x.includes('30 independent'))));
check('insufficient warmup and samples remain gaps',()=>{const a=make();a[0].workloads[0].warmup_ms=999;a[0].workloads[0].sample_ms=249;assert.equal(summarize(a,policy,1).statistical_gaps.length,2);});
check('invalid durations rejected',()=>{const a=make();a[0].workloads[0].sample_ms=NaN;assert.throws(()=>summarize(a,policy,1),/invalid timing or duration/);});
console.log(JSON.stringify({status:'PASS',controls:checks},null,2));
