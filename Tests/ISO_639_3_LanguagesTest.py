#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ISO_639_3_LanguagesTest.py
#
# Module testing ISO_639_3_Languages.py
#   Last modified: 2011-02-03 (also update versionString below)
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
Module testing ISO_639_3_Languages.py.
"""

progName = "ISO-639-3 language code tests"
versionString = "0.81"


import sys, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, ISO_639_3_Languages


class ISO_639_3_LanguagesConverterTests( unittest.TestCase ):
    """ Unit tests for the _ISO_639_3_LanguagesConverter object. """

    def setUp( self ):
        # Create the ISO_639_3_LanguagesConverter object
        self.isoLgC = ISO_639_3_Languages._ISO_639_3_LanguagesConverter().loadAndValidate() # Doesn't reload the XML unnecessarily :)

    def test_010_len( self ):
        """ Test the __len__ function. """
        self.assert_( 6000 < len(self.isoLgC) < 8000 ) # The number of loaded systems
    # end of test_010_len

    def test_020_importDataToPython( self ):
        """ Test the importDataToPython function. """
        result = self.isoLgC.importDataToPython()
        self.assert_( isinstance( result, tuple ) )
        self.assertEqual( len(result), 2 )
    # end of test_020_importDataToPython

    def test_030_exportDataToPython( self ):
        """ Test the exportDataToPython function. """
        self.assertEqual( self.isoLgC.exportDataToPython(), None ) # Basically just make sure that it runs
    # end of test_020_importDataToPython

    def test_040_exportDataToJSON( self ):
        """ Test the exportDataToJSON function. """
        self.assertEqual( self.isoLgC.exportDataToJSON(), None ) # Basically just make sure that it runs
    # end of test_040_exportDataToJSON

    def test_050_exportDataToC( self ):
        """ Test the exportDataToC function. """
        self.assertEqual( self.isoLgC.exportDataToC(), None ) # Basically just make sure that it runs
    # end of test_050_exportDataToC
# end of ISO_639_3_LanguagesConverterTests class


class ISO_639_3_LanguagesTests( unittest.TestCase ):
    """ Unit tests for the ISO_639_3_Languages object. """

    goodCodes = ('aba','eng','mbt','ara','aaa','zzj',)
    badCodes = ('abaa','Eng','qwq','zzz','17','123',)

    def setUp( self ):
        # Create the ISO_639_3_Languages object
        self.isoLgs = ISO_639_3_Languages.ISO_639_3_Languages().loadData() # Doesn't reload the XML unnecessarily :)

    def test_010_len( self ):
        """ Test the __len__ function. """
        self.assert_( len(self.isoLgs) > 7000 )
    # end of test_010_len

    def test_020_isValidLanguageCode( self ):
        """ Test the isValidLanguageCode function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            self.assertTrue( self.isoLgs.isValidLanguageCode( goodCode ) )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertFalse( self.isoLgs.isValidLanguageCode( badCode ) )
    # end of test_020_isValidLanguageCode

    def test_030_getLanguageName( self ):
        """ Test the getLanguageName function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            result = self.isoLgs.getLanguageName( goodCode )
            self.assert_( isinstance( result, str ) )
            self.assert_( len(result) > 2 )
        self.assertEqual( self.isoLgs.getLanguageName( 'eng' ), 'English' )
        self.assertEqual( self.isoLgs.getLanguageName( 'deu' ), 'German' )
        self.assertEqual( self.isoLgs.getLanguageName( 'mqk' ), 'Manobo, Rajah Kabunsuwan' )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertRaises( KeyError, self.isoLgs.getLanguageName, badCode )
    # end of test_030_getLanguageName

    def test_040_getScope( self ):
        """ Test the getScope function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            result = self.isoLgs.getScope( goodCode )
            self.assert_( isinstance( result, str ) )
            self.assert_( len(result) == 1 )
            self.assert_( result in ('I','M','S',) )
        self.assertEqual( self.isoLgs.getScope( 'eng' ), 'I' )
        self.assertEqual( self.isoLgs.getScope( 'deu' ), 'I' )
        self.assertEqual( self.isoLgs.getScope( 'mqk' ), 'I' )
        self.assertEqual( self.isoLgs.getScope( 'aka' ), 'M' )
        self.assertEqual( self.isoLgs.getScope( 'mis' ), 'S' )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertRaises( KeyError, self.isoLgs.getScope, badCode )
    # end of test_040_getScope

    def test_050_getType( self ):
        """ Test the getType function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            result = self.isoLgs.getType( goodCode )
            self.assert_( isinstance( result, str ) )
            self.assert_( len(result) == 1 )
            self.assert_( result in ('A','C','E','H','L','S',) )
        self.assertEqual( self.isoLgs.getType( 'eng' ), 'L' )
        self.assertEqual( self.isoLgs.getType( 'deu' ), 'L' )
        self.assertEqual( self.isoLgs.getType( 'mqk' ), 'L' )
        self.assertEqual( self.isoLgs.getType( 'zzj' ), 'L' )
        self.assertEqual( self.isoLgs.getType( 'akk' ), 'A' )
        self.assertEqual( self.isoLgs.getType( 'avk' ), 'C' )
        self.assertEqual( self.isoLgs.getType( 'avs' ), 'E' )
        self.assertEqual( self.isoLgs.getType( 'axm' ), 'H' )
        self.assertEqual( self.isoLgs.getType( 'mis' ), 'S' )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertRaises( KeyError, self.isoLgs.getType, badCode )
    # end of test_050_getScope

    def test_060_getPart1Code( self ):
        """ Test the getPart1Code function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            result = self.isoLgs.getPart1Code( goodCode )
            if result is not None:
                self.assert_( isinstance( result, str ) )
                self.assert_( len(result) == 2 )
        self.assertEqual( self.isoLgs.getPart1Code( 'eng' ), 'en' )
        self.assertEqual( self.isoLgs.getPart1Code( 'deu' ), 'de' )
        self.assertEqual( self.isoLgs.getPart1Code( 'mqk' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'zzj' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'akk' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'avk' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'avs' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'axm' ), None )
        self.assertEqual( self.isoLgs.getPart1Code( 'mis' ), None )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertRaises( KeyError, self.isoLgs.getPart1Code, badCode )
    # end of test_060_getPart1Code

    def test_070_getPart2Code( self ):
        """ Test the getPart2Code function. """
        for goodCode in ISO_639_3_LanguagesTests.goodCodes:
            result = self.isoLgs.getPart2Code( goodCode )
            if result is not None:
                self.assert_( isinstance( result, str ) )
                self.assert_( len(result) == 3 )
        self.assertEqual( self.isoLgs.getPart2Code( 'eng' ), 'eng' )
        self.assertEqual( self.isoLgs.getPart2Code( 'deu' ), 'ger' )
        self.assertEqual( self.isoLgs.getPart2Code( 'mqk' ), None )
        self.assertEqual( self.isoLgs.getPart2Code( 'zzj' ), None )
        self.assertEqual( self.isoLgs.getPart2Code( 'akk' ), 'akk' )
        self.assertEqual( self.isoLgs.getPart2Code( 'avk' ), None )
        self.assertEqual( self.isoLgs.getPart2Code( 'avs' ), None )
        self.assertEqual( self.isoLgs.getPart2Code( 'axm' ), None )
        self.assertEqual( self.isoLgs.getPart2Code( 'mis' ), 'mis' )
        for badCode in ISO_639_3_LanguagesTests.badCodes:
            self.assertRaises( KeyError, self.isoLgs.getPart2Code, badCode )
    # end of test_070_getPart1Code

    def test_080_getLanguageCode( self ):
        """ Test the getLanguageCode function. """
        for goodName in ('English','english','ENGLISH','French','German','Manobo, Matigsalug',):
            result = self.isoLgs.getLanguageCode( goodName )
            self.assert_( isinstance( result, str ) )
            self.assert_( len(result) == 3 )
        self.assertEqual( self.isoLgs.getLanguageCode( 'eng' ), None )
        self.assertEqual( self.isoLgs.getLanguageCode( 'English' ), 'eng' )
        self.assertEqual( self.isoLgs.getLanguageCode( 'German' ), 'deu' )
        for badName in ('Deutsch','Francais','SomeName',):
            self.assertEqual( self.isoLgs.getLanguageCode(badName), None )
    # end of test_080_getScope

    def test_090_getNameMatches( self ):
        """ Test the getNameMatches function. """
        for goodName in ('English','english','ENGLISH','French','German','Manobo, Matigsalug',):
            result = self.isoLgs.getNameMatches( goodName )
            self.assert_( isinstance( result, list ) )
        self.assert_( len(self.isoLgs.getNameMatches( 'eng' )) > 20 )
        self.assert_( len(self.isoLgs.getNameMatches( 'English' )) > 20 )
        self.assertEqual( self.isoLgs.getNameMatches( 'stupid' ), [] )
        for badName in ('Deutschen','Francais','SomeName',):
            self.assertEqual( self.isoLgs.getNameMatches(badName), [] )
    # end of test_090_getScope
# end of ISO_639_3_LanguagesTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    unittest.main() # Automatically runs all of the above tests
# end of ISO_639_3_LanguagesTest.py
