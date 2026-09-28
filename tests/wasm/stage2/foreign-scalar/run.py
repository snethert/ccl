"""Scalar foreign admission/entry unit. Build and validate in a leased RAM workspace."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage

RUNTIME = ['foreign-binary.mjs', 'foreign-module.mjs', 'bytes.mjs', 'sha256.mjs']
MUTANTS = [
    ('digest', 'sha256(source)===d.sha256', 'true', 'admission-digest'),
    ('memory', 'm.memories[0].maximum===d.memory.maximum', 'true', 'admission-memory-max'),
    ('table', 'table.maximum===d.tables[i]?.maximum', 'true', 'admission-table-limits'),
    ('export-type', 'signature(actual.signature)===signature(e)', 'true', 'admission-export-signature'),
    ('import-type', 'signature(matches[0])===signature(actual)', 'true', 'admission-import-type'),
    ('import-set', 'm.imports.length===d.imports.length', 'true', 'admission-import-extra'),
    ('start', "(m.start!==null)===(init.kind==='start')", 'true', 'binary-refusal-start'),
    ('initializer-alias', '!initializerNames.has(name)', "name!=='initialize'", 'initialization-export'),
    ('enter', 'token=enter(operation);', 'token=operation;', 'initialization-export'),
    ('leave', 'const admitted=leave(token);', 'const admitted=undefined;', 'initialization-export'),
    ('trap-retire', "error instanceof WebAssembly.RuntimeError||state==='initializing'", "state==='initializing'", 'foreign-failure-trap'),
    ('trap-containment', 'throw error;\n    }\n    return result;', 'throw cause;\n    }\n    return result;', 'wasm-caller-cleanup-trap'),
    ('scalar-range', 'value<=2147483647', 'true', None),
    ('argument-snapshot', 'instance.exports[name](...values)', 'instance.exports[name](...args)', 'argument-snapshot'),
]


def command(args, out, log, check=True):
    with (out/log).open('w') as stream:
        result = subprocess.run([str(x) for x in args], stdout=stream, stderr=subprocess.STDOUT, timeout=150,
                                env={**os.environ, 'TMPDIR':str(out)})
    if check and result.returncode:
        raise RuntimeError((out/log).read_text()[-5000:])
    return result.returncode


def run(out, playwright, browser_config):
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        sources = ([ROOT/'runtime/wasm32'/name for name in RUNTIME] +
                   sorted(p for p in HERE.iterdir() if p.suffix in ('.mjs','.py','.wat')) +
                   [ROOT/'tests/wasm/stage1/bootstrap-validation'/name for name in ('common.py','storage.py')])
        source_hashes = {str(p.relative_to(ROOT)):c.sha(p) for p in sources if p.is_file()}
        c.save(out/'sources.json', source_hashes)
        for name in RUNTIME: shutil.copy2(ROOT/'runtime/wasm32'/name, out/'runtime'/name)
        for name in ['check.mjs', 'node.mjs', 'worker.mjs']: shutil.copy2(HERE/name, out/name)
        base = (HERE/'library.wat').read_text()
        variants = {
            'library':base,
            'start':base.replace('  (func $init', '  (start $init)\n  (func $init'),
            'memory-import':base.replace('(memory (export "memory") 1 4)', '(import "env" "memory" (memory 1 4)) (export "memory" (memory 0))'),
            'shared':base.replace('(memory (export "memory") 1 4)', '(memory (export "memory") 1 4 shared)'),
            'unbounded':base.replace('(memory (export "memory") 1 4)', '(memory (export "memory") 1)'),
            'memory64':'(module (memory (export "memory") i64 1 4))',
            'memory-export-absent':base.replace('(memory (export "memory") 1 4)', '(memory 1 4)'),
            'memory-export-alias':base.replace('(memory (export "memory") 1 4)', '(memory (export "memory") (export "alias") 1 4)'),
            'table-unbounded':base.replace('(table 0 4 funcref)', '(table 0 funcref)'),
            'memory-extra':base.replace('(table 0 4 funcref)', '(table 0 4 funcref) (memory 1 2)'),
            'export-global':base.replace('(global $state (mut i32)', '(global $state (export "global") (mut i32)'),
            'table-externref':base.replace('(table 0 4 funcref)', '(table 0 4 externref)'),
            'import-duplicate':base.replace('(memory (export "memory")', '(import "host" "probe" (func $probe2 (param i32)))\n  (memory (export "memory")'),
            'reference-type':base.replace('(param i64) (result i64) local.get 0)', '(param externref) (result externref) local.get 0)'),
            'import-multi':base.replace('(func $host (result i32))', '(func $host (result i32 i64 f32 f64))').replace('(export "host") (result i32)', '(export "host") (result i32 i64 f32 f64)'),
            'invalid-code':base.replace('(export "i32") (param i32) (result i32) local.get 0)', '(export "i32") (param i32) (result i32))'),
            'caller':(HERE/'caller.wat').read_text(),
        }
        try:
            artifacts = {}
            for name, text in variants.items():
                wat, wasm = out/(name+'.wat'), out/(name+'.wasm')
                wat.write_text(text)
                command([c.WABT, wat, '-o', wasm, *c.FLAGS, '--enable-multi-memory', '--enable-memory64']+
                        (['--no-check'] if name=='invalid-code' else []), out, 'assembly.log')
                artifacts[name] = dict(source_sha256=c.sha(wat), wasm_sha256=c.sha(wasm), bytes=wasm.stat().st_size)
                wat.unlink()
            c.save(out/'binaries.json', list(variants))
            c.save(out/'artifacts.json', artifacts)
            c.save(out/'tools.json', {name:dict(path=str(p), sha256=c.sha(p)) for name,p in [('node',c.NODE),('wat2wasm',c.WABT),('python',Path(sys.executable))]})
            command([c.NODE, out/'node.mjs', out/'node.json'], out, 'node.log')
            original = (out/'runtime/foreign-module.mjs').read_text()
            controls=[]
            try:
                for name, before, after, case in MUTANTS:
                    assert original.count(before)==1, name
                    (out/'runtime/foreign-module.mjs').write_text(original.replace(before, after))
                    args=[c.NODE, out/'node.mjs', out/'mutant.json'] + ([case] if case else [])
                    status=command(args, out, 'mutant.log', check=False)
                    result=c.read(out/'mutant.json')
                    if status==0 or result['status']!='FAIL': raise AssertionError('mutant survived: '+name)
                    if case and not result['error'].startswith('Error: '+case+':'): raise AssertionError('wrong mutant failure: '+name)
                    controls.append(dict(name=name, case=case, status='KILLED', error=result['error'], source_sha256=c.sha(out/'runtime/foreign-module.mjs')))
            finally:
                (out/'runtime/foreign-module.mjs').write_text(original)
                c.save(out/'mutants.json', controls)
            if playwright:
                command([c.NODE, HERE/'browser.mjs', out, playwright] + ([browser_config] if browser_config else []), out, 'browser.log')
                for row in c.read(out/'browser.json')['results']:
                    assert row['rows']==c.read(out/'node.json')['rows'], row['engine']
            for name in RUNTIME: assert c.sha(ROOT/'runtime/wasm32'/name)==c.sha(out/'runtime'/name)
            for relative, digest in source_hashes.items(): assert c.sha(ROOT/relative)==digest, relative
            summary=dict(status='PASS',checks=c.read(out/'node.json')['checks'],mutants=len(controls),
                         browsers=[r['engine'] for r in c.read(out/'browser.json')['results']] if playwright else [],
                         skips=[] if playwright else ['browser engines not requested'],review='NOT_REVIEWED',
                         product_lisp_lines_changed=0,criterion_credit=False)
            c.save(out/'summary.json', summary)
            for p in out.glob('*.wasm'): p.unlink()
            for name in ['mutant.json','mutant.log','assembly.log']: (out/name).unlink(missing_ok=True)
            c.save(out/'.run.json',dict(status='PASS'))
            print(json.dumps(summary))
        except Exception as error:
            c.save(out/'failure.json',dict(status='FAIL',error=str(error)))
            c.save(out/'failure-inputs.json',[str(p.relative_to(out)) for p in out.glob('*.wasm')])
            c.save(out/'.run.json',dict(status='FAIL'))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-scalar/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    args=parser.parse_args()
    run(args.output.resolve(),args.playwright.resolve() if args.playwright else None,
        args.browser_config.resolve() if args.browser_config else None)
