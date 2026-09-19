(in-package :wasm32-compiler)
(defun b-debugger (condition)
  (let ((symbol (b-special-symbol '*debugger-hook*)))
    (b-wat "(if (i32.eq ~a (i32.const 1)) (then ~a))" (b-load wasm32::tcr.error_service_mode)
      (b-frame 2
        (lambda (root)
          (let ((c (b-wat "(i32.load offset=8 ~a)" root))
                (hook (b-wat "(i32.load offset=12 ~a)" root))
                (depth (temporary)) (exception (b-exception-local)))
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a (call $special_read ~a))
              (if (i32.ne ~a (i32.const 77825)) (then
                (local.set ~a ~a)
                (if (i32.eq (local.get ~a) (i32.const -1)) (then (throw $call_error (i32.const 15))))
                (i32.store offset=184 (global.get $tcr) (i32.add (local.get ~a) (i32.const 1)))
                (block $debug_ok (block $debug_failed (result exnref) (try_table (catch_all_ref $debug_failed) ~a (br $debug_ok)) unreachable)
                  (local.set ~a) (i32.store offset=184 (global.get $tcr) (local.get ~a)) (throw_ref (local.get ~a)))
                (i32.store offset=184 (global.get $tcr) (local.get ~a))))"
              root condition root symbol hook depth (b-load wasm32::tcr.scratch1) depth depth
              (b-special-extent (lambda ()
                (concatenate 'string (b-bind-symbol symbol "(i32.const 77825)")
                  (b-discard-handler hook (make-b-raw-code :text c) (make-b-raw-code :text hook)))))
              exception depth exception depth)))))))
