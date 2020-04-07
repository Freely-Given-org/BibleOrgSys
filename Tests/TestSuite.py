#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# TestSuite.py
#   Last modified: 2014-12-15 by RJH (also update PROGRAM_VERSION below)
#
# Suite for testing BibleOrgSys
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
Suite testing BibleOrgSys.
"""

LAST_MODIFIED_DATE = '2020-04-06' # by RJH
PROGRAM_NAME = "Bible Organisational System test suite"
PROGRAM_VERSION = '0.13'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


import os.path
import sys
import unittest


sourceFolder = os.path.join( os.path.dirname(__file__), '../BibleOrgSys/' )
sys.path.insert( 0, sourceFolder )

if __name__ == '__main__':
    sys.path.insert( 0, os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) # So we can run it from the above folder and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys import BibleBooksCodesTests
from BibleOrgSys import BibleBookOrdersTests
import ISO_639_3_LanguagesTests, BiblePunctuationSystemsTests
from BibleOrgSys import BibleBooksNamesTests, BibleVersificationSystemsTests, BibleOrganisationalSystemsTests
from BibleOrgSys import BibleReferencesTests
import USFMMarkersTests, USFMFilenamesTests, USXFilenamesTests


# Handle command line parameters (for compatibility)
# Configure basic set-up
parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )


# Create the test suite
suiteList = []

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBooksCodesTests.BibleBooksCodesConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBooksCodesTests.BibleBooksCodesTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( ISO_639_3_LanguagesTests.ISO_639_3_LanguagesConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( ISO_639_3_LanguagesTests.ISO_639_3_LanguagesTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBookOrdersTests.BibleBookOrdersConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBookOrdersTests.BibleBookOrderSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBookOrdersTests.BibleBookOrderSystemTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BiblePunctuationSystemsTests.BiblePunctuationSystemsConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BiblePunctuationSystemsTests.BiblePunctuationSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BiblePunctuationSystemsTests.BiblePunctuationSystemTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBooksNamesTests.BibleBooksNamesConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBooksNamesTests.BibleBooksNamesSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleBooksNamesTests.BibleBooksNamesSystemTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleVersificationSystemsTests.BibleVersificationSystemsConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleVersificationSystemsTests.BibleVersificationSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleVersificationSystemsTests.BibleVersificationSystemTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganisationalSystemsTests.BibleOrganisationalSystemsConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganisationalSystemsTests.BibleOrganisationalSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganisationalSystemsTests.BibleOrganisationalSystemTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleReferencesTests.BibleReferencesTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USFMMarkersTests.USFMMarkersConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USFMMarkersTests.USFMMarkersTests ) )

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USFMFilenamesTests.USFMFilenamesTests1 ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USFMFilenamesTests.USFMFilenamesTests2 ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USXFilenamesTests.USXFilenamesTests1 ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( USXFilenamesTests.USXFilenamesTests2 ) )


# Now run all the tests in the suite
allTests = unittest.TestSuite( suiteList )
unittest.TextTestRunner(verbosity=2).run( allTests )

# end of TestSuite.py
