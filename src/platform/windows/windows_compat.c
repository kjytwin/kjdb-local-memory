#include "windows_compat.h"
#include "pthread.h"
#include <process.h>
#include <sddl.h>
static int failure(DWORD e) {
    switch(e) {
    case ERROR_FILE_NOT_FOUND:case ERROR_PATH_NOT_FOUND:errno=ENOENT;break;
    case ERROR_FILE_EXISTS:case ERROR_ALREADY_EXISTS:errno=EEXIST;break;
    case ERROR_ACCESS_DENIED:errno=EACCES;break;
    case ERROR_LOCK_VIOLATION:case ERROR_SHARING_VIOLATION:errno=EAGAIN;break;
    case ERROR_DISK_FULL:errno=ENOSPC;break;
    case ERROR_NOT_ENOUGH_MEMORY:errno=ENOMEM;break;
    default:errno=EIO;break;
    }
    return -1;
}
static wchar_t *wide(const char *s) {
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,NULL,0);
    if(!n){errno=EINVAL;return NULL;}
    wchar_t *w=malloc((size_t)n*sizeof(*w));
    if(!w){errno=ENOMEM;return NULL;}
    if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,w,n)){free(w);errno=EINVAL;return NULL;}
    return w;
}
static HANDLE handle(int fd) { return (HANDLE)_get_osfhandle(fd); }
int kjdb_win_open(const char *s,int flags,...) {
    wchar_t *w=wide(s);if(!w)return -1;
    DWORD access=(flags&O_RDWR)?GENERIC_READ|GENERIC_WRITE:(flags&O_WRONLY)?GENERIC_WRITE:GENERIC_READ;
    if(flags&O_KJDB_RENAME_FILE)access|=DELETE;
    DWORD disposition=(flags&O_CREAT)?((flags&O_EXCL)?CREATE_NEW:((flags&O_TRUNC)?CREATE_ALWAYS:OPEN_ALWAYS)):((flags&O_TRUNC)?TRUNCATE_EXISTING:OPEN_EXISTING);
    DWORD attrs=(flags&O_DIRECTORY)?FILE_FLAG_BACKUP_SEMANTICS:FILE_FLAG_OVERLAPPED|FILE_FLAG_WRITE_THROUGH;
    if(flags&O_NOFOLLOW)attrs|=FILE_FLAG_OPEN_REPARSE_POINT;
    /* Owner-only DACL for newly created DB/backup files. Existing ACLs stay intact. */
    PSECURITY_DESCRIPTOR sd=NULL;
    if((flags&O_CREAT)&&!ConvertStringSecurityDescriptorToSecurityDescriptorW(L"D:P(A;;FA;;;OW)",SDDL_REVISION_1,&sd,NULL)){free(w);return failure(GetLastError());}
    SECURITY_ATTRIBUTES sa={sizeof(sa),sd,FALSE};
    DWORD sharing=FILE_SHARE_READ|FILE_SHARE_WRITE;
    if(!(flags&O_KJDB_PIN_DIRECTORY))sharing|=FILE_SHARE_DELETE;
    HANDLE h=CreateFileW(w,access,sharing,sd?&sa:NULL,disposition,attrs,NULL);
    DWORD error=GetLastError();if(sd)LocalFree(sd);free(w);
    if(h==INVALID_HANDLE_VALUE)return failure(error);
    BY_HANDLE_FILE_INFORMATION info;
    if(GetFileType(h)!=FILE_TYPE_DISK||!GetFileInformationByHandle(h,&info)){error=GetLastError();CloseHandle(h);return failure(error);}
    if(((flags&O_NOFOLLOW)&&(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT))||
       (!!(flags&O_DIRECTORY)!=!!(info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY))){CloseHandle(h);errno=EINVAL;return -1;}
    int fd=_open_osfhandle((intptr_t)h,_O_BINARY|_O_NOINHERIT|((flags&O_RDWR)?_O_RDWR:(flags&O_WRONLY)?_O_WRONLY:_O_RDONLY));
    if(fd<0)CloseHandle(h);return fd;
}
int kjdb_win_fstat(int fd,struct kjdb_win_stat *s) {
    BY_HANDLE_FILE_INFORMATION i;if(!GetFileInformationByHandle(handle(fd),&i))return failure(GetLastError());
    s->st_mode=(i.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)?_S_IFDIR:_S_IFREG;
    s->st_nlink=i.nNumberOfLinks;
    uint64_t size=((uint64_t)i.nFileSizeHigh<<32)|i.nFileSizeLow;
    if(size>INT64_MAX){errno=EOVERFLOW;return -1;}s->st_size=(int64_t)size;return 0;
}
/* Memory-only relative operations. The caller pins the directory against rename;
 * ancestors must be trusted. Publication renames the initialized file handle,
 * keeps its lock, and never replaces an existing memory.log. */
static wchar_t *memory_path(int dirfd,const char *name) {
    if(!name||!*name||strpbrk(name,"/\\:")||!strcmp(name,".")||!strcmp(name,"..")){errno=EINVAL;return NULL;}
    wchar_t *suffix=wide(name);if(!suffix)return NULL;
    DWORD n=GetFinalPathNameByHandleW(handle(dirfd),NULL,0,FILE_NAME_NORMALIZED);
    if(!n){free(suffix);failure(GetLastError());return NULL;}
    size_t extra=wcslen(suffix)+2;
    wchar_t *path=malloc(((size_t)n+extra)*sizeof(*path));
    if(!path){free(suffix);errno=ENOMEM;return NULL;}
    DWORD used=GetFinalPathNameByHandleW(handle(dirfd),path,n,FILE_NAME_NORMALIZED);
    if(!used||used>=n){free(path);free(suffix);errno=EIO;return NULL;}
    if(path[used-1]!=L'\\')path[used++]=L'\\';
    memcpy(path+used,suffix,(wcslen(suffix)+1)*sizeof(*suffix));free(suffix);
    return path;
}
int kjdb_win_memory_openat(int dirfd,const char *name,int flags,...) {
    wchar_t *path=memory_path(dirfd,name);if(!path)return -1;
    int n=WideCharToMultiByte(CP_UTF8,0,path,-1,NULL,0,NULL,NULL);
    if(!n){free(path);errno=EINVAL;return -1;}
    char *utf8=malloc((size_t)n);if(!utf8){free(path);errno=ENOMEM;return -1;}
    if(!WideCharToMultiByte(CP_UTF8,0,path,-1,utf8,n,NULL,NULL)){free(path);free(utf8);errno=EINVAL;return -1;}
    free(path);int fd=kjdb_win_open(utf8,flags);free(utf8);return fd;
}
int kjdb_win_memory_unlinkat(int dirfd,const char *name,int flags) {
    if(flags){errno=EINVAL;return -1;}
    wchar_t *path=memory_path(dirfd,name);if(!path)return -1;
    BOOL ok=DeleteFileW(path);DWORD e=GetLastError();free(path);return ok?0:failure(e);
}
int kjdb_win_memory_publish(int fd,int dirfd,const char *name) {
    wchar_t *path=memory_path(dirfd,name);if(!path)return -1;
    size_t bytes=wcslen(path)*sizeof(*path);
    size_t size=sizeof(FILE_RENAME_INFO)+bytes;
    if(size>MAXDWORD){free(path);errno=EINVAL;return -1;}
    FILE_RENAME_INFO *info=calloc(1,size);if(!info){free(path);errno=ENOMEM;return -1;}
    info->ReplaceIfExists=FALSE;info->FileNameLength=(DWORD)bytes;
    memcpy(info->FileName,path,bytes);free(path);
    BOOL ok=SetFileInformationByHandle(handle(fd),FileRenameInfo,info,(DWORD)size);
    DWORD e=GetLastError();free(info);return ok?0:failure(e);
}
static ssize_t transfer(int fd,void *p,size_t n,int64_t offset,int writing) {
    if(offset<0){errno=EINVAL;return -1;}if(n>MAXDWORD)n=MAXDWORD;
    OVERLAPPED o={0};o.Offset=(DWORD)(uint64_t)offset;o.OffsetHigh=(DWORD)((uint64_t)offset>>32);
    o.hEvent=CreateEventW(NULL,TRUE,FALSE,NULL);if(!o.hEvent)return failure(GetLastError());
    DWORD done=0;BOOL ok=writing?WriteFile(handle(fd),p,(DWORD)n,&done,&o):ReadFile(handle(fd),p,(DWORD)n,&done,&o);
    DWORD error=ok?ERROR_SUCCESS:GetLastError();
    if(!ok&&error==ERROR_IO_PENDING){ok=GetOverlappedResult(handle(fd),&o,&done,TRUE);error=ok?ERROR_SUCCESS:GetLastError();}
    CloseHandle(o.hEvent);if(!ok){if(!writing&&error==ERROR_HANDLE_EOF)return 0;return failure(error);}return (ssize_t)done;
}
ssize_t kjdb_win_pread(int fd,void *p,size_t n,int64_t o){return transfer(fd,p,n,o,0);}
ssize_t kjdb_win_pwrite(int fd,const void *p,size_t n,int64_t o){return transfer(fd,(void *)p,n,o,1);}
int kjdb_win_truncate(int fd,int64_t n) {
    if(n<0){errno=EINVAL;return -1;}FILE_END_OF_FILE_INFO i;i.EndOfFile.QuadPart=n;
    return SetFileInformationByHandle(handle(fd),FileEndOfFileInfo,&i,sizeof(i))?0:failure(GetLastError());
}
int kjdb_win_sync(int fd) {
    BY_HANDLE_FILE_INFORMATION i;if(!GetFileInformationByHandle(handle(fd),&i))return failure(GetLastError());
    /* Explicit experimental contract: Windows has no POSIX directory fsync here.
     * File bytes are flushed; directory-entry power-loss durability is unqualified. */
    if(i.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)return 0;
    return FlushFileBuffers(handle(fd))?0:failure(GetLastError());
}
int kjdb_win_flock(int fd,int op) {
    OVERLAPPED o={0};DWORD flags=(op&LOCK_EX)?LOCKFILE_EXCLUSIVE_LOCK:0;
    if(op&LOCK_NB)flags|=LOCKFILE_FAIL_IMMEDIATELY;
    o.hEvent=CreateEventW(NULL,TRUE,FALSE,NULL);if(!o.hEvent)return failure(GetLastError());
    BOOL ok=LockFileEx(handle(fd),flags,0,MAXDWORD,MAXDWORD,&o);DWORD e=ok?0:GetLastError();
    if(!ok&&e==ERROR_IO_PENDING){DWORD n;ok=GetOverlappedResult(handle(fd),&o,&n,TRUE);e=ok?0:GetLastError();}
    CloseHandle(o.hEvent);return ok?0:failure(e);
}
void *kjdb_win_mmap(void *p,size_t n,int prot,int flags,int fd,int64_t off) {
    if(p||prot!=(PROT_READ|PROT_WRITE)||flags!=(MAP_PRIVATE|MAP_ANONYMOUS)||fd!=-1||off){errno=EINVAL;return MAP_FAILED;}
    void *v=VirtualAlloc(NULL,n,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!v){failure(GetLastError());return MAP_FAILED;}return v;
}
int kjdb_win_munmap(void *p,size_t n){(void)n;return VirtualFree(p,0,MEM_RELEASE)?0:failure(GetLastError());}
char *kjdb_win_strndup(const char *p,size_t n){size_t z=strnlen(p,n);char *s=malloc(z+1);if(s){memcpy(s,p,z);s[z]=0;}return s;}
int kjdb_win_unlink(const char *s){wchar_t *w=wide(s);if(!w)return -1;BOOL ok=DeleteFileW(w);DWORD e=GetLastError();free(w);return ok?0:failure(e);}
int kjdb_win_link(const char *source,const char *dest){wchar_t *s=wide(source),*d=wide(dest);if(!s||!d){free(s);free(d);return -1;}BOOL ok=CreateHardLinkW(d,s,NULL);DWORD e=GetLastError();free(s);free(d);return ok?0:failure(e);}
int kjdb_win_mkstemp(char *p){size_t n=strlen(p);if(n<6||strcmp(p+n-6,"XXXXXX")){errno=EINVAL;return -1;}for(int i=0;i<128;++i){unsigned r;if(rand_s(&r)){errno=EIO;return -1;}snprintf(p+n-6,7,"%06x",r&0xffffffu);int fd=kjdb_win_open(p,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd>=0||errno!=EEXIST)return fd;}errno=EEXIST;return -1;}
int kjdb_win_clock_gettime(int id,struct timespec *t){
    if(id==CLOCK_REALTIME){FILETIME ft;GetSystemTimePreciseAsFileTime(&ft);uint64_t v=((uint64_t)ft.dwHighDateTime<<32)|ft.dwLowDateTime;v-=UINT64_C(116444736000000000);t->tv_sec=(time_t)(v/10000000);t->tv_nsec=(long)(v%10000000)*100;return 0;}
    if(id==CLOCK_MONOTONIC){LARGE_INTEGER c,f;if(!QueryPerformanceCounter(&c)||!QueryPerformanceFrequency(&f))return failure(GetLastError());t->tv_sec=(time_t)(c.QuadPart/f.QuadPart);t->tv_nsec=(long)((long double)(c.QuadPart%f.QuadPart)*1000000000.0L/(long double)f.QuadPart);return 0;}
    errno=EINVAL;return -1;
}
struct kjdb_win_thread { HANDLE handle;void *(*fn)(void *);void *arg,*result; };
static unsigned __stdcall thread_main(void *p){struct kjdb_win_thread *t=p;t->result=t->fn(t->arg);return 0;}
int pthread_create(pthread_t *out,const void *attr,void *(*fn)(void *),void *arg){if(attr)return ENOTSUP;struct kjdb_win_thread *t=calloc(1,sizeof(*t));if(!t)return ENOMEM;t->fn=fn;t->arg=arg;t->handle=(HANDLE)_beginthreadex(NULL,0,thread_main,t,0,NULL);if(!t->handle){free(t);return EAGAIN;}*out=t;return 0;}
int pthread_join(pthread_t t,void **out){if(WaitForSingleObject(t->handle,INFINITE)!=WAIT_OBJECT_0)return EIO;if(out)*out=t->result;CloseHandle(t->handle);free(t);return 0;}
static BOOL CALLBACK once_main(PINIT_ONCE once,PVOID p,PVOID *context){(void)once;(void)context;void (*fn)(void);memcpy(&fn,p,sizeof(fn));fn();return TRUE;}
int pthread_once(pthread_once_t *once,void (*fn)(void)){return InitOnceExecuteOnce(once,once_main,&fn,NULL)?0:EIO;}
