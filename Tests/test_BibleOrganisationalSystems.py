#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleOrganisationalSystemsTests.py
#   Last modified: 2014-12-15 (also update PROGRAM_VERSION below)
#
# Module testing BibleOrganisationalSystems.py
#
# Copyright (C) 2013-2014 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module testing BibleOrganisationalSystemsConverter.py and BibleOrganisationalSystems.py.
"""

LAST_MODIFIED_DATE = '2020-04-06' # by RJH
PROGRAM_NAME = "Bible Organizational Systems tests"
PROGRAM_VERSION = '0.48'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import unittest
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.Converters import BibleOrganisationalSystemsConverter
from BibleOrgSys.Reference import BibleOrganisationalSystems


class BibleOrganisationalSystemsConverterTests(unittest.TestCase):
    """ Unit tests for the BibleOrganisationalSystemsConverter object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the BibleOrganisationalSystemsConverter object
        self.bossc = BibleOrganisationalSystemsConverter.BibleOrganisationalSystemsConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_1010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bossc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1010_str

    def test_1020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 150 < len(self.bossc) < 250 ) # The number of loaded items
    # end of test_1020_len

    def test_1030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bossc.importDataToPython()
        self.assertTrue( isinstance( result, tuple ) )
        self.assertEqual( len(result), 3 )
    # end of test_1030_importDataToPython

    def test_1040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bossc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1040_pickle

    def test_1050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bossc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToPython

    def test_1060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bossc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToJSON

    def test_1070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        vPrint( 'Quiet', debuggingThisModule, "Sorry, no C export yet :(" )
        #self.assertEqual( self.bossc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1070_exportDataToC
# end of BibleOrganisationalSystemsConverterTests class


class BibleOrganisationalSystemsTests(unittest.TestCase):
    """ Unit tests for the BibleOrganisationalSystems object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the BibleOrganisationalSystems object
        self.boss = BibleOrganisationalSystems.BibleOrganisationalSystems().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2010_str( self ):
        """ Test the __str__ function. """
        result = str( self.boss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2010_str

    def test_2020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 150 < len(self.boss) < 250 ) # The number of loaded systems
    # end of test_2020_len

    def test_2030_getAvailableOrganizationalSystemNames( self ):
        """ Test the getAvailableOrganizationalSystemNames function. """
        results = self.boss.getAvailableOrganizationalSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 140 < len(results) < 250 ) # The number of loaded systems
        self.assertTrue( len(results) <= len(self.boss) ) # Can be less coz this is the index and some items are combined
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("KJV-1611","GNT","NRSV","NIV-2011","LUT",): self.assertTrue( name in results )
    # end of test_2030_getAvailableOrganizationalSystemNames

    #def test_2040_isValidOrganizationalSystemName( self ):
    #    """ Test the isValidOrganizationalSystemName function. """
    #    for goodName in ("KJV","GNT92","NRSV","NIV84","Luther",): self.assertTrue( self.boss.isValidOrganizationalSystemName(goodName) )
    #    for badName in ("KJV2011","Gnt92","NewRSV",): self.assertFalse( self.boss.isValidOrganizationalSystemName(badName) )
    ## end of test_2040_getAvailableOrganizationalSystemNames

    def test_2050_getOrganizationalSystem( self ):
        """ Test the getOrganizationalSystem function. """
        for goodName in ('HEB','NTG','KJV-1611',"GNT","NRSV","NIV-2011","LUT",):
            results = self.boss.getOrganizationalSystem( goodName )
            self.assertTrue( isinstance( results, dict ) )
            self.assertTrue( 6 <= len(results) <= 11 ) # The fields
            self.assertTrue( isinstance( results['name'], list ) )
            self.assertTrue( isinstance( results['referenceAbbreviation'], str ) )
            self.assertTrue( isinstance( results['type'], str ) )
            self.assertTrue( isinstance( results['languageCode'], str ) )
            if 'includesBooks' in results: self.assertTrue( isinstance( results['includesBooks'], list ) )
            if 'booksNamesSystem' in results: self.assertTrue( isinstance( results['booksNamesSystem'], str ) )
            if 'bookOrdersystem' in results: self.assertTrue( isinstance( results['bookOrderSystem'], str ) )
            if 'versificationSystem' in results: self.assertTrue( isinstance( results['versificationSystem'], str ) )
            if 'punctuationSystem' in results: self.assertTrue( isinstance( results['punctuationSystem'], str ) )
            if 'derivedFrom' in results: self.assertTrue( isinstance( results['derivedFrom'], list ) )
            if 'publicationDate' in results: self.assertTrue( isinstance( results['publicationDate'], str ) )
            self.assertFalse( None in results )
            self.assertFalse( '' in results )
        for badName in ("KJV","GNT92","NRVS","NIV-2015","Luther",):
            self.assertEqual( self.boss.getOrganizationalSystem(badName), None )
    # end of test_2050_getOrganizationalSystem

    #def test_2060_checkOrganizationalSystem( self ):
    #    """ Test the getBookList function. """
    #    for systemName in ('RSV52','NLT96','KJV','Vulgate','Septuagint'): # Test these systems against themselves
    #        testSystem = self.boss.getOrganizationalSystem( systemName )
    #        self.boss.checkOrganizationalSystem( "testSystem-"+systemName+'-a', testSystem['CV'] ) # Just compare the number of verses per chapter
    #        self.boss.checkOrganizationalSystem( "testSystem-"+systemName+'-b', testSystem['CV'], testSystem ) # include omitted/combined/reordered verses checks this time
    ## end of test_2060_checkOrganizationalSystem
# end of BibleOrganisationalSystemsTests class


class BibleOrganisationalSystemTests(unittest.TestCase):
    """ Unit tests for the BibleOrganisationalSystem object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create a BibleOrganisationalSystem object
        self.systemName = 'KJV-1638'
        self.bos = BibleOrganisationalSystems.BibleOrganisationalSystem( self.systemName ) # Doesn't reload the XML unnecessarily :)

    def test_3010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bos )
        #dPrint( 'Quiet', debuggingThisModule, 'str result', result )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_3010_str

    def test_3020_getOrganizationalSystemName( self ):
        """ Test the getOrganizationalSystemName function. """
        self.assertEqual( self.bos.getOrganizationalSystemName(), self.systemName )
    # end of test_3020_getOrganizationalSystemName

    def test_3030_getOrganizationalSystemType( self ):
        """ Test the getOrganizationalSystemType function. """
        result = self.bos.getOrganizationalSystemType()
        self.assertTrue( isinstance( result, str ) )
        #dPrint( 'Quiet', debuggingThisModule, 3030, result )
        self.assertTrue( result in ('edition','revision',) )
    # end of test_3030_getOrganizationalSystemType

    def test_3040_getMoreBasicTypes( self ):
        """ Test the getMoreBasicTypes function. """
        results = self.bos.getMoreBasicTypes()
        self.assertTrue( isinstance( results, tuple ) )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
            self.assertTrue( result in ('revision','translation','original',) )
    # end of test_3040_getMoreBasicTypes

    def test_3050_getOrganizationalSystemValue( self ):
        """ Test the getOrganizationalSystemValue function. """
        results = self.bos.getOrganizationalSystemValue( 'derivedFrom' )
        #dPrint( 'Quiet', debuggingThisModule, '\n\n3050 results', results )
        self.assertTrue( isinstance( results, tuple ) or isinstance( results, list ) )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_3050_getOrganizationalSystemValue

    def test_3060_containsBook( self ):
        """ Test the containsBook function. """
        for goodBBB in ('GEN','MAL','MAT','REV'):
            result = self.bos.containsBook( goodBBB )
            #dPrint( 'Quiet', debuggingThisModule, '\n\n3060 result', goodBBB, result )
            self.assertTrue( result in (True,False,) )
            self.assertTrue( result )
        for badBBB in ('SIR','WIS','MA1','PS2'):
            result = self.bos.containsBook( badBBB )
            #dPrint( 'Quiet', debuggingThisModule, '\n\n3060 result', result )
            self.assertTrue( result in (True,False,) )
            self.assertFalse( result )
    # end of test_3060_containsBook

    def test_3070_getBookList( self ):
        """ Test the getBookList function. """
        results = self.bos.getBookList()
        #dPrint( 'Quiet', debuggingThisModule, '\n\n3070 results', results )
        self.assertTrue( isinstance( results, tuple ) or isinstance( results, list ) )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_3070_getBookList

    def test_3080_isValidBCVRef( self ):
        """ Test the isValidBCVRef function. """
        result = self.bos.isValidBCVRef( ('GEN','1','1',''), "Test-3080" )
        #dPrint( 'Quiet', debuggingThisModule, '\n\n3080 result', result )
        self.assertTrue( result in (True,False,) )
        self.assertTrue( result )
    # end of test_3080_isValidBCVRef


    # Tests of the BibleVersificationSystem subclass
    def test_3200_getNumChapters( self ):
        """ Test the getNumChapters function. """
        for BBB,value in (('GEN',50),('MAT',28), ):
            self.assertEqual( self.bos.getNumChapters(BBB), value )
        for badBBB in ('XYZ','Gen', ):
            self.assertRaises( KeyError, self.bos.getNumChapters, badBBB )
    # end of test_3200_getNumChapters

    def test_3210_getNumVerses( self ):
        """ Test the getNumVerses function. """
        for BBB,C,value in (('GEN','1',31),('GEN','50',26),('MAT','28',20), ):
            self.assertEqual( self.bos.getNumVerses(BBB,C), value )
        for badBBB,C in (('XYZ','1'),('Gen','1'), ):
            self.assertRaises( KeyError, self.bos.getNumVerses, badBBB, C )
        for BBB,badC in (('GEN','0'),('GEN','51'), ):
            self.assertRaises( KeyError, self.bos.getNumVerses, BBB, badC )
    # end of test_3210_getNumVerses

    def test_3220_isSingleChapterBook( self ):
        """ Test the isSingleChapterBook function. """
        for BBB in ('PHM','JDE', ):
            self.assertTrue( self.bos.isSingleChapterBook(BBB) )
        for BBB in ('GEN','MAT','REV','MA1', ):
            self.assertFalse( self.bos.isSingleChapterBook(BBB) )
        for badBBB in ('XYZ','Gen','MA6', ):
            self.assertRaises( KeyError, self.bos.isSingleChapterBook, badBBB )
    # end of test_3220_isSingleChapterBook

    def test_3230_getNumVersesList( self ):
        """ Test the getNumVersesList function. """
        for BBB in ('GEN','MAT','JDE',):
            result = self.bos.getNumVersesList( BBB )
            self.assertTrue( isinstance( result, list ) )
            #dPrint( 'Quiet', debuggingThisModule, len(result), result )
            self.assertTrue( 1 <= len(result) <= 151 )
            self.assertEqual( len(result), self.bos.getNumChapters(BBB) )
            for value in result:
                self.assertTrue( isinstance( value, int ) )
        for badBBB in ('XYZ','Gen','MA6', ):
            self.assertRaises( KeyError, self.bos.getNumVersesList, badBBB )
    # end of test_3230_getNumVersesList
# end of BibleOrganisationalSystemTests class


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
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    vPrint( 'Normal', debuggingThisModule, programNameVersion )

    unittest.main() # Automatically runs all of the above tests
# end of BibleOrganisationalSystemsTests.py
