#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMFilenamesTests.py
#   Last modified: 2013-06-24 by RJH (also update ProgVersion below)
#
# Module testing USFMFilenames.py
#
# Copyright (C) 2011-2013 Robert Hunt
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
Module testing USFMFilenames.py.
"""

ProgName = "USFM Filenames tests"
ProgVersion = "0.55"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import sys, os, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, USFMFilenames


class USFMFilenamesTests1( unittest.TestCase ):
    """ Unit tests for the USFMFilenames object. """

    def setUp( self ):
        testFolder = 'Tests/DataFilesForTests/USFMTest1/' # This is a RELATIVE path
        if os.access( testFolder, os.R_OK ): # Create the USFMFilenames object
            self.UFns = USFMFilenames.USFMFilenames( testFolder )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UFns )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        result = len( self.UFns ) # Should be zero coz we haven't tried to get any lists yet
        self.assertEqual( result, 0 )
        junkResults = self.UFns.getConfirmedFilenameTuples()
        result = len( self.UFns )
        self.assertTrue( isinstance( result, int ) )
        self.assertGreater( result, 2 )
    # end of test_020_len

    def test_030_getFilenameTemplate( self ):
        """ Test the getFilenameTemplate function. """
        result = self.UFns.getFilenameTemplate()
        self.assertTrue( isinstance( result, str ) )
        self.assertEqual( len(result), 8 )
        self.assertFalse( ' ' in result )
        self.assertFalse( '.' in result )
        self.assertTrue( 'dd' in result )
        self.assertTrue( 'lll' in result or 'LLL' in result )
        self.assertTrue( 'bbb' in result or 'BBB' in result )
    # end of test_030_getFilenameTemplate

    def test_040_getDerivedFilenameTuples( self ):
        """ Test the getDerivedFilenameTuples function. """
        results = self.UFns.getDerivedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 3 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_040_getDerivedFilenameTuples

    def test_050_getConfirmedFilenameTuples( self ):
        """ Test the getConfirmedFilenameTuples function. """
        results = self.UFns.getConfirmedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_050_getConfirmedFilenames

    def test_052_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getConfirmedFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 4 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_052_getUnusedFilenames

    def test_060_getPossibleFilenameTuplesExt( self ):
        """ Test the getPossibleFilenameTuplesExt function. """
        results = self.UFns.getPossibleFilenameTuplesExt()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_060_getPossibleFilenameTuplesExt

    def test_062_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesExt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 4 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_062_getUnusedFilenames

    def test_070_getPossibleFilenameTuplesInt( self ):
        """ Test the getPossibleFilenameTuplesInt function. """
        results = self.UFns.getPossibleFilenameTuplesInt()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 3 ) # Number of actual files found (not four coz one test file is empty and one id is wrong)
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_070_getPossibleFilenameTuplesInt

    def test_072_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesInt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 5 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_072_getUnusedFilenames

    def test_080_getMaximumPossibleFilenameTuples( self ):
        """ Test the getMaximumPossibleFilenameTuples function. """
        results = self.UFns.getMaximumPossibleFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_080_getMaximumPossibleFilenameTuples

    def test_082_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getMaximumPossibleFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 4 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_082_getUnusedFilenames

    def test_090_getSSFFilenames( self ):
        """ Test the getSSFFilenames function. """
        results = self.UFns.getSSFFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( results, [] ) # Should be no SSF files in a standard USFM project folder

        results = self.UFns.getSSFFilenames( False ) # Should give exactly the same result as above
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( results, [] ) # Should be no SSF files in a standard USFM project folder

        results = self.UFns.getSSFFilenames( True )
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 0 ) # Should be at least one SSF file in a standard USFM project folder
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_090_getSSFFilenames
# end of USFMFilenamesTests1 class


class USFMFilenamesTests2( unittest.TestCase ):
    """ Unit tests for the USFMFilenames object. """

    def setUp( self ):
        testFolder = 'Tests/DataFilesForTests/USFMTest2/' # This is a RELATIVE path
        if os.access( testFolder, os.R_OK ): # Create the USFMFilenames object
            self.UFns = USFMFilenames.USFMFilenames( testFolder )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UFns )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
    # end of test_010_str

    def test_020_len( self ):
        """ Test the __len__ function. """
        result = len( self.UFns ) # Should be zero coz we haven't tried to get any lists yet
        self.assertEqual( result, 0 )
        junkResults = self.UFns.getConfirmedFilenameTuples()
        result = len( self.UFns )
        self.assertTrue( isinstance( result, int ) )
        self.assertGreater( result, 2 )
    # end of test_020_len

    def test_030_getFilenameTemplate( self ):
        """ Test the getFilenameTemplate function. """
        result = self.UFns.getFilenameTemplate()
        self.assertTrue( isinstance( result, str ) )
        self.assertEqual( len(result), 8 )
        self.assertFalse( ' ' in result )
        self.assertFalse( '.' in result )
        self.assertTrue( 'dd' in result )
        self.assertTrue( 'lll' in result or 'LLL' in result )
        self.assertTrue( 'bbb' in result or 'BBB' in result )
    # end of test_030_getFilenameTemplate

    def test_040_getDerivedFilenameTuples( self ):
        """ Test the getDerivedFilenameTuples function. """
        results = self.UFns.getDerivedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 3 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_040_getDerivedFilenameTuples

    def test_050_getConfirmedFilenameTuples( self ):
        """ Test the getConfirmedFilenameTuples function. """
        results = self.UFns.getConfirmedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_050_getConfirmedFilenames

    def test_052_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getConfirmedFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 13 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_052_getUnusedFilenames

    def test_060_getPossibleFilenameTuplesExt( self ):
        """ Test the getPossibleFilenameTuplesExt function. """
        results = self.UFns.getPossibleFilenameTuplesExt()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_060_getPossibleFilenameTuplesExt

    def test_062_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesExt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 14 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_062_getUnusedFilenames

    def test_070_getPossibleFilenameTuplesInt( self ):
        """ Test the getPossibleFilenameTuplesInt function. """
        results = self.UFns.getPossibleFilenameTuplesInt()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 26 ) # Number of actual files found (not four coz one test file is empty and one id is wrong)
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_070_getPossibleFilenameTuplesInt

    def test_072_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesInt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 13 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_072_getUnusedFilenames

    def test_080_getMaximumPossibleFilenameTuples( self ):
        """ Test the getMaximumPossibleFilenameTuples function. """
        results = self.UFns.getMaximumPossibleFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_080_getMaximumPossibleFilenameTuples

    def test_082_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getMaximumPossibleFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 13 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_082_getUnusedFilenames

    def test_090_getSSFFilenames( self ):
        """ Test the getSSFFilenames function. """
        results = self.UFns.getSSFFilenames()
        self.assertTrue( isinstance( results, list ) )
        #self.assertEqual( results, [] ) # Should be no SSF files in a standard USFM project folder

        results = self.UFns.getSSFFilenames( False ) # Should give exactly the same result as above
        self.assertTrue( isinstance( results, list ) )
        #self.assertEqual( results, [] ) # Should be no SSF files in a standard USFM project folder

        results = self.UFns.getSSFFilenames( True )
        self.assertTrue( isinstance( results, list ) )
        self.assertGreater( len(results), 0 ) # Should be at least one SSF file in a standard USFM project folder
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_090_getSSFFilenames
# end of USFMFilenamesTests2 class


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( ProgNameVersion )

    # Make sure you set the testFolder in setUp above
    unittest.main() # Automatically runs all of the above tests
# end of USFMFilenamesTests.py