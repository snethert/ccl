(in-package :wasm32-compiler)

;;; GO uses the existing checked exit record so lexical/dynamic frames and
;;; cleanup extents retire before the next segment. A local branch alone would
;;; bypass their restoration. Program counters are untagged, never GC roots.
(defun b-tagbody (tags forms)
  (let ((pc (temporary)) (segments (list nil)) (positions nil) (index 0))
    (dolist (form forms)
      (if (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::tag-label)
        (progn (incf index) (push nil segments)
               (push (cons (first (ccl::acode-operands form)) index) positions))
        (push form (car segments))))
    (unless (every (lambda (tag) (assoc tag positions :test #'eq)) tags)
      (refuse :b-tag-identity))
    (setq segments (mapcar #'reverse (reverse segments)))
    (let ((code
           (b-exit-frame 3 "(i32.const 77825)"
             (lambda (record)
               (let ((*b-local-tags* (append (mapcar (lambda (p) (list (car p) pc (cdr p) record)) positions) *b-local-tags*)))
                 (with-output-to-string (s)
                   (loop for segment in segments for n from 0 do
                     (format s "(if (i32.le_u (local.get ~a) (i32.const ~d)) (then " pc n)
                     (dolist (form segment) (format s "(drop ~a)" (b-scalar form)))
                     (write-string "))" s))
                   (format s "(local.set ~a (i32.const -1))" pc)
                   (write-string (b-multiple (make-b-raw-code :text "(i32.const 77825)")) s)))))))
      (b-wat "(local.set ~a (i32.const 0)) (block $tagbody_done (loop $tagbody_loop ~a (br_if $tagbody_done (i32.eq (local.get ~a) (i32.const -1))) (br $tagbody_loop))) ~a"
        pc code pc (b-multiple (make-b-raw-code :text "(i32.const 77825)"))))))

(defun b-go (tag)
  (let* ((entry (or (assoc tag *b-local-tags* :test #'eq) (refuse :b-go-identity)))
         (record (fourth entry)))
    (concatenate 'string
      (b-wat "(local.set ~a (i32.const ~d)) (i32.store offset=12 ~a (i32.const 0))" (second entry) (third entry) record)
      (b-store wasm32::tcr.unwind_state "(i32.const 1)")
      (b-wat "(throw $nonlocal_exit ~a)" record))))
