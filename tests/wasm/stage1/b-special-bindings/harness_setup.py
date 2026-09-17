"""Owner state and literal oracle shared by eager and inherited lazy execution."""
def adapt(s):
 s=s.replace(" const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));", " const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));\n const specialNames=['dyn_a','dyn_b','dyn_u'];specialNames.forEach((name,i)=>symbols[name]=600006+32*i);")
 s=s.replace(' function installObjects(){', ''' function installObjects(){
  set(104,610000);set(108,4);set(112,0);set(0,37);
  for(let i=0;i<4;i++)store(610000+4*i,243);
  specialNames.forEach((name,i)=>{const base=symbols[name]-6;store(base,1850);for(let j=1;j<8;j++)store(base+4*j,NIL);store(base+8,i===2?51:4*(101+2*i));store(base+28,4*(i+1));});''')
 s=s.replace('[1,4,5,8].includes(code)','[1,4,5,8,10].includes(code)').replace("code===8?'CONTROL':'DESIGNATOR'", "code===8?'CONTROL':code===10?'UNBOUND':'DESIGNATOR'")
 s=s.replace("assert.deepEqual({status,values:result,nodes},c.expected,c.id+': native/logical result');", "const specials=specialNames.map(name=>load(symbols[name]+2)===51?'unbound':decode(load(symbols[name]+2)));assert.deepEqual({status,values:result,nodes,specials},c.expected,c.id+': native/logical result');assert.equal(get(112),0,c.id+': binding chain restored');assert.deepEqual(Array.from({length:4},(_,i)=>load(610000+4*i)),[243,243,243,243],c.id+': binding vector restored');")
 s=s.replace('observations.push({id:c.id,observed,start,status,values:result,nodes})','observations.push({id:c.id,observed,start,status,values:result,nodes,specials})')
 return s
