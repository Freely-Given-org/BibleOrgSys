#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: MPL-2.0
#
# TestSuite.py
#   Last modified: 2014-12-15 by RJH (also update PROGRAM_VERSION below)
#
# Suite for testing BibleOrgSys
#
# Copyright (C) 2011-2014 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Suite testing BibleOrgSys.
"""
import os.path
import sys
import unittest


from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys import BibleBookOrdersTests
import ISO_639_3_LanguagesTests, BiblePunctuationSystemsTests
from BibleOrgSys import BibleBooksNamesTests, BibleVersificationSystemsTests, BibleOrganisationalSystemsTests
from BibleOrgSys import BibleReferencesTests
import USFMMarkersTests, USFMFilenamesTests, USXFilenamesTests


LAST_MODIFIED_DATE = '2020-04-06' # by RJH
PROGRAM_NAME = "Bible Organisational System test suite"
PROGRAM_VERSION = '0.13'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Handle command line parameters (for compatibility)
# Configure basic set-up
parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

vPrint( 'Normal', DEBUGGING_THIS_MODULE, PROGRAM_NAME_VERSION )


# Create the test suite
suiteList = []

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
