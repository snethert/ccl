"""Owner metadata adaptation; inherited functional expectations stay unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def adapt(s):
 s=s.replace("'condition_handlers'", "'condition_handlers','condition_restarts','restart_type','debugger_hook','interrupt_level','gc_service','interrupt_service','expected_function','expected_or','expected_symbol'")
 s=s.replace('set(108,5)','set(108,14)').replace('i<5','i<14').replace('length:5','length:14').replace('[243,243,243,243,243]','[243,243,243,243,243,243,243,243,243,243,243,243,243,243]')
 s=s.replace('i===3?NIL:',"name==='interrupt_level'?0:i>=3?NIL:")
 s=s.replace(' const specialNames=', ''' const restartSymbols=new Map();
 for(const imp of (compiled.values?[...compiled.values()].flatMap(module=>WebAssembly.Module.imports(module)):read('catalog.json').flatMap(row=>row.imports)))if(imp.module==='symbols'&&imp.name.startsWith('restart_name_')&&!restartSymbols.has(imp.name)){
  const address=632006+32*restartSymbols.size;if(address+26>=640000)throw Error('symbol range');restartSymbols.set(imp.name,address);symbols[imp.name]=address;
 }
 const specialNames=''')
 s=s.replace(' const specialNames=', ' symbols.error_message=680006;symbols.condition_registry=650006;symbols.expected_proper_list=640129;\n const specialNames=')
 # Ordinary inherited sources use no arbitrary quoted restart names.
 prelude=(HERE/'objects.mjs').read_text()
 a=s.index(' function installObjects(){')
 # Keep the prelude outside the module-install splice used by the lazy driver.
 b=s.rfind(' for(const m of mods){',0,a)
 if b>=0:s=s[:b]+prelude+'\n'+s[b:]
 else:s=s[:a]+prelude+'\n'+s[a:]
 s=s.replace(' function installObjects(){',' function installObjects(){\n  installConditionClasses();\n  for(const address of restartSymbols.values()){store(address-6,1850);for(let i=1;i<8;i++)store(address-6+4*i,NIL);}')
 s=s.replace('  store(4096,mods.length+1);', '  store(640256,1850);store(640288,1850);for(let j=1;j<8;j++){store(640256+4*j,NIL);store(640288+4*j,NIL);}store(640128,640137);store(640132,640262);store(640136,NIL);store(640140,640294);store(640000,640009);store(640004,symbols.expected_or);store(640008,640017);store(640012,symbols.expected_symbol);store(640016,NIL);store(640020,symbols.expected_function);store(symbols.expected_function+2,640001);\n  store(4096,mods.length+1);')
 return s

def adapt_loader(s):
 """The installation-control owner supplies the same new immutable imports."""
 prelude=(HERE/'objects.mjs').read_text()
 owner='''
 const NIL=77825;
 const specialNames=['condition_handlers','condition_restarts','restart_type','debugger_hook','interrupt_level','gc_service','interrupt_service','expected_function','expected_or','expected_symbol'];
 specialNames.forEach((name,i)=>{const p=600000+32*i;symbols[name]=p+6;store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);store(p+8,name==='interrupt_level'?0:NIL);store(p+28,4*(i+1));});
 store(tcr+104,610000);store(tcr+108,specialNames.length+1);for(let i=0;i<=specialNames.length;i++)store(610000+4*i,243);
 symbols.condition_registry=650006;symbols.error_message=680006;symbols.expected_proper_list=640129;
 const restartSymbols=new Map();for(const r of catalog)for(const imp of r.imports)if(imp.module==='symbols'&&imp.name.startsWith('restart_name_')&&!restartSymbols.has(imp.name)){const p=632000+32*restartSymbols.size;assert(p+32<640000);restartSymbols.set(imp.name,p+6);symbols[imp.name]=p+6;store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);}
'''+prelude+'\n installConditionClasses();\n'
 assert s.count(' const options={')==1
 s=s.replace(' const options={',owner+' const options={')
 s=s.replace('[[48,262144]', '[[76,700000],[80,700000],[84,900000],[88,920000],[92,920000],[96,940000], [48,262144]')
 return s
