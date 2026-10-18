#ifndef PEACESORT_H
#define PEACESORT_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* LC construction direction, not the final output order. */
typedef enum { PEACESORT_ASCENDING, PEACESORT_DESCENDING } PeacesortDirection;
typedef struct { int64_t *a; size_t len, cap; } LC;
typedef struct { int64_t value; size_t id, offset; } Head;
typedef struct {
    LC *lcs;
    size_t k, n;
    Head *heap;
    size_t hn, lc_capacity;
    int ready;
    PeacesortDirection direction;
} PeacesortIterator;
/* Incremental input: create -> push each value -> finish -> next -> destroy.
 * push/finish return 0 on success, -1 with errno on failure.
 * A failed push does not consume the value; push/finish can be retried after
 * allocation failure. finish is idempotent and does not rewind output.
 * push after finish and next before finish fail with EINVAL.
 * Arbitrary input must finish before any globally sorted output is available.
 * destroy accepts NULL, unfinished streams, and partially consumed iterators.
 * Values are stored in memory; this is not a bounded-memory external sort. */
/* Choose nondecreasing or nonincreasing LCs. Any input order is valid.
 * Descending LCs are read backward; output is always nondecreasing.
 * Invalid direction returns NULL with errno = EINVAL. */
PeacesortIterator *peacesort_stream_create(PeacesortDirection direction);
int peacesort_push(PeacesortIterator *it, int64_t value);
int peacesort_finish(PeacesortIterator *it);

/* All n elements are copied into growing LCs before output begins.
 * NULL data is valid only for n == 0. Returns NULL on error; sets errno
 * to EINVAL, ENOMEM, or EOVERFLOW. Input must contain n readable values.
 * Internal fields are exposed for inspection only; do not modify them. */
PeacesortIterator *peacesort_create(const int64_t *data, size_t n);
/* 1: yielded, 0: exhausted, -1: invalid argument (errno = EINVAL).
 * Use peacesort_next(it, &value) == 1 as the iteration condition. */
int peacesort_next(PeacesortIterator *it, int64_t *value);
void peacesort_destroy(PeacesortIterator *it);
/* out must hold n values; input/output may overlap. Returns 0 on success,
 * -1 on error with errno set. Output is unchanged on allocation failure.
 * NULL data/out are allowed for an empty input. */
int peacesort(const int64_t *data, size_t n, int64_t *out);
#ifdef __cplusplus
}
#endif
#endif
