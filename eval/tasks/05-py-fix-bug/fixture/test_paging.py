import unittest

from paging import paginate


class PagingTest(unittest.TestCase):
    def test_first_page(self):
        page = paginate(list(range(25)), page=1, per_page=10)
        self.assertEqual(page.items, list(range(10)))
        self.assertEqual(page.total_pages, 3)
        self.assertTrue(page.has_next)

    def test_partial_last_page_still_counts(self):
        page = paginate(list(range(25)), page=3, per_page=10)
        self.assertEqual(page.items, [20, 21, 22, 23, 24])
        self.assertEqual(page.total_pages, 3)
        self.assertFalse(page.has_next)

    def test_exact_multiple(self):
        page = paginate(list(range(20)), page=2, per_page=10)
        self.assertEqual(page.total_pages, 2)
        self.assertFalse(page.has_next)

    def test_fewer_items_than_one_page(self):
        page = paginate([1, 2, 3], page=1, per_page=10)
        self.assertEqual(page.total_pages, 1)
        self.assertFalse(page.has_next)

    def test_empty_input_has_no_pages(self):
        page = paginate([], page=1, per_page=10)
        self.assertEqual(page.items, [])
        self.assertEqual(page.total_pages, 0)
        self.assertFalse(page.has_next)

    def test_rejects_zero_page(self):
        with self.assertRaises(ValueError):
            paginate([1], page=0)


if __name__ == "__main__":
    unittest.main()
