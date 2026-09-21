"""Audit 137 overlays. Original reviewed fixtures are immutable."""
import json,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def host(destination):
 source=ROOT/'tests/wasm/stage1/startup-host-inputs'
 destination.mkdir(parents=True)
 for name in ['run.py','native.lisp','compile.lisp','derive.py','inputs.mjs','owner-check.mjs','controls.py']:
  shutil.copy(source/name,destination/name)
 backend=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
 assert ':target-os :wasm' in backend
 features=re.findall(r":target-specific-features '\(([^)]+)\)",backend);assert len(features)==1
 features=features[0].split();assert features==[':wasm-target',':wasm32-target',':32-bit-target',':little-endian-target']
 (destination/'target-profile.json').write_text(json.dumps(dict(os='wasm',features=features),indent=2)+'\n')
 p=destination/'derive.py';s=p.read_text();s=replace(s,'ROOT=HERE.parents[3]',"ROOT=Path(__import__('os').environ['CCL_REVIEW_ROOT'])");s=s.replace("'composition-witness.json'","'host-native.json'");p.write_text(s)
 p=destination/'inputs.mjs';s=p.read_text();s=s[s.index('const need='):];s=replace(s,'text(precompose(text(input.imageName)))','text(input.imageName)');p.write_text('// Wasm namespace input: no platform filename normalization.\n'+s)
 p=destination/'owner-check.mjs';s=p.read_text().replace('inputBytes,precompose}', 'inputBytes}');s=replace(s,"for(const row of witness){assert.deepEqual([...precompose(String.fromCodePoint(...row.slice(0,2)))].map(c=>c.codePointAt(0)),row.slice(2),'native composition pair');comparisons++;}","for(const row of witness){const input=String.fromCodePoint(...row.image);assert.equal(startupInputs({imageName:input,arguments:[]}).imageName,input,'namespace identity');comparisons++;}")
 s=s.replace("imageName:'café'","imageName:'cafe\\u0301'").replace('precompose(input.imageName)','input.imageName');p.write_text(s)
 p=destination/'native.lisp';s=p.read_text();start=s.index(';; Export the pinned');s=s[:start]+'(quit)\n'
 s=replace(s,'(image-fn (with-open-file',"""(image-fn (let ((*features* (append '(%s)
                          (remove-if (lambda (f) (let ((n(symbol-name f)))
                            (and (>= (length n) 7) (string= n "-TARGET" :start1 (- (length n) 7))))) *features*))))
                  (with-open-file"""%' '.join(features))
 s=replace(s,"return f))))","return f)))))")
 # Keep native decoding, argv construction and publication. Reader conditionals
 # now select the port's branch before compiling this form to native code.
 p.write_text(s)
 p=destination/'run.py';s=p.read_text();a=s.index(' pairs=[];witness=[]');b=s.index('def run(out):',a);s=s[:a]+s[b:]
 s=s.replace(",'HOST_COMPOSITION':str(out/'native-composition.txt')",'').replace(",'composition-witness.json'",'')
 s=s.replace('composition_and_owner_comparisons=','input_and_owner_comparisons=')
 s=replace(s,"out.mkdir(parents=True,exist_ok=False);native(out)","out.mkdir(parents=True,exist_ok=False);native(out)\n shutil.copy(ROOT.parent/'ccl-evidence/2026-09-20-stage1-startup-host-inputs-r1/execution/composition.mjs',out/'darwin-composition.mjs')\n shutil.copy(HERE/'target-profile.json',out/'target-profile.json')\n assert all(a['image']==list(map(ord,r['input']['imageName'])) for a,r in zip(read(out/'host-native.json'),cases()))")
 p.write_text(s)
 p=destination/'controls.py';s=p.read_text();s=replace(s,'const imageName=text(precompose(text(input.imageName)));','const imageName=text(input.imageName);');s=replace(s,"'native host callback'),","'namespace identity'),")
 # The exact old Darwin behavior is also retained as a rejected control; its
 # table remains a fault-only dependency, absent from the positive runtime.
 prefix=(source/'inputs.mjs').read_text().split('const need=')[0]
 needle=" ('reversed-argv','inputs.mjs',source,"
 s=replace(s,needle," ('darwin-branch','inputs.mjs',source,source,"+repr(prefix)+"+source.replace('text(input.imageName)','text(precompose(input.imageName))'),'namespace identity'),\n"+needle)
 s=replace(s,"(d/file).write_text(changed)","(d/file).write_text(changed)\n   if name=='darwin-branch':shutil.copy(out/'darwin-composition.mjs',d/'composition.mjs')")
 p.write_text(s)
 # An unused fault-only table is supplied separately by the orchestrator.
 return features
