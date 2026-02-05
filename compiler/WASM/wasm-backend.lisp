;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 backend scaffold.

(in-package "CCL")

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "NXENV")
  (require "WASMENV")
  (require "WASM-ARCH")
  (require "WASM-VINSNS")
  (require "WASM2"))

(defvar *wasm-backend*
  (make-backend :lookup-opcode #'false
                :lookup-macro #'false
                :define-vinsn '%define-wasm-vinsn
                :platform-syscall-mask (logior platform-os-wasm platform-cpu-wasm)
                :p2-dispatch *wasm2-specials*
                :p2-vinsn-templates *wasm-vinsn-templates*
                :p2-template-hash-name '*wasm-vinsn-templates*
                :p2-compile 'wasm2-compile
                :target-specific-features
                '(:wasm :wasm-target :wasm32-target :32-bit-target :little-endian-target)
                :target-fasl-pathname (make-pathname :type "lafsl")
                :target-platform (logior platform-word-size-32
                                         platform-cpu-wasm
                                         platform-os-wasm)
                :target-os :wasm
                :name :wasm32
                :target-arch-name :wasm32
                :target-arch wasm::*wasm32-target-arch*))

(pushnew *wasm-backend* *known-backends* :key #'backend-name)

(provide "WASM-BACKEND")
