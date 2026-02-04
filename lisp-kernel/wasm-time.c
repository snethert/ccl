/*
 * WASM32 time functions (no WASI runtime).
 *
 * We compile with --target=wasm32-wasi for headers, but link freestanding.
 * Provide `time(3)`, `gettimeofday(2)`, and `clock_gettime(2)` by routing
 * through the JS microkernel (kernel_request ABI).
 */

#ifdef WASM32

#include "wasm-host.h"

#include <errno.h>
#include <stdint.h>
#include <sys/time.h>
#include <time.h>

static int
wasm_time_now_ms(uint64_t *out_ms)
{
  uint64_t ms = 0;
  int32_t r = wasm_kernel_time_now(&ms);
  if (r < 0) {
    errno = -r;
    return -1;
  }
  if (out_ms) {
    *out_ms = ms;
  }
  return 0;
}

int
gettimeofday(struct timeval *__restrict tv, void *__restrict tzp)
{
  (void)tzp;
  uint64_t ms = 0;
  if (wasm_time_now_ms(&ms) < 0) {
    return -1;
  }
  if (tv) {
    tv->tv_sec = (time_t)(ms / 1000u);
    tv->tv_usec = (suseconds_t)((ms % 1000u) * 1000u);
  }
  return 0;
}

int
clock_gettime(clockid_t clk_id, struct timespec *tp)
{
  uint64_t ms = 0;
  uint64_t out_ms = 0;

  if (tp == NULL) {
    errno = EINVAL;
    return -1;
  }
  if (wasm_time_now_ms(&ms) < 0) {
    return -1;
  }

  out_ms = ms;

  /* Best-effort monotonic: derive from wall clock but clamp and subtract an
   * origin so it is non-decreasing in the presence of backwards adjustments.
   */
#ifdef CLOCK_MONOTONIC
  if ((clk_id == CLOCK_MONOTONIC) ||
#ifdef CLOCK_MONOTONIC_COARSE
      (clk_id == CLOCK_MONOTONIC_COARSE) ||
#endif
#ifdef CLOCK_MONOTONIC_RAW
      (clk_id == CLOCK_MONOTONIC_RAW) ||
#endif
#ifdef CLOCK_BOOTTIME
      (clk_id == CLOCK_BOOTTIME) ||
#endif
#ifdef CLOCK_BOOTTIME_ALARM
      (clk_id == CLOCK_BOOTTIME_ALARM) ||
#endif
      0) {
    static uint64_t origin_ms = 0;
    static uint64_t last_ms = 0;
    if (origin_ms == 0) {
      origin_ms = ms;
      last_ms = 0;
    }
    if (ms >= origin_ms) {
      out_ms = ms - origin_ms;
    } else {
      out_ms = 0;
    }
    if (out_ms < last_ms) {
      out_ms = last_ms;
    } else {
      last_ms = out_ms;
    }
  } else
#endif
  {
    /* CLOCK_REALTIME and others: treat as wall clock. */
  }

  tp->tv_sec = (time_t)(out_ms / 1000u);
  tp->tv_nsec = (long)((out_ms % 1000u) * 1000000u);
  return 0;
}

time_t
time(time_t *tloc)
{
  uint64_t ms = 0;
  if (wasm_time_now_ms(&ms) < 0) {
    if (tloc) {
      *tloc = (time_t)-1;
    }
    return (time_t)-1;
  }
  time_t sec = (time_t)(ms / 1000u);
  if (tloc) {
    *tloc = sec;
  }
  return sec;
}

#endif /* WASM32 */

