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

LastModifiedDate = '2017-09-27' # by RJH
ShortProgName = "ReorderSongs"
ProgName = "Reorder Songs"
ProgVersion = '0.03'
ProgNameVersion = '{} V{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, os #, logging

sys.path.append( '.' ) # So we can run it from the above folder and still do these imports
import BibleOrgSysGlobals
import SFMFile


testFolder = 'Tests/DataFilesForTests/'
testFile = 'Songs.sfm'
outputFolder = 'OutputFiles/'


def main():
    """
    Reorder songs by title (s line in record).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    # Read our sample data
    songsInputFilepath = os.path.join( testFolder, testFile ) # Relative to module call, not cwd
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "Loading songs from {}…".format( songsInputFilepath ) )
    songs = SFMFile.SFMRecords()
    # Left the four default parameters at the end of the next line so you can see what's available
    songs.read( songsInputFilepath, key='c', ignoreSFMs=None, ignoreEntries=None, changePairs=None, encoding='utf-8' )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "  {} songs loaded".format( len(songs.records) ) )
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( songs )

    keyPairs = []
    for j,songRecord in enumerate(songs.records):
        if debuggingThisModule: print( "songRecord", songRecord )
        sFieldData = songRecord[1]
        assert sFieldData[0] == 's'
        keyPairs.append( (sFieldData[1],j) )
    if debuggingThisModule: print( "keyPairs", keyPairs )

    songsOutputFilepath = os.path.join( outputFolder, testFile ) # Relative to module call, not cwd
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "Writing reordered songs to {}…".format( songsOutputFilepath ) )
    with open( songsOutputFilepath, 'wt' ) as outputFile:
        for k,keyPair in enumerate( sorted(keyPairs) ):
            if debuggingThisModule: print( "keyPair", keyPair )
            outputFile.write( '\n\\c {}\n'.format( k+1 ) ) # Output our new (numbered) c line at the start of the record
            songRecord = songs.records[ keyPair[1] ]
            for s,songLine in enumerate( songRecord ):
                if debuggingThisModule: print( "songLine", s, songLine )
                if s == 0: continue # skip old c line
                outputFile.write( '\\{} {}\n'.format( *songLine ) )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "  {} songs written".format( k+1 ) )

    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} finished.".format( ProgNameVersion ) )
#end of main

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of ReorderSongs.py
