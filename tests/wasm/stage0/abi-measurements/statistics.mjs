import assert from 'node:assert/strict';
import {rng} from './workloads.mjs';
const geometric=xs=>Math.exp(xs.reduce((a,x)=>a+Math.log(x),0)/xs.length);
const quantile=(a,p)=>a[Math.floor((a.length-1)*p)];
export function summarize(trials,policy,seed) {
  const candidates=['C','C4','B'],groups=new Map();
  for(const r of trials) {
    assert.ok(candidates.includes(r.candidate)&&Number.isInteger(r.trial)&&r.trial>=0);
    assert.equal(r.workloads.length,8);assert.deepEqual(r.workloads.map(w=>w.workload),[0,1,2,3,4,5,6,7]);
    assert.ok(r.workloads.every(w=>[w.ns_per_iteration,w.warmup_ms,w.sample_ms].every(x=>Number.isFinite(x)&&x>0)),'invalid timing or duration');
    if(!groups.has(r.trial))groups.set(r.trial,new Map());
    assert.ok(!groups.get(r.trial).has(r.candidate),'duplicate trial candidate');groups.get(r.trial).set(r.candidate,r);
  }
  const paired=[...groups.values()];assert.ok(paired.length>0);
  for(const row of paired)assert.deepEqual([...row.keys()].sort(),[...candidates].sort(),'missing paired candidate');
  const point=Object.fromEntries(candidates.map(c=>[c,geometric(paired.flatMap(row=>row.get(c).workloads.map(w=>w.ns_per_iteration)))]));
  const best=[...candidates].sort((a,b)=>point[a]-point[b])[0],random=rng(seed);
  const ratios=Object.fromEntries(candidates.map(c=>[c,paired.map(row=>geometric(row.get(c).workloads.map((w,i)=>w.ns_per_iteration/row.get(best).workloads[i].ns_per_iteration)))]));
  const bootstrap=Object.fromEntries(candidates.map(c=>[c,[]]));
  for(let b=0;b<10000;b++) {
    const indices=Array.from({length:paired.length},()=>random()%paired.length);
    for(const c of candidates)bootstrap[c].push(geometric(indices.map(i=>ratios[c][i])));
  }
  const estimates=Object.fromEntries(candidates.map(c=>{
    bootstrap[c].sort((a,b)=>a-b);const ratio=geometric(ratios[c]);
    const ci=[quantile(bootstrap[c],.025),quantile(bootstrap[c],.975)];
    return [c,{runtime_ratio_to_point_best:ratio,confidence_interval:ci,relative_half_width:(ci[1]-ci[0])/(2*ratio)}];
  }));
  const reasons=[];
  if(paired.length<policy.minimum_independent_trials)reasons.push('fewer than 30 independent paired trials');
  if(trials.some(t=>t.workloads.some(w=>w.warmup_ms<policy.minimum_warmup_ms_per_workload)))reasons.push('warmup below policy minimum');
  if(trials.some(t=>t.workloads.some(w=>w.sample_ms<policy.minimum_sample_ms_per_workload)))reasons.push('samples below policy minimum');
  if(Object.values(estimates).some(e=>e.relative_half_width>policy.maximum_relative_confidence_interval_half_width))reasons.push('confidence interval exceeds policy bound');
  return {paired_trials:paired.length,point_best:best,estimates,bootstrap_resamples:10000,seed,
    resampling_unit:'whole independent trial, preserving every candidate and all eight workload pairs',
    statistical_gaps:reasons,selection:'NO_SELECTION',
    selection_gaps:['new implementation requires independent review','representative matrix and census weights absent',
      'engine and complete-contract prerequisites missing','product budgets and browser/startup/scale evidence absent',
      'dynamic root-store/reload counts, C-stack high-water and resident Worker memory unavailable']};
}
