"""Held-out demonstration checks; never copied into the agent container."""
import unittest
from urlkit import append_query


class RegressionTests(unittest.TestCase):
    def test_duplicate_existing(self):
        self.assertEqual(append_query("https://example.com/?tag=a&tag=b", {"page": "2"}),
                         "https://example.com/?tag=a&tag=b&page=2")

    def test_blank_value(self):
        self.assertEqual(append_query("https://example.com/?empty=", {"q": "x"}),
                         "https://example.com/?empty=&q=x")

    def test_appended_key_does_not_replace(self):
        self.assertEqual(append_query("https://example.com/?q=old", {"q": "new"}),
                         "https://example.com/?q=old&q=new")

    def test_pairs_preserve_duplicates(self):
        self.assertEqual(append_query("https://example.com/", [("x", "1"), ("x", "2")]),
                         "https://example.com/?x=1&x=2")

    def test_fragment_and_encoding(self):
        self.assertEqual(append_query("https://example.com/a?blank=#section", {"q": "a+b c"}),
                         "https://example.com/a?blank=&q=a%2Bb+c#section")

    def test_no_new_params(self):
        self.assertEqual(append_query("/a?x=1&x=2&blank=#f", []), "/a?x=1&x=2&blank=#f")


if __name__ == "__main__":
    unittest.main(verbosity=2)
