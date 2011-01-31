#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodesTest.py
#
# Module testing BibleBooksCodes.py
#   Last modified: 2011-01-21 (also update versionString below)
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
Module testing BibleBooksCodes.py.
"""

progName = "Bible Books Codes tests"
versionString = "0.96"


import sys, os.path
import unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, BibleBooksCodes


class BibleBooksCodesTests(unittest.TestCase):
    """ Unit tests for the BibleBooksCodes object. """

    def setUp( self ):
        # Create the BibleBooksCodes object
        self.bbc = BibleBooksCodes.BibleBooksCodes().loadData( os.path.join( sourceFolder, "DataFiles/BibleBooksCodes.xml" ) ) # Doesn't reload the XML unnecessarily :)

    def test_010_len( self ):
        """ Test the __len__ function. """
        self.assert_( len(self.bbc) > 150 ) # includes apocryphal books, etc.
    # end of test_010_len

    def test_020_getBBB( self ):
        """ Test the getBBB function. """
        self.assertEqual( self.bbc.getBBB(1), 'GEN' )
        self.assertEqual( self.bbc.getBBB(39), 'MAL' )
        self.assertEqual( self.bbc.getBBB(40), 'MAT' )
        self.assertEqual( self.bbc.getBBB(46), 'CO1' )
        self.assertEqual( self.bbc.getBBB(66), 'REV' )
        self.assertRaises( ValueError, self.bbc.getBBB, -1 )
        self.assertRaises( ValueError, self.bbc.getBBB, 0 )
        self.assertRaises( ValueError, self.bbc.getBBB, 256 )
        self.assertRaises( ValueError, self.bbc.getBBB, 1234 )
        self.assertRaises( KeyError, self.bbc.getBBB, 255 )
    # end of test_020_getBBB

    def test_030_isValidReferenceAbbreviation( self ):
        """ Test the isValidReferenceAbbreviation function. """
        self.assertTrue( self.bbc.isValidReferenceAbbreviation('GEN') )
        self.assertTrue( self.bbc.isValidReferenceAbbreviation('MAL') )
        self.assertTrue( self.bbc.isValidReferenceAbbreviation('MAT') )
        self.assertTrue( self.bbc.isValidReferenceAbbreviation('CO1') )
        self.assertTrue( self.bbc.isValidReferenceAbbreviation('REV') )
        self.assertFalse( self.bbc.isValidReferenceAbbreviation('XYZ') )
        self.assertFalse( self.bbc.isValidReferenceAbbreviation('Gen') )
    # end of test_030_isValidReferenceAbbreviation

    def test_040_getAllReferenceAbbreviations( self ):
        """ Test the getAllReferenceAbbreviations function. """
        results = self.bbc.getAllReferenceAbbreviations()
        self.assert_( isinstance( results, list ) )
        self.assert_( len(results) > 66 )
        self.assertFalse( None in results )
        for result in results: self.assert_( len(result)==3 )
    # end of test_040_getAllReferenceAbbreviations

    def test_050_getReferenceNumber( self ):
        """ Test the getReferenceNumber function. """
        self.assertEqual( self.bbc.getReferenceNumber('GEN'), 1 )
        self.assertEqual( self.bbc.getReferenceNumber('MAL'), 39 )
        self.assertEqual( self.bbc.getReferenceNumber('MAT'), 40 )
        self.assertEqual( self.bbc.getReferenceNumber('CO1'), 46 )
        self.assertEqual( self.bbc.getReferenceNumber('REV'), 66 )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getReferenceNumber, 'Gen' )
    # end of test_050_getReferenceNumber

    def test_060_getCCELNumber( self ):
        """ Test the getCCELNumber function. """
        self.assertEqual( self.bbc.getCCELNumber('GEN'), '1' )
        self.assertEqual( self.bbc.getCCELNumber('MAL'), '39' )
        self.assertEqual( self.bbc.getCCELNumber('MAT'), '40' )
        self.assertEqual( self.bbc.getCCELNumber('CO1'), '46' )
        self.assertEqual( self.bbc.getCCELNumber('REV'), '66' )
        self.assertRaises( KeyError, self.bbc.getCCELNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getCCELNumber, 'Gen' )
    # end of test_060_getCCELNumber

    def test_070_getSBLAbbreviation( self ):
        """ Test the getSBLAbbreviation function. """
        self.assertEqual( self.bbc.getSBLAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getSBLAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getSBLAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getSBLAbbreviation('CO1'), '1 Cor' )
        self.assertEqual( self.bbc.getSBLAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getSBLAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getSBLAbbreviation, 'Gen' )
    # end of test_070_getSBLAbbreviation

    def test_080_getOSISAbbreviation( self ):
        """ Test the getOSISAbbreviation function. """
        self.assertEqual( self.bbc.getOSISAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getOSISAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getOSISAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getOSISAbbreviation('CO1'), '1Cor' )
        self.assertEqual( self.bbc.getOSISAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getOSISAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getOSISAbbreviation, 'Gen' )
    # end of test_080_getOSISAbbreviation

    def test_090_getSwordAbbreviation( self ):
        """ Test the getSwordAbbreviation function. """
        self.assertEqual( self.bbc.getSwordAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getSwordAbbreviation('MAT'), 'Matt' )
        self.assertEqual( self.bbc.getSwordAbbreviation('CO1'), '1Cor' )
        self.assertEqual( self.bbc.getSwordAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getSwordAbbreviation, 'Gen' )
    # end of test_090_getSwordAbbreviation

    def test_100_getParatextAbbreviation( self ):
        """ Test the getParatextAbbreviation function. """
        self.assertEqual( self.bbc.getParatextAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getParatextAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getParatextAbbreviation('MAT'), 'Mat' )
        self.assertEqual( self.bbc.getParatextAbbreviation('CO1'), '1Co' )
        self.assertEqual( self.bbc.getParatextAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getParatextAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getParatextAbbreviation, 'Gen' )
    # end of test_100_getParatextAbbreviation

    def test_110_getParatextNumber( self ):
        """ Test the getParatextNumber function. """
        self.assertEqual( self.bbc.getParatextNumber('GEN'), '01' )
        self.assertEqual( self.bbc.getParatextNumber('MAL'), '39' )
        self.assertEqual( self.bbc.getParatextNumber('MAT'), '41' )
        self.assertEqual( self.bbc.getParatextNumber('CO1'), '47' )
        self.assertEqual( self.bbc.getParatextNumber('REV'), '67' )
        self.assertRaises( KeyError, self.bbc.getParatextNumber, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getParatextNumber, 'Gen' )
    # end of test_110_getParatextNumber

    def test_120_getNETBibleAbbreviation( self ):
        """ Test the getNETBibleAbbreviation function. """
        self.assertEqual( self.bbc.getNETBibleAbbreviation('GEN'), 'Gen' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('MAL'), 'Mal' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('MAT'), 'Mat' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('CO1'), '1Co' )
        self.assertEqual( self.bbc.getNETBibleAbbreviation('REV'), 'Rev' )
        self.assertRaises( KeyError, self.bbc.getNETBibleAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getNETBibleAbbreviation, 'Gen' )
    # end of test_120_getNETBibleAbbreviation

    def test_130_getByzantineAbbreviation( self ):
        """ Test the getByzantineAbbreviation function. """
        self.assertEqual( self.bbc.getByzantineAbbreviation('GEN'), None )
        self.assertEqual( self.bbc.getByzantineAbbreviation('MAT'), 'MT' )
        self.assertEqual( self.bbc.getByzantineAbbreviation('CO1'), '1CO' )
        self.assertEqual( self.bbc.getByzantineAbbreviation('REV'), 'RE' )
        self.assertRaises( KeyError, self.bbc.getByzantineAbbreviation, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getByzantineAbbreviation, 'Mat' )
    # end of test_130_getByzantineAbbreviation

    def test_200_getBBBFromOSIS( self ):
        """ Test the getBBBFromOSIS function. """
        self.assertEqual( self.bbc.getBBBFromOSIS('Gen'), 'GEN' )
        self.assertEqual( self.bbc.getBBBFromOSIS('1Cor'), 'CO1' )
        self.assertEqual( self.bbc.getBBBFromOSIS('Rev'), 'REV' )
        self.assertRaises( KeyError, self.bbc.getBBBFromOSIS, 'XYZ' )
        self.assertRaises( KeyError, self.bbc.getBBBFromOSIS, 'Genesis' )
    # end of test_200_getBBBFromOSIS

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
        self.assert_( isinstance( results, list ) )
        self.assert_( 10 < len(results) < 20 ) # Remember it includes many non-canonical books
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('OBA','PHM','JN2','JN3','JDE',): self.assert_( BBB in results )
    # end of test_310_getSingleChapterBooksList

    def test_320_getOSISSingleChapterBooksList( self ):
        """ Test the getOSISSingleChapterBooksList function. """
        results = self.bbc.getOSISSingleChapterBooksList()
        self.assert_( isinstance( results, list ) )
        self.assert_( 10 < len(results) < 20 ) # Remember it includes many non-canonical books
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for BBB in ('Obad','Phlm','2John','3John','Jude',): self.assert_( BBB in results )
    # end of test_320_getOSISSingleChapterBooksList

    def test_330_getAllOSISBooksCodes( self ):
        """ Test the getAllOSISBooksCodes function. """
        results = self.bbc.getAllOSISBooksCodes()
        self.assert_( isinstance( results, list ) )
        self.assert_( 66 <= len(results) < 120 ) # Remember it includes many non-canonical books
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assert_( 'Gen' in results )
        self.assert_( 'Mal' in results )
        self.assert_( 'Matt' in results )
        self.assert_( 'Rev' in results )
        self.assert_( '2Macc' in results )
        for result in results:
            self.assert_( 2 <= len(result) <= 7 )
    # end of test_330_getAllOSISBooksCodes

    def test_340_getAllParatextBooksCodeNumberTriples( self ):
        """ Test the getAllParatextBooksCodeNumberTriples function. """
        results = self.bbc.getAllParatextBooksCodeNumberTriples()
        self.assert_( isinstance( results, list ) )
        self.assert_( 66 <= len(results) < 120 ) # Remember it includes many non-canonical books
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for resultTuple in results:
            self.assert_( len(resultTuple)== 3 )
            self.assert_( len(resultTuple[0]) == 3 )
            self.assert_( len(resultTuple[1]) == 2 )
            self.assert_( len(resultTuple[2]) == 3 )
        for BBB in (('Gen','01','GEN'),): self.assert_( BBB in results )
    # end of test_340_getAllParatextBooksCodeNumberTriples
# end of BibleBooksCodesTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of BibleBooksCodesTest.py
