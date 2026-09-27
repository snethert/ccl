;;; Host-side bundle producer. Compile level-1 without loading its FASL into
;;; the host cross-loader. The materializer consumes these exact code records.
(in-package "WASM32-COMPILER")

(defun wasm32-bundle-json (value stream)
  (cond ((null value) (write-string "null" stream))
        ((eq value t) (write-string "true" stream))
        ((stringp value) (ccl::wasm32-json-string value stream))
        ((integerp value) (princ value stream))
        ((and (consp value) (eq (car value) :object))
         (write-char #\{ stream)
         (loop for (key . item) in (cdr value) for i from 0 do
           (unless (zerop i) (write-char #\, stream))
           (ccl::wasm32-json-string key stream)
           (write-char #\: stream)
           (wasm32-bundle-json item stream))
         (write-char #\} stream))
        ((or (vectorp value) (consp value))
         (write-char #\[ stream)
         (let ((items (if (vectorp value) (coerce value 'list)
                       (if (listp (cdr value)) value
                         (list (car value) (cdr value))))))
           (loop for item in items for i from 0 do
             (unless (zerop i) (write-char #\, stream))
             (wasm32-bundle-json item stream)))
         (write-char #\] stream))
        (t (error "Unsupported bundle metadata ~s" value))))

(defun wasm32-compile-bundle-records (source fasl records)
  (let ((*wasm32-rooted-imports* t))
   (multiple-value-bind (path modules warnings failure)
      (wasm32-compile-file source :output-file fasl)
    (when failure
      (error "Bundle compilation failed: ~s" source))
    (with-open-file (stream records :direction :output :if-exists :supersede)
      (wasm32-bundle-json
       (list :object (cons "version" 1)
             (cons "units"
                   (coerce
                    (mapcar (lambda (module)
                              (list :object
                                    (cons "name" (getf module :name))
                                    (cons "symbol_count" (getf module :fasl-symbol-count))
                                    (cons "install_record" (wasm32-install-record (getf module :fasl-code-record)))
                                    (cons "record" (getf module :fasl-code-record))))
                            modules)
                    'vector)))
       stream)
      (terpri stream))
    (values path records warnings modules))))
