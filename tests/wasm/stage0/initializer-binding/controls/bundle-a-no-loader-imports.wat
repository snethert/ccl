;; Control: bundle A assembled without the loader service imports the manifest declares.
(module
  (import "env" "memory" (memory 2 2))
  (func (export "init_symbols") (result i32) (i32.store (i32.const 8192) (i32.const 4)) (i32.const 21337))
  (func (export "init_readers") (result i32) (i32.const 21060)))
