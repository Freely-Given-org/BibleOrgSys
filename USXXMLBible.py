#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USXXMLBible.py
#   Last modified: 2013-06-11 by RJH (also update versionString below)
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012-2013 Robert Hunt
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
Module for defining and manipulating complete or partial USX Bibles.
"""

progName = "USX XML Bible handler"
versionString = "0.06"


import os, logging
from gettext import gettext as _
import multiprocessing

import Globals
from USXFilenames import USXFilenames
from USXXMLBibleBook import USXXMLBibleBook
from Bible import Bible



def USXXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for USX Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USX Bible is found,
        returns the loaded USXBible object.
    """
    if Globals.verbosityLevel > 2: print( "USXXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USXXMLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USXXMLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " USXXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    if Globals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getConfirmedFilenames()
    if Globals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
    if Globals.verbosityLevel > 1 and filenameTuples: print( "Found {} USX files.".format( len(filenameTuples) ) )
    if filenameTuples:
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USXXMLBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and autoLoad:
            uB = USXXMLBible( givenFolderName )
            uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            if Globals.logErrorsFlag: logging.warning( _("USXXMLBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    USXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if there's an USX Bible here in this folder
        UFns = USXFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if Globals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getConfirmedFilenames()
        if Globals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
        if Globals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        elif Globals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USX files".format( len(filenameTuples) ) )
        if filenameTuples:
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            uB = USXXMLBible( foundProjects[0] )
            uB.load() # Load and process the file
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

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            print( "USXXMLBible: File '{}' is unreadable".format( self.givenFolderName ) )
    # end of USXXMLBible.__init_


    def loadBook( self, BBB ):
        """
        Used for multiprocessing.
        """
        print( "USXXMLBible.loadBook( {} )".format( BBB ) )
        UBB = USXXMLBibleBook( BBB )
        print( "created", BBB )
        UBB.load( self._filenameDict[BBB], self.givenFolderName, self.encoding )
        print( "loaded", BBB )
        UBB.validateUSFM()
        print( "validated", BBB )
        return UBB
    # end of USXXMLBible.loadBook


    def load( self ):
        """
        Load the books.
        """
        def loadSSFData( ssfFilepath, encoding='utf-8' ):
            """Process the SSF data from the given filepath.
                Returns a dictionary."""
            if Globals.verbosityLevel > 2: print( _("Loading SSF data from '{}'").format( ssfFilepath ) )
            lastLine, lineCount, status, ssfData = '', 0, 0, {}
            with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        if Globals.verbosityLevel > 0: print( "      USXXMLBible.load: Detected UTF-16 Byte Order Marker" )
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
                            ssfData[fieldname] = ''
                            processed = True
                        elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                            bits = fieldname.split( None, 1 )
                            assert( len(bits)==2 )
                            fieldname = bits[0]
                            attributes = bits[1]
                            #print( "attributes = '{}'".format( attributes) )
                            ssfData[fieldname] = (contents, attributes)
                            processed = True
                    elif status==1 and line[0]=='<' and line[-1]=='>':
                        ix1 = line.index('>')
                        ix2 = line.index('</')
                        if ix1!=-1 and ix2!=-1 and ix2>ix1:
                            fieldname = line[1:ix1]
                            contents = line[ix1+1:ix2]
                            if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                                ssfData[fieldname] = contents
                                processed = True
                            elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                                bits = fieldname.split( None, 1 )
                                assert( len(bits)==2 )
                                fieldname = bits[0]
                                attributes = bits[1]
                                #print( "attributes = '{}'".format( attributes) )
                                if line[ix2+2:-1]==fieldname:
                                    ssfData[fieldname] = (contents, attributes)
                                    processed = True
                    if not processed: print( "ERROR: Unexpected '{}' line in SSF file".format( line ) )
            if Globals.verbosityLevel > 2:
                print( "  " + _("Got {} SSF entries:").format( len(ssfData) ) )
                if Globals.verbosityLevel > 3:
                    for key in sorted(ssfData):
                        print( "    {}: {}".format( key, ssfData[key] ) )
            return ssfData
        # end of loadSSFData

        if Globals.verbosityLevel > 1: print( _("USXXMLBible: Loading {} from {}...").format( self.name, self.givenFolderName ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.givenFolderName ):
            somepath = os.path.join( self.givenFolderName, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: print( "ERROR: Not sure what '{}' is in {}!".format( somepath, self.givenFolderName ) )
        if foundFolders: print( "USXXMLBible.load: Surprised to see subfolders in '{}': {}".format( self.givenFolderName, foundFolders ) )
        if not foundFiles:
            print( "USXXMLBible.load: Couldn't find any files in '{}'".format( self.givenFolderName ) )
            return # No use continuing

        self.USXFilenamesObject = USXFilenames( self.givenFolderName )

        if 0:
            # Attempt to load the metadata file
            ssfFilepathList = self.USXFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            if len(ssfFilepathList) == 1: # Seems we found the right one
                self.ssfData = loadSSFData( ssfFilepathList[0] )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        # DON'T KNOW WHY THIS DOESN'T WORK
        if 0 and Globals.maxProcesses > 1: # Load all the books as quickly as possible
            self._filenameDict, parameters = {}, []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
                parameters.append( BBB )
                self._filenameDict[BBB] = filename
            #print( "parameters", parameters )
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self.loadBook, parameters ) # have the pool do our loads
                print( "results", results )
                assert( len(results) == len(parameters) )
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
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
                UBB = USXXMLBibleBook( BBB )
                UBB.load( filename, self.givenFolderName, self.encoding )
                UBB.validateUSFM()
                #print( UBB )
                self.books[BBB] = UBB
                # Make up our book name dictionaries while we're at it
                assumedBookNames = UBB.getAssumedBookNames()
                for assumedBookName in assumedBookNames:
                    self.BBBToNameDict[BBB] = assumedBookName
                    assumedBookNameLower = assumedBookName.lower()
                    self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if Globals.verbosityLevel > 2:
                print( "USXXMLBible.load: Didn't find any regularly named USX files in '{}'".format( self.givenFolderName ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USX file)
                isUSX = False
                thisPath = os.path.join( self.givenFolderName, thisFilename )
                with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    for line in possibleUSXFile:
                        if line.startswith( '\\id ' ):
                            USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if Globals.verbosityLevel > 2: print( "Have possible USX ID '{}'".format( USXId ) )
                            BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USXId )
                            if Globals.verbosityLevel > 2: print( "BBB is '{}'".format( BBB ) )
                            isUSX = True
                        break # We only look at the first line
                if isUSX:
                    UBB = USXXMLBibleBook( BBB )
                    UBB.load( self.givenFolderName, thisFilename, self.encoding )
                    UBB.validateUSFM()
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
            if self.books: print( "USXXMLBible.load: Found {} irregularly named USX files".format( len(self.books) ) )
    # end of USXXMLBible.load
# end of class USXXMLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    testData = (
                ("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/",),
                ("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/",),
                ) # You can put your USX test folder here

    for name, testFolder in testData:
        if os.access( testFolder, os.R_OK ):
            UB = USXXMLBible( testFolder, name )
            UB.load()
            if Globals.verbosityLevel > 0: print( UB )
            if Globals.strictCheckingFlag: UB.check()
            #UBErrors = UB.getErrors()
            # print( UBErrors )
            #print( UB.getVersification () )
            #print( UB.getAddedUnits () )
            #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                ##print( "Looking for", ref )
                #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if Globals.commandLineOptions.export:
    #    if Globals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( progName, versionString ) )
    #       pass

if __name__ == '__main__':
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()
# end of USXXMLBible.py