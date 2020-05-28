import unittest
import os.path
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


class BOSGlobalsTestCase(unittest.TestCase):

    def test_applyStringAdjustments(self):
        longText = "The quick brown fox jumped over the lazy brown dog."
        adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
        result = BibleOrgSysGlobals.applyStringAdjustments( longText, adjustments )
        self.assertEqual( result, "A very quick orange fox tripped over the fat brown dog." )
