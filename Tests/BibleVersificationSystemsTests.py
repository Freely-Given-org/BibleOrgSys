#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleVersificationSystemsTests.py
#
# Module testing BibleVersificationSystems.py
#   Last modified: 2011-12-06 (also update versionString below)
#
# Copyright (C) 2011 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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
Module testing BibleVersificationSystems.py.
"""

progName = "Bible Versification Systems tests"
versionString = "0.47"


import sys, os.path
import unittest
from collections import OrderedDict


sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, BibleVersificationSystemsConverter, BibleVersificationSystems


class BibleVersificationSystemsConverterTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystemsConverter object. """

    def setUp( self ):
        # Create the BibleVersificationSystemsConverter object
        self.bvssc = BibleVersificationSystemsConverter.BibleVersificationSystemsConverter().loadSystems() # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvssc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bvssc) < 50 ) # The number of loaded systems
    # end of test_020_len

    def test_030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bvssc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), len(self.bvssc) )
    # end of test_030_importDataToPython

    def test_040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bvssc.pickle(), None ) # Basically just make sure that it runs
    # end of test_040_pickle

    def test_050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bvssc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_050_exportDataToPython

    def test_060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bvssc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_060_exportDataToJSON

    def test_070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        print( "Sorry, no C export yet :(" )
        #self.assertEqual( self.bvssc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_070_exportDataToC
# end of BibleVersificationSystemsConverterTests class


class BibleVersificationSystemsTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystems object. """

    def setUp( self ):
        # Create the BibleVersificationSystems object
        self.bvss = BibleVersificationSystems.BibleVersificationSystems().loadData( os.path.join( sourceFolder, "DataFiles/VersificationSystems/" ) ) # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bvss) < 50 ) # The number of loaded systems
    # end of test_020_len

    def test_030_getAvailableVersificationSystemNames( self ):
        """ Test the getAvailableVersificationSystemNames function. """
        results = self.bvss.getAvailableVersificationSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 10 < len(results) < 50 ) # The number of loaded systems
        self.assertEqual( len(results), len(self.bvss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("KJV","GNT92","NRSV","NIV84","Luther",): self.assertTrue( name in results )
    # end of test_030_getAvailableVersificationSystemNames

    def test_040_isValidVersificationSystemName( self ):
        """ Test the isValidVersificationSystemName function. """
        for goodName in ("KJV","GNT92","NRSV","NIV84","Luther",): self.assertTrue( self.bvss.isValidVersificationSystemName(goodName) )
        for badName in ("KJV2011","Gnt92","NewRSV",): self.assertFalse( self.bvss.isValidVersificationSystemName(badName) )
    # end of test_040_getAvailableVersificationSystemNames

    def test_050_getVersificationSystem( self ):
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
    # end of test_050_getVersificationSystem

    def test_060_checkVersificationSystem( self ):
        """ Test the getBookList function. """
        for systemName in ('RSV52','NLT96','KJV','Vulgate','Septuagint'): # Test these systems against themselves
            testSystem = self.bvss.getVersificationSystem( systemName )
            self.bvss.checkVersificationSystem( "testSystem-"+systemName+'-a', testSystem['CV'] ) # Just compare the number of verses per chapter
            self.bvss.checkVersificationSystem( "testSystem-"+systemName+'-b', testSystem['CV'], testSystem ) # include omitted/combined/reordered verses checks this time
    # end of test_060_checkVersificationSystem
# end of BibleVersificationSystemsTests class


class BibleVersificationSystemTests(unittest.TestCase):
    """ Unit tests for the BibleVersificationSystem object. """

    def setUp( self ):
        # Create a BibleVersificationSystem object
        self.systemName = "KJV"
        self.bvs = BibleVersificationSystems.BibleVersificationSystem( self.systemName ) # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bvs )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_010_str

    def test_020_numAvailableBooks( self ):
        """ Test the __len__ and numBooks functions. """
        self.assertEqual( len(self.bvs), self.bvs.numAvailableBooks() )
        self.assertTrue( 22 < len(self.bvs) < 120 )
        self.assertTrue( 22 < self.bvs.numAvailableBooks() < 120 )
    # end of test_020_numAvailableBooks

    def test_030_getVersificationSystemName( self ):
        """ Test the getVersificationSystemName function. """
        self.assertEqual( self.bvs.getVersificationSystemName(), self.systemName )
    # end of test_030_getVersificationSystemName

    def test_040_getNumChapters( self ):
        """ Test the getNumChapters function. """
        for BBB,value in (('GEN',50),('MAT',28), ):
            self.assertEqual( self.bvs.getNumChapters(BBB), value )
        for badBBB in ('XYZ','Gen', ):
            self.assertRaises( KeyError, self.bvs.getNumChapters, badBBB )
    # end of test_040_getNumChapters

    def test_050_getNumVerses( self ):
        """ Test the getNumVerses function. """
        for BBB,C,value in (('GEN','1',31),('GEN','50',26),('MAT','28',20), ):
            self.assertEqual( self.bvs.getNumVerses(BBB,C), value )
        for badBBB,C in (('XYZ','1'),('Gen','1'), ):
            self.assertRaises( KeyError, self.bvs.getNumVerses, badBBB, C )
        for BBB,badC in (('GEN','0'),('GEN','51'), ):
            self.assertRaises( KeyError, self.bvs.getNumVerses, BBB, badC )
    # end of test_050_getNumVerses

    def test_060_isSingleChapterBook( self ):
        """ Test the isSingleChapterBook function. """
        for BBB in ('PHM','JDE', ):
            self.assertTrue( self.bvs.isSingleChapterBook(BBB) )
        for BBB in ('GEN','MAT','REV','MA1', ):
            self.assertFalse( self.bvs.isSingleChapterBook(BBB) )
        for badBBB in ('XYZ','Gen','MA6', ):
            self.assertRaises( KeyError, self.bvs.isSingleChapterBook, badBBB )
    # end of test_060_isSingleChapterBook

    def test_070_getNumVersesList( self ):
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
    # end of test_070_getNumVersesList
# end of BibleVersificationSystemTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML files to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of BibleVersificationSystemsTests.py
