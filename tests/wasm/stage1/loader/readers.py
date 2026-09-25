"""Read shared hooks under all 17 existing CCL target profiles.

Only explicitly named top-level edit sites may differ; the new dumper must be
visible in every profile. Native target branches are read by CCL, not a scanner.
"""
from pathlib import Path
import os,shutil,sys,tarfile,tempfile,subprocess
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal
FILES=['lib/nfcomp.lisp','xdump/faslenv.lisp','xdump/xfasload.lisp']
ALLOWED='''(fasl-dump-dispatch fasl-dump-wasm32-function $fasl-wasm32-function
 backend-xload-info *xload-backend-state* xfasload xload-lfun-name target-xcompile-directory)'''
def run(out,misplaced=False):
 out.mkdir(parents=True,exist_ok=True)
 bodies=proposal.sources()
 with tarfile.open(c.STORE/'macos-u1-inputs/source.tar') as archive:
  before={name:archive.extractfile(name).read() for name in FILES}
 for name in FILES:
  for label in ['before','after']:
   p=out/label/name;p.parent.mkdir(parents=True,exist_ok=True)
   p.write_bytes(before[name] if label=='before' else bodies[name].encode())
 if misplaced:
  p=out/'after/lib/nfcomp.lisp';s=p.read_text();s=s.replace('(defun fasl-dump-wasm32-function','#+x86-target\n(defun fasl-dump-wasm32-function');p.write_text(s)
 script=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
 script=script.replace('(getenv "READER_U1"))))','(getenv "READER_ARCH_SOURCE"))))',1)
 old='''(dolist (stem '("l0-def" "l0-pred" "l0-utils"))
            (let* ((relative (concatenate 'string "level-0/" stem ".lisp"))'''
 script=script.replace(old,'''(dolist (relative '("'''+ '" "'.join(FILES)+'''"))
            (let* ((stem (substitute #\\- #\\/ relative))''')
 script=script.replace('(equal (same-reader-forms before after))','''(edits 'ALLOWED)
                   (site (lambda (form)
                           (and (consp form) (member (car form) '(defun defvar defstruct defconstant))
                                (let ((name (second form))) (if (consp name) (car name) name)))))
                   (changed (lambda (form) (member (funcall site form) edits)))
                   (equal (same-reader-forms (remove-if changed before) (remove-if changed after)))'''.replace('ALLOWED',ALLOWED))
 script=script.replace('(assert equal ()', '''(when (equal relative "lib/nfcomp.lisp")
                (assert (= 1 (count 'fasl-dump-wasm32-function after :key site))))
              (dolist (form after)
                (when (funcall changed form)
                  (assert (not (member 'wasm32-target *features*)))))
              (assert equal ()''')
 script=script.replace('(prin1 before s) (terpri s)', '(prin1 (list :before before :after after) s) (terpri s)')
 script=script.replace('(with-cross-compilation-package ("TARGET" (symbol-name arch))',
  '''(assert (not (<= (symbol-value (find-symbol "FASL-MIN-VERSION" arch))
                     #x80 (symbol-value (find-symbol "FASL-MAX-VERSION" arch)))))
        (with-cross-compilation-package ("TARGET" (symbol-name arch))''')
 (out/'readers.lisp').write_text(script)
 with tempfile.TemporaryDirectory(prefix='u1-',dir=out) as tmp:
  source=Path(tmp)
  for name in ['source.tar','bootstrap.tar.gz']:
   with tarfile.open(c.STORE/'macos-u1-inputs'/name) as archive:archive.extractall(source,filter='data')
  kernel=out/'dx86cl64';shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
  env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_ARCH_SOURCE=str(source)+'/',READER_U1=str(out/'before')+'/',READER_PROPOSAL=str(out/'after')+'/',READER_OUTPUT=str(out)+'/')
  c.command([kernel,'-I',c.IMAGE,'--no-init','--batch','--load',c.ROOT/'tests/wasm/native-census/observer.lisp','--load',out/'readers.lisp'],out/'run.log',env,source,timeout=240)
 rows=c.read(out/'readers.json');assert len(rows['rows'])==51
 c.save(out/'summary.json',dict(status='PASS',profiles=17,comparisons=51,wasm_fasl_version=128,native_profiles_admitting_wasm_fasl=0,allowed_forms=ALLOWED,forms={p.name:c.sha(p) for p in out.glob('*.forms')},source_identity={n:c.sha(out/'after'/n) for n in FILES}))
 return c.read(out/'summary.json')
if __name__=='__main__':print(run(Path(sys.argv[1]).resolve(),'--misplaced' in sys.argv)['status'])
