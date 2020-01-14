#!/usr/bin/python3
#
# USFM2USX.minimal.py
#
# Command-line app to export a USX (XML) Bible.
#
# Copyright (C) 2019 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
"""
A short command-line app as part of BOS (Bible Organisational System) demos.
This app inputs any known type of Bible file(s) from disk [set inputFolder below]
    and then exports a USX version in the (default) OutputFiles folder
        (inside the folder where you installed the BOS).

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app can be run from your BOS folder,
    e.g., using the command:
        Apps/USFM2USX.minimal.py

You can discover the available command line parameters with
        Apps/USFM2USX.minimal.py --help

This app also demonstrates how little code is required to use the BOS
    to load a Bible (in any of a large range of formats -- see UnknownBible.py)
    and then to export it in your desired format (see options in BibleWriter.py).
"""

# Allow the system to find the BOS even when the app is down in its own folder
import os, sys

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.UnknownBible import UnknownBible


programName = "USFM to USX (minimal)"
programVersion = '0.02'


# You must specify where to find a Bible to read --
#   this can be either a relative path (like my example where ../ means go to the folder above)
#   or an absolute path (which would start with / or maybe ~/ in Linux).
# Normally this is the only line in the program that you would need to change.
inputFolder = '/home/robert/Paratext8Projects/MBTV/'


# Configure basic Bible Organisational System (BOS) set-up
parser = BibleOrgSysGlobals.setup( programName, programVersion )
BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

# Do the actual Bible load and export work that we want
unknownBible = UnknownBible( inputFolder ) # Tell it the folder to start looking in
loadedBible = unknownBible.search( autoLoadAlways=True, autoLoadBooks=True ) # Load all the books if we find any
if loadedBible is not None:
    loadedBible.toUSX2XML() # Export as USX files (USFM inside XML)
    print(f"\nOutput should be in {os.path.join( os.getcwd(), BibleOrgSysGlobals.DEFAULT_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX2_Export/' )} folder.")

# Do the BOS close-down stuff
BibleOrgSysGlobals.closedown( programName, programVersion )
