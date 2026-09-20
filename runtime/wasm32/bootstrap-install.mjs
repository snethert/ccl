// Own the byte catalog and entry acquisition for a BootstrapSchedule.
// Invocation/argument construction remains a synchronous trusted owner callback.
import {LazyLoader,sha,validate} from './loader.mjs';
import {snapshotBytes} from './bytes.mjs';
const need=(ok,why)=>{if(!ok)throw Error(why);};
export function scheduleInstaller({modules,loaderOptions,imports,invoke}) {
  need(typeof invoke==='function','INVOKER');
  const catalog=new Map();
  for(const m of modules){
    need(!catalog.has(m.name)&&m.record.name===m.name,'CATALOG_UNIQUE');
    const record=structuredClone(m.record),bytes=snapshotBytes(m.bytes);
    validate(bytes,record);catalog.set(m.name,{record,bytes});
  }
  const loader=new LazyLoader({...loaderOptions,catalog:[...catalog.values()].map(m=>m.record),
    readBytes:name=>snapshotBytes(catalog.get(name).bytes)});
  const installed=[];
  return Object.freeze({
    install(m,row){
      const own=catalog.get(m.name);
      need(own&&row.module===m.name&&row.sha256===own.record.sha256&&
        JSON.stringify(m.record)===JSON.stringify(own.record)&&sha(m.bytes)===own.record.sha256,'INSTALL_PLAN_IDENTITY');
      const entry=loader.defer(m.name,imports).host_entry;
      const before=loader.events.length;loader.install(own.record.slot);
      const events=loader.events.slice(before);
      need(events.length===1&&events[0].event==='INSTALLED'&&events[0].slot===own.record.slot&&
        events[0].sha256===row.sha256,'INSTALLED_DIGEST');
      installed.push({name:m.name,slot:own.record.slot,sha256:events[0].sha256});
      const boundRow=structuredClone(row);
      return ()=>invoke(entry,structuredClone(boundRow));
    },
    installed:()=>structuredClone(installed)
  });
}
