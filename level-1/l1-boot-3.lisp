;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Copyright 1994-2009 Clozure Associates
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

;;; l1-boot-3.lisp
;;; Third part of l1-boot

(in-package "CCL")

;;; Register Emacs-friendly aliases for some character encodings.
;;; This could go on forever; try to recognize at least some common
;;; cases.  (The precise set of encoding/coding-system names supported
;;; by Emacs likely depends on Emacs version, loaded Emacs packages, etc.)

(dotimes (i 16)
  (let* ((key (find-symbol (format nil "LATIN~d" i) :keyword))
         (existing (and key (lookup-character-encoding key))))
    (when existing
      (define-character-encoding-alias (intern (format nil "LATIN-~d" i) :keyword) existing)
      (define-character-encoding-alias (intern (format nil "ISO-LATIN-~d" i) :keyword) existing))))

(define-character-encoding-alias :mule-utf-8 :utf-8)

(set-pathname-encoding-name :utf-8)

(catch :toplevel
    (or (find-package "COMMON-LISP-USER")
        (make-package "COMMON-LISP-USER" :use '("COMMON-LISP" "CCL") :NICKNAMES '("CL-USER")))
)

;;; On WASM32, activate full L1 error handlers now that the condition system
;;; is initialized, then clear the /full placeholder fcells before GC.
#+wasm32-target
(progn
  (fset '%kernel-restart #'%kernel-restart/full)
  (fset '%kernel-restart-internal #'%kernel-restart-internal/full)
  (fset '%err-disp #'%err-disp/full)
  (fset '%err-disp-internal #'%err-disp-internal/full)
  (fset '%err-disp-common #'%err-disp-common/full)
  (fset '%error #'%error/full)
  (fset 'error #'error/full)
  (fset 'cerror #'cerror/full)
  (fset '%errno-disp #'%errno-disp/full)
  (fset '%errno-disp-internal #'%errno-disp-internal/full)
  ;; Clear /full fcells so pre-save GC doesn't retain duplicates
  (fmakunbound '%kernel-restart/full)
  (fmakunbound '%kernel-restart-internal/full)
  (fmakunbound '%err-disp/full)
  (fmakunbound '%err-disp-internal/full)
  (fmakunbound '%err-disp-common/full)
  (fmakunbound '%error/full)
  (fmakunbound 'error/full)
  (fmakunbound 'cerror/full)
  (fmakunbound '%errno-disp/full)
  (fmakunbound '%errno-disp-internal/full))

(set-periodic-task-interval .33)
(setq cmain xcmain)
(setq %err-disp %xerr-disp)

;;;end of l1-boot-3.lisp

