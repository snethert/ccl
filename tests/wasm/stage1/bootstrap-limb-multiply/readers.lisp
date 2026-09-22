(in-package :ccl)

(defun multiplication-source-forms (path features)
  (let ((*features* features) (*package* (find-package :ccl)) (*read-eval* t))
    (progv '(digit-size half-digit-size) '(32 16)
    (with-open-file (stream path)
      (loop for form = (read stream nil stream)
            until (eq form stream) collect form)))))

;; The only changed reader expression mentions these two existing features
;; and WASM32-TARGET. Exhaust their truth assignments with Wasm absent. Every
;; existing target is in one of these four classes, regardless of its other
;; reader features. The entire file, not just the changed fragment, is read.
(let* ((base (set-difference *features* '(:x8632-target :arm-target :wasm32-target :32-bit-target :64-bit-target)))
       (old (getenv "MULTIPLY_OLD")) (new (getenv "MULTIPLY_NEW")))
  (with-open-file (stream (getenv "MULTIPLY_READERS") :direction :output :if-exists :error)
    (write-char #\[ stream)
    (loop for added in '((:64-bit-target) (:64-bit-target :x8632-target)
                        (:64-bit-target :arm-target) (:64-bit-target :x8632-target :arm-target)
                        (:32-bit-target) (:32-bit-target :x8632-target)
                        (:32-bit-target :arm-target) (:32-bit-target :x8632-target :arm-target))
          for i from 0 do
      (let ((before (multiplication-source-forms old (append added base)))
            (after (multiplication-source-forms new (append added base))))
        (assert (equal before after))
        (when (member :32-bit-target added) (assert (> (length before) 1)))
        (unless (zerop i) (write-char #\, stream))
        (format stream "{\"assignment\":~d,\"forms\":~d,\"equal\":true}" i (length before))))
    (write-char #\] stream)))
(quit)
