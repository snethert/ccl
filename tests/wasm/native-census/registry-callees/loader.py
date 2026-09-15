"""Join loaded prototypes to compiler bodies through actual FASL versions."""
from collections import defaultdict
from pathlib import Path
import sys
from payloads import require

HERE=Path(__file__).resolve().parent


def collect(build,emissions,before):
    # Reuse the reviewed opcode/mode/position reader. Its full-stream check
    # still applies to this selectively instrumented execution's own counts.
    sys.path.insert(0,str(HERE.parent/'binding-versions'))
    from collect import collect as read_stream
    facts,_=read_stream(build)
    joined=defaultdict(list);unjoined=[]
    for r in facts['reads']:
        if r['reader_mode']!='native':continue
        written=r['written'];candidates=[]
        if written:
            candidates=[e for e in emissions.get(written['code'],[]) if e['afunc'] in before
                        and before[e['afunc']]['event']<e['event']<written['event']]
        if not candidates:
            unjoined.append(dict(function=r['function'],event=r['event'],writer=written));continue
        require(written['event']<r['enter']<r['event'],'LOADER_BODY_ORDER')
        for e in candidates:
            joined[r['function']].append(dict(afunc=e['afunc'],event=r['event'],
                materialization_event=e['event'],writer=written,reader=r,
                relation='SAME_EXECUTION_FASL_VERSION'))
    return dict(joined),unjoined
