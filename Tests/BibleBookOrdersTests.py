#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBookOrdersTests.py
#
# Module testing BibleBookOrders.py
#   Last modified: 2013-01-13 (also update versionString below)
#
# Copyright (C) 2011-2013 Robert Hunt
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
Module testing BibleBookOrdersConverter.py and BibleBookOrders.py.
"""

progName = "Bible Book Orders tests"
versionString = "0.83"


import sys, unittest
from collections import OrderedDict


sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, BibleBookOrdersConverter, BibleBookOrders


class BibleBookOrdersConverterTests( unittest.TestCase ):
    """ Unit tests for the _BibleBookOrdersConverter object. """

    def setUp( self ):
        # Create the BibleBookOrdersConvertor object
        self.bbosc = BibleBookOrdersConverter.BibleBookOrdersConverter().loadSystems() # Doesn't reload the XML unnecessarily :)

    def test_1005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbosc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1005_str

    def test_1010_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bbosc) < 50 ) # The number of loaded systems
    # end of test_1010_len

    def test_1020_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bbosc.importDataToPython()
        self.assertTrue( isinstance( result, tuple ) )
        self.assertEqual( len(result), 2 )
    # end of test_1020_importDataToPython

    def test_1030_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bbosc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1030_pickle

    def test_1040_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bbosc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1040_exportDataToPython

    def test_1050_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bbosc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToJSON

    def test_1060_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.bbosc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToC
# end of BibleBookOrdersConverterTests class


class BibleBookOrderSystemsTests( unittest.TestCase ):
    """ Unit tests for the BibleBookOrderSystems object. """

    def setUp( self ):
        # Create the BibleBookOrderSystems object
        self.bboss = BibleBookOrders.BibleBookOrderSystems().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bboss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2005_str

    def test_2010_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 10 < len(self.bboss) < 50 ) # The number of loaded systems
    # end of test_2010_len

    def test_2020_contains( self ):
        """ Test the __contains__ function. """
        for goodName in ('EuropeanBible','VulgateBible','LutheranBible',):
            self.assertTrue( goodName in self.bboss )
        for badName in ('XYZ','StandardBible',):
            self.assertFalse( badName in self.bboss )
    # end of test_2020_contains

    def test_2030_getAvailableBookOrderSystemNames( self ):
        """ Test the getAvailableBookOrderSystemNames function. """
        results = self.bboss.getAvailableBookOrderSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 10 < len(results) < 50 ) # The number of loaded systems
        self.assertEqual( len(results), len(self.bboss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("EuropeanBible",): self.assertTrue( name in results )
    # end of test_2030_getAvailableBookOrderSystemNames

    def test_2040_getBookOrderSystem( self ):
        """ Test the getBookOrderSystem function. """
        results = self.bboss.getBookOrderSystem( "EuropeanBible" )
        self.assertTrue( isinstance( results, tuple ) )
        self.assertEqual( len(results), 3 ) # The dictionaries
        self.assertTrue( isinstance( results[0], OrderedDict ) )
        self.assertTrue( isinstance( results[1], OrderedDict ) )
        self.assertTrue( isinstance( results[2], list ) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assertEqual( self.bboss.getBookOrderSystem('SomeName'), None )
    # end of test_2040_getBookOrderSystem

    def test_2050_numBooks( self ):
        """ Test the numBooks function. """
        self.assertEqual( self.bboss.numBooks("EuropeanBible"), 73 )
        self.assertRaises( KeyError, self.bboss.numBooks, 'XYZ' )
        self.assertRaises( KeyError, self.bboss.numBooks, 'SomeName' )
    # end of test_2050_numBooks

    def test_2060_containsBook( self ):
        """ Test the containsBook function. """
        version = "EuropeanBible"
        for goodBBB in ('GEN','MAL','MAT','CO1','REV',):
            self.assertTrue( self.bboss.containsBook( version, goodBBB) )
        for badBBB in ('XYZ','Gen','LAO','MA9',):
            self.assertFalse( self.bboss.containsBook( version, badBBB) )

        version = "SomeName"
        self.assertRaises( KeyError, self.bboss.containsBook, version,'MAT' )
    # end of test_060_containsBook

    def test_2070_getBookOrderList( self ):
        """ Test the getBookOrderList function. """
        for (name, count, books,) in ( ("EuropeanBible",73,('GEN','MAL','MAT','REV',)), ("EuropeanBible",73,('GEN','MAL',)), ("EuropeanBible",73,('MAT','REV',)), ):
            results = self.bboss.getBookOrderList( name )
            self.assertTrue( isinstance( results, list ) )
            self.assertEqual( len(results), count ) # The number of books
            self.assertFalse( None in results )
            self.assertFalse( '' in results )
            for BBB in books: self.assertTrue( BBB in results )
    # end of test_2070_getBookOrderList

    def test_2080_checkBookOrderSystem( self ):
        """ Test the checkBookOrderSystem function.
            It returns the number of matched systems. """
        self.assertEqual( self.bboss.checkBookOrderSystem( "myGoodTest", \
            ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV'] ), 5 )
        self.assertEqual( self.bboss.checkBookOrderSystem( "myPartialTest", \
            ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JDE', 'REV'] ), 5 )
    # end of test_2080_checkBookOrderSystem
# end of BibleBookOrderSystemsTests class


class BibleBookOrderSystemTests( unittest.TestCase ):
    """ Unit tests for the BibleBookOrderSystem object. """

    def setUp( self ):
        # Create a BibleBookOrderSystem object
        self.systemName = "EuropeanBible"
        self.bbos = BibleBookOrders.BibleBookOrderSystem( self.systemName ) # Doesn't reload the XML unnecessarily :)

    def test_3005_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbos )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_3005_str

    def test_3010_numBooks( self ):
        """ Test the __len__ and numBooks functions. """
        self.assertEqual( len(self.bbos), 73 )
        self.assertEqual( self.bbos.numBooks(), 73 )
    # end of test_3010_numBooks

    def test_3020_contains( self ):
        """ Test the __contains__ function. """
        for BBB in ('GEN','MAL','MAT','CO1','REV'):
            self.assertTrue( BBB in self.bbos )
        for BBB in ('XYZ','Gen','LAO','MA7','Rev'):
            self.assertFalse( BBB in self.bbos )
    # end of test_3020_contains

    def test_3030_containsBook( self ):
        """ Test the containsBook function. """
        self.assertTrue( self.bbos.containsBook('GEN') )
        self.assertTrue( self.bbos.containsBook('MAL') )
        self.assertTrue( self.bbos.containsBook('MAT') )
        self.assertTrue( self.bbos.containsBook('CO1') )
        self.assertTrue( self.bbos.containsBook('REV') )
        self.assertFalse( self.bbos.containsBook('XYZ') )
        self.assertFalse( self.bbos.containsBook('Gen') )
        self.assertFalse( self.bbos.containsBook('LAO') )
        #self.assertFalse( self.bbos.containsBook('MA1') )
    # end of test_3030_containsBook

    def test_3040_getBookOrderSystemName( self ):
        """ Test the getBookOrderSystemName function. """
        self.assertEqual( self.bbos.getBookOrderSystemName(), self.systemName )
    # end of test_3040_getBookOrderSystemName

    def test_3050_getBookOrderPosition( self ):
        """ Test the getBookOrderPosition function. """
        self.assertEqual( self.bbos.getBookOrderPosition('GEN'), 1 )
        #self.assertEqual( self.bbos.getBookOrderPosition('MAL'), 39 )
        #self.assertEqual( self.bbos.getBookOrderPosition('MAT'), 40 )
        #self.assertEqual( self.bbos.getBookOrderPosition('CO1'), 46 )
        #self.assertEqual( self.bbos.getBookOrderPosition('REV'), 66 )
        for badBBB in ('XYZ','Gen',):
            self.assertRaises( KeyError, self.bbos.getBookOrderPosition, badBBB )
    # end of test_3050_getBookOrderPosition

    def test_3060_getBookAtOrderPosition( self ):
        """ Test the getBookAtOrderPosition function. """
        self.assertEqual( self.bbos.getBookAtOrderPosition(1), 'GEN' )
        #self.assertEqual( self.bbos.getBookAtOrderPosition(39), 'MAL' )
        #self.assertEqual( self.bbos.getBookAtOrderPosition(40), 'MAT' )
        #self.assertEqual( self.bbos.getBookAtOrderPosition(46), 'CO1' )
        #self.assertEqual( self.bbos.getBookAtOrderPosition(66), 'REV' )
        for position in (0,99,):
            self.assertRaises( KeyError, self.bbos.getBookAtOrderPosition, position )
    # end of test_3060_getBookAtOrderPosition

    def test_3070_getBookOrderList( self ):
        """ Test the getSingleChapterBooksList function. """
        results = self.bbos.getBookOrderList()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( len(results) >= 66 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('OBA','PHM','JN2','JN3','JDE',): self.assertTrue( BBB in results )
    # end of test_3070_getBookOrderList

    def test_3080_getNextBook( self ):
        """ Test the getNextBook function. """
        self.assertEqual( self.bbos.getNextBook('GEN'), 'EXO' )
        self.assertEqual( self.bbos.getNextBook('ZEC'), 'MAL' )
        self.assertEqual( self.bbos.getNextBook('MAL'), 'MAT' )
        self.assertEqual( self.bbos.getNextBook('CO1'), 'CO2' )
        self.assertEqual( self.bbos.getNextBook('JDE'), 'REV' )
        self.assertRaises( KeyError, self.bbos.getNextBook, 'XYZ' )
        self.assertRaises( KeyError, self.bbos.getNextBook, 'Gen' )
    # end of test_3080_getNextBook

    def test_3090_correctlyOrdered( self ):
        """ Test the correctlyOrdered function. """
        self.assertTrue( self.bbos.correctlyOrdered('GEN','EXO') )
        self.assertTrue( self.bbos.correctlyOrdered('GEN','LEV') )
        self.assertTrue( self.bbos.correctlyOrdered('GEN','REV') )
        self.assertTrue( self.bbos.correctlyOrdered('MAL','MAT') )
        self.assertTrue( self.bbos.correctlyOrdered('MAT','MRK') )
        self.assertTrue( self.bbos.correctlyOrdered('MAT','CO1') )
        self.assertTrue( self.bbos.correctlyOrdered('CO1','TI1') )
        self.assertTrue( self.bbos.correctlyOrdered('JDE','REV') )
        self.assertFalse( self.bbos.correctlyOrdered('EXO','GEN') )
        self.assertFalse( self.bbos.correctlyOrdered('CO2','CO1') )
        self.assertFalse( self.bbos.correctlyOrdered('REV','MAL') )
        #self.assertRaises( KeyError, self.bbos.correctlyOrdered, 'MA1', 'MA2' )
        self.assertRaises( KeyError, self.bbos.correctlyOrdered, 'XYZ', 'MAT' )
        self.assertRaises( KeyError, self.bbos.correctlyOrdered, 'GEN', 'Rev' )
    # end of test_3090_correctlyOrdered
# end of BibleBookOrderSystemTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML files to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of BibleBookOrdersTests.py
