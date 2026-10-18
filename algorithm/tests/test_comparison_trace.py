import unittest
from algorithm.benchmarks.algorithms import ALGORITHMS, Order
from demo.comparison_trace import build_trace, dataset, playback_schedule


class ComparisonTraceTests(unittest.TestCase):
    def test_trace_matches_algorithm_and_counts(self):
        for pattern in ('random', 'ascending', 'descending', 'near', 'duplicates', 'mixed'):
            values = dataset(24, pattern, 17)
            for name, algorithm in ALGORITHMS.items():
                with self.subTest(pattern=pattern, algorithm=name):
                    trace = build_trace(name, values)
                    order = Order(True)
                    result = algorithm(values, order)
                    self.assertEqual(trace.comparisons, order.comparisons)
                    self.assertEqual(trace.at(0).values, tuple(values))
                    self.assertEqual(trace.at(trace.comparisons + 1).values, tuple(result))
                    self.assertTrue(trace.at(100000).done)
                    self.assertFalse(trace.at(trace.comparisons).done)
                    self.assertEqual(len(trace.states), trace.comparisons + 2)
                    for state in trace.states:
                        self.assertEqual(len(state.values), len(values))
                        if name.startswith('peacesort'):
                            self.assertEqual(list(state.output), sorted(values)[:len(state.output)])

    def test_sampled_trace_matches_full_states(self):
        values = dataset(65, 'random', 17)
        for name in ALGORITHMS:
            full = build_trace(name, values)
            budgets = [0, 1, 10, 100, full.comparisons, full.comparisons + 1]
            sampled = build_trace(name, values, budgets)
            self.assertLessEqual(len(sampled.states), len(set(budgets)))
            self.assertEqual(sampled.comparisons, full.comparisons)
            for budget in budgets:
                self.assertEqual(sampled.at(budget), full.at(budget))

    def test_focus_schedule(self):
        counts = {'fast': 20000, 'medium': 40000, 'slow': 2000000}
        budgets, times, cutoff = playback_schedule(counts, 360, 90, True)
        self.assertEqual(budgets[0], 0)
        self.assertEqual(budgets[-1], 2000001)
        self.assertAlmostEqual(times[-1], 90)
        self.assertAlmostEqual(times[budgets.index(cutoff)], 58.5)
        self.assertEqual(budgets, sorted(set(budgets)))
        self.assertTrue(all(a < b for a, b in zip(times, times[1:])))
        for count in counts.values(): self.assertIn(count + 1, budgets)

    def test_monotonic_matching_lc(self):
        for name, pattern in (('peacesort_ascending', 'ascending'), ('peacesort_descending', 'descending')):
            trace = build_trace(name, dataset(24, pattern, 17))
            self.assertEqual(max(len(state.runs) for state in trace.states), 1)


if __name__ == '__main__':
    unittest.main()
