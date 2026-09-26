"""Retain the integrated replay and fresh corpus; reuse pinned qualification."""
from pathlib import Path
import shutil
import sys
import product
import storage

c = product.c


def retain(execution, corpus, destination):
    record = product.check()
    result = c.read(execution / 'integration.json')
    assert result['status'] == 'PASS' and result['reviewed_artifacts_equal'] == 3628
    assert result['integration_record'] == c.sha(product.RECORD)
    assert result['source_identity'] == record['source_identity']
    c.verify_files(c.ROOT, result['drivers'])
    tree = execution.parent / 'ccl'
    assert tree.is_dir() and not (tree / '.git').exists() and tree != c.ROOT
    c.verify_files(tree, result['drivers'])
    c.verify_files(tree, record['all_sources'])
    c.verify_files(execution, c.read(execution / 'execution-files.json'))
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['fresh_comparisons'] == 26048
    assert regression['runtime'] == record['runtime']
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == record['source_identity']
    summary = dict(status='PASS', product_integration=True, review='AUDIT_183_NO_DEFECT',
        integration=result, corpus=regression, whole_file=[21, 21, 0],
        accepted_originals=[575, 535], ledger=[21, 12], slot_credit=False,
        target_load=False, boot=False, git_free=True, different_root=True,
        follow_up_review='INTEGRATION_HARNESS_PENDING_REVIEW')
    product.module('integration_retain', product.HERE.parent / 'loader-chain/retain.py').retain(
        c, destination, dict(execution=execution, corpus=corpus),
        'STAGE1-LOADER-GC-INTEGRATION', summary,
        {'integration-record.json': record})
    # The shared writer preserves proposal status; this new pack records the
    # user's acceptance of the reviewed product, separately from its harness.
    packet = c.read(destination / 'packet.json')
    packet.update(status='ACCEPTED_AND_INTEGRATED', review='AUDIT_183_NO_DEFECT',
                  follow_up_review='INTEGRATION_HARNESS_PENDING_REVIEW')
    c.save(destination / 'packet.json', packet)
    c.verify_files(destination, packet['files'])
    print(dict(status='PASS', packet=str(destination), sha256=c.sha(destination / 'packet.json')))
    for path in (execution, corpus):
        shutil.rmtree(path)


if __name__ == '__main__':
    execution, corpus, destination = [Path(p).resolve() for p in sys.argv[1:]]
    with storage.lease([execution, corpus]):
        retain(execution, corpus, destination)
