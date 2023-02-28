#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# LEBXMLBible.py
#
# Module handling LEB XML Bibles
#
# Copyright (C) 2023 Robert Hunt
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
Module handling the reading and import of LEB XML Bibles.
"""
from gettext import gettext as _
from typing import List, Tuple
import logging
import os
import sys
from pathlib import Path
from xml.etree.ElementTree import ElementTree, ParseError
# import multiprocessing

if __name__ == '__main__':
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.ISO_639_3_Languages import ISO_639_3_Languages
# from BibleOrgSys.Reference.USFM3Markers import USFM_BIBLE_PARAGRAPH_MARKERS
from BibleOrgSys.Bible import Bible, BibleBook


LAST_MODIFIED_DATE = '2023-02-28' # by RJH
SHORT_PROGRAM_NAME = "LEBXMLBible"
PROGRAM_NAME = "LEB XML Bible format handler"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA') # Must be UPPERCASE
EXTENSIONS_TO_IGNORE = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


# Get the data tables that we need for proper checking
ISOLanguages = ISO_639_3_Languages().loadData()



def LEBXMLBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for LEB XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one LEB Bible is found,
        returns the loaded LEBXMLBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"LEBXMLBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("LEBXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("LEBXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    # LEB is tricky coz a whole Bible can be in one file (normally), or in lots of separate (book) files
    #   and we don't want to think that 66 book files are 66 different LEB Bibles
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, " LEBXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles, foundBookFiles = [], [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in FILENAME_ENDINGS_TO_IGNORE:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                foundFiles.append( something )
                for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                    # osisBkCodes are all UPPERCASE
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                    if osisBkCode in somethingUpper:
                        foundBookFiles.append( something ); break
    #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'LEB ff', foundFiles, foundBookFiles )

    # See if there's an LEB project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OSISa (unexpected) first line was {firstLines} in {thisFilename}" )
                continue
            if '<leb>' not in firstLines[1] and '<leb>' not in firstLines[2]:
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound>1 and numFound==len(foundBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "LEBXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = LEBXMLBible( givenFolderName, lastFilenameFound ) # lastFilenameFound can be None
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    LEBXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles, foundSubBookFiles = [], [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    ignore = False
                    for ending in FILENAME_ENDINGS_TO_IGNORE:
                        if somethingUpper.endswith( ending): ignore=True; break
                    if ignore: continue
                    if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                        foundSubfiles.append( something )
                        for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                            # osisBkCodes are all UPPERCASE
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                            if osisBkCode in somethingUpper:
                                foundSubBookFiles.append( something ); break
        except PermissionError: pass # can't read folder, e.g., system folder
        #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'LEB fsf', foundSubfiles, foundSubBookFiles )

        # See if there's an LEB project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=3 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OSISb (unexpected) first line was {firstLines} in {thisFilename}" )
                    continue
                if '<leb>' not in firstLines[1] and '<leb>' not in firstLines[2]:
                    continue
            foundProjects.append( (tryFolderName, thisFilename) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound>1 and numFound==len(foundSubBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "LEBXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = LEBXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
# end of LEBXMLBibleFileCheck



def clean( elementText, loadErrors=None, location=None, verseMilestone=None ):
    """
    Given some text from an XML element text or tail field (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.

    If the text is None, returns None
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"LEBXMLBible.clean( '{elementText}', '{location}', {verseMilestone} )" )
    if loadErrors: assert isinstance( loadErrors, list )
    if location: assert isinstance( location, str )
    if verseMilestone: assert isinstance( verseMilestone, str )

    if elementText is None: return None
    assert isinstance( elementText, str )
    # else it's not None

    info = ''
    if location: info += ' at ' + location
    if verseMilestone: info += ' at ' + verseMilestone

    result = elementText
    while result.endswith('\n') or result.endswith('\r'): result = result[:-1] # Drop off trailing newlines (assumed to be irrelevant)
    if '  ' in result:
        errorMsg = _("clean: found multiple spaces in {!r}{}").format( result, info )
        if DEBUGGING_THIS_MODULE: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
    if '\t' in result:
        errorMsg = _("clean: found tab in {!r}{}").format( result, info )
        if DEBUGGING_THIS_MODULE: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\t', ' ' )
    if '\n' in result or '\r' in result:
        errorMsg = _("clean: found CR or LF characters in {!r}{}").format( result, info )
        if DEBUGGING_THIS_MODULE: logging.error( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
    while '  ' in result: result = result.replace( '  ', ' ' )
    return result
# end of clean



class LEBXMLBible( Bible ):
    """
    Class for reading, validating, and converting LEBXMLBible XML.
    """
    filenameBase = 'LEBXMLBible'
    # It does not matter if the NameSpace declarations are no longer valid online links
    XMLNameSpace = '{http://www.w3.org/XML/1998/namespace}'
    treeTag = 'leb'


    def __init__( self, sourceFilepath, givenName=None, givenAbbreviation=None, encoding='utf-8' ) -> None:
        """
        Constructor: just sets up the LEB Bible object.

        sourceFilepath can be a folder (esp. if each book is in a separate file)
            or the path of a specific file (probably containing the whole Bible -- most common)
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"LEBXMLBible.__init__( {sourceFilepath}, '{givenName}', '{givenAbbreviation}', {encoding} )" )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'LEB XML Bible object'
        self.objectTypeString = 'LEB'

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.givenAbbreviation, self.encoding  = sourceFilepath, givenName, givenAbbreviation, encoding


        self.title = self.version = self.date = self.source = None
        self.XMLTree = self.header = self.frontMatter = self.divs = self.divTypesString = None
        #self.bkData, self.USFMBooks = {}, {}
        self.lang = self.language = None


        # Do a preliminary check on the readability of our file(s)
        self.possibleFilenames = []
        self.possibleFilenameDict = {}
        if os.path.isdir( self.sourceFilepath ): # We've been given a folder -- see if we can find the files
            self.sourceFolder = self.sourceFilepath
            # There's no standard for LEB XML file naming
            fileList = os.listdir( self.sourceFilepath )
            # First try looking for LEB book names
            BBBList = []
            for filename in fileList:
                if 'VerseMap' in filename: continue # For WLC
                if filename.lower().endswith('.xml'):
                    self.sourceFilepath = os.path.join( self.sourceFolder, filename )
                    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Trying {}…".format( self.sourceFilepath ) )
                    if os.access( self.sourceFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
                        foundBBB = None
                        upperFilename = filename.upper()
                        for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                            # osisBkCodes are all UPPERCASE
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                            if osisBkCode in upperFilename:
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "LEBXMLBible.__init__ found {!r} in {!r}".format( osisBkCode, upperFilename ) )
                                if 'JONAH' in upperFilename and osisBkCode=='NAH': continue # Handle bad choice
                                if 'ZEPH' in upperFilename and osisBkCode=='EPH': continue # Handle bad choice
                                assert not foundBBB # Don't expect duplicates
                                foundBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBkCode, strict=True )
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  FoundBBB1 = {!r}".format( foundBBB ) )
                        if not foundBBB: # Could try a USFM/Paratext book code -- what writer creates these???
                            for bkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes( toUpper=True ):
                                # returned bkCodes are all UPPERCASE
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'bc', bkCode, upperFilename )
                                if bkCode in upperFilename:
                                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'LEBXMLBible.__init__ ' + _("found {!r} in {!r}").format( bkCode, upperFilename ) )
                                    if foundBBB: # already -- don't expect doubles
                                        logging.warning( 'LEBXMLBible.__init__: ' + _("Found a second possible book abbreviation for {} in {}").format( foundBBB, filename ) )
                                    foundBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bkCode, strict=True )
                                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  FoundBBB2 = {!r}".format( foundBBB ) )
                        if foundBBB:
                            if isinstance( foundBBB, list ): foundBBB = foundBBB[0] # Take the first option
                            assert isinstance( foundBBB, str )
                            BBBList.append( foundBBB )
                            self.availableBBBs.add( foundBBB )
                            self.possibleFilenameDict[foundBBB] = filename
            # Now try to sort the booknames in self.possibleFilenames to a better order
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Was", len(self.possibleFilenames), self.possibleFilenames )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  have", len(BBBList), BBBList )
            assert (len(BBBList)==0 and len(self.possibleFilenames)==1) \
                    or len(BBBList) == len(self.possibleFilenames) # Might be no book files (if all in one file)
            newCorrectlyOrderedList = []
            for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes: # ordered by reference number
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
                if BBB in BBBList:
                    ix = BBBList.index( BBB )
                    newCorrectlyOrderedList.append( self.possibleFilenames[ix] )
            self.possibleFilenames = newCorrectlyOrderedList
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Now", self.possibleFilenames ); halt
        else: # it's presumably a file name
            self.sourceFolder = os.path.dirname( self.sourceFilepath )
            if not os.access( self.sourceFilepath, os.R_OK ):
                logging.critical( 'LEBXMLBible: ' + _("File {!r} is unreadable").format( self.sourceFilepath ) )
                return # No use continuing
            vPrint( 'Never', DEBUGGING_THIS_MODULE, f"LEBXMLBible possibleFilenames: {self.possibleFilenames}" )

        self.name, self.abbreviation = self.givenName, self.givenAbbreviation
        self.workNames, self.workPrefixes = [], {}
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['LEB'] = {}
    # end of LEBXMLBible.__init__


    def loadBooks( self ):
        """
        Loads the LEB XML file or files.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "LEBXMLBible.loadBooks()" )

        loadErrors:List[str] = []
        if self.possibleFilenames and len(self.possibleFilenames) > 1: # then we possibly have multiple files, probably one for each book
            # if BibleOrgSysGlobals.maxProcesses > 1 \
            # and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            #     # Load all the books as quickly as possible
            #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(self.possibleFilenames)} LEB books using {BibleOrgSysGlobals.maxProcesses} processes…" )
            #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed.") )
            #     BibleOrgSysGlobals.alreadyMultiprocessing = True
            #     with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            #         results = pool.map( self._loadBookFileMP, self.possibleFilenames ) # have the pool do our loads
            #         assert len(results) == len(self.possibleFilenames)
            #         for bBook,bookLoadErrors in results:
            #             self.stashBook( bBook ) # Saves them in the correct order
            #             loadErrors += bookLoadErrors
            #     BibleOrgSysGlobals.alreadyMultiprocessing = False
            # else: # Just single threaded
                for filename in self.possibleFilenames:
                    pathname = os.path.join( self.sourceFolder, filename )
                    loadedBooks = self.__loadFile( pathname )
                    for loadedBook,bookLoadErrors in loadedBooks:
                        self.stashBook( loadedBook )
                        loadErrors += bookLoadErrors
        elif os.path.isfile( self.sourceFilepath ): # most often we have all the Bible books in one file
            loadedBooks = self.__loadFile( self.sourceFilepath )
            for loadedBook,bookLoadErrors in loadedBooks:
                self.stashBook( loadedBook )
                loadErrors += bookLoadErrors
        else:
            logging.critical( f"LEBXMLBible: Didn't find anything to load at {self.sourceFilepath}" )
            loadErrors.append( _("LEBXMLBible: Didn't find anything to load at {}").format( self.sourceFilepath ) )
        if loadErrors:
            self.checkResultsDictionary['Load Errors'] = loadErrors
            #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "loadErrors", len(loadErrors), loadErrors ); halt
        # TEMP: commented out
        # self.applySuppliedMetadata( 'LEB' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of LEBXMLBible.loadBooks()

    def load( self ):
        self.loadBooks()


    # def loadBook( self, BBB:str, filename=None ):
    #     """
    #     Load the requested book into self.books if it's not already loaded.

    #     #NOTE: You should ensure that preload() has been called first.
    #     """
    #     if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2 or DEBUGGING_THIS_MODULE:
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "LEBXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
    #         #assert self.preloadDone

    #     if not self.possibleFilenames: # then the whole Bible was probably in one file
    #         vPrint( 'Info', DEBUGGING_THIS_MODULE, "  Unable to load LEB by individual book (only whole Bible?) -- returning" )
    #         return # nothing to do here

    #     if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
    #         if BBB in self.books:
    #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {BBB} is already loaded -- returning" )
    #             return # Already loaded
    #         if BBB in self.triedLoadingBook:
    #             logging.warning( "We had already tried loading LEB {} for {}".format( BBB, self.name ) )
    #             return # We've already attempted to load this book
    #     self.triedLoadingBook[BBB] = True

    #     if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("  LEBXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
    #     if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
    #     if filename is None: raise FileNotFoundError( "LEBXMLBible.loadBook: Unable to find file for {}".format( BBB ) )
    #     #BB = BibleBook( self, BBB )
    #     #BB.load( filename, self.sourceFolder, self.encoding )
    #     #if BB._rawLines:
    #         #BB.validateMarkers() # Usually activates InternalBibleBook.processLines()
    #         #self.stashBook( BB )
    #     #else: logging.info( "LEB book {} was completely blank".format( BBB ) )
    #     loadErrors:List[str] = []
    #     pathname = os.path.join( self.sourceFolder, filename )
    #     loadedBooks = self.__loadFile( pathname )
    #     assert len(loadedBooks) == 1
    #     for loadedBook,loadErrors in loadedBooks:
    #         self.stashBook( loadedBook )
    #         loadErrors += loadErrors
    #     self.bookNeedsReloading[BBB] = False
    #     if loadErrors:
    #         if 'Load Errors' not in self.checkResultsDictionary: self.checkResultsDictionary['Load Errors'] = []
    #         self.checkResultsDictionary['Load Errors'].extend( loadErrors )
    #         #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "loadErrors", len(loadErrors), loadErrors ); halt
    #     self.applySuppliedMetadata( 'LEB' ) # Copy some to self.settingsDict
    #     #self.doPostLoadProcessing() # Should only be done after loading ALL books
    # # end of LEBXMLBible.loadBook function


    # def _loadBookFileMP( self, XMLBookFilename ) -> BibleBook:
    #     """
    #     Multiprocessing version!
    #     Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

    #     Parameter is a 2-tuple containing BBB and the filename.

    #     Returns the book info.
    #     """
    #     fnPrint( DEBUGGING_THIS_MODULE, f"_loadBookFileMP( {XMLBookFilename} )" )
    #     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  LoadingMP {self.name} book from {XMLBookFilename} from {self.sourceFolder}…" )

    #     pathname = os.path.join( self.sourceFolder, XMLBookFilename )
    #     result = self.__loadFile( pathname )
    #     assert len(result) == 1 # only one book
    #     assert len(result[0]) == 2 # book and errors
    #     return result[0]
    # # end of LEBXMLBible._loadBookFileMP function


    def __loadFile( self, OSISFilepath ) -> List[BibleBook]:
        """
        Load a single source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  LEBXMLBible loading {OSISFilepath}…" )

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Resetting bookList and loadErrors")
        bookList:List[Tuple[BibleBook,List[str]]] = []
        loadErrors:List[str] = []

        try: self.XMLTree = ElementTree().parse( OSISFilepath )
        except ParseError as err:
            logging.critical( _("Loader parse error in xml file {}: {} {}").format( OSISFilepath, sys.exc_info()[0], err ) )
            loadErrors.append( _("Loader parse error in xml file {}: {} {}").format( OSISFilepath, sys.exc_info()[0], err ) )
            return
        if BibleOrgSysGlobals.debugFlag: assert self.XMLTree # Fail here if we didn't load anything at all

        # Find the main container
        if self.XMLTree.tag == LEBXMLBible.treeTag:
            location = 'LEB file'
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, location, 'fhg1', loadErrors )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8', loadErrors )

            # Process the (70) main containers
            for element in self.XMLTree:
                BibleOrgSysGlobals.checkXMLNoText( element, location, '3f54', loadErrors )
                if element.tag != 'book':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'ks52', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ka10', loadErrors )
                if element.tag == 'title': self.processTitle( element, loadErrors )
                elif element.tag == 'license': self.processLicense( element, loadErrors )
                elif element.tag == 'trademark': self.processTrademark( element, loadErrors )
                elif element.tag == 'preface': self.processPreface( element, loadErrors )
                elif element.tag == 'book': self.processBook( element, bookList, loadErrors )
                else:
                    logging.error( "v4g7 Unprocessed {!r} element ({}) in {}".format( element.tag, element.text, location ) )
                    loadErrors.append( "Unprocessed {!r} element ({}) in {}(v4g7)".format( element.tag, element.text, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if len( bookList ) == 1:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    _loadFile({OSISFilepath}) is returning {bookList[0][0].BBB} with {len(bookList[0][1])} loadErrors" )
        else: # More than one book in this LEB file
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    _loadFile({OSISFilepath}) is returning {len(bookList)} books" )
        return bookList
    # end of LEBXMLBible._loadFile function


    def addLine( self, marker, rest, alObject ) -> None:
        """
        Extra shim function to help debugging.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"addLine( {marker=}, {rest=}, ... )" )
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"===> Adding line {marker}='{rest}'")
        alObject.addLine( marker, rest )
    # end of addLine

    def appendToLastLine( self, rest, alObject ) -> None:
        """
        Extra shim function to help debugging.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"appendToLastLine( {rest=}, ... )" )
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"===> Appending line '{rest}'")
        alObject.appendToLastLine( rest )
    # end of appendToLastLine


    def processTitle( self, element, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processTitle( {element}, {len(loadErrors)} )" )
    # end of processTitle


    def processLicense( self, element, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processLicense( {element}, {len(loadErrors)} )" )
    # end of processLicense


    def processTrademark( self, element, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processTrademark( {element}, {len(loadErrors)} )" )
    # end of processTrademark


    def processPreface( self, element, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processPreface( {element}, {len(loadErrors)} )" )
    # end of processPreface


    def processBook( self, bookElement, bookList, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processBook( {bookElement}, {len(bookList)}, {len(loadErrors)} )" )

        location = 'processBook'
        BibleOrgSysGlobals.checkXMLNoText( bookElement, location, 'js23', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( bookElement, location, 'kad1', loadErrors )

        # Process the attributes first
        bookID = None
        for attrib,value in bookElement.items():
            if attrib=='id':
                bookID = value
            else:
                logging.warning( "mf82 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (mf82)".format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        # The book IDs seem to be OSIS (or SBL)
        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromShortAbbreviation( bookID )
        USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
        USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumStr( BBB )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  It seems we have {BBB}" )
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'OSIS XML Bible Book object'
        thisBook.objectTypeString = 'OSIS'
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Appending {thisBook.BBB} and {len(loadErrors)} load errors to bookList" )
        for bkLE in bookList:
            assert len(bkLE) == 2 # bookObject and loadErrors
            assert bkLE[0].BBB != BBB # Don't allow duplicate books
        bookList.append( (thisBook,loadErrors.copy()) )
        loadErrors.clear()
        self.haveBook = True
        doneChapter = False
        for subelement in bookElement:
            BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'kf93', loadErrors )
            if subelement.tag == 'chapter':
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'jf21', loadErrors )
                self.processChapter( subelement, thisBook, loadErrors )
                doneChapter = True
            elif subelement.tag == 'pericope': # Some single-chapter books (not OBA but PHM, JDE)
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'jf21', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jf21', loadErrors )
                if not doneChapter:
                    self.addLine( 'c', '1', thisBook )
                    doneChapter = True
                self.addLine( 's1', subelement.text, thisBook )
            elif subelement.tag == 'p': # Some single-chapter books (not OBA but PHM, JDE)
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'jf21', loadErrors )
                if not doneChapter:
                    self.addLine( 'c', '1', thisBook )
                    doneChapter = True
                self.processParagraph( subelement, thisBook, loadErrors )
            else:
                logging.error( "kg63 Unprocessed {!r} subelement ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {}(kg63)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of processBook


    def processChapter( self, chapterElement, thisBook, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processChapter( {chapterElement}, ..., {len(loadErrors)} ) for {thisBook.BBB}" )
        assert isinstance( thisBook, BibleBook )

        location = 'processChapter'
        BibleOrgSysGlobals.checkXMLNoText( chapterElement, location, 'jck2', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( chapterElement, location, 'cvf6', loadErrors )

        # Process the attribute(s) first
        chapterID = None
        for attrib,value in chapterElement.items():
            if attrib=='id':
                chapterID = value
            else:
                logging.warning( "sw34 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (sw34)".format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        bits = chapterID.split( ' ' )
        assert len(bits) == 3 if chapterID[1]==' ' else 2 # e.g., '2 Sa 1'
        C = bits[-1]
        self.addLine( 'c', C, thisBook )

        V = '?'
        for subelement in chapterElement:
            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'hb67', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'ms24', loadErrors )
            if subelement.tag == 'pericope':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'ld10', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'ld01', loadErrors )
                haveOutstandingSpace = False
                self.addLine( 's1', subelement.text, thisBook )
                for sub2element in subelement:
                    if sub2element.tag == 'note':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'gdf3', loadErrors )
                        self.processNote( sub2element, thisBook, loadErrors )
                        # self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\f + \\fr {C}:{V} \\ft {sub2element.text}", thisBook )
                        # for sub3element in sub2element:
                        #     print( sub3element.tag )
                        #     if sub3element.tag == 'supplied':
                        #         BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         text = sub3element.text
                        #         assert text
                        #         hadOutstandingSpace = haveOutstandingSpace # Remember
                        #         if text[-1] == ' ':
                        #             text = text[:-1]
                        #             haveOutstandingSpace = True
                        #         self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                        #         if tail := clean( sub3element.tail, loadErrors, location ):
                        #             hadOutstandingSpace = haveOutstandingSpace # Remember
                        #             if tail[-1] == ' ':
                        #                 tail = tail[:-1]
                        #                 haveOutstandingSpace = True
                        #             else: haveOutstandingSpace = False
                        #             if tail: # still
                        #                 self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                    else:
                        logging.error( "jk42 Unprocessed {!r} sub2element ({}) in {}".format( sub2element.tag, sub2element.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub2element ({}) in {}(jk42)".format( sub2element.tag, sub2element.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif subelement.tag == 'p':
                self.processParagraph( subelement, thisBook, loadErrors )
            elif subelement.tag == 'ul':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'aj48', loadErrors )
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'jh82', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'c7mn', loadErrors )
                self.processList( subelement, thisBook, loadErrors )
            else:
                logging.error( "mas9 Unprocessed {!r} subelement ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {}(mas9)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of processChapter


    def processParagraph( self, element, thisBook, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processParagraph( {element}, ..., {len(loadErrors)} ) for {thisBook.BBB}" )
        assert isinstance( thisBook, BibleBook )

        location = 'processParagraph'
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'jkh9', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( element, location, 'adq3', loadErrors )

        haveOutstandingSpace = False
        text = element.text
        if text and text[-1] == ' ':
            text = text[:-1]
            haveOutstandingSpace = True
        self.addLine( 'p', '' if text is None else text, thisBook )

        C = V = '?'
        for subelement in element:
            if subelement.tag == 'verse-number':
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'gdh0', loadErrors )
                # Process the attribute(s) first
                verseID = None
                for attrib,value in subelement.items():
                    if attrib=='id':
                        verseID = value
                    else:
                        logging.warning( "kq73 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (kq73)".format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                bits = verseID.split( ' ' )
                assert len(bits) == 3 if verseID[1]==' ' else 2 # e.g., '2 Sa 1:1'
                try: C,V = bits[-1].split( ':' )
                except ValueError: # if there's no colon
                    # I think this is a random LEB encoding fault like '<p><verse-number id="Ge 2">2</verse-number><verse-number id="Ge 2:1">1</verse-number> And heaven...'
                    continue
                assert subelement.text.strip() == subelement.text
                self.addLine( 'v', f'{subelement.text} ', thisBook )
                # assert haveOutstandingSpace == False # Why not???
                haveOutstandingSpace = False
                if tail := clean( subelement.tail, loadErrors, location ):
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    if tail: # still
                        self.appendToLastLine( tail, thisBook )
            elif subelement.tag == 'supplied':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'mns3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'gd63', loadErrors )
                self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\add {subelement.text}\\add*", thisBook )
                haveOutstandingSpace = False
                if tail := clean( subelement.tail, loadErrors, location ):
                    hadOutstandingSpace = haveOutstandingSpace # Remember it
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    if tail: # still
                        self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
            elif subelement.tag == 'note':
                self.processNote( subelement, thisBook, loadErrors )
            elif subelement.tag == 'tab':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'k6g7', loadErrors )
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'dx43', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jd52', loadErrors )
                self.appendToLastLine( f"  {subelement.tail if subelement.tail else ''}", thisBook ) # Double em-space
            elif subelement.tag == 'br':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'k6g7', loadErrors )
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'dx43', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jd52', loadErrors )
                assert not haveOutstandingSpace
                self.appendToLastLine( '//', thisBook ) # This is the USFM code for an optional line break
                # TODO: See if this is the correct way to handle the two <br /> in LEB
                if tail := clean( subelement.tail, loadErrors, location ):
                    hadOutstandingSpace = haveOutstandingSpace # Remember it
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    if tail: # still
                        self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
            elif subelement.tag == 'span':
                self.processSpan( subelement, thisBook, loadErrors )
            elif subelement.tag == 'i':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'k6g7', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jd52', loadErrors )
                assert subelement.text
                self.appendToLastLine( f"\\it {subelement.text}\\it*{subelement.tail if subelement.tail else ''}", thisBook )
            elif subelement.tag in ('idiom-start','idiom-end'): # should be self-closing
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'sd31', loadErrors )
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'bnd4', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jhw4', loadErrors )
                # TODO: We don't currently save this information
                if tail := clean( subelement.tail, loadErrors, location ):
                    hadOutstandingSpace = haveOutstandingSpace # Remember
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    else: haveOutstandingSpace = False
                    if tail: # still
                        self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
            else:
                logging.error( "bvd3 Unprocessed {!r} subelement ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {}(bvd3)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of processParagraph


    def processList( self, listElement, thisBook, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processList( {listElement}, ..., {len(loadErrors)} ) for {thisBook.BBB}" )
        assert isinstance( thisBook, BibleBook )

        location = 'processList'
        BibleOrgSysGlobals.checkXMLNoAttributes( listElement, location, 'f6hj', loadErrors )
        BibleOrgSysGlobals.checkXMLNoText( listElement, location, 'kas9', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( listElement, location, 'mn34', loadErrors )

        C = V = '?'
        haveOutstandingSpace = False
        for subelement in listElement:
            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'hb67', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'ms24', loadErrors )
            if subelement.tag in ('li1','li2','li3'):
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'ld10', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'ld01', loadErrors )
                self.addLine( subelement.tag, '', thisBook )
                text = subelement.text
                hadOutstandingSpace = haveOutstandingSpace # remember it
                if text and text[-1] == ' ':
                    text = text[:-1]
                    haveOutstandingSpace = True
                if text: # still
                    self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                for sub2element in subelement:
                    if sub2element.tag == 'verse-number':
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'gdh0', loadErrors )
                        # Process the attribute(s) first
                        verseID = None
                        for attrib,value in sub2element.items():
                            if attrib=='id':
                                verseID = value
                            else:
                                logging.warning( "kq73 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                                loadErrors.append( "Unprocessed {} attribute ({}) in {} (kq73)".format( attrib, value, location ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        bits = verseID.split( ' ' )
                        assert len(bits) == 3 if verseID[1]==' ' else 2 # e.g., '2 Sa 1:1'
                        try: C,V = bits[-1].split( ':' )
                        except ValueError: # if there's no colon
                            # I think this is a random LEB encoding fault like '<p><verse-number id="Ge 2">2</verse-number><verse-number id="Ge 2:1">1</verse-number> And heaven...'
                            continue
                        assert sub2element.text.strip() == sub2element.text
                        self.addLine( 'v', sub2element.text, thisBook )
                    elif sub2element.tag == 'supplied':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'mns3', loadErrors )
                        # BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'gd63', loadErrors )
                        self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\add {sub2element.text}\\add*", thisBook )
                        haveOutstandingSpace = False
                        if tail := clean( sub2element.tail, loadErrors, location ):
                            hadOutstandingSpace = haveOutstandingSpace # Remember it
                            if tail[-1] == ' ':
                                tail = tail[:-1]
                                haveOutstandingSpace = True
                            if tail: # still
                                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                    elif sub2element.tag == 'note':
                        # tag BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'gdf3', loadErrors )
                        self.processNote( sub2element, thisBook, loadErrors )
                        # self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\f + \\fr {C}:{V} \\ft {sub2element.text}", thisBook )
                        # for sub3element in sub2element:
                        #     print( sub3element.tag )
                        #     if sub3element.tag == 'supplied':
                        #         BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         text = sub3element.text
                        #         assert text
                        #         hadOutstandingSpace = haveOutstandingSpace # Remember
                        #         if text[-1] == ' ':
                        #             text = text[:-1]
                        #             haveOutstandingSpace = True
                        #         self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                        #         if tail := clean( sub3element.tail, loadErrors, location ):
                        #             hadOutstandingSpace = haveOutstandingSpace # Remember
                        #             if tail[-1] == ' ':
                        #                 tail = tail[:-1]
                        #                 haveOutstandingSpace = True
                        #             else: haveOutstandingSpace = False
                        #             if tail: # still
                        #                 self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                        #     elif sub3element.tag == 'cite':
                        #         # title BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         # BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         text = sub3element.text
                        #         if text:
                        #             hadOutstandingSpace = haveOutstandingSpace # Remember
                        #             if text[-1] == ' ':
                        #                 text = text[:-1]
                        #                 haveOutstandingSpace = True
                        #             self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                        #         if tail := clean( sub3element.tail, loadErrors, location ):
                        #             hadOutstandingSpace = haveOutstandingSpace # Remember
                        #             if tail[-1] == ' ':
                        #                 tail = tail[:-1]
                        #                 haveOutstandingSpace = True
                        #             else: haveOutstandingSpace = False
                        #             if tail: # still
                        #                 self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                        #     elif sub3element.tag == 'i':
                        #         BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         text = sub3element.text
                        #         assert text
                        #         hadOutstandingSpace = haveOutstandingSpace # Remember
                        #         if text[-1] == ' ':
                        #             text = text[:-1]
                        #             haveOutstandingSpace = True
                        #         self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                        #         if tail := clean( sub3element.tail, loadErrors, location ):
                        #             hadOutstandingSpace = haveOutstandingSpace # Remember
                        #             if tail[-1] == ' ':
                        #                 tail = tail[:-1]
                        #                 haveOutstandingSpace = True
                        #             else: haveOutstandingSpace = False
                        #             if tail: # still
                        #                 self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                        #     elif sub3element.tag == 'sc':
                        #         BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         # BibleOrgSysGlobals.checkXMLNoText( sub3element, location, 'kcf8', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         # BibleOrgSysGlobals.checkXMLNoTail( sub3element, location, 'kcf8', loadErrors )
                        #         print( "'sc' ain't done yet xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxXXXXXXXXXXXXXXXXXXXXXXX")
                        #     elif sub3element.tag == 'span':
                        #         # style BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, location, 'kcf8', loadErrors )
                        #         # BibleOrgSysGlobals.checkXMLNoText( sub3element, location, 'kcf8', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, location, 'fjg4', loadErrors )
                        #         BibleOrgSysGlobals.checkXMLNoTail( sub3element, location, 'kcf8', loadErrors )
                        #         print( "'span' ain't done yet xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxXXXXXXXXXXXXXXXXXXXXXXX")
                        #     else:
                        #         logging.error( "d3fg Unprocessed {!r} sub3element ({}) in {}".format( sub3element.tag, sub3element.text, location ) )
                        #         loadErrors.append( "Unprocessed {!r} sub3element ({}) in {}(d3fg)".format( sub3element.tag, sub3element.text, location ) )
                        #         if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        # # Why fails ??? assert not haveOutstandingSpace
                        # self.appendToLastLine( '\\f*', thisBook )
                        # if tail := clean( sub2element.tail, loadErrors, location ):
                        #     if tail[-1] == ' ':
                        #         tail = tail[:-1]
                        #         haveOutstandingSpace = True
                        #     if tail: # still
                        #         self.appendToLastLine( tail, thisBook )
                    elif sub2element.tag == 'tab':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'gdf3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, location, 'gdf3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'gdf3', loadErrors )
                        self.appendToLastLine( f"  {sub2element.tail if sub2element.tail else ''}", thisBook ) # Double em-space
                    elif sub2element.tag == 'i':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'gdf3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'gdf3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, location, 'gdf3', loadErrors )
                        assert sub2element.text
                        self.appendToLastLine( f"\\it {sub2element.text}\\it*", thisBook )
                    elif sub2element.tag == 'span':
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, location, 'gdf3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, location, 'gdf3', loadErrors )
                        self.processSpan( sub2element, thisBook, loadErrors )
                    elif sub2element.tag in ('idiom-start','idiom-end'): # should be self-closing
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'df13', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, location, 'dsfg', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'jf56', loadErrors )
                        # TODO: We don't currently save this information
                        if tail := clean( subelement.tail, loadErrors, location ):
                            hadOutstandingSpace = haveOutstandingSpace # Remember
                            if tail[-1] == ' ':
                                tail = tail[:-1]
                                haveOutstandingSpace = True
                            else: haveOutstandingSpace = False
                            if tail: # still
                                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                    else:
                        logging.error( "hsg3 Unprocessed {!r} sub2element ({}) in {}".format( sub2element.tag, sub2element.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub2element ({}) in {}(hsg3)".format( sub2element.tag, sub2element.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            else:
                logging.error( "lfg3 Unprocessed {!r} subelement ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {}(lfg3)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of processList

    def processNote( self, noteElement, thisBook, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processNote( {noteElement}, ..., {len(loadErrors)} ) for {thisBook.BBB}" )
        assert isinstance( thisBook, BibleBook )
        assert noteElement.tag == 'note'

        location = 'processNote'
        haveOutstandingSpace = False
        C = V = '?'
        self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\f + \\fr {C}:{V} \\ft {noteElement.text}", thisBook )
        for subelement in noteElement:
            if subelement.tag == 'supplied':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'm56d', loadErrors )
                text = subelement.text
                if text:
                    hadOutstandingSpace = haveOutstandingSpace # Remember
                    if text[-1] == ' ':
                        text = text[:-1]
                        haveOutstandingSpace = True
                if text: # still
                    self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                for sub2element in subelement:
                    if sub2element.tag == 'i':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'kj4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'x4vs', loadErrors )
                        assert sub2element.text
                        text = sub2element.text
                        if text:
                            hadOutstandingSpace = haveOutstandingSpace # Remember
                            if text[-1] == ' ':
                                text = text[:-1]
                                haveOutstandingSpace = True
                        if text: # still
                            self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}\\it {text}\\it*", thisBook )
                        if tail := clean( sub2element.tail, loadErrors, location ):
                            hadOutstandingSpace = haveOutstandingSpace # Remember
                            if tail[-1] == ' ':
                                tail = tail[:-1]
                                haveOutstandingSpace = True
                            else: haveOutstandingSpace = False
                            if tail: # still
                                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                    else:
                        logging.error( "nfg4 Unprocessed {!r} sub3element ({}) in {}".format( sub2element.tag, sub2element.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub3element ({}) in {}(nfg4)".format( sub2element.tag, sub2element.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        halt
                if tail := clean( subelement.tail, loadErrors, location ):
                    hadOutstandingSpace = haveOutstandingSpace # Remember
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    else: haveOutstandingSpace = False
                    if tail: # still
                        self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
            elif subelement.tag == 'cite':
                # Process the attribute(s) first
                title = None
                for attrib,value in subelement.items():
                    if attrib=='title':
                        title = value
                    else:
                        logging.warning( "h6k8 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (h6k8)".format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                logging.warning( f"Not using cite {title=}" )
                text = subelement.text
                if text:
                    hadOutstandingSpace = haveOutstandingSpace # Remember
                    if text[-1] == ' ':
                        text = text[:-1]
                        haveOutstandingSpace = True
                if text: # still
                    self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{text}", thisBook )
                for sub2element in subelement:
                    if sub2element.tag == 'i':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, location, 'kj4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'x4vs', loadErrors )
                        assert sub2element.text
                        text = sub2element.text
                        if text:
                            hadOutstandingSpace = haveOutstandingSpace # Remember
                            if text[-1] == ' ':
                                text = text[:-1]
                                haveOutstandingSpace = True
                        if text: # still
                            self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}\\it {text}\\it*", thisBook )
                        if tail := clean( sub2element.tail, loadErrors, location ):
                            hadOutstandingSpace = haveOutstandingSpace # Remember
                            if tail[-1] == ' ':
                                tail = tail[:-1]
                                haveOutstandingSpace = True
                            else: haveOutstandingSpace = False
                            if tail: # still
                                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
                    elif sub2element.tag == 'data':
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, location, 'kj4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, location, 'x4vs', loadErrors )
                        # Process the attribute(s) first
                        ref = None
                        for attrib,value in subelement.items():
                            if attrib=='ref':
                                ref = value
                            else:
                                logging.warning( "b4s6 Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                                loadErrors.append( "Unprocessed {} attribute ({}) in {} (b4s6)".format( attrib, value, location ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        assert sub2element.text
                        self.appendToLastLine( f'\\+jmp {sub2element.text}|link-href="{ref}"\\+jmp*', thisBook )
                    else:
                        logging.error( "nfg4 Unprocessed {!r} sub3element ({}) in {}".format( sub2element.tag, sub2element.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub3element ({}) in {}(nfg4)".format( sub2element.tag, sub2element.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if tail := clean( subelement.tail, loadErrors, location ):
                    hadOutstandingSpace = haveOutstandingSpace # Remember
                    if tail[-1] == ' ':
                        tail = tail[:-1]
                        haveOutstandingSpace = True
                    else: haveOutstandingSpace = False
                    if tail: # still
                        self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
            elif subelement.tag == 'i':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'b45g', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'k8j7', loadErrors )
                assert subelement.text
                self.appendToLastLine( f"\\+it {subelement.text}\\+it*{subelement.tail if subelement.tail else ''}", thisBook )
            elif subelement.tag == 'b':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'bdf3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'j45d', loadErrors )
                self.appendToLastLine( f"\\+bd {subelement.text}\\+bd*{subelement.tail if subelement.tail else ''}", thisBook )
            elif subelement.tag == 'he':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'sfs2', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'jfd5', loadErrors )
                assert subelement.text
                self.appendToLastLine( f"\\+wh {subelement.text}\\+wh*{subelement.tail if subelement.tail else ''}", thisBook )
            elif subelement.tag == 'sc':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'bdf3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'j45d', loadErrors )
                assert subelement.text
                self.appendToLastLine( f"\\+sc {subelement.text}\\+sc*{subelement.tail if subelement.tail else ''}", thisBook )
            elif subelement.tag == 'span':
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'ngrt', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'csf2', loadErrors )
                self.processSpan( subelement, thisBook, loadErrors )
            elif subelement.tag == 'tab':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'bdf3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoText( subelement, location, 'd43h', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'j45d', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'b2c9', loadErrors )
                self.appendToLastLine( '  ', thisBook ) # Double em-space
            else:
                logging.error( "fvc3 Unprocessed {!r} sub2element ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} sub2element ({}) in {}(fvc3)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        # Why fails ??? assert not haveOutstandingSpace
        self.appendToLastLine( '\\f*', thisBook )
        if tail := clean( noteElement.tail, loadErrors, location ):
            hadOutstandingSpace = haveOutstandingSpace # Remember it
            if tail[-1] == ' ':
                tail = tail[:-1]
                haveOutstandingSpace = True
            if tail: # still
                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
    # end of processNote

    def processSpan( self, spanElement, thisBook, loadErrors ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"processSpan( {spanElement}, ..., {len(loadErrors)} ) for {thisBook.BBB}" )
        assert isinstance( thisBook, BibleBook )
        assert spanElement.tag == 'span'

        location = f'processSpan {spanElement.text}'
        haveOutstandingSpace = False

        # Process the attributes first
        spanStyle = None
        for attrib,value in spanElement.items():
            if attrib=='style':
                spanStyle = value
            else:
                logging.warning( "c45g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (c45g)".format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        assert spanStyle
        spanMarker = 'it' # TODO: Could maybe adjust this according to the style ???
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"processSpan {spanElement.text=} {spanStyle=} {spanMarker=}" )
        self.appendToLastLine( f"{' ' if haveOutstandingSpace else ''}\\{spanMarker} {spanElement.text}", thisBook )
        for subelement in spanElement:
            if subelement.tag == 'note':
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, location, 'kf93', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, location, 'kf93', loadErrors )
                self.processNote( subelement, thisBook, loadErrors )
            else:
                logging.error( "kj21 Unprocessed {!r} subelement ({}) in {}".format( subelement.tag, subelement.text, location ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {}(kj21)".format( subelement.tag, subelement.text, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        self.appendToLastLine( f'\\{spanMarker}*', thisBook )
        if tail := clean( spanElement.tail, loadErrors, location ):
            hadOutstandingSpace = haveOutstandingSpace # Remember it
            if tail[-1] == ' ':
                tail = tail[:-1]
                haveOutstandingSpace = True
            if tail: # still
                self.appendToLastLine( f"{' ' if hadOutstandingSpace else ''}{tail}", thisBook )
    # end of processSpan

# end of LEBXMLBible class


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for standardTestFolder in (
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                        ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nStandard testfolder is: {}".format( standardTestFolder ) )
            result1 = LEBXMLBibleFileCheck( standardTestFolder )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA1", result1 )
            result2 = LEBXMLBibleFileCheck( standardTestFolder, autoLoad=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA2", result2 )
            result3 = LEBXMLBibleFileCheck( standardTestFolder, autoLoadBooks=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA3", result3 )


    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Test LEBXMLBible object
        testFilepaths = (
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), # Matigsalug test sample
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the LEB Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths, start=1 ): # Choose testFilepaths or justOne
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nB/ LEB {j}/ Demonstrating the LEB Bible class…" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test filepath is {testFilepath!r}" )
            oB = LEBXMLBible( testFilepath ) # Load and process the XML
            oB.load()
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, oB ) # Just print a summary

            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
                for referenceTuple in (
                                    ('OT','GEN','1','1'), ('OT','GEN','1','3'),
                                    ('OT','RUT','1','1'), ('OT','RUT','3','3'),
                                    ('OT','SA1','1','1'),
                                    ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JAM','1','6'),
                                    ('NT','JDE','1','4'), ('NT','REV','22','21'),
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1'),
                                    ):
                    (t, b, c, v) = referenceTuple
                    if t=='OT' and len(oB)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(oB)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(oB)<=66: continue # Don't bother with DC references if it's too small
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        try:
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, oB.getVerseDataList( svk ) )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "LEBXMLBible.demo:", svk, oB.getVerseText( svk ) )
                        except KeyError:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"LEBXMLBible.demo: {b} {c}:{v} can't be found!" )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineArguments.export:
                #oB.toODF(); halt
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            break
# end of LEBXMLBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for standardTestFolder in (
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ),
                        BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                        Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                        'MadeUpFolder/',
                        ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nStandard testfolder is: {standardTestFolder}" )
            result1 = LEBXMLBibleFileCheck( standardTestFolder )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA1", result1 )
            result2 = LEBXMLBibleFileCheck( standardTestFolder, autoLoad=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA2", result2 )
            result3 = LEBXMLBibleFileCheck( standardTestFolder, autoLoadBooks=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "LEB TestA3", result3 )


    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Test LEBXMLBible object
        testFilepaths = (
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), # Matigsalug test sample
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ), # Full KJV from Crosswire
            BiblesFolderpath.joinpath( 'Original languages/SBLGNT/sblgnt.osis/SBLGNT.osis.xml' ),
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', 'Ruth.xml' ), # Hebrew Ruth
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', 'Dan.xml' ), # Hebrew Daniel
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/' ), # Hebrew Bible
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', '1Sam.xml' ), # Hebrew 1 Samuel
            BiblesFolderpath.joinpath( 'Formats/LEB/Crosswire USFM-to-LEB (Perl)/Matigsalug.osis.xml' ), # Entire Bible in one file 4.4MB
            '../../MatigsalugOSIS/LEB-Output/MBTGEN.xml',
            '../../MatigsalugOSIS/LEB-Output/MBTRUT.xml', # Single books
            '../../MatigsalugOSIS/LEB-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/LEB-Output/MBTMRK.xml', '../../MatigsalugOSIS/LEB-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/LEB-Output/MBT2PE.xml', # Single book
            '../../MatigsalugOSIS/LEB-Output', # Entire folder of single books
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the LEB Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths, start=1 ): # Choose testFilepaths or justOne
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nB/ LEB {j}/ Demonstrating the LEB Bible class…" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test filepath is {testFilepath!r}" )
            oB = LEBXMLBible( testFilepath ) # Load and process the XML
            oB.load()
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, oB ) # Just print a summary

            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
                for referenceTuple in (
                                    ('OT','GEN','1','1'), ('OT','GEN','1','3'),
                                    ('OT','RUT','1','1'), ('OT','RUT','3','3'),
                                    ('OT','SA1','1','1'),
                                    ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JAM','1','6'),
                                    ('NT','JDE','1','4'), ('NT','REV','22','21'),
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1'),
                                    ):
                    (t, b, c, v) = referenceTuple
                    if t=='OT' and len(oB)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(oB)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(oB)<=66: continue # Don't bother with DC references if it's too small
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        try:
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, oB.getVerseDataList( svk ) )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "LEBXMLBible.demo:", svk, oB.getVerseText( svk ) )
                        except KeyError:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"LEBXMLBible.demo: {b} {c}:{v} can't be found!" )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineArguments.export:
                #oB.toODF(); halt
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
# end of LEBXMLBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of LEBXMLBible.py
