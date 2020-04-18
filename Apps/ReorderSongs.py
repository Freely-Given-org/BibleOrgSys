#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ReorderSongs.py
#
# App to reorder songs which are records in a SFM file.
#
# Copyright (C) 2017 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
A short app as part of BOS (Bible Organisational System) demos.
Demonstrates the use of the SFMFile module
    (which is typically used for dictionaries, etc. more than for Bibles).

App to reorder songs which are records in a SFM file.

Basically, read the file in, sort by the contents of \s and write it out with new \c numbers.

    \c 1
    \s Title of song B
    \m \v 1 Text lines of song
    \p More text lines of song
    \q1 Chorus line(s)

    \c 2
    \s Title of song A
    \m \v 1 Text lines of song
    \p More text lines of song
    \q1 Chorus line(s)

    etc.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2017-09-27' # by RJH
SHORT_PROGRAM_NAME = "ReorderSongs"
PROGRAM_NAME = "Reorder Songs"
PROGRAM_VERSION = '0.03'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import sys
import os #, logging

if __name__ == '__main__':
    import sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.InputOutput import SFMFile


testFolder = 'Tests/DataFilesForTests/'
testFile = 'Songs.sfm'
outputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH


def main() -> None:
    """
    Reorder songs by title (\s line in song record -- assumed to always be the second line in the record).
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Read our sample data
    songsInputFilepath = os.path.join( testFolder, testFile ) # Relative to module call, not cwd
    vPrint( 'Quiet', debuggingThisModule, "Loading songs from {}…".format( songsInputFilepath ) )
    songs = SFMFile.SFMRecords()
    # Left the four default parameters at the end of the next line so you can see what's available
    songs.read( songsInputFilepath, key='c', ignoreSFMs=None, ignoreEntries=None, changePairs=None, encoding='utf-8' )
    vPrint( 'Normal', debuggingThisModule, "  {} songs loaded".format( len(songs.records) ) )
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, songs )

    # Extract the information out of the file that we want to use for sorting
    #   (We get the \s field, plus keep track of the index of each record)
    keyPairs = []
    for j,songRecord in enumerate(songs.records):
        if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "songRecord", songRecord )
        sFieldData = songRecord[1] # Get the second line of the song record (assumed to be the \s or title line )
        assert sFieldData[0] == 's' # This is a 2-tuple of marker (without backslash) and marker contents
        keyPairs.append( (sFieldData[1],j) ) # Store the contents of the \s field, along with the index of this record
    if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "keyPairs", keyPairs )

    # Now we sort the records by the \s field and write them out to a new file in the new, sorted order
    songsOutputFilepath = os.path.join( outputFolder, testFile ) # Relative to module call, not cwd
    vPrint( 'Quiet', debuggingThisModule, "Writing reordered songs to {}…".format( songsOutputFilepath ) )
    with open( songsOutputFilepath, 'wt' ) as outputFile:
        for k,keyPair in enumerate( sorted(keyPairs) ):
            if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "keyPair", keyPair )
            outputFile.write( '\n\\c {}\n'.format( k+1 ) ) # Output our new (numbered) c line at the start of the record
            songRecord = songs.records[ keyPair[1] ] # Get the record (song) that we need
            for s,songLine in enumerate( songRecord ):
                if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "songLine", s, songLine )
                if s == 0: continue # skip old c line
                outputFile.write( '\\{} {}\n'.format( *songLine ) )
    vPrint( 'Normal', debuggingThisModule, "  {} songs written".format( k+1 ) )

    vPrint( 'Quiet', debuggingThisModule, "{} finished.".format( programNameVersion ) )
#end of main

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
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ReorderSongs.py
