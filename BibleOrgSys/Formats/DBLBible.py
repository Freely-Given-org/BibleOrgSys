#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DBLBible.py
#
# Module handling Digital Bible Library (DBL) compilations of USX XML Bible books
#                                               along with XML and other metadata
#
# Copyright (C) 2013-2020 Robert Hunt
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
Module for defining and manipulating complete or partial DBL Bible bundles
    saved in folders on the local filesystem.
    (See a separate module for online access of the DBL.)

See http://digitalbiblelibrary.org and http://digitalbiblelibrary.org/info/inside
as well as http://www.everytribeeverynation.org/library.

There seems to be some incomplete documentation at http://digitalbiblelibrary.org/static/docs/index.html
    and specifically the text bundle at http://digitalbiblelibrary.org/static/docs/entryref/text/index.html.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-12' # by RJH
SHORT_PROGRAM_NAME = "DigitalBibleLibrary"
PROGRAM_NAME = "Digital Bible Library (DBL) XML Bible handler"
PROGRAM_VERSION = '0.29'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


import os
import logging
import multiprocessing
from pathlib import Path
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USXXMLBibleBook import USXXMLBibleBook
from BibleOrgSys.Formats.PTX7Bible import loadPTX7Languages, loadPTXVersifications
from BibleOrgSys.Formats.PTX8Bible import getFlagFromAttribute



COMPULSORY_FILENAMES = ( 'METADATA.XML', 'LICENSE.XML', 'STYLES.XML' ) # Must all be UPPER-CASE



def DBLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for DBL Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one DBL Bible bundle is found,
        returns the loaded DBLBible object.
    """
    vPrint( 'Info', debuggingThisModule, "DBLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("DBLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("DBLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', debuggingThisModule, " DBLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
        if filename.upper() in COMPULSORY_FILENAMES: numFilesFound += 1
    for folderName in foundFolders:
        if folderName.upper().startswith('USX_'): numFoldersFound += 1
    if numFilesFound==len(COMPULSORY_FILENAMES) and numFoldersFound>0: numFound += 1

    ## See if there's an USXBible project here in this given folder
    #numFound = 0
    #UFns = USXFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    #vPrint( 'Info', debuggingThisModule, UFns )
    #filenameTuples = UFns.getConfirmedFilenames()
    #vPrint( 'Verbose', debuggingThisModule, "Confirmed:", len(filenameTuples), filenameTuples )
    #if BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: vPrint( 'Quiet', debuggingThisModule, "Found {} USX files.".format( len(filenameTuples) ) )
    #if filenameTuples:
        #numFound += 1

    if numFound:
        vPrint( 'Info', debuggingThisModule, "DBLBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = DBLBible( givenFolderName )
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
            logging.warning( _("DBLBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        vPrint( 'Verbose', debuggingThisModule, "    DBLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if the compulsory files and folder are here in this given folder
        numFilesFound = numFoldersFound = 0
        for filename in foundSubfiles:
            if filename.upper() in COMPULSORY_FILENAMES: numFilesFound += 1
        for folderName in foundSubfolders:
            if folderName.upper().startswith('USX_'): numFoldersFound += 1
        if numFilesFound==len(COMPULSORY_FILENAMES) and numFoldersFound>0:
            foundProjects.append( tryFolderName )
            numFound += 1

        ## See if there's an USX Bible here in this folder
        #UFns = USXFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        #vPrint( 'Info', debuggingThisModule, UFns )
        #filenameTuples = UFns.getConfirmedFilenames()
        #vPrint( 'Verbose', debuggingThisModule, "Confirmed:", len(filenameTuples), filenameTuples )
        #if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: vPrint( 'Quiet', debuggingThisModule, "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        #elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: vPrint( 'Quiet', debuggingThisModule, "  Found {} USX files".format( len(filenameTuples) ) )
        #if filenameTuples:
            #foundProjects.append( tryFolderName )
            #numFound += 1

    if numFound:
        vPrint( 'Info', debuggingThisModule, "DBLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = DBLBible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            return dB
        return numFound
# end of DBLBibleFileCheck



#def clean( elementText, loadErrors=None, location=None ):
    #"""
    #Given some text from an XML element text or tail field (which might be None)
        #return a stripped value and with internal CRLF characters replaced by spaces.

    #If the text is None, returns None
    #"""
    #if elementText is None: return None
    ## else it's not None

    #info = ''
    #if location: info += ' at ' + location

    #result = elementText
    #while result.endswith('\n') or result.endswith('\r'): result = result[:-1] # Drop off trailing newlines (assumed to be irrelevant)
    #if '  ' in result:
        #errorMsg = "clean: found multiple spaces in {!r}{}".format( result, info )
        #logging.warning( errorMsg )
        #if loadErrors is not None: loadErrors.append( errorMsg )
    #if '\t' in result:
        #errorMsg = "clean: found tab in {!r}{}".format( result, info )
        #logging.warning( errorMsg )
        #if loadErrors is not None: loadErrors.append( errorMsg )
        #result = result.replace( '\t', ' ' )
    #if '\n' in result or '\r' in result:
        #errorMsg = "clean: found CR or LF characters in {!r}{}".format( result, info )
        #logging.error( errorMsg )
        #if loadErrors is not None: loadErrors.append( errorMsg )
        #result = result.replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
    #while '  ' in result: result = result.replace( '  ', ' ' )
    #return result
## end of clean



class DBLBible( Bible ):
    """
    Class to load and manipulate DBL Bible bundles.
    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal DBL Bible object.
        """
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            #vPrint( 'Quiet', debuggingThisModule, "__init__( {}, {}, {} )".format( givenFolderName, givenName, encoding ) )
            assert isinstance( givenFolderName, str )
            assert isinstance( givenName, str )
            assert isinstance( encoding, str )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'DBL XML Bible object'
        self.objectTypeString = 'DBL'

        self.sourceFolder, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.sourceFilepath = self.sourceFolder
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        #if givenName:
            #if not os.access( self.sourceFolder, os.R_OK ):
                #logging.error( "DBLBible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            #self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        #else: self.sourceFilepath = self.sourceFolder
        if not os.access( self.sourceFolder, os.R_OK ):
            logging.error( "DBLBible: Folder '{}' is unreadable".format( self.sourceFolder ) )

        # Create empty containers for loading the XML metadata files
        #DBLLicense = DBLStyles = DBLVersification = DBLLanguage = None
    # end of DBLBible.__init__


    def preload( self ):
        """
        Load the XML metadata files.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "preload() from {}".format( self.sourceFolder ) )
        vPrint( 'Normal', debuggingThisModule, _("DBLBible: Loading {} from {}…").format( self.name, self.sourceFilepath ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: vPrint( 'Quiet', debuggingThisModule, "ERROR: Not sure what '{}' is in {}!".format( somepath, self.sourceFilepath ) )
        if not foundFiles:
            vPrint( 'Quiet', debuggingThisModule, "DBLBible.preload: Couldn't find any files in '{}'".format( self.sourceFilepath ) )
            return # No use continuing

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['DBL'] = {}

        self.loadDBLLicense()
        self.loadDBLMetadata() # into self.suppliedMetadata['DBL'] (still in DBL format)
        self.applySuppliedMetadata( 'DBL' ) # copy into self.settingsDict (standardised)
        self.loadDBLStyles()
        result = loadPTXVersifications( self )
        if result: self.suppliedMetadata['DBL']['Versifications'] = result
        result = loadPTX7Languages( self )
        if result: self.suppliedMetadata['DBL']['Languages'] = result
        #vPrint( 'Quiet', debuggingThisModule, 'DBLLicense', len(DBLLicense), DBLLicense )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLMetadata', len(self.suppliedMetadata), self.suppliedMetadata )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLStyles', len(DBLStyles), DBLStyles )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLVersification', len(DBLVersification), DBLVersification )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLLanguage', len(DBLLanguage), DBLLanguage )

        self.preloadDone = True
    # end of DBLBible.preload


    def loadDBLLicense( self ):
        """
        Load the metadata.xml file and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "loadDBLLicense()" )

        licenseFilepath = os.path.join( self.sourceFilepath, 'license.xml' )
        vPrint( 'Info', debuggingThisModule, "DBLBible.loading license data from {}…".format( licenseFilepath ) )
        self.XMLTree = ElementTree().parse( licenseFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        DBLLicense = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='license':
            location = "DBL {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location )

            # Process the metadata attributes first
            licenseID = None
            for attrib,value in self.XMLTree.items():
                if attrib=='id': licenseID = value
                else:
                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            DBLLicense['Id'] = licenseID # This is a long hex number (16 chars)

            # Now process the actual metadata
            for element in self.XMLTree:
                sublocation = element.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, "\nProcessing {}…".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                if element.tag in ( 'dateLicense', 'dateLicenseExpiry' ):
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    DBLLicense[element.tag] = element.text
                elif element.tag == 'publicationRights':
                    assert element.tag not in DBLLicense
                    DBLLicense[element.tag] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        #vPrint( 'Quiet', debuggingThisModule, "  Processing {}…".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('allowOffline', 'allowIntroductions', 'allowFootnotes', 'allowCrossReferences', 'allowExtendedNotes' ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in DBLLicense[element.tag]
                            DBLLicense[element.tag][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        vPrint( 'Info', debuggingThisModule, "  Loaded {} license elements.".format( len(DBLLicense) ) )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLLicense', DBLLicense )
        if DBLLicense: self.suppliedMetadata['DBL']['License'] = DBLLicense
    # end of DBLBible.loadDBLLicense


    def loadDBLMetadata( self ):
        """
        Load the metadata.xml file and parse it into the ordered dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "loadDBLMetadata()" )

        mdFilepath = os.path.join( self.sourceFilepath, 'metadata.xml' )
        vPrint( 'Info', debuggingThisModule, "DBLBible.loading supplied DBL metadata from {}…".format( mdFilepath ) )
        self.XMLTree = ElementTree().parse( mdFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        def getContents( element, location ):
            """
            Load the contents information (which is more nested/complex).
            """
            assert element.tag == 'contents'
            if element.tag not in self.suppliedMetadata['DBL']:
                self.suppliedMetadata['DBL'][element.tag] = {}
            ourDict = self.suppliedMetadata['DBL']['contents']
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location )
            BibleOrgSysGlobals.checkXMLNoText( element, location )
            BibleOrgSysGlobals.checkXMLNoTail( element, location )
            for subelement in element:
                sublocation = subelement.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, "  Processing {}…".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                assert subelement.tag == 'bookList'
                bookListID = bookListIsDefault = None
                for attrib,value in subelement.items():
                    if attrib=='id': bookListID = value
                    elif attrib=='default': bookListIsDefault = value
                    else:
                        logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #vPrint( 'Quiet', debuggingThisModule, "bookListID={!r} bookListIsDefault={}".format( bookListID, bookListIsDefault ) )
                bookListTag = '{}-{}{}'.format( subelement.tag, bookListID, ' (default)' if bookListIsDefault=='true' else '' )
                assert bookListTag not in ourDict
                ourDict[bookListTag] = {}
                ourDict[bookListTag]['divisions'] = {}
                for sub2element in subelement:
                    sub2location = sub2element.tag + ' ' + sublocation
                    #vPrint( 'Quiet', debuggingThisModule, "    Processing {}…".format( sub2location ) )
                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                    if sub2element.tag in ('name','nameLocal','abbreviation','abbreviationLocal','description','descriptionLocal','range','tradition'):
                        if BibleOrgSysGlobals.debugFlag: assert sub2element.text
                        ourDict[bookListTag][sub2element.tag] = sub2element.text
                    elif sub2element.tag == 'division':
                        items = sub2element.items()
                        assert len(items)==1 and items[0][0]=='id'
                        divisionID = items[0][1]
                        #divisionTag = sub2element.tag + '-' + divisionID
                        ourDict[bookListTag]['divisions'][divisionID] = []
                    elif sub2element.tag == 'books':
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                        ourDict[bookListTag]['books'] = []
                        for sub3element in sub2element:
                            sub3location = sub3element.tag + ' ' + sub2location
                            #vPrint( 'Quiet', debuggingThisModule, "        Processing {}…".format( sub3location ) )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                            assert sub3element.tag == 'book'
                            items = sub3element.items()
                            assert len(items)==1 and items[0][0]=='code'
                            bookCode = items[0][1]
                            ourDict[bookListTag]['books'].append( bookCode )
                    else:
                        logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #if 0:
                        #items = sub2element.items()
                        #for sub3element in sub2element:
                            #sub3location = sub3element.tag + ' ' + sub2location
                            #vPrint( 'Quiet', debuggingThisModule, "      Processing {}…".format( sub3location ) )
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                            #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                            #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                            #assert sub3element.tag == 'books' # Don't bother saving this extra level
                            #for sub4element in sub3element:
                                #sub4location = sub4element.tag + ' ' + sub3location
                                #vPrint( 'Quiet', debuggingThisModule, "        Processing {}…".format( sub4location ) )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location )
                                #BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                #assert sub4element.tag == 'book'
                                #items = sub4element.items()
                                #assert len(items)==1 and items[0][0]=='code'
                                #bookCode = items[0][1]
                                #ourDict[bookListTag]['divisions'][divisionID].append( bookCode )
            #vPrint( 'Quiet', debuggingThisModule, "Contents:", self.suppliedMetadata['DBL']['contents'] )
        # end of getContents

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['DBL'] = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='DBLMetadata':
            location = "DBL Metadata ({}) file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location )

            # Process the metadata attributes first
            mdType = mdTypeVersion = mdVersion = mdID = mdRevision = None
            for attrib,value in self.XMLTree.items():
                if attrib=='type': mdType = value
                elif attrib=='typeVersion': mdTypeVersion = value
                elif attrib=='version': mdVersion = value
                elif attrib=='id': mdID = value
                elif attrib=='revision': mdRevision = value
                else:
                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', debuggingThisModule, "mdType={!r} mdTypeVersion={!r} mdVersion={!r} mdID={!r} mdRevision={!r}".format( mdType, mdTypeVersion, mdVersion, mdID, mdRevision ) )
                assert mdType is None or mdType == 'text'
                assert mdTypeVersion is None or mdTypeVersion in ( '1.2','1.3','1.5', )
                assert mdVersion is None or mdVersion in ( '2.0','2.1', ) # This is all we know about
                assert mdRevision in ( '1','2','3','4','5','6','7','8', )
            self.DBLMetadataVersion = mdVersion

            # Now process the actual metadata
            for element in self.XMLTree:
                #vPrint( 'Quiet', debuggingThisModule, "\nMetadata Top", self.suppliedMetadata['DBL'].keys() )
                sublocation = element.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, "\nProcessing {}…".format( sublocation ) )
                #self.suppliedMetadata['DBL'][element.tag] = {}
                if element.tag == 'identification':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert 'identification' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['identification'] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        #vPrint( 'Quiet', debuggingThisModule, "  Processing {}…".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('name','nameLocal','abbreviation','abbreviationLocal','scope','description','descriptionLocal','dateCompleted','systemId','bundleProducer'):
                            thisTag = subelement.tag
                            if subelement.tag == 'systemId': # Can have multiples of these
                                systemId = {}
                                #systemIdType = systemId = csetid = fullname = name = None
                                for attrib,value in subelement.items():
                                    if attrib=='type': systemId['Type'] = value
                                    #elif attrib=='id': systemId[ = value
                                    elif attrib=='csetid': systemId['csetid'] = value
                                    elif attrib=='fullname': systemId['Fullname'] = value
                                    elif attrib=='name': systemId['Name'] = value
                                    else:
                                        logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                for sub2element in subelement:
                                    sub3location = sub2element.tag + ' ' + sub2location
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                    systemId[sub2element.tag] = sub2element.text
                                #vPrint( 'Quiet', debuggingThisModule, "systemId", systemId )
                                pass # Xxxxxxxxxxxxx not stored
                                #thisTag = thisTag + '-' + items[0][1]
                            else: BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            #assert subelement.text # Seems we can have a blank descriptionLocal
                            self.suppliedMetadata['DBL']['identification'][thisTag] = subelement.text
                        else:
                            logging.warning( _("KW42 Unprocessed {} subelement {!r} in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'confidential':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    self.suppliedMetadata['DBL']['confidential'] = element.text
                elif element.tag == 'agencies':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    agencies = {}
                    rightsHolders = {}
                    contributors = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        url = None
                        for attrib,value in subelement.items():
                            if attrib=='url': url = value
                            else:
                                logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        pass # url isn't saved XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx
                        if subelement.tag == 'rightsHolder':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            rightsHolder = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                #vPrint( 'Quiet', debuggingThisModule, "sub3location", sub3location )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                rightsHolder[sub2element.tag] = sub2element.text
                            #vPrint( 'Quiet', debuggingThisModule, "rightsHolder", rightsHolder )
                            if 'uid' in rightsHolder:
                                assert rightsHolder['uid'] not in rightsHolders
                                rightsHolders[rightsHolder['uid']] = rightsHolder
                            else:
                                assert not rightsHolder # empty XML field
                        elif subelement.tag == 'rightsAdmin':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            rightsAdmin = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                rightsHolder[sub2element.tag] = sub2element.text
                            #vPrint( 'Quiet', debuggingThisModule, "rightsAdmin", rightsAdmin )
                            assert 'rightsAdmin' not in agencies
                            agencies['rightsAdmin'] = rightsAdmin
                        elif subelement.tag == 'contributor' and BibleOrgSysGlobals.isBlank( subelement.text ):
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            contributor = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                contributor[sub2element.tag] = sub2element.text
                            #vPrint( 'Quiet', debuggingThisModule, "contributor", contributor )
                            if 'uid' in contributor:
                                assert contributor['uid'] not in contributors
                                contributors[contributor['uid']] = contributor
                            else:
                                assert not contributor # empty XML field
                        elif subelement.tag in ('etenPartner','creator','publisher','contributor'):
                            #vPrint( 'Quiet', debuggingThisModule, "AgenciesStuff", sub2location, repr(subelement.text) )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            if subelement.tag in agencies: agencies[subelement.tag].append( subelement.text )
                            else: agencies[subelement.tag] = [ subelement.text ]
                        else:
                            logging.warning( _("KJ76 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if rightsHolders: agencies['RightsHolders'] = rightsHolders
                    if contributors: agencies['Contributors'] = contributors
                    #vPrint( 'Quiet', debuggingThisModule, "agencies", agencies )
                    assert 'agencies' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['agencies']  = agencies
                elif element.tag == 'language':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert 'language' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['language'] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('iso','name','nameLocal','ldml','rod','script','scriptCode','scriptDirection','numerals'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL']['language'][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("NH34 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'country':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if element.tag not in self.suppliedMetadata['DBL']:
                            self.suppliedMetadata['DBL'][element.tag] = {}
                        if subelement.tag in ('iso','name'):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("QT45 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'countries':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    countries = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag == 'country':
                            #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            #BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            country = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                country[sub2element.tag] = sub2element.text
                            #vPrint( 'Quiet', debuggingThisModule, "country", country )
                            countries[country['iso']] = country
                        else:
                            logging.warning( _("KJ79 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "countries", countries )
                    assert 'countries' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['countries']  = countries
                elif element.tag == 'type':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert 'type' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['type'] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('translationType','audience','medium','isConfidential','hasCharacters','isTranslation','isExpression',):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("TR45 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'relationships':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                elif element.tag == 'bookNames':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        assert subelement.tag == 'book'
                        items = subelement.items()
                        assert len(items)==1 and items[0][0]=='code'
                        bookCode = items[0][1]
                        assert len(bookCode) == 3
                        if element.tag not in self.suppliedMetadata['DBL']:
                            self.suppliedMetadata['DBL'][element.tag] = {}
                        self.suppliedMetadata['DBL'][element.tag][bookCode] = {}
                        for sub2element in subelement:
                            sub3location = sub2element.tag + ' ' + bookCode + ' ' + sub2location
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                            if sub2element.tag in ('long','short','abbr'):
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                                    if sub2element.tag != 'abbr':
                                        assert sub2element.text # Seems abbreviations can be missing
                                self.suppliedMetadata['DBL'][element.tag][bookCode][sub2element.tag] = sub2element.text
                            else:
                                logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'contents':
                    getContents( element, sublocation )
                elif element.tag == 'progress':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    self.suppliedMetadata['DBL'][element.tag] = {} # Don't need this ordered
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        assert subelement.tag == 'book'
                        bookCode = stage = None
                        for attrib,value in subelement.items():
                            if attrib=='code': bookCode = value
                            elif attrib=='stage': stage = value
                            else:
                                logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        #vPrint( 'Quiet', debuggingThisModule, bookCode, stage )
                        assert len(bookCode) == 3
                        if 'bookNames' in self.suppliedMetadata['DBL']:
                            if bookCode not in self.suppliedMetadata['DBL']['bookNames']:
                                logging.warning( _("Bookcode {} mentioned in progress but not found in bookNames").format( bookCode ) )
                                if BibleOrgSysGlobals.strictCheckingFlag and BibleOrgSysGlobals.debugFlag: halt
                        elif 'names' in self.suppliedMetadata['DBL']:
                            if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "Why don't we have a bookNames entry???" )
                            if bookCode not in self.suppliedMetadata['DBL']['names']:
                                logging.warning( _("Bookcode {} mentioned in progress but not found in names").format( bookCode ) )
                                if BibleOrgSysGlobals.strictCheckingFlag and BibleOrgSysGlobals.debugFlag: halt
                        assert stage in ('1','2','3','4')
                        self.suppliedMetadata['DBL'][element.tag][bookCode] = stage
                elif element.tag == 'contact':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    self.suppliedMetadata['DBL'][element.tag] = {} # Don't need this ordered
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('rightsHolder','rightsHolderLocal','rightsHolderAbbreviation','rightsHolderURL','rightsHolderFacebook'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("KP96 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'copyright':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    copyright = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag == 'statement':
                            items = subelement.items()
                            assert len(items)==1 and items[0][0]=='contentType'
                            contentType = items[0][1]
                            assert contentType in ('xhtml',)
                            if not len(subelement) and subelement.text:
                                copyright[subelement.tag+'-'+contentType] = subelement.text
                            else:
                                copyright[subelement.tag+'-'+contentType] = BibleOrgSysGlobals.getFlattenedXML( subelement, sub2location )
                        elif subelement.tag == 'fullStatement':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag == 'statementContent':
                                    items = sub2element.items()
                                    assert len(items)==1 and items[0][0]=='type'
                                    contentType = items[0][1]
                                    assert contentType in ('xhtml',)
                                    if not len(subelement) and subelement.text:
                                        copyright[subelement.tag+'-'+contentType] = sub2element.text
                                    else:
                                        copyright[subelement.tag+'-'+contentType] = BibleOrgSysGlobals.getFlattenedXML( sub2element, sub3location )
                                else:
                                    logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        else:
                            logging.warning( _("ZX23 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "copyright", copyright )
                    assert 'copyright' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['copyright']  = copyright
                elif element.tag == 'promotion':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert 'promotion' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['promotion'] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('promoVersionInfo','promoEmail'):
                            items = subelement.items()
                            assert len(items)==1 and items[0][0]=='contentType'
                            contentType = items[0][1]
                            assert contentType in ('xhtml',)
                            if not len(subelement) and subelement.text:
                                self.suppliedMetadata['DBL'][element.tag][subelement.tag+'-'+contentType] = subelement.text
                            else:
                                self.suppliedMetadata['DBL'][element.tag][subelement.tag+'-'+contentType] = BibleOrgSysGlobals.getFlattenedXML( subelement, sub2location )
                        else:
                            logging.warning( _("KY88 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'archiveStatus':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert 'archiveStatus' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['archiveStatus'] = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('archivistName','dateArchived','dateUpdated','comments'):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else:
                            logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'format' and BibleOrgSysGlobals.isBlank( element.text ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    formatDict = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('versedParagraphs',):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text
                            formatDict[subelement.tag] = subelement.text
                        else:
                            logging.warning( _("WS23 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "formatDict", formatDict )
                    assert 'format' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['format']  = formatDict
                elif element.tag == 'format':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert element.text
                    assert element.tag not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL'][element.tag]  = element.text
                elif element.tag == 'manifest':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    manifest = {}
                    containers = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag == 'container':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            container1 = {}
                            uri1 = None
                            for attrib,value in subelement.items():
                                if attrib=='uri': uri1 = value
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag == 'container':
                                    container2 = {}
                                    uri2 = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='uri': uri2 = value
                                        else:
                                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    #if uri2.startswith( 'USX_' ):
                                        #if 'USXFolderName' in self.suppliedMetadata['DBL']:
                                            #vPrint( 'Quiet', debuggingThisModule, "Seem to have multiple USX folders: had {} now {}".format( self.suppliedMetadata['DBL']['USXFolderName'], uri2 ) )
                                        #self.suppliedMetadata['DBL']['USXFolderName'] = uri2
                                    for sub3element in sub2element:
                                        sub4location = sub3element.tag + ' ' + sub3location
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub4location )
                                        assert sub3element.tag == 'resource'
                                        resource = {}
                                        checksum = mimeType = size = uri = None
                                        for attrib,value in sub3element.items():
                                            resource[attrib] = value
                                            #if attrib=='checksum': checksum = value
                                            #elif attrib=='mimeType': mimeType = value
                                            #elif attrib=='size': size = value
                                            #elif attrib=='uri': uri = value
                                            #else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub4location ) )
                                        container2[resource['uri']] = resource
                                    container1[uri2] = container2
                                elif sub2element.tag == 'resource':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                    resource = {}
                                    checksum = mimeType = size = uri = None
                                    for attrib,value in sub2element.items():
                                        resource[attrib] = value
                                        #if attrib=='checksum': checksum = value
                                        #elif attrib=='mimeType': mimeType = value
                                        #elif attrib=='size': size = value
                                        #elif attrib=='uri': uri = value
                                        #else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                    container1[resource['uri']] = resource
                                else:
                                    logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            containers[uri1] = container1
                        elif subelement.tag == 'resource':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            checksum = mimeType = size = uri = None
                            for attrib,value in subelement.items():
                                if attrib=='checksum': checksum = value
                                elif attrib=='mimeType': mimeType = value
                                elif attrib=='size': size = value
                                elif attrib=='uri': uri = value
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if 'Resources' not in manifest: manifest['Resources'] = {}
                            manifest['Resources'][uri] = (checksum,mimeType,size,uri)
                        else:
                            logging.warning( _("YT76 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    manifest['containers'] = containers
                    #vPrint( 'Quiet', debuggingThisModule, "manifest", manifest )
                    assert 'manifest' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['manifest']  = manifest
                elif element.tag == 'names':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    names = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag == 'name':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            container1 = {}
                            nameID = None
                            for attrib,value in subelement.items():
                                if attrib=='id': nameID = value
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert nameID not in names
                            names[nameID] = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag in ('short','abbr','long'):
                                    names[nameID][sub2element.tag] = sub2element.text
                                else:
                                    logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        else:
                            logging.warning( _("CD32 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    # TODO: Need to pivot these as well ???
                    #vPrint( 'Quiet', debuggingThisModule, "names", names )
                    assert 'names' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['names']  = names
                elif element.tag == 'source':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    source = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        canonicalContent, structure = {}, {}
                        if subelement.tag == 'canonicalContent':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            bookList = []
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag == 'book':
                                    BibleOrgSysGlobals.checkXMLNoText( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                    bookCode = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='code': bookCode = value
                                        else:
                                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    if bookCode: bookList.append( bookCode )
                                else:
                                    logging.warning( _("JD46 Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert bookList
                            assert 'books' not in canonicalContent
                            canonicalContent['books'] = bookList
                        elif subelement.tag == 'structure':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            content = {}
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag == 'content':
                                    BibleOrgSysGlobals.checkXMLNoText( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                    src = role = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='src': assert 'src' not in content; content['src'] = value
                                        elif attrib=='role': assert 'role' not in content; content['role'] = value
                                        else:
                                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                else:
                                    logging.warning( _("BD42 Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert content
                            assert 'content' not in structure
                            structure['content'] = content
                        else:
                            logging.warning( _("BS53 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if canonicalContent:
                            assert 'canonicalContent' not in source
                            source['canonicalContent'] = canonicalContent
                        if structure:
                            assert 'structure' not in source
                            source['structure'] = structure
                    #vPrint( 'Quiet', debuggingThisModule, "source", source )
                    assert 'source' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['source']  = source
                elif element.tag == 'publications':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    publications = {}
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag == 'publication':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            publication = {}
                            publicationID = defaultFlag = None
                            for attrib,value in subelement.items():
                                if attrib=='id': publicationID = value
                                elif attrib=='default': defaultFlag = getFlagFromAttribute( attrib, value )
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            publication['ID'] = publicationID
                            publication['DefaultFlag'] = defaultFlag
                            for sub2element in subelement:
                                sub3location = sub2element.tag + ' ' + sub2location
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub3location )
                                if sub2element.tag in ('name','nameLocal','abbreviation','abbreviationLocal','description','descriptionLocal'):
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub3location )
                                    publication[sub2element.tag] = sub2element.text
                                elif sub2element.tag == 'canonicalContent':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoText( sub2element, sub3location )
                                    canonicalContent = []
                                    for sub3element in sub2element:
                                        sub4location = sub3element.tag + ' ' + sub3location
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub4location )
                                        assert sub3element.tag == 'book'
                                        bookCode = None
                                        for attrib,value in sub3element.items():
                                            if attrib=='code': bookCode = value
                                            else:
                                                logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub4location ) )
                                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        assert bookCode not in canonicalContent
                                        canonicalContent.append( bookCode )
                                    publication['CanonicalContent'] = canonicalContent
                                elif sub2element.tag == 'structure':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoText( sub2element, sub3location )
                                    structure = {}
                                    for sub3element in sub2element:
                                        sub4location = sub3element.tag + ' ' + sub3location
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub4location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub4location )
                                        assert sub3element.tag == 'content'
                                        name = role = source = None
                                        for attrib,value in sub3element.items():
                                            if attrib=='name': name = value
                                            elif attrib=='role': role = value
                                            elif attrib=='src': source = value
                                            else:
                                                logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub4location ) )
                                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        assert name not in structure
                                        structure[name] = (name,role,source)
                                        #if 'USXFolderName' not in self.suppliedMetadata['DBL'] \
                                        #and source.startswith( 'USX_' ):
                                            #self.suppliedMetadata['DBL']['USXFolderName'] = source.split( '/' )[0]
                                    publication['Structure'] = structure
                                else:
                                    logging.warning( _("VF56 Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert publicationID not in publications # Fails on Kwere NT
                            if publicationID in publications: # already
                                publicationID += 'a'
                            assert publicationID not in publications
                            publications[publicationID] = publication
                        else:
                            logging.warning( _("PZ95 Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "publications", publications )
                    assert 'publications' not in self.suppliedMetadata['DBL']
                    self.suppliedMetadata['DBL']['publications']  = publications
                else:
                    logging.warning( _("QT26 Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        #vPrint( 'Quiet', debuggingThisModule, '\n', self.suppliedMetadata['DBL'] )
        vPrint( 'Info', debuggingThisModule, "  Loaded {} supplied metadata elements.".format( len(self.suppliedMetadata['DBL']) ) )

        # Find available books
        possibilities = []
        bookList = []
        haveDefault = False
        if 'contents' in self.suppliedMetadata['DBL']:
            for someKey in self.suppliedMetadata['DBL']['contents']:
                if someKey.startswith( 'bookList' ): possibilities.append( someKey )
                if '(default)' in someKey: haveDefault = someKey
            #vPrint( 'Quiet', debuggingThisModule, "possibilities", possibilities )
            bookListKey = haveDefault if haveDefault else possibilities[0]
            #vPrint( 'Quiet', debuggingThisModule, "BL", self.suppliedMetadata['DBL']['contents'][bookListKey] )
            if 'books' in self.suppliedMetadata['DBL']['contents'][bookListKey]:
                for USFMBookCode in self.suppliedMetadata['DBL']['contents'][bookListKey]['books']:
                    #vPrint( 'Quiet', debuggingThisModule, "USFMBookCode", USFMBookCode )
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                    bookList.append( BBB )
                    self.availableBBBs.add( BBB )
            else: logging.error( "loadDBLMetadata: No books in contents (maybe has divisions?) {}".format( self.sourceFilepath ) ) # need to add code if so
        elif 'publications' in self.suppliedMetadata['DBL']:
            for someKey,pubDict in self.suppliedMetadata['DBL']['publications'].items():
                #vPrint( 'Quiet', debuggingThisModule, someKey, pubDict )
                if 'CanonicalContent' in pubDict:
                    for USFMBookCode in pubDict['CanonicalContent']:
                        #vPrint( 'Quiet', debuggingThisModule, "USFMBookCode", USFMBookCode )
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                        bookList.append( BBB )
                        self.availableBBBs.add( BBB )
                    if 'Structure' in pubDict:
                        #vPrint( 'Quiet', debuggingThisModule, 'Structure', pubDict['Structure'] )
                        for bookSomething,bookInfo in pubDict['Structure'].items():
                            if self.DBLMetadataVersion == '2.0': assert bookInfo[2].startswith( 'USX_' )
                            elif self.DBLMetadataVersion == '2.1': assert bookInfo[2].startswith( 'release/USX_' )
                            self.suppliedMetadata['DBL']['USXFolderName'] = os.path.dirname( bookInfo[2] )
                            logging.info( "USX folder is {}".format( self.suppliedMetadata['DBL']['USXFolderName'] ) )
                            break
                    break
        else: vPrint( 'Quiet', debuggingThisModule, "No book list" ); halt
        self.suppliedMetadata['DBL']['OurBookList']  = bookList
    # end of DBLBible.loadDBLMetadata


    def applySuppliedMetadata( self, applyMetadataType ): # Overrides the default one in InternalBible.py
        """
        Using the dictionary at self.suppliedMetadata,
            load the fields into self.settingsDict
            and try to standardise it at the same time.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata({} )".format( applyMetadataType ) )
        assert applyMetadataType in ( 'DBL', 'Project', )

        if applyMetadataType == 'Project': # This is different stuff
            Bible.applySuppliedMetadata( self, applyMetadataType )
            return

        # (else) Apply our specialized DBL metadata
        self.name = self.suppliedMetadata['DBL']['identification']['name']
        self.abbreviation = self.suppliedMetadata['DBL']['identification']['abbreviation']

        # Now we'll flatten the supplied metadata and remove empty values
        flattenedMetadata = {}
        for mainKey,value in self.suppliedMetadata['DBL'].items():
            #vPrint( 'Quiet', debuggingThisModule, "Got {} = {}".format( mainKey, value ) )
            if not value: pass # ignore empty ones
            elif isinstance( value, str ): flattenedMetadata[mainKey] = value # Straight copy
            elif isinstance( value, list ): flattenedMetadata[mainKey] = value # Straight copy
            elif isinstance( value, dict ): # flatten this
                for subKey,subValue in value.items():
                    #vPrint( 'Quiet', debuggingThisModule, "  Got2 {}--{} = {}".format( mainKey, subKey, subValue ) )
                    if not subValue: pass # ignore empty ones
                    elif isinstance( subValue, str ):
                        flattenedMetadata[mainKey+'--'+subKey] = subValue # Straight copy
                    elif isinstance( subValue, dict ): # flatten this
                        for sub2Key,sub2Value in subValue.items():
                            #vPrint( 'Quiet', debuggingThisModule, "    Got3 {}--{}--{} = {}".format( mainKey, subKey, sub2Key, sub2Value ) )
                            if not sub2Value:  pass # ignore empty ones
                            elif isinstance( sub2Value, str ):
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            elif isinstance( sub2Value, bool ):
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            elif isinstance( sub2Value, list ):
                                assert sub2Key in ('books','CanonicalContent',)
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            elif isinstance( sub2Value, dict ):
                                if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                                    vPrint( 'Quiet', debuggingThisModule, "How do we handle a dict here???" )
                            elif isinstance( sub2Value, tuple ):
                                if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                                    vPrint( 'Quiet', debuggingThisModule, "How do we handle a tuple here???" )
                            else: vPrint( 'Quiet', debuggingThisModule, "Programming error3 in applySuppliedMetadata", mainKey, subKey, sub2Key, repr(sub2Value) ); halt
                    elif isinstance( subValue, list ): # flatten this
                        flattenedMetadata[mainKey+'--'+subKey] = '--'.join( subValue )
                    else: vPrint( 'Quiet', debuggingThisModule, "Programming error2 in applySuppliedMetadata", mainKey, subKey, repr(subValue) ); halt
            else: vPrint( 'Quiet', debuggingThisModule, "Programming error in applySuppliedMetadata", mainKey, repr(value) ); halt
        #vPrint( 'Quiet', debuggingThisModule, "\nflattenedMetadata", flattenedMetadata )

        nameChangeDict = {'License':'Licence'}
        for oldKey,value in flattenedMetadata.items():
            newKey = nameChangeDict[oldKey] if oldKey in nameChangeDict else oldKey
            if newKey in self.settingsDict: # We have a duplicate
                logging.warning("About to replace {!r}={!r} from metadata file".format( newKey, self.settingsDict[newKey] ) )
            else: # Also check for "duplicates" with a different case
                ucNewKey = newKey.upper()
                for key in self.settingsDict:
                    ucKey = key.upper()
                    if ucKey == ucNewKey:
                        logging.warning("About to copy {!r} from metadata file even though already have {!r}".format( newKey, key ) )
                        break
            self.settingsDict[newKey] = value
    # end of InternalBible.applySuppliedMetadata


    def loadDBLStyles( self ):
        """
        Load the styles.xml file and parse it into the ordered dictionary self.suppliedMetadata['DBL'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "loadDBLStyles()" )

        if self.DBLMetadataVersion == '2.1': styleFilepath = os.path.join( self.sourceFilepath, 'release/', 'styles.xml' )
        else: styleFilepath = os.path.join( self.sourceFilepath, 'styles.xml' )
        vPrint( 'Info', debuggingThisModule, "DBLBible.loading styles from {}…".format( styleFilepath ) )
        self.XMLTree = ElementTree().parse( styleFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        def getStyle( element, location ):
            """
            Load the contents information (which is more nested/complex).
            """
            assert element.tag == 'style'
            ourDict = DBLStyles['styles']
            BibleOrgSysGlobals.checkXMLNoText( element, location )
            BibleOrgSysGlobals.checkXMLNoTail( element, location )

            # Process style attributes first
            styleID = publishable = versetext = None
            for attrib,value in element.items():
                if attrib=='id': styleID = value
                elif attrib=='publishable': publishable = value
                elif attrib=='versetext': versetext = value
                else:
                    logging.warning( _("Unprocessed style {} attribute ({}) in {}").format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #vPrint( 'Quiet', debuggingThisModule, "StyleID", styleID )
            assert styleID not in ourDict
            ourDict[styleID] = {}

            # Now process the style properties
            for subelement in element:
                sublocation = subelement.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, "  Processing {}…".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                if subelement.tag in ( 'name', 'description' ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                    assert subelement.tag not in ourDict[styleID]
                    ourDict[styleID][subelement.tag] = subelement.text
                elif subelement.tag == 'property':
                    if 'properties' not in ourDict[styleID]: ourDict[styleID]['properties'] = {}
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                    # Collect the property attributes first
                    name = None
                    attribDict = {}
                    for attrib,value in element.items():
                        if attrib=='name': name = value
                        else: attribDict[attrib] = value
                    if name in ( 'font-family', 'font-size' ):
                        ourDict[styleID]['properties'][name] = ( element.text, attribDict )
                else:
                    logging.warning( _("Unprocessed style {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #vPrint( 'Quiet', debuggingThisModule, "Styles:", DBLStyles['styles'] )
        # end of getStyle

        DBLStyles = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='stylesheet':
            location = "DBL {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, location )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location )

            # Now process the actual properties and styles
            for element in self.XMLTree:
                sublocation = element.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, "\nProcessing {}…".format( sublocation ) )
                if element.tag == 'property':
                    if 'properties' not in DBLStyles: DBLStyles['properties'] = {}
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    # Collect the property attributes first
                    name = None
                    attribDict = {}
                    for attrib,value in element.items():
                        if attrib=='name': name = value
                        else: attribDict[attrib] = value
                    if name in ( 'font-family', 'font-size' ):
                        DBLStyles['properties'][name] = ( element.text, attribDict )
                elif element.tag == 'style':
                    if 'styles' not in DBLStyles: DBLStyles['styles'] = {}
                    getStyle( element, sublocation )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        #vPrint( 'Quiet', debuggingThisModule, '\n', self.suppliedMetadata['DBL'] )
        vPrint( 'Info', debuggingThisModule, "  Loaded {} style elements.".format( len(DBLStyles['styles']) ) )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLStyles', DBLStyles )
        if DBLStyles: self.suppliedMetadata['DBL']['Styles'] = DBLStyles
    # end of DBLBible.loadDBLStyles


    #def loadDBLVersification( self ):
        #"""
        #Load the versification.vrs file (which is a text file)
            #and parse it into the ordered dictionary DBLVersification.
        #"""
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            #vPrint( 'Quiet', debuggingThisModule, "loadDBLVersification()" )

        #versificationFilename = 'versification.vrs'
        #versificationFilepath = os.path.join( self.sourceFilepath, versificationFilename )
        #vPrint( 'Info', debuggingThisModule, "DBLBible.loading versification from {}…".format( versificationFilepath ) )

        #DBLVersification = { 'VerseCounts':{}, 'Mappings':{}, 'Omitted':[] }

        #lineCount = 0
        #with open( versificationFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            #for line in vFile:
                #lineCount += 1
                #if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    #logging.info( "SFMLines: Detected Unicode Byte Order Marker (BOM) in {}".format( versificationFilename ) )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                #if not line: continue # Just discard blank lines
                #lastLine = line
                #if line[0]=='#' and not line.startswith('#!'): continue # Just discard comment lines
                ##vPrint( 'Quiet', debuggingThisModule, "Versification line", repr(line) )

                #if len(line)<7:
                    #vPrint( 'Quiet', debuggingThisModule, "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    #continue

                #if line.startswith( '#! -' ): # It's an excluded verse (or passage???)
                    #assert line[7] == ' '
                    #USFMBookCode = line[4:7]
                    #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                    #C,V = line[8:].split( ':', 1 )
                    ##vPrint( 'Quiet', debuggingThisModule, "CV", repr(C), repr(V) )
                    #if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                    ##vPrint( 'Quiet', debuggingThisModule, "Omitted {} {}:{}".format( BBB, C, V ) )
                    #DBLVersification['Omitted'].append( (BBB,C,V) )
                #elif line[0] == '#': # It's a comment line
                    #pass # Just ignore it
                #elif '=' in line: # it's a verse mapping, e.g.,
                    #left, right = line.split( ' = ', 1 )
                    ##vPrint( 'Quiet', debuggingThisModule, "left", repr(left), 'right', repr(right) )
                    #USFMBookCode1, USFMBookCode2 = left[:3], right[:3]
                    #BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode1 )
                    #BBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode2 )
                    #DBLVersification['Mappings'][BBB1+left[3:]] = BBB2+right[3:]
                    ##vPrint( 'Quiet', debuggingThisModule, DBLVersification['Mappings'] )
                #else: # It's a verse count line, e.g., LAM 1:22 2:22 3:66 4:22 5:22
                    #assert line[3] == ' '
                    #USFMBookCode = line[:3]
                    ##if USFMBookCode == 'ODA': USFMBookCode = 'ODE'
                    #try:
                        #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                        #DBLVersification['VerseCounts'][BBB] = {}
                        #for CVBit in line[4:].split():
                            ##vPrint( 'Quiet', debuggingThisModule, "CVBit", repr(CVBit) )
                            #assert ':' in CVBit
                            #C,V = CVBit.split( ':', 1 )
                            ##vPrint( 'Quiet', debuggingThisModule, "CV", repr(C), repr(V) )
                            #if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                            #DBLVersification['VerseCounts'][BBB][C] = V
                    #except KeyError:
                        #logging.error( "Unknown {!r} USX book code in DBLBible.loading versification from {}".format( USFMBookCode, versificationFilepath ) )

        ##vPrint( 'Quiet', debuggingThisModule, '\n', self.suppliedMetadata['DBL'] )
        #vPrint( 'Info', debuggingThisModule, "  Loaded {} versification elements.".format( len(DBLVersification) ) )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLVersification', DBLVersification ); halt
    ## end of DBLBible.loadDBLVersification


    #def loadDBLLanguage( self ):
        #"""
        #Load the something.lds file (which is an INI file) and parse it into the ordered dictionary DBLLanguage.
        #"""
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            #vPrint( 'Quiet', debuggingThisModule, "loadDBLLanguage()" )

        #languageFilenames = []
        #for something in os.listdir( self.sourceFilepath ):
            #somepath = os.path.join( self.sourceFilepath, something )
            #if os.path.isfile(somepath) and something.endswith('.lds'): languageFilenames.append( something )
        #if len(languageFilenames) > 1:
            #logging.error( "Got more than one language file: {}".format( languageFilenames ) )
        #languageFilename = languageFilenames[0]
        #languageName = languageFilename[:-4] # Remove the .lds

        #languageFilepath = os.path.join( self.sourceFilepath, languageFilename )
        #vPrint( 'Info', debuggingThisModule, "DBLBible.loading language from {}…".format( languageFilepath ) )

        #DBLLanguage = { 'Filename':languageName }

        #lineCount = 0
        #sectionName = None
        #with open( languageFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            #for line in vFile:
                #lineCount += 1
                #if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    #logging.info( "SFMLines: Detected Unicode Byte Order Marker (BOM) in {}".format( languageFilename ) )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                #if not line: continue # Just discard blank lines
                #lastLine = line
                #if line[0]=='#': continue # Just discard comment lines
                ##vPrint( 'Quiet', debuggingThisModule, "line", repr(line) )

                #if len(line)<5:
                    #vPrint( 'Quiet', debuggingThisModule, "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    #continue

                #if line[0]=='[' and line[-1]==']': # it's a new section name
                    #sectionName = line[1:-1]
                    #assert sectionName not in DBLLanguage
                    #DBLLanguage[sectionName] = {}
                #elif '=' in line: # it's a mapping, e.g., UpperCaseLetters=ABCDEFGHIJKLMNOPQRSTUVWXYZ
                    #left, right = line.split( '=', 1 )
                    ##vPrint( 'Quiet', debuggingThisModule, "left", repr(left), 'right', repr(right) )
                    #DBLLanguage[sectionName][left] = right
                #else: vPrint( 'Quiet', debuggingThisModule, "What's this language line? {!r}".format( line ) )

        ##vPrint( 'Quiet', debuggingThisModule, '\n', DBLLanguage )
        #vPrint( 'Info', debuggingThisModule, "  Loaded {} language sections.".format( len(DBLLanguage) ) )
        #vPrint( 'Quiet', debuggingThisModule, 'DBLLanguage', DBLLanguage ); halt
    ## end of DBLBible.loadDBLLanguage


    def loadBooks( self ):
        """
        Load the USX XML Bible text files.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "loadBooks()" )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, _("DBLBible: Loading {} books from {}…").format( self.name, self.sourceFilepath ) )

        if not self.preloadDone: self.preload()
        if not self.preloadDone: return # coz it must have failed

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: vPrint( 'Quiet', debuggingThisModule, "ERROR: Not sure what '{}' is in {}!".format( somepath, self.sourceFilepath ) )
        if not foundFolders: # We need a USX folder
            logging.critical( "DBLBible.loadBooks: Couldn't find any folders in '{}'".format( self.sourceFilepath ) )
            return # No use continuing

        # Determine which is the USX subfolder
        if 'USXFolderName' in self.suppliedMetadata['DBL']:
            self.USXFolderPath = os.path.join( self.sourceFilepath, self.suppliedMetadata['DBL']['USXFolderName'] + '/' )
        else:
            possibilities = []
            haveDefault = False
            for someKey in self.suppliedMetadata['DBL']['contents']:
                if someKey.startswith( 'bookList' ): possibilities.append( someKey )
                if '(default)' in someKey: haveDefault = someKey
            #vPrint( 'Quiet', debuggingThisModule, "possibilities", possibilities )
            bookListKey = haveDefault if haveDefault else possibilities[0]
            USXFolderName = 'USX_' + bookListKey[9:10]
            #vPrint( 'Quiet', debuggingThisModule, "USXFolderName", USXFolderName )
            self.USXFolderPath = os.path.join( self.sourceFilepath, USXFolderName + '/' )
        #vPrint( 'Quiet', debuggingThisModule, "USXFolderPath", self.USXFolderPath )

        ## Work out our filenames
        #self.USXFilenamesObject = USXFilenames( self.USXFolderPath )
        #vPrint( 'Quiet', debuggingThisModule, "fo", self.USXFilenamesObject )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        if 'OurBookList' in self.suppliedMetadata['DBL']:
            for BBB in self.suppliedMetadata['DBL']['OurBookList']:
                filename = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper() + '.usx'
                if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "About to load {} from {} …".format( BBB, filename ) )
                UBB = USXXMLBibleBook( self, BBB )
                UBB.load( filename, self.USXFolderPath, self.encoding )
                UBB.validateMarkers()
                #vPrint( 'Quiet', debuggingThisModule, UBB )
                self.books[BBB] = UBB
                # Make up our book name dictionaries while we're at it
                assumedBookNames = UBB.getAssumedBookNames()
                for assumedBookName in assumedBookNames:
                    self.BBBToNameDict[BBB] = assumedBookName
                    assumedBookNameLower = assumedBookName.lower()
                    self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
        else:
            #vPrint( 'Quiet', debuggingThisModule, "bookListKey", bookListKey )
            for USFMBookCode in self.suppliedMetadata['DBL']['contents'][bookListKey]['books']:
                #vPrint( 'Quiet', debuggingThisModule, "USFMBookCode", USFMBookCode )
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                filename = USFMBookCode + '.usx'
                UBB = USXXMLBibleBook( self, BBB )
                UBB.load( filename, self.USXFolderPath, self.encoding )
                UBB.validateMarkers()
                #vPrint( 'Quiet', debuggingThisModule, UBB )
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
            vPrint( 'Info', debuggingThisModule, "DBLBible.loadBooks: Didn't find any regularly named USX files in '{}'".format( self.USXFolderPath ) )

        self.doPostLoadProcessing()
    # end of DBLBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class DBLBible



def __processDBLBible( parametersTuple ): # for demo
    """
    Special shim function used for multiprocessing.
    """
    codeLetter, mainFolderName, subFolderName = parametersTuple
    vPrint( 'Normal', debuggingThisModule, "\nDBL {} Trying {}".format( codeLetter, subFolderName ) )
    DBL_Bible = DBLBible( mainFolderName, subFolderName )
    DBL_Bible.load()
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
        BBB = 'JN1'
        if BBB in DBL_Bible:
            DBL_Bible.books[BBB].debugPrint()
            for entryKey in DBL_Bible.books[BBB]._CVIndex:
                vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )
# end of __processDBLBible


def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = DBLBibleFileCheck( testFolder )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA1", result1 )
        result2 = DBLBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA2", result2 )
        result3 = DBLBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA3", result3 )

    if 00: # demo the file checking code with temp folder
        resultB = DBLBibleFileCheck( BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'TempFiles/' ), autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestB", resultB )

    if 00: # specify testFolder containing a single module
        vPrint( 'Normal', debuggingThisModule, "\nDBL C/ Trying single module in {}".format( testFolder ) )
        XXXtestDBL_B( testFolder )

    if 00: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        vPrint( 'Normal', debuggingThisModule, "\nDBL D/ Trying installed {} module".format( singleModule ) )
        DBL_Bible = DBLBible( testFolder, singleModule )
        DBL_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in DBL_Bible:
                DBL_Bible.books[BBB].debugPrint()
                for entryKey in DBL_Bible.books[BBB]._CVIndex:
                    vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00: # specified installed modules
        good = ('eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30',
                'eng-rv_dbl_40072c4a5aba4022-rev1-2014-09-24',
                'eng-webbe_dbl_7142879509583d59-rev2-2014-09-24',
                'engwmb_dbl_f72b840c855f362c-rev1-2014-09-24',
                'engwmbb_dbl_04da588535d2f823-rev1-2014-09-24',
                'ton_dbl_25210406001d9aae-rev2-2014-09-24',)
        nonEnglish = ( 'ton_dbl_25210406001d9aae-rev2-2014-09-24', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', debuggingThisModule, "\nDBL E{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            DBL_Bible = DBLBible( testFolder, testFilename )
            DBL_Bible.load()
            break


    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Open access Bibles from DBL
        sampleFolder = BiblesFolderpath.joinpath( 'DBL Bibles/DBL Open Access Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL F{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 1: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'DBL Bibles/Haiola DBL test versions/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL G{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL H{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/'),
                    ) # You can put your DBL test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = DBLBible( testFolder )
                DB.loadDBLMetadata()
                DB.preload()
                vPrint( 'Quiet', debuggingThisModule, DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                DB.loadBooks()
                #DBErrors = DB.getCheckResults()
                # vPrint( 'Quiet', debuggingThisModule, DBErrors )
                #vPrint( 'Quiet', debuggingThisModule, DB.getVersification() )
                #vPrint( 'Quiet', debuggingThisModule, DB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##vPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                    #vPrint( 'Quiet', debuggingThisModule, "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', debuggingThisModule, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
    #       pass
# end of DBLBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = DBLBibleFileCheck( testFolder )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA1", result1 )
        result2 = DBLBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA2", result2 )
        result3 = DBLBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestA3", result3 )

    if 00: # demo the file checking code with temp folder
        resultB = DBLBibleFileCheck( BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'TempFiles/' ), autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "DBL TestB", resultB )

    if 00: # specify testFolder containing a single module
        vPrint( 'Normal', debuggingThisModule, "\nDBL C/ Trying single module in {}".format( testFolder ) )
        XXXtestDBL_B( testFolder )

    if 00: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        vPrint( 'Normal', debuggingThisModule, "\nDBL D/ Trying installed {} module".format( singleModule ) )
        DBL_Bible = DBLBible( testFolder, singleModule )
        DBL_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in DBL_Bible:
                DBL_Bible.books[BBB].debugPrint()
                for entryKey in DBL_Bible.books[BBB]._CVIndex:
                    vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00: # specified installed modules
        good = ('eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30',
                'eng-rv_dbl_40072c4a5aba4022-rev1-2014-09-24',
                'eng-webbe_dbl_7142879509583d59-rev2-2014-09-24',
                'engwmb_dbl_f72b840c855f362c-rev1-2014-09-24',
                'engwmbb_dbl_04da588535d2f823-rev1-2014-09-24',
                'ton_dbl_25210406001d9aae-rev2-2014-09-24',)
        nonEnglish = ( 'ton_dbl_25210406001d9aae-rev2-2014-09-24', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', debuggingThisModule, "\nDBL E{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            DBL_Bible = DBLBible( testFolder, testFilename )
            DBL_Bible.load()


    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Open access Bibles from DBL
        sampleFolder = BiblesFolderpath.joinpath( 'DBL Bibles/DBL Open Access Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL F{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 1: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'DBL Bibles/Haiola DBL test versions/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL G{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )


    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            vPrint( 'Normal', debuggingThisModule, _("Loading {} DBL modules using {} processes…").format( len(foundFolders), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed.") )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processDBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nDBL H{}/ Trying {}".format( j+1, folderName ) )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                DBL_Bible = DBLBible( myTestFolder, folderName )
                DBL_Bible.load()
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in DBL_Bible:
                        DBL_Bible.books[BBB].debugPrint()
                        for entryKey in DBL_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', debuggingThisModule, BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/'),
                    ) # You can put your DBL test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = DBLBible( testFolder )
                DB.loadDBLMetadata()
                DB.preload()
                vPrint( 'Quiet', debuggingThisModule, DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                DB.loadBooks()
                #DBErrors = DB.getCheckResults()
                # vPrint( 'Quiet', debuggingThisModule, DBErrors )
                #vPrint( 'Quiet', debuggingThisModule, DB.getVersification() )
                #vPrint( 'Quiet', debuggingThisModule, DB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##vPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                    #vPrint( 'Quiet', debuggingThisModule, "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', debuggingThisModule, "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
    #       pass
# end of DBLBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of DBLBible.py
