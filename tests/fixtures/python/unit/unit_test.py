import unittest
import assignment_main


class TestMethods(unittest.TestCase):
    def test_add(self):
        self.assertEqual(assignment_main.add(2, 3), 5)

    def test_multiply(self):
        self.assertEqual(assignment_main.multiply(3, 4), 12)
