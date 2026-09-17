(defun b-normalize-literal-apply (form)
  ;; U1's APPLY compiler macro otherwise constructs native destructuring helper
  ;; calls for literal lambdas. Preserve evaluation order via one private LET.
  ;; Validation precedes this rewrite; quoted data is never traversed.
  (if (atom form) form
    (if (eq (car form) 'quote) form
      (let ((parts (mapcar #'b-normalize-literal-apply form)))
        (if (and (eq (first parts) 'apply)
                 (let ((callee (second parts)))
                   (or (and (consp callee) (eq (car callee) 'lambda))
                       (and (consp callee) (eq (car callee) 'function) (consp (second callee)) (eq (car (second callee)) 'lambda)))))
          (let ((temp (gensym "LITERAL-APPLY-")))
            `(let ((,temp ,(second parts))) (apply ,temp ,@(cddr parts))))
          parts)))))
