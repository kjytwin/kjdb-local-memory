#define _GNU_SOURCE
#include "kjdb_memory.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#ifndef _WIN32
#include <sys/random.h>
#include <signal.h>
#else
#define openat kjdb_win_memory_openat
#define unlinkat kjdb_win_memory_unlinkat
#endif
#include <unistd.h>
#define DATA_START UINT64_C(8192)
#define MAX_LOG (UINT64_C(32)*1024*1024)
#define MAX_PAYLOAD 16384u
#define MAX_OPERATIONS 8192u
#define FRAME_SIZE 128u
typedef struct { uint64_t offset; uint32_t length; char request[37]; unsigned char digest[32]; } Entry;
struct KJMemory { int fd, slot, degraded, tail, poisoned; uint64_t generation, end, count; Entry *entries; };
#ifdef KJM_TESTING
#ifdef _WIN32
static volatile LONG crash_stage;
void kjm_test_crash_stage(int stage) { InterlockedExchange(&crash_stage,(LONG)stage); }
static int test_stage(void) { return (int)InterlockedCompareExchange(&crash_stage,0,0); }
#else
static int crash_stage;
void kjm_test_crash_stage(int stage) { crash_stage=stage; }
static int test_stage(void) { return crash_stage; }
#endif
static void crash(int stage) {
    if(test_stage()==stage) {
#ifdef _WIN32
        /* Testing only: another Python thread releases this publication barrier. */
        if(stage==12) { while(test_stage()==12)Sleep(1); return; }
#else
        if(stage==12) { raise(SIGSTOP); return; }
#endif
        _exit(90+stage);
    }
}
#else
static void crash(int stage) { (void)stage; }
#endif
static uint32_t crc(const unsigned char *p,size_t n) {
    uint32_t x=~UINT32_C(0);
    for(size_t i=0;i<n;i++){ x^=p[i]; for(int j=0;j<8;j++) x=(x>>1)^((0u-(x&1u))&UINT32_C(0xedb88320)); }
    return ~x;
}
static uint32_t u32(const unsigned char *p) { uint32_t x=0;for(int i=3;i>=0;i--)x=(x<<8)|p[i];return x; }
static uint64_t u64(const unsigned char *p) { uint64_t x=0;for(int i=7;i>=0;i--)x=(x<<8)|p[i];return x; }
static void w32(unsigned char *p,uint32_t x){for(int i=0;i<4;i++){p[i]=(unsigned char)x;x>>=8;}}
static void w64(unsigned char *p,uint64_t x){for(int i=0;i<8;i++){p[i]=(unsigned char)x;x>>=8;}}
static int exact(int fd,void *buffer,size_t n,uint64_t offset,int writing) {
    unsigned char *p=buffer;
    while(n){ssize_t z=writing?pwrite(fd,p,n,(off_t)offset):pread(fd,p,n,(off_t)offset);
        if(z<0&&errno==EINTR)continue;
        if(z==0)return writing?-1:1;
        if(z<0)return -1;
        p+=(size_t)z;n-=(size_t)z;offset+=(uint64_t)z;
    } return 0;
}
static int syncfd(int fd){int r;do{r=fsync(fd);}while(r<0&&errno==EINTR);return r;}
static int uuid(const char *s) {
    if(!s||strlen(s)!=36)return 0;
    for(int i=0;i<36;i++){
        if(i==8||i==13||i==18||i==23){if(s[i]!='-')return 0;}
        else if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;
    } return 1;
}
static int utf8(const unsigned char *s,size_t n) {
    for(size_t i=0;i<n;){
        unsigned a=s[i++];if(a<128)continue;
        unsigned need,minimum,value;
        if(a>=0xc2&&a<=0xdf){need=1;minimum=0x80;value=a&31;}
        else if(a>=0xe0&&a<=0xef){need=2;minimum=0x800;value=a&15;}
        else if(a>=0xf0&&a<=0xf4){need=3;minimum=0x10000;value=a&7;}
        else return 0;
        if(n-i<need)return 0;
        for(unsigned j=0;j<need;j++){unsigned b=s[i++];if((b&0xc0)!=0x80)return 0;value=(value<<6)|(b&63);}
        if(value<minimum||value>0x10ffff||(value>=0xd800&&value<=0xdfff))return 0;
    } return 1;
}
static void checkpoint(unsigned char b[64],uint64_t generation,uint64_t end,uint64_t count) {
    memset(b,0,64);memcpy(b,"KJMEM001",8);w32(b+8,1);w64(b+16,generation);
    w64(b+24,end);w64(b+32,count);w64(b+40,MAX_LOG);w32(b+48,MAX_PAYLOAD);
    w32(b+56,crc(b,56));
}
static int valid_checkpoint(const unsigned char b[64]) {
    if(memcmp(b,"KJMEM001",8)||u32(b+8)!=1||u32(b+12)||u64(b+40)!=MAX_LOG||
       u32(b+48)!=MAX_PAYLOAD||u32(b+52)||u32(b+60)||u32(b+56)!=crc(b,56))return 0;
    uint64_t count=u64(b+32),end=u64(b+24);
    return count<=MAX_OPERATIONS&&u64(b+16)==count&&end>=DATA_START&&end<=MAX_LOG;
}
static KJMStatus load(KJMemory *m,const struct stat *st) {
    unsigned char slots[2][64];
    if(exact(m->fd,slots[0],64,0,0)||exact(m->fd,slots[1],64,4096,0))return KJM_CORRUPT;
    int a=valid_checkpoint(slots[0]),b=valid_checkpoint(slots[1]);
    if(!a&&!b)return KJM_CORRUPT;
    m->degraded=!(a&&b);
    m->slot=(!a||(b&&u64(slots[1]+16)>u64(slots[0]+16)))?1:0;
    unsigned char *selected=slots[m->slot];
    m->generation=u64(selected+16);m->end=u64(selected+24);m->count=u64(selected+32);
    if(a&&b){
        uint64_t ga=u64(slots[0]+16),gb=u64(slots[1]+16);
        if((ga>gb?ga-gb:gb-ga)>1)return KJM_CORRUPT;
        if(ga==gb&&memcmp(slots[0],slots[1],64))return KJM_CORRUPT;
        unsigned char *older=slots[1-m->slot];
        if(u64(older+24)>m->end)return KJM_CORRUPT;
    }
    if(st->st_size<0||(uint64_t)st->st_size<m->end)return KJM_CORRUPT;
    m->tail=(uint64_t)st->st_size>m->end;
    m->entries=calloc(MAX_OPERATIONS,sizeof(Entry));if(!m->entries)return KJM_NOMEM;
    uint64_t offset=DATA_START;
    for(uint64_t i=0;i<m->count;i++){
        unsigned char frame[FRAME_SIZE],payload[MAX_PAYLOAD];
        if(offset>m->end||m->end-offset<FRAME_SIZE||exact(m->fd,frame,FRAME_SIZE,offset,0))return KJM_CORRUPT;
        uint32_t len=u32(frame+16);
        if(memcmp(frame,"KJMFRAME",8)||u64(frame+8)!=i+1||!len||len>MAX_PAYLOAD||
           (uint64_t)len>m->end-offset-FRAME_SIZE)return KJM_CORRUPT;
        for(unsigned j=92;j<FRAME_SIZE;j++)if(frame[j])return KJM_CORRUPT;
        uint32_t checksum=u32(frame+20);w32(frame+20,0);
        if(checksum!=crc(frame,FRAME_SIZE))return KJM_CORRUPT;
        Entry *e=&m->entries[i];memcpy(e->request,frame+24,36);e->request[36]=0;
        if(!uuid(e->request))return KJM_CORRUPT;
        for(uint64_t j=0;j<i;j++)if(!strcmp(e->request,m->entries[j].request))return KJM_CORRUPT;
        memcpy(e->digest,frame+60,32);e->offset=offset;e->length=len;
        if(exact(m->fd,payload,len,offset+FRAME_SIZE,0)||!utf8(payload,len))return KJM_CORRUPT;
        /* Payload checksum is included as a four-byte trailer. */
        unsigned char trailer[4];
        if(m->end-offset-FRAME_SIZE-len<4||exact(m->fd,trailer,4,offset+FRAME_SIZE+len,0)||u32(trailer)!=crc(payload,len))return KJM_CORRUPT;
        offset+=FRAME_SIZE+len+4;
    }
    return offset==m->end?KJM_OK:KJM_CORRUPT;
}
/* Publish a fully initialized, locked inode without replacing an existing store.
 * Interrupted unpublished files are evidence, never candidates for recovery. */
static int create_store(int dirfd,int *locked) {
    unsigned long long nonce;
#ifdef _WIN32
    unsigned int high,low;
    if(rand_s(&high)||rand_s(&low)){errno=EIO;return -1;}
    nonce=((unsigned long long)high<<32)|low;
#else
    ssize_t n;
    do { n=getrandom(&nonce,sizeof(nonce),0); } while(n<0&&errno==EINTR);
    if(n!=(ssize_t)sizeof(nonce))return -1;
#endif
    char name[64];
    snprintf(name,sizeof(name),".memory.init.%016llx",nonce);
    int flags=O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC;
#ifdef _WIN32
    flags|=O_KJDB_RENAME_FILE;
#endif
    int fd=openat(dirfd,name,flags,0600);
    if(fd<0)return -1;
    crash(5);
    int published=0;
    unsigned char b[64];checkpoint(b,0,DATA_START,0);
    if(flock(fd,LOCK_EX|LOCK_NB)||ftruncate(fd,(off_t)DATA_START))goto fail;
    crash(6);
    if(exact(fd,b,64,0,1))goto fail;
    crash(7);
    if(exact(fd,b,64,4096,1))goto fail;
    crash(8);
    if(syncfd(fd))goto fail;
    crash(9);crash(12);
#ifdef _WIN32
    if(kjdb_win_memory_publish(fd,dirfd,"memory.log")) {
#else
    if(renameat2(dirfd,name,dirfd,"memory.log",RENAME_NOREPLACE)) {
#endif
        int collision=errno==EEXIST;
        close(fd);(void)unlinkat(dirfd,name,0);
        if(collision)return openat(dirfd,"memory.log",O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
        return -1;
    }
    published=1;*locked=1;crash(10);
    return fd;
fail:
    close(fd);
    if(!published)(void)unlinkat(dirfd,name,0);
    return -1;
}
KJMStatus kjm_open(const char *directory,KJMemory **out) {
    if(!directory||!*directory||!out)return KJM_INVALID;
    *out=NULL;
    int directory_flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC;
#ifdef _WIN32
    directory_flags|=O_KJDB_PIN_DIRECTORY;
#endif
    int dirfd=open(directory,directory_flags);
    if(dirfd<0)return KJM_IO;
    int locked=0;
    int fd=openat(dirfd,"memory.log",O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0&&errno==ENOENT)fd=create_store(dirfd,&locked);
    if(fd<0){close(dirfd);return KJM_IO;}
    if(!locked&&flock(fd,LOCK_EX|LOCK_NB)){KJMStatus s=(errno==EWOULDBLOCK||errno==EAGAIN)?KJM_BUSY:KJM_IO;close(fd);close(dirfd);return s;}
    struct stat st;
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_nlink!=1){close(fd);close(dirfd);return KJM_INVALID;}
    /* A prior creator may have died after rename but before directory fsync. */
    if(syncfd(dirfd)){close(fd);close(dirfd);return KJM_IO;}
    crash(11);
    KJMemory *m=calloc(1,sizeof(*m));if(!m){close(fd);close(dirfd);return KJM_NOMEM;}
    m->fd=fd;
    KJMStatus status=load(m,&st);
    close(dirfd);
    if(status!=KJM_OK){kjm_close(m);return status;}
    *out=m;return KJM_OK;
}
KJMStatus kjm_put(KJMemory *m,const char request_id[37],const unsigned char digest[32],
                  const void *payload,size_t len,uint64_t *sequence,int *duplicate) {
    if(!m||!uuid(request_id)||!digest||!payload||!len||len>MAX_PAYLOAD||
       !utf8(payload,len)||!sequence||!duplicate)return KJM_INVALID;
    *sequence=0;*duplicate=0;
    if(m->poisoned)return KJM_OUTCOME_UNKNOWN;
    for(uint64_t i=0;i<m->count;i++)if(!strcmp(m->entries[i].request,request_id)){
        if(memcmp(digest,m->entries[i].digest,32))return KJM_CONFLICT;
        *sequence=i+1;*duplicate=1;return KJM_OK;
    }
    if(m->degraded)return KJM_DEGRADED;
    if(m->tail)return KJM_RECOVERY_REQUIRED;
    if(m->count>=MAX_OPERATIONS||FRAME_SIZE+len+4>MAX_LOG-m->end)return KJM_LIMIT;
    unsigned char frame[FRAME_SIZE]={0},trailer[4],cp[64];
    memcpy(frame,"KJMFRAME",8);w64(frame+8,m->count+1);w32(frame+16,(uint32_t)len);
    memcpy(frame+24,request_id,36);memcpy(frame+60,digest,32);w32(frame+20,crc(frame,FRAME_SIZE));
    w32(trailer,crc(payload,len));
    m->poisoned=1;
    if(exact(m->fd,frame,FRAME_SIZE,m->end,1)||exact(m->fd,(void *)payload,len,m->end+FRAME_SIZE,1)||
       exact(m->fd,trailer,4,m->end+FRAME_SIZE+len,1))return KJM_OUTCOME_UNKNOWN;
    crash(1);
    if(syncfd(m->fd))return KJM_OUTCOME_UNKNOWN;
    crash(2);
    uint64_t end=m->end+FRAME_SIZE+len+4;int slot=1-m->slot;
    checkpoint(cp,m->generation+1,end,m->count+1);
#ifdef KJM_TESTING
    if(test_stage()==3){(void)exact(m->fd,cp,32,(uint64_t)slot*4096,1);(void)syncfd(m->fd);crash(3);}
#endif
    if(exact(m->fd,cp,64,(uint64_t)slot*4096,1)||syncfd(m->fd))return KJM_OUTCOME_UNKNOWN;
    crash(4);
    Entry *e=&m->entries[m->count];e->offset=m->end;e->length=(uint32_t)len;
    memcpy(e->request,request_id,37);memcpy(e->digest,digest,32);
    m->count++;m->generation++;m->end=end;m->slot=slot;m->poisoned=0;
    *sequence=m->count;return KJM_OK;
}
KJMStatus kjm_read(KJMemory *m,uint64_t sequence,void *payload,size_t cap,size_t *len,
                   char request_id[37],unsigned char digest[32]) {
    if(!m||!sequence||sequence>m->count||!payload||!len||!request_id||!digest)return KJM_INVALID;
    Entry *e=&m->entries[sequence-1];*len=e->length;
    if(cap<e->length)return KJM_LIMIT;
    unsigned char trailer[4];
    int read_status=exact(m->fd,payload,e->length,e->offset+FRAME_SIZE,0);
    if(!read_status)read_status=exact(m->fd,trailer,4,e->offset+FRAME_SIZE+e->length,0);
    if(read_status)return read_status>0?KJM_CORRUPT:KJM_IO;
    if(u32(trailer)!=crc(payload,e->length))return KJM_CORRUPT;
    memcpy(request_id,e->request,37);memcpy(digest,e->digest,32);return KJM_OK;
}
KJMStatus kjm_state(KJMemory *m,uint64_t *count,uint64_t *end,int *degraded,int *tail) {
    if(!m||!count||!end||!degraded||!tail)return KJM_INVALID;
    *count=m->count;*end=m->end;*degraded=m->degraded;*tail=m->tail;return KJM_OK;
}
KJMStatus kjm_recover_uncommitted_tail(KJMemory *m) {
    if(!m)return KJM_INVALID;
    if(m->poisoned)return KJM_OUTCOME_UNKNOWN;
    if(m->degraded)return KJM_DEGRADED;
    if(!m->tail)return KJM_OK;
    if(ftruncate(m->fd,(off_t)m->end)||syncfd(m->fd)){m->poisoned=1;return KJM_OUTCOME_UNKNOWN;}
    m->tail=0;return KJM_OK;
}
KJMStatus kjm_backup(KJMemory *m,const char *path) {
    if(!m||!path||!*path)return KJM_INVALID;
    if(m->poisoned)return KJM_OUTCOME_UNKNOWN;
    if(m->degraded)return KJM_DEGRADED;
    char *parent=strdup(path);if(!parent)return KJM_NOMEM;
    char *slash=strrchr(parent,'/');
#ifdef _WIN32
    char *backslash=strrchr(parent,'\\');
    if(backslash&&(!slash||backslash>slash))slash=backslash;
#endif
    if(slash){if(slash==parent||(slash==parent+2&&parent[1]==':'))slash[1]=0;else *slash=0;}else{free(parent);parent=strdup(".");}
    if(!parent)return KJM_NOMEM;
    int dirfd=open(parent,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);free(parent);
    if(dirfd<0)return KJM_IO;
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if(fd<0){close(dirfd);return KJM_IO;}
    KJMStatus status=KJM_OK;unsigned char buffer[16384];
    for(uint64_t at=0;at<m->end;){
        size_t n=(size_t)(m->end-at);if(n>sizeof(buffer))n=sizeof(buffer);
        if(exact(m->fd,buffer,n,at,0)||exact(fd,buffer,n,at,1)){status=KJM_OUTCOME_UNKNOWN;break;}at+=n;
    }
    if(status==KJM_OK&&(syncfd(fd)||syncfd(dirfd)))status=KJM_OUTCOME_UNKNOWN;
    close(fd);close(dirfd);return status;
}
void kjm_close(KJMemory *m){if(m){if(m->fd>=0)close(m->fd);free(m->entries);free(m);}}
