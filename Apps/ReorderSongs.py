#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ReorderSongs.py
#
# App to reorder songs which are records in a SFM file.
#
# Copyright (C) 2017 Robert Hunt
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

lastModifiedDate = '2017-09-27' # by RJH
shortProgramName = "ReorderSongs"
programName = "Reorder Songs"
programVersion = '0.03'
programNameVersion = f'{shortProgramName} v{programVersion}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {lastModifiedDate}'

debuggingThisModule = False


import sys
import os #, logging

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.append( os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports

import BibleOrgSysGlobals
from InputOutput import SFMFile


testFolder = 'Tests/DataFilesForTests/'
testFile = 'Songs.sfm'
outputFolder = BibleOrgSysGlobals.DEFAULT_OUTPUT_FOLDERPATH


def main():
    """
    Reorder songs by title (\s line in song record -- assumed to always be the second line in the record).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    # Read our sample data
    songsInputFilepath = os.path.join( testFolder, testFile ) # Relative to module call, not cwd
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "Loading songs from {}…".format( songsInputFilepath ) )
    songs = SFMFile.SFMRecords()
    # Left the four default parameters at the end of the next line so you can see what's available
    songs.read( songsInputFilepath, key='c', ignoreSFMs=None, ignoreEntries=None, changePairs=None, encoding='utf-8' )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "  {} songs loaded".format( len(songs.records) ) )
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( songs )

    # Extract the information out of the file that we want to use for sorting
    #   (We get the \s field, plus keep track of the index of each record)
    keyPairs = []
    for j,songRecord in enumerate(songs.records):
        if debuggingThisModule: print( "songRecord", songRecord )
        sFieldData = songRecord[1] # Get the second line of the song record (assumed to be the \s or title line )
        assert sFieldData[0] == 's' # This is a 2-tuple of marker (without backslash) and marker contents
        keyPairs.append( (sFieldData[1],j) ) # Store the contents of the \s field, along with the index of this record
    if debuggingThisModule: print( "keyPairs", keyPairs )

    # Now we sort the records by the \s field and write them out to a new file in the new, sorted order
    songsOutputFilepath = os.path.join( outputFolder, testFile ) # Relative to module call, not cwd
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "Writing reordered songs to {}…".format( songsOutputFilepath ) )
    with open( songsOutputFilepath, 'wt' ) as outputFile:
        for k,keyPair in enumerate( sorted(keyPairs) ):
            if debuggingThisModule: print( "keyPair", keyPair )
            outputFile.write( '\n\\c {}\n'.format( k+1 ) ) # Output our new (numbered) c line at the start of the record
            songRecord = songs.records[ keyPair[1] ] # Get the record (song) that we need
            for s,songLine in enumerate( songRecord ):
                if debuggingThisModule: print( "songLine", s, songLine )
                if s == 0: continue # skip old c line
                outputFile.write( '\\{} {}\n'.format( *songLine ) )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "  {} songs written".format( k+1 ) )

    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} finished.".format( programNameVersion ) )
#end of main

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of ReorderSongs.py
