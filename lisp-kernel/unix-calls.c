/*
 * Copyright 2008-2009 Clozure Associates
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* Provide wrappers around some standard C library functions that
   can't easily be called from CCL's FFI for some reason (or where
   we want to override/extend the function's default behavior.)
 
   Functions in this file should be referenced via the kernel
   imports table.

   Callers should generally expect standard C library error-handling
   conventions (e.g., return -1 or NULL and set errno on error.)
*/

#ifndef _LARGEFILE64_SOURCE
#define _LARGEFILE64_SOURCE
#endif
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <stdint.h>
#include <stdio.h>
#ifndef WASM32
#include <signal.h>
#endif
#include <fcntl.h>
#include <stdlib.h>
#ifdef WASM32
#include <string.h>
#endif

#ifdef WASM32
#include "wasm-host.h"
static const char *
wasm_normalize_named_path(const char *path, size_t *out_len)
{
  if (out_len) {
    *out_len = 0;
  }
  if (path == NULL) {
    return NULL;
  }
  size_t len = strlen(path);
  const char *p = path;
  while (len > 0 && *p == '/') {
    p++;
    len--;
  }
  if (out_len) {
    *out_len = len;
  }
  return p;
}
/* No WASI, no POSIX. These are placeholders for the FFI imports table.
 * The JS microkernel should provide real implementations later.
 */
ssize_t
lisp_read(int fd, void *buf, size_t count)
{
  if (fd < 0) {
    (void)buf;
    (void)count;
    errno = EBADF;
    return -1;
  }

  uint32_t nread = 0;
  int32_t r = wasm_kernel_stream_read((uint32_t)fd, buf, (uint32_t)count, &nread);
  if (r < 0) {
    errno = -r;
    return -1;
  }
  return (ssize_t)r;
}

ssize_t
lisp_write(int fd, void *buf, size_t count)
{
  if (fd < 0) {
    (void)buf;
    (void)count;
    errno = EBADF;
    return -1;
  }

  int32_t r = wasm_kernel_stream_write((uint32_t)fd, buf, (uint32_t)count);
  if (r < 0) {
    errno = -r;
#ifdef WASM32
    char msg[128];
    int n = snprintf(msg, sizeof(msg),
                     "WASM lisp_write fail fd=%d count=%lu errno=%d\n",
                     fd, (unsigned long)count, errno);
    if (n > 0) {
      wasm_host_log(msg, (unsigned)n);
    }
#endif
    return -1;
  }
#ifdef WASM32
  if ((size_t)r != count) {
    char msg[128];
    int n = snprintf(msg, sizeof(msg),
                     "WASM lisp_write short fd=%d wrote=%d want=%lu\n",
                     fd, r, (unsigned long)count);
    if (n > 0) {
      wasm_host_log(msg, (unsigned)n);
    }
  }
#endif
  return (ssize_t)r;
}

int
lisp_open(char *path, int flags, mode_t mode)
{
  (void)mode;
  if (path == NULL) {
    errno = EINVAL;
    return -1;
  }

  size_t len = 0;
  const char *name = wasm_normalize_named_path(path, &len);
  if (len == 0) {
    errno = ENOENT;
    return -1;
  }

  int accmode = (flags & O_ACCMODE);
  uint32_t mode_flags = 0;
  switch (accmode) {
    case O_RDONLY:
      mode_flags |= WASM_FILE_MODE_READ;
      break;
    case O_WRONLY:
      mode_flags |= WASM_FILE_MODE_WRITE;
      break;
    case O_RDWR:
      mode_flags |= (WASM_FILE_MODE_READ | WASM_FILE_MODE_WRITE);
      break;
    default:
      errno = EINVAL;
      return -1;
  }

  if (flags & O_CREAT) {
    mode_flags |= WASM_FILE_MODE_CREATE;
  }
  if (flags & O_TRUNC) {
    mode_flags |= WASM_FILE_MODE_TRUNCATE;
  }
  if (flags & O_APPEND) {
    mode_flags |= WASM_FILE_MODE_APPEND;
  }

  if ((flags & O_TRUNC) && !(mode_flags & WASM_FILE_MODE_WRITE)) {
    errno = EACCES;
    return -1;
  }

  struct file_open_payload {
    uint32_t mode_flags;
    uint32_t path_ptr;
    uint32_t path_len;
    uint32_t reserved;
  } p;

  p.mode_flags = mode_flags;
  p.path_ptr = (uint32_t)(uintptr_t)name;
  p.path_len = (uint32_t)len;
  p.reserved = 0;

  uint32_t sid = 0;
  int32_t r = wasm_kernel_stream_open(KERNEL_STREAM_KIND_FILE, &p, (uint32_t)sizeof(p), &sid);
  if (r < 0) {
    if (mode_flags == WASM_FILE_MODE_READ && (r == -ENOSYS || r == -ENOENT)) {
      uint64_t size = 0;
      int32_t rn = wasm_kernel_stream_open_named(name, (uint32_t)len, &sid, &size);
      if (rn < 0) {
        errno = -rn;
        return -1;
      }
      (void)size;
      return (int)sid;
    }
    errno = -r;
    return -1;
  }
  return (int)sid;
}

int
lisp_fchmod(int fd, mode_t mode)
{
  (void)fd;
  (void)mode;
  errno = ENOSYS;
  return -1;
}

int64_t
lisp_lseek(int fd, int64_t offset, int whence)
{
  if (fd < 0) {
    errno = EBADF;
    return -1;
  }

  uint64_t pos = 0;
  int32_t r = wasm_kernel_stream_seek((uint32_t)fd, offset, (uint32_t)whence, &pos);
  if (r < 0) {
    errno = -r;
#ifdef WASM32
    char msg[160];
    int n = snprintf(msg, sizeof(msg),
                     "WASM lisp_lseek fail fd=%d off=%lld whence=%d errno=%d\n",
                     fd, (long long)offset, whence, errno);
    if (n > 0) {
      wasm_host_log(msg, (unsigned)n);
    }
#endif
    return -1;
  }
  return (int64_t)pos;
}

int
lisp_close(int fd)
{
  if (fd < 0) {
    errno = EBADF;
    return -1;
  }

  int32_t r = wasm_kernel_stream_close((uint32_t)fd);
  if (r < 0) {
    errno = -r;
    return -1;
  }
  return 0;
}

int
lisp_ftruncate(int fd, off_t length)
{
  if (fd < 0) {
    errno = EBADF;
    return -1;
  }
  if (length < 0) {
    errno = EINVAL;
    return -1;
  }

  int32_t r = wasm_kernel_stream_truncate((uint32_t)fd, (uint64_t)length);
  if (r < 0) {
    errno = -r;
    return -1;
  }
  return 0;
}

int
lisp_stat(char *path, void *buf)
{
  if (path == NULL || buf == NULL) {
    errno = EINVAL;
    return -1;
  }

  size_t len = 0;
  const char *name = wasm_normalize_named_path(path, &len);
  if (len == 0) {
    errno = ENOENT;
    return -1;
  }

  struct stat *st = (struct stat *)buf;
  memset(st, 0, sizeof(*st));

  struct path_payload {
    uint32_t flags;
    uint32_t path_ptr;
    uint32_t path_len;
    uint32_t reserved;
  } p;

  struct probe_response {
    uint32_t kind;
    uint32_t flags;
    uint64_t size;
    uint64_t mtime_ms;
  } resp;

  p.flags = 0;
  p.path_ptr = (uint32_t)(uintptr_t)name;
  p.path_len = (uint32_t)len;
  p.reserved = 0;

  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_FS_PROBE, &p, (uint32_t)sizeof(p),
                                       &resp, (uint32_t)sizeof(resp), &n);
  if (r == 0) {
    if (n != sizeof(resp)) {
      errno = EINVAL;
      return -1;
    }
    int is_dir = (resp.kind != 0);
    int is_readonly = (resp.flags & 1u) != 0;
    mode_t perms = is_readonly
                     ? (mode_t)(S_IRUSR | S_IRGRP | S_IROTH)
                     : (mode_t)(S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
    if (is_dir) {
      perms = (mode_t)(perms | S_IXUSR | S_IXGRP | S_IXOTH);
      st->st_mode = (mode_t)(S_IFDIR | perms);
    } else {
      st->st_mode = (mode_t)(S_IFREG | perms);
    }
    st->st_nlink = 1;
    st->st_size = (off_t)resp.size;
    st->st_blksize = 4096;
    st->st_blocks = (blkcnt_t)((resp.size + 511) / 512);
    st->st_mtime = (time_t)(resp.mtime_ms / 1000);
    return 0;
  }

  if (r == -ENOSYS || r == -ENOENT) {
    uint32_t sid = 0;
    uint64_t size = 0;
    int32_t rn = wasm_kernel_stream_open_named(name, (uint32_t)len, &sid, &size);
    if (rn < 0) {
      errno = -rn;
      return -1;
    }
    (void)wasm_kernel_stream_close(sid);
    st->st_mode = (mode_t)(S_IFREG | S_IRUSR | S_IRGRP | S_IROTH);
    st->st_nlink = 1;
    st->st_size = (off_t)size;
    st->st_blksize = 4096;
    st->st_blocks = (blkcnt_t)((size + 511) / 512);
    return 0;
  }

  errno = -r;
  return -1;
}

int
lisp_fstat(int fd, void *buf)
{
  (void)fd;
  (void)buf;
  errno = ENOSYS;
  return -1;
}

int
lisp_lstat(char *path, void *buf)
{
  (void)path;
  (void)buf;
  errno = ENOSYS;
  return -1;
}

int
lisp_futex(int *uaddr, int op, int val, void *timeout, int *uaddr2, int val3)
{
  (void)uaddr;
  (void)op;
  (void)val;
  (void)timeout;
  (void)uaddr2;
  (void)val3;
  errno = ENOSYS;
  return -1;
}

DIR *
lisp_opendir(char *path)
{
  (void)path;
  errno = ENOSYS;
  return NULL;
}

struct dirent *
lisp_readdir(DIR *dir)
{
  (void)dir;
  errno = ENOSYS;
  return NULL;
}

int
lisp_closedir(DIR *dir)
{
  (void)dir;
  errno = ENOSYS;
  return -1;
}

int
lisp_pipe(int pipefd[2])
{
  (void)pipefd;
  errno = ENOSYS;
  return -1;
}

int
lisp_gettimeofday(struct timeval *tp, void *tzp)
{
  (void)tp;
  (void)tzp;
  errno = ENOSYS;
  return -1;
}

int
lisp_sigexit(int signum)
{
  (void)signum;
  errno = ENOSYS;
  return -1;
}

char *
lisp_realpath(const char *file_name, char *resolved_name)
{
  (void)file_name;
  (void)resolved_name;
  errno = ENOSYS;
  return NULL;
}

#else /* !WASM32 */

ssize_t
lisp_read(int fd, void *buf, size_t count)
{
  return read(fd,buf,count);
}

ssize_t
lisp_write(int fd, void *buf, size_t count)
{
  return write(fd,buf,count);
}

int
lisp_open(char *path, int flags, mode_t mode)
{
  return open(path,flags,mode);
}

int
lisp_fchmod(int fd, mode_t mode)
{
  return fchmod(fd,mode);
}

int64_t
lisp_lseek(int fd, int64_t offset, int whence)
{
#ifdef LINUX
  return lseek64(fd,offset,whence);
#else
  return lseek(fd,offset,whence);
#endif
}

int
lisp_close(int fd)
{
  return close(fd);
}

int
lisp_ftruncate(int fd, off_t length)
{
  return ftruncate(fd,length);
}

int
lisp_stat(char *path, void *buf)
{
  return stat(path,buf);
}

int
lisp_fstat(int fd, void *buf)
{
  return fstat(fd,buf);
}

int
lisp_lstat(char *path, void *buf)
{
  return lstat(path, buf);
}

int
lisp_futex(int *uaddr, int op, int val, void *timeout, int *uaddr2, int val3)
{
#ifdef LINUX
  return syscall(SYS_futex,uaddr,op,val,timeout,uaddr2,val3);
#else
  errno = ENOSYS;
  return -1;
#endif
}

DIR *
lisp_opendir(char *path)
{
  return opendir(path);
}

struct dirent *
lisp_readdir(DIR *dir)
{
  return readdir(dir);
}

int
lisp_closedir(DIR *dir)
{
  return closedir(dir);
}

int
lisp_pipe(int pipefd[2])
{
  return pipe(pipefd);
}

int
lisp_gettimeofday(struct timeval *tp, void *tzp)
{
  return gettimeofday(tp, tzp);
}

int
lisp_sigexit(int signum)
{
  signal(signum, SIG_DFL);
  return kill(getpid(), signum);
}

#ifdef ANDROID_NEEDS_SIGALTSTACK
/* I for one welcome our new Android overlords. */
#ifndef __NR_sigaltstack
#define __NR_sigaltstack		(__NR_SYSCALL_BASE+186)
#endif
int
sigaltstack(stack_t *in, stack_t *out)
{
  return syscall(__NR_sigaltstack,in,out);
}
#endif

char *
lisp_realpath(const char *file_name, char *resolved_name)
{
  return realpath(file_name, resolved_name);
}

#endif /* WASM32 */
