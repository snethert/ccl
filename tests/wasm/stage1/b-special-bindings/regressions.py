"""Replay the two real development defects against the positive corpus."""
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
 save(out/'controls.json',results);return results
