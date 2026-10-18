# Peacesort

Peacesort partitions input into nondecreasing
or nonincreasing subsequences, then merges their smallest remaining values
using a min-heap. Every element is retained.

## Files

- `algorithm/python/peacesort.py`: standard-library-only Python implementation.
- `algorithm/tests/test_python_sort.py`: Python correctness and lifecycle tests.
- `algorithm/src/peacesort.c`: C11 sorting implementation.
- `algorithm/include/peacesort.h`: public C API.
- `algorithm/tests/test_sort.c`: correctness, stream lifecycle, and sampling tests.
- `algorithm/tests/test_alloc.c`: allocation failure, retry, and cleanup tests.
- `demo/peacesort_manim_demo.py`: step-by-step, overview, and Top-K animations.
- `demo/peacesort_manim_interactive_style.py`: configurable four-panel animation.
- `demo/videos/`: rendered videos.
- `demo/pyproject.toml`, `demo/uv.lock`, and `demo/src/`: Python demo environment and package scaffold.

## Algorithm

LC is the term for an internal subsequence.

The C implementation sorts `int64_t` values. It supports incremental input
and lazy sorted output:

```c
PeacesortIterator *it = peacesort_stream_create(PEACESORT_ASCENDING);
if (!it) { /* inspect errno */ return -1; }

/* Repeat as values arrive. A failed push does not consume the value. */
if (peacesort_push(it, 3) < 0 || peacesort_push(it, 1) < 0 || peacesort_push(it, 2) < 0) {
    peacesort_destroy(it);
    return -1;
}

/* Signal end of input before requesting sorted output. */
if (peacesort_finish(it) < 0) {
    peacesort_destroy(it);
    return -1;
}
int64_t value;
int status;
while ((status = peacesort_next(it, &value)) == 1) {
    /* Use value; stop early here if only Top-K output is needed. */
}
peacesort_destroy(it);
if (status < 0) return -1;
```

LC buffers and their descriptor array grow as values arrive. No input length
is required in advance. Each value is copied into a subsequence; all values
remain in memory until destruction. This is not a bounded-memory external sort.
For arbitrary input, a future value can be smaller than every previous value,
so globally sorted output starts only after `peacesort_finish`. Only the merge is lazy.
Destroying an unfinished or partially consumed stream is supported.

For an existing array, `peacesort_create(data, n)` builds and finishes an iterator.
It samples up to 512 evenly distributed elements to choose forward or reverse
insertion, then builds only the selected partition. This is a heuristic, not
a guarantee of the fewest subsequences. Incremental input uses arrival order and the explicit direction passed to
`peacesort_stream_create(PEACESORT_ASCENDING)` or `peacesort_stream_create(PEACESORT_DESCENDING)`.
Ascending mode builds nondecreasing LCs; descending mode builds nonincreasing
LCs and reads them backward during merging. Both modes always output values in
ascending order. The argument is a construction preference, not a promise about
input order: mixed or unexpected input remains correct, but can create more LCs.
Only one candidate partition is stored. Matching monotonic input needs one LC.

`peacesort(data, n, output)` returns `0` on success and `-1` on error; the output
may overlap the input. `peacesort_create` and `peacesort_stream_create` return `NULL` on failure. Errors set `errno`
to `EINVAL`, `ENOMEM`, or `EOVERFLOW`, rather than exiting the process.
`peacesort_next` returns `1` for a value, `0` for exhaustion, and `-1` for invalid use;
use `== 1`, not a truthiness check, when iterating. Failed pushes and finishes
can be retried after allocation failure. Finishing twice does not rewind the
iterator, and pushes after finishing are rejected.

For `n` values and `k` subsequences, partitioning and full merging each take
O(n log(k+1)) time, with O(n) stored values and O(k) metadata. Consuming only
K outputs saves merge work, but still requires ingesting all input. This numeric
implementation does not promise stability for equal-key records.

Compile and run the tests from the workspace root:

```sh
cc -O3 -std=c11 -Wall -Wextra -Wpedantic -Ialgorithm/include \
  algorithm/src/peacesort.c algorithm/tests/test_sort.c \
  -o /tmp/peacesort-test-sort
/tmp/peacesort-test-sort

cc -O2 -std=c11 -Wall -Wextra -Wpedantic -Ialgorithm/include \
  algorithm/tests/test_alloc.c -o /tmp/peacesort-test-alloc
/tmp/peacesort-test-alloc
```

## Python implementation

Requires Python 3.9 or newer and no third-party dependencies. From the workspace
root, import the implementation directly:

```python
from algorithm.python.peacesort import (
    PEACESORT_ASCENDING, PEACESORT_DESCENDING, PeacesortStream, peacesort_iter, peacesort,
)

stream = PeacesortStream(PEACESORT_DESCENDING)
for value in (9, 7, 8, 2, 2):  # Values may arrive incrementally, in any order.
    stream.push(value)
stream.finish()
print(next(stream))  # 2
print(list(stream))  # [2, 7, 8, 9]
stream.close()

print(peacesort([3, 1, 2]))  # [1, 2, 3]

from itertools import islice
output = peacesort_iter((x for x in [9, 4, 7, 1]), PEACESORT_DESCENDING)
print(list(islice(output, 2)))  # [1, 4]; only two merge steps are performed.
output.close()  # Release storage when stopping early.
```

`PeacesortStream` requires an explicit direction. `peacesort_iter` and `peacesort` default to
`PEACESORT_ASCENDING`. Both directions always produce ascending output and preserve
all duplicates. Python integers are arbitrary precision; floats, booleans,
and other non-built-in-integer values are rejected with `TypeError`.

`peacesort_iter` consumes the entire input iterable once before returning; output
merging is lazy. Unlike the C array convenience API, Python convenience functions
do not sample or reverse input: they honor the chosen construction direction.
Use `PeacesortStream.push` when values arrive over time. Calling `next` before `finish`
or pushing after `finish` raises `RuntimeError`. Repeated `finish` calls do not
rewind. `close` releases stored values and is safe before finishing or after
partial consumption. A closed stream is exhausted and cannot accept more input.
Python allocation failures propagate as `MemoryError`.

Run the Python tests from the workspace root:

```sh
python3 -m unittest discover -s algorithm/tests -p 'test_python*.py' -v
```

## Benchmarks

Compare **Peacesort, insertion, bubble, selection, quick, merge, heap, and a
Timsort variant** on identical datasets, measuring full-sort time and key-comparison
counts separately:

```sh
python3 algorithm/benchmarks/compare.py --sizes 100 1000 10000 --repeats 3
```

See [benchmark instructions](algorithm/benchmarks/README.md).
Results are generated in `algorithm/benchmarks/comparison_results/` when you run
the benchmark. Quadratic algorithms default to sizes up to 2,000. The Timsort
variant omits galloping; native `sorted` is a separate baseline.

## Demos

### Algorithm comparison (ManimGL)

```sh
cd demo
uv sync
uv run manimgl peacesort_comparison.py PeacesortComparison
uv run manimgl peacesort_comparison.py PeacesortComparison -w --video_dir videos
uv run manimgl peacesort_comparison.py PeacesortComparisonAll -w --video_dir videos
```

`PeacesortComparison` shows six panels: Peacesort, quick, merge, insertion,
bubble, and selection. `PeacesortComparisonAll` adds descending-LC Peacesort,
heap sort, and the Timsort variant without galloping.

Each panel uses the same input and shared key-comparison budget. Animation speed
represents comparison progress, **not measured execution speed**. Traces come
from the benchmark reference implementations. Yellow marks compared values
(all matching bars for duplicates); LC colors identify subsequences. Green bars
show emitted Peacesort values, temporary merge buffers, or completed output.
Working arrays may contain transient duplicates while insertion shifts a value
held outside the array. Final output is verified against `sorted`.

Configure input and presentation:

```sh
PEACESORT_N=32 PEACESORT_PATTERN=descending PEACESORT_SECONDS=20 \
  uv run manimgl peacesort_comparison.py PeacesortComparisonAll -w --video_dir videos
```

Options: `PEACESORT_N` (4–2,000, default 24), `PEACESORT_PATTERN`
(`random`, `ascending`, `descending`, `near`, `duplicates`, `mixed`),
`PEACESORT_SEED` (default 17), `PEACESORT_FRAMES` (2–600, default 150), and
`PEACESORT_SECONDS` (1–120, default 16). Frame rounding and opening/final holds
make the actual movie slightly longer. Intermediate states may be sampled;
every algorithm's completion state is retained. For large inputs, each displayed
bar is the mean of adjacent values; all values are still sorted. Traces store only
the selected snapshots, keeping memory bounded by the frame budget.

For N=2,000:

```sh
PEACESORT_N=2000 PEACESORT_SECONDS=90 PEACESORT_FRAMES=360 PEACESORT_TIMELINE=focus \
  uv run manimgl peacesort_comparison.py PeacesortComparisonAll -w --video_dir videos --file_name PeacesortComparisonAll_N2000
```

The rendered videos are `demo/videos/PeacesortComparison.mp4` and
`demo/videos/PeacesortComparisonAll.mp4`.

### Peacesort detail scenes

Run the demos from `demo/` using uv and Python 3.12 or newer:

```sh
cd demo
uv sync
uv run manimgl peacesort_manim_demo.py PeacesortStepByStep
uv run manimgl peacesort_manim_demo.py PeacesortOverview -w
uv run manimgl peacesort_manim_demo.py PeacesortTopKDemo
uv run manimgl peacesort_manim_interactive_style.py PeacesortVisualizer
```

Add `-w` to render a video. The four-panel demo accepts environment variables
such as `PEACESORT_N`, `PEACESORT_PATTERN`, `PEACESORT_TOP_K`, `PEACESORT_FRAMES`, and `PEACESORT_SEED`;
see its module docstring for options. The demos use Python implementations to
illustrate the algorithm and do not call the C library.

For large comparisons, `PEACESORT_TIMELINE=focus` (default when N > 96)
allocates 65% of playback time to the early comparison range when algorithm
counts differ by more than 10x. All panels still share the same comparison
budget, but its rate changes between phases. The movie labels this explicitly.
`PEACESORT_HOLD` controls the pause at each completion (default 1 second in
focus mode). Use `PEACESORT_TIMELINE=linear` for constant comparisons per second.
