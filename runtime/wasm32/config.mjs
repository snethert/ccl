// Process configuration is supplied by a trusted host owner, not discovered here.
const need=(ok,why)=>{if(!ok)throw Error(why);};
const int=(x,lo,hi)=>Number.isSafeInteger(x)&&x>=lo&&x<=hi;
export function processConfiguration(raw){
 need(raw&&Object.getPrototypeOf(raw)===Object.prototype,'CONFIG_OBJECT');
 need(Object.keys(raw).sort().join(',')==='clockTicks,cpuCount,defaults,pageSize,stackSize','CONFIG_FIELDS');
 const x=structuredClone(raw),max=536870911;
 need(int(x.pageSize,1,268435456)&&(x.pageSize&(x.pageSize-1))===0,'PAGE_SIZE');
 need(int(x.clockTicks,-1,max),'CLOCK_TICKS');need(int(x.cpuCount,1,max),'CPU_COUNT');
 need(int(x.stackSize,-max-1,max),'STACK_SIZE');
 need(Array.isArray(x.defaults)&&x.defaults.length===3&&x.defaults.every(v=>int(v,1,max)),'STACK_DEFAULTS');
 const ticks=Math.max(1000,x.clockTicks),period=Math.floor(1000000000/ticks);
 const active=x.stackSize>0,half=active?Math.floor(x.stackSize/2):0;
 return Object.freeze({pageSize:x.pageSize,ticks,period,cpuCount:x.cpuCount,active,
  stackSize:x.stackSize,half,defaults:Object.freeze(x.defaults)});
}
