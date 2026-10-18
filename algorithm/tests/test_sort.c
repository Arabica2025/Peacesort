#include "peacesort.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cmp(const void *x, const void *y) {
    int64_t a = *(const int64_t *)x, b = *(const int64_t *)y;
    return (a > b) - (a < b);
}
static uint64_t seed = 17;
static uint64_t rng(void) {
    seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
    return seed;
}
static void drain(PeacesortIterator *it, const int64_t *expected, size_t n) {
    assert(it);
    for (size_t i = 0; i < n; ++i) {
        int64_t x;
        assert(peacesort_next(it, &x) == 1);
        assert(x == expected[i]);
    }
    int64_t x;
    assert(peacesort_next(it, &x) == 0);
    assert(peacesort_finish(it) == 0); /* Does not rewind. */
    assert(peacesort_next(it, &x) == 0);
    peacesort_destroy(it);
}
static void check(const int64_t *a, size_t n) {
    int64_t *expected = malloc((n ? n : 1) * sizeof(*expected));
    int64_t *out = malloc((n ? n : 1) * sizeof(*out));
    assert(expected && out);
    if (n) memcpy(expected, a, n * sizeof(*a));
    qsort(expected, n, sizeof(*expected), cmp);
    assert(peacesort(a, n, out) == 0);
    assert(memcmp(out, expected, n * sizeof(*out)) == 0);
    drain(peacesort_create(a, n), expected, n);
    int64_t x;
    for (int d = PEACESORT_ASCENDING; d <= PEACESORT_DESCENDING; ++d) {
        PeacesortIterator *stream = peacesort_stream_create((PeacesortDirection)d);
        assert(stream);
        assert(peacesort_next(stream, &x) == -1 && errno == EINVAL);
        for (size_t i = 0; i < n; ++i) assert(peacesort_push(stream, a[i]) == 0);
        assert(peacesort_finish(stream) == 0);
        assert(peacesort_push(stream, 42) == -1 && errno == EINVAL);
        drain(stream, expected, n);
        stream = peacesort_stream_create((PeacesortDirection)d);
        assert(stream);
        for (size_t i = 0; i < n; ++i) assert(peacesort_push(stream, a[i]) == 0);
        assert(peacesort_finish(stream) == 0);
        if (n) assert(peacesort_next(stream, &x) == 1 && x == expected[0]);
        peacesort_destroy(stream); /* Partial consumption in both directions. */
    }
    PeacesortIterator *s;
    s = peacesort_create(a, n);
    assert(s);
    if (n) assert(peacesort_next(s, &x) == 1 && x == expected[0]);
    peacesort_destroy(s); /* Early termination. */
    if (n) memcpy(out, a, n * sizeof(*a));
    assert(peacesort(out, n, out) == 0); /* In-place destination. */
    assert(memcmp(out, expected, n * sizeof(*out)) == 0);
    free(expected); free(out);
}
int main(void) {
    check(NULL, 0);
    assert(peacesort(NULL, 0, NULL) == 0);
    int64_t x = 7;
    assert(peacesort_create(NULL, 1) == NULL && errno == EINVAL);
    assert(peacesort_create(&x, SIZE_MAX / sizeof(x) + 1) == NULL && errno == EOVERFLOW);
    assert(peacesort(&x, 1, NULL) == -1 && errno == EINVAL);
    assert(peacesort_next(NULL, &x) == -1 && errno == EINVAL);
    assert(peacesort_push(NULL, x) == -1 && errno == EINVAL);
    assert(peacesort_finish(NULL) == -1 && errno == EINVAL);
    PeacesortIterator *s = peacesort_stream_create(PEACESORT_ASCENDING);
    assert(s && peacesort_push(s, x) == 0);
    peacesort_destroy(s); /* Unfinished input. */
    peacesort_destroy(NULL);
    assert(peacesort_stream_create((PeacesortDirection)99) == NULL && errno == EINVAL);
    for (int d = PEACESORT_ASCENDING; d <= PEACESORT_DESCENDING; ++d) {
        s = peacesort_stream_create((PeacesortDirection)d);
        assert(s);
        for (int64_t i = 0; i < 1024; ++i)
            assert(peacesort_push(s, d == PEACESORT_ASCENDING ? i : 1023 - i) == 0);
        assert(s->k == 1); /* Matching monotonic input needs only one LC. */
        peacesort_destroy(s);
    }

    size_t sizes[] = {1, 2, 3, 7, 8, 9, 127, 128, 129, 199, 200,
                      255, 256, 257, 511, 512, 513, 1024, 4096, 16384};
    size_t count = 1;
    for (size_t z = 0; z < sizeof(sizes) / sizeof(*sizes); ++z) {
        size_t n = sizes[z];
        int64_t *a = malloc(n * sizeof(*a));
        assert(a);
        for (int kind = 0; kind < 9; ++kind) {
            for (size_t i = 0; i < n; ++i) {
                switch (kind) {
                case 0: a[i] = (int64_t)i; break;
                case 1: a[i] = (int64_t)(n - 1 - i); break;
                case 2: a[i] = (int64_t)(rng() % 9) - 4; break;
                case 3: a[i] = (int64_t)(rng() >> 1); if (rng() & 1) a[i] = -a[i]; break;
                case 4: a[i] = (int64_t)((i % 2) ? i - 1 : i + 1); break;
                case 5: a[i] = i % 2 ? INT64_MIN : INT64_MAX; break;
                case 6: a[i] = i < 512 ? (int64_t)i : -(int64_t)i; break;
                case 7: a[i] = i < 512 ? -(int64_t)i : (int64_t)i; break;
                default: a[i] = 42;
                }
            }
            check(a, n); ++count;
        }
        free(a);
    }
    /* Exhaustive small inputs exercise equal tails and small heap shapes. */
    for (size_t n = 1, combinations = 3; n <= 7; ++n, combinations *= 3) {
        int64_t small[7];
        for (size_t code = 0; code < combinations; ++code) {
            size_t digits = code;
            for (size_t i = 0; i < n; ++i) {
                small[i] = (int64_t)(digits % 3) - 1;
                digits /= 3;
            }
            check(small, n); ++count;
        }
    }
    /* Regression: misleading ascending prefix must not dominate selection. */
    int64_t a[4096];
    for (size_t i = 0; i < 4096; ++i) a[i] = i < 512 ? (int64_t)i : -(int64_t)i;
    s = peacesort_create(a, 4096);
    assert(s && s->k == 512);
    peacesort_destroy(s);
    printf("PASS: %zu datasets (array, both stream directions, lazy, in-place), API and sampling checks\n", count);
    return 0;
}
