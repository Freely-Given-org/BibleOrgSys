#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BiblePunctuationSystemsTests.py
#   Last modified: 2014-12-15 (also update programVersion below)
#
# Module testing BiblePunctuationSystems.py
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
Module testing BiblePunctuationSystemsConverter.py and BiblePunctuationSystems.py.
"""

programName = "Bible Punctuation Systems tests"
programVersion = '0.42'
programNameVersion = f'{programName} v{programVersion}'


import os.path
import unittest
import sys

sourceFolder = os.path.join( os.path.dirname(__file__), '../BibleOrgSys/' )
if sourceFolder not in sys.path:
    sys.path.append( sourceFolder ) # So we can run it from the above folder and still do these imports

import BibleOrgSysGlobals
import Reference.BiblePunctuationSystemsConverter as BiblePunctuationSystemsConverter
import Reference.BiblePunctuationSystems as BiblePunctuationSystems


class BiblePunctuationSystemsConverterTests( unittest.TestCase ):
    """ Unit tests for the _BiblePunctuationSystemsConverter object. """

    def setUp( self ):
        # Create the BiblePunctuationSystemsConvertor object
        self.bpssc = BiblePunctuationSystemsConverter.BiblePunctuationSystemsConverter().loadSystems() # Doesn't reload the XML unnecessarily :)

    def test_1005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bpssc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1005_str

    def test_1010_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 2 < len(self.bpssc) < 20 ) # The number of loaded systems
    # end of test_1010_len

    def test_1020_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bpssc.importDataToPython()
        self.assertTrue( isinstance( result, dict ) )
        self.assertGreater( len(result), 2 ) # Number of punctuation systems
    # end of test_1020_importDataToPython

    def test_1030_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bpssc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1030_pickle

    def test_1040_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bpssc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1040_exportDataToPython

    def test_1050_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bpssc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToJSON

    def test_1060_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.bpssc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToC
# end of BiblePunctuationSystemsConverterTests class


class BiblePunctuationSystemsTests( unittest.TestCase ):
    """ Unit tests for the BiblePunctuationSystems object. """

    def setUp( self ):
        # Create the BiblePunctuationSystems object
        self.bpss = BiblePunctuationSystems.BiblePunctuationSystems().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bpss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2005_str

    def test_2010_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 2 < len(self.bpss) < 20 ) # The number of loaded systems
    # end of test_2010_len

    def test_2020_contains( self ):
        """ Test the __contains__ function. """
        for goodName in ('English','Matigsalug',):
            self.assertTrue( goodName in self.bpss )
        for badName in ('XYZ','StandardBible',):
            self.assertFalse( badName in self.bpss )
    # end of test_2020_contains

    def test_2030_getAvailablePunctuationSystemNames( self ):
        """ Test the getAvailablePunctuationSystemNames function. """
        results = self.bpss.getAvailablePunctuationSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 2 < len(results) < 20 ) # The number of loaded systems
        self.assertEqual( len(results), len(self.bpss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("English",): self.assertTrue( name in results )
    # end of test_2030_getAvailablePunctuationSystemNames

    def test_2040_getPunctuationSystem( self ):
        """ Test the getPunctuationSystem function. """
        results = self.bpss.getPunctuationSystem( "English" )
        self.assertTrue( isinstance( results, dict ) )
        self.assertTrue( 27 <= len(results) < 40 ) # The dictionaries
        for key in ( 'bookSeparator','chapterSeparator','chapterVerseSeparator', ):
            self.assertTrue( key in results )
        for key in results.keys():
            self.assertTrue( isinstance( results[key], str ) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assertEqual( self.bpss.getPunctuationSystem('SomeName'), None )
    # end of test_2040_getPunctuationSystem
# end of BiblePunctuationSystemsTests class


class BiblePunctuationSystemTests( unittest.TestCase ):
    """ Unit tests for the BiblePunctuationSystem object. """

    def setUp( self ):
        # Create a BiblePunctuationSystem object
        self.systemName = "English"
        self.bps = BiblePunctuationSystems.BiblePunctuationSystem( self.systemName ) # Doesn't reload the XML unnecessarily :)

    def test_3005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bps )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_3005_str

    def test_3010_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 27 <= len(self.bps) < 40 )
    # end of test_3010_len

    def test_3020_contains( self ):
        """ Test the __contains__ function. """
        for name in ('bookSeparator','chapterSeparator','chapterVerseSeparator',):
            self.assertTrue( name in self.bps )
        for name in ('XYZ','Gen','LAO','MA1','Rev'):
            self.assertFalse( name in self.bps )
    # end of test_3020_contains

    def test_3030_getPunctuationSystemName( self ):
        """ Test the getPunctuationSystemName function. """
        self.assertEqual( self.bps.getPunctuationSystemName(), self.systemName )
    # end of test_3030_getPunctuationSystemName

    def test_3040_getPunctuationDict( self ):
        """ Test the getPunctuationDict function. """
        results = self.bps.getPunctuationDict()
        self.assertTrue( isinstance( results, dict ) )
        self.assertTrue( 27 <= len(results) < 40 ) # The number of entries
        self.assertEqual( len(results), len(self.bps) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ('bookSeparator','chapterSeparator','chapterVerseSeparator',):
            self.assertTrue( name in results )
        for name in ('XYZ','Gen','LAO','MA1','Rev'):
            self.assertFalse( name in results )
    # end of test_3040_getPunctuationDict

    def test_3050_getAvailablePunctuationValueNames( self ):
        """ Test the getAvailablePunctuationValueNames function. """
        results = self.bps.getAvailablePunctuationValueNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 27 <= len(results) < 40 ) # The number of entries
        self.assertEqual( len(results), len(self.bps) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ('bookSeparator','chapterSeparator','chapterVerseSeparator',):
            self.assertTrue( name in results )
        for name in ('XYZ','Gen','LAO','MA1','Rev'):
            self.assertFalse( name in results )
    # end of test_3050_getAvailablePunctuationValueNames

    def test_3060_getPunctuationValue( self ):
        """ Test the getPunctuationValue function. """
        for name in ('bookSeparator','chapterSeparator','chapterVerseSeparator',):
            result = self.bps.getPunctuationValue( name )
            self.assertTrue( isinstance( result, str ) )
            self.assertTrue( 0 < len(result) < 5 ) # The number of characters
        for name in ('XYZ','Gen','LAO','MA1','Rev'):
            self.assertRaises( KeyError, self.bps.getPunctuationValue, name )
    # end of test_3060_getPunctuationValue
# end of BiblePunctuationSystemTests class


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    unittest.main() # Automatically runs all of the above tests
# end of BiblePunctuationSystemsTests.py
