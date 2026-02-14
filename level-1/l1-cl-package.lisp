;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Copyright 1994-2009 Clozure Associates
;;;
;;; Licensed under the Apache License, Version 2.0 (the "License");
;;; you may not use this file except in compliance with the License.
;;; You may obtain a copy of the License at
;;;
;;;     http://www.apache.org/licenses/LICENSE-2.0
;;;
;;; Unless required by applicable law or agreed to in writing, software
;;; distributed under the License is distributed on an "AS IS" BASIS,
;;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;;; See the License for the specific language governing permissions and
;;; limitations under the License.

; l1-cl-package.lisp

(in-package "CCL")

(defvar *wasm-startup-truth-schema-version* "startup_truth_v1")
(defvar *wasm-startup-truth-enabled* nil)
(defvar *wasm-startup-truth-seq* 0)
(defvar *wasm-startup-truth-sink* nil)
(defvar *wasm-startup-truth-path* "doc/wasm/startup_truth_v1.jsonl")
(defvar *wasm-startup-truth-stdout-mirror* nil)
(defvar *wasm-startup-truth-session-start-emitted* nil)

(unless (fboundp '%wasm-startup-truth-note-event)
  (defun %wasm-startup-truth-json-escape-string (value)
    (let ((string (if (stringp value) value (princ-to-string value))))
      (with-output-to-string (out)
        (dotimes (i (length string))
          (let ((ch (char string i)))
            (case ch
              (#\" (write-string "\\\"" out))
              (#\\ (write-string "\\\\" out))
              (#\Newline (write-string "\\n" out))
              (#\Return (write-string "\\r" out))
              (#\Tab (write-string "\\t" out))
              (t (write-char ch out))))))))

  (defun %wasm-startup-truth-json-write-string (out value)
    (write-char #\" out)
    (write-string (%wasm-startup-truth-json-escape-string value) out)
    (write-char #\" out))

  (defun %wasm-startup-truth-json-write-object (out pairs)
    (write-char #\{ out)
    (do ((rest pairs (cdr rest))
         (first t nil))
        ((null rest))
      (unless first
        (write-char #\, out))
      (let ((pair (car rest)))
        (%wasm-startup-truth-json-write-string out (car pair))
        (write-char #\: out)
        (%wasm-startup-truth-json-write-value out (cdr pair))))
    (write-char #\} out))

  (defun %wasm-startup-truth-json-write-array (out values)
    (write-char #\[ out)
    (do ((rest values (cdr rest))
         (first t nil))
        ((null rest))
      (unless first
        (write-char #\, out))
      (%wasm-startup-truth-json-write-value out (car rest)))
    (write-char #\] out))

  (defun %wasm-startup-truth-json-write-value (out value)
    (cond
      ((stringp value) (%wasm-startup-truth-json-write-string out value))
      ((integerp value) (princ value out))
      ((floatp value) (princ value out))
      ((eq value :json-true) (write-string "true" out))
      ((eq value :json-false) (write-string "false" out))
      ((null value) (write-string "null" out))
      ((and (consp value) (eq (car value) :object))
       (%wasm-startup-truth-json-write-object out (cdr value)))
      ((and (consp value) (eq (car value) :array))
       (%wasm-startup-truth-json-write-array out (cdr value)))
      (t
       (%wasm-startup-truth-json-write-string out (princ-to-string value)))))

  (defun %wasm-startup-truth-json-key (key)
    (let* ((name
            (cond
              ((keywordp key) (symbol-name key))
              ((symbolp key) (symbol-name key))
              (t (princ-to-string key))))
           (lower (string-downcase name)))
      (substitute #\_ #\- lower)))

  (defun %wasm-startup-truth-keyword-plist-p (value)
    (and (listp value)
         (do ((rest value (cddr rest)))
             ((null rest) t)
           (unless (and (keywordp (car rest))
                        (consp (cdr rest)))
             (return nil)))))

  (defun %wasm-startup-truth-symbol-json (value)
    (let ((pkg (symbol-package value)))
      (cons :object
            (list
             (cons "kind" "symbol")
             (cons "name" (symbol-name value))
             (cons "package" (if pkg (package-name pkg) nil))))))

  (defun %wasm-startup-truth-package-json (value)
    (let ((name (ignore-errors (package-name value))))
      (if (stringp name)
        (cons :object
              (list
               (cons "kind" "package")
               (cons "name" name)))
        nil)))

  (defun %wasm-startup-truth-normalize-list (value)
    (if (%wasm-startup-truth-keyword-plist-p value)
      (let ((pairs nil))
        (do ((rest value (cddr rest)))
            ((null rest))
          (push (cons (%wasm-startup-truth-json-key (car rest))
                      (%wasm-startup-truth-normalize-value (cadr rest)))
                pairs))
        (cons :object (nreverse pairs)))
      (let ((items nil))
        (do ((rest value (cdr rest)))
            ((null rest))
          (push (%wasm-startup-truth-normalize-value (car rest)) items))
        (cons :array (nreverse items)))))

  (defun %wasm-startup-truth-normalize-vector (value)
    (let ((items nil))
      (dotimes (i (length value))
        (push (%wasm-startup-truth-normalize-value (aref value i)) items))
      (cons :array (nreverse items))))

  (defun %wasm-startup-truth-normalize-value (value)
    (cond
      ((and (consp value) (eq (car value) :object)) value)
      ((and (consp value) (eq (car value) :array)) value)
      ((stringp value) value)
      ((integerp value) value)
      ((floatp value) value)
      ((eq value t) :json-true)
      ((null value) nil)
      ((symbolp value)
       (if (keywordp value)
         (string-downcase (symbol-name value))
         (%wasm-startup-truth-symbol-json value)))
      ((vectorp value)
       (%wasm-startup-truth-normalize-vector value))
      ((listp value)
       (%wasm-startup-truth-normalize-list value))
      (t
       (or (%wasm-startup-truth-package-json value)
           (princ-to-string value)))))

  (defun %wasm-startup-truth-plist->json-object (payload)
    (let ((pairs nil))
      (do ((rest payload (cddr rest)))
          ((null rest))
        (push (cons (%wasm-startup-truth-json-key (car rest))
                    (%wasm-startup-truth-normalize-value (cadr rest)))
              pairs))
      (cons :object (nreverse pairs))))

  (defun %wasm-startup-truth-phase-string (value)
    (cond
      ((stringp value) value)
      ((symbolp value) (string-downcase (symbol-name value)))
      ((integerp value)
       (case value
         (0 "early")
         (1 "l0-ready")
         (2 "runtime")
         (t (format nil "phase-~d" value))))
      (t "unknown")))

  (defun %wasm-startup-truth-next-seq ()
    (prog1 *wasm-startup-truth-seq*
      (setq *wasm-startup-truth-seq* (1+ *wasm-startup-truth-seq*))))

  (defun %wasm-startup-truth-write-record (record)
    (let ((sink *wasm-startup-truth-sink*))
      (when (streamp sink)
        (%wasm-startup-truth-json-write-value sink record)
        (terpri sink)
        (finish-output sink)
        (when *wasm-startup-truth-stdout-mirror*
          (%wasm-startup-truth-json-write-value *standard-output* record)
          (terpri *standard-output*)
          (finish-output *standard-output*))
        t)))

  (defun %wasm-startup-truth-emit-event-internal (event-type payload phase)
    (let ((record
           (cons :object
                 (list
                  (cons "schema_version" *wasm-startup-truth-schema-version*)
                  (cons "event_type"
                        (string-downcase
                         (if (stringp event-type)
                           event-type
                           (symbol-name event-type))))
                  (cons "phase" (%wasm-startup-truth-phase-string phase))
                  (cons "monotonic_seq" (%wasm-startup-truth-next-seq))
                  (cons "payload" payload)))))
      (%wasm-startup-truth-write-record record)))

  (defun %wasm-startup-truth-open-sink-if-needed ()
    (when (and *wasm-startup-truth-enabled*
               (not (streamp *wasm-startup-truth-sink*))
               (stringp *wasm-startup-truth-path*)
               (> (length *wasm-startup-truth-path*) 0))
      (ignore-errors
        (setf *wasm-startup-truth-sink*
              (open *wasm-startup-truth-path*
                    :direction :output
                    :if-exists :supersede
                    :if-does-not-exist :create
                    :element-type 'character)
              *wasm-startup-truth-seq* 0)))
    (streamp *wasm-startup-truth-sink*))

  (defun %wasm-startup-truth-ensure-ready ()
    (when (%wasm-startup-truth-open-sink-if-needed)
      (unless *wasm-startup-truth-session-start-emitted*
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           "session-start"
           (%wasm-startup-truth-plist->json-object
            (list :output_path *wasm-startup-truth-path*))
           "collect-start")
          (setf *wasm-startup-truth-session-start-emitted* t)))
      t))

  (defun wasm-startup-truth-close-sink ()
    (when (streamp *wasm-startup-truth-sink*)
      (ignore-errors
        (finish-output *wasm-startup-truth-sink*)
        (close *wasm-startup-truth-sink*)))
    (setf *wasm-startup-truth-sink* nil)
    t)

  (defun %wasm-startup-truth-remove-plist-key (plist key)
    (let ((out nil))
      (do ((rest plist (cddr rest)))
          ((null rest) (nreverse out))
        (unless (eq (car rest) key)
          (push (cadr rest) out)
          (push (car rest) out)))))

  (defun %wasm-startup-truth-note-event (event-type &rest payload)
    (let* ((phase (or (getf payload :phase) "unknown"))
           (payload-no-phase (%wasm-startup-truth-remove-plist-key payload :phase)))
      (when (%wasm-startup-truth-ensure-ready)
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           event-type
           (%wasm-startup-truth-plist->json-object payload-no-phase)
           phase))))
    nil)

  (defun %wasm-startup-truth-intern-status-name (status-code)
    (case status-code
      (0 "none")
      (1 "ok")
      (2 "arg-invalid")
      (3 "intern-unavailable")
      (4 "name-alloc-failed")
      (5 "throw")
      (6 "result-non-symbol")
      (7 "existing-symbol")
      (8 "symbol-missing")
      (9 "symbol-synthesized")
      (t "unknown")))

  (defun %wasm-startup-truth-intern-event (resolved-symbol package intern-name intern-status-code phase-code)
    (let ((phase (%wasm-startup-truth-phase-string phase-code)))
      (when (%wasm-startup-truth-ensure-ready)
        (ignore-errors
          (%wasm-startup-truth-emit-event-internal
           "intern"
           (%wasm-startup-truth-plist->json-object
            (list :intern_name intern-name
                  :intern_status_code intern-status-code
                  :intern_status (%wasm-startup-truth-intern-status-name intern-status-code)
                  :package package
                  :resolved_symbol resolved-symbol))
           phase)
          (when (symbolp resolved-symbol)
            (%wasm-startup-truth-emit-event-internal
             "symbol-identity-observe"
             (%wasm-startup-truth-plist->json-object
              (list :symbol resolved-symbol
                    :package package
                    :source "intern"))
             phase)))))
    nil))


(eval-when (:compile-toplevel :execute)
  (defconstant %lisp-symbols%  
    '("&ALLOW-OTHER-KEYS" 
      "&AUX" 
      "&BODY" 
      "&ENVIRONMENT" 
      "&KEY" 
      "&OPTIONAL" 
      "&REST" 
      "&WHOLE" 
      "*" 
      "**" 
      "***" 
      "*BREAK-ON-SIGNALS*" 
      "*COMPILE-FILE-PATHNAME*" 
      "*COMPILE-FILE-TRUENAME*" 
      "*COMPILE-PRINT*" 
      "*COMPILE-VERBOSE*" 
      "*DEBUG-IO*" 
      "*DEBUGGER-HOOK*" 
      "*DEFAULT-PATHNAME-DEFAULTS*" 
      "*ERROR-OUTPUT*" 
      "*FEATURES*" 
      "*GENSYM-COUNTER*" 
      "*LOAD-PATHNAME*" 
      "*LOAD-PRINT*" 
      "*LOAD-TRUENAME*" 
      "*LOAD-VERBOSE*" 
      "*MACROEXPAND-HOOK*" 
      "*MODULES*" 
      "*PACKAGE*" 
      "*PRINT-ARRAY*" 
      "*PRINT-BASE*" 
      "*PRINT-CASE*" 
      "*PRINT-CIRCLE*" 
      "*PRINT-ESCAPE*" 
      "*PRINT-GENSYM*" 
      "*PRINT-LENGTH*" 
      "*PRINT-LEVEL*" 
      "*PRINT-LINES*" 
      "*PRINT-MISER-WIDTH*" 
      "*PRINT-PPRINT-DISPATCH*" 
      "*PRINT-PRETTY*" 
      "*PRINT-RADIX*" 
      "*PRINT-READABLY*" 
      "*PRINT-RIGHT-MARGIN*" 
      "*QUERY-IO*" 
      "*RANDOM-STATE*" 
      "*READ-BASE*" 
      "*READ-DEFAULT-FLOAT-FORMAT*" 
      "*READ-EVAL*" 
      "*READ-SUPPRESS*" 
      "*READTABLE*" 
      "*STANDARD-INPUT*" 
      "*STANDARD-OUTPUT*" 
      "*TERMINAL-IO*" 
      "*TRACE-OUTPUT*" 
      "+" 
      "++" 
      "+++" 
      "-" 
      "/" 
      "//" 
      "///" 
      "/=" 
      "1+" 
      "1-" 
      "<" 
      "<=" 
      "=" 
      ">" 
      ">=" 
      "ABORT" 
      "ABS" 
      "ACONS" 
      "ACOS" 
      "ACOSH" 
      "ADD-METHOD" 
      "ADJOIN" 
      "ADJUST-ARRAY" 
      "ADJUSTABLE-ARRAY-P" 
      "ALLOCATE-INSTANCE" 
      "ALPHA-CHAR-P" 
      "ALPHANUMERICP" 
      "AND" 
      "APPEND" 
      "APPLY" 
      "APROPOS" 
      "APROPOS-LIST" 
      "AREF" 
      "ARITHMETIC-ERROR" 
      "ARITHMETIC-ERROR-OPERANDS" 
      "ARITHMETIC-ERROR-OPERATION" 
      "ARRAY" 
      "ARRAY-DIMENSION" 
      "ARRAY-DIMENSION-LIMIT" 
      "ARRAY-DIMENSIONS" 
      "ARRAY-DISPLACEMENT" 
      "ARRAY-ELEMENT-TYPE" 
      "ARRAY-HAS-FILL-POINTER-P" 
      "ARRAY-IN-BOUNDS-P" 
      "ARRAY-RANK" 
      "ARRAY-RANK-LIMIT" 
      "ARRAY-ROW-MAJOR-INDEX" 
      "ARRAY-TOTAL-SIZE" 
      "ARRAY-TOTAL-SIZE-LIMIT" 
      "ARRAYP" 
      "ASH" 
      "ASIN" 
      "ASINH" 
      "ASSERT" 
      "ASSOC" 
      "ASSOC-IF" 
      "ASSOC-IF-NOT" 
      "ATAN" 
      "ATANH" 
      "ATOM" 
      "BASE-CHAR" 
      "BASE-STRING" 
      "BIGNUM" 
      "BIT" 
      "BIT-AND" 
      "BIT-ANDC1" 
      "BIT-ANDC2" 
      "BIT-EQV" 
      "BIT-IOR" 
      "BIT-NAND" 
      "BIT-NOR" 
      "BIT-NOT" 
      "BIT-ORC1" 
      "BIT-ORC2" 
      "BIT-VECTOR" 
      "BIT-VECTOR-P" 
      "BIT-XOR" 
      "BLOCK" 
      "BOOLE" 
      "BOOLE-1" 
      "BOOLE-2" 
      "BOOLE-AND" 
      "BOOLE-ANDC1" 
      "BOOLE-ANDC2" 
      "BOOLE-C1" 
      "BOOLE-C2" 
      "BOOLE-CLR" 
      "BOOLE-EQV" 
      "BOOLE-IOR" 
      "BOOLE-NAND" 
      "BOOLE-NOR" 
      "BOOLE-ORC1" 
      "BOOLE-ORC2" 
      "BOOLE-SET" 
      "BOOLE-XOR" 
      "BOOLEAN" 
      "BOTH-CASE-P" 
      "BOUNDP" 
      "BREAK" 
      "BROADCAST-STREAM" 
      "BROADCAST-STREAM-STREAMS" 
      "BUILT-IN-CLASS" 
      "BUTLAST" 
      "BYTE" 
      "BYTE-POSITION" 
      "BYTE-SIZE" 
      "CAAAAR" 
      "CAAADR" 
      "CAAAR" 
      "CAADAR" 
      "CAADDR" 
      "CAADR" 
      "CAAR" 
      "CADAAR" 
      "CADADR" 
      "CADAR" 
      "CADDAR" 
      "CADDDR" 
      "CADDR" 
      "CADR" 
      "CALL-ARGUMENTS-LIMIT" 
      "CALL-METHOD" 
      "CALL-NEXT-METHOD" 
      "CAR" 
      "CASE" 
      "CATCH" 
      "CCASE" 
      "CDAAAR" 
      "CDAADR" 
      "CDAAR" 
      "CDADAR" 
      "CDADDR" 
      "CDADR" 
      "CDAR" 
      "CDDAAR" 
      "CDDADR" 
      "CDDAR" 
      "CDDDAR" 
      "CDDDDR" 
      "CDDDR" 
      "CDDR" 
      "CDR" 
      "CEILING" 
      "CELL-ERROR" 
      "CELL-ERROR-NAME" 
      "CERROR" 
      "CHANGE-CLASS" 
      "CHAR" 
      "CHAR-CODE" 
      "CHAR-CODE-LIMIT" 
      "CHAR-DOWNCASE" 
      "CHAR-EQUAL" 
      "CHAR-GREATERP" 
      "CHAR-INT" 
      "CHAR-LESSP" 
      "CHAR-NAME" 
      "CHAR-NOT-EQUAL" 
      "CHAR-NOT-GREATERP" 
      "CHAR-NOT-LESSP" 
      "CHAR-UPCASE" 
      "CHAR/=" 
      "CHAR<" 
      "CHAR<=" 
      "CHAR=" 
      "CHAR>" 
      "CHAR>=" 
      "CHARACTER" 
      "CHARACTERP" 
      "CHECK-TYPE" 
      "CIS" 
      "CLASS" 
      "CLASS-NAME" 
      "CLASS-OF" 
      "CLEAR-INPUT" 
      "CLEAR-OUTPUT" 
      "CLOSE" 
      "CLRHASH" 
      "CODE-CHAR" 
      "COERCE" 
      "COMPILATION-SPEED" 
      "COMPILE" 
      "COMPILE-FILE" 
      "COMPILE-FILE-PATHNAME" 
      "COMPILED-FUNCTION" 
      "COMPILED-FUNCTION-P" 
      "COMPILER-MACRO" 
      "COMPILER-MACRO-FUNCTION" 
      "COMPLEMENT" 
      "COMPLEX" 
      "COMPLEXP" 
      "COMPUTE-APPLICABLE-METHODS" 
      "COMPUTE-RESTARTS" 
      "CONCATENATE" 
      "CONCATENATED-STREAM" 
      "CONCATENATED-STREAM-STREAMS" 
      "COND" 
      "CONDITION" 
      "CONJUGATE" 
      "CONS" 
      "CONSP" 
      "CONSTANTLY" 
      "CONSTANTP" 
      "CONTINUE" 
      "CONTROL-ERROR" 
      "COPY-ALIST" 
      "COPY-LIST" 
      "COPY-PPRINT-DISPATCH" 
      "COPY-READTABLE" 
      "COPY-SEQ" 
      "COPY-STRUCTURE" 
      "COPY-SYMBOL" 
      "COPY-TREE" 
      "COS" 
      "COSH" 
      "COUNT" 
      "COUNT-IF" 
      "COUNT-IF-NOT" 
      "CTYPECASE" 
      "DEBUG" 
      "DECF" 
      "DECLAIM" 
      "DECLARATION" 
      "DECLARE" 
      "DECODE-FLOAT" 
      "DECODE-UNIVERSAL-TIME" 
      "DEFCLASS" 
      "DEFCONSTANT" 
      "DEFGENERIC" 
      "DEFINE-COMPILER-MACRO" 
      "DEFINE-CONDITION" 
      "DEFINE-METHOD-COMBINATION" 
      "DEFINE-MODIFY-MACRO" 
      "DEFINE-SETF-EXPANDER" 
      "DEFINE-SYMBOL-MACRO" 
      "DEFMACRO" 
      "DEFMETHOD" 
      "DEFPACKAGE" 
      "DEFPARAMETER" 
      "DEFSETF" 
      "DEFSTRUCT" 
      "DEFTYPE" 
      "DEFUN" 
      "DEFVAR" 
      "DELETE" 
      "DELETE-DUPLICATES" 
      "DELETE-FILE" 
      "DELETE-IF" 
      "DELETE-IF-NOT" 
      "DELETE-PACKAGE" 
      "DENOMINATOR" 
      "DEPOSIT-FIELD" 
      "DESCRIBE" 
      "DESCRIBE-OBJECT" 
      "DESTRUCTURING-BIND" 
      "DIGIT-CHAR" 
      "DIGIT-CHAR-P" 
      "DIRECTORY" 
      "DIRECTORY-NAMESTRING" 
      "DISASSEMBLE" 
      "DIVISION-BY-ZERO" 
      "DO" 
      "DO*" 
      "DO-ALL-SYMBOLS" 
      "DO-EXTERNAL-SYMBOLS" 
      "DO-SYMBOLS" 
      "DOCUMENTATION" 
      "DOLIST" 
      "DOTIMES" 
      "DOUBLE-FLOAT" 
      "DOUBLE-FLOAT-EPSILON" 
      "DOUBLE-FLOAT-NEGATIVE-EPSILON" 
      "DPB" 
      "DRIBBLE" 
      "DYNAMIC-EXTENT" 
      "ECASE" 
      "ECHO-STREAM" 
      "ECHO-STREAM-INPUT-STREAM" 
      "ECHO-STREAM-OUTPUT-STREAM" 
      "ED" 
      "EIGHTH" 
      "ELT" 
      "ENCODE-UNIVERSAL-TIME" 
      "END-OF-FILE" 
      "ENDP" 
      "ENOUGH-NAMESTRING" 
      "ENSURE-DIRECTORIES-EXIST" 
      "ENSURE-GENERIC-FUNCTION" 
      "EQ" 
      "EQL" 
      "EQUAL" 
      "EQUALP" 
      "ERROR" 
      "ETYPECASE" 
      "EVAL" 
      "EVAL-WHEN" 
      "EVENP" 
      "EVERY" 
      "EXP" 
      "EXPORT" 
      "EXPT" 
      "EXTENDED-CHAR" 
      "FBOUNDP" 
      "FCEILING" 
      "FDEFINITION" 
      "FFLOOR" 
      "FIFTH" 
      "FILE-AUTHOR" 
      "FILE-ERROR" 
      "FILE-ERROR-PATHNAME" 
      "FILE-LENGTH" 
      "FILE-NAMESTRING" 
      "FILE-POSITION" 
      "FILE-STREAM" 
      "FILE-STRING-LENGTH" 
      "FILE-WRITE-DATE" 
      "FILL" 
      "FILL-POINTER" 
      "FIND" 
      "FIND-ALL-SYMBOLS" 
      "FIND-CLASS" 
      "FIND-IF" 
      "FIND-IF-NOT" 
      "FIND-METHOD" 
      "FIND-PACKAGE" 
      "FIND-RESTART" 
      "FIND-SYMBOL" 
      "FINISH-OUTPUT" 
      "FIRST" 
      "FIXNUM" 
      "FLET" 
      "FLOAT" 
      "FLOAT-DIGITS" 
      "FLOAT-PRECISION" 
      "FLOAT-RADIX" 
      "FLOAT-SIGN" 
      "FLOATING-POINT-INEXACT" 
      "FLOATING-POINT-INVALID-OPERATION" 
      "FLOATING-POINT-OVERFLOW" 
      "FLOATING-POINT-UNDERFLOW" 
      "FLOATP" 
      "FLOOR" 
      "FMAKUNBOUND" 
      "FORCE-OUTPUT" 
      "FORMAT" 
      "FORMATTER" 
      "FOURTH" 
      "FRESH-LINE" 
      "FROUND" 
      "FTRUNCATE" 
      "FTYPE" 
      "FUNCALL" 
      "FUNCTION" 
      "FUNCTION-KEYWORDS" 
      "FUNCTION-LAMBDA-EXPRESSION" 
      "FUNCTIONP" 
      "GCD" 
      "GENERIC-FUNCTION" 
      "GENSYM" 
      "GENTEMP" 
      "GET" 
      "GET-DECODED-TIME" 
      "GET-DISPATCH-MACRO-CHARACTER" 
      "GET-INTERNAL-REAL-TIME" 
      "GET-INTERNAL-RUN-TIME" 
      "GET-MACRO-CHARACTER" 
      "GET-OUTPUT-STREAM-STRING" 
      "GET-PROPERTIES" 
      "GET-SETF-EXPANSION" 
      "GET-UNIVERSAL-TIME" 
      "GETF" 
      "GETHASH" 
      "GO" 
      "GRAPHIC-CHAR-P" 
      "HANDLER-BIND" 
      "HANDLER-CASE" 
      "HASH-TABLE" 
      "HASH-TABLE-COUNT" 
      "HASH-TABLE-P" 
      "HASH-TABLE-REHASH-SIZE" 
      "HASH-TABLE-REHASH-THRESHOLD" 
      "HASH-TABLE-SIZE" 
      "HASH-TABLE-TEST" 
      "HOST-NAMESTRING" 
      "IDENTITY" 
      "IF" 
      "IGNORABLE" 
      "IGNORE" 
      "IGNORE-ERRORS" 
      "IMAGPART" 
      "IMPORT" 
      "IN-PACKAGE" 
      "INCF" 
      "INITIALIZE-INSTANCE" 
      "INLINE" 
      "INPUT-STREAM-P" 
      "INSPECT" 
      "INTEGER" 
      "INTEGER-DECODE-FLOAT" 
      "INTEGER-LENGTH" 
      "INTEGERP" 
      "INTERACTIVE-STREAM-P" 
      "INTERN" 
      "INTERNAL-TIME-UNITS-PER-SECOND" 
      "INTERSECTION" 
      "INVALID-METHOD-ERROR" 
      "INVOKE-DEBUGGER" 
      "INVOKE-RESTART" 
      "INVOKE-RESTART-INTERACTIVELY" 
      "ISQRT" 
      "KEYWORD" 
      "KEYWORDP" 
      "LABELS" 
      "LAMBDA" 
      "LAMBDA-LIST-KEYWORDS" 
      "LAMBDA-PARAMETERS-LIMIT" 
      "LAST" 
      "LCM" 
      "LDB" 
      "LDB-TEST" 
      "LDIFF" 
      "LEAST-NEGATIVE-DOUBLE-FLOAT" 
      "LEAST-NEGATIVE-LONG-FLOAT" 
      "LEAST-NEGATIVE-NORMALIZED-DOUBLE-FLOAT" 
      "LEAST-NEGATIVE-NORMALIZED-LONG-FLOAT" 
      "LEAST-NEGATIVE-NORMALIZED-SHORT-FLOAT" 
      "LEAST-NEGATIVE-NORMALIZED-SINGLE-FLOAT" 
      "LEAST-NEGATIVE-SHORT-FLOAT" 
      "LEAST-NEGATIVE-SINGLE-FLOAT" 
      "LEAST-POSITIVE-DOUBLE-FLOAT" 
      "LEAST-POSITIVE-LONG-FLOAT" 
      "LEAST-POSITIVE-NORMALIZED-DOUBLE-FLOAT" 
      "LEAST-POSITIVE-NORMALIZED-LONG-FLOAT" 
      "LEAST-POSITIVE-NORMALIZED-SHORT-FLOAT" 
      "LEAST-POSITIVE-NORMALIZED-SINGLE-FLOAT" 
      "LEAST-POSITIVE-SHORT-FLOAT" 
      "LEAST-POSITIVE-SINGLE-FLOAT" 
      "LENGTH" 
      "LET" 
      "LET*" 
      "LISP-IMPLEMENTATION-TYPE" 
      "LISP-IMPLEMENTATION-VERSION" 
      "LIST" 
      "LIST*" 
      "LIST-ALL-PACKAGES" 
      "LIST-LENGTH" 
      "LISTEN" 
      "LISTP" 
      "LOAD" 
      "LOAD-LOGICAL-PATHNAME-TRANSLATIONS" 
      "LOAD-TIME-VALUE" 
      "LOCALLY" 
      "LOG" 
      "LOGAND" 
      "LOGANDC1" 
      "LOGANDC2" 
      "LOGBITP" 
      "LOGCOUNT" 
      "LOGEQV" 
      "LOGICAL-PATHNAME" 
      "LOGICAL-PATHNAME-TRANSLATIONS" 
      "LOGIOR" 
      "LOGNAND" 
      "LOGNOR" 
      "LOGNOT" 
      "LOGORC1" 
      "LOGORC2" 
      "LOGTEST" 
      "LOGXOR" 
      "LONG-FLOAT" 
      "LONG-FLOAT-EPSILON" 
      "LONG-FLOAT-NEGATIVE-EPSILON" 
      "LONG-SITE-NAME" 
      "LOOP" 
      "LOOP-FINISH" 
      "LOWER-CASE-P" 
      "MACHINE-INSTANCE" 
      "MACHINE-TYPE" 
      "MACHINE-VERSION" 
      "MACRO-FUNCTION" 
      "MACROEXPAND" 
      "MACROEXPAND-1" 
      "MACROLET" 
      "MAKE-ARRAY" 
      "MAKE-BROADCAST-STREAM" 
      "MAKE-CONCATENATED-STREAM" 
      "MAKE-CONDITION" 
      "MAKE-DISPATCH-MACRO-CHARACTER" 
      "MAKE-ECHO-STREAM" 
      "MAKE-HASH-TABLE" 
      "MAKE-INSTANCE" 
      "MAKE-INSTANCES-OBSOLETE" 
      "MAKE-LIST" 
      "MAKE-LOAD-FORM" 
      "MAKE-LOAD-FORM-SAVING-SLOTS" 
      "MAKE-METHOD" 
      "MAKE-PACKAGE" 
      "MAKE-PATHNAME" 
      "MAKE-RANDOM-STATE" 
      "MAKE-SEQUENCE" 
      "MAKE-STRING" 
      "MAKE-STRING-INPUT-STREAM" 
      "MAKE-STRING-OUTPUT-STREAM" 
      "MAKE-SYMBOL" 
      "MAKE-SYNONYM-STREAM" 
      "MAKE-TWO-WAY-STREAM" 
      "MAKUNBOUND" 
      "MAP" 
      "MAP-INTO" 
      "MAPC" 
      "MAPCAN" 
      "MAPCAR" 
      "MAPCON" 
      "MAPHASH" 
      "MAPL" 
      "MAPLIST" 
      "MASK-FIELD" 
      "MAX" 
      "MEMBER" 
      "MEMBER-IF" 
      "MEMBER-IF-NOT" 
      "MERGE" 
      "MERGE-PATHNAMES" 
      "METHOD" 
      "METHOD-COMBINATION" 
      "METHOD-COMBINATION-ERROR" 
      "METHOD-QUALIFIERS" 
      "MIN" 
      "MINUSP" 
      "MISMATCH" 
      "MOD" 
      "MOST-NEGATIVE-DOUBLE-FLOAT" 
      "MOST-NEGATIVE-FIXNUM" 
      "MOST-NEGATIVE-LONG-FLOAT" 
      "MOST-NEGATIVE-SHORT-FLOAT" 
      "MOST-NEGATIVE-SINGLE-FLOAT" 
      "MOST-POSITIVE-DOUBLE-FLOAT" 
      "MOST-POSITIVE-FIXNUM" 
      "MOST-POSITIVE-LONG-FLOAT" 
      "MOST-POSITIVE-SHORT-FLOAT" 
      "MOST-POSITIVE-SINGLE-FLOAT" 
      "MUFFLE-WARNING" 
      "MULTIPLE-VALUE-BIND" 
      "MULTIPLE-VALUE-CALL" 
      "MULTIPLE-VALUE-LIST" 
      "MULTIPLE-VALUE-PROG1" 
      "MULTIPLE-VALUE-SETQ" 
      "MULTIPLE-VALUES-LIMIT" 
      "NAME-CHAR" 
      "NAMESTRING" 
      "NBUTLAST" 
      "NCONC" 
      "NEXT-METHOD-P" 
      "NIL" 
      "NINTERSECTION" 
      "NINTH" 
      "NO-APPLICABLE-METHOD" 
      "NO-NEXT-METHOD" 
      "NOT" 
      "NOTANY" 
      "NOTEVERY" 
      "NOTINLINE" 
      "NRECONC" 
      "NREVERSE" 
      "NSET-DIFFERENCE" 
      "NSET-EXCLUSIVE-OR" 
      "NSTRING-CAPITALIZE" 
      "NSTRING-DOWNCASE" 
      "NSTRING-UPCASE" 
      "NSUBLIS" 
      "NSUBST" 
      "NSUBST-IF" 
      "NSUBST-IF-NOT" 
      "NSUBSTITUTE" 
      "NSUBSTITUTE-IF" 
      "NSUBSTITUTE-IF-NOT" 
      "NTH" 
      "NTH-VALUE" 
      "NTHCDR" 
      "NULL" 
      "NUMBER" 
      "NUMBERP" 
      "NUMERATOR" 
      "NUNION" 
      "ODDP" 
      "OPEN" 
      "OPEN-STREAM-P" 
      "OPTIMIZE" 
      "OR" 
      "OTHERWISE" 
      "OUTPUT-STREAM-P" 
      "PACKAGE" 
      "PACKAGE-ERROR" 
      "PACKAGE-ERROR-PACKAGE" 
      "PACKAGE-NAME" 
      "PACKAGE-NICKNAMES" 
      "PACKAGE-SHADOWING-SYMBOLS" 
      "PACKAGE-USE-LIST" 
      "PACKAGE-USED-BY-LIST" 
      "PACKAGEP" 
      "PAIRLIS" 
      "PARSE-ERROR" 
      "PARSE-INTEGER" 
      "PARSE-NAMESTRING" 
      "PATHNAME" 
      "PATHNAME-DEVICE" 
      "PATHNAME-DIRECTORY" 
      "PATHNAME-HOST" 
      "PATHNAME-MATCH-P" 
      "PATHNAME-NAME" 
      "PATHNAME-TYPE" 
      "PATHNAME-VERSION" 
      "PATHNAMEP" 
      "PEEK-CHAR" 
      "PHASE" 
      "PI" 
      "PLUSP" 
      "POP" 
      "POSITION" 
      "POSITION-IF" 
      "POSITION-IF-NOT" 
      "PPRINT" 
      "PPRINT-DISPATCH" 
      "PPRINT-EXIT-IF-LIST-EXHAUSTED" 
      "PPRINT-FILL" 
      "PPRINT-INDENT" 
      "PPRINT-LINEAR" 
      "PPRINT-LOGICAL-BLOCK" 
      "PPRINT-NEWLINE" 
      "PPRINT-POP" 
      "PPRINT-TAB" 
      "PPRINT-TABULAR" 
      "PRIN1" 
      "PRIN1-TO-STRING" 
      "PRINC" 
      "PRINC-TO-STRING" 
      "PRINT" 
      "PRINT-NOT-READABLE" 
      "PRINT-NOT-READABLE-OBJECT" 
      "PRINT-OBJECT" 
      "PRINT-UNREADABLE-OBJECT" 
      "PROBE-FILE" 
      "PROCLAIM" 
      "PROG" 
      "PROG*" 
      "PROG1" 
      "PROG2" 
      "PROGN" 
      "PROGRAM-ERROR" 
      "PROGV" 
      "PROVIDE" 
      "PSETF" 
      "PSETQ" 
      "PUSH" 
      "PUSHNEW" 
      "QUOTE" 
      "RANDOM" 
      "RANDOM-STATE" 
      "RANDOM-STATE-P" 
      "RASSOC" 
      "RASSOC-IF" 
      "RASSOC-IF-NOT" 
      "RATIO" 
      "RATIONAL" 
      "RATIONALIZE" 
      "RATIONALP" 
      "READ" 
      "READ-BYTE" 
      "READ-CHAR" 
      "READ-CHAR-NO-HANG" 
      "READ-DELIMITED-LIST" 
      "READ-FROM-STRING" 
      "READ-LINE" 
      "READ-PRESERVING-WHITESPACE" 
      "READ-SEQUENCE" 
      "READER-ERROR" 
      "READTABLE" 
      "READTABLE-CASE" 
      "READTABLEP" 
      "REAL" 
      "REALP" 
      "REALPART" 
      "REDUCE" 
      "REINITIALIZE-INSTANCE" 
      "REM" 
      "REMF" 
      "REMHASH" 
      "REMOVE" 
      "REMOVE-DUPLICATES" 
      "REMOVE-IF" 
      "REMOVE-IF-NOT" 
      "REMOVE-METHOD" 
      "REMPROP" 
      "RENAME-FILE" 
      "RENAME-PACKAGE" 
      "REPLACE" 
      "REQUIRE" 
      "REST" 
      "RESTART" 
      "RESTART-BIND" 
      "RESTART-CASE" 
      "RESTART-NAME" 
      "RETURN" 
      "RETURN-FROM" 
      "REVAPPEND" 
      "REVERSE" 
      "ROOM" 
      "ROTATEF" 
      "ROUND" 
      "ROW-MAJOR-AREF" 
      "RPLACA" 
      "RPLACD" 
      "SAFETY" 
      "SATISFIES" 
      "SBIT" 
      "SCALE-FLOAT" 
      "SCHAR" 
      "SEARCH" 
      "SECOND" 
      "SEQUENCE" 
      "SERIOUS-CONDITION" 
      "SET" 
      "SET-DIFFERENCE" 
      "SET-DISPATCH-MACRO-CHARACTER" 
      "SET-EXCLUSIVE-OR" 
      "SET-MACRO-CHARACTER" 
      "SET-PPRINT-DISPATCH" 
      "SET-SYNTAX-FROM-CHAR" 
      "SETF" 
      "SETQ" 
      "SEVENTH" 
      "SHADOW" 
      "SHADOWING-IMPORT" 
      "SHARED-INITIALIZE" 
      "SHIFTF" 
      "SHORT-FLOAT" 
      "SHORT-FLOAT-EPSILON" 
      "SHORT-FLOAT-NEGATIVE-EPSILON" 
      "SHORT-SITE-NAME" 
      "SIGNAL" 
      "SIGNED-BYTE" 
      "SIGNUM" 
      "SIMPLE-ARRAY" 
      "SIMPLE-BASE-STRING" 
      "SIMPLE-BIT-VECTOR" 
      "SIMPLE-BIT-VECTOR-P" 
      "SIMPLE-CONDITION" 
      "SIMPLE-CONDITION-FORMAT-ARGUMENTS" 
      "SIMPLE-CONDITION-FORMAT-CONTROL" 
      "SIMPLE-ERROR" 
      "SIMPLE-STRING" 
      "SIMPLE-STRING-P" 
      "SIMPLE-TYPE-ERROR" 
      "SIMPLE-VECTOR" 
      "SIMPLE-VECTOR-P" 
      "SIMPLE-WARNING" 
      "SIN" 
      "SINGLE-FLOAT" 
      "SINGLE-FLOAT-EPSILON" 
      "SINGLE-FLOAT-NEGATIVE-EPSILON" 
      "SINH" 
      "SIXTH" 
      "SLEEP" 
      "SLOT-BOUNDP" 
      "SLOT-EXISTS-P" 
      "SLOT-MAKUNBOUND" 
      "SLOT-MISSING" 
      "SLOT-UNBOUND" 
      "SLOT-VALUE" 
      "SOFTWARE-TYPE" 
      "SOFTWARE-VERSION" 
      "SOME" 
      "SORT" 
      "SPACE" 
      "SPECIAL" 
      "SPECIAL-OPERATOR-P" 
      "SPEED" 
      "SQRT" 
      "STABLE-SORT" 
      "STANDARD" 
      "STANDARD-CHAR" 
      "STANDARD-CHAR-P" 
      "STANDARD-CLASS" 
      "STANDARD-GENERIC-FUNCTION" 
      "STANDARD-METHOD" 
      "STANDARD-OBJECT" 
      "STEP" 
      "STORAGE-CONDITION" 
      "STORE-VALUE" 
      "STREAM" 
      "STREAM-ELEMENT-TYPE" 
      "STREAM-ERROR" 
      "STREAM-ERROR-STREAM" 
      "STREAM-EXTERNAL-FORMAT" 
      "STREAMP" 
      "STRING" 
      "STRING-CAPITALIZE" 
      "STRING-DOWNCASE" 
      "STRING-EQUAL" 
      "STRING-GREATERP" 
      "STRING-LEFT-TRIM" 
      "STRING-LESSP" 
      "STRING-NOT-EQUAL" 
      "STRING-NOT-GREATERP" 
      "STRING-NOT-LESSP" 
      "STRING-RIGHT-TRIM" 
      "STRING-STREAM" 
      "STRING-TRIM" 
      "STRING-UPCASE" 
      "STRING/=" 
      "STRING<" 
      "STRING<=" 
      "STRING=" 
      "STRING>" 
      "STRING>=" 
      "STRINGP" 
      "STRUCTURE" 
      "STRUCTURE-CLASS" 
      "STRUCTURE-OBJECT" 
      "STYLE-WARNING" 
      "SUBLIS" 
      "SUBSEQ" 
      "SUBSETP" 
      "SUBST" 
      "SUBST-IF" 
      "SUBST-IF-NOT" 
      "SUBSTITUTE" 
      "SUBSTITUTE-IF" 
      "SUBSTITUTE-IF-NOT" 
      "SUBTYPEP" 
      "SVREF" 
      "SXHASH" 
      "SYMBOL" 
      "SYMBOL-FUNCTION" 
      "SYMBOL-MACROLET" 
      "SYMBOL-NAME" 
      "SYMBOL-PACKAGE" 
      "SYMBOL-PLIST" 
      "SYMBOL-VALUE" 
      "SYMBOLP" 
      "SYNONYM-STREAM" 
      "SYNONYM-STREAM-SYMBOL" 
      "T" 
      "TAGBODY" 
      "TAILP" 
      "TAN" 
      "TANH" 
      "TENTH" 
      "TERPRI" 
      "THE" 
      "THIRD" 
      "THROW" 
      "TIME" 
      "TRACE" 
      "TRANSLATE-LOGICAL-PATHNAME" 
      "TRANSLATE-PATHNAME" 
      "TREE-EQUAL" 
      "TRUENAME" 
      "TRUNCATE" 
      "TWO-WAY-STREAM" 
      "TWO-WAY-STREAM-INPUT-STREAM" 
      "TWO-WAY-STREAM-OUTPUT-STREAM" 
      "TYPE" 
      "TYPE-ERROR" 
      "TYPE-ERROR-DATUM" 
      "TYPE-ERROR-EXPECTED-TYPE" 
      "TYPE-OF" 
      "TYPECASE" 
      "TYPEP" 
      "UNBOUND-SLOT" 
      "UNBOUND-SLOT-INSTANCE" 
      "UNBOUND-VARIABLE" 
      "UNDEFINED-FUNCTION" 
      "UNEXPORT" 
      "UNINTERN" 
      "UNION" 
      "UNLESS" 
      "UNREAD-CHAR" 
      "UNSIGNED-BYTE" 
      "UNTRACE" 
      "UNUSE-PACKAGE" 
      "UNWIND-PROTECT" 
      "UPDATE-INSTANCE-FOR-DIFFERENT-CLASS" 
      "UPDATE-INSTANCE-FOR-REDEFINED-CLASS" 
      "UPGRADED-ARRAY-ELEMENT-TYPE" 
      "UPGRADED-COMPLEX-PART-TYPE" 
      "UPPER-CASE-P" 
      "USE-PACKAGE" 
      "USE-VALUE" 
      "USER-HOMEDIR-PATHNAME" 
      "VALUES" 
      "VALUES-LIST" 
      "VARIABLE" 
      "VECTOR" 
      "VECTOR-POP" 
      "VECTOR-PUSH" 
      "VECTOR-PUSH-EXTEND" 
      "VECTORP" 
      "WARN" 
      "WARNING" 
      "WHEN" 
      "WILD-PATHNAME-P" 
      "WITH-ACCESSORS" 
      "WITH-COMPILATION-UNIT" 
      "WITH-CONDITION-RESTARTS" 
      "WITH-HASH-TABLE-ITERATOR" 
      "WITH-INPUT-FROM-STRING" 
      "WITH-OPEN-FILE" 
      "WITH-OPEN-STREAM" 
      "WITH-OUTPUT-TO-STRING" 
      "WITH-PACKAGE-ITERATOR" 
      "WITH-SIMPLE-RESTART" 
      "WITH-SLOTS" 
      "WITH-STANDARD-IO-SYNTAX" 
      "WRITE" 
      "WRITE-BYTE" 
      "WRITE-CHAR" 
      "WRITE-LINE" 
      "WRITE-SEQUENCE" 
      "WRITE-STRING" 
      "WRITE-TO-STRING" 
      "Y-OR-N-P" 
      "YES-OR-NO-P" 
      "ZEROP"
      )
    ))

(let* ((pkg *common-lisp-package*)
       (etab (pkg.etab pkg))
       (itab (pkg.itab pkg)))
  (without-interrupts
   (dolist (name '#.%lisp-symbols%)
     (let* ((namelen (length name)))
       (multiple-value-bind (found-int symbol int-offset)
                            (%get-htab-symbol name namelen itab)
         (multiple-value-bind (found-ext ignore ext-offset)
                              (%get-htab-symbol name namelen etab)
           (declare (ignore ignore))
           (if found-int                ; This shouldn't happen.
             (progn
               (setf (%svref (car itab) int-offset) (%unbound-marker-8))
               (%htab-add-symbol symbol etab ext-offset))
             (unless found-ext
               (let ((added-symbol (%add-symbol name pkg int-offset ext-offset t)))
                 (when (fboundp '%wasm-startup-truth-note-event)
                   (ignore-errors
                     (%wasm-startup-truth-note-event
                      "symbol-identity-observe"
                      :phase "l1-cl-package-bootstrap"
                      :package pkg
                      :symbol added-symbol
                      :symbol_name name
                      :visibility "external")))
                 added-symbol)))))))))
