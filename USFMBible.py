#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMBible.py
#   Last modified: 2014-01-12 by RJH (also update ProgVersion below)
#
# Module handling compilations of USFM Bible books
#
# Copyright (C) 2010-2014 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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
Module for defining and manipulating complete or partial USFM Bibles.
"""

ProgName = "USFM Bible handler"
ProgVersion = "0.46"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
import multiprocessing

import Globals
from USFMFilenames import USFMFilenames
from USFMBibleBook import USFMBibleBook
from Bible import Bible



filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'BBLX', 'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC', ) # Must be UPPERCASE



def USFMBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for USFM Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USFM Bible is found,
        returns the loaded USFMBible object.
    """
    if Globals.verbosityLevel > 2: print( "USFMBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USFMBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USFMBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " USFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an USFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if Globals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples()
    if Globals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
    if Globals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USFM file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            if Globals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USFMBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and autoLoad:
            uB = USFMBible( givenFolderName )
            uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("USFMBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    USFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an USFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if Globals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples()
        if Globals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
        if Globals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USFM files: {}".format( len(filenameTuples), filenameTuples ) )
        elif Globals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USFM file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                if Globals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USFMBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            uB = USFMBible( foundProjects[0] )
            uB.load() # Load and process the file
            return uB
        return numFound
# end of USFMBibleFileCheck



class USFMBible( Bible ):
    """
    Class to load and manipulate USFM Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Create the internal USFM Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "USFM Bible object"
        self.objectTypeString = "USFM"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what '{}' is in {}!".format( somepath, self.sourceFolder ) )
        if foundFolders: logging.info( "USFMBible.load: Surprised to see subfolders in '{}': {}".format( self.sourceFolder, foundFolders ) )
        if not foundFiles:
            if Globals.verbosityLevel > 0: print( "USFMBible: Couldn't find any files in '{}'".format( self.sourceFolder ) )
            return # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if Globals.verbosityLevel > 3 or (Globals.debugFlag and debuggingThisModule):
            print( self.USFMFilenamesObject )

        # Attempt to load the SSF file
        self.ssfFilepath, self.settingsDict = {}, {}
        ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
        if len(ssfFilepathList) == 1: # Seems we found the right one
            self.ssfFilepath = ssfFilepathList[0]
            self.loadSSFData( self.ssfFilepath )

        self.name = self.givenName
        if self.name is None:
            for field in ('FullName','Name',):
                if field in self.settingsDict: self.name = self.settingsDict[field]; break
        if not self.name: self.name = os.path.basename( self.sourceFolder )
        if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        if not self.name: self.name = "USFM Bible"

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples()
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.possibleFilenameDict[BBB] = filename
    # end of USFMBible.__init_


    def loadSSFData( self, ssfFilepath, encoding='utf-8' ):
        """Process the SSF data from the given filepath.
            Returns a dictionary."""
        if Globals.verbosityLevel > 2: print( _("Loading SSF data from '{}'").format( ssfFilepath ) )
        lastLine, lineCount, status, settingsDict = '', 0, 0, {}
        with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                    logging.info( "USFMBible.loadSSFData: Detected UTF-16 Byte Order Marker in {}".format( ssfFilepath ) )
                    line = line[1:] # Remove the Byte Order Marker
                if line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                line = line.strip() # Remove leading and trailing whitespace
                if not line: continue # Just discard blank lines
                lastLine = line
                processed = False
                if status==0 and line=="<ScriptureText>":
                    status = 1
                    processed = True
                elif status==1 and line=="</ScriptureText>":
                    status = 2
                    processed = True
                elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a self-closing (empty) field
                    fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
                    if ' ' not in fieldname:
                        settingsDict[fieldname] = ''
                        processed = True
                    elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                        bits = fieldname.split( None, 1 )
                        if Globals.debugFlag: assert( len(bits)==2 )
                        fieldname = bits[0]
                        attributes = bits[1]
                        #print( "attributes = '{}'".format( attributes) )
                        settingsDict[fieldname] = (contents, attributes)
                        processed = True
                elif status==1 and line[0]=='<' and line[-1]=='>':
                    ix1 = line.index('>')
                    ix2 = line.index('</')
                    if ix1!=-1 and ix2!=-1 and ix2>ix1:
                        fieldname = line[1:ix1]
                        contents = line[ix1+1:ix2]
                        if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                            settingsDict[fieldname] = contents
                            processed = True
                        elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                            bits = fieldname.split( None, 1 )
                            if Globals.debugFlag: assert( len(bits)==2 )
                            fieldname = bits[0]
                            attributes = bits[1]
                            #print( "attributes = '{}'".format( attributes) )
                            if line[ix2+2:-1]==fieldname:
                                settingsDict[fieldname] = (contents, attributes)
                                processed = True
                if not processed: print( "ERROR: Unexpected '{}' line in SSF file".format( line ) )
        if Globals.verbosityLevel > 2:
            print( "  " + _("Got {} SSF entries:").format( len(settingsDict) ) )
            if Globals.verbosityLevel > 3:
                for key in sorted(settingsDict):
                    print( "    {}: {}".format( key, settingsDict[key] ) )
        self.ssfDict = settingsDict # We'll keep a copy of just the SSF settings
        self.settingsDict = settingsDict.copy() # This will be all the combined settings
    # end of USFMBible.loadSSFData


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book if it's not already loaded.
        """
        if Globals.verbosityLevel > 2: print( "USFMBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if Globals.verbosityLevel > 2 or Globals.debugFlag: print( _("  USFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USFMBibleBook( self.name, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.saveBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
    # end of USFMBible.loadBook


    def loadBookMP( self, BBB ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded.
        """
        if Globals.verbosityLevel > 2: print( "USFMBible.loadBookMP( {} )".format( BBB ) )
        assert( BBB not in self.books )
        self.triedLoadingBook[BBB] = True
        if Globals.verbosityLevel > 2 or Globals.debugFlag: print( _("  USFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFMBibleBook( self.name, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        return UBB
    # end of USFMBible.loadBookMP


    def load( self ):
        """
        Load all the books.
        """
        if Globals.verbosityLevel > 1: print( _("USFMBible: Loading {} from {}...").format( self.name, self.sourceFolder ) )

        if Globals.maxProcesses > 1: # Load all the books as quickly as possible
            parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self.loadBookMP, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) )
                for bBook in results: self.saveBook( bBook )
        else: # Just single threaded
            # Load the books one by one -- assuming that they have regular Paratext style filenames
            for BBB,filename in self.maximumPossibleFilenameTuples:
                loadedBook = self.loadBook( BBB, filename ) # also saves it
    # end of USFMBible.load
# end of class USFMBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # Load and process some of our test versions
        count = 0
        for name, encoding, testFolder in ( \
                                            ("Matigsalug", "utf-8", "Tests/DataFilesForTests/USFMTest1/"), \
                                            ("Matigsalug", "utf-8", "Tests/DataFilesForTests/USFMTest2/"), \
                                            ("UEP", "utf-8", "Tests/DataFilesForTests/USFMErrorProject/"), \
                                            ("Exported", "utf-8", "Tests/BOS_USFM_Export/"), \
                                            ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                if Globals.verbosityLevel > 0: print( "\nUSFM A{}/".format( count ) )
                UsfmB = USFMBible( testFolder, name, encoding )
                UsfmB.load()
                if Globals.verbosityLevel > 0: print( UsfmB )
                if Globals.strictCheckingFlag:
                    UsfmB.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = UsfmB.getErrors()
                    # print( UBErrors )
                if Globals.commandLineOptions.export:
                    ##UsfmB.toDrupalBible()
                    UsfmB.doAllExports()
                    if name != "UEP": # Why does this fail to pickle?
                        newObj = Globals.unpickleObject( name + '.pickle' )
                        if Globals.verbosityLevel > 0: print( "newObj is", newObj )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )


    if 0: # Test a whole folder full of folders of USFM Bibles
        testBaseFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "USFMBible: Detected UTF-16 Byte Order Marker in copyright.htm file" )
                        line = line[1:] # Remove the UTF-8 Byte Order Marker
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        USFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USFM_BBB )
                        #print( USFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): print( "Ignoring file '{}' in '{}'".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a USFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, encoding, testFolder = title, "utf-8", somepath
                    if os.access( testFolder, os.R_OK ):
                        if Globals.verbosityLevel > 0: print( "\nUSFM B{}/".format( count ) )
                        UsfmB = USFMBible( testFolder, name, encoding )
                        UsfmB.load()
                        if Globals.verbosityLevel > 0: print( UsfmB )
                        if Globals.strictCheckingFlag:
                            UsfmB.check()
                            UsfmBErrors = UsfmB.getErrors()
                            #print( UsfmBErrors )
                        if Globals.commandLineOptions.export: UsfmB.doAllExports()
                    else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
            if count: print( "\n{} total USFM (partial) Bibles processed.".format( count ) )
            if totalBooks: print( "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testBaseFolder ) )
#end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of USFMBible.py