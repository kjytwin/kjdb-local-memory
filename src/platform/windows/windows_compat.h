#ifndef KJDB_WINDOWS_COMPAT_H
#define KJDB_WINDOWS_COMPAT_H
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <errno.h>
#include <fcntl.h>
#include <io.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
typedef int64_t kjdb_off_t;
typedef intptr_t ssize_t;
struct kjdb_win_stat { int st_mode; int64_t st_size; uint32_t st_nlink; };
#define off_t kjdb_off_t
#define stat kjdb_win_stat
#define fstat kjdb_win_fstat
#define S_ISREG(m) (((m)&_S_IFMT)==_S_IFREG)
#define O_DIRECTORY 0x10000000
#define O_KJDB_PIN_DIRECTORY 0x08000000
#define O_KJDB_RENAME_FILE 0x04000000
#define O_NOFOLLOW 0x20000000
#define O_NONBLOCK 0x40000000
#define O_CLOEXEC _O_NOINHERIT
#define O_RDONLY _O_RDONLY
#define O_RDWR _O_RDWR
#define O_WRONLY _O_WRONLY
#define O_CREAT _O_CREAT
#define O_EXCL _O_EXCL
#define O_TRUNC _O_TRUNC
#define open kjdb_win_open
#define close _close
#define unlink kjdb_win_unlink
#define link kjdb_win_link
#define mkstemp kjdb_win_mkstemp
#define ftruncate kjdb_win_truncate
#define pread kjdb_win_pread
#define pwrite kjdb_win_pwrite
#define fsync kjdb_win_sync
#define strdup _strdup
#define strndup kjdb_win_strndup
#define CLOCK_MONOTONIC 1
#define CLOCK_REALTIME 2
#define clock_gettime kjdb_win_clock_gettime
#define LOCK_SH 1
#define LOCK_EX 2
#define LOCK_NB 4
#define flock kjdb_win_flock
#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_PRIVATE 1
#define MAP_ANONYMOUS 2
#define MAP_FAILED ((void *)-1)
#define mmap kjdb_win_mmap
#define munmap kjdb_win_munmap
int kjdb_win_open(const char *,int,...);
int kjdb_win_memory_openat(int,const char *,int,...);
int kjdb_win_memory_unlinkat(int,const char *,int);
int kjdb_win_memory_publish(int,int,const char *);
int kjdb_win_fstat(int,struct kjdb_win_stat *);
int kjdb_win_unlink(const char *);
int kjdb_win_link(const char *,const char *);
int kjdb_win_mkstemp(char *);
int kjdb_win_truncate(int,int64_t);
ssize_t kjdb_win_pread(int,void *,size_t,int64_t);
ssize_t kjdb_win_pwrite(int,const void *,size_t,int64_t);
int kjdb_win_sync(int);
char *kjdb_win_strndup(const char *,size_t);
int kjdb_win_clock_gettime(int,struct timespec *);
int kjdb_win_flock(int,int);
void *kjdb_win_mmap(void *,size_t,int,int,int,int64_t);
int kjdb_win_munmap(void *,size_t);
#endif
