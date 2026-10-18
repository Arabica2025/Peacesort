import itertools
import random
import unittest

from algorithm.python.peacesort import (
    PEACESORT_ASCENDING, PEACESORT_DESCENDING, PeacesortStream, peacesort_iter, peacesort,
)

DIRECTIONS = (PEACESORT_ASCENDING, PEACESORT_DESCENDING)


class SortTests(unittest.TestCase):
    def check_values(self, values):
        original = list(values)
        expected = sorted(values)
        for direction in DIRECTIONS:
            self.assertEqual(peacesort(values, direction), expected)
            self.assertEqual(peacesort((x for x in values), direction), expected)
            stream = PeacesortStream(direction)
            for value in values:
                stream.push(value)
            stream.finish()
            if expected:
                self.assertEqual(next(stream), expected[0])
                stream.finish()  # Must not rewind after partial consumption.
                self.assertEqual(list(stream), expected[1:])
            else:
                self.assertEqual(list(stream), [])
            stream.finish()
            self.assertEqual(list(stream), [])
        self.assertEqual(values, original)

    def test_exhaustive_small_inputs(self):
        for n in range(8):
            for values in itertools.product((-1, 0, 1), repeat=n):
                self.check_values(list(values))

    def test_distributions_and_boundaries(self):
        rng = random.Random(17)
        for n in (1, 8, 9, 127, 128, 129, 511, 512, 513, 4096, 16384):
            for values in (
                list(range(n)), list(range(n - 1, -1, -1)), [42] * n,
                [rng.randrange(-4, 5) for _ in range(n)],
                [rng.randrange(-(2**63), 2**63) for _ in range(n)],
                [i if i < 512 else -i for i in range(n)],
                [-i if i < 512 else i for i in range(n)],
                [-(2**200) if i % 2 else 2**200 for i in range(n)],
            ):
                self.check_values(values)

    def test_matching_direction_uses_one_lc(self):
        for direction in DIRECTIONS:
            values = list(range(1024))
            if direction is PEACESORT_DESCENDING:
                values.reverse()
            stream = peacesort_iter(values, direction)
            self.assertEqual(stream.lc_count, 1)
            self.assertEqual(list(stream), list(range(1024)))

    def test_lifecycle_and_validation(self):
        for direction in DIRECTIONS:
            stream = PeacesortStream(direction)
            with self.assertRaises(RuntimeError):
                next(stream)
            for invalid in (None, 1.5, float('nan'), '1', True):
                with self.assertRaises(TypeError):
                    stream.push(invalid)
            stream.push(1)
            self.assertEqual(list(stream.finish()), [1])
            with self.assertRaises(RuntimeError):
                stream.push(2)
            stream.close()
            stream.close()
            self.assertEqual(list(stream), [])
            self.assertEqual(stream.lc_count, 0)
            with self.assertRaises(RuntimeError):
                stream.finish()
            with self.assertRaises(RuntimeError):
                stream.push(3)
            unfinished = PeacesortStream(direction)
            unfinished.push(7)
            unfinished.close()
            self.assertEqual(unfinished.lc_count, 0)
        for invalid in (None, 'ascending', 0):
            with self.assertRaises(ValueError):
                PeacesortStream(invalid)

    def test_one_pass_input_and_partial_output(self):
        for direction in DIRECTIONS:
            seen = []
            def source():
                for x in (5, 1, 3, 2, 4):
                    seen.append(x)
                    yield x
            stream = peacesort_iter(source(), direction)
            self.assertEqual(seen, [5, 1, 3, 2, 4])
            self.assertEqual(list(itertools.islice(stream, 2)), [1, 2])
            self.assertEqual(next(stream), 3)
            stream.close()
            self.assertEqual(list(stream), [])

    def test_input_exception_propagates(self):
        def broken():
            yield 3
            raise ValueError('source failed')
        with self.assertRaisesRegex(ValueError, 'source failed'):
            peacesort_iter(broken())


if __name__ == '__main__':
    unittest.main()
