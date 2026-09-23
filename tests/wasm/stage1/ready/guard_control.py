"""One changed initializer, compiled against the retained environment."""
from pathlib import Path
import shutil
import common as c
from probe import probe
from prepare import prepare as execution_prepare
HERE=Path(__file__).resolve().parent

GUARD = '''  (unless (eq (ready-image-status image) t)
    (error "The READY image is not finalized."))
'''


def check(out, ready_prepare):
    work=out/'guard-mutant';work.mkdir()
    source=(HERE/'startup.lisp').read_text()
    assert source.count(GUARD)==1
    submitted=work/'startup.lisp';submitted.write_text(source.replace(GUARD,''))
    compiled=work/'compiled'
    probe(out/'base',submitted,HERE/'inputs.lisp',compiled,c.DEFAULT_CACHE,'class',4)
    execution_prepare(compiled);ready_prepare(compiled)
    c.command([c.NODE,HERE/'run.mjs',compiled,'write',work/'images',work/'writer.json'],
              work/'writer.log',timeout=90)
    c.command([c.NODE,HERE/'guard-control.mjs',compiled,work/'images',out/'guard-control.json'],
              work/'control.log',timeout=90)
    report=c.read(out/'guard-control.json')
    report.update(original_source=c.sha(HERE/'startup.lisp'),mutant_source=c.sha(submitted),
                  compiler=c.read(compiled/'probe-completion.json'),
                  code_digest=(compiled/'class-image-code.sha256').read_text().strip())
    # Durations are measurements, not deterministic evidence identities.
    report['compiler'].pop('seconds',None)
    report['compiler'].pop('compiler_image',None)
    for row in report['compiler']['assembly']:
        row.pop('seconds',None);row.pop('rebuilt',None)
    for key in ('wabt_processes','wabt_cache_hits'):
        report['compiler'].pop(key,None)
    c.save(out/'guard-control.json',report)
    dev=out/'development/guard-control';dev.mkdir(parents=True)
    for original in (submitted,compiled/'probe.log',work/'writer.log',work/'control.log'):
        shutil.copyfile(original,dev/original.name)
    shutil.rmtree(work)
    return report
