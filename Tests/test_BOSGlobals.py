import unittest
import os.path
import sys

sourceFolder = os.path.join( os.path.dirname(__file__), '../BibleOrgSys/' )
if sourceFolder not in sys.path:
    sys.path.append( sourceFolder ) # So we can run it from the above folder and still do these imports

import BibleOrgSysGlobals

class BOSGlobalsTestCase(unittest.TestCase):

    def test_applyStringAdjustments(self):
        longText = "The quick brown fox jumped over the lazy brown dog."
        adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
        result = BibleOrgSysGlobals.applyStringAdjustments( longText, adjustments )
        self.assertEqual( result, "A very quick orange fox tripped over the fat brown dog." )
