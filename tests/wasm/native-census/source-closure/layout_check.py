"""Recompute the bounded D1 integer descriptions directly from the U1 source."""
import re
from functools import reduce
from operator import and_, or_, mul
from analysis import ROOT, require


def form_at(text, start):
    tokens=re.findall(r';[^\n]*|\(|\)|[^\s();]+',text[start:])
    tokens=iter(t for t in tokens if not t.startswith(';'))
    def parse(t):
        if t!='(': return t.lower()
        row=[]
        for t in tokens:
            if t==')': return row
            row.append(parse(t))
        raise ValueError('D1_UNCLOSED_FORM')
    return parse(next(tokens))


def check(capture):
    text=(ROOT/'compiler/X86/X8632/x8632-arch.lisp').read_text()
    for f in capture['layout_source']:
        require(text[f['start']:f['end']]==f['text'],'D1_SOURCE_SPAN')
    values={r['name'].lower():r['value'] for r in capture['layout_constants']}
    require(len(values)==len(capture['layout_constants']),'D1_DUPLICATE_CONSTANT')
    def definition(prefix, name):
        matches=list(re.finditer(r'\('+re.escape(prefix)+r'\s+'+re.escape(name)+r'(?=\s|\))',text,re.I))
        require(len(matches)==1,'D1_DEFINITION '+prefix+' '+name)
        return form_at(text,matches[0].start())
    data_objects={}
    for name in ('ratio','single-float','double-float','complex-single-float','complex-double-float',
                 'complex','symbol','vectorh','value-cell'):
        cells=definition('define-fixedsized-object',name)[2:]
        for i,cell in enumerate(['header']+cells): data_objects[name+'.'+cell]=i*4-6
        for i,cell in enumerate(cells): data_objects[name+'.'+cell+'-cell']=i
        data_objects[name+'.size']=4*(len(cells)+1)
        data_objects[name+'.element-count']=len(cells)
    require('(:start ,origin :step 4)' in text and
            '(define-lisp-object ,name fulltag-misc header ,@non-header-cells)' in text and
            '(define-storage-layout ,name ,(- (symbol-value tagname)) ,@cells)' in text,
            'D1_LAYOUT_FORMULAS')
    cache={}
    def constant(name, ancestors=()):
        if name in data_objects:return data_objects[name]
        if name in cache:return cache[name]
        require(name not in ancestors,'D1_CONSTANT_CYCLE')
        def evaluate(x):
            if isinstance(x,str):
                if re.fullmatch(r'[+-]?\d+',x):return int(x)
                if x.startswith('#x'):return int(x[2:],16)
                if x.startswith('#b'):return int(x[2:],2)
                return constant(x,ancestors+(name,))
            op,*args=x;args=list(map(evaluate,args))
            if op=='+':return sum(args)
            if op=='-':return args[0]-sum(args[1:]) if len(args)>1 else -args[0]
            if op=='*':return reduce(mul,args,1)
            if op=='ash':return args[0]<<args[1] if args[1]>=0 else args[0]>>-args[1]
            if op=='logior':return reduce(or_,args,0)
            if op=='logand':return reduce(and_,args,-1)
            if op=='1-':require(len(args)==1,'D1_ARITY');return args[0]-1
            if op=='1+':require(len(args)==1,'D1_ARITY');return args[0]+1
            raise ValueError('D1_EXPRESSION '+op)
        if re.search(r'\(defconstant\s+'+re.escape(name)+r'\s',text,re.I):
            v=evaluate(definition('defconstant',name)[2])
        else:
            require(name.startswith('subtag-'),'D1_UNKNOWN_CONSTANT '+name)
            suffix=name[7:]
            if re.search(r'\(define-node-subtag\s+'+re.escape(suffix)+r'\s',text,re.I):
                _,_,index=definition('define-node-subtag',suffix);tag=2
            elif re.search(r'\(define-imm-subtag\s+'+re.escape(suffix)+r'\s',text,re.I):
                _,_,index=definition('define-imm-subtag',suffix);tag=7
            else:
                _,_,tag,index=definition('define-subtag',suffix);tag=constant(tag,ancestors+(name,))
            v=(int(index)<<3)|tag
        cache[name]=v;return v
    require('(logior ,tag (ash ,subtag ntagbits))' in text,'D1_SUBTAG_FORMULA')
    for k,v in values.items(): require(type(v)is int and v==constant(k),'D1_CONSTANT '+k)
    fields={r['accessor']:r['value'] for r in capture['layout_fields']}
    expected={'NULL-TAG':1,'SYMBOL-TAG':58,'FUNCTION-TAG':42,'SINGLE-FLOAT-TAG':15,
              'DOUBLE-FLOAT-TAG':23,'SUBTAG-CHAR':75,'CHARCODE-SHIFT':8,
              'UNBOUND-MARKER-VALUE':51,'SLOT-UNBOUND-MARKER-VALUE':83,
              'MISC-SUBTAG-OFFSET':-6,'MISC-DFLOAT-OFFSET':2,
              'SYMBOL-TAG-IS-SUBTAG':True,'FUNCTION-TAG-IS-SUBTAG':True,'SINGLE-FLOAT-TAG-IS-SUBTAG':True}
    for k,v in expected.items(): require(fields['ARCH::TARGET-'+k]==v,'D1_FIELD '+k)
    table=fields['ARCH::TARGET-UVECTOR-SUBTAGS']
    selected={r['name'].removeprefix('KEYWORD::').lower():r['value'] for r in table}
    require(len(selected)==len(table)==37,'D1_TABLE_SET')
    # Independent source table joins. These are profile-selected data rows,
    # not a claim that the represented runtime objects are implemented.
    start=text.index('(defparameter *x8632-target-uvector-subtags*')
    end=text.index('(defun x8632-array-type-name-from-ctype',start)
    source_rows={k.lower():v.lower() for k,v in re.findall(r'\((:[\w-]+)\s*\.\s*,([\w-]+)\s*\)',text[start:end])}
    for key,value in selected.items():
        require(':'+key in source_rows and constant(source_rows[':'+key])==value,'D1_TABLE_VALUE '+key)
    helper=fields['ARCH::TARGET-ARRAY-TYPE-NAME-FROM-CTYPE-FUNCTION']
    require(helper['kind']=='source-rebuilt-helper' and type(helper['function_id'])is int,'D1_HELPER_IDENTITY')
    require(len(capture['layout_macros'])==8 and len({r['function_id'] for r in capture['layout_macros']})==8,
            'D1_MACRO_IDENTITIES')
    return dict(integer_descriptions=len(values),field_descriptions=len(fields))
