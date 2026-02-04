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
#include <limits.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef lseek
#undef lseek
#endif
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

/* Optional in-memory boot image backing store.
 * `open/read/lseek/stat` will expose this as a pseudo-file to the kernel image loader.
 */
static const uint8_t *wasm_boot_image_bytes = NULL;
static size_t wasm_boot_image_len = 0;
static size_t wasm_boot_image_off = 0;
static const int wasm_boot_image_fd = 3;

__attribute__((used, visibility("default"), export_name("wasm_set_boot_image")))
void
wasm_set_boot_image(uint32_t bytes_ptr, uint32_t bytes_len)
{
  wasm_boot_image_bytes = (const uint8_t *)(uintptr_t)bytes_ptr;
  wasm_boot_image_len = (size_t)bytes_len;
  wasm_boot_image_off = 0;
}

/* Forward decls for local libc shims used before their definitions. */
void *memset(void *dst, int c, size_t n);
size_t strlen(const char *s);
int strncmp(const char *a, const char *b, size_t n);

static int
wasm_str_ends_with(const char *s, const char *suffix)
{
  if (!s || !suffix) {
    return 0;
  }
  size_t slen = strlen(s);
  size_t tlen = strlen(suffix);
  if (slen < tlen) {
    return 0;
  }
  return (strncmp(s + (slen - tlen), suffix, tlen) == 0);
}

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

struct wasm_vsn_outbuf {
  char *dst;
  size_t cap;
  size_t written; /* bytes that would have been written (excluding NUL) */
};

static void
wasm_vsn_out_ch(struct wasm_vsn_outbuf *out, char c)
{
  if (out->dst && out->cap) {
    if (out->written + 1 < out->cap) {
      out->dst[out->written] = c;
    }
  }
  out->written++;
}

static void
wasm_vsn_out_mem(struct wasm_vsn_outbuf *out, const char *s, size_t n)
{
  for (size_t i = 0; i < n; i++) {
    wasm_vsn_out_ch(out, s[i]);
  }
}

static void
wasm_vsn_out_str(struct wasm_vsn_outbuf *out, const char *s, size_t maxlen)
{
  if (s == NULL) {
    s = "(null)";
  }
  size_t n = 0;
  while (s[n] && (maxlen == (size_t)-1 || n < maxlen)) {
    n++;
  }
  wasm_vsn_out_mem(out, s, n);
}

static void
wasm_vsn_out_uint_base(struct wasm_vsn_outbuf *out,
                       uint64_t v,
                       unsigned base,
                       int uppercase,
                       int width,
                       int zero_pad)
{
  char tmp[32];
  const char *digits = uppercase ? "0123456789ABCDEF" : "0123456789abcdef";
  int i = 0;
  if (base < 2 || base > 16) {
    return;
  }
  do {
    tmp[i++] = digits[(unsigned)(v % base)];
    v /= base;
  } while (v && i < (int)sizeof(tmp));

  int pad = width - i;
  char padch = zero_pad ? '0' : ' ';
  while (pad-- > 0) {
    wasm_vsn_out_ch(out, padch);
  }
  while (i-- > 0) {
    wasm_vsn_out_ch(out, tmp[i]);
  }
}

static void
wasm_vsn_out_int(struct wasm_vsn_outbuf *out, int64_t v, int width, int zero_pad)
{
  if (v < 0) {
    wasm_vsn_out_ch(out, '-');
    /* Avoid UB on INT64_MIN by converting via unsigned. */
    wasm_vsn_out_uint_base(out, (uint64_t)(~(uint64_t)v + 1), 10, 0, width, zero_pad);
  } else {
    wasm_vsn_out_uint_base(out, (uint64_t)v, 10, 0, width, zero_pad);
  }
}

int
vsnprintf(char *buf, size_t size, const char *fmt, va_list ap)
{
  /* Minimal vsnprintf: supports %%, %s, %c, %d/%i, %u, %x/%X, %p and a small
   * subset of width/precision/length modifiers used by the kernel.
   */
  if (buf && size) {
    buf[0] = 0;
  }

  if (fmt == NULL) {
    return 0;
  }

  struct wasm_vsn_outbuf out = {buf, size, 0};

  for (const char *p = fmt; *p; p++) {
    if (*p != '%') {
      wasm_vsn_out_ch(&out, *p);
      continue;
    }

    p++;
    if (*p == 0) {
      break;
    }

    int zero_pad = 0;
    if (*p == '0') {
      zero_pad = 1;
      p++;
    }

    int width = 0;
    while (*p >= '0' && *p <= '9') {
      width = (width * 10) + (*p - '0');
      p++;
    }

    /* Precision: only used for %s. */
    size_t precision = (size_t)-1;
    if (*p == '.') {
      p++;
      precision = 0;
      while (*p >= '0' && *p <= '9') {
        precision = (precision * 10) + (size_t)(*p - '0');
        p++;
      }
    }

    enum { LEN_NONE, LEN_L, LEN_LL } len = LEN_NONE;
    if (*p == 'l') {
      p++;
      len = LEN_L;
      if (*p == 'l') {
        p++;
        len = LEN_LL;
      }
    }

    char spec = *p;
    switch (spec) {
    case '%':
      wasm_vsn_out_ch(&out, '%');
      break;
    case 'c': {
      int c = va_arg(ap, int);
      wasm_vsn_out_ch(&out, (char)c);
      break;
    }
    case 's': {
      const char *s = va_arg(ap, const char *);
      wasm_vsn_out_str(&out, s, precision);
      break;
    }
    case 'd':
    case 'i': {
      int64_t v;
      if (len == LEN_LL) {
        v = va_arg(ap, long long);
      } else if (len == LEN_L) {
        v = va_arg(ap, long);
      } else {
        v = va_arg(ap, int);
      }
      wasm_vsn_out_int(&out, v, width, zero_pad);
      break;
    }
    case 'u': {
      uint64_t v;
      if (len == LEN_LL) {
        v = va_arg(ap, unsigned long long);
      } else if (len == LEN_L) {
        v = va_arg(ap, unsigned long);
      } else {
        v = va_arg(ap, unsigned int);
      }
      wasm_vsn_out_uint_base(&out, v, 10, 0, width, zero_pad);
      break;
    }
    case 'x':
    case 'X': {
      int uppercase = (spec == 'X');
      uint64_t v;
      if (len == LEN_LL) {
        v = va_arg(ap, unsigned long long);
      } else if (len == LEN_L) {
        v = va_arg(ap, unsigned long);
      } else {
        v = va_arg(ap, unsigned int);
      }
      wasm_vsn_out_uint_base(&out, v, 16, uppercase, width, zero_pad);
      break;
    }
    case 'p': {
      void *vp = va_arg(ap, void *);
      uintptr_t v = (uintptr_t)vp;
      wasm_vsn_out_mem(&out, "0x", 2);
      wasm_vsn_out_uint_base(&out, (uint64_t)v, 16, 0, (int)(sizeof(uintptr_t) * 2), 1);
      break;
    }
    default:
      /* Unknown specifier: emit it verbatim to preserve context. */
      wasm_vsn_out_ch(&out, '%');
      wasm_vsn_out_ch(&out, spec);
      break;
    }
  }

  if (out.dst && out.cap) {
    size_t n = (out.written >= out.cap) ? (out.cap - 1) : out.written;
    out.dst[n] = 0;
  }

  if (out.written > (size_t)INT_MAX) {
    return INT_MAX;
  }
  return (int)out.written;
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
  if (
#ifdef _SC_PAGESIZE
      name == _SC_PAGESIZE
#else
      0
#endif
#ifdef _SC_PAGE_SIZE
      || name == _SC_PAGE_SIZE
#endif
      ) {
    return 4096;
  }
  errno = ENOSYS;
  return -1;
}

int
open(const char *path, int flags, ...)
{
  (void)path;
  (void)flags;
  if (wasm_boot_image_bytes && wasm_str_ends_with(path, ".image")) {
    wasm_boot_image_off = 0;
    return wasm_boot_image_fd;
  }
  errno = ENOENT;
  return -1;
}

int
close(int fd)
{
  if (fd == wasm_boot_image_fd) {
    return 0;
  }
  errno = EBADF;
  return -1;
}

ssize_t
read(int fd, void *buf, size_t count)
{
  if ((fd != wasm_boot_image_fd) || (wasm_boot_image_bytes == NULL)) {
    (void)buf;
    (void)count;
    errno = EBADF;
    return -1;
  }
  if (wasm_boot_image_off >= wasm_boot_image_len) {
    return 0;
  }
  size_t remain = wasm_boot_image_len - wasm_boot_image_off;
  size_t n = (count < remain) ? count : remain;
  if (n) {
    memmove(buf, wasm_boot_image_bytes + wasm_boot_image_off, n);
    wasm_boot_image_off += n;
  }
  return (ssize_t)n;
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
  if ((fd != wasm_boot_image_fd) || (wasm_boot_image_bytes == NULL)) {
    errno = EBADF;
    return (off_t)-1;
  }

  int64_t base = 0;
  switch (whence) {
  case SEEK_SET:
    base = 0;
    break;
  case SEEK_CUR:
    base = (int64_t)wasm_boot_image_off;
    break;
  case SEEK_END:
    base = (int64_t)wasm_boot_image_len;
    break;
  default:
    errno = EINVAL;
    return (off_t)-1;
  }

  int64_t next = base + (int64_t)offset;
  if (next < 0) {
    errno = EINVAL;
    return (off_t)-1;
  }
  if ((uint64_t)next > (uint64_t)wasm_boot_image_len) {
    next = (int64_t)wasm_boot_image_len;
  }
  wasm_boot_image_off = (size_t)next;
  return (off_t)next;
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
  if ((fd != wasm_boot_image_fd) || (wasm_boot_image_bytes == NULL) || (st == NULL)) {
    errno = EBADF;
    return -1;
  }
  memset(st, 0, sizeof(*st));
  st->st_mode = S_IFREG | 0444;
  st->st_size = (off_t)wasm_boot_image_len;
  return 0;
}

int
stat(const char *path, struct stat *st)
{
  if (!wasm_boot_image_bytes || !wasm_str_ends_with(path, ".image") || (st == NULL)) {
    errno = ENOENT;
    return -1;
  }
  memset(st, 0, sizeof(*st));
  st->st_mode = S_IFREG | 0444;
  st->st_size = (off_t)wasm_boot_image_len;
  return 0;
}

int
fsync(int fd)
{
  (void)fd;
  errno = ENOSYS;
  return -1;
}

#endif /* WASM32 */
