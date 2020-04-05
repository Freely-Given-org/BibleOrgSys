#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GoBible.py
#
# Module handling (Java) Go Bible files (intended for feature phones)
#
# Copyright (C) 2019 Robert Hunt
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
#   MERCHANGoBibleILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module reading and loading binary Go Bible files.

See https://github.com/xkjyeah/gobible-creator
and https://github.com/DavidHaslam/GoBibleCore.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-05-14' # by RJH
SHORT_PROGRAM_NAME = "GoBible"
PROGRAM_NAME = "Go Bible format handler"
PROGRAM_VERSION = '0.04'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, struct
import multiprocessing
import tempfile, zipfile
from shutil import rmtree

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


GOBIBLE_FILENAME_END = '.jar'


def GoBibleFileCheck( givenPathname, strictCheck=True, autoLoad=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for GoBible files or folders in the folder and in the next level down.
    Or if given a zip filename, check that.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one GoBible is found,
        returns the loaded GoBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "GoBibleFileCheck( {}, {}, {}, {} )".format( givenPathname, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenPathname and isinstance( givenPathname, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given path is readable
    if not os.access( givenPathname, os.R_OK ):
        logging.critical( _("GoBibleFileCheck: Given {!r} path is unreadable").format( givenPathname ) )
        return False

    if str(givenPathname).endswith( GOBIBLE_FILENAME_END ): # it's a zipped Java object
        if autoLoad or autoLoadBooks:
            gB = GoBible( givenPathname )
            if autoLoad or autoLoadBooks: gB.preload() # Load the BibleInfo file
            if autoLoadBooks: gB.loadBooks() # Load and process the book files
            return gB
        return 1 # Number of Bibles found

    # Must have been given a folder
    givenFolderName = givenPathname
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("GoBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " GoBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            #somethingUpper = something.upper()
            if something.endswith( GOBIBLE_FILENAME_END ):
                foundFiles.append( something )

    # See if there's an GoBible project here in this given folder
    numFound = len( foundFiles )
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("GoBibleFileCheck got {} in {}").format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            foundFilename = foundFiles[0]
            gB = GoBible( os.path.join( givenFolderName, foundFilename ), foundFilename[:-4] )
            if autoLoad or autoLoadBooks: gB.preload() # Load the file
            if autoLoadBooks: gB.loadBooks() # Load and process the book files
            return gB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("GoBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    GoBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                #somethingUpper = something.upper()
                if something.endswith( GOBIBLE_FILENAME_END ):
                    foundSubfiles.append( something )
                    foundProjects.append( os.path.join( tryFolderName, something ) )
                    numFound += 1

    # See if there's an GoBible here in this folder
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("GoBibleFileCheck foundProjects {} {}").format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            gB = GoBible( foundProjects[0] )
            if autoLoad or autoLoadBooks: gB.preload() # Load the file
            if autoLoadBooks: gB.loadBooks() # Load and process the book files
            return gB
        return numFound
# end of GoBibleFileCheck



class GoBible( Bible ):
    """
    Class for reading, validating, and converting GoBible files.
    """
    def __init__( self, sourceFileOrFolder, givenName=None ):
        """
        Constructor: just sets up the Bible object.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            print( f"GoBible.__init__( '{sourceFileOrFolder}', {givenName!r} )" )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Go Bible object'
        self.objectTypeString = 'GoBible'

        # Now we can set our object variables
        self.sourceFileOrFolder, self.givenName = sourceFileOrFolder, givenName
        if sourceFileOrFolder.endswith( GOBIBLE_FILENAME_END ):
            assert os.path.isfile( sourceFileOrFolder )
            self.sourceFilepath = sourceFileOrFolder
            self.sourceFolder = os.path.dirname( sourceFileOrFolder )
        else: # assume it's a folder
            assert os.path.isdir( sourceFileOrFolder )
            self.sourceFolder = sourceFileOrFolder
            self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName+GOBIBLE_FILENAME_END )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("GoBible: File '{}' is unreadable").format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of GoBible.__init__


    def preload( self ):
        """
        Loads the Metadata file if it can be found.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "preload() from {}".format( self.sourceFilepath ) )

        self.unzippedFolderPath = tempfile.mkdtemp( suffix='_GoBible', prefix='BOS_' )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Extracting files into {}…".format( self.unzippedFolderPath ) )
        with zipfile.ZipFile( self.sourceFilepath ) as myzip:
            # NOTE: Could be a security risk here
            myzip.extractall( self.unzippedFolderPath )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.unzippedFolderPath ):
            somepath = os.path.join( self.unzippedFolderPath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "GoBible.preload: Not sure what {!r} is in {}!".format( somepath, self.unzippedFolderPath ) )
        numVitalFolders = 0
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                if folderName in ('Bible Data', 'META-INF'):
                    numVitalFolders += 1
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("GoBible.preload: Surprised to see subfolders in {!r}: {}").format( self.unzippedFolderPath, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "GoBible.preload: Couldn't find any files in {!r}".format( self.unzippedFolderPath ) )
            raise FileNotFoundError # No use continuing
        if not numVitalFolders:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "GoBible.preload: Couldn't find any vital folders in {!r}".format( self.unzippedFolderPath ) )
            raise FileNotFoundError # No use continuing

        self.dataFolderPath = os.path.join( self.unzippedFolderPath, 'Bible Data/' )
        if not os.path.isdir( self.dataFolderPath ):
            logging.critical( _("GoBible.preload: Unable to find folder: {}").format( self.dataFolderPath ) )

        # Do a preliminary check on the contents of our subfolder
        #self.discoveredBookList = []
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.dataFolderPath ):
            somepath = os.path.join( self.dataFolderPath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "GoBible.preload: Not sure what {!r} is in {}!".format( somepath, self.dataFolderPath ) )
        numBookFolders = 0
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                folderNameLower = folderName.lower()
                if folderNameLower.endswith( 'sfm' ): # .sfm or .usfm
                    numBookFolders += 1
                    bookCode = folderName[:-4]
                    # Code below doesn't work -- foldernames vary
                    #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( bookCode )
                    #self.discoveredBookList.append( BBB )
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("GoBible.preload: Surprised to see subfolders in {!r}: {}").format( self.dataFolderPath, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "GoBible.preload: Couldn't find any files in {!r}".format( self.dataFolderPath ) )
            raise FileNotFoundError # No use continuing
        if not numBookFolders:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "GoBible.preload: Couldn't find any book folders in {!r}".format( self.dataFolderPath ) )
            raise FileNotFoundError # No use continuing
        #if debuggingThisModule: print( "GoBible.preload: Discovered", self.discoveredBookList )

        def readInString( fileBytes, fileIndex ):
            """
            Strings have a single byte length, then the UTF-8 characters, then a trailing null.
            """
            stringLength = fileBytes[fileIndex]; fileIndex += 1
            result = ""
            while True:
                nextChar = fileBytes[fileIndex]; fileIndex += 1
                if not nextChar: break # found the trailing null
                result += chr(nextChar)
            assert len(result) == stringLength # Read string correctly
            return result, stringLength+2

        # Load the Index file
        with open( os.path.join( self.dataFolderPath, 'Index' ), 'rb' ) as main_index_file:
            mainIndexContents = main_index_file.read()
        index = 0
        numBooks, = struct.unpack( "<H", mainIndexContents[index:index+2] ); index += 2
        if debuggingThisModule: print( "numBooks", numBooks )

        self.bookNames, self.filenameBases, self.startChapters, self.numChaptersList, self.numVersesList = [], [], [], [], []
        for bookIndex in range( numBooks ):
            #print( "\nbookIndex", bookIndex )

            # Read in the name of the book
            bookName, consumedBytes = readInString( mainIndexContents, index )
            if debuggingThisModule: print( "bookName", repr(bookName) )
            self.bookNames.append( bookName )
            index += consumedBytes

            # Read in the short book name
            filenameBase, consumedBytes = readInString( mainIndexContents, index )
            if debuggingThisModule: print( "filenameBase", repr(filenameBase) )
            self.filenameBases.append( filenameBase )
            index += consumedBytes

            startChapter, = struct.unpack( "<H", mainIndexContents[index:index+2] ); index += 2
            if debuggingThisModule: print( "startChapter", startChapter )
            self.startChapters.append( startChapter )

            # Read in the number of chapters in this book
            numChapters, = struct.unpack( "<H", mainIndexContents[index:index+2] ); index += 2
            if debuggingThisModule: print( "numChapters", numChapters )
            self.numChaptersList.append( numChapters )

            # Read in the file number, verse offset, and number of verses for each chapter
            versesPerChapter = []
            previousFileNumber = 0;
            verseDataOffset = 0;
            for chapterIndex in range( numChapters ):
                # Seems that each entry is six bytes
                if debuggingThisModule: print( chapterIndex, mainIndexContents[index:index+6] )
                if 1:
                    allVersesLength, = struct.unpack( ">I", mainIndexContents[index:index+4] ); index += 4
                    numVerses = mainIndexContents[index]; index += 1
                    # Seems that file number for final chapter is always zero (or missing for the last book)!!!
                    try: fileNumber = mainIndexContents[index]; index += 1
                    except IndexError: fileNumber = 0 # Why??? (will be adjusted just below)

                    # Why do we need this ???
                    if fileNumber == 0 and previousFileNumber > 0:
                        if debuggingThisModule: print( "Don't know why but: Adjusting file number from 0 to", previousFileNumber )
                        fileNumber = previousFileNumber

                    if fileNumber != previousFileNumber:
                        verseDataOffset = 0;
                        previousFileNumber = fileNumber;
                else:
                    fileNumber, = struct.unpack( "<H", mainIndexContents[index:index+2] ); index += 2
                    allVersesLength, = struct.unpack( "<I", mainIndexContents[index:index+4] ); index += 3
                    try:
                        numVerses = mainIndexContents[index]; index += 1
                    except struct.error: numVerses = -1 # Why does it fail for the last chapter of Revelation???

                    if fileNumber != previousFileNumber:
                        verseDataOffset = 0;
                        previousFileNumber = fileNumber;

                versesPerChapter.append( (numVerses, fileNumber, verseDataOffset, allVersesLength) )
                if debuggingThisModule:
                    print( f"Book #{bookIndex+1}   chapter {chapterIndex+1:3}: {fileNumber}, {verseDataOffset:,}, {allVersesLength:,}, {numVerses}" )

                verseDataOffset += allVersesLength
            self.numVersesList.append( versesPerChapter )
        assert index == len(mainIndexContents)

        self.BibleOrgSystem = BibleOrganisationalSystem( 'GENERIC-KJV-66' )
        if numBooks == 66:
            self.bookList = [BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber(x) for x in range(1,66+1)]
        elif numBooks == 27:
            self.bookList = [BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber(x) for x in range(40,66+1)]
        else:
            logging.warning( f"GoBible.preload found {numBooks} books -- trying to figure out book codes" )
            self.bookList = []
            for n in range( numBooks ):
                #print( f"{n+1}/{numBooks}: Got '{self.bookNames[n]}' and '{self.filenameBases[n]}'" )
                BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( self.bookNames[n] )
                BBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( self.filenameBases[n] )
                #print( f"{n+1}/{numBooks}: Found {BBB1} and {BBB2}" )
                if BBB1 and (BBB2==BBB1 or BBB2 is None): BBB = BBB1
                elif BBB2 and BBB1 is None: BBB = BBB2
                elif BBB1 and BBB2:
                    logging.error( f"GoBible.preload choosing '{self.bookNames[n]}'->{BBB1} over '{self.filenameBases[n]}'->{BBB2}" )
                    BBB = BBB1
                else:
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber(n)
                    logging.error( f"GoBible.preload unable to discover book code from '{self.bookNames[n]}'->{BBB1} or '{self.filenameBases[n]}'->{BBB2}: assuming {BBB}" )
                self.bookList.append( BBB )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "GoBible.preload: {} book details preloaded".format( numBooks ) )
        if len(self.bookList) != numBooks:
            logging.critical( f"GoBible.preload could only discover book codes for {len(self.bookList)}/{numBooks} books" )

        self.preloadDone = True
    # end of GoBible.preload


    def loadBook( self, BBB ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "GoBible.loadBook( {} )".format( BBB ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading GoBible {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BBB in self.bookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  GoBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
            GoBibleBk = GoBibleBook( self, BBB )
            GoBibleBk.load( self.bookList.index( BBB ) )
            GoBibleBk.validateMarkers()
            self.stashBook( GoBibleBk )
            #else: logging.info( "GoBible book {} was completely blank".format( BBB ) )
        else: logging.info( "GoBible book {} is not listed as being available".format( BBB ) )
    # end of GoBible.loadBook


    def _loadBookMP( self, BBB ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "loadBookMP( {} )".format( BBB ) )
        assert BBB not in self.books
        self.triedLoadingBook[BBB] = True
        if BBB in self.bookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                print( '  ' + "Loading {} from {} from {}…".format( BBB, self.name, self.sourceFolder ) )
            GoBibleBk = GoBibleBook( self, BBB )
            GoBibleBk.load( self.bookList.index( BBB ) )
            GoBibleBk.validateMarkers()
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                print( _("    Finishing loading GoBible book {}.").format( BBB ) )
            return GoBibleBk
        else: logging.info( "GoBible book {} is not listed as being available".format( BBB ) )
    # end of GoBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading {} from {}…".format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.bookList:
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Loading {} GoBible books using {} processes…".format( len(self.bookList), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.bookList ) # have the pool do our loads
                    assert len(results) == len(self.bookList)
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB in self.bookList:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  GoBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    loadedBook = self.loadBook( BBB ) # also saves it
        else:
            logging.critical( "GoBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )

        # Delete the temporary folder (where .jar was unzipped)
        rmtree( self.unzippedFolderPath )
        self.unzippedFolderPath = None

        self.doPostLoadProcessing()
    # end of GoBible.load
# end of GoBible class



class GoBibleBook( BibleBook ):
    """
    Class to load and manipulate a single GoBible file / book.
    """

    def __init__( self, containerBibleObject, BBB ):
        """
        Create the Go Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'Go Bible Book object'
        self.objectTypeString = 'GoBible'

        #global sortedNLMarkers
        #if sortedNLMarkers is None:
            #sortedNLMarkers = sorted( BibleOrgSysGlobals.GoBibleMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )
    # end of GoBibleBook.__init__


    def load( self, indexToBook ):
        """
        Load the Go Bible book from a folder.

        Tries to combine physical lines into logical lines,
            i.e., so that all lines begin with a GoBible paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( f"GoBibleBook.load( {indexToBook} )" )
        filenameBase = self.containerBibleObject.filenameBases[indexToBook]
        folderPath = os.path.join( self.containerBibleObject.dataFolderPath, filenameBase+'/' )
        loadErrors = []

        # Load the book index first
        indexPath = os.path.join( folderPath, 'Index' )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading book index {}…").format( indexPath ) )
        with open( indexPath, 'rb' ) as bookIndexFile:
            bookIndexContents = bookIndexFile.read()
        numChapters = self.containerBibleObject.numChaptersList[indexToBook]
        index = 0
        chapterLengths = []
        for chapterNumberIndex in range( numChapters ):
            numVerses = self.containerBibleObject.numVersesList[indexToBook][chapterNumberIndex][0]
            #if debuggingThisModule:
                #print( f"Book #{indexToBook+1} Chapter #{chapterNumberIndex+1} has {numVerses} verses" )
            offset = 0
            verseLengths = []
            for verseNumberIndex in range( numVerses ):
                verseLength, = struct.unpack( ">H", bookIndexContents[index:index+2] ); index += 2
                if debuggingThisModule: print( f"{verseNumberIndex+1} Offset={offset:,} VerseLength={verseLength:,}" )
                verseLengths.append( (offset,verseLength) )
                offset += verseLength
            chapterLengths.append( verseLengths )
        assert index == len(bookIndexContents)
        del bookIndexContents


        # Now load the text itself (GoBible is designed to be loaded chapter by chapter)
        lastFileIndexNumber = -1
        needAPee = False
        for chapterNumberIndex in range( numChapters ):
            self.addLine( 'c', str(chapterNumberIndex+1) )
            needAPee = True
            numVerses = self.containerBibleObject.numVersesList[indexToBook][chapterNumberIndex][0]
            fileIndexNumber = self.containerBibleObject.numVersesList[indexToBook][chapterNumberIndex][1]
            if fileIndexNumber != lastFileIndexNumber:
                if fileIndexNumber == 0:
                    chapterText = ""
                else:
                    #print( "co", chapterOffset, "dl", dataLength )
                    #print( chapterText[chapterOffset:] )
                    #assert chapterOffset == dataLength # Check we used all of the last one
                    chapterText = chapterText[chapterOffset:]
                textFilepath = os.path.join( folderPath, f'{filenameBase} {fileIndexNumber}' )
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( f"At book {indexToBook+1} chapter {chapterNumberIndex+1}: loading Bible text from '{textFilepath}'…" )
                with open( textFilepath, 'rb' ) as chapterFile:
                    chapterDataFull = chapterFile.read()
                lastFileIndexNumber = fileIndexNumber
                #print( chapterDataFull[:200], '…' )
                dataLength, = struct.unpack( ">I", chapterDataFull[:4] )
                #print( f"dataLength={dataLength:,}" )
                assert dataLength + 4 == len(chapterDataFull)

                chapterData = chapterDataFull[4:]
                assert dataLength == len(chapterData)
                #print( chapterData[:500] )
                chapterText += chapterData.decode()
                chapterOffset = 0
            for verseNumberIndex in range( numVerses ):
                offset, verseLength = chapterLengths[chapterNumberIndex][verseNumberIndex]
                #print( f"At {chapterNumberIndex+1}:{verseNumberIndex+1} Offset={offset:,} verseLength={verseLength:,}" )
                verseText = chapterText[chapterOffset+offset:chapterOffset+offset+verseLength].strip()
                if debuggingThisModule: print( f"{chapterNumberIndex+1}:{verseNumberIndex+1}: {verseText!r}" )
                if verseText.count( '\x01' ) == 2:
                    ix1 = verseText.find( '\x01' )
                    ix2 = verseText.find( '\x01', ix1+1 )
                    haveBrackets = verseText[ix1+1]=='[' and verseText[ix2-1]==']'
                    extract = verseText[ix1+2:ix2-1] if haveBrackets else verseText[ix1+1:ix2]
                    #print( "extract", repr(extract) )
                    verseTextPrevious = verseText[:ix1].strip()
                    if verseTextPrevious:
                        if needAPee:
                            self.addLine( 'p', '' )
                            needAPee = False
                        self.addLine( 'v', f'{verseNumberIndex+1} {verseTextPrevious}' )
                    self.addLine( 's', extract ) # What should this field be?
                    verseText = verseText[ix2+1:].strip()
                    if verseTextPrevious:
                        self.addLine( 'p', verseText )
                    else:
                        self.addLine( 'p', '' )
                        self.addLine( 'v', f'{verseNumberIndex+1} {verseText}' )
                    needAPee = False
                    #print( "new verseText", repr(verseText) )
                    #if debuggingThisModule: print( f"{chapterNumberIndex+1}:{verseNumberIndex+1}: {verseText!r}" )
                else:
                    if needAPee:
                        self.addLine( 'p', '' )
                        needAPee = False
                    self.addLine( 'v', f'{verseNumberIndex+1} {verseText}' )
            chapterOffset += offset + verseLength
        assert chapterOffset == len(chapterText) # Check we used all of the last one

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        if debuggingThisModule: print( self._rawLines ); halt
    # end of GoBibleBook.load
# end of class GoBibleBook



def testGoBible( GoBibleFile ):
    # Crudely demonstrate the Go Bible class
    from BibleOrgSys.Reference import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the Go Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test file is {!r}".format( GoBibleFile ) )
    vb = GoBible( GoBibleFile )
    vb.loadBooks() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( vb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        vb.check()
        #print( GoBibleB.books['GEN']._processedLines[0:40] )
        vBErrors = vb.getErrors()
        # print( vBErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##vb.toDrupalBible()
        vb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(vb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(vb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(vb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, ob.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = vb.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
# end of testGoBible


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    testFolders =  (
        BiblesFolderpath.joinpath( 'GoBible modules/Haiola GoBible test versions/' ),
        BiblesFolderpath.joinpath( 'GoBible modules/' ),
        )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in testFolders:
            result1 = GoBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "GoBible TestA1", result1 )

            result2 = GoBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "GoBible TestA2", result2 )
            if isinstance( result2, GoBible ): rmtree( result2.unzippedFolderPath )

            result3 = GoBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "GoBible TestA3", result3 )
            #result3.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )

            if BibleOrgSysGlobals.strictCheckingFlag:
                result3.check()
                #print( GoBibleB.books['GEN']._processedLines[0:40] )
                vBErrors = result3.getErrors()
                # print( vBErrors )
            if BibleOrgSysGlobals.commandLineArguments.export:
                ##result3.toDrupalBible()
                if isinstance( result2, GoBible ):
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 1: # all discovered modules in the test folders
        for testFolder in testFolders:
            foundFolders, foundFiles = [], []
            for something in os.listdir( testFolder ):
                somepath = os.path.join( testFolder, something )
                if os.path.isdir( somepath ): foundFolders.append( something )
                elif os.path.isfile( somepath ) and somepath.endswith('.jar'): foundFiles.append( something )

            if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFiles) ) )
                parameters = [os.path.join(testFolder, filename) for filename in sorted(foundFiles)]
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( testGoBible, parameters ) # have the pool do our loads
                    assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                for j, someFile in enumerate( sorted( foundFiles ) ):
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nGoBible D{}/ Trying {}".format( j+1, someFile ) )
                    testGoBible( os.path.join( testFolder, someFile ) )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GoBible.py
