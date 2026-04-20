import unittest
import assignment_main


class TestMethods(unittest.TestCase):
    def test_add_wrong(self):
        self.assertEqual(assignment_main.add(2, 3), 999)
