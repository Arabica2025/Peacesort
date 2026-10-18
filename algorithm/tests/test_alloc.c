/* Compile this file alone: inject failures into the implementation's allocator. */
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
static size_t calls, fail_at, live;
static int failing(void) { return ++calls == fail_at; }
static void *test_malloc(size_t n) {
    if (failing()) return NULL;
    void *p = malloc(n); if (p) ++live; return p;
}
static void *test_calloc(size_t n, size_t width) {
    if (failing()) return NULL;
    void *p = calloc(n, width); if (p) ++live; return p;
}
static void *test_realloc(void *p, size_t n) {
    if (failing()) return NULL;
    int was_null = p == NULL;
    void *q = realloc(p, n); if (q && was_null) ++live; return q;
}
static void test_free(void *p) { if (p) { assert(live); --live; } free(p); }
#define malloc test_malloc
#define calloc test_calloc
#define realloc test_realloc
#define free test_free
#include "../src/peacesort.c"
#undef malloc
#undef calloc
#undef realloc
#undef free

int main(void) {
    int64_t data[129], out[129];
    for (size_t i = 0; i < 129; ++i) data[i] = (int64_t)((i * 37) % 129);
    fail_at = 0; calls = 0;
    assert(peacesort(data, 129, out) == 0);
    size_t allocations = calls;
    assert(!live);
    for (size_t f = 1; f <= allocations; ++f) {
        calls = 0; fail_at = f;
        for (size_t i = 0; i < 129; ++i) out[i] = -99;
        assert(peacesort(data, 129, out) == -1 && errno == ENOMEM);
        assert(!live);
        for (size_t i = 0; i < 129; ++i) assert(out[i] == -99);
    }
    size_t total_stream_allocations = 0;
    for (int d = PEACESORT_ASCENDING; d <= PEACESORT_DESCENDING; ++d) {
        fail_at = 0; calls = 0;
        PeacesortIterator *baseline = peacesort_stream_create((PeacesortDirection)d);
        assert(baseline);
        for (size_t i = 0; i < 129; ++i) assert(peacesort_push(baseline, data[i]) == 0);
        assert(peacesort_finish(baseline) == 0);
        size_t stream_allocations = calls;
        peacesort_destroy(baseline); assert(!live);
        /* Retry every possible failed stream allocation without losing input. */
        for (size_t f = 1; f <= stream_allocations; ++f) {
            calls = 0; fail_at = f;
            PeacesortIterator *s = peacesort_stream_create((PeacesortDirection)d);
            if (!s) { assert(errno == ENOMEM); s = peacesort_stream_create((PeacesortDirection)d); }
            assert(s);
            for (size_t i = 0; i < 129; ++i) {
                if (peacesort_push(s, data[i]) < 0) {
                    assert(errno == ENOMEM && s->n == i);
                    assert(peacesort_push(s, data[i]) == 0);
                }
            }
            if (peacesort_finish(s) < 0) { assert(errno == ENOMEM); assert(peacesort_finish(s) == 0); }
            for (size_t i = 0; i < 129; ++i) {
                int64_t x;
                assert(peacesort_next(s, &x) == 1 && x == (int64_t)i);
            }
            peacesort_destroy(s); assert(!live);
        }
        total_stream_allocations += stream_allocations;
    }
    size_t capacity = 0;
    assert(grow(NULL, &capacity, SIZE_MAX, sizeof(int64_t)) == NULL && errno == EOVERFLOW);
    assert(!live);
    printf("PASS: %zu array and %zu stream allocation failure points, retries, overflow and cleanup\n", allocations, total_stream_allocations);
}
