#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {build,repo,sha,fileSha,save} from './build.mjs';
import {execute,positives,negatives} from './cases.mjs';

const pos=process.argv.indexOf('--output');
if(pos<0||!process.argv[pos+1])throw Error('usage: node tests/wasm/stage0/debug-frames/run.mjs --output EMPTY_DIRECTORY');
const out=path.resolve(process.argv[pos+1]);
if(out===repo||out.startsWith(repo+path.sep))throw Error('use an output directory outside the checkout');
fs.mkdirSync(out,{recursive:true});assert.equal(fs.readdirSync(out).length,0,'never overwrite or mix evidence runs');
fs.mkdirSync(path.join(out,'cases'));fs.mkdirSync(path.join(out,'quarantine'));
const inventoryPath=path.join(repo,'doc/WASM/stage0/inventory.json');
const inventory=JSON.parse(fs.readFileSync(inventoryPath)),sourceRevision=inventory.source_revision;
const revision=spawnSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'});assert.equal(revision.status,0);
const checkoutRevision=revision.stdout.trim();
assert.equal(spawnSync('git',['merge-base','--is-ancestor',sourceRevision,checkoutRevision],{cwd:repo}).status,0);
fs.copyFileSync(inventoryPath,path.join(out,'inventory.json'));
const changed=spawnSync('git',['ls-files','--modified','--others','--exclude-standard','-z'],{cwd:repo,encoding:'utf8'});assert.equal(changed.status,0);
save(path.join(out,'source-state.json'),{revision:sourceRevision,checkout_revision:checkoutRevision,author:'Codex',
  inputs:changed.stdout.split('\0').filter(Boolean).sort().map(p=>({path:p,sha256:fs.existsSync(path.join(repo,p))?fileSha(path.join(repo,p)):'DELETED'}))});
const started=new Date().toISOString();
const report={version:1,source_revision:sourceRevision,inventory_sha256:fileSha(inventoryPath),
  scope:'Hand-built logical debugger-frame slice S0-LL23-b, with freshly executed C boundary and integrated-runtime prerequisites. Not a CCL debugger, D3 selection or full Stage 0 acceptance.',results:[],failure:null};
let built,cases;
try {
  const args=['tests/wasm/stage0/integrated-runtime/run.mjs','--output',path.join(out,'prerequisites')];
  const prerequisite=spawnSync(process.execPath,args,{cwd:repo,encoding:'utf8',timeout:180000});
  save(path.join(out,'prerequisite-command.json'),{executable:process.execPath,args,status:prerequisite.status,signal:prerequisite.signal,error:prerequisite.error?.message,stdout:prerequisite.stdout,stderr:prerequisite.stderr});
  if(prerequisite.error||prerequisite.signal||prerequisite.status!==0)throw Error('integrated-runtime prerequisites failed');
  const prior=JSON.parse(fs.readFileSync(path.join(out,'prerequisites/results.json')));
  assert.equal(prior.inventory_sha256,report.inventory_sha256);
  assert.deepEqual(prior.results.map(r=>[r.id,r.status]),['S0-LL13-c','S0-LL19-b','S0-LL20-a','S0-LL20-b','S0-LL20-c'].map(id=>[id,'PASS']));
  report.results.push(...prior.results.map(r=>({...r,contract_binding:r.contract_binding?{...r.contract_binding,inventory_path:'prerequisites/'+r.contract_binding.inventory_path}:undefined,artifacts:r.artifacts.map(a=>({...a,path:'prerequisites/'+a.path}))})));
  built=build(out,path.join(out,'prerequisites'));
  cases=await execute(built,(name,value,negative)=>save(path.join(out,negative?'quarantine':'cases',name+'.json'),value));
  assert.equal(cases.filter(c=>c.status==='PASS').length,positives.length);
  assert.equal(cases.filter(c=>c.status==='REJECTED').length,negatives.length);
  save(path.join(out,'execution-summary.json'),{positive_cases:positives.length,rejected_controls:negatives.length,
    prerequisites:JSON.parse(fs.readFileSync(path.join(out,'prerequisites/execution-summary.json'))),
    frame_bytes:160,frame_capacity:built.frameSchema.frame_capacity,reply_bytes:built.frameSchema.reply_bytes,reply_capacity:built.frameSchema.reply_capacity,
    inspection_replies:cases.filter(c=>!c.negative).reduce((n,c)=>n+c.inspection_replies.length,0)});
} catch(error) {report.failure=error.stack;save(path.join(out,'failure.json'),{error:error.stack});console.error(error.stack);}
function files(dir=out,prefix='') {
  return fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name)).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name),prefix+e.name+'/'):[prefix+e.name]);
}
const inputs=files().filter(p=>p.startsWith('source/')).map(p=>({path:p,sha256:fileSha(path.join(out,p))}));
const artifacts=files().map(p=>({path:p,sha256:fileSha(path.join(out,p)),role:p.startsWith('quarantine/')?'negative_control':
  /(?:schema|source-sites)\.json$/.test(p)?'schema':p.startsWith('source/')?'test':/\.(wasm|o)$/.test(p)?'implementation':'log'}));
const status=report.failure?'FAIL':'PASS';
report.results.push({id:'S0-LL23-b',variant:'full',status,evidence_kind:'HAND-BUILT WASM EXECUTION',source_revision:sourceRevision,
  test_revision:sha(Buffer.from(JSON.stringify(inputs))),toolchain:{...built?.versions,os:os.platform(),release:os.release(),architecture:os.arch(),
    cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,node_flags:process.execArgv},
  engine:`Node ${process.version} / V8 ${process.versions.v8}`,timestamp:started,
  command:`node tests/wasm/stage0/debug-frames/run.mjs --output ${out}`,
  configuration:{profile:'shared wasm32; admitted self-inspection at declared sites',layout_version:1,build_id:built?.buildId,
    policies:[1,3],value_counts:[0,6],collector:'unmodified reviewed cons-only moving collector; poison old space',
    source_map:'source-sites.json',handle_context:built?.frameSchema.handle_context},
  seed:0,substitutions:[],skips:[],review_disposition:'NOT_REVIEWED',assertions:[{id:'S0-LL23-b:contract',status}],
  cases:cases?.map(c=>({name:c.name,status:c.status,negative:c.negative})),artifacts});
save(path.join(out,'execution-results.json'),report);
const binding=spawnSync('python3',[path.join(repo,'doc/WASM/tools/bind-evidence.py'),
  '--results',path.join(out,'execution-results.json'),'--inventory',path.join(out,'inventory.json'),
  '--output',path.join(out,'results.json'),'--fresh'],{cwd:repo,encoding:'utf8',timeout:30000});
if(binding.error||binding.status!==0)throw Error('evidence binding failed: '+(binding.stderr||binding.error));console.log(`${status} S0-LL23-b; evidence: ${out}; full Stage 0 remains incomplete.`);
process.exitCode=report.failure?1:0;
