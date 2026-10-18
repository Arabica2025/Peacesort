/* Peacesort: C11 LC partitioning followed by a lazy min-heap merge. */
#include "peacesort.h"
#include <errno.h>
#include <stdlib.h>

/* Grow geometrically, checking every allocation-size calculation. */
static void *grow(void *ptr, size_t *capacity, size_t need, size_t width) {
    const size_t limit = SIZE_MAX / width;
    if (need > limit) { errno = EOVERFLOW; return NULL; }
    size_t cap = *capacity;
    if (cap >= need) return ptr;
    if (!cap) cap = limit < 8 ? limit : 8;
    while (cap < need) {
        if (cap > limit / 2) { cap = need; break; }
        cap *= 2;
    }
    void *next = realloc(ptr, cap * width);
    if (!next) { errno = ENOMEM; return NULL; }
    *capacity = cap;
    return next;
}

static void clear_lcs(LC *lcs, size_t k) {
    for (size_t i = 0; i < k; ++i) free(lcs[i].a);
    free(lcs);
}

PeacesortIterator *peacesort_stream_create(PeacesortDirection direction) {
    if (direction != PEACESORT_ASCENDING && direction != PEACESORT_DESCENDING) {
        errno = EINVAL;
        return NULL;
    }
    PeacesortIterator *s = calloc(1, sizeof(*s));
    if (!s) errno = ENOMEM;
    else s->direction = direction;
    return s;
}

int peacesort_push(PeacesortIterator *s, int64_t x) {
    if (!s || s->ready) { errno = EINVAL; return -1; }
    if (s->n >= SIZE_MAX / sizeof(x)) { errno = EOVERFLOW; return -1; }
    size_t lo = 0, hi = s->k;
    /* Ascending runs: first tail <= x; descending runs: first tail >= x. */
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        LC *run = &s->lcs[mid];
        int64_t tail = run->a[run->len - 1];
        if (s->direction == PEACESORT_ASCENDING ? tail > x : tail < x) lo = mid + 1;
        else hi = mid;
    }
    if (lo == s->k) {
        LC *next = grow(s->lcs, &s->lc_capacity, s->k + 1, sizeof(*next));
        if (!next) return -1;
        s->lcs = next;
        LC run = {0};
        run.a = grow(NULL, &run.cap, 1, sizeof(*run.a));
        if (!run.a) return -1;
        run.a[0] = x;
        run.len = 1;
        s->lcs[s->k++] = run;
    } else {
        LC *run = &s->lcs[lo];
        int64_t *next = grow(run->a, &run->cap, run->len + 1, sizeof(*next));
        if (!next) return -1;
        run->a = next;
        run->a[run->len++] = x;
    }
    ++s->n;
    return 0;
}

/* Sample across the array instead of allowing its prefix to dominate. */
static size_t sample_count(const int64_t *a, size_t n, int reverse) {
    int64_t tails[512];
    size_t m = n < 512 ? n : 512, k = 0;
    for (size_t t = 0; t < m; ++t) {
        size_t j = reverse ? m - 1 - t : t;
        size_t index = m == 1 ? 0 :
            ((n - 1) / (m - 1)) * j + ((n - 1) % (m - 1)) * j / (m - 1);
        int64_t x = a[index];
        size_t lo = 0, hi = k;
        while (lo < hi) {
            size_t mid = lo + (hi - lo) / 2;
            if (tails[mid] > x) lo = mid + 1;
            else hi = mid;
        }
        if (lo == k) ++k;
        tails[lo] = x;
    }
    return k;
}

static int less(Head a, Head b) {
    return a.value < b.value || (a.value == b.value && a.id < b.id);
}

static void sift(Head *heap, size_t n, size_t i) {
    while (i < n / 2) {
        size_t child = 2 * i + 1;
        if (child + 1 < n && less(heap[child + 1], heap[child])) ++child;
        if (!less(heap[child], heap[i])) break;
        Head tmp = heap[i]; heap[i] = heap[child]; heap[child] = tmp;
        i = child;
    }
}

int peacesort_finish(PeacesortIterator *s) {
    if (!s) { errno = EINVAL; return -1; }
    if (s->ready) return 0;
    if (s->k > SIZE_MAX / sizeof(*s->heap)) { errno = EOVERFLOW; return -1; }
    if (s->k) {
        s->heap = malloc(s->k * sizeof(*s->heap));
        if (!s->heap) { errno = ENOMEM; return -1; }
    }
    s->hn = s->k;
    for (size_t i = 0; i < s->k; ++i) {
        size_t offset = s->direction == PEACESORT_DESCENDING ? s->lcs[i].len - 1 : 0;
        s->heap[i] = (Head){s->lcs[i].a[offset], i, offset};
    }
    for (size_t i = s->hn / 2; i > 0; --i) sift(s->heap, s->hn, i - 1);
    s->ready = 1;
    return 0;
}

PeacesortIterator *peacesort_create(const int64_t *a, size_t n) {
    if (n > SIZE_MAX / sizeof(*a)) { errno = EOVERFLOW; return NULL; }
    if (n && !a) { errno = EINVAL; return NULL; }
    PeacesortIterator *s = peacesort_stream_create(PEACESORT_ASCENDING);
    if (!s) return NULL;
    int reverse = n > 128 && 3 * sample_count(a, n, 1) < 2 * sample_count(a, n, 0);
    for (size_t i = 0; i < n; ++i) {
        if (peacesort_push(s, a[reverse ? n - 1 - i : i]) < 0) goto fail;
    }
    if (peacesort_finish(s) < 0) goto fail;
    return s;
fail: {
    int error = errno;
    peacesort_destroy(s);
    errno = error;
    return NULL;
}}

int peacesort_next(PeacesortIterator *s, int64_t *out) {
    if (!s || !s->ready || !out) { errno = EINVAL; return -1; }
    if (!s->hn) return 0;
    Head h = s->heap[0];
    *out = h.value;
    int has_next = s->direction == PEACESORT_DESCENDING ? h.offset > 0 :
        h.offset + 1 < s->lcs[h.id].len;
    if (has_next) {
        size_t next = s->direction == PEACESORT_DESCENDING ? h.offset - 1 : h.offset + 1;
        s->heap[0] = (Head){s->lcs[h.id].a[next], h.id, next};
    } else {
        s->heap[0] = s->heap[--s->hn];
    }
    if (s->hn) sift(s->heap, s->hn, 0);
    return 1;
}

void peacesort_destroy(PeacesortIterator *s) {
    if (!s) return;
    clear_lcs(s->lcs, s->k);
    free(s->heap);
    free(s);
}

int peacesort(const int64_t *a, size_t n, int64_t *out) {
    if (n && !out) { errno = EINVAL; return -1; }
    PeacesortIterator *s = peacesort_create(a, n);
    if (!s) return -1;
    for (size_t i = 0; i < n; ++i) peacesort_next(s, &out[i]);
    peacesort_destroy(s);
    return 0;
}
