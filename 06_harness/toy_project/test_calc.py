import unittest

from calc import average, total


class CalcTest(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([1, 2, 3]), 6)

    def test_average(self):
        self.assertEqual(average([2, 4, 6]), 4)

    def test_average_empty(self):
        self.assertEqual(average([]), 0.0)


if __name__ == "__main__":
    unittest.main()
