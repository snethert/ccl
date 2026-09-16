;;; One native build namespace for compiler IR, live registries and code bytes.
;;; The existing reversible observation patch supplies the compiler hooks.
(defpackage :ccl-complete-census (:use :cl)
  (:import-from :ccl-startup-census #:object #:dependency-id)
  (:import-from :ccl-rich-census #:write-json)
  (:import-from :ccl-dispatch-registry #:field #:name-data))
(in-package :ccl-complete-census)

(defvar *output* nil)
(defvar *serial* 0)
(defvar *owner* nil)
(defvar *busy* nil)
(defvar *native-functions* (make-hash-table :test #'eq))
(defvar *pending-functions* nil)
(defvar *original-hook* nil)
(defvar *wrappers* nil)
(defvar *parents* nil)
(defparameter *method-names*
  '(ccl::%add-standard-method-to-standard-gf
    ccl::%remove-standard-method-from-containing-gf ccl::%set-gf-dcode))
(defparameter *retained-phases*
  '(:before-pass2 :function-materialized :binding-installed :binding-removing
    :compile-effect-call :compile-effect-values :compile-initializer-enter :compile-initializer-return
    :compile-initializer-abort :fasl-effect-enter :fasl-effect-return :fasl-effect-abort
    :fasl-function-enter :fasl-function-return :fasl-function-abort :fasl-function-write
    :load-effect-call :load-effect-value :load-effect-abort :load-initializer-emitted :load-operation-emitted
    :startup-enter :startup-return :read))

(defun emit (kind &rest fields)
  (unless (eq *owner* ccl:*current-process*) (error "COMPLETE-CENSUS-OWNER"))
  (apply #'write-record kind fields))

(defun write-record (kind &rest fields)
  (let ((row (apply #'object "sequence" (incf *serial*) "kind" kind
                    "build_event" ccl-rich-census::*sequence*
                    "parent" (or (car *parents*) :null) fields)))
    (write-json row *output*) (terpri *output*) *serial*))

(defun function-id (fn)
  (unless (functionp fn) (error "COMPLETE-CENSUS-FUNCTION"))
  (unless (gethash fn *native-functions*)
    (setf (gethash fn *native-functions*) t)
    (push fn *pending-functions*))
  (dependency-id fn))

(defun scalar (v)
  (cond ((null v) :null)
        ((integerp v) (object "integer" v))
        ((characterp v) (object "character" (char-code v)))
        ((stringp v) (object "string" v))
        ((functionp v) (object "function" (function-id v)))
        ((symbolp v) (object "symbol" (dependency-id v) "name" (name-data v)))
        (t (object "object" (dependency-id v) "type" (name-data (type-of v))))))

(defun drain-functions ()
  (loop while *pending-functions* for fn = (pop *pending-functions*) do
    (let* ((proto (ccl::closure-function fn))
           (vector (ccl::%function-to-function-vector fn))
           (words (ccl::uvsize vector)) (code-words (ccl::%function-code-words fn))
           (note (ccl:function-source-note fn)) (literals nil))
      (ccl::%map-lfimms fn (lambda (v) (push (scalar v) literals)))
      (emit "function" "id" (function-id fn) "prototype" (function-id proto)
            "name" (name-data (ccl:function-name fn))
            "bits" (ccl::lfun-bits fn) "words" words "code_words" code-words
            "source" (if note (namestring (ccl:source-note-filename note)) :null)
            "source_start" (if note (ccl:source-note-start-pos note) :null)
            "source_end" (if note (ccl:source-note-end-pos note) :null)
            "payload_hex" (ccl-resident-bodies::payload-hex fn words)
            "literals" (nreverse literals)))))

(defun live-gf (gf)
  (unless (ccl::standard-generic-function-p gf) (error "COMPLETE-CENSUS-GF"))
  (let ((unbound (loop for slot in (list ccl::sgf.name ccl::sgf.methods ccl::sgf.method-combination)
                       when (eq (ccl::%svref (ccl::gf.slots gf) slot) (ccl::%slot-unbound-marker)) collect slot)))
    (if unbound
      (object "status" "UNINITIALIZED" "gf" (function-id gf) "unbound_slots" unbound)
      (ccl-dispatch-registry::snapshot gf))))

(defun checkpoint (stage)
  (let ((*busy* t) (ccl-rich-census::*busy* t) (*gensym-counter* *gensym-counter*)
        (population (copy-list (ccl::population-data ccl::%all-gfs%))))
    (emit "registry-checkpoint" "stage" stage "entries" (mapcar #'live-gf population))
    (emit "backend-checkpoint" "stage" stage
          "dispatch" (loop for v across (ccl::backend-p2-dispatch ccl::*host-backend*) collect (scalar v))
          "builtins" (loop for v across ccl::%builtin-functions% collect (scalar v)))
    (drain-functions)))

(defun method-state (method)
  (if (null method) :null
    (object "id" (dependency-id method)
            "owner" (if (ccl::%method.gf method) (function-id (ccl::%method.gf method)) :null)
            "function" (function-id (ccl::%method.function method))
            "specializers" (mapcar #'dependency-id (ccl::%method.specializers method))
            "qualifiers" (mapcar #'name-data (ccl::%method.qualifiers method)))))

(defun mutation (name original args)
  (if (or *busy* ccl-rich-census::*busy*) (apply original args)
    (let* ((gf (if (eq name 'ccl::%remove-standard-method-from-containing-gf)
                (ccl::%method.gf (first args)) (first args)))
           (method (cond ((eq name 'ccl::%add-standard-method-to-standard-gf) (second args))
                         ((eq name 'ccl::%remove-standard-method-from-containing-gf) (first args))))
           (entry (let ((*busy* t) (ccl-rich-census::*busy* t) (*gensym-counter* *gensym-counter*))
                    (emit "mutation-enter" "operation" (name-data name)
                          "gf" (if gf (live-gf gf) :null) "method" (method-state method)
                          "dcode" (if (eq name 'ccl::%set-gf-dcode) (function-id (second args)) :null))))
           (*parents* (cons entry *parents*)) (completed nil))
      (unwind-protect
        (multiple-value-prog1 (apply original args) (setf completed t))
        (let ((*busy* t) (ccl-rich-census::*busy* t) (*gensym-counter* *gensym-counter*))
          (emit "mutation-leave" "entry" entry "completed" (if completed :true :false)
                "gf" (if gf (live-gf gf) :null) "method" (method-state method))
          (drain-functions))))))

(defun install-method-wrapper (name)
  (let* ((current (fdefinition name)) (old (assoc name *wrappers*)))
    (unless (and old (eq current (third old)))
      (let ((wrapper (lambda (&rest args) (mutation name current args))))
        (setf *wrappers* (acons name (list current wrapper) (remove name *wrappers* :key #'car)))
        (emit "observer-wrapper" "symbol" (dependency-id name)
              "original" (function-id current) "wrapper" (function-id wrapper))
        (let ((*busy* t) (ccl-rich-census::*busy* t) (ccl::*startup-census-hook* nil)
              (ccl::*warn-if-redefine-kernel* nil))
          (setf (fdefinition name) wrapper))))))

(defun observe (phase value)
  (when (or *busy* ccl-rich-census::*busy*) (return-from observe))
  ;; The reviewed trace already contains instruction emissions and macro
  ;; expansion traffic. This execution needs complete compiler bodies and
  ;; registry/binding history. Retain both sides of every selected phase pair.
  (unless (or (member phase *retained-phases*)
              (and (eq phase :frontend) (typep value 'ccl::afunc) (ccl::afunc-lfun value)))
    (return-from observe))
  (funcall *original-hook* phase value)
  (unless *busy*
    (let ((*busy* t) (ccl-rich-census::*busy* t) (*gensym-counter* *gensym-counter*))
      (case phase
        (:function-materialized
          ;; The shared hook passes the AFUNC, with its LFUN now installed.
          ;; It does not pass the resulting native function directly.
          (unless (typep value 'ccl::afunc) (error "COMPLETE-CENSUS-MATERIALIZATION"))
          (let ((pending (list value)) (rows nil))
            (loop while pending for a = (pop pending) do
              (push (object "afunc" (dependency-id a)
                            "function" (if (ccl::afunc-lfun a) (function-id (ccl::afunc-lfun a)) :null)) rows)
              (setf pending (append (ccl::afunc-inner-functions a) pending)))
            (emit "compiler-materialization" "functions" (nreverse rows))))
        (:binding-installed
          (when (functionp (second value)) (function-id (second value)))
          (when (member (first value) *method-names*) (install-method-wrapper (first value))))))))

(defun with-build-observation (events extra thunk)
  (let ((*owner* ccl:*current-process*) (*serial* 0) (*wrappers* nil) (*parents* nil)
        (*native-functions* (make-hash-table :test #'eq)) (*pending-functions* nil)
        (*output* (open extra :direction :output :if-exists :error :external-format :utf-8))
        (old-oid (fdefinition 'ccl-dispatch-registry::oid))
        (old-fn (fdefinition 'ccl-dispatch-registry::fn))
        (*original-hook* #'ccl-rich-census::observe) (completed nil))
    (unwind-protect
      (progn
        (setf (fdefinition 'ccl-dispatch-registry::oid) #'dependency-id
              (fdefinition 'ccl-dispatch-registry::fn) #'function-id)
        (ccl-rich-census::start events)
        (setf ccl::*startup-census-hook* #'observe)
        (let ((*busy* t) (ccl-rich-census::*busy* t) (*gensym-counter* *gensym-counter*))
          (emit "capture-policy" "phases" (mapcar #'symbol-name *retained-phases*)
                "frontend" "Only pass-1 bodies that already contain an LFUN; ordinary bodies are captured before pass 2"
                "omitted" '("instruction-emissions" "lowering-frames" "macro-expansion-traffic"))
          (ccl::%map-lfuns #'function-id)
          (checkpoint "before")
          (dolist (name *method-names*) (install-method-wrapper name)))
        (funcall thunk)
        (checkpoint "after")
        (setf completed t))
      (setf ccl::*startup-census-hook* nil)
      (let ((ccl::*warn-if-redefine-kernel* nil))
        (dolist (row *wrappers*)
          (unless (eq (fdefinition (first row)) (third row)) (error "COMPLETE-CENSUS-WRAPPER-LOST"))
          (setf (fdefinition (first row)) (second row))))
      (setf (fdefinition 'ccl-dispatch-registry::oid) old-oid
            (fdefinition 'ccl-dispatch-registry::fn) old-fn)
      (when ccl-rich-census::*stream* (ccl-rich-census::finish))
      (let ((*busy* t) (ccl-rich-census::*busy* t))
        (drain-functions)
        (emit "complete" "completed" (if completed :true :false)
              "native_functions" (hash-table-count *native-functions*) "hooks_restored" :true))
      (close *output*))
    (unless completed (error "COMPLETE-CENSUS-INCOMPLETE"))
    (format t "COMPLETE-CENSUS-BUILD-PASS~%")))
