#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ESFMBible.py
#
# Module handling compilations of ESFM Bible books
#
# Copyright (C) 2010-2019 Robert Hunt
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

Creates a semantic dictionary with keys:
    'Tag errors': contains a list of 4-tuples (BBB,C,V,errorWord)
    'Missing': contains a dictionary
    'A' 'G' 'L' 'O' 'P' 'Q' entries each containing a dictionary
        where the key is the name (e.g., 'Jonah')
        and the entry is a list of 4-tuples (BBB,C,V,actualWord)
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "ESFMBible"
PROGRAM_NAME = "ESFM Bible handler"
PROGRAM_VERSION = '0.61'
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
from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames
from BibleOrgSys.Formats.PTX7Bible import loadPTX7ProjectData
from BibleOrgSys.InputOutput.ESFMFile import ESFMFile
from BibleOrgSys.Formats.ESFMBibleBook import ESFMBibleBook, ESFM_SEMANTIC_TAGS
from BibleOrgSys.Bible import Bible



filenameEndingsToAccept = ('.ESFM',) # Must be UPPERCASE here



def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( SHORT_PROGRAM_NAME, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, errorBit )
# end of t



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
    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "ESFMBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        assert givenFolderName and isinstance( givenFolderName, str )
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
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ESFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
                ##print( 'E1', repr(firstLine) )
                #if firstLine is None: continue # seems we couldn't decode the file
                #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                    #logging.info( "ESFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                    #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if not firstLine: continue # don't allow a blank first line
                #if firstLine[0] != '\\': continue # Must start with a backslash
            #foundFiles.append( something )

    # See if there's an ESFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
    for BBB,fn in filenameTuples[:]: # Only accept our specific file extensions
        acceptFlag = False
        for fna in filenameEndingsToAccept:
            if fn.endswith( fna ): acceptFlag = True
        if not acceptFlag: filenameTuples.remove( (BBB,fn) )
    if BibleOrgSysGlobals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "  Found {} ESFM file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Got ESFM SSFs: ({}) {}".format( len(SSFs), SSFs ) )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESFMBibleFileCheck got", numFound, givenFolderName )
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
        #if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ESFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
                    ##print( 'E2', repr(firstLine) )
                    #if firstLine is None: continue # seems we couldn't decode the file
                    #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                        #logging.info( "ESFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                        #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                    #if not firstLine: continue # don't allow a blank first line
                    #if firstLine[0] != '\\': continue # Must start with a backslash
                #foundSubfiles.append( something )

        # See if there's an ESFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
        for BBB,fn in filenameTuples[:]: # Only accept our specific file extensions
            acceptFlag = False
            for fna in filenameEndingsToAccept:
                if fn.endswith( fna ): acceptFlag = True
            if not acceptFlag: filenameTuples.remove( (BBB,fn) )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} ESFM files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "  Found {} ESFM file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Got ESFM SSFs: ({}) {}".format( len(SSFs), SSFs ) )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESFMBibleFileCheck foundProjects", numFound, foundProjects )
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
        if debuggingThisModule:
            print( "ESFMBible.__init__( {!r}, {!r}, {!r} )".format( sourceFolder, givenName, givenAbbreviation ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'ESFM Bible object'
        self.objectTypeString = 'ESFM'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation = sourceFolder, givenName, givenAbbreviation

        self.dontLoadBook = []
        self.spellingDict, self.StrongsDict, self.hyphenationDict, self.semanticDict = {}, {}, {}, {}
    # end of ESFMBible.__init_


    def preload( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("preload() from {}").format( self.sourceFolder ) )

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
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "ESFMBible: Couldn't find any files in {!r}".format( self.sourceFolder ) )
            return # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( self.USFMFilenamesObject )

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
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading SSF data from {!r}").format( ssfFilepath ) )
        #lastLine, lineCount, status, self.suppliedMetadata = '', 0, 0, {}
        #self.suppliedMetadata['MetadataType'] = 'SSFMetadata'
        #with open( ssfFilepath, encoding='utf-8' ) as myFile: # Automatically closes the file when done
            #for line in myFile:
                #lineCount += 1
                #if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
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
                        ##print( "attributes = {!r}".format( attributes) )
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
                            ##print( "attributes = {!r}".format( attributes) )
                            #if line[ix2+2:-1]==fieldname:
                                #self.suppliedMetadata[fieldname] = (contents, attributes)
                                #processed = True
                #if not processed: print( "ERROR: Unexpected {!r} line in SSF file".format( line ) )
        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #print( "  " + _("Got {} SSF entries:").format( len(self.suppliedMetadata) ) )
            #if BibleOrgSysGlobals.verbosityLevel > 3:
                #for key in sorted(self.suppliedMetadata):
                    #print( "    {}: {}".format( key, self.suppliedMetadata[key] ) )
        #self.applySuppliedMetadata() # Copy to self.settingsDict
    ## end of ESFMBible.loadMetadata


    def loadSemanticDictionary( self, BBB, filename ):
        """
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "    " + _("Loading possible semantic dictionary from {}…").format( filename ) )
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
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if count: print( "{} semantic entries added in {} categories".format( count, len(self.semanticDict) ) )
            else: print( "No semantic entries found." )
    # end of ESFMBible.loadSemanticDictionary


    def loadStrongsDictionary( self, BBB, filename ):
        """
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "    " + _("Loading possible Strong's dictionary from {}…").format( filename ) )
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
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if count: print( "{} Strong's entries added in {} categories".format( count, len(self.StrongsDict) ) )
            else: print( "No Strong's entries found." )
    # end of ESFMBible.loadStrongsDictionary


    def loadDictionaries( self ):
        """
        Attempts to load the spelling, hyphenation, and semantic dictionaries if they exist.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "  " + _("Loading any dictionaries…") )
        for BBB,filename in self.maximumPossibleFilenameTuples:
            if BBB=='XXD': self.loadSemanticDictionary( BBB, filename )
            elif BBB=='XXE': self.loadStrongsDictionary( BBB, filename )
    # end of ESFMBible.loadDictionaries


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESFMBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.dontLoadBook: return # Must be a dictionary that's already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading ESFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
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
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "ESFMBible.loadBookMP( {} )".format( BBB_Filename ) )
        BBB, filename = BBB_Filename
        assert BBB not in self.books
        if BBB in self.dontLoadBook: return None
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        EBB = ESFMBibleBook( self, BBB )
        EBB.load( self.possibleFilenameDict[BBB], self.sourceFolder )
        EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading ESFM book {}.").format( BBB ) )
        return EBB
    # end of ESFMBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("ESFMBible: Loading {} from {}…").format( self.name, self.sourceFolder ) )

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
                    print( t("ESFMBible: Loading {} ESFM books using {} processes…").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results:
                        if bBook is not None: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  ESFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    if BBB not in self.dontLoadBook:
                        loadedBook = self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( "ESFMBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
            if 'Tag errors' in self.semanticDict:
                print( "\nESFMBible.load tag errors:", self.semanticDict['Tag errors'] )
            if 'Missing' in self.semanticDict:
                print( "\nESFMBible.load missing:", self.semanticDict['Missing'] )
        #print( "\nSemantic dict: {}".format( self.semanticDict ) )
        if debuggingThisModule:
            print( "\n\nSemantic dict:" )
            for someKey,someEntry in self.semanticDict.items():
                print( "\n{}: {}".format( someKey, someEntry ) )
        self.doPostLoadProcessing()
    # end of ESFMBible.load

    def load( self ):
        self.loadBooks()
# end of class ESFMBible



def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # Load and process some of our test versions
        count = 0
        for name, abbreviation, testFolder in ( # name, abbreviation, folder
            # Not actual ESFM
                #("All Markers Project2", "USFM2All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/')),
                #("All Markers Project3", "USFM3All", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/')),
                ("USFM Error Project", "UEP", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/')),
                ("BOS Exported Files", "Exported", "OutputFiles/BOS_USFM2_Export/"),
                ("BOS Exported Files", "Exported", "OutputFiles/BOS_USFM2_Reexport/"),
                ("BOS Exported Files", "Exported", "OutputFiles/BOS_USFM3_Export/"),
                ("BOS Exported Files", "Exported", "OutputFiles/BOS_USFM3_Reexport/"),
            # Actual ESFM Bibles
                ("Matigsalug", "MBTV", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'),),
                ("ESFM Test 1", "OET-LV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/')),
                ("ESFM Test 2", "OET-RV", BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/')),
                ("Open English Translation—Literal Version", 'OET-LV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/OET-LV/'),),
                ("Open English Translation—Base Version", 'OET-BV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-BV'),),
                ("Open English Translation—Literal Version", 'OET-LV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-LV'),),
                ("Open English Translation—Readers' Version", 'OET-RV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-RV'),),
                ("Open English Translation—Colloquial Version", 'OET-CV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-CV'),),
                ("Open English Translation—Study Version", 'OET-SV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-SV'),),
                ("Open English Translation—Extended Version", 'OET-EV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/OET-EV'),),
                ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nESFM A{}/".format( count ) )
                EsfmB = ESFMBible( testFolder, name, abbreviation )
                EsfmB.load()
                if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Gen assumed book name:", repr( EsfmB.getAssumedBookName( 'GEN' ) ) )
                    print( "Gen long TOC book name:", repr( EsfmB.getLongTOCName( 'GEN' ) ) )
                    print( "Gen short TOC book name:", repr( EsfmB.getShortTOCName( 'GEN' ) ) )
                    print( "Gen book abbreviation:", repr( EsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( EsfmB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    EsfmB.check()
                    #print( EsfmB.books['GEN']._processedLines[0:40] )
                    EsfmBErrors = EsfmB.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##EsfmB.toDrupalBible()
                    EsfmB.doAllExports( wantPhotoBible=False, wantODFs=True, wantPDFs=True )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(abbreviation) + '.pickle', os.path.join( "OutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "newObj is", newObj )
            else: print( f"\nSorry, test folder '{testFolder}' is not readable on this computer." )


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
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
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
                        #print( ESFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): print( "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a ESFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, testFolder = title, somepath
                    if os.access( testFolder, os.R_OK ):
                        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nESFM B{}/".format( count ) )
                        EsfmB = ESFMBible( testFolder, name )
                        EsfmB.load()
                        if BibleOrgSysGlobals.verbosityLevel > 0: print( EsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            EsfmB.check()
                            EsfmBErrors = EsfmB.getErrors()
                            #print( EsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export: EsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: print( f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
            if count: print( "\n{} total ESFM (partial) Bibles processed.".format( count ) )
            if totalBooks: print( "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        else: print( f"\nSorry, test folder '{testBaseFolder}' is not readable on this computer." )
#end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESFMBible.py
