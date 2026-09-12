#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {build,repo,sha,save} from './build.mjs';
import {positives,controls,target,executeCase} from './cases.mjs';
import {ABIHarness} from './harness.mjs';
import {schedule,installSchedule,batch,workloads,rng,shuffle} from './workloads.mjs';
import {summarize} from './statistics.mjs';
import {resources} from './resources.mjs';

const flags=['--liftoff-only','--no-wasm-tier-up','--no-wasm-lazy-compilation'];
assert.deepEqual([...process.execArgv].sort(),[...flags].sort(),'run with the three documented engine flags');
assert.equal(os.platform(),'darwin','macOS reference host required');
const args=process.argv.slice(2),allowed=new Set(['--output','--trials','--warmup-ms','--sample-ms','--seed']);
assert.equal(args.length%2,0,'flags require values');const options={};
for(let i=0;i<args.length;i+=2){assert.ok(allowed.has(args[i])&&!(args[i] in options),'unknown or duplicate argument');options[args[i]]=args[i+1];}
assert.ok(options['--output'],'--output EMPTY_DIRECTORY is required');
const out=path.resolve(options['--output']);assert.ok(out!==repo&&!out.startsWith(repo+path.sep));
fs.mkdirSync(out,{recursive:true});assert.equal(fs.readdirSync(out).length,0,'never overwrite evidence');
const numeric=(name,fallback,max)=>{const n=Number(options[name]??fallback);assert.ok(Number.isInteger(n)&&n>0&&n<=max,name);return n;};
const config={trials:numeric('--trials',3,1000),warmup_ms:numeric('--warmup-ms',100,60000),sample_ms:numeric('--sample-ms',50,60000),
  seed:numeric('--seed',20260912,0xffffffff),packagings:['direct','same-instance','cross-instance'],
  status:'EXPLORATORY_NOT_SELECTION',tier:'V8 Liftoff only; tier-up and lazy compilation disabled',flags,
  independence:'fresh pair of Worker isolates and fresh shared heap for each candidate within each independently seeded trial',
  installation:'all eight callable definitions installed eagerly before any timed batch; no lazy requests in timing',
  scope:'Eight hand-built definitions, two live Workers, cons-only 4 KiB semispace. No representative census, product budget, browser, production image, optimized tier or ABI selection claim.'};
save(out+'/configuration.json',config);
const fileSha=p=>sha(fs.readFileSync(p));
const inventoryPath=path.join(repo,'doc/WASM/stage0/inventory.json'),inventory=JSON.parse(fs.readFileSync(inventoryPath));
fs.copyFileSync(inventoryPath,out+'/inventory.json');
fs.copyFileSync(path.join(repo,'doc/WASM/stage0/benchmarks.json'),out+'/benchmarks.json');
fs.copyFileSync(path.join(repo,'doc/WASM/stage0/measurement-inventory.json'),out+'/measurement-inventory.json');
const policy=JSON.parse(fs.readFileSync(out+'/benchmarks.json'));
function command(executable,args,log,timeout=30000) {
  const r=spawnSync(executable,args,{cwd:repo,encoding:'utf8',timeout,maxBuffer:20*1024*1024});
  save(path.join(out,log),{executable,args,status:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr});
  assert.equal(r.status,0,r.stderr||r.error?.message);return r.stdout;
}
const checkout=command('git',['rev-parse','HEAD'],'checkout-command.json').trim();
const changed=command('git',['ls-files','--modified','--others','--exclude-standard','-z'],'source-command.json').split('\0').filter(Boolean);
save(out+'/source-state.json',{source_revision:inventory.source_revision,checkout_revision:checkout,author:'Codex',
  changes:changed.map(p=>({path:p,sha256:fs.existsSync(path.join(repo,p))?fileSha(path.join(repo,p)):'DELETED'}))});
command(process.execPath,['--v8-options'],'v8-options.json');
const started=new Date().toISOString(),cases=[],batches=[],trials=[],built={};let failure=null;
try {
  console.log('Executing the unchanged reviewed corpus and runtime prerequisites.');
  command(process.execPath,['tests/wasm/stage0/dynamic-call/run.mjs','--output',out+'/prerequisites'],'prerequisite-command.json',300000);
  const prior=JSON.parse(fs.readFileSync(out+'/prerequisites/results.json'));
  assert.equal(prior.results.length,24);assert.ok(prior.results.every(r=>r.status==='PASS'));
  const kernelRoot=out+'/prerequisites/prerequisites/prerequisites';
  for(const packaging of config.packagings) {
    built[packaging]=build(out+'/build/'+packaging,kernelRoot,{packaging});
    for(const candidate of ['C','C4','B']) {
      const base=out+'/correctness/'+packaging+'/'+candidate;fs.mkdirSync(base,{recursive:true});
      for(const test of positives) {
        const r=await executeCase(built[packaging],candidate,test);cases.push({...r,packaging});save(base+'/'+r.name+'.json',r);
        assert.equal(r.status,'PASS',r.error||r.name);
      }
      for(const control of controls) {
        const dir=base+'/quarantine/'+control.name;fs.mkdirSync(dir,{recursive:true});
        const modified=control.mutant?build(dir+'/build',kernelRoot,{candidate,packaging,mutant:control.mutant}):built[packaging];
        const r=await executeCase(modified,candidate,target(control),control);cases.push({...r,packaging});
        save(dir+'/result.json',{...r,injection:{...control,pattern:control.pattern?.source}});
        assert.equal(r.status,'REJECTED',r.error||'control escaped '+r.name);
      }
      const batchDir=base+'/batches';fs.mkdirSync(batchDir);
      for(let workload=0;workload<8;workload++) {
        const h=new ABIHarness(built[packaging],candidate),records=schedule(workload,config.seed);
        try {
          await h.reset();installSchedule(h,records);
          const result=await batch(h,records,32);const r={packaging,candidate,workload,status:'PASS',records,result};
          batches.push(r);save(batchDir+'/'+workload+'.json',r);
        } catch(e) {save(batchDir+'/'+workload+'-failure.json',{error:e.stack,record:h.failureRecord});throw e;}
        finally {await h.close();}
      }
      for(const [name,mutant,workload,code] of [
        ['unconsumed-result',{ignoreResult:true},0,null],
        ['duplicate-result-scanner',{duplicateResultRoot:true},0,931],
        ['stale-moved-self',{staleRoot:true},7,102]
      ]) {
        const dir=base+'/quarantine/batch-'+name;fs.mkdirSync(dir,{recursive:true});
        const modified=build(dir+'/build',kernelRoot,{candidate,packaging,mutant});
        const h=new ABIHarness(modified,candidate),records=schedule(workload,config.seed);let error,rejected=false;
        try {await h.reset();installSchedule(h,records);await batch(h,records,32);}
        catch(e) {error=e.stack;rejected=code?h.words&&h.word(h.global('failure_code'))===code:/BATCH_COMPLETE_RESULT_ORACLE/.test(error);}
        finally {await h.close();}
        const r={name:'batch-'+name,packaging,candidate,workload,mutant,status:rejected?'REJECTED':'FAIL',error,failure:h.failureRecord};
        batches.push(r);save(dir+'/result.json',r);assert.equal(r.status,'REJECTED','batch control escaped '+name);
      }
      save(base+'/resources.json',resources(built[packaging],candidate,out+'/build/'+packaging));
      console.log('QUALIFIED',packaging,candidate,positives.length+' cases',controls.length+' controls','8 batches + 3 batch controls');
    }
  }
  // Freeze and retain this synthetic matrix before timing. It is not the later
  // census-derived representative matrix required for a selection decision.
  const random=rng(config.seed),matrix=[];
  for(let trial=0;trial<config.trials;trial++) {
    const seed=random();
    for(const packaging of shuffle(config.packagings,random))matrix.push({trial,seed,packaging,
      candidates:shuffle(['C','C4','B'],random),workloads:shuffle([0,1,2,3,4,5,6,7],random)});
  }
  save(out+'/exploratory-matrix.json',{config,policy_sha256:fileSha(out+'/benchmarks.json'),matrix});
  for(const m of matrix)for(const candidate of m.candidates) {
    const dir=out+'/trials/'+m.packaging+'/'+m.trial+'/'+candidate;fs.mkdirSync(dir,{recursive:true});
    const h=new ABIHarness(built[m.packaging],candidate),row={...m,candidate,workloads:[]};
    try {
      await h.reset();save(dir+'/startup.json',{workers:h.actors.map(a=>a.configuration),ownership:h.map,
        scope:'fresh Worker isolates in an existing Node process; byte validation and compilation, no browser/network/image/cache milestone',
        memory_scope:'rss is process-wide, heapUsed/heapTotal identify each reporting Worker; no peak/resident-per-Worker claim'});
      for(const workload of m.workloads) {
        const records=schedule(workload,m.seed),chunk=workload===6||workload===7?32:256;
        installSchedule(h,records);save(dir+'/inputs-'+workload+'.json',records);
        const first=await batch(h,records,1,0),warm=[],samples=[];let offset=0,warmup_ms=0,sample_ms=0,iterations=0;
        while(warmup_ms<config.warmup_ms){const r=await batch(h,records,chunk,offset);warm.push(r);warmup_ms+=r.elapsed_ms;offset=(offset+chunk)&31;}
        while(sample_ms<config.sample_ms){const r=await batch(h,records,chunk,offset);samples.push(r);sample_ms+=r.elapsed_ms;iterations+=r.iterations;offset=(offset+chunk)&31;}
        const w={workload,name:workloads[workload],first_batch:first,warmup_ms,sample_ms,iterations,
          ns_per_iteration:sample_ms*1e6/iterations,warm,samples};row.workloads.push(w);save(dir+'/workload-'+workload+'.json',w);
      }
    } catch(e) {save(dir+'/failure.json',{error:e.stack,record:h.failureRecord});throw e;}
    finally {await h.close();}
    row.workloads.sort((a,b)=>a.workload-b.workload);trials.push(row);save(dir+'/trial.json',row);
    console.log('MEASURED',m.packaging,'trial',m.trial,candidate);
  }
  const summaries=Object.fromEntries(config.packagings.map(p=>[p,summarize(trials.filter(t=>t.packaging===p),policy,config.seed)]));
  save(out+'/measurement-summary.json',{status:'EXPLORATORY_MEASURED',policy_sha256:fileSha(out+'/benchmarks.json'),
    matrix_sha256:fileSha(out+'/exploratory-matrix.json'),summaries,
    measurement_ids:JSON.parse(fs.readFileSync(out+'/measurement-inventory.json')).measurements.map(m=>({id:m.id,status:'EXPLORATORY_ONLY',selection_qualified:false})),
    mandatory_path:'frame/root publication, cleanup, result ownership, graph observation, polls, boundary admission/parking and Wasm schedule counters remain charged',
    omitted_from_timing:'host inspection packets, assertions and protocol trace forwarding; correctness mode checks those against identical module bytes',
    selection:'NO_SELECTION'});
} catch(e) {failure=e.stack;save(out+'/failure.json',{error:failure});console.error(failure);}
save(out+'/execution-summary.json',{status:failure?'FAIL':'PASS',positive_cases:cases.filter(c=>c.status==='PASS').length,
  rejected_controls:cases.filter(c=>c.status==='REJECTED').length,positive_batches:batches.filter(b=>b.status==='PASS').length,
  rejected_batch_controls:batches.filter(b=>b.status==='REJECTED').length,trial_candidate_rows:trials.length,
  review_disposition:'NOT_REVIEWED',selection:'NO_SELECTION',scope:config.scope});
function files(dir=out,prefix='') {return fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name)).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name),prefix+e.name+'/'):[prefix+e.name]);}
const all=files(),inputs=all.filter(p=>p.startsWith('build/direct/source/')).map(p=>({path:p,sha256:fileSha(path.join(out,p))}));
const artifacts=all.map(p=>({path:p,sha256:fileSha(path.join(out,p)),role:p.includes('quarantine/')?'negative_control':p.includes('/source/')?'test':/\.(wasm|o)$/.test(p)?'implementation':'log'}));
const record={id:'S0-LL21-a',variant:'full',status:failure?'FAIL':'PASS',evidence_kind:'HAND-BUILT WASM EXECUTION',
  source_revision:inventory.source_revision,test_revision:sha(Buffer.from(JSON.stringify(inputs))),
  toolchain:{...built.direct?.versions,os:os.platform(),release:os.release(),architecture:os.arch(),cpu:os.cpus()[0]?.model,node_flags:process.execArgv},
  engine:`Node ${process.version} / V8 ${process.versions.v8}`,timestamp:started,command:[process.execPath,...process.execArgv,...process.argv.slice(1)].join(' '),
  configuration:config,seed:config.seed,substitutions:[],skips:[],review_disposition:'NOT_REVIEWED',
  assertions:[{id:'S0-LL21-a:contract',status:failure?'FAIL':'PASS'}],artifacts};
save(out+'/execution-results.json',{version:1,source_revision:inventory.source_revision,inventory_sha256:fileSha(out+'/inventory.json'),
  scope:'S0-LL21-a hand-built prebuilt-code publication; changed corpus and timings require review; no ABI selection.',results:[record]});
command('python3',['doc/WASM/tools/bind-evidence.py','--results',out+'/execution-results.json','--inventory',out+'/inventory.json','--output',out+'/results.json','--fresh'],'binding-command.json');
console.log(failure?'FAIL':'PASS',out,'NO_SELECTION');process.exitCode=failure?1:0;
