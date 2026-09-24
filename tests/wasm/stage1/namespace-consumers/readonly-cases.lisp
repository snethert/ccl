(in-package :wasm32-compiler)

(defun namespace-readonly-cases ()
  (list
   (namespace-file-error (lambda () (open "sub/")))
   (namespace-file-error
    (lambda () (open "a.bin" :direction :output :if-exists :overwrite)))
   (namespace-file-error
    (lambda () (open "a.bin" :direction :output :if-exists :supersede)))
   (namespace-file-error
    (lambda () (open "a.bin" :direction :io :if-exists :overwrite)))
   (namespace-file-error
    (lambda () (open "new.bin" :direction :output)))
   (namespace-file-error
    (lambda () (open "new.bin" :if-does-not-exist :create)))
   (open "a.bin" :direction :output :if-exists nil)
   (open "missing" :direction :output :if-does-not-exist nil)
   (probe-file "new.bin")
   (with-open-file (stream "a.bin" :element-type '(unsigned-byte 8))
     (let ((bytes (make-array 8 :element-type '(unsigned-byte 8))))
       (read-sequence bytes stream)
       bytes))))
