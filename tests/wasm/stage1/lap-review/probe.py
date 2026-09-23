"""Probe reviewed LAP modules without recompiling or changing the fixture."""
from pathlib import Path
import argparse, json, subprocess
parser=argparse.ArgumentParser()
parser.add_argument('execution', type=Path)
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
p=args.execution.resolve()
s=(p/'check.mjs').read_text().replace("from './install.mjs'", "from './lap-probe-install.mjs'")
s=s.replace("status:'PASS'", "status:'OBSERVATIONS'").replace("console.log('PASS:',", "console.log('LAP probe calls:',")
installer=(p/'install.mjs').read_text()
clause='catch(e){failure=e;}'
assert installer.count(clause)==1
installer=installer.replace(clause, "catch(e){failure=e;if(e instanceof WebAssembly.RuntimeError)globalThis.lapTrap=String(e);}")
(p/'lap-probe-install.mjs').write_text(installer)
s=s[:s.index('  for(const expected of native.filter')]+'''
  const findings=[];
  const cases=[
    {definition:'%SYMPTR->SYMBOL',raw:77870,expected:77825},
    ...[536870911.4,536870911.5,2147483647,2147483647.49,2147483647.5,2147483647.75,2147483648,-2147483648].map(value=>({definition:'%ROUND-NEAREST-DOUBLE-FLOAT->FIXNUM',value})),
  ];
  for(const probe of cases){
    const expected=native.find(row=>row.definition===probe.definition);
    bytes(tcr,256).fill(0);bytes(config,96).fill(0);put(tcr+200,7);
    for(const [offset,value] of [[48,base],[52,base+size],[56,base],[68,131072],[72,196608],
       [128,root],[80,700000],[76,700000],[84,780000],[88,900000],[92,900000],[96,1000000],[120,132352],[124,132512],[104,650000]])put(tcr+offset,value);
    put(config,tcr);put(config+16,other);put(config+20,other+size);
    put(config+68,32768);put(config+72,4600000);put(config+80,1800000);
    initialSymbolFields.forEach(([p,v])=>put(p,v));gen.extraRoots.length=originalRootCount;gen.reset(movingPools[base]);services();
    put(config+76,gen.extraRoots.length);gen.extraRoots.forEach((slot,i)=>put(4600000+4*i,slot));
    let arg=probe.raw;
    if(arg===undefined){
      const b=new ArrayBuffer(8),d=new DataView(b);d.setFloat64(0,probe.value,true);
      arg=encode({double:[d.getUint32(4,true),d.getUint32(0,true)]});
    }
    put(root,0);put(root+4,1);put(root+8,arg);
    globalThis.lapTrap=null;
    try { findings.push({...probe,returned:gen.invoke(expected.name,[arg])}); }
    catch(error){findings.push({...probe,error:String(error),underlyingTrap:globalThis.lapTrap,trap:error instanceof WebAssembly.RuntimeError});}
  }
  parentPort.postMessage({base,comparisons:cases.length,findings});
}
'''
(p/'lap-boundary-probe.mjs').write_text(s)

subprocess.run(['/usr/local/bin/node', str(p/'lap-boundary-probe.mjs'), str(p), str(args.output.resolve())], check=True)
report=json.loads(args.output.read_text())
assert [r['base'] for r in report['rows']]==[262144,2147483648]
for row in report['rows']:
    cases=row['findings']
    assert cases[0]['returned']==[77870] and cases[0]['expected']==77825
    for c in cases:
        if c.get('value') in (2147483647.5,2147483647.75):
            assert 'float unrepresentable in integer range' in c['underlyingTrap']
            assert 'restored TCR 64' in c['error']
        elif c.get('value') in (536870911.5,2147483647,2147483647.49,2147483648,-2147483648):
            assert c['error'].endswith('checked 5') and c['underlyingTrap'] is None
print('Reproduced NIL-pointer error and rounding traps at both placements.')
