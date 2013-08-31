#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFXXMLBible.py
#   Last modified: 2013-08-31 by RJH (also update ProgVersion below)
#
# Module handling USFX XML Bibles
#
# Copyright (C) 2013 Robert Hunt
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
Module for defining and manipulating complete or partial USFX Bibles.
"""

ProgName = "USFX XML Bible handler"
ProgVersion = "0.01"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
import multiprocessing

import Globals
from Bible import Bible



filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'USX', 'TXT', 'STY', 'LDS', 'SSF', 'VRS',) # Must be UPPERCASE



def USFXXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for USFX XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one USFX Bible is found,
        returns the loaded USFXXMLBible object.
    """
    if Globals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USFXXMLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USFXXMLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " USFXXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    #print( 'ff', foundFiles )

    # See if there's an OpenSong project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or Globals.strictCheckingFlag:
            firstLines = Globals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if Globals.verbosityLevel > 2: print( "USFXB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                continue
            if "<usfx " not in firstLines[0]:
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            ub = USFXXMLBible( givenFolderName, lastFilenameFound )
            ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if Globals.verbosityLevel > 3: print( "    USFXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
        #print( 'fsf', foundSubfiles )

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLines = Globals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if Globals.verbosityLevel > 2: print( "USFXB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                    continue
                if "<usfx " not in firstLines[0]:
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            ub = USFXXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            ub.load() # Load and process the file
            return ub
        return numFound
# end of USFXXMLBibleFileCheck



class USFXXMLBible( Bible ):
    """
    Class to load and manipulate USFX Bibles.

    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal USFX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "USFX XML Bible object"
        self.objectTypeString = "USFX"

        self.givenFolderName, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.givenFolderName )
        if not self.name: self.name = os.path.basename( self.givenFolderName[:-1] ) # Remove the final slash
        if not self.name: self.name = "USFX Bible"

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.error( "USFXXMLBible: File '{}' is unreadable".format( self.givenFolderName ) )
    # end of USFXXMLBible.__init_


    def loadBook( self, BBB, filename=None ):
        """
        Used for multiprocessing.
        """
        if Globals.verbosityLevel > 2: print( "USFXXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USFX {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if Globals.verbosityLevel > 2 or Globals.debugFlag: print( _("  USFXXMLBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USFXXMLBibleBook( self.name, BBB )
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
    # end of USFXXMLBible.loadBook


    def load( self ):
        """
        Load the books.
        """
        def loadSSFData( ssfFilepath, encoding='utf-8' ):
            """Process the SSF data from the given filepath.
                Returns a dictionary."""
            if Globals.verbosityLevel > 2: print( _("Loading SSF data from '{}'").format( ssfFilepath ) )
            lastLine, lineCount, status, settingsDict = '', 0, 0, {}
            with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "USFXXMLBible.load: Detected UTF-16 Byte Order Marker in {}".format( ssfFilepath ) )
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
                            assert( len(bits)==2 )
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
                                assert( len(bits)==2 )
                                fieldname = bits[0]
                                attributes = bits[1]
                                #print( "attributes = '{}'".format( attributes) )
                                if line[ix2+2:-1]==fieldname:
                                    settingsDict[fieldname] = (contents, attributes)
                                    processed = True
                    if not processed: logging.error( "Unexpected '{}' line in SSF file".format( line ) )
            if Globals.verbosityLevel > 2:
                print( "  " + _("Got {} SSF entries:").format( len(settingsDict) ) )
                if Globals.verbosityLevel > 3:
                    for key in sorted(settingsDict):
                        print( "    {}: {}".format( key, settingsDict[key] ) )
            self.ssfDict = settingsDict # We'll keep a copy of just the SSF settings
            self.settingsDict = settingsDict.copy() # This will be all the combined settings
        # end of loadSSFData

        if Globals.verbosityLevel > 1: print( _("USFXXMLBible: Loading {} from {}...").format( self.name, self.givenFolderName ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.givenFolderName ):
            somepath = os.path.join( self.givenFolderName, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what '{}' is in {}!".format( somepath, self.givenFolderName ) )
        if foundFolders: logging.info( "USFXXMLBible.load: Surprised to see subfolders in '{}': {}".format( self.givenFolderName, foundFolders ) )
        if not foundFiles:
            if Globals.verbosityLevel > 0: print( "USFXXMLBible.load: Couldn't find any files in '{}'".format( self.givenFolderName ) )
            return # No use continuing

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        # DON'T KNOW WHY THIS DOESN'T WORK
        if Globals.maxProcesses > 1: # Load all the books as quickly as possible
            parameters = []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
                parameters.append( BBB )
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
                UBB = USFXXMLBibleBook( self.name, BBB )
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
            if Globals.verbosityLevel > 2:
                print( "USFXXMLBible.load: Didn't find any regularly named USFX files in '{}'".format( self.givenFolderName ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USFX file)
                isUSFX = False
                thisPath = os.path.join( self.givenFolderName, thisFilename )
                with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    for line in possibleUSXFile:
                        if line.startswith( '\\id ' ):
                            USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if Globals.verbosityLevel > 2: print( "Have possible USFX ID '{}'".format( USXId ) )
                            BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USXId )
                            if Globals.verbosityLevel > 2: print( "BBB is '{}'".format( BBB ) )
                            isUSFX = True
                        break # We only look at the first line
                if isUSFX:
                    UBB = USFXXMLBibleBook( self.name, BBB )
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
            if self.books: print( "USFXXMLBible.load: Found {} irregularly named USFX files".format( len(self.books) ) )
    # end of USFXXMLBible.load
# end of class USFXXMLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    testData = (
                ("AGM", "../../../../../Data/Work/Bibles/USFX Bibles/Haiola USFX test versions/agm_usfx/",),
                ) # You can put your USFX test folder here

    for name, testFolder in testData:
        if os.access( testFolder, os.R_OK ):
            UB = USFXXMLBible( testFolder, name )
            UB.load()
            if Globals.verbosityLevel > 0: print( UB )
            if Globals.strictCheckingFlag: UB.check()
            if Globals.commandLineOptions.export: UB.doAllExports()
            #UBErrors = UB.getErrors()
            # print( UBErrors )
            #print( UB.getVersification () )
            #print( UB.getAddedUnits () )
            #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                ##print( "Looking for", ref )
                #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if Globals.commandLineOptions.export:
    #    if Globals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( ProgName, ProgVersion ) )
    #       pass

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of USFXXMLBible.py