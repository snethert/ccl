#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {build,repo,sha,save} from './build.mjs';
import {positives,controls,executeCase} from './cases.mjs';
const flag=process.argv.indexOf('--output');
if(flag<0||!process.argv[flag+1])throw Error('usage: node tests/wasm/stage0/dynamic-call/run.mjs --output EMPTY_DIRECTORY');
const out=path.resolve(process.argv[flag+1]);
if(out===repo||out.startsWith(repo+path.sep))throw Error('retain evidence outside the source checkout');
fs.mkdirSync(out,{recursive:true});assert.equal(fs.readdirSync(out).length,0,'never overwrite an evidence run');
const fileSha=p=>sha(fs.readFileSync(p));
const inventoryPath=path.join(repo,'doc/WASM/stage0/inventory.json'),inventory=JSON.parse(fs.readFileSync(inventoryPath));
fs.copyFileSync(inventoryPath,path.join(out,'inventory.json'));
const git=(args)=>{const r=spawnSync('git',args,{cwd:repo,encoding:'utf8'});assert.equal(r.status,0);return r.stdout;};
const checkout=git(['rev-parse','HEAD']).trim();git(['merge-base','--is-ancestor',inventory.source_revision,checkout]);
save(path.join(out,'source-state.json'),{source_revision:inventory.source_revision,checkout_revision:checkout,author:'Codex',
  changes:git(['ls-files','--modified','--others','--exclude-standard','-z']).split('\0').filter(Boolean).sort().map(p=>({path:p,sha256:fs.existsSync(path.join(repo,p))?fileSha(path.join(repo,p)):'DELETED'}))});
const ids=['S0-LL04-a','S0-LL04-b','S0-LL13-a','S0-LL05-a','S0-LL05-b','S0-LL05-c','S0-LL05-d','S0-LL21-b'];
const report={version:1,source_revision:inventory.source_revision,inventory_sha256:fileSha(inventoryPath),
  scope:'Bounded hand-built C/C4/B correctness with freshly executed frame/runtime/boundary prerequisites. No ABI selection, generated code, production capacity or project acceptance.',results:[],failure:null};
const started=new Date().toISOString(),results=[];let built;
try {
  const args=['tests/wasm/stage0/debug-frames/run.mjs','--output',path.join(out,'prerequisites')];
  const r=spawnSync(process.execPath,args,{cwd:repo,encoding:'utf8',timeout:240000});
  save(path.join(out,'prerequisite-command.json'),{executable:process.execPath,args,status:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr});
  assert.equal(r.status,0,'fresh prerequisite execution failed');
  const prior=JSON.parse(fs.readFileSync(path.join(out,'prerequisites/results.json')));
  assert.deepEqual(prior.results.map(r=>[r.id,r.status]),['S0-LL13-c','S0-LL19-b','S0-LL20-a','S0-LL20-b','S0-LL20-c','S0-LL23-b'].map(id=>[id,'PASS']));
  report.results.push(...prior.results.map(r=>({...r,contract_binding:{...r.contract_binding,inventory_path:'prerequisites/'+r.contract_binding.inventory_path},artifacts:r.artifacts.map(a=>({...a,path:'prerequisites/'+a.path}))})));
  const kernelRoot=path.join(out,'prerequisites/prerequisites');
  built=build(path.join(out,'build'),kernelRoot);
  for(const candidate of Object.keys(built.schema.candidates)) {
    for(const test of positives) {
      const r=await executeCase(built,candidate,test);results.push(r);const dir=path.join(out,'cases',candidate);fs.mkdirSync(dir,{recursive:true});save(path.join(dir,r.name+'.json'),r);
      console.log(candidate,r.status,r.name);assert.equal(r.status,'PASS',r.error||r.name);
    }
    for(const control of controls) {
      const dir=path.join(out,'quarantine',candidate,control.name);fs.mkdirSync(dir,{recursive:true});
      const modified=control.mutant?build(path.join(dir,'build'),kernelRoot,{candidate,mutant:control.mutant}):built;
      const test=positives.find(t=>t.name===control.test);assert.ok(test,'unknown control target');
      const r=await executeCase(modified,candidate,test,control);results.push(r);
      save(path.join(dir,'result.json'),{...r,injection:{...control,pattern:control.pattern?.source}});
      console.log(candidate,r.status,r.name);assert.equal(r.status,'REJECTED',r.error||'control escaped the oracle');
    }
  }
  assert.equal(results.filter(r=>r.status==='PASS').length,positives.length*3);
  assert.equal(results.filter(r=>r.status==='REJECTED').length,controls.length*3);
  for(const id of ids)assert.ok(id==='S0-LL04-b'?results.some(r=>r.name==='one-sided-emitted-cons-swap'&&r.status==='REJECTED'):results.some(r=>r.id===id&&r.status==='PASS'),'uncovered inventory assertion '+id);
  save(path.join(out,'execution-summary.json'),{candidates:Object.keys(built.schema.candidates),positive_cases_per_candidate:positives.length,rejected_controls_per_candidate:controls.length,
    total_positive_cases:positives.length*3,total_rejected_controls:controls.length*3,prerequisites:JSON.parse(fs.readFileSync(path.join(out,'prerequisites/execution-summary.json'))),
    bounds:built.schema,memory_bytes:1048576,live_workers:3,ownership_slots:4,
    disclaimer:'Counts demonstrate correctness only at the stated bounds. No performance, scalability, browser or generated-code claim.'});
} catch(e) {report.failure=e.stack;save(path.join(out,'failure.json'),{error:e.stack});console.error(e.stack);}
function files(dir=out,prefix='') {return fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name)).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name),prefix+e.name+'/'):[prefix+e.name]);}
const all=files(),inputs=all.filter(p=>p.startsWith('build/source/')).map(p=>({path:p,sha256:fileSha(path.join(out,p))}));
const artifacts=all.map(p=>({path:p,sha256:fileSha(path.join(out,p)),role:p.startsWith('quarantine/')?'negative_control':/schema|metadata|entries|inventory/.test(p)?'schema':p.includes('/source/')?'test':/\.(wasm|o)$/.test(p)?'implementation':'log'}));
const status=report.failure?'FAIL':'PASS';
for(const id of ids)for(const variant of inventory.tests.find(t=>t.id===id).variants) {
  report.results.push({id,variant,status,evidence_kind:'HAND-BUILT WASM EXECUTION',source_revision:inventory.source_revision,test_revision:sha(Buffer.from(JSON.stringify(inputs))),
    toolchain:{...built?.versions,os:os.platform(),release:os.release(),architecture:os.arch(),cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,node_flags:process.execArgv},
    engine:`Node ${process.version} / V8 ${process.versions.v8}`,timestamp:started,command:`node tests/wasm/stage0/dynamic-call/run.mjs --output ${out}`,
    configuration:{contract:'build/source/dynamic-call/schema.json',candidate:variant==='full'?'all three':variant.slice(5),generic_only:true,arguments:[0,32],values:[0,6],tail_iterations:100000,
      module_granularity:'one emitted callable definition per module plus support and runtime; correctness packaging only',review:'new ABI source and linked kernel require independent review'},
    seed:0,substitutions:[],skips:[],review_disposition:'NOT_REVIEWED',assertions:[{id:id+':contract',status}],
    corpus:results.map(r=>({name:r.name,candidate:r.candidate,status:r.status,negative:r.negative})),artifacts});
}
save(path.join(out,'execution-results.json'),report);
const binding=spawnSync('python3',[path.join(repo,'doc/WASM/tools/bind-evidence.py'),'--results',path.join(out,'execution-results.json'),'--inventory',path.join(out,'inventory.json'),'--output',path.join(out,'results.json'),'--fresh'],{cwd:repo,encoding:'utf8',timeout:30000});
assert.equal(binding.status,0,binding.stderr||'evidence binding failed');
console.log(`${status}: C/C4/B corpus; Stage 0 remains incomplete; ${out}`);process.exitCode=report.failure?1:0;
