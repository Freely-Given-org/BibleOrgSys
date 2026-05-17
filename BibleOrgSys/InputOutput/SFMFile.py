#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SFMFile.py
#
# SFM (Standard Format Marker) data file reader
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module for reading UTF-8 SFM (Standard Format Marker) file.

There are three kinds of SFM encoded files which can be loaded:
    1/ SFMLines: A "flat" file, read line by line into a list.
            This could be any kind of SFM data.
    2/ SFMRecords: A "record based" file (e.g., a dictionary), read record by record into a list
    3/ SFMRecords: A header segment, then a "record based" structure read into the same list,
            for example an interlinearized text.

  In each case, the SFM and its data field are read into a 2-tuple and saved (in order) in the list.

  Now powered by Rust for improved memory efficiency.

  Raises IOError if file doesn't exist.
"""
import logging
import sys

from bible_organisational_system import readSFMLines, readSFMRecords
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2026-05-17' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "SFMFile"
PROGRAM_NAME = "SFM Files loader"
PROGRAM_VERSION = '0.88'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



class SFMLines:
    """
    Class holding a list of (non-blank) SFM lines.
    Each line is a tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self) -> None:
        self.lines = []

    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a SFM field object formatted as a string
        @rtype: string
        """
        result = "SFM Lines Object"
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        for line in self.lines:
            result += ('\n' if result else '') + str( line )
        return result

    def read( self, SFMFilepath:str, ignoreSFMs:list|tuple|None=None, encoding:str|None=None ):
        """
        Read a simple SFM (Standard Format Marker) file into a list of tuples.

        @param SFMFilepath: The filename or URL
        @type SFMFilepath: string
        @param ignoreSFMs: List of SFM markers to ignore
        @type ignoreSFMs: list or tuple
        @param encoding: Ignored (now handled by Rust's UTF-8 reader)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = []
        if isinstance(ignoreSFMs, tuple): ignoreSFMs = list(ignoreSFMs)

        try:
            self.lines = readSFMLines( str(SFMFilepath), ignoreSFMs )
        except Exception as err:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "SFMLines error:", sys.exc_info()[0], err )
            logging.critical( f"Error reading {SFMFilepath}: {err}" )
            # raise
    # end of SFMLines.read
# end of class SFMLines



class SFMRecords:
    """
    Class holding a list of SFM records.
    Each record is a list of SFM lines.
        (The record always starts with the same SFMMarker, except perhaps the first record.)
    Each line is a 2-tuple consisting of (SFMMarker, SFMValue).
    """

    def __init__(self) -> None:
        self.records = []

    def __str__(self):
        """
        This method returns the string representation of a SFM lines object.

        @return: the name of a SFM field object formatted as a string
        @rtype: string
        """
        result = ""
        for record in self.records:
            if result: result += '\n' # Blank line between records
            for line in record:
                result += ('\n' if result else '') + str( line )
        return result


    def read( self, SFMFilepath:str, key:str|None=None, ignoreSFMs:list|tuple|None=None, ignoreEntries:list|tuple|None=None, changePairs:list|None=None, encoding:str|None=None ):
        """
        Read a simple SFM (Standard Format Marker) file into a list of lists of tuples.

        @param SFMFilepath: The filename or URL
        @type SFMFilepath: string
        @param key: The SFM record marker (not including the backslash)
        @type key: string
        @param ignoreSFMs: List of SFM markers to ignore
        @type ignoreSFMs: list or tuple
        @param ignoreEntries: List of entry values to ignore
        @type ignoreEntries: list or tuple
        @param changePairs: List of (find, replace) pairs for markers
        @type changePairs: list
        @param encoding: Ignored (now handled by Rust's UTF-8 reader)
        @type encoding: string
        @rtype: list
        @return: list of lists containing the records
        """

        # Check/handle parameters
        if ignoreSFMs is None: ignoreSFMs = []
        if isinstance(ignoreSFMs, tuple): ignoreSFMs = list(ignoreSFMs)
        if ignoreEntries is None: ignoreEntries = []
        if isinstance(ignoreEntries, tuple): ignoreEntries = list(ignoreEntries)
        if changePairs is None: changePairs = []

        if key:
            if '\\' in key: raise ValueError('SFM marker must not contain backslash')
            if ' ' in key: raise ValueError('SFM marker must not contain spaces')

        try:
            self.records = readSFMRecords( str(SFMFilepath), key, ignoreSFMs, ignoreEntries, changePairs )
        except Exception as err:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "SFMRecords error:", sys.exc_info()[0], err )
            logging.critical( f"Error reading {SFMFilepath}: {err}" )
            # raise
    # end of SFMRecords.read


    def analyze( self ):
        """
        Analyzes the list of records read in from the file
            to find the smallest and largest size (number of lines) of each record
        as well as making a list of all the SFM marker types
            and a dictionary of all the possible values of all the various SFM markers.
        Returns these two integers
            plus the list and the dictionary.
        """
        smallestSize, largestSize, markerList, markerSets = 9999, -1, [], {}
        for record in self.records:
            lr = len( record )
            if lr < smallestSize: smallestSize = lr
            if lr > largestSize: largestSize = lr
            for marker, value in record:
                if marker not in markerList:
                    markerList.append( marker )
                    markerSets[marker] = []
                if value not in markerSets[marker]:
                    markerSets[marker].append( value )
        return smallestSize, largestSize, markerList, markerSets
    # end of SFMRecords.analyze


    def copyToDict( self, internalStructure ):
        """
        self.records is a list of lists.

        This function copies them to a dictionary
            where the keys are the values of the given marker (self.key).

        The inner structure can either be lists (if the parameter is "list" )
            which is most useful if lines with the identical SFM can be repeated within the record.
        The inner structure can be dicts (if the parameter is "dict" )
            which then checks that each line within the record starts with a unique marker.
            The order of the original lines within each record is lost.

        Returns the dictionary.
        """
        assert internalStructure in ( "list", "dict" )
        self.dataDict = {}
        for record in self.records:
            for j, (marker,value) in enumerate( record ):
                if j==0:
                    # assert marker == self.key # Rust reader handles this
                    key = value
                    self.dataDict[key] = [] if internalStructure=="list" else {}
                else:
                    if isinstance( self.dataDict[key], list ):
                        self.dataDict[key].append( (marker,value) )
                    elif isinstance( self.dataDict[key], dict ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, key, marker, value )
                        if marker in self.dataDict[key]:
                            logging.warning( f"Multiple {marker} lines in {key} record--will be overwritten" )
                        self.dataDict[key][marker] = value
        return self.dataDict
    # end of SFMRecords.copyToDict
# end of class SFMRecords



def briefDemo() -> None:
    """
    Demonstrate reading and processing some UTF-8 SFM databases.
    """
    import os.path

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Using {filepath} as test file…" )

    linesDB = SFMLines()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, i, r)
        if i>9: break
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '…\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record

    recordsDB = SFMRecords()
    recordsDB.read( filepath, 'og', ignoreSFMs=('mn','aMU','aMW','cu','cp'))
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(recordsDB.records), 'records read from file', filepath )
    for i, r in enumerate(recordsDB.records):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, i, r)
        if i>3: break
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '…\n',len(recordsDB.records)-1, recordsDB.records[-1]) # Display the last record
# end of SFMFile.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    import os.path

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    filepath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MatigsalugDictionaryA.sfm' )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Using {filepath} as test file…" )

    linesDB = SFMLines()
    linesDB.read( filepath, ignoreSFMs=('mn','aMU','aMW','cu','cp') )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(linesDB.lines), 'lines read from file', filepath )
    for i, r in enumerate(linesDB.lines):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, i, r)
        if i>9: break
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '…\n',len(linesDB.lines)-1, linesDB.lines[-1], '\n') # Display the last record

    recordsDB = SFMRecords()
    recordsDB.read( filepath, 'og', ignoreSFMs=('mn','aMU','aMW','cu','cp'))
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(recordsDB.records), 'records read from file', filepath )
    for i, r in enumerate(recordsDB.records):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, i, r)
        if i>3: break
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '…\n',len(recordsDB.records)-1, recordsDB.records[-1]) # Display the last record
# end of SFMFile.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SFMFile.py
