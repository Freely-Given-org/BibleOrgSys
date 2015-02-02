#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# MakePhotoBible.py
#
# App to export a PhotoBible.
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
A short demo app which inputs any known type of Bible files
    and then exports a PhotoBible in the (default) OutputFiles folder.
"""

from gettext import gettext as _

LastModifiedDate = '2015-02-03' # by RJH
ShortProgName = "MakePhotoBible"
ProgName = "Make PhotoBible"
ProgVersion = '0.10'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


# Allow the app to run from either the BOS folder or in this Apps subfolder
import sys
sys.path.append( '.' )
sys.path.append( '..' )
import BibleOrgSysGlobals
from UnknownBible import UnknownBible


# Specify where to find a Bible to read
#   (This can be either an absolute path or a relative path)
inputFolder = "../../../../../Data/Work/Matigsalug/Bible/MBTV/"


def main():
    """
    This is the main program
        which just tries to open and load some kind of Bible file(s)
        and then export a PhotoBible (in the OutputFiles folder).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( "\nMakePhotoBible: processing {}...".format( inputFolder ) )

    # Try to detect and read the Bible files
    unknownBible = UnknownBible( inputFolder ) # Tell it the folder to start looking in
    loadedBible = unknownBible.search( autoLoadBooks=True ) # Load all the books if we find any
    if BibleOrgSysGlobals.verbosityLevel > 2: print( unknownBible )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( loadedBible )

    # If we were successful, do the export
    if loadedBible:
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nMakePhotoBible: starting export (may take up to 30 minutes)..." )
        if BibleOrgSysGlobals.strictCheckingFlag: loadedBible.check()
        result = loadedBible.toPhotoBible()
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result was: {}".format( result ) )
# end of main

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of MakePhotoBible.py