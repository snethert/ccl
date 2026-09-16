"""Bounded nonexecuting reader for the two intentionally changed U1 FASLs.
Derived from the reviewed DataFasl reader. Additional native compiler forms
are represented literally, including executable bytes and eval forms.
"""
import struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'doc/WASM/tools'))
from r6_registration import require,symbol,conslist,elements,LiteralSource,DataFasl
class CompilerFasl:
    """Complete, bounded decoder for this registration FASL profile.

    Preserve every decoded form, location, identity reference and raw opcode
    offset. Preserve the original package thunk as raw code; never execute it.
    """
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.refs = []
        self.ops = []
        self.capacity = None
        self.package = 'COMMON-LISP-USER'
        self.spans = {}

    def take(self, n):
        require(0 <= n <= len(self.data)-self.pos, 'FASL_TRUNCATED')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def byte(self):
        return self.take(1)[0]

    def count(self):
        result = 0
        for shift in range(0, 35, 7):
            b = self.byte()
            result |= (b & 127) << shift
            if b & 128:
                require(result <= 4096, 'FASL_COUNT_BOUND')
                return result
        raise ValueError('FASL_COUNT_BOUND')

    def string(self):
        data = self.take(self.count())
        require(all(0 <= b < 128 for b in data), 'FASL_STRING')
        return data.decode('ascii')

    def expr(self, depth=0):
        require(depth < 64, 'FASL_DEPTH')
        start, raw = self.pos, self.byte()
        op, push = raw & 127, bool(raw & 128)
        require(op not in (2, 20), 'FASL_EXECUTABLE_OPCODE')
        require(raw != 255 and op in (0, 3, 4, 10, 15, 18, 23, 25, 28, 34, 39, 44, 45, 47, 57, 63, 65, 66, 67, 69, 70, 27, 35, 37, 38, 40, 41, 43, 49, 59, 64, 68, 34, 27, 57, 14, 17, 48, 29, 6, 52, 71), 'FASL_UNKNOWN_OPCODE')
        require(not push or op in (3, 10, 15, 18, 28, 44, 45, 63, 65, 66, 67, 69, 59, 64, 68, 34, 27, 57, 14, 17, 48, 29, 6, 52, 71), 'FASL_EPUSH')
        self.ops.append({'offset': start, 'opcode': op, 'epush': push})
        slot = None
        if push and op not in (28,27,63,66,71):
            slot = len(self.refs)
            self.refs.append(None)
        expr = lambda: self.expr(depth+1)
        if op == 0:
            value = {'noop': True}
        elif op == 3:
            size, words = self.count(), self.count()
            require(0 < words <= size <= 4096, 'FASL_FUNCTION_SIZE')
            value = {'function': {'code': self.take(words*8).hex(),
                                  'constants': [expr() for _ in range(size-words)]}}
        elif op == 4:
            value = {'call': expr()}
            if value['call'].get('function', {}).get('constants') == ['CCL', symbol('CCL::SET-PACKAGE'), -536870912]: self.package = 'CCL'
        elif op == 10:
            value = struct.unpack('>h', self.take(2))[0]
        elif op == 57:
            value = struct.unpack('>i', self.take(4))[0]
        elif op == 18:
            value = None
        elif op == 25:
            index = self.count()
            require(index < len(self.refs) and self.refs[index] is not None, 'FASL_REFERENCE')
            value = self.refs[index]
        elif op == 65:
            value = {'package': self.string()}
        elif op in (63, 66):
            package = expr()
            require(isinstance(package, dict) and set(package) == {'package'}, 'FASL_PACKAGE')
            value = symbol(package['package']+'::'+self.string())
        elif op in (64,67):
            value = symbol(self.package+'::'+self.string())
        elif op == 71:
            value = {'istruct-cell':expr()}
        elif op == 52:
            value = {'istruct':[expr() for _ in range(self.count())]}
        elif op == 6:
            value = {'char':self.byte()}
        elif op == 29:
            value = {'u16vector':self.take(2*self.count()).hex()}
        elif op == 48:
            value = {'u32vector':self.take(4*self.count()).hex()}
        elif op == 17:
            value = {'tvector':[expr() for _ in range(self.count())]}
        elif op == 14:
            value = {'u8vector':self.take(self.count()).hex()}
        elif op == 68:
            value = {'uninterned': self.string()}
        elif op == 59:
            value = struct.unpack('>q', self.take(8))[0]
        elif op in (35,37,43):
            value = {{35:'defun',37:'defmacro',43:'prog1'}[op]:[expr(),expr()]}
        elif op in (27,40,49):
            value = {{27:'symfn',40:'defvar',49:'provide'}[op]:expr()}
        elif op in (38,41):
            value = {{38:'defconstant',41:'defvar-init'}[op]:[expr(),expr(),expr()]}
        elif op == 69:
            value = self.string()
        elif op == 15:
            value = {'cons': [expr(), expr()]}
        elif op in (44, 45):
            items = [expr() for _ in range(self.count()+1)]
            tail = None if op == 44 else expr()
            for item in reversed(items):
                tail = {'cons': [item, tail]}
            value = tail
        elif op == 34:
            subtag, count = self.byte(), self.count()
            require(count <= 4096, 'FASL_LOCATION_VECTOR')
            value = {'vector': {'subtag': subtag, 'values': [expr() for _ in range(count)]}}
        elif op == 39:
            value = {'defparameter': [expr(), expr(), expr()]}
        elif op in (23, 28, 47, 70):
            value = {{23: 'platform', 28: 'eval', 47: 'source', 70: 'location'}[op]: expr()}
            if op == 28:
                # Decode, never execute, the two original metadata forms.
                package = conslist(symbol('CCL::SET-PACKAGE'), 'CCL')
                source_note = conslist(symbol('CCL::FIND-CLASS-CELL'),
                    conslist(symbol('COMMON-LISP::QUOTE'), symbol('CCL::SOURCE-NOTE')),
                    symbol('COMMON-LISP::T'))
                # Represent initializer forms as data only; never evaluate them.
                if value['eval'] == package:
                    self.package = 'CCL'
        if push:
            if op in (28,27,63,66,71):
                self.refs.append(value)
            else:
                self.refs[slot] = value
            require(len(self.refs) <= self.capacity, 'FASL_TABLE_CAPACITY')
        if isinstance(value, dict) and op != 25:
            self.spans[id(value)] = (start, self.pos)
        return value

    def decode(self):
        require(len(self.data) <= 1048576, 'FASL_SIZE_BOUND')
        require(struct.unpack('>HHII', self.take(12)) == (0xff00, 1, 12, len(self.data)-12), 'FASL_HEADER')
        require(self.take(6) == bytes.fromhex('ff6200000000'), 'FASL_VERSION')
        require(self.byte() == 24, 'FASL_TABLE')
        self.capacity = self.count()
        result = []
        while self.pos < len(self.data) and self.data[self.pos] != 255:
            result.append(self.expr())
        require(self.byte() == 255 and self.pos == len(self.data), 'FASL_END')
        return result

def compare_compiler(before,after,source_before,source_after):
    """Explain complete decoded components; no executable-byte normalization."""
    import copy,hashlib
    a=CompilerFasl(before).decode();b=CompilerFasl(after).decode()
    require(len(a)==len(b),'COMPILER_FORM_COUNT')
    insertions=[('    (:arm *arm-xload-modules*)))',"    (:wasm32 '(xwasm32fasload xfasload))\n"),
      ('    (:arm (append *arm-compiler-modules*',"    (:wasm32 '(wasm32-arch wasm32-backend))\n")]
    expected=source_before;positions=[]
    for anchor,text in insertions:
        require(source_before.count(anchor)==1,'COMPILER_SOURCE_ANCHOR')
        positions.append((source_before.index(anchor),len(text)))
        expected=expected.replace(anchor,text+anchor)
    require(expected==source_after,'COMPILER_SOURCE_BOUND')
    notes=0
    def shift(pos):return pos+sum(n for start,n in positions if pos>=start)
    def translate(x):
        nonlocal notes
        if isinstance(x,list):return [translate(v) for v in x]
        if not isinstance(x,dict):return x
        y={k:translate(v) for k,v in x.items()}
        if set(x)=={'vector'}:
            v=x['vector'];items=v['values']
            if v['subtag']==54 and len(items)==4 and items[0]=={'cons':[{'eval':conslist(symbol('CCL::FIND-CLASS-CELL'),conslist(symbol('COMMON-LISP::QUOTE'),symbol('CCL::SOURCE-NOTE')),symbol('COMMON-LISP::T'))},None]}:
                span=items[3]
                if isinstance(span,int):start,length=divmod(span,1<<14);end=start+length
                else:require(isinstance(span,dict) and set(span)=={'cons'},'SOURCE_NOTE_RANGE');start,end=span['cons']
                require(0<=start<=end<=len(source_before),'SOURCE_NOTE_BOUNDS')
                start,end=shift(start),shift(end);length=end-start
                y['vector']['values'][3]=(start<<14)+length if length<(1<<14) else {'cons':[start,end]}
                notes+=1
        return y
    translated=translate(a);changed=[]
    permitted={'CCL::TARGET-XLOAD-MODULES','CCL::TARGET-COMPILER-MODULES'}
    for i,(old,new) in enumerate(zip(translated,b)):
        if old==new:continue
        require(set(old)==set(new)=={'defun'},'UNEXPLAINED_COMPILER_COMPONENT '+str(i))
        of=old['defun'][0]['function'];nf=new['defun'][0]['function'];name=of['constants'][-2]
        require(name==nf['constants'][-2] and name.get('symbol') in permitted,'UNEXPLAINED_COMPILER_FUNCTION')
        require(of['constants'][-1]==nf['constants'][-1] and old['defun'][1]==new['defun'][1],'COMPILER_SIGNATURE_METADATA')
        require(symbol('KEYWORD::WASM32') in nf['constants'],'WASM_BRANCH_MISSING')
        changed.append({'name':name['symbol'],'form_index':i,'before':a[i],'after':new,
          'before_code_sha256':hashlib.sha256(bytes.fromhex(of['code'])).hexdigest(),
          'after_code_sha256':hashlib.sha256(bytes.fromhex(nf['code'])).hexdigest()})
    require({r['name'] for r in changed}==permitted and len(changed)==2,'COMPILER_CHANGE_SET')
    return {'decoded_forms':len(a),'source_notes_checked':notes,'unchanged_except_source_locations':len(a)-2,'intentional_executable_components':changed}


def compare_systems(before,after,source_before,source_after):
    import copy
    readers=[DataFasl(x) for x in (before,after)];a,b=[r.decode() for r in readers]
    sources=[LiteralSource(x) for x in (source_before,source_after)];forms=[r.decode() for r in sources]
    require(len(a)==len(b)==6,'SYSTEMS_FORMS')
    for parsed,src,reader in zip((a,b),forms,sources):
        definition=elements(src[1]);quoted=elements(definition[2])
        require(parsed[5]['defparameter']==[definition[1],quoted[1],None],'SYSTEMS_SOURCE_DATA')
        require(parsed[4]['location']['vector']['values'][-1]=={'cons':reader.spans[1]},'SYSTEMS_SOURCE_SPAN')
    require(a[:4]==b[:4],'SYSTEMS_CODE_OR_METADATA')
    expected=copy.deepcopy(a[4]);expected['location']['vector']['values'][-1]={'cons':sources[1].spans[1]}
    require(expected==b[4],'SYSTEMS_LOCATION')
    old=elements(a[5]['defparameter'][1]);new=elements(b[5]['defparameter'][1])
    at=next(i for i,row in enumerate(old) if elements(row)[0]==symbol('CCL::BACKEND'))+1
    added=[conslist(symbol('CCL::'+n.upper()),'ccl:bin;'+n,conslist(path)) for n,path in [
      ('wasm32-arch','ccl:compiler;WASM32;wasm32-arch.lisp'),('wasm32-backend','ccl:compiler;WASM32;wasm32-backend.lisp'),('xwasm32fasload','ccl:xdump;xwasm32-fasload.lisp')]]
    require(new==old[:at]+added+old[at:],'SYSTEMS_ADDITION_BOUND')
    spans=[r.spans for r in readers];locs=[spans[i][id(x[4])] for i,x in enumerate((a,b))]
    lists=[spans[i][id(x[5]['defparameter'][1])][0] for i,x in enumerate((a,b))]
    starts=[spans[i][id(x[0])][0] for i,x in enumerate((old,new))]
    edits=[(8,12,before[8:12]),(*locs[1],before[slice(*locs[0])]),
      (lists[1],starts[1],before[lists[0]:starts[0]]),
      (spans[1][id(new[at])][0],spans[1][id(new[at+2])][1],b'')]
    accounted=after
    for start,end,replacement in sorted(edits,reverse=True):accounted=accounted[:start]+replacement+accounted[end:]
    require(accounted==before,'SYSTEMS_UNEXPLAINED_BYTES')
    return {'decoded_forms':6,'added_entries':3,'unchanged_executable_bytes':len(bytes.fromhex(a[3]['call']['function']['code'])),'byte_accounting':'Only three entries, list count, source extent and file length differ.'}
