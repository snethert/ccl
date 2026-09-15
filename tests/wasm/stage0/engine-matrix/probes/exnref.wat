(module (tag $t) (func (local exnref)
  (block $h (result exnref) (try_table (catch_ref $t $h) (throw $t)) (return))
  (local.set 0) (throw_ref (local.get 0))))
