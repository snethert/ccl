(in-package "CCL")
(eval-when (:compile-toplevel :execute)
  (require "FASLENV" "ccl:xdump;faslenv"))

;;; The native oracle and target use their own input-buffer representations.
;;; Every parser and opcode below is the original nfasload definition.
(defun loader-fasl-position (s)
  (declare (ignore s))
  0)

(defun loader-fasl-eof (s)
  (declare (ignore s))
  (error "End of fixture input."))

(defmacro loader-with-fasl-input ((s bytes) &body body)
  `(let* ((octets ,bytes)
          (*fasl-api* (%istruct 'faslapi nil nil nil nil #'loader-fasl-position
                               #'loader-fasl-eof #'%simple-fasl-read-byte
                               #'%simple-fasl-read-n-bytes))
          (,s (%istruct 'faslstate nil nil 0 nil nil nil nil nil nil 0 0 nil nil nil)))
     (loader-with-buffer (buffer (+ target::node-size (length octets)))
       #-wasm32-target
       (setf (%get-ptr buffer) (%inc-ptr buffer target::node-size))
       (dotimes (i (length octets))
         (%set-unsigned-byte buffer (+ target::node-size i) (svref octets i)))
       (setf (faslstate.bufcount ,s) (length octets)
             (faslstate.fasldispatch ,s) *fasl-dispatch-table*
             (faslstate.faslfname ,s) "fixture"
             (faslstate.iobuffer ,s)
             #-wasm32-target buffer
             #+wasm32-target (vector buffer target::node-size))
       ,@body)))

(defun loader-fasl-word (word)
  (%word-to-int word))

(defun loader-fasl-numbers ()
  (loader-with-fasl-input (s (vector 0 0 127 255 128 0 255 255
                                   128 0 0 0 255 255 255 255 127 255 255 255))
    (values (%fasl-read-word s) (%fasl-read-word s) (%fasl-read-word s)
            (%fasl-read-word s) (%fasl-read-signed-long s)
            (%fasl-read-signed-long s) (%fasl-read-long s)
            (faslstate.bufcount s))))

(defun loader-fasl-counts ()
  (loader-with-fasl-input (s (vector 128 255 0 129 127 255 0 0 129 0 0 0 0 130))
    (values (%fasl-read-count s) (%fasl-read-count s) (%fasl-read-count s)
            (%fasl-read-count s) (%fasl-read-count s) (%fasl-read-count s)
            (faslstate.bufcount s))))

(defun loader-fasl-copy ()
  (loader-with-fasl-input (s (vector 1 2 128 255 9))
    (let ((out (make-array 8 :element-type '(unsigned-byte 8) :initial-element 17)))
      (%simple-fasl-read-n-bytes s out 2 0)
      (%simple-fasl-read-n-bytes s out 2 3)
      (%simple-fasl-read-n-bytes s out 5 2)
      (values (aref out 0) (aref out 1) (aref out 2) (aref out 3)
              (aref out 4) (aref out 5) (aref out 6) (aref out 7)
              (faslstate.bufcount s)))))

(defun loader-fasl-utf8 (kind)
  (let* ((bytes (case kind
                  (0 (vector 65 66 67))
                  (1 (vector 195 169 206 187 230 188 162))
                  (2 (vector 65 240 159 152 128 90))
                  (t (vector 192 65 255))))
         (text (make-string 3)))
    (loader-with-fasl-input (s bytes)
      (%fasl-read-utf-8-string s text 3 (- (length bytes) 3))
      (values text (faslstate.bufcount s)))))

(defun loader-fasl-list ()
  (loader-with-fasl-input (s (vector $fasl-vlist 130
                                   $fasl-word-fixnum 0 23
                                   $fasl-word-fixnum 255 255
                                   $fasl-nil))
    (values (%fasl-expr s) (faslstate.bufcount s))))

(defun loader-fasl-epush ()
  (loader-with-fasl-input (s (vector $fasl-vetab-alloc 132
                                   #.(fasl-epush-op $fasl-cons)
                                   $fasl-word-fixnum 0 42 $fasl-nil
                                   $fasl-veref 128))
    (%fasl-expr s)
    (let ((value (%fasl-expr s)))
      (values value (eq value (%fasl-expr s)) (faslstate.faslecnt s)
              (faslstate.bufcount s)))))

(defun loader-fasl-refusals (kind)
  (handler-case
      (loader-with-fasl-input (s (case kind
                                  (0 (vector 127))
                                  (1 (vector $fasl-veref 128))
                                  (t (vector))))
        (%fasl-expr s)
        nil)
    (error () t)))

(defvar *loader-fasl-cleanup* 0)
(defun loader-fasl-native-code (opcode)
  (unwind-protect
       (loader-with-fasl-input (s (vector opcode))
         (%fasl-expr s))
    (incf *loader-fasl-cleanup*)))

(defun loader-fasl-immediate (kind)
  (let* ((value (case kind (0 (%unbound-marker)) (1 (%slot-unbound-marker))
                          (2 (%illegal-marker)) (t #\Z)))
         (word #-wasm32-target (%address-of value)
               #+wasm32-target (case kind (0 target::unbound-marker)
                                         (1 target::slot-unbound-marker)
                                         (2 target::illegal-marker)
                                         (t (+ (ash 90 8) target::subtag-character)))))
    (loader-with-fasl-input (s (vector $fasl-timm (ldb (byte 8 24) word)
                                     (ldb (byte 8 16) word) (ldb (byte 8 8) word)
                                     (ldb (byte 8 0) word)))
      (values (eq (%fasl-expr s) value) (faslstate.bufcount s)))))

(defvar *loader-fasl-state* nil)
(defvar *loader-fasl-destination* nil)
(defun loader-fasl-hold ()
  #+wasm32-target
  (progn
    (setq *loader-fasl-destination* (make-array 8 :element-type '(unsigned-byte 8)
                                                :initial-element 17)
          *loader-fasl-state* (%istruct 'faslstate nil nil 0 nil nil nil nil nil
                                       (vector (make-array 8 :element-type '(unsigned-byte 8)) 0)
                                       8 0 nil nil nil)))
  t)
