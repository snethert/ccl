"""Focused emitted-code controls for the new paths, without replaying the corpus."""
import json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def check(out):
 read=lambda n:json.loads((out/n).read_text())
 syms={r['name']:r['id'] for r in read('compiled/symbols.json')}
 modules=read('compiled/modules.json')
 sin=next(r['name'] for r in modules if r['function']==syms['%DOUBLE-FLOAT-SIN!'])
 left=(out/'compiled/core_natural_left.wat').read_text()
 at=left.index('(i32.ge_u',left.index('(i32.const 519)'))
 tail=left[at:];assert '(else (i32.shl (local.get' in tail
 changed=left[:at]+tail.replace('(else (i32.shl (local.get','(else (i32.shr_u (local.get',1)
 sine=(out/'compiled'/f'{sin}.wat').read_text()
 controls=[('shift-direction','core_natural_left','CORE-NATURAL-LEFT',changed,'CORE-NATURAL-LEFT'),
  ('coercion-width','core_coerce_double','CORE-COERCE-DOUBLE',(out/'compiled/core_coerce_double.wat').read_text().replace('(call $float_slow (i32.const 11)','(call $float_slow (i32.const 10)'), 'CORE-COERCE-DOUBLE'),
  ('math-operation',sin,'CORE-LIBM-SIN64',sine.replace('(call $float_slow (i32.const 14)','(call $float_slow (i32.const 16)'),'exceeds adopted'),
  ('float-result-offset',sin,'CORE-LIBM-SIN64',sine.replace('(i64.store offset=8','(i64.store offset=4'),'AssertionError')]
 reports=[];root=out/'faults';root.mkdir()
 for label,module,focus,text,reason in controls:
  original=(out/'compiled'/f'{module}.wat').read_text();assert text!=original,label
  work=root/label;work.mkdir();(work/'compiled').mkdir()
  # Link immutable inputs, replacing only the deliberately changed artifact.
  for source in out.iterdir():
   if source.is_file():(work/source.name).symlink_to(source)
  (work/'runtime').symlink_to(out/'runtime',target_is_directory=True)
  for source in (out/'compiled').iterdir():
   if source.is_file() and source.name not in (module+'.wat',module+'.wasm'):(work/'compiled'/source.name).symlink_to(source)
  wat=work/'compiled'/f'{module}.wat';wat.write_text(text)
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-all',wat,'-o',wat.with_suffix('.wasm')],check=True)
  # Node resolves symlinked scripts by their real location. Copy these two so
  # the control's own directory supplies the deliberately changed module.
  for name in ('check.mjs','install.mjs'):
   (work/name).unlink();shutil.copy(out/name,work/name)
  log=work/'run.log'
  with log.open('w') as stream:
   result=subprocess.run(['/usr/local/bin/node',work/'check.mjs',work,work/'result.json'],env=dict(os.environ,CCL_LIBRARY_CASE=focus),stdout=stream,stderr=stream,timeout=60)
  assert result.returncode!=0 and reason in log.read_text(),label
  reports.append(dict(name=label,module=module,case=focus,status='REJECTED'))
  # Retain the mutant and original failure, not links to entire prerequisites.
  for path in list(work.rglob('*')):
   if path.is_symlink():path.unlink()
 (out/'math-controls.json').write_text(json.dumps(dict(status='PASS',controls=reports,scope='Validated emitted-code faults; not compiler-source mutants or an exhaustive predicate sweep.'),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':check(Path(sys.argv[1]).resolve())
