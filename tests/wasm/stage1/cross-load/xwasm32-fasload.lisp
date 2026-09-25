;;; Host producer for D1 heap storage and the associated Wasm modules.
(in-package :ccl)
(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "XFASLOAD" "ccl:xdump;xfasload"))

(defvar *wasm32-xload-modules* nil)
(defvar *wasm32-xload-functions* nil)

(defun wasm32-xload-unavailable (&rest arguments)
  (declare (ignore arguments))
  (wasm32-compiler::refuse :native-image-operation))

(defun wasm32-initialize-static-space ()
  (assert (= (xload-make-cons *xload-target-nil* *xload-target-nil*
                             *xload-static-space*)
             wasm32::canonical-nil-value)))

(defvar *wasm32-xload-backend*
  (make-backend-xload-info
   :name :wasm32 :compiler-target-name :wasm32
   :macro-apply-code-function 'wasm32-xload-unavailable
   :static-space-init-function 'wasm32-initialize-static-space
   :closure-trampoline-code nil :udf-code nil
   :default-image-name nil :default-startup-file-name nil
   :subdirs '("ccl:level-0;WASM32;") :nil-relative-symbols '(t nil)
   :image-base-address nil :static-space-address nil :purespace-reserve nil))
(add-xload-backend *wasm32-xload-backend*)

(defun wasm32-fasl-text (state)
  (let ((size (%fasl-read-count state)))
    (unless (<= 1 size (ash 1 24))
      (wasm32-compiler::refuse :fasl-module-text-length))
    (let ((text (make-string size)))
      (dotimes (i size text)
        (let ((byte (%fasl-read-byte state)))
          (unless (< byte 128) (wasm32-compiler::refuse :fasl-module-text-byte))
          (setf (schar text i) (code-char byte)))))))

(defun wasm32-xload-function (state)
  (unless (= (%fasl-read-count state) 1)
    (wasm32-compiler::refuse :fasl-function-version))
  (let* ((name (wasm32-fasl-text state))
         (wat (wasm32-fasl-text state))
         (code-id (1+ (length *wasm32-xload-modules*)))
         (function (xload-make-gvector :function 6)))
    (when (assoc name *wasm32-xload-modules* :test #'equal)
      (wasm32-compiler::refuse :fasl-duplicate-module))
    ;; Publish to the local FASL reference table before reading the pool;
    ;; ordinary shared and recursive constants retain their identity.
    (%epushval state function)
    (let* ((pool (%fasl-expr state))
           (name-object (%fasl-expr state))
           (imports (%fasl-expr state)))
      (unless (and (= (logand pool 7) 6)
                   (= (logand (xload-%svref pool -1) 255) wasm32::subtag-simple-vector)
                   (>= (ash (xload-%svref pool -1) -8) 2))
        (wasm32-compiler::refuse :fasl-function-pool))
      (setf (xload-%svref function 0) (ash code-id 2)
            (xload-%svref function 1) *xload-target-nil*
            (xload-%svref function 2) 4
            (xload-%svref function 3) (xload-%svref pool 0)
            (xload-%svref function 4) (xload-%svref pool 1)
            (xload-%svref function 5) pool)
      (push (list name code-id wat function imports) *wasm32-xload-modules*)
      (push (cons function name-object) *wasm32-xload-functions*)
      (setf (faslstate.faslval state) function))))

(defun wasm32-xload-function-name (function)
  (or (cdr (assoc function *wasm32-xload-functions*))
      (wasm32-compiler::refuse :fasl-function-owner)))

(defun wasm32-write-space (space path)
  (with-open-file (stream path :direction :output :if-exists :error
                          :element-type '(unsigned-byte 8))
    (dotimes (i (xload-space-lowptr space))
      (write-byte (u8-ref (xload-space-data space) i) stream))))

(defun wasm32-xload-json (value stream)
  (cond ((eq value t) (write-string "true" stream))
        ((stringp value)
         (write-char #\" stream)
         (map nil (lambda (c)
                    (case c
                      (#\" (write-string "\\\"" stream))
                      (#\\ (write-string "\\\\" stream))
                      (t (if (< (char-code c) 32)
                           (format stream "\\u~4,'0x" (char-code c))
                           (write-char c stream))))) value)
         (write-char #\" stream))
        ((integerp value) (princ value stream))
        ((or (listp value) (vectorp value))
         (write-char #\[ stream)
         (loop for x across (coerce value 'vector) for i from 0 do
           (unless (zerop i) (write-char #\, stream))
           (wasm32-xload-json x stream))
         (write-char #\] stream))
        (t (error "Invalid producer value ~s" value))))

(defun wasm32-write-cross-load (directory roots)
  ;; This intermediate contains simulated coordinates only. The image writer
  ;; replaces all tagged addresses with checked object-boundary relocations.
  (ensure-directories-exist (merge-pathnames "heap.bin" directory))
  (wasm32-write-space *xload-dynamic-space* (merge-pathnames "heap.bin" directory))
  (wasm32-write-space *xload-static-space* (merge-pathnames "static.bin" directory))
  (with-open-file (s (merge-pathnames "cross-load.json" directory)
                     :direction :output :if-exists :error)
    (format s "{~s:1,~s:~d,~s:~d,~s:" "version" "heapBase"
            (xload-space-vaddr *xload-dynamic-space*) "staticBase"
            (xload-space-vaddr *xload-static-space*) "roots")
    (wasm32-xload-json roots s)
    (format s ",~s:[" "modules")
    (loop for (name code-id wat function imports) in (reverse *wasm32-xload-modules*)
          for i from 0 do
      (unless (zerop i) (write-char #\, s))
      (format s "{~s:" "name") (wasm32-xload-json name s)
      (format s ",~s:~d,~s:~d,~s:" "code_id" code-id "function" function "symbols")
      (wasm32-xload-json
       (loop for j below (ash (xload-%svref imports -1) -8)
             for row = (xload-%svref imports j)
             collect (list (xload-get-string (xload-%svref row 1))
                           (xload-%svref row 0))) s)
      (write-char #\} s)
      (with-open-file (w (merge-pathnames (format nil "module-~d.wat" code-id) directory)
                         :direction :output :if-exists :error)
        (write-string wat w)))
    (format s "],~s:[" "symbols")
    (let ((symbols nil))
      (maphash (lambda (address symbol)
                 (push (list (package-name (symbol-package symbol))
                             (symbol-name symbol) address) symbols))
               *xload-symbol-addresses*)
      (loop for row in (sort symbols #'< :key #'third) for i from 0 do
        (unless (zerop i) (write-char #\, s))
        (wasm32-xload-json row s)))
    (write-string "]}" s))
  directory)

(defun wasm32-cross-load (directory &rest pathnames)
  (unless (eq (backend-name *target-backend*) :wasm32)
    (wasm32-compiler::refuse :cross-load-target))
  ;; Bind every setup variable: a Wasm invocation cannot alter another target.
  (progv '(*xload-image-base-address* *xload-purespace-reserve*
           *xload-static-space-address* *xload-readonly-space-address*
           *xload-dynamic-space-address* *xload-managed-static-space-address*
           *xload-static-cons-space-address* *xload-target-nil*
           *xload-target-unbound-marker* *xload-target-misc-header-offset*
           *xload-target-misc-subtag-offset* *xload-target-fixnumshift*
           *xload-target-fulltag-cons* *xload-target-car-offset*
           *xload-target-cdr-offset* *xload-target-cons-size*
           *xload-target-fulltagmask* *xload-target-misc-data-offset*
           *xload-target-fulltag-misc* *xload-target-subtag-char*
           *xload-target-charcode-shift* *xload-target-big-endian*
           *xload-host-big-endian* *xload-target-use-code-vectors*
           *xload-target-fulltag-for-symbols* *xload-target-fulltag-for-functions*
           *xload-target-char-code-limit*) nil
    ;; The registered backend has no native image base. Only this private
    ;; simulation gives the existing target-width accessors arena coordinates.
    (let ((*xload-target-backend* (copy-backend-xload-info *wasm32-xload-backend*)))
      (setf (backend-xload-info-image-base-address *xload-target-backend*) #x100000
            (backend-xload-info-purespace-reserve *xload-target-backend*) 0
            (backend-xload-info-static-space-address *xload-target-backend*) 77824)
      (setup-xload-target-parameters)
      (let* ((*xload-symbols* (make-hash-table :test #'eq))
             (*xload-symbol-addresses* (make-hash-table :test #'eql))
             (*xload-spaces* nil)
             (*xload-dynamic-space* (init-xload-space #x100000 #x40000 area-dynamic))
             (*xload-readonly-space* *xload-dynamic-space*)
             (*xload-static-space* (init-xload-space 77824 4096 area-static))
             (*xload-package-alist* (xload-clone-packages (xload-initial-packages)))
             (*xload-aliased-package-addresses* nil)
             (*xload-cold-load-functions* nil) (*xload-cold-load-documentation* nil)
             (*xload-early-class-cells* nil)
             (*xload-early-istruct-cells* *xload-target-nil*)
             (*xload-special-binding-indices* (make-hash-table :test #'eql))
             (*xload-next-special-binding-index* 1)
             (*xload-loading-file-source-file* nil) (*xload-loading-toplevel-location* nil)
             (*xload-fasl-dispatch-table* (copy-seq *xload-fasl-dispatch-table*))
             (*wasm32-xload-modules* nil) (*wasm32-xload-functions* nil))
        (setf (svref *xload-fasl-dispatch-table* $fasl-function) #'wasm32-xload-function)
        (funcall (backend-xload-info-static-space-init-function *xload-target-backend*))
        ;; As in XFASLOAD, the undefined-function marker is a noncallable
        ;; vector. It contains no native instruction or trampoline.
        (setf (xload-%svref (xload-make-gvector :simple-vector 1) 0)
              *xload-target-unbound-marker*)
        (setq *xload-aliased-package-addresses*
              (xload-assign-aliased-package-addresses *xload-package-alist*))
        (dolist (symbol '(t nil))
          (xload-copy-symbol symbol :preserve-constantness t :space *xload-static-space*))
        (assert (= (xload-lookup-symbol t) wasm32::canonical-t-value))
        (setf (xload-symbol-value (xload-lookup-symbol nil)) *xload-target-nil*)
        (xload-fasload pathnames)
        (xload-finalize-packages)
        (wasm32-write-cross-load directory
          (list (list "cold-load-functions" (xload-save-list (reverse *xload-cold-load-functions*)))
                (list "early-class-cells" (xload-save-list (mapcar #'xload-save-list *xload-early-class-cells*)))
                (list "packages" (xload-save-list (mapcar #'cdr *xload-aliased-package-addresses*)))
                (list "functions" (xload-save-list (mapcar #'car (reverse *wasm32-xload-functions*))))))))))

(provide "XWASM32FASLOAD")
