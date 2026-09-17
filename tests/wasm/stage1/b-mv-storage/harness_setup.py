"""Owner state and literal oracle shared by eager and inherited lazy execution."""
def adapt(s):
 s=s.replace(" const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));", " const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));\n const specialNames=['dyn_a','dyn_b','dyn_u'];specialNames.forEach((name,i)=>symbols[name]=600006+32*i);")
 s=s.replace(' function installObjects(){', ''' function installObjects(){
  set(104,610000);set(108,4);set(112,0);set(0,37);
  for(let i=0;i<4;i++)store(610000+4*i,243);
  specialNames.forEach((name,i)=>{const base=symbols[name]-6;store(base,1850);for(let j=1;j<8;j++)store(base+4*j,NIL);store(base+8,i===2?51:4*(101+2*i));store(base+20,0);store(base+28,4*(i+1));});''')
 s=s.replace('[1,4,5,8].includes(code)','[1,4,5,8,10,12].includes(code)').replace("code===8?'CONTROL':'DESIGNATOR'", "code===8?'CONTROL':code===10?'UNBOUND':code===12?'BINDING':'DESIGNATOR'")
 s=s.replace("assert.deepEqual({status,values:result,nodes},c.expected,c.id+': native/logical result');", "const specials=specialNames.map(name=>load(symbols[name]+2)===51?'unbound':decode(load(symbols[name]+2)));assert.deepEqual({status,values:result,nodes,specials},c.expected,c.id+': native/logical result');assert.equal(get(112),0,c.id+': binding chain restored');assert.deepEqual(Array.from({length:4},(_,i)=>load(610000+4*i)),[243,243,243,243],c.id+': binding vector restored');")
 s=s.replace('observations.push({id:c.id,observed,start,status,values:result,nodes})','observations.push({id:c.id,observed,start,status,values:result,nodes,specials})')
 assert s.count('store(512,mods.length+1);store(516,1);for(let i=1;i<=mods.length;i++){store(520+8*i,17);store(524+8*i,23);}')==1, 'OBSOLETE_REGISTRY_SITE'
 s=s.replace('store(512,mods.length+1);store(516,1);for(let i=1;i<=mods.length;i++){store(520+8*i,17);store(524+8*i,23);}','')
 s=s.replace('const compiled=new Map',"assert(4104+16*(mods.length+1)<=16384,'code registry exceeds fixture-owned range');\nassert(196608+32*mods.length<=262144,'function symbols exceed fixture-owned range');\nconst compiled=new Map")
 s=s.replace("   {name:'walk_list',args:[head],values:[284,292],heap:0},","   {name:'mvc_tail',args:[head],values:[284,292],heap:0},\n   {name:'mvb_tail',args:[head],values:[284,292],heap:0},\n   {name:'mvc_tail_indirect',args:[handles.get('mvc_tail_indirect'),head],values:[284,292],heap:0},\n   {name:'walk_list',args:[head],values:[284,292],heap:0},")
 return storage(s)

def storage(s):
 s=s.replace(' function installObjects(){', ' function installObjects(){\n  set(80,700000);set(76,700000);set(84,900000);')
 s=s.replace("let n=load(head+4);if(head===activeFrame)","let n=load(head+4),pointer=head+8;if(n===0xffffffff){pointer=load(head+8);n=load(head+12);const inline=pointer===head+32&&n<=4&&head>=get(68)&&head+48<=get(72);assert(inline||pointer===0&&n===0||pointer>=get(80)+16&&pointer+4*n<=get(76),label+': dynamic result extent');if(n&&!inline){assert(load(pointer-12)!==0,label+': live result owner');assert.equal(load(pointer-4),1381384241,label+': result buffer marker');assert(n<=load(pointer-8),label+': owned result extent');}}if(head===activeFrame)")
 s=s.replace("assert(n<=(get(72)-head-8)/4,label+': root capacity');for(let i=0;i<n;i++){let p=head+8+4*i;", "assert(n<=(memory.buffer.byteLength-pointer)/4,label+': root capacity');for(let i=0;i<n;i++){let p=pointer+4*i;")
 s=s.replace("inspect('returned '+c.id);", "assert.equal(get(76),get(80),c.id+': temporary results released');inspect('returned '+c.id);")
 return s
