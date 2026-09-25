"""NSL-2 publication proposal; only applied to disposable pristine U1 trees."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def replace(text, before, after, count=1):
    assert text.count(before) == count, (before, text.count(before))
    return text.replace(before, after)


def sources():
    backend = (ROOT / 'compiler/WASM32/wasm32-backend.lisp').read_text()
    backend = replace(backend,
        '(unless *module-result-tag* (refuse :native-fasl-publication))',
        '(unless *module-result-tag* (return-from wasm32-pass2 (wasm32-fasl-pass2 afunc)))')
    backend += '\n' + (HERE / 'publication.lisp').read_text()
    dumper = (ROOT / 'lib/nfcomp.lisp').read_text()
    dumper = replace(dumper, '(defun fasl-dump-function (f)\n', '''(defun fasl-dump-function (f)
  (when (eq *fasl-target* :wasm32)
    (return-from fasl-dump-function (funcall 'wasm32-fasl-dump-function f)))
''', 2)
    loader = (ROOT / 'xdump/xfasload.lisp').read_text()
    loader = replace(loader, '(defun xfasload (output-file &rest pathnames)\n', '''(defun xfasload (output-file &rest pathnames)
  (when (eq (backend-name *target-backend*) :wasm32)
    (return-from xfasload (apply 'wasm32-cross-load output-file pathnames)))
''')
    loader = replace(loader, '(defun xload-lfun-name (lf)\n', '''(defun xload-lfun-name (lf)
  (when (eq (backend-name *target-backend*) :wasm32)
    (return-from xload-lfun-name (funcall 'wasm32-xload-function-name lf)))
''')
    arch = (ROOT / 'compiler/WASM32/wasm32-arch.lisp').read_text()
    arch = replace(arch, ":uvector-subtags '((:bignum . 7)",
                   ":uvector-subtags '((:function . 42) (:bignum . 7)")
    arch = replace(arch, "(cl:defun unavailable-array-size (cl:&rest args) (cl:declare (cl:ignore args)) (cl:error \"WASM32 array-size lowering not implemented\"))",
        '''(cl:defun cross-load-array-data-size (subtag count)
  (cl:unless (cl:and (cl:integerp count) (cl:<= 0 count #x3fffffff))
    (cl:error "Invalid Wasm array element count ~s" count))
  (cl:case subtag
    (191 (cl:* count 4))
    (cl:t (cl:error "Wasm cross-loader array kind not admitted: ~s" subtag))))''')
    arch = replace(arch, "#'unavailable-array-size", "#'cross-load-array-data-size")
    arch += '\n(in-package "WASM32")\n(cl:defconstant fasl-version #x80)\n(cl:defconstant fasl-min-version #x80)\n(cl:defconstant fasl-max-version #x80)\n'
    return {'compiler/WASM32/wasm32-backend.lisp': backend,
            'compiler/WASM32/wasm32-arch.lisp': arch,
            'lib/nfcomp.lisp': dumper, 'xdump/xfasload.lisp': loader,
            'xdump/xwasm32-fasload.lisp': (HERE / 'xwasm32-fasload.lisp').read_text()}


def runtime_sources():
    image = (ROOT / 'runtime/wasm32/heap-image.mjs').read_text()
    image = replace(image, "   }else if(tag===90){", """   }else if(tag===98){
    need(n===8,'package shape');count=8;size=40;
   }else if(tag===90){""")
    bundle = (ROOT / 'runtime/wasm32/bundle.mjs').read_text()
    bundle = replace(bundle, 'x=inspect(bytes),ranges=entryRanges(bytes)',
                     'x=inspect(bytes,{ownerRetry:true}),ranges=entryRanges(bytes,{ownerRetry:true})')
    bundle = replace(bundle, "  need(sha256(bytes)===m.d2.outputs.full.binary_sha256,'BINARY');", """  const services=x.imports.filter(i=>i.kind==='function'),seenServices=new Set();
  for(const service of services){
   const key=service.module+'/'+service.name;
   const signature=key==='integer/calculate'?{params:['i32','i32'],results:['i32']}:
     key==='floating/calculate'?{params:['i32','i32','i32'],results:['i32']}:null;
   need(signature!==null,'SERVICE_NAME');
   need(same(service.signature,signature),'SERVICE_SIGNATURE');
   need(!seenServices.has(key),'SERVICE_DUPLICATE');seenServices.add(key);
  }
  need(sha256(bytes)===m.d2.outputs.full.binary_sha256,'BINARY');""")
    return {'runtime/wasm32/heap-image.mjs': image,
            'runtime/wasm32/bundle.mjs': bundle}
