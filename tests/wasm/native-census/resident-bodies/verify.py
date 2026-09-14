"""Replay retained witnesses and one fresh native export from the pinned image."""
import argparse
import gzip
from pathlib import Path
import shutil
import tarfile
from common import HERE,ROOT,read,save,digest,require
from run import initial_rows,execute_native
from analyze import analyze,missing_codes
from controls import run as controls


def verify(packet,store,work):
    work.mkdir(parents=True,exist_ok=False);manifest=read(packet/'packet.json')
    require(manifest['id']=='NATIVE-RESIDENT-BODIES-R1' and manifest['review_disposition']=='NOT_REVIEWED','PACKET_SCOPE')
    rows=manifest['files']
    require(len({r['path'] for r in rows})==len(rows),'PACKET_DUPLICATE')
    require({p.name for p in packet.iterdir() if p.is_file()}=={'packet.json'}|{r['path'] for r in rows},'PACKET_MEMBERSHIP')
    for r in rows:
        p=packet/r['path'];require(p.parent==packet and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'ARTIFACT '+r['path'])
    for p,sha in read(packet/'sources.json').items():require(digest(ROOT/p)==sha,'SOURCE '+p)
    pins=read(HERE/'inputs.json');require(pins==read(packet/'inputs.json'),'INPUT_MANIFEST')
    paths={k:store/r['path'] for k,r in pins['inputs'].items()}
    for k,p in paths.items():require(digest(p)==pins['inputs'][k]['sha256'],'INPUT '+k)
    source=work/'ccl';source.mkdir()
    with tarfile.open(paths['source']) as archive:archive.extractall(source,filter='data')
    with tarfile.open(paths['bootstrap']) as archive:archive.extract(archive.getmember(pins['image_member']),source,filter='data')
    image=source/pins['image_member'];require(digest(image)==pins['image_sha256'],'IMAGE_IDENTITY')
    kernel=source/'dx86cl64';shutil.copyfile(paths['kernel'],kernel);kernel.chmod(0o755)
    old=initial_rows(paths['events']);blob=image.read_bytes();requests=missing_codes(read(paths['bindings']))
    require((packet/'requests.lisp').read_text()=='('+' '.join(map(str,requests))+')\n','REQUEST_ARTIFACT')
    native=read(packet/'first-bodies.json.gz')
    prefix=gzip.decompress((packet/'first-prefix.jsonl.gz').read_bytes()).splitlines(keepends=True)
    facts,summary=analyze(blob,old,prefix,native,requests)
    result=controls(blob,old,prefix,native,requests,facts,summary)
    for name,value in [('bodies.json.gz',facts),('summary.json',summary),('controls.json',result)]:
        save(work/name,value);require((work/name).read_bytes()==(packet/name).read_bytes(),'REPRODUCTION '+name)
    print('PASS: retained image/prefix/body joins and 24 controls; running a fresh native export.',flush=True)
    fresh,export=execute_native(source,work,paths,packet/'requests.lisp','fresh')
    fresh_facts,fresh_summary=analyze(blob,old,fresh,export,requests)
    require(export==native and fresh_facts==facts and fresh_summary==summary,'FRESH_NATIVE_REPRODUCTION')
    require(digest(image)==pins['image_sha256'] and digest(kernel)==pins['inputs']['kernel']['sha256'],'NATIVE_INPUT_CHANGED')
    save(work/'verification.json',dict(status='PASS',analysis_outputs_byte_identical=3,
        native_export_equal=True,controls_rejected=result['controls_rejected'],
        original_readonly_prefix_byte_identical=summary['original_prefix_events'],
        image_bodies_witnessed=summary['image_bodies_witnessed'],
        full_initial_inventory_equal=False,source_ir_bodies_closed=0,native_build=False,archive_scan=False))
    print('PASS: fresh native export reproduces the body witness; dynamic suffix remains unjoined.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','evidence','work'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve(),a.work.resolve())
