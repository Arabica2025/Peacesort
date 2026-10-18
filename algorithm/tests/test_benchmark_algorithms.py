import itertools
import random
import unittest
from algorithm.benchmarks.algorithms import ALGORITHMS, Order
from algorithm.python.peacesort import peacesort, PEACESORT_ASCENDING, PEACESORT_DESCENDING


class AlgorithmTests(unittest.TestCase):
    def check_case(self, values):
        expected = sorted(values)
        original = list(values)
        for name, method in ALGORITHMS.items():
            with self.subTest(algorithm=name, n=len(values)):
                self.assertEqual(method(values, Order()), expected)
                self.assertEqual(method(values, Order(True)), expected)
                self.assertEqual(values, original)
        self.assertEqual(peacesort(values, PEACESORT_ASCENDING), expected)
        self.assertEqual(peacesort(values, PEACESORT_DESCENDING), expected)

    def test_exhaustive(self):
        for n in range(6):
            for values in itertools.product((-1, 0, 1), repeat=n):
                self.check_case(list(values))

    def test_boundaries_and_runs(self):
        rng = random.Random(17)
        for n in (31, 32, 33, 63, 64, 65, 127, 128, 129, 511):
            for values in (list(range(n)), list(range(n))[::-1], [1] * n,
                           [rng.randrange(-1000, 1000) for _ in range(n)],
                           [i if i < n // 2 else -i for i in range(n)]):
                self.check_case(values)
        self.check_case([-(2**200), 2**200, 0, 0, -(2**63), 2**63 - 1])

    def test_known_comparison_counts(self):
        for n in range(20):
            order = Order(True)
            ALGORITHMS['selection'](list(range(n)), order)
            self.assertEqual(order.comparisons, n * (n - 1) // 2)
            for name in ('insertion', 'bubble', 'timsort_no_gallop'):
                order = Order(True)
                ALGORITHMS[name](list(range(n)), order)
                self.assertEqual(order.comparisons, max(0, n - 1))


if __name__ == '__main__':
    unittest.main()
