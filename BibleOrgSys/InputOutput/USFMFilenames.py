#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# USFMFilenames.py
#
# Module handling USFM Bible filenames
#
# Copyright (C) 2010-2026 Robert Hunt
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
Module for creating and manipulating USFM filenames.

Now powered by Rust for high-performance project discovery.
"""
from pathlib import Path
import os
import logging

from bible_organisational_system import discoverFilenames, DiscoveryOptions
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import bos_books_codes_py


LAST_MODIFIED_DATE = '2026-05-17' # by RJH (Rust conversion)
SHORT_PROGRAM_NAME = "USFMFilenames"
PROGRAM_NAME = "USFM Bible filenames handler"
PROGRAM_VERSION = '0.80'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



class USFMFilenames:
    """
    Class for creating and manipulating USFM filenames.

    Always returns lists of USFM filenames in the default rough sequence order from the BibleBooksCodes module.
    """

    def __init__( self, givenFolderName ) -> None:
        """
        Create the object by inspecting files in the given folder.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"USFMFilenames.__init__( {givenFolderName} )" )
        self.givenFolderName = givenFolderName
        self.pattern, self.fileExtension = '', ''
        self.fileList = []
        self.lastTupleList = None

        if not os.access( self.givenFolderName, os.R_OK ):
            logging.critical( f"USFMFilenames: Given {self.givenFolderName!r} folder is unreadable" )
            return

        options = DiscoveryOptions( strict_check=BibleOrgSysGlobals.strictCheckingFlag )
        try:
            results = discoverFilenames( str(givenFolderName), is_usx=False, options=options )
            self.pattern = results.pattern
            self.fileExtension = results.fileExtension
            self.lastTupleList = results.matchedFiles
            # For backward compatibility, fileList contains all recognized files
            self.fileList = [f for _, f in results.matchedFiles] + results.unusedFilenames
        except Exception as err:
            logging.error( f"USFMFilenames: Error in Rust discovery: {err}" )
    # end of USFMFilenames.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of an object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USFM Filenames object:"
        indent = 2
        if self.givenFolderName: result += ('\n' if result else '') + ' '*indent + f"Folder: {self.givenFolderName}"
        if self.pattern: result += ('\n' if result else '') + ' '*indent + f"Filename pattern: {self.pattern}"
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + f"File extension: {self.fileExtension}"
        if self.fileList and BibleOrgSysGlobals.verbosityLevel > 2: result += ('\n' if result else '') + ' '*indent + f"File list: ({len(self.fileList)}) {self.fileList}"
        return result
    # end of USFMFilenames.__str___


    def __len__( self ):
        """
        This method returns the last number of files found.

        @return: None (if no search done) or else the last number of USFM files found
        @rtype: int
        """
        if self.lastTupleList is None: return 0
        return len( self.lastTupleList )
    # end of USFMFilenames.__len___


    def getFilenameTemplate( self ):
        """
        Returns a pattern/template for USFM filenames.
        """
        return self.pattern
    # end of USFMFilenames.getFilenameTemplate


    def getAllFilenames( self ):
        """
        Return a list of all filenames in our folder.
            This excludes names of subfolders and backup files.
        """
        return self.fileList
    # end of USFMFilenames.getAllFilenames


    def getDerivedFilenameTuples( self ):
        """
        Return a theoretical list of valid USFM filenames that match our filename template.
        """
        # For now, we return the same as confirmed because Rust discovery is already highly effective
        return self.lastTupleList or []
    # end of USFMFilenames.getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self, strictCheck=False ):
        """
        Return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames.
        """
        if strictCheck and not BibleOrgSysGlobals.strictCheckingFlag:
             options = DiscoveryOptions( strict_check=True )
             try:
                 results = discoverFilenames( str(self.givenFolderName), is_usx=False, options=options )
                 self.lastTupleList = results.matchedFiles
             except Exception as err:
                 logging.error( f"USFMFilenames.getConfirmedFilenameTuples: Error in Rust discovery: {err}" )
        return self.lastTupleList or []
    # end of USFMFilenames.getConfirmedFilenameTuples


    def getPossibleFilenameTuplesExt( self ):
        """
        Return a list of filename tuples just derived from the list of files in the folder.
        """
        # With Rust discovery, we already have this in lastTupleList
        return self.lastTupleList or []
    # end of USFMFilenames.getPossibleFilenameTuplesExt


    def getPossibleFilenameTuplesInt( self ):
        """
        Return a list of filename tuples which contain book codes internally on the \\id line.
        """
        # Already handled by Rust discovery
        return self.lastTupleList or []
    # end of USFMFilenames.getPossibleFilenameTuplesInt


    def getMaximumPossibleFilenameTuples( self, strictCheck=False ):
        """
        Find the method that finds the maximum number of USFM Bible files.
        """
        confirmed = self.getConfirmedFilenameTuples( strictCheck=strictCheck )
        possibleExt = self.getPossibleFilenameTuplesExt()
        possibleInt = self.getPossibleFilenameTuplesInt()
        # print( f"({len(confirmed)}) {confirmed=}")
        # print( f"({len(possibleExt)}) {possibleExt=}")
        # print( f"({len(possibleInt)}) {possibleInt=}")

        if len(possibleExt) >= len(confirmed) and len(possibleExt) >= len(possibleInt):
            return possibleExt
        if len(possibleInt) >= len(confirmed):
            return possibleInt
        return confirmed
    # end of USFMFilenames.getMaximumPossibleFilenameTuples


    def getUnusedFilenames( self ):
        """
        Return a list of filenames which didn't seem to be USFM files.
        """
        if self.lastTupleList is None: return []
        folderFilenames = os.listdir( self.givenFolderName )
        matched = [f for _, f in self.lastTupleList]
        return [f for f in folderFilenames if f not in matched and os.path.isfile(os.path.join(self.givenFolderName, f))]
    # end of USFMFilenames.getUnusedFilenames


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """
        Return a list of full pathnames of .ssf files in the folder.
        """
        def getSSFFilenamesHelper( folder ):
            resultPathlist = []
            try:
                files = os.listdir( folder )
                for foundFilename in files:
                    if not foundFilename.endswith('~'): # Ignore backup files
                        foundFileBit, foundExtBit = os.path.splitext( foundFilename )
                        if foundExtBit.lower()=='.ssf':
                            resultPathlist.append( os.path.join( folder, foundFilename ) )
            except FileNotFoundError: pass
            return resultPathlist
        # end of getSSFFilenamesHelper

        filelist = getSSFFilenamesHelper( self.givenFolderName )
        if not filelist and searchAbove: # try the next level up
            filelist = getSSFFilenamesHelper( os.path.join( self.givenFolderName, '../' ) )
            if auto and len(filelist)>1: # See if we can help them by automatically choosing the right one
                count, index = 0, -1
                for j, filepath in enumerate(filelist): # Check if we can find a single matching ssf file
                    foundPathBit, foundExtBit = os.path.splitext( filepath )
                    foundPathBit, foundFileBit = os.path.split( foundPathBit )
                    if foundFileBit in str(self.givenFolderName):
                        index = j; count += 1 # Take a guess that this might be the right one
                if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"getSSFFilenames: returning filelist ({len(filelist)})={filelist}" )
        return filelist
    # end of USFMFilenames.getSSFFilenames
# end of class USFMFilenames


def briefDemo() -> None:
    """ Demonstrate finding files in some USFM Bible folders. """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # These are relative paths -- you can replace these with your test folder(s)
    testFolders = (BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                   Path( '/srv/AutoProcesses/Processed/' ),
                   Path( '/srv/AutoProcesses/Processed/Test/' ),
                   )
    for j, testFolder in enumerate( testFolders ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'\n{j+1}' )
        if os.access( testFolder, os.R_OK ):
            UFns = USFMFilenames( testFolder )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, UFns )
            result = UFns.getAllFilenames(); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nAll: {len(result)} files found" )
            result = UFns.getMaximumPossibleFilenameTuples(); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nMaxPoss: {len(result)} books found" )
            if result: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  First book: {result[0]}, Last book: {result[-1]}" )
            result = UFns.getUnusedFilenames(); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Unused: {len(result)} files" )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )

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
# end of USFMFilenames.py
