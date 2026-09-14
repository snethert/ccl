#!/usr/bin/env python3
"""Publish an R6 comparison without copying its previously retained native inputs."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
from run import ID, ROOT, read, save, sha, require, gate
from evidence_binding import safe_path, binding_errors


def publish(output,evidence,name):
    require(safe_path(name)==name and '/' not in name,'PACKET_NAME')
    packet=evidence/name;envelope=evidence/(name+'-results.json')
    require(not packet.exists() and not envelope.exists(),'NEVER_OVERWRITE')
    require(read(output/'run.json')['status']=='PASS','COMPLETED_PRODUCER')
    report=read(output/'results.json');references=read(output/'references.json')
    require(references==[dict(temporary_path='references/'+str(i),**x) for i,x in enumerate(read(output/'source/tests/wasm/stage0/r6-control/inputs.json')['inputs'])],'REFERENCE_BOUND')
    reference_map={r['temporary_path']:r['path'] for r in references}
    require(len(report['results'])==1 and report['results'][0]['id']==ID and report['results'][0]['review_disposition']=='NOT_REVIEWED','EXECUTION_SCOPE')
    shutil.copytree(output,packet,ignore=shutil.ignore_patterns('references','__pycache__'))
    # The original envelope remains a derivation record; its temporary links
    # are reconstructed by run.py, not duplicated into the permanent packet.
    (packet/'results.json').rename(packet/'producer-results.json')
    published=copy.deepcopy(report);mapping=[]
    row=published['results'][0]
    for artifact in row['artifacts']:
        old=safe_path(artifact['path']);new=reference_map.get(old,name+'/'+old)
        require((evidence/new).resolve().is_relative_to(evidence) and sha(evidence/new)==artifact['sha256'],'PUBLISHED_BYTES '+new)
        artifact['path']=new;mapping.append(dict(original=old,published=new,sha256=artifact['sha256']))
    row['contract_binding']['inventory_path']=name+'/'+safe_path(row['contract_binding']['inventory_path'])
    inverse=copy.deepcopy(published)
    for a,original in zip(inverse['results'][0]['artifacts'],report['results'][0]['artifacts']):a['path']=original['path']
    inverse['results'][0]['contract_binding']['inventory_path']=report['results'][0]['contract_binding']['inventory_path']
    require(inverse==report,'ONLY_LOCATORS_CHANGED')
    require(not binding_errors(read(ROOT/'doc/WASM/stage0/inventory.json'),published,lambda n:(evidence/safe_path(n)).read_bytes()),'CURRENT_BINDING')
    save(envelope,published)
    result=gate(packet/'slot-inventory.json',envelope)
    require(result==read(packet/'slot-gate.json'),'PUBLISHED_GATE')
    save(packet/'publication.json',dict(version=1,status='PASS',producer_envelope_sha256=sha(packet/'producer-results.json'),
        published_envelope=str(envelope),published_envelope_sha256=sha(envelope),
        changes='Only artifact and inventory snapshot locators changed; all other result fields exactly preserved.',
        source_sha256=sha(Path(__file__)),references=mapping,gate=result))
    shutil.copyfile(__file__,packet/'publish.py')
    print('PASS published R6 envelope; direct native inputs referenced without duplicate archives.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--name',required=True)
    a=p.parse_args();publish(a.output.resolve(),a.evidence.resolve(),a.name)
