#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodesTests.py
#   Last modified: 2020-03-08 by RJH (also update PROGRAM_VERSION below)
#
# Module testing BibleBooksCodes.py
#
# Copyright (C) 2011-2014 Robert Hunt
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
Module testing BibleBooksCodesConverter.py and BibleBooksCodes.py.
"""

LAST_MODIFIED_DATE = '2020-04-06' # by RJH
PROGRAM_NAME = "Bible Books Codes tests"
PROGRAM_VERSION = '0.72'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import unittest
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint
from BibleOrgSys.Reference.Converters import BibleBooksCodesConverter
from BibleOrgSys.Reference import BibleBooksCodes


class BibleBooksCodesConverterTests( unittest.TestCase ):
    """ Unit tests for the _BibleBooksCodesConverter object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the BibleBooksCodesConverter object
        self.bbcsc = BibleBooksCodesConverter.BibleBooksCodesConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_1010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbcsc )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
    # end of test_1010_str

    def test_1020_len( self ):
        """ Test the __len__ function. """
        self.assertGreater( len(self.bbcsc), 100 ) # The number of loaded books codes
        self.assertLess( 100 < len(self.bbcsc), 255 ) # The number of loaded books codes
    # end of test_1020_len

    def test_1030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bbcsc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), 18 )
        for dictName in ('referenceNumberDict','referenceAbbreviationDict','sequenceList',
                        'SBLAbbreviationDict','OSISAbbreviationDict','SwordAbbreviationDict','CCELDict',
                        'USFMAbbreviationDict','USFMNumberDict','USXNumberDict','UnboundCodeDict',
                        'BibleditNumberDict','NETBibleAbbreviationDict','DrupalBibleAbbreviationDict','BibleWorksAbbreviationDict',
                        'ByzantineAbbreviationDict','EnglishNameDict',
                        'allAbbreviationsDict',):
            self.assertTrue( dictName in result )
            self.assertGreater( len(result[dictName]), 20 )
            self.assertLess( len(result[dictName]), 420 )
    # end of test_1030_importDataToPython

    def test_1040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bbcsc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1040_pickle

    # def test_1050_exportDataToPython( self ):
    #     """ Test the exportDataToPython function. """
    #     self.assertEqual( self.bbcsc.exportDataToPython(), None ) # Basically just make sure that it runs
    # # end of test_1050_importDataToPython

    def test_1060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bbcsc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToJSON

    # def test_1070_exportDataToC( self ):
    #     """ Test the exportDataToC function. """
    #     self.assertEqual( self.bbcsc.exportDataToC(), None ) # Basically just make sure that it runs
    # # end of test_1070_exportDataToC
# end of BibleBooksCodesConverterTests class



class BibleBooksCodesTests( unittest.TestCase ):
    """ Unit tests for the BibleBooksCodes object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the BibleBooksCodes object
        self.bbc = BibleBooksCodes.BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2010_str

    def test_2020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( len(self.bbc) > 150 ) # includes apocryphal books, etc.
    # end of test_2020_len

    def test_2030_getBBBFromReferenceNumber( self ):
        """ Test the getBBBFromReferenceNumber function. """
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(1), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(39), 'MAL' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(40), 'MAT' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(46), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromReferenceNumber(66), 'REV' )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, -1 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 0 )
        self.assertRaises( KeyError, self.bbc.getBBBFromReferenceNumber, 455 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 1000 )
        self.assertRaises( ValueError, self.bbc.getBBBFromReferenceNumber, 1234 )
    # end of test_2030_getBBBFromReferenceNumber

    def test_2040_isValidBBB( self ):
        """ Test the isValidBBB function. """
        for goodBBB in ( 'GEN', 'MAL', 'MAT', 'CO1', 'REV', ):
            self.assertTrue( self.bbc.isValidBBB(goodBBB) )
        for badBBB in ( 'XYZ', 'Gen', 'CO4', ):
            self.assertFalse( self.bbc.isValidBBB(badBBB) )
    # end of test_2040_isValidBBB

    def test_2060_getAllReferenceAbbreviations( self ):
        """ Test the getAllReferenceAbbreviations function. """
        results = self.bbc.getAllReferenceAbbreviations()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 66 < len(results) < 250 )
        self.assertFalse( None in results )
        for result in results:
            self.assertTrue( len(result)==3 )
    # end of test_2060_getAllReferenceAbbreviations

    def test_2070_getReferenceNumber( self ):
        """ Test the getReferenceNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            RefN = self.bbc.getReferenceNumber( BBB )
            assert isinstance( RefN, int )
            if RefN is not None:
                self.assertGreater( RefN, 0 )
                self.assertLess( RefN, 1000 )
        self.assertEqual( self.bbc.getReferenceNumber('GEN'), 1 )
        self.assertEqual( self.bbc.getReferenceNumber('MAL'), 39 )
        self.assertEqual( self.bbc.getReferenceNumber('MAT'), 40 )
        self.assertEqual( self.bbc.getReferenceNumber('CO1'), 46 )
        self.assertEqual( self.bbc.getReferenceNumber('REV'), 66 )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'Gen' )
    # end of test_2070_getReferenceNumber

    def test_2075_getSequenceList( self ):
        """ Test the getSequenceList function. """
        allBBBs = self.bbc.getAllReferenceAbbreviations()
        seqBBBs = self.bbc.getSequenceList()
        self.assertEqual( len(seqBBBs), len(allBBBs) )
        for BBB in seqBBBs:
            self.assertTrue( isinstance( BBB, str ) )
            self.assertEqual( len(BBB), 3 )
            self.assertEqual( BBB.upper(), BBB )
        # Now test it with a list
        myBBBs = ['REV','CO2','GEN','PSA','CO1','ISA','SA2','MAT','GLS','JOB']
        seqBBBs = self.bbc.getSequenceList( myBBBs )
        self.assertEqual( len(seqBBBs), len(myBBBs) )
        self.assertEqual( seqBBBs, ['GEN', 'SA2', 'JOB', 'PSA', 'ISA', 'MAT', 'CO1', 'CO2', 'REV', 'GLS'] )
        #self.assertRaises( AssertionError, self.bbc.getSequenceList( ['GEN','EXX'] ) )
        self.assertRaises( AssertionError, self.bbc.getSequenceList, 'Gen' )
    # end of test_2075_getSequenceList

    def test_2080_getCCELNumber( self ):
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
    # end of test_2080_getCCELNumber

    def test_2090_getSBLAbbreviation( self ):
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
    # end of test_2090_getSBLAbbreviation

    def test_2100_getOSISAbbreviation( self ):
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
    # end of test_2100_getOSISAbbreviation

    def test_2110_getSwordAbbreviation( self ):
        """ Test the getSwordAbbreviation function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            SwordAbbrev = self.bbc.getSwordAbbreviation( BBB )
            if SwordAbbrev is not None:
                self.assertTrue( ' ' not in SwordAbbrev )
                self.assertGreater( len(SwordAbbrev), 1 ) # e.g., Ps
                self.assertLess( len(SwordAbbrev), 14 ) # e.g., AddEsth, EpCorPaul, T12Patr.TNaph(13)
        self.assertEqual( self.bbc.getSwordAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getSwordAbbreviation('CO1'), '1Cor' )
        self.assertEqual( self.bbc.getSwordAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'Gen' )
    # end of test_2110_getSwordAbbreviation

    def test_2120_getUSFMAbbreviation( self ):
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
    # end of test_2120_getUSFMAbbreviation

    def test_2130_getUSFMNumber( self ):
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
    # end of test_2130_getUSFMNumber

    def test_2140_getUSXNumber( self ):
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
    # end of test_2140_getUSXNumber

    def test_2145_getUnboundBibleCode( self ):
        """ Test the getUnboundBibleCode function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            UBC = self.bbc.getUnboundBibleCode( BBB )
            if UBC is not None:
                self.assertTrue( ' ' not in UBC )
                self.assertTrue( len(UBC) == 3 )
                self.assertTrue( UBC[0].isdigit() and UBC[1].isdigit() and not UBC[2].isdigit() )
                self.assertTrue( UBC[2] in ('O','N','A') )
        self.assertEqual( self.bbc.getUnboundBibleCode('GEN'), '01O' )
        self.assertEqual( self.bbc.getUnboundBibleCode('SA1'), '09O' )
        self.assertEqual( self.bbc.getUnboundBibleCode('MAL'), '39O' )
        self.assertEqual( self.bbc.getUnboundBibleCode('MAT'), '40N' )
        self.assertEqual( self.bbc.getUnboundBibleCode('CO1'), '46N' )
        self.assertEqual( self.bbc.getUnboundBibleCode('REV'), '66N' )
        self.assertEqual( self.bbc.getUnboundBibleCode('TOB'), '67A' )
        self.assertEqual( self.bbc.getUnboundBibleCode('MA1'), '77A' )
        self.assertEqual( self.bbc.getUnboundBibleCode('ODE'), '86A' )
        self.assertRaises( KeyError, self.bbc.getUnboundBibleCode, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getUnboundBibleCode, 'Gen' )
    # end of test_2145_getUnboundBibleCode

    def test_2150_getBibleditNumber( self ):
        """ Test the getBibleditNumber function. """
        for BBB in self.bbc.getAllReferenceAbbreviations():
            BEN = self.bbc.getBibleditNumber( BBB )
            if BEN is not None:
                self.assertTrue( ' ' not in BEN )
                self.assertTrue( 1 <= len(BEN) <= 2 )
                BENint = int( BEN )
                self.assertTrue( 1 <= BENint <= 88 )
        self.assertEqual( self.bbc.getBibleditNumber('GEN'), '1' )
        self.assertEqual( self.bbc.getBibleditNumber('SA1'), '9' )
        self.assertEqual( self.bbc.getBibleditNumber('MAL'), '39' )
        self.assertEqual( self.bbc.getBibleditNumber('MAT'), '40' )
        self.assertEqual( self.bbc.getBibleditNumber('CO1'), '46' )
        self.assertEqual( self.bbc.getBibleditNumber('REV'), '66' )
        self.assertEqual( self.bbc.getBibleditNumber('MA1'), '80' )
        self.assertRaises( KeyError, self.bbc.getBibleditNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getBibleditNumber, 'Gen' )
    # end of test_2150_getBibleditNumber

    def test_2160_getNETBibleAbbreviation( self ):
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
    # end of test_2160_getNETBibleAbbreviation

    def test_2170_getByzantineAbbreviation( self ):
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
    # end of test_2170_getByzantineAbbreviation

    def test_2200_getBBBFromOSISAbbreviation( self ):
        """ Test the getBBBFromOSISAbbreviation function. """
        self.assertEqual( self.bbc.getBBBFromOSISAbbreviation('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromOSISAbbreviation('1Cor'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromOSISAbbreviation('Rev'), 'REV' )
        for badCode in ('XYZ','Genesis',):
            self.assertRaises( KeyError, self.bbc.getBBBFromOSISAbbreviation, badCode )
    # end of test_2200_getBBBFromOSISAbbreviation

    def test_2210_getBBBFromUSFMAbbreviation( self ):
        """ Test the getBBBFromUSFM function. """
        self.assertEqual( self.bbc.getBBBFromUSFMAbbreviation('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromUSFMAbbreviation('Ezr'), 'EZR' )
        self.assertEqual( self.bbc.getBBBFromUSFMAbbreviation('Mat'), 'MAT' )
        self.assertEqual( self.bbc.getBBBFromUSFMAbbreviation('1Co'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromUSFMAbbreviation('Rev'), 'REV' )
        for badCode in ('XYZ','Abc',): # Must be three characters
            self.assertRaises( KeyError, self.bbc.getBBBFromUSFMAbbreviation, badCode )
        for badCode in (':)','WXYZ','Genesis',): # Must not be three characters
            self.assertRaises( AssertionError, self.bbc.getBBBFromUSFMAbbreviation, badCode )
    # end of test_2210_getBBBFromUSFMAbbreviation

    def test_2215_getBBBFromUnboundBibleCode( self ):
        """ Test the getBBBFromUnboundBibleCode function. """
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('01O'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('15O'), 'EZR' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('40N'), 'MAT' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('46N'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('66N'), 'REV' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('67A'), 'TOB' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('79A'), 'MA3' )
        self.assertEqual( self.bbc.getBBBFromUnboundBibleCode('86A'), 'ODE' )
        for badCode in ('XYZ','Abc',): # Must be three characters
            self.assertRaises( KeyError, self.bbc.getBBBFromUnboundBibleCode, badCode )
        for badCode in (':)','WXYZ','Genesis',): # Must not be three characters
            self.assertRaises( KeyError, self.bbc.getBBBFromUnboundBibleCode, badCode )
    # end of test_2215_getBBBFromUnboundBibleCode

    def test_2220_getBBBFromText( self ):
        """ Test the getBBBFromText function. """
        self.assertEqual( self.bbc.getBBBFromText('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromText('1Co'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromText('Rev'), 'REV' )
        for badCode in ('XYZ','Abc',':)','WXYZ',):
            self.assertEqual( self.bbc.getBBBFromText( badCode ), None )
    # end of test_2220_getBBBFromText

    def test_300_getExpectedChaptersList( self ):
        """ Test the getSingleChapterBooksList function. """
        self.assertEqual( self.bbc.getExpectedChaptersList('GEN'), ['50'] )
        self.assertEqual( self.bbc.getExpectedChaptersList('CO1'), ['16'] )
        self.assertEqual( self.bbc.getExpectedChaptersList('REV'), ['22'] )
        self.assertRaises( KeyError, self.bbc.getExpectedChaptersList, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getExpectedChaptersList, 'Gen' )
    # end of test_300_getExpectedChaptersList

    def test_2310_getSingleChapterBooksList( self ):
        """ Test the getSingleChapterBooksList function. """
        results = self.bbc.getSingleChapterBooksList()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 15 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 25 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('OBA','PHM','JN2','JN3','JDE',): self.assertTrue( BBB in results )
    # end of test_2310_getSingleChapterBooksList

    def test_2320_getOSISSingleChapterBooksList( self ):
        """ Test the getOSISSingleChapterBooksList function. """
        results = self.bbc.getOSISSingleChapterBooksList()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 10 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 20 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('Obad','Phlm','2John','3John','Jude',): self.assertTrue( BBB in results )
    # end of test_2320_getOSISSingleChapterBooksList

    def test_2330_getAllOSISBooksCodes( self ):
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
    # end of test_2330_getAllOSISBooksCodes

    def test_2340_getAllUSFMBooksCodes( self ):
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
    # end of test_2340_getAllUSFMBooksCodes

    def test_2350_getAllUSFMBooksCodeNumberTriples( self ):
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
        for T3 in (('Gen','01','GEN'),('Mat','41','MAT'),): self.assertTrue( T3 in results )
    # end of test_2350_getAllUSFMBooksCodeNumberTriples

    def test_2360_getAllUSXBooksCodeNumberTriples( self ):
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
        for T3 in (('Gen','001','GEN'),('Mat','040','MAT'),): self.assertTrue( T3 in results )
    # end of test_2360_getAllUSXBooksCodeNumberTriples

    #def test_2365_getAllUnboundBibleBooksCodePairs( self ):
        #""" Test the getAllUnboundBibleBooksCodePairs function. """
        #results = self.bbc.getAllUnboundBibleBooksCodePairs()
        #dPrint( 'Quiet', debuggingThisModule, results)
        #self.assertTrue( isinstance( results, list ) )
        #self.assertGreater( len(results), 65 ) # Remember it includes many non-canonical books
        #self.assertLess( len(results), 120 )
        #self.assertFalse( None in results )
        #self.assertFalse( '' in results )
        #for resultTuple in results:
            #self.assertEqual( len(resultTuple), 2 )
            #self.assertEqual( len(resultTuple[0]), 3 ) # UBC
            #self.assertEqual( len(resultTuple[1]), 3 ) # BBB
        #for T2 in (('01O','GEN'),('40N','MAT'),): self.assertTrue( T2 in results )
    ## end of test_2365_getAllUnboundBibleBooksCodePairs

    def test_2370_getAllBibleditBooksCodeNumberTriples( self ):
        """ Test the getAllBibleditBooksCodeNumberTriples function. """
        results = self.bbc.getAllBibleditBooksCodeNumberTriples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 65 ) # Remember it includes many non-canonical books
        self.assertLess( len(results), 120 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for resultTuple in results:
            self.assertEqual( len(resultTuple), 3 )
            self.assertEqual( len(resultTuple[0]), 3 )
            self.assertTrue( 1 <= len(resultTuple[1]) <= 2 )
            self.assertEqual( len(resultTuple[2]), 3 )
        for T3 in (('Gen','1','GEN'),('Mat','40','MAT'),): self.assertTrue( T3 in results )
    # end of test_2370_getAllBibleditBooksCodeNumberTriples

    def test_2380_getPossibleAlternativeBooksCodes( self ):
        """ Test the getPossibleAlternativeBooksCodes function. """
        for BBB in ('GEN','MAL','MAT','REV','SIR',):
            result = self.bbc.getPossibleAlternativeBooksCodes( BBB )
            self.assertEqual( result, None )
        for BBB in ('EST','PSA','DAN',):
            result = self.bbc.getPossibleAlternativeBooksCodes( BBB )
            self.assertTrue( isinstance( result, list ) )
            self.assertGreater( len(result), 0 )
        result = self.bbc.getPossibleAlternativeBooksCodes( 'EST' )
        self.assertTrue( isinstance( result, list ) )
        self.assertGreater( len(result), 2 )
        self.assertTrue( 'ESG' in result )
        self.assertTrue( 'ESA' in result )
        self.assertTrue( 'ESC' in result )
    # end of test_2380_getPossibleAlternativeBooksCodes

    def test_2390_getTypicalSection( self ):
        """ Test the getTypicalSection function. """
        for BBB, section in (('GEN','OT'),('MAL','OT'),('MAT','NT'),('REV','NT'), \
                                ('SIR','DC'), ('PRF','FRT'), ('XXC','BAK'),):
            result = self.bbc.getTypicalSection( BBB )
            self.assertEqual( result, section )
        for badBBB in ('ABC','xyz','Gen',):
            self.assertRaises( KeyError, self.bbc.getTypicalSection, badBBB )
    # end of test_2390_getTypicalSection

    # Test the NR (not recommended) functions
    def test_2800_getEnglishName_NR( self ):
        """ Test the getEnglishName_NR function. """
        for BBB in ('GEN','MAL','MAT','REV','SIR',):
            result = self.bbc.getEnglishName_NR( BBB )
            self.assertTrue( isinstance( result, str ) )
            self.assertGreater( len(result), 2 ) # Job is the shortest
    # end of test_2800_getEnglishName_NR

    def test_2810_getEnglishNameList_NR( self ):
        """ Test the getEnglishNameList_NR function. """
        for BBB in ('GEN','MAL','MAT','REV','SIR',):
            results = self.bbc.getEnglishNameList_NR( BBB )
            self.assertTrue( isinstance( results, list ) )
            self.assertGreater( len(results), 0 ) # Malachi only has 1
            for result in results:
                self.assertTrue( isinstance( result, str ) )
                self.assertGreater( len(result), 2 ) # Job is the shortest
    # end of test_2810_getEnglishNameList_NR

    def test_2820_isOldTestament_NR( self ):
        """ Test the isOldTestament_NR function. """
        for BBB in ('GEN','JOS','SA1','KI2','MAL',):
            self.assertTrue( self.bbc.isOldTestament_NR( BBB ))
        for BBB in ('MAT','ACT','CO1','PE2','REV',):
            self.assertFalse( self.bbc.isOldTestament_NR( BBB ))
        for BBB in ('SIR','MA1','WIS','PS2','JDT',):
            self.assertFalse( self.bbc.isOldTestament_NR( BBB ))
        count = 0
        for BBB in self.bbc:
            if self.bbc.isOldTestament_NR( BBB ): count += 1
        self.assertEqual( count, 39 )
    # end of test_2820_isOldTestament_NR

    def test_2830_isNewTestament_NR( self ):
        """ Test the isNewTestament_NR function. """
        for BBB in ('GEN','JOS','SA1','KI2','MAL',):
            self.assertFalse( self.bbc.isNewTestament_NR( BBB ))
        for BBB in ('MAT','ACT','CO1','PE2','REV',):
            self.assertTrue( self.bbc.isNewTestament_NR( BBB ))
        for BBB in ('SIR','MA1','WIS','PS2','JDT',):
            self.assertFalse( self.bbc.isNewTestament_NR( BBB ))
        count = 0
        for BBB in self.bbc:
            if self.bbc.isNewTestament_NR( BBB ): count += 1
        self.assertEqual( count, 27 )
    # end of test_2830_isNewTestament_NR

    def test_2830_isDeuterocanon_NR( self ):
        """ Test the isDeuterocanon_NR function. """
        for BBB in ('GEN','JOS','SA1','KI2','MAL',):
            self.assertFalse( self.bbc.isDeuterocanon_NR( BBB ))
        for BBB in ('MAT','ACT','CO1','PE2','REV',):
            self.assertFalse( self.bbc.isDeuterocanon_NR( BBB ))
        for BBB in ('SIR','MA1','WIS','LJE','JDT',):
            self.assertTrue( self.bbc.isDeuterocanon_NR( BBB ))
        for BBB in ('MA3','EZ5','LJB','MQ1','FOQ',):
            self.assertFalse( self.bbc.isDeuterocanon_NR( BBB ))
        count = 0
        for BBB in self.bbc:
            if self.bbc.isDeuterocanon_NR( BBB ): count += 1
        self.assertEqual( count, 15 )
    # end of test_2830_isDeuterocanon_NR
# end of BibleBooksCodesTests class


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
# end of BibleBooksCodesTests.py
