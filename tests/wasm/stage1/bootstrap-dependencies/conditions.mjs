 const shapes=JSON.parse(fs.readFileSync(dir+'/compiled/native-condition-classes.json'));
 const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7,8199,16391,49159,81927,147463,278535,540679];
 function vector(words,tag=250){const p=cursor;cursor+=8*Math.ceil((4+4*words.length)/8);put(p,words.length*256+tag);words.forEach((w,i)=>put(p+4+4*i,w));if(!(words.length&1))put(p+4+4*words.length,0);return p+6;}
 function string(text){return vector(Array.from(text).map(c=>c.codePointAt(0)),191);}
 assert.equal(shapes.length,masks.length);
 symbols.condition_registry=vector(shapes.map((shape,i)=>{
   const name=symbol('class_'+shape.name),fields=vector(shape.slots.map((s,j)=>symbol('slot_'+i+'_'+j)));
   const defaults=vector(shape.slots.map(s=>s.default===null?NIL:typeof s.default==='string'?string(s.default):83));
   const instance=cursor;cursor+=16;[882,0,NIL,NIL].forEach((v,j)=>put(instance+4*j,v));
   put(instance+12,vector([instance+6,name,NIL],106));
   const wrapper=vector([name,4*i,instance+6,fields,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,masks[i]*4]);
   return vector([wrapper,masks[i]*4,defaults]);
 }));
 symbols.error_message=string('Checked Lisp runtime operation failed.');

 owners.forEach((row,i)=>put(600000+32*i+4,string(row.name)));
 [1850,string('T'),77838,NIL,NIL,8,NIL,0].forEach((v,i)=>put(77832+4*i,v));
 [1850,string('NIL'),NIL,NIL,NIL,8,NIL,0].forEach((v,i)=>put(77864+4*i,v));
