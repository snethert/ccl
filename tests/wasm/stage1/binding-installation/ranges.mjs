// Body extents, including local declarations, in engine-validated module bytes.
// This does not decode instructions or infer executable entrypoints from offsets.
import {inspect} from './binary.mjs';
export function entryRanges(bytes){
 const m=inspect(bytes);if(!WebAssembly.validate(bytes))throw Error('INVALID_WASM');
 let p=8,end=bytes.length;const leb=()=>{let v=0;for(let i=0;i<5;i++){if(p>=end)throw Error('RANGE_TRUNCATED');const b=bytes[p++];if(i===4&&b>15)throw Error('RANGE_LEB');v+=(b&127)*2**(7*i);if(!(b&128))return v;}throw Error('RANGE_LEB');};
 const bodies=[],imported=m.imports.filter(i=>i.kind==='function').length;
 while(p<bytes.length){end=bytes.length;const section=bytes[p++],n=leb(),stop=p+n;if(stop>end)throw Error('RANGE_SECTION');end=stop;
  if(section===10){const count=leb();if(count!==m.functions.length-imported)throw Error('RANGE_COUNT');for(let i=0;i<count;i++){const length=leb(),start=p,finish=start+length;if(!length||finish>end)throw Error('RANGE_BODY');bodies.push({index:imported+i,start,end:finish});p=finish;}if(p!==stop)throw Error('RANGE_TRAILING');}p=stop;
 }
 return m.exports.map(e=>{const b=bodies.find(b=>b.index===e.index);if(e.kind!==0||!b)throw Error('RANGE_EXPORT');return {role:e.name,...b};});
}
