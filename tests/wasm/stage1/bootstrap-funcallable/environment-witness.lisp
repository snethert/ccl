(in-package "CCL")

#-omit-file-environment
(eval-when (:compile-toplevel)
  (require "NUMBER-CASE-MACRO")
  (defmacro recount-local (x) `(%i+ ,x 4))
  (define-symbol-macro recount-word-bytes target::node-size))

(defun recount-macro (x)
  (recount-local x))

(defun recount-symbol ()
  recount-word-bytes)

(defun recount-number (x)
  (number-case x
    (fixnum :fixnum)
    (bignum :bignum)
    (t :other)))

(defun recount-empty (x)
  "The target body is deliberately absent."
  #-wasm32-target (car x))

(defun recount-self (x)
  (recount-self x))
