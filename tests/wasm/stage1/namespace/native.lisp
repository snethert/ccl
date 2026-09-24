(in-package :ccl)

(defvar *namespace-root* (getenv "NAMESPACE_ROOT"))
(defvar *namespace-handles* (make-hash-table :test 'equal))

(defun namespace-native-path (path)
  (concatenate 'string *namespace-root*
               (if (eql (char path 0) #\/) "" "/ccl/") path))

(defun namespace-virtual-path (path)
  (let* ((name (namestring path))
         (relative (subseq name (length *namespace-root*))))
    (if (and (> (length relative) 1)
             (eql (char relative (1- (length relative))) #\/))
      (subseq relative 0 (1- (length relative)))
      relative)))

(defun namespace-native-stat (path)
  (let* ((true (truename (namespace-native-path path)))
         (name (namestring true))
         (directory (eql (char name (1- (length name))) #\/)))
    (vector (namespace-virtual-path true)
            (if directory "directory" "file")
            (if directory 0
              (with-open-file (stream true :element-type '(unsigned-byte 8))
                (file-length stream))))))

(defun namespace-native-bytes (stream count)
  (let* ((bytes (make-array count :element-type '(unsigned-byte 8)))
         (end (read-sequence bytes stream)))
    (subseq bytes 0 end)))

(defun namespace-native-request (request)
  (destructuring-bind (operation &rest args) request
    (let* ((op (intern (string-upcase operation) :keyword))
           (first (car args))
           (handle (gethash first *namespace-handles*)))
      (case op
        (:stat (namespace-native-stat first))
        (:realpath
         (let ((path (%realpath (namespace-native-path first))))
           (unless (and path (probe-file path)) (error "Missing path"))
           (namespace-virtual-path path)))
        (:open
         (setf (gethash first *namespace-handles*)
               (cons (open (namespace-native-path (cadr args))
                           :direction :input :element-type '(unsigned-byte 8))
                     (cadr args)))
         t)
        (:fstat (namespace-native-stat (cdr handle)))
        (:read (namespace-native-bytes (car handle) (cadr args)))
        (:pread
         (destructuring-bind (name offset count) args
           (declare (ignore name))
           (let* ((stream (car handle)) (position (file-position stream)))
             (unwind-protect
                  (progn (file-position stream offset)
                         (namespace-native-bytes stream count))
               (file-position stream position)))))
        (:seek
         (destructuring-bind (name offset origin) args
           (declare (ignore name))
           (let* ((stream (car handle))
                  (position (+ offset
                               (cond ((equal origin "set") 0)
                                     ((equal origin "cur") (file-position stream))
                                     ((equal origin "end") (file-length stream))))))
             (unless (and (>= position 0) (file-position stream position))
               (error "Invalid position"))
             (file-position stream))))
        (:close (close (car handle)) (remhash first *namespace-handles*) t)
        (:opendir
         (let* ((directory (truename (namespace-native-path (cadr args))))
                (paths (directory (merge-pathnames "*.*" directory)))
                (names (mapcar (lambda (p)
                                 (let ((name (namespace-virtual-path p)))
                                   (subseq name (1+ (position #\/ name :from-end t)))))
                               paths)))
           (setf (gethash first *namespace-handles*) (sort names #'string<))
           t))
        (:readdir
         (prog1 (car handle) (setf (gethash first *namespace-handles*) (cdr handle))))
        (:closedir (remhash first *namespace-handles*) t)
        (t (error "Unknown request ~s" request))))))

(defun namespace-json (value stream)
  (cond ((null value) (write-string "null" stream))
        ((eq value t) (write-string "true" stream))
        ((stringp value)
         (write-char #\" stream)
         (loop for char across value
               for code = (char-code char)
               do (case char
                    (#\" (write-string "\\\"" stream))
                    (#\\ (write-string "\\\\" stream))
                    (t (if (< code 32)
                         (format stream "\\u~4,'0x" code)
                         (write-char char stream)))))
         (write-char #\" stream))
        ((vectorp value)
         (write-char #\[ stream)
         (dotimes (i (length value))
           (unless (zerop i) (write-char #\, stream))
           (namespace-json (aref value i) stream))
         (write-char #\] stream))
        ((integerp value) (format stream "~d" value))
        (t (error "Unencodable result ~s" value))))

(let* ((requests (with-open-file (stream (getenv "NAMESPACE_REQUESTS")) (read stream)))
       (rows (make-array (length requests))))
  (loop for request in requests
        for index from 0
        do (setf (aref rows index)
                 (vector index (handler-case (namespace-native-request request)
                                 (error () "error")))))
  (with-open-file (stream (getenv "NAMESPACE_RESULTS") :direction :output
                          :if-exists :supersede :external-format :utf-8)
    (namespace-json rows stream)
    (terpri stream)))
