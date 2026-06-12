#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# OSISXMLBible.py
#
# Module handling OSIS XML Bibles
#
# Copyright (C) 2010-2023 Robert Hunt
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
Module handling the reading and import of OSIS XML Bibles.

Unfortunately, the OSIS specification (designed by committee for many different tasks)
    allows many different ways of encoding Bibles so the variations are very many.

This is a quickly updated version of an early module,
    and it's both ugly and fragile  :-(

CHANGELOG:
    2013-09 Updated to also handle Kahunapule's "modified OSIS"
    2026-05-20 Use the new, faster Rust parser
"""
import logging
import os
import sys
from pathlib import Path
from xml.etree.ElementTree import ElementTree, ParseError
import multiprocessing

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.ISO_639_3_Languages import ISO_639_3_Languages
from BibleOrgSys.Bible import Bible, BibleBook
from usfm_markers_py import USFM_BIBLE_PARAGRAPH_MARKERS
import bos_books_codes_py
from bible_organisational_system import parseOsis


LAST_MODIFIED_DATE = '2026-05-28' # by RJH
SHORT_PROGRAM_NAME = "OSISXMLBible"
PROGRAM_NAME = "OSIS XML Bible format handler"
PROGRAM_VERSION = '0.67'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA') # Must be UPPERCASE
EXTENSIONS_TO_IGNORE = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


# Get the data tables that we need for proper checking
ISOLanguages = ISO_639_3_Languages().loadData()



def OSISXMLBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for OSIS XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OSIS Bible is found,
        returns the loaded OSISXMLBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"OSISXMLBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( f"OSISXMLBibleFileCheck: Given {givenFolderName!r} folder is unreadable" )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( f"OSISXMLBibleFileCheck: Given {givenFolderName!r} path is not a folder" )
        return False

    # Find all the files and folders in this folder
    # OSIS is tricky coz a whole Bible can be in one file (normally), or in lots of separate (book) files
    #   and we don't want to think that 66 book files are 66 different OSIS Bibles
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" OSISXMLBibleFileCheck: Looking for files in given {givenFolderName}" )
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
                for osisBkCode in bos_books_codes_py.get_all_osis_book_codes():
                    # osisBkCodes are all UPPERCASE
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                    if osisBkCode in somethingUpper:
                        foundBookFiles.append( something ); break
    #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'OSIS ff', foundFiles, foundBookFiles )

    # See if there's an OSIS project here in this folder
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
            if '<osis' not in firstLines[1] and '<osis' not in firstLines[2]:
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound>1 and numFound==len(foundBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "OSISXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = OSISXMLBible( givenFolderName, lastFilenameFound ) # lastFilenameFound can be None
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    OSISXMLBibleFileCheck: Looking for files in {tryFolderName}" )
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
                        for osisBkCode in bos_books_codes_py.get_all_osis_book_codes():
                            # osisBkCodes are all UPPERCASE
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                            if osisBkCode in somethingUpper:
                                foundSubBookFiles.append( something ); break
        except PermissionError: pass # can't read folder, e.g., system folder
        #dPrint( 'Never', DEBUGGING_THIS_MODULE, 'OSIS fsf', foundSubfiles, foundSubBookFiles )

        # See if there's an OSIS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OSISb (unexpected) first line was {firstLines} in {thisFilename}" )
                    continue
                if '<osis' not in firstLines[1]:
                    continue
            foundProjects.append( (tryFolderName, thisFilename) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound>1 and numFound==len(foundSubBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "OSISXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = OSISXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
# end of OSISXMLBibleFileCheck



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
        errorMsg = f"clean: found multiple spaces in {info!r}{result}"
        if DEBUGGING_THIS_MODULE: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
    if '\t' in result:
        errorMsg = f"clean: found tab in {info!r}{result}"
        if DEBUGGING_THIS_MODULE: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\t', ' ' )
    if '\n' in result or '\r' in result:
        errorMsg = f"clean: found CR or LF characters in {info!r}{result}"
        if DEBUGGING_THIS_MODULE: logging.error( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
    while '  ' in result: result = result.replace( '  ', ' ' )
    return result
# end of clean



class OSISXMLBible( Bible ):
    """
    Class for reading, validating, and converting OSISXMLBible XML.
    """
    filenameBase = 'OSISXMLBible'
    # It does not matter if the NameSpace declarations are no longer valid online links
    XMLNameSpace = '{http://www.w3.org/XML/1998/namespace}'
    #OSISNameSpace = '{http://ebible.org/2003/OSIS/namespace}'
    OSISNameSpace = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
    treeTag = OSISNameSpace + 'osis'
    textTag = OSISNameSpace + 'osisText'
    headerTag = OSISNameSpace + 'header'
    divTag = OSISNameSpace + 'div'


    def __init__( self, sourceFilepath, givenName=None, givenAbbreviation=None, encoding='utf-8' ) -> None:
        """
        Constructor: just sets up the OSIS Bible object.

        sourceFilepath can be a folder (esp. if each book is in a separate file)
            or the path of a specific file (probably containing the whole Bible -- most common)
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"OSISXMLBible.__init__( {sourceFilepath}, '{givenName}', '{givenAbbreviation}', {encoding} )" )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'OSIS XML Bible object'
        self.objectTypeString = 'OSIS'

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
            # There's no standard for OSIS xml file naming
            fileList = os.listdir( self.sourceFilepath )
            # First try looking for OSIS book names
            BBBList = []
            for filename in fileList:
                if 'VerseMap' in filename: continue # For WLC
                if filename.lower().endswith('.xml'):
                    self.sourceFilepath = os.path.join( self.sourceFolder, filename )
                    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Trying {self.sourceFilepath}…" )
                    if os.access( self.sourceFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
                        foundBBB = None
                        upperFilename = filename.upper()
                        for osisBkCode in bos_books_codes_py.get_all_osis_book_codes():
                            # osisBkCodes are all UPPERCASE
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'obc', osisBkCode, upperFilename )
                            if osisBkCode in upperFilename:
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"OSISXMLBible.__init__ found {osisBkCode!r} in {upperFilename!r}" )
                                if 'JONAH' in upperFilename and osisBkCode=='NAH': continue # Handle bad choice
                                if 'ZEPH' in upperFilename and osisBkCode=='EPH': continue # Handle bad choice
                                assert not foundBBB # Don't expect duplicates
                                BBB = bos_books_codes_py.osis_book_code_to_bos_book_code( osisBkCode, strict=True )
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  FoundBBB1 = {foundBBB!r}" )
                        if not foundBBB: # Could try a USFM/Paratext book code -- what writer creates these???
                            for bkCode in bos_books_codes_py.get_all_usfm_abbreviations( to_upper=True ):
                                # returned bkCodes are all UPPERCASE
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'bc', bkCode, upperFilename )
                                if bkCode in upperFilename:
                                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'OSISXMLBible.__init__ ' + f"found {bkCode!r} in {upperFilename!r}" )
                                    if foundBBB: # already -- don't expect doubles
                                        logging.warning( 'OSISXMLBible.__init__: ' + f"Found a second possible book abbreviation for {foundBBB} in {filename}" )
                                    foundBBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code( bkCode, strict=False )
                                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  FoundBBB2 = {foundBBB!r}" )
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
            for BBB in bos_books_codes_py.get_all_bos_book_codes(): # ordered by reference number
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
                if BBB in BBBList:
                    ix = BBBList.index( BBB )
                    newCorrectlyOrderedList.append( self.possibleFilenames[ix] )
            self.possibleFilenames = newCorrectlyOrderedList
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Now", self.possibleFilenames ); assert False, "We want to stop here"
        else: # it's presumably a file name
            self.sourceFolder = os.path.dirname( self.sourceFilepath )
            if not os.access( self.sourceFilepath, os.R_OK ):
                logging.critical( 'OSISXMLBible: ' + f"File {self.sourceFilepath!r} is unreadable" )
                return # No use continuing
            vPrint( 'Never', DEBUGGING_THIS_MODULE, f"OSISXMLBible possibleFilenames: {self.possibleFilenames}" )

        self.name, self.abbreviation = self.givenName, self.givenAbbreviation
        self.workNames, self.workPrefixes = [], {}
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['OSIS'] = {}
    # end of OSISXMLBible.__init__


    def loadBooks( self ):
        """
        Loads the OSIS XML file or files.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "OSISXMLBible.loadBooks()" )

        loadErrors:list[str] = []
        if self.possibleFilenames and len(self.possibleFilenames) > 1: # then we possibly have multiple files, probably one for each book
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                # Load all the books as quickly as possible
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(self.possibleFilenames)} OSIS books using {BibleOrgSysGlobals.maxProcesses} processes…" )
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookFileMP, self.possibleFilenames ) # have the pool do our loads
                    assert len(results) == len(self.possibleFilenames)
                    for bBook,bookLoadErrors in results:
                        self.stashBook( bBook ) # Saves them in the correct order
                        loadErrors += bookLoadErrors
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                for filename in self.possibleFilenames:
                    pathname = os.path.join( self.sourceFolder, filename )
                    loadedBooks = self.__loadFile( pathname )
                    for loadedBook,bookLoadErrors in loadedBooks:
                        self.stashBook( loadedBook )
                        loadErrors += bookLoadErrors
        elif os.path.isfile( self.sourceFilepath ): # most often we have all the Bible books in one file
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Using optimized Rust OSIS parser for {self.sourceFilepath}…" )
            try:
                results = parseOsis( self.sourceFilepath )
                for bbb, raw_lines in results['books'].items():
                    bBook = BibleBook( self, bbb )
                    bBook.objectNameString = 'OSIS XML Bible Book object'
                    bBook.objectTypeString = 'OSIS'
                    bBook._rawLines = raw_lines
                    self.stashBook( bBook )
                if 'metadata' in results:
                    self.suppliedMetadata['OSIS'].update( results['metadata'] )
            except Exception as err:
                logging.warning( f"Rust OSIS parser failed: {err}. Falling back to Python parser." )
                loadedBooks = self.__loadFile( self.sourceFilepath )
                for loadedBook,bookLoadErrors in loadedBooks:
                    self.stashBook( loadedBook )
                    loadErrors += bookLoadErrors
        else:
            logging.critical( f"OSISXMLBible: Didn't find anything to load at {self.sourceFilepath}" )
            loadErrors.append( f"OSISXMLBible: Didn't find anything to load at {self.sourceFilepath}" )
        if loadErrors:
            self.checkResultsDictionary['Load Errors'] = loadErrors
            #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "loadErrors", len(loadErrors), loadErrors ); assert False, "We want to stop here"
        self.applySuppliedMetadata( 'OSIS' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of OSISXMLBible.loadBooks()

    def load( self ):
        self.loadBooks()


    def loadBook( self, BBB:str, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        #NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2 or DEBUGGING_THIS_MODULE:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"OSISXMLBible.loadBook( {BBB}, {filename} )" )
            #assert self.preloadDone

        if not self.possibleFilenames: # then the whole Bible was probably in one file
            vPrint( 'Info', DEBUGGING_THIS_MODULE, "  Unable to load OSIS by individual book (only whole Bible?) -- returning" )
            return # nothing to do here

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {BBB} is already loaded -- returning" )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( f"We had already tried loading OSIS {BBB} for {self.name}" )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  OSISXMLBible: Loading {BBB} from {self.name} from {self.sourceFolder}…" )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( f"OSISXMLBible.loadBook: Unable to find file for {BBB}" )
        #BB = BibleBook( self, BBB )
        #BB.load( filename, self.sourceFolder, self.encoding )
        #if BB._rawLines:
            #BB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            #self.stashBook( BB )
        #else: logging.info( f"OSIS book {BBB} was completely blank" )
        loadErrors:list[str] = []
        pathname = os.path.join( self.sourceFolder, filename )
        loadedBooks = self.__loadFile( pathname )
        assert len(loadedBooks) == 1
        for loadedBook,loadErrors in loadedBooks:
            self.stashBook( loadedBook )
            loadErrors += loadErrors
        self.bookNeedsReloading[BBB] = False
        if loadErrors:
            if 'Load Errors' not in self.checkResultsDictionary: self.checkResultsDictionary['Load Errors'] = []
            self.checkResultsDictionary['Load Errors'].extend( loadErrors )
            #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "loadErrors", len(loadErrors), loadErrors ); assert False, "We want to stop here"
        self.applySuppliedMetadata( 'OSIS' ) # Copy some to self.settingsDict
        #self.doPostLoadProcessing() # Should only be done after loading ALL books
    # end of OSISXMLBible.loadBook function


    def _loadBookFileMP( self, XMLBookFilename ) -> BibleBook:
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.

        Returns the book info.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"_loadBookFileMP( {XMLBookFilename} )" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  LoadingMP {self.name} book from {XMLBookFilename} from {self.sourceFolder}…" )

        pathname = os.path.join( self.sourceFolder, XMLBookFilename )
        result = self.__loadFile( pathname )
        assert len(result) == 1 # only one book
        assert len(result[0]) == 2 # book and errors
        return result[0]
    # end of OSISXMLBible._loadBookFileMP function


    def __loadFile( self, OSISFilepath ) -> list[BibleBook]:
        """
        Load a single source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  OSISXMLBible loading {OSISFilepath}…" )

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Resetting bookList and loadErrors")
        bookList:list[tuple[BibleBook,list[str]]] = []
        loadErrors:list[str] = []

        try: self.XMLTree = ElementTree().parse( OSISFilepath )
        except ParseError as err:
            logging.critical( f"Loader parse error in xml file {OSISFilepath}: {sys.exc_info()[0]} {err}" )
            loadErrors.append( f"Loader parse error in xml file {OSISFilepath}: {sys.exc_info()[0]} {err}" )
            return
        if BibleOrgSysGlobals.debugFlag: assert self.XMLTree # Fail here if we didn't load anything at all

        # Find the main (osis) container
        if self.XMLTree.tag == OSISXMLBible.treeTag:
            location = 'OSIS file'
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8', loadErrors )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.XMLTree.items():
                if attrib.endswith("schemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( f"fv6g Unprocessed {attrib} attribute ({value}) in {location}" )
                    loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {location} (fv6g)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

            # Find the submain (osisText) container
            if len(self.XMLTree)==1 and (self.XMLTree[0].tag == OSISXMLBible.textTag or (not BibleOrgSysGlobals.strictCheckingFlag and self.XMLTree[0].tag == 'osisText')):
                sublocation = "osisText in " + location
                textElement = self.XMLTree[0]
                BibleOrgSysGlobals.checkXMLNoText( textElement, sublocation, '3b5g', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( textElement, sublocation, '7h9k', loadErrors )
                # Process the attributes first
                self.osisIDWork = self.osisRefWork = canonical = None
                for attrib,value in textElement.items():
                    if attrib=='osisIDWork':
                        self.osisIDWork = value
                        if not self.name: self.name = value
                    elif attrib=='osisRefWork': self.osisRefWork = value
                    elif attrib=='canonical':
                        canonical = value
                        assert canonical in ('true','false')
                    elif attrib==OSISXMLBible.XMLNameSpace+'lang': self.lang = value
                    else:
                        logging.warning( f"gb2d Unprocessed {attrib} attribute ({value}) in {sublocation}" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {sublocation} (gb2d)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if self.osisRefWork:
                    if self.osisRefWork not in ('bible','Bible','defaultReferenceScheme'):
                        logging.warning( f"New variety of osisRefWork: {self.osisRefWork!r}" )
                        loadErrors.append( f"New variety of osisRefWork: {self.osisRefWork!r}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if self.lang:
                    if self.lang in ('en','de','he'): # Only specifically recognise these ones so far (English, German, Hebrew)
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Language is {self.lang!r}" )
                    else:
                        logging.info( f"Discovered unknown {self.lang!r} language" )
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  osisIDWork is {self.osisIDWork!r}" )

                # Find (and move) the header container
                if textElement[0].tag == OSISXMLBible.headerTag:
                    self.header = textElement[0]
                    textElement.remove( self.header )
                    self.validateHeader( self.header, loadErrors )
                else:
                    logging.warning( f"Missing header element (looking for {OSISXMLBible.headerTag!r} tag)" )
                    loadErrors.append( f"Missing header element (looking for {OSISXMLBible.headerTag!r} tag)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

                # Find (and move) the optional front matter (div) container
                if textElement[0].tag == OSISXMLBible.divTag or (not BibleOrgSysGlobals.strictCheckingFlag and textElement[0].tag == 'div'):
                    sub2location = "div of " + sublocation
                    # Process the attributes first
                    div0Type = div0OsisID = canonical = None
                    for attrib,value in textElement[0].items():
                        if attrib=='type': div0Type = value
                        elif attrib=='osisID': div0OsisID = value
                        elif attrib=='canonical':
                            assert canonical is None
                            canonical = value
                            assert canonical in ('true','false')
                        else:
                            logging.warning( f"7j4d Unprocessed {attrib} attribute ({value}) in {sub2location}" )
                            loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {sub2location} (7j4d)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if div0Type == 'front':
                        self.frontMatter = textElement[0]
                        textElement.remove( self.frontMatter )
                        self.validateFrontMatter( bookList, self.frontMatter, loadErrors )
                    else: logging.info( "No front matter division" )

                self.divs, self.divTypesString = [], None
                for element in textElement:
                    if element.tag == OSISXMLBible.divTag or (not BibleOrgSysGlobals.strictCheckingFlag and element.tag == 'div'):
                        sub2location = "div in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoText( element, sub2location, '3a2s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( element, sub2location, '4k8a', loadErrors )
                        divType = element.get( 'type' )
                        if divType is None:
                            logging.error( "Missing div type in OSIS file" )
                            loadErrors.append( "Missing div type in OSIS file" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if divType != self.divTypesString:
                            if not self.divTypesString: self.divTypesString = divType
                            else: self.divTypesString = 'MixedTypes'
                        self.validateAndExtractMainDiv( bookList, element, loadErrors )
                        self.divs.append( element )
                    else:
                        logging.error( f"Expected to find {OSISXMLBible.divTag!r} but got {element.tag!r}" )
                        loadErrors.append( f"Expected to find {OSISXMLBible.divTag!r} but got {element.tag!r}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            else:
                logging.error( f"Expected to find {OSISXMLBible.textTag!r} but got {self.XMLTree[0].tag!r}" )
                loadErrors.append( f"Expected to find {OSISXMLBible.textTag!r} but got {self.XMLTree[0].tag!r}" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        else:
            logging.error( f"Expected to load {OSISXMLBible.treeTag!r} but got {self.XMLTree.tag!r}" )
            loadErrors.append( f"Expected to load {OSISXMLBible.treeTag!r} but got {self.XMLTree.tag!r}" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip():
            logging.error( f"Unexpected {self.XMLTree.tag!r} tail data after {self.XMLTree.tail} element" )
            loadErrors.append( f"Unexpected {self.XMLTree.tag!r} tail data after {self.XMLTree.tail} element" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        if len( bookList ) == 1:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    _loadFile({OSISFilepath}) is returning {bookList[0][0].BBB} with {len(bookList[0][1])} loadErrors" )
        else: # More than one book in this OSIS file
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    _loadFile({OSISFilepath}) is returning {len(bookList)} books" )
        return bookList
    # end of OSISXMLBible._loadFile function


    def validateDivineName( self, thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        """
        assert isinstance( thisBook, BibleBook )

        location = "validateDivineName: " + locationDescription
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '3f7h', loadErrors )
        thisBook.appendToLastLine( f'\\nd {clean(element.text)}' )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                sublocation = "w of " + location
                self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"v4g7 Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location} (v4g7)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        thisBook.appendToLastLine( '\\nd*' )
        if element.tail and element.tail.strip(): thisBook.appendToLastLine( clean(element.tail) )
    # end of validateDivineName


    def validateAndLoadSEG( self, thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
        Nesting doesn't currently work here.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateAndLoadSEG( {BibleOrgSysGlobals.elementStr(element)}, {locationDescription}, {verseMilestone} )" )
        assert isinstance( thisBook, BibleBook )
        location = 'validateAndLoadSEG: ' + locationDescription
        SegText = element.text

        # Process the attributes
        theType = None
        for attrib,value in element.items():
            if attrib=='type': theType = value
            else:
                logging.warning( f"lj06 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} -element of {element.tag} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} -element of {element.tag} at {location} (lj06)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        #dPrint( 'Never', DEBUGGING_THIS_MODULE, "khf8", "Have", location, repr(element.text), repr(theType) )
        markerOpen = False
        if theType:
            if theType=='verseNumber': marker = 'fv'
            elif theType=='keyword': marker = 'fk'
            elif theType=='otPassage': marker = 'qt'
            elif theType in ('section',
                             'x-small','x-large','x-suspended',
                             'x-maqqef','x-sof-pasuq','x-pe','x-paseq','x-samekh','x-reversednun'):
                marker = theType # invented -- used below
            else:
                marker = 'x--' # Gets ignored below
                dPrint( 'Quiet', DEBUGGING_THIS_MODULE, theType, location, verseMilestone ); assert False, "We want to stop here"
        else: # What marker do we need ???
            marker = 'fv'
        if marker == 'section': # We don't have marker for this
            thisBook.appendToLastLine( ' ' + clean(SegText) + ' ' )
        elif marker.startswith( 'x-' ): # We don't have marker for this
            thisBook.appendToLastLine( clean(SegText) )
        else:
            thisBook.appendToLastLine( f'\\{marker} {clean(SegText)}' )
            markerOpen = True
        for subelement in element:
            sublocation = element.tag + ' in ' + location
            if subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"8k1w Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation} (8k3s)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if markerOpen: thisBook.appendToLastLine( f'\\{marker}*' )
        segTail = clean( element.tail, loadErrors, location, verseMilestone )
        if segTail: thisBook.appendToLastLine( segTail )
    # end of validateAndLoadSEG


    def validateAndLoadWord( self, thisBook, element, location, verseMilestone, loadErrors ):
        """
        Handle a 'w' element and submit a string (which may include embedded Strongs' numbers, etc.).

        Nothing is returned.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.sourceFilepath)
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateAndLoadWord( {thisBook}, {element}, {location}, … )" )
        assert isinstance( thisBook, BibleBook )

        sublocation = "validateAndLoadWord: w of " + location
        word = clean( element.text, loadErrors, sublocation, verseMilestone )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' w', word )
        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
            #assert word -- might be false, e.g., in <w lemma="strong:H03069"><divineName>God</divineName></w>
        thisBook.appendToLastLine( '\\w ' + (word if word else '' ) )

        # Process the sub-elements (formatted parts of the word) first
        #assert len(element) <= 1
        if len(element) > 1:
            logging.warning( f"Unusual for word '{word}' to have multiple ({len(element)}) sub-elements in {sublocation} at {verseMilestone} (bd52)" )
        for subelement in element:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '  st', subelement.tag )
            if subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"8k3s Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation} (8k3s)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        # Process the attributes
        ID = lemma = morph = wType = src = gloss = n = None
        for attrib,value in element.items():
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{word} {attrib}={value} @ {location}" )
            if attrib=='id': ID = value
            elif attrib=='lemma':
                lemma = self.workPrefixes['w/@lemma']+':'+value if 'w/@lemma' in self.workPrefixes else value
            elif attrib=='morph':
                morph = self.workPrefixes['w/@morph']+':'+value if 'w/@morph' in self.workPrefixes else value
            elif attrib=='type': wType = value
            elif attrib=='src': src = value
            elif attrib=='gloss': gloss = value
            elif attrib=='n': n = value # Might be something like 1.1.1 (in morphhb/wlc)
            else:
                logging.warning( f"2h6k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (2h6k)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if wType and (BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE):
            assert wType.startswith( 'x-split-' ) or wType=='x-ketiv', f"{wType=}" # Followed by a number 1-10 or more

        attributeDict = {}
        if lemma \
        and ( lemma.startswith('strong:') or lemma.startswith('Strong:') ):
            if len(lemma)>7:
                lemma = lemma[7:]
                if lemma:
                    #thisBook.appendToLastLine( f'\\str {lemma}\\str*' )
                    attributeDict['strong'] = lemma
                    lemma = None # we've used it
        elif gloss and gloss.startswith('s:'):
            if len(gloss)>2:
                gloss = gloss[2:]
                if gloss:
                    thisBook.appendToLastLine( f'\\str {gloss}\\str*' )
                    attributeDict['strong'] = gloss
                    gloss = None # we've used it
        if lemma: attributeDict['lemma'] = lemma
        if morph: attributeDict['x-morph'] = morph
        if wType: attributeDict['x-wType'] = wType
        if src: attributeDict['x-src'] = src
        if gloss: attributeDict['x-gloss'] = gloss
        if n: attributeDict['x-cantillationLevel'] = n
        #if lemma or morph or wType or src or gloss:
            #logging.warning( f"Losing lemma or morph or wType or src or gloss here at {verseMilestone} from {BibleOrgSysGlobals.elementStr(element)}" )
            #loadErrors.append( f"Losing lemma or morph or wType or src or gloss here at {verseMilestone}" )
            #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if attributeDict:
            attributeString = '|'
            for attributeName,attributeValue in attributeDict.items():
                if len(attributeString) > 1: attributeString += ' '
                attributeString += f'{attributeName}="{attributeValue}"'
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "attributeString", attributeString )
            thisBook.appendToLastLine( attributeString )
        thisBook.appendToLastLine( '\\w*')

        trailingPunctuation = clean( element.tail, loadErrors, sublocation, verseMilestone )
        if trailingPunctuation: thisBook.appendToLastLine( trailingPunctuation )
        #combinedWord = word + trailingPunctuation
        #return combinedWord
    # end of validateAndLoadWord


    def validateHighlight( self, thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
        Nesting doesn't currently work here.
        """
        assert isinstance( thisBook, BibleBook )
        location = "validateHighlight: " + locationDescription
        #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'gb5g', loadErrors )
        highlightedText, highlightedTail = element.text, element.tail
        #if not highlightedText: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "validateHighlight", repr(highlightedText), repr(highlightedTail), repr(location), repr(verseMilestone) )
        #if BibleOrgSysGlobals.debugFlag: assert highlightedText # No text if nested!
        highlightType = None
        for attrib,value in element.items():
            if attrib=='type':
                highlightType = value
            else:
                logging.warning( f"7kj3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location} (7kj3)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if highlightType == 'italic': marker = 'it'
        elif highlightType == 'bold': marker = 'bd'
        elif highlightType == 'emphasis': marker = 'em'
        elif highlightType == 'small-caps': marker = 'sc'
        elif highlightType == 'super': marker = 'ord'
        elif highlightType == 'normal': marker = 'no'
        elif BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'validateHighlight: highlightX', highlightType, locationDescription, verseMilestone )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
        thisBook.appendToLastLine( f'\\{marker} {clean(highlightedText)}\\{marker}*' )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "hi of " + locationDescription
                self.validateHighlight( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # recursive call
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "note of " + locationDescription
                self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"bdhj Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (bdhj)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if highlightedTail and highlightedTail.strip(): thisBook.appendToLastLine( clean(highlightedTail) )
    # end of validateHighlight


    def validateRDG( self, thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän

        Doesn't currently add any pseudo-USFM markers for the reading XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        Nesting doesn't currently work here.
        """
        assert isinstance( thisBook, BibleBook )
        location = 'validateRDG: ' + locationDescription
        BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c54b', loadErrors )

        # Process the attributes first
        readingType = None
        for attrib,value in element.items():
            if attrib=='type':
                readingType = value
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'readingType', readingType )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                    assert readingType in ('x-qere','x-accent')
            else:
                logging.warning( f"2s3d Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {element.tag} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {element.tag} at {location} (2s3d)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        if element.text: thisBook.appendToLastLine( element.text )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w': # cross-references ???
                sublocation = "validateRDG: w of rdg of " + locationDescription
                self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Have", sublocation, "6n83" )
                #rdgW = subelement.text
                #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 's2vb', loadErrors )
                #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '5b3f', loadErrors )
                ## Process the attributes
                #lemma = morph = n = None
                #for attrib,value in subelement.items():
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Attribute RDG1 {attrib}={value!r}" )
                    #if attrib=='lemma': lemma = value # e.g., 'l/5649'
                    #elif attrib=='morph': morph = value # e.g., 'HC/Ncfdc'
                    #elif attrib=='n': n = value # e.g., '0.0'
                    #else:
                        #logging.warning( f"6b8m Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {subelement.tag} at {sublocation}" )
                        #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {subelement.tag} at {sublocation} (6b8m)" )
                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                #thisBook.appendToLastLine( rdgW )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references ???
                sublocation = "validateRDG: seg of rdg of " + locationDescription
                self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateRDG: hi of rdg of " + locationDescription
                self.validateHighlight( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"3dxm Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location} (3dxm)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if element.tail and element.tail.strip(): thisBook.appendToLastLine( clean(element.tail) )
    # end of validateRDG


    def validateProperName( thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        """
        location = "validateProperName: " + locationDescription
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'hsd8', loadErrors )
        BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks91', loadErrors )
        divineName = element.text
        thisBook.appendToLastLine( f'\\pn {clean(divineName)}\\pn*' )
        if element.tail and element.tail.strip(): thisBook.appendToLastLine( clean(element.tail) )
    # end of validateProperName


    def validateCrossReferenceOrFootnote( self, thisBook, element, locationDescription, verseMilestone, loadErrors ):
        """
        Check/validate and process a cross-reference or footnote.
        """
        assert isinstance( thisBook, BibleBook )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "validateCrossReferenceOrFootnote at", locationDescription, verseMilestone )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"element tag={element.tag!r} text={element.text!r} tail={element.tail!r} attr={element.items()} ch={element}" )
        location = "validateCrossReferenceOrFootnote: " + locationDescription

        noteType = noteN = noteOsisRef = noteOsisID = notePlacement = noteResp = None
        for attrib,value in element.items():
            if attrib=='type': noteType = value # cross-reference or empty for a footnote
            elif attrib=='n': noteN = value
            elif attrib=='osisRef': noteOsisRef = value
            elif attrib=='osisID': noteOsisID = value
            elif attrib=='placement': notePlacement = value
            elif attrib=='resp': noteResp = value
            else:
                logging.warning( f"2s4d Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {element.tag} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {element.tag} at {location} (2s4d)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, notePlacement )
        if notePlacement and BibleOrgSysGlobals.debugFlag: assert notePlacement in ('foot','inline')
        vPrint( 'Never', DEBUGGING_THIS_MODULE, f"  Note attributes: noteType={noteN!r} noteN={noteOsisRef!r} noteOsisRef={noteOsisID!r} noteOsisID={verseMilestone!r} at {noteType}" )

        guessed = False
        openFieldname = None
        if not noteType: # easier to handle later if we decide what it is now
            if not element.items(): # it's just a note with NO ATTRIBUTES at all
                noteType = 'footnote'
            else: # we have some attributes
                noteType = 'footnote' if noteN else 'crossReference'
            guessed = True
        #assert noteType and noteN
        if noteType == 'crossReference':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
            if BibleOrgSysGlobals.debugFlag:
                if notePlacement: assert notePlacement == 'inline'
            if not noteN: noteN = '-'
            thisBook.appendToLastLine( f'\\x {noteN}' )
            openFieldname = 'x'
        elif noteType == 'footnote':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
        elif noteType == 'study':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); assert False, "We want to stop here"
        elif noteType == 'translation':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
            if BibleOrgSysGlobals.debugFlag:
                if notePlacement: assert notePlacement == 'foot'
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); assert False, "We want to stop here"
        elif noteType == 'variant':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
        elif noteType == 'alternative':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
        elif noteType == 'exegesis':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            thisBook.appendToLastLine( f'\\f {noteN} ' )
            openFieldname = 'f'
        elif noteType == 'x-index':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert notePlacement in ('inline',)
            if not noteN: noteN = '~'
            thisBook.appendToLastLine( f'\\f {noteN} ' ) # Not sure what this is ???
            openFieldname = 'f'
        elif noteType == 'x-strongsMarkup':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  noteType =", noteType, "noteN =", noteN, repr(notePlacement) )
            if BibleOrgSysGlobals.debugFlag: assert notePlacement is None
            if not noteN: noteN = '+ '
            thisBook.appendToLastLine( f'\\str {noteN} ' )
            openFieldname = 'str'
        else:
            vPrint( 'Never', DEBUGGING_THIS_MODULE, "validateCrossReferenceOrFootnote note1", repr(noteType) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
        noteText = clean( element.text, loadErrors, location, verseMilestone )
        #if not noteText or noteText.isspace(): # Maybe we can infer the anchor reference
        #    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
        #        noteText = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
        #    else: noteText = ''
        if noteText and not noteText.isspace(): # In some OSIS files, this is the anchor reference (in others, that's put in the tail of an enclosed reference subelement)
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vm", verseMilestone, repr(noteText) ); assert False, "We want to stop here"
            #if verseMilestone.startswith( 'Matt.6'): assert False, "We want to stop here"
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  noteType = {noteType}, noteText = {noteText!r}" )
            if noteType == 'crossReference': # This could be something like '1:6:' or '1:8: a'
                thisBook.appendToLastLine( f'\\xt {clean(noteText)}' )
            elif noteType == 'footnote': # This could be something like '4:3 In Greek: some note.' or it could just be random text
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {noteType=}, {noteText=!r}" )
                if BibleOrgSysGlobals.debugFlag: assert noteText
                if ':' in noteText and noteText[0].isdigit(): # Let's roughly assume that it starts with a chapter:verse reference
                    bits = noteText.split( None, 1 )
                    if BibleOrgSysGlobals.debugFlag: assert len(bits) == 2
                    try: sourceText, footnoteText = bits
                    except ValueError: sourceText, footnoteText = noteText, ''
                    if BibleOrgSysGlobals.debugFlag: assert sourceText and footnoteText
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  footnoteSource = {footnoteSource!r}, sourceText = {sourceText!r}" )
                    if not sourceText[-1] == ' ': sourceText += ' '
                    thisBook.appendToLastLine( f'\\fr {sourceText}' )
                    thisBook.appendToLastLine( f'\\ft {footnoteText}'  )
                else: # Let's assume it's a simple note
                    thisBook.appendToLastLine( f'\\ft {noteText}' )
            elif noteType == 'exegesis':
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Need to handle exegesis note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                thisBook.appendToLastLine( f'\\ft {clean(noteText)}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "exegesis note fl35", location, "Type =", noteType, "N =", repr(noteN), "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'study':
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Need to handle study note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                thisBook.appendToLastLine( f'\\ft {clean(noteText)}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "study note dg32", location, "Type =", noteType, "N =", repr(noteN), "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'translation':
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Need to handle translation note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                thisBook.appendToLastLine( f'\\ft {clean(noteText)}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "translation note fgd1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'x-index':
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Need to handle index note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                #thisBook.addLine( 'ix~', noteText )
                thisBook.appendToLastLine( f'\\ft {clean(noteText)}' )
            elif noteType == 'x-strongsMarkup':
                thisBook.appendToLastLine( f'\\ft {noteText}' )
            else:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "note2", noteType )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                sublocation = "validateCrossReferenceOrFootnote: reference of " + locationDescription
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Have", sublocation, "7h3f" )
                referenceText = (subelement.text if subelement.text is not None else '').strip()
                referenceTail = (subelement.tail if subelement.tail is not None else '').strip()
                referenceOsisRef = referenceType = None
                for attrib,value in subelement.items():
                    if attrib=='osisRef': referenceOsisRef = value
                    elif attrib=='type': referenceType = value
                    else:
                        logging.warning( f"1sc5 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (1sc5)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  reference attributes: noteType={!r}, referenceText={!r}, referenceOsisRef={!r}, referenceType={!r}, referenceTail={!r}". \
                                        format( noteType, referenceText, referenceOsisRef, referenceType, referenceTail ) )
                if referenceText and not referenceType: # Maybe we can infer the anchor reference
                    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'vm', verseMilestone )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'ror', referenceOsisRef )
                        anchor = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
                        #referenceType = 'source' # so it works below for cross-references
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'rt', referenceText )
                        if noteType=='crossReference':
                            #assert not noteText and not referenceTail
                            if noteText and not noteText.isspace():
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'nt', repr(noteText) )
                                # The following code doesn't work great for bridged verses,
                                #   e.g., <verse sID="Rom.9.11" osisID="Rom.9.11 Rom.9.12"/> (bridge isn't in verseMilestone)
                                if anchor in noteText or anchor.replace('.',':') in noteText \
                                or ( noteText[0].isdigit() and (':' in noteText or '.' in noteText) and '-' in noteText ):
                                    anchor = noteText
                                else:
                                    logging.error( f"What do we do here with the {verseMilestone!r} note at {noteText}" )
                                    loadErrors.append( f"What do we do here with the {verseMilestone!r} note at {noteText}" )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning:
                                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"What do we do here with the {verseMilestone!r} note at {noteText}" )
                                        assert False, "We want to stop here"
                            thisBook.appendToLastLine( f'\\xo {anchor}' )
                            continue
                        elif noteType=='footnote':
                            thisBook.addLine( 'v~', anchor ) # There's no USFM for this
                        else:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'CATERPILLAR', sublocation, verseMilestone, noteType, referenceType, referenceText )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                if noteType=='crossReference' and referenceType=='source':
                    #assert not noteText and not referenceTail
                    if BibleOrgSysGlobals.debugFlag: assert not noteText or noteText.isspace()
                    thisBook.appendToLastLine( f'\\xt {referenceText}' )
                elif noteType=='crossReference' and not referenceType and referenceOsisRef is not None:
                    if 0 and USFMResults and USFMResults[-1][0]=='xt': # Combine multiple cross-references into one xt field
                        thisBook.appendToLastLine( f'\\xt {USFMResults.pop()[1]+referenceText}' )
                    else:
                        thisBook.appendToLastLine( f'\\xt {clean(referenceText)}' )
                elif noteType=='footnote' and referenceType=='source':
                    if BibleOrgSysGlobals.debugFlag: assert referenceText and not noteText
                    if not referenceText[-1] == ' ': referenceText += ' '
                    thisBook.appendToLastLine( f'\\fr {clean(referenceText)}' )
                elif noteType=='study' and referenceType=='source': # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"rT={referenceText!r} nT={noteText!r} rTail={referenceTail!r}" )
                    if BibleOrgSysGlobals.debugFlag: assert referenceText and not noteText.strip()
                    if not referenceText[-1] == ' ': referenceText += ' '
                    #else: logging.warning( f"How come there's no tail? rT={referenceText!r} nT={noteText!r} rTail={referenceTail!r}" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "study note3", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); assert False, "We want to stop here"
                elif noteType=='translation' and referenceType=='source': # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{self.abbreviation}: rT={referenceText!r} nT={noteText!r} rTail={referenceTail!r}" )
                        assert referenceText and not noteText
                    if not referenceText[-1] == ' ': referenceText += ' '
                    thisBook.appendToLastLine( f'\\fr {referenceText}' )
                elif noteType=='translation' and referenceType is None: # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{self.abbreviation}: rT={referenceText!r} nT={noteText!r} rTail={referenceTail!r}" )
                        #assert referenceText
                    if noteText:
                        thisBook.appendToLastLine( f'\\fr {referenceText} \\ft {noteText}' )
                    else:
                        if referenceText and referenceText[-1]!=' ': referenceText += ' '
                        thisBook.appendToLastLine( f'\\fr {referenceText}' )
                else:
                    logging.critical( f"Don't know how to handle notetype={noteType!r} and referenceType={referenceType!r} yet" )
                    loadErrors.append( f"Don't know how to handle notetype={noteType!r} and referenceType={referenceType!r} yet" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                for sub2element in subelement: # Can have nested references in some OSIS files
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                        sub2location = "validateCrossReferenceOrFootnote: reference of reference of " + locationDescription
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Have", sub2location, "w3r5" )
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                        subreferenceText = sub2element.text
                        if BibleOrgSysGlobals.debugFlag: assert noteType == 'crossReference'
                        thisBook.appendToLastLine( f'\\xo {subreferenceText}' )
                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'foreign':
                        sub2location = "validateCrossReferenceOrFootnote: foreign of reference of " + locationDescription
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                        subreferenceText = sub2element.text
                        thisBook.appendToLastLine( f'\\tl {clean(subreferenceText)}\\tl*' )
                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'seg':
                        sub2location = "validateCrossReferenceOrFootnote: seg of reference of " + locationDescription
                        self.validateAndLoadSEG( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                    else:
                        logging.error( f"7h45 Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (7h45)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.abbreviation, sub2element.tag ); assert False, "We want to stop here"
                if referenceTail and referenceTail.strip():
                    thisBook.appendToLastLine( f"\\{('xt' if noteType=='crossReference' else 'ft')} {clean(referenceTail)}" )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'q':
                sublocation = "validateCrossReferenceOrFootnote: q of " + locationDescription
                qWho = qReferenceType = qMarker = None
                for attrib,value in subelement.items():
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, attrib, value )
                    if attrib=='who': qWho = value
                    elif attrib=='type': qReferenceType = value
                    elif attrib=='marker': qMarker = value # usually a quote character
                    else:
                        logging.warning( f"3d4r Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (3d4r)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if qReferenceType: assert qReferenceType in ('x-footnote',)
                    if qMarker:
                        assert qMarker in ( "'", '"', )
                        if BibleOrgSysGlobals.debugFlag: assert not (qWho or qReferenceType)
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "noteType", repr(noteType) )
                if BibleOrgSysGlobals.debugFlag: assert noteType in ('footnote','translation','study')
                qText = subelement.text.strip() if subelement.text else ''
                qTail = subelement.tail
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'qText', repr(qText) )
                #if BibleOrgSysGlobals.debugFlag: assert qText
                if '\n' in qText: # why's this
                    qText = qText.replace( '\n', '\\fp ' )
                thisBook.appendToLastLine( f'\\fq {qText}' )
                for sub2element in subelement:
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        #sub2location = "validateCrossReferenceOrFootnote: transChange of " + locationDescription
                        self.validateTransChange( thisBook, sub2element, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    else:
                        logging.error( f"gk23 Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation} (gk23)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if qTail and qTail.strip():
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'qTail', repr(qTail) )
                    thisBook.appendToLastLine( f'\\ft {clean(qTail)}' )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                sublocation = "validateCrossReferenceOrFootnote: catchWord of " + locationDescription
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '2w43', loadErrors )
                catchWordText, catchWordTail = subelement.text, subelement.tail
                if noteType == 'footnote':
                    thisBook.appendToLastLine( f'\\fq {clean(catchWordText)}' )
                    for sub2element in subelement: # Can have nested catchWords in some (horrible) OSIS files)
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'catchWord': #
                            sub2location = "validateCrossReferenceOrFootnote: catchWord of catchWord of " + locationDescription
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Have", sub2location, "j2f6" )
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '2d4r', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '23c6', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'c456n', loadErrors )
                            subCatchWordText = sub2element.text
                            if BibleOrgSysGlobals.debugFlag: assert noteType == 'footnote'
                            thisBook.appendToLastLine( f'\\fq {subCatchWordText}' )
                        else:
                            logging.error( f"8j6g Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                            loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (8j6g)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                elif noteType == 'translation':
                    thisBook.appendToLastLine( f'\\fq {clean(catchWordText)}' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh36', loadErrors )
                elif noteType == 'variant':
                    thisBook.appendToLastLine( f'\\fq {clean(catchWordText)}' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh37', loadErrors )
                elif noteType == 'alternative':
                    thisBook.appendToLastLine( f'\\fq {clean(catchWordText)}' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh38', loadErrors )
                else:
                    vPrint( 'Never', DEBUGGING_THIS_MODULE, f"{noteType!r} note not handled FG35" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                if catchWordTail:
                    thisBook.appendToLastLine( f'\\fq* {clean(catchWordTail)}' ) # Do we need the space
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateCrossReferenceOrFootnote: hi of " + locationDescription
                self.validateHighlight( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                justFinishedLG = False
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'rdg':
                sublocation = "validateCrossReferenceOrFootnote: rdg of " + locationDescription
                self.validateRDG( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                justFinishedLG = False
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                sublocation = "validateCrossReferenceOrFootnote: divineName of " + locationDescription
                self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                sublocation = "validateCrossReferenceOrFootnote: name of " + locationDescription
                validateProperName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references
                sublocation = "validateCrossReferenceOrFootnote: seg of " + locationDescription
                self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateCrossReferenceOrFootnote: note of " + locationDescription
                noteText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vw24', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'plq2', loadErrors )
                # Process the attributes
                notePlacement = noteOsisRef = noteOsisID = noteType = None
                for attrib,value in subelement.items():
                    if attrib=='type': noteType = value
                    elif attrib=='placement': notePlacement = value
                    elif attrib=='osisRef': noteOsisRef = value
                    elif attrib=='osisID': noteOsisID = value
                    else:
                        logging.warning( f"f5j3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (f5j3)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                logging.error( f"odf3 Unprocessed note: {repr(noteText)} {repr(noteType)} {repr(notePlacement)} {repr(noteOsisRef)} {repr(noteOsisID)}" )
                loadErrors.append( f"Unprocessed note: {repr(noteText)} {repr(noteType)} {repr(notePlacement)} {repr(noteOsisRef)} {repr(noteOsisID)} (odf3)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                sublocation = "validateCrossReferenceOrFootnote: transChange of " + locationDescription
                self.validateTransChange( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                sublocation = "validateCrossReferenceOrFootnote: foreign of " + locationDescription
                fText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                # Process the attributes
                fN = None
                for attrib,value in subelement.items():
                    if attrib=='n': fN = value
                    else:
                        logging.warning( f"h0j3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (h0j3)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                logging.error( f'Unused {fText!r} foreign field at {sublocation+" at "+verseMilestone}' )
                loadErrors.append( f'Unused {fText!r} foreign field at {sublocation+" at "+verseMilestone}' )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            else:
                logging.error( f"1d54 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (1d54)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if openFieldname: thisBook.appendToLastLine( f'\\{openFieldname}*' )
        #if element.tail and element.tail.strip(): thisBook.appendToLastLine( clean(element.tail) )
        noteTail = clean( element.tail, loadErrors, location, verseMilestone )
        if noteTail: thisBook.appendToLastLine( noteTail )
    # end of OSISXMLBible.validateCrossReferenceOrFootnote


    def validateTransChange( self, thisBook, element, location, verseMilestone, loadErrors ):
        """
        Handle a transChange element and return a string.
        """
        assert isinstance( thisBook, BibleBook )
        sublocation = "validateTransChange: transChange of " + location
        # Process the attributes
        transchangeType = None
        for attrib,value in element.items():
            if attrib=='type': transchangeType = value
            else:
                logging.warning( f"8q1k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (8q1k)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if BibleOrgSysGlobals.debugFlag: assert transchangeType in ('added',)
        tcText = clean(element.text) if element.text else ''
        thisBook.appendToLastLine( f'\\add {tcText}' )
        # Now process the subelements
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                sublocation = "validateTransChange: w of transChange of " + location
                self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                sublocation = "validateTransChange: divineName of transChange of " + location
                self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                sublocation = "validateTransChange: name of transChange of " + location
                validateProperName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateTransChange: note of transChange of " + location
                self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                sublocation = "validateTransChange: seg of transChange of " + location
                self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"dfv3 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {sublocation} (dfv3)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        tcTail = clean(element.tail) if element.tail else ''
        thisBook.appendToLastLine( f'\\add*{tcTail}' )
    # end of validateTransChange


    def validateVerseElement( self, thisBook, element, verseMilestone, chapterMilestone, locationDescription, loadErrors ):
        """
        Check/validate and process a verse element.

        This currently handles three types of OSIS files:
            1/ Has verse start milestones and end milestones
            2/ Has verse start milestones but no end milestones
            3/ Verse elements are containers for the actual verse information

        Returns one of the following:
            OSIS verse ID string for a startMilestone
            '' for an endMilestone
            'verseContainer.' + verse number string for a container
            'verseContents#' + verse number string + '#' + verse contents for a verse contained within the <verse>…</verse> markers
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"OSISXMLBible.validateVerseElement at {locationDescription} with {chapterMilestone!r} and {verseMilestone!r}" )
        assert isinstance( thisBook, BibleBook )
        location = "validateVerseElement: " + locationDescription
        verseText = element.text
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vT", verseText )
        #BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'x2f5', loadErrors )
        OSISVerseID = sID = eID = n = None
        for attrib,value in element.items():
            if attrib=='osisID': OSISVerseID = value
            elif attrib=='sID': sID = value
            elif attrib=='eID': eID = value
            elif attrib=='n': n = value
            else:
                displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                logging.warning( f"8jh6 Unprocessed {location!r} attribute ({attrib}) in {value} subelement of {displayTag}" )
                loadErrors.append( f"Unprocessed {location!r} attribute ({attrib}) in {value} subelement of {displayTag} (8jh6)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        vPrint( 'Never', DEBUGGING_THIS_MODULE, f" validateVerseElement attributes: OSISVerseID = {OSISVerseID!r} sID = {sID!r} eID = {eID!r} n = {n!r}" )
        if sID and eID:
            logging.critical( f"Invalid combined sID and eID verse attributes in {location}: {element.items()}" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if sID and not OSISVerseID:
            logging.error( f"Missing verse attributes in {location}: {element.items()}" )
            loadErrors.append( f"Missing verse attributes in {location}: {element.items()}" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        # See if this is a milestone or a verse container
        if len(element)==0 and ( sID or eID ): # it's a milestone (no sub-elements)
            if BibleOrgSysGlobals.debugFlag: assert not verseText
            if sID and OSISVerseID and not eID: # we have a start milestone
                if verseMilestone: # but we already have an open milestone
                    if self.haveEIDs:
                        logging.error( f"Got a {sID} verse milestone while {verseMilestone} is still open at {location}" )
                        loadErrors.append( f"Got a {sID} verse milestone while {verseMilestone} is still open at {location}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                verseMilestone = sID
                #for char in (' ','-'):
                #    if char in verseMilestone: # it contains a range like 'Mark.6.17 Mark.6.18' or 'Mark.6.17-Mark.6.18'
                #        chunks = verseMilestone.split( char )
                #        if BibleOrgSysGlobals.debugFlag: assert len(chunks) == 2
                #        verseMilestone = chunks[0] # Take the start of the range
                #if not verseMilestone.count('.')==2: logging.error( f"validateVerseElement: {verseMilestone} verse milestone seems wrong format for {OSISVerseID}" )
                vmBits, cmBits = verseMilestone.split( '.' ), chapterMilestone.split( '.' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "cv milestone stuff", repr(verseMilestone), repr(chapterMilestone), vmBits, cmBits )
                if chapterMilestone.startswith( 'chapterContainer.' ): # The chapter is a container but the verse is a milestone!
                    if not verseMilestone.startswith( chapterMilestone[17:] ):
                        logging.error( f"{chapterMilestone!r} verse milestone seems wrong in {location!r} chapter milestone at {verseMilestone}" )
                        loadErrors.append( f"{chapterMilestone!r} verse milestone seems wrong in {location!r} chapter milestone at {verseMilestone}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                elif vmBits[0:2] != cmBits[0:2]:
                    logging.error( f"This {chapterMilestone!r} verse milestone seems wrong in {location!r} chapter milestone at {verseMilestone}" )
                    loadErrors.append( f"This {chapterMilestone!r} verse milestone seems wrong in {location!r} chapter milestone at {verseMilestone}" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif eID and not OSISVerseID and not sID: # we have an end milestone
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here", repr(verseMilestone), repr(OSISVerseID), repr(sID), repr(eID) )
                self.haveEIDs = True
                if verseMilestone:
                    if eID==verseMilestone: pass # Good -- the end milestone matched the open start milestone
                    else:
                        logging.error( f"{eID!r} verse milestone end didn't match last end milestone {location!r} at {verseMilestone}" )
                        loadErrors.append( f"{eID!r} verse milestone end didn't match last end milestone {location!r} at {verseMilestone}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                else:
                    logging.critical( f"Have {location!r} verse end milestone but no verse start milestone encountered at {eID}" )
                    loadErrors.append( f"Have {location!r} verse end milestone but no verse start milestone encountered at {eID}" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                return '' # end milestone closes any open milestone
            else:
                logging.critical( f"Unrecognized verse milestone in {location}: {element.items()}" )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " ", verseMilestone ); assert False, "We want to stop here"
                return '' # don't have any other way to handle this

            if verseMilestone: # have an open milestone
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "'"+verseMilestone+"'" )
                if BibleOrgSysGlobals.debugFlag: assert ' ' not in verseMilestone
                if '-' in verseMilestone: # Something like Jas.1.7-Jas.1.8
                    chunks = verseMilestone.split( '-' )
                    if len(chunks) != 2:
                        logging.error( f"Shouldn't have multiple hyphens in verse milestone {verseMilestone!r}" )
                        loadErrors.append( f"Shouldn't have multiple hyphens in verse milestone {verseMilestone!r}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    bits1 = chunks[0].split( '.' )
                    if len(bits1) != 3:
                        logging.error( f"Expected three components before hyphen in verse milestone {verseMilestone!r}" )
                        loadErrors.append( f"Expected three components before hyphen in verse milestone {verseMilestone!r}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    bits2 = chunks[1].split( '.' )
                    if len(bits2) != 3:
                        logging.error( f"Expected three components after hyphen in verse milestone {verseMilestone!r}" )
                        loadErrors.append( f"Expected three components after hyphen in verse milestone {verseMilestone!r}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        bits2 = [bits1[0],bits1[1],'999'] # Try to do something intelligent
                    thisBook.addLine( 'v', bits1[2]+'-'+bits2[2] )
                else: # no hyphen
                    bits = verseMilestone.split( '.' )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "sdfssf", verseMilestone, bits )
                    if BibleOrgSysGlobals.debugFlag: assert len(bits) >= 3
                    thisBook.addLine( 'v', bits[2]+' ' )
                vTail = clean(element.tail) # Newlines and leading spaces are irrelevant to USFM formatting
                if vTail: # This is the main text of the verse (follows the verse milestone)
                    thisBook.appendToLastLine( vTail )
                return verseMilestone
            if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here" # Should not happen

        else: # not a milestone -- it's verse container
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 's2d4', loadErrors )
            bits = OSISVerseID.split('.')
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "OSISXMLBible.validateVerseElement verse container bits", bits, 'vT', verseText )
            if BibleOrgSysGlobals.debugFlag: assert len(bits)==3 and bits[1].isdigit() and bits[2].isdigit()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "validateVerseElement: Have a verse container at", verseMilestone )
            if verseText and verseText.strip():
                if self.source == "ftp://unboundftp.biola.edu/pub/albanian_utf8.zip": # Do some special handling
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here", "&amp;quot;" in verseText, "&quot;" in verseText )
                    verseText = verseText.lstrip().replace('&quot;','"').replace('&lt;','<').replace('&gt;','>') # Fix some encoding issues
                    if "&" in verseText: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Still have ampersand in {verseText!r}" )
                return 'verseContents#' + bits[2] + '#' + verseText
            else: # it's a container for subelements
                return 'verseContainer.' + bits[2]

        if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here" # Should never reach this point in the code
    # end of OSISXMLBible.validateVerseElement


    def validateTitle( self, thisBook, element, locationDescription, chapterMilestone, verseMilestone, loadErrors ):
        """
        Check/validate and process a OSIS Bible paragraph, including all subfields.
        """
        assert isinstance( thisBook, BibleBook )
        location = "validateTitle: " + locationDescription
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateTitle @ {locationDescription} @ {chapterMilestone}/{verseMilestone}" )

        BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c4vd', loadErrors )
        titleText = clean( element.text, loadErrors, location, verseMilestone )

        titleType = titleSubType = titleShort = titleLevel = titleCanonicalFlag = None
        for attrib,value in element.items():
            if attrib=='type':
                titleType = value
            elif attrib=='subType':
                titleSubType = value
            elif attrib=='short':
                titleShort = value
            elif attrib=='level':
                titleLevel = value
            elif attrib=='canonical':
                titleCanonicalFlag = value
                assert titleCanonicalFlag in ('true','false')
            else:
                logging.warning( f"4b8e Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location} (4b8e)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'vdq2', repr(titleType), repr(titleSubType), repr(titleText), titleLevel, titleCanonicalFlag )
        if BibleOrgSysGlobals.debugFlag:
            if titleType: assert titleType in ('main','chapter','psalm','scope','sub','parallel','acrostic')
            if titleSubType: assert titleSubType == 'x-preverse'
        if chapterMilestone:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'title', verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
            if titleText:
                if not titleType and not titleShort and self.language=='ksw': # it's a Karen alternate chapter number
                    thisBook.addLine( 'cp', titleText )
                elif titleType == 'parallel':
                    thisBook.addLine( 'sr', titleText )
                elif titleCanonicalFlag=='true':
                    assert titleType == 'psalm'
                    thisBook.addLine( 'd', titleText )
                else: # let's guess that it's a section heading
                    if DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "title assumed to be section heading", verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
                    sfm = 's'
                    if titleLevel:
                        assert titleLevel in ('1','2','3')
                        sfm += titleLevel
                    thisBook.addLine( sfm, titleText )
        else: # must be in the introduction if it's before all chapter milestones
        #if self.haveBook:
            #assert titleText
            if titleText:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'title', repr(titleText) )
                thisBook.addLine( 'imt', titleText ) # Could it also be 'is'?
        #else: # Must be a book group title
            #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'vcw5', loadErrors )
            #if BibleOrgSysGlobals.debugFlag: assert titleText
            #if titleText:
                #dPrint( 'Info', DEBUGGING_THIS_MODULE, "    Got book group title", repr(titleText) )
                #self.divisions[titleText] = []
                ##thisBook.addLine( 'bgt', titleText ) # Could it also be 'is'?
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                sublocation = "validateTitle: title of " + locationDescription
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '21d5', loadErrors )
                titleText = clean( subelement.text, loadErrors, sublocation, verseMilestone )
                # Handle attributes
                titleType = titleLevel = None
                for attrib,value in subelement.items():
                    if attrib== 'type': titleType = value
                    elif attrib== 'level': titleLevel = value
                    else:
                        logging.warning( f"56v3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {subelement.tag} at {sublocation} (56v3)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if titleText:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(mainDivType), repr(titleType), repr(titleLevel), repr(chapterMilestone) )
                    if chapterMilestone: marker = 'sr'
                    else: marker = f"mt{titleLevel if titleLevel else ''}"
                    thisBook.addLine( marker, titleText )
                for sub2element in subelement:
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference':
                        sub2location = "reference of " + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'f5g2', loadErrors )
                        referenceText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                        referenceTail = clean( sub2element.tail, loadErrors, sub2location, verseMilestone )
                        referenceOsisRef = None
                        for attrib,value in sub2element.items():
                            if attrib=='osisRef':
                                referenceOsisRef = value
                            else:
                                logging.warning( f"89n5 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub2element.tag} at {sublocation}" )
                                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub2element.tag} at {sublocation} (89n5)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if BibleOrgSysGlobals.debugFlag:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'here bd02', repr(referenceText), repr(referenceOsisRef), repr(referenceTail) )
                        thisBook.addLine( 'r', referenceText+referenceTail )
                    else:
                        logging.error( f"2d6h Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (2d6h)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateTitle: hi of " + locationDescription
                self.validateHighlight( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateTitle: note of " + locationDescription
                self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'w': # Probably a canonical Psalm title
                sublocation = "validateTitle: w of " + locationDescription
                self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                #if 0:
                    #word = subelement.text if subelement.text else ''
                    ## Handle attributes
                    #lemma = morph = None
                    #for attrib,value in subelement.items():
                        #if attrib=='lemma': lemma = value
                        #elif attrib=='morph': morph = value
                        #else:
                            #logging.warning( f"dv42 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                            #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (dv42)" )
                    #if lemma and lemma.startswith('strong:'):
                        #word += f"\\str {lemma[7:]}\\str*"
                        #lemma = None # we've used it
                    #if lemma or morph:
                        #if BibleOrgSysGlobals.debugFlag: logging.info( f"Losing lemma or morph here at {verseMilestone}" )
                        #loadErrors.append( f"Losing lemma or morph here at {verseMilestone}" )
                    ## Handle sub-elements
                    #for sub2element in subelement:
                        #if sub2element.tag == OSISXMLBible.OSISNameSpace+'xyz':
                            #sub2location = "divineName of " + sublocation
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, 'fbf3', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'kje3', loadErrors )
                            #if BibleOrgSysGlobals.debugFlag: assert sub2element.text
                            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Here scw2", repr(sub2element.text) )
                            #word += f"\\nd {sub2element.text}\\nd*"
                            #if sub2element.tail: word += sub2element.tail
                        #else:
                            #logging.error( f"kd92 Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                            #loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (kd92)" )
                            #if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                    #if subelement.tail: word += subelement.tail
                    #thisBook.appendToLastLine( word )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'abbr':
                sublocation = "validateTitle: abbr of " + locationDescription
                abbrText = subelement.text
                abbrTail = subelement.tail
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'gd56', loadErrors )
                # Handle attributes
                abbrExpansion = None
                for attrib,value in subelement.items():
                    if attrib== 'expansion': abbrExpansion = value
                    else:
                        logging.warning( f"vsy3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {subelement.tag} at {sublocation} (vsy3)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                #thisBook.appendToLastLine( f'{abbrText}\\abbr {abbrExpansion}\\abbr*{abbrTail}' )
                logging.warning( f'Unused {repr(abbrText)}={repr(abbrExpansion)} abbr field at {sublocation+" at "+verseMilestone}' )
                loadErrors.append( f'Unused {repr(abbrText)}={repr(abbrExpansion)} abbr field at {sublocation+" at "+verseMilestone}' )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"abbr in title: {abbrText!r} -> {abbrExpansion!r}" )
                    pass
                    #assert False, "We want to stop here"
                thisBook.appendToLastLine( f'{abbrText}{abbrTail}' )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                sublocation = "validateTitle: transChange of " + locationDescription
                self.validateTransChange( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                sublocation = "validateTitle: foreign of " + locationDescription
                foreignText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                # Process the attributes
                foreignN = None
                for attrib,value in subelement.items():
                    if attrib=='n': foreignN = value # This can be a Hebrew letter/number in OS KJV
                    else:
                        logging.warning( f"h0j3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (h0j3)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if 'Ps' in verseMilestone: # or 'Lam' in verseMilestone:
                    # Assume it's an acrostic heading (but we don't use the foreignN field)
                    thisBook.addLine( 'qa', foreignText )
                else:
                    logging.error( f'Unused {foreignText!r} foreign field at {sublocation+" at "+verseMilestone}' )
                    loadErrors.append( f'Unused {foreignText!r} foreign field at {sublocation+" at "+verseMilestone}' )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                sublocation = "validateTitle: reference of " + locationDescription
                rText = subelement.text
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'ld10', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'js12', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'jsv2', loadErrors )
                logging.error( f'Unused {rText!r} reference field at {sublocation+" at "+verseMilestone}' )
                loadErrors.append( f'Unused {rText!r} reference field at {sublocation+" at "+verseMilestone}' )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                sublocation = "validateTitle: verse of " + locationDescription
                verseMilestone = validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                sublocation = "validateTitle: verse of " + locationDescription
                self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( f"jkd7 Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {locationDescription}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {locationDescription} (jkd7)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
        #titleTail = clean( element.tail, loadErrors, location, verseMilestone )
    # end of OSISXMLBible.validateTitle


    def validateHeader( self, header, loadErrors ):
        """
        Check/validate the given OSIS header record.
        """
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading {self.abbreviation+' ' if self.abbreviation else ''}OSIS header…" )
        headerlocation = 'header'
        BibleOrgSysGlobals.checkXMLNoText( header, headerlocation, '2s90', loadErrors )
        BibleOrgSysGlobals.checkXMLNoAttributes( header, headerlocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( header, headerlocation, '0k6l', loadErrors )

        for element in header:
            if element.tag == OSISXMLBible.OSISNameSpace+'revisionDesc':
                location = "revisionDesc of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '2t5y', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6hj8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '3a1l', loadErrors )
                # Process the attributes first
                resp = None
                for attrib,value in element.items():
                    if attrib=='resp': resp = value
                    else:
                        logging.warning( f"4j6a Unprocessed {attrib} attribute ({value}) in {location}" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {location} (4j6a)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, '4f3f', loadErrors )
                    if len(subelement):
                        logging.error( f"Unexpected {len(subelement)} subelements in subelement {subelement.tag} in {osisWork} revisionDesc" )
                        loadErrors.append( f"Unexpected {len(subelement)} subelements in subelement {subelement.tag} in {osisWork} revisionDesc" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '9hj5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6g3s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4sd2', loadErrors )
                        date = subelement.text
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4f4s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3c5g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9k5a', loadErrors )
                        p = element.text
                    else:
                        logging.error( f"6g4g Unprocessed {subelement.text!r} sub-element ({subelement.tag}) in revisionDesc element" )
                        loadErrors.append( f"Unprocessed {subelement.text!r} sub-element ({subelement.tag}) in revisionDesc element (6g4g)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
            elif element.tag == OSISXMLBible.OSISNameSpace+'work':
                location = "work of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '5h9k', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '2s3d', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '1d4f', loadErrors )
                # Process the attributes first
                osisWorkName = lang = None
                for attrib,value in element.items():
                    if attrib=='osisWork':
                        osisWorkName = value
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Have a {osisWorkName!r} work" )
                    elif attrib==OSISXMLBible.XMLNameSpace+"lang": lang = value
                    else:
                        logging.warning( f"2k5s Unprocessed {attrib} attribute ({value}) in work element" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in work element (2k5s)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                assert osisWorkName
                # Now process the subelements
                for subelement in element:
                    if len(subelement):
                        logging.error( f"hf54 Unexpected {len(subelement)} subelements in subelement {subelement.tag} in {osisWork} work" )
                        loadErrors.append( f"Unexpected {len(subelement)} subelements in subelement {subelement.tag} in {osisWork} work (hf54)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        if 0: self.validateTitle( thisBook, subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        else:
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '0k5f', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '8k0k', loadErrors )
                            if not self.title: self.title = subelement.text # Take the first title
                            titleType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': titleType = value
                                else:
                                    logging.warning( f"8f83 Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                    loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (8f83)" )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'version':
                        sublocation = "version of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '3g1h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '7h4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2j9z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '0k3d', loadErrors )
                        self.suppliedMetadata['OSIS']['Version'] = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( f"93d2 Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                            loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (93d2)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4x5h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3f9j', loadErrors )
                        date = subelement.text
                        dateType = dateEvent = None
                        for attrib,value in subelement.items():
                            if attrib=='type': dateType = value
                            elif attrib=='event': dateEvent = value
                            else:
                                logging.warning( f"2k4d Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (2k4d)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if BibleOrgSysGlobals.debugFlag: assert dateType in (None,'Gregorian')
                        if BibleOrgSysGlobals.debugFlag: assert dateEvent in (None,'eversion')
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'creator':
                        sublocation = "creator of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9n3z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3n5z', loadErrors )
                        self.suppliedMetadata['OSIS']['Creator'] = subelement.text
                        creatorRole = creatorType = None
                        for attrib,value in subelement.items():
                            if attrib=='role': creatorRole = value
                            elif attrib=='type': creatorType = value
                            else:
                                logging.warning( f"9f2d Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (9f2d)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, "    Creator (role={!r}{}) was {!r}".format( creatorRole, f", type={creatorType!r}" if creatorType else '', self.suppliedMetadata['OSIS']['Creator'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'contributor':
                        sublocation = "contributor of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2u5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z4o', loadErrors )
                        self.suppliedMetadata['OSIS']['Contributor'] = subelement.text
                        contributorRole = None
                        for attrib,value in subelement.items():
                            if attrib=='role': contributorRole = value
                            else:
                                logging.warning( f"1s5g Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (1s5g)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Contributor ({contributorRole}) was {self.suppliedMetadata['OSIS']['Contributor']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'subject':
                        sublocation = "subject of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'frg3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ft4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'c35g', loadErrors )
                        self.suppliedMetadata['OSIS']['Subject'] = subelement.text
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Subject was {self.suppliedMetadata['OSIS']['Subject']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'description':
                        sublocation = "description of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4a7s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1j6z', loadErrors )
                        self.suppliedMetadata['OSIS']['Description'] = subelement.text
                        descriptionType = descriptionSubType = resp = None
                        for attrib,value in subelement.items():
                            if attrib=='type': descriptionType = value
                            elif attrib=='subType': descriptionSubType = value
                            elif attrib=='resp': resp = value
                            else:
                                logging.warning( f"6f3d Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (6f3d)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if descriptionType: assert descriptionType in ('usfm','x-english','x-lwc')
                        if self.suppliedMetadata['OSIS']['Description'] and BibleOrgSysGlobals.verbosityLevel > 2:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Description{} is {!r}".format( f" ({descriptionType})" if descriptionType else '', self.suppliedMetadata['OSIS']['Description'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'format':
                        sublocation = "format of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8v3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5n3x', loadErrors )
                        self.suppliedMetadata['OSIS']['Format'] = subelement.text
                        formatType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': formatType = value
                            else:
                                logging.warning( f"2f5s Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (2f5s)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if BibleOrgSysGlobals.debugFlag: assert formatType == 'x-MIME'
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Format ({formatType}) is {self.suppliedMetadata['OSIS']['Format']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'type':
                        sublocation = "type of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j8b', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3b4z', loadErrors )
                        self.suppliedMetadata['OSIS']['Type'] = subelement.text
                        typeType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': typeType = value
                            else:
                                logging.warning( f"7j3f Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (7j3f)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if BibleOrgSysGlobals.debugFlag: assert typeType == 'OSIS'
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Type ({typeType}) is {self.suppliedMetadata['OSIS']['Type']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'identifier':
                        sublocation = "identifier of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2x6e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5a2m', loadErrors )
                        identifier = subelement.text
                        identifierType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': identifierType = value
                            else:
                                logging.warning( f"2d5g Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (2d5g)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "id", repr(identifierType) )
                        if BibleOrgSysGlobals.debugFlag: assert identifierType in ('OSIS','URL','ISBN','x-ebible-id')
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Identifier ({identifierType}) is {identifier!r}" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Here vds1", repr(self.name), repr(self.abbreviation) )
                        if identifierType=='OSIS':
                            if not self.name: self.name = identifier
                            if identifier.startswith( 'Bible.' ) and not self.abbreviation:
                                self.abbreviation = identifier[6:]
                        self.suppliedMetadata['OSIS']['Identifier'] = identifier
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Here vds2", repr(self.name), repr(self.abbreviation) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'source':
                        sublocation = "source of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4gh7', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6p3a', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1i8p', loadErrors )
                        self.suppliedMetadata['OSIS']['Source'] = subelement.text
                        sourceRole = None
                        for attrib,value in subelement.items():
                            if attrib=='role': sourceRole = value
                            else:
                                logging.warning( f"6h7h Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (6h7h)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, "    Source{} was {!r}".format( f" ({sourceRole})" if sourceRole else '', self.suppliedMetadata['OSIS']['Source'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'publisher':
                        sublocation = "publisher of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z7g', loadErrors )
                        self.suppliedMetadata['OSIS']['Publisher'] = subelement.text.replace( '&amp;', '&' )
                        publisherType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': publisherType = value
                            else:
                                logging.warning( f"7g5g Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (7g5g)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Publisher {f'({publisherType}) ' if publisherType else ''}is/was {self.suppliedMetadata['OSIS']['Publisher']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'scope':
                        sublocation = "scope of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2g5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1z4i', loadErrors )
                        self.suppliedMetadata['OSIS']['Scope'] = subelement.text
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Scope is {self.suppliedMetadata['OSIS']['Scope']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'coverage':
                        sublocation = "coverage of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d6g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3a6p', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9l2p', loadErrors )
                        self.suppliedMetadata['OSIS']['Coverage'] = subelement.text
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Coverage is {self.suppliedMetadata['OSIS']['Coverage']!r}" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'refSystem':
                        sublocation = "refSystem of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2s4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3mtp', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3p65', loadErrors )
                        self.suppliedMetadata['OSIS']['RefSystem'] = subelement.text
                        if self.suppliedMetadata['OSIS']['RefSystem'] in ('Bible','Bible.KJV','Bible.NRSVA','Dict.Strongs','Dict.Robinsons','Dict.strongMorph'):
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Reference system is {self.suppliedMetadata['OSIS']['RefSystem']!r}" )
                        else:
                            logging.info( f"Discovered an unknown {self.suppliedMetadata['OSIS']['RefSystem']!r} refSystem" )
                            loadErrors.append( f"Discovered an unknown {self.suppliedMetadata['OSIS']['RefSystem']!r} refSystem" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'language':
                        sublocation = "language of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n34', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4v2n', loadErrors )
                        self.suppliedMetadata['OSIS']['Language'] = subelement.text
                        languageType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': languageType = value
                            else:
                                logging.warning( f"6g4f Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (6g4f)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if languageType in ('SIL','IETF','x-ethnologue','x-in-english','x-vernacular'):
                            if ISOLanguages.isValidLanguageCode( self.suppliedMetadata['OSIS']['Language'] ):
                                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Language is: {ISOLanguages.getLanguageName( self.suppliedMetadata['OSIS']['Language'] )}" )
                            elif BibleOrgSysGlobals.verbosityLevel>2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Discovered an unknown {self.suppliedMetadata['OSIS']['Language']!r} language" )
                        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Discovered an unknown {languageType!r} languageType" )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'rights':
                        sublocation = "rights of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '6v2x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9l5b', loadErrors )
                        copyrightType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': copyrightType = value
                            else:
                                logging.warning( f"1s3d Unprocessed {sublocation!r} attribute ({attrib}) in {value}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} attribute ({attrib}) in {value} (1s3d)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        vPrint( 'Never', DEBUGGING_THIS_MODULE, "copyrightType", copyrightType )
                        if BibleOrgSysGlobals.debugFlag:
                            assert copyrightType in (None,'x-copyright','x-license','x-license-url','x-BY-SA','x-BY','x-comments-to')
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, "    Rights{} are/were {!r}".format( f" ({copyrightType})" if copyrightType else '', subelement.text ) )
                        self.suppliedMetadata['OSIS']['Rights'] = subelement.text
                        if copyrightType: self.suppliedMetadata['OSIS']['CopyrightType'] = copyrightType
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'relation':
                        sublocation = "relation of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'g4h2', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'd2fd', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 's2fy', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'gh53', loadErrors )
                    else:
                        logging.error( f"7h5g Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text}" )
                        loadErrors.append( f"Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text} (7h5g)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                #if element.find('date') is not None: self.date = element.find('date').text
                #if element.find('title') is not None: self.title = element.find('title').text
                self.workNames.append( osisWorkName )
            elif element.tag == OSISXMLBible.OSISNameSpace+'workPrefix':
                location = "workPrefix of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, 'f5h8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6g4f', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, 'f2g7', loadErrors )
                # Process the attributes first
                workPrefixPath = workPrefixWork = None
                for attrib,value in element.items():
                    if attrib=='path':
                        workPrefixPath = value
                        assert workPrefixPath.startswith( '//' )
                        assert '/@' in workPrefixPath
                        workPrefixPath = workPrefixPath[2:] # Remove two leading slashes
                        assert workPrefixPath in ( 'w/@lemma', 'w/@morph' ) # All we've discovered so far
                    elif attrib=='osisWork':
                        workPrefixWork = value
                        assert workPrefixWork in self.workNames
                    else:
                        logging.warning( f"7yh4 Unprocessed {attrib} attribute ({value}) in workPrefix element" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in workPrefix element (7yh4)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                assert workPrefixPath and workPrefixWork
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'revisionDesc':
                        sublocation = "revisionDesc of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c3t5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2w3e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'm5o0', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'z2f8', loadErrors )
                        #self.something = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( f"3h6r Unprocessed {subelement.tag!r} attribute ({attrib}) in {value} subelement of workPrefix element" )
                            loadErrors.append( f"Unprocessed {subelement.tag!r} attribute ({attrib}) in {value} subelement of workPrefix element (3h6r)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    else:
                        logging.error( f"8h4g Unprocessed {subelement.text!r} sub-element ({subelement.tag}) in workPrefix element" )
                        loadErrors.append( f"Unprocessed {subelement.text!r} sub-element ({subelement.tag}) in workPrefix element (8h4g)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                # NOTE: These subelements are not currently saved
                self.workPrefixes[workPrefixPath] = workPrefixWork
            else:
                logging.error( f"Expected to load {OSISXMLBible.OSISNameSpace+'work'!r} but got {element.tag!r}" )
                loadErrors.append( f"Expected to load {OSISXMLBible.OSISNameSpace+'work'!r} but got {element.tag!r}" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            if element.tail is not None and element.tail.strip():
                logging.error( f"Unexpected {element.tag!r} tail data after {element.tail} element in header element" )
                loadErrors.append( f"Unexpected {element.tag!r} tail data after {element.tail} element in header element" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if not self.workNames:
            logging.warning( "OSIS header doesn't specify any work records." )
            loadErrors.append( "OSIS header doesn't specify any work records." )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
    # end of OSISXMLBible.validateHeader


    def validateFrontMatter( self, bookList, frontMatter, loadErrors ):
        """
        Check/validate the given OSIS front matter (div) record.
        """
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading {self.abbreviation+' ' if self.abbreviation else ''}OSIS front matter…" )
        assert isinstance( bookList, list )

        frontMatterLocation = "frontMatter"
        BibleOrgSysGlobals.checkXMLNoText( frontMatter, frontMatterLocation, 'c3a2', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( frontMatter, frontMatterLocation, 'm7s9', loadErrors )
        # Process the attributes first
        for attrib,value in frontMatter.items():
            if attrib=='type':
                pass # We've already processed this
            else:
                logging.warning( f"98h4 Unprocessed {attrib} attribute ({value}) in {frontMatterLocation}" )
                loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {frontMatterLocation} (98h4)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        thisBook = BibleBook( self, 'FRT' )
        thisBook.objectNameString = 'OSIS XML Bible Book object'
        thisBook.objectTypeString = 'OSIS'
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Appending {thisBook.BBB} and {len(loadErrors)} load errors to bookList" )
        for bkLE in bookList:
            assert len(bkLE) == 2 # bookObject and loadErrors
            assert bkLE[0].BBB != 'FRT' # Don't allow duplicate books
        bookList.append( (thisBook,loadErrors.copy()) )
        loadErrors.clear()
        self.haveBook = True

        chapterMilestone = verseMilestone = 'FrontMatter'
        for element in frontMatter:
            if element.tag == OSISXMLBible.OSISNameSpace+'titlePage':
                location = "titlePage of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'k9l3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, '1w34', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'a3s4', loadErrors )
                # Process the attributes first
                for attrib,value in element.items():
                    if attrib=='type':
                        if BibleOrgSysGlobals.debugFlag: assert value == 'front' # We've already processed this in the calling routine
                    else:
                        logging.warning( f"3f5d Unprocessed {attrib} attribute ({value}) in {location}" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {location} (3f5d)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'dv61', loadErrors )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '5ygg', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j54', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'h3x5', loadErrors )
                        p = element.text
                    else:
                        logging.error( f"1dc5 Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text}" )
                        loadErrors.append( f"Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text} (1dc5)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = "div of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'b3f4', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'd3s2', loadErrors )
                # Process the attributes first
                divType = None
                for attrib,value in element.items():
                    if attrib=='type': divType = value
                    else:
                        logging.warning( f"7h4g Unprocessed {attrib} attribute ({value}) in {location}" )
                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {location} (7h4g)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                if BibleOrgSysGlobals.debugFlag: assert divType == 'x-license'

                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        self.validateTitle( thisBook, subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '48j6', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'l0l0', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'k8j8', loadErrors )
                            #date = subelement.text
                            #logging.warning( "sdh3 Not handled yet", subelement.text )
                            #loadErrors.append( "sdh3 Not handled yet", subelement.text )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2de5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'd4d4', loadErrors )
                        p = element.text
                        # Now process the subelements
                        for sub2element in subelement:
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sublocation, 's3s3', loadErrors )
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'a':
                                sub2location = "a of " + sublocation
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'j4h3', loadErrors )
                                aText, aTail = element.text, element.tail
                                # Process the attributes
                                href = None
                                for attrib,value in sub2element.items():
                                    if attrib=='href': href = value
                                    else:
                                        logging.warning( f"7g4a Unprocessed {attrib} attribute ({value}) in {sub2location}" )
                                        loadErrors.append( f"Unprocessed {attrib} attribute ({value}) in {sub2location} (7g4a)" )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            else:
                                logging.error( f"3d45 Unprocessed {sublocation!r} sub2-element ({sub2element.tag}) in {sub2element.text}" )
                                loadErrors.append( f"Unprocessed {sublocation!r} sub2-element ({sub2element.tag}) in {sub2element.text} (3d45)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    else:
                        logging.error( f"034f Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text}" )
                        loadErrors.append( f"Unprocessed {location!r} sub-element ({subelement.tag}) in {subelement.text} (034f)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
            else:
                logging.error( f"2sd4 Unprocessed {frontMatterLocation!r} sub-element ({element.tag}) in {element.text}" )
                loadErrors.append( f"Unprocessed {frontMatterLocation!r} sub-element ({element.tag}) in {element.text} (2sd4)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
            if element.tail is not None and element.tail.strip():
                logging.error( f"Unexpected {element.tag!r} tail data after {element.tail} element in header element" )
                loadErrors.append( f"Unexpected {element.tag!r} tail data after {element.tail} element in header element" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"

        self.stashBook( thisBook )
        self.haveBook = True
    # end of OSISXMLBible.validateFrontMatter


    def validateAndExtractMainDiv( self, bookList, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This may be a book group, or directly into a book
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"validateAndExtractMainDiv( {len(bookList)}, {len(div)}, {len(loadErrors)} )…" )
        assert isinstance( bookList, list )
        assert isinstance( loadErrors, list )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading {self.abbreviation+' ' if self.abbreviation else ''}OSIS main div…" )
        self.haveEIDs = False
        self.haveBook = False


        def validateGroupTitle( element, locationDescription ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.
            """
            location = "validateGroupTitle: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoTail( element, location, 'c4vd', loadErrors )
            titleText = element.text
            titleType = titleSubType = titleShort = titleLevel = None
            for attrib,value in element.items():
                #if attrib=='type':
                    #titleType = value
                #elif attrib=='subType':
                    #titleSubType = value
                if attrib=='short':
                    titleShort = value
                #elif attrib=='level':
                    #titleLevel = value # Not used anywhere yet :(
                else:
                    logging.warning( f"vdv3 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location} (vdv3)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            #if titleSubType: assert titleSubType == 'x-preverse'
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'js21', loadErrors )
            if BibleOrgSysGlobals.debugFlag: assert titleText
            if titleText:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, "    Got book group title", repr(titleText) )
                self.divisions[titleText] = []
        # end of OSISXMLBible.validateGroupTitle


        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {mainDivOsisID} {mainDivType}…" )
            elif attrib=='osisID':
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {mainDivOsisID} {mainDivType}…" )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( f"93f5 Unprocessed {value!r} attribute ({attrib}) in main div element" )
                loadErrors.append( f"Unprocessed {value!r} attribute ({attrib}) in main div element (93f5)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( f"Incomplete mainDivType {mainDivType!r} and mainDivOsisID {mainDivOsisID!r} attributes in main div element" )
            loadErrors.append( f"Incomplete mainDivType {mainDivType!r} and mainDivOsisID {mainDivOsisID!r} attributes in main div element" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        if mainDivType == 'bookGroup': # this is all the books lumped in together into one big div
            if BibleOrgSysGlobals.debugFlag: assert mainDivCanonical == 'true'
            # We have to set BBB when we get a chapter reference
            vPrint( 'Info', DEBUGGING_THIS_MODULE, "  Loading a book group…" )
            self.haveBook = False
            for element in div:
                if element.tag == OSISXMLBible.OSISNameSpace+'title':
                    location = f"title of {mainDivType} div"
                    validateGroupTitle( element, location )
                elif element.tag == OSISXMLBible.OSISNameSpace+'div': # Assume it's a book
                    self.validateAndExtractBookDiv( bookList, element, loadErrors )
                else:
                    logging.error( f"hfs6 Unprocessed {mainDivType!r} sub-element ({element.tag}) in {element.text} div" )
                    loadErrors.append( f"Unprocessed {mainDivType!r} sub-element ({element.tag}) in {element.text} div (hfs6)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        elif mainDivType == 'book': # this is a single book (not in a group)
            self.validateAndExtractBookDiv( bookList, div, loadErrors )
        else:
            logging.critical( f"What kind of OSIS book div is this? {repr(mainDivType)} {repr(mainDivOsisID)} {repr(mainDivCanonical)}" )
            loadErrors.append( f"What kind of OSIS book div is this? {repr(mainDivType)} {repr(mainDivOsisID)} {repr(mainDivCanonical)}" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
    # end of OSISXMLBible.validateAndExtractMainDiv


    def validateAndExtractBookDiv( self, bookList, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This should be a book division.
        """
        assert isinstance( bookList, list )
        assert isinstance( loadErrors, list )

        def validateChapterElement( bookList, element, chapterMilestone, verseMilestone, locationDescription ):
            """
            Check/validate and process a chapter element.

            Returns one of the following:
                OSIS chapter ID string for a startMilestone
                '' for an endMilestone
                'chapter' + chapter number string for a container
            """
            nonlocal BBB, USFMAbbreviation, USFMNumber #, bookResults, USFMResults
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateChapterElement at {locationDescription} with {chapterMilestone} and {verseMilestone}" )
            assert isinstance( bookList, list )

            location = "validateChapterElement: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 's2a8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'j9k7', loadErrors )
            OSISChapterID = sID = eID = chapterN = canonical = chapterTitle = None
            for attrib,value in element.items():
                if attrib=='osisID': OSISChapterID = value
                elif attrib=='sID': sID = value
                elif attrib=='eID': eID = value
                elif attrib=='n': chapterN = value
                elif attrib=='canonical': canonical = value
                elif attrib=='chapterTitle': chapterTitle = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( f"5f3d Unprocessed {location!r} attribute ({attrib}) in {value} subelement of {displayTag}" )
                    loadErrors.append( f"Unprocessed {location!r} attribute ({attrib}) in {value} subelement of {displayTag} (5f3d)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            if sID and not OSISChapterID:
                logging.error( f"Missing chapter ID attribute in {location}: {element.items()}" )
                loadErrors.append( f"Missing chapter ID attribute in {location}: {element.items()}" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

            if len(element)==0 and ( sID or eID or OSISChapterID): # it's a chapter milestone (no sub-elements)
                # No verse milestone should be open because verses can't cross chapter boundaries
                if verseMilestone:
                    if self.haveEIDs:
                        logging.error( f"Unexpected {element.items()} chapter milestone while {verseMilestone} verse milestone is still open at {location}" )
                        loadErrors.append( f"Unexpected {element.items()} chapter milestone while {verseMilestone} verse milestone is still open at {location}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

                if OSISChapterID and sID and not eID:
                    chapterMilestone = sID
                    #if not chapterMilestone.count('.')==1: logging.warning( f"{chapterMilestone} chapter milestone seems wrong format for {OSISChapterID} at {location}" )
                elif eID and not OSISChapterID and not sID:
                    if chapterMilestone and eID==chapterMilestone: chapterMilestone = ''
                    else:
                        logging.error( f"Chapter milestone {eID} end didn't match {chapterMilestone} at {location}" )
                        loadErrors.append( f"Chapter milestone {eID} end didn't match {chapterMilestone} at {location}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                elif OSISChapterID and not (sID or eID): # some OSIS formats use this
                    if BibleOrgSysGlobals.debugFlag: assert canonical == 'true'
                    chapterMilestone = OSISChapterID
                else:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'SQUIGGLE', repr(OSISChapterID), repr(sID), repr(eID) )
                    logging.error( f"Unrecognized chapter milestone in {location}: {element.items()} at {location}" )
                    loadErrors.append( f"Unrecognized chapter milestone in {location}: {element.items()} at {location}" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

                if chapterMilestone: # Have a chapter milestone like Jas.1
                    if not OSISChapterID:
                        logging.error( f"Missing chapter ID for {chapterMilestone} at {location}" )
                        loadErrors.append( f"Missing chapter ID for {chapterMilestone} at {location}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    else:
                        if not OSISChapterID.count('.')==1:
                            logging.error( f"{OSISChapterID} chapter ID seems wrong format for {chapterMilestone} at {location}" )
                            loadErrors.append( f"{OSISChapterID} chapter ID seems wrong format for {chapterMilestone} at {location}" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        bits = OSISChapterID.split( '.' )
                        if BibleOrgSysGlobals.debugFlag: assert len(bits) == 2
                        cmBBB = None
                        try:
                            cmBBB = bos_books_codes_py.osis_book_code_to_bos_book_code( bits[0] )
                        except KeyError:
                            logging.critical( f"{bits[0]!r} is not a valid OSIS book identifier in chapter milestone {OSISChapterID}" )
                            loadErrors.append( f"{bits[0]!r} is not a valid OSIS book identifier in chapter milestone {OSISChapterID}" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        if cmBBB and isinstance( cmBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Multiple alternatives for OSIS {cmBBB!r}: {mainDivOsisID} (Choosing the first one)" )
                            cmBBB = cmBBB[0]
                        if cmBBB and cmBBB != BBB: # We've started on a new book
                            #if BBB and ( len(bookResults)>20 or len(USFMResults)>20 ): # Save the previous book
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here MAGIC", cmBBB, BBB, repr(chapterMilestone), len(thisBook._rawLines) )
                            if BBB and len(thisBook._rawLines) > 5: # Save the previous book
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, verseMilestone )
                                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Saving previous {self.abbreviation+' ' if self.abbreviation else ''}{BBB} book into results…" )
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, mainDivOsisID, "results", BBB, bookResults[:10], "…" )
                                # Remove the last titles
                                #lastBookResult = bookResults.pop()
                                #if lastBookResult[0]!='sectionTitle':
                                    #lastBookResult = None
                                #lastUSFMResult = USFMResults.pop()
                                #if lastUSFMResult[0]!='s':
                                    #lastUSFMResult = None
                                lastLineTuple = thisBook._rawLines.pop()
                                if BibleOrgSysGlobals.debugFlag: assert len(lastLineTuple) == 2
                                if lastLineTuple[0] != 's':
                                    thisBook._rawLines.append( lastLineTuple ) # No good -- put it back
                                    lastLineTuple = None
                                #if bookResults: self.bkData[BBB] = bookResults
                                #if USFMResults: self.USFMBooks[BBB] = USFMResults
                                self.stashBook( thisBook )
                                #bookResults, USFMResults = [], []
                                #if lastBookResult:
                                    #lastBookResultList = list( lastBookResult )
                                    #lastBookResultList[0] = 'mainTitle'
                                    #adjBookResult = tuple( lastBookResultList )
                                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, lastBookResultList )
                                #if lastUSFMResult:
                                    #lastUSFMResultList = list( lastUSFMResult )
                                    #lastUSFMResultList[0] = 'mt1'
                                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, lastUSFMResultList )
                                    #adjSFMResult = tuple( lastUSFMResultList )
                                if lastLineTuple:
                                    thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + f" converted to USFM from OSIS by {PROGRAM_NAME} V{PROGRAM_VERSION}" )
                                    thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
                                    thisBook.addLine( 'mt1', lastLineTuple[1] ) # Change from s to mt1
                                chapterMilestone = verseMilestone = ''
                                foundH = False
                            BBB = cmBBB[0] if isinstance( cmBBB, list) else cmBBB # It can be a list like: ['EZR', 'EZN']
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "23f4 BBB is", BBB )
                            USFMAbbreviation = bos_books_codes_py.bos_book_code_to_usfm_abbrev( BBB )
                            USFMNumber = bos_books_codes_py.bos_book_code_to_usfm_num_str( BBB )
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
                        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "validateChapterElement bookList", len(bookList), [bkLE[0].BBB for bkLE in bookList] )
                        bookList[-1][0].addLine( 'c', bits[1] )

                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "validateChapterElement returning milestone:", chapterMilestone )
                return chapterMilestone

            else: # not a milestone -- it's a chapter container
                bits = OSISChapterID.split('.')
                if BibleOrgSysGlobals.debugFlag: assert len(bits)==2 and bits[1].isdigit()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "validateChapterElement returning data:", 'chapterContainer.' + OSISChapterID )
                return 'chapterContainer.' + OSISChapterID
        # end of OSISXMLBible.validateChapterElement


        def validateSigned( thisBook, element, locationDescription, verseMilestone ):
            """
            """
            location = "validateSigned: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '9i6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'vd62', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'fc3v3', loadErrors )
            signedName = subelement.text
            if BibleOrgSysGlobals.debugFlag and subelement.tail: assert False, "We want to stop here"
            thisBook.appendToLastLine( f'\\sg {clean(signedName)}\\sg*' )
        # end of validateSigned


        def validateLB( thisBook, element, locationDescription, verseMilestone ):
            """
            """
            location = "validateLB: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'cf4g', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '5t3x', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'sn52', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '3c5f', loadErrors )
            thisBook.addLine( 'm', '' )
        # end of OSISXMLBible.validateLB


        def validateLG( thisBook, element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible lg field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateLG at {location} at {verseMilestone}" )
            location = "validateLG: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6v', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'vdj4', loadErrors )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'l':
                    sublocation = "validateLG l of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d56g', loadErrors )
                    lgLevel = None
                    for attrib,value in subelement.items():
                        if attrib=='level':
                            lgLevel = value
                        else:
                            logging.warning( f"2xc4 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                            loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (2xc4)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if not lgLevel: # This is probably an OSIS formatting error
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "LG lgLevel problem", verseMilestone, repr(element.text), subelement.items() )
                        logging.warning( f"No level attribute specified in {sublocation} at {verseMilestone}" )
                        loadErrors.append( f"No level attribute specified in {sublocation} at {verseMilestone}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        lgLevel = '1' # Dunno what we have here ???
                    if BibleOrgSysGlobals.debugFlag: assert lgLevel in ('1','2','3','4')
                    thisBook.addLine( 'q'+lgLevel, '' if subelement.text is None else clean(subelement.text) )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "validateLG: verse of l of " + locationDescription
                            verseMilestone = self.validateVerseElement( thisBook, sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "validateLG: note of l of " + locationDescription
                            self.validateCrossReferenceOrFootnote( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            sub2location = "validateLG: divineName of l of " + locationDescription
                            self.validateDivineName( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "validateLG: hi of l of " + locationDescription
                            self.validateHighlight( thisBook, sub2element, sub2location, verseMilestone, loadErrors ) # Also handles the tail
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                            sub2location = "validateLG: w of l of " + locationDescription
                            self.validateAndLoadWord( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                            #if wordStuff: thisBook.appendToLastLine( wordStuff )
                        else:
                            logging.error( f"4j12 Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                            loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (4j12)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateLG divineName of " + locationDescription
                    self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateLG verse of " + locationDescription
                    verseMilestone = self.validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                else:
                    logging.error( f"q2b6 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (q2b6)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
            if element.tail: # and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                thisBook.addLine( 'm', clean(element.tail) )
            return verseMilestone
        # end of OSISXMLBible.validateLG


        def validateList( thisBook, element, locationDescription, verseMilestone, level=None ):
            """
            Check/validate and process a OSIS Bible list field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateList for {self.name} at {locationDescription} at {verseMilestone}" )
            if level is None: level = 1
            location = "validateList: " + locationDescription

            BibleOrgSysGlobals.checkXMLNoText( element, f"{location} at {verseMilestone}", '2dx3', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, f"{location} at {verseMilestone}", '2c5b', loadErrors )
            canonical = None
            for attrib,value in element.items():
                if attrib== 'canonical':
                    canonical = value
                    assert canonical == 'false'
                else:
                    logging.warning( f"h2f5 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location} (h2f5)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'item':
                    sublocation = "item of " + location
                    itemText = subelement.text
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "itemText", repr(itemText) )
                    if chapterMilestone: marker = 'li' + str(level)
                    else: marker = 'io' + str(level) # No chapter so we're in the introduction
                    if itemText and itemText.strip(): thisBook.addLine( marker, clean(itemText) )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'xf52', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ad36', loadErrors )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "verse of " + sublocation
                            verseMilestone = self.validateVerseElement( thisBook, sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                            #verseTail = sub3element.tail
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "verseTail", repr(verseTail) )
                            #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location+" at "+verseMilestone, 'cvf4', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'sdyg', loadErrors )
                            #osisID = verseSID = verseEID = verseN = None
                            #for attrib,value in sub3element.items():
                                #if attrib=='osisID':
                                    #osisID = value
                                #elif attrib=='sID':
                                    #verseSID = value
                                #elif attrib=='eID':
                                    #verseEID = value
                                #elif attrib=='n':
                                    #verseN = value
                                #else: logging.warning( f"fghb Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub3element.tag} at {sub2location}" )
                            #if osisID: assert verseSID and verseN and not verseEID
                            #elif verseEID: assert not verseSID and not verseN
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "verseStuff", repr(osisID), repr(verseSID), repr(verseN), repr(verseEID) )
                            ##thisBook.addLine( 'r~', referenceText+referenceTail )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "note of " + sublocation
                            self.validateCrossReferenceOrFootnote( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "hi of " + sublocation
                            self.validateHighlight( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                            sub2location = "list of " + sublocation
                            verseMilestone = validateList( thisBook, sub2element, sub2location, verseMilestone, level+1 )
                        else:
                            logging.error( f"f153 Unprocessed {verseMilestone!r} sub3element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                            loadErrors.append( f"Unprocessed {verseMilestone!r} sub3element ({sub2element.tag}) in {sub2element.text} at {sublocation} (f153)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                else:
                    logging.error( f"s154 Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} subelement ({subelement.tag}) in {subelement.text} at {location} (s154)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            return verseMilestone

            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'list', divType, subDivType )
            #BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location+" at "+verseMilestone, '3x6g', loadErrors )
            #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '8j4g' )
            #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '7tgf' )
            #for sub3element in sub2element:
                #if sub3element.tag == OSISXMLBible.OSISNameSpace+'item':
                    #sub3location = "item of " + sub2location
                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '3d8n' )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '4g7g' )
                    #item = sub3element.text
                    #if item and item.strip():
                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, subDivType )
                        #if subDivType == 'outline':
                            #thisBook.addLine( 'io1', item.strip() )
                        #elif subDivType == 'section':
                            #thisBook.addLine( 'io1', item.strip() )
                        #elif BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                    #for sub4element in sub3element:
                        #if sub4element.tag == OSISXMLBible.OSISNameSpace+'list':
                            #sub4location = "list of " + sub3location
                            #BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location+" at "+verseMilestone, '5g3d' )
                            #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '4w5x' )
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location+" at "+verseMilestone, '3d45' )
                            #for sub5element in sub4element:
                                #if sub5element.tag == OSISXMLBible.OSISNameSpace+'item':
                                    #sub5location = "item of " + sub4location
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5location+" at "+verseMilestone, '4c5t' )
                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5location+" at "+verseMilestone, '2sd1' )
                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5location+" at "+verseMilestone, '8j7n' )
                                    #subItem = sub5element.text
                                    #if subItem:
                                        #if subDivType == 'outline':
                                            #thisBook.addLine( 'io2', clean(subItem) )
                                        #elif subDivType == 'section':
                                            #thisBook.addLine( 'io2', clean(subItem) )
                                        #elif BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, subDivType ); assert False, "We want to stop here"
                                #else: logging.error( f"3kt6 Unprocessed {verseMilestone!r} sub5element ({sub5element.tag}) in {sub5element.text} at {sub4location}" )
                        #elif sub4element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            #sub4location = "list of " + sub3location
                            #self.validateVerseElement( thisBook, sub4element, verseMilestone, chapterMilestone, sub4location )
                        #else: logging.error( f"2h4s Unprocessed {verseMilestone!r} sub4element ({sub4element.tag}) in {sub4element.text} at {sub3location}" )
                #else: logging.error( f"8k4j Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location}" )
        # end of OSISXMLBible.validateList


        def validateMilestone( thisBook, subelement, location, verseMilestone ):
            """
            """
            sublocation = "milestone of " + location
            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'f9s5', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'q9v5', loadErrors )
            milestoneType = milestoneMarker = milestoneSubtype = milestoneResp = None
            for attrib,value in subelement.items():
                if attrib=='type': milestoneType = value
                elif attrib=='marker': milestoneMarker = value
                elif attrib=='subType': milestoneSubtype = value
                elif attrib=='resp': milestoneResp = value
                else:
                    logging.warning( f"8h6k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (8h6k)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here bd63", repr(milestoneType) )
            if BibleOrgSysGlobals.debugFlag:
                assert milestoneType in ('x-p','x-extra-p','x-strongsMarkup')
                assert milestoneMarker in (None,'¶') # What are these?
                assert milestoneSubtype in (None,'x-added') # What are these?
            thisBook.addLine( 'p', '' )
            trailingText = subelement.tail
            if trailingText and trailingText.strip(): thisBook.appendToLastLine( clean(trailingText) )
            #return subelement.tail if subelement.tail else ''
        # end of validateMilestone


        def validateParagraph( thisBook, element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            nonlocal chapterMilestone
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"validateParagraph at {locationDescription} at {verseMilestone}" )
            location = "validateParagraph: " + locationDescription
            paragraphType = canonical = None
            for attrib,value in element.items():
                if attrib=='type':
                    paragraphType = value
                elif attrib=='canonical':
                    canonical = value
                    assert canonical in ('true','false')
                else:
                    logging.warning( f"6g3f Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} element of {element.tag} at {location} (6g3f)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            paragraphCode = None
            if paragraphType:
                if BibleOrgSysGlobals.debugFlag:
                    assert paragraphType.startswith( 'x-')
                    if paragraphType not in  ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr'): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, paragraphType )
                    if DEBUGGING_THIS_MODULE:
                        assert paragraphType in ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr')
                paragraphCode = paragraphType[2:]
            justFinishedLG = False
            if not element.text: # A new paragraph starting
                pContents = None
            else: # A new paragraph in the middle of a verse, e.g., James 3:5b
                pContents = clean( element.text )
                #if pContents.isspace(): pContents = None # Ignore newlines and blank lines in the xml file
            if paragraphCode in USFM_BIBLE_PARAGRAPH_MARKERS:
                thisBook.addLine( paragraphCode, '' if pContents is None else pContents )
            elif chapterMilestone:
                thisBook.addLine( 'p', '' if pContents is None else pContents )
            else: # Must be in the introduction
                thisBook.addLine( 'ip', '' if pContents is None else pContents )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'chapter': # A chapter break within a paragraph (relatively rare)
                    sublocation = "validateParagraph: chapter of " + locationDescription
                    chapterMilestone = validateChapterElement( bookList, subelement, chapterMilestone, verseMilestone, sublocation )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateParagraph: verse of " + locationDescription
                    if justFinishedLG: # Have a verse straight after a LG (without an intervening p)
                        thisBook.addLine( 'm', '' )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Added m" )
                    verseMilestone = self.validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateParagraph: note of " + locationDescription
                    self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                    sublocation = "validateParagraph: lg of " + locationDescription
                    verseMilestone = validateLG( thisBook, subelement, sublocation, verseMilestone )
                    #if 0:
                        #BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '3ch6', loadErrors )
                        ##lgText = subelement.text
                        #lgTail = subelement.tail
                        #for attrib,value in subelement.items():
                            #if attrib=='type':
                                #assert False, "We want to stop here"
                            #elif attrib=='n':
                                #assert False, "We want to stop here"
                            #elif attrib=='osisRef':
                                #assert False, "We want to stop here"
                            #elif attrib=='osisID':
                                #assert False, "We want to stop here"
                            #else:
                                #logging.warning( f"1s5g Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation}" )
                                #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {subelement.tag} at {sublocation} (1s5g)" )
                        #for sub2element in subelement:
                            #if sub2element.tag == OSISXMLBible.OSISNameSpace+'l':
                                #sub2location = "l of " + sublocation
                                #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4vw3', loadErrors )
                                #lText = sub2element.text
                                #level3 = None
                                #for attrib,value in sub2element.items():
                                    #if attrib=='level':
                                        #level3 = value
                                    #else:
                                        #logging.warning( f"9d3k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {sub2element.tag} at {sub2location}" )
                                        #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub-element of {sub2element.tag} at {sub2location} (9d3k)" )
                                #if not level3:
                                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "level3 problem", verseMilestone, lText, sub2element.items() )
                                    #logging.warning( f"validateParagraph: No level attribute specified in {sub2location} at {verseMilestone}" )
                                    #loadErrors.append( f"validateParagraph: No level attribute specified in {sub2location} at {verseMilestone}" )
                                    #level3 = '1' # Dunno what we have here ???
                                #if BibleOrgSysGlobals.debugFlag: assert level3 in ('1','2','3')
                                #thisBook.addLine( 'q'+level3, lText )
                                #for sub3element in sub2element:
                                    #if sub3element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                        #sub3location = "verse of " + sub2location
                                        #verseMilestone = validateVerseElement( thisBook, sub3element, verseMilestone, chapterMilestone, sub3location )
                                    #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        #sub3location = "note of " + sub2location
                                        #self.validateCrossReferenceOrFootnote( thisBook, sub3element, sub3location, verseMilestone, loadErrors )
                                        #noteTail = sub3element.tail
                                        #if noteTail: # This is the main text of the verse (follows the inserted note)
                                            #bookResults.append( ('lverse+', noteTail) )
                                            #adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            #if adjNoteTail: USFMResults.append( ('v~',adjNoteTail) )
                                    #else:
                                        #logging.error( f"32df Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location}" )
                                        #loadErrors.append( f"Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location} (32df)" )
                            #else:
                                #logging.error( f"5g1e Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                                #loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (5g1e)" )
                        #if lgTail and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                            #thisBook.addLine( 'm', lgTail )
                    justFinishedLG = True
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                    sublocation = "validateParagraph: reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vbs4', loadErrors )
                    reference = subelement.text
                    theType = None
                    for attrib,value in subelement.items():
                        if attrib=='type':
                            theType = value
                        else:
                            logging.warning( f"4f5f Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {subelement.tag} at {sublocation}" )
                            loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2-element of {subelement.tag} at {sublocation} (4f5f)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if theType:
                        if theType == 'x-bookName':
                            thisBook.appendToLastLine( f'\\bk {clean(reference)}\\bk*' )
                        elif BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, theType ); assert False, "We want to stop here"
                    pTail = subelement.tail
                    if pTail and pTail.strip(): # Just ignore XML spacing characters
                        thisBook.appendToLastLine( clean(pTail) )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateParagraph: hi of " + locationDescription
                    self.validateHighlight( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                    sublocation = "validateParagraph: lb of " + locationDescription
                    validateLB( thisBook, subelement, sublocation, verseMilestone )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                    sublocation = "validateParagraph: w of " + locationDescription
                    self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                    #if wordStuff: thisBook.appendToLastLine( wordStuff )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3s5f', loadErrors )
                    #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'f3v5', loadErrors )
                    #word, trailingPunctuation = subelement.text, subelement.tail
                    #if trailingPunctuation is None: trailingPunctuation = ''
                    #combined = word + trailingPunctuation
                    #thisBook.addLine( 'w~', combined )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'signed':
                    sublocation = "validateParagraph: signed of " + locationDescription
                    validateSigned( thisBook, subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateParagraph: divineName of " + locationDescription
                    self.validateDivineName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                    sublocation = "validateParagraph: name of " + locationDescription
                    validateProperName( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    sublocation = "validateParagraph: seg of " + locationDescription
                    self.validateAndLoadSEG( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                    sublocation = "validateParagraph: transChange of " + locationDescription
                    self.validateTransChange( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                    sublocation = "validateParagraph: foreign of reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'kd02', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'kls2', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ks10', loadErrors )
                    subreferenceText = subelement.text
                    thisBook.appendToLastLine( f'\\tl {clean(subreferenceText)}\\tl*' )
                else:
                    logging.error( f"3kj6 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                    loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (3kj6)" )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            if element.tail and not element.tail.isspace(): # Just ignore XML spacing characters
                thisBook.appendToLastLine( clean(element.tail) )
            return verseMilestone
        # end of OSISXMLBible.validateParagraph


        def validateTable( thisBook, element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible table, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            location = "validateTable: " + locationDescription
            thisBook.addLine( 'tr', ' ' )
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'kd20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'kd21', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'so20', loadErrors )
            tableTail = clean(element.tail, loadErrors, location, verseMilestone )
            if tableTail: thisBook.appendToLastLine( tableTail )
            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
            return verseMilestone
        # end of OSISXMLBible.validateTable



        # Main code for validateAndExtractBookDiv
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading {self.abbreviation+' ' if self.abbreviation else ''}OSIS book div…" )
        self.haveEIDs = False
        self.haveBook = False

        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {mainDivOsisID} {mainDivType}…" )
            elif attrib=='osisID':
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {mainDivOsisID} {mainDivType}…" )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( f"93f5 Unprocessed {value!r} attribute ({attrib}) in main div element" )
                loadErrors.append( f"Unprocessed {value!r} attribute ({attrib}) in main div element (93f5)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( f"Incomplete mainDivType {mainDivType!r} and mainDivOsisID {mainDivOsisID!r} attributes in main div element" )
            loadErrors.append( f"Incomplete mainDivType {mainDivType!r} and mainDivOsisID {mainDivOsisID!r} attributes in main div element" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
        if mainDivType=='book':
            # This is a single book
            if len(mainDivOsisID)>3 and mainDivOsisID[-1] in ('1','2','3') and mainDivOsisID[-2]=='.': # Fix a bug in the Snowfall USFM to OSIS software
                logging.critical( f"Fixing single-book bug in OSIS {mainDivOsisID!r} book ID" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                mainDivOsisID = mainDivOsisID[:-2] # Change 1Kgs.1 to 1Kgs
            try:
                BBB = bos_books_codes_py.osis_book_code_to_bos_book_code( mainDivOsisID )
            except KeyError:
                logging.critical( f"{mainDivOsisID!r} is not a valid OSIS book identifier in mainDiv" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                for tryBBB in ( 'XXA', 'XXB', 'XXC', 'XXD', 'XXE' ):
                    if tryBBB not in self:
                        BBB = tryBBB; break
            if BBB:
                if isinstance( BBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Multiple alternatives for OSIS {BBB!r}: {mainDivOsisID} (Choosing the first one)" )
                    BBB = BBB[0]
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loading {self.abbreviation+' ' if self.abbreviation else ''}{BBB}…" )
                USFMAbbreviation = bos_books_codes_py.bos_book_code_to_usfm_abbrev( BBB )
                USFMNumber = bos_books_codes_py.bos_book_code_to_usfm_num_str( BBB )
                thisBook = BibleBook( self, BBB )
                thisBook.objectNameString = 'OSIS XML Bible Book object'
                thisBook.objectTypeString = 'OSIS'
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Appending {thisBook.BBB} and {len(loadErrors)} load errors to bookList" )
                for bkLE in bookList:
                    assert len(bkLE) == 2 # bookObject and loadErrors
                    assert bkLE[0].BBB != BBB, f"OSIS loader stopped at duplicate {BBB} book"
                bookList.append( (thisBook,loadErrors.copy()) )
                loadErrors.clear()
                haveBook = True
            thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + f" converted to USFM from OSIS by {PROGRAM_NAME} V{PROGRAM_VERSION}" )
            thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
        #elif mainDivType=='bookGroup':
            ## This is all the books lumped in together into one big div
            #if BibleOrgSysGlobals.debugFlag: assert mainDivCanonical == 'true'
            ## We have to set BBB when we get a chapter reference
            #dPrint( 'Info', DEBUGGING_THIS_MODULE, "  Loading a book group…" )
            #self.haveBook = False
        else:
            logging.critical( f"What kind of OSIS book div is this? {repr(mainDivType)} {repr(mainDivOsisID)} {repr(mainDivCanonical)}" )
            loadErrors.append( f"What kind of OSIS book div is this? {repr(mainDivType)} {repr(mainDivOsisID)} {repr(mainDivCanonical)}" )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"

        chapterMilestone = verseMilestone = ''
        foundH = False
        for element in div:
########### Title -- could be a book title or (in some OSIS files) a section title (with no way to tell the difference)
#               or even worse still (in the Karen), an alternate chapter number
            if element.tag == OSISXMLBible.OSISNameSpace+'title':
                location = f"title of {mainDivType} div"
                self.validateTitle( thisBook, element, location, chapterMilestone, verseMilestone, loadErrors )
########### Div (of the main div) -- most stuff would be expected to be inside a section div inside the book div
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = f"div of {mainDivType} div"
                #if verseMilestone is None: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, location, chapterMilestone ); assert False, "We want to stop here"
                BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6h', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '0j6h', loadErrors )
                # Process the attributes
                divType = divCanonical = divScope = osisID = None
                for attrib,value in element.items():
                    if attrib==OSISXMLBible.XMLNameSpace+'space':
                        divSpace = value
                    elif attrib=='type':
                        divType = value
                        location = value + ' ' + location
                    elif attrib=='canonical':
                        divCanonical = value
                        #assert divCanonical == 'false'
                    elif attrib=='scope': divScope = value
                    elif attrib=='osisID': osisID = value # Unused, e.g., "Rom.c" colophon div in OS KJV
                    else:
                        logging.warning( f"2h56 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location} (2h56)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location} (2h56)" )
                            assert False, "We want to stop here"
                # Now process the subelements
                for subelement in element:
###                 ### chapter in div
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'chapter':
                        sublocation = "chapter of " + location
                        chapterMilestone = validateChapterElement( bookList, subelement, chapterMilestone, verseMilestone, sublocation )
###                 ### verse in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = self.validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
###                 ### title in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                        sublocation = "title of " + location
                        self.validateTitle( thisBook, subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d4f', loadErrors )
                            #sectionHeading = subelement.text
                            #titleType = None
                            #for attrib,value in subelement.items():
                                #if attrib=='type':
                                    #titleType = value
                                #else:
                                    #logging.warning( f"4h2x Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                                    #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (4h2x)" )
                            #if chapterMilestone:
                                #bookResults.append( ('title', titleType, sectionHeading) )
                                #USFMResults.append( ('s', sectionHeading) )
                            #else: # Must be in the introduction
                                #bookResults.append( ('title', titleType, sectionHeading) )
                                #USFMResults.append( ('is', sectionHeading) )
                            #for sub2element in subelement:
                                #if sub2element.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                                    #sub2location = "title of " + sublocation
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '3d5g', loadErrors )
                                    #sectionReference = sub2element.text
                                    #sectionReferenceType = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type':
                                            #sectionReferenceType = value
                                        #else:
                                            #logging.warning( f"8h4d Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {sub2element.tag} at {sub2location}" )
                                            #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {sub2element.tag} at {sub2location} (8h4d)" )
                                    #if sectionReference:
                                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, divType, self.subDivType, sectionReferenceType ); assert False, "We want to stop here"
                                        ##assert divType=='section' and self.subDivType in ('outline',) and sectionReferenceType=='parallel'
                                        #if BibleOrgSysGlobals.debugFlag: assert divType=='section' and sectionReferenceType=='parallel'
                                        #thisBook.addLine( 'sr', clean(sectionReference) )
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '3d3d', loadErrors )
                                            #referenceText = sub3element.text
                                            #referenceTail = sub3element.tail
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( f"7k43 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub3element.tag} at {sub2location}" )
                                                    #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub3element.tag} at {sub2location} (7k43)" )
                                            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, referenceText, referenceOsisRef, referenceTail )
                                            #bookResults.append( ('reference',referenceText) )
                                            #USFMResults.append( ('r+',referenceText+referenceTail) )
                                        #else:
                                            #logging.error( f"46g2 Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location}" )
                                            #loadErrors.append( f"Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location} (46g2)" )
###                 ### p in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                        sublocation = "p of " + location
                        verseMilestone = validateParagraph( thisBook, subelement, sublocation, verseMilestone )
###                 ### list in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'list':
                        sublocation = "list of " + location
                        verseMilestone = validateList( thisBook, subelement, sublocation, verseMilestone )
###                 ### lg in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                        sublocation = "lg of " + location
                        verseMilestone = validateLG( thisBook, subelement, sublocation, verseMilestone )
###                 ### div in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'div':
                        sublocation = "div of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2c5bv', loadErrors )
                        subDivType = subDivScope = subDivSpace = canonical = None
                        for attrib,value in subelement.items():
                            if attrib=='type':
                                subDivType = value
                                sublocation = value + ' ' + sublocation
                            elif attrib=='scope':
                                subDivScope = value # Should be an OSIS verse range
                            elif attrib=='canonical':
                                canonical = value
                                assert canonical in ('true','false')
                            elif attrib==self.XMLNameSpace+"space":
                                subDivSpace = value
                                if BibleOrgSysGlobals.debugFlag: assert subDivSpace == 'preserve'
                            else:
                                logging.warning( f"84kf Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                                loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (84kf)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "self.subDivType", self.subDivType )
                        for sub2element in subelement:
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'title':
                                sub2location = "title of " + sublocation
                                self.validateTitle( thisBook, sub2element, sub2location, chapterMilestone, verseMilestone, loadErrors )
                                #if 0:
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4v5g', loadErrors )
                                    #titleText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                                    #titleType = titleSubType = titleCanonicalFlag = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type': titleType = value
                                        #elif attrib=='subType': titleSubType = value
                                        #elif attrib=='canonical': titleCanonicalFlag = value
                                        #else:
                                            #logging.warning( f"1d4r Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {sub2element.tag} at {sub2location}" )
                                            #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub2element of {sub2element.tag} at {sub2location} (1d4r)" )
                                    #if titleType: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "titleType", titleType )
                                    #if BibleOrgSysGlobals.debugFlag:
                                        #if titleType: assert titleType in ('psalm','parallel','sub')
                                        #if titleSubType: assert titleSubType == 'x-preverse'
                                    #if titleText:
                                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, divType, subDivType )
                                        #if titleCanonicalFlag=='true' and titleType=='psalm':
                                            #thisBook.addLine( 'd', titleText )
                                        #elif divType=='introduction' and subDivType in ('section','outline'):
                                            #thisBook.addLine( 'iot' if subDivType == 'outline' else 'is', titleText )
                                        #elif divType=='majorSection' and subDivType=='section':
                                            #thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 's1', titleText )
                                        #elif divType=='majorSection' and subDivType=='subSection':
                                            #thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 'ms1', titleText )
                                        #elif divType=='section' and subDivType=='subSection':
                                            #thisBook.addLine( 'xxxx3' if subDivType == 'outline' else 's', titleText )
                                        #elif divType=='section' and subDivType=='outline':
                                            #thisBook.addLine( 'iot', titleText )
                                        #else:
                                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "What title?", divType, subDivType, repr(titleText), titleType, titleSubType, titleCanonicalFlag, verseMilestone )
                                            #if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'k6l3', loadErrors )
                                            #referenceText = clean( sub3element.text, loadErrors, sub3location, verseMilestone )
                                            #referenceTail = clean( sub3element.tail, loadErrors, sub3location, verseMilestone )
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( f"nm46 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub3element.tag} at {sub2location}" )
                                                    #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} sub3element of {sub3element.tag} at {sub2location} (nm46)" )
                                            #logging.error( f'Unused {referenceText!r} reference field at {sublocation+" at "+verseMilestone}' )
                                            #loadErrors.append( f'Unused {referenceText!r} reference field at {sublocation+" at "+verseMilestone}' )
                                            #if BibleOrgSysGlobals.debugFlag:
                                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "What's this?", referenceText, referenceOsisRef, referenceTail )
                                                #if DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                            #sub3location = "note of " + sub2location
                                            #self.validateCrossReferenceOrFootnote( thisBook, sub3element, sub3location, verseMilestone, loadErrors )
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                            #sub3location = "hi of " + sub2location
                                            #self.validateHighlight( thisBook, sub3element, sub3location, verseMilestone, loadErrors ) # Also handles the tail
                                        #else:
                                            #logging.error( f"m4g5 Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location}" )
                                            #loadErrors.append( f"Unprocessed {verseMilestone!r} sub3element ({sub3element.tag}) in {sub3element.text} at {sub2location} (m4g5)" )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'p':
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( thisBook, sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lg':
                                sub2location = "lg of " + sublocation
                                verseMilestone = validateLG( thisBook, sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                                sub2location = "list of " + sublocation
                                verseMilestone = validateList( thisBook, sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'chapter':
                                sub2location = "chapter of " + sublocation
                                chapterMilestone = validateChapterElement( bookList, sub2element, chapterMilestone, verseMilestone, sub2location )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                sub2location = "verse of " + sublocation
                                verseMilestone = self.validateVerseElement( thisBook, sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                sub2location = "hi of " + sublocation
                                self.validateHighlight( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lb':
                                sub2location = "lb of " + sublocation
                                validateLB( thisBook, sub2element, sub2location, verseMilestone )
                            else:
                                logging.error( f"14k5 Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                                loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (14k5)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
###                 ### lb in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                        sublocation = "lb of " + location
                        validateLB( thisBook, subelement, sublocation, verseMilestone )
###                 ### closer in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'closer':
                        sublocation = "closer of " + location
                        clsText = clean(subelement.text, loadErrors, sublocation, verseMilestone )
                        clsTail = clean(subelement.tail, loadErrors, sublocation, verseMilestone )
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation+" at "+verseMilestone, 'js29', loadErrors )
                        thisBook.appendToLastLine( f'\\cls {clsText}' )
                        for sub2element in subelement:
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'p':
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( thisBook, sub2element, sub2location, verseMilestone )
                            else:
                                logging.error( f"dc63 Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                                loadErrors.append( f"Unprocessed {verseMilestone!r} sub2element ({sub2element.tag}) in {sub2element.text} at {sublocation} (dc63)" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                        thisBook.appendToLastLine( f'\\cls*{clsTail if clsTail else ""}' )
###                 ### table in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'table': # not actually written yet! XXXXXXX ……
                        sublocation = 'table of ' + location
                        verseMilestone = validateTable( thisBook, subelement, sublocation, verseMilestone )
###                 ### w in colophon div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                        sublocation = 'w of ' + location
                        self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        sublocation = 'transChange of ' + location
                        self.validateTransChange( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'milestone':
                        sublocation = 'milestone of ' + location
                        validateMilestone( thisBook, subelement, sublocation, verseMilestone )
                    else:
                        logging.error( f"3f67 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (3f67)" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
########### P
            elif element.tag == OSISXMLBible.OSISNameSpace+'p':
                location = f"p of {mainDivType} div"
                verseMilestone = validateParagraph( thisBook, element, location, verseMilestone )
########### Q
            elif element.tag == OSISXMLBible.OSISNameSpace+'q':
                location = f"q of {mainDivType} div"
                qText = element.text
                qTail = element.tail
                # Process the attributes
                sID = eID = level = marker = None
                for attrib,value in element.items():
                    if attrib=='sID': sID = value
                    elif attrib=='eID': eID = value
                    elif attrib=='level': level = value
                    elif attrib=='marker':
                        marker = value
                        if BibleOrgSysGlobals.debugFlag: assert len(marker) == 1
                    else:
                        logging.warning( f"6j33 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {location}" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = self.validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        sublocation = "transChange of " + location
                        self.validateTransChange( thisBook, subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                        sublocation = "note of " + location
                        self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                        sublocation = "w of " + location
                        self.validateAndLoadWord( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '8h4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '2k3m', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2s7z', loadErrors )
                        p = element.text
                        if p == '¶':
                            #bookResults.append( ('paragraph', None) )
                            #bookResults.append( ('p', None) )
                            thisBook.addLine( 'p', '' )

                        else:
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"p = {element.text!r}" ); assert False, "We want to stop here"
                            #bookResults.append( ('paragraph', p) )
                            #bookResults.append( ('p', p) )
                            thisBook.addLine( 'p', p )
                    else:
                        logging.error( f"95k3 Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location}" )
                        loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({subelement.tag}) in {subelement.text} at {location} (95k3)" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, subelement.tag )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
########### Chapter
            elif element.tag == OSISXMLBible.OSISNameSpace+'chapter' or (not BibleOrgSysGlobals.strictCheckingFlag and element.tag=='chapter'):
                location = f"chapter of {mainDivType} div"
                chapterMilestone = validateChapterElement( bookList, element, chapterMilestone, verseMilestone, location )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "BBB is", BBB )
                if chapterMilestone and mainDivType=='bookGroup':
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "cm", chapterMilestone )
                    OSISBookID = chapterMilestone.split('.')[0]
                    try:
                        newBBB = bos_books_codes_py.osis_book_code_to_bos_book_code( OSISBookID )
                    except KeyError:
                        logging.critical( f"{OSISBookID!r} is not a valid OSIS book identifier" )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                    if newBBB and isinstance( newBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Multiple alternatives for OSIS {newBBB!r}: {mainDivOsisID} (Choosing the first one)" )
                        newBBB = newBBB[0]
                    if newBBB != BBB:
                        BBB = newBBB
                        USFMAbbreviation = bos_books_codes_py.bos_book_code_to_usfm_abbrev( BBB )
                        USFMNumber = bos_books_codes_py.bos_book_code_to_usfm_num_str( BBB )
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loading {self.abbreviation+' ' if self.abbreviation else ''}{BBB}…" )
                if chapterMilestone.startswith('chapterContainer.'): # it must have been a container -- process the subelements
                    OSISChapterID = chapterMilestone[17:] # Remove the 'chapterContainer.' prefix
                    chapterBits = OSISChapterID.split( '.' )
                    if BibleOrgSysGlobals.debugFlag: assert len(chapterBits) == 2
                    if BibleOrgSysGlobals.debugFlag: assert chapterBits[1].isdigit()
                    thisBook.addLine( 'c', chapterBits[1] )
                    #sentence = ""
                    #thisBook.addLine( 'v~', '' ) # Start our line
                    for subelement in element:
                        if subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                            #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = 'p of ' + location
                            verseMilestone = validateParagraph( thisBook, subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                            #if sentence: thisBook.appendToLastLine( sentence ); sentence = ''
                            sublocation = 'title of ' + location
                            self.validateTitle( thisBook, subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                            self.validateAndLoadWord( thisBook, subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                            self.validateTransChange( thisBook, subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            self.validateDivineName( thisBook, subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'milestone':
                            #if sentence: thisBook.appendToLastLine( sentence ); sentence = ''
                            validateMilestone( thisBook, subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'q':
                            sublocation = 'q of ' + location
                            #words = ""
                            #if subelement.text: words += subelement.text
                            trailingPunctuation = subelement.tail if subelement.tail else ''
                            # Process the attributes
                            qWho = qMarker = None
                            for attrib,value in subelement.items():
                                if attrib=='who': qWho = value
                                elif attrib=='marker': qMarker = value
                                else:
                                    logging.warning( f"zq1k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation}" )
                                    loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sublocation} (zq1k)" )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'who', repr(qWho), 'marker', repr(qMarker) )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    self.validateAndLoadWord( thisBook, sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                                    self.validateTransChange( thisBook, sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                                    self.validateDivineName( thisBook, sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'milestone':
                                    #sentence += words
                                    #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                                    validateMilestone( thisBook, sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                    #sentence += words
                                    #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "verse of " + sublocation
                                    verseMilestone = self.validateVerseElement( thisBook, sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                    #sentence += words
                                    #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "note of " + sublocation
                                    self.validateCrossReferenceOrFootnote( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                                else:
                                    logging.error( f"d33s Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                                    loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation} (d33s)" )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                            if 0 and qWho=="Jesus": sentence += f"\\wj {words}\\wj*{trailingPunctuation}"
                            else:
                                logging.info( f"qWho of {repr(qWho)} unused" )
                                #sentence += words + trailingPunctuation
                            thisBook.addLine( 'q1', '' )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                            #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "note of " + location
                            self.validateCrossReferenceOrFootnote( thisBook, subelement, sublocation, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'inscription':
                            #inscription = ""
                            sublocation = "inscription of " + location
                            thisBook.appendToLastLine( '\\sc ' )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'r9s5', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'r9v5', loadErrors )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    self.validateAndLoadWord( thisBook, sub2element, sublocation, verseMilestone, loadErrors )
                                else:
                                    logging.error( f"4k3s Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation}" )
                                    loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({sub2element.tag}) in {sub2element.text} at {sublocation} (4k3s)" )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                            thisBook.appendToLastLine( f"\\sc*{clean(subelement.tail)}" )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Here 3c52", repr(sentence) )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse' or (not BibleOrgSysGlobals.strictCheckingFlag and subelement.tag=='verse'):
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "here cx35", repr(sentence) )
                            #if sentence: thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "verse of " + location
                            verseMilestone = self.validateVerseElement( thisBook, subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'vM', verseMilestone ); assert False, "We want to stop here"
                            if verseMilestone and verseMilestone.startswith('verseContainer.'): # it must have been a container -- process the subelements
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Yikes!" ) # Why??????????????
                                thisBook.addLine( 'v', verseMilestone[15:]+' ' ) # Remove the 'verseContainer.' prefix
                                for sub2element in subelement:
                                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                        sub2location = "w of " + sublocation
                                        self.validateAndLoadWord( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '2k3c', loadErrors )
                                        #word = sub2element.text
                                        #if BibleOrgSysGlobals.debugFlag: assert word # That should be the actual word
                                        ## Process the attributes
                                        #lemma = morph = n = None
                                        #for attrib,value in sub2element.items():
                                            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Attribute w1 {attrib}={value!r}" )
                                            #if attrib=='lemma': lemma = value # e.g., '7679'
                                            #elif attrib=='morph': morph = value
                                            #elif attrib=='n': n = value # e.g. '1.1'
                                            #else:
                                                #logging.warning( f"2h54 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub2location}" )
                                                #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub2location} (2h54)" )
                                                #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "wlm", word, lemma, morph )
                                        #thisBook.appendToLastLine( f"{word} [{lemma}]" )
                                        ## Now process the subelements
                                        #segText = segTail = segType = None
                                        #for sub3element in sub2element:
                                            #if sub3element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                #sub3location = "seg of " + sub2location
                                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '43gx', loadErrors )
                                                #segText, segTail = sub3element.text, sub3element.tail # XXXxxxxxxxxxxxxxx unused …
                                                ## Process the attributes
                                                #segType = None
                                                #for attrib,value in sub3element.items():
                                                    #if attrib=='type': segType = value
                                                    #else:
                                                        #logging.warning( f"963k Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub3location}" )
                                                        #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub3location} (963k)" )
                                                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
                                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "segTTT", segText, segTail, segType )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                        sub2location = "seg of " + sublocation
                                        self.validateAndLoadSEG( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '9s8v', loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '93dr', loadErrors )
                                        #seg = sub2element.text
                                        #if BibleOrgSysGlobals.debugFlag: assert seg # That should be the actual segment character
                                        ## Process the attributes first
                                        #for attrib,value in sub2element.items():
                                            #if attrib=='type':
                                                #segType = value
                                            #else:
                                                #logging.warning( f"5jj2 Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub2location}" )
                                                #loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub2location} (5jj2)" )
                                        #thisBook.addLine( 'segment', f"{seg} [{segType}]" )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        sub2location = "note of " + sublocation
                                        self.validateCrossReferenceOrFootnote( thisBook, sub2element, sub2location, verseMilestone, loadErrors )
                                        #if 0:
                                            #noteTail = sub2element.tail
                                            #if noteTail: # This is the main text of the verse (follows the inserted note)
                                                #thisBook.appendToLastLine( clean(noteTail) )
                                            ## Now process the subelements
                                            #for sub3element in sub2element:
                                                #if sub3element.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                                                    #sub3location = "catchword of " + sub2location
                                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '3d2a', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '0o9i', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '9k8j', loadErrors )
                                                    #catchWord = sub3element.text
                                                #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'rdg':
                                                    #sub3location = "rdg of " + sub2location
                                                    #self.validateRDG( thisBook, sub3element, sub3location, verseMilestone, loadErrors ) # Also handles the tail
                                                    ##if 0:
                                                        ##BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '8h7g', loadErrors )
                                                        ##rdg = sub3element.text
                                                        ### Process the attributes
                                                        ##rdgType = None
                                                        ##for attrib,value in sub3element.items():
                                                            ##if attrib=='type': rdgType = value
                                                            ##else:
                                                                ##logging.warning( f"3hgh Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub3location}" )
                                                                ##loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub3location} (3hgh)" )
                                                        ### Now process the subelements
                                                        ##for sub4element in sub3element:
                                                            ##if sub4element.tag == OSISXMLBible.OSISNameSpace+'w':
                                                                ##sub4location = "w of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '6g5d', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '5r4d', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##lemma = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=='lemma': lemma = value
                                                                    ##else:
                                                                        ##logging.warning( f"85kd Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub4location}" )
                                                                        ##loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub4location} (85kd)" )
                                                            ##elif sub4element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                                ##sub4location = "seg of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '5r4q', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '4s3a', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##segType = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=='type': segType = value
                                                                    ##else:
                                                                        ##logging.warning( f"9r5j Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub4location}" )
                                                                        ##loadErrors.append( f"Unprocessed {verseMilestone!r} attribute ({attrib}) in {value} at {sub4location} (9r5j)" )
                                                            ##else:
                                                                ##logging.error( f"7k3s Unprocessed {verseMilestone!r} sub-element ({sub4element.tag}) in {sub4element.text} at {sub3location}" )
                                                                ##loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({sub4element.tag}) in {sub4element.text} at {sub3location} (7k3s)" )
                                                                ##if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                                                #else:
                                                    #logging.error( f"9y5g Unprocessed {verseMilestone!r} sub-element ({sub3element.tag}) in {sub3element.text} at {sub2location}" )
                                                    #loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({sub3element.tag}) in {sub3element.text} at {sub2location} (9y5g)" )
                                                    #if BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                                    else:
                                        logging.error( f"05kq Unprocessed {sub2element.tag!r} sub-element {repr(sub2element.text)} in {sublocation} at {verseMilestone}" )
                                        loadErrors.append( f"Unprocessed {sub2element.tag!r} sub-element {repr(sub2element.text)} in {sublocation} at {verseMilestone} (05kq)" )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
                            elif verseMilestone and verseMilestone.startswith('verseContents#'): # it must have been a container -- process the string
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "verseContents", verseMilestone )
                                bits = verseMilestone.split( '#', 2 )
                                if BibleOrgSysGlobals.debugFlag: assert len(bits) == 3
                                if BibleOrgSysGlobals.debugFlag: assert bits[0] == 'verseContents'
                                if BibleOrgSysGlobals.debugFlag: assert bits[1].isdigit()
                                if BibleOrgSysGlobals.debugFlag: assert bits[2]
                                thisData = bits[1]
                                if bits[2].strip(): thisData += ' ' + bits[2].replace('\n','')
                                #assert bits[2].strip()
                                thisBook.addLine( 'v', thisData )
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, USFMResults[-4:] )
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'CHOCOLATE', thisBook._rawLines[-4:] )
                        else:
                            logging.error( f"4s9j Unprocessed {subelement.tag!r} sub-element {repr(subelement.text)} in {location} at {verseMilestone}" )
                            loadErrors.append( f"Unprocessed {subelement.tag!r} sub-element {repr(subelement.text)} in {location} at {verseMilestone} (4s9j)" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert False, "We want to stop here"
########### Verse
            elif element.tag == OSISXMLBible.OSISNameSpace+'verse': # Some OSIS Bibles have verse milestones directly in a bookgroup div
                location = f"verse of {mainDivType} div"
                verseMilestone = self.validateVerseElement( thisBook, element, verseMilestone, chapterMilestone, location, loadErrors )
########### Lg
            elif element.tag == OSISXMLBible.OSISNameSpace+'lg':
                location = f"lg of {mainDivType} div"
                verseMilestone = validateLG( thisBook, element, location, verseMilestone )
########### TransChange
            elif element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                location = f"transChange of {mainDivType} div"
                self.validateTransChange( thisBook, element, location, verseMilestone, loadErrors )
########### Note
            elif element.tag == OSISXMLBible.OSISNameSpace+'note':
                location = f"note of {mainDivType} div"
                self.validateCrossReferenceOrFootnote( thisBook, element, location, verseMilestone, loadErrors )
########### LB
            elif element.tag == OSISXMLBible.OSISNameSpace+'lb':
                location = f"lb of {mainDivType} div"
                validateLB( thisBook, element, location, verseMilestone )
########### List
            elif element.tag == OSISXMLBible.OSISNameSpace+'list':
                location = f"list of {mainDivType} div"
                verseMilestone = validateList( thisBook, element, location, verseMilestone )
########### Table
            elif element.tag == OSISXMLBible.OSISNameSpace+'table':
                location = f"table of {mainDivType} div"
                verseMilestone = validateTable( thisBook, element, location, verseMilestone )
########### W
            elif element.tag == OSISXMLBible.OSISNameSpace+'w':
                location = f"w of {mainDivType} div"
                self.validateAndLoadWord( thisBook, element, location, verseMilestone, loadErrors )
########### Left-overs!
            else:
                logging.critical( f"5ks1 Unprocessed {verseMilestone!r} sub-element ({element.tag}) in {element.text} div at {mainDivType}" )
                loadErrors.append( f"Unprocessed {verseMilestone!r} sub-element ({element.tag}) in {element.text} div at {mainDivType} (5ks1)" )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: assert False, "We want to stop here"
            #if element.tail is not None and element.tail.strip(): logging.error( f"Unexpected left-over {verseMilestone!r} tail data after {element.tail} element in {element.tag} div at {mainDivType}" )

        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Done Validating", BBB, mainDivOsisID, mainDivType )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bookResults", bookResults )
        if BBB:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Saving {self.abbreviation+' ' if self.abbreviation else ''}{BBB} book into results…" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, mainDivOsisID, "results", BBB, bookResults[:10], "…" )
            #if bookResults: self.bkData[BBB] = bookResults
            #if USFMResults: self.USFMBooks[BBB] = USFMResults
            # self.stashBook( thisBook )
            # Should be already there I think
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Appending {thisBook.BBB} and {len(loadErrors)} load errors to bookList" )
            found = False
            for bkLE in bookList:
                assert len(bkLE) == 2 # bookObject and loadErrors
                if bkLE[0].BBB == BBB: found = True; break
            assert found # book should already be in list
            # bookList.append( (thisBook,loadErrors.copy()) )
            loadErrors.clear() # Ready for next book
    # end of OSISXMLBible.validateAndExtractBookDiv
# end of OSISXMLBible class


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for standardTestFolder in (
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                        ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nStandard testfolder is: {standardTestFolder}" )
            result1 = OSISXMLBibleFileCheck( standardTestFolder )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA1", result1 )
            result2 = OSISXMLBibleFileCheck( standardTestFolder, autoLoad=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA2", result2 )
            result3 = OSISXMLBibleFileCheck( standardTestFolder, autoLoadBooks=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA3", result3 )


    BiblesFolderpath = Path( '/srv/Bibles/' )
    if 1: # Test OSISXMLBible object
        testFilepaths = (
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), # Matigsalug test sample
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the OSIS Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths, start=1 ): # Choose testFilepaths or justOne
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nB/ OSIS {j}/ Demonstrating the OSIS Bible class…" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test filepath is {testFilepath!r}" )
            oB = OSISXMLBible( testFilepath ) # Load and process the XML
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
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "OSISXMLBible.demo:", svk, oB.getVerseText( svk ) )
                        except KeyError:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"OSISXMLBible.demo: {b} {c}:{v} can't be found!" )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineArguments.export:
                #oB.toODF(); assert False, "We want to stop here"
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            break
# end of OSISXMLBible.briefDemo

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
                        Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                        'MadeUpFolder/',
                        ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nStandard testfolder is: {standardTestFolder}" )
            result1 = OSISXMLBibleFileCheck( standardTestFolder )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA1", result1 )
            result2 = OSISXMLBibleFileCheck( standardTestFolder, autoLoad=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA2", result2 )
            result3 = OSISXMLBibleFileCheck( standardTestFolder, autoLoadBooks=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "OSIS TestA3", result3 )


    BiblesFolderpath = Path( '/srv/Bibles/' )
    if 1: # Test OSISXMLBible object
        testFilepaths = (
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), # Matigsalug test sample
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ), # Full KJV from Crosswire
            BiblesFolderpath.joinpath( 'Original languages/SBLGNT/sblgnt.osis/SBLGNT.osis.xml' ),
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', 'Ruth.xml' ), # Hebrew Ruth
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', 'Dan.xml' ), # Hebrew Daniel
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/' ), # Hebrew Bible
            BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'wlc/', '1Sam.xml' ), # Hebrew 1 Samuel
            BiblesFolderpath.joinpath( 'Formats/OSIS/Crosswire USFM-to-OSIS (Perl)/Matigsalug.osis.xml' ), # Entire Bible in one file 4.4MB
            '../../MatigsalugOSIS/OSIS-Output/MBTGEN.xml',
            '../../MatigsalugOSIS/OSIS-Output/MBTRUT.xml', # Single books
            '../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/OSIS-Output/MBTMRK.xml', '../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/OSIS-Output/MBT2PE.xml', # Single book
            '../../MatigsalugOSIS/OSIS-Output', # Entire folder of single books
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the OSIS Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths, start=1 ): # Choose testFilepaths or justOne
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nB/ OSIS {j}/ Demonstrating the OSIS Bible class…" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test filepath is {testFilepath!r}" )
            oB = OSISXMLBible( testFilepath ) # Load and process the XML
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
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "OSISXMLBible.demo:", svk, oB.getVerseText( svk ) )
                        except KeyError:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"OSISXMLBible.demo: {b} {c}:{v} can't be found!" )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineArguments.export:
                #oB.toODF(); assert False, "We want to stop here"
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
# end of OSISXMLBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of OSISXMLBible.py
