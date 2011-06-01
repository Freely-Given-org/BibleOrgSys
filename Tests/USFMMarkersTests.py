#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMMarkersTests.py
#
# Module testing USFMMarkers.py
#   Last modified: 2011-06-02 (also update versionString below)
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
Module testing USFMMarkers.py.
"""

progName = "USFM Markers tests"
versionString = "0.53"


import sys, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, USFMMarkersConverter, USFMMarkers


class USFMMarkersConverterTests( unittest.TestCase ):
    """ Unit tests for the _USFMMarkersConverter object. """

    def setUp( self ):
        # Create the USFMMarkersConvertor object
        self.UMc = USFMMarkersConverter.USFMMarkersConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UMc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 100 < len(self.UMc) < 255 ) # The number of USFM markers
    # end of test_020_len

    def test_030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.UMc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertEqual( len(result), 11 )
        for dictName in ( "rawMarkerDict", "numberedMarkerList", "combinedMarkerDict", "conversionDict", "backConversionDict", \
                            "newlineMarkersList", "numberedNewlineMarkersList", "combinedNewlineMarkersList", \
                            "internalMarkersList", "numberedInternalMarkersList", "combinedInternalMarkersList", ):
            self.assertTrue( dictName in result )
            self.assertTrue( 5 < len(result[dictName]) < 255 )
    # end of test_030_importDataToPython

    def test_040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.UMc.pickle(), None ) # Basically just make sure that it runs
    # end of test_040_pickle

    def test_050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.UMc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_050_exportDataToPython

    def test_060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.UMc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_060_exportDataToJSON

    def test_070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.UMc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_070_exportDataToC
# end of USFMMarkersConverterTests class


class USFMMarkersTests( unittest.TestCase ):
    """ Unit tests for the USFMMarkers object. """

    def setUp( self ):
        # Create the USFMMarkers object
        self.UMs = USFMMarkers.USFMMarkers().loadData() # Doesn't reload the XML unnecessarily :)

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UMs )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 40 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( len(self.UMs) > 110 )
    # end of test_020_len

    def test_030_contains( self ):
        """ Test the __contains__ function. """
        for goodMarker in ( 'h', 'q', 'p', 'c', 'v', 'q1', 'q2', 'q3', 'em', ):
            self.assertTrue( goodMarker in self.UMs )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( badMarker in self.UMs )
    # end of test_030_contains

    def test_040_isValidMarker( self ):
        """ Test the isValidMarker function. """
        for goodMarker in ( 'h', 'q', 'p', 'c', 'v', 'q1', 'q2', 'q3', 'em', ):
            self.assertTrue( self.UMs.isValidMarker(goodMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isValidMarker(badMarker) )
    # end of test_040_isValidMarker

    def test_050_isNewlineMarker( self ):
        """ Test the isNewlineMarker function. """
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertTrue( self.UMs.isNewlineMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertTrue( self.UMs.isNewlineMarker(numberableMarker) )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isNewlineMarker(numberedMarker) )
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isNewlineMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isNewlineMarker(badMarker) )
    # end of test_050_isNewlineMarker

    def test_060_isInternalMarker( self ):
        """ Test the isInternalMarker function. """
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertTrue( self.UMs.isInternalMarker(simpleMarker) )
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertFalse( self.UMs.isInternalMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertFalse( self.UMs.isInternalMarker(numberableMarker) )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isInternalMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isInternalMarker(badMarker) )
    # end of test_060_isNewlineMarker

    def test_070_isCompulsoryMarker( self ):
        """ Test the isCompulsoryMarker function. """
        for simpleMarker in ( 'id', 'c', 'v', 'h', 'h1', 'h2', ):
            self.assertTrue( self.UMs.isCompulsoryMarker(simpleMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(simpleMarker) )
        for numberableMarker in ( 'q', 'ili', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isCompulsoryMarker(badMarker) )
    # end of test_070_isCompulsoryMarker

    def test_080_isNumberableMarker( self ):
        """ Test the isNumberableMarker function. """
        for simpleMarker in ( 'h', 's', 'q', 'ili', ):
            self.assertTrue( self.UMs.isNumberableMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isNumberableMarker(numberedMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isNumberableMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isNumberableMarker(badMarker) )
    # end of test_080_isNumberableMarker

    def test_090_isPrinted( self ):
        """ Test the isPrinted function. """
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isPrinted(numberedMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertTrue( self.UMs.isPrinted(simpleMarker) )
        for simpleMarker in ( 'id', 'ide', 'sts', 'rem', 'fig', 'ndx', ):
            self.assertFalse( self.UMs.isPrinted(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.isPrinted(badMarker) )
    # end of test_090_isPrinted

    def test_100_markerShouldBeClosed( self ):
        """ Test the markerShouldBeClosed function. """
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', 'wj', 'ndx', ):
            self.assertTrue( self.UMs.markerShouldBeClosed(simpleMarker) in ('A','S',) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.markerShouldBeClosed(numberedMarker) == 'N' )
        for simpleMarker in ( 'id', 'ide', 'sts', 'rem', 'periph', ):
            self.assertTrue( self.UMs.markerShouldBeClosed(simpleMarker) == 'N' )
        for badMarker in ( 'H', 'y', 'wd', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.markerShouldBeClosed(badMarker) )
    # end of test_100_markerShouldBeClosed

    def test_105_markerShouldHaveContent( self ):
        """ Test the markerShouldHaveContent function. """
        for simpleMarker in ( 'c', 'v', 'f', 'ft', 'x', 'xq', 'em', 'wj', 'ndx', ):
            self.assertTrue( self.UMs.markerShouldHaveContent(simpleMarker) == 'A' )
        for simpleMarker in ( 'p', ):
            self.assertTrue( self.UMs.markerShouldHaveContent(simpleMarker) == 'S' )
        for numberedMarker in ( 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.markerShouldHaveContent(numberedMarker) == 'A' )
        for numberedMarker in ( 'q1', 'q2', 'q3', ):
            self.assertTrue( self.UMs.markerShouldHaveContent(numberedMarker) == 'S' )
        for simpleMarker in ( 'b', 'nb', 'pb', 'esb', 'ib', ):
            self.assertTrue( self.UMs.markerShouldHaveContent(simpleMarker) == 'N' )
        for badMarker in ( 'H', 'y', 'wd', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertFalse( self.UMs.markerShouldHaveContent(badMarker) )
    # end of test_105_markerShouldHaveContent

    def test_110_toRawMarker( self ):
        """ Test the toRawMarker function. """
        for simpleMarker in ( 'h', 'q', 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.toRawMarker(simpleMarker), simpleMarker )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.toRawMarker(numberedMarker), numberedMarker[:-1] )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.toRawMarker, badMarker )
    # end of test_110_toRawMarker

    def test_120_toStandardMarker( self ):
        """ Test the toStandardMarker function. """
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.toStandardMarker(simpleMarker), simpleMarker )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertEqual( self.UMs.toStandardMarker(numberableMarker), numberableMarker+'1' )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.toStandardMarker(numberedMarker), numberedMarker )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.toStandardMarker, badMarker )
    # end of test_120_toStandardMarker

    def test_130_markerOccursIn( self ):
        """ Test the markerOccursIn function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.markerOccursIn( marker )
            self.assertTrue( isinstance( result , str ) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.markerOccursIn, badMarker )
    # end of test_130_markerOccursIn

    def test_140_getMarkerEnglishName( self ):
        """ Test the getMarkerEnglishName function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerEnglishName( marker )
            self.assertTrue( isinstance( result , str ) )
            self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.getMarkerEnglishName, badMarker )
    # end of test_140_getMarkerEnglishName

    def test_150_getMarkerDescription( self ):
        """ Test the getMarkerDescription function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerDescription( marker )
            if result is not None:
                self.assertTrue( isinstance( result , str ) )
                self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', '\\p', ):
            self.assertRaises( KeyError, self.UMs.getMarkerDescription, badMarker )
    # end of test_150_getMarkerDescription

    def test_160_getOccursInList( self ):
        """ Test the getOccursInList function. """
        result = self.UMs.getOccursInList()
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 8 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
        for name in ( 'Introduction', 'Text', ):
            self.assertTrue( name in result )
    #end of test_160_getOccursInList

    def test_170_getNewlineMarkersList( self ):
        """ Test the getNewlineMarkersList function. """
        result = self.UMs.getNewlineMarkersList()
        self.assertTrue( isinstance( result , list ) )
        self.assertGreater( len(result), 30 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'p', 'q', 'q1', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'f', 'wj', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q9', 'wj*', ):
            self.assertFalse( badMarker in result )
    #end of test_170_getNewlineMarkersList

    def test_180_getInternalMarkersList( self ):
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
    #end of test_180_getInternalMarkersList

    def test_190_getCharacterMarkersList( self ):
        """ Test the getCharacterMarkersList function. """
        result = self.UMs.getCharacterMarkersList()
        self.assertTrue( isinstance( result, list ) )
        self.assertGreater( len(result), 20 )
        for something in result:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertFalse( '*' in something )
            self.assertLess( len(something), 7 )
        for goodMarker in ( 'em', 'nd', 'fig', 'sig', 'bk', 'wj', ):
            self.assertTrue( goodMarker in result )
        for goodMarker in ( 'x', 'xo', 'f', 'fr', 'ft', 'p', 'q', 'q1', ):
            self.assertFalse( goodMarker in result )
        for badMarker in ( 'H', 'xyz', 'q9', 'bk*', ):
            self.assertFalse( badMarker in result )
        result2 = self.UMs.getCharacterMarkersList( includeBackslash=True )
        self.assertTrue( isinstance( result2, list ) )
        self.assertEqual( len(result2), len(result) )
        for something in result2:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertEqual( something[0], '\\' )
            self.assertFalse( something[-1] == '\\' )
            self.assertFalse( '*' in something )
            self.assertLess( len(something), 7 )
        for testCase in ('\\nd', '\\em'):
            self.assertTrue( testCase in result2 )
        result3 = self.UMs.getCharacterMarkersList( includeEndMarkers=True )
        self.assertTrue( isinstance( result3, list ) )
        self.assertEqual( len(result3), len(result)*2 )
        for something in result3:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertFalse( '\\' in something )
            self.assertLess( len(something), 7 )
        for testCase in ('nd', 'nd*'):
            self.assertTrue( testCase in result3 )
        result4 = self.UMs.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True )
        self.assertTrue( isinstance( result4, list ) )
        self.assertEqual( len(result4), len(result)*2 )
        for something in result4:
            self.assertTrue( isinstance( something , str ) )
            self.assertTrue( something )
            self.assertEqual( something[0], '\\' )
            self.assertFalse( something[-1] == '\\' )
            self.assertLess( len(something), 7 )
        for testCase in ('\\nd', '\\nd*'):
            self.assertTrue( testCase in result4 )
    #end of test_190_getCharacterMarkersList

    def test_200_getTypicalNoteSets( self ):
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
    #end of test_200_getTypicalNoteSets

    def test_210_getMarkerListFromText( self ):
        """ Test the getMarkerListFromText function. """
        self.assertEqual( self.UMs.getMarkerListFromText(''), [] )
        self.assertEqual( self.UMs.getMarkerListFromText('This \\bk book\\bk* is good'), [('bk',' ',5), ('bk','*',13)] )
    #end of test_210_getMarkerListFromText
# end of USFMMarkersTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of USFMMarkersTests.py
