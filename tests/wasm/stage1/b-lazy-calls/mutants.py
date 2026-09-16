"""Single-site omissions, replayed through the same corpus or refusal oracle."""
from pathlib import Path
import json,re,shutil
from prepare import one

def mutations(out):
    loader=(out/'loader.mjs').read_text();binary=(out/'binary.mjs').read_text();stub=(out/'stub.wat').read_text()
    def patch(file,text,a,b,oracle):return file,one(text,a,b),oracle
    return {
      'ignore-digest':patch('loader.mjs',loader,"need(sha(bytes)===record.sha256,'BINARY_DIGEST');","need(true,'BINARY_DIGEST');",'controls'),
      'ignore-profile':patch('loader.mjs',loader,"need(record.profile===PROFILE,'PROFILE');","need(true,'PROFILE');",'controls'),
      'ignore-export-role':patch('loader.mjs',loader,"need(record.entries[role]?.index===e.index&&record.entries[role]?.role===role,'EXPORT_ROLE');","need(true,'EXPORT_ROLE');",'controls'),
      'ignore-imports':patch('loader.mjs',loader,"need(same(m.imports,record.imports),'IMPORT_MANIFEST');","need(true,'IMPORT_MANIFEST');",'controls'),
      'allow-initialization':patch('binary.mjs',binary,"if(![0,1,2,3,7,10].includes(id))fail('INITIALIZATION_OR_SECTION');","if(false)fail('INITIALIZATION_OR_SECTION');",'controls'),
      'ignore-registry':patch('loader.mjs',loader,"need(get(base)>r.code&&get(base+4)===1&&same([get(p),get(p+4),get(p+8),get(p+12)],[r.slot,r.version,r.signature,r.role]),'REGISTRY_IDENTITY');","need(true,'REGISTRY_IDENTITY');",'controls'),
      'ignore-table-identity':patch('loader.mjs',loader,"need(o.table.get(r.slot)===row.pair.entry&&o.tail_table.get(r.slot)===row.pair.tail_entry,'TABLE_IDENTITY');","need(true,'TABLE_IDENTITY');",'controls'),
      'omit-tail-publication':patch('loader.mjs',loader,'o.table.set(slot,pair.entry);o.tail_table.set(slot,pair.tail_entry);','o.table.set(slot,pair.entry);','harness'),
      'swap-published-roles':patch('loader.mjs',loader,'o.table.set(slot,pair.entry);o.tail_table.set(slot,pair.tail_entry);','o.table.set(slot,pair.tail_entry);o.tail_table.set(slot,pair.entry);','harness'),
      'alias-manifest':patch('loader.mjs',loader,'const r=structuredClone(source);','const r=source;','controls'),
      'stub-drops-self':patch('stub.wat',stub,'(return_call_indirect $entries (type $B) (local.get $self)','(return_call_indirect $entries (type $B) (i32.const 77825)','harness'),
      'stub-drops-count':patch('stub.wat',stub,'(local.get $self) (local.get $count) (global.get $slot)))','(local.get $self) (i32.const 0) (global.get $slot)))','harness'),
      'stub-drops-continuation':patch('stub.wat',stub,'(local.get $context) (global.get $slot)))','(i32.const 0) (global.get $slot)))','harness'),
      'stub-wrong-tail-table':patch('stub.wat',stub,'return_call_indirect $tails','return_call_indirect $entries','harness'),
    }

def run(out,command):
    dest=out/'mutants';dest.mkdir();rows=[]
    for name,(filename,text,oracle)in mutations(out).items():
        folder=dest/name;folder.mkdir()
        for p in out.iterdir():
            if p.is_file() and p.suffix in ('.mjs','.json','.wasm','.wat'):shutil.copy(p,folder/p.name)
        # Read-only references to the unchanged generated binaries and controls.
        for n in ('installed','malformed'):(folder/n).symlink_to(out/n,target_is_directory=True)
        (folder/filename).write_text(text)
        if filename=='stub.wat':assert command(['/usr/local/bin/wat2wasm','--enable-tail-call',str(folder/filename),'-o',str(folder/'lazy-stub.wasm')],folder,'build')==0
        code=command(['/usr/local/bin/node',str(folder/(oracle+'.mjs')),str(folder),str(folder/'result.json')],folder,'execution')
        log=(folder/'execution.log').read_text();match=re.search(r'AssertionError(?: \[[^\]]+\])?: (.*)',log)
        assert code!=0 and match,'MUTANT_ORACLE '+name+' '+str(folder/'execution.log')
        rows.append({'name':name,'status':'REJECTED','oracle':oracle,'first_assertion':match[1]})
    (out/'mutants.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
