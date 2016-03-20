#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBible.py
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012-2016 Robert Hunt
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

LastModifiedDate = '2016-03-01' # by RJH
ShortProgName = "USXXMLBibleHandler"
ProgName = "USX XML Bible handler"
ProgVersion = '0.27'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
import multiprocessing

import BibleOrgSysGlobals
from USXFilenames import USXFilenames
from PTXBible import loadPTXSSFData
from USXXMLBibleBook import USXXMLBibleBook
from Bible import Bible



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



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
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an USXBible project here in this given folder
    numFound = 0
    UFns = USXFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getPossibleFilenameTuples()
    if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USXXMLBible( givenFolderName )
            if autoLoadBooks: uB.load() # Load and process the file
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
        filenameTuples = UFns.getPossibleFilenameTuples()
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
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of USXXMLBibleFileCheck



class USXXMLBible( Bible ):
    """
    Class to load and manipulate USX Bibles.

    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal USX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "USX XML Bible object"
        self.objectTypeString = "USX"

        self.givenFolderName, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.givenFolderName )
        if not self.name: self.name = os.path.basename( self.givenFolderName[:-1] ) # Remove the final slash
        if not self.name: self.name = "USX Bible"

        self.ssfFilepath = None
    # end of USXXMLBible.__init_


    def preload( self ):
        """
        Tries to determine USX filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("preload() from {}").format( self.sourceFolder ) )

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.error( "USXXMLBible: File {!r} is unreadable".format( self.givenFolderName ) )

        # Find the filenames of all our books
        self.USXFilenamesObject = USXFilenames( self.givenFolderName )
        self.possibleFilenameDict = {}
        for BBB,filename in self.USXFilenamesObject.getConfirmedFilenameTuples():
            self.possibleFilenameDict[BBB] = filename

        if 0: # we don't have a getSSFFilenames function :(
            if self.suppliedMetadata is None: self.suppliedMetadata = {}
            if self.ssfFilepath is None: # it might have been loaded first
                # Attempt to load the SSF file
                #self.suppliedMetadata, self.settingsDict = {}, {}
                ssfFilepathList = self.USXFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
                #print( "ssfFilepathList", ssfFilepathList )
                if len(ssfFilepathList) > 1:
                    logging.error( exp("preload: Found multiple possible SSF files -- using first one: {}").format( ssfFilepathList ) )
                if len(ssfFilepathList) >= 1: # Seems we found the right one
                    SSFDict = loadPTXSSFData( self, ssfFilepathList[0] )
                    if SSFDict:
                        if 'PTX' not in self.suppliedMetadata: self.suppliedMetadata['PTX'] = {}
                        self.suppliedMetadata['PTX']['SSF'] = SSFDict
                        self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "USFM Bible"

        self.preloadDone = True
    # end of USFMBible.preload


    def loadBook( self, BBB, filename=None ):
        """
        Used for multiprocessing.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  USXXMLBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
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
        self.saveBook( UBB )
        #return UBB
    # end of USXXMLBible.loadBook


    def loadBooks( self ):
        """
        Load the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("USXXMLBible: Loading {} books from {}...").format( self.name, self.givenFolderName ) )

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

        #if 0: # We don't have a getSSFFilenames function
            ## Attempt to load the metadata file
            #ssfFilepathList = self.USXFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            #if len(ssfFilepathList) == 1: # Seems we found the right one
                #SSFDict = loadPTXSSFData( ssfFilepathList[0] )
                #if SSFDict:
                    #if 'PTX' not in self.suppliedMetadata: self.suppliedMetadata['PTX'] = {}
                    #self.suppliedMetadata['PTX']['SSF'] = SSFDict
                    #self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        # DON'T KNOW WHY THIS DOESN'T WORK
        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
            parameters = []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenameTuples():
                parameters.append( BBB )
            #print( "parameters", parameters )
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self.loadBook, parameters ) # have the pool do our loads
                print( "results", results )
                assert len(results) == len(parameters)
                for j, UBB in enumerate( results ):
                    BBB = parameters[j]
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
        else: # Just single threaded
            #print( self.USXFilenamesObject.getConfirmedFilenameTuples() ); halt
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenameTuples():
                UBB = USXXMLBibleBook( self, BBB )
                UBB.load( filename, self.givenFolderName, self.encoding )
                UBB.validateMarkers()
                #print( UBB )
                self.saveBook( UBB )
                #self.books[BBB] = UBB
                ## Make up our book name dictionaries while we're at it
                #assumedBookNames = UBB.getAssumedBookNames()
                #for assumedBookName in assumedBookNames:
                    #self.BBBToNameDict[BBB] = assumedBookName
                    #assumedBookNameLower = assumedBookName.lower()
                    #self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    #self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    #if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "USXXMLBible.loadBooks: Didn't find any regularly named USX files in {!r}".format( self.givenFolderName ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USX file)
                isUSX = False
                thisPath = os.path.join( self.givenFolderName, thisFilename )
                try:
                    with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                        for line in possibleUSXFile:
                            if line.startswith( '\\id ' ):
                                USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Have possible USX ID {!r}".format( USXId ) )
                                BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USXId )
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "BBB is {!r}".format( BBB ) )
                                isUSX = True
                            break # We only look at the first line
                except UnicodeDecodeError: isUSX = False
                if isUSX:
                    UBB = USXXMLBibleBook( self, BBB )
                    UBB.load( self.givenFolderName, thisFilename, self.encoding )
                    UBB.validateMarkers()
                    print( UBB )
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            if self.books: print( "USXXMLBible.loadBooks: Found {} irregularly named USX files".format( len(self.books) ) )
        self.doPostLoadProcessing()
    # end of USXXMLBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class USXXMLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    testData = (
                ("Matigsalug3", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/",),
                #("Matigsalug4", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/",),
                #("Matigsalug5", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/",),
                ) # You can put your USX test folder here

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        for j, (name, testFolder) in enumerate( testData ):
            print( "\nA{}: Testfolder is: {}".format( j+1, testFolder ) )
            result1 = USXXMLBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}a".format( j+1 ), result1 )
            result2 = USXXMLBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}b".format( j+1 ), result2 )
            result3 = USXXMLBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USX TestA{}c".format( j+1 ), result3 )

    if 1:
        for j, (name, testFolder) in enumerate( testData ):
            print( "\nB{}: Testfolder is: {} ({})".format( j+1, testFolder, name ) )
            if os.access( testFolder, os.R_OK ):
                UB = USXXMLBible( testFolder, name )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                if BibleOrgSysGlobals.commandLineArguments.export: UB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                #UBErrors = UB.getErrors()
                # print( UBErrors )
                #print( UB.getVersification () )
                #print( UB.getAddedUnits () )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "B{}: Sorry, test folder {!r} is not readable on this computer.".format( j+1, testFolder ) )

        #if BibleOrgSysGlobals.commandLineArguments.export:
        #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( ProgName, ProgVersion ) )
        #       pass

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ShortProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ShortProgName, ProgVersion )
# end of USXXMLBible.py