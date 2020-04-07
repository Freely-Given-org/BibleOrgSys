#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PickledBible.py
#
# Module handling a set of pickled Bible books (intended for fast loading)
#
# Copyright (C) 2018-2019 Robert Hunt
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
Module for defining and manipulating complete or partial Bibles with a pickled object for each book.

NOTE: Unfortunately it seems that loading a very large pickled object
        including all the linked objects is 3-4 times slower
        than processing the original USFM files from scratch.
    Also, the pickled files seem 10x larger than the originals.
    Ah, but we don't need all those fields, so we added a dataLevel control!

    PickledBibleFileCheck( givenPathname, strictCheck=True, autoLoad=False, autoLoadBooks=False )
    createPickledBible( BibleObject, outputFolder=None, metadataDict=None, dataLevel=None, zipOnly=False )
    getZippedPickledBibleDetails( zipFilepath )
    getZippedPickledBiblesDetails( zipFolderpath, extended=False )
    class PickledBible( Bible )
        __init__( self, sourceFileOrFolder )
        __str__( self )
        preload( self )
            _loadBookEssentials( self, BBB )
        loadBook( self, BBB )
            _loadBookMP( self, BBB )
        loadBooks( self )
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-23' # by RJH
SHORT_PROGRAM_NAME = "PickledBible"
PROGRAM_NAME = "Pickle Bible handler"
PROGRAM_VERSION = '0.15'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
from pathlib import Path
import logging
import pickle
import zipfile
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBibleBook import InternalBibleBook
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList
from BibleOrgSys.Internals.InternalBibleIndexes import InternalBibleCVIndex, InternalBibleSectionIndex



# The following are all case sensitive
ZIPPED_PICKLE_FILENAME_END = '.BOSPickledBible.zip' # This is what the filename must END WITH
DBL_FILENAME_END = 'DBL.zip'
VERSION_FILENAME = 'BibleVersion.pickle' # Contains the object version number
INFO_FILENAME = 'BibleInfo.pickle' # Contains the Bible metadata
BOOK_FILENAME = '{}.pickle' # Each book is stored in a separate BBB.pickle file



def PickledBibleFileCheck( givenPathname:Path, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ) -> int:
    """
    Given a folder, search for Pickle Bible files or folders in the folder and in the next level down.
    Or if given a zip filename, check that.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Pickle Bible is found,
        returns the loaded PickledBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "PickledBibleFileCheck( {}, {}, {}, {} )".format( givenPathname, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenPathname and isinstance( givenPathname, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given path is readable
    if not os.access( givenPathname, os.R_OK ):
        logging.critical( _("PickledBibleFileCheck: Given {!r} path is unreadable").format( givenPathname ) )
        return False

    if str(givenPathname).endswith( ZIPPED_PICKLE_FILENAME_END ): # it's a zipped pickled Bible
        if autoLoad or autoLoadBooks:
            pB = PickledBible( givenPathname )
            if autoLoad or autoLoadBooks: pB.preload() # Load the BibleInfo file
            if autoLoadBooks: pB.loadBooks() # Load and process the book files
            return pB
        return 1 # Number of Bibles found

    # Must have been given a folder
    givenFolderName = givenPathname
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PickledBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PickledBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            #somethingUpper = something.upper()
            if something in (ZIPPED_PICKLE_FILENAME_END, VERSION_FILENAME):
                foundFiles.append( something )

    # See if there's an PickledBible project here in this given folder
    numFound = len( foundFiles )
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("PickledBibleFileCheck got {} in {}").format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            pB = PickledBible( givenFolderName )
            if autoLoad or autoLoadBooks: pB.preload() # Load the BibleInfo file
            if autoLoadBooks: pB.loadBooks() # Load and process the book files
            return pB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("PickledBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PickledBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                #somethingUpper = something.upper()
                if something in (ZIPPED_PICKLE_FILENAME_END, VERSION_FILENAME):
                    foundSubfiles.append( something )
                    numFound += 1

    # See if there's an Pickle Bible here in this folder
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("PickledBibleFileCheck foundProjects {} {}").format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            pB = PickledBible( foundProjects[0] )
            if autoLoad or autoLoadBooks: pB.preload() # Load the BibleInfo file
            if autoLoadBooks: pB.loadBooks() # Load and process the book files
            return pB
        return numFound
# end of PickledBibleFileCheck



def createPickledBible( BibleObject, outputFolder=None, metadataDict=None, dataLevel=None, zipOnly=False ):
    """
    Saves the Python book objects as pickle files
        then the Bible object (less books)
        and a version info file
        plus a zipped version of everthing for downloading.

    dataLevel:  1 = absolute minimal data saved (default)
                2 = small amount saved
                3 = all saved except BOS object

    Note: This can add up to a couple of GB if discovery data and everything else is included!

    We don't include all fields -- these files are intended to be read-only only,
        i.e., not a full editable version.
    """
    from datetime import datetime

    if BibleOrgSysGlobals.debugFlag: print( "createPickledBible( {}, {}, {}, {} )".format( outputFolder, metadataDict, dataLevel, zipOnly ) )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running createPickledBible" )
    #if not outputFolder: outputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Export/' )
    #if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

    if metadataDict is None: metadataDict = {}
    if dataLevel is None: dataLevel = 1 # Save just enough attributes to display the module

    if BibleOrgSysGlobals.debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
        assert BibleObject.abbreviation
        assert BibleObject.books

    # First pickle the individual books
    createdFilenames = [] # Keep track so we know what to zip (and possibly to delete again later)
    for BBB,bookObject in BibleObject.books.items():
        filename = BOOK_FILENAME.format( BBB )
        createdFilenames.append( filename )
        filepath = os.path.join( outputFolder, filename )
        if debuggingThisModule: print( "Book size", BBB, BibleOrgSysGlobals.totalSize( bookObject ) )
        with open( filepath, 'wb' ) as pickleOutputFile:
            try:
                if 0: # dump whole book
                    pickle.dump( bookObject, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
                else: # be selective about fields
                    for attributeName in dir( bookObject ):
                        #print( "here1: attributeName =", repr(attributeName) )
                        attributeValue = bookObject.__getattribute__( attributeName )
                        #print( "here2", repr(attributeValue) )
                        attributeType = type( attributeValue )
                        #print( "here3: attributeType =", repr(attributeType) )
                        typeAsString = str(attributeType)
                        #print( "here4: typeAsString =", repr(typeAsString) )
                        #print( 'attrib', attributeName, typeAsString )
                        if '__' not in attributeName and 'method' not in typeAsString:
                            if (dataLevel==1 and attributeName in ('sourceFolder','sourceFilename','sourceFilepath',
                                                        '_processedFlag','_processedLines',
                                                        '_indexedFlag','_CVIndex')) \
                            or (dataLevel==2 and attributeName not in ('errorDictionary','containerBibleObject',
                                                        'checkUSFMSequencesFlag')) \
                            or dataLevel not in (1,2):
                                if debuggingThisModule:
                                    print( "  Book attribute size", attributeName, BibleOrgSysGlobals.totalSize( attributeValue ) )
                                #print( "  pickling", typeAsString, attributeName, attributeValue if attributeName!='discoveryResults' else '…' )
                                pickle.dump( attributeName, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
                                pickle.dump( attributeValue, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
                            elif debuggingThisModule:
                                print( "  Skipped book attribute size", attributeName, BibleOrgSysGlobals.totalSize( attributeValue ) )
            except pickle.PicklingError as err:
                logging.error( "BibleOrgSysGlobals: Unexpected error in pickleBook: {0} {1}".format( sys.exc_info()[0], err ) )
                logging.critical( "BibleOrgSysGlobals.pickleObject: Unable to pickle book into {}".format( filename ) )
                return False

    # Now pickle the main Bible object attributes (less the books)
    filepath = os.path.join( outputFolder, INFO_FILENAME )
    createdFilenames.append( INFO_FILENAME )
    if debuggingThisModule: print( "Bible size", BibleOrgSysGlobals.totalSize( BibleObject ) )
    with open( filepath, 'wb' ) as pickleOutputFile:
        try:
            for attributeName in dir( BibleObject ):
                #print( "here1: attributeName =", repr(attributeName) )
                attributeValue = BibleObject.__getattribute__( attributeName )
                #print( "here2", repr(attributeValue) )
                attributeType = type( attributeValue )
                #print( "here3: attributeType =", repr(attributeType) )
                typeAsString = str(attributeType)
                #print( "here4: typeAsString =", repr(typeAsString) )
                #print( 'attrib', attributeName, typeAsString )
                if '__' not in attributeName and 'method' not in typeAsString:
                    if attributeName == 'genericBOS': # Just save the name, not the BOS
                        attributeValue = BibleObject.genericBOS.getOrganisationalSystemName()
                    if (dataLevel==1 and attributeName in ( 'sourceFolder','sourceFilename','sourceFilepath',
                                                'abbreviation','givenName','shortName','name',
                                                'description','version',
                                                'genericBOS')) \
                    or (dataLevel==2 and attributeName not in ('books','discoveryResults',
                                                'triedLoadingBook','bookNeedsReloading','preloadDone',
                                                'errorDictionary','genericBRL',
                                                'USFMFilenamesObject','ssfFilepath')) \
                    or dataLevel not in (1,2):
                        if debuggingThisModule:
                            print( "  Bible attribute size", attributeName, BibleOrgSysGlobals.totalSize( attributeValue ) )
                        #print( "  pickling", typeAsString, attributeName, attributeValue if attributeName!='discoveryResults' else '…' )
                        pickle.dump( attributeName, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
                        pickle.dump( attributeValue, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
                    elif debuggingThisModule:
                        print( "  Skipped Bible attribute size", attributeName, BibleOrgSysGlobals.totalSize( attributeValue ) )
        except pickle.PicklingError as err:
            logging.error( "BibleOrgSysGlobals: Unexpected error in pickleBible: {0} {1}".format( sys.exc_info()[0], err ) )
            logging.critical( "BibleOrgSysGlobals.pickleObject: Unable to pickle Bible into {}".format( filename ) )
            return False

    # Now pickle the version object
    from BibleOrgSys.Internals.InternalBible import programNameVersionDate as IBProgVersion
    from BibleOrgSys.Internals.InternalBibleBook import programNameVersionDate as IBBProgVersion
    from BibleOrgSys.Internals.InternalBibleInternals import programNameVersionDate as IBIProgVersion
    filepath = os.path.join( outputFolder, VERSION_FILENAME )
    createdFilenames.append( VERSION_FILENAME )
    with open( filepath, 'wb' ) as pickleOutputFile:
        for something in ( programNameVersionDate, dataLevel, datetime.now().isoformat(' '),
                            IBProgVersion, IBBProgVersion, IBIProgVersion,
                            BibleObject.getAName(), BibleObject.getBookList(),
                            metadataDict ):
            #print( "String size", something, BibleOrgSysGlobals.totalSize( something ) )
            try:
                #print( "Pickling", repr(something) )
                pickle.dump( something, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
            except pickle.PicklingError as err:
                logging.error( "BibleOrgSysGlobals: Unexpected error in pickleBible: {0} {1}".format( sys.exc_info()[0], err ) )
                logging.critical( "BibleOrgSysGlobals.pickleObject: Unable to pickle Bible into {}".format( filename ) )
                return False

    # Now create a zipped version of the entire folder
    zipFilename = BibleObject.getAName( abbrevFirst=True )
    if BibleOrgSysGlobals.debugFlag: assert zipFilename
    zipFilename = BibleOrgSysGlobals.makeSafeFilename( zipFilename+ZIPPED_PICKLE_FILENAME_END )
    zipFilepath = os.path.join( outputFolder, zipFilename )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} pickle files…".format( len(createdFilenames) ) )
    zf = zipfile.ZipFile( zipFilepath, 'w', compression=zipfile.ZIP_DEFLATED )
    for filename in createdFilenames:
        filepath = os.path.join( outputFolder, filename )
        zf.write( filepath, filename )
        if zipOnly: os.remove( filepath )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  PickledBible.createPickledBible finished successfully." )
    return True
# end of PickledBible.createPickledBible



def _loadObjectAttributes( pickleFileObject, BibleObject ):
    """
    Load the saved attributes for the BibleObject.

    Returns the number of attributes loaded.
    """
    #print( "_loadObjectAttributes( {}, {} )".format( pickleFileObject, BibleObject ) )
    loadedCount = 0
    while True: # Load name/value pairs for Bible attributes
        try: attributeName = pickle.load( pickleFileObject )
        except EOFError: break
        assert isinstance( attributeName, str ) # Leave these asserts enabled for security
        assert '__' not in attributeName # Leave these asserts enabled for security
        attributeValue = pickle.load( pickleFileObject )
        #print( f"Attribute {attributeName}='{attributeValue}' {type(attributeValue)}" )
        assert attributeValue is None \
            or isinstance( attributeValue, (str,bool,Path,InternalBibleCVIndex,InternalBibleSectionIndex,InternalBibleEntryList) ) # Leave these asserts enabled for security
        if attributeName == 'objectNameString': attributeName = 'originalObjectNameString'
        elif attributeName == 'objectTypeString': attributeName = 'originalObjectTypeString'
        #print( "attribute: {} = {}".format( attributeName, attributeValue if attributeName!='discoveryResults' else '…' ) )
        setattr( BibleObject, attributeName, attributeValue )
        loadedCount += 1
    return loadedCount
# end of PickledBible._loadObjectAttributes

def _getObjectAttributesDict( pickleFileObject, selected=None ):
    """
    Load the saved attributes for the BibleObject into a dictionary.

    A list of attribute names to be selected can also be included.

    Returns the dictionary.
    """
    #print( "_getObjectAttributesDict( {}, {} )".format( pickleFileObject, selected ) )
    resultDict = {}
    while True: # Load name/value pairs for Bible attributes
        try: attributeName = pickle.load( pickleFileObject )
        except EOFError: break
        assert isinstance( attributeName, str ) # Leave these asserts enabled for security
        assert '__' not in attributeName # Leave these asserts enabled for security
        attributeValue = pickle.load( pickleFileObject )
        #print( "Attribute {}={}".format( attributeName, attributeValue ) )
        assert attributeValue is None \
            or isinstance( attributeValue, (str,bool,Path,InternalBibleCVIndex,InternalBibleSectionIndex,InternalBibleEntryList) ) # Leave these asserts enabled for security
        if attributeName == 'objectNameString': attributeName = 'originalObjectNameString'
        elif attributeName == 'objectTypeString': attributeName = 'originalObjectTypeString'
        #print( "attribute: {} = {}".format( attributeName, attributeValue if attributeName!='discoveryResults' else '…' ) )
        if not selected or (attributeName in selected):
            if debuggingThisModule: print( "Adding {}={}".format( attributeName, attributeValue ) )
            resultDict[attributeName] = attributeValue
    return resultDict
# end of PickledBible._getObjectAttributesDict



def getZippedPickledBibleDetails( zipFilepath, extended=False ):
    """
    Given the filepath to a zipped pickled Bible module,
        return a dictionary containing some details about the pickled module.

    If extended, also includes the original BibleObject attributes that were saved.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( _("getZippedPickledBibleDetails( {}, {} )").format( zipFilepath, extended ) )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        assert zipFilepath.endswith( ZIPPED_PICKLE_FILENAME_END )

    pB = PickledBible( zipFilepath )
    if extended:
        with zipfile.ZipFile( zipFilepath ) as thisZip:
            with thisZip.open( INFO_FILENAME ) as pickleInputFile:
                if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
                    BibleAttributeDict = _getObjectAttributesDict( pickleInputFile )
                    for attributeName in BibleAttributeDict:
                        assert attributeName not in pB.pickleVersionData # This would get overwritten
                    pB.pickleVersionData.update( BibleAttributeDict )
                else:
                    pB.pickleVersionData.update( _getObjectAttributesDict( pickleInputFile ) )
    #print( "getZippedPickledBibleDetails returning", pB.pickleVersionData ); halt
    return pB.pickleVersionData
# end of getZippedPickledBibleDetails

def getZippedPickledBiblesDetails( zipFolderpath, extended=False ):
    """
    Given the filepath to a zipped pickled Bible module,
        return a dictionary containing some details about the pickled module.

    Guarantees a non-empty 'abbreviation' entry in each dictionary if the extended flag is set.
    """
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( _("getZippedPickledBiblesDetails( {}, {} )").format( zipFolderpath, extended ) )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        assert os.path.isdir( zipFolderpath )

    resultList = []
    for something in sorted( os.listdir( zipFolderpath ) ):
        #print( "getZippedPickledBiblesDetails something", something )
        somepath = os.path.join( zipFolderpath, something )
        if os.path.isfile( somepath ):
            if something.endswith( ZIPPED_PICKLE_FILENAME_END ):
                detailDict = getZippedPickledBibleDetails( somepath, extended )
                assert 'zipFilename' not in detailDict
                detailDict['zipFilename'] = something
                assert 'zipFolderpath' not in detailDict
                detailDict['zipFolderpath'] = zipFolderpath
                #print( something, detailDict )
                if extended:
                    assert 'abbreviation' in detailDict
                    assert detailDict['abbreviation']
                resultList.append( detailDict )
            elif BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
                logging.warning( "Unexpected {} file in {}".format( something, zipFolderpath ) )
        elif BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
            logging.warning( "Unexpected {} folder in {}".format( something, zipFolderpath ) )
    return resultList
# end of getZippedPickledBiblesDetails



class PickledBible( Bible ):
    """
    Class to load and manipulate Pickle Bibles.

    """
    def __init__( self, sourceFileOrFolder ):
        """
        Create the internal Pickle Bible object.

        NOTE: source can be a folder (containing several pickle files)
            or a something.pickle.zip filepath.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Pickled Bible object'
        self.objectTypeString = 'PickledBible'

        # Now we can set our object variables
        self.pickleVersionData = {}

        def loadVersionStuff( pickleFileObject ):
            """
            This function loads all the fields from the version file.

            NOTE: This refers to the pickle/software/object versions, not the Bible text version.
            """
            myDict = {}
            myDict['WriterVersionDate'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['WriterVersionDate'], str ) # Security check
            myDict['DataLevel'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['DataLevel'], int ) # Security check
            myDict['WrittenDateTime'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['WrittenDateTime'], str ) # Security check
            myDict['IBProgVersion'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['IBProgVersion'], str ) # Security check
            myDict['IBBProgVersion'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['IBBProgVersion'], str ) # Security check
            myDict['IBIProgVersion'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['IBIProgVersion'], str ) # Security check
            myDict['workName'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['workName'], str ) # Security check
            myDict['bookList'] = pickle.load( pickleFileObject )
            assert isinstance( myDict['bookList'], list ) # Security check
            myDict.update( pickle.load( pickleFileObject ) ) # metadataDict
            if debuggingThisModule: print( "myDict", myDict )
            return myDict
        # end of PickledBible.__init_ loadVersionStuff

        # Now we load the version info file
        if str(sourceFileOrFolder).endswith( ZIPPED_PICKLE_FILENAME_END ):
            assert os.path.isfile( sourceFileOrFolder )
            self.pickleFilepath = sourceFileOrFolder
            self.pickleSourceFolder = os.path.dirname( sourceFileOrFolder )
            self.pickleIsZipped = True
            try:
                with zipfile.ZipFile( self.pickleFilepath ) as thisZip:
                    with thisZip.open( VERSION_FILENAME ) as pickleInputFile:
                        self.pickleVersionData = loadVersionStuff( pickleInputFile )
            except zipfile.BadZipFile:
                logging.critical( "PickledBible: "+_("Not a valid zipFile at {}").format( self.pickleFilepath ) )
        else: # assume it's a folder
            assert os.path.isdir( sourceFileOrFolder )
            self.pickleSourceFolder = sourceFileOrFolder
            self.pickleIsZipped = False
            filepath = os.path.join( self.pickleSourceFolder, VERSION_FILENAME )
            if os.path.exists( filepath ):
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( _("Loading pickle version info from pickle file {}…").format( filepath ) )
                with open( filepath, 'rb') as pickleInputFile:
                    self.pickleVersionData = loadVersionStuff( pickleInputFile )
            else: logging.critical( "PickledBible: "+_("Unable to find {!r}").format( VERSION_FILENAME ) )

        if debuggingThisModule: print( "pickleVersionData", self.pickleVersionData )
    # end of PickledBible.__init_


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        This one overrides the default one in InternalBible.py
            to handle extra source folders and other specifics of Pickled Bibles.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "PickledBible.__str__()" )

        set1 = ( 'Title', 'Description', 'Version', 'Revision', ) # Ones to print at verbosityLevel > 1
        set2 = ( 'Status', 'Font', 'Copyright', 'Licence', ) # Ones to print at verbosityLevel > 2
        set3 = set1 + set2 + ( 'Name', 'Abbreviation' ) # Ones not to print at verbosityLevel > 3

        result = self.objectNameString
        indent = 2
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.name: result += ('\n' if result else '') + ' '*indent + _("Name: {}").format( self.name )
        if self.abbreviation: result += ('\n' if result else '') + ' '*indent + _("Abbreviation: {}").format( self.abbreviation )
        result += ('\n' if result else '') + ' '*indent + _("Packaged: {}").format( self.pickleVersionData['WrittenDateTime'].split( ' ', 1)[0] )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            for something,sometext in self.pickleVersionData.items():
                result += ('\n' if result else '') + ' '*indent + _("{}: {}").format( something, sometext )
        else:
            if 'aboutText' in self.pickleVersionData and self.pickleVersionData['aboutText']:
                result += ('\n' if result else '') + ' '*indent + _("About: {}").format( self.pickleVersionData['aboutText'] )
            if 'sourceURL' in self.pickleVersionData and self.pickleVersionData['sourceURL']:
                result += ('\n' if result else '') + ' '*indent + _("Source URL: {}").format( self.pickleVersionData['sourceURL'] )
            if 'licenceText' in self.pickleVersionData and self.pickleVersionData['licenceText']:
                result += ('\n' if result else '') + ' '*indent + _("Licence: {}").format( self.pickleVersionData['licenceText'] )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            for fieldName in set1:
                fieldContents = self.getSetting( fieldName )
                if fieldContents:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, fieldContents )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            if self.sourceFolder: result += ('\n' if result else '') + ' '*indent + _("Original source folder: {}").format( self.sourceFolder )
            elif self.sourceFilepath: result += ('\n' if result else '') + ' '*indent + _("Original source: {}").format( self.sourceFilepath )
            for fieldName in ( 'Status', 'Font', 'Copyright', 'Licence', ):
                fieldContents = self.getSetting( fieldName )
                if fieldContents:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, fieldContents )
        if (BibleOrgSysGlobals.debugFlag or debuggingThisModule) and BibleOrgSysGlobals.verbosityLevel > 3 \
        and self.suppliedMetadata and self.objectTypeString not in ('PTX7','PTX8'): # There's too much potential Paratext metadata
            for metadataType in self.suppliedMetadata:
                for fieldName in self.suppliedMetadata[metadataType]:
                    if fieldName not in set3:
                        fieldContents = self.suppliedMetadata[metadataType][fieldName]
                        if fieldContents:
                            result += ('\n' if result else '') + '  '*indent + _("{}: {!r}").format( fieldName, fieldContents )
        #if self.revision: result += ('\n' if result else '') + ' '*indent + _("Revision: {}").format( self.revision )
        #if self.version: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.version )
        result += ('\n' if result else '') + ' '*indent + _("Number of{} books: {}{}") \
                                        .format( '' if self.loadedAllBooks else ' loaded', len(self.books), ' {}'.format( self.getBookList() ) if 0<len(self.books)<5 else '' )
        return result
    # end of PickledBible.__str__


    def preload( self ):
        """
        Loads the BibleInfo file if it can be found.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("preload() from {}").format( self.pickleSourceFolder ) )
            assert not self.preloadDone
            assert self.pickleIsZipped or self.pickleSourceFolder is not None
            #print( "preload1", len(dir(self)), dir(self) )

        if self.pickleIsZipped:
            with zipfile.ZipFile( self.pickleFilepath ) as thisZip:
                with thisZip.open( INFO_FILENAME ) as pickleInputFile:
                    loadedCount = _loadObjectAttributes( pickleInputFile, self )
        else: # it's not zipped
            filepath = os.path.join( self.pickleSourceFolder, INFO_FILENAME )
            if os.path.exists( filepath ):
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( _("Loading PickledBible info from pickle file {}…").format( filepath ) )
                with open( filepath, 'rb') as pickleInputFile:
                    loadedCount = _loadObjectAttributes( pickleInputFile, self )
            else: logging.critical( _("PickledBible: unable to find {!r}").format( INFO_FILENAME ) )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("  Loaded {} PickledBible attributes").format( loadedCount ) )

        for BBB in self.pickleVersionData['bookList']:
            if BBB in self.triedLoadingBook:
                del self.triedLoadingBook[BBB] # So we can load them (again) from the pickle files

        #print( "preload2", len(dir(self)), dir(self) )
        #print( self )
        self.preloadDone = True
    # end of PickledBible.preload


    def _loadBookEssentials( self, BBB ):
        """
        Load the requested book and return the new bookObject.

        This function is multiprocessing safe.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "PickledBible._loadBookEssentials( {} )".format( BBB ) )

        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( _("  PickledBible: Loading {} from {} from {}…").format( BBB, self.name, self.pickleSourceFolder ) )
        #if 0: # whole book object
            #if self.pickleIsZipped:
                #with zipfile.ZipFile( self.pickleFilepath ) as thisZip:
                    #with thisZip.open( BOOK_FILENAME.format( BBB ) ) as pickleInputFile:
                        #bookObject = pickle.load( pickleInputFile )
            #else: # not zipped
                #bookObject = BibleOrgSysGlobals.unpickleObject( BOOK_FILENAME.format( BBB ), self.pickleSourceFolder )
        #else: # with attribute names and values
        bookObject = InternalBibleBook( 'NoneYet', BBB )
        bookObject.objectNameString = 'Pickled Bible book object'
        bookObject.objectTypeString = 'PickledBibleBook'
        if self.pickleIsZipped:
            with zipfile.ZipFile( self.pickleFilepath ) as thisZip:
                with thisZip.open( BOOK_FILENAME.format( BBB ) ) as pickleInputFile:
                    loadedCount = _loadObjectAttributes( pickleInputFile, bookObject )
        else: # not zipped
            with open( os.path.join( self.pickleSourceFolder, BOOK_FILENAME.format( BBB ) ), 'rb' ) as pickleInputFile:
                loadedCount = _loadObjectAttributes( pickleInputFile, bookObject )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("  Loaded {} {} PickledBible book attributes").format( loadedCount, BBB ) )

        self.bookNeedsReloading[BBB] = False
        return bookObject
    # end of PickledBible._loadBookEssentials


    def loadBook( self, BBB ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "PickledBible.loadBook( {} )".format( BBB ) )
            assert self.preloadDone

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading Pickle {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book

        self.books[BBB] = self._loadBookEssentials( BBB )
    # end of PickledBible.loadBook


    def _loadBookMP( self, BBB ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Returns the book info.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("loadBookMP( {} )").format( BBB ) )

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return self.books[BBB] # Already loaded
        #if BBB in self.triedLoadingBook:
            #logging.warning( "We had already tried loading Pickle {} for {}".format( BBB, self.name ) )
            #return # We've already attempted to load this book

        return self._loadBookEssentials( BBB )
    # end of PickledBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the Bible books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading {} from {}…").format( self.getAName(), self.pickleSourceFolder ) )

        if not self.preloadDone: self.preload()

        if len( self.pickleVersionData['bookList'] ) > 2:
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.pickleVersionData['bookList']] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( _("Loading {} {} books using {} processes…").format( len(self.pickleVersionData['bookList']), 'Pickle', BibleOrgSysGlobals.maxProcesses ) )
                    print( _("  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed.") )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.pickleVersionData['bookList'] ) # have the pool do our loads
                    assert len(results) == len(self.pickleVersionData['bookList'])
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB in self.pickleVersionData['bookList']:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  PickledBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    self.loadBook( BBB ) # also saves it
        else:
            logging.critical( "PickledBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of PickledBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class PickledBible



def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                    BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Export/' ),
                    BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Reexport/' ),
                    'MadeUpFakeFolder/',
                    )
    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for j,testFolder in enumerate( testFolders, start=1 ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( f"\nPickle Bible A{j} testfolder is: {testFolder}" )
            result1 = PickledBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestAa", result1 )
            result2 = PickledBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestAb", result2 )
            result3 = PickledBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestAc", result3 )
            if isinstance( result3, Bible ):
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #print( result3.books['GEN']._processedLines[0:40] )
                    pBibleErrors = result3.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    result3.pickle()
                    ##result3.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    resourcesFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH
    if 1: # demo the file checking code with zip files
        for j,testAbbreviation in enumerate( ('ASV', 'RV', 'WEB' ) ):
            testFilepath = os.path.join( resourcesFolder, testAbbreviation+ZIPPED_PICKLE_FILENAME_END )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nPickle Bible B{} testFilepath is: {}".format( j+1, testFilepath ) )
            result1 = PickledBibleFileCheck( testFilepath )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestBa", result1 )
            result2 = PickledBibleFileCheck( testFilepath, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestBb", result2 )
            result3 = PickledBibleFileCheck( testFilepath, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Pickle Bible TestBc", result3 )
            if isinstance( result3, Bible ):
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #print( result3.books['GEN']._processedLines[0:40] )
                    pBibleErrors = result3.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    result3.pickle()
                    ##result3.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

    if 1: # Load and process some of our test versions
        for j,(name, encoding, testFolder) in enumerate( (
                        ("Test1", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest1/') ),
                        ("Test2", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest2/') ),
                        ("Test3", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest3/') ),
                        ("Exported1", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Export/') ),
                        ("Exported2", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Reexport/') ),
                        ) ):
            if os.access( testFolder, os.R_OK ):
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nPickle Bible C{}/".format( j+1 ) )
                pBible = PickledBible( testFolder )
                pBible.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Gen assumed book name:", repr( pBible.getAssumedBookName( 'GEN' ) ) )
                    print( "Gen long TOC book name:", repr( pBible.getLongTOCName( 'GEN' ) ) )
                    print( "Gen short TOC book name:", repr( pBible.getShortTOCName( 'GEN' ) ) )
                    print( "Gen book abbreviation:", repr( pBible.getBooknameAbbreviation( 'GEN' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( pBible )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    pBible.check()
                    #print( pBible.books['GEN']._processedLines[0:40] )
                    pBibleErrors = pBible.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    pBible.pickle()
                    ##pBible.toDrupalBible()
                    pBible.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "OutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "newObj is", newObj )
                if 1:
                    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
                    from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntry
                    for BBB,C,V in ( ('MAT','1','1'),('MAT','1','2'),('MAT','1','3'),('MAT','1','4'),('MAT','1','5'),('MAT','1','6'),('MAT','1','7'),('MAT','1','8') ):
                        svk = SimpleVerseKey( BBB, C, V )
                        shortText = svk.getShortText()
                        verseDataList = pBible.getVerseDataList( svk )
                        if BibleOrgSysGlobals.verbosityLevel > 0:
                            print( "\n{}\n{}".format( shortText, verseDataList ) )
                        if verseDataList is None: continue
                        for verseDataEntry in verseDataList:
                            # This loop is used for several types of data
                            assert isinstance( verseDataEntry, InternalBibleEntry )
                            marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                            adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                            fullText = verseDataEntry.getFullText()
                            if BibleOrgSysGlobals.verbosityLevel > 0:
                                print( "marker={} cleanText={!r}{}".format( marker, cleanText,
                                                        " extras={}".format( extras ) if extras else '' ) )
                                if adjustedText and adjustedText!=cleanText:
                                    print( ' '*(len(marker)+4), "adjustedText={!r}".format( adjustedText ) )
                                if fullText and fullText!=cleanText:
                                    print( ' '*(len(marker)+4), "fullText={!r}".format( fullText ) )
                                if originalText and originalText!=cleanText:
                                    print( ' '*(len(marker)+4), "originalText={!r}".format( originalText ) )
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                print( '\n' + _("Sorry, test folder {!r} is not readable on this computer.").format( testFolder ) )


    if 1: # Load a zipped version
        pFilepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Export/MBTV'+ZIPPED_PICKLE_FILENAME_END )
        if os.access( pFilepath, os.R_OK ):
            pBible = PickledBible( pFilepath )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "D1:", pBible )
            pBible.load()
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "D2:", pBible )
            assert pBible.pickleIsZipped # That's what we were supposedly testing
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( '\n' + _("Sorry, test file {!r} is not readable on this computer.").format( pFilepath ) )


    if 1: # demo the file checking code with zip files
        testResourcesFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Test_DistributableResources/' )
        j = 1
        for testFolder in ( resourcesFolder, testResourcesFolder ):
            if os.path.exists( testFolder ):
                for something in sorted( os.listdir( testFolder ) ):
                    somepath = os.path.join( testFolder, something )
                    if not something.endswith( ZIPPED_PICKLE_FILENAME_END ):
                        # Could be a DBL.zip file or something
                        logger = logging.warning if something.endswith(DBL_FILENAME_END) else logging.error
                        logger( "PickledBible: "+_("Skipping non-BOS-pickle file: {}").format( somepath ) )
                        continue
                    abbrev = something.split('.',1)[0]
                    pBible = PickledBible( somepath )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nE{}a: {}".format( j, abbrev ), pBible )
                    pBible.load()
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "E{}b: {}".format( j, abbrev ), pBible )
                    assert pBible.pickleIsZipped # That's what we were supposedly testing
                    j += 1
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                print( '\n' + _("Sorry, test folder {!r} is not readable on this computer.").format( testFolder ) )


    if 1: # demo the file checking code with zip files
        testResourcesFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Test_PrivateResources/' )
        j = 1
        for testFolder in ( resourcesFolder, testResourcesFolder ):
            if os.path.exists( testFolder ):
                for something in sorted( os.listdir( testFolder ) ):
                    somepath = os.path.join( testFolder, something )
                    if not something.endswith( ZIPPED_PICKLE_FILENAME_END ):
                        # Could be a DBL.zip file or something
                        logger = logging.warning if something.endswith(DBL_FILENAME_END) else logging.error
                        logger( "PickledBible: "+_("Skipping non-BOS-pickle file: {}").format( somepath ) )
                        continue
                    abbrev = something.split('.',1)[0]
                    pBible = PickledBible( somepath )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nF{}a: {}".format( j, abbrev ), pBible )
                    pBible.load()
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "F{}b: {}".format( j, abbrev ), pBible )
                    assert pBible.pickleIsZipped # That's what we were supposedly testing
                    j += 1
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                print( '\n' + _("Sorry, test folder {!r} is not readable on this computer.").format( testFolder ) )


    if 1: # Test other functions
        for j,testAbbreviation in enumerate( ('ASV', 'RV', 'WEB' ) ):
            testFilepath = os.path.join( resourcesFolder, testAbbreviation+ZIPPED_PICKLE_FILENAME_END )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nPickle Bible G{} testFilepath is: {}".format( j+1, testFilepath ) )
            if os.path.isfile( testFilepath ):
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "  getZippedPickledBibleDetails()", getZippedPickledBibleDetails( testFilepath ) )
            else:
                logging.error( f"testFilepath '{testFilepath}' is not available on this computer!" )
                continue
        pbdDictList = getZippedPickledBiblesDetails( resourcesFolder )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "\nH1: getZippedPickledBiblesDetails()", len(pbdDictList), pbdDictList )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nH2: getZippedPickledBiblesDetails()", len(pbdDictList) )
        if pbdDictList and BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nH3: getZippedPickledBiblesDetails()", len(pbdDictList[0]), pbdDictList[0] )
        pbdExtendedDictList = getZippedPickledBiblesDetails( resourcesFolder, extended=True )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "\nI1: getZippedPickledBiblesDetails( extended )", len(pbdExtendedDictList), pbdExtendedDictList )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nI2: getZippedPickledBiblesDetails( extended )", len(pbdExtendedDictList) )
        if pbdExtendedDictList and BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nI3: getZippedPickledBiblesDetails( extended )", len(pbdExtendedDictList[0]), pbdExtendedDictList[0] )
            #for a,v in pbdExtendedDictList[0].items(): print( "  {}={}".format( a, v ) )
#end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of PickledBible.py
