
;;; A lexpr points at the count word of a retained root frame. Validate that
;;; frame before reading the count; an arbitrary fixnum is not a stack pointer.
(defun bootstrap-lexpr-count (pointer length)
  (let ((frame (temporary)) (limit (temporary)) (count (temporary)))
    (with-output-to-string (s)
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top))"
        frame (b-load wasm32::tcr.root_head) limit)
      (write-string "(block $lexpr_found (loop $lexpr_search" s)
      (write-string
        (b-condition
          (b-wat "(i32.or (i32.or (i32.eqz (local.get ~a)) (i32.and (local.get ~a) (i32.const 3))) (i32.or (i32.lt_u (local.get ~a) ~a) (i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const 12)) (i64.extend_i32_u (local.get ~a)))))"
            frame frame frame (b-load wasm32::tcr.vsp_base) frame limit) 5) s)
      (format s "(local.set ~a (i32.load offset=4 (local.get ~a)))" count frame)
      (write-string
        (b-condition
          (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.add (i64.const 8) (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 4)))) (i64.extend_i32_u (local.get ~a)))"
            frame count limit) 5) s)
      (format s "(br_if $lexpr_found (i32.eq ~a (i32.add (local.get ~a) (i32.const 8)))) (local.set ~a (local.get ~a)) (local.set ~a (i32.load (local.get ~a))) (br $lexpr_search)))"
        pointer frame limit frame frame frame)
      (format s "(local.set ~a (i32.load ~a))" length pointer)
      (write-string
        (b-condition
          (b-wat "(i32.or (i32.or (i32.and (local.get ~a) (i32.const 3)) (i32.lt_s (local.get ~a) (i32.const 0))) (i32.ne (i32.add (i32.shr_u (local.get ~a) (i32.const 2)) (i32.const 1)) (local.get ~a)))"
            length length length count) 5) s)
      (format s "(local.set ~a (i32.shr_u (local.get ~a) (i32.const 2)))" length length))))

(defun bootstrap-lexpr-copy (cursor length index prefix destination offset)
  ;; Source arguments run backwards after the tagged count. No call can move
  ;; them between this load and publication in the ordinary APPLY root frame.
  (b-wat "(block $lexpr_done (loop $lexpr_copy (br_if $lexpr_done (i32.ge_u (local.get ~a) (i32.add (local.get ~a) (i32.const ~d)))) (i32.store (i32.add (local.get ~a) (i32.add (i32.const ~d) (i32.mul (local.get ~a) (i32.const 4)))) (i32.load (i32.add (local.get ~a) (i32.mul (i32.sub (i32.add (local.get ~a) (i32.const ~d)) (local.get ~a)) (i32.const 4))))) (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $lexpr_copy)))"
    index length prefix destination offset index cursor length prefix index index index))
