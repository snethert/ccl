// The READY profile admits strong EQ tables. Bind public function cells to
// the same reviewed Lisp wrappers used by direct class-mode calls.
export function bindReadyTables({owners,gen,get,put,bindings:tableBindings}) {
  const symbol = (pkg,name) => {
    const rows=owners.filter(x=>x.package===pkg&&x.name===name);
    if(rows.length!==1)throw Error('READY binding identity: '+pkg+'::'+name);
    return gen.ownerWords.get(rows[0].id);
  };
  // Resolve every binding before publishing any of them.
  const bindings=tableBindings.map(([pkg,name,target])=>{
    const slot=symbol(pkg,name)+6,fn=get(symbol('CCL',target)+6);
    if((fn&7)!==6)throw Error('READY function tag');
    if((get(fn-6)&255)!==42)throw Error('READY function header');
    return [slot,fn];
  });
  for(const [slot,fn] of bindings)put(slot,fn);
}
