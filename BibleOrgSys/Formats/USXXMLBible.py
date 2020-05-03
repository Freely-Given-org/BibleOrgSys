#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBible.py
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012-2020 Robert Hunt
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
Module for defining and manipulating complete or partial USX Bibles.
"""
from gettext import gettext as _
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
from BibleOrgSys.InputOutput.USXFilenames import USXFilenames
from BibleOrgSys.Formats.USXXMLBibleBook import USXXMLBibleBook
from BibleOrgSys.Bible import Bible


LAST_MODIFIED_DATE = '2020-04-22' # by RJH
SHORT_PROGRAM_NAME = "USXXMLBibleHandler"
PROGRAM_NAME = "USX XML Bible handler"
PROGRAM_VERSION = '0.38'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False

logger = logging.getLogger( SHORT_PROGRAM_NAME )


def USXXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USX Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USX Bible is found,
        returns the loaded USXXMLBible object.
    """
    vPrint( 'Info', debuggingThisModule, "USXXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
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
    vPrint( 'Verbose', debuggingThisModule, " USXXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    vPrint( 'Info', debuggingThisModule, UFns )
    #filenameTuples = UFns.getPossibleFilenameTuples( strictCheck=True )
    #vPrint( 'Quiet', debuggingThisModule, 'P', len(filenameTuples) )
    filenameTuples = UFns.getConfirmedFilenameTuples( strictCheck=True )
    #vPrint( 'Quiet', debuggingThisModule, 'C', len(filenameTuples) )
    vPrint( 'Verbose', debuggingThisModule, "Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: vPrint( 'Quiet', debuggingThisModule, "  Found {} USX file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, "USXXMLBibleFileCheck got", numFound, givenFolderName )
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
        vPrint( 'Verbose', debuggingThisModule, "    USXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ): foundSubfiles.append( something )
        except PermissionError: pass # can't read folder, e.g., system folder

        # See if there's an USX Bible with standard Paratext style filenames here in this folder
        UFns = USXFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        vPrint( 'Info', debuggingThisModule, UFns )
        #filenameTuples = UFns.getPossibleFilenameTuples()
        filenameTuples = UFns.getConfirmedFilenameTuples( strictCheck=True )
        vPrint( 'Verbose', debuggingThisModule, "Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: vPrint( 'Quiet', debuggingThisModule, "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "  Found {} USX file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, "USXXMLBibleFileCheck foundProjects", numFound, foundProjects )
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
            vPrint( 'Quiet', debuggingThisModule, "USXXMLBible preload() from {}".format( self.sourceFolder ) )

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.error( "USXXMLBible: File {!r} is unreadable".format( self.givenFolderName ) )

        # Find the filenames of all our books
        self.USXFilenamesObject = USXFilenames( self.givenFolderName )
        #vPrint( 'Quiet', debuggingThisModule, "DDFSDF", self.USXFilenamesObject )
        #vPrint( 'Quiet', debuggingThisModule, "DFSFGE", self.USXFilenamesObject.getPossibleFilenameTuples() )
        #vPrint( 'Quiet', debuggingThisModule, "SDFSDQ", self.USXFilenamesObject.getConfirmedFilenameTuples() )
        self.possibleFilenameDict = {}
        filenameTuples = self.USXFilenamesObject.getConfirmedFilenameTuples()
        if not filenameTuples: # Try again
            filenameTuples = self.USXFilenamesObject.getPossibleFilenameTuples()
        for BBB,filename in filenameTuples:
            self.availableBBBs.add( BBB )
            self.possibleFilenameDict[BBB] = filename
        #vPrint( 'Quiet', debuggingThisModule, "GHJGHR", self.possibleFilenameDict ); halt

        self.preloadDone = True
    # end of USXXMLBible.preload


    def loadBook( self, BBB:str, filename=None ):
        """
        NOTE: You should ensure that preload() has been called first.
        """
        vPrint( 'Never', debuggingThisModule, "USXXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.preloadDone

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("  USXXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USXXMLBibleBook( self, BBB )
        UBB.load( filename, self.givenFolderName, self.encoding )
        UBB.validateMarkers()
        #for j, something in enumerate( UBB._processedLines ):
            #vPrint( 'Quiet', debuggingThisModule, j, something )
            #if j > 100: break
        #for j, something in enumerate( sorted(UBB._CVIndex) ):
            #vPrint( 'Quiet', debuggingThisModule, j, something )
            #if j > 50: break
        self.stashBook( UBB )
        self.bookNeedsReloading[BBB] = False
    # end of USXXMLBible.loadBook


    def _loadBookMP( self, BBB:str, filename=None ):
        """
        Used for multiprocessing.

        NOTE: You should ensure that preload() has been called first.
        """
        vPrint( 'Never', debuggingThisModule, "USXXMLBible._loadBookMP( {}, {} )".format( BBB, filename ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.preloadDone

        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("  USXXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USXXMLBibleBook( self, BBB )
        UBB.load( filename, self.givenFolderName, self.encoding )
        UBB.validateMarkers()
        #for j, something in enumerate( UBB._processedLines ):
            #vPrint( 'Quiet', debuggingThisModule, j, something )
            #if j > 100: break
        #for j, something in enumerate( sorted(UBB._CVIndex) ):
            #vPrint( 'Quiet', debuggingThisModule, j, something )
            #if j > 50: break
        return UBB
    # end of USXXMLBible._loadBookMP


    def loadBooks( self ):
        """
        Load the books.
        """
        vPrint( 'Normal', debuggingThisModule, _("USXXMLBible: Loading {} books from {}…").format( self.name, self.givenFolderName ) )

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
            vPrint( 'Quiet', debuggingThisModule, "USXXMLBible.loadBooks: Couldn't find any files in {!r}".format( self.givenFolderName ) )
            return # No use continuing

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            # Load all the books as quickly as possible
            parameters = []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenameTuples():
                parameters.append( BBB )
            #vPrint( 'Quiet', debuggingThisModule, "parameters", parameters )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} {} books using {} processes…").format( len(parameters), 'USX', BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed.") )
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self._loadBookMP, parameters ) # have the pool do our loads
                #vPrint( 'Quiet', debuggingThisModule, "results", results )
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
            #vPrint( 'Quiet', debuggingThisModule, self.USXFilenamesObject.getConfirmedFilenameTuples() ); halt
            for BBB,filename in self.possibleFilenameDict.items():
                self.loadBook( BBB, filename ) # also saves it
                #UBB = USXXMLBibleBook( self, BBB )
                #UBB.load( filename, self.givenFolderName, self.encoding )
                #UBB.validateMarkers()
                #vPrint( 'Quiet', debuggingThisModule, UBB )
                #self.stashBook( UBB )

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            vPrint( 'Info', debuggingThisModule, "USXXMLBible.loadBooks: Didn't find any regularly named USX files in {!r}".format( self.givenFolderName ) )
            #for thisFilename in foundFiles:
                ## Look for BBB in the ID line (which should be the first line in a USX file)
                #isUSX = False
                #thisPath = os.path.join( self.givenFolderName, thisFilename )
                #try:
                    #with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                        #for line in possibleUSXFile:
                            #if line.startswith( '\\id ' ):
                                #USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                                #vPrint( 'Info', debuggingThisModule, "Have possible USX ID {!r}".format( USXId ) )
                                #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USXId )
                                #vPrint( 'Info', debuggingThisModule, "BBB is {!r}".format( BBB ) )
                                #isUSX = True
                            #break # We only look at the first line
                #except UnicodeDecodeError: isUSX = False
                #if isUSX:
                    #UBB = USXXMLBibleBook( self, BBB )
                    #UBB.load( self.givenFolderName, thisFilename, self.encoding )
                    #UBB.validateMarkers()
                    #vPrint( 'Quiet', debuggingThisModule, UBB )
                    #self.books[BBB] = UBB
                    ## Make up our book name dictionaries while we're at it
                    #assumedBookNames = UBB.getAssumedBookNames()
                    #for assumedBookName in assumedBookNames:
                        #self.BBBToNameDict[BBB] = assumedBookName
                        #assumedBookNameLower = assumedBookName.lower()
                        #self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            #if self.books: vPrint( 'Quiet', debuggingThisModule, "USXXMLBible.loadBooks: Found {} irregularly named USX files".format( len(self.books) ) )

        self.doPostLoadProcessing()
    # end of USXXMLBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class USXXMLBible



bkName_RE = '[1-3]? ?[A-Z][a-zA-Z]{1,4}'
CorV_RE = '[1-9][0-9]{0,2}'
CV_RE = f'{CorV_RE}:{CorV_RE}'
IOR_RE = re.compile( r'<char style="ior">(.+?)</char>' )

def makeRefs( BBB:str, C:str, V:str, BRL, text:str ) -> str:
    """
    Used for ior and xt fields to make computer-readable ref fields

    TODO: Still need to handle these refs:
            'Lib 23:33-36,39-43'
            '1Har 10:14-22,27'
            'Diy 31:6-7,23.'
    """
    vPrint( 'Verbose', debuggingThisModule, f'makeRefs( {text} )…' )
    currentBBB = BBB
    bitResults = []
    for bit in text.split( ';' ):
        bitResult = bit
        match = re.match( rf'(\s*)({bkName_RE}) ({CV_RE}[-–]{CV_RE})(\s*\.?)$', bit )
        if match:  # e.g., Jos 3:4-4:5
            # print( f"MatchA '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}'")
            currentBBB = BRL.getBBBFromText( match.group(2) )
            USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
            if USFMBookCode:
                bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3).replace("–","-")}">{match.group(2)} {match.group(3)}</ref>{match.group(4)}'
        else:
            match = re.match( rf'(\s*)({bkName_RE}) ({CorV_RE}):({CorV_RE})([-–])({CorV_RE})(, ?)({CorV_RE})(\s*\.?)$', bit )
            if match: # e.g., Jos 3:4-7,12
                # print( f"MatchB '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}' '{match.group(5)}' '{match.group(6)}' '{match.group(7)}' '{match.group(8)}' '{match.group(9)}'")
                currentBBB = BRL.getBBBFromText( match.group(2) )
                USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                if USFMBookCode:
                    bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3)}:{match.group(4)}{match.group(5).replace("–","-")}{match.group(6)}">{match.group(2)} {match.group(3)}:{match.group(4)}{match.group(5)}{match.group(6)}</ref>{match.group(7)}<ref loc="{USFMBookCode} {match.group(3)}:{match.group(8)}">{match.group(8)}</ref>{match.group(9)}'
            else:
                match = re.match( rf'(\s*)({bkName_RE}) ({CV_RE}[-–]{CorV_RE})(\s*\.?)$', bit )
                if match: # e.g., Jos 3:4-7
                    # print( f"MatchC '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}'")
                    currentBBB = BRL.getBBBFromText( match.group(2) )
                    USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                    if USFMBookCode:
                        bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3).replace("–","-")}">{match.group(2)} {match.group(3)}</ref>{match.group(4)}'
                else:
                    match = re.match( rf'(\s*)({bkName_RE}) ({CorV_RE}):({CorV_RE})(, ?)({CorV_RE})(\s*\.?)$', bit )
                    if match: # e.g., Jos 3:4,9
                        # print( f"MatchD '{match.group(1)}' '{match.group(2)}' '{match.group(3)}':'{match.group(4)}' '{match.group(5)}' '{match.group(6)}' '{match.group(7)}'")
                        currentBBB = BRL.getBBBFromText( match.group(2) )
                        USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                        if USFMBookCode:
                            bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3)}:{match.group(4)}">{match.group(2)} {match.group(3)}:{match.group(4)}</ref>{match.group(5)}<ref loc="{USFMBookCode} {match.group(3)}:{match.group(6)}">{match.group(6)}</ref>{match.group(7)}'
                    else:
                        match = re.match( rf'(\s*)({bkName_RE}) ({CV_RE})(\s*\.?)$', bit )
                        if match: # e.g., Jos 3:4
                            # print( f"MatchE '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}'")
                            currentBBB = BRL.getBBBFromText( match.group(2) )
                            USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                            if USFMBookCode:
                                bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3)}">{match.group(2)} {match.group(3)}</ref>{match.group(4)}'
                        else:
                            match = re.match( rf'(\s*)({bkName_RE}) ({CorV_RE})(\s*\.?)$', bit )
                            if match: # e.g., Jud 4
                                # print( f"MatchF '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}'")
                                currentBBB = BRL.getBBBFromText( match.group(2) )
                                # print( currentBBB )
                                assert BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( currentBBB )
                                USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                                if USFMBookCode:
                                    bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(3)}">{match.group(2)} {match.group(3)}</ref>{match.group(4)}'
                            else:
                                match = re.match( rf'(\s*)({CV_RE}[-–]{CV_RE})(\s*\.?)$', bit )
                                if match: # e.g., 1:2-3:4
                                    # print( f"MatchAA '{match.group(1)}' '{match.group(2)}' '{match.group(3)}'")
                                    USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                                    if USFMBookCode:
                                        bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(2).replace("–","-")}">{match.group(2)}</ref>{match.group(3)}'
                                else:
                                    match = re.match( rf'(\s*)({CV_RE}[-–]{CorV_RE})(\s*\.?)$', bit )
                                    if match: # e.g., 1:2-6
                                        # print( f"MatchBB '{match.group(1)}' '{match.group(2)}' '{match.group(3)}'")
                                        USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                                        if USFMBookCode:
                                            bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(2).replace("–","-")}">{match.group(2)}</ref>{match.group(3)}'
                                    else:
                                        match = re.match( rf'(\s*)({CorV_RE}):({CorV_RE})(, ?)({CorV_RE})(\s*\.?)$', bit )
                                        if match: # e.g., 3:5,9
                                            # print( f"MatchCC '{match.group(1)}' '{match.group(2)}' '{match.group(3)}' '{match.group(4)}' '{match.group(5)}' '{match.group(6)}'")
                                            USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                                            if USFMBookCode:
                                                bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(2)}:{match.group(3)}">{match.group(2)}:{match.group(3)}</ref>{match.group(4)}<ref loc="{USFMBookCode} {match.group(2)}:{match.group(5)}">{match.group(5)}</ref>{match.group(6)}'
                                        else:
                                            match = re.match( rf'(\s*)({CV_RE})(\s*\.?)$', bit )
                                            if match: # e.g., 3:5
                                                # print( f"MatchDD '{match.group(1)}' '{match.group(2)}' '{match.group(3)}'")
                                                USFMBookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( currentBBB ).upper()
                                                if USFMBookCode:
                                                    bitResult = f'{match.group(1)}<ref loc="{USFMBookCode} {match.group(2)}">{match.group(2)}</ref>{match.group(3)}'
                                            else: logging.critical( f"toUSX makeRefs unable to parse {BBB} {C}:{V} '{bit}'")
        bitResults.append( bitResult )
    refString = ';'.join( bitResults )
    vPrint( 'Never', debuggingThisModule, f"  makeRefs returning {refString}" )
    return refString
# end of makeRefs for USX3


def createUSXXMLBible( self, outputFolderpath, controlDict, validationSchema ) -> bool:
    """
    Or toUSX3XML

    self is a BibleWriter object.

    Using settings from the given control file,
        converts the USFM information to UTF-8 USX 3.0 XML files.

    See https://ubsicap.github.io/usx/ for more information.

    If a schema is given (either a path or URL), the XML output files are validated.
    """
    import zipfile
    import tarfile

    from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS
    from BibleOrgSys.Reference.USFM3Markers import USFM_PRECHAPTER_MARKERS
    from BibleOrgSys.InputOutput.MLWriter import MLWriter
    from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
    from BibleOrgSys.Reference.BibleReferences import BibleReferenceList

    vPrint( 'Normal', debuggingThisModule, f"Running createUSXXMLBible( {outputFolderpath} )…" )
    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

    ALL_CHAR_MARKERS = BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )

    filesFolder = os.path.join( outputFolderpath, 'USX3Files/' )
    if not os.access( filesFolder, os.F_OK ): os.makedirs( filesFolder ) # Make the empty folder if there wasn't already one there

    ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []


    def writeUSX3Book( BBB, bkData ):
        """ Writes a book to the filesFolder. """


        def handleInternalTextMarkersForUSX3( originalText ):
            """
            Handles character formatting markers within the originalText.
            Tries to find pairs of markers and replaces them with html char segments.
            """
            if not originalText: return ''
            if '\\' not in originalText: return originalText
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "toUSXXML:hITM4USX:", BBB, C,V, marker, "'"+originalText+"'" )
            markerList = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( originalText ),
                                        key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
            # for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
            #     pass

            adjText = originalText
            haveOpenChar = False
            for charMarker in ALL_CHAR_MARKERS:
                #vPrint( 'Quiet', debuggingThisModule, "handleInternalTextMarkersForUSX3", charMarker )
                # Handle USFM character markers
                fullCharMarker = '\\' + charMarker + ' '
                if fullCharMarker in adjText:
                    if haveOpenChar:
                        adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                        logger.info( "toUSXXML: USX export had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C,V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                    adjText = adjText.replace( fullCharMarker, f'{"</char>" if haveOpenChar else ""}<char style="{charMarker}"CLOSED_BIT>' )
                    haveOpenChar = True
                endCharMarker = '\\' + charMarker + '*'
                if endCharMarker in adjText:
                    if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                        logger.error( "toUSXXML: Ignored extra {!r} closing marker in {} {}:{} {}:{!r} now {!r}".format( charMarker, BBB, C,V, marker, originalText, adjText ) )
                        adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                    else: # looks good
                        adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                        adjText = adjText.replace( endCharMarker, '</char>' )
                        haveOpenChar = False
            if '\\z' in adjText:
                # Handle custom (character) markers
                while True:
                    matchOpen = re.search( r'\\z([\w\d]+?) ', adjText )
                    if not matchOpen: break
                    #vPrint( 'Quiet', debuggingThisModule, f"Matched custom marker open '{matchOpen.group(0)}'" )
                    adjText = adjText[:matchOpen.start(0)] + f'<char style="z{matchOpen.group(1)}"CLOSED_BIT>' + adjText[matchOpen.end(0):]
                    haveOpenChar = True
                    #vPrint( 'Quiet', debuggingThisModule, "adjText", adjText )
                    matchClose = re.search( r'\\z{}\*'.format( matchOpen.group(1) ), adjText )
                    if matchClose:
                        #vPrint( 'Quiet', debuggingThisModule, f"Matched custom marker close '{matchClose.group(0)}'" )
                        adjText = adjText[:matchClose.start(0)] + '</char>' + adjText[matchClose.end(0):]
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            haveOpenChar = False
                        #vPrint( 'Quiet', debuggingThisModule, "adjText", adjText )
            if haveOpenChar:
                adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                logger.info( "toUSXXML: Had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C,V, marker, originalText, adjText ) )
            if '\\' in adjText:
                logger.critical( "toUSXXML: Didn't handle a backslash in {} {}:{} {}:{!r} now {!r}".format( BBB, C,V, marker, originalText, adjText ) )
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt
            if 'CLOSED_BIT' in adjText:
                logger.critical( "toUSXXML: Didn't handle a character style correctly in {} {}:{} {}:{!r} now {!r}".format( BBB, C,V, marker, originalText, adjText ) )
            if '"ior"' in adjText: # Usually in \\iot lines
                # Make these into live references
                match = IOR_RE.search( adjText, 0 )
                while match:
                    adjText = f'{adjText[:match.start()]}<char style="ior">{makeRefs( BBB, C,V, self.genericBRL, match.group(1) )}</char>{adjText[match.end():]}'
                    match = IOR_RE.search( adjText, match.end() )
            return adjText
        # end of toUSXXML.handleInternalTextMarkersForUSX3


        def handleNotes( text:str, extras ) -> str:
            """ Integrate notes into the text again. """

            def processXRef( USXxref:str ) -> str:
                """
                Return the USX XML for the processed cross-reference (xref).

                NOTE: The parameter here already has the /x and /x* removed.

                \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                    gives
                <note style="x" caller="-"><char style="xo" closed="false">1:3: </char><char style="xt">2Kur 4:6.</char></note>
                """
                USXxrefXML = '\n    <note '
                xoOpen = xtOpen = False
                for j,token in enumerate(USXxref.split('\\')):
                    #vPrint( 'Quiet', debuggingThisModule, "toUSXXML:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                    lcToken = token.lower()
                    if j==0: # The first token (but the x has already been removed)
                        USXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                            .format( token.rstrip() )
                    elif lcToken.startswith('xo '): # xref reference follows
                        if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                            USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            xoOpen = False
                        if xtOpen: # if we have multiple cross-references one after the other
                            USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            xtOpen = False
                        adjToken = token[3:]
                        USXxrefXML += '<char style="xo"'
                        xoOpen = True
                    elif lcToken.startswith('xo*'):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xoOpen and not xtOpen
                        USXxrefXML += '>' + adjToken + '</char>'
                        xoOpen = False
                    elif lcToken.startswith('xt '): # xref text follows
                        if xtOpen: # Multiple xt's in a row
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xoOpen
                            USXxrefXML += f' closed="false">{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                        if xoOpen:
                            USXxrefXML += f' closed="false">{adjToken}</char>'
                            xoOpen = False
                        adjToken = token[3:]
                        USXxrefXML += '<char style="xt"'
                        xtOpen = True
                    elif lcToken.startswith('xt*'):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xtOpen and not xoOpen
                        USXxrefXML += f'>{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                        xtOpen = False
                    #elif lcToken in ('xo*','xt*','x*',):
                    #    pass # We're being lazy here and not checking closing markers properly
                    else:
                        logger.critical( _("toUSXXML: Unprocessed {!r} token in {} {}:{} xref {!r}").format( token, BBB, C,V, USXxref ) )
                if xoOpen:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                    USXxrefXML += f' closed="false">{adjToken}</char>'
                    xoOpen = False
                if xtOpen:
                    USXxrefXML += f' closed="false">{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                USXxrefXML += '</note>'
                return USXxrefXML
            # end of toUSXXML.processXRef

            def processFootnote( USXfootnote:str ) -> str:
                """
                Return the USX XML for the processed footnote.

                NOTE: The parameter here already has the /f and /f* removed.

                \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                    gives
                <note style="f" caller="+"><char style="fr" closed="false">2:23 </char><char style="ft">Te Hibruwanen: bayew egpekegsahid ka ngaran te “malitan” wey “lukes.”</char></note>
                """
                USXfootnoteXML = '\n    <note '
                frOpen = fTextOpen = fCharOpen = xtOpen = False
                for j,token in enumerate(USXfootnote.split('\\')):
                    #vPrint( 'Quiet', debuggingThisModule, f"USX processFootnote {j}: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                    lcToken = token.lower()
                    if j==0:
                        USXfootnoteXML += f'caller="{token.rstrip()}" style="f">'
                    elif lcToken.startswith('fr '): # footnote reference follows
                        if frOpen:
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                            logger.error( _("toUSXXML: Two consecutive fr fields in {} {}:{} footnote {!r}").format( token, BBB, C,V, USXfootnote ) )
                            USXfootnoteXML += f' closed="false">{adjToken}</char>'
                            frOpen = False
                        if fTextOpen:
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                            USXfootnoteXML += f' closed="false">{adjToken}</char>'
                            fTextOpen = False
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                        adjToken = token[3:]
                        USXfootnoteXML += '<char style="fr"'
                        frOpen = True
                    elif lcToken.startswith('fr* '):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert frOpen and not fTextOpen and not fCharOpen
                        USXfootnoteXML += f'>{adjToken}</char>'
                        frOpen = False
                    elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                        if fCharOpen:
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                            USXfootnoteXML += f'>{adjToken}</char>'
                            fCharOpen = False
                        if frOpen:
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                            USXfootnoteXML += f' closed="false">{adjToken}</char>'
                            frOpen = False
                        if fTextOpen:
                            USXfootnoteXML += f' closed="false">{adjToken}</char>'
                            fTextOpen = False
                        fMarker = lcToken.split()[0] # Get the bit before the space
                        USXfootnoteXML += f'<char style="{fMarker}"'
                        adjToken = token[len(fMarker)+1:] # Get the bit after the space
                        #vPrint( 'Quiet', debuggingThisModule, "{!r} {!r}".format( fMarker, adjToken ) )
                        fTextOpen = True
                    elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                        #if BibleOrgSysGlobals.debugFlag:
                            #vPrint( 'Quiet', debuggingThisModule, "toUSXXML.processFootnote: Problem with {} {} {} in {} {}:{} footnote {!r} part {!r}".format( fTextOpen, frOpen, fCharOpen, BBB, C,V, USXfootnote, lcToken ) )
                            #assert fTextOpen and not frOpen and not fCharOpen
                        if frOpen or fCharOpen or not fTextOpen:
                            logger.error( "toUSXXML.processFootnote: Closing problem at {} {}:{} in footnote {!r}".format( BBB, C,V, USXfootnote ) )
                        USXfootnoteXML += f'>{adjToken}</char>'
                        fTextOpen = False
                    elif lcToken.startswith('xt '): # xref text follows
                        if xtOpen: # Multiple xt's in a row
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xoOpen
                            USXfootnoteXML += f' closed="false">{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                        adjToken = token[3:]
                        USXfootnoteXML += '<char style="xt"'
                        xtOpen = True
                    elif lcToken.startswith('xt*'):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xtOpen and not xoOpen
                        USXfootnoteXML += f'>{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                        xtOpen = False
                    elif lcToken.startswith('z'):
                        #vPrint( 'Quiet', debuggingThisModule, f"USX processFootnote {j} custom: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                        ixSpace = lcToken.find( ' ' )
                        if ixSpace == -1: ixSpace = 9999
                        ixAsterisk = lcToken.find( '*' )
                        if ixAsterisk == -1: ixAsterisk = 9999
                        if ixSpace < ixAsterisk: # Must be an opening marker
                            if fCharOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            if fTextOpen:
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                fTextOpen = False
                            marker = lcToken[:ixSpace]
                            USXfootnoteXML += f'<char style="{marker}"'
                            adjToken = token[len(marker)+1:] # Get the bit after the space
                            fCharOpen = marker
                        elif ixAsterisk < ixSpace: # Must be an closing marker
                            if not fCharOpen:
                                logger.error( "toUSXXML.processFootnote: Closing problem at {} {}:{} in custom footnote {!r}".format( BBB, C,V, USXfootnote ) )
                            USXfootnoteXML += f'>{adjToken}</char>'
                            fCharOpen = False
                        else:
                            logger.error( "toUSXXML.processFootnote: Marker roblem at {} {}:{} in custom footnote {!r}".format( BBB, C,V, USXfootnote ) )
                    else: # Could be character formatting (or closing of character formatting)
                        subTokens = lcToken.split()
                        firstToken = subTokens[0]
                        #vPrint( 'Quiet', debuggingThisModule, "ft", firstToken )
                        if firstToken in ALL_CHAR_MARKERS: # Yes, confirmed
                            if fCharOpen: # assume that the last one is closed by this one
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            USXfootnoteXML += f'<char style="{firstToken}"'
                            adjToken = token[len(firstToken)+1:] # Get the bit after the space
                            fCharOpen = firstToken
                        else: # The problem is that a closing marker doesn't have to be followed by a space
                            if firstToken[-1]=='*' and firstToken[:-1] in ALL_CHAR_MARKERS: # it's a closing tag (that was followed by a space)
                                if fCharOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                        logger.warning( _("toUSXXML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C,V, USXfootnote ) )
                                    USXfootnoteXML += f'>{adjToken}</char>'
                                    fCharOpen = False
                                logger.warning( _("toUSXXML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C,V, USXfootnote ) )
                            else:
                                ixAS = firstToken.find( '*' )
                                #vPrint( 'Quiet', debuggingThisModule, firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in ALL_CHAR_MARKERS: # it's a closing tag
                                    if fCharOpen:
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                                            assert not frOpen
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logger.warning( _("toUSXXML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C,V, USXfootnote ) )
                                        USXfootnoteXML += f'>{adjToken}</char>'
                                        fCharOpen = False
                                    logger.warning( _("toUSXXML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C,V, USXfootnote ) )
                                else:
                                    logger.critical( _("toUSXXML: Unprocessed {!r} token in {} {}:{} footnote {!r}").format( firstToken, BBB, C,V, USXfootnote ) )
                                    vPrint( 'Quiet', debuggingThisModule, "toUSXXML ALL_CHAR_MARKERS", ALL_CHAR_MARKERS )
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt
                #vPrint( 'Quiet', debuggingThisModule, "  ", frOpen, fCharOpen, fTextOpen )
                if frOpen:
                    logger.warning( _("toUSXXML: Unclosed 'fr' token in {} {}:{} footnote {!r}").format( BBB, C,V, USXfootnote) )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen and not fTextOpen
                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                if fCharOpen:
                    logger.info( _("toUSXXML: Unclosed {!r} token in {} {}:{} footnote {!r}").format( fCharOpen, BBB, C,V, USXfootnote) )
                if fTextOpen or fCharOpen:
                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                if xtOpen:
                    USXfootnoteXML += f' closed="false">{makeRefs( BBB, C,V, self.genericBRL, adjToken )}</char>'
                USXfootnoteXML += '</note>'
                #vPrint( 'Quiet', debuggingThisModule, '', USXfootnote, USXfootnoteXML )
                return USXfootnoteXML
            # end of toUSXXML.processFootnote


            # Main code for handleNotes
            adjText = text
            if extras:
                offset = 0
                for extra in extras: # do any footnotes and cross-references
                    extraType, extraIndex, extraText, cleanExtraText = extra
                    #vPrint( 'Quiet', debuggingThisModule, "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C,V, text, extraType, extraIndex, extraText ) )
                    adjIndex = extraIndex - offset
                    lenT = len( adjText )
                    if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logger.warning( _("toUSXXML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                        vPrint( 'Quiet', debuggingThisModule, "toUSXXML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C,V, extraIndex, offset, len(text), adjIndex ) )
                        vPrint( 'Quiet', debuggingThisModule, "  Verse={!r}".format( text ) )
                        vPrint( 'Quiet', debuggingThisModule, "  Extras={!r}".format( extras ) )
                    #assert 0 <= adjIndex <= len(verse)
                    #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                    #if adjText!=extraText: vPrint( 'Quiet', debuggingThisModule, "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( extraText )
                        #vPrint( 'Quiet', debuggingThisModule, "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( extraText )
                        #vPrint( 'Quiet', debuggingThisModule, "xr got", extra )
                    elif extraType == 'fig':
                        logger.critical( "USXXML figure not handled yet" )
                        extra = '' # temp
                        #extra = processFigure( extraText )
                        #vPrint( 'Quiet', debuggingThisModule, "fig got", extra )
                    elif extraType == 'str':
                        extra = '' # temp
                    elif extraType == 'sem':
                        extra = '' # temp
                    elif extraType == 'vp':
                        extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                    elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, extraType ); halt
                    #vPrint( 'Quiet', debuggingThisModule, "was", verse )
                    adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                    offset -= len( extra )
                    #vPrint( 'Quiet', debuggingThisModule, "now", verse )
            return adjText
        # end of toUSXXML.handleNotes


        # Main code for writeUSX3Book
        USXAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
        USXNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSXNumber( BBB )
        if not USXAbbrev:
            logger.error( "toUSXXML: Can't write {} USX book because no USFM code available".format( BBB ) )
            unhandledBooks.append( BBB )
            return
        if not USXNumber:
            logger.error( "toUSXXML: Can't write {} USX book because no USX number available".format( BBB ) )
            unhandledBooks.append( BBB )
            return

        version = 3.0
        C, V = '-1', '-1' # So first/id line starts at -1:0
        xw = MLWriter( BibleOrgSysGlobals.makeSafeFilename( USXNumber+USXAbbrev+'.usx' ), filesFolder )
        xw.setHumanReadable()
        xw.spaceBeforeSelfcloseTag = True
        xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
        xw.writeLineOpen( 'usx', (('version','3.0') if version>=3 else None ) )
        haveOpenPara = paraJustOpened = False
        haveOpenVerse = needToCloseVerse = False
        gotVP = None
        # marker = None
        # closedV = False
        for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
            # lastMarker = marker
            marker, originalMarker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getOriginalMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
            if marker == '¬v':
                assert haveOpenVerse
                haveOpenVerse = False
                assert not needToCloseVerse
                needToCloseVerse = True
                continue
            elif '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker in ('v=','cl¤'):
                continue # Just ignore added markers — not needed here
            if marker in USFM_PRECHAPTER_MARKERS:
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert C=='-1' or marker=='rem' or marker.startswith('mte')
                V = str( int(V) + 1 )
            getMarkerContentType = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType( marker )
            # if BBB=='RUT': vPrint( 'Quiet', debuggingThisModule,
            #     f"{BBB} {C}:{V} {marker}({originalMarker})='{text}'{'+extras' if extras else ''} mCT={getMarkerContentType} hOP={haveOpenPara} pJO={paraJustOpened} hOV={haveOpenVerse} nCV={needToCloseVerse}" )

            adjText = handleNotes( text, extras )
            if marker == 'id':
                if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                    logger.critical( "toUSXXML: Book {}{} has a id line inside an open paragraph: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw.writeLineClose( 'para' )
                    haveOpenPara = False
                adjTxLen = len( adjText )
                if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                    logger.warning( "toUSXXML: Book {}{} has a non-standard id line: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                if adjText[0:3] != USXAbbrev:
                    logger.error( "toUSXXML: Book {}{} might have incorrect code on id line — we got: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX3(adjText), [('code',USXAbbrev),('style',marker)] )
                else: xw.writeLineOpenSelfclose( 'book', [('code',USXAbbrev),('style',marker)] )
                #elif not text: logger.error( "toUSXXML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )

            elif marker == 'c':
                assert not haveOpenVerse
                if haveOpenPara:
                    if needToCloseVerse:
                        xw.removeFinalNewline( suppressFollowingIndent=True )
                        xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                        needToCloseVerse = False # So we don't do it again
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw.writeLineClose( 'para' )
                    haveOpenPara = False
                else: assert not needToCloseVerse
                if C != '-1':
                    xw.writeLineOpenSelfclose( 'chapter', [('eid',f'{USXAbbrev} {C}')] )
                #vPrint( 'Quiet', debuggingThisModule, BBB, 'C', repr(text), repr(adjText) )
                C, V = text, '0' # not adjText!
                xw.writeLineOpenSelfclose ( 'chapter', [('number',C),('style','c'),('sid',f'{USXAbbrev} {C}')] )
                if adjText != text:
                    logger.warning( "toUSXXML: Lost additional note text on c for {} {!r}".format( BBB, C ) )
            elif marker == 'c~': # Don't really know what this stuff is!!!
                if not adjText: logger.warning( "toUSXXML: Missing text for c~" ); continue
                # TODO: We haven't stripped out character fields from within the text — not sure how USX handles them yet
                xw.removeFinalNewline( suppressFollowingIndent=True )
                xw.writeLineText( handleInternalTextMarkersForUSX3(adjText), noTextCheck=True ) # no checks coz might already have embedded XML
            elif marker == 'c#': # Chapter number added for printing
                ignoredMarkers.add( marker ) # Just ignore it completely
            elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                gotVP = adjText # Just remember it for now
            elif marker == 'v':
                if needToCloseVerse:
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw._writeToBuffer( ' ' ) # Space between verses (unless at end of paragraph)
                    xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                    needToCloseVerse = False
                else: assert not haveOpenVerse
                V = adjText
                haveOpenVerse = True
                if gotVP: # this is the verse number to be published
                    adjText = gotVP
                    gotVP = None
                if paraJustOpened: paraJustOpened = False
                else:
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    # xw._writeToBuffer( ' ' ) # Space between verses
                    # Remove anything that'll cause a big XML problem later
                if adjText:
                    xw.writeLineOpenSelfclose ( 'verse', [('number',adjText.replace('<','').replace('>','').replace('"','')),
                                                            ('style','v'),('sid',f'{USXAbbrev} {C}:{V}')] )

            elif marker in ('v~','p~',):
                if not adjText: logger.critical( "toUSXXML: Missing text for {}".format( marker ) ); continue
                xw.removeFinalNewline( suppressFollowingIndent=True )
                xw.writeLineText( handleInternalTextMarkersForUSX3(adjText), noTextCheck=True ) # no checks coz might already have embedded XML
                paraJustOpened = False
            elif getMarkerContentType == 'N': # N = never, e.g., b, nb
                if haveOpenPara:
                    if needToCloseVerse:
                        xw.removeFinalNewline( suppressFollowingIndent=True )
                        xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                        needToCloseVerse = False # So we don't do it again
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw.writeLineClose( 'para' )
                    haveOpenPara = False
                if adjText:
                    logger.error( "toUSXXML: {} {}:{} has a {} line containing text ({!r}) that was ignored".format( BBB, C,V, originalMarker, adjText ) )
                xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
            elif getMarkerContentType == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                if haveOpenPara:
                    if needToCloseVerse:
                        xw.removeFinalNewline( suppressFollowingIndent=True )
                        xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                        needToCloseVerse = False # So we don't do it again
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw.writeLineClose( 'para' )
                    haveOpenPara = False
                # if BBB=='RUT': print( f"S Have {C}:{V} oM={originalMarker} adjTxt={adjText}")
                styles = [('style',originalMarker),('vid',f'{USXAbbrev} {C}:{V}')] \
                                if haveOpenVerse else ('style',originalMarker)
                if adjText:
                    xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX3(adjText),
                                styles, noTextCheck=True ) # no checks coz might already have embedded XML
                else:
                    xw.writeLineOpen( 'para', styles )
                    paraJustOpened = True
                haveOpenPara = True
            else:
                #assert getMarkerContentType == 'A' # A = always, e.g.,  ide, mt, h, s, ip, etc.
                if getMarkerContentType != 'A':
                    logger.critical( "BibleWriter.toUSXXML: ToProgrammer — markerContentType should be 'A': {!r} is {!r} Why?".format( marker, getMarkerContentType ) )
                if haveOpenPara:
                    if needToCloseVerse:
                        xw.removeFinalNewline( suppressFollowingIndent=True )
                        xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                        needToCloseVerse = False # So we don't do it again
                    xw.removeFinalNewline( suppressFollowingIndent=True )
                    xw.writeLineClose( 'para' )
                    haveOpenPara = False
                xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX3(adjText), ('style',originalMarker if originalMarker else marker), noTextCheck=True ) # no checks coz might already have embedded XML
        if haveOpenPara:
            if needToCloseVerse:
                xw.removeFinalNewline( suppressFollowingIndent=True )
                xw.writeLineOpenSelfclose( 'verse', [('eid',f'{USXAbbrev} {C}:{V}')] )
                needToCloseVerse = False # So we don't do it again
            xw.removeFinalNewline( suppressFollowingIndent=True )
            xw.writeLineClose( 'para' )
        xw.writeLineClose( 'usx' )
        xw.close( writeFinalNL=False ) # Try to imitate Paratext output as closely as possible
        if validationSchema: return xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
    # end of toUSXXML.writeUSX3Book

    # Set-up our Bible reference system
    if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
        BOS = self.genericBOS
        BRL = self.genericBRL
    else:
        BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
        BRL = BibleReferenceList( BOS, BibleObject=None )

    vPrint( 'Info', debuggingThisModule, _("  Exporting to USX format…") )
    #USXOutputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( "USX output/' )
    #if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

    validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
    for BBB,bookData in self.books.items():
        bookResults = writeUSX3Book( BBB, bookData )
        if validationSchema:
            if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
            if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
            if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
    if validationSchema:
        if validationResults[0] > 0:
            with open( os.path.join( outputFolderpath, 'ValidationErrors.txt' ), 'wt', encoding='utf-8' ) as veFile:
                if validationResults[1]: veFile.write( validationResults[1] + '\n\n\n' ) # Normally empty
                if validationResults[2]: veFile.write( validationResults[2] )

    if ignoredMarkers:
        logger.info( "toUSXXML: Ignored markers were {}".format( ignoredMarkers ) )
        vPrint( 'Info', debuggingThisModule, "  " + _("ERROR: Ignored toUSXXML markers were {}").format( ignoredMarkers ) )
    if unhandledMarkers:
        logger.error( "toUSXXML: Unhandled markers were {}".format( unhandledMarkers ) )
        vPrint( 'Normal', debuggingThisModule, "  " + _("ERROR: Unhandled toUSXXML markers were {}").format( unhandledMarkers ) )
    if unhandledBooks:
        logger.warning( "toUSXXML: Unhandled books were {}".format( unhandledBooks ) )
        vPrint( 'Normal', debuggingThisModule, "  " + _("WARNING: Unhandled toUSXXML books were {}").format( unhandledBooks ) )

    # Now create a zipped collection
    vPrint( 'Info', debuggingThisModule, "  Zipping USX3 files…" )
    zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllUSX3Files.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
    for filename in os.listdir( filesFolder ):
        #if not filename.endswith( '.zip' ):
        filepath = os.path.join( filesFolder, filename )
        zf.write( filepath, filename ) # Save in the archive without the path
    zf.close()
    # Now create the gzipped file
    vPrint( 'Info', debuggingThisModule, "  GZipping USX3 files…" )
    tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX3Files.gzip' ), 'w:gz' )
    for filename in os.listdir( filesFolder ):
        if filename.endswith( '.usx' ):
            filepath = os.path.join( filesFolder, filename )
            tar.add( filepath, arcname=filename, recursive=False )
    tar.close()
    # Now create the bz2 file
    vPrint( 'Info', debuggingThisModule, "  BZipping USX3 files…" )
    tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX3Files.bz2' ), 'w:bz2' )
    for filename in os.listdir( filesFolder ):
        if filename.endswith( '.usx' ):
            filepath = os.path.join( filesFolder, filename )
            tar.add( filepath, arcname=filename, recursive=False )
    tar.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        vPrint( 'Quiet', debuggingThisModule, "  BibleWriter.toUSXXML finished successfully." )
    if validationSchema: return validationResults
    return True
# end of USXXMLBible.createUSXXMLBible function



def testMakeRefs() -> None:
    """
    USX3 includes livened references, e.g., for \\ior1 and \\xt fields
    """
    from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
    from BibleOrgSys.Reference.BibleReferences import BibleReferenceList

    genericBOS = BibleOrganisationalSystem( 'GENERIC-KJV-80-ENG' )
    genericBRL = BibleReferenceList( genericBOS, None )
    BBB, C, V = 'GEN', '1', '2'

    for j, (string1,string2) in enumerate( (
            ('xyz', 'xyz'),
            ('EXO 3:4', '<ref loc="EXO 3:4">EXO 3:4</ref>'),
            ('EXO 3:4-5', '<ref loc="EXO 3:4-5">EXO 3:4-5</ref>'),
            ('EXO 3:4,6', '<ref loc="EXO 3:4">EXO 3:4</ref>,<ref loc="EXO 3:6">6</ref>'),
            ('EXO 3:4, 7', '<ref loc="EXO 3:4">EXO 3:4</ref>, <ref loc="EXO 3:7">7</ref>'),
            ('EXO 3:4–5:6', '<ref loc="EXO 3:4-5:6">EXO 3:4–5:6</ref>'), # en-dash
            ('EXO 3:4-5:6', '<ref loc="EXO 3:4-5:6">EXO 3:4-5:6</ref>'), # hyphen
            ('EXO 3:4-5,7', '<ref loc="EXO 3:4-5">EXO 3:4-5</ref>,<ref loc="EXO 3:7">7</ref>'),
            ('PSA 118:1–119:123', '<ref loc="PSA 118:1-119:123">PSA 118:1–119:123</ref>'), # en-dash

            ('3JN 4',   '<ref loc="3JN 4">3JN 4</ref>'),
            # ('3JN 4-5', '<ref loc="3JN 4-5">3JN 4-5</ref>'),
            # ('3JN 4,6', '<ref loc="3JN 4">3JN 4</ref>,<ref loc="3JN 6">6</ref>'),

            ('3:4', f'<ref loc="{BBB} 3:4">3:4</ref>'),
            ('3:4-5', f'<ref loc="{BBB} 3:4-5">3:4-5</ref>'),
            ('3:4,6', f'<ref loc="{BBB} 3:4">3:4</ref>,<ref loc="{BBB} 3:6">6</ref>'),
            ('3:4, 7', f'<ref loc="{BBB} 3:4">3:4</ref>, <ref loc="{BBB} 3:7">7</ref>'),
            ('3:4–5:6', f'<ref loc="{BBB} 3:4-5:6">3:4–5:6</ref>'), # en-dash
            ('3:4-5:6', f'<ref loc="{BBB} 3:4-5:6">3:4-5:6</ref>'), # hyphen
            # ('3:4-5,7', f'<ref loc="{BBB} 3:4-5:6">3:4-5:6</ref>'),
            ), start=1 ):
        result = makeRefs( BBB, C,V, genericBRL, string1 )
        vPrint( 'Normal', debuggingThisModule, f"  {j}/ Got '{result}' from '{string1}'" )
        if result != string2:
            logging.critical( f"{j}/ Got bad  '{result}' from makeRefs()" )
            logging.critical( f"{j}/ Expected '{string2}' from '{string1}'" )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt
# end of testMakeRefs()


def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    import random

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testMakeRefs()

    testData = (
            ('Test1',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1'),),
            ('Test2',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2'),),
            ('MatigsalugUSFM',Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'),), # USFM not USX !
            ("Matigsalug3", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/'),),
            ("Matigsalug4", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/'),),
            ("Matigsalug5", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/'),),
            ) # You can put your USX test folder here

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        name, testFolder = random.choice( testData )
        vPrint( 'Quiet', debuggingThisModule, "\nA: Testfolder is: {}".format( testFolder ) )
        result1 = USXXMLBibleFileCheck( testFolder )
        vPrint( 'Normal', debuggingThisModule, "USX TestAa", result1 )
        result2 = USXXMLBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', debuggingThisModule, "USX TestAb (autoLoad)", result2 )
        result3 = USXXMLBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "USX TestAc (autoLoadBooks)", result3 )

    if 1:
        name, testFolder = random.choice( testData )
        vPrint( 'Quiet', debuggingThisModule, "\nB: Testfolder is: {} ({})".format( testFolder, name ) )
        if os.access( testFolder, os.R_OK ):
            UB = USXXMLBible( testFolder, name )
            UB.load()
            vPrint( 'Quiet', debuggingThisModule, UB )
            if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
            if BibleOrgSysGlobals.commandLineArguments.export: UB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            #UBErrors = UB.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, UBErrors )
            #vPrint( 'Quiet', debuggingThisModule, UB.getVersification() )
            #vPrint( 'Quiet', debuggingThisModule, UB.getAddedUnits() )
            #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                ##vPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                #vPrint( 'Quiet', debuggingThisModule, "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
        else: vPrint( 'Quiet', debuggingThisModule, "B: Sorry, test folder {!r} is not readable on this computer.".format( testFolder ) )

        #if BibleOrgSysGlobals.commandLineArguments.export:
        #    vPrint( 'Quiet', debuggingThisModule, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
        #       pass

    if 1:
        USXSourceFolder = Path( '/srv/Documents/USXResources/' ) # You can put your own folder here
        for j, something in enumerate( sorted( os.listdir( USXSourceFolder ) ) ):
            if something == '.git': assert j==0; continue
            #if something != 'TND': continue # Test this one only!!!
            #vPrint( 'Quiet', debuggingThisModule, "something", something )
            somepath = os.path.join( USXSourceFolder, something )
            if os.path.isfile( somepath ):
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                    vPrint( 'Quiet', debuggingThisModule, "C{}/ Unexpected {} file in {}".format( j, something, USXSourceFolder ) )
            elif os.path.isdir( somepath ):
                abbreviation = something
                vPrint( 'Quiet', debuggingThisModule, "\nC{}/ Loading USX {}…".format( j, abbreviation ) )
                loadedBible = USXXMLBible( somepath, givenName=abbreviation+' Bible' )
                loadedBible.loadBooks() # Load and process the USX XML books
                vPrint( 'Quiet', debuggingThisModule, loadedBible ) # Just print a summary
                break
# end of USXXMLBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testMakeRefs()

    testData = (
            ('MS1', Path('/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/Exports/USX/MBTV')),
            ('Test1',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1'),),
            ('Test2',BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2'),),
            ('MatigsalugUSFM', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'),), # USFM not USX !
            ("Matigsalug3", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/'),),
            ("Matigsalug4", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/'),),
            ("Matigsalug5", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/'),),
            ) # You can put your USX test folder here

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for j, (name, testFolder) in enumerate( testData ):
            vPrint( 'Quiet', debuggingThisModule, "\nA{}: Testfolder is: {}".format( j+1, testFolder ) )
            result1 = USXXMLBibleFileCheck( testFolder )
            vPrint( 'Normal', debuggingThisModule, "USX TestA{}a".format( j+1 ), result1 )
            result2 = USXXMLBibleFileCheck( testFolder, autoLoad=True )
            vPrint( 'Normal', debuggingThisModule, "USX TestA{}b (autoLoad)".format( j+1 ), result2 )
            result3 = USXXMLBibleFileCheck( testFolder, autoLoadBooks=True )
            vPrint( 'Normal', debuggingThisModule, "USX TestA{}c (autoLoadBooks)".format( j+1 ), result3 )

    if 1:
        for j, (name, testFolder) in enumerate( testData ):
            vPrint( 'Quiet', debuggingThisModule, "\nB{}: Testfolder is: {} ({})".format( j+1, testFolder, name ) )
            if os.access( testFolder, os.R_OK ):
                UB = USXXMLBible( testFolder, name )
                UB.load()
                vPrint( 'Quiet', debuggingThisModule, UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                if BibleOrgSysGlobals.commandLineArguments.export: UB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                #UBErrors = UB.getCheckResults()
                # vPrint( 'Quiet', debuggingThisModule, UBErrors )
                #vPrint( 'Quiet', debuggingThisModule, UB.getVersification() )
                #vPrint( 'Quiet', debuggingThisModule, UB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##vPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                    #vPrint( 'Quiet', debuggingThisModule, "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: vPrint( 'Quiet', debuggingThisModule, "B{}: Sorry, test folder {!r} is not readable on this computer.".format( j+1, testFolder ) )

        #if BibleOrgSysGlobals.commandLineArguments.export:
        #    vPrint( 'Quiet', debuggingThisModule, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
        #       pass

    if 1:
        USXSourceFolder = Path( '/srv/Documents/USXResources/' ) # You can put your own folder here
        for j, something in enumerate( sorted( os.listdir( USXSourceFolder ) ) ):
            if something == '.git': assert j==0; continue
            #if something != 'TND': continue # Test this one only!!!
            #vPrint( 'Quiet', debuggingThisModule, "something", something )
            somepath = os.path.join( USXSourceFolder, something )
            if os.path.isfile( somepath ):
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                    vPrint( 'Quiet', debuggingThisModule, "C{}/ Unexpected {} file in {}".format( j, something, USXSourceFolder ) )
            elif os.path.isdir( somepath ):
                abbreviation = something
                vPrint( 'Quiet', debuggingThisModule, "\nC{}/ Loading USX {}…".format( j, abbreviation ) )
                loadedBible = USXXMLBible( somepath, givenName=abbreviation+' Bible' )
                loadedBible.loadBooks() # Load and process the USX XML books
                vPrint( 'Quiet', debuggingThisModule, loadedBible ) # Just print a summary
# end of USXXMLBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USXXMLBible.py
