"""Single-site compiler mutations, recompiled through the real front end."""
def mutations(source):
 def change(old,new):
  assert source.count(old)==1,(old,source.count(old));return source.replace(old,new)
 edits={'capture-value-not-cell': ('base (b-cell-reference v)))', 'base (b-read-variable v)))'),
  'inherited-first-slot': ('(+ 4 (* 4 n)))', '(+ 4 (* 0 n)))'),
  'capture-cells-alias': ('(b-at base (+ 1 (* 8 i)))', '(b-at base (+ 1 (* 0 i)))'),
  'captured-write-cdr': ('(b-at (b-cell-reference root) 3)', '(b-at (b-cell-reference root) -1)'),
  'closure-capacity': ('(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.extend_i32_u ~a))',
                       '(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) '
                       '(i64.extend_i32_u ~a)))'),
  'closure-bound-root': ('(length *b-bound-vars*))))\n           (wat',
                         '(max 0 (1- (length *b-bound-vars*))))))\n           (wat'),
  'exception-ownership': ('(write-string restore s)\n'
                          '             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)',
                          '(write-string "" s)\n'
                          '             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)'),
  'local-group-first-function': ('(b-bind-value v (b-make-closure f))',
                                 '(b-bind-value v (b-make-closure (first (second args))))'),
  'local-function-binding-nil': ('(b-bind-value v (b-make-closure f))',
                                 '(b-bind-value v (b-wat "(block (result i32) (drop ~a) (i32.const 77825))" '
                                 '(b-make-closure f)))'),
  'local-self-nil': ('(eq op \'b-self) "(local.get $self)"', '(eq op \'b-self) "(i32.const 77825)"'),
  'inline-arguments-reversed': ('loop for val in vals for i from 0', 'loop for val in (reverse vals) for i from 0'),
  'inline-required-first-value': ('(+ 8 (* 4 i)) base)) s))\n          (when rest',
                                  '(+ 8 (* 0 i)) base)) s))\n          (when rest'),
  'inline-rest-first-value': ('(* 4 (+ (length required) i))', '(* 4 (+ (length required) 0))'),
  'inline-rest-nil': ('(write-string (b-bind-value rest\n                (if (zerop count)',
                      '(write-string (b-bind-value rest\n                (if (or t (zerop count))'),
  'inline-defaults-nil': ('(b-scalar init))) s))\n          (write-string (b-multiple body)',
                          '"(i32.const 77825)")) s))\n          (write-string (b-multiple body)'),
  'metadata-root-count': (':bound-words (length *b-bound-vars*)', ':bound-words (1+ (length *b-bound-vars*))')}
 return {name:change(*pair) for name,pair in edits.items()}

def source_regression(source):
 from pathlib import Path
 old=(Path(__file__).parent/"rejected-normalizer.lisp").read_text()
 return source[:source.index("(defun b-normalize-literal-apply")]+old
