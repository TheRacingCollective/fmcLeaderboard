from unittest import TestCase
from leaderboard import calculateResults


class Test(TestCase):

    def test_simple_case(self):
        stageTimes = {'feed': {'entry': []}}
        results, offsets = calculateResults(stageTimes)
        expected_results = '{"data": []}'
        expected_offsets = '{}'
        self.assertEqual(results, expected_results)
        self.assertEqual(offsets, expected_offsets)