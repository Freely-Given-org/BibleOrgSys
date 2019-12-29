import unittest

import sys
sys.path.append( 'BibleOrgSys/' )

import BibleOrgSysGlobals

class BOSGlobalsTestCase(unittest.TestCase):

    def test_applyStringAdjustments(self):
        longText = "The quick brown fox jumped over the lazy brown dog."
        adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
        result = BibleOrgSysGlobals.applyStringAdjustments( longText, adjustments )
        self.assertEqual( result, "A very quick orange fox tripped over the fat brown dog." )
