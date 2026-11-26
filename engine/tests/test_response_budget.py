import unittest
from group7_auto.android_snapshot import ResponseBudget


class ResponseBudgetTests(unittest.TestCase):
    def test_completed_generation_leaves_independent_progress_budget(self):
        budget = ResponseBudget(0, 120, 120, 15)
        budget.observe(110, True, 'opening')
        budget.observe(115, False, 'opening')
        for now in range(125, 186, 10):
            budget.observe(now, False, str(now))

    def test_still_generating_does_not_extend_generation_limit(self):
        budget = ResponseBudget(0, 120, 120, 15)
        with self.assertRaisesRegex(TimeoutError, 'generation'):
            budget.observe(121, True, 'growing answer')

    def test_stalled_capture_fails_even_with_large_total_budget(self):
        budget = ResponseBudget(0, 120, 120, 15)
        budget.observe(10, False, 'same viewport')
        with self.assertRaisesRegex(TimeoutError, 'progress'):
            budget.observe(26, False, 'same viewport')

    def test_changing_viewports_cannot_extend_capture_forever(self):
        budget = ResponseBudget(0, 120, 30, 15)
        budget.observe(10, False, 'first')
        budget.observe(20, False, 'second')
        budget.observe(30, False, 'third')
        with self.assertRaisesRegex(TimeoutError, 'capture'):
            budget.observe(41, False, 'fourth')
