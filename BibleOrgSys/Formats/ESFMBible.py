#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ESFMBible.py
#
# Module handling compilations of ESFM Bible books
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
Module for defining and manipulating complete or partial ESFM Bibles.

See https://GitHub.com/Freely-Given-org/ESFM for more info on ESFM.
        \\id 1JN - Matigsalug Translation v1.0.17
        \\usfm 3.0
        \\ide UTF-8
        \\rem ESFM v0.6 JN1
        \\rem WORKDATA Matigsalug.txt
        \\rem FILEDATA Matigsalug.JN1.txt
        \\rem WORDTABLE Matigsalug.words.tsv
        \\h 1 Huwan
        \\toc1 1 Huwan
        \\toc2 1 Huwan
        \\toc3 1Huw
        \\mt2 Ka an-anayan ne sulat ni
        \\mt1 Huwan

Creates a semantic dictionary with keys:
    'Tag errors': contains a list of 4-tuples (BBB,C,V,errorWord)
    'Missing': contains a dictionary
    'A' 'G' 'L' 'O' 'P' 'Q' entries each containing a dictionary
        where the key is the name (e.g., 'Jonah')
        and the entry is a list of 4-tuples (BBB,C,V,actualWord)
"""
from typing import List, Tuple, Optional
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
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames
from BibleOrgSys.Formats.PTX7Bible import loadPTX7ProjectData
from BibleOrgSys.InputOutput.ESFMFile import ESFMFile
from BibleOrgSys.Formats.ESFMBibleBook import ESFMBibleBook, ESFM_SEMANTIC_TAGS
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry
from BibleOrgSys.Bible import Bible


LAST_MODIFIED_DATE = '2023-03-21' # by RJH
SHORT_PROGRAM_NAME = "ESFMBible"
PROGRAM_NAME = "ESFM Bible handler"
PROGRAM_VERSION = '0.67'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


filenameEndingsToAccept = ('.ESFM',) # Must be UPPERCASE here



def ESFMBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for ESFM Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one ESFM Bible is found,
        returns the loaded ESFMBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, "ESFMBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        assert givenFolderName and isinstance( givenFolderName, (str,Path) )
        assert autoLoad in (True,False,) and autoLoadBooks in (True,False)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ESFMBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ESFMBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Check that there's a USFM Bible here first
    from BibleOrgSys.Formats.USFMBible import USFMBibleFileCheck
    if not USFMBibleFileCheck( givenFolderName, strictCheck, discountSSF=False ): # no autoloads
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, " ESFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS: continue # don't visit these directories
            foundFolders.append( something )
        #elif os.path.isfile( somepath ):
            #somethingUpper = something.upper()
            #somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ##ignore = False
            ##for ending in filenameEndingsToIgnore:
                ##if somethingUpper.endswith( ending): ignore=True; break
            ##if ignore: continue
            ##if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                ##foundFiles.append( something )
            #if somethingUpperExt not in filenameEndingsToAccept: continue
            #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                #firstLine = BibleOrgSysGlobals.peekIntoFile( something, givenFolderName )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'E1', repr(firstLine) )
                #if firstLine is None: continue # seems we couldn't decode the file
                #if firstLine and firstLine[0]==BibleOrgSysGlobals.BOM:
                    #logging.info( "ESFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                    #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if not firstLine: continue # don't allow a blank first line
                #if firstLine[0] != '\\': continue # Must start with a backslash
            #foundFiles.append( something )

    # See if there's an ESFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    dPrint( 'Never', DEBUGGING_THIS_MODULE, UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
    for BBB,fn in filenameTuples.copy(): # Only accept our specific file extensions
        acceptFlag = False
        for fna in filenameEndingsToAccept:
            if fn.endswith( fna ): acceptFlag = True
        if not acceptFlag: filenameTuples.remove( (BBB,fn) )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "  Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Found {} ESFM file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, "Got ESFM SSFs: ({}) {}".format( len(SSFs), SSFs ) )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
        numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "ESFMBibleFileCheck got", numFound, givenFolderName )
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
            logging.warning( _("ESFMBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    ESFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        #foundSubfolders, foundSubfiles = [], []
        #for something in os.listdir( tryFolderName ):
            #somepath = os.path.join( givenFolderName, thisFolderName, something )
            #if os.path.isdir( somepath ): foundSubfolders.append( something )
            #elif os.path.isfile( somepath ):
                #somethingUpper = something.upper()
                #somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ##ignore = False
                ##for ending in filenameEndingsToIgnore:
                    ##if somethingUpper.endswith( ending): ignore=True; break
                ##if ignore: continue
                ##if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    ##foundSubfiles.append( something )
                #if somethingUpperExt not in filenameEndingsToAccept: continue
                #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    #firstLine = BibleOrgSysGlobals.peekIntoFile( something, tryFolderName )
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'E2', repr(firstLine) )
                    #if firstLine is None: continue # seems we couldn't decode the file
                    #if firstLine and firstLine[0]==BibleOrgSysGlobals.BOM:
                        #logging.info( "ESFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                        #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                    #if not firstLine: continue # don't allow a blank first line
                    #if firstLine[0] != '\\': continue # Must start with a backslash
                #foundSubfiles.append( something )

        # See if there's an ESFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        dPrint( 'Never', DEBUGGING_THIS_MODULE, UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
        for BBB,fn in filenameTuples.copy(): # Only accept our specific file extensions
            acceptFlag = False
            for fna in filenameEndingsToAccept:
                if fn.endswith( fna ): acceptFlag = True
            if not acceptFlag: filenameTuples.remove( (BBB,fn) )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "  Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Found {} ESFM files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Found {} ESFM file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, "Got ESFM SSFs: ({}) {}".format( len(SSFs), SSFs ) )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "ESFMBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = ESFMBible( foundProjects[0] )
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of ESFMBibleFileCheck



linkedWordRegex = re.compile( '([-A-za-zⱤḩⱪşʦāēīōūəʸʼˊ/()]+)¦([1-9][0-9]{0,5})' )
class ESFMBible( Bible ):
    """
    Class to load and manipulate ESFM Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None ) -> None:
        """
        Create the internal ESFM Bible object.

        Note that there's no encoding parameter here
            because ESFM is defined to only be UTF-8.

        After creating the class,
            set loadAuxilliaryFiles to True if
                you want metadata and word files to be loaded along with each book.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.__init__( {!r}, {!r}, {!r} )".format( sourceFolder, givenName, givenAbbreviation ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'ESFM Bible object'
        self.objectTypeString = 'ESFM'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation = sourceFolder, givenName, givenAbbreviation
        self.dontLoadBook = []

        self.loadAuxilliaryFiles = False
        self.ESFMWorkData, self.ESFMFileData, self.ESFMWordTables = {}, {}, {}
        self.spellingDict, self.StrongsDict, self.hyphenationDict, self.semanticDict = {}, {}, {}, {}
    # end of ESFMBible.__init_


    def preload( self ):
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.preload() from {}".format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what {!r} is in {}!".format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( "ESFMBible.load: Surprised to see subfolders in {!r}: {}".format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ESFMBible: Couldn't find any files in {!r}".format( self.sourceFolder ) )
            return # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}

        # Attempt to load the SSF file
        self.ssfFilepath = None
        ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
        if len(ssfFilepathList) == 1: # Seems we found the right one
            self.ssfFilepath = ssfFilepathList[0]
            PTXSettingsDict = loadPTX7ProjectData( self, self.ssfFilepath )
            if PTXSettingsDict:
                if 'PTX7' not in self.suppliedMetadata: self.suppliedMetadata['PTX7'] = {}
                self.suppliedMetadata['PTX7']['SSF'] = PTXSettingsDict
                self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "ESFM Bible"

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.availableBBBs.add( BBB )
            self.possibleFilenameDict[BBB] = filename

        self.preloadDone = True
    # end of ESFMBible.preload


    #def loadMetadata( self, ssfFilepath ):
        #"""
        #Process the SSF metadata from the given filepath into self.suppliedMetadata.

        #Returns a dictionary.
        #"""
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, _("Loading SSF data from {!r}").format( ssfFilepath ) )
        #lastLine, lineCount, status, self.suppliedMetadata = '', 0, 0, {}
        #self.suppliedMetadata['MetadataType'] = 'SSFMetadata'
        #with open( ssfFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
            #for line in myFile:
                #lineCount += 1
                #if lineCount==1 and line and line[0]==BibleOrgSysGlobals.BOM:
                    #logging.info( "ESFMBible.loadMetadata: Detected Unicode Byte Order Marker (BOM) in {}".format( ssfFilepath ) )
                    #line = line[1:] # Remove the Byte Order Marker (BOM)
                #if line and line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                #line = line.strip() # Remove leading and trailing whitespace
                #if not line: continue # Just discard blank lines
                #lastLine = line
                #processed = False
                #if status==0 and line=="<ScriptureText>":
                    #status = 1
                    #processed = True
                #elif status==1 and line=="</ScriptureText>":
                    #status = 2
                    #processed = True
                #elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a self-closing (empty) field
                    #fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
                    #if ' ' not in fieldname:
                        #self.suppliedMetadata[fieldname] = ''
                        #processed = True
                    #elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                        #bits = fieldname.split( None, 1 )
                        #if BibleOrgSysGlobals.debugFlag: assert len(bits)==2
                        #fieldname = bits[0]
                        #attributes = bits[1]
                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "attributes = {!r}".format( attributes) )
                        #self.suppliedMetadata[fieldname] = (contents, attributes)
                        #processed = True
                #elif status==1 and line[0]=='<' and line[-1]=='>':
                    #ix1 = line.find('>')
                    #ix2 = line.find('</')
                    #if ix1!=-1 and ix2!=-1 and ix2>ix1:
                        #fieldname = line[1:ix1]
                        #contents = line[ix1+1:ix2]
                        #if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                            #self.suppliedMetadata[fieldname] = contents
                            #processed = True
                        #elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                            #bits = fieldname.split( None, 1 )
                            #if BibleOrgSysGlobals.debugFlag: assert len(bits)==2
                            #fieldname = bits[0]
                            #attributes = bits[1]
                            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "attributes = {!r}".format( attributes) )
                            #if line[ix2+2:-1]==fieldname:
                                #self.suppliedMetadata[fieldname] = (contents, attributes)
                                #processed = True
                #if not processed: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ERROR: Unexpected {!r} line in SSF file".format( line ) )
        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  " + _("Got {} SSF entries:").format( len(self.suppliedMetadata) ) )
            #if BibleOrgSysGlobals.verbosityLevel > 3:
                #for key in sorted(self.suppliedMetadata):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    {}: {}".format( key, self.suppliedMetadata[key] ) )
        #self.applySuppliedMetadata() # Copy to self.settingsDict
    ## end of ESFMBible.loadMetadata


    def loadSemanticDictionary( self, BBB:str, filename ):
        """
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "    " + _("Loading possible semantic dictionary from {}…").format( filename ) )
        sourceFilepath = os.path.join( self.sourceFolder, filename )
        originalBook = ESFMFile()
        originalBook.read( sourceFilepath )

        count = 0
        for marker,originalText in originalBook.lines:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, marker, repr(originalText) )
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
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if count: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} semantic entries added in {} categories".format( count, len(self.semanticDict) ) )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "No semantic entries found." )
    # end of ESFMBible.loadSemanticDictionary


    def loadStrongsDictionary( self, BBB:str, filename ):
        """
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "    " + _("Loading possible Strong's dictionary from {}…").format( filename ) )
        sourceFilepath = os.path.join( self.sourceFolder, filename )
        originalBook = ESFMFile()
        originalBook.read( sourceFilepath )

        count = 0
        for marker,originalText in originalBook.lines:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, marker, repr(originalText) )
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
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if count: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} Strong's entries added in {} categories".format( count, len(self.StrongsDict) ) )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "No Strong's entries found." )
    # end of ESFMBible.loadStrongsDictionary


    def loadDictionaries( self ):
        """
        Attempts to load the spelling, hyphenation, and semantic dictionaries if they exist.
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  " + _("Loading any dictionaries…") )
        for BBB,filename in self.maximumPossibleFilenameTuples:
            if BBB=='XXD': self.loadSemanticDictionary( BBB, filename )
            elif BBB=='XXE': self.loadStrongsDictionary( BBB, filename )
    # end of ESFMBible.loadDictionaries


    def loadBook( self, BBB:str, filename=None ):
        """
        Load the requested book if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.dontLoadBook: return # Must be a dictionary that's already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading ESFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        try:
            if filename is None and BBB in self.possibleFilenameDict:
                filename = self.possibleFilenameDict[BBB]
        except AttributeError as e:
            logging.critical( f"Was a preload() done on this {self.abbreviation} ESFMBible? Or is folder {self.sourceFolder} empty? (Can't find any possible filenames.)" )
            # raise ValueError( f"ESFMBible.loadBook: Unable to load {BBB}{' '+filename if filename else ''} for {self.abbreviation} ESFM Bible" )
        if filename is None:
            raise FileNotFoundError( "ESFMBible.loadBook: Unable to find file for {}".format( BBB ) )

        EBB = ESFMBibleBook( self, BBB )
        EBB.load( filename, self.sourceFolder )
        if EBB._rawLines:
            EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.stashBook( EBB )
        else: logging.info( "ESFM book {} was completely blank".format( BBB ) )
    # end of ESFMBible.loadBook


    def _loadBookMP( self, BBB_Filename ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.loadBookMP( {} )".format( BBB_Filename ) )
        BBB, filename = BBB_Filename
        assert BBB not in self.books
        if BBB in self.dontLoadBook: return None
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        EBB = ESFMBibleBook( self, BBB )
        EBB.load( self.possibleFilenameDict[BBB], self.sourceFolder )
        EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("    Finishing loading ESFM book {}.").format( BBB ) )
        return EBB
    # end of ESFMBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books that we can find.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.loadBooks() loading {} from {}".format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            # First try to load the dictionaries
            self.loadDictionaries()
            # Now load the books
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ESFMBible: Loading {} ESFM books using {} processes…".format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results:
                        if bBook is not None:
                            bBook.containerBibleObject = self # Because the pickling and unpickling messes this up
                            self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    if BBB not in self.dontLoadBook:
                        loadedBook = self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( "ESFMBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.getBookList() )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE:
            if 'Tag errors' in self.semanticDict:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFMBible.load tag errors:", self.semanticDict['Tag errors'] )
            if 'Missing' in self.semanticDict:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFMBible.load missing:", self.semanticDict['Missing'] )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nSemantic dict: {}".format( self.semanticDict ) )
        if self.semanticDict:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n\nSemantic dict:" )
            for someKey,someEntry in self.semanticDict.items():
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{}: {}".format( someKey, someEntry ) )
        if self.loadAuxilliaryFiles: self.lookForAuxilliaryFilenames()
        self.doPostLoadProcessing()
    # end of ESFMBible.loadBooks

    def load( self ):
        self.loadBooks()


    def lookForAuxilliaryFilenames( self ):
        """
        Looks into the loaded ESFM books for WORKDATA, FILEDATA, and/or WORDTABLE auxilliary filenames.
            \\id 1JN - Matigsalug Translation v1.0.17
            \\usfm 3.0
            \\ide UTF-8
            \\rem ESFM v0.6 JN1
            \\rem WORKDATA Matigsalug.txt
            \\rem FILEDATA Matigsalug.JN1.txt
            \\rem WORDTABLE Matigsalug.words.tsv
            \\h 1 Huwan

        If it finds some, and if that particular filename is not yet already listed,
            loads any unique filename into a dict with the value set to None.
        Also checks that the referred file does actually exist.

        By doing it at this Bible level,
            later we can cache any data files that are used by multiple Bible books.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ESFMBible.lookForAuxilliaryFilenames()" )

        for BBB,bookObject in self.books.items():
            if bookObject.ESFMWorkDataFilename:
                assert bookObject.ESFMWorkDataFilename.endswith( '.txt' )
                if bookObject.ESFMWorkDataFilename not in self.ESFMWorkData:
                    self.ESFMWorkData[bookObject.ESFMWorkDataFilename] = None
                    filepath = os.path.join( self.sourceFolder, bookObject.ESFMWorkDataFilename )
                    if not os.path.isfile( filepath ):
                        logging.critical( f"ESFMBible.lookForAuxilliaryFilenames didn't find a WORK DATA file at {filepath}")
                if len(self.ESFMWorkData) > 1:
                    logging.critical( f"ESFMBible.lookForAuxilliaryFilenames didn't expect MULTIPLE WORK DATA files: ({len(self.ESFMWorkData)}) {[k for k in self.ESFMWorkData]}")
            if bookObject.ESFMFileDataFilename:
                assert bookObject.ESFMFileDataFilename.endswith( '.txt' )
                if bookObject.ESFMFileDataFilename in self.ESFMFileData:
                    logging.critical( f"ESFMBible.lookForAuxilliaryFilenames didn't expect REPEATED FILE DATA files: ({len(self.ESFMFileData)}) {[k for k in self.ESFMFileData]} now {BBB} {bookObject.ESFMFileDataFilename}")
                else:
                    self.ESFMFileData[bookObject.ESFMFileDataFilename] = None
                    filepath = os.path.join( self.sourceFolder, bookObject.ESFMFileDataFilename )
                    if not os.path.isfile( filepath ):
                        logging.critical( f"ESFMBible.lookForAuxilliaryFilenames didn't find a FILE DATA file at {filepath}")
            if bookObject.ESFMWordTableFilename:
                assert bookObject.ESFMWordTableFilename.endswith( '.tsv' )
                if bookObject.ESFMWordTableFilename not in self.ESFMWordTables:
                    self.ESFMWordTables[bookObject.ESFMWordTableFilename] = None
                    filepath = os.path.join( self.sourceFolder, bookObject.ESFMWordTableFilename )
                    if not os.path.isfile( filepath ):
                        logging.critical( f"ESFMBible.lookForAuxilliaryFilenames didn't find a WORD TABLE file at {filepath}")
        if DEBUGGING_THIS_MODULE:
            print( f"{self.ESFMWorkData=}" )
            print( f"{self.ESFMFileData=}" )
            print( f"{self.ESFMWordTables=}" )
    # end of ESFMBible.lookForAuxilliaryFilenames


    def livenESFMWordLinks( self, BBB:str, verseList:InternalBibleEntryList, linkTemplate:str ) -> Tuple[InternalBibleEntryList,Optional[List[str]]]:
        """
        The link template can be a filename like 'Word_{n}.html' or an entire link like 'https://SomeSite/words/page_{n}.html'
            The '{n}' gets substituted with the actual word link string.

        Note that we don't have enough information here to surround the <a>..</a> link with a <span title="something">..</span>
            so that will have to be done later.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"livenESFMWordLinks( {BBB}, ({len(verseList)}) {verseList} )" )
        assert '{n}' in linkTemplate
        bookObject = self.books[BBB]
        wordFileName = bookObject.ESFMWordTableFilename
        if wordFileName:
            assert wordFileName.endswith( '.tsv' )
            # print( f"ESFMBible.livenESFMWordLinks found filename '{wordFileName}' for {self.abbreviation} {BBB}" )
            # print( f"ESFMBible.livenESFMWordLinks found loaded word links: {self.ESFMWordTables[wordFileName]}" )
            if self.ESFMWordTables[wordFileName] is None:
                with open( os.path.join( self.sourceFolder, wordFileName ), 'rt', encoding='UTF-8' ) as wordFile:
                    self.ESFMWordTables[wordFileName] = wordFile.read().rstrip( '\n' ).split( '\n' ) # Remove any blank line at the end then split
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"ESFMBible.livenESFMWordLinks loaded {len(self.ESFMWordTables[wordFileName]):,} total rows from {wordFileName}" )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"ESFMBible.livenESFMWordLinks loaded column names were: ({len(self.ESFMWordTables[wordFileName][0])}) {self.ESFMWordTables[wordFileName][0]}" )

        updatedVerseList = InternalBibleEntryList()
        for entry in verseList:
            originalText = entry.getOriginalText()
            if originalText is None or '¦' not in originalText:
                updatedVerseList.append( entry )
                continue
            # If we get here, we have at least one ESFM wordlink row number in the text
            # print( f"{n}: '{originalText}'")
            searchStartIndex = 0
            count = 0
            while True:
                match = linkedWordRegex.search( originalText, searchStartIndex )
                if not match:
                    break
                # print( f"{BBB} word match 1='{match.group(1)}' 2='{match.group(2)}' all='{book_html[match.start():match.end()]}'" )
                assert match.group(2).isdigit()
                # row_number = int( match.group(2) )
                originalText = f'''{originalText[:match.start()]}<a href="{linkTemplate.replace('{n}', match.group(2))}">{match.group(1)}</a>{originalText[match.end():]}'''
                searchStartIndex = match.end() + len(linkTemplate) + 4 # We've added at least that many characters
                count += 1
            if count > 0:
                # print( f"  Now '{originalText}'")
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Made {count:,} {self.abbreviation} {BBB} ESFM words into live links." )
                # adjText, cleanText, extras = _processLineFix( self, C:str,V:str, originalMarker:str, text:str, fixErrors:List[str] )
                # newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras(), originalText )
                # Since we messed up many of the fields, set them to blank/null entries so that the old/wrong/outdated values can't be accidentally used
                newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), None, '', None, originalText )
                updatedVerseList.append( newEntry )
            else:
                logging.critical( f"ESFMBible.livenESFMWordLinks unable to find wordlink in '{originalText}'" )
                updatedVerseList.append( entry )

        return updatedVerseList, self.ESFMWordTables[wordFileName]if wordFileName else None
    # end of ESFMBible.livenESFMWordLinks
# end of class ESFMBible



def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Load and process some of our test versions
        count = 0
        for name, abbreviation, testFolder in ( # name, abbreviation, folder
            # Not actual ESFM
                #("All Markers Project2", "USFM2All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/')),
                #("All Markers Project3", "USFM3All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/')),
                ("USFM Error Project", "UEP", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/')),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM2_Export/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM2_Reexport/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM3_Export/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM3_Reexport/"),
            # Actual ESFM Bibles
                ("Matigsalug", "MBTV", Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'),),
                ("ESFM Test 1", "OET-LV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/')),
                ("ESFM Test 2", "OET-RV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/')),
                ("Open English Translation—Literal Version", 'OET-LV', Path( '/mnt/SSDs/Matigsalug/Bible/OET-LV/'),),
                ("Open English Translation—Base Version", 'OET-BV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-BV'),),
                ("Open English Translation—Literal Version", 'OET-LV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-LV'),),
                ("Open English Translation—Readers' Version", 'OET-RV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-RV'),),
                ("Open English Translation—Colloquial Version", 'OET-CV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-CV'),),
                ("Open English Translation—Study Version", 'OET-SV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-SV'),),
                ("Open English Translation—Extended Version", 'OET-EV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-EV'),),
                ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFM A{}/".format( count ) )
                EsfmB = ESFMBible( testFolder, name, abbreviation )
                EsfmB.load()
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen assumed book name:", repr( EsfmB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen long TOC book name:", repr( EsfmB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen short TOC book name:", repr( EsfmB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen book abbreviation:", repr( EsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    EsfmB.check()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB.books['GEN']._processedLines[0:40] )
                    EsfmBErrors = EsfmB.getCheckResults()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##EsfmB.toDrupalBible()
                    EsfmB.doAllExports( wantPhotoBible=False, wantODFs=True, wantPDFs=True )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(abbreviation) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "newObj is", newObj )
                break
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test a whole folder full of folders of ESFM Bibles
        testBaseFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==BibleOrgSysGlobals.BOM:
                        logging.info( "ESFMBible: Detected Unicode Byte Order Marker (BOM) in copyright.htm file" )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        ESFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromESFM( ESFM_BBB )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ESFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a ESFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, testFolder = title, somepath
                    if os.access( testFolder, os.R_OK ):
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFM B{}/".format( count ) )
                        EsfmB = ESFMBible( testFolder, name )
                        EsfmB.load()
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            EsfmB.check()
                            EsfmBErrors = EsfmB.getCheckResults()
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export: EsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
            if count: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{} total ESFM (partial) Bibles processed.".format( count ) )
            if totalBooks: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testBaseFolder}' is not readable on this computer." )
#end of ESFMBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Load and process some of our test versions
        count = 0
        for name, abbreviation, testFolder in ( # name, abbreviation, folder
            # Not actual ESFM
                #("All Markers Project2", "USFM2All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/')),
                #("All Markers Project3", "USFM3All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/')),
                ("USFM Error Project", "UEP", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/')),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM2_Export/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM2_Reexport/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM3_Export/"),
                ("BOS Exported Files", "Exported", "BOSOutputFiles/BOS_USFM3_Reexport/"),
            # Actual ESFM Bibles
                ("Matigsalug", "MBTV", Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/'),),
                ("ESFM Test 1", "OET-LV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/')),
                ("ESFM Test 2", "OET-RV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/')),
                ("Open English Translation—Literal Version", 'OET-LV', Path( '/mnt/SSDs/Matigsalug/Bible/OET-LV/'),),
                ("Open English Translation—Base Version", 'OET-BV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-BV'),),
                ("Open English Translation—Literal Version", 'OET-LV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-LV'),),
                ("Open English Translation—Readers' Version", 'OET-RV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-RV'),),
                ("Open English Translation—Colloquial Version", 'OET-CV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-CV'),),
                ("Open English Translation—Study Version", 'OET-SV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-SV'),),
                ("Open English Translation—Extended Version", 'OET-EV', Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-EV'),),
                ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFM A{}/".format( count ) )
                EsfmB = ESFMBible( testFolder, name, abbreviation )
                EsfmB.load()
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen assumed book name:", repr( EsfmB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen long TOC book name:", repr( EsfmB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen short TOC book name:", repr( EsfmB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen book abbreviation:", repr( EsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    EsfmB.check()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB.books['GEN']._processedLines[0:40] )
                    EsfmBErrors = EsfmB.getCheckResults()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##EsfmB.toDrupalBible()
                    EsfmB.doAllExports( wantPhotoBible=False, wantODFs=True, wantPDFs=True )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(abbreviation) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "newObj is", newObj )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test a whole folder full of folders of ESFM Bibles
        testBaseFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==BibleOrgSysGlobals.BOM:
                        logging.info( "ESFMBible: Detected Unicode Byte Order Marker (BOM) in copyright.htm file" )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        ESFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromESFM( ESFM_BBB )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ESFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a ESFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, testFolder = title, somepath
                    if os.access( testFolder, os.R_OK ):
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nESFM B{}/".format( count ) )
                        EsfmB = ESFMBible( testFolder, name )
                        EsfmB.load()
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            EsfmB.check()
                            EsfmBErrors = EsfmB.getCheckResults()
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, EsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export: EsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
            if count: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{} total ESFM (partial) Bibles processed.".format( count ) )
            if totalBooks: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testBaseFolder}' is not readable on this computer." )
# end of ESFMBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESFMBible.py
