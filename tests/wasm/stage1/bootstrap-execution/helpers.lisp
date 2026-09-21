(defun bootstrap-primary (code)
  (b-wat "(block (result i32) ~a (i32.load (local.get $results)))" code))
