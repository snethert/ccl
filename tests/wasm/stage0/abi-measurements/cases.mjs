import assert from 'node:assert/strict';
import {positives as reviewedCases,controls as reviewedControls} from '../dynamic-call/cases.mjs';
import {ABIHarness} from './harness.mjs';

export const publicationCase={
  name:'publish-prebuilt-code-existing-and-late-worker',id:'S0-LL21-a',options:{lazyCodes:[11]},
  async run(h) {
    const published=await h.actors[0].simple('publish',[11]);
    const calls=[];
    for (const id of [1,2]) {
      if (id===2) await h.late();
      h.packets=[];h.prepare([7,11],{id});
      const r=await h.run(0,2,{id,published:true,collect:id!==1});
      assert.deepEqual(r.values.map(v=>h.describe(v)),[2540,{car:11},7,11,{car:511},2]);
      assert.deepEqual(r.result,[10160,6]);
      assert.equal(r.snapshot.publication.previously_installed,false,'first call was already installed');
      assert.equal(r.snapshot.publication.sha256,published.result.sha256);
      assert.ok(r.snapshot.events.some(e=>e.kind==='installed'&&e.code===11),'worker did not install published code');
      calls.push(h.evidence(r));
    }
    h.packets=[];h.prepare([7,11]);const old=await h.run(0,2);
    assert.deepEqual(old.values.map(v=>h.describe(v)),[1529,{car:10},7,11,{car:500},2]);
    return {published,calls,old:h.evidence(old)};
  }
};
export const positives=[...reviewedCases.map(t=>t.name==='apply-cycle-condition'
  ? {...t,name:'apply-circular-list-reaches-argument-capacity'} : t),publicationCase];
export const controls=[{name:'driver-digest-mismatch',options:{badDriverHash:true},test:'ordered-6',pattern:/DRIVER_DIGEST_MISMATCH/},...reviewedControls.map(c=>c.name==='duplicate-result-root-ownership'
  ? {...c,failureCode:931} : c.name==='stale-owned-result-count'?{...c,failureCode:932}:c),
  {name:'actual-same-signature-table-corruption',test:'role-registry',pattern:/ROLE_MISMATCH/},
  {name:'missing-prebuilt-publication',test:'publication-missing',pattern:/UNPUBLISHED_CODE/},
  {name:'corrupted-prebuilt-publication',test:'publication-digest',pattern:/PUBLICATION_DIGEST/}
];
export function target(control) {
  if (control.test==='role-registry') return {id:'S0-LL21-a',run:h=>h.actors[0].simple('corrupt-role')};
  if (control.test.startsWith('publication-')) return {
    id:'S0-LL21-a',options:{lazyCodes:[11]},async run(h) {
      if (control.test==='publication-digest') {
        await h.actors[0].simple('publish',[11]);
        const p=h.map.workers[0].publication.start+8;h.put(p,h.word(p)^1);
      }
      h.prepare([7,11],{id:1});return h.run(0,2,{id:1,published:true,collect:false});
    }
  };
  const test=positives.find(t=>t.name===control.test);assert.ok(test,'unknown control target');return test;
}

export async function executeCase(build,candidate,test,control) {
  const h=new ABIHarness(build,candidate,{...test.options,...control?.options});let evidence,error,rejected=false;
  try {await h.reset();evidence=await test.run(h);}
  catch(e) {
    error=e.stack;
    if(control) {
      if(control.failureCode)rejected=!!h.words&&h.word(h.global('failure_code'))===control.failureCode;
      else rejected=control.pattern.test(error)&&!/deadline|timed.out/.test(error);
      if(control.beforeEntry)rejected&&=h.failureRecord?.snapshot?.state.entry_count===0&&h.failureRecord?.snapshot?.entered===0;
    }
  } finally {await h.close();}
  return {name:control?.name||test.name,id:test.id,candidate,status:control?(rejected?'REJECTED':'FAIL'):error?'FAIL':'PASS',
    negative:!!control,error,evidence:evidence||{failure:h.failureRecord,packets:h.packets,io:h.io,collections:h.collections,
      failure_code:h.words&&h.word(h.global('failure_code'))}};
}
