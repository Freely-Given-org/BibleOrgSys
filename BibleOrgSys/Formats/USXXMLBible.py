#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBible.py
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012-2019 Robert Hunt
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
Module for defining and manipulating complete or partial USX Bibles.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "USXXMLBibleHandler"
PROGRAM_NAME = "USX XML Bible handler"
PROGRAM_VERSION = '0.38'
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
from BibleOrgSys.InputOutput.USXFilenames import USXFilenames
#from BibleOrgSys.Formats.PTX7Bible import loadPTX7ProjectData
from BibleOrgSys.Formats.USXXMLBibleBook import USXXMLBibleBook
from BibleOrgSys.Bible import Bible



def USXXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USX Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USX Bible is found,
        returns the loaded USXXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USXXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USXXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " USXXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )

    # See if there's an USXBible project here in this given folder
    numFound = 0
    UFns = USXFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    #filenameTuples = UFns.getPossibleFilenameTuples( strictCheck=True )
    #print( 'P', len(filenameTuples) )
    filenameTuples = UFns.getConfirmedFilenameTuples( strictCheck=True )
    #print( 'C', len(filenameTuples) )
    if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USXXMLBible( givenFolderName )
            if autoLoad or autoLoadBooks: uB.preload() # Determine the filenames
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("USXXMLBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    USXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if there's an USX Bible with standard Paratext style filenames here in this folder
        UFns = USXFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
        #filenameTuples = UFns.getPossibleFilenameTuples()
        filenameTuples = UFns.getConfirmedFilenameTuples( strictCheck=True )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples and debuggingThisModule:
            print( "  Found {} USX file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USXXMLBible( foundProjects[0] )
            if autoLoad or autoLoadBooks: uB.preload() # Determine the filenames
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            return uB
        return numFound
# end of USXXMLBibleFileCheck



class USXXMLBible( Bible ):
    """
    Class to load and manipulate USX Bibles.

    """
    def __init__( self, givenFolderName, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Create the internal USX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'USX XML Bible object'
        self.objectTypeString = 'USX'

        self.givenFolderName, self.givenName, self.abbreviation, self.encoding = givenFolderName, givenName, givenAbbreviation, encoding # Remember our parameters
        self.sourceFolder = self.givenFolderName

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.givenFolderName )
        if not self.name: self.name = os.path.basename( self.givenFolderName[:-1] ) # Remove the final slash
        if not self.name: self.name = 'USX Bible'
    # end of USXXMLBible.__init_


    def preload( self ):
        """
        Tries to determine USX filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "USXXMLBible preload() from {}".format( self.sourceFolder ) )

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.error( "USXXMLBible: File {!r} is unreadable".format( self.givenFolderName ) )

        # Find the filenames of all our books
        self.USXFilenamesObject = USXFilenames( self.givenFolderName )
        #print( "DDFSDF", self.USXFilenamesObject )
        #print( "DFSFGE", self.USXFilenamesObject.getPossibleFilenameTuples() )
        #print( "SDFSDQ", self.USXFilenamesObject.getConfirmedFilenameTuples() )
        self.possibleFilenameDict = {}
        filenameTuples = self.USXFilenamesObject.getConfirmedFilenameTuples()
        if not filenameTuples: # Try again
            filenameTuples = self.USXFilenamesObject.getPossibleFilenameTuples()
        for BBB,filename in filenameTuples:
            self.availableBBBs.add( BBB )
            self.possibleFilenameDict[BBB] = filename
        #print( "GHJGHR", self.possibleFilenameDict ); halt

        self.preloadDone = True
    # end of USXXMLBible.preload


    def loadBook( self, BBB, filename=None ):
        """
        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "USXXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
            assert self.preloadDone

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  USXXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USXXMLBibleBook( self, BBB )
        UBB.load( filename, self.givenFolderName, self.encoding )
        UBB.validateMarkers()
        #for j, something in enumerate( UBB._processedLines ):
            #print( j, something )
            #if j > 100: break
        #for j, something in enumerate( sorted(UBB._CVIndex) ):
            #print( j, something )
            #if j > 50: break
        #halt
        self.stashBook( UBB )
        self.bookNeedsReloading[BBB] = False
    # end of USXXMLBible.loadBook


    def _loadBookMP( self, BBB, filename=None ):
        """
        Used for multiprocessing.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "USXXMLBible._loadBookMP( {}, {} )".format( BBB, filename ) )
            assert self.preloadDone

        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  USXXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USXXMLBibleBook( self, BBB )
        UBB.load( filename, self.givenFolderName, self.encoding )
        UBB.validateMarkers()
        #for j, something in enumerate( UBB._processedLines ):
            #print( j, something )
            #if j > 100: break
        #for j, something in enumerate( sorted(UBB._CVIndex) ):
            #print( j, something )
            #if j > 50: break
        #halt
        return UBB
    # end of USXXMLBible._loadBookMP


    def loadBooks( self ):
        """
        Load the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("USXXMLBible: Loading {} books from {}…").format( self.name, self.givenFolderName ) )

        if not self.preloadDone: self.preload()

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.givenFolderName ):
            somepath = os.path.join( self.givenFolderName, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what {!r} is in {}!".format( somepath, self.givenFolderName ) )
        if foundFolders: logging.info( "USXXMLBible.loadBooks: Surprised to see subfolders in {!r}: {}".format( self.givenFolderName, foundFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "USXXMLBible.loadBooks: Couldn't find any files in {!r}".format( self.givenFolderName ) )
            return # No use continuing

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            # Load all the books as quickly as possible
            parameters = []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenameTuples():
                parameters.append( BBB )
            #print( "parameters", parameters )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( _("Loading {} {} books using {} processes…").format( len(parameters), 'USX', BibleOrgSysGlobals.maxProcesses ) )
                print( _("  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed.") )
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self._loadBookMP, parameters ) # have the pool do our loads
                #print( "results", results )
                #assert len(results) == len(parameters)
                for j, UBB in enumerate( results ):
                    BBB = parameters[j]
                    #self.books[BBB] = UBB
                    self.stashBook( UBB )
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            #print( self.USXFilenamesObject.getConfirmedFilenameTuples() ); halt
            for BBB,filename in self.possibleFilenameDict.items():
                self.loadBook( BBB, filename ) # also saves it
                #UBB = USXXMLBibleBook( self, BBB )
                #UBB.load( filename, self.givenFolderName, self.encoding )
                #UBB.validateMarkers()
                #print( UBB )
                #self.stashBook( UBB )

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "USXXMLBible.loadBooks: Didn't find any regularly named USX files in {!r}".format( self.givenFolderName ) )
            #for thisFilename in foundFiles:
                ## Look for BBB in the ID line (which should be the first line in a USX file)
                #isUSX = False
                #thisPath = os.path.join( self.givenFolderName, thisFilename )
                #try:
                    #with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                        #for line in possibleUSXFile:
                            #if line.startswith( '\\id ' ):
                                #USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                                #if BibleOrgSysGlobals.verbosityLevel > 2: print( "Have possible USX ID {!r}".format( USXId ) )
                                #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USXId )
                                #if BibleOrgSysGlobals.verbosityLevel > 2: print( "BBB is {!r}".format( BBB ) )
                                #isUSX = True
                            #break # We only look at the first line
                #except UnicodeDecodeError: isUSX = False
                #if isUSX:
                    #UBB = USXXMLBibleBook( self, BBB )
                    #UBB.load( self.givenFolderName, thisFilename, self.encoding )
                    #UBB.validateMarkers()
                    #print( UBB )
                    #self.books[BBB] = UBB
                    ## Make up our book name dictionaries while we're at it
                    #assumedBookNames = UBB.getAssumedBookNames()
                    #for assumedBookName in assumedBookNames:
                        #self.BBBToNameDict[BBB] = assumedBookName
                        #assumedBookNameLower = assumedBookName.lower()
                        #self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            #if self.books: print( "USXXMLBible.loadBooks: Found {} irregularly named USX files".format( len(self.books) ) )

        self.doPostLoadProcessing()
    # end of USXXMLBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class USXXMLBible



def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    testData = (
                ('Test1',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1'),),
                ('Test2',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2'),),
                ('MatigsalugUSFM',BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'),), # USFM not USX !
                ("Matigsalug3", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/'),),
                ("Matigsalug4", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/'),),
                ("Matigsalug5", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/'),),
                ) # You can put your USX test folder here

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for j, (name, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nA{}: Testfolder is: {}".format( j+1, testFolder ) )
            result1 = USXXMLBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}a".format( j+1 ), result1 )
            result2 = USXXMLBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}b (autoLoad)".format( j+1 ), result2 )
            result3 = USXXMLBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}c (autoLoadBooks)".format( j+1 ), result3 )

    if 1:
        for j, (name, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nB{}: Testfolder is: {} ({})".format( j+1, testFolder, name ) )
            if os.access( testFolder, os.R_OK ):
                UB = USXXMLBible( testFolder, name )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                if BibleOrgSysGlobals.commandLineArguments.export: UB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                #UBErrors = UB.getErrors()
                # print( UBErrors )
                #print( UB.getVersification() )
                #print( UB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "B{}: Sorry, test folder {!r} is not readable on this computer.".format( j+1, testFolder ) )

        #if BibleOrgSysGlobals.commandLineArguments.export:
        #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
        #       pass

    if 1:
        USXSourceFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../srv/Documents/USXResources/' ) # You can put your own folder here
        for j, something in enumerate( sorted( os.listdir( USXSourceFolder ) ) ):
            if something == '.git': assert j==0; continue
            #if something != 'TND': continue # Test this one only!!!
            #print( "something", something )
            somepath = os.path.join( USXSourceFolder, something )
            if os.path.isfile( somepath ):
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                    print( "C{}/ Unexpected {} file in {}".format( j, something, USXSourceFolder ) )
            elif os.path.isdir( somepath ):
                abbreviation = something
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nC{}/ Loading USX {}…".format( j, abbreviation ) )
                loadedBible = USXXMLBible( somepath, givenName=abbreviation+' Bible' )
                loadedBible.loadBooks() # Load and process the USX XML books
                if BibleOrgSysGlobals.verbosityLevel > 0: print( loadedBible ) # Just print a summary
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USXXMLBible.py
