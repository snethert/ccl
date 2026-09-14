;;; Loaded only after the original observer's initial inventory has completed.
(defpackage :ccl-resident-bodies (:use :cl)
  (:import-from :ccl-startup-census #:object)
  (:import-from :ccl-rich-census #:write-json #:source-description))
(in-package :ccl-resident-bodies)

(defun payload-hex (fn words)
  ;; Same copy primitive and boundary as U1 %COPY-FUNCTION. Include the node
  ;; suffix too, so the file oracle can reject changes to immediate operands.
  (let* ((size (* 8 words)) (bytes (make-array size :element-type '(unsigned-byte 8)))
         (hex (make-string (* 2 size))) (digits "0123456789abcdef"))
    (ccl::%copy-ivector-to-ivector (ccl::%function-to-function-vector fn) 0 bytes 0 size)
    (dotimes (i size hex)
      (setf (char hex (* 2 i)) (char digits (ash (aref bytes i) -4))
            (char hex (1+ (* 2 i))) (char digits (logand (aref bytes i) 15))))))

(defun export-image (requests output)
  (when ccl::*startup-census-hook* (error "RESIDENT-HOOK-ACTIVE"))
  (let ((wanted (with-open-file (s requests) (let ((*read-eval* nil)) (read s))))
        (functions nil) (rows nil) (ordinal 0))
    (unless (and (listp wanted) (every (lambda (n) (and (integerp n) (> n 0))) wanted))
      (error "RESIDENT-REQUESTS"))
    (ccl::%map-areas
     (lambda (obj)
       (when (= (ccl::typecode obj) target::subtag-function)
         (push (ccl::lfun-vector-lfun obj) functions))) :readonly)
    (dolist (fn functions)
      ;; Do not allocate a replacement ID when the initial inventory lacked it.
      (let* ((id (gethash fn ccl-startup-census::*dependency-identities*))
             (code (gethash (ccl::closure-function fn) ccl-startup-census::*dependency-identities*))
             (words (ccl::uvsize (ccl::%function-to-function-vector fn)))
             (ncode (ccl::%function-code-words fn))
             (selected (member code wanted)) (note (ccl:function-source-note fn)))
        (unless (and id code (= id code) (<= 1 ncode (- words 2)))
          (error "RESIDENT-PROTOTYPE-IDENTITY"))
        (push (object "ordinal" (prog1 ordinal (incf ordinal)) "id" id "code" code
                      "address" (ccl::%address-of fn) "total_words" words "code_words" ncode
                      "description" (source-description fn)
                      "source_end" (or (and note (ccl:source-note-end-pos note)) :null)
                      "selected" (if selected :true :false)
                      "payload_hex" (if selected (payload-hex fn words) :null)) rows)))
    (with-open-file (s output :direction :output :if-exists :error :external-format :utf-8)
      (write-json (object "version" 1 "area" "readonly" "functions" (nreverse rows)) s)
      (terpri s))
    (format t "RESIDENT-BODIES-PASS functions=~d selected=~d~%" ordinal
            (count-if (lambda (fn) (member (gethash fn ccl-startup-census::*dependency-identities*) wanted)) functions))))
