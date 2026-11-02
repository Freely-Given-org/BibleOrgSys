import unittest

from BibleOrgSys.OriginalLanguages import Hebrew, Greek

DEBUGGING_THIS_MODULE = False


# Samples borrowed from the module demo texts (Hebrew Daniel 11:11 and Greek Mark 1:1)
HEBREW_SAMPLES = (
    "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה",
    "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו",
    "מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים",
    "",
    "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
)

GREEK_SAMPLES = (
    "Ἀρχὴ τοῦ εὐαγγελίου ˚Ἰησοῦ ˚Χριστοῦ, Υἱοῦ ˚Θεοῦ.",
    "Καθὼς γέγραπται ἐν τῷ Ἠσαΐᾳ τῷ προφήτῃ: “Ἰδοὺ, ἀποστέλλω τὸν ἄγγελόν μου.”",
    "Ἐγένετο Ἰωάννης, ὁ βαπτίζων ἐν τῇ ἐρήμῳ",
    "",
    "λόγος",
)


class HebrewStripTestCase(unittest.TestCase):
    """Characterisation tests capturing the *current* behaviour of Hebrew.py
       strip methods before optimising them."""

    def test_removeCantillationMarks(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeCantillationMarks()
            self.assertIsInstance(result, str)
            for mark in Hebrew.cantillationMarks:
                self.assertNotIn(mark, result)

    def test_removeCantillationMarks_withMeteg(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeCantillationMarks(removeMetegOrSiluq=True)
            for mark in Hebrew.cantillationMarks:
                self.assertNotIn(mark, result)

    def test_removeVowelPointing(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeVowelPointing()
            for point in Hebrew.vowelPoints:
                self.assertNotIn(point, result)

    def test_removeVowelPointing_withMeteg(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeVowelPointing(removeMetegOrSiluq=True)
            for point in Hebrew.vowelPoints:
                self.assertNotIn(point, result)

    def test_removeOtherMarks(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeOtherMarks()
            for mark in Hebrew.otherMarks:
                self.assertNotIn(mark, result)
            self.assertNotIn(Hebrew.metegOrSiluq, result)

    def test_removeOtherMarks_keepSinShinDots(self):
        for text in HEBREW_SAMPLES:
            h = Hebrew.Hebrew(text)
            result = h.removeOtherMarks(removeSinShinDots=False)
            self.assertNotIn(Hebrew.metegOrSiluq, result)
            self.assertNotIn(Hebrew.dageshOrMapiq, result)

    def test_exact_outputs(self):
        """Byte-exact current outputs (golden values) — these must not change."""
        text = HEBREW_SAMPLES[0]
        self.assertEqual(
            Hebrew.Hebrew(text).removeCantillationMarks(),
            "בִּשְׁנַת שָׁלוֹשׁ לְמַלְכוּת יְהוֹיָקִים מֶֽלֶךְ־יְהוּדָה",
        )
        self.assertEqual(
            Hebrew.Hebrew(text).removeVowelPointing(),
            "בּשׁנ֣ת שׁל֔ושׁ למלכ֖וּת יהויק֣ים מֽלך־יהוּד֑ה",
        )
        text2 = HEBREW_SAMPLES[1]
        h = Hebrew.Hebrew(text2)
        resultA = h.removeVowelPointing(removeMetegOrSiluq=True)
        resultB = h.removeOtherMarks(resultA, removeSinShinDots=False)
        self.assertEqual(resultB, "וי֣אמר המ֔לך לאשׁפנ֖ז ר֣ב סריס֑יו")


class GreekStripTestCase(unittest.TestCase):
    """Characterisation tests capturing the *current* behaviour of Greek.py
       strip methods before optimising them."""

    def test_removeAccents(self):
        for text in GREEK_SAMPLES:
            g = Greek.Greek(text)
            result = g.removeAccents()
            self.assertIsInstance(result, str)

    def test_exact_outputs(self):
        """Byte-exact current outputs (golden values) — these must not change."""
        self.assertEqual(
            Greek.Greek("Ἀρχὴ").removeAccents(),
            "Αρχη",
        )
        self.assertEqual(
            Greek.Greek("λόγος").removeAccents(),
            "λογος",
        )
        self.assertEqual(
            Greek.Greek(GREEK_SAMPLES[2]).removeAccents(),
            "Ἐγενετο Ἰωαννης, ο βαπτιζων εν τη ερημω",
        )
        self.assertEqual(Greek.Greek("").removeAccents(), "")

    def test_removeOtherMarks_isIdentity(self):
        # Currently a no-op for all input
        for text in GREEK_SAMPLES:
            self.assertEqual(Greek.Greek(text).removeOtherMarks(), text)


if __name__ == "__main__":
    unittest.main()
