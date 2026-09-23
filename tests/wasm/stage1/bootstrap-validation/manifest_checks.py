"""O-33: development files cannot change execution identity."""
from pathlib import Path
import tempfile
import common as c
from prepare import driver_inputs


def check(output):
    output=Path(output);output.mkdir()
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        root=Path(temporary);driver=root/'driver';driver.mkdir()
        source=driver/'encode.py';source.write_text('VALUE = 1\n')
        dev=driver/'development';dev.mkdir()
        (dev/'before.log').write_text('old attempt')
        c.save(root/'driver-manifest.json',c.inventory(driver))
        before=driver_inputs(root)
        (dev/'before.log').unlink();(dev/'after.log').write_text('new attempt')
        (dev/'old_encoder.py').write_text('not an input')
        (driver/'extra.log').write_text('not an input')
        assert driver_inputs(root)==before
        source.write_text('VALUE = 2\n')
        try:driver_inputs(root)
        except ValueError:pass
        else:raise AssertionError('changed declared driver admitted')
        source.write_text('VALUE = 1\n')
        (driver/'injected.py').write_text('unexpected import')
        try:driver_inputs(root)
        except ValueError:pass
        else:raise AssertionError('undeclared executable driver admitted')
    result=dict(status='PASS',development_ignored=True,declared_source_change_refused=True,
                undeclared_source_refused=True)
    c.save(output/'manifest-checks.json',result);return result


if __name__=='__main__':
    import argparse
    import storage
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    with storage.lease([a.output]):print(check(a.output))
