#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { build, repo, sha, fileSha, save } from './build.mjs';
import { executeCases, randomized } from './cases.mjs';

const pos=process.argv.indexOf('--output');
if(pos<0||!process.argv[pos+1]) throw Error('usage: node tests/wasm/stage0/integrated-runtime/run.mjs --output EMPTY_DIRECTORY');
const out=path.resolve(process.argv[pos+1]);
if(out===repo||out.startsWith(repo+path.sep)) throw Error('use an output directory outside the checkout');
fs.mkdirSync(out,{recursive:true}); assert.equal(fs.readdirSync(out).length,0,'never overwrite or mix evidence runs');
fs.mkdirSync(path.join(out,'cases')); fs.mkdirSync(path.join(out,'quarantine'));
const inventoryPath=path.join(repo,'doc/WASM/stage0/inventory.json');
const policyPath=path.join(repo,'doc/WASM/stage0/benchmarks.json');
const revision=spawnSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'});
assert.equal(revision.status,0); const checkoutRevision=revision.stdout.trim();
const inventory=JSON.parse(fs.readFileSync(inventoryPath)); const sourceRevision=inventory.source_revision;
assert.equal(spawnSync('git',['merge-base','--is-ancestor',sourceRevision,checkoutRevision],{cwd:repo}).status,0,'checkout must descend from the pinned baseline');
const policy=JSON.parse(fs.readFileSync(policyPath));
assert.equal(policy.dedicated_host_progress_limits.rendezvous_timeout_ms,1000,'C wait deadline must match the frozen policy');
assert.equal(policy.dedicated_host_progress_limits.per_schedule_timeout_ms,5000,'scheduler deadline must match the frozen policy');
fs.copyFileSync(inventoryPath,path.join(out,'inventory.json'));fs.copyFileSync(policyPath,path.join(out,'benchmarks.json'));
const changed=spawnSync('git',['ls-files','--modified','--others','--exclude-standard','-z'],{cwd:repo,encoding:'utf8'});
assert.equal(changed.status,0);
save(path.join(out,'source-state.json'),{revision:sourceRevision,checkout_revision:checkoutRevision,inputs:changed.stdout.split('\0').filter(Boolean).sort().map(p=>({path:p,sha256:fs.existsSync(path.join(repo,p))?fileSha(path.join(repo,p)):'DELETED'}))});
const report={version:1,source_revision:sourceRevision,inventory_sha256:fileSha(inventoryPath),
  scope:'Hand-built S0-LL20-a/b/c integration, with freshly executed S0-LL13-c/S0-LL19-b prerequisites. Not full Stage 0 acceptance.',results:[],failure:null};
let built,cases,random;
const started=new Date().toISOString();
try {
  const args=['tests/wasm/stage0/runtime-boundary/run.mjs','--output',path.join(out,'prerequisites')];
  const prerequisite=spawnSync(process.execPath,args,{cwd:repo,encoding:'utf8',timeout:120000});
  save(path.join(out,'prerequisite-command.json'),{executable:process.execPath,args,status:prerequisite.status,signal:prerequisite.signal,error:prerequisite.error?.message,stdout:prerequisite.stdout,stderr:prerequisite.stderr});
  if(prerequisite.error||prerequisite.signal||prerequisite.status!==0) throw Error('C boundary prerequisites failed');
  const prior=JSON.parse(fs.readFileSync(path.join(out,'prerequisites/results.json')));
  assert.equal(prior.inventory_sha256,report.inventory_sha256);
  assert.deepEqual(prior.results.map(r=>[r.id,r.status]),[['S0-LL13-c','PASS'],['S0-LL19-b','PASS']]);
  report.results.push(...prior.results.map(r=>({...r,artifacts:r.artifacts.map(a=>({...a,path:'prerequisites/'+a.path}))})));
  built=build(out);
  const write=(name,value,negative)=>save(path.join(out,negative?'quarantine':'cases',name+'.json'),value);
  cases=await executeCases(built,write);
  random=await randomized(built,write,{seeds:policy.dedicated_host_progress_limits.random_schedule_seeds_minimum,limits:policy.dedicated_host_progress_limits});
  save(path.join(out,'execution-summary.json'),{positive_cases:cases.filter(c=>c.status==='PASS').length,
    rejected_controls:cases.filter(c=>c.status==='REJECTED').length,randomized_schedules:random.seeds,
    safepoint_latency_p99_ms:random.safepoint_latency_p99_ms,safepoint_latency_max_ms:random.safepoint_latency_max_ms,
    rendezvous_max_ms:random.rendezvous_max_ms});
} catch(error) {
  report.failure=error.stack; save(path.join(out,'failure.json'),{error:error.stack}); console.error(error.stack);
}
function files(dir=out,prefix='') {
  return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name),prefix+e.name+'/'):[prefix+e.name]);
}
const inputs=files().filter(p=>p.startsWith('source/')).map(p=>({path:p,sha256:fileSha(path.join(out,p))}));
const artifacts=files().map(p=>({path:p,sha256:fileSha(path.join(out,p)),role:p.startsWith('quarantine/')?'negative_control':p.startsWith('source/')?'test':/\.(wasm|o)$/.test(p)?'implementation':'log'}));
if(built) artifacts.push({path:'source/integrated-runtime/schema.json',sha256:fileSha(path.join(out,'source/integrated-runtime/schema.json')),role:'schema'});
for(const id of ['S0-LL20-a','S0-LL20-b','S0-LL20-c']) {
  const status=report.failure?'FAIL':'PASS';
  report.results.push({id,variant:'full',status,evidence_kind:'HAND-BUILT WASM EXECUTION',source_revision:sourceRevision,
    test_revision:sha(Buffer.from(JSON.stringify(inputs))),toolchain:{...built?.versions,os:os.platform(),release:os.release(),architecture:os.arch(),
      cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,node_flags:process.execArgv},
    engine:`Node ${process.version} / V8 ${process.versions.v8}`,timestamp:started,
    command:`node tests/wasm/stage0/integrated-runtime/run.mjs --output ${out}`,
    configuration:{profile:'shared wasm32; blocking Worker requests',collector:'bounded cons-only semispace copying; poison old space',
      schema_version:built?.schema.version,seed_range:[1,policy.dedicated_host_progress_limits.random_schedule_seeds_minimum],benchmark_policy_sha256:fileSha(policyPath)},
    seed:1,substitutions:[],skips:[],review_disposition:'NOT_REVIEWED',assertions:[{id:id+':contract',status}],
    cases:cases?.filter(c=>c.id===id).map(c=>({name:c.name,status:c.status})),artifacts});
  console.log(`${status} ${id}`);
}
save(path.join(out,'results.json'),report);
console.log(`Evidence: ${out}; full Stage 0 remains incomplete.`);
process.exitCode=report.failure?1:0;
