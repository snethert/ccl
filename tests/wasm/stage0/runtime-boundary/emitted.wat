;; Final EH encoding: try_table in the adapter, throw/tag here.
(module
  (tag $exit (export "exit") (param i32))
  (tag $cleanup (export "cleanup") (param i32))
  (func (export "raise") (param $tcr i32)
    (throw $exit (local.get $tcr))))
