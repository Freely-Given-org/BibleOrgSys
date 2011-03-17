#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMMarkersTests.py
#
# Module testing USFMMarkers.py
#   Last modified: 2011-03-17 (also update versionString below)
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
versionString = "0.50"


import sys, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, USFMMarkers


class USFMMarkersConverterTests( unittest.TestCase ):
    """ Unit tests for the _USFMMarkersConverter object. """

    def setUp( self ):
        # Create the USFMMarkersConvertor object
        self.UMc = USFMMarkers._USFMMarkersConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

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
        self.assertEqual( len(result), 6 )
        for dictName in ("rawMarkerDict","adjustedMarkerDict","conversionDict","backConversionDict","paragraphMarkersList","characterMarkersList",):
            self.assertTrue( dictName in result )
            self.assertTrue( 10 < len(result[dictName]) < 255 )
    # end of test_030_importDataToPython

    def test_040_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.UMc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_040_importDataToPython

    def test_050_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.UMc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_050_exportDataToJSON

    def test_060_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.UMc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_060_exportDataToC
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

    def test_030_isValidMarker( self ):
        """ Test the isValidMarker function. """
        for goodMarker in ( 'h', 'q', 'p', 'c', 'v', 'q1', 'q2', 'q3', 'em', ):
            self.assertTrue( self.UMs.isValidMarker(goodMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertFalse( self.UMs.isValidMarker(badMarker) )
    # end of test_030_isValidMarker

    def test_040_getRawMarker( self ):
        """ Test the getRawMarker function. """
        for simpleMarker in ( 'h', 'q', 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.getRawMarker(simpleMarker), simpleMarker )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.getRawMarker(numberedMarker), numberedMarker[:-1] )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.getRawMarker, badMarker )
    # end of test_040_getRawMarker

    def test_050_getStandardMarker( self ):
        """ Test the getStandardMarker function. """
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', 'em', ):
            self.assertEqual( self.UMs.getStandardMarker(simpleMarker), simpleMarker )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertEqual( self.UMs.getStandardMarker(numberableMarker), numberableMarker+'1' )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertEqual( self.UMs.getStandardMarker(numberedMarker), numberedMarker )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.getStandardMarker, badMarker )
    # end of test_050_getStandardMarker

    def test_060_isParagraphMarker( self ):
        """ Test the isParagraphMarker function. """
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertTrue( self.UMs.isParagraphMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertTrue( self.UMs.isParagraphMarker(numberableMarker) )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isParagraphMarker(numberedMarker) )
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isParagraphMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.isParagraphMarker, badMarker )
    # end of test_050_isParagraphMarker

    def test_070_isCharacterMarker( self ):
        """ Test the isCharacterMarker function. """
        for simpleMarker in ( 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertTrue( self.UMs.isCharacterMarker(simpleMarker) )
        for simpleMarker in ( 'p', 'c', 'b', 'v', 'toc1', ):
            self.assertFalse( self.UMs.isCharacterMarker(simpleMarker) )
        for numberableMarker in ( 'h', 'q', 'ili', ):
            self.assertFalse( self.UMs.isCharacterMarker(numberableMarker) )
        for numberedMarker in ( 'h1', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertFalse( self.UMs.isCharacterMarker(numberedMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.isCharacterMarker, badMarker )
    # end of test_070_isParagraphMarker

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
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.isCompulsoryMarker, badMarker )
    # end of test_070_isCompulsoryMarker

    def test_080_isNumberableMarker( self ):
        """ Test the isNumberableMarker function. """
        for simpleMarker in ( 'h', 's', 'q', 'ili', ):
            self.assertTrue( self.UMs.isNumberableMarker(simpleMarker) )
        for numberedMarker in ( 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', ):
            self.assertTrue( self.UMs.isNumberableMarker(numberedMarker) )
        for simpleMarker in ( 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            self.assertFalse( self.UMs.isNumberableMarker(simpleMarker) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.isNumberableMarker, badMarker )
    # end of test_080_isNumberableMarker

    def test_090_markerOccursIn( self ):
        """ Test the markerOccursIn function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.markerOccursIn( marker )
            self.assertTrue( isinstance( result , str ) )
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.markerOccursIn, badMarker )
    # end of test_090_markerOccursIn

    def test_100_getMarkerEnglishName( self ):
        """ Test the getMarkerEnglishName function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerEnglishName( marker )
            self.assertTrue( isinstance( result , str ) )
            self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.getMarkerEnglishName, badMarker )
    # end of test_100_getMarkerEnglishName

    def test_110_getMarkerDescription( self ):
        """ Test the getMarkerEnglishName function. """
        for marker in ( 'h', 's', 'q', 'ili', 'q1', 'q2', 'q3', 's1', 'ili1', 'ili2', 'ili3', 'p', 'b', 'toc1', 'f', 'ft', 'x', 'xq', 'em', ):
            result = self.UMs.getMarkerDescription( marker )
            if result is not None:
                self.assertTrue( isinstance( result , str ) )
                self.assertTrue( result ) # Mustn't be blank
        for badMarker in ( 'H', 'y', 'Q1', 'q5', 'toc4', 'x*', ):
            self.assertRaises( KeyError, self.UMs.getMarkerDescription, badMarker )
    # end of test_110_getMarkerEnglishName
# end of USFMMarkersTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of USFMMarkersTests.py
