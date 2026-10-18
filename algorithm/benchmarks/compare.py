"""Compare sorting algorithm families on identical data and count comparisons."""
from __future__ import annotations
import argparse
import csv
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from algorithm.benchmarks.algorithms import ALGORITHMS, QUADRATIC, Order
PATTERNS = ('random', 'ascending', 'descending', 'duplicates', 'nearly_sorted', 'mixed')


def random_values(seed):
    mask = (1 << 64) - 1
    while True:
        seed ^= (seed << 13) & mask
        seed ^= seed >> 7
        seed ^= (seed << 17) & mask
        yield seed


def dataset(n, pattern, seed):
    rng = random_values(seed)
    if pattern == 'random':
        return [next(rng) % 2000001 - 1000000 for _ in range(n)]
    if pattern == 'descending':
        return list(range(n - 1, -1, -1))
    if pattern == 'duplicates':
        return [next(rng) % 16 - 8 for _ in range(n)]
    if pattern == 'mixed':
        return [i if i < n // 2 else -i for i in range(n)]
    values = list(range(n))
    if pattern == 'nearly_sorted' and n:
        for _ in range(n // 100 + 1):
            x, y = next(rng) % n, next(rng) % n
            values[x], values[y] = values[y], values[x]
    return values



def write_csv(path, rows, fields):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 1000, 10000])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--quadratic-limit', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--output', type=Path, default=ROOT / 'algorithm/benchmarks/comparison_results')
    args = parser.parse_args()
    if min(args.sizes) < 0 or args.repeats < 1 or args.warmups < 0 or args.quadratic_limit < 0 or not 0 < args.seed < 2**64:
        parser.error('Invalid size, repetition count, limit, or seed')
    args.output.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], []
    methods = {**ALGORITHMS, 'native_sorted': lambda values, order: sorted(values)}
    patterns = (*PATTERNS, 'all_equal')
    for n in args.sizes:
        print(f'Comparing algorithms: n={n}', flush=True)
        for pattern in patterns:
            values = [7] * n if pattern == 'all_equal' else dataset(n, pattern, args.seed)
            expected = sorted(values)
            names = []
            for name in methods:
                if name in QUADRATIC and n > args.quadratic_limit:
                    skipped.append({'n': n, 'pattern': pattern, 'algorithm': name,
                                    'reason': 'above quadratic-limit'})
                else:
                    names.append(name)
            # A separate untimed pass measures key comparisons.
            counts = {}
            for name in names:
                order = Order(count=True)
                result = methods[name](values, order)
                if result != expected: raise RuntimeError(f'Incorrect {name}: {pattern}, n={n}')
                counts[name] = order.comparisons if name != 'native_sorted' else ''
            for rep in range(args.warmups + args.repeats):
                offset = rep % len(names)
                for name in names[offset:] + names[:offset]:
                    order = Order()
                    start = time.perf_counter_ns()
                    result = methods[name](values, order)
                    elapsed = (time.perf_counter_ns() - start) / 1e6
                    if result != expected: raise RuntimeError(f'Incorrect {name}: {pattern}, n={n}')
                    del result
                    if rep >= args.warmups:
                        rows.append({'n': n, 'pattern': pattern, 'algorithm': name,
                                     'repeat': rep - args.warmups, 'ms': elapsed,
                                     'key_comparisons': counts[name]})
    fields = ['n', 'pattern', 'algorithm', 'repeat', 'ms', 'key_comparisons']
    write_csv(args.output / 'raw.csv', rows, fields)
    groups = {}
    for row in rows:
        key = (row['n'], row['pattern'], row['algorithm'])
        groups.setdefault(key, []).append(row)
    summary = []
    for (n, pattern, name), samples in groups.items():
        times = [s['ms'] for s in samples]
        summary.append({'n': n, 'pattern': pattern, 'algorithm': name, 'samples': len(times),
                        'median_ms': statistics.median(times), 'min_ms': min(times),
                        'max_ms': max(times), 'key_comparisons': samples[0]['key_comparisons']})
    write_csv(args.output / 'summary.csv', summary, list(summary[0]))
    write_csv(args.output / 'skipped.csv', skipped, ['n', 'pattern', 'algorithm', 'reason'])
    metadata = {'python': sys.version, 'platform': platform.platform(),
                'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'arguments': {**vars(args), 'output': str(args.output)},
                'timing': 'full sort including input copy/output creation; counting disabled',
                'comparison_count': 'separate pass; every key < call; excludes indices and movement',
                'timsort_variant': 'natural runs, minrun, binary insertion, run-stack merge; no galloping',
                'peacesort_variant': 'reference port of C stream LC partition and heap merge, explicit direction',
                'native_sorted': 'separate runtime baseline; not a pure-Python reference implementation'}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    report = ['# Sorting algorithm comparison', '',
              'Median full-sort milliseconds. See `summary.csv` for key-comparison counts.',
              'Reference implementations share a Python harness; timings are not language-independent rankings.',
              '`native_sorted` is a separate native runtime baseline. `timsort_no_gallop` is a Timsort variant.', '']
    for n in args.sizes:
        report += [f'## N = {n}', '', '| Algorithm | ' + ' | '.join(patterns) + ' |',
                   '| --- | ' + ' | '.join(['---:'] * len(patterns)) + ' |']
        for name in methods:
            cells = []
            for pattern in patterns:
                samples = groups.get((n, pattern, name))
                cells.append(f"{statistics.median(s['ms'] for s in samples):.3f}" if samples else 'skipped')
            report.append('| ' + name + ' | ' + ' | '.join(cells) + ' |')
        report.append('')
    (args.output / 'report.md').write_text('\n'.join(report))
    print(f'Verified {len(rows)} measured outputs. Results: {args.output / "report.md"}')


if __name__ == '__main__':
    main()
