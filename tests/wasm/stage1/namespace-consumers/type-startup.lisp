(in-package :wasm32-compiler)

;;; Select original initialization forms for the type dependencies of OPEN.
;;; The parser, cache, translators and subtype methods are CCL's own bodies.
(defun namespace-type-startup-form ()
  (let ((*package* (find-package :ccl)) (classes nil) (forms nil) (variables nil) (documentation nil)
        (class-mapping nil) (encodings nil) (encoding-macro nil) (mop-startup nil)
        (specializer-slots nil) (eql-specializer-slots nil) (class-info-init nil)
        (wanted '(ccl::%deftype-expanders% ccl::*type-translators*
                  ccl::*builtin-type-info* ccl::%builtin-type-cells%
                  ccl::*wild-type* ccl::*empty-type* ccl::*universal-type*)))
    (labels ((read-forms (file function)
               (with-open-file (s file)
                 (loop for form = (read s nil :eof) until (eq form :eof)
                       do (funcall function form))))
             (class-map (form)
               (when (consp form)
                 (if (and (eq (car form) 'macrolet)
                          (eq (caaadr form) 'ccl::map-subtag))
                   (progn
                     (assert (null class-mapping))
                     ;; Keep the original mapping forms for tags represented
                     ;; by D1. Native code vectors and catch frames have no D1
                     ;; heap tag and cannot occur in this target's objects.
                     (setq class-mapping
                           `(let ((ccl::v ccl::*class-table*))
                              (macrolet ,(second form)
                                ,@(remove-if-not
                                   (lambda (mapping)
                                     (and (consp mapping)
                                          (eq (car mapping) 'ccl::map-subtag)
                                          (symbolp (second mapping))
                                          (boundp (second mapping))))
                                   (cddr form))))))
                   (progn (class-map (car form)) (class-map (cdr form))))))
             (deftypes (form)
               (when (consp form)
                 (if (and (eq (car form) 'deftype)
                          (member (second form) '(signed-byte unsigned-byte)))
                   (push form forms)
                   (progn (deftypes (car form)) (deftypes (cdr form)))))))
      (call-with-target
       (lambda ()
         (read-forms "ccl:level-0;l0-misc.lisp"
           (lambda (form)
             (when (and (consp form) (eq (car form) 'ccl::%fhave)
                        (equal (second form) '(quote ccl::set-documentation)))
               (push form documentation))))
         (read-forms "ccl:level-1;l1-clos-boot.lisp"
           (lambda (form)
             (class-map form)
             (when (and (consp form) (eq (car form) 'ccl::fset)
                        (or (equal (second form) '(quote ccl::%make-method-instance))
                            (equal (second form) '(quote ccl::pessimize-make-instance-for-class-name))))
               (push form mop-startup))
             (when (and (consp form)
                        (or (eq (car form) 'ccl::new-type-class)
                            (and (eq (car form) 'defparameter)
                                 (eq (second form) 'ccl::*class-type-class*))))
               (push form classes))))
         (read-forms "ccl:level-1;l1-typesys.lisp"
           (lambda (form)
             (when (consp form)
               (when (or (and (eq (car form) 'defvar) (member (second form) wanted))
                         (and (eq (car form) 'let*)
                              (eq (caar (second form)) 'ccl::type-cache-specs))
                         (and (eq (car form) 'ccl::define-type-method)
                              (member (caadr form) '(class ccl::named number ccl::union ccl::intersection)))
                         (and (eq (car form) 'ccl::def-type-translator)
                              (member (second form) '(integer or and))))
                 (when (eq (car form) 'defvar) (push (second form) variables))
                 (push form forms))
               (deftypes form))))
         (read-forms "ccl:level-1;l1-aprims.lisp"
           (lambda (form)
             (when (and (consp form) (eq (car form) 'defvar)
                        (member (second form) '(ccl::%setf-function-names%
                                               ccl::%setf-function-name-inverses%
                                               ccl::*setf-names-lock*)))
               (push `(makunbound ',(second form)) mop-startup)
               (push form mop-startup))))
         (read-forms "ccl:level-1;l1-dcode.lisp"
           (lambda (form)
             (when (and (consp form) (eq (car form) 'let*)
                        (eq (caaadr form) 'ccl::eql-specializers-lock))
               (push form mop-startup))
             (when (and (consp form) (member (car form) '(defvar defparameter))
                        (member (second form) '(ccl::*min-gf-dispatch-table-size*
                                               ccl::*max-gf-dispatch-table-size*
                                               ccl::*gf-dt-ovf-cnt*)))
               (when (eq (car form) 'defvar)
                 (push `(makunbound ',(second form)) mop-startup))
               (push form mop-startup))))
         (read-forms "ccl:level-1;l1-clos.lisp"
           (lambda (form)
             (when (and (consp form)
                        (eq (car form) 'ccl::%ensure-class-preserving-wrapper))
               (cond ((equal (second form) '(quote ccl::specializer))
                      (setq specializer-slots (getf (cddr form) :direct-slots)))
                     ((equal (second form) '(quote class))
                      (setq class-info-init
                            (getf (find 'ccl::info (eval (getf (cddr form) :direct-slots))
                                         :key (lambda (slot) (getf slot :name))) :initform)))
                     ((equal (second form) '(quote ccl::eql-specializer))
                      (setq eql-specializer-slots (getf (cddr form) :direct-slots)))))))
         (dolist (file '("ccl:level-1;l1-streams.lisp" "ccl:level-1;l1-sysio.lisp"
                        "ccl:level-1;l1-unicode.lisp"))
           (read-forms file
             (lambda (form)
               (when (and (consp form) (eq (car form) 'defmacro)
                          (eq (second form) 'ccl::define-character-encoding))
                 (setq encoding-macro (cdr form)))
               (when (and (consp form)
                          (or (and (member (car form) '(defvar defparameter))
                                   (member (second form)
                                     '(ccl::*character-encodings* ccl::*external-formats*
                                       ccl::*default-external-format*
                                       ccl::*default-file-character-encoding*
                                       ccl::*default-line-termination*
                                       ccl::*canonical-line-termination-conventions*
                                       ccl::*elements-per-buffer*
                                       ccl::*native-newline-string* ccl::*unicode-newline-string*
                                       ccl::*cr-newline-string* ccl::*crlf-newline-string*
                                       ccl::*nul-string*)))
                              (and (eq (car form) 'ccl::define-character-encoding)
                                   (member (second form) '(:iso-8859-1 :utf-8)))))
                 (when (eq (car form) 'defvar)
                   (push `(makunbound ',(second form)) encodings))
                 (push form encodings))))))))
    (assert (and class-mapping specializer-slots eql-specializer-slots class-info-init))
    `(defun namespace-type-initialize (image setf-names)
       ,class-mapping
       ;; Original l1-clos-boot discriminator for DEFSTRUCT instances.
       (setf (svref ccl::*class-table* wasm32::subtag-struct)
             #'(lambda (s) (ccl::%structure-class-of s)))
       ;; Resolve additional bootstrap globals to classes already present in
       ;; the qualified class set. New methods and GFs are constructed below.
       (setq ccl::*generic-function-class* (find-class 'generic-function)
             ccl::*standard-generic-function-class* (find-class 'standard-generic-function)
             ccl::*method-class* (find-class 'ccl::method)
             ccl::*standard-method-class* (find-class 'standard-method)
             ccl::*specializer-class* (find-class 'ccl::specializer)
             ccl::*character-class* (find-class 'character)
             ccl::*base-char-class* (find-class 'base-char)
             ccl::*standard-char-class* (find-class 'standard-char))
       ;; All documentation keys in this fixture are already rooted symbols;
       ;; its owned strong table has the same liveness for those keys.
       (setq ccl::%documentation (make-hash-table :test 'eq)
             ccl::%documentation-lock% (ccl:make-lock))
       ,@(nreverse documentation)
       ,@(nreverse mop-startup)
       ;; These are the compiler's structured SETF-name identities, linked
       ;; to the same symbol cells used by its emitted calls.
       (dolist (entry setf-names)
         (setf (gethash (car entry) ccl::%setf-function-names%) (cdr entry)
               (gethash (cdr entry) ccl::%setf-function-name-inverses%) (car entry)))
       (setq ccl::*type-classes* nil
             ccl::*type-kind-info* (make-hash-table :test 'equal))
       ,@(nreverse classes)
       ;; The fixture already admits these class definitions. Construct their
       ;; target ctypes using the original constructor, without copying ctypes
       ;; or native translator functions out of the host process.
       (dolist (entry (svref image 11))
         (let ((class (cdr entry)))
           (unless (ccl::%class.info class)
             (setf (ccl::%class.info class) ,class-info-init))
           (ccl::update-class-proper-names (car entry) nil class)
           (setf (ccl::%class.ctype class) (ccl::make-class-ctype class)
                 (ccl::info-type-kind (car entry)) :instance)))
       ,@(mapcar (lambda (name) `(makunbound ',name)) variables)
       ,@(nreverse forms)
       ;; The frozen class graph deliberately omits EQL-SPECIALIZER's slot
       ;; metadata. Build it on target from the two original declarations,
       ;; using CCL's ordinary slot-definition constructor. No native slot
       ;; objects or newly projected methods enter the fixture.
       (let* ((class (find-class 'ccl::eql-specializer))
              (declarations (append ,specializer-slots ,eql-specializer-slots))
              (names (ccl::%wrapper-instance-slots (ccl::%class.own-wrapper class))))
         (assert (= (length declarations) (length names)))
         (setf (ccl::%class.slots class)
               (loop for declaration in declarations for i from 0 collect
                 (let ((slot
                         (make-instance 'ccl::standard-effective-slot-definition
                           :name (getf declaration :name)
                           :type (getf declaration :type t)
                           :initargs (getf declaration :initargs)
                           :initform (getf declaration :initform)
                           :initfunction (getf declaration :initfunction)
                           :allocation :instance :class class)))
                   (assert (eq (getf declaration :name) (svref names i)))
                   (setf (ccl::standard-effective-slot-definition.location slot) (1+ i))
                   slot))))
       ;; Stream prototypes are built on the target from the admitted class
       ;; definitions, using the same allocator as MAKE-BASIC-STREAM-INSTANCE.
       (dolist (entry (svref image 11))
         (let ((class (cdr entry)))
           (when (subtypep class 'ccl::basic-stream)
             (setf (ccl::%class.prototype class) (ccl::allocate-basic-stream class)))))
       (macrolet (,encoding-macro) ,@(nreverse encodings))
       t)))
