#!/usr/bin/env python3
import argparse,datetime,json,shutil,tarfile,subprocess
from pathlib import Path
from run import HERE,ROOT,BASE,sha,read,save

def manifest(out):
    save(out/'packet.json',{'version':1,'files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(out.rglob('*'))if p.is_file()and p.name!='packet.json']})

def retain(evidence,run,out,development):
    assert not out.exists(),'NO_OVERWRITE';assert read(run/'summary.json')['status']=='PASS';out.mkdir(parents=True)
    sources=[p for p in HERE.iterdir()if p.is_file()and p.suffix in ('.py','.mjs','.wat','.md','.json')]
    for p in sources:
        executed=run/'executed-sources'/p.name
        if executed.exists():assert p.read_bytes()==executed.read_bytes(),'EXECUTED_SOURCE '+p.name
        dest=out/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
    save(out/'source-pins.json',{str(p.relative_to(ROOT)):sha(p)for p in sorted(sources)})
    # Generated modules and their native/model corpus remain in the accepted pack.
    dependencies=read(run/'dependencies.json');save(out/'dependencies.json',dependencies)
    for p in run.iterdir():
        if p.is_file() and p.name not in ('modules.json','cases.json','root-contracts.json','dependencies.json'):
            shutil.copy(p,out/p.name)
    shutil.copytree(run/'malformed',out/'malformed')
    with tarfile.open(out/'mutants.tar.gz','w:gz')as tar:
        for d in sorted((run/'mutants').iterdir()):
            for name in ('loader.mjs','binary.mjs','stub.wat','lazy-stub.wasm','execution.log','execution-command.json','build.log','build-command.json'):
                p=d/name
                if p.exists():tar.add(p,arcname=str(p.relative_to(run/'mutants')))
    with tarfile.open(out/'development.tar.gz','w:gz')as tar:
        for d in development:
            assert d.exists()
            # Keep exact executed source, commands, logs, malformed inputs and
            # outputs; never duplicate unchanged compiler-generated binaries.
            for p in sorted(d.rglob('*')):
                if not p.is_file()or p.is_symlink():continue
                rel=p.relative_to(d)
                if 'installed'in rel.parts or p.name in ('cases.json','modules.json','root-contracts.json','catalog.json'):continue
                if p.suffix in ('.py','.mjs','.wat','.json','.log','.wasm'):tar.add(p,arcname=d.name+'/'+str(rel))
            log=d.with_suffix('.log')
            if log.exists():tar.add(log,arcname=d.name+'/driver.log')
    save(out/'run.json',{'status':'PASS','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':BASE,'base_manifest_sha256':sha(evidence/BASE/'packet.json'),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'native_execution':'NONE; unchanged accepted compiler/modules and native/R6 evidence reused','summary':read(run/'summary.json')})
    save(out/'toolchain.json',{name:{'path':'/usr/local/bin/'+name,'sha256':sha(Path('/usr/local/bin')/name),'version':subprocess.check_output(['/usr/local/bin/'+name,'--version'],text=True).strip()}for name in ('node','wat2wasm')})
    manifest(out)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('evidence','run','output'):p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--development',nargs='*',type=Path,default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.output.resolve(),[p.resolve()for p in a.development])
