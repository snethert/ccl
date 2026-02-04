/*
 * WASM32 kernel imports table (CCL KERNEL_IMPORTS).
 *
 * On native targets, lisp-kernel/imports.s builds a table of host services and
 * stores its base in the lisp global KERNEL_IMPORTS.
 *
 * For WASM bring-up, we keep the Lisp-side mechanism (CCL philosophy) but make
 * the table point to kernel-owned functions (many are stubs). Host services
 * should be implemented via the kernel_request ABI instead of direct OS calls.
 */

#ifdef WASM32

#include "lisp.h"
#include "threads.h"

#include <stdint.h>
#include <sys/select.h>
#include <sys/stat.h>
#include <sys/types.h>

/* --- Forward declarations (many have no shared header) --- */

extern int fd_setsize_bytes(void);
extern void do_fd_set(int fd, fd_set *fdsetp);
extern void do_fd_clr(int fd, fd_set *fdsetp);
extern int do_fd_is_set(int fd, fd_set *fdsetp);
extern void do_fd_zero(fd_set *fdsetp);

extern void *xGetSharedLibrary(char *path, int mode);
extern void *xFindSymbol(void *handle, char *name);

extern void *lisp_malloc(size_t size);
extern void lisp_free(void *p);

extern int wait_for_signal(int signo, int seconds, int milliseconds);

extern void register_xmacptr_dispose_function(void *dfn);

extern void open_debug_output(int fd);
extern void *get_r_debug(void);

extern void restore_soft_stack_limit(unsigned stkreg);
extern void lisp_egc_control(Boolean activate);
extern void lisp_bug(char *string);

extern void *xNewThread(natural control_stack_size, natural value_stack_size, natural temp_stack_size);
extern void *do_nothing(void);
extern void xDisposeThread(TCR *tcr);
extern OSErr xThreadCurrentStackSpace(TCR *tcr, unsigned *resultP);

extern void usage_exit(char *herald, int exit_status, char *other_args);

extern void *new_semaphore(int count);
extern int wait_on_semaphore(void *s, int seconds, int millis);
extern void signal_semaphore(SEMAPHORE s);
extern void destroy_semaphore(void **s);

extern RECURSIVE_LOCK new_recursive_lock(void);
extern int lock_recursive_lock(RECURSIVE_LOCK m, TCR *tcr);
extern int unlock_recursive_lock(RECURSIVE_LOCK m, TCR *tcr);
extern void destroy_recursive_lock(RECURSIVE_LOCK m);

extern void lisp_suspend_other_threads(void);
extern void lisp_resume_other_threads(void);
extern Boolean lisp_suspend_tcr(TCR *tcr);
extern Boolean lisp_resume_tcr(TCR *tcr);

extern rwlock *rwlock_new(void);
extern void rwlock_destroy(rwlock *rw);
extern int rwlock_rlock(rwlock *rw, TCR *tcr, struct timespec *waitfor);
extern int rwlock_wlock(rwlock *rw, TCR *tcr, struct timespec *waitfor);
extern int rwlock_unlock(rwlock *rw, TCR *tcr);

extern int recursive_lock_trylock(RECURSIVE_LOCK m, TCR *tcr, int *was_free);

extern char *foreign_name_and_offset(natural addr, int *delta);

extern ssize_t lisp_read(int fd, void *buf, size_t count);
extern ssize_t lisp_write(int fd, void *buf, size_t count);
extern int lisp_open(char *path, int flags, mode_t mode);
extern int lisp_fchmod(int fd, mode_t mode);
extern int64_t lisp_lseek(int fd, int64_t offset, int whence);
extern int lisp_close(int fd);
extern int lisp_ftruncate(int fd, off_t length);
extern int lisp_stat(char *path, void *buf);
extern int lisp_fstat(int fd, void *buf);
extern int lisp_futex(int *uaddr, int futex_op, int val, const void *timeout, int *uaddr2, int val3);
extern void *lisp_opendir(char *path);
extern void *lisp_readdir(void *dir);
extern int lisp_closedir(void *dir);
extern int lisp_pipe(int *fds);
extern int lisp_gettimeofday(struct timeval *tp, void *tzp);
extern int lisp_sigexit(int signum);
typedef int (*jvm_initfunc)(void *, void *, void *);
extern int jvm_init(jvm_initfunc f, void *arg0, void *arg1, void *arg2);
extern int lisp_lstat(char *path, void *buf);
extern char *lisp_realpath(const char *in, char *out);

/* --- WASM-only stubs for imports that are implemented in asm on other targets --- */

void *
tcr_frame_ptr(TCR *tcr)
{
  (void)tcr;
  return NULL;
}

void
save_fp_context(void *buf)
{
  (void)buf;
}

void
restore_fp_context(void *buf)
{
  (void)buf;
}

void
put_vector_registers(void *buf)
{
  (void)buf;
}

void
get_vector_registers(void *buf)
{
  (void)buf;
}

/*
 * The imports table order MUST match lisp-kernel/imports.s and the compiler's
 * KERNEL-IMPORT-* enum order.
 */
#define KI(fn) ((LispObj)(fn))
static LispObj wasm_kernel_imports[] = {
  KI(fd_setsize_bytes),
  KI(do_fd_set),
  KI(do_fd_clr),
  KI(do_fd_is_set),
  KI(do_fd_zero),
  KI(xMakeDataExecutable),
  KI(xGetSharedLibrary),
  KI(xFindSymbol),
  KI(lisp_malloc),
  KI(lisp_free),
  KI(wait_for_signal),
  KI(tcr_frame_ptr),
  KI(register_xmacptr_dispose_function),
  KI(open_debug_output),
  KI(get_r_debug),
  KI(restore_soft_stack_limit),
  KI(lisp_egc_control),
  KI(lisp_bug),
  KI(xNewThread),
  KI(do_nothing),
  KI(xDisposeThread),
  KI(xThreadCurrentStackSpace),
  KI(usage_exit),
  KI(save_fp_context),
  KI(restore_fp_context),
  KI(put_vector_registers),
  KI(get_vector_registers),
  KI(new_semaphore),
  KI(wait_on_semaphore),
  KI(signal_semaphore),
  KI(destroy_semaphore),
  KI(new_recursive_lock),
  KI(lock_recursive_lock),
  KI(unlock_recursive_lock),
  KI(destroy_recursive_lock),
  KI(lisp_suspend_other_threads),
  KI(lisp_resume_other_threads),
  KI(lisp_suspend_tcr),
  KI(lisp_resume_tcr),
  KI(rwlock_new),
  KI(rwlock_destroy),
  KI(rwlock_rlock),
  KI(rwlock_wlock),
  KI(rwlock_unlock),
  KI(recursive_lock_trylock),
  KI(foreign_name_and_offset),
  KI(lisp_read),
  KI(lisp_write),
  KI(lisp_open),
  KI(lisp_fchmod),
  KI(lisp_lseek),
  KI(lisp_close),
  KI(lisp_ftruncate),
  KI(lisp_stat),
  KI(lisp_fstat),
  KI(lisp_futex),
  KI(lisp_opendir),
  KI(lisp_readdir),
  KI(lisp_closedir),
  KI(lisp_pipe),
  KI(lisp_gettimeofday),
  KI(lisp_sigexit),
  KI(jvm_init),
  KI(lisp_lstat),
  KI(lisp_realpath),
};
#undef KI

/*
 * pmcl-kernel.c stores this value in the lisp global KERNEL_IMPORTS.
 * On other targets, imports.s defines this symbol.
 */
LispObj import_ptrs_base = (LispObj)wasm_kernel_imports;

#endif /* WASM32 */
