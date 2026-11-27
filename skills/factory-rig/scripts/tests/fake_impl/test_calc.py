import unittest

import calc


class T(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)

    def test_multiply(self):
        self.assertEqual(calc.multiply(4, 5), 20)

    def test_multiply_rejects_floats(self):
        with self.assertRaises(TypeError):
            calc.multiply(1.5, 2)
