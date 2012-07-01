#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodesTests.py
#   Last modified: 2012-06-30 by RJH (also update versionString below)
#
# Module testing BibleBooksCodes.py
#
# Copyright (C) 2011-2012 Robert Hunt
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
Module testing BibleBooksCodes.py.
"""

progName = "Bible Books Codes tests"
versionString = "0.62"


import sys, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, BibleBooksCodesConverter, BibleBooksCodes


class BibleBooksCodesConverterTests( unittest.TestCase ):
    """ Unit tests for the _BibleBooksCodesConverter object. """

    def setUp( self ):
        # Create the BibleBooksCodesConvertor object
        self.bbcsc = BibleBooksCodesConverter.BibleBooksCodesConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbcsc )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertGreater( len(self.bbcsc), 100 ) # The number of loaded books codes
        self.assertLess( 100 < len(self.bbcsc), 255 ) # The number of loaded books codes
    # end of test_020_len

    def test_030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bbcsc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), 13 )
        for dictName in ("referenceNumberDict","referenceAbbreviationDict","SBLAbbreviationDict","OSISAbbreviationDict","SwordAbbreviationDict","CCELDict", \
                        "USFMAbbreviationDict","USFMNumberDict","USXNumberDict","NETBibleAbbreviationDict","ByzantineAbbreviationDict","EnglishNameDict","allAbbreviationsDict",):
            self.assertTrue( dictName in result )
            self.assertGreater( len(result[dictName]), 10 )
            self.assertLess( len(result[dictName]), 255 )
    # end of test_030_importDataToPython

    def test_040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bbcsc.pickle(), None ) # Basically just make sure that it runs
    # end of test_040_pickle

    def test_050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bbcsc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_050_importDataToPython

    def test_060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bbcsc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_060_exportDataToJSON

    def test_070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.bbcsc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_070_exportDataToC
# end of BibleBooksCodesConverterTests class


class BibleBooksCodesTests( unittest.TestCase ):
    """ Unit tests for the BibleBooksCodes object. """

    def setUp( self ):
        # Create the BibleBooksCodes object
        self.bbc = BibleBooksCodes.BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( len(self.bbc) > 150 ) # includes apocryphal books, etc.
    # end of test_020_len

    def test_030_getBBBFromReferenceNumber( self ):
        """ Test the getBBBFromReferenceNumber function. """
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(1), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(39), 'MAL' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(40), 'MAT' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(46), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(66), 'REV' )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, -1 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 0 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 256 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 1234 )
        self.assertRaises( KeyError, self.bbc.getBBBFromReferenceNumber, 255 )
    # end of test_030_getBBBFromReferenceNumber

    def test_040_isValidReferenceAbbreviation( self ):
        """ Test the isValidReferenceAbbreviation function. """
        for goodBBB in ( 'GEN', 'MAL', 'MAT', 'CO1', 'REV', ):
            self.assertTrue( self.bbc.isValidReferenceAbbreviation(goodBBB) )
        for badBBB in ( 'XYZ', 'Gen', 'CO4', ):
            self.assertFalse( self.bbc.isValidReferenceAbbreviation(badBBB) )
    # end of test_040_isValidReferenceAbbreviation

    def test_060_getAllReferenceAbbreviations( self ):
        """ Test the getAllReferenceAbbreviations function. """
        results = self.bbc.getAllReferenceAbbreviations()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 66 < len(results) < 250 )
        self.assertFalse( None in results )
        for result in results:
            self.assertTrue( len(result)==3 )
    # end of test_060_getAllReferenceAbbreviations

    def test_070_getReferenceNumber( self ):
        """ Test the getReferenceNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            RefN = self.bbc.getReferenceNumber( BBB )
            if RefN is not None:
                self.assertTrue( 1 <= RefN <= 249 )
        self.assertEqual( self.bbc.getReferenceNumber('GEN'), 1 )
        self.assertEqual( self.bbc.getReferenceNumber('MAL'), 39 )
        self.assertEqual( self.bbc.getReferenceNumber('MAT'), 40 )
        self.assertEqual( self.bbc.getReferenceNumber('CO1'), 46 )
        self.assertEqual( self.bbc.getReferenceNumber('REV'), 66 )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'Gen' )
    # end of test_070_getReferenceNumber

    def test_080_getCCELNumber( self ):
        """ Test the getCCELNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            CCELN = self.bbc.getCCELNumber( BBB )
            if CCELN is not None:
                self.assertTrue( ' ' not in CCELN )
                self.assertTrue( 1 <= len(CCELN) <= 2 )
                CCELNint = int( CCELN )
                self.assertTrue( 1 <= CCELNint <= 95 )
        self.assertEqual( self.bbc.getCCELNumber('GEN'), '1' )
        self.assertEqual( self.bbc.getCCELNumber('MAL'), '39' )
        self.assertEqual( self.bbc.getCCELNumber('MAT'), '40' )
        self.assertEqual( self.bbc.getCCELNumber('CO1'), '46' )
        self.assertEqual( self.bbc.getCCELNumber('REV'), '66' )
        self.assertRaises( KeyError, self.bbc.getCCELNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getCCELNumber, 'Gen' )
    # end of test_080_getCCELNumber

    def test_090_getSBLAbbreviation( self ):
        """ Test the getSBLAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            SBLAbbrev = self.bbc.getSBLAbbreviation( BBB )
            if SBLAbbrev is not None:
                self.assertTrue( 2 <= len(SBLAbbrev) <= 8 )
        self.assertEqual( self.bbc.getSBLAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getSBLAbbreviation('PSA'), 'Ps' )
        self.assertEqual( self.bbc.getSBLAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getSBLAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getSBLAbbreviation('CO1'), '1 Cor' )
        self.assertEqual( self.bbc.getSBLAbbreviation('TH1'), '1 Thess' )
        self.assertEqual( self.bbc.getSBLAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getSBLAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getSBLAbbreviation, 'Gen' )
    # end of test_090_getSBLAbbreviation

    def test_100_getOSISAbbreviation( self ):
        """ Test the getOSISAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            OSISAbbrev = self.bbc.getOSISAbbreviation( BBB )
            if OSISAbbrev is not None:
                self.assertTrue( ' ' not in OSISAbbrev )
                self.assertTrue( 2 <= len(OSISAbbrev) <= 7 )
        self.assertEqual( self.bbc.getOSISAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getOSISAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getOSISAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getOSISAbbreviation('CO1'), '1Cor' )
        self.assertEqual( self.bbc.getOSISAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getOSISAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getOSISAbbreviation, 'Gen' )
    # end of test_100_getOSISAbbreviation

    def test_110_getSwordAbbreviation( self ):
        """ Test the getSwordAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            SwordAbbrev = self.bbc.getSwordAbbreviation( BBB )
            if SwordAbbrev is not None:
                self.assertTrue( ' ' not in SwordAbbrev )
                self.assertTrue( 2 <= len(SwordAbbrev) <= 7 )
        self.assertEqual( self.bbc.getSwordAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getSwordAbbreviation('CO1'), '1Cor' )
        self.assertEqual( self.bbc.getSwordAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'Gen' )
    # end of test_110_getSwordAbbreviation

    def test_120_getUSFMAbbreviation( self ):
        """ Test the getUSFMAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            USFMAbbrev = self.bbc.getUSFMAbbreviation( BBB )
            if USFMAbbrev is not None:
                self.assertTrue( ' ' not in USFMAbbrev )
                self.assertEqual( len(USFMAbbrev), 3 )
        self.assertEqual( self.bbc.getUSFMAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getUSFMAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getUSFMAbbreviation('MAT'), 'Mat' )
        self.assertEqual( self.bbc.getUSFMAbbreviation('CO1'), '1Co' )
        self.assertEqual( self.bbc.getUSFMAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getUSFMAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getUSFMAbbreviation, 'Gen' )
    # end of test_120_getUSFMAbbreviation

    def test_130_getUSFMNumber( self ):
        """ Test the getUSFMNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            USFMN = self.bbc.getUSFMNumber( BBB )
            if USFMN is not None:
                self.assertTrue( ' ' not in USFMN )
                self.assertEqual( len(USFMN), 2 )
        self.assertEqual( self.bbc.getUSFMNumber('GEN'), '01' )
        self.assertEqual( self.bbc.getUSFMNumber('MAL'), '39' )
        self.assertEqual( self.bbc.getUSFMNumber('MAT'), '41' )
        self.assertEqual( self.bbc.getUSFMNumber('CO1'), '47' )
        self.assertEqual( self.bbc.getUSFMNumber('REV'), '67' )
        self.assertRaises( KeyError, self.bbc.getUSFMNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getUSFMNumber, 'Gen' )
    # end of test_130_getUSFMNumber

    def test_140_getUSXNumber( self ):
        """ Test the getUSXNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            USXN = self.bbc.getUSXNumber( BBB )
            if USXN is not None:
                self.assertTrue( ' ' not in USXN )
                self.assertEqual( len(USXN), 3 )
                USXNint = int( USXN )
                self.assertTrue( 1 <= USXNint <= 123 )
        self.assertEqual( self.bbc.getUSXNumber('GEN'), '001' )
        self.assertEqual( self.bbc.getUSXNumber('MAL'), '039' )
        self.assertEqual( self.bbc.getUSXNumber('MAT'), '040' )
        self.assertEqual( self.bbc.getUSXNumber('CO1'), '046' )
        self.assertEqual( self.bbc.getUSXNumber('REV'), '066' )
        self.assertEqual( self.bbc.getUSXNumber('LBA'), '115' )
        self.assertRaises( KeyError, self.bbc.getUSXNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getUSXNumber, 'Gen' )
    # end of test_140_getUSXNumber

    def test_150_getNETBibleAbbreviation( self ):
        """ Test the getNETBibleAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            NetAbbrev = self.bbc.getNETBibleAbbreviation( BBB )
            if NetAbbrev is not None:
                self.assertTrue( ' ' not in NetAbbrev )
                self.assertEqual( len(NetAbbrev), 3 )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('MAT'), 'Mat' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('CO1'), '1Co' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getNETBibleAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getNETBibleAbbreviation, 'Gen' )
    # end of test_150_getNETBibleAbbreviation

    def test_160_getByzantineAbbreviation( self ):
        """ Test the getByzantineAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            BzAbbrev = self.bbc.getByzantineAbbreviation( BBB )
            if BzAbbrev is not None:
                self.assertTrue( ' ' not in BzAbbrev )
                self.assertTrue( 2 <= len(BzAbbrev) <= 4 )
        self.assertEqual( self.bbc.getByzantineAbbreviation('GEN'), None )
        self.assertEqual( self.bbc.getByzantineAbbreviation('MAT'), 'MT' )
        self.assertEqual( self.bbc.getByzantineAbbreviation('CO1'), '1CO' )
        self.assertEqual( self.bbc.getByzantineAbbreviation('REV'), 'RE' )
        self.assertRaises( KeyError, self.bbc.getByzantineAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getByzantineAbbreviation, 'Mat' )
    # end of test_160_getByzantineAbbreviation

    def test_200_getBBBFromOSIS( self ):
        """ Test the getBBBFromOSIS function. """
        self.assertEqual( self.bbc.getBBBFromOSIS('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromOSIS('1Cor'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromOSIS('Rev'), 'REV' )
        for badCode in ('XYZ','Genesis',):
            self.assertRaises( KeyError, self.bbc.getBBBFromOSIS, badCode )
    # end of test_200_getBBBFromOSIS

    def test_210_getBBBFromUSFM( self ):
        """ Test the getBBBFromUSFM function. """
        self.assertEqual( self.bbc.getBBBFromUSFM('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromUSFM('Ezr'), 'EZR' )
        self.assertEqual( self.bbc.getBBBFromUSFM('Mat'), 'MAT' )
        self.assertEqual( self.bbc.getBBBFromUSFM('1Co'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromUSFM('Rev'), 'REV' )
        for badCode in ('XYZ','Abc',): # Must be three characters
            self.assertRaises( KeyError, self.bbc.getBBBFromUSFM, badCode )
        for badCode in (':)','WXYZ','Genesis',): # Must not be three characters
            self.assertRaises( AssertionError, self.bbc.getBBBFromUSFM, badCode )
    # end of test_210_getBBBFromUSFM

    def test_220_getBBB( self ):
        """ Test the getBBB function. """
        self.assertEqual( self.bbc.getBBB('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBB('1Co'), 'CO1' )
        self.assertEqual( self.bbc.getBBB('Rev'), 'REV' )
        for badCode in ('XYZ','Abc',':)','WXYZ','Genesis',):
            self.assertEqual( self.bbc.getBBB( badCode ), None )
    # end of test_220_getBBB

    def test_300_getExpectedChaptersList( self ):
        """ Test the getSingleChapterBooksList function. """
        self.assertEqual( self.bbc.getExpectedChaptersList('GEN'), ['50'] )
        self.assertEqual( self.bbc.getExpectedChaptersList('CO1'), ['16'] )
        self.assertEqual( self.bbc.getExpectedChaptersList('REV'), ['22'] )
        self.assertRaises( KeyError, self.bbc.getExpectedChaptersList, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getExpectedChaptersList, 'Gen' )
    # end of test_300_getExpectedChaptersList

    def test_310_getSingleChapterBooksList( self ):
        """ Test the getSingleChapterBooksList function. """
        results = self.bbc.getSingleChapterBooksList()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 10 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 20 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('OBA','PHM','JN2','JN3','JDE',): self.assertTrue( BBB in results )
    # end of test_310_getSingleChapterBooksList

    def test_320_getOSISSingleChapterBooksList( self ):
        """ Test the getOSISSingleChapterBooksList function. """
        results = self.bbc.getOSISSingleChapterBooksList()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 10 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 20 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('Obad','Phlm','2John','3John','Jude',): self.assertTrue( BBB in results )
    # end of test_320_getOSISSingleChapterBooksList

    def test_330_getAllOSISBooksCodes( self ):
        """ Test the getAllOSISBooksCodes function. """
        results = self.bbc.getAllOSISBooksCodes()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 65 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 120 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assertTrue( 'GEN' in results )
        self.assertTrue( 'MAL' in results )
        self.assertTrue( 'MATT' in results )
        self.assertTrue( 'REV' in results )
        self.assertTrue( '2MACC' in results )
        for result in results:
            self.assertGreater( len(result), 1 )
            self.assertLess( len(result), 8 )
    # end of test_330_getAllOSISBooksCodes

    def test_340_getAllUSFMBooksCodes( self ):
        """ Test the getAllUSFMBooksCodes function. """
        results1 = self.bbc.getAllUSFMBooksCodes()
        self.assertTrue( isinstance( results1, list ) )
        self.assertGreater( len(results1), 100 ) # Remember it includes many non-canonical books
        self.assertLess( len(results1), 140 )
        self.assertFalse( None in results1 )
        self.assertFalse( '' in results1 )
        for result in results1:
            self.assertEqual( len(result), 3 )
        for BBB in ('Gen','Rev',): self.assertTrue( BBB in results1 )
        results2 = self.bbc.getAllUSFMBooksCodes( True ) # Upper case
        self.assertTrue( isinstance( results2, list ) )
        self.assertGreater( len(results2), 100 ) # Remember it includes many non-canonical books
        self.assertLess( len(results2), 140 )
        self.assertEqual( len(results1), len(results2) )
        self.assertFalse( None in results2 )
        self.assertFalse( '' in results2 )
        for result in results2:
            self.assertEqual( len(result), 3 )
            self.assertEqual( result, result.upper() )
        for BBB in ('GEN','REV',): self.assertTrue( BBB in results2 )
    # end of test_340_getAllUSFMBooksCodes

    def test_350_getAllUSFMBooksCodeNumberTriples( self ):
        """ Test the getAllUSFMBooksCodeNumberTriples function. """
        results = self.bbc.getAllUSFMBooksCodeNumberTriples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 65 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 120 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for resultTuple in results:
            self.assertEqual( len(resultTuple), 3 )
            self.assertEqual( len(resultTuple[0]), 3 )
            self.assertEqual( len(resultTuple[1]), 2 )
            self.assertEqual( len(resultTuple[2]), 3 )
        for BBB in (('Gen','01','GEN'),): self.assertTrue( BBB in results )
    # end of test_350_getAllUSFMBooksCodeNumberTriples

    def test_360_getAllUSXBooksCodeNumberTriples( self ):
        """ Test the getAllUSXBooksCodeNumberTriples function. """
        results = self.bbc.getAllUSXBooksCodeNumberTriples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 65 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 120 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for resultTuple in results:
            self.assertEqual( len(resultTuple), 3 )
            self.assertEqual( len(resultTuple[0]), 3 )
            self.assertEqual( len(resultTuple[1]), 3 )
            self.assertEqual( len(resultTuple[2]), 3 )
        for BBB in (('Gen','001','GEN'),): self.assertTrue( BBB in results )
    # end of test_360_getAllUSXBooksCodeNumberTriples
# end of BibleBooksCodesTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of BibleBooksCodesTests.py
