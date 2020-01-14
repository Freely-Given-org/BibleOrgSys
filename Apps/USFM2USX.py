#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFM2USX.py
#
# Command-line app to export a USX (XML) Bible.
#
# Copyright (C) 2019 Robert Hunt
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
A short command-line app as part of BOS (Bible Organisational System) demos.
This app inputs any known type of Bible file(s) [set inputFolder below]
    and then exports a USX version in the (default) OutputFiles folder
        (inside the folder where you installed the BOS).

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app can be run from your BOS folder,
    e.g., using the command:
        Apps/USFM2USX.py

You can discover the version with
        Apps/USFM2USX.py --version

You can discover the available command line parameters with
        Apps/USFM2USX.py --help

    e.g., for verbose mode
        Apps/USFM2USX.py --verbose
    or
        Apps/USFM2USX.py -v

This app also demonstrates how little actual code is required to use the BOS
    to load a Bible (in any of a large range of formats -- see UnknownBible.py)
    and then to export it in your desired format (see options in BibleWriter.py).
There is also a minimum version of this same app (Apps/USFM2USX.minimal.py)
    which really shows how few lines are required to use the BOS for Bible conversions.

The (Python3) BOS is developed and well-tested on Linux (Ubuntu)
    but also runs on Windows (although not so well tested).
"""

# You must specify where to find a Bible to read --
#   this can be either a relative path (like my example where ../ means go to the folder above)
#   or an absolute path (which would start with / or maybe ~/ in Linux).
# Normally this is the only line in the program that you would need to change.
defaultInputFolder = '/home/robert/Paratext8Projects/MBTV/'
defaultInputFolder = 'Tests/DataFilesForTests/USFM2AllMarkersProject/'
# defaultInputFolder = 'Tests/DataFilesForTests/USFM3AllMarkersProject/'
defaultInputFolder = 'Tests/DataFilesForTests/zTemp/'


from gettext import gettext as _

lastModifiedDate = '2019-01-29' # by RJH
shortProgramName = "USFM2USX"
programName = "USFM to USX"
programVersion = '0.02'
programNameVersion = f'{programName} v{programVersion}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {lastModifiedDate}'

import os, shutil

# Allow the system to find the BOS even when the app is down in its own folder
if __name__ == '__main__':
    import sys
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.UnknownBible import UnknownBible



def main():
    """
    This is the main program for the app
        which just tries to open and load some kind of Bible file(s)
            from the inputFolder that you specified
        and then export a USX Bible (in the default OutputFiles folder).

    Note that the standard verbosityLevel is 2:
        -s (silent) is 0
        -q (quiet) is 1
        -i (information) is 3
        -v (verbose) is 4.
    """
    inputFileOrFolder = defaultInputFolder

    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( programNameVersion )
        print( f"\n{shortProgramName}: processing input folder {inputFileOrFolder!r} …" )

    # Try to detect and read/load the Bible file(s)
    unknownBible = UnknownBible( inputFileOrFolder ) # Tell it the folder to start looking in
    loadedBible = unknownBible.search( autoLoadAlways=True, autoLoadBooks=True ) # Load all the books if we find any
    if BibleOrgSysGlobals.verbosityLevel > 2: print( unknownBible ) # Display what Bible typed we found
    if BibleOrgSysGlobals.verbosityLevel > 1: print( loadedBible ) # Show how many books we loaded

    # If we were successful, do the export
    if loadedBible is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: loadedBible.check()

        defaultOutputFolder = BibleOrgSysGlobals.DEFAULT_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX2_Export/' )
        if os.path.exists( defaultOutputFolder ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( f"\n{shortProgramName}: removing previous {defaultOutputFolder} folder…" )
                shutil.rmtree( defaultOutputFolder )

        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( f"\n{shortProgramName}: starting export…" )

        # We only want to do the USX export (from the BibleWriter.py module)
        result = loadedBible.toUSX2XML() # Export as USX files (USFM inside XML)
        # However, you could easily change this to do all exports
        #result = loadedBible.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        # Or you could choose a different export, for example:
        #result = loadedBible.toOSISXML()
        if BibleOrgSysGlobals.verbosityLevel > 2: print( f"  Result was: {result}" )
        print(f"\n{shortProgramName}: output should be in {defaultOutputFolder} folder.")
# end of main

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    # Do the BOS close-down stuff
    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of USFM2USX.py
