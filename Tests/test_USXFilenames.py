#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USXFilenamesTests.py
#
# Module testing USXFilenames.py
#
# Copyright (C) 2012-2019 Robert Hunt
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
Module testing USXFilenames.py.
"""

lastModifiedDate = '2019-12-29' # by RJH
programName = "USX Filenames tests"
programVersion = '0.51'
programNameVersion = f'{programName} v{programVersion}'


import os
import unittest
import sys

sourceFolder = os.path.join( os.path.dirname(__file__), '../BibleOrgSys/' )
if sourceFolder not in sys.path:
    sys.path.append( sourceFolder ) # So we can run it from the above folder and still do these imports

import BibleOrgSysGlobals
import InputOutput.USXFilenames as USXFilenames


class USXFilenamesTests1( unittest.TestCase ):
    """ Unit tests for the USXFilenames object. """

    def setUp( self ):
        testFolder = 'Tests/DataFilesForTests/USXTest1/' # This is a RELATIVE path
        if os.access( testFolder, os.R_OK ): # Create the USXFilenames object
            self.UFns = USXFilenames.USXFilenames( testFolder )
        else: print( "Sorry, test folder {!r} doesn't exist on this computer.".format( testFolder ) )

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
        self.assertEqual( len(result), 6 )
        self.assertFalse( ' ' in result )
        self.assertFalse( '.' in result )
        self.assertEqual( result, 'dddBBB' )
    # end of test_015_getFilenameTemplate

    def test_020_getPossibleFilenameTuples( self ):
        """ Test the getPossibleFilenameTuples function. """
        results = self.UFns.getPossibleFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 3 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertEqual( len(result[1]), 10 ) # Filename, e.g., 008RUT.usx
    # end of test_020_getPossibleFilenameTuples

    def test_030_getConfirmedFilenameTuples( self ):
        """ Test the getConfirmedFilenameTuples function. """
        results = self.UFns.getConfirmedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 3 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertEqual( len(result[1]), 10 ) # Filename, e.g., 08RUT.usx
    # end of test_030_getConfirmedFilenameTuples

    def test_040_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 2 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_040_getUnusedFilenames

    #def test_050_getSSFFilenames( self ):
    #    """ Test the getSSFFilenames function. """
    #    results = self.UFns.getSSFFilenames()
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertEqual( results, [] ) # Should be no SSF files in a standard USX project folder

    #    results = self.UFns.getSSFFilenames( False ) # Should give exactly the same result as above
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertEqual( results, [] ) # Should be no SSF files in a standard USX project folder

    #    results = self.UFns.getSSFFilenames( True )
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertGreater( len(results), 0 ) # Should be at least one SSF file in a standard USX project folder
    #    self.assertFalse( None in results )
    #    self.assertFalse( '' in results )
    #    for result in results:
    #        self.assertTrue( isinstance( result, str ) )
    ## end of test_050_getSSFFilenames
# end of USXFilenamesTests1 class



class USXFilenamesTests2( unittest.TestCase ):
    """ Unit tests for the USXFilenames object. """

    def setUp( self ):
        testFolder = 'Tests/DataFilesForTests/USXTest2/' # This is a RELATIVE path
        if os.access( testFolder, os.R_OK ): # Create the USXFilenames object
            self.UFns = USXFilenames.USXFilenames( testFolder )
        else: print( "Sorry, test folder {!r} doesn't exist on this computer.".format( testFolder ) )

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
        self.assertEqual( len(result), 6 )
        self.assertFalse( ' ' in result )
        self.assertFalse( '.' in result )
        self.assertEqual( result, 'dddBBB' )
    # end of test_015_getFilenameTemplate

    def test_020_getPossibleFilenameTuples( self ):
        """ Test the getPossibleFilenameTuples function. """
        results = self.UFns.getPossibleFilenameTuples()
        print("results", len(results), results)
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 66 )
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertEqual( len(result[1]), 10 ) # Filename, e.g., 008RUT.usx
    # end of test_020_getPossibleFilenameTuples

    def test_030_getConfirmedFilenameTuples( self ):
        """ Test the getConfirmedFilenameTuples function. """
        results = self.UFns.getConfirmedFilenameTuples()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 66 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, tuple ) )
            self.assertEqual( len(result), 2 )
            self.assertEqual( len(result[0]), 3 ) # BBB
            self.assertEqual( len(result[1]), 10 ) # Filename, e.g., 08RUT.usx
    # end of test_030_getConfirmedFilenameTuples

    def test_040_getUnusedFilenames( self ):
        """ Test the getUnusedFilenames function. """
        results = self.UFns.getUnusedFilenames()
        self.assertTrue( isinstance( results, list ) )
        self.assertEqual( len(results), 0 ) # Number of actual files found
        self.assertFalse( None in results )
        self.assertFalse( '' in results )
        for result in results:
            self.assertTrue( isinstance( result, str ) )
    # end of test_040_getUnusedFilenames

    #def test_050_getSSFFilenames( self ):
    #    """ Test the getSSFFilenames function. """
    #    results = self.UFns.getSSFFilenames()
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertEqual( results, [] ) # Should be no SSF files in a standard USX project folder

    #    results = self.UFns.getSSFFilenames( False ) # Should give exactly the same result as above
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertEqual( results, [] ) # Should be no SSF files in a standard USX project folder

    #    results = self.UFns.getSSFFilenames( True )
    #    self.assertTrue( isinstance( results, list ) )
    #    self.assertGreater( len(results), 0 ) # Should be at least one SSF file in a standard USX project folder
    #    self.assertFalse( None in results )
    #    self.assertFalse( '' in results )
    #    for result in results:
    #        self.assertTrue( isinstance( result, str ) )
    ## end of test_050_getSSFFilenames
# end of USXFilenamesTests2 class


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    # Make sure you set the testFolder in setUp above
    unittest.main() # Automatically runs all of the above tests
# end of USXFilenamesTests.py
