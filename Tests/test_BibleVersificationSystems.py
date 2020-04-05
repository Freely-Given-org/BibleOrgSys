#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleVersificationSystemsTests.py
#   Last modified: 2014-12-15 (also update PROGRAM_VERSION below)
#
# Module testing BibleVersificationSystems.py
#
# Copyright (C) 2011-2014 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
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
Module testing BibleVersificationSystemsConverter.py and BibleVersificationSystems.py.
"""

PROGRAM_NAME = "Bible Versification Systems tests"
PROGRAM_VERSION = '0.48'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import unittest
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.Converters import BibleVersificationSystemsConverter
from BibleOrgSys.Reference import BibleVersificationSystems


class BibleVersificationSystemsConverterTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystemsConverter object. """

    def setUp( self ):
        # Create the BibleVersificationSystemsConverter object
        self.bvssc = BibleVersificationSystemsConverter.BibleVersificationSystemsConverter().loadSystems() # Doesn't reload the XML unnecessarily :)

    def test_1010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvssc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1010_str

    def test_1020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bvssc) < 50 ) # The number of loaded systems
    # end of test_1020_len

    def test_1030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bvssc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), len(self.bvssc) )
    # end of test_1030_importDataToPython

    def test_1040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bvssc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1040_pickle

    def test_1050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bvssc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToPython

    def test_1060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bvssc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToJSON

    def test_1070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        print( "Sorry, no C export yet :(" )
        #self.assertEqual( self.bvssc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1070_exportDataToC
# end of BibleVersificationSystemsConverterTests class


class BibleVersificationSystemsTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystems object. """

    def setUp( self ):
        # Create the BibleVersificationSystems object
        self.bvss = BibleVersificationSystems.BibleVersificationSystems().loadData( os.path.join( sourceFolder, "DataFiles/VersificationSystems/" ) ) # Doesn't reload the XML unnecessarily :)

    def test_2010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2010_str

    def test_2020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bvss) < 50 ) # The number of loaded systems
    # end of test_2020_len

    def test_2030_getAvailableVersificationSystemNames( self ):
        """ Test the getAvailableVersificationSystemNames function. """
        results = self.bvss.getAvailableVersificationSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 10 < len(results) < 50 ) # The number of loaded systems
        self.assertEqual( len(results), len(self.bvss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("KJV","GNT92","NRSV","NIV84","Luther",): self.assertTrue( name in results )
    # end of test_2030_getAvailableVersificationSystemNames

    def test_2040_isValidVersificationSystemName( self ):
        """ Test the isValidVersificationSystemName function. """
        for goodName in ("KJV","GNT92","NRSV","NIV84","Luther",): self.assertTrue( self.bvss.isValidVersificationSystemName(goodName) )
        for badName in ("KJV2011","Gnt92","NewRSV",): self.assertFalse( self.bvss.isValidVersificationSystemName(badName) )
    # end of test_2040_getAvailableVersificationSystemNames

    def test_2050_getVersificationSystem( self ):
        """ Test the getVersificationSystem function. """
        for name in ("KJV","GNT92","NRSV","NIV84","Luther",):
            results = self.bvss.getVersificationSystem( name )
            self.assertTrue( isinstance( results, dict ) )
            self.assertEqual( len(results), 4 ) # The dictionaries
            self.assertTrue( isinstance( results['CV'], OrderedDict ) )
            self.assertTrue( isinstance( results['omitted'], OrderedDict ) )
            self.assertTrue( isinstance( results['combined'], dict ) )
            self.assertTrue( isinstance( results['reordered'], dict ) )
            self.assertFalse( None in results )
            self.assertFalse( '' in results )
            self.assertEqual( self.bvss.getVersificationSystem('SomeName'), None )
    # end of test_2050_getVersificationSystem

    def test_2060_checkVersificationSystem( self ):
        """ Test the getBookList function. """
        for systemName in ('RSV52','NLT96','KJV','Vulgate','Septuagint'): # Test these systems against themselves
            testSystem = self.bvss.getVersificationSystem( systemName )
            self.bvss.checkVersificationSystem( "testSystem-"+systemName+'-a', testSystem['CV'] ) # Just compare the number of verses per chapter
            self.bvss.checkVersificationSystem( "testSystem-"+systemName+'-b', testSystem['CV'], testSystem ) # include omitted/combined/reordered verses checks this time
    # end of test_2060_checkVersificationSystem
# end of BibleVersificationSystemsTests class


class BibleVersificationSystemTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystem object. """

    def setUp( self ):
        # Create a BibleVersificationSystem object
        self.systemName = "KJV"
        self.bvs = BibleVersificationSystems.BibleVersificationSystem( self.systemName ) # Doesn't reload the XML unnecessarily :)

    def test_3010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvs )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_3010_str

    def test_3020_numAvailableBooks( self ):
        """ Test the __len__ and numBooks functions. """
        self.assertEqual( len(self.bvs), self.bvs.numAvailableBooks() )
        self.assertTrue( 22 < len(self.bvs) < 120 )
        self.assertTrue( 22 < self.bvs.numAvailableBooks() < 120 )
    # end of test_3020_numAvailableBooks

    def test_3030_getVersificationSystemName( self ):
        """ Test the getVersificationSystemName function. """
        self.assertEqual( self.bvs.getVersificationSystemName(), self.systemName )
    # end of test3030_getVersificationSystemName

    def test_3040_getNumChapters( self ):
        """ Test the getNumChapters function. """
        for BBB,value in (('GEN',50),('MAT',28), ):
            self.assertEqual( self.bvs.getNumChapters(BBB), value )
        for badBBB in ('XYZ','Gen', ):
            self.assertRaises( KeyError, self.bvs.getNumChapters, badBBB )
    # end of test_3040_getNumChapters

    def test_3050_getNumVerses( self ):
        """ Test the getNumVerses function. """
        for BBB,C,value in (('GEN','1',31),('GEN','50',26),('MAT','28',20), ):
            self.assertEqual( self.bvs.getNumVerses(BBB,C), value )
        for badBBB,C in (('XYZ','1'),('Gen','1'), ):
            self.assertRaises( KeyError, self.bvs.getNumVerses, badBBB, C )
        for BBB,badC in (('GEN','0'),('GEN','51'), ):
            self.assertRaises( KeyError, self.bvs.getNumVerses, BBB, badC )
    # end of test_3050_getNumVerses

    def test_3060_isSingleChapterBook( self ):
        """ Test the isSingleChapterBook function. """
        for BBB in ('PHM','JDE', ):
            self.assertTrue( self.bvs.isSingleChapterBook(BBB) )
        for BBB in ('GEN','MAT','REV','MA1', ):
            self.assertFalse( self.bvs.isSingleChapterBook(BBB) )
        for badBBB in ('XYZ','Gen','MA6', ):
            self.assertRaises( KeyError, self.bvs.isSingleChapterBook, badBBB )
    # end of test_3060_isSingleChapterBook

    def test_3070_getNumVersesList( self ):
        """ Test the getNumVersesList function. """
        for BBB in ('GEN','MAT','JDE',):
            result = self.bvs.getNumVersesList( BBB )
            self.assertTrue( isinstance( result, list ) )
            print( len(result), result )
            self.assertTrue( 1 <= len(result) <= 151 )
            self.assertEqual( len(result), self.bvs.getNumChapters(BBB) )
            for value in result:
                self.assertTrue( isinstance( value, int ) )
        for badBBB in ('XYZ','Gen','MA6', ):
            self.assertRaises( KeyError, self.bvs.getNumVersesList, badBBB )
    # end of test_3070_getNumVersesList
# end of BibleVersificationSystemTests class


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    unittest.main() # Automatically runs all of the above tests
# end of BibleVersificationSystemsTests.py
