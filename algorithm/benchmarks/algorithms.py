"""Comparable reference algorithms with explicit key-comparison counting.

Every function returns a new list. These are reference implementations, not
claims about the fastest implementation of each algorithm family.
"""


class Order:
    def __init__(self, count=False):
        self.count = count
        self.comparisons = 0

    def lt(self, a, b):
        if self.count:
            self.comparisons += 1
        return a < b


def insertion_sort(values, order):
    a = list(values)
    for i in range(1, len(a)):
        x, j = a[i], i
        while j and order.lt(x, a[j - 1]):
            a[j] = a[j - 1]
            j -= 1
        a[j] = x
    return a


def bubble_sort(values, order):
    a = list(values)
    end = len(a) - 1
    while end > 0:
        last = 0
        for i in range(end):
            if order.lt(a[i + 1], a[i]):
                a[i], a[i + 1] = a[i + 1], a[i]
                last = i
        end = last
    return a


def selection_sort(values, order):
    a = list(values)
    for i in range(len(a) - 1):
        smallest = i
        for j in range(i + 1, len(a)):
            if order.lt(a[j], a[smallest]):
                smallest = j
        a[i], a[smallest] = a[smallest], a[i]
    return a


def quick_sort(values, order):
    """Iterative median-of-three, three-way partition quicksort."""
    a = list(values)
    pending = [(0, len(a) - 1)]
    while pending:
        lo, hi = pending.pop()
        if lo >= hi:
            continue
        x, y, z = a[lo], a[(lo + hi) // 2], a[hi]
        if order.lt(y, x): x, y = y, x
        if order.lt(z, y): y, z = z, y
        if order.lt(y, x): x, y = y, x
        pivot = y
        left, i, right = lo, lo, hi
        while i <= right:
            if order.lt(a[i], pivot):
                a[left], a[i] = a[i], a[left]
                left += 1
                i += 1
            elif order.lt(pivot, a[i]):
                a[i], a[right] = a[right], a[i]
                right -= 1
            else:
                i += 1
        # Process smaller partition first to limit pending stack size.
        parts = [(lo, left - 1), (right + 1, hi)]
        if parts[0][1] - parts[0][0] < parts[1][1] - parts[1][0]:
            parts.reverse()
        pending.extend(parts)
    return a


def merge(left, right, order):
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if order.lt(right[j], left[i]):
            out.append(right[j]); j += 1
        else:
            out.append(left[i]); i += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out


def merge_sort(values, order):
    """Bottom-up stable mergesort."""
    a = list(values)
    width = 1
    while width < len(a):
        for lo in range(0, len(a), 2 * width):
            a[lo:lo + 2 * width] = merge(a[lo:lo + width], a[lo + width:lo + 2 * width], order)
        width *= 2
    return a


def heap_sort(values, order):
    a = list(values)
    def sift(i, n):
        while 2 * i + 1 < n:
            child = 2 * i + 1
            if child + 1 < n and order.lt(a[child], a[child + 1]): child += 1
            if not order.lt(a[i], a[child]): break
            a[i], a[child] = a[child], a[i]
            i = child
    for i in range(len(a) // 2 - 1, -1, -1): sift(i, len(a))
    for end in range(len(a) - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        sift(0, end)
    return a


def timsort_no_gallop(values, order):
    """Timsort variant: natural runs, minrun, binary insertion, run-stack merge.

    Deliberately omits galloping and merge-boundary trimming; not a performance
    surrogate for production Timsort. See README for the design reference.
    """
    a = list(values)
    n, r = len(a), 0
    while n >= 64:
        r |= n & 1
        n >>= 1
    minrun = n + r
    runs = []
    def merge_at(i):
        runs[i:i + 2] = [merge(runs[i], runs[i + 1], order)]
    start = 0
    while start < len(a):
        end = start + 1
        if end < len(a):
            descending = order.lt(a[end], a[start])
            end += 1
            while end < len(a):
                falling = order.lt(a[end], a[end - 1])
                if falling != descending: break
                end += 1
            if descending:
                a[start:end] = a[start:end][::-1]
        stop = min(len(a), max(end, start + minrun))
        for i in range(end, stop):
            x, lo, hi = a[i], start, i
            while lo < hi:
                mid = (lo + hi) // 2
                if order.lt(x, a[mid]): hi = mid
                else: lo = mid + 1
            a[lo + 1:i + 1] = a[lo:i]
            a[lo] = x
        runs.append(a[start:stop])
        start = stop
        while len(runs) > 1:
            i = len(runs) - 2
            if ((i > 0 and len(runs[i - 1]) <= len(runs[i]) + len(runs[i + 1])) or
                (i > 1 and len(runs[i - 2]) <= len(runs[i - 1]) + len(runs[i]))):
                if len(runs[i - 1]) < len(runs[i + 1]): i -= 1
            elif len(runs[i]) > len(runs[i + 1]):
                break
            merge_at(i)
    while len(runs) > 1:
        i = len(runs) - 2
        if i > 0 and len(runs[i - 1]) < len(runs[i + 1]): i -= 1
        merge_at(i)
    return runs[0] if runs else []


def peacesort_reference(values, order, descending=False):
    """Same LC partition and sift-down merge as the C stream implementation."""
    runs = []
    for x in values:
        lo, hi = 0, len(runs)
        while lo < hi:
            mid = (lo + hi) // 2
            skip = order.lt(runs[mid][-1], x) if descending else order.lt(x, runs[mid][-1])
            if skip: lo = mid + 1
            else: hi = mid
        if lo == len(runs): runs.append([x])
        else: runs[lo].append(x)
    heap = [(run[-1 if descending else 0], i, len(run) - 1 if descending else 0)
            for i, run in enumerate(runs)]
    def less(a, b):
        if order.lt(a[0], b[0]): return True
        if order.lt(b[0], a[0]): return False
        return a[1] < b[1]
    def sift(i):
        while 2 * i + 1 < len(heap):
            child = 2 * i + 1
            if child + 1 < len(heap) and less(heap[child + 1], heap[child]): child += 1
            if not less(heap[child], heap[i]): break
            heap[child], heap[i] = heap[i], heap[child]
            i = child
    for i in range(len(heap) // 2 - 1, -1, -1): sift(i)
    out = []
    while heap:
        x, run_id, offset = heap[0]
        out.append(x)
        offset += -1 if descending else 1
        if 0 <= offset < len(runs[run_id]):
            heap[0] = (runs[run_id][offset], run_id, offset)
        else:
            last = heap.pop()
            if heap: heap[0] = last
        if heap: sift(0)
    return out


def peacesort_descending(values, order):
    return peacesort_reference(values, order, descending=True)


ALGORITHMS = {
    'insertion': insertion_sort, 'bubble': bubble_sort, 'selection': selection_sort,
    'quick_3way': quick_sort, 'merge': merge_sort, 'heap': heap_sort,
    'timsort_no_gallop': timsort_no_gallop,
    'peacesort_ascending': peacesort_reference, 'peacesort_descending': peacesort_descending,
}
QUADRATIC = {'insertion', 'bubble', 'selection'}
