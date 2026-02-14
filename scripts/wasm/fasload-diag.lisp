(in-package "CCL")

(format t "~&FASLOAD-DIAG begin~%")
(multiple-value-bind (value condition)
    (ignore-errors (%fasload "level-1.lafsl"))
  (format t "~&FASLOAD-DIAG value=~S~%" value)
  (if condition
      (progn
        (format t "~&FASLOAD-DIAG condition-type=~S~%" (type-of condition))
        (format t "~&FASLOAD-DIAG condition=~A~%" condition))
      (format t "~&FASLOAD-DIAG condition=nil~%")))
(format t "~&FASLOAD-DIAG end~%")
