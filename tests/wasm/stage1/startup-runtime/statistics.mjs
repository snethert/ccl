// Session-local full-collector counters. No foreign buffers or heap pointers.
export class CollectionStatistics {
 #clock; #microseconds=0n; #collections=0n; #freed=0n; #timingValid=true;
 constructor(clock=()=>BigInt(Math.floor(performance.now()*1000))) {
  if(typeof clock!=='function')throw Error('statistics clock');
  this.#clock=clock;
 }
 sample(){try{const n=this.#clock();return typeof n==='bigint'&&n>=0n?n:null;}catch{return null;}}
 committed(start,reclaimed){
  // The heap is already committed: a bad clock must not turn success into a
  // collection refusal. Instead make timing explicitly unavailable.
  const end=this.sample(); this.#collections++; this.#freed+=BigInt(reclaimed);
  if(start===null||end===null||end<start)this.#timingValid=false;
  else this.#microseconds+=end-start;
 }
 snapshot(){return Object.freeze({microseconds:this.#microseconds,collections:this.#collections,bytesFreed:this.#freed,timingValid:this.#timingValid});}
 gctime(units=1000){
  if(!this.#timingValid)throw Error('statistics timing unavailable');
  if(units!==1000&&units!==1000000)throw Error('statistics time units');
  let n=this.#microseconds;
  if(units===1000){let q=n/1000n,r=n%1000n;n=q+(r>500n||(r===500n&&(q&1n))?1n:0n);}
  // Native slots: total, full, generation 0, generation 1, generation 2.
  // This owner admits only the full, non-generational copying collector.
  return Object.freeze([n,n,0n,0n,0n]);
 }
}
