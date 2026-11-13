import unittest

from BibleOrgSys.OriginalLanguages import BibleLexicon

DEBUGGING_THIS_MODULE = False


class BibleLexiconSingletonTestCase(unittest.TestCase):
    def test_getBibleLexicon_isLazySingleton(self) -> None:
        a = BibleLexicon.getBibleLexicon()
        b = BibleLexicon.getBibleLexicon()
        self.assertIs(a, b)

    def test_getBibleLexicon_returnsLexicon(self) -> None:
        lex = BibleLexicon.getBibleLexicon()
        self.assertIsInstance(lex, BibleLexicon.BibleLexicon)


if __name__ == '__main__':
    unittest.main()
