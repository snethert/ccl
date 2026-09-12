;;; Observation-only architecture subset. No native target is copied or modified.
(defpackage "WASM-CENSUS" (:use "CL"))
(defpackage "WASM-CENSUS-OS" (:use "CL"))
(in-package "WASM-CENSUS")
(eval-when (:compile-toplevel :load-toplevel :execute)
  ;; D1's specified data-layout subset, independently checked by the host oracle.
  (defconstant nbits-in-word 32)
  (defconstant node-size 4)
  (defconstant fixnumshift 2)
  (defconstant fulltag-cons 1)
  (defconstant fulltag-misc 6)
  (defconstant ntagbits 3)
  (defconstant nlisptagbits 2))
(defvar *census-arch*
  (arch::make-target-arch
   :name :wasm32-census :package-name "WASM-CENSUS"
   :nbits-in-word nbits-in-word :lisp-node-size node-size :word-shift 2
   :fixnum-shift fixnumshift :most-positive-fixnum (1- (ash 1 29))
   :most-negative-fixnum (- (ash 1 29)) :ntagbits ntagbits :nlisptagbits nlisptagbits
   :cons-tag fulltag-cons :fulltag-misc fulltag-misc :fulltagmask 7
   :fixnum-tag 0 :big-endian nil :uvector-subtags nil
   :car-offset 3 :cdr-offset -1 :misc-data-offset -2))
(provide "WASM-CENSUS-ARCH")
