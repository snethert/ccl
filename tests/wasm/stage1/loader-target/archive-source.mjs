// Main-thread archive file source. Every read is authenticated, including a
// reread; standalone ArrayBuffers can be transferred without pooled aliases.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
export function standalone(path){
 const size=fs.statSync(path).size,buffer=new ArrayBuffer(size),fd=fs.openSync(path,'r');
 try{let offset=0;while(offset<size){const n=fs.readSync(fd,new Uint8Array(buffer,offset),0,size-offset,offset);
  if(!n)throw Error('archive source: truncated input');offset+=n;}}
 finally{fs.closeSync(fd);}return buffer;
}
export function readArchiveSource(source){
 const bytes=standalone(source.binaryPath),metadata=standalone(source.metadataPath);
 const digest=b=>createHash('sha256').update(new Uint8Array(b)).digest('hex');
 if(digest(bytes)!==source.digest)throw Error('archive source: BINARY_DIGEST');
 if(digest(metadata)!==source.manifestDigest)throw Error('archive source: MANIFEST_DIGEST');
 return {bytes,metadata};
}
export function archiveSource(dir,row,kind='runtime'){
 // Legacy build directories lack counts in their small directory. Read only
 // that metadata to adapt them; new producers include the counts directly.
 let functions=row.function_count,roots=row.root_cells;
 if(functions===undefined||roots===undefined){const full=JSON.parse(fs.readFileSync(dir+'/'+row.manifest));
  const m=kind==='boot'?full.archive:full;functions=m.function_count;roots=m.root_cells;}
 return {kind,digest:row.sha256,manifestDigest:row.manifest_sha256,
  binaryPath:dir+'/'+row.file,metadataPath:dir+'/'+row.manifest,function_count:functions,root_cells:roots};
}
