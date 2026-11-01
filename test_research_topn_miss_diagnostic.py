import unittest
from scripts.research_topn_miss_diagnostic import classify_miss, summarize_misses


class MissDiagnosticTest(unittest.TestCase):
    def setUp(self):
        self.tickets = ["1-2-3", "1-3-2", "2-1-3", "1-2-4", "2-3-1",
                        "1-4-2", "3-1-2", "2-1-4", "3-2-1", "1-5-2"]

    def test_first_uncovered_prefix(self):
        self.assertEqual(classify_miss(self.tickets, [4, 1, 2]), "first_place_uncovered")
        self.assertEqual(classify_miss(self.tickets, [1, 6, 2]), "second_place_uncovered_given_first")
        self.assertEqual(classify_miss(self.tickets, [1, 2, 5]), "third_place_uncovered_given_first_second")
        self.assertEqual(classify_miss(self.tickets, [1, 2, 3]), "hit")

    def test_topn_classification_and_accounting(self):
        rows = [(self.tickets, [1, 2, 3]), (self.tickets, [1, 2, 4]),
                (self.tickets, [1, 6, 2]), (self.tickets, [4, 1, 2])]
        summary = summarize_misses(rows)
        self.assertEqual([summary["top" + str(n)]["hits"] for n in (3, 5, 10)], [1, 2, 2])
        for item in summary.values():
            self.assertEqual(item["evaluated"], item["hits"] + item["misses"])
            self.assertEqual(item["misses"], item["first_place_uncovered"] +
                             item["second_place_uncovered_given_first"] +
                             item["third_place_uncovered_given_first_second"])

    def test_reject_invalid_data(self):
        for tickets, finish in [(["1-2-3", "1-2-3"], [1, 2, 3]),
                                (["1-1-2"], [1, 2, 3]),
                                (["1-2-3"], [1, 1, 2])]:
            with self.assertRaises(ValueError):
                classify_miss(tickets, finish, min(len(tickets), 2))
        with self.assertRaises(ValueError):
            classify_miss(self.tickets, [1, 2, 3], 0)


if __name__ == "__main__":
    unittest.main()
