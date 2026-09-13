;;; Source-derived metadata expanders, local to one census process.
(defpackage :ccl-census-macros (:use :cl))
(in-package :ccl-census-macros)

(defvar *sources* nil)
(defvar *registry* nil)
(defvar *uses* nil)
(defvar *remaining* nil)
(defvar *mode* "normal")
(defun obj (&rest fields) (apply #'ccl-source-traversal::obj fields))
(defun label (x) (ccl-source-traversal::label x))
(defun field (x k) (ccl-source-traversal::field x k))
(defun syntax (x)
  ;; Lossless for the proper-list, symbol, string and integer syntax here.
  (cond ((null x) :null)
        ((consp x) (obj "cons" (list (syntax (car x)) (syntax (cdr x)))))
        ((symbolp x) (if (symbol-package x) (obj "symbol" (label x))
                      (obj "symbol" (label x) "identity" (ccl-startup-census::dependency-id x))))
        ((or (integerp x) (stringp x)) x)
        (t (error "MACRO-SYNTAX-NOT-SUPPORTED ~s" x))))

(defun ir (x)
  (cond ((ccl::acode-p x)
         (obj "operator" (label (ccl::acode-operator-name (ccl::acode-operator x)))
              "operands" (ir (ccl::acode-operands x))))
        ((consp x) (obj "cons" (list (ir (car x)) (ir (cdr x)))))
        (t (syntax x))))

(defun ir-probe (&optional shadow)
  (let ((*uses* nil) (*remaining* nil))
    (with-routing
      (lambda ()
        (ir (ccl::afunc-acode
              (ccl-census-stub::capture-lambda
                (if shadow '(lambda () (macrolet ((ccl::gvector (&rest args) (declare (ignore args)) 42))
                                         (ccl::gvector :istruct 10)))
                  '(lambda () (ccl::gvector :istruct 10))) 'ccl::macro-probe)))))))

(defun read-source (relative marker)
  (let* ((path (merge-pathnames relative (pathname (concatenate 'string (ccl:getenv "CCL_DEFAULT_DIRECTORY") "/"))))
         (text (ccl-source-traversal::source-text path))
         (start (search marker text))
         (*package* (find-package "CCL")) (*read-eval* nil))
    (unless (and start (not (search marker text :start2 (1+ start))))
      (error "MACRO-SOURCE-NOT-UNIQUE ~s" marker))
    (multiple-value-bind (form end) (read-from-string text t nil :start start)
      (let ((key (format nil "~a:~d" relative start)))
        (push (obj "key" key "path" relative "start" start "end" end
                   "text" (subseq text start end) "reader" (ccl-source-traversal::context)) *sources*)
        (values form key)))))

(defun native-function (lambda-form)
  ;; Expanders execute on the cross-compiler host. Source is read for the
  ;; census target; this explicit host compilation produces only fixture code.
  (let* ((ccl::*target-backend* ccl::*host-backend*)
         (*features* (ccl::setup-target-features ccl::*host-backend* *features*)))
    (ccl::with-cross-compilation-target ((ccl::backend-name ccl::*host-backend*))
      (ccl::compile-named-function lambda-form :target (ccl::backend-name ccl::*host-backend*)))))

(defun add-expander (form key &optional helper)
  (unless (eq (car form) 'defmacro) (error "SOURCE-MACRO-REQUIRED"))
  (let* ((name (second form))
         (lambda-form (ccl::parse-macro-1 name (third form) (cdddr form)))
         ;; Lexically bind the freshly read helper: no function-cell swap.
         (fn (native-function
               (if helper `(lambda (&rest args)
                             (flet (,(cdr helper)) (apply (function ,lambda-form) args)))
                 lambda-form)))
         (old (macro-function name)))
    (unless (and old (not (eq old fn)) (not (assoc name *registry*)))
      (error "MACRO-REGISTRY-IDENTITY"))
    (push (list name fn old key (if helper (label (second helper)) :null)) *registry*)))

(defun prepare ()
  (ccl-census-stub::with-target-state
    (lambda ()
      (let* ((helper (read-source "level-1/sysutils.lisp" "(defun type-keyword-code "))
             (generator (read-source "lib/macros.lisp" "(defun define-accessors "))
             (generate (native-function `(lambda ,@(cddr generator)))))
        (dolist (spec '(("library/lispequ.lisp" "(defmacro gvector ")
                        ("library/lispequ.lisp" "(defmacro allocate-typed-vector ")
                        ("library/lispequ.lisp" "(defmacro %istruct ")
                        ("lib/macros.lisp" "(defmacro %null-ptr ")))
          (multiple-value-bind (form key) (apply #'read-source spec)
            (add-expander form key (when (member (second form) '(ccl::gvector ccl::allocate-typed-vector)) helper))))
        (dolist (spec '(("(def-accessors (basic-stream) %svref" nil)
                        ("(def-accessor-macros %svref
  pfe.routine-descriptor" t)))
          (multiple-value-bind (form key) (read-source "library/lispequ.lisp" (first spec))
            (let ((generated (funcall generate (second form) (cddr form) (second spec))))
              (unless (eq (car generated) 'progn) (error "ACCESSOR-GENERATOR-SHAPE"))
              (dolist (definition (cdr generated))
                ;; Constants and ADD-ACCESSOR-TYPES are deliberately not installed.
                (when (and (consp definition) (eq (car definition) 'defmacro))
                  (when (and (equal *mode* "wrong-slot") (eq (second definition) 'ccl::basic-stream.state))
                    (setf (car (last (fourth definition))) 3))
                  (add-expander definition key))))))))))

(defun expand-selected (entry form env)
  (if (and (equal *mode* "host-subtag") (eq (first entry) 'ccl::gvector))
    (let ((ccl::*target-backend* ccl::*host-backend*)) (funcall (second entry) form env))
    (funcall (second entry) form env)))

(defun with-routing (thunk)
  (let* ((old-hook *macroexpand-hook*)
         (*macroexpand-hook*
           (lambda (fn form env)
             (let ((entry (and (consp form) (assoc (car form) *registry*))))
               ;; A compiler macro or local shadow with the same name is not
               ;; this binding. Keep it as an explicit remaining dependency.
               (if (and entry (or (equal *mode* "name-only") (eq fn (third entry)))
                        (not (and (equal *mode* "bypass-source") (eq (car form) 'ccl::gvector))))
                 (let ((expansion (expand-selected entry form env)))
                   (push (obj "operator" (label (car form)) "source" (fourth entry)
                              "sequence" (+ (length *uses*) (length *remaining*))
                              "original_id" (ccl-startup-census::dependency-id fn)
                              "selected_id" (ccl-startup-census::dependency-id (second entry))
                              "context" (ccl-source-traversal::context)
                              "input" (syntax form) "output" (syntax expansion)) *uses*)
                   expansion)
                 (progn
                   (let ((note (ccl:function-source-note fn)))
                     (push (obj "operator" (label (car form))
                                "sequence" (+ (length *uses*) (length *remaining*))
                                "function_id" (ccl-startup-census::dependency-id fn)
                                "source" (if note (namestring (ccl::source-note-filename note)) :null)
                                "position" (if note (ccl::source-note-start-pos note) :null)) *remaining*))
                   (funcall old-hook fn form env)))))))
    (funcall thunk)))

(defun probes ()
  (let ((rows nil))
    (ccl-census-descriptions::with-descriptions
      (lambda ()
        (ccl-census-stub::with-target-state
          (lambda ()
            (dolist (entry (reverse *registry*))
              (let* ((name (first entry))
                     (form (cond ((eq name 'ccl::gvector) '(ccl::gvector :istruct 10 20))
                                 ((eq name 'ccl::allocate-typed-vector) '(ccl::allocate-typed-vector :simple-vector 3 7))
                                 ((eq name 'ccl::%istruct) '(ccl::%istruct 'ccl::probe 10 20))
                                 ((eq name 'ccl::%null-ptr) '(ccl::%null-ptr))
                                 (t (list name 'ccl::probe)))))
                (push (obj "operator" (label name) "input" (syntax form)
                           "output" (syntax (expand-selected entry form nil))) rows)))
            (push (obj "operator" "target-ir" "output" (ir-probe)) rows)
            (push (obj "operator" "local-shadow-ir" "output" (ir-probe t)) rows)
            ;; A deliberately different metadata value must affect expansion.
            (let* ((cell (assoc :istruct (arch::target-uvector-subtags wasm-census::*census-arch*)))
                   (old (cdr cell)))
              (unwind-protect
                (progn (setf (cdr cell) 234)
                  (push (obj "operator" "alternate-subtag"
                             "output" (syntax (expand-selected (assoc 'ccl::gvector *registry*) '(ccl::gvector :istruct 10) nil))
                             "ir" (ir-probe)) rows))
                (setf (cdr cell) old)))
            (let ((answer (handler-case
                            (progn (expand-selected (assoc 'ccl::gvector *registry*) '(ccl::gvector :unprovided 10) nil) :null)
                            (error (e) (princ-to-string e)))))
              (push (obj "operator" "missing-subtag" "condition" answer) rows))))))
    (nreverse rows)))

(defun run ()
  (let ((*sources* nil) (*registry* nil) (*uses* nil) (*remaining* nil)
        (*mode* (or (ccl:getenv "CCL_MACRO_MODE") "normal"))
        (before (ccl-source-traversal::state)) (old-hook *macroexpand-hook*))
    (prepare)
    (let ((probe-results (probes)))
      ;; Test restoration through a real nonlocal escape as well as normal return.
      (let ((tag (gensym)))
        (unless (eq :escaped (catch tag (with-routing (lambda () (throw tag :escaped)))))
          (error "MACRO-ESCAPE-FAILED")))
      (unless (eq old-hook *macroexpand-hook*) (error "MACRO-HOOK-NONLOCAL-RESTORATION"))
      (with-routing #'ccl-census-descriptions::run)
      (unless (and (eq old-hook *macroexpand-hook*) (equal before (ccl-source-traversal::state))
                   (every (lambda (entry) (eq (third entry) (macro-function (first entry)))) *registry*))
        (error "MACRO-STATE-NOT-RESTORED"))
      (with-open-file (out (ccl:getenv "CCL_MACRO_OUTPUT") :direction :output :if-exists :error :external-format :utf-8)
        (ccl-startup-census::json
          (obj "version" 1 "sources" (nreverse *sources*)
               "registry" (loop for e in (reverse *registry*) collect
                              (obj "operator" (label (first e)) "source" (fourth e) "helper" (fifth e)
                                   "original_id" (ccl-startup-census::dependency-id (third e))
                                   "selected_id" (ccl-startup-census::dependency-id (second e))))
               "probes" probe-results "uses" (nreverse *uses*) "remaining" (nreverse *remaining*)
               "restored" :true "global_macro_bindings_unchanged" :true
               "macro_environment_qualified" :false) out)
        (terpri out)))))
