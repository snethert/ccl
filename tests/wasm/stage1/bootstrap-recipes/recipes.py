"""Account for every name in the requested cohort, including fixture names."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARENT=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-closure-r1'

def disposition(name):
    if name.startswith('CORE-') or name=='EQL':
        return 'fixture-or-primitive', 'Already used by the fixture; not an original CCL definition needing a recipe.'
    if name=='%SLOT-REF':
        return 'target-primitive', 'WASM32 callable primitive, already exercised by core-slot-access; not an unchanged native DEFUN.'
    if name.startswith('%SINGLE-FLOAT-') and name.endswith('!'):
        return 'paired-interface-covered', 'The pinned 64-bit image has the non-destructive single-float entry, not this 32-bit destructive entry. The existing 26-entry libm packet compares its value through that native counterpart. Do not invent a native destructive object or add exact-original execution credit.'
    if name in {'%16-RANDOM-BITS','%MRG31K3P'}:
        return 'lowering-needed', 'Real random state writes uint32 values above the target fixnum range; boxed uint32 stores are still refused. A zero-only state would not exercise a valid generator.'
    if name=='IS-COMBINABLE':
        return 'lowering-needed', 'The real Unicode bitmap uses bignum bitsets; variable LOGBITP over those bitsets is still a missing arithmetic path. Out-of-range characters alone would give only NIL.'
    if name in {'BOOTSTRAPPING-FASL-MIN-VERSION','BOOTSTRAPPING-FASL-MAX-VERSION','MIXUP-HASH-CODE','SUBTAG-BYTES','SWAP'}:
        return 'target-representation-oracle', 'This returns target format, tag, or word-width data. It needs a separately asserted target table, not macOS raw-value equality or a zero-only witness.'
    if name in {'ENSURE-OPEN-SHLIB','ENTRY->ADDR','RESOLVE-CONTAINER','SHARED-LIBRARY-AT','SHARED-LIBRARY-WITH-NAME','SHLIB-CONTAINING-ENTRY','XP-FLAGS-REGISTER','XP-FPSCR-INFO','DBG'}:
        return 'excluded-native-interface', 'Dynamic loading, native exception contexts or kernel debugger entry is outside the Stage 1 host profile. Admission/closure is not a claim that this is required bootstrap code; the target worklist disposition remains owed.'
    if name=='%PATH-MEMBER':
        return 'native-source-bug', 'Audit149 found a string read before its bounds test. The checked target refuses; no execution credit is obtained by avoiding that path.'
    if name=='%CLOSE-STRING-OUTPUT-STREAM':
        return 'graph-transport-needed', 'The real recycling path joins stream, ioblock and pool identities and creates a cycle. It needs graph-preserving argument/global snapshots; a NIL pool bypass would not test recycling.'
    if name=='%UNFHAVE':
        return 'function-cell-state-needed', 'Needs a native unbound-function identity and target function-cell publication/observation. A made-up sentinel or unobserved cell write is not a recipe.'
    if name=='NEXT-CATCH':
        return 'live-frame-needed', 'Needs a live catch-chain and a frame-aware native caller. An arbitrary vector with a chosen link field is not that protocol.'
    if name=='%GVECTOR':
        return 'dynamic-constructor-needed', 'This callable body takes a runtime subtag; existing constructors are admitted for literal layouts. Existing literal constructor witnesses do not establish the dynamic callable entry.'
    raise AssertionError('No explicit disposition: '+name)

def report(out):
    out=Path(out);read=lambda p:json.loads(p.read_text())
    before=read(PARENT/'execution/execution-frontier.json')
    cohort=[r for r in before['not_executed'] if r['static']]
    assert len(cohort)==64
    current=read(out/'execution-frontier.json');executed=set(current['names'])
    rows=[]
    for r in cohort:
        name=r['name']
        kind,reason=('executed','Original definition called against native, with results and input/global post-state compared at both placements before and after movement.') if name in executed else disposition(name)
        rows.append(dict(name=name,package=r['package'],disposition=kind,reason=reason))
    counts={k:sum(r['disposition']==k for r in rows) for k in sorted({r['disposition'] for r in rows})}
    result=dict(baseline=64,baseline_original_execution=436,executed_originals=len(executed),
                new_executions=sorted(executed-set(before['names'])),counts=counts,rows=rows,
                scope='All 64 requested names are accounted for. Fixture entries and paired 32/64-bit interfaces are separated from new exact-native execution. No exclusions or source branches are silently integrated.')
    (out/'recipe-cohort.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result
