#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BCVBible.py
#
# Module handling Bibles where each verse is stored in a separate file.
#
# Copyright (C) 2014-2019 Robert Hunt
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
Module for defining and manipulating complete or partial BCV Bibles.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-05-09' # by RJH
SHORT_PROGRAM_NAME = "BCVBible"
PROGRAM_NAME = "BCV Bible handler"
PROGRAM_VERSION = '0.22'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot

METADATA_FILENAME = 'Metadata.txt'


def BCVBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for BCV Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one BCV Bible is found,
        returns the loaded BCVBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "BCVBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( "BCVBibleFileCheck: Given {!r} folder is unreadable".format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( "BCVBibleFileCheck: Given {!r} path is not a folder".format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " BCVBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
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
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )

    # See if there's an BCVBible project here in this given folder
    numFound = 0
    if METADATA_FILENAME in foundFiles:
        numFound += 1
        if strictCheck:
            for folderName in foundFolders:
                if folderName not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                    print( "BCVBibleFileCheck: Suprised to find folder:", folderName )
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "BCVBibleFileCheck got {} in {}".format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            bcvB = BCVBible( givenFolderName )
            if autoLoad: bcvB.preload()
            if autoLoadBooks: bcvB.loadBooks() # Load and process the file
            return bcvB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("BCVBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    BCVBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )

        # See if there's an BCV Bible here in this folder
        if METADATA_FILENAME in foundSubfiles:
            numFound += 1
            if strictCheck:
                for folderName in foundSubfolders:
                    if folderName not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                        print( "BCVBibleFileCheckSuprised to find folder:", folderName )
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "BCVBibleFileCheck foundProjects {} {}".format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            bcvB = BCVBible( foundProjects[0] )
            if autoLoad: bcvB.preload()
            if autoLoadBooks: bcvB.loadBooks() # Load and process the file
            return bcvB
        return numFound
# end of BCVBibleFileCheck



class BCVBible( Bible ):
    """
    Class to load and manipulate BCV Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None, encoding=None ):
        """
        Create the internal BCV Bible object.

        Note that sourceFolder can be None if we don't know that yet.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'BCV Bible object'
        self.objectTypeString = 'BCV'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding
    # end of BCVBible.__init_


    def preload( self ):
        """
        Loads the Metadata file if it can be found.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("preload() from {}").format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( _("BCVBible.preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("BCVBible.preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( _("BCVBible.preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
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
        #if not self.name: self.name = "BCV Bible"

        self.preloadDone = True
    # end of BCVBible.preload


    def loadMetadata( self, metadataFilepath ):
        """
        Process the netadata from the given filepath.

        Sets some class variables and puts a dictionary into self.settingsDict.
        """
        if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Loading metadata from {!r}".format( metadataFilepath ) )
        #if encoding is None: encoding = 'utf-8'
        self.metadataFilepath = metadataFilepath
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['BCV'] = {}

        self.givenBookList = None
        lastLine, lineCount, status = '', 0, 0
        with open( metadataFilepath, 'rt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1:
                    if line[0]==chr(65279): #U+FEFF
                        logging.info( "loadMetadata1: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                        line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
                    elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                        logging.info( "loadMetadata2: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                        line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                line = line.strip() # Remove leading and trailing whitespace
                if not line: continue # Just discard blank lines
                lastLine = line
                processed = False
                #BCVVersion = 1.0
                for fieldName in ('BCVVersion','ProjectName','Name','Abbreviation','BookList',):
                    if line.startswith( fieldName+' = ' ):
                        self.suppliedMetadata['BCV'][fieldName] = line[len(fieldName)+3:]
                        processed = True
                        break
                if not processed: print( _("ERROR: Unexpected {!r} line in metadata file").format( line ) )
        #print( 'SD', self.suppliedMetadata['BCV'] ); halt
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  " + _("Got {} metadata entries:").format( len(self.suppliedMetadata['BCV']) ) )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                for key in sorted(self.suppliedMetadata['BCV']):
                    print( "    {}: {}".format( key, self.suppliedMetadata['BCV'][key] ) )

        if 'BCVVersion' in self.suppliedMetadata['BCV']:
            assert self.suppliedMetadata['BCV']['BCVVersion'] == '1.0'

        #if 'ProjectName' in self.suppliedMetadata['BCV']:
            #self.projectName = self.suppliedMetadata['BCV']['ProjectName']
        #if 'Name' in self.suppliedMetadata['BCV']:
            #self.projectName = self.suppliedMetadata['BCV']['Name']
        #if 'Abbreviation' in self.suppliedMetadata['BCV']:
            #self.projectName = self.suppliedMetadata['BCV']['Abbreviation']
        if 'BookList' in self.suppliedMetadata['BCV']:
            BL = self.suppliedMetadata['BCV']['BookList']
            if BL and BL[0]=='[' and BL[-1]==']': self.givenBookList = eval( BL )
            #print( 'x1', repr(self.givenBookList), repr(self.givenBookList[2]) )
            if isinstance( self.givenBookList, list ):
                # del self.suppliedMetadata['BCV']['BookList']
                pass
            else: print( _("ERROR: Unexpected {!r} format in metadata file").format( BL ) )
            #bl = self.suppliedMetadata['BCV']['BookList']
            #if bl[0]=='[' and bl[-1]==']':
                #for something in bl[1:-1].split( ',' ):
                    #if something[0]==' ': something = something[1:]
                    #if something[0]=="'" and something[-1]=="'": something = something[1:-1]
                    #if something in BibleOrgSysGlobals.loadedBibleBooksCodes:
                        #self.givenBookList.append( something )
                    #else: print( "ERROR: Unexpected {!r} booklist entry in metadata file".format( something ) )
                #del self.suppliedMetadata['BCV']['BookList']
            #else: print( "ERROR: Unexpected {!r} format in metadata file".format( bl ) )

        if self.suppliedMetadata['BCV']:
            self.applySuppliedMetadata( 'BCV' ) # Copy some to self.settingsDict
            if debuggingThisModule: print( 's.SD', self.settingsDict )
    # end of BCVBible.loadMetadata


    def loadBook( self, BBB ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "BCVBible.loadBook( {} )".format( BBB ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading BCV {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  BCVBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
            bcvBB = BCVBibleBook( self, BBB )
            bcvBB.load( self.sourceFolder )
            if bcvBB._processedLines:
                bcvBB.validateMarkers()
                self.stashBook( bcvBB )
            else: logging.info( "BCV book {} was completely blank".format( BBB ) )
            self.availableBBBs.add( BBB )
        else: logging.info( "BCV book {} is not listed as being available".format( BBB ) )
    # end of BCVBible.loadBook


    def _loadBookMP( self, BBB ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("loadBookMP( {} )").format( BBB ) )
        assert BBB not in self.books
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                print( '  ' + "Loading {} from {} from {}…".format( BBB, self.name, self.sourceFolder ) )
            bcvBB = BCVBibleBook( self, BBB )
            bcvBB.load( self.sourceFolder )
            bcvBB.validateMarkers()
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading BCV book {}.").format( BBB ) )
            return bcvBB
        else: logging.info( "BCV book {} is not listed as being available".format( BBB ) )
    # end of BCVBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading {} from {}…".format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.givenBookList:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Loading {} BCV books using {} processes…".format( len(self.givenBookList), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
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
                        #print( _("  BCVBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    loadedBook = self.loadBook( BBB ) # also saves it
        else:
            logging.critical( "BCVBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of BCVBible.load
# end of class BCVBible



class BCVBibleBook( BibleBook ):
    """
    Class to load and manipulate a single BCV file / book.
    """

    def __init__( self, containerBibleObject, BBB ):
        """
        Create the BCV Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'BCV Bible Book object'
        self.objectTypeString = 'BCV'
    # end of BCVBibleBook.__init__


    def loadBookMetadata( self, metadataFilepath ):
        """
        Process the metadata from the given filepath.

        Sets some class variables and puts a dictionary into self.settingsDict.
        """
        if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
            print( '  ' + "Loading {} metadata from {!r}…".format( self.BBB, metadataFilepath ) )
        #if encoding is None: encoding = 'utf-8'
        self.metadataFilepath = metadataFilepath
        self.givenCVList = None
        lastLine, lineCount, status, settingsDict = '', 0, 0, {}
        with open( metadataFilepath ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadBookMetadata: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                    line = line[1:] # Remove the Byte Order Marker (BOM)
                if line and line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                line = line.strip() # Remove leading and trailing whitespace
                if not line: continue # Just discard blank lines
                lastLine = line
                processed = False
#BCVVersion = 1.0
#WorkName = Matigsalug
#CVList = [('1', '1'), ('1', '2'), ('1', '3'), ('1', '4'), ('1', '5'), …
                for fieldName in ('BCVVersion','WorkName','CVList',):
                    if line.startswith( fieldName+' = ' ):
                        settingsDict[fieldName] = line[len(fieldName)+3:]
                        processed = True
                        break
                if not processed: print( "ERROR: Unexpected {!r} line in metadata file".format( line ) )
        #print( 'SD', settingsDict )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  " + "Got {} metadata entries:".format( len(settingsDict) ) )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                for key in sorted(settingsDict):
                    print( "    {}: {}".format( key, settingsDict[key] ) )

        if 'BCVVersion' in settingsDict: settingsDict['BCVVersion'] == '1.0'; del settingsDict['BCVVersion']
        if 'WorkName' in settingsDict: self.workName = settingsDict['WorkName']; del settingsDict['WorkName']
        #if 'Name' in settingsDict: self.projectName = settingsDict['Name']; del settingsDict['Name']
        #if 'Abbreviation' in settingsDict: self.projectName = settingsDict['Abbreviation']; del settingsDict['Abbreviation']
        if 'CVList' in settingsDict:
            #self.givenCVList = None
            CVL = settingsDict['CVList']
            if CVL and CVL[0]=='[' and CVL[-1]==']': self.givenCVList = eval( CVL )
            #print( 'x1', repr(self.givenCVList) )
            if isinstance( self.givenCVList, list ): del settingsDict['CVList']
            else: print( "ERROR: Unexpected {!r} format in metadata file".format( CVL ) )

        if settingsDict:
            self.settingsDict = settingsDict
            print( 'book SD', self.settingsDict )
    # end of BCVBibleBook.loadBookMetadata


    def load( self, folder ):
        """
        Load the BCV Bible book from a folder.

        Tries to standardise by combining physical lines into logical lines,
            i.e., so that all lines begin with a BCV paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """

        def doaddLine( originalMarker, originalText ):
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            #print( "doaddLine( {}, {} )".format( repr(originalMarker), repr(originalText) ) )
            marker, text = originalMarker, originalText.replace( '~', ' ' )
            if '\\' in text: # Check markers inside the lines
                markerList = BibleOrgSysGlobals.BCVMarkers.getMarkerListFromText( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if insideMarker == '\\': # it's a free-standing backspace
                        loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: {!r}").format( self.BBB, C, V, marker, text ) )
                        logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                        self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
                    elif BibleOrgSysGlobals.BCVMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} NewLine marker {!r} shouldn't appear within line in \\{}: {!r}").format( self.BBB, C, V, insideMarker, marker, text ) )
                            logging.error( _("NewLine marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
                        thisText = text[ix:iMIndex].rstrip()
                        self.addLine( marker, thisText )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        #print( "Did a split from {}:{!r} to {}:{!r} leaving {}:{!r}".format( originalMarker, originalText, marker, thisText, insideMarker, text[ix:] ) )
                        marker = insideMarker # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    text = text[ix:] # Get the final bit of the line
            self.addLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of doaddLine


        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading {} from {}…").format( self.BBB, folder ) )
        self.sourceFolder = os.path.join( folder, self.BBB+'/' )

        # Read book metadata
        self.loadBookMetadata( os.path.join( self.sourceFolder, self.BBB+'__BookMetadata.txt' ) )

        fixErrors = []
        self._processedLines = InternalBibleEntryList() # Contains more-processed tuples which contain the actual Bible text -- see below

        DUMMY_VALUE = 999999 # Some number bigger than the number of characters in a line
        for CV in self.givenCVList:
            lineCount = 0
            if isinstance( CV, tuple) and len(CV)==2:
                C, V = CV
                filename = self.BBB+'_C'+C+'V'+V+'.txt'
            else:
                assert CV == ('-1',)
                C = V = '-1', '0'
                filename = self.BBB+'__Intro.txt'
            with open( os.path.join( self.sourceFolder, filename ), 'rt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "loadBCVBibleBook: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                        line = line[1:] # Remove the Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                    #print( CV, "line", line )
                    assert line and line[0]=='\\'
                    ixEQ = line.find( '=' )
                    ixLL = line.find( '<<' )
                    if ixEQ == -1: ixEQ = DUMMY_VALUE
                    if ixLL == -1: ixLL = DUMMY_VALUE
                    ix = min( ixEQ, ixLL )
                    marker = line[1:ix]
                    #print( 'marker', repr(marker) )
                    if ixLL == DUMMY_VALUE:
                        originalMarker = None
                        if marker == 'v~': originalMarker = 'v'
                        elif marker == 'c#': originalMarker = 'c'
                    else: originalMarker = line[ixLL+2:ixEQ]
                    #print( 'originalMarker', repr(originalMarker) )
                    if ixEQ == DUMMY_VALUE: text = None
                    else: text = line[ixEQ+1:]
                    #print( 'text', repr(text) )

                    if marker[0] == '¬':
                        assert originalMarker is None and text is None
                        adjText = extras = None
                    else:
                        if originalMarker is None: originalMarker = marker
                        if text is None: text = ''
                        adjText, cleanText, extras = self.processLineFix( C, V, originalMarker, text, fixErrors ) # separate out the notes (footnotes and cross-references)
                    self._processedLines.append( InternalBibleEntry(marker, originalMarker, adjText, cleanText, extras, text) )

            #if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
            #if debugging: print( self._rawLines ); halt
        if fixErrors: self.errorDictionary['Fix Text Errors'] = fixErrors
        self._processedFlag = True
        self.makeCVIndex()
    # end of load
# end of class BCVBibleBook



def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest1/' )
    testFolder = "OutputFiles/BOS_BCV_Export/"


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nBCV TestA1" )
        result1 = BCVBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "BCV TestA1", result1 )

        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nBCV TestA2" )
        result2 = BCVBibleFileCheck( testFolder, autoLoad=True ) # But doesn't preload books
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "BCV TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #print( UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getErrors()
            # print( bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nBCV TestA3" )
        result3 = BCVBibleFileCheck( testFolder, autoLoad=True, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "BCV TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #print( UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getErrors()
            # print( bibleErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nBCV D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
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
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nBCV A{}/".format( count ) )
                bcvB = BCVBible( testFolder, name, encoding=encoding )
                bcvB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Gen assumed book name:", repr( bcvB.getAssumedBookName( 'GEN' ) ) )
                    print( "Gen long TOC book name:", repr( bcvB.getLongTOCName( 'GEN' ) ) )
                    print( "Gen short TOC book name:", repr( bcvB.getShortTOCName( 'GEN' ) ) )
                    print( "Gen book abbreviation:", repr( bcvB.getBooknameAbbreviation( 'GEN' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( bcvB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    bcvB.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = bcvB.getErrors()
                    # print( bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##bcvB.toDrupalBible()
                    bcvB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "OutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "newObj is", newObj )
            else: print( f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
#end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BCVBible.py
