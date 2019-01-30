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
This app inputs any known type of Bible file(s) [set inputFolder below]
    and then exports a USX version in the (default) OutputFiles folder
        (inside the folder where you installed the BOS).

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app MUST BE RUN FROM YOUR BOS folder,
    e.g., using the command:
        Apps/USFM2USX.py

You can discover the available command line parameters with
        Apps/USFM2USX.py --help

This app also demonstrates how little code is required to use the BOS
    to load a Bible (in any of a large range of formats -- see UnknownBible.py)
    and then to export it in your desired format (see options in BibleWriter.py).
"""

import os

# Allow the system to find the BOS even when the app is down in its own folder
import sys; sys.path.append( '.' ) # Append the containing folder to the path to search for the BOS
import BibleOrgSysGlobals
from UnknownBible import UnknownBible


ProgName = "USFM to USX"
ProgVersion = '0.01'


# You must specify where to find a Bible to read --
#   this can be either a relative path (like my example where ../ means go to the folder above)
#   or an absolute path (which would start with / or maybe ~/ in Linux).
# Normally this is the only line in the program that you would need to change.
inputFolder = '/home/robert/Paratext8Projects/MBTV/'


def main():
    unknownBible = UnknownBible( inputFolder ) # Tell it the folder to start looking in
    loadedBible = unknownBible.search( autoLoadAlways=True, autoLoadBooks=True ) # Load all the books if we find any
    if loadedBible is not None:
        loadedBible.toUSX2XML() # Export as USX files (USFM inside XML)
        print(f"\nOutput should be in {os.path.join( os.getcwd(), 'OutputFiles/', 'BOS_USX2_Export/' )} folder.")
# end of main

if __name__ == '__main__':
    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of USFM2USX.minimal.py
