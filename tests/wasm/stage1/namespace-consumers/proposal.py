"""Namespace source boundary proposal, applied only to disposable U1 trees."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def replace(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old))
    return text.replace(old,new)

def sources():
    streams=(ROOT/'level-1/l1-streams.lisp').read_text()
    streams=replace(streams,'#-wasm32-target\n(defun %make-heap-ivector', ''';;; Wasm I/O buffers are traced vectors. No address into a movable vector
;;; escapes to the host; FD-READ roots the vector and copies after resumption.
#+wasm32-target
(defun %make-heap-ivector (subtype size-in-bytes size-in-elts)
  (declare (ignore size-in-bytes))
  (values (%alloc-misc size-in-elts subtype) nil))

#+wasm32-target
(defun dispose-heap-ivector (v)
  (declare (ignore v))
  nil) ; The collector owns this vector's storage.

#-wasm32-target
(defun %make-heap-ivector''')
    streams=replace(streams,'    (unless\n        #+ppc32-target','''    (unless
        #+wasm32-target
        (= (logand subtag target::fulltagmask) target::fulltag-immheader)
        #+ppc32-target''')
    streams=replace(streams,'#-wasm32-target\n(defun optimal-buffer-size','''#+wasm32-target
(defun optimal-buffer-size (fd element-type)
  (declare (ignore fd))
  (let ((bytes (subtag-bytes (element-type-subtype element-type) 1)))
    (max 1 (floor *elements-per-buffer* bytes))))

#-wasm32-target
(defun optimal-buffer-size''')
    streams=replace(streams,'(bufptr (io-buffer-bufptr buf))','(bufptr #+wasm32-target (io-buffer-buffer buf)\n                 #-wasm32-target (io-buffer-bufptr buf))')
    streams=replace(streams,'(let* ((n (with-eagain fd :input\n\t\t    (fd-read fd bufptr size))))','''(let* ((n #+wasm32-target (fd-read fd bufptr size)
                   #-wasm32-target (with-eagain fd :input
                                    (fd-read fd bufptr size))))''')
    streams=replace(streams,'  (cancel-terminate-when-unreachable s)','  #-wasm32-target (cancel-terminate-when-unreachable s)')
    files=(ROOT/'level-1/l1-files.lisp').read_text()
    files=replace(files,'(defun %signal-file-error (err-num &optional pathname args)', '''#+wasm32-target
(defun %signal-file-error (err-num &optional pathname args)
  ;; The virtual namespace has stable errno values and no native stack-frame
  ;; pointer or libc strerror entry. Keep CCL's file condition and payload.
  (error 'simple-file-error :pathname pathname
         :error-type (if (< err-num 0)
                       (%wasm-file-error-string (- err-num))
                       (%rsc-string err-num))
         :format-arguments (list args)))

#-wasm32-target
(defun %signal-file-error (err-num &optional pathname args)''')
    files=replace(files,'(*default-pathname-defaults* #p"")','(*default-pathname-defaults* #+wasm32-target (%cons-pathname nil nil nil)\n                                    #-wasm32-target #p"")',count=2)
    files=replace(files,'  (when create-directory\n    (create-directory path))',
                  '  #+wasm32-target (declare (ignore create-directory))\n  #-wasm32-target\n  (when create-directory\n    (create-directory path))')
    sysio=(ROOT/'level-1/l1-sysio.lisp').read_text()
    sysio=replace(sysio,"\t\t     ((memq direction '(:output :io))\n", """\t\t     ((memq direction '(:output :io))
                      ;; Refuse before generating or renaming a temporary
                      ;; file. :IF-EXISTS NIL and :ERROR were handled above.
                      #+wasm32-target (signal-file-error -30 filename)
""")
    pathnames=(ROOT/'level-1/l1-pathnames.lisp').read_text()
    pathnames=replace(pathnames,'(defun ccl-directory ()', '''#+wasm32-target
(defun ccl-directory ()
  (unless *wasm-namespace-ccl-root*
    (error "The namespace CCL root has not been initialized."))
  (native-to-directory-pathname *wasm-namespace-ccl-root*))

#-wasm32-target
(defun ccl-directory ()''')
    pathnames=replace(pathnames,'(defun setup-initial-translations ()\n  (setf',
                      '(defun setup-initial-translations ()\n  #-wasm32-target\n  (setf')
    unicode=(ROOT/'level-1/l1-unicode.lisp').read_text()
    unicode=replace(unicode,'(defmacro define-character-encoding (name doc &rest args &key &allow-other-keys)\n', '''(defmacro define-character-encoding (name doc &rest args &key &allow-other-keys)
  ;; Namespace streams use the original stream and vector codecs. Native
  ;; address callbacks require a foreign-memory ABI and are absent on Wasm.
  #+wasm32-target
  (setq args (loop for (key value) on args by #'cddr
                   unless (member key '(:memory-encode-function :memory-decode-function
                                        :length-of-memory-encoding-function))
                     append (list key value)))
''')
    primitives=(HERE.parent/'namespace-primitives/w32-files.lisp').read_text()
    primitives+='''
;;; The virtual namespace owns the current directory; no process cwd leaks in.
(defun current-directory-name ()
  (%realpath "."))

(defun %probe-file-x (namestring)
  (let* ((realpath (%realpath namestring))
         (kind (if realpath (%unix-file-kind realpath))))
    (if kind (values realpath kind) (values nil nil))))

(defun fd-input-available-p (fd timeout)
  (declare (ignore timeout))
  ;; All admitted regular byte sources are ready, including EOF.
  (>= (fd-size fd) 0))
'''
    primitives+='\n'+(HERE/'namespace-init.lisp').read_text()
    primitives+='''
(defun %wasm-file-error-string (errno)
  (case errno
    (2 "No such file or directory : ~s")
    (9 "Bad file descriptor : ~s")
    (17 "File exists : ~s")
    (20 "Not a directory : ~s")
    (21 "Is a directory : ~s")
    (22 "Invalid argument : ~s")
    (24 "Too many open files : ~s")
    (30 "Read-only file system : ~s")
    (t "File operation failed : ~s")))
'''
    backend=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
    backend=replace(backend,"          ((member name '(ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set ccl::%wasm-bignum-length-set ccl::%copy-ivector-to-ivector))", """          ((eq name 'ccl::%copy-ivector-to-ivector)
           (b-multiple (make-b-raw-code :text (bootstrap-ivector-byte-copy forms))))
          ((member name '(ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set ccl::%wasm-bignum-length-set))""")
    backend+='\n'+(HERE/'byte-copy.lisp').read_text()
    backend=replace(backend,'(defun bootstrap-make-vector (forms)',
                    '(defun bootstrap-make-simple-vector (forms)')
    backend=replace(backend,'(defun bootstrap-uvector-access (op forms)',
                    '(defun bootstrap-basic-uvector-access (op forms)')
    backend+='\n'+(HERE/'integer-vectors.lisp').read_text()
    old='''                      (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.lt_s ~a (i32.const ~d)) (i32.gt_s ~a (i32.const ~d))))" value value (* 4 low) value (* 4 high)) 5) s)
                      (format s "(i32.store~a ~a ~a) ~a" (case width (1 "8") (2 "16") (t "")) address
                              (if (eq kind :fixnum-vector) value (b-wat "(i32.shr_s ~a (i32.const 2))" value)) value))'''
    new='''                      (format s "(i32.store~a ~a ~a) ~a"
                              (case width (1 "8") (2 "16") (t "")) address
                              (bootstrap-integer-vector-value value subtag low high) value))'''
    backend=replace(backend,old,new)
    backend=replace(backend,"      (ccl::immediate\n       (cond ((and *bootstrap-front-end* (pool-literal-p (first args)))", """      (ccl::immediate
       (cond ((and *b-cpl-conditions* (typep (first args) 'ccl::class-cell))
              (bootstrap-predicate-call
               'ccl::find-class-cell
               (list (make-b-raw-code :text (bootstrap-symbol (ccl::class-cell-name (first args))))
                     (bootstrap-constant t))))
             ((and *bootstrap-front-end* (pool-literal-p (first args)))""")
    old="(and keys (copy-seq (or (fifth keys) #()))))))))"
    backend=replace(backend,old,"(and keys (copy-seq (or (fifth keys) #()))))\n          (ccl::afunc-name (first entry))))))")
    backend=replace(backend,"          ((member name '(ccl::lfun-bits ccl::inner-lfun-bits ccl::lfun-bits-known-function))", """          ((eq name 'ccl::%wasm-function-name)
           (unless (= (length forms) 1) (refuse :function-name-arity))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms
               (lambda (values) (bootstrap-function-info (first values) 3))))))
          ((member name '(ccl::lfun-bits ccl::inner-lfun-bits ccl::lfun-bits-known-function))""")
    backend=replace(backend,'(defun pool-literal-p (x)',""";;; A file compiler can refer to an emitted function before its load-time
;;; definition publishes a public binding. Its linker-owned cell identifies
;;; that exact emitted function, independently of later redefinitions.
(defstruct (wasm32-function-reference (:type vector) :named
                                     (:constructor make-wasm32-function-reference (cell)))
  cell)

(defun pool-literal-p (x)""")
    backend=replace(backend,'(defun pool-literal-p (x)\n  (and ',
                    '(defun pool-literal-p (x)\n  (and (not (wasm32-function-reference-p x)) ')
    backend=replace(backend,"       (cond ((and *b-cpl-conditions* (typep (first args) 'ccl::class-cell))", """       (cond ((wasm32-function-reference-p (first args))
              (let ((cell (wasm32-function-reference-cell (first args))))
                (unless (and (symbolp cell) cell (null (symbol-package cell)))
                  (refuse :function-reference-cell))
                (b-wat "(call $function_value_lisp ~a (local.get $top))"
                       (bootstrap-symbol cell))))
             ((and *b-cpl-conditions* (typep (first args) 'ccl::class-cell))""")
    backend=replace(backend,"             ((and *b-cpl-conditions* (typep (first args) 'ccl::class-cell))", """             ((and *b-cpl-conditions* (packagep (first args)))
              (bootstrap-predicate-call 'ccl::%wasm-package-literal
                (list (make-b-raw-code :text
                        (bootstrap-symbol (intern (package-name (first args)) :keyword))))))
             ((and *b-cpl-conditions* (typep (first args) 'ccl::class-cell))""")
    # Make the metadata accessor's extent check depend on the field requested.
    backend=replace(backend,'(i32.const 3)))" pool offset) 4)',
                    '(i32.const ~d)))" pool offset (max 3 (1+ index))) 4)')
    start=backend.index('(defun bootstrap-function-info')
    end=backend.index('(defun bootstrap-function-bits',start)
    accessor=backend[start:end]
    accessor=replace(accessor,'(i32.add (local.get ~a) (i32.const 16)))',
                     '(i32.add (local.get ~a) (i32.const ~d)))')
    accessor=replace(accessor,'      pool offset\n',
                     '      pool offset (* 4 (1+ (max 3 (1+ index))))\n')
    backend=backend[:start]+accessor+backend[end:]
    definitions=(ROOT/'level-0/l0-def.lisp').read_text()
    definitions=replace(definitions,'(defun lfun-vector-name (fun',
                        (HERE/'function-names.lisp').read_text()+'(defun lfun-vector-name (fun')
    foreign=(ROOT/'lib/foreign-types.lisp').read_text()
    foreign=replace(foreign,'#.(ecase (backend-name *target-backend*)',
                    '#.(ecase (backend-name *target-backend*)\n                        (:wasm32 nil)')
    foreign=replace(foreign,'(defvar *host-ftd* (make-ftd', '''(defvar *host-ftd* (make-ftd
                    ;; The single-Worker target owns this type registry for
                    ;; the lifetime of its image. It does not request weak
                    ;; table semantics from the strong-table provider.
                    #+wasm32-target :ordinal-types
                    #+wasm32-target (make-hash-table :test #'eq)''')
    for function in ('expand-ff-call','record-type-returns-structure-as-first-arg',
                     'generate-callback-bindings','generate-callback-return-value'):
        foreign=replace(foreign,"                    'os::"+function,
                        "                    #+wasm32-target '%wasm-native-ffi-excluded\n                    #-wasm32-target 'os::"+function)
    foreign=replace(foreign,':platform-ordinal-types\n                    (case',
                    ':platform-ordinal-types\n                    #+wasm32-target nil\n                    #-wasm32-target (case')
    foreign=replace(foreign,'(setf (backend-target-foreign-type-data *host-backend*)',
                    '#-wasm32-target\n(setf (backend-target-foreign-type-data *host-backend*)')
    foreign=replace(foreign,'#-(or darwin-target windows-target)\n(defun dlerror',
                    '#-(or darwin-target windows-target wasm32-target)\n(defun dlerror')
    foreign=replace(foreign,',(target-word-size-case\n\t\t\t\t\t(32',
        ''';; During target startup the foreign descriptor is available before
                                ;; the compiler backend objects. Use its ABI.
                                #+wasm32-target
                                ,(ecase (getf (ftd-attributes *target-ftd*) :bits-per-word)
                                   (32 '(integer 0 #.(expt 2 24)))
                                   (64 '(integer 0 #.(expt 2 56))))
                                #-wasm32-target
                                ,(target-word-size-case
                                        (32''')
    primitives+='''
(defun %wasm-native-ffi-excluded (&rest arguments)
  (declare (ignore arguments))
  (error "Native foreign calls are excluded from the Wasm target."))
'''
    low_primitives=(ROOT/'level-0/WASM32/w32-prims.lisp').read_text()+'''

;;; A D1 closure stores its compiled entry and callable metadata in the same
;;; function object as its environment. There is no native closure wrapper
;;; to unwrap; LFUN-BITS and LFUN-VECTOR-NAME address that object's metadata.
(defun closure-function (function)
  function)
'''
    for name in ('layout-prims.lisp','tables.lisp','package-prims.lisp'):
        low_primitives+='\n'+(HERE/name).read_text()
    dcode=(ROOT/'level-1/l1-dcode.lisp').read_text()
    dcode=replace(dcode,"(eql-specializers-hash (make-hash-table :test #'eql  :weak :value))",
        """;; The Wasm bootstrap owns its canonical specializers for the image
       ;; lifetime; it does not request weak-table semantics.
       (eql-specializers-hash (make-hash-table :test #'eql
                                             #-wasm32-target :weak
                                             #-wasm32-target :value))""")
    aprims=(ROOT/'level-1/l1-aprims.lisp').read_text()
    aprims=replace(aprims,'(defvar %setf-function-names%',
        ';;; The Wasm image owns these canonical function names for its lifetime.\n(defvar %setf-function-names%')
    aprims=replace(aprims,"(make-hash-table :weak t :test 'eq)",
        "(make-hash-table #-wasm32-target :weak #-wasm32-target t :test 'eq)",count=2)
    return {'compiler/WASM32/wasm32-backend.lisp':backend,'level-1/l1-streams.lisp':streams,'level-1/l1-files.lisp':files,
            'level-1/WASM32/w32-files.lisp':primitives, 'level-0/l0-def.lisp':definitions,
            'level-1/l1-pathnames.lisp':pathnames, 'level-1/l1-unicode.lisp':unicode,
            'lib/foreign-types.lisp':foreign, 'level-1/l1-sysio.lisp':sysio,
            'level-0/WASM32/w32-prims.lisp':low_primitives,
            'level-1/l1-dcode.lisp':dcode, 'level-1/l1-aprims.lisp':aprims}


def collector():
    text=(ROOT/'runtime/wasm32/collector.c').read_text()
    return replace(text,'else if(tag==50){if(n!=4)return reject(s,BAD_OBJECT);',
                   'else if(tag==50){if(n!=4&&n!=7)return reject(s,BAD_OBJECT);')

def runtime_sources():
    import symbols
    owner=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
    old='     else if([10,26,42,58,106,114,122,250].includes(tag)'
    owner=replace(owner,old,"     else if(tag===98){need(n===8,'image package shape');count=8;bytes=40;}\n"+old)
    return {'runtime/wasm32/collector.c':collector(),
            'runtime/wasm32/collector-owner.mjs':owner,
            'runtime/wasm32/symbols.c':symbols.source()}
