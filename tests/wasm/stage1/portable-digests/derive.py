"""Derive the browser-portable runtime without changing integrated files."""
from pathlib import Path
import hashlib,json,shutil,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def derive(out):
    out.mkdir(parents=True,exist_ok=False)
    for p in (ROOT/'runtime/wasm32').glob('*.mjs'):shutil.copy(p,out/p.name)
    for n in ['bytes.mjs','sha256.mjs']:shutil.copy(HERE/n,out/n)
    for n in ['collector-owner.mjs','float-service.mjs','integer-service.mjs','scalar-service.mjs','loader.mjs']:
        p=out/n;s=p.read_text();s=replace(s,"import {createHash} from 'node:crypto';","import {sha256} from './sha256.mjs';")
        if n=='collector-owner.mjs':s=replace(s,"createHash('sha256').update(bytes).digest('hex')","sha256(bytes)")
        if n=='integer-service.mjs':s=replace(s,"createHash('sha256').update(bytes).digest('hex')","sha256(bytes)")
        if n=='float-service.mjs':s=replace(s,"const hash=b=>createHash('sha256').update(b).digest('hex');","const hash=sha256;")
        if n=='scalar-service.mjs':
            s=replace(s,"createHash('sha256').update(scalarBytes).digest('hex')","sha256(scalarBytes)")
            s="import {utf8} from './bytes.mjs';\n"+s
            s=replace(s,"const name=s=>[...u(s.length),...Buffer.from(s)];","const name=s=>{const b=utf8(s);return [...u(b.length),...b];};")
        if n=='loader.mjs':
            s="import {snapshotBytes} from './bytes.mjs';\n"+s
            s=replace(s,"export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');","export const sha=sha256;")
            s=replace(s,'Buffer.from(o.readBytes(row.record.name))','snapshotBytes(o.readBytes(row.record.name))')
        p.write_text(s)
    p=out/'binary.mjs';s=p.read_text();s=replace(s,"Buffer.from(bytes.subarray(0,8)).toString('hex')","hex(bytes.subarray(0,8))");p.write_text("import {hex} from './bytes.mjs';\n"+s)
    p=out/'installer.mjs';s=p.read_text();s=replace(s,'Buffer.from(readBytes(r.name))','snapshotBytes(readBytes(r.name))');s=replace(s,'Buffer.from(JSON.stringify(m))','utf8(JSON.stringify(m))');p.write_text("import {snapshotBytes,utf8} from './bytes.mjs';\n"+s)
    for p in out.glob('*.mjs'):
        assert 'node:' not in p.read_text() and not re.search(r'\bBuffer\.',p.read_text()),p
    return {p.name:sha(p) for p in sorted(out.iterdir())}
