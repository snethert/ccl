/*
 * WASM32 host ABI (kernel_request) helpers.
 *
 * These wrappers provide a synchronous "Stage 1" path for calling into the JS
 * microkernel while the full yield/resume model is still being designed.
 *
 * See: doc/wasm/kernel-request-abi.md
 */

#ifdef WASM32

#include "wasm-host.h"

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint32_t request_id;
  uint32_t opcode;
} wasm_kernel_trace_request;

#define WASM_KERNEL_TRACE_REQUEST_MAX 128u
#define WASM_KERNEL_TRACE_DUMP_MAX 128u

static wasm_kernel_trace_request wasm_kernel_trace_requests[WASM_KERNEL_TRACE_REQUEST_MAX];
static uint32_t wasm_kernel_trace_request_count = 0u;
static uint32_t wasm_kernel_trace_next_slot = 0u;

static const char *
wasm_kernel_trace_opcode_name(uint32_t opcode)
{
  switch (opcode) {
    case KERNEL_OP_CAPS: return "KERNEL_OP_CAPS";
    case KERNEL_OP_LOG: return "KERNEL_OP_LOG";
    case KERNEL_OP_STREAM_WRITE: return "KERNEL_OP_STREAM_WRITE";
    case KERNEL_OP_STREAM_READ: return "KERNEL_OP_STREAM_READ";
    case KERNEL_OP_TIME_NOW: return "KERNEL_OP_TIME_NOW";
    case KERNEL_OP_STREAM_OPEN: return "KERNEL_OP_STREAM_OPEN";
    case KERNEL_OP_STREAM_CLOSE: return "KERNEL_OP_STREAM_CLOSE";
    case KERNEL_OP_COMPILED_MODULES_REFRESH: return "KERNEL_OP_COMPILED_MODULES_REFRESH";
    case KERNEL_OP_FS_PROBE: return "KERNEL_OP_FS_PROBE";
    case KERNEL_OP_FS_TRUENAME: return "KERNEL_OP_FS_TRUENAME";
    case KERNEL_OP_FS_DIRECTORY: return "KERNEL_OP_FS_DIRECTORY";
    case KERNEL_OP_FS_FILE_WRITE_DATE: return "KERNEL_OP_FS_FILE_WRITE_DATE";
    case KERNEL_OP_FS_RENAME: return "KERNEL_OP_FS_RENAME";
    case KERNEL_OP_FS_DELETE: return "KERNEL_OP_FS_DELETE";
    case KERNEL_OP_FS_ENSURE_DIRS: return "KERNEL_OP_FS_ENSURE_DIRS";
    case KERNEL_OP_FS_DELETE_EMPTY_DIR: return "KERNEL_OP_FS_DELETE_EMPTY_DIR";
    case KERNEL_OP_FS_DELETE_TREE: return "KERNEL_OP_FS_DELETE_TREE";
    case KERNEL_OP_STREAM_SEEK: return "KERNEL_OP_STREAM_SEEK";
    case KERNEL_OP_STREAM_TRUNCATE: return "KERNEL_OP_STREAM_TRUNCATE";
    case KERNEL_OP_UI_POLL: return "KERNEL_OP_UI_POLL";
    case KERNEL_OP_UI_RENDER: return "KERNEL_OP_UI_RENDER";
    case KERNEL_OP_UI_MEASURE_TEXT: return "KERNEL_OP_UI_MEASURE_TEXT";
    case KERNEL_OP_RUNTIME_EVENT: return "KERNEL_OP_RUNTIME_EVENT";
    case KERNEL_OP_RUNTIME_COMMAND_POLL: return "KERNEL_OP_RUNTIME_COMMAND_POLL";
    default: return "KERNEL_OP_UNKNOWN";
  }
}

static void
wasm_kernel_trace_log(const char *fmt, ...)
{
  char line[256];
  va_list args;
  va_start(args, fmt);
  int n = vsnprintf(line, sizeof(line), fmt, args);
  va_end(args);
  if (n <= 0) {
    return;
  }
  unsigned out_len = (unsigned)((n < (int)sizeof(line)) ? n : (int)(sizeof(line) - 1));
  wasm_host_log(line, out_len);
}

static void
wasm_kernel_trace_dump_bytes(const char *phase,
                             uint32_t opcode,
                             uint32_t request_id,
                             const void *buf,
                             uint32_t len)
{
  const uint8_t *p = (const uint8_t *)buf;
  uint32_t shown = len;
  if (shown > WASM_KERNEL_TRACE_DUMP_MAX) {
    shown = WASM_KERNEL_TRACE_DUMP_MAX;
  }
  if (shown == 0u || p == NULL) {
    wasm_kernel_trace_log(
      "WASM kernel trace: %s op=0x%08x(%s) req=%u payload=<empty>\n",
      phase ? phase : "?",
      (unsigned)opcode,
      wasm_kernel_trace_opcode_name(opcode),
      (unsigned)request_id);
    return;
  }

  for (uint32_t off = 0; off < shown; off += 16u) {
    char hexbuf[16u * 3u + 1u];
    uint32_t line_count = shown - off;
    if (line_count > 16u) {
      line_count = 16u;
    }
    uint32_t out = 0u;
    for (uint32_t i = 0; i < line_count; i++) {
      static const char hexdigits[] = "0123456789abcdef";
      uint8_t b = p[off + i];
      hexbuf[out++] = hexdigits[(b >> 4) & 0x0f];
      hexbuf[out++] = hexdigits[b & 0x0f];
      if (i + 1u < line_count) {
        hexbuf[out++] = ' ';
      }
    }
    hexbuf[out] = '\0';
    wasm_kernel_trace_log(
      "WASM kernel trace: %s op=0x%08x(%s) req=%u bytes[%u..%u]=%s\n",
      phase ? phase : "?",
      (unsigned)opcode,
      wasm_kernel_trace_opcode_name(opcode),
      (unsigned)request_id,
      (unsigned)off,
      (unsigned)(off + line_count),
      hexbuf);
  }
  if (shown < len) {
    wasm_kernel_trace_log(
      "WASM kernel trace: %s op=0x%08x(%s) req=%u payload_truncated shown=%u total=%u\n",
      phase ? phase : "?",
      (unsigned)opcode,
      wasm_kernel_trace_opcode_name(opcode),
      (unsigned)request_id,
      (unsigned)shown,
      (unsigned)len);
  }
}

static void
wasm_kernel_trace_record(uint32_t request_id, uint32_t opcode)
{
  if (request_id == 0u) {
    return;
  }
  uint32_t idx;
  if (wasm_kernel_trace_request_count < WASM_KERNEL_TRACE_REQUEST_MAX) {
    idx = wasm_kernel_trace_request_count++;
  } else {
    idx = wasm_kernel_trace_next_slot;
    wasm_kernel_trace_next_slot++;
    if (wasm_kernel_trace_next_slot >= WASM_KERNEL_TRACE_REQUEST_MAX) {
      wasm_kernel_trace_next_slot = 0u;
    }
  }
  wasm_kernel_trace_requests[idx].request_id = request_id;
  wasm_kernel_trace_requests[idx].opcode = opcode;
}

static int
wasm_kernel_trace_lookup(uint32_t request_id, uint32_t *out_opcode)
{
  if (request_id == 0u) {
    return 0;
  }
  for (uint32_t i = 0; i < wasm_kernel_trace_request_count; i++) {
    if (wasm_kernel_trace_requests[i].request_id == request_id) {
      if (out_opcode) {
        *out_opcode = wasm_kernel_trace_requests[i].opcode;
      }
      return 1;
    }
  }
  return 0;
}

static void
wasm_kernel_trace_forget(uint32_t request_id)
{
  if (request_id == 0u) {
    return;
  }
  for (uint32_t i = 0; i < wasm_kernel_trace_request_count; i++) {
    if (wasm_kernel_trace_requests[i].request_id == request_id) {
      wasm_kernel_trace_requests[i].request_id = 0u;
      wasm_kernel_trace_requests[i].opcode = 0u;
      return;
    }
  }
}

uint32_t
kernel_request(uint32_t opcode, const void *payloadPtr, uint32_t payloadLen)
{
  uint32_t request_id = wasm_host_import_kernel_request(opcode, payloadPtr, payloadLen);
  wasm_kernel_trace_record(request_id, opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: request op=0x%08x(%s) req=%u payload_ptr=0x%08x payload_len=%u\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)request_id,
    (unsigned)(uint32_t)(uintptr_t)payloadPtr,
    (unsigned)payloadLen);
  wasm_kernel_trace_dump_bytes("request-payload", opcode, request_id, payloadPtr, payloadLen);
  return request_id;
}

uint32_t
kernel_poll(uint32_t requestId)
{
  uint32_t status = wasm_host_import_kernel_poll(requestId);
  uint32_t opcode = 0u;
  (void)wasm_kernel_trace_lookup(requestId, &opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: poll op=0x%08x(%s) req=%u status=%u\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)requestId,
    (unsigned)status);
  return status;
}

int32_t
kernel_result(uint32_t requestId)
{
  int32_t result = wasm_host_import_kernel_result(requestId);
  uint32_t opcode = 0u;
  (void)wasm_kernel_trace_lookup(requestId, &opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: result op=0x%08x(%s) req=%u result=%d\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)requestId,
    (int)result);
  return result;
}

uint32_t
kernel_response_size(uint32_t requestId)
{
  uint32_t size = wasm_host_import_kernel_response_size(requestId);
  uint32_t opcode = 0u;
  (void)wasm_kernel_trace_lookup(requestId, &opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: response_size op=0x%08x(%s) req=%u size=%u\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)requestId,
    (unsigned)size);
  return size;
}

uint32_t
kernel_copy_response(uint32_t requestId, void *dstPtr, uint32_t dstLen)
{
  uint32_t copied = wasm_host_import_kernel_copy_response(requestId, dstPtr, dstLen);
  uint32_t opcode = 0u;
  (void)wasm_kernel_trace_lookup(requestId, &opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: copy_response op=0x%08x(%s) req=%u copied=%u dst_ptr=0x%08x dst_len=%u\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)requestId,
    (unsigned)copied,
    (unsigned)(uint32_t)(uintptr_t)dstPtr,
    (unsigned)dstLen);
  wasm_kernel_trace_dump_bytes("response-payload", opcode, requestId, dstPtr, copied);
  return copied;
}

void
kernel_drop_request(uint32_t requestId)
{
  uint32_t opcode = 0u;
  (void)wasm_kernel_trace_lookup(requestId, &opcode);
  wasm_kernel_trace_log(
    "WASM kernel trace: drop op=0x%08x(%s) req=%u\n",
    (unsigned)opcode,
    wasm_kernel_trace_opcode_name(opcode),
    (unsigned)requestId);
  wasm_kernel_trace_forget(requestId);
  wasm_host_import_kernel_drop_request(requestId);
}

int32_t
wasm_kernel_request_begin(uint32_t opcode,
                          const void *payload,
                          uint32_t payload_len,
                          uint32_t *out_request_id)
{
  if (out_request_id == NULL) {
    return -EINVAL;
  }
  uint32_t request_id = kernel_request(opcode, payload, payload_len);
  if (request_id == 0) {
    return -EINVAL;
  }
  *out_request_id = request_id;
  return 0;
}

uint32_t
wasm_kernel_request_status(uint32_t request_id)
{
  return kernel_poll(request_id);
}

int32_t
wasm_kernel_request_get_result(uint32_t request_id)
{
  return kernel_result(request_id);
}

uint32_t
wasm_kernel_request_response_size_u32(uint32_t request_id)
{
  return kernel_response_size(request_id);
}

int32_t
wasm_kernel_request_copy_response(uint32_t request_id,
                                  void *out_buf,
                                  uint32_t out_cap,
                                  uint32_t *out_len)
{
  if (out_len) {
    *out_len = 0;
  }

  uint32_t need = kernel_response_size(request_id);
  if (need == 0) {
    return 0;
  }
  if (need > out_cap) {
    return -E2BIG;
  }
  if (out_buf == NULL) {
    return -EINVAL;
  }

  uint32_t copied = kernel_copy_response(request_id, out_buf, out_cap);
  if (copied != need) {
    return -EINVAL;
  }
  if (out_len) {
    *out_len = copied;
  }
  return 0;
}

void
wasm_kernel_request_drop(uint32_t request_id)
{
  kernel_drop_request(request_id);
}

int32_t
wasm_kernel_request_copy(uint32_t opcode,
                         const void *payload,
                         uint32_t payload_len,
                         void *out_buf,
                         uint32_t out_cap,
                         uint32_t *out_len)
{
  uint32_t request_id;
  uint32_t status;
  int32_t result;
  uint32_t need;

  if (out_len) {
    *out_len = 0;
  }

  request_id = kernel_request(opcode, payload, payload_len);
  if (request_id == 0) {
    return -EINVAL;
  }

  status = kernel_poll(request_id);
  if (status == KERNEL_STATUS_PENDING) {
    /* Stage 2 will need an explicit yield/resume mechanism. For now, treat
     * pending as would-block and drop the request.
     */
    kernel_drop_request(request_id);
    return -EWOULDBLOCK;
  }

  result = kernel_result(request_id);

  /* ABI-level errors still provide an errno-style result; surface it. */
  if (status == KERNEL_STATUS_ERROR) {
    kernel_drop_request(request_id);
    return result ? result : -EINVAL;
  }

  /* Copy response payload if requested. */
  if (out_buf && out_cap) {
    need = kernel_response_size(request_id);
    if (need > out_cap) {
      kernel_drop_request(request_id);
      return -E2BIG;
    }
    if (need) {
      uint32_t copied = kernel_copy_response(request_id, out_buf, out_cap);
      if (copied != need) {
        kernel_drop_request(request_id);
        return -EINVAL;
      }
      if (out_len) {
        *out_len = copied;
      }
    }
  } else if (out_len) {
    *out_len = kernel_response_size(request_id);
  }

  kernel_drop_request(request_id);
  return result;
}

int32_t
wasm_kernel_caps(uint32_t *out_abi_version,
                 uint32_t *out_capability_bits,
                 uint32_t *out_max_response_bytes)
{
  struct caps {
    uint32_t abi_version;
    uint32_t capability_bits;
    uint32_t max_response_bytes;
    uint32_t reserved;
  } c;
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_CAPS, NULL, 0, &c, (uint32_t)sizeof(c), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(c)) {
    return -EINVAL;
  }
  if (out_abi_version) {
    *out_abi_version = c.abi_version;
  }
  if (out_capability_bits) {
    *out_capability_bits = c.capability_bits;
  }
  if (out_max_response_bytes) {
    *out_max_response_bytes = c.max_response_bytes;
  }
  return 0;
}

int32_t
wasm_kernel_stream_write(uint32_t sid_or_fd, const void *bytes, uint32_t len)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t flags;
    uint32_t data_ptr;
    uint32_t data_len;
  } p;

  p.sid_or_fd = sid_or_fd;
  p.flags = 0;
  p.data_ptr = (uint32_t)(uintptr_t)bytes;
  p.data_len = len;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_WRITE, &p, (uint32_t)sizeof(p), NULL, 0, NULL);
  return r;
}

int32_t
wasm_kernel_stream_read(uint32_t sid_or_fd, void *buf, uint32_t cap, uint32_t *out_nread)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t max_bytes;
  } p;
  uint32_t n = 0;

  if (out_nread) {
    *out_nread = 0;
  }

  p.sid_or_fd = sid_or_fd;
  p.max_bytes = cap;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), buf, cap, &n);
  if (r < 0) {
    return r;
  }
  if ((uint32_t)r != n) {
    return -EINVAL;
  }
  if (out_nread) {
    *out_nread = n;
  }
  return r;
}

int32_t
wasm_kernel_stream_open(uint32_t kind, const void *arg, uint32_t arg_len, uint32_t *out_sid)
{
  struct payload {
    uint32_t kind;
    uint32_t flags;
    uint32_t arg_ptr;
    uint32_t arg_len;
  } p;
  uint32_t n = 0;

  if (out_sid) {
    *out_sid = 0;
  }
  if (out_sid == NULL) {
    return -EINVAL;
  }

  p.kind = kind;
  p.flags = 0;
  p.arg_ptr = (arg_len != 0) ? (uint32_t)(uintptr_t)arg : 0;
  p.arg_len = arg_len;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_OPEN, &p, (uint32_t)sizeof(p), NULL, 0, &n);
  if (r < 0) {
    return r;
  }
  if (n != 0) {
    return -EINVAL;
  }
  if (r < 3) {
    return -EINVAL;
  }
  *out_sid = (uint32_t)r;
  return 0;
}

int32_t
wasm_kernel_stream_open_named(const char *name,
                              uint32_t name_len,
                              uint32_t *out_sid,
                              uint64_t *out_size)
{
  struct payload {
    uint32_t kind;
    uint32_t flags;
    uint32_t arg_ptr;
    uint32_t arg_len;
  } p;
  uint8_t resp[8];
  uint32_t n = 0;

  if (out_sid) {
    *out_sid = 0;
  }
  if (out_size) {
    *out_size = 0;
  }
  if (out_sid == NULL) {
    return -EINVAL;
  }

  p.kind = KERNEL_STREAM_KIND_NAMED_RO;
  p.flags = 0;
  p.arg_ptr = (name_len != 0) ? (uint32_t)(uintptr_t)name : 0;
  p.arg_len = name_len;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_OPEN, &p, (uint32_t)sizeof(p),
                                       resp, (uint32_t)sizeof(resp), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(resp)) {
    return -EINVAL;
  }
  if (r < 3) {
    return -EINVAL;
  }
  *out_sid = (uint32_t)r;
  if (out_size) {
    uint64_t size = 0;
    memmove(&size, resp, sizeof(size));
    *out_size = size;
  }
  return 0;
}

int32_t
wasm_kernel_stream_close(uint32_t sid)
{
  struct payload {
    uint32_t sid;
    uint32_t flags;
  } p;

  p.sid = sid;
  p.flags = 0;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_CLOSE, &p, (uint32_t)sizeof(p), NULL, 0, NULL);
  return r;
}

int32_t
wasm_kernel_stream_seek(uint32_t sid, int64_t offset, uint32_t whence, uint64_t *out_pos)
{
  struct payload {
    uint32_t sid;
    uint32_t whence;
    int64_t offset;
  } p;
  uint64_t pos = 0;
  uint32_t n = 0;

  if (out_pos) {
    *out_pos = 0;
  }

  p.sid = sid;
  p.whence = whence;
  p.offset = offset;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_SEEK, &p, (uint32_t)sizeof(p),
                                       &pos, (uint32_t)sizeof(pos), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(pos)) {
    return -EINVAL;
  }
  if (out_pos) {
    *out_pos = pos;
  }
  return 0;
}

int32_t
wasm_kernel_stream_truncate(uint32_t sid, uint64_t length)
{
  struct payload {
    uint32_t sid;
    uint32_t flags;
    uint64_t length;
  } p;

  p.sid = sid;
  p.flags = 0;
  p.length = length;

  return wasm_kernel_request_copy(KERNEL_OP_STREAM_TRUNCATE, &p, (uint32_t)sizeof(p), NULL, 0, NULL);
}

int32_t
wasm_kernel_compiled_modules_refresh(uint32_t registry, uint32_t nil)
{
  struct payload {
    uint32_t registry;
    uint32_t nil;
  } p;

  p.registry = registry;
  p.nil = nil;

  return wasm_kernel_request_copy(KERNEL_OP_COMPILED_MODULES_REFRESH, &p, (uint32_t)sizeof(p), NULL, 0, NULL);
}

int32_t
wasm_kernel_time_now(uint64_t *out_unix_ms)
{
  uint64_t ms = 0;
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_TIME_NOW, NULL, 0, &ms, (uint32_t)sizeof(ms), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(ms)) {
    return -EINVAL;
  }
  if (out_unix_ms) {
    /* WASM is little-endian; microkernel returns little-endian u64. */
    *out_unix_ms = ms;
  }
  return 0;
}

int32_t
wasm_kernel_ui_poll(uint32_t max_events,
                    uint32_t max_bytes,
                    uint32_t flags,
                    void *out_buf,
                    uint32_t out_cap,
                    uint32_t *out_len,
                    uint32_t *out_count)
{
  struct payload {
    uint32_t max_events;
    uint32_t max_bytes;
    uint32_t flags;
  } p;

  p.max_events = max_events;
  p.max_bytes = max_bytes;
  p.flags = flags;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_UI_POLL, &p, (uint32_t)sizeof(p), out_buf, out_cap, out_len);
  if (r < 0) {
    return r;
  }
  if (out_count) {
    *out_count = (uint32_t)r;
  }
  return r;
}

int32_t
wasm_kernel_ui_render(const void *payload, uint32_t payload_len)
{
  return wasm_kernel_request_copy(KERNEL_OP_UI_RENDER, payload, payload_len, NULL, 0, NULL);
}

int32_t
wasm_kernel_ui_measure_text(const char *font,
                            uint32_t font_len,
                            const char *text,
                            uint32_t text_len,
                            struct wasm_ui_text_metrics *out_metrics)
{
  struct payload {
    uint32_t font_ptr;
    uint32_t font_len;
    uint32_t text_ptr;
    uint32_t text_len;
  } p;

  p.font_ptr = (uint32_t)(uintptr_t)font;
  p.font_len = font_len;
  p.text_ptr = (uint32_t)(uintptr_t)text;
  p.text_len = text_len;

  struct wasm_ui_text_metrics metrics;
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_UI_MEASURE_TEXT, &p, (uint32_t)sizeof(p),
                                       &metrics, (uint32_t)sizeof(metrics), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(metrics)) {
    return -EINVAL;
  }
  if (out_metrics) {
    *out_metrics = metrics;
  }
  return 0;
}

int32_t
wasm_kernel_runtime_event(const void *payload, uint32_t payload_len)
{
  return wasm_kernel_request_copy(KERNEL_OP_RUNTIME_EVENT, payload, payload_len, NULL, 0, NULL);
}

int32_t
wasm_kernel_runtime_command_poll(uint32_t max_bytes,
                                 uint32_t flags,
                                 void *out_buf,
                                 uint32_t out_cap,
                                 uint32_t *out_len)
{
  struct payload {
    uint32_t max_bytes;
    uint32_t flags;
  } p;

  p.max_bytes = max_bytes;
  p.flags = flags;
  return wasm_kernel_request_copy(KERNEL_OP_RUNTIME_COMMAND_POLL,
                                  &p,
                                  (uint32_t)sizeof(p),
                                  out_buf,
                                  out_cap,
                                  out_len);
}

__attribute__((used, visibility("default"), export_name("wasm_ffi_test_add")))
int32_t
wasm_ffi_test_add(int32_t a, int32_t b)
{
  return a + b;
}

#endif /* WASM32 */
