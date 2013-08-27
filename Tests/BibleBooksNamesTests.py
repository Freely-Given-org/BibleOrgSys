#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksNamesTests.py
#   Last modified: 2013-08-28 (also update ProgVersion below)
#
# Module testing BibleBooksNames.py
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
Module testing BibleBooksNamesConverter.py and BibleBooksNames.py.
"""

ProgName = "Bible Books Names tests"
ProgVersion = "0.30"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import sys, unittest
from collections import OrderedDict


sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, BibleBooksNamesConverter, BibleBooksNames


class BibleBooksNamesConverterTests( unittest.TestCase ):
    """ Unit tests for the BibleBooksNamesConverter object. """

    def setUp( self ):
        # Create the BibleBooksNamesConverter object
        self.bbnsc = BibleBooksNamesConverter.BibleBooksNamesConverter().loadSystems() # Doesn't reload the XML unnecessarily :)

    def test_1010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbnsc )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_1010_str

    def test_1020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 3 < len(self.bbnsc) < 20 ) # The number of loaded systems
    # end of test_1020_len

    def test_1030_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.bbnsc.importDataToPython()
        self.assertTrue( isinstance( result, tuple ) )
        self.assertEqual( len(result), 2 )
    # end of test_1030_importDataToPython

    def test_1040_pickle( self ):
        """ Test the pickle function. """
        self.assertEqual( self.bbnsc.pickle(), None ) # Basically just make sure that it runs
    # end of test_1040_pickle

    def test_1050_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.bbnsc.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_1050_exportDataToPython

    def test_1060_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.bbnsc.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_1060_exportDataToJSON

    def test_1070_exportDataToC( self ):
        """ Test the exportDataToC function. """
        print( "Sorry, no C export yet :(" )
        #self.assertEqual( self.bbnsc.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_1070_exportDataToC
# end of BibleBooksNamesConverterTests class


class BibleBooksNamesSystemsTests( unittest.TestCase ):
    """ Unit tests for the BibleBooksNamesSystems object. """

    def setUp( self ):
        # Create the BibleBooksNamesSystems object
        self.bbnss = BibleBooksNames.BibleBooksNamesSystems().loadData() # Doesn't reload the XML unnecessarily :)

    def test_2010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbnss )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_2010_str

    def test_2020_len( self ):
        """ Test the __len__ function. """
        self.assertTrue( 3 < len(self.bbnss) < 20 ) # The number of loaded systems
    # end of test_2020_len

    def test_2030_contains( self ):
        """ Test the __contains__ function. """
        for goodName in ('eng_traditional','deu_traditional','mbt',):
            self.assertTrue( goodName in self.bbnss )
        for badName in ('eng','StandardBible',):
            self.assertFalse( badName in self.bbnss )
    # end of test_2030_contains

    def test_2040_getAvailableBooksNamesSystemNames( self ):
        """ Test the getAvailableBooksNamesSystemNames function. """
        results = self.bbnss.getAvailableBooksNamesSystemNames()
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 3 < len(results) < 20 ) # The number of loaded systems
        self.assertEqual( len(results), len(self.bbnss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ("eng_traditional",): self.assertTrue( name in results )

        # Do it for a specified language code
        results = self.bbnss.getAvailableBooksNamesSystemNames( 'eng' )
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 1 <= len(results) < 3 )
        self.assertTrue( len(results) < len(self.bbnss) )
        self.assertFalse( None in results )
        for name in ("traditional",): self.assertTrue( name in results )

        results = self.bbnss.getAvailableBooksNamesSystemNames( languageCode='mbt')
        self.assertTrue( isinstance( results, list ) )
        self.assertTrue( 1 <= len(results) < 3 )
        self.assertTrue( len(results) < len(self.bbnss) )
        self.assertFalse( None in results )
        for name in ('',): self.assertTrue( name in results )
    # end of test_2040_getAvailableBooksNamesSystemNames

    def test_2050_getAvailableLanguageCodes( self ):
        """ Test the getAvailableLanguageCodes function. """
        results = self.bbnss.getAvailableLanguageCodes()
        self.assertTrue( isinstance( results, set ) )
        self.assertTrue( 3 < len(results) < 20 )
        self.assertTrue( len(results) <= len(self.bbnss) )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for name in ('eng','fra','deu',): self.assertTrue( name in results )
    # end of test_2050_getAvailableLanguageCodes

    def test_2060_getBooksNamesSystem( self ):
        """ Test the getBooksNamesSystem function. """
        results = self.bbnss.getBooksNamesSystem( "eng_traditional" )
        self.assertTrue( isinstance( results, tuple ) )
        self.assertEqual( len(results), 5 ) # The dictionaries
        self.assertTrue( isinstance( results[0], dict ) and 5 < len(results[0]) < 10 )
        self.assertTrue( isinstance( results[1], dict ) and 5 < len(results[1]) < 10 )
        self.assertTrue( isinstance( results[2], dict ) and 50 < len(results[2]) < 300 )
        self.assertTrue( isinstance( results[3], OrderedDict ) and not results[3] ) # Should be empty
        self.assertTrue( isinstance( results[4], OrderedDict ) and not results[4] )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assertEqual( self.bbnss.getBooksNamesSystem('SomeName'), None )

        # Now do it again with a specified book list
        sampleBookList = ['GEN','EXO','LEV','JDG','SA1','SA2','KI1','KI2','MAL','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','PE1','PE2','JAM','JDE','REV']
        results = self.bbnss.getBooksNamesSystem( "eng_traditional", sampleBookList )
        self.assertTrue( isinstance( results, tuple ) )
        self.assertEqual( len(results), 5 ) # The dictionaries
        self.assertTrue( isinstance( results[0], dict ) and 5 < len(results[0]) < 10 )
        self.assertTrue( isinstance( results[1], dict ) and 5 < len(results[1]) < 10 )
        self.assertTrue( isinstance( results[2], dict ) and len(results[2]) == len(sampleBookList) )
        self.assertTrue( isinstance( results[3], OrderedDict ) and 300 < len(results[3]) < 400 )
        self.assertTrue( isinstance( results[4], OrderedDict ) and 1000 < len(results[4]) < 2000 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        self.assertEqual( self.bbnss.getBooksNamesSystem('SomeName', sampleBookList), None )
    # end of test_2060_getBooksNamesSystem
# end of BibleBooksNamesSystemsTests class


class BibleBooksNamesSystemTests( unittest.TestCase ):
    """ Unit tests for the BibleBooksNamesSystem object. """

    def setUp( self ):
        # Create a BibleBooksNamesSystem object
        self.systemName = "eng_traditional"
        sampleBookList = ['GEN','EXO','LEV','NUM','DEU','JOS','JDG','SA1','SA2','KI1','KI2','ZEC','MAL']
        self.bbns = BibleBooksNames.BibleBooksNamesSystem( self.systemName, sampleBookList ) # Doesn't reload the XML unnecessarily :)

    def test_3010_str( self ):
        """ Test the __str__ function. """
        result = str( self.bbns )
        self.assertTrue( isinstance( result, str ) )
        self.assertTrue( len(result) > 20 )
    # end of test_3010_str

    def test_3020_getBooksNamesSystemName( self ):
        """ Test the getBooksNamesSystemName function. """
        self.assertEqual( self.bbns.getBooksNamesSystemName(), self.systemName )
    # end of test_3020_getBooksNamesSystemName

    def test_3030_getBookName( self ):
        """ Test the getBookName function. """
        for BBB,name in (('GEN','Genesis',),('EXO','Exodus'),('MAL','Malachi'),):
            result = self.bbns.getBookName( BBB )
            self.assertEqual( result, name )
        for badBBB in ('Gen','XYZ','MAT','REV',):
            self.assertRaises( KeyError, self.bbns.getBookName, badBBB )
    # end of test_3030_getBookName

    def test_3040_getBookAbbreviation( self ):
        """ Test the getBookAbbreviation function. """
        for BBB,name in (('GEN','Gen',),('EXO','Exo'),('MAL','Mal'),):
            result = self.bbns.getBookAbbreviation( BBB )
            self.assertEqual( result, name )
        for badBBB in ('Gen','XYZ','MAT','REV',):
            self.assertRaises( KeyError, self.bbns.getBookAbbreviation, badBBB )
    # end of test_3040_getBookAbbreviation

    def test_3050_getBBB( self ):
        """ Test the getBBB function. """
        tests = ( ('GEN',('GEN','Gen','Ge','G')),    ('EXO',('Exo','Exd','eX','E','e')),    ('MAL',('Mal','MALACHI','MaLaChI')), )
        for BBB,inputs in tests:
            for thisInput in inputs:
                result = self.bbns.getBBB( thisInput )
                self.assertEqual( result, BBB )
        for badInput in ('XYZ','MAT','REV',):
            self.assertEqual( self.bbns.getBBB(badInput), None )
    # end of test_3050_getBBB

    def test_3060_getDivisionAbbreviation( self ):
        """ Test the getDivisionAbbreviation function. """
        tests = ( ('OT',('OT','Ot','oT','Old', 'oLdTeSt')), )
        for divisionStandardAbbreviation,inputs in tests:
            for thisInput in inputs:
                result = self.bbns.getDivisionAbbreviation( thisInput )
                self.assertEqual( result, divisionStandardAbbreviation )
        for badInput in ('XYZ','GEN','MAT','REV','NT','Nt','nT','NewTest','nEwTeS','Pauline','Pa','Pl'): # Note: there's no NT in sampleBookList above
            self.assertEqual( self.bbns.getDivisionAbbreviation(badInput), None )
    # end of test_3060_getDivisionAbbreviation

    def test_3070_getDivisionBooklist( self ):
        """ Test the getDivisionBooklist function. """
        tests = ( ('OT',('OT','Ot','oT','Old', 'oLdTeSt')), )
        for divisionStandardAbbreviation,inputs in tests:
            for thisInput in inputs:
                result = self.bbns.getDivisionBooklist( thisInput )
                self.assertTrue( isinstance( result, list ) )
                self.assertEqual( len(result), 39 )
        for badInput in ('XYZ','GEN','MAT','REV','NT','Nt','nT','NewTest','nEwTeS','Pauline','Pa','Pl'): # Note: there's no NT in sampleBookList above
            self.assertEqual( self.bbns.getDivisionBooklist(badInput), None )
    # end of test_3070_getDivisionBooklist
# end of BibleBooksNamesSystemTests class


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    if Globals.verbosityLevel > 1: print( ProgNameVersion )

    unittest.main() # Automatically runs all of the above tests
# end of BibleBooksNamesTests.py