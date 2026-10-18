"""Peacesort for integers with incremental input and lazy ascending output.

Only the standard library is required. Input must finish before output starts;
all input is retained in memory. Direction controls LC construction, not output.
"""
from __future__ import annotations

import heapq
from collections.abc import Iterable, Iterator
from enum import Enum


class PeacesortDirection(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


PEACESORT_ASCENDING = PeacesortDirection.ASCENDING
PEACESORT_DESCENDING = PeacesortDirection.DESCENDING


class PeacesortStream(Iterator[int]):
    """Create -> push values -> finish -> iterate -> optionally close early.

    Accepts built-in Python integers (arbitrary precision, excluding bool).
    Either direction handles arbitrary input correctly. Matching monotonic
    input needs one LC. Runtime is O(n log(k+1)), with O(n) stored values.
    """

    def __init__(self, direction: PeacesortDirection):
        if not isinstance(direction, PeacesortDirection):
            raise ValueError("direction must be PEACESORT_ASCENDING or PEACESORT_DESCENDING")
        self._direction = direction
        self._runs: list[list[int]] = []
        self._heap: list[tuple[int, int, int]] = []
        self._finished = False
        self._closed = False

    @property
    def direction(self) -> PeacesortDirection:
        return self._direction

    @property
    def lc_count(self) -> int:
        """Number of stored LCs; zero after close()."""
        return len(self._runs)

    def push(self, value: int) -> None:
        """Append one value; reject pushes after finish() or close()."""
        if self._closed or self._finished:
            raise RuntimeError("input is already finished or closed")
        if type(value) is not int:
            raise TypeError("PeacesortStream accepts built-in integers only")
        lo, hi = 0, len(self._runs)
        ascending = self._direction is PEACESORT_ASCENDING
        while lo < hi:
            mid = lo + (hi - lo) // 2
            tail = self._runs[mid][-1]
            skip = tail > value if ascending else tail < value
            if skip:
                lo = mid + 1
            else:
                hi = mid
        if lo == len(self._runs):
            self._runs.append([value])
        else:
            self._runs[lo].append(value)

    def finish(self) -> PeacesortStream:
        """End input and prepare the heap. Repeated calls do not rewind."""
        if self._closed:
            raise RuntimeError("stream is closed")
        if not self._finished:
            descending = self._direction is PEACESORT_DESCENDING
            heap = []
            for run_id, run in enumerate(self._runs):
                offset = len(run) - 1 if descending else 0
                heap.append((run[offset], run_id, offset))
            heapq.heapify(heap)
            self._heap = heap
            self._finished = True
        return self

    def __iter__(self) -> PeacesortStream:
        return self

    def __next__(self) -> int:
        if self._closed:
            raise StopIteration
        if not self._finished:
            raise RuntimeError("finish input before requesting sorted output")
        if not self._heap:
            raise StopIteration
        value, run_id, offset = self._heap[0]
        run = self._runs[run_id]
        offset += -1 if self._direction is PEACESORT_DESCENDING else 1
        if 0 <= offset < len(run):
            heapq.heapreplace(self._heap, (run[offset], run_id, offset))
        else:
            heapq.heappop(self._heap)
        return value

    def close(self) -> None:
        """Release stored values, including after unfinished/partial use."""
        self._heap.clear()
        self._runs.clear()
        self._closed = True


def peacesort_iter(values: Iterable[int], direction: PeacesortDirection = PEACESORT_ASCENDING) -> PeacesortStream:
    """Consume input once now; return an iterator that merges on demand.

    No sampling or input reversal is performed, including for lists. Choose
    direction explicitly when the input distribution is known.
    """
    stream = PeacesortStream(direction)
    try:
        for value in values:
            stream.push(value)
        return stream.finish()
    except BaseException:
        stream.close()
        raise


def peacesort(values: Iterable[int], direction: PeacesortDirection = PEACESORT_ASCENDING) -> list[int]:
    """Return all values sorted ascending, preserving duplicates."""
    stream = peacesort_iter(values, direction)
    try:
        return list(stream)
    finally:
        stream.close()
