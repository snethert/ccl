"""Check that reused code cannot inherit a newly compiled caller's values."""
from pathlib import Path
import argparse,sys
from functools import partial
from payloads import read,save,require
from seed_calls import Resolver
from flow import convert
from lexical import Resolver as Original
from test_lexical import selected


def run(a):
    raw=read(a.probes);ops={r['id']:r['name'] for r in raw['snapshot']['operators']}
    captures={r['case']:convert(r,ops) for r in raw['captures']};checks=[]
    for case in ('captured-constant','escaping-capture','captured-lexical-prototype'):
        c=captures[case];old=selected(c,Original);new=selected(c,partial(Resolver,entries=set()))
        require(old and all(r['status']=='FINITE_EXPRESSION' for r in old),'SEED_CAPTURE_POSITIVE')
        require(all(r['status']=='UNRESOLVED' and r['reason']=='resident-closure-environment-unqualified' for r in new),
                'SEED_CAPTURE_BORROWED '+case)
        checks.append(dict(case=case,status='REJECTED_BORROWED_ENVIRONMENT'))
    for case in ('local-parameter','two-local-callers','forwarded-parameter'):
        c=captures[case];old=selected(c,Original)
        require(old and all(r['status']=='FINITE_EXPRESSION' for r in old),'SEED_PARAMETER_POSITIVE')
        # This AFUNC is now reached as an independent resident entry. Its
        # original source family's callers no longer enumerate all entries.
        entries={r['function_id'] for r in old}
        bad=selected(c,partial(Resolver,entries=entries))
        require(all(r['status']=='UNRESOLVED' and r['reason']=='resident-entry-parameter' for r in bad),'SEED_PARAMETER_BORROWED')
        good=selected(c,partial(Resolver,entries=set()))
        require(good==old,'SEED_LOCAL_PARAMETER_REGRESSION')
        checks.append(dict(case=case,status='REJECTED_BORROWED_CALLERS_AND_PRESERVED_LOCAL_FLOW'))
    for case in ('inline-required-value','inline-default-value','inline-aux-value'):
        c=captures[case]
        require(selected(c,partial(Resolver,entries=set()))==selected(c,Original),'SEED_INLINE_REGRESSION')
        checks.append(dict(case=case,status='PASS'))
    save(a.output,dict(status='PASS',checks=checks));print('PASS',len(checks),'resident entry/capture checks',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probes',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        import traceback
        a.output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        a.output.with_suffix('.failed-source.py').write_bytes(Path(__file__).read_bytes());raise
