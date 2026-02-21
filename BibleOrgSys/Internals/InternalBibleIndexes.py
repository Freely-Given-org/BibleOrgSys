#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# InternalBibleIndexes.py
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
TODO: Rewrite makeBookCVIndex to take advantage of the new v= fields.

Module for defining and manipulating Bible indexes including:

    InternalBibleBookCVIndexEntry
    InternalBibleBookCVIndex
        Everything before chapter 1 is considered chapter -1.
        The first line in chapter -1 is considered verse 0
            and each successive line has a successive verse number.
        Everything before verse 1 in regular chapters
            is considered as verse 0, e.g., many section headings, etc.

    InternalBibleBookSectionIndexEntry
    InternalBibleBookSectionIndex

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
    Books (like FRT) that don't have chapters (or verses) store the information in chapter '0'.

CHANGELOG:
    2022-06-05 Quieten makeBookCVIndex print statement
    2022-07-31 Added items() methods to indexes
    2023-02-03 Improved indexing of non-chapter books
    2023-03-02 Improved section index
    2023-04-13 Put verse ranges and suffixes back into CV index entries -- this might be a breaking change for some applications???
    2023-06-02 Allow finding all verses and verse ranges (esp. for notes, commentaries)
    2025-05-21 Combine c/ms1/s1 section headings in section heading index for Psalms
"""
from gettext import gettext as _
from pathlib import Path
import logging

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, BOS_NESTING_MARKERS, BOS_END_MARKERS, getLeadingInt


LAST_MODIFIED_DATE = '2025-09-29' # by RJH
SHORT_PROGRAM_NAME = "BibleIndexes"
PROGRAM_NAME = "Bible indexes handler"
PROGRAM_VERSION = '0.94'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


MAX_NONCRITICAL_ERRORS_PER_BOOK = 4



# Rust implementations for better memory usage and speed (drop-in replacements with camelCase API)
from bible_organisational_system import CVIndexEntry as InternalBibleBookCVIndexEntry  # type: ignore[assignment]
from bible_organisational_system import InternalBibleBookCVIndex  # type: ignore[assignment]
from bible_organisational_system import InternalBibleBookSectionIndexEntry  # type: ignore[assignment]
from bible_organisational_system import InternalBibleBookSectionIndex  # type: ignore[assignment]


def briefDemo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
    ICVE = InternalBibleBookCVIndexEntry( 0, 1, ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ICVE={ICVE}" )
    ISE = InternalBibleBookSectionIndexEntry( '1', '5', 0, 1, 's1', 'Section Name', ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ISE={ISE}" )

    #IBB = InternalBibleIndexes( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    if 1: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
        import os
        from BibleOrgSys.Formats.USFMBible import USFMBible

        testData = ( # name, abbreviation, folderpath for USFM files
                ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData, start=1 ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleIndexes B{j}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                UB.discover()
                UB.makeSectionIndex()
                break
            else: logging.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleIndexes.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
    ICVE = InternalBibleBookCVIndexEntry( 0, 1, ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ICVE={ICVE}" )
    ISE = InternalBibleBookSectionIndexEntry( '1', '5', 0, 1, 's1', 'Section Name', ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ISE={ISE}" )

    #IBB = InternalBibleIndexes( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    if 1: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
        import os
        from BibleOrgSys.Formats.USFMBible import USFMBible

        testData = ( # name, abbreviation, folderpath for USFM files
                ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData, start=1 ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleIndexes B{j}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                UB.discover()
                UB.makeSectionIndex()
            else: logging.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleIndexes.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleIndexes.py
