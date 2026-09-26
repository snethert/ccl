"""Reuse the owner transaction checks for both hash-vector representations."""
from pathlib import Path
import sys
import shutil
import product
import storage
c=product.c


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    product.runtime(out)
    code=(product.HERE.parent/'collector-owner/check.mjs').read_text()
    extra=(product.HERE.parent/'loader-aref/collector-cases.mjs').read_text()
    extra+='''
function nativeHash(size=3){return node(74,[0,1<<30,0,N,N,51,N,0,0,N,51,N,size*4,0,...Array(size*2).fill(51)]);}
setup();put(EXTERNAL,node(74,Array(20).fill(51)));collect();pass('uninitialized-native-hash');
setup();const h=nativeHash(),k=cons(43*4);put(h-2+14*4,k);put(h-2+15*4,cons(97*4));put(h-2+8*4,4);put(EXTERNAL,h);
collect();const mh=get(EXTERNAL);assert.equal(get(get(mh-2+14*4)+3),43*4);assert.equal(get(get(mh-2+15*4)+3),97*4);
assert.equal(get(mh+2)&(1<<29),1<<29);pass('native-hash-key-movement');
for(const [name,offset,value] of [['weak',8,1<<14],['size',52,16],['count',36,16],['free-list',16,0],['unaligned-flags',8,(1<<30)+1]]){
 setup();const p=nativeHash()-6;put(p+offset,value);put(EXTERNAL,p+6);refused('native-hash-'+name,collect,'collection refused 2');
}
setup();const raw=node(74,Array(20).fill(51));put(raw+2,0);put(EXTERNAL,raw);refused('mixed-uninitialized-hash',collect,'collection refused 2');
'''
    anchor='fs.writeFileSync(process.argv[3],';assert code.count(anchor)==1
    (out/'check.mjs').write_text(code.replace(anchor,extra+'\n'+anchor))
    for name in ('collector-owner.mjs','sha256.mjs','bytes.mjs'):
        shutil.copyfile(c.ROOT/'runtime/wasm32'/name,out/('owner.mjs' if name=='collector-owner.mjs' else name))
    c.command([c.NODE,out/'check.mjs',out/'collector.wasm',out/'result.json'],out/'check.log')
    result=dict(status='PASS',runtime=c.read(out/'array-runtime.json'),checks=c.read(out/'result.json'))
    c.save(out/'summary.json',result);print(result['checks'])


if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve())
