/*
 * Minimal libc/runtime shims for the WASM32 "no WASI" bring-up.
 *
 * This is intentionally tiny and incomplete: it exists to make the kernel
 * link as a freestanding wasm module while the real JS microkernel API is
 * being designed.
 */

#ifdef WASM32

#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <time.h>
#include <stdio.h>

/* wasi-libc declares errno as TLS; provide it. */
_Thread_local int errno;

FILE *const stdin = (FILE *)0;
FILE *const stdout = (FILE *)0;
FILE *const stderr = (FILE *)0;

/* Declared in platform-wasm32.h, but keep this file standalone. */
extern int32_t wasm_memory_grow_and_relocate(uint32_t pages);

static uintptr_t
align_up_uintptr(uintptr_t p, uintptr_t a)
{
  return (p + (a - 1)) & ~(a - 1);
}

/* Extremely simple bump allocator. free() is a no-op. */
static uintptr_t wasm_heap_ptr = 0;

/* Forward decls for local libc shims used before their definitions. */
void *memset(void *dst, int c, size_t n);

void *
malloc(size_t size)
{
  if (size == 0) {
    size = 1;
  }

  if (wasm_heap_ptr == 0) {
    extern char __heap_base;
    wasm_heap_ptr = align_up_uintptr((uintptr_t)&__heap_base, 16);
  }

  uintptr_t p = align_up_uintptr(wasm_heap_ptr, 16);
  uintptr_t n = align_up_uintptr(size, 16);
  uintptr_t newp = p + n;
  if (newp < p) {
    errno = ENOMEM;
    return NULL;
  }

#if defined(__wasm__)
  const uintptr_t wasm_page_size = 65536u;
  uintptr_t have = (uintptr_t)__builtin_wasm_memory_size(0) * wasm_page_size;
  if (newp > have) {
    uintptr_t need = newp - have;
    uint32_t pages = (uint32_t)((need + wasm_page_size - 1) / wasm_page_size);
    if (pages == 0) {
      pages = 1;
    }
    if (wasm_memory_grow_and_relocate(pages) < 0) {
      errno = ENOMEM;
      return NULL;
    }
  }
#endif

  wasm_heap_ptr = newp;
  return (void *)p;
}

void
free(void *p)
{
  (void)p;
}

void *
calloc(size_t nmemb, size_t size)
{
  size_t total = nmemb * size;
  if (nmemb != 0 && total / nmemb != size) {
    errno = ENOMEM;
    return NULL;
  }
  void *p = malloc(total);
  if (p) {
    (void)memset(p, 0, total);
  }
  return p;
}

void *
memset(void *dst, int c, size_t n)
{
  unsigned char *p = (unsigned char *)dst;
  for (size_t i = 0; i < n; i++) {
    p[i] = (unsigned char)c;
  }
  return dst;
}

void *
memmove(void *dst, const void *src, size_t n)
{
  unsigned char *d = (unsigned char *)dst;
  const unsigned char *s = (const unsigned char *)src;

  if (d == s || n == 0) {
    return dst;
  }
  if (d < s) {
    for (size_t i = 0; i < n; i++) {
      d[i] = s[i];
    }
  } else {
    for (size_t i = n; i != 0; i--) {
      d[i - 1] = s[i - 1];
    }
  }
  return dst;
}

size_t
strlen(const char *s)
{
  size_t n = 0;
  while (s && s[n]) {
    n++;
  }
  return n;
}

char *
strcpy(char *dst, const char *src)
{
  char *p = dst;
  while (src && *src) {
    *p++ = *src++;
  }
  *p = 0;
  return dst;
}

int
strcmp(const char *a, const char *b)
{
  while (a && b && *a && (*a == *b)) {
    a++;
    b++;
  }
  unsigned char ac = (unsigned char)(a ? *a : 0);
  unsigned char bc = (unsigned char)(b ? *b : 0);
  return (int)ac - (int)bc;
}

int
strncmp(const char *a, const char *b, size_t n)
{
  for (size_t i = 0; i < n; i++) {
    unsigned char ac = (unsigned char)(a ? a[i] : 0);
    unsigned char bc = (unsigned char)(b ? b[i] : 0);
    if (ac != bc || ac == 0) {
      return (int)ac - (int)bc;
    }
  }
  return 0;
}

char *
strchr(const char *s, int c)
{
  if (!s) {
    return NULL;
  }
  for (; *s; s++) {
    if ((unsigned char)*s == (unsigned char)c) {
      return (char *)s;
    }
  }
  return (c == 0) ? (char *)s : NULL;
}

int
toupper(int c)
{
  if (c >= 'a' && c <= 'z') {
    return c - ('a' - 'A');
  }
  return c;
}

unsigned long
strtoul(const char *nptr, char **endptr, int base)
{
  const char *p = nptr;
  while (p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) {
    p++;
  }

  if (base == 0) {
    if (p && p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) {
      base = 16;
      p += 2;
    } else if (p && p[0] == '0') {
      base = 8;
      p++;
    } else {
      base = 10;
    }
  }

  unsigned long v = 0;
  const char *start = p;
  for (;; p++) {
    int d = -1;
    unsigned char ch = (unsigned char)(p ? *p : 0);
    if (ch >= '0' && ch <= '9') d = ch - '0';
    else if (ch >= 'a' && ch <= 'f') d = 10 + (ch - 'a');
    else if (ch >= 'A' && ch <= 'F') d = 10 + (ch - 'A');
    else break;

    if (d < 0 || d >= base) break;
    v = v * (unsigned long)base + (unsigned long)d;
  }

  if (endptr) {
    *endptr = (char *)((p && p != start) ? p : nptr);
  }
  return v;
}

static int
vsnprintf_stub(char *buf, size_t size)
{
  if (buf && size) {
    buf[0] = 0;
  }
  return 0;
}

int
vsnprintf(char *buf, size_t size, const char *fmt, va_list ap)
{
  (void)fmt;
  (void)ap;
  return vsnprintf_stub(buf, size);
}

int
snprintf(char *buf, size_t size, const char *fmt, ...)
{
  va_list ap;
  va_start(ap, fmt);
  int r = vsnprintf(buf, size, fmt, ap);
  va_end(ap);
  return r;
}

int
sprintf(char *buf, const char *fmt, ...)
{
  va_list ap;
  va_start(ap, fmt);
  int r = vsnprintf(buf, (size_t)-1, fmt, ap);
  va_end(ap);
  return r;
}

int
sscanf(const char *str, const char *fmt, ...)
{
  (void)str;
  (void)fmt;
  return 0;
}

int
fprintf(FILE *stream, const char *fmt, ...)
{
  (void)stream;
  (void)fmt;
  return 0;
}

int
vfprintf(FILE *stream, const char *fmt, va_list ap)
{
  (void)stream;
  (void)fmt;
  (void)ap;
  return 0;
}

size_t
fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream)
{
  (void)ptr;
  (void)size;
  (void)stream;
  return nmemb;
}

int
fputc(int c, FILE *stream)
{
  (void)stream;
  return c;
}

int
fputs(const char *s, FILE *stream)
{
  (void)s;
  (void)stream;
  return 0;
}

int
fflush(FILE *stream)
{
  (void)stream;
  return 0;
}

int
ferror(FILE *stream)
{
  (void)stream;
  return 0;
}

void
clearerr(FILE *stream)
{
  (void)stream;
}

int
fileno(FILE *stream)
{
  (void)stream;
  return -1;
}

FILE *
fdopen(int fd, const char *mode)
{
  (void)fd;
  (void)mode;
  return NULL;
}

int
setvbuf(FILE *stream, char *buf, int mode, size_t size)
{
  (void)stream;
  (void)buf;
  (void)mode;
  (void)size;
  return 0;
}

int
fclose(FILE *stream)
{
  (void)stream;
  return 0;
}

char *
fgets(char *s, int size, FILE *stream)
{
  (void)s;
  (void)size;
  (void)stream;
  return NULL;
}

int
fgetc(FILE *stream)
{
  (void)stream;
  return -1;
}

char *
strerror(int errnum)
{
  (void)errnum;
  return (char *)"error";
}

void
perror(const char *s)
{
  (void)s;
}

__attribute__((noreturn))
void
abort(void)
{
  __builtin_trap();
  __builtin_unreachable();
}

__attribute__((noreturn))
void
_exit(int status)
{
  (void)status;
  __builtin_trap();
  __builtin_unreachable();
}

__attribute__((noreturn))
void
exit(int status)
{
  _exit(status);
}

long
sysconf(int name)
{
  (void)name;
  errno = ENOSYS;
  return -1;
}

int
open(const char *path, int flags, ...)
{
  (void)path;
  (void)flags;
  errno = ENOSYS;
  return -1;
}

int
close(int fd)
{
  (void)fd;
  errno = ENOSYS;
  return -1;
}

ssize_t
read(int fd, void *buf, size_t count)
{
  (void)fd;
  (void)buf;
  (void)count;
  errno = ENOSYS;
  return -1;
}

ssize_t
write(int fd, const void *buf, size_t count)
{
  (void)fd;
  (void)buf;
  (void)count;
  errno = ENOSYS;
  return -1;
}

off_t
lseek(int fd, off_t offset, int whence)
{
  (void)fd;
  (void)offset;
  (void)whence;
  errno = ENOSYS;
  return (off_t)-1;
}

off_t
__wasilibc_tell(int fd)
{
  (void)fd;
  errno = ENOSYS;
  return (off_t)-1;
}

int
fstat(int fd, struct stat *st)
{
  (void)fd;
  (void)st;
  errno = ENOSYS;
  return -1;
}

int
stat(const char *path, struct stat *st)
{
  (void)path;
  (void)st;
  errno = ENOSYS;
  return -1;
}

int
fsync(int fd)
{
  (void)fd;
  errno = ENOSYS;
  return -1;
}

time_t
time(time_t *tloc)
{
  if (tloc) {
    *tloc = 0;
  }
  return (time_t)0;
}

#endif /* WASM32 */
