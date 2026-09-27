;;; Synchronous host character output for the single-Worker READY profile.
(in-package "CCL")

(defclass wasm-output-stream (fundamental-character-output-stream)
  ((channel :initarg :channel :reader wasm-output-channel)
   (column :initform 0 :accessor stream-line-column)
   (open-p :initform t :accessor open-stream-p)))

(defmethod stream-write-string ((stream wasm-output-stream) string
                               &optional (start 0) end)
  (unless (open-stream-p stream)
    (error 'stream-is-closed-error :stream stream))
  (let ((text (ensure-simple-string (subseq string start end))))
    (%wasm-process-request 7 (wasm-output-channel stream) text)
    (loop for char across text
          do (setf (stream-line-column stream)
                   (case char
                     ((#\Newline #\Return) 0)
                     (#\Tab (+ (stream-line-column stream)
                               (- 8 (mod (stream-line-column stream) 8))))
                     (t (1+ (stream-line-column stream)))))))
  string)

(defmethod stream-write-char ((stream wasm-output-stream) char)
  (stream-write-string stream (make-string 1 :initial-element char))
  char)

(defmethod close ((stream wasm-output-stream) &key abort)
  (declare (ignore abort))
  (setf (open-stream-p stream) nil)
  t)

;; Writes complete synchronously. The inherited FORCE-/FINISH-/CLEAR-OUTPUT
;; methods have no pending buffer to process. Input is an ordinary EOF stream;
;; interactive input and the listener are outside this startup profile.
(defparameter *stdin* (make-string-input-stream ""))
(defparameter *stdout* (make-instance 'wasm-output-stream :channel 1))
(defparameter *stderr* (make-instance 'wasm-output-stream :channel 2))
(defparameter *terminal-input* *stdin*)
(defparameter *terminal-output* *stdout*)
(setq *standard-input* *stdin*
      *standard-output* *stdout*
      *error-output* *stderr*
      *trace-output* *stdout*
      *terminal-io* (make-two-way-stream *stdin* *stdout*)
      *query-io* *terminal-io*
      *debug-io* *terminal-io*)
