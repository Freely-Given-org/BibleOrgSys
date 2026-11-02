import unittest

from BibleOrgSys.OriginalLanguages import BibleLexicon

DEBUGGING_THIS_MODULE = False


class BibleLexiconSingletonTestCase(unittest.TestCase):
    def test_getBibleLexicon_isLazySingleton(self):
        a = BibleLexicon.getBibleLexicon()
        b = BibleLexicon.getBibleLexicon()
        self.assertIs(a, b)

    def test_getBibleLexicon_returnsLexicon(self):
        lex = BibleLexicon.getBibleLexicon()
        self.assertIsInstance(lex, BibleLexicon.BibleLexicon)


if __name__ == '__main__':
    unittest.main()
