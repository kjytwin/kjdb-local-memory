#ifndef KJDB_MEMORY_H
#define KJDB_MEMORY_H
#include <stddef.h>
#include <stdint.h>
typedef struct KJMemory KJMemory;
typedef enum {
    KJM_OK=0, KJM_INVALID, KJM_IO, KJM_CORRUPT, KJM_BUSY,
    KJM_LIMIT, KJM_CONFLICT, KJM_DEGRADED, KJM_RECOVERY_REQUIRED,
    KJM_OUTCOME_UNKNOWN, KJM_NOMEM
} KJMStatus;
/* Linux/POSIX; Windows local preview has file-flush-only durability.
 * Single caller per handle. Separate format from token DB.
 * Payload is bounded UTF-8 supplied by the trusted wrapper. Request digest
 * is SHA256 of canonical caller input, excluding server-generated fields. */
KJMStatus kjm_open(const char *directory, KJMemory **out);
KJMStatus kjm_put(KJMemory *, const char request_id[37],
                 const unsigned char input_digest[32], const void *payload,
                 size_t length, uint64_t *sequence, int *duplicate);
KJMStatus kjm_read(KJMemory *, uint64_t sequence, void *payload,
                  size_t capacity, size_t *length, char request_id[37],
                  unsigned char input_digest[32]);
KJMStatus kjm_state(KJMemory *, uint64_t *count, uint64_t *end, int *degraded, int *tail);
KJMStatus kjm_recover_uncommitted_tail(KJMemory *);
KJMStatus kjm_backup(KJMemory *, const char *new_path);
void kjm_close(KJMemory *);
#ifdef KJM_TESTING
void kjm_test_crash_stage(int stage);
#endif
#endif
