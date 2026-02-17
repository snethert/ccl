;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Copyright 2026 Clozure Associates
;;;
;;; Licensed under the Apache License, Version 2.0 (the "License");
;;; you may not use this file except in compliance with the License.
;;; You may obtain a copy of the License at
;;;
;;;     http://www.apache.org/licenses/LICENSE-2.0
;;;
;;; Unless required by applicable law or agreed to in writing, software
;;; distributed under the License is distributed on an "AS IS" BASIS,
;;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;;; See the License for the specific language governing permissions and
;;; limitations under the License.

(in-package "CCL")

(eval-when (:compile-toplevel :execute)
  (require "FASLENV" "ccl:xdump;faslenv")
  (require "ARM-ARCH"))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "XFASLOAD" "ccl:xdump;xfasload"))

;; Keep in sync with build/wasm32/subprims-map.json.
(defconstant +wasm-macro-apply-entry-index+ 130)
(defconstant +wasm-udf-entry-index+ 131)
;; _SPcall_closure index in the subprims table.
(defconstant +wasm-closure-trampoline-entry-index+ 71)

(defun wasm-entry-fixnum (index)
  (ash index arm::fixnumshift))

(defun wasm-make-stub-code-vector (entry-index)
  (make-array 1
              :element-type '(unsigned-byte 32)
              :initial-element (wasm-entry-fixnum entry-index)))

(defparameter *wasm-macro-apply-code*
  (wasm-make-stub-code-vector +wasm-macro-apply-entry-index+))

(defun wasm-fixup-macro-apply-code ()
  *wasm-macro-apply-code*)

(defparameter *wasm-closure-trampoline-code*
  (wasm-make-stub-code-vector +wasm-closure-trampoline-entry-index+))

;;; For now, use a stub code vector so the kernel can supply the real entry.
(defparameter *wasm-udf-code*
  (wasm-make-stub-code-vector +wasm-udf-entry-index+))

(defun xload-wasm-set-entrypoint (xload-fn)
  (let* ((code (xload-%svref xload-fn 1))
         (entry (xload-%fullword-ref code 0)))
    (setf (xload-%svref xload-fn 0) entry)
    xload-fn))

(defun wasm-initialize-static-space ()
  (xload-make-word-ivector arm::subtag-u32-vector 1021 *xload-static-space*)
  ;; Make NIL.  Note that NIL is sort of a misaligned cons (it
  ;; straddles two doublewords.)
  (xload-make-cons *xload-target-nil* 0 *xload-static-space*)
  (xload-make-cons 0 *xload-target-nil* *xload-static-space*))

(defparameter *wasm32-xload-backend*
  (make-backend-xload-info
   :name :wasm32
   :macro-apply-code-function 'wasm-fixup-macro-apply-code
   :closure-trampoline-code *wasm-closure-trampoline-code*
   :udf-code *wasm-udf-code*
   :default-image-name "ccl:build;wasm32;wasm-boot.image"
   :default-startup-file-name "ccl:build;wasm32;level-1.lafsl"
   :subdirs '("ccl:level-0;WASM;")
   :compiler-target-name :wasm32
   ;; Phase 0B: Read image base from CCL_WASM_IMAGE_BASE env var
   ;; (set by rebuild-everything.sh from __heap_base aligned to 64KiB).
   ;; This ensures bias=0 at load time — no relocation walk needed.
   :image-base-address (or (let ((s (getenv "CCL_WASM_IMAGE_BASE")))
                             (and s (parse-integer s :radix 16 :junk-allowed t)))
                           #x10000000)
   :nil-relative-symbols (append arm::*arm-nil-relative-symbols*
                                  '(ccl::%wasm-compiled-modules%
                                    ccl::%wasm-const-pools%))
   :static-space-init-function 'wasm-initialize-static-space
   :purespace-reserve (ash 64 20)
   :static-space-address (- (- arm::nil-value arm::fulltag-nil) (ash 1 12))
))

(add-xload-backend *wasm32-xload-backend*)

#+wasm32-target
(setq *xload-default-backend* *wasm32-xload-backend*)
