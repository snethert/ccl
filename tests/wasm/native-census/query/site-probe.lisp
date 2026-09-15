;;; Private native recompilation. No source edit, FASL, or global definition install.
(defpackage :ccl-census-query (:use :cl))
(in-package :ccl-census-query)
(defvar *events* nil)
(defvar *total* 0)
(defvar *limit* 10000)
(defvar *owner* nil)

(defun obj (&rest xs) (apply #'ccl-startup-census::object xs))
(defun printed (x)
  (let ((*print-circle* t) (*print-readably* t) (*package* (find-package :keyword)))
    (write-to-string x)))

(defun dispatch (designator &rest args)
  ;; Resolve a symbol only AFTER all arguments have been evaluated, then invoke
  ;; that exact value. Recording the symbol's earlier cell would be unsound.
  (unless (eq *owner* ccl:*current-process*) (error "QUERY-WITNESS-OWNER"))
  (let* ((value (if (symbolp designator) (fboundp designator) designator))
         (function (and (functionp value) value)))
    (incf *total*)
    (when (<= *total* *limit*)
      (push (list designator function) *events*))
    ;; APPLY preserves all values and nonlocal exits. Invalid designators retain
    ;; native dispatch/error behavior; a selected target is not an entry proof.
    (apply (or function designator) args)))

(defun definition (path name)
  (let ((*package* (find-package :cl-user)) (*readtable* (copy-readtable))
        (*read-eval* nil) (found nil))
    (with-open-file (s path :external-format :utf-8)
      (loop for start = (file-position s) for form = (read s nil s) until (eq form s) do
        (cond ((and (consp form) (eq (car form) 'in-package))
               (setf *package* (or (find-package (second form)) (error "QUERY-SOURCE-PACKAGE"))))
              ((and (consp form) (eq (car form) 'defun) (equal (second form) name))
               (when found (error "QUERY-DUPLICATE-DEFINITION"))
               (setf found (list form start (file-position s)))))))
    (or found (error "QUERY-NO-TOPLEVEL-DEFUN"))))

(defun lambda-form (form)
  ;; Use U1's DEFUN expander, retaining its block and global-name declaration,
  ;; but never evaluate the installation form it returns.
  (let* ((expanded (macroexpand-1 form)) (install (second expanded)) (nf (second install)))
    (unless (and (eq (first expanded) 'progn) (eq (first install) 'ccl::%defun)
                 (eq (first nf) 'ccl::nfunction) (eq (first (third nf)) 'lambda))
      (error "QUERY-DEFUN-EXPANSION"))
    (third nf)))

(defun sites (root)
  (let ((result nil))
    (labels ((family (afunc fpath)
               (let ((seen (make-hash-table :test #'eq)))
                 (labels ((walk (x path)
                            (cond
                              ((ccl::acode-p x)
                               (unless (gethash x seen)
                                 (setf (gethash x seen) t)
                                 (let ((op (ccl::acode-operator-name (ccl::acode-operator x))))
                                   (when (eq op 'ccl::call)
                                     (push (list x fpath path) result))
                                   (unless (member op '(ccl::immediate ccl::fixnum ccl::nil ccl::t))
                                     (walk (ccl::acode-operands x) (append path '("operands")))))))
                              ((consp x)
                               (unless (gethash x seen)
                                 (setf (gethash x seen) t)
                                 (walk (car x) (append path '("car")))
                                 (walk (cdr x) (append path '("cdr"))))))))
                   (walk (ccl::afunc-acode afunc) nil)))
               (loop for child in (ccl::afunc-inner-functions afunc) for i from 0 do
                 (family child (append fpath (list i))))))
      (family root nil))
    (nreverse result)))

(defun site-record (entry index)
  (destructuring-bind (node family path) entry
    (let ((callee (first (ccl::acode-operands node))))
      (obj "index" index "family_path" family "acode_path" path
           "operator" "CCL::CALL"
           "callee_operator" (if (ccl::acode-p callee)
                                  (ccl-startup-census::label-of
                                    (ccl::acode-operator-name (ccl::acode-operator callee))) :null)
           "spread" (if (third (ccl::acode-operands node)) :true :false)))))

(defun rewrite-call (node)
  (destructuring-bind (callee arglist &optional spread) (ccl::acode-operands node)
    (unless (and (listp arglist) (= (length arglist) 2)) (error "QUERY-CALL-ARGUMENTS"))
    ;; Native register arguments are stored in reverse order. Repartition after
    ;; adding the original designator as the forwarding function's first arg.
    (let* ((args (cons callee (append (first arglist) (reverse (second arglist)))))
           (nreg (if spread 1 (ccl::backend-num-arg-regs ccl::*host-backend*)))
           (stack (max 0 (- (length args) nreg))))
      (setf (ccl::acode-operands node)
            (list (ccl::make-acode (ccl::%nx1-operator ccl::immediate) #'dispatch)
                  (list (subseq args 0 stack) (reverse (nthcdr stack args))) spread)))))

(defun compile-observed (lambda name selected instrument)
  (let* ((backend ccl::*host-backend*) (old (ccl::backend-p2-compile backend))
         (owner ccl:*current-process*) (catalog nil) (visited 0) (result nil))
    (unwind-protect
      (progn
        (setf (ccl::backend-p2-compile backend)
          (lambda (afunc &rest args)
            (unless (eq owner ccl:*current-process*) (error "QUERY-COMPILE-OWNER"))
            (incf visited)
            (unless (= visited 1) (error "QUERY-MULTIPLE-PASS2-ROOTS"))
            (let* ((entries (sites afunc))
                   (entry (and selected (nth selected entries)))
                   (node (first entry)) (saved (and node (ccl::acode-operands node))))
              (setf catalog (loop for item in entries for i from 0 collect (site-record item i)))
              (when (and selected (null entry)) (error "QUERY-SITE-ABSENT"))
              (unwind-protect
                (progn (when instrument (rewrite-call node)) (apply old afunc args))
                (when node (setf (ccl::acode-operands node) saved))))))
        (setf result (ccl::compile-named-function (copy-tree lambda) :name name
                                                :force-legacy-backend t :keep-symbols nil)))
      (setf (ccl::backend-p2-compile backend) old))
    (unless (and (functionp result) (= visited 1) (eq old (ccl::backend-p2-compile backend)))
      (error "QUERY-COMPILE-RESTORATION"))
    (values result catalog)))

(defun code-bytes (fn)
  (subseq (ccl-resident-bodies::payload-hex fn (ccl::uvsize (ccl::%function-to-function-vector fn)))
          0 (* 16 (ccl::%function-code-words fn))))

(defun scenario (fn runner)
  (handler-case
    (list :returned (multiple-value-list (funcall runner fn)))
    (error (e) (list :condition (type-of e)))))

(defun events ()
  (loop for (designator fn) in (reverse *events*) for index from 0 collect
    (obj "event" index "designator" (ccl-rich-census::describe-value designator nil)
         "target" (if fn (ccl-rich-census::describe-value fn nil) :null)
         "observation" "resolved-for-dispatch; entry and completion not asserted")))

(defun run ()
  (let* ((*read-eval* nil)
         (name (read-from-string (ccl:getenv "QUERY_FUNCTION")))
         (source (ccl:getenv "QUERY_SOURCE"))
         (form (definition source name))
         (lambda (lambda-form (first form)))
         (prior (fboundp name))
         (site-text (ccl:getenv "QUERY_SITE"))
         (site (and site-text (parse-integer site-text)))
         (output nil))
    (when (and site (< site 0)) (error "QUERY-SITE-INDEX"))
    (multiple-value-bind (reference catalog) (compile-observed lambda name site nil)
      (setf output (obj "version" 1 "function" (ccl-startup-census::label-of name)
                        "source_start" (second form) "source_end" (third form)
                        "form" (printed (first form)) "sites" catalog))
      (when site
        (let* ((scenario-form (with-open-file (s (ccl:getenv "QUERY_SCENARIO"))
                                (let ((x (read s)))
                                  (unless (and (consp x) (eq (car x) 'lambda) (eq (read s nil s) s))
                                    (error "QUERY-SCENARIO-FORM")) x)))
               (runner (compile nil scenario-form))
               (first (scenario reference runner))
               (*events* nil) (*total* 0) (*owner* ccl:*current-process*)
               (*limit* (parse-integer (or (ccl:getenv "QUERY_EVENT_LIMIT") "10000"))))
          (multiple-value-bind (instrumented again) (compile-observed lambda name site t)
            (unless (equal catalog again) (error "QUERY-SITE-DRIFT"))
            (let ((second (scenario instrumented runner)))
              (multiple-value-bind (restored third) (compile-observed lambda name site nil)
                (unless (and (equal third catalog) (equal (code-bytes reference) (code-bytes restored)))
                  (error "QUERY-CODE-RESTORATION"))
                (let ((last (scenario restored runner)))
                  (unless (and (equalp first second) (equalp first last))
                    (error "QUERY-SCENARIO-DIFFERENCE ~s ~s ~s" first second last))
                  (setf output (append output
                    (list "site" site "scenario_result" (printed first)
                          "events" (events) "total_events" *total*
                          "dropped_events" (max 0 (- *total* *limit*))
                          "reference_code" (code-bytes reference)
                          "instrumented_code" (code-bytes instrumented)
                          "restored_code_identical" :true "scenario_equal" :true
                          "bound" :false))))))))))
    (unless (eq prior (fboundp name)) (error "QUERY-DEFINITION-INSTALLED"))
    (with-open-file (s (ccl:getenv "QUERY_OUTPUT") :direction :output :if-exists :error)
      (ccl-rich-census::write-json output s) (terpri s))
    (format t "CENSUS-QUERY-PASS~%")))
