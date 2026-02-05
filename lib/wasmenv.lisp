;;; -*- Mode:Lisp; Package:CCL; -*-
;;;
;;; Minimal WASM32 environment (ARM layout).

(in-package "CCL")

(require "ARMENV")

(defconstant $numwasmsaveregs 0)
(defconstant $numwasmargregs 3)

(defconstant wasm-nonvolatile-registers-mask
  0)

(defconstant wasm-arg-registers-mask
  (logior (ash 1 arm::arg_z)
          (ash 1 arm::arg_y)
          (ash 1 arm::arg_x)))

(defconstant wasm-temp-registers-mask
  (logior (ash 1 arm::temp0)
          (ash 1 arm::temp1)
          (ash 1 arm::temp2)))

(defconstant wasm-tagged-registers-mask
  (logior wasm-temp-registers-mask
          wasm-arg-registers-mask
          wasm-nonvolatile-registers-mask))

(defconstant wasm-temp-node-regs
  (make-mask arm::temp0
             arm::temp1
             arm::temp2
             arm::arg_x
             arm::arg_y
             arm::arg_z))

(defconstant wasm-nonvolatile-node-regs
  0)

(defconstant wasm-node-regs (logior wasm-temp-node-regs wasm-nonvolatile-node-regs))

(defconstant wasm-imm-regs (make-mask
                             arm::imm0
                             arm::imm1
                             arm::imm2))

(defconstant wasm-temp-fp-regs (1- (ash 1 28)))

(defconstant wasm-cr-fields (make-mask 0))

(defconstant $undo-wasm-c-frame 16)

(ccl::provide "WASMENV")
