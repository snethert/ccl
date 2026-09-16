#!/usr/bin/env python3
"""Generate isolated wasm32 architecture descriptions from the accepted schemas."""
import argparse, hashlib, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
LAYOUT=ROOT/'doc/WASM/contracts/wasm32-layout.v1.json'
TCR=ROOT/'doc/WASM/contracts/tcr.v1.json'

def require(ok,reason):
    if not ok:raise ValueError(reason)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def atom(s):
    require(re.fullmatch(r'[a-z0-9.*+_-]+',s.lower()) is not None,'UNSAFE_SYMBOL '+s)
    return s.lower()
def lisp_value(v):
    if type(v) is int:return str(v)
    require(type(v) is dict and set(v)=={'byte_size','byte_position'} and all(type(n) is int and n>=0 for n in v.values()),'UNSUPPORTED_VALUE')
    return '(byte %d %d)'%(v['byte_size'],v['byte_position'])

def descriptions(layout,tcr):
    require((layout['schema'],layout['version'],layout['word_bytes'],layout['endianness'],layout['object_alignment'])==('wasm32-layout',1,4,'little',8),'LAYOUT_PROFILE')
    values={};gaps=[]
    def add(name,value,source):
        name=atom(name);lisp_value(value)
        if name in values:
            require(values[name]['value']==value,'CONFLICTING_DESCRIPTION '+name)
            values[name]['sources'].append(source)
        else:values[name]=dict(value=value,sources=[source])
    def gap(name,row):gaps.append(dict(name=name,disposition=row['disposition'],target=row.get('target',''),note=row.get('note','')))
    for group in ['constants','subtags','headers']:
        for row in layout[group]:
            if row['disposition']=='inherited':add(row['name'],row['value'],group+'/'+row['name'])
            else:gap(group+'/'+row['name'],row)
    for group in ['objects','layouts']:
        for obj in layout[group]:
            if obj['disposition']!='inherited':
                gap(group+'/'+obj['name'],obj)
                for cell in obj['cells']:gap(group+'/'+obj['name']+'/'+cell['name'],cell)
                continue
            add(obj['name']+'.size',obj['size_bytes'],group+'/'+obj['name']+'/size')
            for cell in obj['cells']:
                path=group+'/'+obj['name']+'/'+cell['name']
                if cell['disposition']!='inherited':gap(path,cell);continue
                require(cell['raw_offset']-obj['tag_value']==cell['tagged_displacement'],'CELL_COORDINATES '+path)
                add(obj['name']+'.'+cell['name'],cell['tagged_displacement'],path+'/tagged_displacement')
                add(obj['name']+'.'+cell['name']+'.raw-offset',cell['raw_offset'],path+'/raw_offset')
    # Native runtime layouts are never exported. The production TCR is separate.
    require(tcr['size_bytes']==256 and tcr['alignment']==16,'TCR_PROFILE')
    spans=[];names=set()
    for f in tcr['fields']:
        require(f['name'] not in names,'TCR_DUPLICATE');names.add(f['name'])
        require(f['offset']%f['alignment']==0 and f['width'] in (4,8) and f['offset']+f['width']<=tcr['reserved'][0],'TCR_FIELD '+f['name'])
        spans.append((f['offset'],f['offset']+f['width']))
        add('tcr.'+f['name'],f['offset'],'production-tcr/'+f['name'])
        add('tcr.'+f['name']+'.width',f['width'],'production-tcr/'+f['name']+'/width')
    spans.sort();require(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),'TCR_OVERLAP')
    add('tcr.size',tcr['size_bytes'],'production-tcr/size')
    # The schema describes source-only enumerations and subprimitives as work.
    for row in layout['enums']:gap('enums/'+row['group'],row)
    gap('subprims',layout['subprims'])
    return values,gaps

SLOTS={'lisp-node-size':'node-size','nil-value':'canonical-nil-value','fixnum-shift':'fixnumshift',
 'most-positive-fixnum':'target-most-positive-fixnum','most-negative-fixnum':'target-most-negative-fixnum',
 'misc-data-offset':'misc-data-offset','misc-dfloat-offset':'misc-dfloat-offset','nbits-in-word':'nbits-in-word',
 'ntagbits':'ntagbits','nlisptagbits':'nlisptagbits','word-shift':'word-shift','t-offset':'t-offset',
 'unbound-marker-value':'unbound-marker','slot-unbound-marker-value':'slot-unbound-marker','fixnum-tag':'tag-fixnum',
 'single-float-tag':'subtag-single-float','double-float-tag':'subtag-double-float','cons-tag':'fulltag-cons',
 'null-tag':'fulltag-cons','symbol-tag':'subtag-symbol','misc-subtag-offset':'misc-subtag-offset',
 'car-offset':'cons.car','cdr-offset':'cons.cdr','subtag-char':'subtag-character','charcode-shift':'charcode-shift',
 'fulltagmask':'fulltagmask','fulltag-misc':'fulltag-misc'}
SLOTS.update({'max-%d-bit-constant-index'%n:'max-%d-bit-constant-index'%n for n in [64,32,16,8,1]})

def generate(layout,tcr):
    values,gaps=descriptions(layout,tcr)
    arch_source=ROOT/'compiler/X86/X8632/x8632-arch.lisp'
    require(sha(arch_source)==layout['sources']['compiler/X86/X8632/x8632-arch.lisp'],'ARCH_SOURCE_IDENTITY')
    source=arch_source.read_text();start=source.index('(defparameter *x8632-target-uvector-subtags*');end=source.index(';;; This should return',start)
    aliases=re.findall(r'\(:([\w-]+)\s*\.\s*,([\w-]+)\s*\)',source[start:end])
    require(len(aliases)==40,'UVECTOR_ALIAS_POPULATION')
    vectors=[(key,name.lower()) for key,name in aliases if name.lower() in values]
    for slot,name in SLOTS.items():require(name in values,'MISSING_ARCH_FIELD '+slot)
    lines=[';;; Generated from accepted D1 and production TCR schemas; do not edit.',
      '(defpackage "WASM32" (:use))','(in-package "WASM32")']
    for name,row in sorted(values.items()):lines.append('(cl:defconstant %s %s)'%(name,lisp_value(row['value']).replace('(byte ','(cl:byte ')))
    lines+=['(cl:defparameter *target-arch*', '  (arch::make-target-arch :name :wasm32 :package-name "WASM32"',
      '    :big-endian cl:nil :single-float-tag-is-subtag cl:t :symbol-tag-is-subtag cl:t',
      "    :uvector-subtags '(%s)"%' '.join('(:%s . %s)'%(key,values[name]['value']) for key,name in vectors)]
    lines+=['    :%s %s'%(slot,name) for slot,name in sorted(SLOTS.items())]
    lines+=['    :array-data-size-function #\'unavailable-array-size',
      '    :array-type-name-from-ctype-function #\'unavailable-array-type))',
      '(cl:defun unavailable-array-size (cl:&rest args) (cl:declare (cl:ignore args)) (cl:error "WASM32 array-size lowering not implemented"))',
      '(cl:defun unavailable-array-type (cl:&rest args) (cl:declare (cl:ignore args)) (cl:error "WASM32 array-type lowering not implemented"))',
      '(cl:provide "WASM32-ARCH")']
    # Functions must be defined before their function objects are installed.
    guard=lines[-3:-1];lines=lines[:-3]+[lines[-1]]
    insert=next(i for i,l in enumerate(lines) if l=='(cl:defparameter *target-arch*');lines[insert:insert]=guard
    return '\n'.join(lines)+'\n',dict(version=1,values=values,unavailable=gaps,uvector_aliases=vectors,arch_slots=SLOTS,scope='D1 inherited data descriptions and production TCR offsets; native/replaced/deferred values excluded. Function representation, array helpers, subprimitives and cross-dump remain unimplemented.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    text,record=generate(json.loads(LAYOUT.read_text()),json.loads(TCR.read_text()));(a.output/'wasm32-arch.lisp').write_text(text);write(a.output/'descriptions.json',record)
