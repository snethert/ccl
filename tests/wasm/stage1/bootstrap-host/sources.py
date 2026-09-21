"""All constant branches in one proposal; retain the platform interface file."""
from foreign import CONSTANT_VALUES,files,sites,target_name
CONSTANTS={key:target_name(key) for key in CONSTANT_VALUES}

def derive(root):
    result={}
    for name in files():
        text=(root/name).read_text();edits=[]
        for m in sites(text):
            if m[1]=='$' and m[2] in CONSTANTS:
                edits.append((m.start(),m.end(),'#+wasm32-target target::'+CONSTANTS[m[2]]+' #-wasm32-target '+m[0]))
        for start,end,replacement in reversed(edits):text=text[:start]+replacement+text[end:]
        if edits:result[name]=text
    return result
from pathlib import Path
FILES=tuple(derive(Path(__file__).resolve().parents[4]))
