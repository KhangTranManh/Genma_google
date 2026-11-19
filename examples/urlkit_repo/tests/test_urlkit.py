import unittest
from urlkit import append_query


class QueryTests(unittest.TestCase):
    def test_append_single(self):
        self.assertEqual(append_query("https://example.com/path", {"q": "hello world"}),
                         "https://example.com/path?q=hello+world")


if __name__ == "__main__":
    unittest.main()
