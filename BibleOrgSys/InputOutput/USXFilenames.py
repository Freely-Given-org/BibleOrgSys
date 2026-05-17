#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# USXFilenames.py
#
# Module handling USX Bible filenames
#
# Copyright (C) 2012-2022 Robert Hunt
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
Module for creating and manipulating USX filenames.

Now powered by Rust for high-performance project discovery.
"""

import os
import logging

from bible_organisational_system import discoverFilenames, DiscoveryOptions
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import bos_books_codes_py


LAST_MODIFIED_DATE = '2026-05-17' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "USXBible"
PROGRAM_NAME = "USX Bible filenames handler"
PROGRAM_VERSION = '0.60'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



class USXFilenames:
    """
    Class for creating and manipulating USX Filenames.
    """

    def __init__( self, givenFolderName ) -> None:
        """
        Create the object by inspecting files in the given folder.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"USXFilenames.__init__( {givenFolderName} )" )

        self.givenFolderName = givenFolderName
        self.pattern, self.fileExtension = '', 'usx'
        self.fileList = []
        self.lastTupleList = None

        if not os.access( self.givenFolderName, os.R_OK ):
            logging.critical( f"USXFilenames: Given {self.givenFolderName!r} folder is unreadable" )
            return

        options = DiscoveryOptions( strict_check=BibleOrgSysGlobals.strictCheckingFlag )
        try:
            results = discoverFilenames( str(givenFolderName), is_usx=True, options=options )
            self.pattern = results.pattern
            self.fileExtension = results.fileExtension
            self.lastTupleList = results.matchedFiles
            # For backward compatibility, fileList contains all recognized files
            self.fileList = [f for _, f in results.matchedFiles] + results.unusedFilenames
        except Exception as err:
            logging.error( f"USXFilenames: Error in Rust discovery: {err}" )
    # end of USXFilenames.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of an object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USX Filenames object"
        indent = 2
        if self.givenFolderName: result += ('\n' if result else '') + ' '*indent + f"Folder: {self.givenFolderName}"
        if self.pattern: result += ('\n' if result else '') + ' '*indent + f"Filename pattern: {self.pattern}"
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + f"File extension: {self.fileExtension}"
        return result
    # end of USXFilenames.__str__


    def getFilenameTemplate( self ) -> str:
        """
        Returns a pattern/template for USX filenames.
        """
        return self.pattern
    # end of USXFilenames.getFilenameTemplate


    def getDerivedFilenameTuples( self ):
        """
        Return a list of valid USX filenames that match our filename template.
        """
        return self.lastTupleList or []
    # end of USXFilenames.getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self, strictCheck:bool=False ):
        """
        Return a list of tuples of UPPER CASE book codes with actual (present and readable) USX filenames.
        """
        if strictCheck and not BibleOrgSysGlobals.strictCheckingFlag:
             options = DiscoveryOptions( strict_check=True )
             try:
                 results = discoverFilenames( str(self.givenFolderName), is_usx=True, options=options )
                 self.lastTupleList = results.matchedFiles
             except Exception as err:
                 logging.error( f"USXFilenames.getConfirmedFilenameTuples: Error in Rust discovery: {err}" )
        return self.lastTupleList or []
    # end of USXFilenames.getConfirmedFilenameTuples


    def getPossibleFilenameTuples( self, strictCheck:bool=False ) -> list[tuple[str,str]]:
        """
        Return a list of filenames just derived from the list of files in the folder.
        """
        return self.getConfirmedFilenameTuples( strictCheck=strictCheck )
    # end of USXFilenames.getPossibleFilenameTuples


    def getUnusedFilenames( self ):
        """
        Return a list of filenames which didn't match the USFX template.
        """
        if self.lastTupleList is None: return []
        folderFilenames = os.listdir( self.givenFolderName )
        matched = [f for _, f in self.lastTupleList]
        return [f for f in folderFilenames if f not in matched and os.path.isfile(os.path.join(self.givenFolderName, f))]
    # end of USXFilenames.getUnusedFilenames
# end of class USXFiles


def briefDemo() -> None:
    """
    Demonstrate finding files in some USX Bible folders.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # These are relative paths -- you can replace these with your test folder(s)
    testFolders = (BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),)
    for testFolder in testFolders:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' )
        if os.access( testFolder, os.R_OK ):
            UsxFns = USXFilenames( testFolder )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsxFns )
            result = UsxFns.getMaximumPossibleFilenameTuples(); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nConfirmed: {len(result)} books found" )
            result = UsXFns.getUnusedFilenames(); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Other: {len(result)} files" )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )
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
# end of USXFilenames.py
