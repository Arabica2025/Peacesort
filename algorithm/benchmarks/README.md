# Algorithm comparison

This compares Peacesort with insertion, bubble, selection, quick, merge, heap,
and a Timsort variant. It measures **key comparisons** separately from elapsed
time, so the report is about algorithm behavior rather than just C versus Python.

```sh
python3 algorithm/benchmarks/compare.py
python3 algorithm/benchmarks/compare.py --sizes 100 1000 10000 --repeats 7 --warmups 2
python3 algorithm/benchmarks/compare.py --sizes 5000 --quadratic-limit 5000
python3 -m unittest discover -s algorithm/tests -p 'test_benchmark*.py' -v
```

The default run measures N=100, 1,000, and 10,000. Insertion, bubble, and selection
are skipped above N=2,000 by default; increase `--quadratic-limit` to include them.
Skips are recorded, never represented as zero time. Choose `--seed` to explore
other random inputs and `--output` to preserve separate runs.

## What is compared

| Algorithm | Reference variant | Worst-case time | Additional algorithm storage* |
| --- | --- | --- | --- |
| Peacesort ascending/descending | Explicit LC direction, binary placement, lazy heap merge fully consumed | O(n log n) | O(n) |
| Insertion | Shift-based insertion | O(n²) | O(1) |
| Bubble | Early stop with last-swap boundary | O(n²) | O(1) |
| Selection | Repeated minimum selection | O(n²) | O(1) |
| Quick | Median-of-three pivot, three-way partition, iterative stack | O(n²) | O(log n) stack |
| Merge | Bottom-up stable merge | O(n log n) | O(n) |
| Heap | In-place max-heap and sift-down | O(n log n) | O(1) |
| Timsort variant | Natural runs, minrun extension, binary insertion, run-stack merging; no galloping | O(n log n) | O(n) |

*Excludes the common new-result/input-copy storage. All functions return a new
list without changing the input. Native `sorted` is shown as an additional
runtime baseline, not ranked as another pure-Python reference implementation.

The Timsort reference follows the run-based design described in
[CPython 3.10's Timsort design notes](https://github.com/python/cpython/blob/3.10/Objects/listsort.txt).
It deliberately omits galloping and merge-boundary trimming. Its row is named
`timsort_no_gallop`: these results must not be presented as production Timsort
performance. The installed runtime's native sorting behavior/version is separate
and is recorded in metadata.

The Peacesort reference reproduces the C stream partition and heap-merge
structure using explicit `<` comparisons, including deterministic LC-id tie
breaking. It does not replace or modify the production implementation. Both
construction directions are shown on every input; the benchmark does not choose
the faster direction after seeing results. The production C and Python implementations live outside this benchmark module.

## Measurement and interpretation

- Every reference algorithm uses the same `Order.lt` comparison interface.
  An untimed pass counts key `<` calls; timed passes disable counting. Counts
  exclude index checks, key movement, allocation, and LC-id tie breaking.
  Comparing equality through two `<` calls counts twice. These are counts for
  the documented variants, not universal counts for an algorithm family.
- All methods see the same dataset per pattern and size. Patterns include random,
  ascending, descending, duplicates, nearly sorted, mixed-direction, and all equal.
  Identical seeds reproduce data. Method order rotates between repetitions.
- Timing includes full output construction, input copies where used, and internal
  algorithm work. Dataset generation, expected-output generation, verification,
  and destruction of the returned result are outside timing.
- Every output is checked against `sorted`; separate tests cover exhaustive small
  inputs, integer extremes, run boundaries, input preservation, and known counts.
- Defaults are one warmup and three measured repetitions. Reports show median
  timings; CSV also records min/max, raw samples, and comparison counts.
- No benchmark gives a language-independent wall-clock ranking. Shared reference
  code reduces implementation mismatches, while key counts expose algorithmic
  work. Memory access, data movement, allocation, and runtime overhead still
  matter. Native `sorted` has a different implementation cost and no key count.
- This is a full-sort comparison. It does not measure Top-K or external-memory
  streaming, and it does not measure peak memory. Big-O storage above describes
  the algorithms, not observed peak bytes.

## Results

Generated results are excluded from version control. The runner creates
`comparison_results/` (overwritten on the next run):

- `report.md`: comparison tables by input size.
- `summary.csv`: median/min/max time and key counts.
- `raw.csv`: individual measured samples.
- `skipped.csv`: explicit size-limit exclusions.
- `metadata.json`: runtime, parameters, methodology.

Use the tables to identify input-dependent strengths, not to declare one
algorithm universally fastest. Use larger datasets and more seeds/repetitions
to investigate a specific workload.
