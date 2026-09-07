import unittest

from summarize import format_report, read_rows, summarize

CSV = """region,amount
north,10
south,25
east,5
north,15
west,25
"""


class SummarizeTest(unittest.TestCase):
    def setUp(self):
        self.rows = read_rows(CSV)

    def test_totals_sorted_by_size_then_name(self):
        self.assertEqual(
            summarize(self.rows),
            [("north", 25.0), ("south", 25.0), ("west", 25.0), ("east", 5.0)],
        )

    def test_top_limits_the_result(self):
        self.assertEqual(
            summarize(self.rows, top=2), [("north", 25.0), ("south", 25.0)]
        )

    def test_top_none_returns_everything(self):
        self.assertEqual(len(summarize(self.rows, top=None)), 4)

    def test_top_larger_than_the_data_is_harmless(self):
        self.assertEqual(len(summarize(self.rows, top=99)), 4)

    def test_top_zero_returns_nothing(self):
        self.assertEqual(summarize(self.rows, top=0), [])

    def test_report_formatting_unchanged(self):
        self.assertEqual(
            format_report(summarize(self.rows, top=1)), "north\t25.00"
        )


if __name__ == "__main__":
    unittest.main()
