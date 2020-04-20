#!/usr/bin/env python3
#
# Bible2USX_minimal.py
#
# Command-line app to export a USX (XML) Bible.
#
# Copyright (C) 2019-2020 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
"""
A short command-line app as part of BOS (Bible Organisational System) demos.
This app inputs any known type of Bible file(s) from disk
    and then exports a USX version in the (default) BOSOutputFiles folder
        (inside the BibleOrgSys folder in your home folder).

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app can be run from your BOS folder,
    e.g., using the command:
        Apps/Bible2USX_minimal.py path/to/BibleFileOrFolder

You can discover the available command line parameters with
        Apps/Bible2USX_minimal.py --help

This app also demonstrates how little code is required to use the BOS
    to load a Bible (in any of a large range of formats — see UnknownBible.py)
    and then to export it in your desired format (see options in BibleWriter.py).
"""
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import Bible
from BibleOrgSys.UnknownBible import UnknownBible


PROGRAM_NAME = "Bible to USX (minimal)"
PROGRAM_VERSION = '0.09'


def run():
    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
    parser.add_argument( "inputBibleFileOrFolder", help="path/to/BibleFileOrFolder" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    # Search for a Bible and attempt to load it
    unknownBible = UnknownBible( BibleOrgSysGlobals.commandLineArguments.inputBibleFileOrFolder )
    loadedBible = unknownBible.search( autoLoadAlways=True, autoLoadBooks=True ) # Load all the books if we find any

    # See if we were successful at loading one (and only one), and if so, do the export
    if isinstance( loadedBible, Bible ): # i.e., not an error message
        loadedBible.toUSXXML() # Export as USX files (USFM inside XML)
        vPrint( 'Quiet', False, f"\nOutput should be in {BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX2_Export/' )}/ folder." )

    # Do the BOS close-down stuff
    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )

if __name__ == '__main__':
    run()
