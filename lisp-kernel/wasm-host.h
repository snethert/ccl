/*
 * WASM32 host ABI (kernel_request) declarations and helpers.
 *
 * This is the guest-side (kernel/runtime) view of the JS microkernel imports.
 * See: doc/wasm/kernel-request-abi.md
 */

#ifndef __ccl_wasm_host_h__
#define __ccl_wasm_host_h__

#ifdef WASM32

#include <stdint.h>

/* Status codes returned by kernel_poll/kernel_wait. */
#define KERNEL_STATUS_PENDING 0u
#define KERNEL_STATUS_DONE 1u
#define KERNEL_STATUS_ERROR 2u

/* Opcode registry (initial). */
#define KERNEL_OP_CAPS 0x00000000u
#define KERNEL_OP_LOG 0x00000001u
#define KERNEL_OP_STREAM_WRITE 0x00000002u
#define KERNEL_OP_STREAM_READ 0x00000003u
#define KERNEL_OP_TIME_NOW 0x00000004u
#define KERNEL_OP_STREAM_OPEN 0x00000005u
#define KERNEL_OP_STREAM_CLOSE 0x00000006u
#define KERNEL_OP_COMPILED_MODULES_REFRESH 0x00000007u
#define KERNEL_OP_FS_PROBE 0x00000008u
#define KERNEL_OP_FS_TRUENAME 0x00000009u
#define KERNEL_OP_FS_DIRECTORY 0x0000000au
#define KERNEL_OP_FS_FILE_WRITE_DATE 0x0000000bu
#define KERNEL_OP_FS_RENAME 0x0000000cu
#define KERNEL_OP_FS_DELETE 0x0000000du
#define KERNEL_OP_FS_ENSURE_DIRS 0x0000000eu
#define KERNEL_OP_FS_DELETE_EMPTY_DIR 0x0000000fu
#define KERNEL_OP_FS_DELETE_TREE 0x00000010u
#define KERNEL_OP_STREAM_SEEK 0x00000011u
#define KERNEL_OP_STREAM_TRUNCATE 0x00000012u
#define KERNEL_OP_UI_POLL 0x00000020u
#define KERNEL_OP_UI_RENDER 0x00000021u
#define KERNEL_OP_UI_MEASURE_TEXT 0x00000022u
#define KERNEL_OP_RUNTIME_EVENT 0x00000023u

/* Stream kind registry (KERNEL_OP_STREAM_OPEN.kind). */
#define KERNEL_STREAM_KIND_PIPE 0u
#define KERNEL_STREAM_KIND_NAMED_RO 1u
#define KERNEL_STREAM_KIND_FILE 2u

/* File mode flags (STREAM_OPEN file kind). */
#define WASM_FILE_MODE_READ 0x1u
#define WASM_FILE_MODE_WRITE 0x2u
#define WASM_FILE_MODE_CREATE 0x4u
#define WASM_FILE_MODE_TRUNCATE 0x8u
#define WASM_FILE_MODE_APPEND 0x10u

/*
 * Host ABI note (copy-based responses, MVP).
 *
 * Response payload bytes are retrieved by calling the imported functions:
 *   - kernel_response_size(request_id)
 *   - kernel_copy_response(request_id, dst_ptr, dst_len)
 *   - kernel_drop_request(request_id)
 *
 * The microkernel owns response storage until kernel_drop_request is called.
 * After copying, the guest owns the bytes in its linear memory.
 *
 * TODO(zero-copy): Provide optional ABI extensions that avoid the copy by
 * placing response bytes directly in guest linear memory (caller-provided
 * output buffers, or a microkernel-managed arena/ring buffer). Any zero-copy
 * form must define explicit lifetime/invalidation rules and must remain
 * optional; the copy-based ABI is the required baseline.
 */

/* Import module name is "ccl" (see doc/wasm/kernel-request-abi.md). */
__attribute__((import_module("ccl"), import_name("kernel_request")))
uint32_t kernel_request(uint32_t opcode, const void *payloadPtr, uint32_t payloadLen);

__attribute__((import_module("ccl"), import_name("kernel_poll")))
uint32_t kernel_poll(uint32_t requestId);

__attribute__((import_module("ccl"), import_name("kernel_result")))
int32_t kernel_result(uint32_t requestId);

__attribute__((import_module("ccl"), import_name("kernel_response_size")))
uint32_t kernel_response_size(uint32_t requestId);

__attribute__((import_module("ccl"), import_name("kernel_copy_response")))
uint32_t kernel_copy_response(uint32_t requestId, void *dstPtr, uint32_t dstLen);

__attribute__((import_module("ccl"), import_name("kernel_drop_request")))
void kernel_drop_request(uint32_t requestId);

/* Stage-2 building blocks: manual request lifecycle. */
int32_t wasm_kernel_request_begin(uint32_t opcode,
                                  const void *payload,
                                  uint32_t payload_len,
                                  uint32_t *out_request_id);

uint32_t wasm_kernel_request_status(uint32_t request_id);
int32_t wasm_kernel_request_get_result(uint32_t request_id);
uint32_t wasm_kernel_request_response_size_u32(uint32_t request_id);

int32_t wasm_kernel_request_copy_response(uint32_t request_id,
                                         void *out_buf,
                                         uint32_t out_cap,
                                         uint32_t *out_len);

void wasm_kernel_request_drop(uint32_t request_id);

/* Synchronous helper used by the current bring-up (Stage 1). */
int32_t wasm_kernel_request_copy(uint32_t opcode,
                                 const void *payload,
                                 uint32_t payload_len,
                                 void *out_buf,
                                 uint32_t out_cap,
                                 uint32_t *out_len);

/* Convenience wrappers for common MVP ops. */
int32_t wasm_kernel_caps(uint32_t *out_abi_version,
                         uint32_t *out_capability_bits,
                         uint32_t *out_max_response_bytes);

int32_t wasm_kernel_stream_write(uint32_t sid_or_fd, const void *bytes, uint32_t len);

int32_t wasm_kernel_stream_read(uint32_t sid_or_fd, void *buf, uint32_t cap, uint32_t *out_nread);

int32_t wasm_kernel_stream_open(uint32_t kind, const void *arg, uint32_t arg_len, uint32_t *out_sid);
int32_t wasm_kernel_stream_close(uint32_t sid);
int32_t wasm_kernel_stream_seek(uint32_t sid, int64_t offset, uint32_t whence, uint64_t *out_pos);
int32_t wasm_kernel_stream_truncate(uint32_t sid, uint64_t length);
int32_t wasm_kernel_compiled_modules_refresh(uint32_t registry, uint32_t nil);

/* Named byte sources (read-only). */
int32_t wasm_kernel_stream_open_named(const char *name,
                                      uint32_t name_len,
                                      uint32_t *out_sid,
                                      uint64_t *out_size);

int32_t wasm_kernel_time_now(uint64_t *out_unix_ms);

/* UI bridge helpers (Stage 2+ integration). */
struct wasm_ui_text_metrics {
  double width;
  double height;
  double ascent;
  double descent;
};

int32_t wasm_kernel_ui_poll(uint32_t max_events,
                            uint32_t max_bytes,
                            uint32_t flags,
                            void *out_buf,
                            uint32_t out_cap,
                            uint32_t *out_len,
                            uint32_t *out_count);

int32_t wasm_kernel_ui_render(const void *payload, uint32_t payload_len);

int32_t wasm_kernel_ui_measure_text(const char *font,
                                    uint32_t font_len,
                                    const char *text,
                                    uint32_t text_len,
                                    struct wasm_ui_text_metrics *out_metrics);

int32_t wasm_kernel_runtime_event(const void *payload, uint32_t payload_len);

/* Minimal FFI smoke helper (imported by compiled modules). */
int32_t wasm_ffi_test_add(int32_t a, int32_t b);

#endif /* WASM32 */

#endif /* __ccl_wasm_host_h__ */
