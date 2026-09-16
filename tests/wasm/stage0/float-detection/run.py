#!/usr/bin/env python3
"""D6 floating-point detection: checked operations classified without engine flags, proved against exact rational arithmetic."""
import argparse, hashlib, json, platform, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus as C
from oracle import check
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
ID = 'FLOAT-DETECTION-R3'
SCOPE = ('Hand-built wasm32 checked floating-point operations on macOS Node/V8: f64 add, sub, mul, div and sqrt classified as exact, '
         'overflow, division-by-zero, invalid, underflow or inexact without engine flags, a checked float-to-integer conversion that never '
         'traps, and the f32 default-mode slice. Overflow, division by zero and invalid come from operand and result classification; '
         'underflow and inexact from error-free witnesses (TwoSum, scaled TwoProduct, residuals) with exact power-of-two scaling for small '
         'results, small operands and operands near the largest exponent; tininess decided after rounding as IEEE 754 and x86 define it, '
         'including results that round up to the smallest normal. Corpus cases with expectations from exact rational rounding in Python; '
         'every f64 case also executed natively with SSE scalar instructions on this x86-64 Mac, MXCSR flags and result bits agreeing with '
         'the oracle; eleven module mutants rejected. Specification evidence for the D6 floating-point hypothesis; no policy decision, no gate credit.')
MUTANTS = {
    'divisor-zero-check-omitted': ("    (if (call $iszero (local.get $b))\n      (then (return (select (i32.const 0) (i32.const 2) (call $isinf (local.get $a))))))   ;; finite nonzero / 0\n", ''),
    'nan-propagated-as-invalid': ("    (if (i32.or (call $isnan (local.get $a)) (call $isnan (local.get $b))) (then (return (i32.const 0))))\n    (if (call $isnan (local.get $r)) (then (return (i32.const 3))))\n    (if (call $isinf (local.get $r))\n      (then (return (select (i32.const 0) (i32.const 1) (i32.or (call $isinf (local.get $a)) (call $isinf (local.get $b)))))))\n    (i32.const -1))",
                                  "    (if (call $isnan (local.get $r)) (then (return (i32.const 3))))\n    (if (call $isinf (local.get $r))\n      (then (return (select (i32.const 0) (i32.const 1) (i32.or (call $isinf (local.get $a)) (call $isinf (local.get $b)))))))\n    (i32.const -1))"),
    'overflow-unqualified': ("      (then (return (select (i32.const 0) (i32.const 1) (i32.or (call $isinf (local.get $a)) (call $isinf (local.get $b)))))))\n    (i32.const -1))", "      (then (return (i32.const 1))))\n    (i32.const -1))"),
    'large-operand-unscaled': ("    (if (f64.gt (f64.abs (local.get $a)) (global.get $BIG))\n      (then (return (f64.mul (call $twoproduct_plain (f64.mul (local.get $a) (global.get $SCALE_DOWN)) (local.get $b) (f64.mul (local.get $p) (global.get $SCALE_DOWN))) (global.get $SCALE_UP)))))\n", ''),
    'witness-ignored': ("    (if (local.get $exact) (then (return (i32.const 0))))\n    (select (i32.const 4) (i32.const 5)\n      (i32.or (call $tiny (local.get $r))\n              (i32.and (f64.eq (f64.abs (local.get $r)) (global.get $MIN_NORMAL)) (local.get $boundary_tiny)))))", "    (i32.const 0))"),
    'underflow-as-inexact': ("    (select (i32.const 4) (i32.const 5)\n      (i32.or (call $tiny (local.get $r))\n              (i32.and (f64.eq (f64.abs (local.get $r)) (global.get $MIN_NORMAL)) (local.get $boundary_tiny)))))", "    (i32.const 5))"),
    'trunc-unchecked': ("    (if (i32.or (call $isnan (local.get $a)) (call $isinf (local.get $a))) (then (return (i32.const 3))))\n    (local.set $t (f64.trunc (local.get $a)))", "    (local.set $t (f64.trunc (local.get $a)))"),
    'small-product-unscaled': ("    (if (call $small (local.get $r))\n      (then\n        ;; scale both factors by 2^537 (exact); the scaled product is at least 1, so no partial product underflows\n", "    (if (i32.const 0)\n      (then\n"),
    # the R2 review's finding: tininess judged on the final result misses products and quotients that round up to the smallest normal
    'tininess-on-final-result': ("      (i32.or (call $tiny (local.get $r))\n              (i32.and (f64.eq (f64.abs (local.get $r)) (global.get $MIN_NORMAL)) (local.get $boundary_tiny)))))", "      (call $tiny (local.get $r))))"),
    'boundary-tie-tiny': ("(f64.lt (f64.mul (local.get $e) (f64.copysign (global.get $ONE) (local.get $r))) (f64.neg (global.get $QUARTER)))", "(f64.le (f64.mul (local.get $e) (f64.copysign (global.get $ONE) (local.get $r))) (f64.neg (global.get $QUARTER)))"),
    'quotient-boundary-ignored': ("          (f64.lt (f64.add (f64.sub (f64.abs (local.get $as)) (f64.mul (global.get $S52) (f64.abs (local.get $bs))))\n                           (f64.mul (global.get $QUARTER) (f64.abs (local.get $bs))))\n                  (f64.const 0))))))", "          (i32.const 0)))))"),
}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2) + '\n')
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'corpus.py', 'ieee.py', 'oracle.py', 'execute.mjs', 'checked.wat', 'native-witness.c')]


NATIVE_OPS = ('add', 'sub', 'mul', 'div', 'sqrt')


def native(out, corpus, commands, environment):
    """Execute every f64 case natively on this x86-64 Mac and require the MXCSR flags and result bits to agree with the oracle."""
    cc = Path(shutil.which('cc')).resolve(); build = Path(tempfile.mkdtemp(prefix='ccl-float-native-'))
    cases = [c for c in corpus['cases'] if c['op'] in NATIVE_OPS]
    try:
        invoke([str(cc), '-O0', '-o', str(build / 'witness'), str(HERE / 'native-witness.c')], commands, out)
        listing = invoke(['/usr/bin/otool', '-tv', str(build / 'witness')], commands, out)
        mnemonics = sorted({line.split('\t')[1] for line in listing.splitlines() if line.count('\t') >= 1 and re.fullmatch(r'(add|sub|mul|div|sqrt)sd', line.split('\t')[1])})
        feed = ''.join('%s %s %s\n' % (c['op'], c['a'], c.get('b', '0' * 16)) for c in cases)
        p = subprocess.run([str(build / 'witness')], input=feed, capture_output=True, text=True, timeout=120)
        commands.append(dict(argv=[str(build / 'witness')], stdin_lines=len(cases), exit_code=p.returncode, stderr=p.stderr)); save(out / 'commands.json', commands)
        require(p.returncode == 0, 'NATIVE_EXIT')
    finally:
        shutil.rmtree(build)
    (out / 'native').mkdir(); (out / 'native' / 'witness.txt').write_text(p.stdout)
    lines = p.stdout.splitlines(); require(len(lines) == len(cases), 'NATIVE_LINES'); counts = {}
    require(mnemonics == ['addsd', 'divsd', 'mulsd', 'sqrtsd', 'subsd'], 'NATIVE_INSTRUCTIONS ' + repr(mnemonics))
    for c, line in zip(cases, lines):
        op, a, b, result, flags = line.split(); flags = int(flags, 16)
        require(op == c['op'] and a == c['a'] and (c.get('b') is None or b == c['b']), 'NATIVE_ECHO ' + c['id'])
        # IE, ZE, OE, UE, PE in x86 priority; DE (denormal operand) is not a condition
        status = 3 if flags & 1 else 2 if flags & 4 else 1 if flags & 8 else 4 if flags & 16 else 5 if flags & 32 else 0
        require(status == c['status'], 'NATIVE_STATUS %s expected %d observed %d flags %02x' % (c['id'], c['status'], status, flags))
        if c['result'] is None: require(int(result, 16) & 0x7fffffffffffffff > 0x7ff0000000000000, 'NATIVE_NAN ' + c['id'])
        else: require(result == c['result'], 'NATIVE_RESULT %s expected %s observed %s' % (c['id'], c['result'], result))
        counts[status] = counts.get(status, 0) + 1
    summary = dict(cases=len(cases), by_status={str(k): v for k, v in sorted(counts.items())}, scalar_double_mnemonics=mnemonics)
    save(out / 'native' / 'compile.json', dict(compiler=str(cc), version=environment['cc'], flags=['-O0'], mxcsr='0x1F80 before every operation: flags clear, all masked, round to nearest, DAZ and FTZ off',
                                              agreement='every status from the flags in x86 priority and every result bit pattern equal the oracle expectation', **summary))
    return summary


def invoke(argv, commands, out, cwd=None, timeout=300):
    p = subprocess.run(argv, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    commands.append(dict(argv=argv, cwd=str(cwd or ROOT), exit_code=p.returncode, stdout=p.stdout[-2000:], stderr=p.stderr[-2000:]))
    save(out / 'commands.json', commands)
    require(p.returncode == 0, 'COMMAND_EXIT ' + repr(commands[-1]))
    return p.stdout


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    node = Path(shutil.which('node')).resolve(); compiler = Path(shutil.which('wat2wasm')).resolve(); objdump = Path(shutil.which('wasm-objdump')).resolve(); cc = Path(shutil.which('cc')).resolve()
    commands = []
    environment = dict(node=invoke([str(node), '--version'], commands, out).strip(), v8=invoke([str(node), '-p', 'process.versions.v8'], commands, out).strip(),
                       wabt=invoke([str(compiler), '--version'], commands, out).strip(), cc=invoke([str(cc), '--version'], commands, out).splitlines()[0].strip(),
                       machine=platform.machine(), executable_sha256={str(p): sha(p) for p in (node, compiler, objdump, cc)}, python=sys.version, platform=platform.platform())
    require(environment['machine'] == 'x86_64', 'NATIVE_REFERENCE_X86_64')
    save(out / 'environment.json', environment)
    corpus = C.build(); save(out / 'corpus.json', corpus)
    native_summary = native(out, corpus, commands, environment)
    source = (HERE / 'checked.wat').read_text(); observations = []; summary = None
    for case in ['complete', *MUTANTS]:
        b = out / 'bundles' / case; d = out / 'cases' / case; b.mkdir(parents=True); d.mkdir(parents=True)
        text = source
        if case in MUTANTS:
            old, new = MUTANTS[case]; require(text.count(old) == 1, 'MUTANT_SITE ' + case); text = text.replace(old, new)
            save(b / 'mutation.json', dict(mutant=case, file='checked.wat', old=old, new=new))
        (b / 'checked.wat').write_text(text)
        save(b / 'options.json', dict(assembler_flags=[], node_arguments=[], memory_pages=1, corpus_seed=corpus['seed'], corpus_cases=len(corpus['cases'])))
        save(b / 'host-compiler.json', dict(path=str(compiler), sha256=sha(compiler), version=environment['wabt'], disassembler=str(objdump), disassembler_sha256=sha(objdump)))
        invoke([str(compiler), 'checked.wat', '-o', 'checked.wasm'], commands, out, cwd=b)
        (b / 'checked.wasm.disassembly.txt').write_text(invoke([str(objdump), '-d', 'checked.wasm'], commands, out, cwd=b))
        invoke([str(node), str(HERE / 'execute.mjs'), str(b), str(out / 'corpus.json'), str(d)], commands, out)
        observed = read(d / 'observed.json'); require(observed['node'] == environment['node'], 'ENGINE_IDENTITY')
        if case in MUTANTS:
            try: check(corpus, observed)
            except ValueError as e: observations.append(dict(case=case, status='REJECTED_MUTANT', reason=str(e))); continue
            raise ValueError('MUTANT_ESCAPED ' + case)
        summary = check(corpus, observed); observations.append(dict(case=case, status='PASS', **summary))
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED', mutants_rejected=len(MUTANTS), native=native_summary, **summary))
    return observations


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    try:
        observations = exercise(out); (out / 'source').mkdir()
        for p in sources(): (out / 'source' / p.name).write_bytes(p.read_bytes())
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS'); print('PASS: float detection, %d corpus cases, %d executed natively in agreement, %d mutants rejected. Review pending; no gate credit.' % (observations[0]['cases'], read(out / 'native' / 'compile.json')['cases'], len(MUTANTS)))
        for o in observations[1:]: print('  ' + o['case'] + ': ' + o['reason'])
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source').mkdir(exist_ok=True)
            for name, data in snapshots.items(): (out / 'source' / Path(name).name).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    temp = Path(tempfile.mkdtemp(prefix='ccl-float-detection-verify-'))
    try:
        fresh = temp / 'replay'; observations = exercise(fresh)
        require(read(fresh / 'environment.json') == read(packet / 'environment.json'), 'ENGINE_CHANGED')
        require(observations == read(packet / 'observations.json'), 'REPLAY_OBSERVATIONS')
        names = [p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name != 'commands.json']
        for n in names: require((fresh / n).read_bytes() == (packet / n).read_bytes(), 'REPLAY_BYTES ' + str(n))
    except BaseException as e:
        save(temp / 'failure.json', dict(status='FAIL', packet=str(packet), error=str(e))); print('Original verification failure retained at ' + str(temp), file=sys.stderr); raise
    else:
        shutil.rmtree(temp)
    print('PASS: fresh checked-float execution; ' + str(len(names)) + ' identical deterministic files and pins.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
