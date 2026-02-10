;;; -*- Mode:Lisp; Package:CCL; -*-
;;;
;;; Minimal WASM32 environment.
;;;
;;; Keep a transition-compatible register layout, but avoid direct
;;; dependency on ARMENV symbols in this module.

(in-package "CCL")

(defconstant $numwasmsaveregs 0)
(defconstant $numwasmargregs 3)

;; Register indexes used by the wasm32 runtime ABI.
;; These values intentionally mirror the historical ordering so
;; existing backend assumptions remain stable during migration.
(defconstant wasm-reg-imm0 0)
(defconstant wasm-reg-imm1 1)
(defconstant wasm-reg-imm2 2)
(defconstant wasm-reg-rcontext 3)
(defconstant wasm-reg-arg-z 4)
(defconstant wasm-reg-arg-y 5)
(defconstant wasm-reg-arg-x 6)
(defconstant wasm-reg-temp0 7)
(defconstant wasm-reg-temp1 8)
(defconstant wasm-reg-temp2 9)

(defconstant wasm-regclass-immediate :immediate)
(defconstant wasm-regclass-context :context)
(defconstant wasm-regclass-argument :argument)
(defconstant wasm-regclass-temporary :temporary)

(defconstant wasm-register-class-map
  (vector wasm-regclass-immediate
          wasm-regclass-immediate
          wasm-regclass-immediate
          wasm-regclass-context
          wasm-regclass-argument
          wasm-regclass-argument
          wasm-regclass-argument
          wasm-regclass-temporary
          wasm-regclass-temporary
          wasm-regclass-temporary))

(defun wasm-register-class (reg-index)
  (if (and (typep reg-index 'fixnum)
           (>= reg-index 0)
           (< reg-index (length wasm-register-class-map)))
    (svref wasm-register-class-map reg-index)
    (error "Unknown WASM register index: ~s" reg-index)))

(defconstant wasm-nonvolatile-registers-mask
  0)

(defconstant wasm-arg-registers-mask
  (logior (ash 1 wasm-reg-arg-z)
          (ash 1 wasm-reg-arg-y)
          (ash 1 wasm-reg-arg-x)))

(defconstant wasm-temp-registers-mask
  (logior (ash 1 wasm-reg-temp0)
          (ash 1 wasm-reg-temp1)
          (ash 1 wasm-reg-temp2)))

(defconstant wasm-tagged-registers-mask
  (logior wasm-temp-registers-mask
          wasm-arg-registers-mask
          wasm-nonvolatile-registers-mask))

(defconstant wasm-temp-node-regs
  (make-mask wasm-reg-temp0
             wasm-reg-temp1
             wasm-reg-temp2
             wasm-reg-arg-x
             wasm-reg-arg-y
             wasm-reg-arg-z))

(defconstant wasm-nonvolatile-node-regs
  0)

(defconstant wasm-node-regs (logior wasm-temp-node-regs wasm-nonvolatile-node-regs))

(defconstant wasm-imm-regs (make-mask
                             wasm-reg-imm0
                             wasm-reg-imm1
                             wasm-reg-imm2))

(defconstant wasm-temp-fp-regs (1- (ash 1 28)))

(defconstant wasm-cr-fields (make-mask 0))

(defconstant $undo-wasm-c-frame 16)

(ccl::provide "WASMENV")
