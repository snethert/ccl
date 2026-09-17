"""Join LL05 assertions to executed populations and the accepted B decision."""
from support import ROOT,read,save,sha,require

def write(out):
 summary=read(out/'summary.json');require(summary['status']=='PASS','QUALIFICATION_COMPLETE')
 source=ROOT/'tests/wasm/stage0/abi-decision/decision.json';decision=read(source)
 require(decision['selected_abi']=='B' and decision['basis']=='PROJECT_DECISION','ACCEPTED_B')
 require(decision['abi']['parameters']==['self:i32','nargs:i32'] and decision['abi']['results']==['value0:i32','nvalues:i32'] and decision['abi']['argument_parameter_count']==0,'B_ENTRY_SHAPE')
 mods=read(out/'positive/modules.json');names={m['name'] for m in mods}
 require(all('call'+str(n) in names for n in range(7)),'ORDERED_ARGUMENT_POPULATION')
 for name in ('call128','call129','call257','call512','local_labels','closure_apply','key','opt','apply2','mvc_tail','mvb_tail'):
  require(name in names,'CORPUS_OBLIGATION '+name)
 require(summary['tail_steps_per_run']==100000 and summary['tail_stack_bytes']==2048 and summary['public_dispatches']==0,'TAIL_AND_INTERNAL_ENTRY')
 require(summary['implicit_error_comparisons']>=288 and summary['implicit_error_controls']==10,'LISP_CALL_ERRORS')
 controls=read(out/'full-loader/full-controls.json')['cases'];cn={c['name'] for c in controls}
 require({'wrong-export-signature','export-role','actual-table-substitution-entry','actual-table-substitution-tail_entry','same-signature-wrong-code','registry-signature','registry-role','public-stub-count-and-closure-self'}<=cn,'LOADER_OBLIGATIONS')
 require(summary['full_loader']['mutants']==14,'LOADER_MUTANTS')
 save(out/'abi-binding.json',dict(selected_abi='B',decision_source=str(source.relative_to(ROOT)),decision_sha256=sha(source),public_signature=decision['abi']['parameters'],results=decision['abi']['results'],internal_signature=['self:i32','nargs:i32','continuation:i32'],binding='The actual generated exports/imports are decoded by the loader and checked against these signatures; all selected B arguments remain in the explicit value stack.',selection_basis='Project decision; no timing claim.'))
 save(out/'coverage.json',{'S1-LL05-a':{'arguments':'positive: call0..call6 and long overflow corpus; native.json plus independent literal/model expectations','calls':'direct/live bindings, FUNCALL, closures, FLET/LABELS, APPLY and recursion in positive','binding':'required/optional/rest/keyword/supplied-p plus dynamic parameters','values':'zero/one/many, dynamic producers, retained and transferred results; single-scanner inspections','errors':'call-errors: native-first arity and designator handlers before unwinding, keyword class distinction, declining/masked/nested handlers, dynamic producer transfers','controls':['controls.json','error-controls/controls.json','condition-controls/controls.json']},'S1-LL05-b':{'installation':'full-loader/full-controls.json, loader-controls, lazy-composition, condition-lazy and call-error-lazy','stubs':'public count and live closure SELF, paired internal/public entries; actual table and binary signature/role substitutions refused','tails':'48 chains of 100000 transfers within 2048 bytes, exact/variable arity and complete results','extents':'cleanup, special-binding and nonlocal-exit cases; tails disabled while an extent must survive','abi':'abi-binding.json pins the accepted B decision directly'},'limits':read(out/'scope.json')['limits'] if (out/'scope.json').exists() else read(__import__('support').HERE/'scope.json')['limits']})
 save(out/'options.json',dict(profile='full',workers=1,memory_pages=32769,flags=['--enable-threads','--enable-exceptions','--enable-tail-call'],target='wasm32',host_callbacks_in_generated_closure=False,constants_slot_claimed=False))
