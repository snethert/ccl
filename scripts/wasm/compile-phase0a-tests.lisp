;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Phase 0A unit tests — WASM LAP bridge functions.
;;;
;;; Generates a JSON bundle of compiled WASM test modules.
;;; Each test function returns fixnum 1 (pass) or 0 (fail).
;;;
;;; Test categories:
;;;   A — Pure fixnum operations (work in minimal WASM runtime)
;;;   B — Vector operations (need basic allocation)
;;;   C — Bignum operations (need bignum support)
;;;   D — Float operations (need float allocation)
;;;   E — String/symbol operations (need string support)
;;;   S — Stub verification (always work)

(in-package "CCL")

(defvar %wasm-compiled-modules% nil)
(declaim (special %wasm-compiled-modules% *wasm2-next-entry-index*
                  *wasm2-enable-const-pool*
                  *wasm2-collect-module-debug*
                  *wasm2-compiled-modules-debug*))

;;; =====================================================================
;;; Test function definitions
;;; =====================================================================

(defparameter *wasm-phase0a-test-functions*
  '(
    ;; =================================================================
    ;; wasm-numbers.lisp — Category A (pure fixnum)
    ;; =================================================================

    ;; %fixnum-signum
    (ccl::test-signum-positive
     (lambda ()
       (if (= (%fixnum-signum 42) 1) 1 0)))

    (ccl::test-signum-negative
     (lambda ()
       (if (= (%fixnum-signum -7) -1) 1 0)))

    (ccl::test-signum-zero
     (lambda ()
       (if (= (%fixnum-signum 0) 0) 1 0)))

    ;; %ilogcount
    (ccl::test-ilogcount-zero
     (lambda ()
       (if (= (%ilogcount 0) 0) 1 0)))

    (ccl::test-ilogcount-one
     (lambda ()
       (if (= (%ilogcount 1) 1) 1 0)))

    (ccl::test-ilogcount-powers
     (lambda ()
       ;; 255 = #xFF = 8 bits set
       (if (= (%ilogcount 255) 8) 1 0)))

    (ccl::test-ilogcount-mixed
     (lambda ()
       ;; 170 = #xAA = 10101010 = 4 bits set
       (if (= (%ilogcount 170) 4) 1 0)))

    ;; %iash
    (ccl::test-iash-left
     (lambda ()
       (if (= (%iash 1 3) 8) 1 0)))

    (ccl::test-iash-right
     (lambda ()
       (if (= (%iash 16 -2) 4) 1 0)))

    (ccl::test-iash-zero
     (lambda ()
       (if (= (%iash 42 0) 42) 1 0)))

    ;; %fixnum-intlen
    (ccl::test-intlen-zero
     (lambda ()
       (if (= (%fixnum-intlen 0) 0) 1 0)))

    (ccl::test-intlen-one
     (lambda ()
       (if (= (%fixnum-intlen 1) 1) 1 0)))

    (ccl::test-intlen-255
     (lambda ()
       (if (= (%fixnum-intlen 255) 8) 1 0)))

    (ccl::test-intlen-neg
     (lambda ()
       ;; integer-length of -1 is 0, of -2 is 1, of -128 is 7
       (if (and (= (%fixnum-intlen -1) 0)
                (= (%fixnum-intlen -2) 1)
                (= (%fixnum-intlen -128) 7))
         1 0)))

    ;; %fixnum-truncate
    (ccl::test-truncate-basic
     (lambda ()
       (multiple-value-bind (q r) (%fixnum-truncate 10 3)
         (if (and (= q 3) (= r 1)) 1 0))))

    (ccl::test-truncate-exact
     (lambda ()
       (multiple-value-bind (q r) (%fixnum-truncate 12 4)
         (if (and (= q 3) (= r 0)) 1 0))))

    (ccl::test-truncate-negative
     (lambda ()
       (multiple-value-bind (q r) (%fixnum-truncate -7 2)
         (if (and (= q -3) (= r -1)) 1 0))))

    (ccl::test-truncate-neg-divisor
     (lambda ()
       (multiple-value-bind (q r) (%fixnum-truncate 7 -2)
         (if (and (= q -3) (= r 1)) 1 0))))

    (ccl::test-truncate-neg-one
     (lambda ()
       ;; Special case: division by -1 = negation
       (multiple-value-bind (q r) (%fixnum-truncate 42 -1)
         (if (and (= q -42) (= r 0)) 1 0))))

    ;; %fixnum-gcd
    (ccl::test-gcd-coprime
     (lambda ()
       (if (= (%fixnum-gcd 7 11) 1) 1 0)))

    (ccl::test-gcd-common
     (lambda ()
       (if (= (%fixnum-gcd 12 8) 4) 1 0)))

    (ccl::test-gcd-same
     (lambda ()
       (if (= (%fixnum-gcd 7 7) 7) 1 0)))

    (ccl::test-gcd-one-zero
     (lambda ()
       (if (and (= (%fixnum-gcd 0 5) 5)
                (= (%fixnum-gcd 5 0) 5))
         1 0)))

    (ccl::test-gcd-large
     (lambda ()
       ;; gcd(48, 18) = 6
       (if (= (%fixnum-gcd 48 18) 6) 1 0)))

    (ccl::test-gcd-powers-of-two
     (lambda ()
       ;; gcd(16, 64) = 16
       (if (= (%fixnum-gcd 16 64) 16) 1 0)))

    ;; called-for-mv-p — always NIL on WASM
    (ccl::test-called-for-mv-p
     (lambda ()
       (if (eq (called-for-mv-p) nil) 1 0)))


    ;; =================================================================
    ;; wasm-misc.lisp — Category A (pure fixnum / stubs)
    ;; =================================================================

    ;; %heap-bytes-allocated — returns 0
    (ccl::test-heap-bytes
     (lambda ()
       (if (= (%heap-bytes-allocated) 0) 1 0)))

    ;; values function
    (ccl::test-values-single
     (lambda ()
       (if (= (values 42) 42) 1 0)))

    (ccl::test-values-multiple
     (lambda ()
       (multiple-value-bind (a b c) (values 1 2 3)
         (if (and (= a 1) (= b 2) (= c 3)) 1 0))))

    ;; interrupt-level / set-interrupt-level
    ;; These access TCR — may trap if TCR not set up. Category A with caveats.

    ;; %store-node-conditional — Category B (needs vector allocation)
    (ccl::test-store-node-cond-hit
     (lambda ()
       ;; Create a vector, conditional-store if old matches
       (let ((v (vector 10 20 30)))
         ;; Offset for element 0: target::misc-data-offset = 4 (on 32-bit)
         ;; But %store-node-conditional takes fixnum byte offset
         (let ((result (%store-node-conditional 4 v 10 99)))
           (if (and result (eq (uvrefv 0) 99)) 1 0)))))

    (ccl::test-store-node-cond-miss
     (lambda ()
       (let ((v (vector 10 20 30)))
         (let ((result (%store-node-conditional 4 v 42 99)))
           ;; Should fail — old value is 10, not 42
           (if (and (not result) (eq (uvrefv 0) 10)) 1 0)))))

    ;; %atomic-incf-node — Category B
    (ccl::test-atomic-incf-node
     (lambda ()
       (let ((v (vector 10 20)))
         ;; Increment element at offset 4 by 5
         (let ((old (%atomic-incf-node 5 v 4)))
           ;; old should be 10, new value should be 15
           (if (and (eq old 10) (eq (uvrefv 0) 15)) 1 0)))))

    ;; Thread control stubs — Category S
    (ccl::test-tcr-interrupt
     (lambda ()
       (if (= (%%tcr-interrupt 0) 0) 1 0)))

    (ccl::test-suspend-other-threads
     (lambda ()
       (if (eq (%suspend-other-threads) t) 1 0)))

    (ccl::test-resume-other-threads
     (lambda ()
       (if (eq (%resume-other-threads) nil) 1 0)))

    (ccl::test-check-deferred-gc
     (lambda ()
       (if (eq (%check-deferred-gc) nil) 1 0)))

    (ccl::test-pending-user-interrupt
     (lambda ()
       (if (eq (pending-user-interrupt) nil) 1 0)))

    (ccl::test-lock-unlock-gc
     (lambda ()
       (if (and (eq (%lock-gc-lock) nil)
                (eq (%unlock-gc-lock) nil))
         1 0)))

    ;; %atomic-pop-static-cons — returns NIL
    (ccl::test-atomic-pop-static-cons
     (lambda ()
       (if (eq (%atomic-pop-static-cons) nil) 1 0)))

    ;; get-saved-register-values — returns no values
    (ccl::test-saved-register-values
     (lambda ()
       (multiple-value-bind (a) (get-saved-register-values)
         (if (eq a nil) 1 0))))

    ;; %copy-gvector-to-gvector — Category B
    (ccl::test-copy-gvector-forward
     (lambda ()
       (let ((src (vector 1 2 3 4 5))
             (dst (vector 0 0 0 0 0)))
         (%copy-gvector-to-gvector src 0 dst 0 5)
         (if (and (eq (uvrefdst 0) 1)
                  (eq (uvrefdst 1) 2)
                  (eq (uvrefdst 2) 3)
                  (eq (uvrefdst 3) 4)
                  (eq (uvrefdst 4) 5))
           1 0))))

    (ccl::test-copy-gvector-overlap-fwd
     (lambda ()
       ;; Copy within same vector, non-overlapping direction
       (let ((v (vector 1 2 3 4 5)))
         (%copy-gvector-to-gvector v 0 v 2 3)
         ;; v should be (1 2 1 2 3)
         (if (and (eq (uvrefv 0) 1)
                  (eq (uvrefv 1) 2)
                  (eq (uvrefv 2) 1)
                  (eq (uvrefv 3) 2)
                  (eq (uvrefv 4) 3))
           1 0))))

    (ccl::test-copy-gvector-overlap-bwd
     (lambda ()
       ;; Copy within same vector, backward direction
       (let ((v (vector 1 2 3 4 5)))
         (%copy-gvector-to-gvector v 2 v 0 3)
         ;; v should be (3 4 5 4 5)
         (if (and (eq (uvrefv 0) 3)
                  (eq (uvrefv 1) 4)
                  (eq (uvrefv 2) 5))
           1 0))))


    ;; =================================================================
    ;; wasm-def.lisp — Category A/S
    ;; =================================================================

    ;; %current-frame-ptr — returns 0
    (ccl::test-current-frame-ptr
     (lambda ()
       (if (= (%current-frame-ptr) 0) 1 0)))

    ;; arm-hard-float-p — returns NIL
    (ccl::test-arm-hard-float
     (lambda ()
       (if (eq (arm-hard-float-p) nil) 1 0)))

    ;; %%frame-backlink — returns 0
    (ccl::test-frame-backlink
     (lambda ()
       (if (= (%%frame-backlink 0) 0) 1 0)))

    ;; %%frame-savefn — returns NIL
    (ccl::test-frame-savefn
     (lambda ()
       (if (eq (%%frame-savefn 0) nil) 1 0)))

    ;; %cfp-lfun — returns (values nil nil)
    (ccl::test-cfp-lfun
     (lambda ()
       (multiple-value-bind (a b) (%cfp-lfun 0)
         (if (and (eq a nil) (eq b nil)) 1 0))))

    ;; %current-vsp — returns 0
    (ccl::test-current-vsp
     (lambda ()
       (if (= (%current-vsp) 0) 1 0)))

    ;; %%frame-savevsp — returns 0
    (ccl::test-frame-savevsp
     (lambda ()
       (if (= (%%frame-savevsp 0) 0) 1 0)))

    ;; %save-standard-binding-list — returns NIL
    (ccl::test-save-binding-list
     (lambda ()
       (if (eq (%save-standard-binding-list nil) nil) 1 0)))

    ;; %saved-bindings-address — returns 0
    (ccl::test-saved-bindings-addr
     (lambda ()
       (if (= (%saved-bindings-address) 0) 1 0)))

    ;; %code-vector-pc — returns NIL
    (ccl::test-code-vector-pc
     (lambda ()
       (if (eq (%code-vector-pc nil nil) nil) 1 0)))

    ;; %lookup-subprim-address — returns 0
    (ccl::test-lookup-subprim
     (lambda ()
       (if (= (%lookup-subprim-address 0) 0) 1 0)))

    ;; %make-code-executable — no-op, returns NIL
    (ccl::test-make-code-exec
     (lambda ()
       (if (eq (%make-code-executable nil) nil) 1 0)))

    ;; apply+ — Category A
    (ccl::test-apply-plus
     (lambda ()
       (if (= (apply+ #'+ 1 2 3 nil) 6) 1 0)))

    ;; closure-function — Category B
    (ccl::test-closure-function
     (lambda ()
       ;; closure-function on a compiled function should return itself
       (let ((f #'+))
         (if (functionp (closure-function f)) 1 0))))

    ;; %apply-lexpr-with-method-context — Category A
    (ccl::test-apply-method-ctx
     (lambda ()
       (if (= (%apply-lexpr-with-method-context nil #'+ '(1 2)) 3)
         1 0)))

    ;; %init-misc — Category B
    (ccl::test-init-misc
     (lambda ()
       (let ((v (vector 1 2 3)))
         (%init-misc 0 v)
         (if (and (eq (uvrefv 0) 0)
                  (eq (uvrefv 1) 0)
                  (eq (uvrefv 2) 0))
           1 0))))


    ;; =================================================================
    ;; wasm-utils.lisp — Category S (stubs)
    ;; =================================================================

    ;; gc — no-op, returns NIL
    (ccl::test-gc
     (lambda ()
       (if (eq (gc) nil) 1 0)))

    ;; egc — no-op, returns NIL
    (ccl::test-egc
     (lambda ()
       (if (eq (egc t) nil) 1 0)))

    ;; purify — no-op, returns NIL
    (ccl::test-purify
     (lambda ()
       (if (eq (purify) nil) 1 0)))

    ;; impurify — no-op, returns NIL
    (ccl::test-impurify
     (lambda ()
       (if (eq (impurify) nil) 1 0)))

    ;; lisp-heap-gc-threshold — returns 0
    (ccl::test-gc-threshold
     (lambda ()
       (if (= (lisp-heap-gc-threshold) 0) 1 0)))

    ;; set-lisp-heap-gc-threshold — returns 0
    (ccl::test-set-gc-threshold
     (lambda ()
       (if (= (set-lisp-heap-gc-threshold 1000) 0) 1 0)))

    ;; use-lisp-heap-gc-threshold — returns NIL
    (ccl::test-use-gc-threshold
     (lambda ()
       (if (eq (use-lisp-heap-gc-threshold) nil) 1 0)))

    ;; allow-heap-allocation — returns NIL
    (ccl::test-allow-heap-alloc
     (lambda ()
       (if (eq (allow-heap-allocation t) nil) 1 0)))

    ;; heap-allocation-allowed-p — returns T
    (ccl::test-heap-alloc-p
     (lambda ()
       (if (eq (heap-allocation-allowed-p) t) 1 0)))

    ;; %ensure-static-conses — returns NIL
    (ccl::test-ensure-static-conses
     (lambda ()
       (if (eq (%ensure-static-conses) nil) 1 0)))

    ;; set-gc-notification-threshold — returns 0
    (ccl::test-set-gc-notif
     (lambda ()
       (if (= (set-gc-notification-threshold 100) 0) 1 0)))

    ;; get-gc-notification-threshold — returns 0
    (ccl::test-get-gc-notif
     (lambda ()
       (if (= (get-gc-notification-threshold) 0) 1 0)))

    ;; %configure-egc — returns NIL
    (ccl::test-configure-egc
     (lambda ()
       (if (eq (%configure-egc 100 200 300) nil) 1 0)))

    ;; true — always T
    (ccl::test-true-fn
     (lambda ()
       (if (and (eq (true) t)
                (eq (true 1 2 3) t))
         1 0)))

    ;; false — always NIL
    (ccl::test-false-fn
     (lambda ()
       (if (and (eq (false) nil)
                (eq (false 1 2 3) nil))
         1 0)))

    ;; %allocate-list — Category B
    (ccl::test-allocate-list
     (lambda ()
       (let ((lst (%allocate-list 42 3)))
         (if (and (consp lst)
                  (= (length lst) 3)
                  (= (car lst) 42)
                  (= (cadr lst) 42)
                  (= (caddr lst) 42))
           1 0))))


    ;; =================================================================
    ;; wasm-pred.lisp — Category A
    ;; =================================================================

    ;; eql on fixnums
    (ccl::test-eql-fixnum
     (lambda ()
       (if (and (eql 42 42)
                (not (eql 42 43)))
         1 0)))

    ;; eql on nil/t
    (ccl::test-eql-nil
     (lambda ()
       (if (and (eql nil nil)
                (eql t t)
                (not (eql nil t)))
         1 0)))

    ;; equal on fixnums
    (ccl::test-equal-fixnum
     (lambda ()
       (if (and (equal 42 42)
                (not (equal 42 43)))
         1 0)))

    ;; equal on conses — Category B
    (ccl::test-equal-conses
     (lambda ()
       (if (and (equal '(1 2 3) (list 1 2 3))
                (not (equal '(1 2 3) (list 1 2 4))))
         1 0)))

    ;; equal on nested conses — Category B
    (ccl::test-equal-nested
     (lambda ()
       (if (equal (list 1 (list 2 3)) (list 1 (list 2 3)))
         1 0)))


    ;; =================================================================
    ;; wasm-io.lisp — Category S
    ;; =================================================================

    ;; %get-errno — returns 0
    (ccl::test-get-errno
     (lambda ()
       (if (= (%get-errno) 0) 1 0)))


    ;; =================================================================
    ;; wasm-hash.lisp — Category S/A
    ;; =================================================================

    ;; %get-fwdnum — returns 0
    (ccl::test-get-fwdnum
     (lambda ()
       (if (= (%get-fwdnum) 0) 1 0)))

    ;; %get-gc-count — returns 0
    (ccl::test-get-gc-count
     (lambda ()
       (if (= (%get-gc-count) 0) 1 0)))

    ;; fast-mod — basic modular arithmetic
    (ccl::test-fast-mod
     (lambda ()
       (if (and (= (fast-mod 10 3) 1)
                (= (fast-mod 12 4) 0)
                (= (fast-mod 7 7) 0))
         1 0)))

    ;; strip-tag-to-fixnum — on fixnum input, returns same
    (ccl::test-strip-tag-fixnum
     (lambda ()
       (if (= (strip-tag-to-fixnum 42) 42) 1 0)))


    ;; =================================================================
    ;; wasm-array.lisp — Category B
    ;; =================================================================

    ;; %init-misc — already tested above

    ;; %array-header-data-and-offset — needs array headers, skip for now

    ;; %aref2, %aref3, %aset2, %aset3 — need multi-dim arrays
    ;; Just test basic call doesn't crash if arrays are available

    ;; %boole-and on vectors — Category B
    (ccl::test-boole-and
     (lambda ()
       (let ((b1 (vector #xFF00 #x0F0F))
             (b2 (vector #xF0F0 #xFFFF))
             (dest (vector 0 0)))
         (%boole-and 2 b1 b2 dest)
         (if (and (= (uvrefdest 0) (logand #xFF00 #xF0F0))
                  (= (uvrefdest 1) (logand #x0F0F #xFFFF)))
           1 0))))

    (ccl::test-boole-ior
     (lambda ()
       (let ((b1 (vector #xFF00 #x0000))
             (b2 (vector #x00FF #x0F0F))
             (dest (vector 0 0)))
         (%boole-ior 2 b1 b2 dest)
         (if (and (= (uvrefdest 0) (logior #xFF00 #x00FF))
                  (= (uvrefdest 1) (logior #x0000 #x0F0F)))
           1 0))))

    (ccl::test-boole-xor
     (lambda ()
       (let ((b1 (vector #xFFFF #xAAAA))
             (b2 (vector #xFF00 #x5555))
             (dest (vector 0 0)))
         (%boole-xor 2 b1 b2 dest)
         (if (and (= (uvrefdest 0) (logxor #xFFFF #xFF00))
                  (= (uvrefdest 1) (logxor #xAAAA #x5555)))
           1 0))))

    (ccl::test-boole-clr
     (lambda ()
       (let ((dest (vector #xFFFF #xFFFF)))
         (%boole-clr 2 nil nil dest)
         (if (and (= (uvrefdest 0) 0)
                  (= (uvrefdest 1) 0))
           1 0))))

    (ccl::test-boole-set
     (lambda ()
       (let ((dest (vector 0 0)))
         (%boole-set 2 nil nil dest)
         (if (and (= (uvrefdest 0) #xFFFFFFFF)
                  (= (uvrefdest 1) #xFFFFFFFF))
           1 0))))

    (ccl::test-boole-1
     (lambda ()
       (let ((b1 (vector 42 99))
             (dest (vector 0 0)))
         (%boole-1 2 b1 nil dest)
         (if (and (= (uvrefdest 0) 42)
                  (= (uvrefdest 1) 99))
           1 0))))

    (ccl::test-boole-2
     (lambda ()
       (let ((b2 (vector 42 99))
             (dest (vector 0 0)))
         (%boole-2 2 nil b2 dest)
         (if (and (= (uvrefdest 0) 42)
                  (= (uvrefdest 1) 99))
           1 0))))

    (ccl::test-boole-nand
     (lambda ()
       (let ((b1 (vector #xFFFFFFFF))
             (b2 (vector #xFF00FF00))
             (dest (vector 0)))
         (%boole-nand 1 b1 b2 dest)
         ;; nand(FFFFFFFF, FF00FF00) = ~(FF00FF00) = 00FF00FF
         (if (= (uvrefdest 0) #x00FF00FF)
           1 0))))


    ;; =================================================================
    ;; wasm-bignum.lisp helpers — Category A (inline, pure math)
    ;; These are declared inline so the compiler expands them.
    ;; =================================================================

    ;; %u32 — mask to 32 bits
    (ccl::test-u32-zero
     (lambda ()
       (if (= (logand 0 #xFFFFFFFF) 0) 1 0)))

    (ccl::test-u32-max
     (lambda ()
       (if (= (logand #xFFFFFFFF #xFFFFFFFF) #xFFFFFFFF) 1 0)))

    (ccl::test-u32-overflow
     (lambda ()
       ;; #x100000000 masked to 32 bits = 0
       (if (= (logand #x100000000 #xFFFFFFFF) 0) 1 0)))

    (ccl::test-u32-neg
     (lambda ()
       ;; (logand -1 #xFFFFFFFF) = #xFFFFFFFF
       (if (= (logand -1 #xFFFFFFFF) #xFFFFFFFF) 1 0)))

    ;; %high-half / %low-half — 16-bit extraction
    (ccl::test-high-half
     (lambda ()
       ;; #xDEADBEEF: high-half = #xDEAD
       (if (= (logand (ash #xDEADBEEF -16) #xFFFF) #xDEAD) 1 0)))

    (ccl::test-low-half
     (lambda ()
       ;; #xDEADBEEF: low-half = #xBEEF
       (if (= (logand #xDEADBEEF #xFFFF) #xBEEF) 1 0)))

    ;; %compose-digit — compose from halves
    (ccl::test-compose-digit
     (lambda ()
       ;; compose(#xDEAD, #xBEEF) = #xDEADBEEF
       (let ((result (logand #xFFFFFFFF
                             (logior (ash (logand #xDEAD #xFFFF) 16)
                                     (logand #xBEEF #xFFFF)))))
         (if (= result #xDEADBEEF) 1 0))))

    (ccl::test-compose-digit-zero
     (lambda ()
       (let ((result (logand #xFFFFFFFF
                             (logior (ash (logand 0 #xFFFF) 16)
                                     (logand 0 #xFFFF)))))
         (if (= result 0) 1 0))))

    ;; %mul32x32 — 32x32 -> 64 multiply
    ;; Testing the algorithm inline since it's declared inline
    (ccl::test-mul32x32-simple
     (lambda ()
       ;; 2 * 3 = 6, high = 0
       (let* ((a 2) (b 3)
              (al (logand a #xFFFF)) (ah (ash a -16))
              (bl (logand b #xFFFF)) (bh (ash b -16))
              (ll (* al bl)) (lh (* al bh))
              (hl (* ah bl)) (hh (* ah bh))
              (mid (+ lh hl))
              (low-sum (+ ll (ash (logand mid #xFFFF) 16)))
              (lo (logand low-sum #xFFFFFFFF))
              (hi (logand (+ hh (ash mid -16) (ash low-sum -32)) #xFFFFFFFF)))
         (if (and (= lo 6) (= hi 0)) 1 0))))

    (ccl::test-mul32x32-large
     (lambda ()
       ;; #x10000 * #x10000 = #x100000000 → lo=0, hi=1
       (let* ((a #x10000) (b #x10000)
              (al (logand a #xFFFF)) (ah (ash a -16))
              (bl (logand b #xFFFF)) (bh (ash b -16))
              (ll (* al bl)) (lh (* al bh))
              (hl (* ah bl)) (hh (* ah bh))
              (mid (+ lh hl))
              (low-sum (+ ll (ash (logand mid #xFFFF) 16)))
              (lo (logand low-sum #xFFFFFFFF))
              (hi (logand (+ hh (ash mid -16) (ash low-sum -32)) #xFFFFFFFF)))
         (if (and (= lo 0) (= hi 1)) 1 0))))

    (ccl::test-mul32x32-max
     (lambda ()
       ;; #xFFFF * #xFFFF = #xFFFE0001
       (let* ((a #xFFFF) (b #xFFFF)
              (al (logand a #xFFFF)) (ah (ash a -16))
              (bl (logand b #xFFFF)) (bh (ash b -16))
              (ll (* al bl)) (lh (* al bh))
              (hl (* ah bl)) (hh (* ah bh))
              (mid (+ lh hl))
              (low-sum (+ ll (ash (logand mid #xFFFF) 16)))
              (lo (logand low-sum #xFFFFFFFF))
              (hi (logand (+ hh (ash mid -16) (ash low-sum -32)) #xFFFFFFFF)))
         (if (and (= lo #xFFFE0001) (= hi 0)) 1 0))))

    ;; CLZ / CTZ algorithm tests — Category A (pure math)
    (ccl::test-clz-zero
     (lambda ()
       ;; CLZ of 0 = 32
       (let ((d 0))
         (if (= (if (zerop d) 32
                  (let ((n 0))
                    (when (zerop (logand d #xFFFF0000)) (setq n (+ n 16) d (ash d 16)))
                    (when (zerop (logand d #xFF000000)) (setq n (+ n 8) d (ash d 8)))
                    (when (zerop (logand d #xF0000000)) (setq n (+ n 4) d (ash d 4)))
                    (when (zerop (logand d #xC0000000)) (setq n (+ n 2) d (ash d 2)))
                    (when (zerop (logand d #x80000000)) (setq n (+ n 1)))
                    n))
                32) 1 0))))

    (ccl::test-clz-one
     (lambda ()
       ;; CLZ of 1 = 31
       (let ((d 1) (n 0))
         (when (zerop (logand d #xFFFF0000)) (setq n (+ n 16) d (ash d 16)))
         (when (zerop (logand d #xFF000000)) (setq n (+ n 8) d (ash d 8)))
         (when (zerop (logand d #xF0000000)) (setq n (+ n 4) d (ash d 4)))
         (when (zerop (logand d #xC0000000)) (setq n (+ n 2) d (ash d 2)))
         (when (zerop (logand d #x80000000)) (setq n (+ n 1)))
         (if (= n 31) 1 0))))

    (ccl::test-clz-msb
     (lambda ()
       ;; CLZ of #x80000000 = 0
       (let ((d #x80000000) (n 0))
         (when (zerop (logand d #xFFFF0000)) (setq n (+ n 16) d (ash d 16)))
         (when (zerop (logand d #xFF000000)) (setq n (+ n 8) d (ash d 8)))
         (when (zerop (logand d #xF0000000)) (setq n (+ n 4) d (ash d 4)))
         (when (zerop (logand d #xC0000000)) (setq n (+ n 2) d (ash d 2)))
         (when (zerop (logand d #x80000000)) (setq n (+ n 1)))
         (if (= n 0) 1 0))))

    (ccl::test-ctz-one
     (lambda ()
       ;; CTZ of 1 = 0
       (let ((d 1) (n 0))
         (when (zerop (logand d #x0000FFFF)) (setq n (+ n 16) d (ash d -16)))
         (when (zerop (logand d #x000000FF)) (setq n (+ n 8) d (ash d -8)))
         (when (zerop (logand d #x0000000F)) (setq n (+ n 4) d (ash d -4)))
         (when (zerop (logand d #x00000003)) (setq n (+ n 2) d (ash d -2)))
         (when (zerop (logand d #x00000001)) (setq n (+ n 1)))
         (if (= n 0) 1 0))))

    (ccl::test-ctz-power-of-two
     (lambda ()
       ;; CTZ of #x100 = 8
       (let ((d #x100) (n 0))
         (when (zerop (logand d #x0000FFFF)) (setq n (+ n 16) d (ash d -16)))
         (when (zerop (logand d #x000000FF)) (setq n (+ n 8) d (ash d -8)))
         (when (zerop (logand d #x0000000F)) (setq n (+ n 4) d (ash d -4)))
         (when (zerop (logand d #x00000003)) (setq n (+ n 2) d (ash d -2)))
         (when (zerop (logand d #x00000001)) (setq n (+ n 1)))
         (if (= n 8) 1 0))))


    ;; =================================================================
    ;; wasm-bignum.lisp — Category C (need bignum/vector support)
    ;; These call the actual Phase 0A functions at runtime.
    ;; =================================================================

    ;; %udiv64by32 — unsigned 64/32 division
    ;; This is a plain Lisp function using floor.
    (ccl::test-udiv64-basic
     (lambda ()
       ;; 0:100 / 10 = 10 remainder 0
       (multiple-value-bind (q r) (%udiv64by32 0 100 10)
         (if (and (= q 10) (= r 0)) 1 0))))

    (ccl::test-udiv64-remainder
     (lambda ()
       ;; 0:7 / 3 = 2 remainder 1
       (multiple-value-bind (q r) (%udiv64by32 0 7 3)
         (if (and (= q 2) (= r 1)) 1 0))))

    (ccl::test-udiv64-large
     (lambda ()
       ;; 1:0 / 1 = #x100000000 -> q = 0 (mod 2^32)
       ;; Actually: dividend = (1 << 32) | 0 = #x100000000
       ;; #x100000000 / 1 = #x100000000, masked to 32 bits = 0
       (multiple-value-bind (q r) (%udiv64by32 1 0 1)
         (if (and (= q 0) (= r 0)) 1 0))))


    ;; =================================================================
    ;; wasm-float.lisp — Category D / Category A for helpers
    ;; =================================================================

    ;; %count-leading-zeros-32 — pure math, usable immediately
    (ccl::test-clz32-fn-zero
     (lambda ()
       (if (= (%count-leading-zeros-32 0) 32) 1 0)))

    (ccl::test-clz32-fn-one
     (lambda ()
       (if (= (%count-leading-zeros-32 1) 31) 1 0)))

    (ccl::test-clz32-fn-msb
     (lambda ()
       (if (= (%count-leading-zeros-32 #x80000000) 0) 1 0)))

    (ccl::test-clz32-fn-byte
     (lambda ()
       ;; #xFF = 255, CLZ of 255 in 32 bits = 24
       (if (= (%count-leading-zeros-32 #xFF) 24) 1 0)))

    (ccl::test-clz32-fn-halfword
     (lambda ()
       ;; #xFFFF CLZ in 32 bits = 16
       (if (= (%count-leading-zeros-32 #xFFFF) 16) 1 0)))

    ;; FPU stubs
    (ccl::test-ffi-exception-status
     (lambda ()
       (if (= (%ffi-exception-status) 0) 1 0)))

    (ccl::test-fpscr-control
     (lambda ()
       (if (= (%get-fpscr-control) 0) 1 0)))

    (ccl::test-fpscr-status
     (lambda ()
       (if (= (%get-fpscr-status) 0) 1 0)))

    (ccl::test-get-fpscr
     (lambda ()
       (if (= (%get-fpscr) 0) 1 0)))

    ;; get-fpu-mode — returns a plist or a keyword value
    (ccl::test-fpu-mode-rounding
     (lambda ()
       (if (eq (get-fpu-mode :rounding-mode) :nearest) 1 0)))

    ;; set-fpu-mode — no-op, returns 0
    (ccl::test-set-fpu-mode
     (lambda ()
       (if (= (set-fpu-mode) 0) 1 0)))


    ;; =================================================================
    ;; wasm-clos.lisp — Category S (stubs)
    ;; =================================================================

    ;; gag-one-arg — returns NIL
    (ccl::test-gag-one-arg
     (lambda ()
       (if (eq (gag-one-arg 42) nil) 1 0)))

    ;; gag-two-arg — returns NIL
    (ccl::test-gag-two-arg
     (lambda ()
       (if (eq (gag-two-arg 1 2) nil) 1 0)))


    ;; =================================================================
    ;; wasm-symbol.lisp — Category E / A
    ;; =================================================================

    ;; %pname-hash on empty string — returns 0
    ;; We need a string uvector. If string creation works:
    ;; For now, test the algorithm inline.
    (ccl::test-pname-hash-zero-len
     (lambda ()
       ;; %pname-hash with len 0 returns 0
       (if (= (%pname-hash nil 0) 0) 1 0)))

    ;; %string-hash on empty — returns 0
    (ccl::test-string-hash-zero-len
     (lambda ()
       (if (= (%string-hash 0 nil 0) 0) 1 0)))


    ;; =================================================================
    ;; wasm-numbers.lisp — Category D (float truncation)
    ;; =================================================================

    ;; %mrg31k3p stub — returns 0
    (ccl::test-mrg31k3p
     (lambda ()
       (if (= (%mrg31k3p nil) 0) 1 0)))

    ;; %sfloat-hwords — Category D (needs single-float)
    ;; Test inline once floats work


    ;; =================================================================
    ;; Additional edge case tests — Category A
    ;; =================================================================

    ;; Multiple values through values function
    (ccl::test-values-empty
     (lambda ()
       ;; (values) with no args in multiple-value-bind
       (multiple-value-bind (a) (values)
         (if (eq a nil) 1 0))))

    ;; Fixnum arithmetic edge cases
    (ccl::test-fixnum-ops-edge
     (lambda ()
       (if (and (= (%i+ 0 0) 0)
                (= (%i+ 1 -1) 0)
                (= (%i- 5 5) 0)
                (= (%i* 1 42) 42)
                (= (%i* 0 999) 0))
         1 0)))

    ;; GCD edge cases
    (ccl::test-gcd-one
     (lambda ()
       (if (and (= (%fixnum-gcd 1 100) 1)
                (= (%fixnum-gcd 100 1) 1))
         1 0)))

    ;; Truncate edge: dividend 0
    (ccl::test-truncate-zero-dividend
     (lambda ()
       (multiple-value-bind (q r) (%fixnum-truncate 0 7)
         (if (and (= q 0) (= r 0)) 1 0))))

    ;; Large fixnum GCD
    (ccl::test-gcd-large-fixnum
     (lambda ()
       ;; gcd(1000000, 999999) = 1 (coprime)
       (if (= (%fixnum-gcd 1000000 999999) 1) 1 0)))

    (ccl::test-gcd-large-common
     (lambda ()
       ;; gcd(1000000, 500000) = 500000
       (if (= (%fixnum-gcd 1000000 500000) 500000) 1 0)))

    ;; Signum edge: most-negative-fixnum is still negative
    (ccl::test-signum-min-fixnum
     (lambda ()
       ;; We can't easily get most-negative-fixnum as a constant,
       ;; but -100000 is certainly negative
       (if (= (%fixnum-signum -100000) -1) 1 0)))

    ;; ilogcount larger values
    (ccl::test-ilogcount-all-ones
     (lambda ()
       ;; #xFFFF = 16 bits set
       (if (= (%ilogcount #xFFFF) 16) 1 0)))

    ;; Boole complement operations — Category B
    (ccl::test-boole-c1
     (lambda ()
       (let ((b1 (vector #xFF00FF00))
             (dest (vector 0)))
         (%boole-c1 1 b1 nil dest)
         ;; ~(#xFF00FF00) masked to 32 bits = #x00FF00FF
         (if (= (uvrefdest 0) #x00FF00FF)
           1 0))))

    (ccl::test-boole-c2
     (lambda ()
       (let ((b2 (vector #xFF00FF00))
             (dest (vector 0)))
         (%boole-c2 1 nil b2 dest)
         (if (= (uvrefdest 0) #x00FF00FF)
           1 0))))

    (ccl::test-boole-eqv
     (lambda ()
       (let ((b1 (vector #xFF00FF00))
             (b2 (vector #xFF00FF00))
             (dest (vector 0)))
         (%boole-eqv 1 b1 b2 dest)
         ;; eqv of same = ~xor = ~0 = #xFFFFFFFF
         (if (= (uvrefdest 0) #xFFFFFFFF)
           1 0))))

    (ccl::test-boole-nor
     (lambda ()
       (let ((b1 (vector #xFF000000))
             (b2 (vector #x00FF0000))
             (dest (vector 0)))
         (%boole-nor 1 b1 b2 dest)
         ;; nor = ~(FF000000 | 00FF0000) = ~(FFFF0000) = 0000FFFF
         (if (= (uvrefdest 0) #x0000FFFF)
           1 0))))

    (ccl::test-boole-andc1
     (lambda ()
       (let ((b1 (vector #xFF000000))
             (b2 (vector #xFFFF0000))
             (dest (vector 0)))
         (%boole-andc1 1 b1 b2 dest)
         ;; andc1 = b2 & ~b1 = FFFF0000 & 00FFFFFF = 00FF0000
         (if (= (uvrefdest 0) #x00FF0000)
           1 0))))

    (ccl::test-boole-andc2
     (lambda ()
       (let ((b1 (vector #xFFFF0000))
             (b2 (vector #xFF000000))
             (dest (vector 0)))
         (%boole-andc2 1 b1 b2 dest)
         ;; andc2 = b1 & ~b2 = FFFF0000 & 00FFFFFF = 00FF0000
         (if (= (uvrefdest 0) #x00FF0000)
           1 0))))

    (ccl::test-boole-orc1
     (lambda ()
       (let ((b1 (vector #xFF000000))
             (b2 (vector #x00000000))
             (dest (vector 0)))
         (%boole-orc1 1 b1 b2 dest)
         ;; orc1 = b2 | ~b1 = 00000000 | 00FFFFFF = 00FFFFFF
         (if (= (uvrefdest 0) #x00FFFFFF)
           1 0))))

    (ccl::test-boole-orc2
     (lambda ()
       (let ((b1 (vector #x00000000))
             (b2 (vector #xFF000000))
             (dest (vector 0)))
         (%boole-orc2 1 b1 b2 dest)
         ;; orc2 = b1 | ~b2 = 00000000 | 00FFFFFF = 00FFFFFF
         (if (= (uvrefdest 0) #x00FFFFFF)
           1 0))))

    ))


;;; =====================================================================
;;; Compilation infrastructure (same pattern as compile-smoke-modules.lisp)
;;; =====================================================================

(defun parse-argv (argv)
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (cond
          ((string= arg "--")
           (setf seen-delimiter t))
          ((string= arg "--output")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --output"))
             (push (cons :output val) out)))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t nil))))
    out))

(defun json-escape-string (s)
  (with-output-to-string (out)
    (loop for ch across s do
      (case ch
        (#\" (write-string "\\\"" out))
        (#\\ (write-string "\\\\" out))
        (#\Newline (write-string "\\n" out))
        (#\Return (write-string "\\r" out))
        (#\Tab (write-string "\\t" out))
        (t (write-char ch out))))))

(defun json-write-string (out s)
  (write-char #\" out)
  (write-string (json-escape-string s) out)
  (write-char #\" out))

(defun json-write-bytes (out bytes)
  (write-char #\[ out)
  (let ((len (length bytes)))
    (dotimes (i len)
      (when (> i 0)
        (write-char #\, out))
      (princ (aref bytes i) out)))
  (write-char #\] out))

(defun json-write-string-list (out items)
  (write-char #\[ out)
  (loop for item in items
        for idx from 0
        do (when (> idx 0)
             (write-char #\, out))
           (json-write-string out item))
  (write-char #\] out))

(defun function-entry-index (fn)
  (let* ((info (%lfun-info fn))
         (entry (and info (getf info 'wasm-entry-index))))
    (if entry
      entry
      (let* ((raw (uvref fn 0)))
        (unless (fixnump raw)
          (error "Unexpected function entry: ~s" raw))
        (let* ((target-shift (arch::target-fixnum-shift
                              (backend-target-arch (find-backend :wasm32)))))
          (ash raw (- target-shift)))))))

(defun compile-phase0a-tests ()
  (setf %wasm-compiled-modules% nil)
  (when (boundp '*wasm2-compiled-modules-debug*)
    (setf *wasm2-compiled-modules-debug* nil))
  (when (boundp '*wasm2-next-entry-index*)
    (setf *wasm2-next-entry-index* 500))
  (let* ((backend (find-backend :wasm32))
         (*target-ftd* (or (and backend (backend-target-foreign-type-data backend))
                           *target-ftd*))
         (results nil))
    (let ((*wasm2-enable-const-pool* t)
          (*wasm2-collect-module-debug* t))
      (declare (special *wasm2-enable-const-pool*
                        *wasm2-collect-module-debug*))
      (dolist (entry *wasm-phase0a-test-functions*)
        (destructuring-bind (name lambda-form) entry
          (multiple-value-bind (fn warnings)
              (compile-named-function lambda-form :name name :target :wasm32)
            (declare (ignore warnings))
            (push (list :name (symbol-name name)
                        :entry-index (function-entry-index fn))
                  results)))))
  (nreverse results)))

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/compile-phase0a-tests.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun load-wasm-backend ()
  (let* ((root (repo-root-from-script)))
    (flet ((load-rel (path)
             (load (merge-pathnames path root))))
      (let ((*warn-if-redefine-kernel* nil))
        (let ((*compile-definitions* nil))
          (load-rel "compiler/ARM/arm-arch.lisp")
          (load-rel "lib/armenv.lisp")
          (load-rel "lib/wasmenv.lisp")
          (load-rel "compiler/backend.lisp")
          (unless (boundp 'platform-cpu-wasm)
            (defconstant platform-cpu-wasm (ash 4 3)))
          (unless (boundp 'platform-os-wasm)
            (defconstant platform-os-wasm 7))
          (load-rel "compiler/WASM/wasm-arch.lisp")
          (load-rel "compiler/WASM/wasm-vinsns.lisp"))
        (let ((*compile-definitions* t))
          ;; Register %fixnum-set and %fixnum-set-natural as acode operators.
          ;; Find empty () slots in the live operator table and fill them.
          (let ((filled 0))
            (do ((tail *next-nx-operators* (cdr tail)))
                ((or (null tail) (>= filled 2)))
              (when (null (car tail))
                (cond ((= filled 0)
                       (setf (car tail)
                             (list '%fixnum-set
                                   (logior operator-single-valued-mask
                                           operator-acode-subforms-mask)
                                   t))
                       (incf filled))
                      ((= filled 1)
                       (setf (car tail)
                             (list '%fixnum-set-natural
                                   (logior operator-single-valued-mask
                                           operator-acode-subforms-mask)
                                   'natural))
                       (incf filled)))))
            (format t "~&DIAG: Patched ~d operators into table~%" filled)
            (unless (= filled 2)
              (error "Failed to find empty slots for %fixnum-set operators")))
          (load-rel "compiler/WASM/wasm-ffi.lisp")
          (load-rel "compiler/acode-rewrite.lisp")
          (load-rel "compiler/nx1.lisp")
          ;; Refresh fasl dumping to pick up local compiler edits.
          (load-rel "lib/nfcomp.lisp")
          (load-rel "compiler/WASM/wasm2.lisp")
          (load-rel "compiler/WASM/wasm-backend.lisp"))))))

(defun sorted-compiled-modules ()
  (sort (copy-list %wasm-compiled-modules%)
        #'<
        :key (lambda (entry) (svref entry 2))))

(defun module-gc-root-policy-mode (entry)
  (let ((mode (and (> (length entry) 5) (svref entry 5))))
    (when (and mode (fixnump mode) (>= mode 0))
      mode)))

(defun module-gc-root-boundary-op-index (debug-entries)
  (let ((index (make-hash-table :test #'eql)))
    (dolist (entry debug-entries index)
      (let* ((entry-index (getf entry :entry-index))
             (ops (getf entry :gc-root-boundary-ops)))
        (when (and (fixnump entry-index)
                   (listp ops)
                   (every #'stringp ops))
          (setf (gethash entry-index index) ops))))))

(defun write-module-bundle (output-path functions modules &key debug-entries)
  (let ((boundary-index (module-gc-root-boundary-op-index debug-entries)))
  (ensure-directories-exist output-path)
  (with-open-file (out output-path
                       :direction :output
                       :if-exists :supersede
                       :if-does-not-exist :create)
    (write-char #\{ out)
    (write-string "\"functions\":[" out)
    (loop for fn in functions
          for idx from 0
          do (when (> idx 0) (write-char #\, out))
             (write-char #\{ out)
             (write-string "\"name\":" out)
             (json-write-string out (getf fn :name))
             (write-string ",\"entryIndex\":" out)
             (princ (getf fn :entry-index) out)
             (write-char #\} out))
    (write-string "],\"modules\":[" out)
    (loop for entry in modules
          for idx from 0
          do (when (> idx 0) (write-char #\, out))
             (write-char #\{ out)
             (write-string "\"exportName\":" out)
             (json-write-string out (svref entry 1))
             (write-string ",\"entryIndex\":" out)
             (princ (svref entry 2) out)
             (write-string ",\"moduleVersion\":" out)
             (princ (svref entry 3) out)
             (write-string ",\"moduleBytes\":" out)
             (json-write-bytes out (svref entry 0))
             (when (and (> (length entry) 4) (svref entry 4))
               (write-string ",\"constPoolBytes\":" out)
               (json-write-bytes out (svref entry 4)))
             (let ((gc-mode (module-gc-root-policy-mode entry)))
               (when gc-mode
                 (write-string ",\"gcRootPolicyMode\":" out)
                 (princ gc-mode out)))
             (let ((gc-boundary-ops (gethash (svref entry 2) boundary-index)))
               (when gc-boundary-ops
                 (write-string ",\"gcRootBoundaryOps\":" out)
                 (json-write-string-list out gc-boundary-ops)))
             (write-char #\} out))
    (write-char #\] out)
    (let ((rows nil))
      (dolist (entry modules)
        (let ((gc-mode (module-gc-root-policy-mode entry)))
          (when gc-mode
            (push (cons (svref entry 2) gc-mode) rows))))
      (setf rows (nreverse rows))
      (when rows
        (write-string ",\"gcRootPolicyModes\":{" out)
        (loop for row in rows
              for idx from 0
              do (when (> idx 0) (write-char #\, out))
                 (json-write-string out (princ-to-string (car row)))
                 (write-char #\: out)
                 (princ (cdr row) out))
        (write-char #\} out)))
    (let ((rows nil))
      (dolist (entry modules)
        (let ((gc-boundary-ops (gethash (svref entry 2) boundary-index)))
          (when gc-boundary-ops
            (push (cons (svref entry 2) gc-boundary-ops) rows))))
      (setf rows (nreverse rows))
      (when rows
        (write-string ",\"gcRootBoundaryOps\":{" out)
        (loop for row in rows
              for idx from 0
              do (when (> idx 0) (write-char #\, out))
                 (json-write-string out (princ-to-string (car row)))
                 (write-char #\: out)
                 (json-write-string-list out (cdr row)))
        (write-char #\} out)))
    (write-char #\} out)
    (terpri out))))

(defun main ()
  (load-wasm-backend)
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (output (or (cdr (assoc :output argv))
                     (namestring (merge-pathnames "build/wasm32/modules/wasm-phase0a-tests.json")))))
    (let* ((functions (compile-phase0a-tests))
           (modules (sorted-compiled-modules))
           (debug-entries (copy-list *wasm2-compiled-modules-debug*)))
      (write-module-bundle output functions modules :debug-entries debug-entries)
      (format t "Phase 0A tests: compiled ~d test functions into ~d modules~%"
              (length functions) (length modules))
      (format t "Wrote to ~a~%" output)))
  (finish-output))

(main)
(ccl:quit)
