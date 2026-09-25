;;; Wasm registration counterpart of U1 xx8632-fasload.lisp, made real for
;;; NSL-2 (P2-2): the host cross-loader for wasm32 fasls and the writer of
;;; the two coordinated artifacts of outline section 07 — the bootstrap heap
;;; (bytes of one D1 dynamic space plus the canonical static objects) and the
;;; code set (one module record per emitted function, with its WAT, arity,
;;; symbol imports and code imports). No native instruction word, trampoline,
;;; host address or engine table index enters either artifact.
(in-package "CCL")
(eval-when (:compile-toplevel :execute)
  (require "FASLENV" "ccl:xdump;faslenv"))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "XFASLOAD" "ccl:xdump;xfasload"))

;;; D1 function objects: header (6 . 42); cells code-id, environment,
;;; version 1, metadata, debug, pool. The pool begins with arity and debug
;;; vectors, followed by (#x574153, lfun-bits, key vector, name).
(defconstant wasm32-function-subtag 42)
(defconstant wasm32-function-cells 6)
(defparameter *wasm32-static-space-address* 77824)
(defparameter *wasm32-image-base-address* 2097152)
(defparameter *wasm32-scratch-space-address* #x40000000)
(defparameter *wasm32-first-code-id* 16)

(defstruct wasm32-xload-state code-set (code-names (make-hash-table :test #'eq)) (next-code-id 16) scratch)
(define-symbol-macro *wasm32-code-set* (wasm32-xload-state-code-set *xload-backend-state*))
(define-symbol-macro *wasm32-code-names* (wasm32-xload-state-code-names *xload-backend-state*))
(define-symbol-macro *wasm32-next-code-id* (wasm32-xload-state-next-code-id *xload-backend-state*))
(define-symbol-macro *wasm32-scratch-space* (wasm32-xload-state-scratch *xload-backend-state*))

(defun wasm32-initialize-kernel-symbols ()
  (dolist (symbol '(*package* *keyword-package* %all-packages% %unbound-function%
                    *gc-event-status-bits* %toplevel-catch% %closure-code% %macro-code%
                    %builtin-functions% %toplevel-function% *openmcl-svn-revision* *optional-features*))
    (xload-copy-symbol symbol))
  (make-wasm32-xload-state
   :next-code-id *wasm32-first-code-id*
   :scratch (init-xload-space *wasm32-scratch-space-address* (ash 1 20) area-dynamic)))

(defun wasm32-write-image (directory)
  (wasm32-write-artifacts directory *xload-dynamic-space* *xload-static-space*))

;;; D1 canonical objects: NIL's cons cell at 77824, T at 77832, NIL at 77864.
;;; The nil-relative list (T NIL) places the two symbols behind the cons.
(defun wasm32-initialize-static-space ()
  (xload-make-cons *xload-target-nil* *xload-target-nil* *xload-static-space*))

(defun wasm32-macro-apply-code ()
  *xload-target-nil*)

(defun wasm32-function-header ()
  (make-xload-header wasm32-function-cells wasm32-function-subtag))

(defun wasm32-xload-function-pool (lf)
  (let* ((lfv (logior *xload-target-fulltag-misc*
                      (logandc2 lf *xload-target-fulltagmask*))))
    (unless (= (xload-%svref lfv -1) (wasm32-function-header))
      (error "Not a wasm32 function address: #x~x" lf))
    (let* ((pool (xload-%svref lfv 5)))
      (unless (>= (ash (xload-%svref pool -1) (- target::num-subtag-bits)) 6)
        (error "Function at #x~x has no function-info prefix" lf))
      pool)))

(defun wasm32-xload-lfun-name (lf)
  (xload-%svref (wasm32-xload-function-pool lf) 5))

(defvar *wasm32-xload-backend*
  (make-backend-xload-info
   :name :wasm32 :compiler-target-name :wasm32
   :macro-apply-code-function 'wasm32-macro-apply-code
   :static-space-init-function 'wasm32-initialize-static-space
   ;; No code vectors: %closure-code% is NIL and the undefined-function
   ;; object is a one-element vector holding NIL, never a native word.
   :closure-trampoline-code nil :udf-code 77825
   :default-image-name "ccl:wasm32-boot;" :default-startup-file-name "ccl:level-1.w32fsl"
   :unified-dynamic-space t
   :initialize-symbols-function 'wasm32-initialize-kernel-symbols
   :image-writer-function 'wasm32-write-image
   :compile-file-function 'wasm32-compiler::wasm32-compile-file
   :subdirs '("ccl:level-0;WASM32;") :nil-relative-symbols '(t nil)
   :image-base-address 2097152 :static-space-address 77824 :purespace-reserve 0
   :lfun-name-function 'wasm32-xload-lfun-name))
(when (and (find-xload-backend :wasm32)
           (not (eq (find-xload-backend :wasm32) *wasm32-xload-backend*)))
  (error "Conflicting WASM32 cross-loader"))
(add-xload-backend *wasm32-xload-backend*)

;;; Reading host-side records out of the scratch space.
(defun wasm32-scratch-list (addr)
  (loop until (= addr *xload-target-nil*)
        collect (xload-car addr)
        do (setq addr (xload-cdr addr))))

(defun wasm32-scratch-fixnum (word)
  (unless (zerop (logand word 3)) (error "Not a fixnum in the code record: #x~x" word))
  (ash word (- *xload-target-fixnumshift*)))

(defun wasm32-scratch-string (addr)
  (xload-get-string addr))

;;; A code record is (version name arity captures wat wires codes keywords children):
;;; wires are (wire-string . index) into the module's symbol vector, codes
;;; are the imported module names, children are nested records.
(defun wasm32-register-code (record symbols unit)
  (destructuring-bind (version name arity captures wat wires codes keywords children)
      (wasm32-scratch-list record)
    (unless (= (wasm32-scratch-fixnum version) 2)
      (error "Unsupported wasm32 code record version"))
    (let* ((name (wasm32-scratch-string name))
           (children (mapcar (lambda (child) (wasm32-register-code child symbols unit))
                             (wasm32-scratch-list children)))
           (id (prog1 *wasm32-next-code-id* (incf *wasm32-next-code-id*))))
      (when (wasm32-scratch-list keywords)
        (error "Keyword imports are not admitted by this loader"))
      (when (assoc name (gethash unit *wasm32-code-names*) :test #'string=)
        (error "Duplicate module name ~s" name))
      (push (cons name id) (gethash unit *wasm32-code-names*))
      (push (list :id id :name (format nil "module_~d" id)
                  :arity (destructuring-bind (schema required optional restp keysp allow-other-keys keys)
                             (wasm32-scratch-list arity)
                           (unless (and (= (wasm32-scratch-fixnum schema) 1)
                                        (= (xload-%svref keys -1) 250))
                             (error "Unsupported wasm32 callable metadata"))
                           (list (wasm32-scratch-fixnum required)
                                 (wasm32-scratch-fixnum optional)
                                 (not (= restp *xload-target-nil*))
                                 (not (= keysp *xload-target-nil*))
                                 (not (= allow-other-keys *xload-target-nil*))
                                 nil))
                  :captures (wasm32-scratch-fixnum captures)
                  :wat (wasm32-scratch-string wat)
                  :symbols (mapcar (lambda (pair)
                                     (cons (wasm32-scratch-string (xload-car pair))
                                           (xload-%svref symbols (wasm32-scratch-fixnum (xload-cdr pair)))))
                                   (wasm32-scratch-list wires))
                  :codes (mapcar (lambda (code)
                                   (let* ((code (wasm32-scratch-string code))
                                          (entry (assoc code (gethash unit *wasm32-code-names*) :test #'string=)))
                                     (unless entry (error "Code import ~s precedes its module" code))
                                     entry))
                                 (wasm32-scratch-list codes))
                  :children children)
            *wasm32-code-set*)
      id)))

(defun wasm32-fasl-function (s)
  (let* ((n (%fasl-read-count s))
         (fn (xload-make-gvector wasm32-function-subtag wasm32-function-cells)))
    (unless (>= n 8) (error "Malformed wasm32 function"))
    (%epushval s fn)
    (let* ((record (let ((*xload-dynamic-space* *wasm32-scratch-space*)
                         (*xload-readonly-space* *wasm32-scratch-space*))
                     (%fasl-expr s)))
           (symbols (%fasl-expr s))
           (pool (xload-make-gvector :simple-vector (- n 2))))
      (dotimes (i (- n 2))
        (setf (xload-%svref pool i) (%fasl-expr s)))
      ;; Every record carries its complete nested code graph. Resolve code
      ;; wires in this record's private namespace; published names use code IDs.
      (let ((id (wasm32-register-code record symbols (list nil))))
        (setf (xload-%svref fn 0) (ash id *xload-target-fixnumshift*)
              (xload-%svref fn 1) *xload-target-nil*
              (xload-%svref fn 2) (ash 1 *xload-target-fixnumshift*)
              (xload-%svref fn 3) (xload-%svref pool 0)
              (xload-%svref fn 4) (xload-%svref pool 1)
              (xload-%svref fn 5) pool))
      (setf (faslstate.faslval s) fn))))

(setf (svref *xload-fasl-dispatch-table* $fasl-wasm32-function)
      #'wasm32-fasl-function)

;;; Only the representation and artifact boundaries are target-specific.
;;; The shared XFASLOAD performs its original kernel initialization, file load,
;;; cold-load list construction, documentation, binding indices and packages.
(defparameter *wasm32-xload-parameter-variables*
  '(*xload-image-base-address*
    *xload-purespace-reserve*
    *xload-readonly-space-address*
    *xload-dynamic-space-address*
    *xload-managed-static-space-address*
    *xload-static-space-address*
    *xload-target-nil*
    *xload-target-unbound-marker*
    *xload-target-misc-header-offset*
    *xload-target-misc-subtag-offset*
    *xload-target-fixnumshift*
    *xload-target-fulltag-cons*
    *xload-target-car-offset*
    *xload-target-cdr-offset*
    *xload-target-cons-size*
    *xload-target-fulltagmask*
    *xload-target-misc-data-offset*
    *xload-target-fulltag-misc*
    *xload-target-subtag-char*
    *xload-target-charcode-shift*
    *xload-target-big-endian*
    *xload-host-big-endian*
    *xload-target-use-code-vectors*
    *xload-target-fulltag-for-symbols*
    *xload-target-fulltag-for-functions*
    *xload-target-char-code-limit*
    *xload-static-cons-space-address*))

(defun wasm32-xfasload (output-directory &rest pathnames)
  (with-cross-compilation-target (:wasm32)
    (let* ((*xload-target-backend* *wasm32-xload-backend*)
           (*target-backend* (find-backend :wasm32))
           (*xload-startup-file* (backend-xload-info-default-startup-file-name *xload-target-backend*)))
      (progv *wasm32-xload-parameter-variables*
             (mapcar #'symbol-value *wasm32-xload-parameter-variables*)
        (setup-xload-target-parameters)
        (apply #'xfasload output-directory pathnames)))))

;;; Artifact writer. Bytes are little-endian words exactly as the target
;;; memory holds them; every reference stays a D1 tagged word relative to the
;;; declared space starts, which the JavaScript writer turns into the
;;; heap-image.mjs record. JSON here is deliberately minimal.
(defun wasm32-json-string (string stream)
  (write-char #\" stream)
  (loop for c across string do
    (let ((code (char-code c)))
      (cond ((char= c #\") (write-string "\\\"" stream))
            ((char= c #\\) (write-string "\\\\" stream))
            ((< code 32) (format stream "\\u~4,'0x" code))
            (t (write-char c stream)))))
  (write-char #\" stream))

(defun wasm32-json (value stream)
  (cond ((null value) (write-string "null" stream))
        ((eq value t) (write-string "true" stream))
        ((integerp value) (format stream "~d" value))
        ((stringp value) (wasm32-json-string value stream))
        ((and (consp value) (eq (car value) :object))
         (write-char #\{ stream)
         (loop for (key . item) in (cdr value) for i from 0 do
           (unless (zerop i) (write-char #\, stream))
           (wasm32-json-string key stream) (write-char #\: stream) (wasm32-json item stream))
         (write-char #\} stream))
        ((listp value)
         (write-char #\[ stream)
         (loop for item in value for i from 0 do
           (unless (zerop i) (write-char #\, stream))
           (wasm32-json item stream))
         (write-char #\] stream))
        (t (error "Unsupported JSON value ~s" value))))

(defun wasm32-write-space (space pathname)
  (let* ((data (xload-space-data space))
         (bytes (xload-space-lowptr space)))
    (with-open-file (s pathname :direction :output :if-exists :supersede
                       :element-type '(unsigned-byte 8))
      (dotimes (i (floor bytes 4))
        (let ((word (aref data i)))
          (dotimes (k 4)
            (write-byte (ldb (byte 8 (* 8 k)) word) s)))))
    bytes))

(defun wasm32-module-json (module)
  (list :object
        (cons "id" (getf module :id))
        (cons "name" (getf module :name))
        (cons "arity" (getf module :arity))
        (cons "captures" (getf module :captures))
        (cons "wat" (getf module :wat))
        (cons "symbols" (mapcar (lambda (pair) (list (car pair) (cdr pair))) (getf module :symbols)))
        (cons "codes" (mapcar (lambda (pair) (list (car pair) (cdr pair))) (getf module :codes)))
        (cons "children" (getf module :children))))

(defun wasm32-write-artifacts (directory dynamic static)
  (let* ((directory (pathname directory))
         (heap-bytes (wasm32-write-space dynamic (merge-pathnames "heap.bin" directory)))
         (static-bytes (wasm32-write-space static (merge-pathnames "static.bin" directory)))
         (symbols nil))
    (maphash (lambda (address symbol)
               (push (list :object
                           (cons "package" (and (symbol-package symbol) (package-name (symbol-package symbol))))
                           (cons "name" (symbol-name symbol))
                           (cons "address" address))
                     symbols))
             *xload-symbol-addresses*)
    (setq symbols (sort symbols #'< :key (lambda (row) (cdr (fourth row)))))
    (flet ((value-of (symbol)
             (let ((address (xload-lookup-symbol symbol)))
               (if address (xload-symbol-value address) nil))))
      (with-open-file (s (merge-pathnames "image.json" directory) :direction :output :if-exists :supersede)
        (wasm32-json
         (list :object
               (cons "version" 1)
               (cons "layout" "D1")
               (cons "dynamic" (list :object (cons "start" (xload-space-vaddr dynamic)) (cons "bytes" heap-bytes)))
               (cons "static" (list :object (cons "start" (xload-space-vaddr static)) (cons "bytes" static-bytes)))
               (cons "nil" *xload-target-nil*)
               (cons "t" (+ *xload-target-nil* (arch::target-t-offset (backend-target-arch *target-backend*))))
               (cons "unbound" *xload-target-unbound-marker*)
               (cons "values" (list :object
                                    (cons "cold-load-functions" (value-of '*xload-cold-load-functions*))
                                    (cons "toplevel-function" (value-of '%toplevel-function%))
                                    (cons "all-packages" (value-of '%all-packages%))
                                    (cons "unbound-function" (value-of '%unbound-function%))))
               (cons "symbols" symbols))
         s)
        (terpri s)))
    (with-open-file (s (merge-pathnames "code-set.json" directory) :direction :output :if-exists :supersede)
      (wasm32-json
       (list :object
             (cons "version" 1)
             (cons "first-code-id" *wasm32-first-code-id*)
             (cons "modules" (mapcar #'wasm32-module-json (reverse *wasm32-code-set*))))
       s)
      (terpri s))
    (list :heap-bytes heap-bytes :static-bytes static-bytes
          :symbols (length symbols) :modules (length *wasm32-code-set*))))

(defun wasm32-cross-load (&rest arguments)
  (apply #'wasm32-xfasload arguments))
(provide "XWASM32FASLOAD")
