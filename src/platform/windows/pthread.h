#ifndef KJDB_WINDOWS_PTHREAD_SUBSET_H
#define KJDB_WINDOWS_PTHREAD_SUBSET_H
#include "windows_compat.h"
/* Private subset used by KJDB, not a general pthread implementation.
 * Reader locks intentionally serialize on Windows for unambiguous unlock. */
typedef SRWLOCK pthread_mutex_t;
typedef SRWLOCK pthread_rwlock_t;
typedef CONDITION_VARIABLE pthread_cond_t;
typedef INIT_ONCE pthread_once_t;
typedef struct kjdb_win_thread *pthread_t;
#define PTHREAD_MUTEX_INITIALIZER SRWLOCK_INIT
#define PTHREAD_ONCE_INIT INIT_ONCE_STATIC_INIT
static inline int pthread_mutex_init(pthread_mutex_t *p,const void *a) { if(a)return ENOTSUP; InitializeSRWLock(p);return 0; }
static inline int pthread_mutex_lock(pthread_mutex_t *p) { AcquireSRWLockExclusive(p);return 0; }
static inline int pthread_mutex_unlock(pthread_mutex_t *p) { ReleaseSRWLockExclusive(p);return 0; }
static inline int pthread_mutex_destroy(pthread_mutex_t *p) { (void)p;return 0; }
#define pthread_rwlock_init pthread_mutex_init
#define pthread_rwlock_rdlock pthread_mutex_lock
#define pthread_rwlock_wrlock pthread_mutex_lock
#define pthread_rwlock_unlock pthread_mutex_unlock
#define pthread_rwlock_destroy pthread_mutex_destroy
static inline int pthread_cond_init(pthread_cond_t *p,const void *a) { if(a)return ENOTSUP;InitializeConditionVariable(p);return 0; }
static inline int pthread_cond_wait(pthread_cond_t *p,pthread_mutex_t *m) { return SleepConditionVariableSRW(p,m,INFINITE,0)?0:EIO; }
static inline int pthread_cond_signal(pthread_cond_t *p) { WakeConditionVariable(p);return 0; }
static inline int pthread_cond_broadcast(pthread_cond_t *p) { WakeAllConditionVariable(p);return 0; }
static inline int pthread_cond_destroy(pthread_cond_t *p) { (void)p;return 0; }
int pthread_create(pthread_t *,const void *,void *(*)(void *),void *);
int pthread_join(pthread_t,void **);
int pthread_once(pthread_once_t *,void (*)(void));
#endif
