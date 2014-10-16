#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ESFMBible.py
#   Last modified: 2014-10-16 by RJH (also update ProgVersion below)
#
# Module handling compilations of ESFM Bible books
#
# Copyright (C) 2010-2014 Robert Hunt
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
Module for defining and manipulating complete or partial ESFM Bibles.
"""

ProgName = "ESFM Bible handler"
ProgVersion = "0.57"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
import multiprocessing

import Globals
from USFMFilenames import USFMFilenames
from ESFMFile import ESFMFile
from ESFMBibleBook import ESFMBibleBook, ESFM_SEMANTIC_TAGS
from Bible import Bible



#filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
#extensionsToIgnore = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML', 'JAR',
                    #'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    #'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot
filenameEndingsToAccept = ('.ESFM',) # Must be UPPERCASE here
#BibleFilenameEndingsToAccept = ('.ESFM',) # Must be UPPERCASE here


#def removeUnwantedTupleExtensions( fnTuples ):
    #"""
    #Given a container of (BBB,filename) 2-tuples,
        #results a list without any of the above file extensions.
    #"""
    #resultList = []
    #for BBB,filename in fnTuples:
        #ignoreFlag = False
        #for ignoreExtension in extensionsToIgnore:
            #if filename.upper().endswith( ignoreExtension ): ignoreFlag = True; break
        #if not ignoreFlag: resultList.append( (BBB,filename) )
    #return resultList
## end of removeUnwantedTupleExtensions


def ESFMBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for ESFM Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one ESFM Bible is found,
        returns the loaded ESFMBible object.
    """
    if Globals.verbosityLevel > 2: print( "ESFMBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) and autoLoadBooks in (True,False) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ESFMBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ESFMBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " ESFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                #foundFiles.append( something )
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an ESFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if Globals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
    for BBB,fn in filenameTuples[:]: # Only accept our specific file extensions
        acceptFlag = False
        for fna in filenameEndingsToAccept:
            if fn.endswith( fna ): acceptFlag = True
        if not acceptFlag: filenameTuples.remove( (BBB,fn) )
    if Globals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
    if Globals.verbosityLevel > 1 and filenameTuples: print( "  Found {} ESFM file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            if Globals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "ESFMBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            eB = ESFMBible( givenFolderName )
            if autoLoadBooks: eB.load() # Load and process the file
            return eB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ESFMBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    ESFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                #ignore = False
                #for ending in filenameEndingsToIgnore:
                    #if somethingUpper.endswith( ending): ignore=True; break
                #if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    #foundSubfiles.append( something )
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an ESFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if Globals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        for BBB,fn in filenameTuples[:]: # Only accept our specific file extensions
            acceptFlag = False
            for fna in filenameEndingsToAccept:
                if fn.endswith( fna ): acceptFlag = True
            if not acceptFlag: filenameTuples.remove( (BBB,fn) )
        if Globals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
        if Globals.verbosityLevel > 2 and filenameTuples: print( "  Found {} ESFM files: {}".format( len(filenameTuples), filenameTuples ) )
        elif Globals.verbosityLevel > 1 and filenameTuples: print( "  Found {} ESFM file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                if Globals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "ESFMBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = ESFMBible( foundProjects[0] )
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of ESFMBibleFileCheck



class ESFMBible( Bible ):
    """
    Class to load and manipulate ESFM Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None ):
        """
        Create the internal ESFM Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "ESFM Bible object"
        self.objectTypeString = "ESFM"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation = sourceFolder, givenName, givenAbbreviation

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what '{}' is in {}!".format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in ('__MACOSX'): continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( "ESFMBible.load: Surprised to see subfolders in '{}': {}".format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if Globals.verbosityLevel > 0: print( "ESFMBible: Couldn't find any files in '{}'".format( self.sourceFolder ) )
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
        if not self.name: self.name = "ESFM Bible"

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.possibleFilenameDict[BBB] = filename

        self.dontLoadBook = []
        self.spellingDict, self.StrongsDict, self.hyphenationDict, self.semanticDict = {}, {}, {}, {}
    # end of ESFMBible.__init_


    def loadSSFData( self, ssfFilepath ):
        """Process the SSF data from the given filepath.
            Returns a dictionary."""
        if Globals.verbosityLevel > 2: print( _("Loading SSF data from '{}'").format( ssfFilepath ) )
        lastLine, lineCount, status, settingsDict = '', 0, 0, {}
        with open( ssfFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                    logging.info( "ESFMBible.loadSSFData: Detected UTF-16 Byte Order Marker in {}".format( ssfFilepath ) )
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
    # end of ESFMBible.loadSSFData


    def loadSemanticDictionary( self, BBB, filename ):
        """
        """
        if Globals.verbosityLevel > 1: print( "    " + _("Loading possible semantic dictionary from {}...").format( filename ) )
        sourceFilepath = os.path.join( self.sourceFolder, filename )
        originalBook = ESFMFile()
        originalBook.read( sourceFilepath )

        count = 0
        for marker,originalText in originalBook.lines:
            #print( marker, repr(originalText) )
            if marker == 'rem' and originalText.startswith('ESFM '):
                if ' SEM' not in originalText: return
            elif marker == 'gl':
                if originalText[0] in ESFM_SEMANTIC_TAGS \
                and originalText[1] == ' ' \
                and len(originalText)>2:
                    tagMarker = originalText[0]
                    tagContent = originalText[2:]
                    if tagMarker not in self.semanticDict: self.semanticDict[tagMarker] = {}
                    if tagContent not in self.semanticDict[tagMarker]: self.semanticDict[tagMarker][tagContent] = []
                    count += 1
        self.dontLoadBook.append( BBB )
        if Globals.verbosityLevel > 1:
            if count: print( "{} semantic entries added in {} categories".format( count, len(self.semanticDict) ) )
            else: print( "No semantic entries found." )
    # end of ESFMBible.loadSemanticDictionary


    def loadStrongsDictionary( self, BBB, filename ):
        """
        """
        if Globals.verbosityLevel > 1: print( "    " + _("Loading possible Strong's dictionary from {}...").format( filename ) )
        sourceFilepath = os.path.join( self.sourceFolder, filename )
        originalBook = ESFMFile()
        originalBook.read( sourceFilepath )

        count = 0
        for marker,originalText in originalBook.lines:
            #print( marker, repr(originalText) )
            if marker == 'rem' and originalText.startswith('ESFM '):
                if ' STR' not in originalText: return
            elif marker == 'gl':
                if originalText[0] in 'HG':
                    tagMarker = originalText[0]
                    sNumber = originalText[1:]
            elif marker == 'html':
                dictEntry = originalText
                if tagMarker not in self.StrongsDict: self.StrongsDict[tagMarker] = {}
                if sNumber not in self.StrongsDict[tagMarker]: self.StrongsDict[tagMarker][sNumber] = dictEntry
                count += 1
        self.dontLoadBook.append( BBB )
        if Globals.verbosityLevel > 1:
            if count: print( "{} Strong's entries added in {} categories".format( count, len(self.StrongsDict) ) )
            else: print( "No Strong's entries found." )
    # end of ESFMBible.loadStrongsDictionary


    def loadDictionaries( self ):
        """
        Attempts to load the spelling, hyphenation, and semantic dictionaries if they exist.
        """
        if Globals.verbosityLevel > 1: print( "  " + _("Loading any dictionaries...") )
        for BBB,filename in self.maximumPossibleFilenameTuples:
            if BBB=='XXD': self.loadSemanticDictionary( BBB, filename )
            elif BBB=='XXE': self.loadStrongsDictionary( BBB, filename )
    # end of ESFMBible.loadDictionaries


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book if it's not already loaded.
        """
        if Globals.verbosityLevel > 2: print( "ESFMBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.dontLoadBook: return # Must be a dictionary that's already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading ESFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if Globals.verbosityLevel > 2 or Globals.debugFlag:
            try: print( _("  ESFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
            except UnicodeEncodeError: print( _("  ESFMBible: Loading {}...").format( BBB ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        EBB = ESFMBibleBook( self, BBB )
        EBB.load( filename, self.sourceFolder )
        if EBB._rawLines:
            EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.saveBook( EBB )
        else: logging.info( "ESFM book {} was completely blank".format( BBB ) )
    # end of ESFMBible.loadBook


    def _loadBookMP( self, BBB_Filename ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if Globals.verbosityLevel > 3: print( "ESFMBible.loadBookMP( {} )".format( BBB_Filename ) )
        BBB, filename = BBB_Filename
        assert( BBB not in self.books )
        if BBB in self.dontLoadBook: return None
        self.triedLoadingBook[BBB] = True
        if Globals.verbosityLevel > 2 or Globals.debugFlag:
            print( _("  ESFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        EBB = ESFMBibleBook( self, BBB )
        EBB.load( self.possibleFilenameDict[BBB], self.sourceFolder )
        EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if Globals.verbosityLevel > 2 or Globals.debugFlag: print( _("    Finishing loading ESFM book {}.").format( BBB ) )
        return EBB
    # end of ESFMBible.loadBookMP


    def load( self ):
        """
        Load all the books.
        """
        if Globals.verbosityLevel > 1: print( _("ESFMBible: Loading {} from {}...").format( self.name, self.sourceFolder ) )

        if self.maximumPossibleFilenameTuples:
            # First try to load the dictionaries
            self.loadDictionaries()
            # Now load the books
            if Globals.maxProcesses > 1: # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if Globals.verbosityLevel > 1:
                    print( _("ESFMBible: Loading {} books using {} CPUs...").format( len(self.maximumPossibleFilenameTuples), Globals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert( len(results) == len(self.maximumPossibleFilenameTuples) )
                    for bBook in results:
                        if bBook is not None: self.saveBook( bBook ) # Saves them in the correct order
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if Globals.verbosityLevel > 1 or Globals.debugFlag:
                        #print( _("  ESFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
                    if BBB not in self.dontLoadBook:
                        loadedBook = self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( _("ESFMBible: No books to load in {}!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        if 'Tag errors' in self.semanticDict: print( "Tag errors:", self.semanticDict['Tag errors'] )
        if 'Missing' in self.semanticDict: print( "Missing:", self.semanticDict['Missing'] )
        self.doPostLoadProcessing()
    # end of ESFMBible.load
# end of class ESFMBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # Load and process some of our test versions
        count = 0
        for name, abbreviation, testFolder in ( # name, abbreviation, folder
                    ("Open English Translation—Literal Version", "OET-LV", "../../../../../Data/Work/Matigsalug/Bible/OET-LV/",),
                    #("Matigsalug", "MBTV", "../../../../../Data/Work/Matigsalug/Bible/MBTV/",),
                    #("ESFM Test 1", "OET-LV", "Tests/DataFilesForTests/ESFMTest1/"),
                    #("ESFM Test 2", "OET-RV", "Tests/DataFilesForTests/ESFMTest2/"),
                    #("All Markers Project", "WEB+", "Tests/DataFilesForTests/USFMAllMarkersProject/"),
                    #("USFM Error Project", "UEP", "Tests/DataFilesForTests/USFMErrorProject/"),
                    #("BOS Exported Files", "Exported", "Tests/BOS_USFM_Export/"),
                    ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                if Globals.verbosityLevel > 0: print( "\nESFM A{}/".format( count ) )
                EsfmB = ESFMBible( testFolder, name, abbreviation )
                EsfmB.load()
                print( "Gen assumed book name:", repr( EsfmB.getAssumedBookName( 'GEN' ) ) )
                print( "Gen long TOC book name:", repr( EsfmB.getLongTOCName( 'GEN' ) ) )
                print( "Gen short TOC book name:", repr( EsfmB.getShortTOCName( 'GEN' ) ) )
                print( "Gen book abbreviation:", repr( EsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                if Globals.verbosityLevel > 0: print( EsfmB )
                if Globals.strictCheckingFlag:
                    EsfmB.check()
                    #print( EsfmB.books['GEN']._processedLines[0:40] )
                    EsfmBErrors = EsfmB.getErrors()
                    # print( UBErrors )
                if Globals.commandLineOptions.export:
                    ##EsfmB.toDrupalBible()
                    EsfmB.doAllExports( wantPhotoBible=False, wantODFs=True, wantPDFs=True )
                    newObj = Globals.unpickleObject( Globals.makeSafeFilename(abbreviation) + '.pickle', os.path.join( "OutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    if Globals.verbosityLevel > 0: print( "newObj is", newObj )
            else: print( "\nSorry, test folder '{}' is not readable on this computer.".format( testFolder ) )


    if 0: # Test a whole folder full of folders of ESFM Bibles
        testBaseFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "ESFMBible: Detected UTF-16 Byte Order Marker in copyright.htm file" )
                        line = line[1:] # Remove the UTF-8 Byte Order Marker
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        ESFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = Globals.BibleBooksCodes.getBBBFromESFM( ESFM_BBB )
                        #print( ESFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): print( "Ignoring file '{}' in '{}'".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a ESFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, testFolder = title, somepath
                    if os.access( testFolder, os.R_OK ):
                        if Globals.verbosityLevel > 0: print( "\nESFM B{}/".format( count ) )
                        EsfmB = ESFMBible( testFolder, name )
                        EsfmB.load()
                        if Globals.verbosityLevel > 0: print( EsfmB )
                        if Globals.strictCheckingFlag:
                            EsfmB.check()
                            EsfmBErrors = EsfmB.getErrors()
                            #print( EsfmBErrors )
                        if Globals.commandLineOptions.export: EsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: print( "\nSorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
            if count: print( "\n{} total ESFM (partial) Bibles processed.".format( count ) )
            if totalBooks: print( "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        else: print( "\nSorry, test folder '{}' is not readable on this computer.".format( testBaseFolder ) )
#end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of ESFMBible.py
