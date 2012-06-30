#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMFilenamesTests.py
#   Last modified: 2012-06-30 by RJH (also update versionString below)
#
# Module testing USFMFilenames.py
#
# Copyright (C) 2011-2012 Robert Hunt
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
Module testing USFMFilenames.py.
"""

progName = "USFM Filenames tests"
versionString = "0.54"


import sys, os, unittest

sourceFolder = "."
sys.path.append( sourceFolder )
import Globals, USFMFilenames


class USFMFilenamesTests( unittest.TestCase ):
    """ Unit tests for the USFMFilenames object. """

    def setUp( self ):
        testFolder = 'Tests/DataFilesForTests/USFMTest/' # This is a RELATIVE path
        if os.access( testFolder, os.R_OK ): # Create the USFMFilenames object
            self.UFns = USFMFilenames.USFMFilenames( testFolder )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

    def test_010_str( self ):
        """ Test the __str__ function. """
        result = str( self.UFns )
        self.assertTrue( isinstance( result, str ) )
        self.assertGreater( len(result), 20 )
    # end of test_010_str

    def test_015_getFilenameTemplate( self ):
        """ Test the getFilenameTemplate function. """
        result = self.UFns.getFilenameTemplate()
        self.assertTrue( isinstance( result, str ) )
        self.assertEqual( len(result), 8 )
        self.assertFalse( ' ' in result )
        self.assertFalse( '.' in result )
        self.assertTrue( 'dd' in result )
        self.assertTrue( 'lll' in result or 'LLL' in result )
        self.assertTrue( 'bbb' in result or 'BBB' in result )
    # end of test_015_getFilenameTemplate

    def test_020_getDerivedFilenameTuples( self ):
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
    # end of test_020_getDerivedFilenameTuples

    def test_030_getConfirmedFilenameTuples( self ):
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
    # end of test_030_getConfirmedFilenames

    def test_031_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getConfirmedFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_031_getUnusedFilenames

    def test_040_getPossibleFilenameTuplesExt( self ):
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
    # end of test_040_getPossibleFilenameTuplesExt

    def test_041_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesExt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_041_getUnusedFilenames

    def test_050_getPossibleFilenameTuplesInt( self ):
        """ Test the getPossibleFilenameTuplesInt function. """
        results = self.UFns.getPossibleFilenameTuplesInt()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 0 ) # Number of actual files found (none coz our test files are empty)
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertGreater( len(result[1]), 10 ) # Filename, e.g., lll08RUT.SCP
    # end of test_050_getPossibleFilenameTuplesInt

    def test_051_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getPossibleFilenameTuplesInt()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 5 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_051_getUnusedFilenames

    def test_060_getMaximumPossibleFilenameTuples( self ):
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
    # end of test_060_getMaximumPossibleFilenameTuples

    def test_061_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        junkResults = self.UFns.getMaximumPossibleFilenameTuples()
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_061_getUnusedFilenames

    def test_070_getSSFFilenames( self ):
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
    # end of test_070_getSSFFilenames
# end of USFMFilenamesTests class


if __name__ == '__main__':
    # Handle command line parameters (for compatibility)
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    # Make sure you set the testFolder in setUp above
    unittest.main() # Automatically runs all of the above tests
# end of USFMFilenamesTests.py
