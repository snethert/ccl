/*
 * WASM32 kernel stubs
 *
 * These definitions exist to let the WASM kernel link as a freestanding module
 * during early bring-up (no image loader, no OS, no WASI).
 */

#ifdef WASM32

#include "lisp.h"
#include "gc.h"
#include "lisp-exceptions.h"
#include "lisp_globals.h"
#include "wasm-host.h"
#include "wasm-subprims.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <sys/types.h>
#include <limits.h>
#include <string.h>

/* Used by lisp-debug.c for banner/prompt printing. */
pid_t main_thread_pid = 0;

/* pmcl-kernel.c stores the address of these in lisp globals. On other
 * platforms they're code labels; for now they're placeholders.
 */
LispObj ret1valn = 0;
LispObj nvalret = 0;
LispObj popj = 0;
extern LispObj lisp_nil;
__attribute__((import_module("ccl"), import_name("wasm_host_install_const_pool")))
int32_t wasm_host_install_const_pool(uint32_t entry_index);
extern int lisp_open(char *path, int flags, mode_t mode);
extern int lisp_close(int fd);
extern OSErr save_application(int fd, Boolean egc_was_enabled);

static const uint8_t wasm_ui_payload_Ready[] = {
  49, 66, 73, 85, 1, 0, 0, 0, 14, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  3, 0, 0, 0, 100, 105, 118, 6, 0, 0, 0, 98, 117, 116, 116, 111, 110, 14, 0, 0, 0, 100, 97, 116,
  97, 45, 119, 105, 100, 103, 101, 116, 45, 105, 100, 11, 0, 0, 0, 100, 101, 109, 111, 45, 98, 117, 116, 116,
  111, 110, 5, 0, 0, 0, 67, 108, 105, 99, 107, 10, 0, 0, 0, 100, 101, 109, 111, 45, 108, 97, 98, 101,
  108, 5, 0, 0, 0, 82, 101, 97, 100, 121, 6, 0, 0, 0, 99, 97, 110, 118, 97, 115, 11, 0, 0, 0,
  100, 101, 109, 111, 45, 99, 97, 110, 118, 97, 115, 17, 0, 0, 0, 100, 97, 116, 97, 45, 99, 97, 110, 118,
  97, 115, 45, 115, 99, 101, 110, 101, 198, 0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116,
  111, 109, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100,
  115, 34, 58, 123, 34, 120, 34, 58, 48, 44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58,
  53, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 53, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58,
  123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34,
  116, 111, 112, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110,
  100, 115, 34, 58, 123, 34, 120, 34, 58, 53, 44, 34, 121, 34, 58, 53, 44, 34, 119, 105, 100, 116, 104, 34,
  58, 50, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 50, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34,
  58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 102, 48, 48, 34, 125, 125, 93, 10, 0, 0, 0, 100, 101,
  109, 111, 45, 119, 101, 98, 103, 108, 16, 0, 0, 0, 100, 97, 116, 97, 45, 119, 101, 98, 103, 108, 45, 115,
  99, 101, 110, 101, 198, 0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109, 34, 44,
  34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123,
  34, 120, 34, 58, 48, 44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 52, 48, 44, 34,
  104, 101, 105, 103, 104, 116, 34, 58, 52, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105,
  108, 108, 34, 58, 34, 35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111, 112, 34,
  44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58,
  123, 34, 120, 34, 58, 56, 44, 34, 121, 34, 58, 56, 44, 34, 119, 105, 100, 116, 104, 34, 58, 49, 54, 44,
  34, 104, 101, 105, 103, 104, 116, 34, 58, 49, 54, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102,
  105, 108, 108, 34, 58, 34, 35, 48, 102, 48, 34, 125, 125, 93, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255,
  255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0, 5, 0,
  0, 0, 6, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 1, 0, 0, 0, 1, 0,
  0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 2, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 4, 0, 0, 0, 1, 0, 0, 0, 0, 0,
  0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0,
  0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255,
  255, 255, 6, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0, 2, 0,
  0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 0, 9, 0,
  0, 0, 3, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255,
  255, 255, 7, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 11, 0,
  0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 3, 0, 0, 0, 13, 0, 0, 0, 0, 0, 0, 0,
};
static const uint32_t wasm_ui_payload_Ready_len = 862;

static const uint8_t wasm_ui_payload_Clicked[] = {
  49, 66, 73, 85, 1, 0, 0, 0, 14, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  3, 0, 0, 0, 100, 105, 118, 6, 0, 0, 0, 98, 117, 116, 116, 111, 110, 14, 0, 0, 0, 100, 97, 116,
  97, 45, 119, 105, 100, 103, 101, 116, 45, 105, 100, 11, 0, 0, 0, 100, 101, 109, 111, 45, 98, 117, 116, 116,
  111, 110, 5, 0, 0, 0, 67, 108, 105, 99, 107, 10, 0, 0, 0, 100, 101, 109, 111, 45, 108, 97, 98, 101,
  108, 7, 0, 0, 0, 67, 108, 105, 99, 107, 101, 100, 6, 0, 0, 0, 99, 97, 110, 118, 97, 115, 11, 0,
  0, 0, 100, 101, 109, 111, 45, 99, 97, 110, 118, 97, 115, 17, 0, 0, 0, 100, 97, 116, 97, 45, 99, 97,
  110, 118, 97, 115, 45, 115, 99, 101, 110, 101, 198, 0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111,
  116, 116, 111, 109, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117,
  110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 48, 44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104,
  34, 58, 53, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 53, 48, 125, 44, 34, 112, 114, 111, 112, 115,
  34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34,
  58, 34, 116, 111, 112, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111,
  117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 53, 44, 34, 121, 34, 58, 53, 44, 34, 119, 105, 100, 116,
  104, 34, 58, 50, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 50, 48, 125, 44, 34, 112, 114, 111, 112,
  115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 102, 48, 48, 34, 125, 125, 93, 10, 0, 0, 0,
  100, 101, 109, 111, 45, 119, 101, 98, 103, 108, 16, 0, 0, 0, 100, 97, 116, 97, 45, 119, 101, 98, 103, 108,
  45, 115, 99, 101, 110, 101, 198, 0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109,
  34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34,
  58, 123, 34, 120, 34, 58, 48, 44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 52, 48,
  44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 52, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34,
  102, 105, 108, 108, 34, 58, 34, 35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111,
  112, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115,
  34, 58, 123, 34, 120, 34, 58, 56, 44, 34, 121, 34, 58, 56, 44, 34, 119, 105, 100, 116, 104, 34, 58, 49,
  54, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 49, 54, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123,
  34, 102, 105, 108, 108, 34, 58, 34, 35, 48, 102, 48, 34, 125, 125, 93, 1, 0, 0, 0, 0, 0, 0, 0,
  255, 255, 255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0,
  5, 0, 0, 0, 6, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 1, 0, 0, 0,
  1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0,
  2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 4, 0, 0, 0, 1, 0, 0, 0,
  0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0,
  3, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  255, 255, 255, 255, 6, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0,
  2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 0,
  9, 0, 0, 0, 3, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
  255, 255, 255, 255, 7, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0,
  11, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 3, 0, 0, 0, 13, 0, 0, 0, 0, 0, 0, 0,
};
static const uint32_t wasm_ui_payload_Clicked_len = 864;

static const uint8_t wasm_ui_payload_Canvas_demo_canvas_top[] = {
  49, 66, 73, 85, 1, 0, 0, 0, 14, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  3, 0, 0, 0, 100, 105, 118, 6, 0, 0, 0, 98, 117, 116, 116, 111, 110, 14, 0, 0, 0, 100, 97, 116,
  97, 45, 119, 105, 100, 103, 101, 116, 45, 105, 100, 11, 0, 0, 0, 100, 101, 109, 111, 45, 98, 117, 116, 116,
  111, 110, 5, 0, 0, 0, 67, 108, 105, 99, 107, 10, 0, 0, 0, 100, 101, 109, 111, 45, 108, 97, 98, 101,
  108, 22, 0, 0, 0, 67, 97, 110, 118, 97, 115, 32, 100, 101, 109, 111, 45, 99, 97, 110, 118, 97, 115, 58,
  116, 111, 112, 6, 0, 0, 0, 99, 97, 110, 118, 97, 115, 11, 0, 0, 0, 100, 101, 109, 111, 45, 99, 97,
  110, 118, 97, 115, 17, 0, 0, 0, 100, 97, 116, 97, 45, 99, 97, 110, 118, 97, 115, 45, 115, 99, 101, 110,
  101, 198, 0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109, 34, 44, 34, 107, 105,
  110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34,
  58, 48, 44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 53, 48, 44, 34, 104, 101, 105,
  103, 104, 116, 34, 58, 53, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34,
  58, 34, 35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111, 112, 34, 44, 34, 107,
  105, 110, 100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120,
  34, 58, 53, 44, 34, 121, 34, 58, 53, 44, 34, 119, 105, 100, 116, 104, 34, 58, 50, 48, 44, 34, 104, 101,
  105, 103, 104, 116, 34, 58, 50, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108,
  34, 58, 34, 35, 102, 48, 48, 34, 125, 125, 93, 10, 0, 0, 0, 100, 101, 109, 111, 45, 119, 101, 98, 103,
  108, 16, 0, 0, 0, 100, 97, 116, 97, 45, 119, 101, 98, 103, 108, 45, 115, 99, 101, 110, 101, 198, 0, 0,
  0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109, 34, 44, 34, 107, 105, 110, 100, 34, 58,
  34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 48, 44, 34,
  121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 52, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34,
  58, 52, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 48,
  48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111, 112, 34, 44, 34, 107, 105, 110, 100, 34,
  58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 56, 44,
  34, 121, 34, 58, 56, 44, 34, 119, 105, 100, 116, 104, 34, 58, 49, 54, 44, 34, 104, 101, 105, 103, 104, 116,
  34, 58, 49, 54, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35,
  48, 102, 48, 34, 125, 125, 93, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 0,
  0, 0, 0, 4, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 1,
  0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2,
  0, 0, 0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 255, 255, 255, 255, 4, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0,
  0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 0,
  0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 6, 0, 0, 0, 1,
  0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2,
  0, 0, 0, 3, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 0, 9, 0, 0, 0, 3, 0, 0, 0, 10,
  0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0, 2,
  0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 11, 0, 0, 0, 0, 0, 0, 0, 12,
  0, 0, 0, 3, 0, 0, 0, 13, 0, 0, 0, 0, 0, 0, 0,
};
static const uint32_t wasm_ui_payload_Canvas_demo_canvas_top_len = 879;

static const uint8_t wasm_ui_payload_WebGL_demo_webgl_top[] = {
  49, 66, 73, 85, 1, 0, 0, 0, 14, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  3, 0, 0, 0, 100, 105, 118, 6, 0, 0, 0, 98, 117, 116, 116, 111, 110, 14, 0, 0, 0, 100, 97, 116,
  97, 45, 119, 105, 100, 103, 101, 116, 45, 105, 100, 11, 0, 0, 0, 100, 101, 109, 111, 45, 98, 117, 116, 116,
  111, 110, 5, 0, 0, 0, 67, 108, 105, 99, 107, 10, 0, 0, 0, 100, 101, 109, 111, 45, 108, 97, 98, 101,
  108, 20, 0, 0, 0, 87, 101, 98, 71, 76, 32, 100, 101, 109, 111, 45, 119, 101, 98, 103, 108, 58, 116, 111,
  112, 6, 0, 0, 0, 99, 97, 110, 118, 97, 115, 11, 0, 0, 0, 100, 101, 109, 111, 45, 99, 97, 110, 118,
  97, 115, 17, 0, 0, 0, 100, 97, 116, 97, 45, 99, 97, 110, 118, 97, 115, 45, 115, 99, 101, 110, 101, 198,
  0, 0, 0, 91, 123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109, 34, 44, 34, 107, 105, 110, 100,
  34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 48,
  44, 34, 121, 34, 58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 53, 48, 44, 34, 104, 101, 105, 103, 104,
  116, 34, 58, 53, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34,
  35, 48, 48, 48, 34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111, 112, 34, 44, 34, 107, 105, 110,
  100, 34, 58, 34, 114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58,
  53, 44, 34, 121, 34, 58, 53, 44, 34, 119, 105, 100, 116, 104, 34, 58, 50, 48, 44, 34, 104, 101, 105, 103,
  104, 116, 34, 58, 50, 48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58,
  34, 35, 102, 48, 48, 34, 125, 125, 93, 10, 0, 0, 0, 100, 101, 109, 111, 45, 119, 101, 98, 103, 108, 16,
  0, 0, 0, 100, 97, 116, 97, 45, 119, 101, 98, 103, 108, 45, 115, 99, 101, 110, 101, 198, 0, 0, 0, 91,
  123, 34, 105, 100, 34, 58, 34, 98, 111, 116, 116, 111, 109, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34, 114,
  101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 48, 44, 34, 121, 34,
  58, 48, 44, 34, 119, 105, 100, 116, 104, 34, 58, 52, 48, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58, 52,
  48, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 48, 48, 48,
  34, 125, 125, 44, 123, 34, 105, 100, 34, 58, 34, 116, 111, 112, 34, 44, 34, 107, 105, 110, 100, 34, 58, 34,
  114, 101, 99, 116, 34, 44, 34, 98, 111, 117, 110, 100, 115, 34, 58, 123, 34, 120, 34, 58, 56, 44, 34, 121,
  34, 58, 56, 44, 34, 119, 105, 100, 116, 104, 34, 58, 49, 54, 44, 34, 104, 101, 105, 103, 104, 116, 34, 58,
  49, 54, 125, 44, 34, 112, 114, 111, 112, 115, 34, 58, 123, 34, 102, 105, 108, 108, 34, 58, 34, 35, 48, 102,
  48, 34, 125, 125, 93, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 0, 0, 0,
  0, 4, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 1, 0, 0,
  0, 0, 0, 0, 0, 255, 255, 255, 255, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0,
  0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 255, 255, 255, 255, 4, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0,
  0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0,
  0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 6, 0, 0, 0, 1, 0, 0,
  0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
  0, 3, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 0, 9, 0, 0, 0, 3, 0, 0, 0, 10, 0, 0,
  0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 7, 0, 0, 0, 2, 0, 0,
  0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 11, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0,
  0, 3, 0, 0, 0, 13, 0, 0, 0, 0, 0, 0, 0,
};
static const uint32_t wasm_ui_payload_WebGL_demo_webgl_top_len = 877;

enum {
  WASM_SUBPRIM_FUNCALL_INDEX = 24,
  WASM_SUBPRIM_MKCATCH1V_INDEX = 25,
  WASM_SUBPRIM_MKUNWIND_INDEX = 27,
  WASM_SUBPRIM_VALUES_INDEX = 37,
  WASM_SUBPRIM_NTHROWVALUES_INDEX = 40,
  WASM_SUBPRIM_NTHROW1VALUE_INDEX = 41,
  /* Keep in sync with scripts/wasm/make_minimal_image.py and load-image.mjs. */
  WASM_BOOT_ENTRY_INDEX = 200,
  /* Smoke-test entrypoint for the WASM calling convention. */
  WASM_TEST_ENTRY_INDEX = 201,
  /* Constant-return entrypoint for compiler IR bring-up. */
  WASM_CONST_ENTRY_INDEX = 202
};

static inline LispObj
wasm_subprim_fixnum(uint32_t index)
{
  return box_fixnum(index);
}

static inline LispObj
wasm_nrs_symbol_lispobj(lispsymbol *sym)
{
  return ptr_to_lispobj((BytePtr)sym + fulltag_misc);
}

typedef void (*wasm_lisp_fn)(void);

static inline void
wasm_call_entry_index(uint32_t index)
{
  ((wasm_lisp_fn)(uintptr_t)index)();
}

static void
wasm_call_lisp_function(TCR *tcr, LispObj fn_value)
{
  if (fn_value == (LispObj)nil_value) {
    __builtin_trap();
  }

  if (fulltag_of(fn_value) != fulltag_misc) {
    __builtin_trap();
  }

  LispObj header = header_of(fn_value);
  int subtag = header_subtag(header);
  if (subtag == subtag_symbol) {
    lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(fn_value));
    fn_value = sym->fcell;
    if (fulltag_of(fn_value) != fulltag_misc) {
      __builtin_trap();
    }
    header = header_of(fn_value);
    subtag = header_subtag(header);
  }

  if (subtag != subtag_function && subtag != subtag_pseudofunction) {
    __builtin_trap();
  }

  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  LispObj entry = deref(fn_value, 1);
  if (tag_of(entry) != tag_fixnum) {
    __builtin_trap();
  }

  {
    uint32_t entry_index = (uint32_t)unbox_fixnum(entry);
    uint32_t mode = wasm_lookup_entry_gc_root_policy_mode(entry_index);
    wasm_publish_gc_root_policy_mode(mode);
    wasm_call_entry_index(entry_index);
  }
}

static int
wasm_interrupts_enabled(TCR *tcr)
{
  LispObj *tlb = tcr->tlb_pointer;
  if (tlb == NULL) {
    return 0;
  }
  LispObj level = tlb[INTERRUPT_LEVEL_BINDING_INDEX];
  if (tag_of(level) != tag_fixnum) {
    return 0;
  }
  return unbox_fixnum(level) >= 0;
}

static int
wasm_maybe_deliver_interrupt(TCR *tcr)
{
  if (tcr == NULL) {
    return 0;
  }
  if (tcr->interrupt_pending <= 0) {
    return 0;
  }
  if (!wasm_interrupts_enabled(tcr)) {
    return 0;
  }

  tcr->wasm_gprs[arg_z] = lisp_nil;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  wasm_call_lisp_function(tcr, wasm_nrs_symbol_lispobj(&nrs_CMAIN));
  return tcr->wasm_pending_throw ? 1 : 0;
}

static uint32_t wasm_subprims_ready = 0;
static LispObj wasm_last_compiled_modules = 0;
LispObj wasm_funcall1(LispObj fn_value, LispObj arg0);
uint32_t wasm_subprim_nonlocal_exit_coherence_selftest(void);
static LispObj wasm_find_package_named_bytes(const uint8_t *bytes, uint32_t len);
static LispObj wasm_find_symbol_named_bytes(const uint8_t *name, uint32_t len, LispObj package);

enum {
  WASM_TOPLEVEL_EXIT = 0,
  WASM_TOPLEVEL_PENDING_THROW = 1,
  WASM_TOPLEVEL_YIELD = 2
};

static void
wasm_maybe_refresh_compiled_modules(void)
{
  LispObj registry = nrs_WASM_COMPILED_MODULES.vcell;
  if (registry == wasm_last_compiled_modules) {
    return;
  }
  wasm_last_compiled_modules = registry;
  if (registry == lisp_nil) {
    return;
  }
  (void)wasm_kernel_compiled_modules_refresh((uint32_t)registry, (uint32_t)lisp_nil);
}

__attribute__((used, visibility("default"), export_name("wasm_set_subprims_ready")))
void
wasm_set_subprims_ready(uint32_t ready)
{
  if (ready) {
    wasm_subprims_ready = 1u;
    wasm_publish_gc_root_policy_mode(WASM_GC_ROOT_MODE_RUNTIME_DEFAULT);
  } else {
    wasm_subprims_ready = 0u;
    wasm_publish_gc_root_policy_mode(WASM_GC_ROOT_MODE_RUNTIME_BOOTSTRAP);
  }
}

__attribute__((used, visibility("default"), export_name("wasm_get_subprims_ready")))
uint32_t
wasm_get_subprims_ready(void)
{
  return wasm_subprims_ready;
}

__attribute__((used, visibility("default"), export_name("wasm_set_gc_root_policy")))
uint32_t
wasm_set_gc_root_policy(uint32_t policy_mask)
{
  wasm_publish_gc_root_policy(policy_mask);
  return wasm_current_gc_root_policy();
}

__attribute__((used, visibility("default"), export_name("wasm_get_gc_root_policy")))
uint32_t
wasm_get_gc_root_policy(void)
{
  return wasm_current_gc_root_policy();
}

__attribute__((used, visibility("default"), export_name("wasm_set_gc_root_policy_mode")))
uint32_t
wasm_set_gc_root_policy_mode(uint32_t mode)
{
  wasm_publish_gc_root_policy_mode(mode);
  return wasm_current_gc_root_policy_mode();
}

__attribute__((used, visibility("default"), export_name("wasm_get_gc_root_policy_mode")))
uint32_t
wasm_get_gc_root_policy_mode(void)
{
  return wasm_current_gc_root_policy_mode();
}

__attribute__((used, visibility("default"), export_name("wasm_set_entry_gc_root_policy_mode")))
uint32_t
wasm_set_entry_gc_root_policy_mode(uint32_t entry_index, uint32_t mode)
{
  wasm_register_entry_gc_root_policy_mode(entry_index, mode);
  return wasm_lookup_entry_gc_root_policy_mode(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_get_entry_gc_root_policy_mode")))
uint32_t
wasm_get_entry_gc_root_policy_mode(uint32_t entry_index)
{
  return wasm_lookup_entry_gc_root_policy_mode(entry_index);
}

__attribute__((used, visibility("default"), export_name("wasm_clear_entry_gc_root_policy_modes")))
void
wasm_clear_entry_gc_root_policy_modes_export(void)
{
  wasm_clear_entry_gc_root_policy_modes();
}

__attribute__((used, visibility("default"), export_name("wasm_gc_forwarding_selftest")))
uint32_t
wasm_gc_forwarding_selftest_export(void)
{
  return wasm_gc_forwarding_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_cstack_frame_coherence_selftest")))
uint32_t
wasm_cstack_frame_coherence_selftest_export(void)
{
  return wasm_cstack_frame_coherence_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_save_image_direct")))
int32_t
wasm_save_image_direct(uint32_t path_ptr, uint32_t path_len, uint32_t egc_enabled)
{
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
  static const uint8_t save_internal_sym_name[] = {
    '%', 'S', 'A', 'V', 'E', '-', 'A', 'P', 'P', 'L', 'I', 'C', 'A', 'T', 'I', 'O', 'N',
    '-', 'I', 'N', 'T', 'E', 'R', 'N', 'A', 'L'
  };
  if (path_ptr == 0 || path_len == 0) {
    return -EINVAL;
  }

  if (path_len >= 1024u) {
    return -ENAMETOOLONG;
  }

  char path[1024];
  const uint8_t *src = (const uint8_t *)(uintptr_t)path_ptr;
  for (uint32_t i = 0; i < path_len; i++) {
    path[i] = (char)src[i];
  }
  path[path_len] = '\0';

  int fd = lisp_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
  if (fd < 0) {
    return -errno;
  }

  area *active_area = active_dynamic_area;
  Boolean egc_was_enabled = (active_area != NULL) && (active_area->older != NULL);

  TCR *tcr = wasm_get_current_tcr();
  if (tcr != NULL && wasm_subprims_ready) {
    static const char msg_try_lisp_save[] = "WASM save-image: trying %save-application-internal\n";
    static const char msg_lisp_save_ok[] = "WASM save-image: %save-application-internal succeeded\n";
    static const char msg_lisp_save_no_symbol[] = "WASM save-image: %save-application-internal symbol not found\n";
    static const char msg_lisp_save_bad_symbol[] = "WASM save-image: %save-application-internal symbol has unexpected object type\n";
    static const char msg_lisp_save_udf[] = "WASM save-image: %save-application-internal fcell is UDF\n";
    static const char msg_lisp_save_throw[] = "WASM save-image: %save-application-internal signaled throw\n";
    static const char msg_lisp_save_fallback[] = "WASM save-image: %save-application-internal unavailable/failed; fallback save_application\n";
    wasm_host_log(msg_try_lisp_save, (unsigned)(sizeof(msg_try_lisp_save) - 1));
    LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
    LispObj save_sym = (LispObj)0;
    if (ccl_pkg != lisp_nil) {
      save_sym = wasm_find_symbol_named_bytes(
        save_internal_sym_name,
        (uint32_t)sizeof(save_internal_sym_name),
        ccl_pkg);
    }
    if (save_sym == (LispObj)0) {
      save_sym = wasm_find_symbol_named_bytes(
        save_internal_sym_name,
        (uint32_t)sizeof(save_internal_sym_name),
        (LispObj)0);
    }
    if (save_sym == (LispObj)0) {
      wasm_host_log(msg_lisp_save_no_symbol, (unsigned)(sizeof(msg_lisp_save_no_symbol) - 1));
    } else if (!(fulltag_of(save_sym) == fulltag_misc &&
                 header_subtag(header_of(save_sym)) == subtag_symbol)) {
      wasm_host_log(msg_lisp_save_bad_symbol, (unsigned)(sizeof(msg_lisp_save_bad_symbol) - 1));
    } else {
      lispsymbol *save_raw = (lispsymbol *)ptr_from_lispobj(untag(save_sym));
      if (save_raw->fcell == nrs_UDF.vcell) {
        wasm_host_log(msg_lisp_save_udf, (unsigned)(sizeof(msg_lisp_save_udf) - 1));
      } else {
        (void)wasm_funcall1(save_sym, box_fixnum(fd));
        if (!tcr->wasm_pending_throw) {
          wasm_host_log(msg_lisp_save_ok, (unsigned)(sizeof(msg_lisp_save_ok) - 1));
          return 0;
        }
        tcr->wasm_pending_throw = 0;
        wasm_host_log(msg_lisp_save_throw, (unsigned)(sizeof(msg_lisp_save_throw) - 1));
      }
    }
    wasm_host_log(msg_lisp_save_fallback, (unsigned)(sizeof(msg_lisp_save_fallback) - 1));
    (void)lisp_close(fd);
    fd = lisp_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) {
      return -errno;
    }
  } else {
    static const char msg_skip_lisp_save[] = "WASM save-image: no current TCR or subprims not ready; using save_application\n";
    wasm_host_log(msg_skip_lisp_save, (unsigned)(sizeof(msg_skip_lisp_save) - 1));
  }

  if (egc_was_enabled) {
    static const char msg_disable_egc[] =
      "WASM save-image: disabling EGC for direct save path\n";
    wasm_host_log(msg_disable_egc, (unsigned)(sizeof(msg_disable_egc) - 1));
    egc_control(false, active_area->active);
  }

  Boolean save_egc_enabled = (egc_enabled != 0) ? true : egc_was_enabled;
  OSErr err = save_application(fd, save_egc_enabled);

  if (egc_was_enabled) {
    static const char msg_restore_egc[] =
      "WASM save-image: restoring EGC after direct save path\n";
    wasm_host_log(msg_restore_egc, (unsigned)(sizeof(msg_restore_egc) - 1));
    egc_control(true, NULL);
  }

  return (int32_t)err;
}

static uint32_t wasm_ui_demo_phase = 0;

__attribute__((used, visibility("default"), export_name("wasm_ui_demo_turn")))
int32_t
wasm_ui_demo_turn(void)
{
  const uint8_t *payload = wasm_ui_payload_Ready;
  uint32_t payload_len = wasm_ui_payload_Ready_len;

  switch (wasm_ui_demo_phase) {
    case 0:
      payload = wasm_ui_payload_Ready;
      payload_len = wasm_ui_payload_Ready_len;
      break;
    case 1:
      payload = wasm_ui_payload_Clicked;
      payload_len = wasm_ui_payload_Clicked_len;
      break;
    case 2:
      payload = wasm_ui_payload_Canvas_demo_canvas_top;
      payload_len = wasm_ui_payload_Canvas_demo_canvas_top_len;
      break;
    default:
      payload = wasm_ui_payload_WebGL_demo_webgl_top;
      payload_len = wasm_ui_payload_WebGL_demo_webgl_top_len;
      break;
  }

  if (wasm_ui_demo_phase < 3) {
    wasm_ui_demo_phase++;
  }

  return wasm_kernel_ui_render(payload, payload_len);
}

static int
wasm_toplevel_loop(TCR *tcr)
{
  for (;;) {
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      return -1;
    }
    if (wasm_maybe_deliver_interrupt(tcr)) {
      return WASM_TOPLEVEL_PENDING_THROW;
    }
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    if (vsp_ptr == NULL) {
      return -1;
    }
    LispObj topfn = *vsp_ptr;
    if (topfn == lisp_nil) {
      return 0;
    }

    tcr->wasm_gprs[arg_z] = nrs_TOPLCATCH.vcell;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));

    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[nargs] = box_fixnum(0);
    tcr->wasm_gprs[nfn] = topfn;
    tcr->wasm_gprs[Rfn] = topfn;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));
    if (tcr->wasm_pending_throw) {
      wasm_maybe_refresh_compiled_modules();
      return WASM_TOPLEVEL_PENDING_THROW;
    }

    LispObj result = tcr->wasm_gprs[arg_z];
    tcr->wasm_gprs[arg_z] = lisp_nil;
    tcr->wasm_gprs[imm0] = box_fixnum(1);
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
    if (tcr->wasm_pending_throw) {
      tcr->wasm_pending_throw = 0;
    }
    wasm_maybe_refresh_compiled_modules();

    if (result != lisp_nil) {
      return WASM_TOPLEVEL_YIELD;
    }
  }
}

static LispObj *
wasm_toplevel_slot(TCR *tcr)
{
  if (tcr == NULL || tcr->vs_area == NULL) {
    return NULL;
  }
  BytePtr high = tcr->vs_area->high;
  if (high == NULL) {
    return NULL;
  }
  return (LispObj *)(high - node_size);
}

static LispObj *
wasm_vsp_empty(TCR *tcr)
{
  if (tcr == NULL || tcr->vs_area == NULL) {
    return NULL;
  }
  return (LispObj *)tcr->vs_area->high;
}

__attribute__((used, visibility("default"), export_name("wasm_get_tcr_toplevel_function")))
LispObj
wasm_get_tcr_toplevel_function(LispObj raw_tcr)
{
  TCR *tcr = (TCR *)raw_tcr;
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *slot = wasm_toplevel_slot(tcr);
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (slot == NULL || vsp_empty == NULL) {
    return lisp_nil;
  }

  LispObj *vsp_ptr = NULL;
  if (tcr == wasm_get_current_tcr()) {
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  } else if (tcr->vs_area != NULL) {
    vsp_ptr = (LispObj *)tcr->vs_area->active;
  }
  if (vsp_ptr == NULL || vsp_ptr == vsp_empty) {
    return lisp_nil;
  }
  return *slot;
}

__attribute__((used, visibility("default"), export_name("wasm_set_tcr_toplevel_function")))
LispObj
wasm_set_tcr_toplevel_function(LispObj raw_tcr, LispObj fun)
{
  TCR *tcr = (TCR *)raw_tcr;
  if (tcr == NULL) {
    return fun;
  }
  LispObj *slot = wasm_toplevel_slot(tcr);
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (slot == NULL || vsp_empty == NULL) {
    return fun;
  }

  *slot = 0;

  LispObj *vsp_ptr = NULL;
  if (tcr == wasm_get_current_tcr()) {
    vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  } else if (tcr->vs_area != NULL) {
    vsp_ptr = (LispObj *)tcr->vs_area->active;
  }
  if (vsp_ptr == NULL) {
    vsp_ptr = vsp_empty;
  }
  if (vsp_ptr == vsp_empty) {
    tcr->vs_area->active = (BytePtr)slot;
    tcr->save_vsp = slot;
    if (tcr == wasm_get_current_tcr()) {
      tcr->wasm_gprs[vsp] = (LispObj)slot;
    }
  }

  *slot = fun;
  return fun;
}

__attribute__((used, visibility("default"), export_name("wasm_boot_entry")))
void
wasm_boot_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr != NULL) {
    *vsp_ptr = lisp_nil;
  }
  tcr->wasm_gprs[arg_z] = lisp_nil;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry")))
void
wasm_test_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }

  LispObj arg = tcr->wasm_gprs[arg_z];
  if (tag_of(arg) != tag_fixnum) {
    tcr->wasm_gprs[arg_z] = lisp_nil;
  } else {
    tcr->wasm_gprs[arg_z] = arg + box_fixnum(1);
  }
  tcr->wasm_gprs[nargs] = box_fixnum(1);

  /* Allow the stub to terminate the toplevel loop if used as %toplevel-function%. */
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr != NULL) {
    *vsp_ptr = lisp_nil;
  }
}

static LispObj wasm_const_value = (LispObj)nil_value;

static inline int64_t
wasm_fixnum_min(void)
{
  return -(1LL << (nbits_in_word - fixnum_shift - 1));
}

static inline int64_t
wasm_fixnum_max(void)
{
  return (1LL << (nbits_in_word - fixnum_shift - 1)) - 1;
}

static inline int
wasm_fixnum_fits(int64_t value)
{
  return (value >= wasm_fixnum_min()) && (value <= wasm_fixnum_max());
}

static inline size_t
wasm_align_dnode(size_t bytes)
{
  return (bytes + (dnode_size - 1)) & ~(size_t)(dnode_size - 1);
}

static inline unsigned
wasm_max_bignum_digits(void)
{
  return (unsigned)((1u << (sizeof(uint32_t) * 8 - num_subtag_bits)) - 1u);
}

static int
wasm_reserve_heap_segment(TCR *tcr, size_t bytes_needed)
{
  ExceptionInformation xp;

  if (tcr == NULL) {
    return 0;
  }

  if (tcr->save_allocptr == (void *)VOID_ALLOCPTR ||
      tcr->save_allocbase == (void *)VOID_ALLOCPTR ||
      tcr->save_allocptr == NULL || tcr->save_allocbase == NULL) {
    memset(&xp, 0, sizeof(xp));
    if (!new_heap_segment(&xp, (natural)bytes_needed, true, tcr, NULL)) {
      return 0;
    }
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  if ((alloc_ptr - (signed_natural)bytes_needed) < alloc_base) {
    memset(&xp, 0, sizeof(xp));
    if (!new_heap_segment(&xp, (natural)bytes_needed, true, tcr, NULL)) {
      return 0;
    }
  }

  return 1;
}

static LispObj
wasm_alloc_bignum_uninitialized(TCR *tcr, unsigned digits, uint32_t **data_out)
{
  if (data_out != NULL) {
    *data_out = NULL;
  }
  if (digits == 0) {
    return lisp_nil;
  }
  if (digits > wasm_max_bignum_digits()) {
    return lisp_nil;
  }

  size_t words = 1 + (size_t)digits;
  if (words > (SIZE_MAX / node_size)) {
    return lisp_nil;
  }

  size_t bytes = wasm_align_dnode(words * node_size);
  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag_bignum, digits);

  if (data_out != NULL) {
    *data_out = (uint32_t *)((BytePtr)obj + misc_data_offset);
  }

  return obj;
}

static LispObj
wasm_alloc_node_vector_initialized(TCR *tcr, unsigned subtag, signed_natural count)
{
  if (count < 0) {
    static const char msg[] = "WASM misc_alloc: negative count\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  size_t words = 1 + (size_t)count;
  if (words > (SIZE_MAX / node_size)) {
    static const char msg[] = "WASM misc_alloc: size overflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  size_t bytes = wasm_align_dnode(words * node_size);
  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    static const char msg[] = "WASM misc_alloc: reserve failed\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    static const char msg[] = "WASM misc_alloc: allocptr underflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag, count);

  LispObj *data = (LispObj *)((BytePtr)obj + misc_data_offset);
  for (signed_natural i = 0; i < count; i++) {
    data[i] = lisp_nil;
  }

  return obj;
}

static int
wasm_ivector_total_bytes(unsigned subtag, signed_natural count, size_t *bytes_out)
{
  if (count < 0) {
    static const char msg[] = "WASM misc_alloc: negative count\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return 0;
  }

  size_t element_count = (size_t)count;
  size_t total = 0;

  if (subtag <= max_32_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 2)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + (element_count << 2);
  } else if (subtag <= max_8_bit_ivector_subtag) {
    if (element_count > (SIZE_MAX - 4u)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + element_count;
  } else if (subtag <= max_16_bit_ivector_subtag) {
    if (element_count > ((SIZE_MAX - 4u) >> 1)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + (element_count << 1);
  } else if (subtag == subtag_complex_double_float_vector) {
    if (element_count > ((SIZE_MAX - 8u) >> 4)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 8u + (element_count << 4);
  } else if (subtag == subtag_bit_vector) {
    if (element_count > (SIZE_MAX - 7u)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 4u + ((element_count + 7u) >> 3);
  } else {
    if (element_count > ((SIZE_MAX - 8u) >> 3)) {
      static const char msg[] = "WASM misc_alloc: size overflow\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      return 0;
    }
    total = 8u + (element_count << 3);
  }

  *bytes_out = wasm_align_dnode(total);
  return 1;
}

static LispObj
wasm_alloc_ivector_uninitialized(TCR *tcr, unsigned subtag, signed_natural count)
{
  size_t bytes = 0;
  if (!wasm_ivector_total_bytes(subtag, count, &bytes)) {
    return lisp_nil;
  }

  if (!wasm_reserve_heap_segment(tcr, bytes)) {
    static const char msg[] = "WASM misc_alloc: reserve failed\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)bytes;
  if (newptr < alloc_base) {
    static const char msg[] = "WASM misc_alloc: allocptr underflow\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_misc);
  header_of(obj) = make_header(subtag, count);

  if (bytes > misc_data_offset) {
    memset((BytePtr)obj + misc_data_offset, 0, bytes - misc_data_offset);
  }

  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_misc_alloc")))
LispObj
wasm_misc_alloc(TCR *tcr, unsigned subtag, signed_natural count)
{
  if (tcr == NULL) {
    static const char msg[] = "WASM misc_alloc: null TCR\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    return lisp_nil;
  }

  unsigned tag = subtag & fulltagmask;
  if (tag == fulltag_nodeheader) {
    return wasm_alloc_node_vector_initialized(tcr, subtag, count);
  }
  if (tag == fulltag_immheader) {
    return wasm_alloc_ivector_uninitialized(tcr, subtag, count);
  }

  static const char msg[] = "WASM misc_alloc: bad subtag\n";
  wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_box_signed_64")))
LispObj
wasm_box_signed_64(TCR *tcr, int64_t value)
{
  if (wasm_fixnum_fits(value)) {
    return box_fixnum((signed_natural)value);
  }

  unsigned count = (value >= (int64_t)INT32_MIN && value <= (int64_t)INT32_MAX) ? 1u : 2u;
  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, count, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  uint64_t uval = (uint64_t)value;
  data[0] = (uint32_t)uval;
  if (count > 1) {
    data[1] = (uint32_t)(uval >> 32);
  }
  return obj;
}

static LispObj
wasm_box_unsigned_64(TCR *tcr, uint64_t value)
{
  if (value <= (uint64_t)wasm_fixnum_max()) {
    return box_fixnum((signed_natural)value);
  }

  uint32_t lo = (uint32_t)value;
  uint32_t hi = (uint32_t)(value >> 32);
  unsigned digits = (hi == 0) ? 1u : 2u;
  if ((hi == 0 && (lo & 0x80000000u)) || (hi & 0x80000000u)) {
    digits += 1;
  }

  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  memset(data, 0, (size_t)digits * sizeof(uint32_t));
  data[0] = lo;
  if (digits > 1) {
    data[1] = hi;
  }
  return obj;
}

static LispObj
wasm_box_shifted_fixnum(TCR *tcr, int32_t value, uint32_t shift)
{
  if (shift < 63) {
    int64_t shifted = ((int64_t)value) << shift;
    return wasm_box_signed_64(tcr, shifted);
  }
  if (value == 0) {
    return box_fixnum(0);
  }

  uint32_t mag = (value < 0) ? (uint32_t)(-(int64_t)value) : (uint32_t)value;
  uint32_t word_shift = shift / 32;
  uint32_t bit_shift = shift % 32;
  uint64_t chunk = ((uint64_t)mag) << bit_shift;
  uint32_t low = (uint32_t)chunk;
  uint32_t high = (uint32_t)(chunk >> 32);
  unsigned digits = 0;

  if (value < 0) {
    int has_high = (bit_shift != 0) && (high != 0);
    digits = word_shift + 1 + (has_high ? 1u : 0u);
    uint32_t msd = has_high ? (uint32_t)~high : (uint32_t)(~low + 1u);
    if ((msd & 0x80000000u) == 0) {
      digits += 1;
    }
  } else {
    digits = word_shift + 1;
    uint32_t msd = low;
    if (bit_shift != 0) {
      if (high != 0) {
        digits += 1;
        msd = high;
      } else if (low & 0x80000000u) {
        digits += 1;
        msd = 0;
      }
    }
    if (msd & 0x80000000u) {
      digits += 1;
    }
  }

  if (digits > wasm_max_bignum_digits()) {
    return lisp_nil;
  }

  uint32_t *data = NULL;
  LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
  if (obj == lisp_nil || data == NULL) {
    return lisp_nil;
  }

  memset(data, 0, (size_t)digits * sizeof(uint32_t));
  data[word_shift] = low;
  if (bit_shift != 0 && high != 0) {
    data[word_shift + 1] = high;
  }

  if (value < 0) {
    uint64_t carry = 1;
    for (unsigned i = 0; i < digits; i++) {
      uint64_t sum = (uint64_t)(~data[i]) + carry;
      data[i] = (uint32_t)sum;
      carry = sum >> 32;
    }
  }

  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_set_const_value")))
void
wasm_set_const_value(LispObj value)
{
  wasm_const_value = value;
}

__attribute__((used, visibility("default"), export_name("wasm_const_entry")))
void
wasm_const_entry(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj value = wasm_const_value;
  LispObj fn_value = tcr->wasm_gprs[nfn];
  if (fulltag_of(fn_value) == fulltag_misc) {
    LispObj header = header_of(fn_value);
    if (header_subtag(header) == subtag_function &&
        header_element_count(header) >= 4) {
      value = deref(fn_value, 3);
    }
  }
  tcr->wasm_gprs[arg_z] = value;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_constant")))
void
wasm_return_constant(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_z] = value;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_get_arg_z")))
LispObj
wasm_get_arg_z(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[arg_z];
}

__attribute__((used, visibility("default"), export_name("wasm_get_arg_y")))
LispObj
wasm_get_arg_y(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[arg_y];
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_z")))
void
wasm_set_arg_z(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_z] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_y")))
void
wasm_set_arg_y(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_y] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_arg_x")))
void
wasm_set_arg_x(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[arg_x] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_nargs")))
void
wasm_set_nargs(uint32_t count)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[nargs] = box_fixnum((signed_natural)count);
}

__attribute__((used, visibility("default"), export_name("wasm_set_nfn")))
void
wasm_set_nfn(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[nfn] = value;
  tcr->wasm_gprs[Rfn] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_set_imm0")))
void
wasm_set_imm0(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_gprs[imm0] = value;
}

__attribute__((used, visibility("default"), export_name("wasm_get_nfn")))
LispObj
wasm_get_nfn(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  return tcr->wasm_gprs[nfn];
}

__attribute__((used, visibility("default"), export_name("wasm_get_nargs")))
uint32_t
wasm_get_nargs(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return 0;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return 1;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count < 0) {
    return 0;
  }
  return (uint32_t)count;
}

__attribute__((used, visibility("default"), export_name("wasm_lisp_word_ref")))
LispObj
wasm_lisp_word_ref(LispObj base, LispObj offset)
{
  if (tag_of(offset) != tag_fixnum) {
    return lisp_nil;
  }

  signed_natural idx = unbox_fixnum(offset);
  if (idx < 0) {
    return lisp_nil;
  }

  if (base == (LispObj)nil_value || tag_of(base) == tag_list) {
    signed_natural len = 0;
    LispObj cur = base;
    while (cur != (LispObj)nil_value) {
      if (tag_of(cur) != tag_list) {
        return lisp_nil;
      }
      cons *cell = (cons *)ptr_from_lispobj(untag(cur));
      cur = cell->cdr;
      len++;
    }

    if (idx == 0) {
      return box_fixnum(len);
    }

    signed_natural element_index = len - idx;
    if (element_index < 0 || element_index >= len) {
      return lisp_nil;
    }

    cur = base;
    for (signed_natural i = 0; i < element_index; i++) {
      if (cur == (LispObj)nil_value || tag_of(cur) != tag_list) {
        return lisp_nil;
      }
      cons *cell = (cons *)ptr_from_lispobj(untag(cur));
      cur = cell->cdr;
    }
    if (cur == (LispObj)nil_value || tag_of(cur) != tag_list) {
      return lisp_nil;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(cur));
    return cell->car;
  }

  if (tag_of(base) == tag_fixnum) {
    signed_natural addr = unbox_fixnum(base);
    LispObj *ptr = (LispObj *)(uintptr_t)addr;
    return ptr[idx];
  }

  if (fulltag_of(base) == fulltag_misc) {
    LispObj header = header_of(base);
    signed_natural count = header_element_count(header);
    if (idx >= 0 && idx < count) {
      return deref(base, idx);
    }
  }

  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_return_arg_z")))
void
wasm_return_arg_z(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  if (tcr->wasm_pending_throw) {
    return;
  }
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_arg_y")))
void
wasm_return_arg_y(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  if (tcr->wasm_pending_throw) {
    return;
  }
  tcr->wasm_gprs[arg_z] = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_values2")))
LispObj
wasm_return_values2(LispObj value0, LispObj value1)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = value1;
  *--vsp_ptr = value0;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(2);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_return_values3")))
LispObj
wasm_return_values3(LispObj value0, LispObj value1, LispObj value2)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = value2;
  *--vsp_ptr = value1;
  *--vsp_ptr = value0;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_return_values4")))
LispObj
wasm_return_values4(LispObj value0, LispObj value1, LispObj value2, LispObj value3)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = value3;
  *--vsp_ptr = value2;
  *--vsp_ptr = value1;
  *--vsp_ptr = value0;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[arg_z] = value0;
  tcr->wasm_gprs[nargs] = box_fixnum(4);
  return value0;
}

__attribute__((used, visibility("default"), export_name("wasm_get_mv")))
LispObj
wasm_get_mv(uint32_t index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural count = unbox_fixnum(raw);
  if ((signed_natural)index < 0 || (signed_natural)index >= count) {
    return lisp_nil;
  }
  if (index == 0) {
    return tcr->wasm_gprs[arg_z];
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  return vsp_ptr[index];
}

__attribute__((used, visibility("default"), export_name("wasm_get_mv_indexed")))
LispObj
wasm_get_mv_indexed(LispObj raw_index)
{
  if (tag_of(raw_index) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural index = unbox_fixnum(raw_index);
  if (index < 0) {
    return lisp_nil;
  }
  return wasm_get_mv((uint32_t)index);
}

__attribute__((used, visibility("default"), export_name("wasm_restore_vsp")))
void
wasm_restore_vsp(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count <= 1) {
    return;
  }
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  if (vsp_ptr == NULL) {
    return;
  }
  vsp_ptr += count;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_vpush")))
void
wasm_vpush(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return;
  }
  *--vsp_ptr = value;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
}

__attribute__((used, visibility("default"), export_name("wasm_vsp_ref")))
LispObj
wasm_vsp_ref(uint32_t index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  LispObj raw = tcr->wasm_gprs[nargs];
  if (tag_of(raw) != tag_fixnum) {
    return lisp_nil;
  }
  signed_natural count = unbox_fixnum(raw);
  if (count <= 0 || (signed_natural)index >= count) {
    return lisp_nil;
  }
  return vsp_ptr[index];
}

__attribute__((used, visibility("default"), export_name("wasm_vpop")))
LispObj
wasm_vpop(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *vsp_ptr = tcr->save_vsp;
  if (vsp_ptr == NULL) {
    return lisp_nil;
  }
  LispObj value = *vsp_ptr++;
  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  return value;
}

__attribute__((used, visibility("default"), export_name("wasm_spill_push")))
void
wasm_spill_push(LispObj value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_base == NULL) {
    return;
  }
  if (sp <= tcr->wasm_spill_base) {
    __builtin_trap();
  }
  *--sp = value;
  tcr->wasm_spill_sp = sp;
}

__attribute__((used, visibility("default"), export_name("wasm_spill_pop")))
LispObj
wasm_spill_pop(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj *sp = tcr->wasm_spill_sp;
  if (sp == NULL || tcr->wasm_spill_limit == NULL) {
    return lisp_nil;
  }
  if (sp >= tcr->wasm_spill_limit) {
    __builtin_trap();
  }
  LispObj value = *sp++;
  tcr->wasm_spill_sp = sp;
  return value;
}

__attribute__((used, visibility("default"), export_name("wasm_pending_throw_p")))
uint32_t
wasm_pending_throw_p(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return 0;
  }
  return tcr->wasm_pending_throw ? 1 : 0;
}

__attribute__((used, visibility("default"), export_name("wasm_clear_pending_throw")))
void
wasm_clear_pending_throw(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  tcr->wasm_pending_throw = 0;
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_add")))
void
wasm_return_fixnum_add(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t a = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t b = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t sum = a + b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, sum);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_sub")))
void
wasm_return_fixnum_sub(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t a = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t b = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t diff = a - b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, diff);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_mul")))
void
wasm_return_fixnum_mul(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural a = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  signed_natural b = unbox_fixnum(tcr->wasm_gprs[arg_y]);
  int64_t prod = (int64_t)a * (int64_t)b;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, prod);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_ash")))
void
wasm_return_fixnum_ash(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural val = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  signed_natural amt = unbox_fixnum(tcr->wasm_gprs[arg_y]);
  signed_natural result = 0;
  if (amt >= 0) {
    tcr->wasm_gprs[arg_z] = wasm_box_shifted_fixnum(tcr, (int32_t)val, (uint32_t)amt);
    tcr->wasm_gprs[nargs] = box_fixnum(1);
    return;
  } else {
    signed_natural shift = -amt;
    result = (shift >= (signed_natural)(nbits_in_word - 1)) ? ((val < 0) ? -1 : 0) : (val >> shift);
  }
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, result);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_neg")))
void
wasm_return_fixnum_neg(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int64_t val = (int64_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int64_t neg = -val;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, neg);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("_SPmakes32")))
void
_SPmakes32(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj raw = tcr->wasm_gprs[imm0];
  int32_t val = (tag_of(raw) == tag_fixnum) ? (int32_t)unbox_fixnum(raw) : (int32_t)raw;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, (int64_t)val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("_SPfix_overflow")))
void
_SPfix_overflow(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  int32_t val = (int32_t)unbox_fixnum(tcr->wasm_gprs[arg_z]);
  int32_t adjust = (int32_t)(3u << (nbits_in_word - 2));
  val ^= adjust;
  tcr->wasm_gprs[arg_z] = wasm_box_signed_64(tcr, (int64_t)val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logand")))
void
wasm_return_fixnum_logand(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a & b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logior")))
void
wasm_return_fixnum_logior(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a | b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_logxor")))
void
wasm_return_fixnum_logxor(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  LispObj a = tcr->wasm_gprs[arg_z];
  LispObj b = tcr->wasm_gprs[arg_y];
  tcr->wasm_gprs[arg_z] = a ^ b;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

__attribute__((used, visibility("default"), export_name("wasm_return_fixnum_lognot")))
void
wasm_return_fixnum_lognot(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return;
  }
  signed_natural val = unbox_fixnum(tcr->wasm_gprs[arg_z]);
  tcr->wasm_gprs[arg_z] = box_fixnum(~val);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
}

static LispObj
wasm_funcall_common(TCR *tcr, LispObj fn_value, const LispObj *args, signed_natural count, int preserve_mv)
{
  static const char msg_enter[] = "WASM wasm_funcall_common: enter\n";
  static const char msg_call[] = "WASM wasm_funcall_common: call subprim\n";
  static const char msg_exit[] = "WASM wasm_funcall_common: return\n";
  wasm_host_log(msg_enter, (unsigned)(sizeof(msg_enter) - 1));
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  int in_lisp = (tcr->valence == TCR_STATE_LISP);
  LispObj *saved_vsp = in_lisp ? (LispObj *)tcr->wasm_gprs[vsp] : tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = 0;
  if (!in_lisp) {
    old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
    tcr->valence = TCR_STATE_LISP;
  }
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  for (signed_natural i = count - 1; i >= 0; i--) {
    *--vsp_ptr = args[i];
  }

  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(count);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_host_log(msg_call, (unsigned)(sizeof(msg_call) - 1));
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  if (tcr->wasm_pending_throw) {
    LispObj *throw_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (throw_vsp == NULL) {
      throw_vsp = saved_vsp;
    }
    tcr->save_vsp = throw_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)throw_vsp;
    if (!in_lisp) {
      tcr->valence = TCR_STATE_FOREIGN;
      wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    }
    return result;
  }

  LispObj raw_nargs = tcr->wasm_gprs[nargs];
  signed_natural value_count = (tag_of(raw_nargs) == tag_fixnum) ? unbox_fixnum(raw_nargs) : 1;

  if (preserve_mv && value_count > 1) {
    LispObj *mv_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (mv_vsp != NULL) {
      tcr->save_vsp = mv_vsp;
    } else {
      tcr->save_vsp = saved_vsp;
      tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
      tcr->wasm_gprs[nargs] = box_fixnum(1);
    }
  } else {
    tcr->save_vsp = saved_vsp;
    tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
    if (value_count > 1) {
      tcr->wasm_gprs[nargs] = box_fixnum(1);
    }
  }
  if (!in_lisp) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
  }

  wasm_host_log(msg_exit, (unsigned)(sizeof(msg_exit) - 1));
  return result;
}

enum {
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_OK = 1u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_TCR = 10u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_SUBPRIMS_NOT_READY = 11u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_SAVEVSP = 12u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_HOST_FRAME = 13u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_INSTALL = 14u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_PENDING_THROW = 15u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_VSP = 16u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SAVEVSP = 17u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_LAST = 18u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_RESTORE = 19u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_FRAME_EXIT = 20u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SP_RESTORE = 21u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_INSTALL = 22u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_PENDING_THROW = 23u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_VSP = 24u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SAVEVSP = 25u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_LAST = 26u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_RESTORE = 27u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SP_RESTORE = 28u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_INSTALL = 29u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_PENDING_THROW = 30u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_ARGZ = 31u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_VSP = 32u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_SAVEVSP = 33u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_LAST = 34u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_RESTORE = 35u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS = 36u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_INSTALL = 37u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_PENDING_THROW = 38u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_NARGS = 39u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_ARGZ = 40u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VSP = 41u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_SAVEVSP = 42u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VALUES = 43u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_LAST = 44u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_RESTORE = 45u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_INSTALL = 46u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_PENDING_THROW = 47u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_ARGZ = 48u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_VSP = 49u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVEVSP = 50u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVETSP = 51u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_LAST = 52u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_RESTORE = 53u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SP_RESTORE = 54u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_STACK_BOUNDS = 55u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_INSTALL = 56u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_PENDING_THROW = 57u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_NARGS = 58u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_ARGZ = 59u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_VSP = 60u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVETSP = 61u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVEVSP_VALUES = 62u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_LAST = 63u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_RESTORE = 64u,
  WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SP_RESTORE = 65u
};

typedef struct wasm_subprim_nonlocal_exit_selftest_state {
  BytePtr cstack_sp;
  natural last_lisp_frame;
  LispObj *save_vsp;
  LispObj catch_top;
  xframe_list *xframe;
  void *nfp;
  LispObj *save_tsp;
  int valence;
  LispObj pending_throw;
  LispObj reg_vsp;
  LispObj reg_arg_z;
  LispObj reg_arg_y;
  LispObj reg_arg_x;
  LispObj reg_nargs;
  LispObj reg_imm0;
  LispObj reg_nfn;
  LispObj reg_rfn;
} wasm_subprim_nonlocal_exit_selftest_state;

static void
wasm_capture_subprim_nonlocal_exit_selftest_state(TCR *tcr,
                                                  wasm_subprim_nonlocal_exit_selftest_state *state)
{
  state->cstack_sp = (BytePtr)wasm_get_cstack_pointer();
  state->last_lisp_frame = tcr->last_lisp_frame;
  state->save_vsp = tcr->save_vsp;
  state->catch_top = tcr->catch_top;
  state->xframe = tcr->xframe;
  state->nfp = tcr->nfp;
  state->save_tsp = tcr->save_tsp;
  state->valence = tcr->valence;
  state->pending_throw = tcr->wasm_pending_throw;
  state->reg_vsp = tcr->wasm_gprs[vsp];
  state->reg_arg_z = tcr->wasm_gprs[arg_z];
  state->reg_arg_y = tcr->wasm_gprs[arg_y];
  state->reg_arg_x = tcr->wasm_gprs[arg_x];
  state->reg_nargs = tcr->wasm_gprs[nargs];
  state->reg_imm0 = tcr->wasm_gprs[imm0];
  state->reg_nfn = tcr->wasm_gprs[nfn];
  state->reg_rfn = tcr->wasm_gprs[Rfn];
}

static void
wasm_restore_subprim_nonlocal_exit_selftest_state(TCR *tcr,
                                                  const wasm_subprim_nonlocal_exit_selftest_state *state)
{
  wasm_set_cstack_pointer(state->cstack_sp);
  tcr->last_lisp_frame = state->last_lisp_frame;
  tcr->save_vsp = state->save_vsp;
  tcr->catch_top = state->catch_top;
  tcr->xframe = state->xframe;
  tcr->nfp = state->nfp;
  tcr->save_tsp = state->save_tsp;
  tcr->valence = state->valence;
  tcr->wasm_pending_throw = state->pending_throw;
  tcr->wasm_gprs[vsp] = state->reg_vsp;
  tcr->wasm_gprs[arg_z] = state->reg_arg_z;
  tcr->wasm_gprs[arg_y] = state->reg_arg_y;
  tcr->wasm_gprs[arg_x] = state->reg_arg_x;
  tcr->wasm_gprs[nargs] = state->reg_nargs;
  tcr->wasm_gprs[imm0] = state->reg_imm0;
  tcr->wasm_gprs[nfn] = state->reg_nfn;
  tcr->wasm_gprs[Rfn] = state->reg_rfn;
}

uint32_t
wasm_subprim_nonlocal_exit_coherence_selftest(void)
{
  TCR *tcr = wasm_get_current_tcr();
  wasm_subprim_nonlocal_exit_selftest_state original;
  area *vs_area;
  natural direct_old_last_lisp_frame;
  natural direct_host_last_lisp_frame;
  LispObj *direct_unwind_throw_vsp;
  LispObj cleanup_invoked_sentinel = box_fixnum(0x3301);
  LispObj mv0 = box_fixnum(0x3401);
  LispObj mv1 = box_fixnum(0x3402);
  LispObj mv2 = box_fixnum(0x3403);
  LispObj funcall_mv0 = box_fixnum(0x4401);
  LispObj funcall_mv1 = box_fixnum(0x4402);
  LispObj funcall_mv2 = box_fixnum(0x4403);
  LispObj nthrow1_fn_obj[3] __attribute__((aligned(8)));
  LispObj nthrowvalues_fn_obj[3] __attribute__((aligned(8)));
  LispObj nthrow1_entry_fixnum = box_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX);
  LispObj nthrowvalues_entry_fixnum = box_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX);
  LispObj nthrow1_fn_value;
  LispObj nthrowvalues_fn_value;
  LispObj funcall_mv_args[3];

  if (tcr == NULL) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_TCR;
  }
  if (!wasm_subprims_ready) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_SUBPRIMS_NOT_READY;
  }
  if (tcr->save_vsp == NULL) {
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_NO_SAVEVSP;
  }

  wasm_capture_subprim_nonlocal_exit_selftest_state(tcr, &original);

  nthrow1_fn_obj[0] = make_header(subtag_function, 2);
  nthrow1_fn_obj[1] = nthrow1_entry_fixnum;
  nthrow1_fn_obj[2] = nthrow1_entry_fixnum;
  nthrow1_fn_value = (LispObj)((BytePtr)nthrow1_fn_obj + fulltag_misc);

  nthrowvalues_fn_obj[0] = make_header(subtag_function, 2);
  nthrowvalues_fn_obj[1] = nthrowvalues_entry_fixnum;
  nthrowvalues_fn_obj[2] = nthrowvalues_entry_fixnum;
  nthrowvalues_fn_value = (LispObj)((BytePtr)nthrowvalues_fn_obj + fulltag_misc);

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;

  direct_old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)original.save_vsp);
  direct_host_last_lisp_frame = tcr->last_lisp_frame;
  if (direct_host_last_lisp_frame == 0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_HOST_FRAME;
  }
  tcr->valence = TCR_STATE_LISP;

  tcr->wasm_gprs[arg_z] = box_fixnum(0x1101);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x1102);
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROW1VALUE_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_PENDING_THROW;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SAVEVSP;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_CATCH_RESTORE;
  }

  /* Phase-3: mkunwind + nthrowvalues cleanup entry must execute and restore
   * non-local-exit coherence for a zero-value throw.
   */
  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_PENDING_THROW;
  }
  if (tcr->wasm_gprs[arg_z] != (LispObj)nil_value) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_SAVEVSP;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_CATCH_RESTORE;
  }

  /* Phase-3: same path with MV payload verifies push/recover around cleanup. */
  vs_area = tcr->vs_area;
  if ((vs_area == NULL) || (vs_area->low == NULL) || (vs_area->high == NULL)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS;
  }
  direct_unwind_throw_vsp = original.save_vsp - 3;
  if (((BytePtr)direct_unwind_throw_vsp < vs_area->low) ||
      ((BytePtr)(direct_unwind_throw_vsp + 3) > vs_area->high)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_STACK_BOUNDS;
  }
  direct_unwind_throw_vsp[0] = mv0;
  direct_unwind_throw_vsp[1] = mv1;
  direct_unwind_throw_vsp[2] = mv2;

  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->save_vsp = direct_unwind_throw_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)direct_unwind_throw_vsp;
  tcr->wasm_gprs[arg_z] = mv0;
  tcr->wasm_gprs[arg_y] = mv1;
  tcr->wasm_gprs[arg_x] = mv2;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = mv0;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_NTHROWVALUES_INDEX));
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_PENDING_THROW;
  }
  if (tcr->wasm_gprs[nargs] != box_fixnum(3)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_NARGS;
  }
  if (tcr->wasm_gprs[arg_z] != mv0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VSP;
  }
  if ((tcr->save_vsp == NULL) || (tcr->save_tsp != NULL)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_SAVEVSP;
  }
  if ((tcr->save_vsp[0] != mv0) ||
      (tcr->save_vsp[1] != mv1) ||
      (tcr->save_vsp[2] != mv2)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_VALUES;
  }
  if (tcr->last_lisp_frame != direct_host_last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_UNWIND_MV_CATCH_RESTORE;
  }

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, direct_old_last_lisp_frame);
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_FRAME_EXIT;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_DIRECT_SP_RESTORE;
  }

  tcr->wasm_pending_throw = 0;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x2201);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKCATCH1V_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = box_fixnum(0x2202);
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrow1_fn_value, NULL, 0, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_PENDING_THROW;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SAVEVSP;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_SP_RESTORE;
  }

  /*
   * Phase-4: same unwind-cleanup boundaries must hold when _SPnthrowvalues
   * is entered through wasm_funcall_common.
   */
  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_INSTALL;
  }

  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = cleanup_invoked_sentinel;
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrowvalues_fn_value, NULL, 0, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_PENDING_THROW;
  }
  if (tcr->wasm_gprs[arg_z] != (LispObj)nil_value) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_VSP;
  }
  if (tcr->save_vsp != original.save_vsp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVEVSP;
  }
  if (tcr->save_tsp != NULL) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SAVETSP;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_SP_RESTORE;
  }

  vs_area = tcr->vs_area;
  if ((vs_area == NULL) ||
      (vs_area->low == NULL) ||
      (vs_area->high == NULL) ||
      ((BytePtr)(original.save_vsp - 3) < vs_area->low) ||
      ((BytePtr)original.save_vsp > vs_area->high)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_STACK_BOUNDS;
  }

  tcr->wasm_pending_throw = 0;
  tcr->save_tsp = NULL;
  tcr->valence = TCR_STATE_FOREIGN;
  tcr->save_vsp = original.save_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)original.save_vsp;
  tcr->catch_top = original.catch_top;
  tcr->wasm_gprs[arg_z] = funcall_mv0;
  tcr->wasm_gprs[arg_y] = funcall_mv1;
  tcr->wasm_gprs[arg_x] = funcall_mv2;
  tcr->wasm_gprs[nargs] = box_fixnum(3);
  tcr->wasm_gprs[imm0] = box_fixnum(WASM_SUBPRIM_VALUES_INDEX);
  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_MKUNWIND_INDEX));
  if (tcr->catch_top == original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_INSTALL;
  }

  funcall_mv_args[0] = funcall_mv0;
  funcall_mv_args[1] = funcall_mv1;
  funcall_mv_args[2] = funcall_mv2;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[arg_z] = funcall_mv0;
  tcr->wasm_gprs[imm0] = box_fixnum(1);
  (void)wasm_funcall_common(tcr, nthrowvalues_fn_value, funcall_mv_args, 3, 0);
  if (!tcr->wasm_pending_throw) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_PENDING_THROW;
  }
  if (tcr->wasm_gprs[nargs] != box_fixnum(3)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_NARGS;
  }
  if (tcr->wasm_gprs[arg_z] != funcall_mv0) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_ARGZ;
  }
  if ((LispObj)tcr->save_vsp != tcr->wasm_gprs[vsp]) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_VSP;
  }
  if (tcr->save_tsp != NULL) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVETSP;
  }
  if ((tcr->save_vsp == NULL) ||
      (tcr->save_vsp[0] != funcall_mv0) ||
      (tcr->save_vsp[1] != funcall_mv1) ||
      (tcr->save_vsp[2] != funcall_mv2)) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SAVEVSP_VALUES;
  }
  if (tcr->last_lisp_frame != original.last_lisp_frame) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_LAST;
  }
  if (tcr->catch_top != original.catch_top) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_CATCH_RESTORE;
  }
  if ((BytePtr)wasm_get_cstack_pointer() != original.cstack_sp) {
    wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
    return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_FUNCALL_UNWIND_MV_SP_RESTORE;
  }

  wasm_restore_subprim_nonlocal_exit_selftest_state(tcr, &original);
  return WASM_SUBPRIM_NONLOCAL_EXIT_SELFTEST_OK;
}

__attribute__((used, visibility("default"), export_name("wasm_subprim_nonlocal_exit_coherence_selftest")))
uint32_t
wasm_subprim_nonlocal_exit_coherence_selftest_export(void)
{
  return wasm_subprim_nonlocal_exit_coherence_selftest();
}

__attribute__((used, visibility("default"), export_name("wasm_funcall0")))
LispObj
wasm_funcall0(LispObj fn_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_funcall_common(tcr, fn_value, NULL, 0, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall1")))
LispObj
wasm_funcall1(LispObj fn_value, LispObj arg0)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[1];
  args[0] = arg0;
  return wasm_funcall_common(tcr, fn_value, args, 1, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall2")))
LispObj
wasm_funcall2(LispObj fn_value, LispObj arg0, LispObj arg1)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[2];
  args[0] = arg0;
  args[1] = arg1;
  return wasm_funcall_common(tcr, fn_value, args, 2, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall7")))
LispObj
wasm_funcall7(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[7];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  return wasm_funcall_common(tcr, fn_value, args, 7, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall8")))
LispObj
wasm_funcall8(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[8];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  return wasm_funcall_common(tcr, fn_value, args, 8, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall9")))
LispObj
wasm_funcall9(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[9];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  return wasm_funcall_common(tcr, fn_value, args, 9, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall10")))
LispObj
wasm_funcall10(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8, LispObj arg9)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[10];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  args[9] = arg9;
  return wasm_funcall_common(tcr, fn_value, args, 10, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall3")))
LispObj
wasm_funcall3(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[3];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  return wasm_funcall_common(tcr, fn_value, args, 3, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall4")))
LispObj
wasm_funcall4(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[4];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  return wasm_funcall_common(tcr, fn_value, args, 4, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall5")))
LispObj
wasm_funcall5(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[5];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  return wasm_funcall_common(tcr, fn_value, args, 5, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall6")))
LispObj
wasm_funcall6(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[6];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  return wasm_funcall_common(tcr, fn_value, args, 6, 0);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall0_mv")))
LispObj
wasm_funcall0_mv(LispObj fn_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_funcall_common(tcr, fn_value, NULL, 0, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall1_mv")))
LispObj
wasm_funcall1_mv(LispObj fn_value, LispObj arg0)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[1];
  args[0] = arg0;
  return wasm_funcall_common(tcr, fn_value, args, 1, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall2_mv")))
LispObj
wasm_funcall2_mv(LispObj fn_value, LispObj arg0, LispObj arg1)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[2];
  args[0] = arg0;
  args[1] = arg1;
  return wasm_funcall_common(tcr, fn_value, args, 2, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall7_mv")))
LispObj
wasm_funcall7_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[7];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  return wasm_funcall_common(tcr, fn_value, args, 7, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall8_mv")))
LispObj
wasm_funcall8_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[8];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  return wasm_funcall_common(tcr, fn_value, args, 8, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall9_mv")))
LispObj
wasm_funcall9_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[9];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  return wasm_funcall_common(tcr, fn_value, args, 9, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall10_mv")))
LispObj
wasm_funcall10_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5, LispObj arg6, LispObj arg7, LispObj arg8, LispObj arg9)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[10];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  args[6] = arg6;
  args[7] = arg7;
  args[8] = arg8;
  args[9] = arg9;
  return wasm_funcall_common(tcr, fn_value, args, 10, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall3_mv")))
LispObj
wasm_funcall3_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[3];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  return wasm_funcall_common(tcr, fn_value, args, 3, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall4_mv")))
LispObj
wasm_funcall4_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[4];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  return wasm_funcall_common(tcr, fn_value, args, 4, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall5_mv")))
LispObj
wasm_funcall5_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[5];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  return wasm_funcall_common(tcr, fn_value, args, 5, 1);
}

__attribute__((used, visibility("default"), export_name("wasm_funcall6_mv")))
LispObj
wasm_funcall6_mv(LispObj fn_value, LispObj arg0, LispObj arg1, LispObj arg2, LispObj arg3, LispObj arg4, LispObj arg5)
{
  TCR *tcr = wasm_get_current_tcr();
  LispObj args[6];
  args[0] = arg0;
  args[1] = arg1;
  args[2] = arg2;
  args[3] = arg3;
  args[4] = arg4;
  args[5] = arg5;
  return wasm_funcall_common(tcr, fn_value, args, 6, 1);
}

LispObj
start_lisp(TCR *tcr, LispObj arg)
{
  (void)arg;
  if (tcr != NULL) {
    tcr->valence = TCR_STATE_LISP;
  }

  if (!wasm_subprims_ready) {
    static const char msg[] =
      "WASM start_lisp: subprims not ready; returning to host\n";
    wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    goto done;
  }

  if (tcr != NULL) {
    tcr->wasm_pending_throw = 0;
    tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
    LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
    LispObj *vsp_empty = wasm_vsp_empty(tcr);
    if (vsp_ptr == NULL) {
      vsp_ptr = vsp_empty;
      if (vsp_ptr != NULL) {
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      }
    }
    if (vsp_ptr == NULL) {
      static const char msg[] =
        "WASM start_lisp: VSP not initialized; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }
    LispObj topfn = nrs_TOPLFUNC.vcell;
    LispObj *slot = wasm_toplevel_slot(tcr);
    if (topfn != lisp_nil) {
      if (slot != NULL) {
        *slot = topfn;
        if (tcr->vs_area != NULL) {
          tcr->vs_area->active = (BytePtr)slot;
        }
        tcr->save_vsp = slot;
        vsp_ptr = slot;
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      } else {
        *--vsp_ptr = topfn;
        tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
      }
      nrs_TOPLFUNC.vcell = lisp_nil;
    } else if (slot != NULL && *slot != lisp_nil) {
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      vsp_ptr = slot;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    } else if (vsp_ptr == vsp_empty || *vsp_ptr == lisp_nil) {
      static const char msg[] =
        "WASM start_lisp: toplevel function is NIL; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
      goto done;
    }

    (void)wasm_toplevel_loop(tcr);

    tcr->save_vsp = (LispObj *)tcr->wasm_gprs[vsp];
    if (tcr->wasm_pending_throw) {
      tcr->wasm_pending_throw = 0;
    }
  }

done:
  if (tcr != NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
  }

  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_run_toplevel")))
int
wasm_run_toplevel(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -1;
  }
  if (!wasm_subprims_ready) {
    return -2;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)tcr->save_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;
  tcr->wasm_gprs[vsp] = (LispObj)tcr->save_vsp;
  LispObj *vsp_ptr = (LispObj *)tcr->wasm_gprs[vsp];
  LispObj *vsp_empty = wasm_vsp_empty(tcr);
  if (vsp_ptr == NULL) {
    vsp_ptr = vsp_empty;
    if (vsp_ptr != NULL) {
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    }
  }
  if (vsp_ptr == NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -4;
  }
  LispObj topfn = nrs_TOPLFUNC.vcell;
  LispObj *slot = wasm_toplevel_slot(tcr);
  if (topfn != lisp_nil) {
    if (slot != NULL) {
      *slot = topfn;
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      vsp_ptr = slot;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    } else {
      *--vsp_ptr = topfn;
      tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
    }
    nrs_TOPLFUNC.vcell = lisp_nil;
  } else if (slot != NULL && *slot != lisp_nil) {
    if (tcr->vs_area != NULL) {
      tcr->vs_area->active = (BytePtr)slot;
    }
    tcr->save_vsp = slot;
    vsp_ptr = slot;
    tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  } else if (vsp_ptr == vsp_empty || *vsp_ptr == lisp_nil) {
    tcr->valence = TCR_STATE_FOREIGN;
    wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
    return -3;
  }

  int rc = wasm_toplevel_loop(tcr);

  tcr->save_vsp = (LispObj *)tcr->wasm_gprs[vsp];
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
  }
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);
  return rc;
}

__attribute__((used, visibility("default"), export_name("wasm_test_funcall")))
LispObj
wasm_test_funcall(uint32_t raw_arg)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[3] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum(WASM_TEST_ENTRY_INDEX);
  fn_obj[0] = make_header(subtag_function, 2);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = box_fixnum((signed_natural)raw_arg);

  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_const_funcall")))
LispObj
wasm_test_const_funcall(uint32_t raw_value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum(WASM_CONST_ENTRY_INDEX);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = box_fixnum((signed_natural)raw_value);
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall")))
LispObj
wasm_test_entry_funcall(uint32_t entry_index, uint32_t raw_value)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = box_fixnum((signed_natural)raw_value);
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->wasm_gprs[nargs] = box_fixnum(0);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall2")))
LispObj
wasm_test_entry_funcall2(uint32_t entry_index, uint32_t raw_a, uint32_t raw_b)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = 0;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = box_fixnum((signed_natural)raw_b);
  *--vsp_ptr = box_fixnum((signed_natural)raw_a);

  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(2);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall1_raw")))
LispObj
wasm_test_entry_funcall1_raw(uint32_t entry_index, LispObj arg)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = 0;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);

  LispObj *saved_vsp = tcr->save_vsp;
  if (saved_vsp == NULL) {
    return lisp_nil;
  }

  natural old_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, (LispObj)saved_vsp);
  tcr->valence = TCR_STATE_LISP;
  tcr->wasm_pending_throw = 0;

  LispObj *vsp_ptr = saved_vsp;
  *--vsp_ptr = arg;

  tcr->save_vsp = vsp_ptr;
  tcr->wasm_gprs[vsp] = (LispObj)vsp_ptr;
  tcr->wasm_gprs[nargs] = box_fixnum(1);
  tcr->wasm_gprs[nfn] = fn_value;
  tcr->wasm_gprs[Rfn] = fn_value;

  wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

  LispObj result = tcr->wasm_gprs[arg_z];
  tcr->save_vsp = saved_vsp;
  tcr->wasm_gprs[vsp] = (LispObj)saved_vsp;
  tcr->valence = TCR_STATE_FOREIGN;
  wasm_exit_lisp_frame(tcr, old_last_lisp_frame);

  return result;
}

__attribute__((used, visibility("default"), export_name("wasm_test_entry_funcall0_raw")))
LispObj
wasm_test_entry_funcall0_raw(uint32_t entry_index)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }
  if (!wasm_subprims_ready) {
    return lisp_nil;
  }

  LispObj fn_obj[4] __attribute__((aligned(8)));
  LispObj entry_fixnum = box_fixnum((signed_natural)entry_index);
  fn_obj[0] = make_header(subtag_function, 4);
  fn_obj[1] = entry_fixnum;
  fn_obj[2] = entry_fixnum;
  fn_obj[3] = 0;
  LispObj fn_value = (LispObj)((BytePtr)fn_obj + fulltag_misc);
  static const char msg_enter[] = "WASM raw entry call: enter\n";
  static const char msg_exit[] = "WASM raw entry call: return\n";
  wasm_host_log(msg_enter, (unsigned)(sizeof(msg_enter) - 1));
  LispObj result = wasm_funcall0(fn_value);
  wasm_host_log(msg_exit, (unsigned)(sizeof(msg_exit) - 1));
  return result;
}

static uint32_t
wasm_const_pool_read_u32(const uint8_t *bytes,
                         uint32_t len,
                         uint32_t *offset,
                         int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset || (*offset + 4u) > len) {
    if (ok) *ok = 0;
    return 0;
  }
  uint32_t pos = *offset;
  uint32_t v = (uint32_t)bytes[pos]
               | ((uint32_t)bytes[pos + 1] << 8)
               | ((uint32_t)bytes[pos + 2] << 16)
               | ((uint32_t)bytes[pos + 3] << 24);
  *offset = pos + 4u;
  return v;
}

static uint32_t
wasm_const_pool_read_uleb32(const uint8_t *bytes,
                            uint32_t len,
                            uint32_t *offset,
                            int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset) {
    if (ok) *ok = 0;
    return 0;
  }

  uint32_t value = 0;
  uint32_t shift = 0;
  for (uint32_t i = 0; i < 5; i++) {
    if (*offset >= len) {
      if (ok) *ok = 0;
      return 0;
    }
    uint8_t byte = bytes[*offset];
    (*offset)++;
    value |= ((uint32_t)(byte & 0x7fu)) << shift;
    if ((byte & 0x80u) == 0u) {
      return value;
    }
    shift += 7;
  }

  if (ok) *ok = 0;
  return 0;
}

static int32_t
wasm_const_pool_read_sleb32(const uint8_t *bytes,
                            uint32_t len,
                            uint32_t *offset,
                            int *ok)
{
  if (!ok || !*ok) {
    return 0;
  }
  if (!bytes || !offset) {
    if (ok) *ok = 0;
    return 0;
  }

  int64_t value = 0;
  uint32_t shift = 0;
  uint8_t byte = 0;
  for (uint32_t i = 0; i < 5; i++) {
    if (*offset >= len) {
      if (ok) *ok = 0;
      return 0;
    }
    byte = bytes[*offset];
    (*offset)++;
    value |= ((int64_t)(byte & 0x7fu)) << shift;
    shift += 7;
    if ((byte & 0x80u) == 0u) {
      if ((shift < 32u) && (byte & 0x40u)) {
        value |= -((int64_t)1 << shift);
      }
      if ((value < INT32_MIN) || (value > INT32_MAX)) {
        if (ok) *ok = 0;
        return 0;
      }
      return (int32_t)value;
    }
  }

  if (ok) *ok = 0;
  return 0;
}

static uint32_t
wasm_const_pool_read_nat(const uint8_t *bytes,
                         uint32_t len,
                         uint32_t *offset,
                         uint32_t version,
                         int *ok)
{
  return (version >= 2u)
    ? wasm_const_pool_read_uleb32(bytes, len, offset, ok)
    : wasm_const_pool_read_u32(bytes, len, offset, ok);
}

static const uint8_t *
wasm_const_pool_read_bytes(const uint8_t *bytes,
                           uint32_t len,
                           uint32_t *offset,
                           uint32_t count,
                           int *ok)
{
  if (!ok || !*ok) {
    return NULL;
  }
  if (!bytes || !offset || (*offset + count) > len) {
    if (ok) *ok = 0;
    return NULL;
  }
  const uint8_t *out = bytes + *offset;
  *offset += count;
  return out;
}

static int
wasm_lisp_string_equals_bytes(LispObj str,
                              const uint8_t *bytes,
                              uint32_t len)
{
  if (!bytes) {
    return 0;
  }
  if (fulltag_of(str) != fulltag_misc) {
    return 0;
  }
  LispObj header = header_of(str);
  if (header_subtag(header) != subtag_simple_base_string) {
    return 0;
  }
  uint32_t count = (uint32_t)header_element_count(header);
  if (count != len) {
    return 0;
  }
  uint32_t *data = (uint32_t *)((BytePtr)str + misc_data_offset);
  for (uint32_t i = 0; i < len; i++) {
    if ((data[i] & 0xffu) != bytes[i]) {
      return 0;
    }
  }
  return 1;
}

static int
wasm_package_names_contains(LispObj names,
                            const uint8_t *bytes,
                            uint32_t len)
{
  if (fulltag_of(names) == fulltag_misc) {
    LispObj header = header_of(names);
    if (header_subtag(header) == subtag_simple_base_string) {
      return wasm_lisp_string_equals_bytes(names, bytes, len);
    }
  }
  LispObj list = names;
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      return 0;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    if (wasm_lisp_string_equals_bytes(cell->car, bytes, len)) {
      return 1;
    }
    list = cell->cdr;
  }
  return 0;
}

static LispObj
wasm_find_package_named_bytes(const uint8_t *bytes, uint32_t len)
{
  LispObj list = nrs_ALL_PACKAGES.vcell;
  if (fulltag_of(list) == fulltag_misc) {
    LispObj header = header_of(list);
    if (header_subtag(header) == subtag_package) {
      package *pkg = (package *)ptr_from_lispobj(untag(list));
      if (wasm_package_names_contains(pkg->names, bytes, len)) {
        return list;
      }
    }
  }
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      break;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    LispObj pkg_obj = cell->car;
    if (fulltag_of(pkg_obj) == fulltag_misc) {
      LispObj header = header_of(pkg_obj);
      if (header_subtag(header) == subtag_package) {
        package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
        if (wasm_package_names_contains(pkg->names, bytes, len)) {
          return pkg_obj;
        }
      }
    }
    list = cell->cdr;
  }
  return lisp_nil;
}

static int
wasm_symbol_package_matches(lispsymbol *rawsym, LispObj package)
{
  if (package == (LispObj)0) {
    return 1;
  }
  LispObj predicate = rawsym->package_predicate;
  if (fulltag_of(predicate) == fulltag_cons) {
    predicate = car(predicate);
  }
  return predicate == package;
}

static LispObj
wasm_package_symbol_vector(LispObj table)
{
  if (table == lisp_nil) {
    return (LispObj)0;
  }
  LispObj vec = table;
  if (fulltag_of(vec) == fulltag_cons) {
    vec = car(vec);
  }
  if (fulltag_of(vec) != fulltag_misc) {
    return (LispObj)0;
  }
  LispObj header = header_of(vec);
  natural subtag = header_subtag(header);
  if (subtag != subtag_simple_vector && subtag != subtag_hash_vector) {
    return (LispObj)0;
  }
  return vec;
}

static LispObj
wasm_find_symbol_in_vector_bytes(LispObj vec,
                                 const uint8_t *name,
                                 uint32_t len)
{
  if (vec == (LispObj)0 || !name || len == 0) {
    return (LispObj)0;
  }
  uint32_t count = (uint32_t)header_element_count(header_of(vec));
  LispObj *data = (LispObj *)((BytePtr)vec + misc_data_offset);
  for (uint32_t i = 0; i < count; i++) {
    LispObj sym = data[i];
    if (fulltag_of(sym) != fulltag_misc || header_subtag(header_of(sym)) != subtag_symbol) {
      continue;
    }
    lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
    if (wasm_lisp_string_equals_bytes(rawsym->pname, name, len)) {
      return sym;
    }
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_in_package_tables_bytes(LispObj pkg_obj,
                                         const uint8_t *name,
                                         uint32_t len)
{
  if (pkg_obj == (LispObj)0 ||
      fulltag_of(pkg_obj) != fulltag_misc ||
      header_subtag(header_of(pkg_obj)) != subtag_package) {
    return (LispObj)0;
  }
  package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
  LispObj itab_vec = wasm_package_symbol_vector(pkg->itab);
  LispObj sym = wasm_find_symbol_in_vector_bytes(itab_vec, name, len);
  if (sym) {
    return sym;
  }
  LispObj etab_vec = wasm_package_symbol_vector(pkg->etab);
  return wasm_find_symbol_in_vector_bytes(etab_vec, name, len);
}

static LispObj
wasm_find_symbol_in_all_packages_bytes(const uint8_t *name, uint32_t len)
{
  LispObj list = nrs_ALL_PACKAGES.vcell;
  if (fulltag_of(list) == fulltag_misc &&
      header_subtag(header_of(list)) == subtag_package) {
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(list, name, len);
    if (sym) {
      return sym;
    }
  }
  while (list != lisp_nil) {
    if (fulltag_of(list) != fulltag_cons) {
      break;
    }
    cons *cell = (cons *)ptr_from_lispobj(untag(list));
    LispObj pkg_obj = cell->car;
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(pkg_obj, name, len);
    if (sym) {
      return sym;
    }
    list = cell->cdr;
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_in_range_bytes(LispObj *start,
                                LispObj *end,
                                const uint8_t *name,
                                uint32_t len,
                                LispObj package)
{
  LispObj header;
  LispObj tag;
  while (start < end) {
    header = *start;
    tag = fulltag_of(header);
    if (header_subtag(header) == subtag_symbol) {
      LispObj pname = deref(ptr_to_lispobj(start), 1);
      LispObj pname_header = header_of(pname);
      if ((header_subtag(pname_header) == subtag_simple_base_string) &&
          ((uint32_t)header_element_count(pname_header) == len)) {
        uint32_t *p = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);
        int match = 1;
        for (uint32_t i = 0; i < len; i++) {
          if ((p[i] & 0xffu) != name[i]) {
            match = 0;
            break;
          }
        }
        if (match) {
          lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(ptr_to_lispobj(start));
          if (wasm_symbol_package_matches(rawsym, package)) {
            return ptr_to_lispobj(start) + fulltag_misc;
          }
        }
      }
    }
    if (nodeheader_tag_p(tag)) {
      start += (~1 & (2 + header_element_count(header)));
    } else if (immheader_tag_p(tag)) {
      start = (LispObj *)skip_over_ivector((natural)start, header);
    } else {
      start += 2;
    }
  }
  return (LispObj)0;
}

static LispObj
wasm_find_symbol_named_bytes(const uint8_t *name, uint32_t len, LispObj package)
{
  if (!name || len == 0) {
    return (LispObj)0;
  }
  if (package != (LispObj)0) {
    LispObj sym = wasm_find_symbol_in_package_tables_bytes(package, name, len);
    if (sym) {
      return sym;
    }
  } else {
    LispObj sym = wasm_find_symbol_in_all_packages_bytes(name, len);
    if (sym) {
      return sym;
    }
  }

  area *a = ((area *)ptr_from_lispobj(lisp_global(ALL_AREAS)))->succ;
  while (a->code != AREA_VOID) {
    area_code code = a->code;
    if ((code == AREA_STATIC) ||
        (code == AREA_DYNAMIC) ||
        (code == AREA_MANAGED_STATIC) ||
        (code == AREA_READONLY) ||
        (code == AREA_WATCHED) ||
        (code == AREA_STATIC_CONS)) {
      LispObj sym = wasm_find_symbol_in_range_bytes((LispObj *)a->low,
                                                    (LispObj *)a->active,
                                                    name,
                                                    len,
                                                    package);
      if (sym) {
        return sym;
      }
    }
    a = a->succ;
  }
  return (LispObj)0;
}

static LispObj
wasm_const_pool_make_base_string(TCR *tcr, const uint8_t *bytes, uint32_t len)
{
  if (tcr == NULL) {
    return lisp_nil;
  }
  LispObj obj = wasm_misc_alloc(tcr, subtag_simple_base_string, (signed_natural)len);
  if (obj == lisp_nil) {
    return lisp_nil;
  }
  uint32_t *data = (uint32_t *)((BytePtr)obj + misc_data_offset);
  for (uint32_t i = 0; i < len; i++) {
    data[i] = (uint32_t)bytes[i];
  }
  return obj;
}

static LispObj
wasm_alloc_cons(TCR *tcr, LispObj car_value, LispObj cdr_value)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  if (!wasm_reserve_heap_segment(tcr, (size_t)dnode_size)) {
    return lisp_nil;
  }

  BytePtr alloc_ptr = (BytePtr)tcr->save_allocptr;
  BytePtr alloc_base = (BytePtr)tcr->save_allocbase;
  BytePtr newptr = alloc_ptr - (signed_natural)dnode_size;
  if (newptr < alloc_base) {
    return lisp_nil;
  }

  tcr->save_allocptr = (void *)newptr;
  LispObj obj = (LispObj)(newptr + fulltag_cons);

  cons *cell = (cons *)ptr_from_lispobj(untag(obj));
  cell->car = car_value;
  cell->cdr = cdr_value;
  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_alloc_cons_bridge")))
LispObj
wasm_alloc_cons_bridge(LispObj car_value, LispObj cdr_value)
{
  TCR *tcr = wasm_get_current_tcr();
  return wasm_alloc_cons(tcr, car_value, cdr_value);
}

static LispObj
wasm_const_pool_intern_symbol(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg);

static int32_t
wasm_set_command_line_output_arg(TCR *tcr, const uint8_t *output_bytes, uint32_t output_len)
{
  static const uint8_t argv_sym_name[] = {
    '*', 'C', 'O', 'M', 'M', 'A', 'N', 'D', '-', 'L', 'I', 'N', 'E', '-',
    'A', 'R', 'G', 'U', 'M', 'E', 'N', 'T', '-', 'L', 'I', 'S', 'T', '*'
  };
  static const uint8_t delimiter[] = { '-', '-' };
  static const uint8_t output_opt[] = { '-', '-', 'o', 'u', 't', 'p', 'u', 't' };

  if (tcr == NULL || output_bytes == NULL || output_len == 0) {
    return -1;
  }

  LispObj argv_sym = wasm_find_symbol_named_bytes(argv_sym_name, (uint32_t)sizeof(argv_sym_name), (LispObj)0);
  if (argv_sym == (LispObj)0) {
    static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };
    LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
    if (ccl_pkg != lisp_nil) {
      argv_sym = wasm_const_pool_intern_symbol(
        tcr,
        argv_sym_name,
        (uint32_t)sizeof(argv_sym_name),
        ccl_pkg);
    }
  }
  if (argv_sym == (LispObj)0) {
    argv_sym = wasm_const_pool_intern_symbol(
      tcr,
      argv_sym_name,
      (uint32_t)sizeof(argv_sym_name),
      (LispObj)0);
  }
  if (argv_sym == (LispObj)0 ||
      fulltag_of(argv_sym) != fulltag_misc ||
      header_subtag(header_of(argv_sym)) != subtag_symbol) {
    return -2;
  }

  LispObj delim_str = wasm_const_pool_make_base_string(tcr, delimiter, (uint32_t)sizeof(delimiter));
  LispObj opt_str = wasm_const_pool_make_base_string(tcr, output_opt, (uint32_t)sizeof(output_opt));
  LispObj out_str = wasm_const_pool_make_base_string(tcr, output_bytes, output_len);
  if (delim_str == lisp_nil || opt_str == lisp_nil || out_str == lisp_nil) {
    return -3;
  }

  LispObj list = lisp_nil;
  list = wasm_alloc_cons(tcr, out_str, list);
  if (list == lisp_nil) return -4;
  list = wasm_alloc_cons(tcr, opt_str, list);
  if (list == lisp_nil) return -4;
  list = wasm_alloc_cons(tcr, delim_str, list);
  if (list == lisp_nil) return -4;

  lispsymbol *argv_raw = (lispsymbol *)ptr_from_lispobj(untag(argv_sym));
  argv_raw->vcell = list;
  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_run_script_with_output")))
int32_t
wasm_run_script_with_output(uint32_t script_ptr, uint32_t script_len, uint32_t output_ptr, uint32_t output_len)
{
  static const uint8_t load_sym_name_upper[] = { 'L', 'O', 'A', 'D' };
  static const uint8_t load_sym_name_lower[] = { 'l', 'o', 'a', 'd' };
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  static const uint8_t ccl_pkg_name[] = { 'C', 'C', 'L' };

  if (script_ptr == 0 || script_len == 0) {
    return -1;
  }

  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return -2;
  }
  if (!wasm_subprims_ready) {
    return -3;
  }

  if (output_ptr != 0 && output_len != 0) {
    int32_t argv_rc = wasm_set_command_line_output_arg(
      tcr,
      (const uint8_t *)(uintptr_t)output_ptr,
      output_len);
    if (argv_rc != 0) {
      return -10 + argv_rc;
    }
  }

  LispObj load_sym = wasm_find_symbol_named_bytes(
    load_sym_name_upper,
    (uint32_t)sizeof(load_sym_name_upper),
    (LispObj)0);
  if (load_sym == (LispObj)0) {
    load_sym = wasm_find_symbol_named_bytes(
      load_sym_name_lower,
      (uint32_t)sizeof(load_sym_name_lower),
      (LispObj)0);
  }
  if (load_sym == (LispObj)0) {
    LispObj cl_pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
    if (cl_pkg != lisp_nil) {
      load_sym = wasm_const_pool_intern_symbol(
        tcr,
        load_sym_name_upper,
        (uint32_t)sizeof(load_sym_name_upper),
        cl_pkg);
    }
  }
  if (load_sym == (LispObj)0) {
    LispObj ccl_pkg = wasm_find_package_named_bytes(ccl_pkg_name, (uint32_t)sizeof(ccl_pkg_name));
    if (ccl_pkg != lisp_nil) {
      load_sym = wasm_const_pool_intern_symbol(
        tcr,
        load_sym_name_upper,
        (uint32_t)sizeof(load_sym_name_upper),
        ccl_pkg);
    }
  }
  if (load_sym == (LispObj)0) {
    static const uint8_t toplevel_sym_name[] = {
      '%', 'T', 'O', 'P', 'L', 'E', 'V', 'E', 'L', '-', 'F', 'U', 'N', 'C', 'T', 'I', 'O', 'N', '%'
    };
    LispObj top_sym = wasm_find_symbol_named_bytes(
      toplevel_sym_name,
      (uint32_t)sizeof(toplevel_sym_name),
      (LispObj)0);
    return (top_sym == (LispObj)0) ? -41 : -4;
  }

  LispObj script_path = wasm_const_pool_make_base_string(
    tcr,
    (const uint8_t *)(uintptr_t)script_ptr,
    script_len);
  if (script_path == lisp_nil) {
    return -5;
  }

  (void)wasm_funcall1(load_sym, script_path);
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
    return -6;
  }
  return 0;
}

static LispObj
wasm_const_pool_make_package(TCR *tcr, const uint8_t *bytes, uint32_t len)
{
  if (tcr == NULL || bytes == NULL || len == 0) {
    return lisp_nil;
  }

  const signed_natural count = (signed_natural)((sizeof(package) / sizeof(LispObj)) - 1);
  LispObj pkg_obj = wasm_misc_alloc(tcr, subtag_package, count);
  if (pkg_obj == lisp_nil) {
    return lisp_nil;
  }

  LispObj name_str = wasm_const_pool_make_base_string(tcr, bytes, len);
  if (name_str == lisp_nil) {
    return lisp_nil;
  }

  package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
  pkg->itab = lisp_nil;
  pkg->etab = lisp_nil;
  pkg->used = lisp_nil;
  pkg->used_by = lisp_nil;
  pkg->names = name_str;
  pkg->shadowed = lisp_nil;

  return pkg_obj;
}

static LispObj
wasm_const_pool_register_package(TCR *tcr, LispObj pkg_obj)
{
  if (tcr == NULL || pkg_obj == lisp_nil) {
    return lisp_nil;
  }

  LispObj list = nrs_ALL_PACKAGES.vcell;
  if (list == lisp_nil || fulltag_of(list) != fulltag_cons) {
    LispObj cell = wasm_alloc_cons(tcr, pkg_obj, lisp_nil);
    if (cell == lisp_nil) {
      return lisp_nil;
    }
    nrs_ALL_PACKAGES.vcell = cell;
    return pkg_obj;
  }

  LispObj cell = wasm_alloc_cons(tcr, pkg_obj, list);
  if (cell == lisp_nil) {
    return lisp_nil;
  }
  nrs_ALL_PACKAGES.vcell = cell;
  return pkg_obj;
}

static void
wasm_log_const_pool_fallback(const char *prefix,
                             unsigned prefix_len,
                             const uint8_t *bytes,
                             uint32_t len)
{
  static const char newline[] = "\n";
  if (prefix && prefix_len) {
    wasm_host_log(prefix, prefix_len);
  }
  if (bytes && len) {
    wasm_host_log((const char *)bytes, (unsigned)len);
  }
  wasm_host_log(newline, 1);
}

static void
wasm_log_const_pool_function_failure(uint32_t entry_index,
                                     const char *reason,
                                     const uint8_t *name_bytes,
                                     uint32_t name_len)
{
  char prefix[160];
  int n = snprintf(
    prefix,
    sizeof(prefix),
    "WASM const-pool function failure: entry=%u reason=%s name=",
    (unsigned)entry_index,
    reason ? reason : "?");
  if (n > 0) {
    wasm_host_log(prefix, (unsigned)n);
  }
  if (name_bytes && name_len) {
    wasm_host_log((const char *)name_bytes, (unsigned)name_len);
  }
  wasm_host_log("\n", 1);
}

static LispObj
wasm_const_pool_ensure_package(TCR *tcr, const uint8_t *bytes, uint32_t len)
{
  if (!bytes || len == 0) {
    return (LispObj)0;
  }

  LispObj pkg = wasm_find_package_named_bytes(bytes, len);
  if (pkg != lisp_nil) {
    return pkg;
  }
  if (tcr == NULL) {
    return lisp_nil;
  }

  {
    static const char msg_create_pkg[] = "WASM const-pool: creating package fallback: ";
    wasm_log_const_pool_fallback(msg_create_pkg,
                                 (unsigned)(sizeof(msg_create_pkg) - 1),
                                 bytes,
                                 len);
  }

  LispObj created = wasm_const_pool_make_package(tcr, bytes, len);
  if (created == lisp_nil) {
    return lisp_nil;
  }

  if (len == 7 &&
      bytes[0] == 'K' && bytes[1] == 'E' && bytes[2] == 'Y' &&
      bytes[3] == 'W' && bytes[4] == 'O' && bytes[5] == 'R' &&
      bytes[6] == 'D') {
    nrs_KEYWORD_PACKAGE.vcell = created;
  }

  return wasm_const_pool_register_package(tcr, created);
}

static LispObj
wasm_const_pool_find_symbol_in_pools(const uint8_t *name_bytes, uint32_t name_len, LispObj package)
{
  if (!name_bytes || name_len == 0) {
    return (LispObj)0;
  }

  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil) {
    return (LispObj)0;
  }
  if (fulltag_of(table) != fulltag_misc || header_subtag(header_of(table)) != subtag_simple_vector) {
    return (LispObj)0;
  }

  uint32_t table_count = (uint32_t)header_element_count(header_of(table));
  LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
  for (uint32_t i = 0; i < table_count; i++) {
    LispObj pool = table_data[i];
    if (pool == lisp_nil) {
      continue;
    }
    if (fulltag_of(pool) != fulltag_misc || header_subtag(header_of(pool)) != subtag_simple_vector) {
      continue;
    }
    uint32_t pool_count = (uint32_t)header_element_count(header_of(pool));
    LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);
    for (uint32_t j = 0; j < pool_count; j++) {
      LispObj sym = pool_data[j];
      if (fulltag_of(sym) != fulltag_misc || header_subtag(header_of(sym)) != subtag_symbol) {
        continue;
      }
      lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
      if (!wasm_symbol_package_matches(rawsym, package)) {
        continue;
      }
      if (wasm_lisp_string_equals_bytes(rawsym->pname, name_bytes, name_len)) {
        return sym;
      }
    }
  }
  return (LispObj)0;
}

static LispObj
wasm_const_pool_make_symbol(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj package)
{
  if (tcr == NULL || !name_bytes || name_len == 0) {
    return (LispObj)0;
  }

  {
    static const char msg_make_sym[] = "WASM const-pool: creating symbol fallback: ";
    wasm_log_const_pool_fallback(msg_make_sym,
                                 (unsigned)(sizeof(msg_make_sym) - 1),
                                 name_bytes,
                                 name_len);
  }

  LispObj pname = wasm_const_pool_make_base_string(tcr, name_bytes, name_len);
  if (pname == lisp_nil) {
    return (LispObj)0;
  }

  const signed_natural count = (signed_natural)((sizeof(lispsymbol) / sizeof(LispObj)) - 1);
  LispObj sym_obj = wasm_misc_alloc(tcr, subtag_symbol, count);
  if (sym_obj == lisp_nil) {
    return (LispObj)0;
  }

  lispsymbol *sym = (lispsymbol *)ptr_from_lispobj(untag(sym_obj));
  sym->pname = pname;
  sym->vcell = undefined;
  sym->fcell = nrs_UDF.vcell;
  sym->package_predicate = package ? package : lisp_nil;
  sym->flags = box_fixnum(0);
  sym->plist = lisp_nil;
  sym->binding_index = box_fixnum(0);

  if (package != (LispObj)0 && package == nrs_KEYWORD_PACKAGE.vcell) {
    sym->vcell = sym_obj;
  }

  return sym_obj;
}

static LispObj
wasm_const_pool_intern_symbol(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  if (tcr == NULL || name_bytes == NULL || name_len == 0) {
    return (LispObj)0;
  }

  static LispObj intern_sym = (LispObj)0;
  if (intern_sym == (LispObj)0) {
    static const uint8_t intern_name[] = { 'I', 'N', 'T', 'E', 'R', 'N' };
    static const uint8_t cl_pkg_name[] = {
      'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
    };
    LispObj cl_pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
    if (cl_pkg != lisp_nil) {
      intern_sym = wasm_find_symbol_named_bytes(
        intern_name,
        (uint32_t)sizeof(intern_name),
        cl_pkg);
    }
    if (intern_sym == (LispObj)0) {
      intern_sym = wasm_find_symbol_named_bytes(
        intern_name,
        (uint32_t)sizeof(intern_name),
        (LispObj)0);
    }
    if (!intern_sym) {
      static const char msg[] = "WASM const-pool: INTERN symbol unavailable for ";
      wasm_log_const_pool_fallback(msg, (unsigned)(sizeof(msg) - 1), name_bytes, name_len);
      return (LispObj)0;
    }
  }

  if (fulltag_of(intern_sym) != fulltag_misc ||
      header_subtag(header_of(intern_sym)) != subtag_symbol) {
    return (LispObj)0;
  }
  lispsymbol *intern_rawsym = (lispsymbol *)ptr_from_lispobj(untag(intern_sym));
  if (intern_rawsym->fcell == nrs_UDF.vcell) {
    static const char msg[] = "WASM const-pool: INTERN fcell UDF for ";
    wasm_log_const_pool_fallback(msg, (unsigned)(sizeof(msg) - 1), name_bytes, name_len);
    return (LispObj)0;
  }

  LispObj name_str = wasm_const_pool_make_base_string(tcr, name_bytes, name_len);
  if (name_str == lisp_nil) {
    return (LispObj)0;
  }

  LispObj pkg_arg = pkg;
  if (pkg_arg == (LispObj)0) {
    pkg_arg = nrs_PACKAGE.vcell;
  }

  LispObj result = wasm_funcall2(intern_sym, name_str, pkg_arg);
  if (tcr->wasm_pending_throw) {
    tcr->wasm_pending_throw = 0;
    static const char msg[] = "WASM const-pool: INTERN threw for ";
    wasm_log_const_pool_fallback(msg, (unsigned)(sizeof(msg) - 1), name_bytes, name_len);
    return (LispObj)0;
  }
  if (result == lisp_nil) {
    static const char msg[] = "WASM const-pool: INTERN returned NIL for ";
    wasm_log_const_pool_fallback(msg, (unsigned)(sizeof(msg) - 1), name_bytes, name_len);
    return (LispObj)0;
  }
  return result;
}

static LispObj
wasm_const_pool_table_ensure(TCR *tcr, uint32_t entry_index)
{
  if (tcr == NULL) {
    return lisp_nil;
  }

  LispObj table = nrs_WASM_CONST_POOLS.vcell;
  if (table == lisp_nil) {
    uint32_t count = entry_index + 1u;
    LispObj obj = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)count);
    if (obj == lisp_nil) {
      return lisp_nil;
    }
    nrs_WASM_CONST_POOLS.vcell = obj;
    return obj;
  }

  if (fulltag_of(table) != fulltag_misc || header_subtag(header_of(table)) != subtag_simple_vector) {
    return lisp_nil;
  }

  uint32_t count = (uint32_t)header_element_count(header_of(table));
  if (entry_index < count) {
    return table;
  }

  uint32_t new_count = entry_index + 1u;
  LispObj obj = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)new_count);
  if (obj == lisp_nil) {
    return lisp_nil;
  }

  LispObj *dst = (LispObj *)((BytePtr)obj + misc_data_offset);
  LispObj *src = (LispObj *)((BytePtr)table + misc_data_offset);
  for (uint32_t i = 0; i < new_count; i++) {
    dst[i] = (i < count) ? src[i] : lisp_nil;
  }

  nrs_WASM_CONST_POOLS.vcell = obj;
  return obj;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_install")))
LispObj
wasm_const_pool_install(uint32_t entry_index, uint32_t payload_ptr, uint32_t payload_len)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) {
    return lisp_nil;
  }

  if (payload_ptr == 0 || payload_len == 0u) {
    return lisp_nil;
  }

  const uint8_t *bytes = (const uint8_t *)(uintptr_t)payload_ptr;
  uint32_t offset = 0;
  int ok = 1;

  uint32_t version = 0;
  uint32_t count = 0;
  if (payload_len >= 8u &&
      bytes[0] == 1u &&
      bytes[1] == 0u &&
      bytes[2] == 0u &&
      bytes[3] == 0u) {
    version = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
    count = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
  } else {
    version = wasm_const_pool_read_uleb32(bytes, payload_len, &offset, &ok);
    count = wasm_const_pool_read_uleb32(bytes, payload_len, &offset, &ok);
  }
  if (!ok || (version != 1u && version != 2u)) {
    return lisp_nil;
  }

  LispObj pool = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)count);
  if (pool == lisp_nil) {
    return lisp_nil;
  }
  LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);

  for (uint32_t i = 0; i < count; i++) {
    uint32_t tag = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
    if (!ok) {
      return lisp_nil;
    }
    switch (tag) {
      case 6: { /* fixnum */
        if (version >= 2u) {
          int32_t sval = wasm_const_pool_read_sleb32(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          pool_data[i] = (LispObj)(uint32_t)sval;
        } else {
          uint32_t raw = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          pool_data[i] = (LispObj)raw;
        }
        break;
      }
      case 10: { /* character */
        uint32_t code = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        pool_data[i] = (LispObj)((code << charcode_shift) | subtag_character);
        break;
      }
      case 11: { /* single-float */
        uint32_t bits = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        signed_natural count = (signed_natural)((sizeof(single_float) / sizeof(LispObj)) - 1);
        LispObj obj = wasm_misc_alloc(tcr, subtag_single_float, count);
        if (obj == lisp_nil) {
          return lisp_nil;
        }
        single_float *sf = (single_float *)ptr_from_lispobj(untag(obj));
        sf->value = (LispObj)bits;
        pool_data[i] = obj;
        break;
      }
      case 12: { /* double-float */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        signed_natural count = (signed_natural)((sizeof(double_float) / sizeof(LispObj)) - 1);
        LispObj obj = wasm_misc_alloc(tcr, subtag_double_float, count);
        if (obj == lisp_nil) {
          return lisp_nil;
        }
        double_float *df = (double_float *)ptr_from_lispobj(untag(obj));
        df->value_high = (LispObj)hi;
        df->value_low = (LispObj)lo;
        pool_data[i] = obj;
        break;
      }
      case 13: { /* int64 */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        int64_t value = ((int64_t)hi << 32) | (int64_t)lo;
        pool_data[i] = wasm_box_signed_64(tcr, value);
        break;
      }
      case 14: { /* uint64 */
        uint32_t hi = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        uint32_t lo = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
        if (!ok) {
          return lisp_nil;
        }
        uint64_t value = ((uint64_t)hi << 32) | (uint64_t)lo;
        pool_data[i] = wasm_box_unsigned_64(tcr, value);
        break;
      }
      case 15: { /* bignum */
        uint32_t digits = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        uint32_t *data = NULL;
        LispObj obj = wasm_alloc_bignum_uninitialized(tcr, digits, &data);
        if (obj == lisp_nil || data == NULL) {
          return lisp_nil;
        }
        for (uint32_t d = 0; d < digits; d++) {
          uint32_t word = wasm_const_pool_read_u32(bytes, payload_len, &offset, &ok);
          if (!ok) {
            return lisp_nil;
          }
          data[d] = word;
        }
        pool_data[i] = obj;
        break;
      }
      case 1: { /* symbol */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *pkg_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, pkg_len, &ok);
        if (!ok || !name_bytes) {
          return lisp_nil;
        }
        LispObj pkg = (LispObj)0;
        int pkg_missing = 0;
        if (pkg_len > 0 && pkg_bytes) {
          if (pkg_len == 7 &&
              pkg_bytes[0] == 'K' && pkg_bytes[1] == 'E' && pkg_bytes[2] == 'Y' &&
              pkg_bytes[3] == 'W' && pkg_bytes[4] == 'O' && pkg_bytes[5] == 'R' &&
              pkg_bytes[6] == 'D') {
            pkg = nrs_KEYWORD_PACKAGE.vcell;
          } else {
            LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
            if (found != lisp_nil) {
              pkg = found;
            } else {
              pkg_missing = 1;
            }
          }
        }
        /*
         * Prefer INTERN for package-qualified symbols so we resolve the
         * canonical package entry instead of arbitrary same-name heap symbols.
         * Keep raw scan as fallback for early bring-up phases where INTERN
         * may not yet be callable.
         */
        LispObj sym = (LispObj)0;
        if (!pkg_missing && pkg != (LispObj)0) {
          sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
        }
        if (!sym) {
          sym = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg);
          if (!sym && pkg_missing) {
            sym = wasm_find_symbol_named_bytes(name_bytes, name_len, (LispObj)0);
          }
        }
        if (!sym) {
          if (pkg_missing) {
            LispObj found = wasm_const_pool_ensure_package(tcr, pkg_bytes, pkg_len);
            if (found == lisp_nil) {
              return lisp_nil;
            }
            pkg = found;
          }
          sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
          if (!sym) {
            sym = wasm_const_pool_find_symbol_in_pools(name_bytes, name_len, pkg);
          }
          if (!sym) {
            sym = wasm_const_pool_make_symbol(tcr, name_bytes, name_len, pkg);
          }
          if (!sym) {
            return lisp_nil;
          }
        }
        pool_data[i] = sym;
        break;
      }
      case 2: { /* string */
        uint32_t len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *data = wasm_const_pool_read_bytes(bytes, payload_len, &offset, len, &ok);
        if (!ok || !data) {
          return lisp_nil;
        }
        LispObj str = wasm_const_pool_make_base_string(tcr, data, len);
        if (str == lisp_nil) {
          return lisp_nil;
        }
        pool_data[i] = str;
        break;
      }
      case 3: { /* vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, subtag_simple_vector, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 4: { /* function */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *pkg_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, pkg_len, &ok);
        if (!ok || !name_bytes) {
          return lisp_nil;
        }
        LispObj pkg = (LispObj)0;
        int pkg_missing = 0;
        if (pkg_len > 0 && pkg_bytes) {
          if (pkg_len == 7 &&
              pkg_bytes[0] == 'K' && pkg_bytes[1] == 'E' && pkg_bytes[2] == 'Y' &&
              pkg_bytes[3] == 'W' && pkg_bytes[4] == 'O' && pkg_bytes[5] == 'R' &&
              pkg_bytes[6] == 'D') {
            pkg = nrs_KEYWORD_PACKAGE.vcell;
          } else {
            LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
            if (found != lisp_nil) {
              pkg = found;
            } else {
              pkg_missing = 1;
            }
          }
        }
        LispObj sym = (LispObj)0;
        if (!pkg_missing && pkg != (LispObj)0) {
          sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
        }
        if (!sym) {
          sym = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg);
          if (!sym && pkg_missing) {
            sym = wasm_find_symbol_named_bytes(name_bytes, name_len, (LispObj)0);
          }
        }
        if (!sym) {
          if (pkg_missing) {
            LispObj found = wasm_const_pool_ensure_package(tcr, pkg_bytes, pkg_len);
            if (found == lisp_nil) {
              return lisp_nil;
            }
            pkg = found;
          }
          sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
          if (!sym) {
            wasm_log_const_pool_function_failure(entry_index, "symbol-missing", name_bytes, name_len);
            return lisp_nil;
          }
        }
        lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
        LispObj fn = rawsym->fcell;
        if (fn == nrs_UDF.vcell) {
          wasm_log_const_pool_function_failure(entry_index, "fcell-udf", name_bytes, name_len);
          return lisp_nil;
        }
        pool_data[i] = fn;
        break;
      }
      case 5: { /* function-vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, subtag_function, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 16: { /* entry-function */
        uint32_t entry_index = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, subtag_function, (signed_natural)2);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj entry = box_fixnum((signed_natural)entry_index);
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        vec_data[0] = entry;
        vec_data[1] = entry;
        pool_data[i] = vec;
        break;
      }
      case 9: { /* gvector */
        uint32_t raw_subtag = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok) {
          return lisp_nil;
        }
        LispObj vec = wasm_misc_alloc(tcr, (unsigned)raw_subtag, (signed_natural)vcount);
        if (vec == lisp_nil) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
          if (!ok || idx >= count) {
            return lisp_nil;
          }
          if (idx < i) {
            vec_data[j] = pool_data[idx];
          }
        }
        pool_data[i] = vec;
        break;
      }
      case 7: { /* package */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        const uint8_t *name_bytes = wasm_const_pool_read_bytes(bytes, payload_len, &offset, name_len, &ok);
        if (!ok || !name_bytes) {
          return lisp_nil;
        }
        LispObj pkg = wasm_const_pool_ensure_package(tcr, name_bytes, name_len);
        if (pkg == lisp_nil) {
          return lisp_nil;
        }
        pool_data[i] = pkg;
        break;
      }
      case 8: { /* cons */
        uint32_t car_idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        uint32_t cdr_idx = wasm_const_pool_read_nat(bytes, payload_len, &offset, version, &ok);
        if (!ok || car_idx >= count || cdr_idx >= count) {
          return lisp_nil;
        }
        LispObj cell = wasm_alloc_cons(tcr, lisp_nil, lisp_nil);
        if (cell == lisp_nil) {
          return lisp_nil;
        }
        if (car_idx < i) {
          cons *raw = (cons *)ptr_from_lispobj(untag(cell));
          raw->car = pool_data[car_idx];
        }
        if (cdr_idx < i) {
          cons *raw = (cons *)ptr_from_lispobj(untag(cell));
          raw->cdr = pool_data[cdr_idx];
        }
        pool_data[i] = cell;
        break;
      }
      default:
        return lisp_nil;
    }
  }

  /* Second pass: patch forward references in vectors/gvectors/function-vectors/conses. */
  uint32_t patch_offset = 0;
  int patch_ok = 1;
  uint32_t patch_version = 0;
  uint32_t patch_count = 0;
  if (payload_len >= 8u &&
      bytes[0] == 1u &&
      bytes[1] == 0u &&
      bytes[2] == 0u &&
      bytes[3] == 0u) {
    patch_version = wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
    patch_count = wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
  } else {
    patch_version = wasm_const_pool_read_uleb32(bytes, payload_len, &patch_offset, &patch_ok);
    patch_count = wasm_const_pool_read_uleb32(bytes, payload_len, &patch_offset, &patch_ok);
  }
  if (!patch_ok || patch_version != version || patch_count != count) {
    return lisp_nil;
  }
  for (uint32_t i = 0; i < count; i++) {
    uint32_t tag = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
    if (!patch_ok) {
      return lisp_nil;
    }
    switch (tag) {
      case 6: { /* fixnum */
        if (patch_version >= 2u) {
          (void)wasm_const_pool_read_sleb32(bytes, payload_len, &patch_offset, &patch_ok);
        } else {
          (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        }
        break;
      }
      case 10: /* character */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        break;
      case 11: /* single-float */
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        break;
      case 12: /* double-float */
      case 13: /* int64 */
      case 14: /* uint64 */
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        break;
      case 15: { /* bignum */
        uint32_t digits = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        for (uint32_t d = 0; patch_ok && d < digits; d++) {
          (void)wasm_const_pool_read_u32(bytes, payload_len, &patch_offset, &patch_ok);
        }
        break;
      }
      case 1: /* symbol */
      case 4: { /* function */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, name_len, &patch_ok);
        uint32_t pkg_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, pkg_len, &patch_ok);
        break;
      }
      case 2: { /* string */
        uint32_t len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, len, &patch_ok);
        break;
      }
      case 3: /* vector */
      case 5: { /* function-vector */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok) {
          return lisp_nil;
        }
        LispObj vec = pool_data[i];
        if (fulltag_of(vec) != fulltag_misc) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
          if (!patch_ok || idx >= count) {
            return lisp_nil;
          }
          vec_data[j] = pool_data[idx];
        }
        break;
      }
      case 16: /* entry-function */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        break;
      case 9: { /* gvector */
        (void)wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok); /* raw_subtag */
        uint32_t vcount = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok) {
          return lisp_nil;
        }
        LispObj vec = pool_data[i];
        if (fulltag_of(vec) != fulltag_misc) {
          return lisp_nil;
        }
        LispObj *vec_data = (LispObj *)((BytePtr)vec + misc_data_offset);
        for (uint32_t j = 0; j < vcount; j++) {
          uint32_t idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
          if (!patch_ok || idx >= count) {
            return lisp_nil;
          }
          vec_data[j] = pool_data[idx];
        }
        break;
      }
      case 7: { /* package */
        uint32_t name_len = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        (void)wasm_const_pool_read_bytes(bytes, payload_len, &patch_offset, name_len, &patch_ok);
        break;
      }
      case 8: { /* cons */
        uint32_t car_idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        uint32_t cdr_idx = wasm_const_pool_read_nat(bytes, payload_len, &patch_offset, patch_version, &patch_ok);
        if (!patch_ok || car_idx >= count || cdr_idx >= count) {
          return lisp_nil;
        }
        LispObj cell = pool_data[i];
        if (fulltag_of(cell) != fulltag_cons) {
          return lisp_nil;
        }
        cons *raw = (cons *)ptr_from_lispobj(untag(cell));
        raw->car = pool_data[car_idx];
        raw->cdr = pool_data[cdr_idx];
        break;
      }
      default:
        return lisp_nil;
    }
    if (!patch_ok) {
      return lisp_nil;
    }
  }

  LispObj table = wasm_const_pool_table_ensure(tcr, entry_index);
  if (table == lisp_nil) {
    return lisp_nil;
  }
  LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
  table_data[entry_index] = pool;
  return pool;
}

__attribute__((used, visibility("default"), export_name("wasm_const_pool_ref")))
LispObj
wasm_const_pool_ref(uint32_t entry_index, uint32_t const_index)
{
  int requested = 0;
  for (;;) {
    LispObj table = nrs_WASM_CONST_POOLS.vcell;
    if (table == lisp_nil ||
        fulltag_of(table) != fulltag_misc ||
        header_subtag(header_of(table)) != subtag_simple_vector) {
      if (!requested && (wasm_host_install_const_pool(entry_index) > 0)) {
        requested = 1;
        continue;
      }
      return lisp_nil;
    }
    uint32_t count = (uint32_t)header_element_count(header_of(table));
    if (entry_index >= count) {
      if (!requested && (wasm_host_install_const_pool(entry_index) > 0)) {
        requested = 1;
        continue;
      }
      return lisp_nil;
    }
    LispObj *table_data = (LispObj *)((BytePtr)table + misc_data_offset);
    LispObj pool = table_data[entry_index];
    if (pool == lisp_nil ||
        fulltag_of(pool) != fulltag_misc ||
        header_subtag(header_of(pool)) != subtag_simple_vector) {
      if (!requested && (wasm_host_install_const_pool(entry_index) > 0)) {
        requested = 1;
        continue;
      }
      return lisp_nil;
    }
    uint32_t pool_count = (uint32_t)header_element_count(header_of(pool));
    if (const_index >= pool_count) {
      return lisp_nil;
    }
    LispObj *pool_data = (LispObj *)((BytePtr)pool + misc_data_offset);
    return pool_data[const_index];
  }
}

__attribute__((used, visibility("default"), export_name("wasm_get_lisp_nil")))
LispObj
wasm_get_lisp_nil(void)
{
  extern LispObj lisp_nil;
  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_get_compiled_module_registry")))
LispObj
wasm_get_compiled_module_registry(void)
{
  extern LispObj lisp_nil;
  LispObj reg = nrs_WASM_COMPILED_MODULES.vcell;
  return reg ? reg : lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_all_packages_raw")))
LispObj
wasm_debug_all_packages_raw(void)
{
  return nrs_ALL_PACKAGES.vcell;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_cons_car_raw")))
LispObj
wasm_debug_cons_car_raw(LispObj obj)
{
  extern LispObj lisp_nil;
  if ((obj & fulltagmask) != fulltag_cons) {
    return lisp_nil;
  }
  cons *cell = (cons *)ptr_from_lispobj(untag(obj));
  return cell->car;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_cons_cdr_raw")))
LispObj
wasm_debug_cons_cdr_raw(LispObj obj)
{
  extern LispObj lisp_nil;
  if ((obj & fulltagmask) != fulltag_cons) {
    return lisp_nil;
  }
  cons *cell = (cons *)ptr_from_lispobj(untag(obj));
  return cell->cdr;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_package_names_raw")))
LispObj
wasm_debug_package_names_raw(LispObj pkg_obj)
{
  extern LispObj lisp_nil;
  if ((pkg_obj & fulltagmask) != fulltag_misc) {
    return lisp_nil;
  }
  LispObj header = header_of(pkg_obj);
  if (header_subtag(header) != subtag_package) {
    return lisp_nil;
  }
  package *pkg = (package *)ptr_from_lispobj(untag(pkg_obj));
  return pkg->names;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_package_common_lisp_raw")))
LispObj
wasm_debug_find_package_common_lisp_raw(void)
{
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  return wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_symbol_identity_raw")))
LispObj
wasm_debug_find_symbol_identity_raw(void)
{
  static const uint8_t id_name[] = {
    'I', 'D', 'E', 'N', 'T', 'I', 'T', 'Y'
  };
  return wasm_find_symbol_named_bytes(id_name, (uint32_t)sizeof(id_name), (LispObj)0);
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_symbol_toplevel_raw")))
LispObj
wasm_debug_find_symbol_toplevel_raw(void)
{
  static const uint8_t top_name[] = {
    'T', 'O', 'P', 'L', 'E', 'V', 'E', 'L'
  };
  return wasm_find_symbol_named_bytes(top_name, (uint32_t)sizeof(top_name), (LispObj)0);
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_symbol_percent_set_toplevel_raw")))
LispObj
wasm_debug_find_symbol_percent_set_toplevel_raw(void)
{
  static const uint8_t set_top_name[] = {
    '%', 'S', 'E', 'T', '-', 'T', 'O', 'P', 'L', 'E', 'V', 'E', 'L'
  };
  return wasm_find_symbol_named_bytes(set_top_name, (uint32_t)sizeof(set_top_name), (LispObj)0);
}

__attribute__((used, visibility("default"), export_name("wasm_debug_get_nrs_toplfunc_raw")))
LispObj
wasm_debug_get_nrs_toplfunc_raw(void)
{
  extern LispObj lisp_nil;
  LispObj fn = nrs_TOPLFUNC.vcell;
  return fn ? fn : lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_function_entry_index")))
int32_t
wasm_debug_function_entry_index(LispObj fn)
{
  if ((fn & fulltagmask) != fulltag_misc) {
    return -1;
  }
  LispObj header = deref(fn, 0);
  if (header_subtag(header) != subtag_function) {
    return -1;
  }
  LispObj entry = deref(fn, 1);
  if ((entry & fixnummask) != tag_fixnum) {
    return -1;
  }
  return (int32_t)unbox_fixnum(entry);
}

__attribute__((used, visibility("default"), export_name("wasm_debug_misc_subtag")))
int32_t
wasm_debug_misc_subtag(LispObj obj)
{
  if ((obj & fulltagmask) != fulltag_misc) {
    return -1;
  }
  LispObj header = deref(obj, 0);
  return (int32_t)header_subtag(header);
}

__attribute__((used, visibility("default"), export_name("wasm_debug_header_element_count")))
int32_t
wasm_debug_header_element_count(LispObj obj)
{
  if ((obj & fulltagmask) != fulltag_misc) {
    return -1;
  }
  return (int32_t)header_element_count(header_of(obj));
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_symbol_boundp_pkgtable_raw")))
LispObj
wasm_debug_find_symbol_boundp_pkgtable_raw(void)
{
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  static const uint8_t boundp_name[] = {
    'B', 'O', 'U', 'N', 'D', 'P'
  };
  LispObj pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
  if (pkg == lisp_nil) {
    return (LispObj)0;
  }
  return wasm_find_symbol_in_package_tables_bytes(pkg, boundp_name, (uint32_t)sizeof(boundp_name));
}

__attribute__((used, visibility("default"), export_name("wasm_debug_find_symbol_boundp_scan_raw")))
LispObj
wasm_debug_find_symbol_boundp_scan_raw(void)
{
  static const uint8_t cl_pkg_name[] = {
    'C', 'O', 'M', 'M', 'O', 'N', '-', 'L', 'I', 'S', 'P'
  };
  static const uint8_t boundp_name[] = {
    'B', 'O', 'U', 'N', 'D', 'P'
  };
  LispObj pkg = wasm_find_package_named_bytes(cl_pkg_name, (uint32_t)sizeof(cl_pkg_name));
  if (pkg == lisp_nil) {
    pkg = (LispObj)0;
  }
  area *a = ((area *)ptr_from_lispobj(lisp_global(ALL_AREAS)))->succ;
  while (a->code != AREA_VOID) {
    area_code code = a->code;
    if ((code == AREA_STATIC) ||
        (code == AREA_DYNAMIC) ||
        (code == AREA_MANAGED_STATIC) ||
        (code == AREA_READONLY) ||
        (code == AREA_WATCHED) ||
        (code == AREA_STATIC_CONS)) {
      LispObj sym = wasm_find_symbol_in_range_bytes((LispObj *)a->low,
                                                    (LispObj *)a->active,
                                                    boundp_name,
                                                    (uint32_t)sizeof(boundp_name),
                                                    pkg);
      if (sym) {
        return sym;
      }
    }
    a = a->succ;
  }
  return (LispObj)0;
}

__attribute__((used, visibility("default"), export_name("wasm_debug_copy_symbol_name")))
uint32_t
wasm_debug_copy_symbol_name(LispObj sym, uint32_t out_ptr, uint32_t out_len)
{
  if ((sym & fulltagmask) != fulltag_misc) {
    return 0;
  }
  LispObj sym_header = deref(sym, 0);
  if (header_subtag(sym_header) != subtag_symbol) {
    return 0;
  }

  lispsymbol *rawsym = (lispsymbol *)ptr_from_lispobj(untag(sym));
  LispObj pname = rawsym->pname;
  LispObj pname_header = header_of(pname);
  if (header_subtag(pname_header) != subtag_simple_base_string) {
    return 0;
  }

  uint32_t len = (uint32_t)header_element_count(pname_header);
  if (out_ptr == 0 || out_len == 0) {
    return len;
  }

  BytePtr dst = (BytePtr)(uintptr_t)out_ptr;
  uint32_t copy_len = (len < out_len) ? len : out_len;
  uint32_t *src = (uint32_t *)ptr_from_lispobj(pname + misc_data_offset);
  for (uint32_t i = 0; i < copy_len; i++) {
    dst[i] = (uint8_t)src[i];
  }
  return len;
}

__attribute__((used, visibility("default"), export_name("wasm_reset_root_image_runtime_state")))
int32_t
wasm_reset_root_image_runtime_state(void)
{
  extern LispObj lisp_nil;

  wasm_reset_gc_root_policy();
  wasm_clear_entry_gc_root_policy_modes();
  nrs_WASM_COMPILED_MODULES.vcell = lisp_nil;
  nrs_WASM_CONST_POOLS.vcell = lisp_nil;

  TCR *tcr = wasm_get_current_tcr();
  if (tcr != NULL) {
    LispObj *slot = wasm_toplevel_slot(tcr);
    if (slot != NULL) {
      /*
       * Clear any stale per-TCR toplevel slot from previous host runs.
       * Keep nrs_TOPLFUNC intact so the freshly loaded image can seed
       * start_lisp on the next entry.
       */
      *slot = lisp_nil;
      if (tcr->vs_area != NULL) {
        tcr->vs_area->active = (BytePtr)slot;
      }
      tcr->save_vsp = slot;
      tcr->wasm_gprs[vsp] = (LispObj)slot;
    }
  }

  return 0;
}

#endif /* WASM32 */
