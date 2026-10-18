"""Render-independent comparison traces from the benchmark implementations."""
from dataclasses import dataclass
from bisect import bisect_right
import random
import sys

from algorithm.benchmarks.algorithms import ALGORITHMS, Order

DEFAULT_ALGORITHMS = ('peacesort_ascending', 'quick_3way', 'merge', 'insertion', 'bubble', 'selection')
ALL_ALGORITHMS = tuple(ALGORITHMS)
NAMES = {
    'peacesort_ascending': 'Peacesort / ascending LC',
    'peacesort_descending': 'Peacesort / descending LC',
    'quick_3way': 'Quicksort / 3-way', 'merge': 'Merge sort',
    'insertion': 'Insertion sort', 'bubble': 'Bubble sort',
    'selection': 'Selection sort', 'heap': 'Heap sort',
    'timsort_no_gallop': 'Timsort / no galloping',
}


@dataclass(frozen=True)
class State:
    values: tuple
    compared: tuple = ()
    runs: tuple = ()
    output: tuple = ()
    phase: str = 'Ready'
    done: bool = False


@dataclass
class Trace:
    name: str
    states: list
    comparisons: int
    checkpoints: list = None

    def at(self, budget):
        if self.checkpoints is not None:
            return self.states[max(0, bisect_right(self.checkpoints, budget) - 1)]
        return self.states[min(budget, len(self.states) - 1)]


def dataset(n, pattern, seed):
    rng = random.Random(seed)
    values = list(range(1, n + 1))
    if pattern == 'random': rng.shuffle(values)
    elif pattern == 'descending': values.reverse()
    elif pattern == 'near':
        for _ in range(max(1, n // 12)):
            i, j = rng.randrange(n), rng.randrange(n)
            values[i], values[j] = values[j], values[i]
    elif pattern == 'duplicates': values = [rng.randrange(1, 7) for _ in values]
    elif pattern == 'mixed': values = values[:n // 2] + values[n // 2:][::-1]
    elif pattern != 'ascending': raise ValueError(f'Unknown pattern: {pattern}')
    return values


def build_trace(name, values, snapshot_budgets=None):
    """Snapshot at key comparisons; never use animation time as wall-clock time.

    Frames inspect the actual reference algorithm's working arrays. A merge's
    temporary buffer is displayed separately until it is committed to its array.
    """
    if name not in ALGORITHMS: raise ValueError(f'Unknown algorithm: {name}')
    original = tuple(values)
    states = [State(original)]
    checkpoints = [0]
    selected = None if snapshot_budgets is None else set(snapshot_budgets)
    target_names = {'peacesort_reference' if name.startswith('peacesort_') else ALGORITHMS[name].__name__}

    class TracingOrder(Order):
        def lt(self, a, b):
            self.comparisons += 1
            if selected is not None and self.comparisons not in selected:
                return a < b
            checkpoints.append(self.comparisons)
            frame = sys._getframe(1)
            merge_frame = None
            while frame and frame.f_code.co_name not in target_names:
                if frame.f_code.co_name == 'merge': merge_frame = frame
                frame = frame.f_back
            if frame is None: raise RuntimeError('Cannot locate algorithm frame')
            local = frame.f_locals
            if name.startswith('peacesort_'):
                runs = tuple(tuple(run) for run in local['runs'])
                output = tuple(local.get('out', ()))
                consumed = sum(map(len, runs))
                view = tuple(x for run in runs for x in run) + original[consumed:]
                phase = ('Lazy heap merge' if 'out' in local else 'Build head heap') if 'heap' in local else 'Build LCs / binary search'
            else:
                runs = ()
                view = tuple(local.get('a', original))
                output = tuple(merge_frame.f_locals.get('out', ())) if merge_frame else ()
                phase = 'Merge buffer (not yet committed)' if merge_frame else 'Working array'
                if name == 'timsort_no_gallop' and local.get('runs'):
                    pending = tuple(x for run in local['runs'] for x in run)
                    view = pending + tuple(local['a'][local['start']:])
                    phase = 'Natural runs / merge stack' if not merge_frame else phase
            states.append(State(view, (a, b), runs, output, phase))
            return a < b

    order = TracingOrder(True)
    result = ALGORITHMS[name](values, order)
    if result != sorted(values): raise AssertionError(f'Incorrect {name} output')
    states.append(State(tuple(result), output=tuple(result), phase='Sorted / all values retained', done=True))
    checkpoints.append(order.comparisons + 1)
    return Trace(name, states, order.comparisons, checkpoints if selected is not None else None)


def comparison_counts(names, values):
    """Count first without snapshots, allowing a bounded common frame schedule."""
    counts = {}
    expected = sorted(values)
    for name in names:
        order = Order(True)
        if ALGORITHMS[name](values, order) != expected:
            raise AssertionError(f'Incorrect {name} output')
        counts[name] = order.comparisons
    return counts


def playback_schedule(counts, frames, seconds, focus=False):
    """Shared budget with an optional 65% time allocation to the early phase."""
    end = max(counts.values()) + 1
    early = [count + 1 for count in counts.values() if count + 1 < end / 10]
    cutoff = max(early) if focus and early else end
    def time_at(budget):
        if cutoff == end:
            return seconds * budget / end
        if budget <= cutoff:
            return seconds * .65 * budget / cutoff
        return seconds * (.65 + .35 * (budget - cutoff) / (end - cutoff))
    def budget_at(t):
        if cutoff == end:
            return round(end * t)
        if t <= .65:
            return round(cutoff * t / .65)
        return round(cutoff + (end - cutoff) * (t - .65) / .35)
    budgets = sorted({budget_at(i / (frames - 1)) for i in range(frames)} |
                     {count + 1 for count in counts.values()} | {0, cutoff, end})
    return budgets, [time_at(budget) for budget in budgets], cutoff
