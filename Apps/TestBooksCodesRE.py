#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TestBooksCodesRE.py
#
# Module which checks regular expressions.
#
# Copyright (C) 2015-2021 Robert Hunt
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
Module which tests the regular expression for Bible Books Codes.
"""

from gettext import gettext as _
import sys
import re
from collections import defaultdict

# Allow the app to run from either the BOS folder or in this Apps subfolder
if __name__ == '__main__':
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2021-01-23' # by RJH
SHORT_PROGRAM_NAME = "TestBooksCodesRE"
PROGRAM_NAME = "TestBooksCodes Regular Expressions"
PROGRAM_VERSION = '0.21'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Regular expressions to be searched for
#       \d      Matches any decimal digit; this is equivalent to the class [0-9].
#       \D      Matches any non-digit character; this is equivalent to the class [^0-9].
#       \s      Matches any whitespace character; this is equivalent to the class [ \t\n\r\f\v].
#       \S      Matches any non-whitespace character; this is equivalent to the class [^ \t\n\r\f\v].
#       \w      Matches any alphanumeric character; this is equivalent to the class [a-zA-Z0-9_].
#       \W      Matches any non-alphanumeric character; this is equivalent to the class [^a-zA-Z0-9_].
#
#       ?       Matches sequence zero or once (i.e., for something that's optional) -- same as {0,1}
#       *       Matches sequence zero or more times (greedy) -- same as {0,}
#       +       Matches sequence one or more times -- same as {1,}
#       {m,n}   Matches at least m repetitions, and at most n
#
BBB_RE = '([A-PR-XZ][A-EG-VX-Z1][A-WYZ1-6])' # Copy into VerseReferences.py
OSIS_BOOK_RE = '([1-5A-EG-JL-PRSTVWZ][BCEJKMPSTa-ehimoprsuxz](?:[AJMa-eghik-pr-v](?:[DEPacdeghklmnrstuvz](?:[Gachnrsz](?:[nrst][ah]?)?)?)?)?)' # Copy into VerseReferences.py


def doBBB():
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\ndoBBB" )
    Letter0, Letter1, Letter2 = defaultdict( int ), defaultdict( int ), defaultdict( int )
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
        Letter0[BBB[0]] += 1
        Letter1[BBB[1]] += 1
        Letter2[BBB[2]] += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', sorted(L0) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', sorted(L1) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', sorted(L2) )

    # Now test the RE on the books codes
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
        match = re.search( BBB_RE, BBB )
        if not match:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
            halt # Got a BBB that can't be found by the RE
# end of doBBB


def doOSIS():
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\ndoOSIS" )
    minL, maxL = 999, 0
    L = {}
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
        OB = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
        if not OB: continue
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, OB )
        lOB = len( OB )
        if lOB < minL: minL = lOB
        if lOB > maxL: maxL = lOB
        for j,obChar in enumerate( OB ):
            if j not in L: L[j] = {}
            if OB[j] in L[j]: L[j][OB[j]] += 1
            else: L[j][OB[j]] = 1
    for k in range( maxL ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', k, sorted(L[k]) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', minL, maxL )

    # Now test the RE on the books codes
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
        OB = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
        if not OB: continue
        match = re.search( OSIS_BOOK_RE, OB )
        if not match:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, OB )
            halt # Got a OB that can't be found by the RE
# end of doOSIS


def main() -> None:
    doBBB()
    doOSIS()
# end of main

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of TestBooksCodesRE.py
