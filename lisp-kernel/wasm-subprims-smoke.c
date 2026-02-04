/*
 * WASM32 smoke-test subprims
 *
 * These provide "safe" implementations for a small set of subprims so we can
 * validate `call_indirect` dispatch early, without bringing up `start_lisp`.
 */

#ifdef WASM32

__attribute__((used, visibility("default"), export_name("_SPunused1")))
void
_SPunused1(void)
{
  /* no-op */
}

__attribute__((used, visibility("default"), export_name("_SPunused2")))
void
_SPunused2(void)
{
  /* no-op */
}

#endif /* WASM32 */
