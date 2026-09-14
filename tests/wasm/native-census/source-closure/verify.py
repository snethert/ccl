"""Verify this packet and recompute its two source-wide call worklists."""
import argparse
from pathlib import Path
import tarfile
from analysis import read, require
from analyze_survey import analyze_survey
from probe_run import retained
from run import ROOT, digest


def verify(packet,work):
    work.mkdir(parents=True,exist_ok=False);record=read(packet/'packet.json')
    require(record['id']=='NATIVE-SOURCE-CLOSURE-R1' and record['review_disposition']=='NOT_REVIEWED','PACKET_SCOPE')
    rows=record['files'];require(len({r['path'] for r in rows})==len(rows),'PACKET_DUPLICATES')
    require({p.name for p in packet.iterdir()if p.is_file()}=={'packet.json'}|{r['path']for r in rows},'PACKET_MEMBERSHIP')
    for r in rows:
        p=packet/r['path'];require(p.parent==packet and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'PACKET_IDENTITY '+r['path'])
    pins=read(packet/'sources.json')
    for name,expected in pins.items():
        require(digest(ROOT/name)==expected,'SOURCE_IDENTITY '+name)
    for name in ('capture.tar.gz','development.tar.gz'):
        target=work/name.removesuffix('.tar.gz');target.mkdir()
        with tarfile.open(packet/name) as archive:archive.extractall(target,filter='data')
        members=read(target/'members.json')
        require({str(p.relative_to(target))for p in target.rglob('*')if p.is_file()}=={'members.json'}|{r['path']for r in members},'ARCHIVE_MEMBERSHIP')
        for row in members:
            p=target/row['path'];require(p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'ARCHIVE_IDENTITY '+row['path'])
    capture=work/'capture';probes=capture/'probes'
    results,controls=retained(probes)
    require(results==read(probes/'summary.json') and controls==read(probes/'controls.json'),'PROBE_RESULTS')
    summary=read(packet/'summary.json')
    require(summary['census_acceptance']=='BLOCKED' and summary['original_r7_bounds_changed'] is False,'NO_CLOSURE_PROMOTION')
    require(summary['probe_controls']==len(controls) and summary['reference']==results['reference'],'PROBE_SUMMARY')
    for mode in ('native','target'):
        for item in read(capture/mode/'summary.json')['files']:
            session=capture/mode/f"{item['ordinal']:03d}"
            run=read(session/'run.json')
            # Runtime source files are unchanged between the retained sessions
            # and this packet. Analysis/checker development is pinned separately.
            for source,sha in run['source_sha256'].items():
                require(pins[source]==sha,'SESSION_SOURCE '+source)
            if (session/'capture.json.gz').exists():
                import gzip,hashlib
                require(hashlib.sha256(gzip.decompress((session/'capture.json.gz').read_bytes())).hexdigest()==run['capture_sha256'],'SESSION_CAPTURE')
        out=work/(mode+'-analysis');analyze_survey(capture/mode,out)
        for file in ('analysis.json','calls.jsonl.gz'):
            require((out/file).read_bytes()==(capture/(mode+'-analysis')/file).read_bytes(),'DERIVED_ANALYSIS '+mode+'/'+file)
        require(read(out/'analysis.json')['totals']==summary[mode],'ANALYSIS_SUMMARY '+mode)
    print('PASS: two complete survey worklists, probe oracles, exact sources/artifacts, retained failures; census remains BLOCKED')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('packet',type=Path);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();verify(a.packet.resolve(),a.work.resolve())
