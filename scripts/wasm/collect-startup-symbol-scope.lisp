;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Startup symbol scope artifact constants.

(in-package "CCL")

(defconstant +startup-symbol-scope-schema-version+
  "startup_symbol_scope_v1")

(defconstant +startup-symbol-scope-generator-version+
  "startup_symbol_scope_generator_v1")

(defconstant +startup-symbol-scope-field-generated-at-utc+
  "generated_at_utc")

;; Canonical JSON emits object keys in lexicographic order.
(defconstant +startup-symbol-scope-canonical-object-key-order+
  :lexicographic)

;; Arrays with semantic constraints are emitted sorted by the producer.
(defconstant +startup-symbol-scope-canonical-array-ordering+
  :sorted)

;; startup_symbol_scope_v1 identity hash excludes generated_at_utc only.
(defconstant +startup-symbol-scope-identity-hash-excluded-input-fields+
  (list +startup-symbol-scope-field-generated-at-utc+))

(defconstant +startup-symbol-scope-field-schema-version+
  "schema_version")

(defconstant +startup-symbol-scope-field-generator-version+
  "generator_version")

(defconstant +startup-symbol-scope-required-top-level-fields+
  (list +startup-symbol-scope-field-schema-version+
        +startup-symbol-scope-field-generator-version+
        "inputs"
        "symbols"
        "counts"))

(defconstant +startup-symbol-scope-read-failure-reader-parse-error+
  "reader-parse-error")

(defconstant +startup-symbol-scope-read-failure-unsupported-reader-dispatch+
  "unsupported-reader-dispatch")

(defconstant +startup-symbol-scope-read-failure-read-eval-disabled+
  "read-eval-disabled")

(defconstant +startup-symbol-scope-read-failure-missing-package-during-read+
  "missing-package-during-read")

(defstruct (read-failure-state
             (:constructor make-read-failure-state))
  (counts (make-hash-table :test 'equal))
  (entries nil))

(defmacro with-read-safety (&body body)
  "Run BODY with reader-eval disabled for scanner safety."
  `(let ((*read-eval* nil))
     ,@body))

(defun classify-reader-failure-reason (condition)
  "Classify read failures into stable reason codes for diagnostics."
  (let ((message (string-downcase (princ-to-string condition))))
    (cond
      ((search "missing-package-during-read" message)
       +startup-symbol-scope-read-failure-missing-package-during-read+)
      ((search "read-eval" message)
       +startup-symbol-scope-read-failure-read-eval-disabled+)
      ((or (search "dispatch" message)
           (search "reader macro" message))
       +startup-symbol-scope-read-failure-unsupported-reader-dispatch+)
      (t
       +startup-symbol-scope-read-failure-reader-parse-error+))))

(defun record-reader-failure (state pathname condition)
  "Record a recoverable parse failure and continue with remaining files."
  (let* ((reason (classify-reader-failure-reason condition))
         (counts (read-failure-state-counts state)))
    (incf (gethash reason counts 0))
    (push (list (cons :file (namestring pathname))
                (cons :reason reason)
                (cons :message (princ-to-string condition)))
          (read-failure-state-entries state))
    state))

(defun deterministic-pathname< (left right)
  (string< (namestring left) (namestring right)))

(defun sort-pathnames-deterministically (pathnames)
  "Sort PATHNAMES in deterministic file traversal order."
  (sort (copy-list pathnames) #'deterministic-pathname<))

(defun maybe-package-designator-from-in-package-form (form)
  "Extract package designator text from (IN-PACKAGE ...) forms."
  (when (and (consp form)
             (symbolp (car form))
             (string-equal (symbol-name (car form)) "IN-PACKAGE")
             (null (cddr form)))
    (let ((designator (cadr form)))
      (cond
        ((packagep designator)
         (package-name designator))
        ((symbolp designator)
         (symbol-name designator))
        ((stringp designator)
         designator)
        (t
         nil)))))

(defun apply-in-package-transition-if-present (form pathname failure-state)
  "Apply reader package transition for an IN-PACKAGE top-level FORM."
  (let ((designator (maybe-package-designator-from-in-package-form form)))
    (when designator
      (let ((package (or (find-package designator)
                         (find-package (string-upcase designator)))))
        (if package
          (setf *package* package)
          (record-reader-failure
           failure-state
           pathname
           (make-condition 'simple-error
                           :format-control "missing-package-during-read: ~a"
                           :format-arguments (list designator))))))))

(defun feature-token->reader-symbols (feature-token)
  "Map feature token text to reader-visible feature symbols."
  (let ((upper (string-upcase feature-token))
        (symbols nil))
    (flet ((add-interned (package-name)
             (let ((package (find-package package-name)))
               (when package
                 (multiple-value-bind (symbol interned-p)
                     (intern upper package)
                   (declare (ignore interned-p))
                   (pushnew symbol symbols :test #'eq))))))
      (add-interned "KEYWORD")
      (add-interned "CCL")
      (add-interned "COMMON-LISP-USER"))
    (nreverse symbols)))

(defun feature-set->reader-features (feature-set)
  "Build deterministic *FEATURES* symbols list from FEATURE-SET strings."
  (let ((features nil))
    (dolist (feature-token feature-set (nreverse features))
      (dolist (feature-symbol (feature-token->reader-symbols feature-token))
        (pushnew feature-symbol features :test #'eq)))))

(defun read-file-forms-with-recovery (pathname failure-state &key reader-features)
  "Read top-level forms from PATHNAME with recoverable parser failures."
  (let ((*package* (or (find-package "CCL") *package*))
        (*features* (if reader-features
                      (copy-list reader-features)
                      *features*))
        (forms nil))
    (with-read-safety
      (handler-case
          (with-open-file (stream pathname :direction :input)
            (loop
              (handler-case
                  (let ((form (read stream nil :eof)))
                    (when (eq form :eof)
                      (return))
                    (push form forms)
                    (apply-in-package-transition-if-present form pathname failure-state))
                (error (condition)
                  (record-reader-failure failure-state pathname condition)
                  ;; After a reader-parse-error, this file is skipped.
                  (return)))))
        (error (condition)
          (record-reader-failure failure-state pathname condition))))
    (nreverse forms)))

(defun scan-files-in-deterministic-order (pathnames &key feature-set)
  "Read PATHNAMES in deterministic order and keep parse failures recoverable."
  (let ((failure-state (make-read-failure-state))
        (reader-features (and feature-set
                              (feature-set->reader-features feature-set)))
        (forms-by-file nil))
    (dolist (pathname (sort-pathnames-deterministically pathnames))
      (push (cons pathname
                  (read-file-forms-with-recovery pathname
                                                 failure-state
                                                 :reader-features reader-features))
            forms-by-file))
    (values (nreverse forms-by-file) failure-state)))

(defconstant +startup-symbol-role-defined-function+
  "defined-function")

(defconstant +startup-symbol-role-defined-special+
  "defined-special")

(defconstant +startup-symbol-role-call-head+
  "call-head")

(defconstant +startup-symbol-role-function-designator+
  "function-designator")

(defconstant +startup-symbol-role-symbol-atom+
  "symbol-atom")

(defconstant +startup-symbol-role-contract-required+
  "contract-required")

(defconstant +startup-symbol-function-definition-heads+
  (list "DEFUN"
        "DEFMACRO"
        "DEFINE-COMPILER-MACRO"
        "DEFSETF"
        "DEFINE-SETF-EXPANDER"))

(defconstant +startup-symbol-special-definition-heads+
  (list "DEFVAR"
        "DEFPARAMETER"
        "DEF-STANDARD-INITIAL-BINDING"
        "DEFGLOBAL"))

(defstruct (symbol-role-state
             (:constructor make-symbol-role-state))
  (roles-by-key (make-hash-table :test 'equal))
  (excluded-uninterned-total 0))

(defun startup-symbol-head-matches-p (head names)
  (and (symbolp head)
       (member (string-upcase (symbol-name head))
               names
               :test #'string=)))

(defun canonical-symbol-key-from-symbol (symbol)
  "Convert SYMBOL into PACKAGE::SYMBOL canonical key text."
  (let ((package (symbol-package symbol)))
    (when package
      (format nil "~a::~a"
              (string-upcase (package-name package))
              (string-upcase (symbol-name symbol))))))

(defun canonicalize-startup-symbol-key (key)
  "Normalize KEY text into canonical PACKAGE::SYMBOL format."
  (when (stringp key)
    (let ((trimmed (string-trim '(#\Space #\Tab #\Newline #\Return) key)))
      (when (> (length trimmed) 0)
        (with-read-safety
          (handler-case
              (multiple-value-bind (form position)
                  (read-from-string trimmed nil :eof)
                (when (and (symbolp form)
                           (= position (length trimmed)))
                  (canonical-symbol-key-from-symbol form)))
            (error ()
              nil)))))))

(defun startup-symbol-role-state-add (state key role)
  "Add ROLE to KEY inside STATE."
  (when (and key role)
    (let ((role-set (or (gethash key (symbol-role-state-roles-by-key state))
                        (setf (gethash key (symbol-role-state-roles-by-key state))
                              (make-hash-table :test 'equal)))))
      (setf (gethash role role-set) t)))
  state)

(defun startup-symbol-role-state-add-symbol (state symbol role)
  "Add ROLE for SYMBOL into STATE, tracking uninterned exclusions."
  (cond
    ((not (symbolp symbol))
     state)
    ((null (symbol-package symbol))
     (incf (symbol-role-state-excluded-uninterned-total state))
     state)
    (t
     (startup-symbol-role-state-add
      state
      (canonical-symbol-key-from-symbol symbol)
      role))))

(defun startup-symbol-definition-target-symbol (target)
  "Extract definition/designator symbol from TARGET syntax."
  (cond
    ((symbolp target)
     target)
    ((and (consp target)
          (symbolp (car target))
          (string-equal (symbol-name (car target)) "SETF")
          (symbolp (cadr target)))
     (cadr target))
    (t
     nil)))

(defun startup-symbol-function-form-p (head)
  (and (symbolp head)
       (string-equal (symbol-name head) "FUNCTION")))

(defun startup-symbol-proper-list-p (value)
  "Return T only when VALUE is a proper (NIL-terminated) list."
  (loop
    for tail = value then (cdr tail) do
      (cond
        ((null tail) (return t))
        ((consp tail) nil)
        (t (return nil)))))

(defun extract-symbol-roles-from-form (form state)
  "Walk FORM and record symbol roles into STATE."
  (labels ((walk (node context)
             (cond
               ((symbolp node)
                (case context
                  (:call-head
                   (startup-symbol-role-state-add-symbol
                    state node +startup-symbol-role-call-head+))
                  (:function-designator
                   (startup-symbol-role-state-add-symbol
                    state node +startup-symbol-role-function-designator+))
                  (:definition-target
                   nil)
                  (t
                   (startup-symbol-role-state-add-symbol
                    state node +startup-symbol-role-symbol-atom+))))
               ((consp node)
                (if (startup-symbol-proper-list-p node)
                  (let* ((head (car node))
                         (function-definition-p
                           (startup-symbol-head-matches-p
                            head
                            +startup-symbol-function-definition-heads+))
                         (special-definition-p
                           (startup-symbol-head-matches-p
                            head
                            +startup-symbol-special-definition-heads+))
                         (function-designator-form-p
                           (startup-symbol-function-form-p head))
                         (definition-target
                           (startup-symbol-definition-target-symbol (cadr node))))
                    (when function-definition-p
                      (startup-symbol-role-state-add-symbol
                       state definition-target +startup-symbol-role-defined-function+))
                    (when special-definition-p
                      (startup-symbol-role-state-add-symbol
                       state definition-target +startup-symbol-role-defined-special+))
                    (when function-designator-form-p
                      (startup-symbol-role-state-add-symbol
                       state definition-target +startup-symbol-role-function-designator+))
                    (walk head :call-head)
                    (loop for arg in (cdr node)
                          for index from 1 do
                            (cond
                              ((and function-designator-form-p (= index 1))
                               (walk arg :function-designator))
                              ((and (or function-definition-p special-definition-p)
                                    (= index 1))
                               (walk arg :definition-target))
                              (t
                               (walk arg nil)))))
                  ;; Dotted pairs appear in quoted constants; traverse safely.
                  (progn
                    (walk (car node) nil)
                    (walk (cdr node) nil))))
               ((vectorp node)
                (loop for element across node do
                  (walk element nil)))
               (t
                nil))))
    (walk form nil))
  state)

(defun contract-required-entry->key (entry)
  "Resolve ENTRY into canonical PACKAGE::SYMBOL key text when possible."
  (cond
    ((symbolp entry)
     (canonical-symbol-key-from-symbol entry))
    ((stringp entry)
     (canonicalize-startup-symbol-key entry))
    ((and (consp entry) (assoc :key entry))
     (contract-required-entry->key (cdr (assoc :key entry))))
    ((and (consp entry) (assoc "key" entry :test #'string=))
     (contract-required-entry->key (cdr (assoc "key" entry :test #'string=)))
    )
    (t
     nil)))

(defun add-contract-required-roles (state required-entries)
  "Add contract-required roles from REQUIRED-ENTRIES into STATE."
  (dolist (entry required-entries state)
    (let ((key (contract-required-entry->key entry)))
      (when key
        (startup-symbol-role-state-add
         state key +startup-symbol-role-contract-required+)))))

(defun symbol-role-state->alist (state)
  "Return deterministic (KEY . SORTED-ROLES) alist for STATE."
  (let ((out nil))
    (maphash
     (lambda (key role-set)
       (let ((roles nil))
         (maphash
          (lambda (role present)
            (declare (ignore present))
            (push role roles))
          role-set)
         (push (cons key (sort roles #'string<)) out)))
     (symbol-role-state-roles-by-key state))
    (sort out #'string< :key #'car)))

(defun extract-startup-symbol-roles (forms &key contract-required-entries)
  "Extract deterministic symbol role sets from FORMS and contract entries."
  (let ((state (make-symbol-role-state)))
    (dolist (form forms)
      (extract-symbol-roles-from-form form state))
    (when contract-required-entries
      (add-contract-required-roles state contract-required-entries))
    (symbol-role-state->alist state)))

(defun parse-argv (argv)
  "Parse CLI arguments for the startup symbol scope scanner."
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (labels ((pop-required-value (flag)
                   (let ((value (pop args)))
                     (unless value
                       (error "Missing value for ~a" flag))
                     value)))
          (cond
            ((string= arg "--")
             (setf seen-delimiter t))
            ((or (string= arg "-h") (string= arg "--help"))
             (push (cons :help t) out))
            ((string= arg "--repo-root")
             (push (cons :repo-root (pop-required-value "--repo-root")) out))
            ((string= arg "--out")
             (push (cons :out (pop-required-value "--out")) out))
            ((string= arg "--feature-profile")
             (push (cons :feature-profile (pop-required-value "--feature-profile")) out))
            ((string= arg "--contract-json")
             (push (cons :contract-json (pop-required-value "--contract-json")) out))
            ((string= arg "--run-fixture-tests")
             (push (cons :run-fixture-tests t) out))
            ((string= arg "--fixtures-dir")
             (push (cons :fixtures-dir (pop-required-value "--fixtures-dir")) out))
            (seen-delimiter
             (error "Unknown argument: ~s" arg))
            (t
             nil)))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/collect-startup-symbol-scope.lisp -- --repo-root PATH --out PATH --feature-profile PROFILE --contract-json PATH~%")
  (format t "Required scanner flags: --repo-root, --out, --feature-profile. --contract-json defaults to doc/wasm/bootstrap-l0-contract.v1.json under --repo-root when present.~%")
  (format t "Fixture test mode: --run-fixture-tests --fixtures-dir PATH~%"))

(defconstant +startup-symbol-scope-build-schema-version+
  "startup_symbol_scope_build_v1")

(defconstant +startup-symbol-scope-supported-feature-profiles+
  '(("wasm32-target-v1" . ("wasm32-target"))))

(defun json-escape-string (s)
  (with-output-to-string (out)
    (loop for ch across s do
      (case ch
        (#\" (write-string "\\\"" out))
        (#\\ (write-string "\\\\" out))
        (#\Newline (write-string "\\n" out))
        (#\Return (write-string "\\r" out))
        (#\Tab (write-string "\\t" out))
        (t (write-char ch out))))))

(defun json-write-string (out s)
  (write-char #\" out)
  (write-string (json-escape-string s) out)
  (write-char #\" out))

(defun json-write-object (out pairs)
  (write-char #\{ out)
  (loop for pair in pairs
        for index from 0 do
          (when (> index 0)
            (write-char #\, out))
          (json-write-string out (car pair))
          (write-char #\: out)
          (json-write-value out (cdr pair)))
  (write-char #\} out))

(defun json-write-array (out items)
  (write-char #\[ out)
  (loop for item in items
        for index from 0 do
          (when (> index 0)
            (write-char #\, out))
          (json-write-value out item))
  (write-char #\] out))

(defun json-write-value (out value)
  (cond
    ((stringp value) (json-write-string out value))
    ((integerp value) (princ value out))
    ((floatp value) (princ value out))
    ((eq value :true) (write-string "true" out))
    ((eq value :false) (write-string "false" out))
    ((null value) (write-string "null" out))
    ((and (consp value) (eq (car value) :object))
     (json-write-object out (cdr value)))
    ((and (consp value) (eq (car value) :array))
     (json-write-array out (cdr value)))
    (t
     (json-write-string out (princ-to-string value)))))

(defun make-json-object (&rest pairs)
  (cons :object pairs))

(defun make-json-array (&rest items)
  (cons :array items))

(defun maybe-namestring (pathname)
  (and pathname (namestring pathname)))

(defun repo-root-pathname (repo-root)
  (let ((probe (probe-file repo-root)))
    (if probe
      (truename probe)
      (error "Repository root does not exist: ~a" repo-root))))

(defun collect-scan-paths (repo-root-path)
  (let* ((l0-pattern (merge-pathnames "level-0/*.lisp" repo-root-path))
         (l1-pattern (merge-pathnames "level-1/**/*.lisp" repo-root-path))
         (l0-files (sort-pathnames-deterministically (directory l0-pattern)))
         (l1-files (sort-pathnames-deterministically (directory l1-pattern)))
         (all-files (append l0-files l1-files)))
    (values all-files l0-files l1-files)))

(defun flatten-forms (forms-by-file)
  (let ((out nil))
    (dolist (entry forms-by-file (nreverse out))
      (dolist (form (cdr entry))
        (push form out)))))

(defun uppercase-subseq (value start end)
  (string-upcase (subseq value start end)))

(defun symbol-key->package-name (key)
  (let ((separator (search "::" key)))
    (when separator
      (uppercase-subseq key 0 separator))))

(defun symbol-key->symbol-name (key)
  (let ((separator (search "::" key)))
    (when separator
      (uppercase-subseq key (+ separator 2) (length key)))))

(defun bindable-roles-p (roles)
  (or (member +startup-symbol-role-defined-function+ roles :test #'string=)
      (member +startup-symbol-role-defined-special+ roles :test #'string=)
      (member +startup-symbol-role-contract-required+ roles :test #'string=)))

(defun hash-table-keys-sorted (table)
  (let ((keys nil))
    (maphash (lambda (key value)
               (declare (ignore value))
               (push key keys))
             table)
    (sort keys #'string<)))

(defun alist->json-object (alist)
  (apply #'make-json-object
         (mapcar (lambda (pair) (cons (car pair) (cdr pair)))
                 (sort (copy-list alist) #'string< :key #'car))))

(defun feature-set-for-profile (feature-profile)
  (or (cdr (assoc feature-profile
                  +startup-symbol-scope-supported-feature-profiles+
                  :test #'string=))
      (error "unknown-feature-profile: ~a" feature-profile)))

(defun universal-time->rfc3339-utc (universal-time)
  (multiple-value-bind (second minute hour day month year)
      (decode-universal-time universal-time 0)
    (format nil "~4,'0d-~2,'0d-~2,'0dT~2,'0d:~2,'0d:~2,'0dZ"
            year month day hour minute second)))

(defun maybe-string-sha256 (pathname)
  (let ((file (probe-file pathname)))
    (if file
      (let* ((command (format nil "shasum -a 256 ~a | awk '{print $1}'"
                              (with-output-to-string (out)
                                (write-char #\' out)
                                (write-string (namestring file) out)
                                (write-char #\' out))))
             (process (run-program "/bin/sh"
                                   (list "-lc" command)
                                   :output :stream
                                   :error :stream))
             (stream (external-process-output-stream process))
             (digest (and stream (read-line stream nil ""))))
        (if (and digest (> (length digest) 0))
          digest
          ""))
      "")))

(defun read-failure-reason-count (failure-state reason)
  (gethash reason (read-failure-state-counts failure-state) 0))

(defun read-failure-counts-alist (failure-state)
  (let ((counts (read-failure-state-counts failure-state))
        (out nil))
    (dolist (reason (hash-table-keys-sorted counts) (nreverse out))
      (push (cons reason (gethash reason counts 0)) out))))

(defun summarize-role-counts (symbols)
  (let ((counts (make-hash-table :test 'equal)))
    (dolist (symbol symbols)
      (dolist (role (cdr (assoc "roles" symbol :test #'string=)))
        (incf (gethash role counts 0))))
    counts))

(defun summarize-package-counts (symbols)
  (let ((counts (make-hash-table :test 'equal)))
    (dolist (symbol symbols)
      (let ((package-name (cdr (assoc "package_name" symbol :test #'string=))))
        (incf (gethash package-name counts 0))))
    counts))

(defun counts-table->json-object (table)
  (apply #'make-json-object
         (mapcar (lambda (key) (cons key (gethash key table 0)))
                 (hash-table-keys-sorted table))))

(defun build-symbol-records (role-alist)
  (let ((records nil))
    (dolist (entry role-alist (nreverse records))
      (let* ((key (car entry))
             (roles (copy-list (cdr entry)))
             (package-name (or (symbol-key->package-name key) ""))
             (symbol-name (or (symbol-key->symbol-name key) ""))
             (bindable (if (bindable-roles-p roles) :true :false)))
        (push (list (cons "key" key)
                    (cons "package_name" package-name)
                    (cons "symbol_name" symbol-name)
                    (cons "roles" roles)
                    (cons "bindable" bindable)
                    (cons "provenance" (list)))
              records)))))

(defun maybe-contract-required-entries (contract-pathname)
  "Return contract-required entries; currently empty when sidecar is absent or unsupported."
  (declare (ignore contract-pathname))
  nil)

(defun build-scope-artifact (repo-root-path feature-profile l0-files l1-files forms-by-file failure-state contract-pathname)
  (let* ((contract-required-entries (maybe-contract-required-entries contract-pathname))
         (role-alist (extract-startup-symbol-roles
                      (flatten-forms forms-by-file)
                      :contract-required-entries contract-required-entries))
         (symbols (build-symbol-records role-alist))
         (role-counts (summarize-role-counts symbols))
         (package-counts (summarize-package-counts symbols))
         (bindable-total
           (loop for symbol in symbols
                 count (eq (cdr (assoc "bindable" symbol :test #'string=)) :true)))
         (failure-counts (read-failure-counts-alist failure-state))
         (generated-at (universal-time->rfc3339-utc (get-universal-time)))
         (feature-set (feature-set-for-profile feature-profile)))
    (make-json-object
     (cons "schema_version" +startup-symbol-scope-schema-version+)
     (cons "generator_version" +startup-symbol-scope-generator-version+)
     (cons "inputs"
           (make-json-object
            (cons "repo_root" (namestring repo-root-path))
            (cons "scan_roots" (make-json-array "level-0/*.lisp" "level-1/**/*.lisp"))
            (cons "files_scanned_total" (+ (length l0-files) (length l1-files)))
            (cons "files_scanned_l0" (length l0-files))
            (cons "files_scanned_l1" (length l1-files))
            (cons "contract_hash" (maybe-string-sha256 contract-pathname))
            (cons "source_hash" "")
            (cons "generated_at_utc" generated-at)
            (cons "feature_profile" feature-profile)
            (cons "feature_set" (cons :array (copy-list feature-set)))
            (cons "scanner_script_hash" (maybe-string-sha256 *load-truename*))
            (cons "host_ccl_version" (lisp-implementation-version))))
     (cons "symbols"
           (cons :array symbols))
     (cons "counts"
           (make-json-object
            (cons "symbols_total" (length symbols))
            (cons "bindable_total" bindable-total)
            (cons "by_role" (counts-table->json-object role-counts))
            (cons "by_package" (counts-table->json-object package-counts))
            (cons "excluded_uninterned_total" 0)
            (cons "excluded_unsupported_reader_total"
                  (read-failure-reason-count failure-state
                                             +startup-symbol-scope-read-failure-unsupported-reader-dispatch+))
            (cons "excluded_by_reason"
                  (alist->json-object failure-counts)))))))

(defun write-json-file (pathname value)
  (with-open-file (out pathname
                       :direction :output
                       :if-does-not-exist :create
                       :if-exists :supersede
                       :external-format :utf-8)
    (json-write-value out value)
    (terpri out)))

(defun json-string (value)
  (with-output-to-string (out)
    (json-write-value out value)))

(defun emit-build-summary (scope-artifact out-path failure-state)
  (let* ((counts (cdr (assoc "counts" (cdr scope-artifact) :test #'string=)))
         (inputs (cdr (assoc "inputs" (cdr scope-artifact) :test #'string=)))
         (summary
           (make-json-object
            (cons "schema_version" +startup-symbol-scope-build-schema-version+)
            (cons "artifact_schema_version" +startup-symbol-scope-schema-version+)
            (cons "out_path" out-path)
            (cons "symbols_total"
                  (cdr (assoc "symbols_total" (cdr counts) :test #'string=)))
            (cons "files_scanned_total"
                  (cdr (assoc "files_scanned_total" (cdr inputs) :test #'string=)))
            (cons "excluded_by_reason"
                  (alist->json-object (read-failure-counts-alist failure-state))))))
    (format t "~&STARTUP_SYMBOL_SCOPE_BUILD ~a~%" (json-string summary))
    (finish-output)))

(defun require-arg (argv key)
  (let ((value (cdr (assoc key argv))))
    (unless (and (stringp value) (> (length value) 0))
      (error "Missing required argument ~a" key))
    value))

(defun resolve-contract-json-arg (argv repo-root-path)
  "Resolve contract sidecar path from argv or repo-root default."
  (let ((explicit (cdr (assoc :contract-json argv))))
    (if (and (stringp explicit) (> (length explicit) 0))
      explicit
      (let ((default (merge-pathnames "doc/wasm/bootstrap-l0-contract.v1.json"
                                      repo-root-path)))
        (if (probe-file default)
          (namestring default)
          (error "Missing required argument CONTRACT-JSON"))))))

(defun scanner-fixture-test-assert (condition format-control &rest format-arguments)
  (unless condition
    (error "~?" format-control format-arguments)))

(defun scanner-fixture-roles-for-key (role-alist key)
  (cdr (assoc key role-alist :test #'string=)))

(defun scanner-fixture-key-has-role-p (role-alist key role)
  (let ((roles (scanner-fixture-roles-for-key role-alist key)))
    (and roles
         (member role roles :test #'string=))))

(defun run-startup-symbol-scope-fixture-tests (fixtures-dir)
  (let* ((fixtures-root (truename fixtures-dir))
         (fixture-paths
           (list
            (merge-pathnames "package-transitions.lisp" fixtures-root)
            (merge-pathnames "reader-conditionals.lisp" fixtures-root)
            (merge-pathnames "escaped-symbols.lisp" fixtures-root)
            (merge-pathnames "unsupported-reader-dispatch.lisp" fixtures-root)))
         (feature-set (feature-set-for-profile "wasm32-target-v1")))
    (dolist (fixture fixture-paths)
      (unless (probe-file fixture)
        (error "Missing fixture file: ~a" fixture)))
    (multiple-value-bind (forms-by-file failure-state)
        (scan-files-in-deterministic-order fixture-paths :feature-set feature-set)
      (let* ((role-alist (extract-startup-symbol-roles (flatten-forms forms-by-file)))
             (unsupported-count
               (read-failure-reason-count failure-state
                                          +startup-symbol-scope-read-failure-unsupported-reader-dispatch+))
             (summary
               (make-json-object
                (cons "fixtures_total" (length fixture-paths))
                (cons "symbols_total" (length role-alist))
                (cons "unsupported_reader_dispatch_total" unsupported-count))))
        ;; package transitions
        (scanner-fixture-test-assert
         (scanner-fixture-key-has-role-p role-alist
                                         "COMMON-LISP-USER::FIXTURE-PACKAGE-TRANSITION-USER"
                                         +startup-symbol-role-defined-function+)
         "Missing package-transition key role: ~a"
         "COMMON-LISP-USER::FIXTURE-PACKAGE-TRANSITION-USER")
        (scanner-fixture-test-assert
         (scanner-fixture-key-has-role-p role-alist
                                         "CCL::FIXTURE-PACKAGE-TRANSITION-CCL"
                                         +startup-symbol-role-defined-function+)
         "Missing package-transition key role: ~a"
         "CCL::FIXTURE-PACKAGE-TRANSITION-CCL")
        ;; reader conditionals
        (scanner-fixture-test-assert
         (scanner-fixture-key-has-role-p role-alist
                                         "CCL::FIXTURE-READER-CONDITIONAL-ENABLED"
                                         +startup-symbol-role-defined-function+)
         "Missing enabled reader-conditional symbol: ~a"
         "CCL::FIXTURE-READER-CONDITIONAL-ENABLED")
        (scanner-fixture-test-assert
         (null (scanner-fixture-roles-for-key role-alist
                                              "CCL::FIXTURE-READER-CONDITIONAL-DISABLED"))
         "Disabled reader-conditional symbol should be excluded: ~a"
         "CCL::FIXTURE-READER-CONDITIONAL-DISABLED")
        ;; escaped symbols
        (scanner-fixture-test-assert
         (scanner-fixture-key-has-role-p role-alist
                                         "CCL::FIXTUREESCAPEDFUNCTION"
                                         +startup-symbol-role-defined-function+)
         "Missing escaped function key role: ~a"
         "CCL::FIXTUREESCAPEDFUNCTION")
        (scanner-fixture-test-assert
         (scanner-fixture-key-has-role-p role-alist
                                         "CCL::FIXTUREESCAPEDSPECIAL"
                                         +startup-symbol-role-defined-special+)
         "Missing escaped special key role: ~a"
         "CCL::FIXTUREESCAPEDSPECIAL")
        ;; unsupported reader dispatch
        (scanner-fixture-test-assert
         (>= unsupported-count 1)
         "Expected at least one unsupported reader-dispatch exclusion")
        (format t "~&STARTUP_SYMBOL_SCOPE_FIXTURE_TEST ~a~%" (json-string summary))
        (finish-output)
        t))))

(defun main ()
  (handler-case
      (let* ((argv (parse-argv ccl:*command-line-argument-list*)))
        (when (cdr (assoc :help argv))
          (usage)
          (quit 0))
        (when (cdr (assoc :run-fixture-tests argv))
          (handler-case
              (progn
                (run-startup-symbol-scope-fixture-tests
                 (require-arg argv :fixtures-dir))
                (quit 0))
            (error (condition)
              (format *error-output*
                      "~&STARTUP_SYMBOL_SCOPE_FIXTURE_TEST_FAIL ~a~%"
                      condition)
              (finish-output *error-output*)
              (quit 1))))
        (let* ((repo-root (require-arg argv :repo-root))
               (out-path (require-arg argv :out))
               (feature-profile (require-arg argv :feature-profile))
               (repo-root-path (repo-root-pathname repo-root))
               (contract-json (resolve-contract-json-arg argv repo-root-path))
               (feature-set (feature-set-for-profile feature-profile)))
          (multiple-value-bind (all-files l0-files l1-files)
              (collect-scan-paths repo-root-path)
            (multiple-value-bind (forms-by-file failure-state)
                (scan-files-in-deterministic-order all-files
                                                   :feature-set feature-set)
              (let ((scope-artifact (build-scope-artifact repo-root-path
                                                          feature-profile
                                                          l0-files
                                                          l1-files
                                                          forms-by-file
                                                          failure-state
                                                          contract-json)))
                (write-json-file out-path scope-artifact)
                (emit-build-summary scope-artifact out-path failure-state))))))
    (error (condition)
      (format *error-output* "~&STARTUP_SYMBOL_SCOPE_BUILD_FAIL ~a~%" condition)
      (finish-output *error-output*)
      (quit 1))))

(main)
#-wasm32-target
(ccl:quit)
