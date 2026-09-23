"""Target primitives for CCL's class and method dispatch implementation."""
from pathlib import Path
import importlib.util
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cached_backend', HERE.parent/'bootstrap-method-dispatch/backend.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
base_generate, base_sources, base_arch = previous.generate, previous.source_files, previous.arch
base_runtime = previous.runtime_files


def generate():
    text = base_generate()
    needle = '(ccl::%function (b-wat'
    assert text.count(needle) == 1
    text = text.replace(needle, """(ccl::%function
       (when *bootstrap-front-end* (pushnew (first args) *bootstrap-callees*))
       (b-wat""")
    needle = '(type-error 156 :datum :expected-type)'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + '\n                                  (ccl::no-applicable-method-exists 32796 :gf :args)')
    needle = "(case (macro-function 'handler-case)))"
    assert text.count(needle) == 1
    text = text.replace(needle, "(case (macro-function 'handler-case)) (bits (macro-function 'ccl::lfun-bits-known-function)))")
    needle = '(funcall hook expander form environment))))'
    assert text.count(needle) == 1
    text = text.replace(needle, """(if (eq expander bits)
          (progn
            (unless (= (length form) 2) (refuse :function-bits-arity))
            (list 'ccl::lfun-bits (second form)))
          (funcall hook expander form environment)))))""")
    for signature in ('(defun b-call (callee argument-list &optional local-self)',
                      '(defun b-internal-call (callee argument-list local-self)'):
        assert text.count(signature) == 1
        text = text.replace(signature, signature + """
  ;; U1 splits positional arguments into stack and reversed register lists.
  ;; Wasm has one argument vector, but retains U1's source evaluation order.
  (when (and *bootstrap-front-end* (second argument-list))
    (setq argument-list (list (append (first argument-list) (reverse (second argument-list))) nil)))""")
    needle = "    (cond ((and (eq name 'assoc)"
    text = text.replace(needle, """    (cond ((and (eq name 'ccl::%function) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms (lambda (values)
               (b-wat "(call $function_value_lisp ~a (local.get $top))" (first values)))))))
          ((and (eq name 'assoc)""")
    needle = '(ccl::multiple-value-call (b-multiple-call (first args) (second args)))'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + """
      (ccl::multiple-value-list
       (b-multiple-call (ccl::make-acode (ccl::%nx1-operator ccl::%function) 'list) args))""")
    text = text.replace('ccl::local-go ccl::multiple-value-call ccl::multiple-value-bind',
                        'ccl::local-go ccl::multiple-value-call ccl::multiple-value-list ccl::multiple-value-bind')
    needle = "          ((and (eq name 'assoc)"
    assert text.count(needle) == 1
    text = text.replace(needle, """          ((member name '(ccl::lfun-bits ccl::inner-lfun-bits ccl::lfun-bits-known-function))
           (when (member (length forms) '(1 2))
             (b-multiple (make-b-raw-code :text (if (cdr forms) (bootstrap-set-function-bits forms) (bootstrap-function-bits forms))))))
          ((and (eq name 'assoc)""")
    needle = '(function . functionp) (package . packagep)'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + '''
    (ccl::eql-specializer . ccl::eql-specializer-p)
    (class . ccl::classp) (ccl::standard-method . ccl::standard-method-p)
    (ccl::macptr . ccl::macptrp)
    (standard-generic-function . ccl::standard-generic-function-p)
    (ccl::funcallable-standard-object . ccl::funcallable-instance-p)''')
    needle = "          ((member name '(ccl::lfun-bits"
    assert text.count(needle) == 1
    text = text.replace(needle, """          ((member name '(ccl::lfun-bits""")
    needle = '(children nil))\n      (labels ((visit (x)'
    assert text.count(needle) == 1
    text = text.replace(needle, """(children nil))
      (when *bootstrap-front-end*
        (setq values (append values (list #x574153 (bootstrap-lfun-bits (first entry))
          (let ((keys (fourth (ccl::acode-operands (ccl::afunc-acode (first entry))))))
            (and keys (copy-seq (or (fifth keys) #()))))))))
      (labels ((visit (x)""")
    text = text.replace('(defun bootstrap-function-keyvect (forms)', '(defun bootstrap-metadata-keyvect (forms)')
    start = text.index('(defun bootstrap-make-vector (forms)')
    end = text.index('(defun bootstrap-make-list (forms)', start)
    body = text[start:end]
    old = '(i32.and (i32.ne ~a (i32.const 1000)) (i32.and (i32.ne ~a (i32.const 764)) (i32.ne ~a (i32.const 796))))\" tag tag tag'
    new = '(i32.and (i32.ne ~a (i32.const 424)) (i32.and (i32.ne ~a (i32.const 1000)) (i32.and (i32.ne ~a (i32.const 764)) (i32.ne ~a (i32.const 796)))))\" tag tag tag tag'
    assert body.count(old) == 1
    body = body.replace(old, new)
    old = '(i32.eq (local.get ~a) (i32.const 1000)) (then ~a) (else ~a))\"\n                                kind'
    new = '(i32.or (i32.eq (local.get ~a) (i32.const 1000)) (i32.eq (local.get ~a) (i32.const 424))) (then ~a) (else ~a))\"\n                                kind kind'
    assert body.count(old) == 1
    text = text[:start] + body.replace(old, new) + text[end:]
    marker = "          ((and (eq name 'assoc)"
    assert text.count(marker) == 1
    text = text.replace(marker, """          ((and (eq name 'make-array)
                      (or (= (length forms) 1)
                          (and (= (length forms) 3)
                               (eq (bootstrap-immediate (second forms)) :initial-element))))
           (b-multiple (make-b-raw-code :text
             (bootstrap-make-vector
               (list (first forms) (bootstrap-constant wasm32::subtag-simple-vector)
                     (if (cdr forms) (third forms) (bootstrap-constant nil)))))))
          ((and (eq name 'assoc)""")
    marker = "          ((and (eq name 'assoc)"
    assert text.count(marker) == 1
    text = text.replace(marker, """          ((and (eq name 'ccl::%ilogcount) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms (lambda (values)
               (let ((value (car values)))
                 (b-wat "~a (i32.shl (i32.popcnt (i32.shr_s ~a (i32.const 2))) (i32.const 2))"
                   (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 4) value)))))))
          ((and (eq name 'assoc)""")
    text += '\n' + (HERE/'emit.lisp').read_text()
    return text


def source_files(root):
    sources = base_sources(root)
    sources['level-0/WASM32/w32-prims.lisp'] += '\n' + (HERE/'primitives.lisp').read_text()
    path = 'level-1/l1-clos-boot.lisp'
    source = sources.get(path, (root/path).read_text())
    needle = '(defun %inner-method-function (method)\n'
    assert source.count(needle) == 1
    sources[path] = source.replace(needle, needle + '  #+wasm32-target (%method-function method)\n  #-wasm32-target\n')
    sources[path] = sources[path].replace('(defun compute-dcode (gf &optional dt)', '#-wasm32-target\n(defun compute-dcode (gf &optional dt)')
    source = sources[path]
    needle = '  #+x8632-target\n  (defparameter *ivector-vector-classes*'
    assert source.count(needle) == 1
    source = source.replace(needle, '  #+(or x8632-target wasm32-target)\n  (defparameter *ivector-vector-classes*')
    start = source.index('  (defstatic *class-table*')
    end = source.index('  (defun no-class-error ', start)
    body = source[start:end]
    needle = '        #+ppc32-target\n        (do*'
    assert body.count(needle) == 1
    body = body.replace(needle, """        #+wasm32-target
        (setf (%svref v target::tag-fixnum) *fixnum-class*
              (%svref v target::tag-list) #'%wasm-class-of-list
              (%svref v target::tag-imm) *immediate-class*)
""" + needle)
    for kind in ('symbol', 'function'):
        needle = '#+x8632-target target::subtag-' + kind
        assert body.count(needle) == 1
        body = body.replace(needle, '#+(or x8632-target wasm32-target) target::subtag-' + kind)
    needle = '(- x8632::ntagbits)))'
    assert body.count(needle) == 1
    body = body.replace(needle, """(- x8632::ntagbits))
                              #+wasm32-target
                              (ash (the fixnum (- subtype target::min-cl-ivector-subtag))
                                   (- target::ntagbits)))""")
    sources[path] = source[:start] + body + source[end:]

    path = 'level-1/l1-dcode.lisp'
    source = sources.get(path, (root/path).read_text())
    needle = "    (replace-function-code gf (or (cdr (assq dcode dcode-proto-alist))"
    assert source.count(needle) == 1
    source = source.replace(needle, "    #-wasm32-target\n" + needle)
    start = source.index('(defun %make-gf-instance ')
    end = source.index('(defun gf-arg-info-valid-p ', start)
    body = source[start:end]
    assert body.count('    gf))') == 1
    source = source[:start] + body.replace('    gf))',
        '    #+wasm32-target (compute-dcode gf)\n    gf))') + source[end:]

    needle = '(fn #+(or ppc-target arm-target)'
    assert source.count(needle) == 1
    source = source.replace(needle, """(fn #+wasm32-target
                     (%wasm-make-funcallable-instance #'funcallable-trampoline
                       (vector nil wrapper slots dt #'false 0 (ash 1 $lfbits-gfn-bit)))
                   #+(or ppc-target arm-target)""")
    needle = '(combined-method-gf (%svref varg 2))'
    assert source.count(needle) == 2
    source = source.replace(needle, """#+wasm32-target
             (if (> (uvsize varg) 3) (%svref varg 3)
               (combined-method-gf (%svref varg 2)))
             #-wasm32-target (combined-method-gf (%svref varg 2))""")
    start = source.index('(defun bad-key-error ')
    end = source.index('(defun %%check-keywords ', start)
    body = source[start:end]
    body = body.replace('(readable-keys (format nil "~s" keys))',
                        '(readable-keys #+wasm32-target keys #-wasm32-target (format nil "~s" keys))')
    body = body.replace('"Bad keyword ~s to ~s.~%keyargs: ~s~%allowable keys are ~a."',
                        '#+wasm32-target "Bad keyword ~s to ~s.~%keyargs: ~s~%allowable keys are ~s."\n                          #-wasm32-target "Bad keyword ~s to ~s.~%keyargs: ~s~%allowable keys are ~a."')
    source = source[:start] + body + source[end:]
    sources[path] = source
    path = 'level-1/l1-clos.lisp' 
    source = sources.get(path, (root/path).read_text())
    needle = '(fn\n          #+ppc-target'
    assert source.count(needle) == 1
    sources[path] = source.replace(needle, """(fn
          #+wasm32-target
           (%wasm-make-funcallable-instance #'funcallable-trampoline
             (vector nil wrapper slots dt #'false 0
               (logior (ash 1 $lfbits-gfn-bit) (ash 1 $lfbits-aok-bit))))
          #+ppc-target""")
    path = 'level-1/l1-error-signal.lisp'
    source = sources.get(path, (root/path).read_text())
    needle = '(defun cerror (cont-string condition &rest args)\n'
    assert source.count(needle) == 1
    source = source.replace(needle, needle + """  #+wasm32-target
  (restart-case
      (error (if (stringp condition)
               (make-condition 'simple-error :format-control condition :format-arguments args)
               condition))
    (continue () :report (lambda (stream) (apply #'format stream cont-string args)) nil))
  #-wasm32-target
""")
    sources[path] = source
    path = 'level-1/l1-dcode.lisp'
    source = sources[path]
    needle = '(defun %method-combination-error (format-string &rest args)\n'
    assert source.count(needle) == 1
    sources[path] = source.replace(needle, needle + """  #+wasm32-target
  (error (make-condition 'simple-error :format-control format-string :format-arguments args))
  #-wasm32-target
""")
    return sources

previous.parent.generate = generate
previous.parent.source_files = source_files
arch, proposal = previous.arch, previous.proposal


def runtime_files():
    files = base_runtime()
    root = HERE.parents[3]
    text = (root/'runtime/wasm32/collector.c').read_text()
    needle = '   else if(node_subtag(tag)'
    assert text.count(needle) == 1
    text = text.replace(needle, """   else if(tag==90){
    /* Stage 1 populations retain members strongly; the native GC link is zero. */
    if(n!=3||(W)p+16>s->used||LOAD(p+4)!=0||(LOAD(p+8)!=0&&LOAD(p+8)!=4))return reject(s,BAD_OBJECT);
    scan=3;size=16;
   }
   else if(node_subtag(tag)""")
    files['collector.c'] = text
    name = 'collector-owner.mjs'
    text = files.get(name, (root/'runtime/wasm32'/name).read_text())
    needle = '     if([10,26,42,58,106,114,122,250].includes(tag)'
    assert text.count(needle) == 1
    text = text.replace(needle, """     if(tag===90){need(n===3&&p+16<=region.end&&this.#get(p+4)===0&&(this.#get(p+8)===0||this.#get(p+8)===4),'image population shape');count=3;bytes=16;}
     else if([10,26,42,58,106,114,122,250].includes(tag)""")
    files[name] = text
    return files
