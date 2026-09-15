;; Prohibited legacy encoding. Retained only to show the encoding pin refuses it.
(module (tag $t) (func (try (do (throw $t)) (catch $t))))
