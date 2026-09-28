// Resident named blobs, one instance per declared library on this Worker.
import {openForeignModule} from './foreign-module.mjs';
const need=(ok,why)=>{if(!ok)throw Error('foreign-libraries: '+why);};
export function foreignLibraries({namespace,libraries,boundary,errorTag,maximumBytes=64*1024*1024}) {
 need(Number.isSafeInteger(maximumBytes)&&maximumBytes>0&&maximumBytes<=64*1024*1024,'LIMIT');
 const session=namespace.session(),rows=new Map(),paths=new Set();
 need(Array.isArray(libraries),'LIBRARIES');
 // Snapshot declarations and import capabilities before any foreign code runs.
 for(const entry of libraries){
  const declaration=structuredClone(entry.declaration),name=declaration?.name;
  need(typeof name==='string'&&name.length>0&&!rows.has(name),'NAME');
  const path=session.realpath(entry.path);
  need(!paths.has(path),'DUPLICATE_PATH');paths.add(path);
  const imports=Object.create(null);
  need(Array.isArray(declaration.imports),'IMPORTS');
  for(const i of declaration.imports)(imports[i.module]??=Object.create(null))[i.name]=entry.imports?.[i.module]?.[i.name];
  rows.set(name,{path,declaration,imports,state:'unopened',library:null});
 }
 return Object.freeze({
  open(name){
   const row=rows.get(name);need(row,'UNKNOWN_LIBRARY');
   need(row.state!=='opening','REENTRY');
   need(row.state!=='failed'&&row.state!=='closed','RETIRED');
   if(row.library){need(row.library.state==='ready','RETIRED');return row.library;}
   row.state='opening';
   try{
    let bytes;const fd=session.open(row.path);
    try{
     const stat=session.fstat(fd);
     need(stat.kind==='file'&&Number.isSafeInteger(stat.size)&&stat.size>0&&stat.size<=maximumBytes,'SIZE');
     bytes=new Uint8Array(stat.size);
     for(let offset=0;offset<bytes.length;){
      const count=Math.min(65536,bytes.length-offset),part=session.pread(fd,offset,count);
      need(part instanceof Uint8Array&&part.length>0&&part.length<=count,'READ');
      bytes.set(part,offset);offset+=part.length;
     }
    }finally{session.close(fd);}
    row.library=openForeignModule({bytes,declaration:row.declaration,imports:row.imports,boundary,errorTag});
    row.state='ready';return row.library;
   }catch(error){row.state='failed';throw error;}
  },
  close(name){
   const row=rows.get(name);need(row,'UNKNOWN_LIBRARY');need(row.state!=='opening','REENTRY');
   row.library?.close();row.state='closed';
  }
 });
}
