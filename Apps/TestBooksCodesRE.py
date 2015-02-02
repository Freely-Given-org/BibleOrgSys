#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# TestBooksCodesRE.py
#
# Module which checks regular expressions.
#
# Copyright (C) 2015 Robert Hunt
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
Module which tests the regular expression for Bible Books Codes.
"""

from gettext import gettext as _

LastModifiedDate = '2015-01-25' # by RJH
ShortProgName = "TestBooksCodesRE"
ProgName = "TestBooksCodes Regular Expressions"
ProgVersion = '0.20'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, re

# Allow the app to run from either the BOS folder or in this Apps subfolder
sys.path.append( '.' )
sys.path.append( '..' )
import BibleOrgSysGlobals


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
    print( "\ndoBBB" )
    L0, L1, L2 = {}, {}, {}
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        if BBB[0] in L0: L0[BBB[0]] += 1
        else: L0[BBB[0]] = 1
        if BBB[1] in L1: L1[BBB[1]] += 1
        else: L1[BBB[1]] = 1
        if BBB[2] in L2: L2[BBB[2]] += 1
        else: L2[BBB[2]] = 1
    print( ' ', sorted(L0) )
    print( ' ', sorted(L1) )
    print( ' ', sorted(L2) )

    # Now test the RE on the books codes
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        match = re.search( BBB_RE, BBB )
        if not match:
            print( BBB )
            halt # Got a BBB that can't be found by the RE
# end of doBBB


def doOSIS():
    print( "\ndoOSIS" )
    minL, maxL = 999, 0
    L = {}
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        OB = BibleOrgSysGlobals.BibleBooksCodes.getOSISAbbreviation( BBB )
        if not OB: continue
        #print( OB )
        lOB = len( OB )
        if lOB < minL: minL = lOB
        if lOB > maxL: maxL = lOB
        for j,obChar in enumerate( OB ):
            if j not in L: L[j] = {}
            if OB[j] in L[j]: L[j][OB[j]] += 1
            else: L[j][OB[j]] = 1
    for k in range( 0, maxL ):
        print( ' ', k, sorted(L[k]) )
    print( ' ', minL, maxL )

    # Now test the RE on the books codes
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        OB = BibleOrgSysGlobals.BibleBooksCodes.getOSISAbbreviation( BBB )
        if not OB: continue
        match = re.search( OSIS_BOOK_RE, OB )
        if not match:
            print( OB )
            halt # Got a OB that can't be found by the RE
# end of doOSIS


def main():
    doBBB()
    doOSIS()
# end of main

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of TestBooksCodesRE.py