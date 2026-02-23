/*
 * WASM32 kernel_request smoke exports.
 *
 * These exports exist to validate the kernel_request ABI wiring early, without
 * bringing up start_lisp.
 */

#ifdef WASM32

#include "wasm-host.h"
#include "lisp.h"
#include "lisp_globals.h"

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/stat.h>
#include <unistd.h>

extern int lisp_open(char *path, int flags, mode_t mode);
extern ssize_t lisp_read(int fd, void *buf, size_t count);
extern ssize_t lisp_write(int fd, void *buf, size_t count);
extern int32_t lisp_lseek(int fd, int32_t offset, int whence);
extern int lisp_close(int fd);
extern int lisp_ftruncate(int fd, int32_t length);
extern int lisp_stat(char *path, void *buf);

__attribute__((used, visibility("default"), export_name("wasm_kernel_caps_abi_version")))
uint32_t
wasm_kernel_caps_abi_version(void)
{
  uint32_t abi = 0;
  int32_t r = wasm_kernel_caps(&abi, NULL, NULL);
  if (r < 0) {
    return 0;
  }
  return abi;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_write")))
int32_t
wasm_kernel_request_smoke_write(uint32_t sid_or_fd)
{
  static const char msg[] = "kernel_request smoke write\n";
  return wasm_kernel_stream_write(sid_or_fd, msg, (uint32_t)(sizeof(msg) - 1));
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_time_now_ms")))
uint64_t
wasm_kernel_request_smoke_time_now_ms(void)
{
  uint64_t ms = 0;
  int32_t r = wasm_kernel_time_now(&ms);
  if (r < 0) {
    return 0;
  }
  return ms;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_begin_stdin_read")))
uint32_t
wasm_kernel_request_smoke_begin_stdin_read(uint32_t max_bytes)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t max_bytes;
  } p;

  uint32_t request_id = 0;

  p.sid_or_fd = 0;
  p.max_bytes = max_bytes;

  int32_t r = wasm_kernel_request_begin(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), &request_id);
  if (r < 0) {
    return 0;
  }
  return request_id;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_poll")))
uint32_t
wasm_kernel_request_smoke_poll(uint32_t request_id)
{
  return wasm_kernel_request_status(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_result")))
int32_t
wasm_kernel_request_smoke_result(uint32_t request_id)
{
  return wasm_kernel_request_get_result(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_copy_response")))
int32_t
wasm_kernel_request_smoke_copy_response(uint32_t request_id, uint32_t dst_ptr, uint32_t dst_cap)
{
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy_response(request_id, (void *)(uintptr_t)dst_ptr, dst_cap, &n);
  if (r < 0) {
    return r;
  }
  return (int32_t)n;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_drop")))
void
wasm_kernel_request_smoke_drop(uint32_t request_id)
{
  wasm_kernel_request_drop(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_named_roundtrip")))
int32_t
wasm_kernel_request_smoke_named_roundtrip(void)
{
  static const char name[] = "named.bin";
  static const uint8_t expected[] = {0x00, 0x11, 0x22, 0x33, 0xaa, 0xbb, 0xcc, 0xdd};
  uint8_t buf[sizeof(expected)];
  struct stat st;

  int fd = lisp_open((char *)name, O_RDONLY, 0);
  if (fd < 0) {
    return -errno;
  }

  ssize_t n = lisp_read(fd, buf, sizeof(buf));
  if (n < 0) {
    int e = errno;
    (void)lisp_close(fd);
    return -e;
  }
  if ((size_t)n != sizeof(expected)) {
    (void)lisp_close(fd);
    return -1;
  }
  for (size_t i = 0; i < sizeof(expected); i++) {
    if (buf[i] != expected[i]) {
      (void)lisp_close(fd);
      return -1;
    }
  }

  if (lisp_close(fd) < 0) {
    return -errno;
  }

  if (lisp_stat((char *)name, &st) < 0) {
    return -errno;
  }
  if ((uint64_t)st.st_size != (uint64_t)sizeof(expected)) {
    return -1;
  }

  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_pipe_roundtrip")))
int32_t
wasm_kernel_request_smoke_pipe_roundtrip(void)
{
  static const uint8_t msg[] = {0x00, 0x01, 0x02, 0x7f, 0x80, 0xff};
  uint8_t buf[16];
  uint32_t nread = 0;

  uint32_t sid = 0;
  int32_t r = wasm_kernel_stream_open(KERNEL_STREAM_KIND_PIPE, NULL, 0, &sid);
  if (r < 0) {
    return r;
  }

  r = wasm_kernel_stream_write(sid, msg, (uint32_t)sizeof(msg));
  if (r != (int32_t)sizeof(msg)) {
    (void)wasm_kernel_stream_close(sid);
    return (r < 0) ? r : -1;
  }

  r = wasm_kernel_stream_read(sid, buf, (uint32_t)sizeof(buf), &nread);
  if (r != (int32_t)sizeof(msg) || nread != (uint32_t)sizeof(msg)) {
    (void)wasm_kernel_stream_close(sid);
    return (r < 0) ? r : -1;
  }
  for (size_t i = 0; i < sizeof(msg); i++) {
    if (buf[i] != msg[i]) {
      (void)wasm_kernel_stream_close(sid);
      return -1;
    }
  }

  r = wasm_kernel_stream_close(sid);
  if (r < 0) {
    return r;
  }

  r = wasm_kernel_stream_read(sid, buf, (uint32_t)sizeof(buf), &nread);
  if (r != -EBADF) {
    return (r < 0) ? r : -1;
  }
  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_file_seek_truncate")))
int32_t
wasm_kernel_request_smoke_file_seek_truncate(void)
{
  static char name[] = "seek-truncate-c.bin";
  static const uint8_t data[] = {0x41, 0x42, 0x43, 0x44, 0x45};
  uint8_t buf[sizeof(data)];

  int fd = lisp_open(name, O_RDWR | O_CREAT | O_TRUNC, 0);
  if (fd < 0) {
    return -errno;
  }

  ssize_t nwritten = lisp_write(fd, (void *)data, sizeof(data));
  if (nwritten != (ssize_t)sizeof(data)) {
    int e = (nwritten < 0) ? errno : EIO;
    (void)lisp_close(fd);
    return -e;
  }

  if (lisp_lseek(fd, 0, SEEK_SET) < 0) {
    int e = errno;
    (void)lisp_close(fd);
    return -e;
  }

  ssize_t nread = lisp_read(fd, buf, sizeof(buf));
  if (nread != (ssize_t)sizeof(data)) {
    int e = (nread < 0) ? errno : EIO;
    (void)lisp_close(fd);
    return -e;
  }
  for (size_t i = 0; i < sizeof(data); i++) {
    if (buf[i] != data[i]) {
      (void)lisp_close(fd);
      return -EIO;
    }
  }

  if (lisp_ftruncate(fd, 3) < 0) {
    int e = errno;
    (void)lisp_close(fd);
    return -e;
  }

  int64_t endpos = lisp_lseek(fd, 0, SEEK_END);
  if (endpos < 0) {
    int e = errno;
    (void)lisp_close(fd);
    return -e;
  }
  if (endpos != 3) {
    (void)lisp_close(fd);
    return -EIO;
  }

  if (lisp_lseek(fd, 0, SEEK_SET) < 0) {
    int e = errno;
    (void)lisp_close(fd);
    return -e;
  }

  nread = lisp_read(fd, buf, sizeof(buf));
  if (nread != 3) {
    int e = (nread < 0) ? errno : EIO;
    (void)lisp_close(fd);
    return -e;
  }
  for (size_t i = 0; i < 3; i++) {
    if (buf[i] != data[i]) {
      (void)lisp_close(fd);
      return -EIO;
    }
  }

  if (lisp_close(fd) < 0) {
    return -errno;
  }
  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_ui_persist_label_save")))
int32_t
wasm_ui_persist_label_save(uint32_t value)
{
  static char path[] = "/ui/wasm-ui-state.bin";
  uint8_t byte = (uint8_t)(value & 0xffu);

  int fd = lisp_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
  if (fd < 0) {
    return -errno;
  }

  ssize_t nwritten = lisp_write(fd, &byte, 1);
  if (nwritten != 1) {
    int e = (nwritten < 0) ? errno : EIO;
    (void)lisp_close(fd);
    return -e;
  }

  if (lisp_close(fd) < 0) {
    return -errno;
  }

  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_ui_persist_label_load")))
int32_t
wasm_ui_persist_label_load(void)
{
  static char path[] = "/ui/wasm-ui-state.bin";
  uint8_t byte = 0;

  int fd = lisp_open(path, O_RDONLY, 0);
  if (fd < 0) {
    return -errno;
  }

  ssize_t nread = lisp_read(fd, &byte, 1);
  if (nread != 1) {
    int e = (nread < 0) ? errno : ENOENT;
    (void)lisp_close(fd);
    return -e;
  }

  if (lisp_close(fd) < 0) {
    return -errno;
  }

  return (int32_t)byte;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_compiled_modules_refresh")))
int32_t
wasm_kernel_request_smoke_compiled_modules_refresh(void)
{
  LispObj registry = nrs_WASM_COMPILED_MODULES.vcell;
  if (registry == 0 || registry == lisp_nil) {
    return 0;
  }
  return wasm_kernel_compiled_modules_refresh((uint32_t)registry, (uint32_t)lisp_nil);
}

#endif /* WASM32 */
