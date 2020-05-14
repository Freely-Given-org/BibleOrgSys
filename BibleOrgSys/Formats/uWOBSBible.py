#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# uWOBSBible.py
#
# Module handling unfoldingWord Open Bible Stories stored in markdown files.
#
# Copyright (C) 2020 Robert Hunt
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
Module for defining and manipulating complete or partial uW Open Bible Stories.

Note that we squeeze the MD format into pseudo-USFM.
We create a Bible object with a single 'OBS' book.
Story numbers (1..50) are stored as chapters.
Frame numbers are stored as verses.
Image links are stored in \\fig fields.
Frame text is stored in the verse fields.
"""
from gettext import gettext as _
from typing import Dict, List, Any, Optional
import os
from pathlib import Path
import logging
import multiprocessing
import re

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry
from BibleOrgSys.Formats.uWNotesBible import loadYAML


LAST_MODIFIED_DATE = '2020-05-06' # by RJH
SHORT_PROGRAM_NAME = "uWOBSBible"
PROGRAM_NAME = "unfoldingWord Open Bible Stories handler"
PROGRAM_VERSION = '0.01'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot

METADATA_FILENAME = 'manifest.yaml'


def uWOBSBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for uW OBS Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one uW OBS Bible is found,
        returns the loaded uWOBSBible object.
    """
    vPrint( 'Info', debuggingThisModule, "uWOBSBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( "uWOBSBibleFileCheck: Given {!r} folder is unreadable".format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( "uWOBSBibleFileCheck: Given {!r} path is not a folder".format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', debuggingThisModule, " uWOBSBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS \
            and something not in ('content', '.apps'):
                foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )

    # See if there's an uWOBSBible project here in this given folder
    numFound = 0
    if METADATA_FILENAME in foundFiles:
        numFound += 1
        if strictCheck:
            for folderName in foundFolders:
                vPrint( 'Quiet', debuggingThisModule, "uWOBSBibleFileCheck: Suprised to find folder:", folderName )
    if numFound:
        vPrint( 'Info', debuggingThisModule, "uWOBSBibleFileCheck got {} in {}".format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uWnB = uWOBSBible( givenFolderName )
            if autoLoad: uWnB.preload()
            if autoLoadBooks: uWnB.loadBooks() # Load and process the file
            return uWnB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("uWOBSBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        vPrint( 'Verbose', debuggingThisModule, "    uWOBSBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ):
                    if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS \
                    and something not in ('content', '.apps'):
                        foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    ignore = False
                    for ending in filenameEndingsToIgnore:
                        if somethingUpper.endswith( ending): ignore=True; break
                    if ignore: continue
                    if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                        foundSubfiles.append( something )
        except PermissionError: pass # can't read folder, e.g., system folder

        # See if there's an uW OBS Bible here in this folder
        if METADATA_FILENAME in foundSubfiles:
            numFound += 1
            if strictCheck:
                for folderName in foundSubfolders:
                    vPrint( 'Quiet', debuggingThisModule, "uWOBSBibleFileCheckSuprised to find folder:", folderName )
    if numFound:
        vPrint( 'Info', debuggingThisModule, "uWOBSBibleFileCheck foundProjects {} {}".format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uWnB = uWOBSBible( foundProjects[0] )
            if autoLoad: uWnB.preload()
            if autoLoadBooks: uWnB.loadBooks() # Load and process the file
            return uWnB
        return numFound
# end of uWOBSBibleFileCheck



class uWOBSBible( Bible ):
    """
    Class to load and manipulate uW OBS Bibles.

    """
    def __init__( self, sourceFolder, givenName:Optional[str]=None, givenAbbreviation:Optional[str]=None, encoding:Optional[str]=None ) -> None:
        """
        Create the internal uW OBS Bible object.

        Note that sourceFolder can be None if we don't know that yet.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'uW OBS Bible object'
        self.objectTypeString = 'uW OBS'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding
    # end of uWOBSBible.__init_


    def preload( self ) -> None:
        """
        Loads the Metadata file if it can be found.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, _("preload() from {}").format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( _("uWOBSBible.preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("uWOBSBible.preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            vPrint( 'Quiet', debuggingThisModule, _("uWOBSBible.preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        #if self.metadataFilepath is None: # it might have been loaded first
        # Attempt to load the metadata file
        self.loadMetadata( os.path.join( self.sourceFolder, METADATA_FILENAME ) )
        if isinstance( self.givenBookList, list ):
            self.availableBBBs.update( self.givenBookList )

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "uW OBS Bible"

        self.preloadDone = True
    # end of uWOBSBible.preload


    def loadMetadata( self, metadataFilepath ) -> None:
        """
        Process the metadata from the given filepath.

        Sets some class variables and puts a dictionary into self.settingsDict.
        """
        vPrint( 'Never', debuggingThisModule, "Loading metadata from {!r}".format( metadataFilepath ) )
        self.metadataFilepath = metadataFilepath
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        if 'uW' not in self.suppliedMetadata: self.suppliedMetadata['uW'] = {}
        self.suppliedMetadata['uW']['Manifest'] = loadYAML( metadataFilepath )
        vPrint( 'Never', debuggingThisModule, f"\ns.sM: {self.suppliedMetadata}" )

        if self.suppliedMetadata['uW']['Manifest']:
            self.applySuppliedMetadata( 'uW' ) # Copy some to self.settingsDict
            vPrint( 'Never', debuggingThisModule, f"\ns.sD: {self.settingsDict}" )
    # end of uWOBSBible.loadMetadata


    def loadBook( self, BBB:str ) -> None:
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        vPrint( 'Info', debuggingThisModule, "uWOBSBible.loadBook( {} )".format( BBB ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading uW OBS {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            vPrint( 'Verbose', debuggingThisModule, _("  uWOBSBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
            bcvBB = uWOBSBibleBook( self, BBB )
            bcvBB.load()
            if bcvBB._rawLines:
                self.stashBook( bcvBB )
                bcvBB.validateMarkers()
            else: logging.info( "uW OBS book {} was completely blank".format( BBB ) )
            self.availableBBBs.add( BBB )
        else: logging.info( "uW OBS book {} is not listed as being available".format( BBB ) )
    # end of uWOBSBible.loadBook


    def _loadBookMP( self, BBB:str ) -> Optional[BibleBook]:
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        vPrint( 'Verbose', debuggingThisModule, _("loadBookMP( {} )").format( BBB ) )
        assert BBB not in self.books
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', debuggingThisModule, '  ' + "Loading {} from {} from {}…".format( BBB, self.name, self.sourceFolder ) )
            bcvBB = uWOBSBibleBook( self, BBB )
            bcvBB.load()
            bcvBB.validateMarkers()
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("    Finishing loading uW OBS book {}.").format( BBB ) )
            return bcvBB
        else: logging.info( "uW OBS book {} is not listed as being available".format( BBB ) )
    # end of uWOBSBible.loadBookMP


    def loadBooks( self ) -> None:
        """
        Load all the books.
        """
        vPrint( 'Normal', debuggingThisModule, f"Loading '{self.name}' from {self.sourceFolder}…" )

        if not self.preloadDone: self.preload()

        if self.givenBookList:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Loading {} uW OBS books using {} processes…".format( len(self.givenBookList), BibleOrgSysGlobals.maxProcesses ) )
                    vPrint( 'Quiet', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.givenBookList ) # have the pool do our loads
                    assert len(results) == len(self.givenBookList)
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB in self.givenBookList:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #vPrint( 'Quiet', debuggingThisModule, _("  uWOBSBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    loadedBook = self.loadBook( BBB ) # also saves it
        else:
            logging.critical( "uWOBSBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #vPrint( 'Quiet', debuggingThisModule, self.getBookList() )
        self.doPostLoadProcessing()
    # end of uWOBSBible.load
# end of class uWOBSBible



class uWOBSBibleBook( BibleBook ):
    """
    Class to load and manipulate a single uW OBS file / book.
    """

    def __init__( self, containerBibleObject:Bible, BBB:str ) -> None:
        """
        Create the uW OBS Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'uW OBS Bible Book object'
        self.objectTypeString = 'uW OBS'
    # end of uWOBSBibleBook.__init__


    def load( self ) -> None:
        """
        Load the uW OBS Bible book from a folder.

        Tries to standardise by combining physical lines into logical lines,
            i.e., so that all lines begin with a uW OBS paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """
        self.sourceFolder = self.containerBibleObject.sourceFolder
        vPrint( 'Info', debuggingThisModule, "  " + _("Loading {} from {}…").format( self.BBB, self.sourceFolder ) )

        assert self.BBB == 'OBS'
        assert self.containerBibleObject.suppliedMetadata['uW']['Manifest']['projects'][0]['path'] == './content'

        contentFolder = os.path.join( self.sourceFolder, 'content/' )


        def doAddLine( originalMarker:str, originalText:str ) -> None:
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            vPrint( 'Never', debuggingThisModule, "doAddLine( {}, {} )".format( repr(originalMarker), repr(originalText) ) )
            self.addLine( originalMarker, originalText ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
            # marker, text = originalMarker, originalText.replace( '~', ' ' )
            # if '\\' in text: # Check markers inside the lines
            #     markerList = BibleOrgSysGlobals.BCVMarkers.getMarkerListFromText( text )
            #     ix = 0
            #     for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
            #         if insideMarker == '\\': # it's a free-standing backspace
            #             loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: {!r}").format( self.BBB, C, V, marker, text ) )
            #             logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
            #             self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
            #         elif BibleOrgSysGlobals.BCVMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
            #             if ix==0:
            #                 loadErrors.append( _("{} {}:{} NewLine marker {!r} shouldn't appear within line in \\{}: {!r}").format( self.BBB, C, V, insideMarker, marker, text ) )
            #                 logging.error( _("NewLine marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
            #                 self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
            #             thisText = text[ix:iMIndex].rstrip()
            #             self.addLine( marker, thisText )
            #             ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
            #             #vPrint( 'Quiet', debuggingThisModule, "Did a split from {}:{!r} to {}:{!r} leaving {}:{!r}".format( originalMarker, originalText, marker, thisText, insideMarker, text[ix:] ) )
            #             marker = insideMarker # setup for the next line
            #     if ix != 0: # We must have separated multiple lines
            #         text = text[ix:] # Get the final bit of the line
            # self.addLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of doAddLine


        fixErrors = []
        for storyNumber in range(1,50+1):
            storyNumberString = str(storyNumber).zfill(2)
            mdFilepath = os.path.join( contentFolder, f'{storyNumberString}.md' )
            with open( os.path.join( mdFilepath ), 'rt', encoding='utf-8' ) as mdFile: # Automatically closes the file when done
                lineCount = state = 0
                for line in mdFile:
                    line = line.rstrip( '\n\r' )
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "loaduWOBSBibleBook: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                        line = line[1:] # Remove the Byte Order Marker (BOM)
                    # vPrint( 'Quiet', debuggingThisModule, state, lineCount, "line", line )
                    if lineCount == 1: # Title line
                        assert state == 0
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                            assert line.startswith( '# ')
                        title = line[2:]
                        doAddLine( 'c', str(storyNumber) )
                        doAddLine( 's1', title )
                        # doAddLine( 'p', '' )
                        V = 0
                        state = 1
                    elif not line:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                            assert state in (1,3,5,7)
                        state += 1
                    elif state == 2:
                        if line.startswith( '![OBS Image](' ):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                                assert line.endswith( '.jpg)' )
                            V += 1
                            doAddLine( 'v', f'{V} \\fig |src="{line[13:-1]}"\\fig*' )
                            state = 3
                        else: # Assume it's the references
                            if line[0] == '_' and line[-1] == '_': line = line[1:-1]
                            doAddLine( 'r', line )
                            state = 9
                    elif state == 4:
                        doAddLine( 'p', line)
                        state = 1
                    else:
                        halt
            #if loadErrors: self.checkResultsDictionary['Load Errors'] = loadErrors
            #if debugging: vPrint( 'Quiet', debuggingThisModule, self._rawLines ); halt
        if fixErrors: self.checkResultsDictionary['Fix Text Errors'] = fixErrors
    # end of load
# end of class uWOBSBibleBook



def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/unfoldingWordHelps/en_obs/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA1" )
        result1 = uWOBSBibleFileCheck( testFolderpath )
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA1", result1 )

        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA2" )
        result2 = uWOBSBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA3" )
        result3 = uWOBSBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolderpath ):
            somepath = os.path.join( testFolderpath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nuW OBS D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolderpath, someFolder+'/' )
                testBCV( someFolder )


    if 0: # Load and process some of our test versions
        count = 0
        for name, encoding, testFolder in (
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest1/')),
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest2/')),
                                        ("Exported", 'utf-8', "Tests/BOS_BCV_Export/"),
                                        ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', debuggingThisModule, "\nuW OBS A{}/".format( count ) )
                uWnB = uWOBSBible( testFolder, name, encoding=encoding )
                uWnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( uWnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( uWnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( uWnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( uWnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, uWnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    uWnB.check()
                    #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = uWnB.getCheckResults()
                    # vPrint( 'Quiet', debuggingThisModule, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##uWnB.toDrupalBible()
                    uWnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
            else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
#end of uWOBSBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/unfoldingWordHelps/en_obs/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA1" )
        result1 = uWOBSBibleFileCheck( testFolderpath )
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA1", result1 )

        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA2" )
        result2 = uWOBSBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        vPrint( 'Quiet', debuggingThisModule, "\nuW OBS TestA3" )
        result3 = uWOBSBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "uW OBS TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        for BBB in ('OBS','RUT','JN3'):
            vPrint( 'Quiet', debuggingThisModule, f"OBS 1:1 gCVD", result3.getContextVerseData( ('OBS','1','1','') ) )
            vPrint( 'Quiet', debuggingThisModule, f"OBS 1:1 gVDL", result3.getVerseDataList( ('OBS','1','1','') ) )
            vPrint( 'Quiet', debuggingThisModule, f"OBS 1:1 gVT", result3.getVerseText( ('OBS','1','1','') ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolderpath ):
            somepath = os.path.join( testFolderpath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nuW OBS D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolderpath, someFolder+'/' )
                testBCV( someFolder )


    if 0: # Load and process some of our test versions
        count = 0
        for name, encoding, testFolder in (
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest1/')),
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest2/')),
                                        ("Exported", 'utf-8', "Tests/BOS_BCV_Export/"),
                                        ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', debuggingThisModule, "\nuW OBS A{}/".format( count ) )
                uWnB = uWOBSBible( testFolder, name, encoding=encoding )
                uWnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( uWnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( uWnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( uWnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( uWnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, uWnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    uWnB.check()
                    #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = uWnB.getCheckResults()
                    # vPrint( 'Quiet', debuggingThisModule, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##uWnB.toDrupalBible()
                    uWnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
            else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
# end of uWOBSBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of uWOBSBible.py
