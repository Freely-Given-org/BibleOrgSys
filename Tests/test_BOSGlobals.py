import unittest

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

DEBUGGING_THIS_MODULE = False


class BOSGlobalsTestCase(unittest.TestCase):

    def test_applyStringAdjustments(self):
        longText = "The quick brown fox jumped over the lazy brown dog."
        adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
        result = BibleOrgSysGlobals.applyStringAdjustments( longText, adjustments )
        self.assertEqual( result, "A very quick orange fox tripped over the fat brown dog." )

    def test_makeSafeString(self):
        self.assertEqual( BibleOrgSysGlobals.makeSafeString( '' ), '' )
        self.assertEqual( BibleOrgSysGlobals.makeSafeString( 'OET-RV' ), 'OET-RV' )
        self.assertEqual( BibleOrgSysGlobals.makeSafeString( '<b>bad</b>' ), '_LT_b_GT_bad_LT_/b_GT_' )
        self.assertEqual( BibleOrgSysGlobals.makeSafeString( '<b>bad</b>' ), '_LT_b_GT_bad_LT_/b_GT_' ) # cache hit, same result
        self.assertEqual( BibleOrgSysGlobals.makeSafeString( 'a<b>c' ), 'a_LT_b_GT_c' )

    def test_removeAccents(self):
        self.assertEqual( BibleOrgSysGlobals.removeAccents( '' ), '' )
        self.assertEqual( BibleOrgSysGlobals.removeAccents( 'Matthew' ), 'Matthew' )
        self.assertEqual( BibleOrgSysGlobals.removeAccents( 'éàü' ), 'eau' )
        self.assertEqual( BibleOrgSysGlobals.removeAccents( 'ābrahām' ), 'abraham' )
        self.assertEqual( BibleOrgSysGlobals.removeAccents( 'Ābrahām' ), 'Ābraham' ) # uppercase macron not in ACCENT_DICT
        self.assertEqual( BibleOrgSysGlobals.removeAccents( 'Ælfréd' ), 'AElfred' )
