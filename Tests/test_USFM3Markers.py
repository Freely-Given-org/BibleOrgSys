#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFM3MarkersTests.py
#
# Module testing USFM3Markers.py
#
# Copyright (C) 2011-2020 Robert Hunt
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
Module testing USFM3Markers.py.
"""

LAST_MODIFIED_DATE = '2020-02-24' # by RJH
PROGRAM_NAME = "USFM3 Markers tests"
PROGRAM_VERSION = '0.62'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import unittest
import sys

BOSTopFolderpath = os.path.dirname( os.path.dirname( __file__ ) )
if BOSTopFolderpath not in sys.path:
    sys.path.insert( 0, BOSTopFolderpath ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.Converters import USFM3MarkersConverter
from BibleOrgSys.Reference import USFM3Markers


class USFM3MarkersConverterTests( unittest.TestCase ):
    """ Unit tests for the _USFM3MarkersConverter object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the USFM3MarkersConverter object
        self.UMc = USFM3MarkersConverter.USFM3MarkersConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_1010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UMc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1010_str

    def test_1020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 100 < len(self.UMc) < 255 ) # The number of USFM markers
    # end of test_1020_len

    def test_1030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.UMc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), 12 )
        for dictName in ( "rawMarkerDict", "numberedMarkerList", "combinedMarkerDict", "conversionDict", "backConversionDict", \
                            "newlineMarkersList", "numberedNewlineMarkersList", "combinedNewlineMarkersList", \
                            "internalMarkersList", "numberedInternalMarkersList", "combinedInternalMarkersList", \
                            "deprecatedMarkersList", ):
            self.assertTrue( dictName in result )
            self.assertTrue( 3 < len(result[dictName]) < 220 )
    # end of test_1030_importDataToPython

    def test_1040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.UMc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1040_pickle

    def test_1050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.UMc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToPython

    def test_1060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.UMc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToJSON

    def test_1070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.UMc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1070_exportDataToC
# end of USFM3MarkersConverterTests class


class USFM3MarkersTests( unittest.TestCase ):
    """ Unit tests for the USFM3Markers object. """

    def setUp( self ):
        parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
        # BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
        BibleOrgSysGlobals.preloadCommonData()
        # Create the USFM3Markers object
        self.UMs = USFM3Markers.USFM3Markers().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UMs )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 40 )
    # end of test_2010_str

    def test_2020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( len(self.UMs) > 110 )
    # end of test_2020_len

    def test_2030_contains( self ):
        """ Test the __contains__ function. """
        for goodMarker in ( 'h', 'q', 'p', 'c', 'v', 'q1', 'q2', 'q3', 'em', ):
            self.assertTrue( goodMarker in self.UMs )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( badMarker in self.UMs )
    # end of test_2030_contains

    def test_2040_isValidMarker( self ):
        """ Test the isValidMarker function. """
        for goodMarker in ( 'h', 'q', 'p', 'c', 'v', 'q1', 'q2', 'q3', 'em', ):
            self.assertTrue( self.UMs.isValidMarker(goodMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isValidMarker(badMarker) )
    # end of test_2040_isValidMarker

    def test_2050_isNewlineMarker( self ):
        """ Test the isNewlineMarker function. """
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertTrue( self.UMs.isNewlineMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertTrue( self.UMs.isNewlineMarker(numberableMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isNewlineMarker(numberedMarker) )
        for deprecatedMarker in ( 'ps','pdi','pde', ):
            self.assertTrue( self.UMs.isNewlineMarker(deprecatedMarker) )
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isNewlineMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isNewlineMarker(badMarker) )
    # end of test_2050_isNewlineMarker

    def test_2060_isInternalMarker( self ):
        """ Test the isInternalMarker function. """
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertTrue( self.UMs.isInternalMarker(simpleMarker) )
        for deprecatedMarker in ( 'wr', ):
            self.assertTrue( self.UMs.isInternalMarker(deprecatedMarker) )
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertFalse( self.UMs.isInternalMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertFalse( self.UMs.isInternalMarker(numberableMarker) )
        for numberedMarker in ( 'h', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isInternalMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isInternalMarker(badMarker) )
    # end of test_2060_isNewlineMarker

    def test_2065_isDeprecatedMarker( self ):
        """ Test the isDeprecatedMarker function. """
        for simpleMarker in ( 'pdi', 'pde', 'wr', 'ps', ):
            self.assertTrue( self.UMs.isDeprecatedMarker(simpleMarker) )
        for numberableMarker in ( 'ph1', 'ph2', 'ph3', ):
            self.assertTrue( self.UMs.isDeprecatedMarker(numberableMarker) )
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertFalse( self.UMs.isDeprecatedMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertFalse( self.UMs.isDeprecatedMarker(numberableMarker) )
        for numberedMarker in ( 'h', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isDeprecatedMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isDeprecatedMarker(badMarker) )
    # end of test_2065_isDeprecatedMarker

    def test_2070_isCompulsoryMarker( self ):
        """ Test the isCompulsoryMarker function. """
        for simpleMarker in ( 'id', 'c', 'v', 'h', ):
            self.assertTrue( self.UMs.isCompulsoryMarker(simpleMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(simpleMarker) )
        for numberableMarker in ( 'q', 'ili', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(badMarker) )
    # end of test_2070_isCompulsoryMarker

    def test_2080_isNumberableMarker( self ):
        """ Test the isNumberableMarker function. """
        for simpleMarker in ( 's', 'q', 'ili', ):
            self.assertTrue( self.UMs.isNumberableMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isNumberableMarker(numberedMarker) )
        for simpleMarker in ( 'h', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isNumberableMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isNumberableMarker(badMarker) )
    # end of test_2080_isNumberableMarker

    def test_2085_isNestingMarker( self ):
        """ Test the isNestingMarker function. """
        for simpleMarker in ( 'it', 'nd', 'bk', 'em', 'wj', ):
            self.assertTrue( self.UMs.isNestingMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isNestingMarker(numberedMarker) )
        for simpleMarker in ( 'h', 's', 'q', 'ili', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', ):
            self.assertFalse( self.UMs.isNestingMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isNestingMarker(badMarker) )
    # end of test_2085_isNestingMarker

    def test_2090_isPrinted( self ):
        """ Test the isPrinted function. """
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isPrinted(numberedMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertTrue( self.UMs.isPrinted(simpleMarker) )
        for simpleMarker in ( 'id', 'ide', 'sts', 'rem', 'fig', 'ndx', ):
            self.assertFalse( self.UMs.isPrinted(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isPrinted(badMarker) )
    # end of test_2090_isPrinted

    def test_2100_getMarkerClosureType( self ):
        """ Test the getMarkerClosureType function. """
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', 'wj', 'ndx', ):
            self.assertTrue( self.UMs.getMarkerClosureType(simpleMarker) in ('A','O',) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.getMarkerClosureType(numberedMarker) == 'N' )
        for simpleMarker in ( 'id', 'ide', 'sts', 'rem', 'periph', ):
            self.assertTrue( self.UMs.getMarkerClosureType(simpleMarker) == 'N' )
        for badMarker in ( 'H', 'y', 'wd', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.getMarkerClosureType(badMarker) )
    # end of test_2100_getMarkerClosureType

    def test_2105_getMarkerContentType( self ):
        """ Test the getMarkerContentType function. """
        for simpleMarker in ( 'c', 'v', 'f', 'ft', 'x', 'xq', 'em', 'wj', 'ndx', ):
            self.assertTrue( self.UMs.getMarkerContentType(simpleMarker) == 'A' )
        for simpleMarker in ( 'p', ):
            self.assertTrue( self.UMs.getMarkerContentType(simpleMarker) == 'S' )
        for numberedMarker in ( 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.getMarkerContentType(numberedMarker) == 'A' )
        for numberedMarker in ( 'q1', 'q2', 'q3', ):
            self.assertTrue( self.UMs.getMarkerContentType(numberedMarker) == 'S' )
        for simpleMarker in ( 'b', 'nb', 'pb', 'esb', 'ib', ):
            self.assertTrue( self.UMs.getMarkerContentType(simpleMarker) == 'N' )
        for badMarker in ( 'H', 'y', 'wd', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.getMarkerContentType(badMarker) )
    # end of test_2105_getMarkerContentType

    def test_2110_toRawMarker( self ):
        """ Test the toRawMarker function. """
        for simpleMarker in ( 'h', 'q', 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.toRawMarker(simpleMarker), simpleMarker )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.toRawMarker(numberedMarker), numberedMarker[:-1] )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.toRawMarker, badMarker )
    # end of test_2110_toRawMarker

    def test_2120_toStandardMarker( self ):
        """ Test the toStandardMarker function. """
        for simpleMarker in ( 'h', 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.toStandardMarker(simpleMarker), simpleMarker )
        for numberableMarker in ( 'q', 'ili', ):
            self.assertEqual( self.UMs.toStandardMarker(numberableMarker), numberableMarker+'1' )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.toStandardMarker(numberedMarker), numberedMarker )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.toStandardMarker, badMarker )
    # end of test_2120_toStandardMarker

    def test_2130_markerOccursIn( self ):
        """ Test the markerOccursIn function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.markerOccursIn( marker )
            self.assertTrue( isinstance( result , str ) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.markerOccursIn, badMarker )
    # end of test_2130_markerOccursIn

    def test_2140_getMarkerEnglishName( self ):
        """ Test the getMarkerEnglishName function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerEnglishName( marker )
            self.assertTrue( isinstance( result , str ) )
            self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.getMarkerEnglishName, badMarker )
    # end of test_2140_getMarkerEnglishName

    def test_2150_getMarkerDescription( self ):
        """ Test the getMarkerDescription function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerDescription( marker )
            if result is not None:
                self.assertTrue( isinstance( result , str ) )
                self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.getMarkerDescription, badMarker )
    # end of test_2150_getMarkerDescription

    def test_2160_getOccursInList( self ):
        """ Test the getOccursInList function. """
        result = self.UMs.getOccursInList()
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 8 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
        for name in ( 'Introduction', 'Text', ):
            self.assertTrue( name in result )
    #end of test_2160_getOccursInList

    def test_2170_getNewlineMarkersList( self ):
        """ Test the getNewlineMarkersList function. """
        result = self.UMs.getNewlineMarkersList( 'Raw' )
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 60 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'p', 'q', 'qr', 'r', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'f', 'wj', 'q1', 's2', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q5', 'wj*', ):
            self.assertFalse( badMarker in result )
    #end of test_2170_getNewlineMarkersList

    def test_2172_getNewlineMarkersList( self ):
        """ Test the getNewlineMarkersList function. """
        result = self.UMs.getNewlineMarkersList( 'Numbered' )
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 60 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'p', 'q1', 'pi2', 's3', 'r', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'f', 'wj', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q5', 'wj*', ):
            self.assertFalse( badMarker in result )
    #end of test_2172_getNewlineMarkersList

    def test_2174_getNewlineMarkersList( self ):
        """ Test the getNewlineMarkersList function. """
        result = self.UMs.getNewlineMarkersList( 'Combined' )
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 60 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'p', 'q', 'q1', 's', 's3', 'r', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'f', 'wj', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q5', 'wj*', ):
            self.assertFalse( badMarker in result )
    #end of test_2174_getNewlineMarkersList

    def test_2176_getNewlineMarkersList( self ):
        """ Test the getNewlineMarkersList function. """
        result = self.UMs.getNewlineMarkersList( 'CanonicalText' )
        self.assertTrue( isinstance( result , list ) )
        self.assertTrue( 30 < len(result) < 40 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'p', 'pi2', 'q1', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'f', 'wj', 's', 's1', 'r', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q5', 'wj*', ):
            self.assertFalse( badMarker in result )
    #end of test_2176_getNewlineMarkersList

    def test_2180_getInternalMarkersList( self ):
        """ Test the getInternalMarkersList function. """
        result = self.UMs.getInternalMarkersList()
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 10 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'x', 'f', 'ft', 'em', 'bk', 'wj', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'p', 'q', 'q1', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q9', 'bk*', ):
            self.assertFalse( badMarker in result )
    #end of test_2180_getInternalMarkersList

    def test_2190_getCharacterMarkersList( self ):
        """ Test the getCharacterMarkersList function. """
        result1 = self.UMs.getCharacterMarkersList()
        self.assertTrue( isinstance( result1, list ) )
        self.assertGreater( len(result1), 20 )
        for something in result1:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertFalse( '*' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 5 )
        for goodMarker in ( 'em', 'nd', 'fig', 'sig', 'bk', 'wj', ):
            self.assertTrue( goodMarker in result1 )
        for goodMarker in ( 'x', 'xo', 'f', 'fr', 'ft', 'p', 'q', 'q1', ):
            self.assertFalse( goodMarker in result1 )
        for badMarker in ( 'H', 'xyz', 'q9', 'bk*', ):
            self.assertFalse( badMarker in result1 )
        result2 = self.UMs.getCharacterMarkersList( includeBackslash=True )
        self.assertTrue( isinstance( result2, list ) )
        self.assertEqual( len(result2), len(result1) )
        for something in result2:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertEqual( something[0], '\\' )
            self.assertFalse( something[-1] == '\\' )
            self.assertFalse( '*' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 6 )
        for testCase in ('\\nd', '\\em'):
            self.assertTrue( testCase in result2 )
        result3 = self.UMs.getCharacterMarkersList( includeEndMarkers=True )
        self.assertTrue( isinstance( result3, list ) )
        self.assertEqual( len(result3), len(result1)*2 )
        for something in result3:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 6 )
        for testCase in ('nd', 'nd*'):
            self.assertTrue( testCase in result3 )
        result4 = self.UMs.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True )
        self.assertTrue( isinstance( result4, list ) )
        self.assertEqual( len(result4), len(result1)*2 )
        for something in result4:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertEqual( something[0], '\\' )
            self.assertFalse( something[-1] == '\\' )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 7 )
        for testCase in ('\\nd', '\\nd*'):
            self.assertTrue( testCase in result4 )
        result5 = self.UMs.getCharacterMarkersList( expandNumberableMarkers=True )
        self.assertTrue( isinstance( result5, list ) )
        self.assertGreater( len(result5), len(result1) )
        for something in result5:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertFalse( '*' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 5 )
        for testCase in ('tc1','tc2','tc3','tcr1',):
            self.assertTrue( testCase in result5 )
        result6 = self.UMs.getCharacterMarkersList( includeBackslash=True, expandNumberableMarkers=True )
        self.assertTrue( isinstance( result6, list ) )
        self.assertGreater( len(result6), len(result1) )
        for something in result6:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertTrue( '\\' in something )
            self.assertFalse( '*' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 6 )
        for testCase in ('\\tc1','\\tc2','\\tc3','\\tcr1',):
            self.assertTrue( testCase in result6 )
        result7 = self.UMs.getCharacterMarkersList( includeEndMarkers=True, expandNumberableMarkers=True )
        self.assertTrue( isinstance( result7, list ) )
        self.assertEqual( len(result7), len(result5)*2 )
        for something in result7:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 6 )
        for testCase in ('wj','tc1','tc2','tc3','tcr1', 'wj*','tc1*','tc2*','tc3*','tcr1*',):
            self.assertTrue( testCase in result7 )
        result8 = self.UMs.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True, expandNumberableMarkers=True )
        self.assertTrue( isinstance( result8, list ) )
        self.assertEqual( len(result8), len(result5)*2 )
        for something in result8:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertTrue( '\\' in something )
            self.assertFalse( ' ' in something )
            self.assertLess( len(something), 7 )
        for testCase in ('\\wj','\\tc1','\\tc2','\\tc3','\\tcr1', '\\wj*','\\tc1*','\\tc2*','\\tc3*','\\tcr1*',):
            self.assertTrue( testCase in result8 )
    #end of test_2190_getCharacterMarkersList

    def test_2200_getTypicalNoteSets( self ):
        """ Test the getTypicalNoteSets function. """
        result1 = self.UMs.getTypicalNoteSets()
        result2 = self.UMs.getTypicalNoteSets( 'All' )
        self.assertTrue( isinstance( result1, tuple ) )
        self.assertTrue( result1 == result2 )
        self.assertGreater( len(result1), 20 )
        for something in result1:
            self.assertTrue( isinstance( something , list ) )
            self.assertTrue( something )
            self.assertGreater( len(something), 1 )
        result3 = self.UMs.getTypicalNoteSets( 'fn' )
        self.assertTrue( isinstance( result3, tuple ) )
        self.assertLess( len(result3), len(result1) )
        for something in result3:
            self.assertTrue( isinstance( something , list ) )
            self.assertTrue( something )
            self.assertGreater( len(something), 1 )
        result4 = self.UMs.getTypicalNoteSets( 'xr' )
        self.assertTrue( isinstance( result4, tuple ) )
        self.assertLess( len(result4), len(result1) )
        for something in result4:
            self.assertTrue( isinstance( something , list ) )
            self.assertTrue( something )
            self.assertGreater( len(something), 1 )
        result5 = self.UMs.getTypicalNoteSets( 'pq' )
        self.assertEqual( result5, None )
    #end of test_2200_getTypicalNoteSets

    def test_2210_getMarkerListFromText( self ):
        """ Test the getMarkerListFromText function. """
        self.assertEqual( self.UMs.getMarkerListFromText(''), [] )
        self.assertEqual( self.UMs.getMarkerListFromText('This is just plain text.'), [] )
        self.assertEqual( self.UMs.getMarkerListFromText('This \\bk book\\bk* is good'), \
                                [('bk',5,' ','\\bk ',['bk'],1,'book'), ('bk',13,'*','\\bk*',[],None,' is good')] )
    #end of test_2210_getMarkerListFromText
# end of USFM3MarkersTests class


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
# end of USFM3MarkersTests.py
