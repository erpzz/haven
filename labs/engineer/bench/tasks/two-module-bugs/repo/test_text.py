import unittest

from slugify import slugify
from wordcount import top_words


class SlugifyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_trim_without_trailing_hyphen(self):
        self.assertEqual(slugify("Local models can do real engineering work", 20), "local-models-can-do")


class TopWordsTest(unittest.TestCase):
    def test_most_common_first(self):
        self.assertEqual(top_words("b a b c b a", 2), ["b", "a"])

    def test_ties_alphabetical(self):
        self.assertEqual(top_words("x y z", 2), ["x", "y"])


if __name__ == "__main__":
    unittest.main()
