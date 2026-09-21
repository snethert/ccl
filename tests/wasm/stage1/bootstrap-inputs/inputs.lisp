(in-package :wasm32-compiler)

(defun input-structure (object)
  (setf (gethash object *witness-nodes*)
        (cons 'struct (cons (list (type-of object))
                           (loop for i from 1 below (ccl::uvsize object)
                                 collect (ccl::%svref object i)))))
  object)

(defun input-ioblock (shift sharing)
  (input-structure (ccl::make-ioblock :element-shift shift :sharing sharing)))

(defun more-inputs (name)
  (let ((s (symbol-name name)))
    (cond
      ((member s '("RECURSIVE-LOCK-PTR" "READ-WRITE-LOCK-PTR") :test #'equal)
       (values (loop for pointer in '(nil 0 7) collect
                     (list (witness-node 'lock
                             (list pointer (if (equal s "RECURSIVE-LOCK-PTR")
                                             'ccl::recursive-lock 'ccl::read-write-lock)
                                   0 "input lock" nil nil)))) t))
      ((equal s "%IOBLOCK-UNTYI")
       (values (loop for char in '(#\a #\Newline #\Null #\U+03BB) collect
                     (list (input-ioblock 0 nil) char)) t))
      ((member s '("IOBLOCK-INPOS" "IOBLOCK-OUTPOS") :test #'equal)
       (values (loop for index in '(0 1 31) collect
                     (let ((buffer (input-structure (ccl::make-io-buffer :idx index :count (+ index 4)))))
                       (list (input-structure (ccl::make-ioblock :inbuf buffer :outbuf buffer))))) t))
      ((member s '("STRING-INPUT-STREAM-IOBLOCK-READ-CHAR"
                   "STRING-INPUT-STREAM-IOBLOCK-PEEK-CHAR") :test #'equal)
       (values (loop for (text index) in '(("" 0) ("a" 0) ("a" 1) ("aλz" 1) ("aλz" 3))
                     collect (list (input-structure
                                    (ccl::make-string-input-stream-ioblock
                                     :string text :index index :end (length text))))) t))
      ((equal s "STRING-INPUT-STREAM-IOBLOCK-UNREAD-CHAR")
       (values (loop for (text index) in '(("a" 1) ("aλz" 2) ("aλz" 3))
                     collect (list (input-structure
                                    (ccl::make-string-input-stream-ioblock
                                     :string text :index index :end (length text)))
                                   (char text (1- index)))) t))
      ((equal s "%EPUSHVAL")
       (values (loop for push in '(nil t) append
                     (loop for val in '(nil 17 (1 . 2)) collect
                           (list (witness-istruct 'ccl::faslstate
                                   (list "input" (make-array 3 :initial-element nil)
                                         1 nil nil nil nil nil nil 0 0 push nil nil)) val))) t))
      ((equal s "CHEAP-CONS") (values '((nil nil) (1 (2 3)) ((1 2) :tail)) t))
      ((member s '("FREE-CONS" "CHEAP-COPY-LIST" "CHEAP-FREE-LIST") :test #'equal)
       (values '((nil) ((1)) ((1 2 3)) ((1 2 . :tail))) t))
      ((equal s "CHEAP-LIST") (values '(() (1) (1 nil :three)) t))
      ((equal s "OBJECT-IN-APPLICATION-HEAP-P") (values '((nil) (0) (7) ((1 . 2))) t))
      ((equal s "USING-LINEAR-SCAN") (values '(()) t))
      ((equal s "UCS-4-STREAM-DECODE")
       (values '((0 nil nil) (65 nil nil) (255 nil nil) (65535 nil nil)) t))
      ((member s '("LOCK-ACQUISITION-STATUS" "CLEAR-LOCK-ACQUISITION-STATUS"
                   "SEMAPHORE-NOTIFICATION-STATUS" "CLEAR-SEMAPHORE-NOTIFICATION-STATUS") :test #'equal)
       (let ((kind (if (search "SEMAPHORE" s) 'ccl::semaphore-notification 'ccl::lock-acquisition)))
         (values (loop for value in '(nil t :waiting (1 2))
                       collect (list (witness-istruct kind (list value)))) t)))
      ((member s '("IOBLOCK-OCTETS-TO-ELEMENTS" "IOBLOCK-ELEMENTS-TO-OCTETS") :test #'equal)
       (values (loop for shift in '(0 1 2 3) append
                    (loop for n in '(0 1 7 8 65) collect
                          (list (input-ioblock shift nil) n))) t))
      ((member s '("INSTALL-IOBLOCK-INPUT-LINE-TERMINATION"
                   "INSTALL-IOBLOCK-OUTPUT-LINE-TERMINATION") :test #'equal)
       (values (loop for sharing in '(nil :private :lock) append
                    (loop for mode in '(nil :cr :crlf :unicode)
                          collect (list (input-ioblock 0 sharing) mode))) t))
      ((equal s "COERCE-TO-VALUES")
       (values (list (list (witness-istruct 'ccl::values-ctype '(nil nil (integer) nil t nil nil nil)))
                     (list (witness-istruct 'ccl::named-ctype '(nil nil integer)))) t))
      ((equal s "MAKE-INTERSECTION-CTYPE")
       (values '((nil nil) (t (integer symbol))) t))
      ((equal s "NUMERIC-TYPES-ADJACENT")
       (values (loop for (low high) in '((nil 3) (3 nil) (3 4) (3 5) ((3) 3) (3 (3)))
                     collect (list (witness-istruct 'ccl::numeric-ctype (list nil nil 'integer nil nil nil low nil))
                                   (witness-istruct 'ccl::numeric-ctype (list nil nil 'integer nil nil high nil nil)))) t))
      ((member s '("EVENT-TICKS" "FIND-NAMED-PERIODIC-TASK") :test #'equal)
       (values (if (equal s "EVENT-TICKS") '(()) '((:first) (:second) (:missing))) t))
      ((equal s "SET-EVENT-TICKS") (values '((0) (1) (32767)) t))
      (t (values nil nil)))))

(defun more-environment (name)
  (let ((s (symbol-name name)))
    (cond
      ((member s '("CHEAP-CONS" "FREE-CONS" "CHEAP-COPY-LIST" "CHEAP-LIST" "CHEAP-FREE-LIST") :test #'equal)
       (list (cons 'ccl::*cons-pool* (witness-node 'pool (list '(nil nil nil nil))))))
      ((equal s "USING-LINEAR-SCAN") '((ccl::*backend-use-linear-scan* . t)))
      ((member s '("COERCE-TO-VALUES" "MAKE-INTERSECTION-CTYPE") :test #'equal)
       '((ccl::*type-classes* . ((values . :values) (intersection . :intersection)))))
      ((member s '("EVENT-TICKS" "SET-EVENT-TICKS" "FIND-NAMED-PERIODIC-TASK") :test #'equal)
       (let* ((first (witness-istruct 'ccl::periodic-task
                      (list (witness-istruct 'ccl::ptaskstate '(0 7 nil 0)) :first nil)))
              (second (witness-istruct 'ccl::periodic-task
                       (list (witness-istruct 'ccl::ptaskstate '(0 9 nil 0)) :second nil))))
         (if (equal s "FIND-NAMED-PERIODIC-TASK")
           (list (cons 'ccl::*%periodic-tasks%* (list first second)))
           (list (cons 'ccl::*event-dispatch-task* first))))))))
