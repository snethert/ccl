// Immutable owner inputs, not reads from Node's process or a browser's URL.
// Native Darwin composes adjacent pairs without Unicode canonical reordering.
import {pairs} from './composition.mjs';
const combinations=new Map(pairs.map(([a,b,c])=>[a*65536+b,c]));
export function precompose(value){const out=[];for(const c of value){const n=c.codePointAt(0),v=out.length&&n<4096?combinations.get(out.at(-1)*65536+n):undefined;if(v===undefined)out.push(n);else out[out.length-1]=v;}return out.map(c=>String.fromCodePoint(c)).join('');}
const need=(ok,why)=>{if(!ok)throw Error('startup inputs: '+why);};
function text(value){
 need(typeof value==='string','string');const chars=[...value];
 need(chars.length<=4096&&!chars.some(c=>{const n=c.codePointAt(0);return n===0||n>=0xd800&&n<=0xdfff;}),'string domain');return value;
}
export function startupInputs(input){
 need(input&&Object.keys(input).length===2&&Object.hasOwn(input,'imageName')&&Object.hasOwn(input,'arguments'),'fields');
 const imageName=text(precompose(text(input.imageName)));
 need(Array.isArray(input.arguments)&&input.arguments.length<=256,'argument count');
 const args=Array.from(input.arguments,text);need([...imageName].length+args.reduce((n,s)=>n+[...s].length,0)<=65536,'text budget');
 return Object.freeze({imageName,arguments:Object.freeze(args)});
}
export function materializeInputs({memory,base,end,input}){
 const values=startupInputs(input),strings=[values.imageName,...values.arguments].map(s=>[...s].map(c=>c.codePointAt(0)));
 const widths=strings.map(s=>Math.ceil((4+4*s.length)/8)*8),size=widths.reduce((n,w)=>n+w,0)+8*values.arguments.length;
 need(memory instanceof WebAssembly.Memory&&Number.isSafeInteger(base)&&base>=0&&base%8===0&&Number.isSafeInteger(end)&&end===base+size&&end<=memory.buffer.byteLength,'extent');
 const d=new DataView(memory.buffer),put=(p,n)=>d.setUint32(p,n,true);let cursor=base;
 // All validation precedes the first write. Strings are independent native reads.
 const pointers=strings.map((s,i)=>{const p=cursor;cursor+=widths[i];new Uint8Array(memory.buffer,p,widths[i]).fill(0);put(p,s.length*256+191);s.forEach((c,j)=>put(p+4+j*4,c));return p+6;});
 let head=77825,previous=0;
 for(const p of pointers.slice(1)){const cell=cursor;cursor+=8;put(cell,77825);put(cell+4,p);if(previous)put(previous,cell+1);else head=cell+1;previous=cell;}
 return Object.freeze({image:pointers[0],arguments:head,end,values});
}
export function inputBytes(input){const v=startupInputs(input);return [v.imageName,...v.arguments].reduce((n,s)=>n+Math.ceil((4+4*[...s].length)/8)*8,8*v.arguments.length);}
