"""Retain one compact diagnostic packet, with no gate or acceptance mutation."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
from analysis import read, require
from probe_run import retained
from run import ROOT, HERE, LOADS, digest, save


def archive(output, roots, select=lambda p:True):
    identities=[];seen={}
    with tarfile.open(output,'w:gz') as tar:
        for prefix,root in roots:
            for p in sorted(root.rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts or not select(p):continue
                name=prefix+'/'+p.relative_to(root).as_posix();raw=p.read_bytes()
                sha=hashlib.sha256(raw).hexdigest();identities.append(dict(path=name,bytes=len(raw),sha256=sha))
                info=tarfile.TarInfo(name);info.mtime=0;info.mode=0o644
                if sha in seen:
                    info.type=tarfile.LNKTYPE;info.linkname=seen[sha];tar.addfile(info)
                else:
                    info.size=len(raw);tar.addfile(info,io.BytesIO(raw));seen[sha]=name
        raw=(json.dumps(identities,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(raw)
        tar.addfile(info,io.BytesIO(raw))
    return dict(files=len(identities),unique_payloads=len(seen),bytes=output.stat().st_size)


def finalize(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    results,controls=retained(args.probes)
    require(results==read(args.probes/'summary.json') and controls==read(args.probes/'controls.json'),'PROBE_RECORDS')
    native=read(args.native_analysis/'analysis.json');target=read(args.target_analysis/'analysis.json')
    require(native['totals']['successful_files']==164 and native['totals']['files']==target['totals']['files']==164,'SOURCE_COVERAGE')
    before=read(args.work/'baseline.json')
    after={str(p.relative_to(args.work/'ccl')):digest(p) for p in sorted((args.work/'ccl').rglob('*'))if p.is_file()}
    require(before==after,'DISPOSABLE_SOURCE_OR_FASL_CHANGED')
    restoration=dict(files=len(before),source_and_fasls_unchanged=True,baseline_sha256=digest(args.work/'baseline.json'))
    save(output/'restoration.json',restoration)
    source_paths={p for p in HERE.rglob('*')if p.is_file() and '__pycache__' not in p.parts}
    source_paths.update(HERE.parent/n for n in LOADS)
    source_paths.update([HERE.parent/'observer.lisp',HERE.parent/'dependencies.lisp',HERE.parent/'source-traversal/inputs.json'])
    # The exact U1 archive is already pinned; these are the directly interpreted
    # frontend/layout definitions used by the new recorder and its independent checks.
    source_paths.update(ROOT/n for n in ('lib/nfcomp.lisp','compiler/nx0.lisp','compiler/nx1.lisp',
       'compiler/nx-basic.lisp','compiler/nxenv.lisp','compiler/X86/x862.lisp',
       'compiler/X86/X8632/x8632-arch.lisp','level-0/X86/x86-def.lisp','xdump/faslenv.lisp'))
    pins={str(p.relative_to(ROOT)):digest(p) for p in sorted(source_paths)}
    save(output/'sources.json',pins);save(output/'inputs.json',read(args.work/'inputs.json'))
    summary=dict(status='COLLECTED_AND_CHECKED',review_disposition='NOT_REVIEWED',native=native['totals'],target=target['totals'],
       native_unresolved_computed_calls=sum(native['unresolved_lexical_reasons'].values())+native['call_categories']['computed-callee'],
       target_form_failures=sum(len(f.get('gaps',[]))for f in target['files']),
       target_tainted_captures=sum(f.get('tainted_captures',0)for f in target['files']),
       probe_controls=len(controls),reference=results['reference'],restoration=restoration,
       native_preview_differences=len(results['reproduction']['native']['diagnostic_preview_differences']),
       census_acceptance='BLOCKED',inventory_unchanged=True,original_r7_bounds_changed=False,
       scope='Independent source-file observations. Not a sequential r7 rebuild, qualified target macro environment, joined bootstrap closure or Wasm execution.')
    save(output/'summary.json',summary)
    for name,path in (('native-analysis',args.native_analysis),('target-analysis',args.target_analysis)):
        shutil.copyfile(path/'analysis.json',output/(name+'.json'))
    archives={}
    archives['capture.tar.gz']=archive(output/'capture.tar.gz',[
        ('native',args.native),('target',args.target),('probes',args.probes),
        ('native-analysis',args.native_analysis),('target-analysis',args.target_analysis)])
    omitted=[]
    def development_select(p):
        if p.name!='capture.json.gz':return True
        if not any('survey' in part for part in p.parts):return True
        with gzip.open(p,'rb') as stream:prefix=stream.read(128)
        # The producer writes these two literal top-level fields first. Anything
        # else is retained, including a partial or unfamiliar capture format.
        if not prefix.startswith(b'{"version":1,"status":"CAPTURED",'):return True
        omitted.append(dict(path=str(p.relative_to(args.development)),sha256=digest(p),
                            availability='SUPERSEDED_SUCCESS_CAPTURE_HASH_ONLY'))
        return False
    archives['development.tar.gz']=archive(output/'development.tar.gz',[('development',args.development)],development_select)
    save(output/'development-omitted-successes.json',omitted)
    shutil.copyfile(HERE/'development.md',output/'development.md')
    record=dict(version=1,id='NATIVE-SOURCE-CLOSURE-R1',timestamp=datetime.now(timezone.utc).isoformat(),
       implementation_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       source_revision='c994217adc56b3f8a564526cee4695893ac84d86',
       python=platform.python_version(),host=platform.platform(),scope=summary['scope'],
       review_disposition='NOT_REVIEWED',archives=archives,
       files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p))for p in sorted(output.iterdir())if p.is_file()])
    save(output/'packet.json',record);print(summary);print(archives)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('native','target','native-analysis','target-analysis','probes','work','development','output'):
        p.add_argument('--'+k,type=Path,required=True)
    finalize(p.parse_args())
