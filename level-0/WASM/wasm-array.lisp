;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 array operations.
;;; On ARM these are LAP functions; on WASM they are pure Lisp using
;;; uvref/uvsize and compiler intrinsics.

(in-package "CCL")

;;; Extract the underlying data vector and cumulative displacement
;;; from an array header.  An array-header has a data-vector slot
;;; (cell 2) and a displacement slot (cell 3).  Chase through any
;;; chain of displaced array headers until we reach the actual
;;; data vector.  Return (values data-vector total-offset).
(defun %array-header-data-and-offset (array)
  (let ((offset 0)
        (current array))
    (declare (fixnum offset))
    (loop
      (let* ((data (%svref current target::arrayH.data-vector-cell))
             (disp (%svref current target::arrayH.displacement-cell))
             (subtag (typecode data)))
        (setq offset (+ offset disp))
        (setq current data)
        (unless (or (= subtag target::subtag-vectorH)
                    (= subtag target::subtag-arrayH))
          (return (values current offset)))))))

;;; Initialize all slots of a miscellaneous (uvector) object to val.
;;; The ARM version dispatches on subtag and does word-level fills;
;;; the WASM version uses uvref/uvsize which the compiler handles.
(defun %init-misc (val misc)
  (dotimes (i (uvsize misc))
    (setf (uvref misc i) val))
  misc)


;;; ---------------------------------------------------------------
;;; Boole operations on bit vectors, word by word.
;;; All take (len b1 b2 dest) where len is the number of 32-bit
;;; words to process.  b1 and b2 are source bit vectors; dest
;;; is the result bit vector.  The result is dest.
;;; ---------------------------------------------------------------

(defun %boole-clr (len b1 b2 dest)
  (declare (fixnum len) (ignore b1 b2))
  (dotimes (i len)
    (setf (uvref dest i) 0))
  dest)

(defun %boole-set (len b1 b2 dest)
  (declare (fixnum len) (ignore b1 b2))
  (dotimes (i len)
    (setf (uvref dest i) #xFFFFFFFF))
  dest)

(defun %boole-1 (len b1 b2 dest)
  (declare (fixnum len) (ignore b2))
  (dotimes (i len)
    (setf (uvref dest i) (uvref b1 i)))
  dest)

(defun %boole-2 (len b1 b2 dest)
  (declare (fixnum len) (ignore b1))
  (dotimes (i len)
    (setf (uvref dest i) (uvref b2 i)))
  dest)

(defun %boole-c1 (len b1 b2 dest)
  (declare (fixnum len) (ignore b2))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF (lognot (uvref b1 i)))))
  dest)

(defun %boole-c2 (len b1 b2 dest)
  (declare (fixnum len) (ignore b1))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF (lognot (uvref b2 i)))))
  dest)

(defun %boole-and (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand (uvref b1 i) (uvref b2 i))))
  dest)

(defun %boole-ior (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logior (uvref b1 i) (uvref b2 i))))
  dest)

(defun %boole-xor (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logxor (uvref b1 i) (uvref b2 i))))
  dest)

(defun %boole-eqv (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF
                                 (lognot (logxor (uvref b1 i) (uvref b2 i))))))
  dest)

(defun %boole-nand (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF
                                 (lognot (logand (uvref b1 i) (uvref b2 i))))))
  dest)

(defun %boole-nor (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF
                                 (lognot (logior (uvref b1 i) (uvref b2 i))))))
  dest)

(defun %boole-andc1 (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand (uvref b2 i)
                                 (logand #xFFFFFFFF (lognot (uvref b1 i))))))
  dest)

(defun %boole-andc2 (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand (uvref b1 i)
                                 (logand #xFFFFFFFF (lognot (uvref b2 i))))))
  dest)

(defun %boole-orc1 (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF
                                 (logior (uvref b2 i)
                                         (logand #xFFFFFFFF (lognot (uvref b1 i)))))))
  dest)

(defun %boole-orc2 (len b1 b2 dest)
  (declare (fixnum len))
  (dotimes (i len)
    (setf (uvref dest i) (logand #xFFFFFFFF
                                 (logior (uvref b1 i)
                                         (logand #xFFFFFFFF (lognot (uvref b2 i)))))))
  dest)

;;; Dispatch table for %simple-bit-boole.
(defparameter *simple-bit-boole-functions* ())

(setq *simple-bit-boole-functions*
      (vector
       #'%boole-clr
       #'%boole-set
       #'%boole-1
       #'%boole-2
       #'%boole-c1
       #'%boole-c2
       #'%boole-and
       #'%boole-ior
       #'%boole-xor
       #'%boole-eqv
       #'%boole-nand
       #'%boole-nor
       #'%boole-andc1
       #'%boole-andc2
       #'%boole-orc1
       #'%boole-orc2))

(defun %simple-bit-boole (op b1 b2 result)
  (funcall (svref *simple-bit-boole-functions* op)
           (ash (the fixnum (+ (length result) 31)) -5)
           b1
           b2
           result))


;;; ---------------------------------------------------------------
;;; Multi-dimensional array access.
;;; On ARM these dispatch via subprims (.SParef2, .SParef3, etc.).
;;; On WASM, delegate to standard aref/aset.
;;; ---------------------------------------------------------------

(defun %aref2 (array i j)
  (aref array i j))

(defun %aref3 (array i j k)
  (aref array i j k))

(defun %aset2 (array i j newval)
  (setf (aref array i j) newval))

(defun %aset3 (array i j k newval)
  (setf (aref array i j k) newval))
