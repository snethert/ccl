"""Target-only exclusions belong on definitions, not their libc tokens."""
import re
from pathlib import Path
from foreign import CONSTANT_VALUES,files,sites,target_name,mask

# There is no native address space, process, FFI, terminal or socket service.
EXCLUDED_FUNCTIONS=set('''mmap munmap mprotect mincore mlock munlock dlopen dlclose dladdr
fork execvp waitpid kill setuid setgid setpgid chown getpwuid getpwnam getuid getpid
getpwuid_r tcgetpgrp getdtablesize getsockopt getrusage system fpathconf fcntl poll
sysconf host_info mach_host_self sysctl'''.split())
EXCLUDED_CONSTANTS=set('''MAP_ANON MAP_PRIVATE MAP_FIXED PROT_NONE PROT_READ PROT_WRITE PROT_EXEC
RTLD_NOW RTLD_NOLOAD RUSAGE_SELF SIGSTOP SIGTSTP SIGTTIN SIGTTOU WNOHANG WUNTRACED
WCOREFLAG SOL_SOCKET SO_SNDLOWAT _PC_MAX_INPUT _PC_PIPE_BUF _SC_CLK_TCK _SC_PAGESIZE
F_GETFL F_SETFL POLLIN POLLOUT'''.split())
CONSTANTS={key:target_name(key) for key in CONSTANT_VALUES if key not in EXCLUDED_CONSTANTS}

def definitions(text):
    plain=mask(text);stack=[];ends={}
    for i,c in enumerate(plain):
        if c=='(':stack.append(i)
        elif c==')':
            assert stack, ('extra close',i)
            ends[stack.pop()]=i+1
    assert not stack
    return [(m.start(),ends[m.start()],m[1],m[2]) for m in
            re.finditer(r'\((defun|defmacro|defmethod|defvar|defparameter|defloadvar|defstatic|def-standard-initial-binding|setq)\s+([^\s()]+)',plain,re.I)]

def plan(root,name):
    text=(root/name).read_text();defs=definitions(text);excluded={}
    for m in sites(text):
        if (m[1]=='_' and m[2].lower() in EXCLUDED_FUNCTIONS) or (m[1]=='$' and m[2] in EXCLUDED_CONSTANTS):
            candidates=[row for row in defs if row[0]<=m.start()<row[1]]
            assert candidates,(name,m[0],text.count('\n',0,m.start())+1)
            row=max([r for r in candidates if r[2].lower()!='setq'] or candidates)
            if row[3].lower() not in ('%file-kind','*dlopen-flags*'):
                excluded.setdefault(row,[]).append(m[0])
    edits=[(start,start,'#-wasm32-target\n') for start,end,kind,symbol in excluded]
    for m in sites(text):
        if m[1]=='$' and m[2] in CONSTANTS and not any(a<=m.start()<b for a,b,_,_ in excluded):
            edits.append((m.start(),m.end(),'#+wasm32-target target::'+CONSTANTS[m[2]]+' #-wasm32-target '+m[0]))
    return sorted(edits),[dict(start=a,end=b,kind=k,name=s,reasons=v) for (a,b,k,s),v in sorted(excluded.items())]

def derive(root):
    result={}
    for name in files():
        text=(root/name).read_text();edits,_=plan(root,name)
        for start,end,replacement in reversed(edits):text=text[:start]+replacement+text[end:]
        if edits:result[name]=text
    return result
FILES=tuple(derive(Path(__file__).resolve().parents[4]))
