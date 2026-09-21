(in-package :wasm32-compiler)

(defun core-inputs (name)
  (let ((s (symbol-name name)))
    (cond
      ((equal s "SYMBOL-NAME") (values '((nil) (t) (:library-test) (library-test-symbol)) t))
      ((equal s "SYMBOL-PLIST") (values '((library-test-symbol)) t))
      ((equal s "GET") (values '((library-test-symbol :absent) (library-test-symbol :absent 7)) t))
      ((equal s "PUT") (values '((library-put-symbol :key (1 . 2))) t))
      ((member s '("NEED-CHAR-CODE" "UTF-16-CHARACTER-SIZE-IN-OCTETS") :test #'equal)
       (values '((#\Null) (#\A) (#\u+1000) (#\u+1f601)) t))
      ((equal s "REQUIRE-NUMARG") (values '((#\A 1) (#\B 0)) t))
      ((equal s "REQUIRE-NO-NUMARG") (values '((#\A nil)) t))
      ((equal s "CORE-ILOGNOT") (values '((0) (-1) (7) (-536870912) (536870911)) t))
      ((equal s "CORE-FIXNUM-LESS") (values '((-1 0) (0 -1) (1 1) (-536870912 536870911)) t))
      ((equal s "%COPY-U8-TO-STRING")
       (values (list (list (make-array 4 :element-type '(unsigned-byte 8) :initial-contents '(0 65 128 255)) 0 (copy-seq "....") 0 4)) t))
      ((equal s "%COPY-STRING-TO-U8")
       (values (list (list "Aλ😁" 0 (make-array 4 :element-type '(unsigned-byte 8) :initial-element 99) 1 3)) t))
      ((member s '("CORE-FORMAT-ERROR" "CORE-FORMAT-SIGNAL" "CORE-FORMAT-COLLECT" "CORE-TYPE-ERROR" "CORE-FORMAT-ORDER" "CORE-FORMAT-DECLINE" "CORE-SIMPLE-INITARGS") :test #'equal)
       (values '((nil) ((1 . 2)) (7) ("string")) t))
      ((equal s "CORE-DYNAMIC-FORMAT") (values '(("one ~s" (1 . 2)) ("two ~a" 7)) t))
      ((equal s "CORE-SCHAR") (values '(("abc" 0) ("abc" 2) ("λ😁" 1)) t))
      ((equal s "CORE-SET-CHAR") (values '(("abc" 0 #\Z) ("λ😁" 1 #\A)) t))
      ((equal s "CORE-CHAR-CODE") (values '((#\Null) (#\A) (#\u+1000) (#\u+1f601)) t))
      ((equal s "CORE-CODE-CHAR") (values '((0) (65) (55295) (55296) (57343) (57344) (128513) (1114111)) t))
      ((member s '("CORE-GVECTOR" "CORE-STRUCT" "CORE-SLOT" "CORE-CLEANUP" "CORE-TRANSFER") :test #'equal)
       (values '(((1 . 2)) ((3 4))) t))
      ((equal s "CORE-REF") (values '((#((1 . 2) (3 . 4)))) t))
      ((equal s "CORE-SET") (values '((#((1 . 2) 7) (3 . 4))) t))
      ((member s '("FUNCTIONP" "LFUNP") :test #'equal)
       (values (list (list nil) (list 7) (list #'car) (list '(1 2))) t))
      ;; Symbols have a dedicated tag on x86-64, but are node vectors on D1.
      ;; Compare representation predicates only on their shared domain here.
      ((member s '("GVECTORP" "MISCOBJP" "UVECTORP" "IVECTORP") :test #'equal)
       (values '((nil) (0) (-1) ((1 . 2)) (#\A) ("abc") (#(1 2)) (#*101)) t))
      ((member s '("SYMBOLP" "SYMBOL-ARG-P" "NON-NIL-SYMBOL-P" "NON-NIL-SYMBOLP"
                   "CONSP" "LISTP" "ARRAYP" "VECTORP" "SEQUENCEP" "ATOM"
                   "FIXNUMP" "BIGNUMP" "INTEGERP" "RATIOP" "RATIONALP" "REALP" "NUMBERP"
                   "SHORT-FLOAT-P" "DOUBLE-FLOAT-P" "FLOATP" "COMPLEXP"
                   "COMPLEX-SINGLE-FLOAT-P" "COMPLEX-DOUBLE-FLOAT-P"
                   "SIMPLE-BASE-STRING-P" "SIMPLE-STRING-P" "SIMPLE-VECTOR-P" "SIMPLE-BIT-VECTOR-P"
                   "CHARACTERP" "BASE-CHAR-P" "EXTENDED-CHAR-P" "PACKAGEP" "STRUCTUREP"
                   "ISTRUCTP" "ISTRUCT-TYPE-NAME" "BASIC-STREAM-P" "STANDARD-INSTANCE-P"
                   "MACPTRP" "DEAD-MACPTR-P" "GVECTORP" "IVECTORP" "MISCOBJP" "UVECTORP"
                   "FUNCTIONP" "LFUNP" "BITP" "UNSIGNED-BYTE-P"
                   "UNSIGNED-BYTE-8-P" "SIGNED-BYTE-8-P" "UNSIGNED-BYTE-16-P" "SIGNED-BYTE-16-P"
                   "UNSIGNED-BYTE-32-P" "SIGNED-BYTE-32-P" "QUOTED-FORM-P" "LAMBDA-EXPRESSION-P")
               :test #'equal)
       (values (mapcar (lambda (x) (if (equal s "SYMBOL-ARG-P") (list x t) (list x)))
                       '(nil t 0 1 -1 127 128 255 256 32767 65536 -536870912 536870911
                         1208925819614629174706176 -1208925819614629174706176
                         1/3 -5/7 #c(1/3 2/3) 0.0s0 -1.5s0 0.0d0 3.25d0 :test (1 . 2) (1 2 3) #\A #\u+1000 "abc" #(1 2) #*101)) t))
      ((member s '("%REQUIRE-TYPE-BUILTIN" "%REQUIRE-TYPE-CLASS-CELL" "STRUCTURE-TYPEP" "ISTRUCT-TYPEP") :test #'equal)
       (values '((nil nil) (7 :type) (:test :type) ((1 2) :type)) t))
      ((member s '("EQ" "MAX-2" "MIN-2" "%IMAX" "%IMIN" "/=-2" ">=-2" "<=-2") :test #'equal)
       (values (append '((1 1) (-7 3) (9 4) (0 -1))
                       (unless (member s '("EQ" "%IMAX" "%IMIN") :test #'equal)
                         '((1.5d0 2.5d0) (-3.0s0 1) (1208925819614629174706176 7)))) t))
      ((member s '("CAR" "CDR" "CAAR" "CADR" "CDAR" "CDDR" "CAAAR" "CAADR" "CADAR" "CADDR" "CDAAR" "CDADR" "CDDAR" "CDDDR") :test #'equal)
       (values '((nil) ((((1 . 2) . (3 . 4)) . ((5 . 6) . (7 . 8))))) t))
      ((member s '("COPY-TREE" "IDENTITY") :test #'equal)
       (values '((nil) (7) ((1 (2 . 3) 4))) t))
      ((member s '("MEMQ" "ADJOIN-EQ" "CPL-MEMQ") :test #'equal)
       (values '((1 nil) (1 (1 2)) (2 (1 2 3)) (4 (1 2))) t))
      ((member s '("MEMEQL" "ADJOIN-EQL") :test #'equal)
       (values '((1 nil) (2 (1 2 3)) (1/3 (2/3 1/3)) (#\A (#\B #\A))
                 (1152921504606846976 (1 1152921504606846976))) t))
      ((equal s "%PL-SEARCH") (values '(((1 2 3 4) 1) ((1 2 3 4) 3) ((1 2) 7) (nil 1)) t))
      ((member s '("APPEND-2" "UNION-EQ" "NRECONC") :test #'equal)
       (values '((nil nil) ((1 2) nil) (nil (3 4)) ((1 2) (3 4))) t))
      ((equal s "APPEND") (values '(nil ((1 2)) ((1 2) (3 4) (5 6))) t))
      ((equal s "LIST") (values '(nil (1) (1 2 3)) t))
      ((equal s "LIST*") (values '((nil) (1 2) (1 2 (3 4))) t))
      ((member s '("LIST-REVERSE" "LIST-NREVERSE" "FINAL-CONS") :test #'equal)
       (values '((nil) ((1)) ((1 2 3))) t))
      ((equal s "NREMOVE") (values '((1 (1 2 1 3)) (7 (1 2 3))) t))
      ((equal s "REMOVE-FROM-ALIST") (values '((1 ((1 . 2) (3 . 4))) (7 ((1 . 2)))) t))
      ((equal s "HEAP-AREA-NAME") (values (loop for n from 0 to 12 collect (list n)) t))
      ((equal s "FIND-BUILTIN-CELL") (values '((integer) (:absent) (nil t)) t))
      ((equal s "INDEX->VECTOR-INDEX") (values '((0) (1) (7)) t))
      ((member s '("%SIMPLE-FASL-INIT-BUFFER" "CHARACTER-ENCODED-IN-SINGLE-OCTET"
                   "TWO-OCTETS-PER-CHARACTER" "FOUR-OCTETS-PER-CHARACTER") :test #'equal)
       (values '((nil) (#\A) (#\u+1000)) t))
      ((member s '("8-BIT-FIXED-WIDTH-OCTETS-IN-STRING" "UCS-2-OCTETS-IN-STRING" "UCS-4-OCTETS-IN-STRING"
                   "8-BIT-FIXED-WIDTH-LENGTH-OF-VECTOR-ENCODING" "8-BIT-FIXED-WIDTH-LENGTH-OF-MEMORY-ENCODING") :test #'equal)
       (values '((nil 1 8) (nil 7 3) (nil 3 3)) t))
      ((member s '("DEF-INFO.LFBITS" "DEF-INFO.KEYVECT" "DEF-INFO.FILE" "DEF-INFO.METHODS" "DEF-INFO.MACRO-P"
                   "DEF-INFO.FUNCTION-P" "DEF-INFO.DEFTYPE" "DEF-INFO.DEFTYPE-TYPE") :test #'equal)
       (values '((nil) (#(12 :key :file (:methods 1 2))) (#((12 . :source) :key :file (ccl::macro)))) t))
      ((equal s "DEF-INFO-METHOD.KEYVECT") (values '(((((:a :b) . :file))) (((7 . :file)))) t))
      ((equal s "DEF-INFO-METHOD.FILE") (values '((((7 . :file))) (((nil . :other)))) t))
      ((equal s "BOOTSTRAPPING-RECORD-SOURCE-FILE") (values '((nil) (7 nil)) t))
      ((equal s "SLOT-ID-LOOKUP-NO-SLOTS") (values '((nil nil) (7 :test)) t))
      ((equal s "%TYPE-ERROR-TYPE") (values '((:test) ((integer 0 7))) t))
      ((equal s "%MAKE-RATIO") (values '((1 3) (-5 7)) t))
      ((equal s "%MAKE-COMPLEX") (values '((1 3) (-5 7)) t))
      ((member s '("DEFAULT-PRINT-LEVEL" "DEFAULT-PRINT-LENGTH" "DEFAULT-PRINT-STRING-LENGTH") :test #'equal)
       (values '((:default) (nil) (7)) t))
      ((member s '("LOADING-FILE-SOURCE-FILE"
                   "PRELOAD-ALL-FUNCTIONS" "LISP-IMPLEMENTATION-TYPE") :test #'equal)
       (values '(nil) t))
      (t (values nil nil)))))
