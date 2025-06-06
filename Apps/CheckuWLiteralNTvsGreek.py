#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# CheckuWLiteralNTvsGreek.py
#
# Command-line app to download the UGNT and ULT from the Door43 Resource Catalog
#   and then do some automated comparisons of the two texts.
#
# Copyright (C) 2019-2025 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
A short command-line app as part of BOS (Bible Organisational System) demos.
This app downloads both a Greek New Testament and a literal English translation
    from the online Door43 Resource Catalog
    and then compares the texts of the two versions verse by verse.

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app can be run from your BOS folder,
    e.g., using the command:
        Apps/CheckuWLiteralNTvsGreek.py

You can discover the version with
        Apps/CheckuWLiteralNTvsGreek.py --version

You can discover the available command line parameters with
        Apps/CheckuWLiteralNTvsGreek.py --help

    e.g., for verbose mode
        Apps/CheckuWLiteralNTvsGreek.py --verbose
    or
        Apps/CheckuWLiteralNTvsGreek.py -v

This app also demonstrates how little actual code is required to use the BOS to load an online Bible
    and then to process it verse by verse.

The (Python3) BOS is developed and well-tested on Linux (Ubuntu)
    but also runs on Windows and OS-X (although not so well tested).
"""
# from gettext import gettext as _
import logging

# Allow the system to find the BOS even when the app is down in its own folder
if __name__ == '__main__':
    import os, sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
from BibleOrgSys.Online.Door43OnlineCatalog import Door43CatalogResources, Door43CatalogBible


LAST_MODIFIED_DATE = '2025-02-08' # by RJH
SHORT_PROGRAM_NAME = "CheckuWLiteralNTvsGreek"
PROGRAM_NAME = "Check unfoldingWord Literal NT vs Greek"
PROGRAM_VERSION = '0.04'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


DEBUGGING_THIS_MODULE = False



def main() -> None:
    """
    This is the main program for the app

    Note that the standard verbosityLevel is 2:
        -s (silent) is 0
        -q (quiet) is 1
        -i (information) is 3
        -v (verbose) is 4.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Download the online Door43 Resource Catalog
    door43CatalogResources = Door43CatalogResources()
    vPrint( 'Info', DEBUGGING_THIS_MODULE, door43CatalogResources )
    door43CatalogResources.fetchCatalog()
    vPrint( 'Info', DEBUGGING_THIS_MODULE, '\n{door43CatalogResources}\n\n' )

    # Download and load all books from the UGNT = unfoldingWord® Greek New Testament
    UGNTDict = door43CatalogResources.searchBibles( 'el-x-koine', 'unfoldingWord® Greek New Testament' )
    if UGNTDict:
        Door43CatalogUGNTBible = Door43CatalogBible( UGNTDict )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, Door43CatalogUGNTBible )
        Door43CatalogUGNTBible.preload()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, Door43CatalogUGNTBible )
        Door43CatalogUGNTBible.load()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, Door43CatalogUGNTBible, end='\n\n' )
    assert len(Door43CatalogUGNTBible) == 27, f"{len(Door43CatalogUGNTBible)=}"

    # Download the ULT = unfoldingWord® Literal Text
    ULTDict = door43CatalogResources.searchBibles( 'en', 'unfoldingWord® Literal Text' )
    if ULTDict:
        Door43CatalogULTBible = Door43CatalogBible( ULTDict )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, Door43CatalogULTBible )
        Door43CatalogULTBible.preload()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, Door43CatalogULTBible, end='\n\n' )
    assert len(Door43CatalogULTBible) == 66, f"{len(Door43CatalogULTBible)=}"

    # Go through the UGNT verse by verse
    #   and do some comparisions with the matching ULT verses
    # NOTE: This code assumes matching versification systems
    count1 = count2 = 0
    for BBB, UGNTBook in Door43CatalogUGNTBible.books.items():
        for C in range( 1, Door43CatalogUGNTBible.getNumChapters( BBB )+1 ):
            for V in range( 1, Door43CatalogUGNTBible.getNumVerses( BBB, C )+1 ):
                ref = SimpleVerseKey( BBB, C, V )
                text1 = Door43CatalogUGNTBible.getVerseText( ref, fullTextFlag=False )
                if not text1:
                    logging.error( f"Blank text at {ref.getShortText()} in UGNT" )
                try:
                    # NOTE: The following line will automatically load the ULT book into memory as required
                    text2 = Door43CatalogULTBible.getVerseText( ref, fullTextFlag=False )
                    if not text2:
                        logging.error( f"Blank text at {ref.getShortText()} in ULT" )
                except KeyError:
                    logging.error( f"Can't find {ref.getShortText()} in ULT" )
                    text2 = ''

                # Now that we have text1 and text2 for the verse specified in ref,
                #   do our analysis/comparison now
                J1 = 'Ἰησοῦς' in text1 or 'Ἰησοῦ' in text1 or 'Ἰησοῦν' in text1
                J2 = 'Jesus' in text2
                if J1 and not J2:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Found 'Jesus' in Grk {ref.getShortText()}: {text1}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"                              {text2}" )
                    count1 += 1
                if J2 and not J1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Found 'Jesus' in ULT {ref.getShortText()}: {text2}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"                              {text1}" )
                    count2 += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nFound {count1} unmatched occurrences in UGNT, {count2} in ULT." )
# end of main

def briefDemo() -> None:
    """
    Fast demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
# end of briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    # Do the BOS close-down stuff
    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of CheckuWLiteralNTvsGreek.py
