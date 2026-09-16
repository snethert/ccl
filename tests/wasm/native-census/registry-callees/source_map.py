"""Exact source-coordinate accounting for the already reviewed observer patch.

Reconstructs the nine patched byte strings in memory. No checkout or disposable
source file is modified, and spans intersecting any edit are never mapped.
"""
import hashlib
import re
from pathlib import Path
from payloads import require,read

HERE=Path(__file__).resolve().parent
HUNK=re.compile(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def apply_file(original,patch_lines):
    source=original.splitlines(keepends=True);offsets=[0]
    for line in source:offsets.append(offsets[-1]+len(line))
    result=[];regions=[];old=0;new_offset=0
    def unchanged(stop):
        nonlocal old,new_offset
        require(old<=stop<=len(source),'PATCH_OLD_ORDER')
        size=offsets[stop]-offsets[old]
        if size:
            start=offsets[old]
            if regions and regions[-1][0]+regions[-1][2]==start and regions[-1][1]+regions[-1][2]==new_offset:
                regions[-1][2]+=size
            else:regions.append([start,new_offset,size])
            result.extend(source[old:stop]);new_offset+=size
        old=stop
    cursor=0
    while cursor<len(patch_lines):
        match=HUNK.match(patch_lines[cursor]);require(match is not None,'PATCH_HUNK')
        os=int(match[1]);oc=int(match[2] or b'1');ns=int(match[3]);nc=int(match[4] or b'1')
        unchanged(os-1 if oc else os)
        require(sum(x.count(b'\n') for x in result)==(ns-1 if nc else ns),'PATCH_NEW_POSITION')
        cursor+=1;consumed=0;produced=0
        while consumed<oc or produced<nc:
            require(cursor<len(patch_lines),'PATCH_TRUNCATED');line=patch_lines[cursor];cursor+=1
            kind=line[:1];data=line[1:]
            require(kind in (b' ',b'+',b'-'),'PATCH_LINE')
            if kind in (b' ',b'-'):
                require(old<len(source) and source[old]==data,'PATCH_EXACT_CONTEXT');consumed+=1
            if kind==b' ':unchanged(old+1);produced+=1
            elif kind==b'-':old+=1
            else:result.append(data);new_offset+=len(data);produced+=1
        require((consumed,produced)==(oc,nc),'PATCH_HUNK_COUNTS')
    unchanged(len(source));return b''.join(result),regions


def build(source):
    fixture=HERE.parent/'rich-observation';manifest=read(fixture/'patch.json');patch=(fixture/'observation.patch').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    require(sha(patch)==manifest['patch_sha256'],'COORDINATE_PATCH_IDENTITY')
    pieces={};lines=patch.splitlines(keepends=True);i=0
    while i<len(lines):
        require(lines[i].startswith(b'--- a/'),'PATCH_OLD_FILE');name=lines[i][6:].strip().decode();i+=1
        require(lines[i]==b'+++ b/'+name.encode()+b'\n','PATCH_NEW_FILE');i+=1;start=i
        while i<len(lines) and not lines[i].startswith(b'--- a/'):i+=1
        require(name not in pieces,'PATCH_FILE_DUPLICATE');pieces[name]=lines[start:i]
    require(set(pieces)=={r['path'] for r in manifest['files']},'PATCH_FILE_SET')
    records={}
    for row in manifest['files']:
        original=(source/row['path']).read_bytes();require(sha(original)==row['original_sha256'],'COORDINATE_ORIGINAL_BYTES')
        observed,regions=apply_file(original,pieces[row['path']])
        require(sha(observed)==row['observed_sha256'],'COORDINATE_OBSERVED_BYTES')
        require(all(c<128 for c in original+observed),'COORDINATE_CHARACTER_ENCODING')
        records[row['path'].casefold()]=dict(original_sha256=row['original_sha256'],observed_sha256=row['observed_sha256'],
                                           unchanged_regions=regions)
    return records


def span(records,path,start,end):
    if path not in records:return (start,end),None
    record=records[path]
    for old,new,length in record['unchanged_regions']:
        if old<=start<end<=old+length:
            result=(new+start-old,new+end-old)
            return result,dict(path=path,original_sha256=record['original_sha256'],observed_sha256=record['observed_sha256'],
                               original_span=[start,end],observed_span=list(result),unchanged_region=[old,new,length])
    return None,None
