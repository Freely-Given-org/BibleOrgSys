#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# InternalBibleInternals.py
#
# Module handling the internal objects for Bible books
#
# Copyright (C) 2010-2024 Robert Hunt
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
Module for defining and manipulating internal Bible objects including:

    InternalBibleExtra
    InternalBibleExtraList
        A list of InternalBibleExtras
            with internal data validation functions
            and with a str() function useful for debugging.

    InternalBibleEntry
    InternalBibleEntryList
        A list of InternalBibleEntries
            with internal data validation functions
            and with a str() function useful for debugging.

Some notes about internal formats:
    The BibleOrgSys internal format is based on
        ESFM (see https://Freely-Given.org/Software/BibleDropBox/ESFMBibles.html )
        which is turn is based on USFM 3 (see https://ubsicap.github.io/usfm/index.html).
    Each Bible book (including front and back matter) is stored in
        a separate InternalBibleBook object.
    Each "new line" type field is considered a separate line in
        a list of "lines" inside the book object.
        These are stored as InternalBible Entry fields
            inside the InternalBibleEntryList in the Bible book object.

        Three types of text fields can be retrieved from the InternalBibleEntry:
            1/ The full and complete ESFM/USFM text of the "line"
            2/ The adjusted text which has "note" fields
                (e.g., footnotes and cross-references) removed
            3/ The clean text which also has inline formatting
                (e.g., bold, bookname, word-of-Jesus) removed

        Notes are removed from the text and placed into a list of "extras"
            stored in an InternalBibleExtraList object.
        Each InternalBibleExtra contains an index back to the adjusted text
            (and hence that index must be adjusted if the text string is edited).

    The introduction is stored as chapter '-1'. (All our chapter and verse "numbers" are stored as strings.)
        (We allow for some rare printed Roman Catholic Bibles that have an actual chapter 0.)
"""
from gettext import gettext as _
import logging
import re

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
#from BibleReferences import BibleAnchorReference


LAST_MODIFIED_DATE = '2024-11-08' # by RJH
SHORT_PROGRAM_NAME = "BibleInternals"
PROGRAM_NAME = "Bible internals handler"
PROGRAM_VERSION = '0.88'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False
MAX_NONCRITICAL_ERRORS_PER_BOOK = 4


from bible_organisational_system import getSmallLeadingInt, getPositiveLeadingInt # Rust implementation



# Rust implementations for better memory usage and speed (drop-in replacements with camelCase APIs)
from bible_organisational_system import (  # type: ignore[assignment]
    InternalBibleExtra,
    InternalBibleExtraList,
    InternalBibleEntry,
    InternalBibleEntryList,
    CVIndexEntry as InternalBibleBookCVIndexEntry,
    InternalBibleBookCVIndex,
    InternalBibleBookSectionIndexEntry,
    InternalBibleBookSectionIndex,
)



def briefDemo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    # from pathlib import Path
    global DEBUGGING_THIS_MODULE

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since these are only helper classes, they can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    # if 0: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
    #     import os
    #     from BibleOrgSys.Formats.USFMBible import USFMBible

    #     testData = ( # name, abbreviation, folderpath for USFM files
    #             ("Matigsalug", 'MBTV', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/') ),
    #             ) # You can put your USFM test folder here

    #     for j, (name, abbrev, testFolder) in enumerate( testData ):
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleInternals B{j+1}/ {abbrev} from {testFolder}…" )
    #         if os.access( testFolder, os.R_OK ):
    #             UB = USFMBible( testFolder, name, abbrev )
    #             UB.load()
    #             UB.discover() # Why does this only help if -1 flag is enabled???
    #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
    #             if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
    #             #DEBUGGING_THIS_MODULE = False
    #             for BBB,bookObject in UB.books.items():
    #                 bookObject._SectionIndex = InternalBibleBookSectionIndex( bookObject )
    #                 bookObject._SectionIndex.makeBookSectionIndex()
    #                 if BBB=='GEN': halt
    #         else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleInternals.briefDemo


def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    global DEBUGGING_THIS_MODULE

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since these are only helper classes, they can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    resultDict = parseWordAttributes('testWork', 'GEN','1','2', 'word|x=pos="noun"')
    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"resultDict = {resultDict}" )
    assert resultDict == {'word': 'word', 'x': 'pos="noun"'}

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    # if 0: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
    #     import os
    #     from BibleOrgSys.Formats.USFMBible import USFMBible

    #     testData = ( # name, abbreviation, folderpath for USFM files
    #             ("Matigsalug", 'MBTV', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/') ),
    #             ) # You can put your USFM test folder here

    #     for j, (name, abbrev, testFolder) in enumerate( testData ):
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleInternals B{j+1}/ {abbrev} from {testFolder}…" )
    #         if os.access( testFolder, os.R_OK ):
    #             UB = USFMBible( testFolder, name, abbrev )
    #             UB.load()
    #             UB.discover() # Why does this only help if -1 flag is enabled???
    #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
    #             if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
    #             #DEBUGGING_THIS_MODULE = False
    #             for BBB,bookObject in UB.books.items():
    #                 bookObject._SectionIndex = InternalBibleBookSectionIndex( bookObject )
    #                 bookObject._SectionIndex.makeBookSectionIndex()
    #                 if BBB=='GEN': halt
    #         else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleInternals.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleInternals.py
