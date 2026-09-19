// Bootstrap sealed condition registry. Every wrapper and slot-name vector has
// the U1 layout; no native address or private condition-proxy mask is stored in
// an instance. The owner keeps this registry reachable for the life of the image.
const conditionClasses=[
 ['CONDITION',1,[]],['SIMPLE-CONDITION',9,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],
 ['SIMPLE-ERROR',31,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],
 ['TYPE-ERROR',39,['DATUM','EXPECTED-TYPE','FORMAT-CONTROL']],
 ['CONTROL-ERROR',71,[]],['SIMPLE-WARNING',393,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],
 ['PROGRAM-ERROR',519,[]],['SIMPLE-PROGRAM-ERROR',527,['FORMAT-CONTROL','FORMAT-ARGUMENTS','CONTEXT']],
 ['UNDEFINED-FUNCTION',1031,['NAME','ERROR-TYPE']],['UNBOUND-VARIABLE',2055,['NAME','ERROR-TYPE']],
 ['STORAGE-CONDITION',4099,[]],['ERROR',7,[]]
];
function installConditionClasses(){
 const vector=(p,values,tag=250)=>{store(p,256*values.length+tag);values.forEach((x,i)=>store(p+4*(i+1),x));return p+6;};
 const symbol=(p)=>{store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);return p+6;};
 const shapes=read('native-condition-classes.json');assert.equal(shapes.length,conditionClasses.length);
 let stringTop=660000;
 const literalString=text=>{const p=stringTop;stringTop+=8*Math.ceil((4+4*text.length)/8);assert(stringTop<680000);store(p,256*text.length+191);Array.from(text).forEach((c,i)=>store(p+4+4*i,c.codePointAt(0)));return p+6;};
 const message='Checked Lisp runtime operation failed.';store(680000,256*message.length+191);Array.from(message).forEach((c,i)=>store(680004+4*i,c.codePointAt(0)));
 const rows=[];
 for(let i=0;i<conditionClasses.length;i++){
  const [name,mask,slots]=conditionClasses[i],base=651000+512*i;
  const className=symbol(base+256),wrapperName=symbol(base+288);
  const names=slots.map((_,j)=>symbol(base+320+32*j));
  assert.equal(shapes[i].name,name);assert.deepEqual(shapes[i].slots.map(s=>s.name),slots);
  const slotNames=vector(base+64,names),defaults=vector(base+88,shapes[i].slots.map(s=>s.default===null?NIL:typeof s.default==='string'?literalString(s.default):83));
  // The bootstrap class identity is a standard-instance with NAME and CPL
  // slots. General class mutation and method dispatch are LL11's interface.
  store(base+112,882);store(base+116,0);store(base+120,NIL);store(base+124,base+134);
  vector(base+128,[base+118,className,NIL],106);
  const wrapper=vector(base,[wrapperName,4*i,base+118,slotNames,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,mask*4]);
  rows.push(vector(base+160,[wrapper,mask*4,defaults]));
 }
 vector(650000,rows);
 // Six pre-existing explicit-condition cases are instances too.
 for(let i=0;i<6;i++){
  const p=620000+64*i,slots=conditionClasses[i][2];
  store(p,882);store(p+4,0);store(p+8,651006+512*i);store(p+12,p+22);
  vector(p+16,[p+6,...slots.map(()=>NIL)],106);
 }
}
