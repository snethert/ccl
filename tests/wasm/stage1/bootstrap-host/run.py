import importlib.util,sys,shutil,json,subprocess,hashlib,re

from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[3]
sys.path.insert(0,str(here));import backend

HERE=here;ROOT=root;EVIDENCE=root.parent/"ccl-evidence"

CORE=here.parent/"bootstrap-core"

def fixture(name):
    return here/name if (here/name).exists() else CORE/name

def compile_corpus(out):
    out=Path(out).resolve();out.mkdir()
    driver=out/'driver';shutil.copytree(root/'tests/wasm/stage1/constants',driver,ignore=shutil.ignore_patterns('__pycache__'))
    p=driver/'compile.py';p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",f"ROOT=Path({str(root)!r});REG=ROOT/'tests/wasm/stage1/registration'"))
    for name in ['whole-file.lisp','core-measure.lisp','execute.lisp','cases.lisp','controls.lisp','probes.lisp']:shutil.copy(CORE/'measure.lisp' if name=='core-measure.lisp' else fixture(name),driver/('measure.lisp' if name=='core-measure.lisp' else name))
    primitive=root.parent/'ccl-evidence/2026-09-21-stage1-population-pushnew-r1/execution'
    text=(primitive/'eql-adapter.wat').read_text()
    assert text.count('(local.get $argc) (i32.const 3)')==1
    text=text.replace('(local.get $argc) (i32.const 3)', '(local.get $argc) (i32.const 2)')
    text=text.replace('(i32.load offset=8 (local.get $args)) (global.get $scratch)', '(i32.const 77825) (global.get $scratch)')
    (driver/'eql-adapter.wat').write_text(text)
    values=root/'tests/wasm/stage1/bootstrap-values'
    shutil.copy(here.parent/'bootstrap-frontend/legacy.lisp',driver/'legacy.lisp')
    for name in ['extra.lisp']:shutil.copy(values/name,driver/name)
    measure=(values/'measure.lisp').read_text()
    measure=measure.replace('(setq *frontend-result* (funcall thunk))','(setq *frontend-result* (funcall thunk))')
    measure=measure.replace('(call-with-target\n                          (lambda () (compile-bootstrap-form form "probe" links)))', '(let ((result (call-with-target (lambda () (compile-bootstrap-form form (format nil "scan_~d" i) links))))) (core-check-body form result) (push (list form result) *core-candidates*) result)')
    measure=measure.replace('(and (symbol-package symbol)\n                                       (package-name (symbol-package symbol)))', '(if (symbol-package symbol) (package-name (symbol-package symbol)) "<uninterned>")')
    (driver/'base-measure.lisp').write_text(measure)
    chunks=[]
    for directory in ['level-0','level-1']:
     for path in sorted((root/directory).glob('*.lisp')):chunks.append((str(path.relative_to(root)),backend.source_files(root).get(str(path.relative_to(root)),path.read_text())))
    (driver/'chunks.lisp').write_text("'("+'\n'.join('('+repr(name).replace("'",'"')+' 0 "'+text.replace('\\','\\\\').replace('"','\\"')+'")' for name,text in chunks)+')')

    shutil.copy(fixture('compile.lisp'),driver/'compile.lisp')
    shutil.copy(HERE/'witnesses.lisp',driver/'witnesses.lisp')
    shutil.copy(HERE/'inputs.lisp',driver/'inputs.lisp')
    shutil.copy(HERE/'foreign-scan.lisp',driver/'foreign-scan.lisp')
    for name in ('w32-os.lisp','os-probes.lisp'):shutil.copy(HERE/name,driver/name)
    shutil.copy(root/'tests/wasm/stage1/float-calls/class-shapes.lisp',driver/'class-shapes.lisp')
    shutil.copy(here/'measure.lisp',driver/'worklist.lisp')

    sys.path.insert(0,str(driver));spec=importlib.util.spec_from_file_location('core_driver',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.proposal=backend.proposal
    mod.run(root.parent/'ccl-evidence',out/'compiled',backend.generate())

def stable_reader_diagnostics(out):
    # A CCL reader error prints its stream address; preserve the raw diagnostic
    # and compare every other byte, including error class and source position.
    p=Path(out)/'compiled/native-read-skips.sexp'
    text=re.sub(r"(#<STRING-INPUT-STREAM\s+)#x[0-9A-Fa-f]+(?=>)", r"\1STREAM-IDENTITY", p.read_text())
    p.with_name('native-read-skips-stable.sexp').write_text(text)

def save(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def run(out):
    out=Path(out).resolve()
    compile_corpus(out)
    stable_reader_diagnostics(out)
    import foreign
    foreign.qualify(out)
    subprocess.run([sys.executable,HERE/'execute.py',out],check=True)
    subprocess.run([sys.executable,HERE/'checks.py',out],check=True)
    subprocess.run([sys.executable,HERE/'host-checks.py',out],check=True)
    summarize(out)

def summarize(out):
    out=Path(out).resolve()
    native=json.loads((out/'compiled/native.json').read_text())
    target_names={r['definition'] for r in native if r.get('targetOnly')}
    executed={r['definition'] for r in native if not r['definition'].startswith('CORE-') and not r.get('targetOnly') and r['definition'] not in ('EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ')}
    from report import report
    assert report(out)==len(executed)
    throughput=json.loads((out/'compiled/throughput.json').read_text())
    closed=json.loads((out/'compiled/closed.json').read_text())
    whole=json.loads((out/'compiled/whole-file.json').read_text())
    execution=json.loads((out/'execution.json').read_text())['rows']
    visits=json.loads((out/'compiled/operator-visits.json').read_text())
    legacy=[]
    for f in sorted((out/'compiled').glob('*.legacy')):
        assert f.read_bytes()==(EVIDENCE/'2026-09-21-stage1-bootstrap-values-r1/execution/compiled'/f.name).read_bytes(),f.name
        legacy.append(f.name)
    assert len(legacy)==10 and len(executed)>=100
    assert all(r['status']=='ADMITTED' or (r['name']=='CPU-COUNT' and r['status']=='GLOBAL-SETQ') for r in whole if not r['file'].endswith('l0-misc.lisp'))
    worklist=json.loads((out/'compiled/worklist-throughput.json').read_text())
    files=re.findall(r'\("([^"]+)" (\d+) (T|NIL)\)',(out/'compiled/worklist.sexp').read_text())
    assert len(files)==57 and any(path.endswith('linux-files.lisp') for path,n,c in files) and next(n for path,n,c in files if path.endswith('l0-bignum64.lisp'))=='0'
    save(out/'summary.json',dict(status='PASS',original_definitions_executed=len(executed),
        non_nil_witness=json.loads((out/'member-witnesses.json').read_text())['non_nil_witness'],
        istruct_checks=json.loads((out/'istruct-checks.json').read_text())['checks'],
        historical_diagnostic_admitted=sum(r['proposal']=='admitted' for r in throughput['functions']),
        historical_diagnostic_denominator=len(throughput['functions']),read_skips=len(throughput['skips']),
        target_worklist=dict(files=len(files),read_complete=sum(c=='T' for _,_,c in files),denominator_complete=False,
          parsed_definitions=len(worklist['functions']),admitted=sum(r['outcome']=='admitted' for r in worklist['functions']),
          scope='A lower bound. Read stops at first error in each file; missing compile-time environments and foreign interfaces, plus compound-name exclusions, prevent a complete denominator.'),
        whole_files={f:dict(records=sum(r['file']==f for r in whole),admitted=sum(r['file']==f and r['status']=='ADMITTED' for r in whole)) for f in dict.fromkeys(r['file'] for r in whole)},
        callee_closed_definitions=sum(r['static'] and r['name'] not in target_names and r['package']!='WASM32-COMPILER' and r['name']!='EQL' for r in closed),
        native_cases=len(native),
        target_protocol_cases=sum(r.get('targetOnly') or r['definition'].startswith('CORE-HOST-') for r in native),
        target_protocol_comparisons=4*sum(r.get('targetOnly') or r['definition'].startswith('CORE-HOST-') for r in native),
        target_comparisons=sum(r['comparisons'] for r in execution),
        native_comparisons=sum(r['comparisons'] for r in execution)-4-4*sum(r.get('targetOnly') or r['definition'].startswith('CORE-HOST-') for r in native),
        declared_signed_zero_differences=4,
        collections_between_calls=sum(r['collections'] for r in execution),
        collections_during_calls=sum(r['internalCollections'] for r in execution),
        fast_comparison_checks=sum(r['fastChecks'] for r in execution),
        access_refusals=sum(len(r['refusals']) for r in execution),
        whole_file_records=len(whole),whole_file_named_definitions=sum(r['name'] is not None for r in whole),
        emitted_ir_visits=sum(n for r in visits for _,n in r['operators']),
        emitted_operators=sorted({op for r in visits for op,_ in r['operators']}),
        legacy_files_identical=len(legacy),carry=json.loads((out/'carry.json').read_text()),
        scope='Callee closure does not establish initialized globals or a ready bootstrap image; fixture controls and the EQL leaf do not count as original definitions.'))
    print((out/'summary.json').read_text())

if __name__=='__main__':
    (compile_corpus if '--compile-only' in sys.argv else run)(sys.argv[1])
