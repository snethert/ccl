"""Inventory foreign reader sites without executing a foreign reader macro."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
WORKLIST=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-carry-r1/execution/compiled/worklist.sexp'

def files():
    return re.findall(r'\("([^"]+)" \d+ (?:T|NIL)\)',WORKLIST.read_text())

def mask(text):
    # Mask strings, escaped symbols, line comments and nested block comments.
    # Character literals consume their first character even when it is a quote.
    out=list(text);i=0
    while i<len(text):
        start=i
        if text.startswith('#\\',i):
            i+=3
            while i<len(text) and text[i] not in '() \t\r\n':i+=1
        elif text.startswith('#|',i):
            i+=2;depth=1
            while depth:
                assert i<len(text),'unterminated block comment'
                if text.startswith('#|',i):depth+=1;i+=2
                elif text.startswith('|#',i):depth-=1;i+=2
                else:i+=1
        elif text[i]==';':
            i=text.find('\n',i)
            if i<0:i=len(text)
        elif text[i] in ('"','|'):
            delimiter=text[i]
            i+=1
            while i<len(text):
                c=text[i];i+=1
                if c=='\\':i+=1
                elif c==delimiter:break
        else:i+=1;continue
        out[start:i]=' '*(i-start)
    return ''.join(out)

def sites(text):
    return list(re.finditer(r'#([$_])\s*([A-Za-z0-9_]+)', mask(text)))

def classify(kind,name):
    if kind=='$':
        return 'target-protocol-constant' if name in CONSTANT_VALUES else 'existing-platform-conditional'
    low=name.lower()
    if low in ('memmove','memset'):return 'runtime-memory-operation-owed'
    if low.removesuffix('f') in ('pow','exp','log','sqrt','sin','cos','tan','atan','atan2','asin','acos','sinh','cosh','tanh','log1p','expm1','hypot'):return 'numeric-libm-coverage-owed'
    if any(x in low for x in ('dlopen','dlsym','dlclose','dlerror','dyld','modulehandle','loadlibrary','freelibrary','getprocaddress')):return 'native-ffi-excluded'
    if any(x in low for x in ('mmap','munmap','mprotect','madvise','mincore','mlock','virtual','mapview','unmapview')):return 'memory-owner-replacement-owed'
    if any(x in low for x in ('fork','exec','waitpid','kill','signal','process','thread','sched','sem','sleep','yield')):return 'scheduler-or-process-provider-owed'
    if any(x in low for x in ('time','clock','sysconf','host_info','mach_host','getenv','setenv','unsetenv','uname')):return 'host-configuration-provider-owed'
    return 'namespace-or-host-provider-owed'

# These are target protocol identifiers. They are never passed to native libc.
CONSTANT_VALUES=dict(SEEK_SET=0,SEEK_CUR=1,SEEK_END=2,
 EPERM=1,ENOENT=2,ESRCH=3,EINTR=4,EEXIST=17,ENFILE=23,EMFILE=24,EISDIR=21,ERANGE=34,ETIMEDOUT=110,
 O_RDONLY=0,O_WRONLY=1,O_RDWR=2,O_CREAT=64,O_EXCL=128,O_TRUNC=512,O_NONBLOCK=2048,
 F_GETFL=3,F_SETFL=4,PATH_MAX=4096,POLLIN=1,POLLOUT=4,
 S_IFMT=61440,S_IFIFO=4096,S_IFCHR=8192,S_IFDIR=16384,S_IFREG=32768,S_IFLNK=40960,S_IFSOCK=49152,
 EX_USAGE=64,EX_SOFTWARE=70,EX_OSERR=71,PROT_NONE=0,PROT_READ=1,PROT_WRITE=2,PROT_EXEC=4,
 MAP_PRIVATE=2,MAP_FIXED=16,MAP_ANON=32,RTLD_NOW=2,RTLD_NOLOAD=4,RUSAGE_SELF=0,
 SIGSTOP=19,SIGTSTP=20,SIGTTIN=21,SIGTTOU=22,WNOHANG=1,WUNTRACED=2,WCOREFLAG=128,
 SOL_SOCKET=1,SO_SNDLOWAT=19,_PC_MAX_INPUT=2,_PC_PIPE_BUF=5,_SC_CLK_TCK=2,_SC_PAGESIZE=30)
PRIOR_NAMES=dict(SEEK_SET='io-seek-set',SEEK_CUR='io-seek-cur',EINTR='io-error-interrupted',EEXIST='io-error-file-exists',ENFILE='io-error-system-file-limit',EMFILE='io-error-process-file-limit')
def target_name(name):return PRIOR_NAMES.get(name,'os-'+name.lower().replace('_','-').strip('-'))

def inventory():
    rows=[]
    for file in files():
        text=(ROOT/file).read_text()
        for m in sites(text):
            rows.append(dict(file=file,line=text.count('\n',0,m.start())+1,offset=m.start(),token=m[0],kind=m[1],name=m[2],disposition=classify(m[1],m[2])))
    return dict(worklist_sha256=hashlib.sha256(WORKLIST.read_bytes()).hexdigest(),files=len(files()),sites=rows,
        scope='All syntactic constant/function reader sites in the restored 57-file worklist, including existing-target-only branches. Strings and comments excluded. Per-host availability is not inferred. Active Wasm sites are also recorded independently by CCL with acquisition disabled.')

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(inventory(),indent=2,sort_keys=True)+'\n')


def qualify(out):
    from collections import Counter
    from sources import derive, plan, CONSTANTS, EXCLUDED_FUNCTIONS, EXCLUDED_CONSTANTS
    sample='; #$NO\n\"#_no\" #| #_no #| #$NO |# |# |#_no| #_ function #$YES'
    assert [(m[1],m[2]) for m in sites(sample)]==[('_','function'),('$','YES')]
    active=json.loads((out/'compiled/foreign-active.json').read_text())
    assert not active['failures']
    changed=derive(ROOT)
    plans={file:plan(ROOT,file) for file in files()}
    lookup={}
    data=inventory()
    for file in files():
        original=(ROOT/file).read_text()
        proposed=changed.get(file,original)
        edits, excluded=plan(ROOT,file)
        for m in sites(original):
            offset=m.start()+sum(len(new)-(b-a) for a,b,new in edits if b<=m.start())
            if any(a==m.start() and b>a for a,b,new in edits):continue
            assert proposed[offset:offset+len(m[0])]==m[0]
            lookup[(file,len(proposed[:offset].encode()),m[1],m[2].upper())]=m.start()
    reached=set()
    for row in active['rows']:
        if row['kind'] not in ('_','$'):continue
        file=row['file'].removeprefix('ccl:').replace(';','/')
        if file.startswith('l1/'):file='level-1/'+file[3:]
        key=(file,row['offset'],row['kind'],row['name'])
        assert key in lookup,key
        reached.add((file,lookup[key]))
    for row in data['sites']:
        row['active_wasm_foreign_reference']=(row['file'],row['offset']) in reached
        exclusions=plans[row['file']][1]
        enclosing=next((x for x in exclusions if x['start']<=row['offset']<x['end']),None)
        if enclosing:
            row['disposition']='excluded-with-caller'
            row['excluded_definition']=enclosing['name']
        elif not row['active_wasm_foreign_reference'] and not (row['kind']=='$' and row['name'] in CONSTANTS):
            row['disposition']='existing-platform-conditional'
        row['implemented']=row['kind']=='$' and row['name'] in CONSTANTS and enclosing is None
        row['scope']='Identifier only; does not implement the operation.' if row['implemented'] else ('Unresolved active target dependency.' if row['active_wasm_foreign_reference'] else 'Not read as a foreign reference under the Wasm profile; existing-platform branch retained.')
    assert not any(r['active_wasm_foreign_reference'] and r['disposition']=='excluded-with-caller' for r in data['sites'])
    assert not any(r['kind']=='$' for r in active['rows'])
    data['summary']=dict(sites=len(data['sites']),constant_branches=sum(r['implemented'] for r in data['sites']),constant_identifiers=len(CONSTANTS),active_functions=sum(r['kind']=='_' for r in active['rows']),active_foreign_types=[r for r in active['rows'] if r['kind']=='>'],by_disposition=dict(Counter(r['disposition'] for r in data['sites'])))
    (out/'foreign-sites.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    lines=['# Foreign references in the restored worklist','',data['scope'],'','| Source | Token | Active foreign read on Wasm | Disposition |','|---|---|---|---|']
    for r in data['sites']:
        lines.append(f"| {r['file']}:{r['line']} | `{r['token']}` | {'yes' if r['active_wasm_foreign_reference'] else 'no'} | {r['disposition']} |")
    (out/'foreign-sites.md').write_text('\n'.join(lines)+'\n')
