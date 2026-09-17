"""Replay inherited regressions and the reviewed 447-module registry collision."""
import subprocess
from pathlib import Path
from support import HERE,compile_cases,require,save
from mutants import source_regression

def run(evidence,positive,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 backend=out/'binding-data-rewrite.lisp';backend.write_text(source_regression((HERE/'wasm32-backend.lisp').read_text()))
 directory=out/'binding-data-rewrite'
 try:compile_cases(evidence,directory,backend)
 except ValueError as error:require(str(error)=='NATIVE_COMPILE '+str(directory/'compile.log'),'REGRESSION_COMPILE_REASON')
 else:raise AssertionError('binding data rewrite escaped')
 log=(directory/'compile.log').read_text()
 require('While compiling local_apply_variable' in log and 'Bad initialization form: (LET' in log,'BINDING_DATA_COUNTEREXAMPLE')
 script=out/'keyword-overlap.mjs';text=(HERE/'execute.mjs').read_text();require(text.count('524294+i*16')==1,'KEYWORD_MUTATION_SITE');script.write_text(text.replace('524294+i*16','262150+i*16'))
 argv=['/usr/local/bin/node',str(script),str(positive),str(out/'keyword-overlap.json')];save(out/'command.json',argv)
 with (out/'keyword-overlap.log').open('w') as stream:child=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
 log=(out/'keyword-overlap.log').read_text();require(child.returncode!=0 and 'AssertionError' in log and 'local_self_identity-' in log and 'native/logical result' in log,'KEYWORD_OVERLAP_COUNTEREXAMPLE')
 results=[{'name':'binding-data-rewrite','stage':'native compilation','status':'REJECTED','oracle':'local_apply_variable must compile; old rewrite corrupts LET binding data'}, {'name':'keyword-overlap','stage':'fixture token decoding','status':'REJECTED','oracle':'local_self_identity must preserve returned function identity'}]
 backend=out/'special-package-alias.lisp'
 text=(HERE/'wasm32-backend.lisp').read_text();guard='  (unless (eq (symbol-package symbol) (find-package "WASM32-COMPILER")) (refuse :b-special-package))\n'
 require(text.count(guard)==1,'PACKAGE_MUTATION_SITE');backend.write_text(text.replace(guard,''))
 directory=out/'special-package-alias'
 try:compile_cases(evidence,directory,backend)
 except ValueError as error:require(str(error)=='NATIVE_COMPILE '+str(directory/'compile.log'),'PACKAGE_REGRESSION_REASON')
 else:raise AssertionError('special package identity escaped')
 require('Unrefused source foreign-special-package' in (directory/'compile.log').read_text(),'PACKAGE_ALIAS_COUNTEREXAMPLE')
 results.append({'name':'special-package-alias','stage':'source admission','status':'REJECTED','oracle':'foreign package special cannot alias a private symbol import'})
 script=out/'obsolete-registry.mjs';text=(HERE/'execute.mjs').read_text();site=' function installObjects(){'
 require(text.count(site)==1,'OBSOLETE_REGISTRY_REGRESSION_SITE')
 # Run the old writes after the real registry initializer, exactly as the old
 # harness did, so the first positive invocation sees the authentic overlap.
 site='installObjects();for(const [name,target]of Object.entries(c.bindings))'
 require(text.count(site)==1,'CORPUS_INSTALL_SITE')
 old='store(512,mods.length+1);store(516,1);for(let i=1;i<=mods.length;i++){store(520+8*i,17);store(524+8*i,23);}'
 script.write_text(text.replace(site,'installObjects();'+old+'for(const [name,target]of Object.entries(c.bindings))'))
 argv=['/usr/local/bin/node',str(script),str(positive),str(out/'obsolete-registry.json')];save(out/'obsolete-registry-command.json',argv)
 with (out/'obsolete-registry.log').open('w') as stream:child=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
 log=(out/'obsolete-registry.log').read_text();require(child.returncode!=0 and 'AssertionError' in log,'OBSOLETE_REGISTRY_COUNTEREXAMPLE')
 results.append({'name':'obsolete-registry','stage':'fixture registry initialization','status':'REJECTED','oracle':'corpus exceeds 447 modules; unread legacy table corrupts code registry'})
 save(out/'controls.json',results);return results
