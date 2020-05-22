#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleReferencesTests.py
#   Last modified: 2014-12-15 by RJH (also update PROGRAM_VERSION below)
#
# Module testing BibleReferences.py
#
# Copyright (C) 2012-2014 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module testing BibleReferences.py.
"""

LAST_MODIFIED_DATE = '2020-04-06' # by RJH
PROGRAM_NAME = "Bible References tests"
PROGRAM_VERSION = '0.25'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import unittest
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint
from BibleOrgSys.Reference import BibleBooksCodes
from BibleOrgSys.Reference import BibleOrganisationalSystems
from BibleOrgSys.Reference import BibleReferences


class BibleReferencesTests( unittest.TestCase ):
    """ Unit tests for the BibleReferences object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the BibleOrganisationalSystems objects
        self.BOS = BibleOrganisationalSystems.BibleOrganisationalSystem( "RSV" )

    def test_100_BibleSingleReference( self ):
        """ Test the BibleSingleReference function. """
        BSR = BibleReferences.BibleSingleReference( self.BOS )
        result = str( BSR )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
        #vPrint( 'Quiet', debuggingThisModule, "\nSingle Reference (good)" )
        for goodRef in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b", \
                        "Mat.7:0","Mt. 7:3","1Cor 1:1","1 Cor 1:2", "II Cor 1:3", "IICor 1:4","ISA 1:5",):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRef ) )
            result = BSR.parseReferenceString( goodRef )
            #vPrint( 'Quiet', debuggingThisModule, goodRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 6 )
            self.assertEqual( result[0], True ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], str ) ) # Book code
            self.assertEqual( len(result[2]), 3 )
            self.assertTrue( isinstance( result[3], str ) ) # Chapter number
            self.assertTrue( 1 <= len(result[3]) <= 3 )
            self.assertTrue( isinstance( result[4], str ) ) # Verse number
            self.assertTrue( 1 <= len(result[4]) <= 3 )
            self.assertTrue( isinstance( result[5], str ) ) # Verse suffix
            self.assertTrue( 0 <= len(result[5]) <= 1 )
        for badRef in ("Mut 7:3","Mat.7777:3","Mat. 7:3333","Mta 7:3","Mt-7:3","Jde 77","Jde. 77","Jde 11:7","Jde. 2:7","Jab 8:4","Jobs. 8:4","Job88:4","Job  8:444","Lev. 8:4bc", \
                        "Mat 0:3","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( badRef ) )
            result = BSR.parseReferenceString( badRef )
            #vPrint( 'Quiet', debuggingThisModule, badRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 6 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( result[2] is None or isinstance( result[2], str ) ) # Book code
            self.assertTrue( isinstance( result[3], str ) ) # Chapter number
            #self.assertTrue( 1 <= len(result[3]) <= 3 )
            self.assertTrue( isinstance( result[4], str ) ) # Verse number
            #self.assertTrue( 1 <= len(result[4]) <= 3 )
            self.assertTrue( isinstance( result[5], str ) ) # Verse suffix
            #self.assertTrue( 0 <= len(result[5]) <= 1 )
        for goodRefs in ("Mat. 7:3,7","Mat. 7:3; 4:7","Mat. 7:3,7; 4:7","Mat. 7:3,7; 4:7,9,11","Mat. 7:3; Heb. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2,9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4:4,7; Rev. 1:1; 1:1","Mrk. 7:3a,7b,8"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRefs ) )
            result = BSR.parseReferenceString( goodRefs )
            #vPrint( 'Quiet', debuggingThisModule, goodRefs, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 6 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( result[2] is None or isinstance( result[2], str ) ) # Book code
            self.assertTrue( isinstance( result[3], str ) ) # Chapter number
            #self.assertTrue( 1 <= len(result[3]) <= 3 )
            self.assertTrue( isinstance( result[4], str ) ) # Verse number
            #self.assertTrue( 1 <= len(result[4]) <= 3 )
            self.assertTrue( isinstance( result[5], str ) ) # Verse suffix
            #self.assertTrue( 0 <= len(result[5]) <= 1 )
    # end of test_100_BibleSingleReference

    def test_200_BibleSingleReferences( self ):
        """ Test the BibleSingleReferences function. """
        BSRs = BibleReferences.BibleSingleReferences( self.BOS )
        result = str( BSRs )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
        #vPrint( 'Quiet', debuggingThisModule, "\nSingle References (good)" )
        for goodRef in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b", \
                        "Mat.7:0","Mt. 7:3","1Cor 1:1","1 Cor 1:2", "II Cor 1:3", "IICor 1:4","ISA 1:5",):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRef ) )
            result = BSRs.parseReferenceString( goodRef )
            #vPrint( 'Quiet', debuggingThisModule, goodRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], True ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertEqual( len(result[2]), 1 )
            self.assertEqual( len(result[2][0]), 4 ) # Book, chap, vrs, suffix
            self.assertTrue( isinstance( result[2][0][0], str ) ) # Book code
            self.assertEqual( len(result[2][0][0]), 3 )
            self.assertTrue( isinstance( result[2][0][1], str ) ) # Chapter number
            self.assertTrue( 1 <= len(result[2][0][1]) <= 3 )
            self.assertTrue( isinstance( result[2][0][2], str ) ) # Verse number
            self.assertTrue( 1 <= len(result[2][0][2]) <= 3 )
            self.assertTrue( isinstance( result[2][0][3], str ) ) # Verse suffix
            self.assertTrue( 0 <= len(result[2][0][3]) <= 1 )
        for badRef in ("Mut 7:3","Mat.7777:3","Mat. 7:3333","Mta 7:3","Mt-7:3","Jde 77","Jde. 77","Jde 11:7","Jde. 2:7","Jab 8:4","Jobs. 8:4","Job88:4","Job  8:444","Lev. 8:4bc", \
                        "Mat 0:3","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( badRef ) )
            result = BSRs.parseReferenceString( badRef )
            #vPrint( 'Quiet', debuggingThisModule, badRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 0 <= len(result[2]) <= 1 ) # Some of them do parse
        for goodRefs in ("Mat. 7:3,7","Mat. 7:3; 4:7","Mat. 7:3,7; 4:7","Mat. 7:3,7; 4:7,9,11","Mat. 7:3; Heb. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2,9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4:4,7; Rev. 1:1; 1:1","Mrk. 7:3a,7b,8"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRefs ) )
            result = BSRs.parseReferenceString( goodRefs )
            #vPrint( 'Quiet', debuggingThisModule, goodRefs, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], True ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 2 <= len(result[2]) <= 9 )
            for r1,r2,r3,r4 in result[2]:
                self.assertTrue( isinstance( r1, str ) ) # Book code
                self.assertEqual( len(r1), 3 )
                self.assertTrue( isinstance( r2, str ) ) # Chapter number
                self.assertTrue( 1 <= len(r2) <= 3 )
                self.assertTrue( isinstance( r3, str ) ) # Verse number
                self.assertTrue( 1 <= len(r3) <= 3 )
                self.assertTrue( isinstance( r4, str ) ) # Verse suffix
                self.assertTrue( 0 <= len(r4) <= 1 )
        for badRefs in ("Meat. 7:3,7","Mat. 7:3-14:7","Mat. 7:3,7; 4+7","Mat. 7:3,7; 4:7*9,11","Mat. 7:3; Hub. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2-9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4=4,7; Rev. 1:1; 1:1","Mrk. 7:3a-7b,8"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( badRefs ) )
            result = BSRs.parseReferenceString( badRefs )
            #vPrint( 'Quiet', debuggingThisModule, badRefs, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 1 <= len(result[2]) <= 9 )
            for r1,r2,r3,r4 in result[2]:
                self.assertTrue( r1 is None or isinstance( r1, str ) ) # Book code
                self.assertTrue( r1 is None or len(r1)==3 )
                self.assertTrue( isinstance( r2, str ) ) # Chapter number
                self.assertTrue( 1 <= len(r2) <= 3 )
                self.assertTrue( isinstance( r3, str ) ) # Verse number
                self.assertTrue( 1 <= len(r3) <= 3 )
                self.assertTrue( isinstance( r4, str ) ) # Verse suffix
                self.assertTrue( 0 <= len(r4) <= 1 )
    # end of test_200_BibleSingleReferences

    def test_300_BibleReferenceList( self ):
        """ Test the BibleReferenceList function. """
        BRL = BibleReferences.BibleReferenceList( self.BOS )
        result = str( BRL )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
        #vPrint( 'Quiet', debuggingThisModule, "\nSingle References (good)" )
        for goodRef in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b", \
                        "Mat.7:0","Mt. 7:3","1Cor 1:1","1 Cor 1:2", "II Cor 1:3", "IICor 1:4","ISA 1:5",):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRef ) )
            result = BRL.parseReferenceString( goodRef )
            #vPrint( 'Quiet', debuggingThisModule, goodRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], True ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertEqual( len(result[2]), 1 )
            self.assertEqual( len(result[2][0]), 4 ) # Book, chap, vrs, suffix
            self.assertTrue( isinstance( result[2][0][0], str ) ) # Book code
            self.assertEqual( len(result[2][0][0]), 3 )
            self.assertTrue( isinstance( result[2][0][1], str ) ) # Chapter number
            self.assertTrue( 1 <= len(result[2][0][1]) <= 3 )
            self.assertTrue( isinstance( result[2][0][2], str ) ) # Verse number
            self.assertTrue( 1 <= len(result[2][0][2]) <= 3 )
            self.assertTrue( isinstance( result[2][0][3], str ) ) # Verse suffix
            self.assertTrue( 0 <= len(result[2][0][3]) <= 1 )
        for badRef in ("Mut 7:3","Mat.7777:3","Mat. 7:3333","Mta 7:3","Mt-7:3","Jde 77","Jde. 77","Jde 11:7","Jde. 2:7","Jab 8:4","Jobs. 8:4","Job88:4","Job  8:444","Lev. 8:4bc", \
                        "Mat 0:3","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( badRef ) )
            result = BRL.parseReferenceString( badRef )
            #vPrint( 'Quiet', debuggingThisModule, badRef, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 0 <= len(result[2]) <= 1 ) # Some of them do parse
        for goodRefs in ("Mat. 7:3,7","Mat. 7:3; 4:7","Mat. 7:3,7; 4:7","Mat. 7:3,7; 4:7,9,11","Mat. 7:3; Heb. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2,9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4:4,7; Rev. 1:1; 1:1","Mrk. 7:3a,7b,8"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( goodRefs ) )
            result = BRL.parseReferenceString( goodRefs )
            #vPrint( 'Quiet', debuggingThisModule, goodRefs, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], True ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 2 <= len(result[2]) <= 9 )
            for r1,r2,r3,r4 in result[2]:
                self.assertTrue( isinstance( r1, str ) ) # Book code
                self.assertEqual( len(r1), 3 )
                self.assertTrue( isinstance( r2, str ) ) # Chapter number
                self.assertTrue( 1 <= len(r2) <= 3 )
                self.assertTrue( isinstance( r3, str ) ) # Verse number
                self.assertTrue( 1 <= len(r3) <= 3 )
                self.assertTrue( isinstance( r4, str ) ) # Verse suffix
                self.assertTrue( 0 <= len(r4) <= 1 )
        for badRefs in ("Meat. 7:3,7","Mat. 7:3 to 14:7","Mat. 7:3,7; 4+7","Mat. 7:3,7; 4:7*9,11","Mat. 7:3; Hub. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2=9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4=4,7; Rev. 1:1; 1:1","Mrk. 7:3a:7b,8"):
            #vPrint( 'Quiet', debuggingThisModule, "Processing {!r} reference string…".format( badRefs ) )
            result = BRL.parseReferenceString( badRefs )
            #vPrint( 'Quiet', debuggingThisModule, badRefs, " ", result )
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 3 )
            self.assertEqual( result[0], False ) # Success (have errors) flag
            self.assertTrue( result[1] in (True,False,) ) # Have warnings flag
            self.assertTrue( isinstance( result[2], list ) ) # List of tuples
            self.assertTrue( 1 <= len(result[2]) <= 9 )
            for r1,r2,r3,r4 in result[2]:
                self.assertTrue( r1 is None or isinstance( r1, str ) ) # Book code
                self.assertTrue( r1 is None or len(r1)==3 )
                self.assertTrue( isinstance( r2, str ) ) # Chapter number
                self.assertTrue( 1 <= len(r2) <= 3 )
                self.assertTrue( isinstance( r3, str ) ) # Verse number
                self.assertTrue( 1 <= len(r3) <= 3 )
                self.assertTrue( isinstance( r4, str ) ) # Verse suffix
                self.assertTrue( 0 <= len(r4) <= 1 )
    # end of test_300_BibleReferenceList

    def test_400_BibleAnchorReference( self ):
        """ Test the BibleAnchorReference function. """
        # Test ones that should work
        for ourBBB, ourC, ourV, ourAnchor in ( ('GEN','17','25', '17:25'), \
                                            ('EXO','12','17-18', '12:17'), ('LEV','12','17-18', '12:18'), ('NUM','12','17', '12:17-18'), ('DEU','12','18', '12:17-18'), \
                                            ('JOS','12','17,18', '12:17'), ('JDG','12','17,18', '12:18'), ('SA1','12','17', '12:17,18'), ('SA2','12','18', '12:17,18'), \
                                            ('CH1','12','17-19', '12:18'), ('CH2','12','18', '12:17-19'), ):
            BAR = BibleReferences.BibleAnchorReference( ourBBB, ourC, ourV )
            vPrint( 'Quiet', debuggingThisModule, BAR ) # Just print a summary
            self.assertTrue( BAR.matchesAnchorString( ourAnchor ) )
    # end of test_400_BibleAnchorReference

    def test_410_BibleAnchorReference( self ):
        """ Test the BibleAnchorReference function. """
        # Test ones that shouldn't work
        for ourBBB, ourC, ourV, ourAnchor in ( ('GEN','17','25', '17:5'), \
                                            ('EXO','12','17-18', '12:16'), ('LEV','12','17-18', '12:19'), ('NUM','12','16', '12:17-18'), ('DEU','12','19', '12:17-18'), \
                                            ('JOS','12','17,18', '12:16'), ('JDG','12','17,18', '12:19'), ('SA1','12','16', '12:17,18'), ('SA2','12','19', '12:17,18'), \
                                            ('CH1','12','17-19', '2:18'), ('CH2','2','18', '12:17-19'), ):
            BAR = BibleReferences.BibleAnchorReference( ourBBB, ourC, ourV )
            #vPrint( 'Quiet', debuggingThisModule, BAR ) # Just print a summary
            self.assertFalse( BAR.matchesAnchorString( ourAnchor ) )
    # end of test_410_BibleAnchorReference
# end of BibleReferencesTests class


def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    vPrint( 'Normal', debuggingThisModule, programNameVersion )

    unittest.main() # Automatically runs all of the above tests
# end of BibleReferencesTests.py
