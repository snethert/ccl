(in-package :wasm32-compiler)

;;; Compile original DEFMETHOD forms and execute their installers on target.
;;; The qualified native class/method projection is not extended.
(defparameter *namespace-method-names*
  '(streamp input-stream-p output-stream-p open-stream-p interactive-stream-p stream-element-type
    ccl::initialize-basic-stream ccl::stream-create-ioblock
    ccl::map-to-basic-stream-class-name ccl::select-stream-class
    ccl::select-stream-advance-function ccl::select-stream-untyi-function
    ccl::stream-position ccl::stream-length ccl::stream-filename
    ccl::stream-actual-filename (setf ccl::stream-filename)
    (setf ccl::stream-actual-filename) ccl::stream-read-byte
    ccl::stream-read-vector ccl::stream-read-char ccl::stream-unread-char
    ccl::stream-read-line ccl::stream-peek-char ccl::stream-read-char-no-hang
    ccl::default-character-encoding
    ccl::stream-io-error ccl::stream-eofp ccl::stream-listen
    close ccl::class-prototype find-method))

(defun namespace-method-forms ()
  (let ((*package* (find-package :ccl)) (forms nil))
    (dolist (file '("ccl:level-1;l1-clos-boot.lisp"
                    "ccl:level-1;l1-streams.lisp" "ccl:level-1;l1-sysio.lisp"
                    "ccl:level-1;l1-unicode.lisp"))
      (with-open-file (stream file)
        (loop for form = (read stream nil :end) until (eq form :end) do
          (when (and (consp form) (eq (car form) 'defmethod)
                     (member (second form) *namespace-method-names* :test #'equal))
            (let* ((tail (cddr form))
                   (qualifiers (loop while (and tail (atom (car tail))) collect (pop tail)))
                   (specializers (loop for arg in (car tail) until (member arg lambda-list-keywords)
                                       collect (if (consp arg) (second arg) t))))
              (unless (find-if
                       (lambda (spec)
                         (and (equal (first spec) (second form))
                              (equal (second spec) specializers)
                              (equal (fourth spec) qualifiers)))
                       *condition-method-specs*)
                (push form forms)))))))
    ;; Read the accessor declarations from their defining source. D1's
    ;; method entry uses ordinary SLOT-VALUE, as in the qualified condition
    ;; accessors; the methods themselves are created by DEFMETHOD on target.
    (with-open-file (stream "ccl:level-1;l1-error-system.lisp")
      (loop for form = (read stream nil :end) until (eq form :end) do
        (when (and (consp form) (eq (car form) 'define-condition)
                   (member (second form) '(file-error stream-error)))
          (dolist (slot (fourth form))
            (let ((reader (getf (cdr slot) :reader)))
              (when reader
                (push `(defmethod ,reader ((object ,(second form)))
                         (slot-value object ',(car slot))) forms)))))))
    (list `(defun namespace-method-initialize () ,@(nreverse forms) t))))
