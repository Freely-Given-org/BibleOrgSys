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
ProgVersion = "0.01"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import sys, re

sys.path.append( '.' )
sys.path.append( '..' )
import BibleOrgSysGlobals


BBB_RE = '([A-PR-XZ][A-EG-VX-Z1][A-WYZ1-6])' # Copy into VerseReferences.py

def main():
    L0, L1, L2 = {}, {}, {}
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        if BBB[0] in L0: L0[BBB[0]] += 1
        else: L0[BBB[0]] = 1
        if BBB[1] in L1: L1[BBB[1]] += 1
        else: L1[BBB[1]] = 1
        if BBB[2] in L2: L2[BBB[2]] += 1
        else: L2[BBB[2]] = 1
    print( sorted(L0) )
    print( sorted(L1) )
    print( sorted(L2) )

    # Now test the RE on the books codes
    for BBB in BibleOrgSysGlobals.BibleBooksCodes:
        #print( BBB )
        match = re.search( BBB_RE, BBB )
        if not match:
            print( BBB )
            halt # Got a BBB that can't be found by the RE
# end of main

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    #parser.add_option("-r", "--runScrape", action="store_true", dest="scrape", default=False, help="scrape other versification systems (requires other software installed -- the paths are built into this program)")
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of TestBooksCodesRE.py