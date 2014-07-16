#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# TestSuite.py
#   Last modified: 2013-08-28 by RJH (also update ProgVersion below)
#
# Suite for testing BibleOrgSys
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
Suite testing BibleOrgSys.
"""

ProgName = "Bible Organisational System test suite"
ProgVersion = "0.12"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import sys, unittest


sourceFolder = "."
sys.path.append( sourceFolder )

import Globals
import BibleBooksCodesTests, BibleBookOrdersTests
import ISO_639_3_LanguagesTests, BiblePunctuationSystemsTests
import BibleBooksNamesTests, BibleVersificationSystemsTests, BibleOrganizationalSystemsTests
import BibleReferencesTests
import USFMMarkersTests, USFMFilenamesTests, USXFilenamesTests


# Handle command line parameters (for compatibility)
# Configure basic set-up
parser = Globals.setup( ProgName, ProgVersion )
Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

if Globals.verbosityLevel > 1: print( ProgNameVersion )


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

suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganizationalSystemsTests.BibleOrganizationalSystemsConverterTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganizationalSystemsTests.BibleOrganizationalSystemsTests ) )
suiteList.append( unittest.TestLoader().loadTestsFromTestCase( BibleOrganizationalSystemsTests.BibleOrganizationalSystemTests ) )

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