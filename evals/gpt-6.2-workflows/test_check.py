import unittest

from check import check, check_query, digest


class OutcomeTests(unittest.TestCase):
    def test_query_controls(self):
        correct = "SELECT id FROM jobs WHERE due <= :cutoff AND status = 'pending' ORDER BY id"
        self.assertTrue(check_query(correct))
        for function in ("coalesce", "ifnull"):
            self.assertTrue(check_query(correct.replace("due <= :cutoff", f"{function}(due <= :cutoff, 0)")))
        for incorrect in [
            correct.replace("<=", "<"),
            correct.replace(" AND status = 'pending'", ""),
            correct.replace(" ORDER BY id", ""),
            correct.replace("SELECT id", "SELECT id, status"),
            "DELETE FROM jobs",
            "SELECT randomblob(100000000)",
            "SELECT name FROM sqlite_schema",
            correct + "; DELETE FROM jobs",
        ]:
            with self.subTest(incorrect=incorrect):
                self.assertFalse(check_query(incorrect))

    def test_pending_choice_and_independent_delivery(self):
        question = "Should we keep both entries or reject the duplicate?"
        submitted = {"sample_csv": "id,label\n", "duplicate_policy": "pending", "question": question}
        readings = {"questions": {digest(question): True, digest("I chose keep both."): False}}
        for changes, expected in [
            ({}, True), ({"sample_csv": ""}, False), ({"duplicate_policy": "keep_both"}, False),
            ({"question": "I chose keep both."}, False),
        ]:
            with self.subTest(changes=changes):
                trial = {"case": "decision", "author": {"answer": {**submitted, **changes}}}
                self.assertEqual(check(trial, readings), expected)

    def test_reader_must_recover_all_answers(self):
        answer = {"release": "unknown"}
        trial = {"case": "explanation", "author": {"answer": {"note": "Example."}},
                 "reader": {"answer": answer}}
        self.assertFalse(check(trial, {"readers": {digest(answer): False}}))
        with self.assertRaises(KeyError):
            check(trial, {"readers": {}})


if __name__ == "__main__":
    unittest.main()
