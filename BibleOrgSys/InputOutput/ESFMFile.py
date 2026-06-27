#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ESFMFile.py
#
# ESFM (Enhanced Standard Format Marker) data file reader
#
# Copyright (C) 2010-2022 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module for reading UTF-8 ESFM (Enhanced Standard Format Marker) Bible file.

  ESFMFile: A "flat" text file, read line by line into a list.

  The ESFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Now powered by Rust for improved memory efficiency.

  Raises an IOError error if file doesn't exist.
"""


import logging
import sys

from bible_organisational_system import readESFMFile
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2026-06-07' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "ESFMFile"
PROGRAM_NAME = "ESFM File loader"
PROGRAM_VERSION = '0.90'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



class ESFMFile:
    """
    Class holding a list of (non-blank) ESFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self) -> None:
        self.lines = []
    # end of ESFMFile.__init__


    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a ESFM field object formatted as a string
        @rtype: string
        """
        result = "ESFM File Object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result
    # end of ESFMFile.__str__


    def read( self, esfm_filepath:str, ignoreSFMs:list|tuple|None=None ):
        """Read a simple ESFM (Enhanced Standard Format Marker) file into a list of tuples.

        @param esfm_filepath: The filename or URL
        @type esfm_filepath: string
        @param ignoreSFMs: List of SFM markers to ignore
        @type ignoreSFMs: list or tuple
        @rtype: list
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ESFMFile.read( {repr(esfm_filepath)}, {repr(ignoreSFMs)} )" )

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = []
        elif isinstance(ignoreSFMs, tuple): ignoreSFMs = list(ignoreSFMs)

        try:
            self.lines = readESFMFile( str(esfm_filepath), ignoreSFMs )
        except Exception as err:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ESFMFile error:", sys.exc_info()[0], err )
            logging.critical( f"Error reading {esfm_filepath}: {err}" )
            # raise
    # end of ESFMFile.read
# end of class ESFMFile



def briefDemo() -> None:
    """
    Demonstrate reading and processing some UTF-8 ESFM files.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    import os.path
    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Using {filepath} as test file…" )

    linesDB = ESFMFile()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, i, r)
        if i>9: break
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '…\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record
# end of fullDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESFMFile.py
