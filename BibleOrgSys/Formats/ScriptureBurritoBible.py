#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ScriptureBurritoBible.py
#
# Module handling Scripture Burrito (SB) JSON metadata
#   along with compilations of USFM or USX XML Bible books
# This module handles any text SBs with B/C/V encoding,
#   i.e., Bibles and commentaries, etc.
#
# Copyright (C) 2022 Robert Hunt
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
Module for defining and manipulating complete or partial SB Bible bundles
    saved in folders on the local filesystem.

See https://docs.burrito.bible/en/develop/index.html
as well as various repositories at https://github.com/bible-technology.
"""

from gettext import gettext as _
import os
import logging
import multiprocessing
from pathlib import Path
import json

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Formats.USXXMLBible import USXXMLBible
from BibleOrgSys.Formats.USFMBibleBook import USFMBibleBook
from BibleOrgSys.Formats.USXXMLBibleBook import USXXMLBibleBook


LAST_MODIFIED_DATE = '2022-04-12' # by RJH
SHORT_PROGRAM_NAME = "ScriptureBurrito"
PROGRAM_NAME = "Scripture Burrito (SB) Bible handler"
PROGRAM_VERSION = '0.01'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


COMPULSORY_FILENAMES = ( 'metadata.json', )
COMPULSORY_FOLDERS = ( 'ingredients', ) # WITHOUT trailing slashes



def ScriptureBurritoBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for SB Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one SB Bible bundle is found,
        returns the loaded ScriptureBurritoBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, "ScriptureBurritoBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ScriptureBurritoBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ScriptureBurritoBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, " ScriptureBurritoBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )

    # See if the compulsory files and folder are here in this given folder
    numFound = numFilesFound = numFoldersFound = 0
    for filename in foundFiles:
        if filename in COMPULSORY_FILENAMES: numFilesFound += 1
    for folderName in foundFolders:
        if folderName in COMPULSORY_FOLDERS: numFoldersFound += 1
    if numFilesFound==len(COMPULSORY_FILENAMES) and numFoldersFound==len(COMPULSORY_FOLDERS): numFound += 1

    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "ScriptureBurritoBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = ScriptureBurritoBible( givenFolderName )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            return dB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ScriptureBurritoBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    ScriptureBurritoBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ): foundSubfiles.append( something )
        except PermissionError: pass # can't read folder, e.g., system folder

        # See if the compulsory files and folder are here in this given folder
        numFilesFound = numFoldersFound = 0
        for filename in foundSubfiles:
            if filename in COMPULSORY_FILENAMES: numFilesFound += 1
        for folderName in foundSubfolders:
            if folderName in COMPULSORY_FOLDERS: numFoldersFound += 1
        if numFilesFound==len(COMPULSORY_FILENAMES) and numFoldersFound==len(COMPULSORY_FOLDERS):
            foundProjects.append( tryFolderName )
            numFound += 1

    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "ScriptureBurritoBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            sB = ScriptureBurritoBible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                sB.preload() # Load and process the metadata files
                if autoLoadBooks: sB.loadBooks() # Load and process the book files
            return sB
        return numFound
# end of ScriptureBurritoBibleFileCheck



class ScriptureBurritoBible( Bible ):
    """
    Class to load and manipulate SB Bible bundles.
    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ) -> None:
        """
        Create the internal SB Bible object.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "ScriptureBurritoBible.__init__( {}, {}, {} )".format( givenFolderName, givenName, encoding ) )
        if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
            assert isinstance( givenFolderName, (str,Path) )
            assert isinstance( givenName, str )
            assert isinstance( encoding, str )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'SB XML Bible object'
        self.objectTypeString = 'SB'

        self.sourceFolder, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.sourceFilepath = self.sourceFolder
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        #if givenName:
            #if not os.access( self.sourceFolder, os.R_OK ):
                #logging.error( "ScriptureBurritoBible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            #self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        #else: self.sourceFilepath = self.sourceFolder
        if not os.access( self.sourceFolder, os.R_OK ):
            logging.error( "ScriptureBurritoBible: Folder '{}' is unreadable".format( self.sourceFolder ) )

        # Create empty containers for loading the XML metadata files
        #SBLicense = SBStyles = SBVersification = SBLanguage = None
    # end of ScriptureBurritoBible.__init__


    def preload( self ):
        """
        Load the JSON metadata file.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "preload() from {}".format( self.sourceFolder ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("ScriptureBurritoBible: Loading {} from {}…").format( self.name, self.sourceFilepath ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ERROR: Not sure what '{}' is in {}!".format( somepath, self.sourceFilepath ) )
        if not foundFiles:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ScriptureBurritoBible.preload: Couldn't find any files in '{}'".format( self.sourceFilepath ) )
            return # No use continuing

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['SB'] = {}

        self.loadSBMetadata() # into self.suppliedMetadata['SB'] (still in SB format)
        self.applySuppliedMetadata( 'SB' ) # copy into self.settingsDict (standardised)
        self.preloadDone = True
    # end of ScriptureBurritoBible.preload


    def loadSBMetadata( self ):
        """
        Load the metadata.json file and parse it into the ordered dictionary self.suppliedMetadata.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "loadSBMetadata()" )

        loadErrors:List[str] = []
        mdFilepath = os.path.join( self.sourceFilepath, 'metadata.json' )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "ScriptureBurritoBible.loading supplied SB metadata from {}…".format( mdFilepath ) )
        with open(mdFilepath, 'rt', encoding='utf-8') as jsonFile:
            loadedJson = json.load(jsonFile)
        #print(loadedJson.keys()) # dict_keys(['meta', 'idAuthorities', 'identification', 'confidential', 'languages', 'type', 'copyright', 'localizedNames', 'ingredients'])
        if not loadedJson:
            logging.error(f"Unable to load SB metadata from {mdFilepath}")
            loadErrors.append(f"ERROR: Unabled to load SB metadata from {mdFilepath}")
        elif len(loadedJson) < 4:
            logging.warning(f"Seems that loaded SB metadata might be deficient with only keys: {loadedJson.keys()}")
            loadErrors.append(f"WARNING: Seems that loaded SB metadata might be deficient with only keys: {loadedJson.keys()}")

        try:
            if loadedJson['confidential'] == True:
                logging.warning("This Scripture Burrito seems to be confidential!")
                loadErrors.append("WARNING: This Scripture Burrito seems to be confidential!")
        except: pass

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['SB'] = loadedJson # Put it all straight in
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  Loaded {} supplied top-level SB metadata elements.".format( len(self.suppliedMetadata['SB']) ) )

        if 'ingredients' in self.suppliedMetadata['SB']: # Find available books
            self.possibleFilenameDict = {}
            self.maximumPossibleFilenameTuples = []
            haveUSFM = haveUSX = False
            for someKey,someValue in self.suppliedMetadata['SB']['ingredients'].items():
                if someValue['mimeType'] == 'text/x-usfm': haveUSFM = True
                elif someValue['mimeType'] == 'text/x-usx': haveUSX = True
                else:
                    logging.error(f"Unrecognised {someKey} SB '{someValue['mimeType']}' format")
                    loadErrors.append(f"ERROR: Unrecognised {someKey} SB '{someValue['mimeType']}' format")
                if len(someValue['scope']) == 1: # We only expect one book per file
                    USFMBookCode = list(someValue['scope'].keys())[0]
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                    self.givenBookList.append( BBB )
                    self.availableBBBs.add( BBB )
                    self.possibleFilenameDict[BBB] = someKey
                    self.maximumPossibleFilenameTuples.append( (BBB,someKey) )
                else:
                    logging.error(f"Only expected {someKey} to contain one book: {someValue['scope'].keys()}")
                    loadErrors.append(f"ERROR: Only expected {someKey} to contain one book: {someValue['scope'].keys()}")
            if not haveUSFM and not haveUSX:
                logging.warning("Unable to find USFM or USX files in Scripture Burrito")
                loadErrors.append("WARNING: Unable to find USFM or USX files in Scripture Burrito")
            elif haveUSFM and haveUSX:
                logging.warning("Didn't expect both USFM and USX in Scripture Burrito")
                loadErrors.append("WARNING: Didn't expect both USFM and USX in Scripture Burrito")
            else: # Have exactly one of them
                self.suppliedMetadata['SB']['Filetype'] = 'USFM' if haveUSFM else 'USX'
        else:
            logging.warning("No ingredients list in Scripture Burrito")
            loadErrors.append("WARNING: No ingredients list in Scripture Burrito")

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Found {len(self.availableBBBs)} book ingredients in Scripture Burrito for {self.suppliedMetadata['SB']['identification']['name']}")
    # end of ScriptureBurritoBible.loadSBMetadata


    def applySuppliedMetadata( self, applyMetadataType ): # Overrides the default one in InternalBible.py
        """
        Using the dictionary at self.suppliedMetadata,
            load the fields into self.settingsDict
            and try to standardise it at the same time.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "applySuppliedMetadata( {} )".format( applyMetadataType ) )
        assert applyMetadataType in ( 'SB', 'Project', )

        if applyMetadataType == 'Project': # This is different stuff
            Bible.applySuppliedMetadata( self, applyMetadataType )
            return

        # (else) Apply our specialized SB metadata
        try: self.name = self.suppliedMetadata['SB']['identification']['name']['en']
        except KeyError: self.name = list(self.suppliedMetadata['SB']['identification']['name'].keys())[0]
        try: self.abbreviation = self.suppliedMetadata['SB']['identification']['abbreviation']['en']
        except KeyError: self.abbreviation = list(self.suppliedMetadata['SB']['identification']['abbreviation'].keys())[0]
        # print(self.name, self.abbreviation)
        self.encoding = 'utf-8'

        # Now we'll flatten the supplied metadata and remove empty values
        flattenedMetadata = {}
        for mainKey,value in self.suppliedMetadata['SB'].items():
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got {} = {}".format( mainKey, value ) )
            if not value: pass # ignore empty ones
            elif isinstance( value, str ): flattenedMetadata[mainKey] = value # Straight copy
            elif isinstance( value, list ):
                for n,someListEntry in enumerate(value):
                    if isinstance( someListEntry, dict ):
                        for subKey,subValue in someListEntry.items():
                            if not subValue:  pass # ignore empty ones
                            elif isinstance( subValue, (str,bool,int) ):
                                flattenedMetadata[mainKey+'--entry'+str(n)+'--'+subKey] = subValue # Straight copy
                    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error5 in applySuppliedMetadata", mainKey, value, someListEntry, repr(someListEntry) ); halt
            elif isinstance( value, dict ): # flatten this
                for subKey,subValue in value.items():
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Got2 {}--{} = {}".format( mainKey, subKey, subValue ) )
                    if not subValue: pass # ignore empty ones
                    elif isinstance( subValue, (str,bool,int) ):
                        flattenedMetadata[mainKey+'--'+subKey] = subValue # Straight copy
                    elif isinstance( subValue, dict ): # flatten this
                        for sub2Key,sub2Value in subValue.items():
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Got3 {}--{}--{} = {}".format( mainKey, subKey, sub2Key, sub2Value ) )
                            if not sub2Value:  pass # ignore empty ones
                            elif isinstance( sub2Value, (str,bool,int) ):
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            # elif isinstance( sub2Value, list ):
                            #     assert sub2Key in ('books','CanonicalContent',)
                            #     flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            elif isinstance( sub2Value, dict ):
                                for sub3Key,sub3Value in sub2Value.items():
                                    if not sub3Value:  pass # ignore empty ones
                                    elif isinstance( sub3Value, (str,bool,int) ):
                                        flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key+'--'+sub3Key] = sub3Value # Straight copy
                                    # elif isinstance( sub3Value, list ):
                                    #     assert sub3Value in ('books','CanonicalContent',)
                                    #     flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key+'--'+sub3Key] = sub3Value # Straight copy
                                    elif isinstance( sub3Value, dict ):
                                        for sub4Key,sub4Value in sub3Value.items():
                                            if not sub4Value:  pass # ignore empty ones
                                            elif isinstance( sub4Value, (str,bool,int) ):
                                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key+'--'+sub3Key+'--'+sub4Key] = sub4Value # Straight copy
                                            # elif isinstance( sub4Value, list ):
                                            #     assert sub3Value in ('books','CanonicalContent',)
                                            #     flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key+'--'+sub3Key+'--'+sub4Key] = sub4Value # Straight copy
                                            # elif isinstance( sub4Value, dict ):
                                            #     if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                                            #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "How do we handle a dict here???", sub3Key, sub4Value )
                                            # elif isinstance( sub4Value, tuple ):
                                            #     if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                                            #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "How do we handle a tuple here???" )
                                            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error4 in applySuppliedMetadata", mainKey, subKey, sub2Key, repr(sub2Value) ); halt
                                    # elif isinstance( sub3Value, tuple ):
                                    #     if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                                    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "How do we handle a tuple here???" )
                                    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error4 in applySuppliedMetadata", mainKey, subKey, sub2Key, repr(sub2Value) ); halt
                            # elif isinstance( sub2Value, tuple ):
                            #     if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
                            #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "How do we handle a tuple here???" )
                            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error3 in applySuppliedMetadata", mainKey, subKey, sub2Key, repr(sub2Value) ); halt
                    elif isinstance( subValue, list ): # flatten this
                        flattenedMetadata[mainKey+'--'+subKey] = '--'.join( subValue )
                    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error2 in applySuppliedMetadata", mainKey, subKey, repr(subValue) ); halt
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Programming error in applySuppliedMetadata", mainKey, repr(value) ); halt
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nflattenedMetadata", flattenedMetadata )

        # The following does nothing useful for SB
        # nameChangeDict = {} #{'License':'Licence'}
        # for oldKey,value in flattenedMetadata.items():
        #     newKey = nameChangeDict[oldKey] if oldKey in nameChangeDict else oldKey
        #     if newKey in self.settingsDict: # We have a duplicate
        #         logging.warning("About to replace {!r}={!r} from metadata file".format( newKey, self.settingsDict[newKey] ) )
        #     else: # Also check for "duplicates" with a different case
        #         ucNewKey = newKey.upper()
        #         for key in self.settingsDict:
        #             ucKey = key.upper()
        #             if ucKey == ucNewKey:
        #                 logging.warning("About to copy {!r} from metadata file even though already have {!r}".format( newKey, key ) )
        #                 break
        #     self.settingsDict[newKey] = value
    # end of InternalBible.applySuppliedMetadata




    def loadBooks( self ):
        """
        Load the USFM or USX (XML) Bible text files.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "loadBooks()" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("ScriptureBurritoBible: Loading {} books from {}…").format( self.name, self.sourceFilepath ) )

        if not self.preloadDone: self.preload()
        if not self.preloadDone: return # coz it must have failed

        if self.suppliedMetadata['SB']['Filetype'] == 'USFM':
            USFMBible.loadBooks( self )
        elif self.suppliedMetadata['SB']['Filetype'] == 'USX':
            USXXMLBible.loadBooks( self )

        self.doPostLoadProcessing()
    # end of ScriptureBurritoBible.loadBooks

    def load( self ):
        self.loadBooks()

    def loadBook( self, BBB:str, filename ) -> None:
        """
        Load the USFM or USX (XML) Bible text file.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "loadBook()" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("ScriptureBurritoBible: Loading {} from {} {}…").format( BBB, self.name, self.sourceFilepath ) )

        if self.suppliedMetadata['SB']['Filetype'] == 'USFM':
            USFMBible.loadBook( self, BBB, filename )
        elif self.suppliedMetadata['SB']['Filetype'] == 'USX':
            USXXMLBible.loadBook( self, BBB, filename )

    def _loadBookMP( self, BBB_Filename_duple ) -> USFMBibleBook:
        """
        Load the USFM or USX (XML) Bible text file (for multiprocessing).
        """
        fnPrint( DEBUGGING_THIS_MODULE, "_loadBookMP()" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("ScriptureBurritoBible: Loading {} from {} {}…").format( BBB_Filename_duple, self.name, self.sourceFilepath ) )

        if self.suppliedMetadata['SB']['Filetype'] == 'USFM':
            return USFMBible._loadBookMP( self, BBB_Filename_duple )
        elif self.suppliedMetadata['SB']['Filetype'] == 'USX':
            return USXXMLBible._loadBookMP( self, BBB_Filename_duple )
# end of class ScriptureBurritoBible



def __processScriptureBurritoBible( parametersTuple ): # for demo
    """
    Special shim function used below for multiprocessing.
    """
    codeLetter, mainFolderName, subFolderName = parametersTuple
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB {} Trying {}".format( codeLetter, subFolderName ) )
    SB_Bible = ScriptureBurritoBible( mainFolderName, subFolderName )
    SB_Bible.load()
    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
        BBB = 'JN1'
        if BBB in SB_Bible:
            SB_Bible.books[BBB].debugPrint()
            for entryKey in SB_Bible.books[BBB]._CVIndex:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )
# end of __processScriptureBurritoBible


def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = ScriptureBurritoBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA1", result1 )
        result2 = ScriptureBurritoBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA2", result2 )
        result3 = ScriptureBurritoBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA3", result3 )


    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Open access Bibles from SB
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB F{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 0: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/sb_textTranslation/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB G{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB H{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/'),
                    ) # You can put your SB test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = ScriptureBurritoBible( testFolder )
                DB.loadSBMetadata()
                DB.preload()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                DB.loadBooks()
                #DBErrors = DB.getCheckResults()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DBErrors )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB.getVersification() )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Looking for", ref )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
    #       pass
# end of ScriptureBurritoBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = ScriptureBurritoBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA1", result1 )
        result2 = ScriptureBurritoBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA2", result2 )
        result3 = ScriptureBurritoBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA3", result3 )

    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Open access Bibles from SB
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB F{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 0: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'SB Bibles/Haiola SB test versions/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB G{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading {} SB modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nSB H{}/ Trying '{}/'…".format( j+1, folderName ) )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
    #       pass
# end of ScriptureBurritoBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ScriptureBurritoBible.py
