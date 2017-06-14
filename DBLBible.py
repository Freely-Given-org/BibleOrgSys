#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DBLBible.py
#
# Module handling Digital Bible Library (DBL) compilations of USX XML Bible books
#                                               along with XML and other metadata
#
# Copyright (C) 2013-2017 Robert Hunt
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
Module for defining and manipulating complete or partial DBL Bible bundles.

See http://digitalbiblelibrary.org and http://digitalbiblelibrary.org/info/inside
as well as http://www.everytribeeverynation.org/library.

There seems to be some incomplete documentation at http://digitalbiblelibrary.org/static/docs/index.html
    and specifically the text bundle at http://digitalbiblelibrary.org/static/docs/entryref/text/index.html.
"""

from gettext import gettext as _

LastModifiedDate = '2017-06-15' # by RJH
ShortProgName = "DigitalBibleLibrary"
ProgName = "Digital Bible Library (DBL) XML Bible handler"
ProgVersion = '0.21'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals
from Bible import Bible
from USXXMLBibleBook import USXXMLBibleBook
from PTX7Bible import loadPTX7Languages, loadPTXVersifications



COMPULSORY_FILENAMES = ( 'METADATA.XML', 'LICENSE.XML', 'STYLES.XML' ) # Must all be UPPER-CASE



def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, errorBit )
# end of t



def DBLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for DBL Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one DBL Bible bundle is found,
        returns the loaded DBLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
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
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " DBLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something == '__MACOSX': continue # don't visit these directories
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
    #if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    #filenameTuples = UFns.getConfirmedFilenames()
    #if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
    #if BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "Found {} USX files.".format( len(filenameTuples) ) )
    #if filenameTuples:
        #numFound += 1

    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBibleFileCheck got", numFound, givenFolderName )
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
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    DBLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
        #filenameTuples = UFns.getConfirmedFilenames()
        #if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
        #if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        #elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USX files".format( len(filenameTuples) ) )
        #if filenameTuples:
            #foundProjects.append( tryFolderName )
            #numFound += 1

    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = DBLBible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            return dB
        return numFound
# end of DBLBibleFileCheck



class DBLBible( Bible ):
    """
    Class to load and manipulate DBL Bible bundles.
    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal DBL Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'DBL XML Bible object'
        self.objectTypeString = 'DBL'

        self.sourceFolder, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        if givenName:
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.error( "DBLBible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        else: self.sourceFilepath = self.sourceFolder
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.error( "DBLBible: Folder '{}' is unreadable".format( self.sourceFilepath ) )

        # Create empty containers for loading the XML metadata files
        #DBLLicense = DBLStyles = DBLVersification = DBLLanguage = None
    # end of DBLBible.__init__


    def preload( self ):
        """
        Load the XML metadata files.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("preload() from {}").format( self.sourceFolder ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("DBLBible: Loading {} from {}…").format( self.name, self.sourceFilepath ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: print( "ERROR: Not sure what '{}' is in {}!".format( somepath, self.sourceFilepath ) )
        if not foundFiles:
            print( "DBLBible.preload: Couldn't find any files in '{}'".format( self.sourceFilepath ) )
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
        #print( 'DBLLicense', len(DBLLicense), DBLLicense )
        #print( 'DBLMetadata', len(self.suppliedMetadata), self.suppliedMetadata )
        #print( 'DBLStyles', len(DBLStyles), DBLStyles )
        #print( 'DBLVersification', len(DBLVersification), DBLVersification )
        #print( 'DBLLanguage', len(DBLLanguage), DBLLanguage )

        self.preloadDone = True
    # end of DBLBible.preload


    def loadDBLLicense( self ):
        """
        Load the metadata.xml file and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadDBLLicense()") )

        licenseFilepath = os.path.join( self.sourceFilepath, 'license.xml' )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBible.loading license data from {}…".format( licenseFilepath ) )
        self.tree = ElementTree().parse( licenseFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        DBLLicense = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='license':
            location = "DBL {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Process the metadata attributes first
            licenseID = None
            for attrib,value in self.tree.items():
                if attrib=='id': licenseID = value
                else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            DBLLicense['Id'] = licenseID

            # Now process the actual metadata
            for element in self.tree:
                sublocation = element.tag + ' ' + location
                #print( "\nProcessing {}…".format( sublocation ) )
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
                        #print( "  Processing {}…".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('allowOffline', 'allowIntroductions', 'allowFootnotes', 'allowCrossReferences', 'allowExtendedNotes' ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in DBLLicense[element.tag]
                            DBLLicense[element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} license elements.".format( len(DBLLicense) ) )
        #print( 'DBLLicense', DBLLicense )
        if DBLLicense: self.suppliedMetadata['DBL']['License'] = DBLLicense
    # end of DBLBible.loadDBLLicense


    def loadDBLMetadata( self ):
        """
        Load the metadata.xml file and parse it into the ordered dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadDBLMetadata()") )

        mdFilepath = os.path.join( self.sourceFilepath, 'metadata.xml' )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBible.loading supplied DBL metadata from {}…".format( mdFilepath ) )
        self.tree = ElementTree().parse( mdFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        def getContents( element, location ):
            """
            Load the contents information (which is more nested/complex).
            """
            assert element.tag == 'contents'
            ourDict = self.suppliedMetadata['DBL']['contents']
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location )
            BibleOrgSysGlobals.checkXMLNoText( element, location )
            BibleOrgSysGlobals.checkXMLNoTail( element, location )
            for subelement in element:
                sublocation = subelement.tag + ' ' + location
                #print( "  Processing {}…".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                assert subelement.tag == 'bookList'
                bookListID = bookListIsDefault = None
                for attrib,value in subelement.items():
                    if attrib=='id': bookListID = value
                    elif attrib=='default': bookListIsDefault = value
                    else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                bookListTag = subelement.tag + '-' + bookListID + (' (default)' if bookListIsDefault=='true' else '')
                assert bookListTag not in ourDict
                ourDict[bookListTag] = {}
                ourDict[bookListTag]['divisions'] = OrderedDict()
                for sub2element in subelement:
                    sub2location = sub2element.tag + ' ' + sublocation
                    #print( "    Processing {}…".format( sub2location ) )
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
                            #print( "        Processing {}…".format( sub3location ) )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                            assert sub3element.tag == 'book'
                            items = sub3element.items()
                            assert len(items)==1 and items[0][0]=='code'
                            bookCode = items[0][1]
                            ourDict[bookListTag]['books'].append( bookCode )
                    else: logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                    #if 0:
                        #items = sub2element.items()
                        #for sub3element in sub2element:
                            #sub3location = sub3element.tag + ' ' + sub2location
                            #print( "      Processing {}…".format( sub3location ) )
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                            #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                            #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                            #assert sub3element.tag == 'books' # Don't bother saving this extra level
                            #for sub4element in sub3element:
                                #sub4location = sub4element.tag + ' ' + sub3location
                                #print( "        Processing {}…".format( sub4location ) )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location )
                                #BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                #assert sub4element.tag == 'book'
                                #items = sub4element.items()
                                #assert len(items)==1 and items[0][0]=='code'
                                #bookCode = items[0][1]
                                #ourDict[bookListTag]['divisions'][divisionID].append( bookCode )
            #print( "Contents:", self.suppliedMetadata['DBL']['contents'] )
        # end of getContents

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['DBL'] = {}
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='DBLMetadata':
            location = "DBL Metadata ({}) file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Process the metadata attributes first
            mdType = mdTypeVersion = mdID = mdRevision = None
            for attrib,value in self.tree.items():
                if attrib=='type': mdType = value
                elif attrib=='typeVersion': mdTypeVersion = value
                elif attrib=='id': mdID = value
                elif attrib=='revision': mdRevision = value
                else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            if BibleOrgSysGlobals.debugFlag:
                assert mdType == 'text'
                assert mdTypeVersion in ( '1.3', '1.5', )
                assert mdRevision in ( '1','2','3', '4', )

            # Now process the actual metadata
            for element in self.tree:
                sublocation = element.tag + ' ' + location
                #print( "\nProcessing {}…".format( sublocation ) )
                self.suppliedMetadata['DBL'][element.tag] = OrderedDict()
                if element.tag == 'identification':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        #print( "  Processing {}…".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('name','nameLocal','abbreviation','abbreviationLocal','scope','description','dateCompleted','systemId','bundleProducer'):
                            thisTag = subelement.tag
                            if subelement.tag == 'systemId': # Can have multiples of these
                                systemIdType = csetid = fullname = name = None
                                for attrib,value in subelement.items():
                                    if attrib=='type': systemIdType = value
                                    elif attrib=='csetid': csetid = value
                                    elif attrib=='fullname': fullname = value
                                    elif attrib=='name': name = value
                                    else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                pass # Xxxxxxxxxxxxx not stored
                                #thisTag = thisTag + '-' + items[0][1]
                            else: BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            assert subelement.text
                            self.suppliedMetadata['DBL'][element.tag][thisTag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'confidential':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    self.suppliedMetadata['DBL']['confidential'] = element.text
                elif element.tag == 'agencies':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        url = None
                        for attrib,value in subelement.items():
                            if attrib=='url': url = value
                            else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                        pass # url isn't saved XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx
                        if subelement.tag in ('etenPartner','creator','publisher','contributor'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'language':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('iso','name','ldml','rod','script','scriptDirection','numerals'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'country':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('iso','name'):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'type':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('translationType','audience'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
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
                            else: logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub3location ) )
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
                            else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                        #print( bookCode, stage )
                        assert len(bookCode) == 3
                        if bookCode not in self.suppliedMetadata['DBL']['bookNames']:
                            logging.warning( _("Bookcode {} mentioned in progress but not found in bookNames").format( bookCode ) )
                        assert stage in ('1','2','3','4')
                        self.suppliedMetadata['DBL'][element.tag][bookCode] = stage
                elif element.tag == 'contact':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('rightsHolder','rightsHolderLocal','rightsHolderAbbreviation','rightsHolderURL','rightsHolderFacebook'):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'copyright':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('statement',):
                            items = subelement.items()
                            assert len(items)==1 and items[0][0]=='contentType'
                            contentType = items[0][1]
                            assert contentType in ('xhtml',)
                            if not len(subelement) and subelement.text:
                                self.suppliedMetadata['DBL'][element.tag][subelement.tag+'-'+contentType] = subelement.text
                            else:
                                self.suppliedMetadata['DBL'][element.tag][subelement.tag+'-'+contentType] = BibleOrgSysGlobals.getFlattenedXML( subelement, sub2location )
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'promotion':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
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
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'archiveStatus':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('archivistName','dateArchived','dateUpdated','comments'):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text
                            self.suppliedMetadata['DBL'][element.tag][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                elif element.tag == 'format':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    assert element.text
                    self.suppliedMetadata['DBL'][element.tag]  = element.text
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
        #print( '\n', self.suppliedMetadata['DBL'] )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} supplied metadata elements.".format( len(self.suppliedMetadata['DBL']) ) )

        # Find available books
        possibilities = []
        haveDefault = False
        for someKey in self.suppliedMetadata['DBL']['contents']:
            if someKey.startswith( 'bookList' ): possibilities.append( someKey )
            if '(default)' in someKey: haveDefault = someKey
        #print( "possibilities", possibilities )
        bookListKey = haveDefault if haveDefault else possibilities[0]
        for USFMBookCode in self.suppliedMetadata['DBL']['contents'][bookListKey]['books']:
            #print( "USFMBookCode", USFMBookCode )
            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
            self.availableBBBs.add( BBB )
    # end of DBLBible.loadDBLMetadata


    def applySuppliedMetadata( self, applyMetadataType ): # Overrides the default one in InternalBible.py
        """
        Using the dictionary at self.suppliedMetadata,
            load the fields into self.settingsDict
            and try to standardise it at the same time.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( t("applySuppliedMetadata({} )").format( applyMetadataType ) )
        assert applyMetadataType in ( 'DBL', 'Project', )

        if applyMetadataType == 'Project': # This is different stuff
            Bible.applySuppliedMetadata( applyMetadataType )
            return

        # (else) Apply our specialized DBL metadata
        self.name = self.suppliedMetadata['DBL']['identification']['name']
        self.abbreviation = self.suppliedMetadata['DBL']['identification']['abbreviation']

        # Now we'll flatten the supplied metadata and remove empty values
        flattenedMetadata = {}
        for mainKey,value in self.suppliedMetadata['DBL'].items():
            #print( "Got {} = {}".format( mainKey, value ) )
            if not value: pass # ignore empty ones
            elif isinstance( value, str ): flattenedMetadata[mainKey] = value # Straight copy
            elif isinstance( value, dict ): # flatten this
                for subKey,subValue in value.items():
                    #print( "  Got2 {}--{} = {}".format( mainKey, subKey, subValue ) )
                    if not subValue: pass # ignore empty ones
                    elif isinstance( subValue, str ):
                        flattenedMetadata[mainKey+'--'+subKey] = subValue # Straight copy
                    elif isinstance( subValue, dict ): # flatten this
                        for sub2Key,sub2Value in subValue.items():
                            #print( "    Got3 {}--{}--{} = {}".format( mainKey, subKey, sub2Key, sub2Value ) )
                            if not sub2Value:  pass # ignore empty ones
                            elif isinstance( sub2Value, str ):
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            elif isinstance( sub2Value, list ):
                                assert sub2Key == 'books'
                                flattenedMetadata[mainKey+'--'+subKey+'--'+sub2Key] = sub2Value # Straight copy
                            else: print( "Programming error3 in applySuppliedMetadata", mainKey, subKey, sub2Key, repr(sub2Value) ); halt
                    else: print( "Programming error2 in applySuppliedMetadata", mainKey, subKey, repr(subValue) ); halt
            else: print( "Programming error in applySuppliedMetadata", mainKey, repr(value) ); halt
        #print( "\nflattenedMetadata", flattenedMetadata )

        nameChangeDict = {} # not done yet
        for oldKey,value in flattenedMetadata.items():
            newKey = nameChangeDict[oldKey] if oldKey in nameChangeDict else oldKey
            if newKey in self.settingsDict: # We have a duplicate
                logging.warning("About to replace {}={} from metadata file".format( repr(newKey), repr(self.settingsDict[newKey]) ) )
            else: # Also check for "duplicates" with a different case
                ucNewKey = newKey.upper()
                for key in self.settingsDict:
                    ucKey = key.upper()
                    if ucKey == ucNewKey:
                        logging.warning("About to copy {} from metadata file even though already have {}".format( repr(newKey), repr(key) ) )
                        break
            self.settingsDict[newKey] = value
    # end of InternalBible.applySuppliedMetadata


    def loadDBLStyles( self ):
        """
        Load the styles.xml file and parse it into the ordered dictionary self.suppliedMetadata['DBL'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadDBLStyles()") )

        styleFilepath = os.path.join( self.sourceFilepath, 'styles.xml' )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBible.loading styles from {}…".format( styleFilepath ) )
        self.tree = ElementTree().parse( styleFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

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
                else: logging.warning( _("Unprocessed style {} attribute ({}) in {}").format( attrib, value, location ) )
            #print( "StyleID", styleID )
            assert styleID not in ourDict
            ourDict[styleID] = OrderedDict()

            # Now process the style properties
            for subelement in element:
                sublocation = subelement.tag + ' ' + location
                #print( "  Processing {}…".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                if subelement.tag in ( 'name', 'description' ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                    assert subelement.tag not in ourDict[styleID]
                    ourDict[styleID][subelement.tag] = subelement.text
                elif subelement.tag == 'property':
                    if 'properties' not in ourDict[styleID]: ourDict[styleID]['properties'] = OrderedDict()
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
                else: logging.warning( _("Unprocessed style {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
            #print( "Styles:", DBLStyles['styles'] )
        # end of getStyle

        DBLStyles = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='stylesheet':
            location = "DBL {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Now process the actual properties and styles
            for element in self.tree:
                sublocation = element.tag + ' ' + location
                #print( "\nProcessing {}…".format( sublocation ) )
                if element.tag == 'property':
                    if 'properties' not in DBLStyles: DBLStyles['properties'] = OrderedDict()
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
                    if 'styles' not in DBLStyles: DBLStyles['styles'] = OrderedDict()
                    getStyle( element, sublocation )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
        #print( '\n', self.suppliedMetadata['DBL'] )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} style elements.".format( len(DBLStyles['styles']) ) )
        #print( 'DBLStyles', DBLStyles )
        if DBLStyles: self.suppliedMetadata['DBL']['Styles'] = DBLStyles
    # end of DBLBible.loadDBLStyles


    #def loadDBLVersification( self ):
        #"""
        #Load the versification.vrs file (which is a text file)
            #and parse it into the ordered dictionary DBLVersification.
        #"""
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            #print( t("loadDBLVersification()") )

        #versificationFilename = 'versification.vrs'
        #versificationFilepath = os.path.join( self.sourceFilepath, versificationFilename )
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBible.loading versification from {}…".format( versificationFilepath ) )

        #DBLVersification = { 'VerseCounts':{}, 'Mappings':{}, 'Omitted':[] }

        #lineCount = 0
        #with open( versificationFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            #for line in vFile:
                #lineCount += 1
                #if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    #logging.info( "SFMLines: Detected Unicode Byte Order Marker (BOM) in {}".format( versificationFilename ) )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                #if not line: continue # Just discard blank lines
                #lastLine = line
                #if line[0]=='#' and not line.startswith('#!'): continue # Just discard comment lines
                ##print( "Versification line", repr(line) )

                #if len(line)<7:
                    #print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    #continue

                #if line.startswith( '#! -' ): # It's an excluded verse (or passage???)
                    #assert line[7] == ' '
                    #USFMBookCode = line[4:7]
                    #BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                    #C,V = line[8:].split( ':', 1 )
                    ##print( "CV", repr(C), repr(V) )
                    #if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                    ##print( "Omitted {} {}:{}".format( BBB, C, V ) )
                    #DBLVersification['Omitted'].append( (BBB,C,V) )
                #elif line[0] == '#': # It's a comment line
                    #pass # Just ignore it
                #elif '=' in line: # it's a verse mapping, e.g.,
                    #left, right = line.split( ' = ', 1 )
                    ##print( "left", repr(left), 'right', repr(right) )
                    #USFMBookCode1, USFMBookCode2 = left[:3], right[:3]
                    #BBB1 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode1 )
                    #BBB2 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode2 )
                    #DBLVersification['Mappings'][BBB1+left[3:]] = BBB2+right[3:]
                    ##print( DBLVersification['Mappings'] )
                #else: # It's a verse count line, e.g., LAM 1:22 2:22 3:66 4:22 5:22
                    #assert line[3] == ' '
                    #USFMBookCode = line[:3]
                    ##if USFMBookCode == 'ODA': USFMBookCode = 'ODE'
                    #try:
                        #BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                        #DBLVersification['VerseCounts'][BBB] = OrderedDict()
                        #for CVBit in line[4:].split():
                            ##print( "CVBit", repr(CVBit) )
                            #assert ':' in CVBit
                            #C,V = CVBit.split( ':', 1 )
                            ##print( "CV", repr(C), repr(V) )
                            #if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                            #DBLVersification['VerseCounts'][BBB][C] = V
                    #except KeyError:
                        #logging.error( "Unknown {!r} USX book code in DBLBible.loading versification from {}".format( USFMBookCode, versificationFilepath ) )

        ##print( '\n', self.suppliedMetadata['DBL'] )
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} versification elements.".format( len(DBLVersification) ) )
        #print( 'DBLVersification', DBLVersification ); halt
    ## end of DBLBible.loadDBLVersification


    #def loadDBLLanguage( self ):
        #"""
        #Load the something.lds file (which is an INI file) and parse it into the ordered dictionary DBLLanguage.
        #"""
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            #print( t("loadDBLLanguage()") )

        #languageFilenames = []
        #for something in os.listdir( self.sourceFilepath ):
            #somepath = os.path.join( self.sourceFilepath, something )
            #if os.path.isfile(somepath) and something.endswith('.lds'): languageFilenames.append( something )
        #if len(languageFilenames) > 1:
            #logging.error( "Got more than one language file: {}".format( languageFilenames ) )
        #languageFilename = languageFilenames[0]
        #languageName = languageFilename[:-4] # Remove the .lds

        #languageFilepath = os.path.join( self.sourceFilepath, languageFilename )
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "DBLBible.loading language from {}…".format( languageFilepath ) )

        #DBLLanguage = { 'Filename':languageName }

        #lineCount = 0
        #sectionName = None
        #with open( languageFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            #for line in vFile:
                #lineCount += 1
                #if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    #logging.info( "SFMLines: Detected Unicode Byte Order Marker (BOM) in {}".format( languageFilename ) )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                #if not line: continue # Just discard blank lines
                #lastLine = line
                #if line[0]=='#': continue # Just discard comment lines
                ##print( "line", repr(line) )

                #if len(line)<5:
                    #print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    #continue

                #if line[0]=='[' and line[-1]==']': # it's a new section name
                    #sectionName = line[1:-1]
                    #assert sectionName not in DBLLanguage
                    #DBLLanguage[sectionName] = {}
                #elif '=' in line: # it's a mapping, e.g., UpperCaseLetters=ABCDEFGHIJKLMNOPQRSTUVWXYZ
                    #left, right = line.split( '=', 1 )
                    ##print( "left", repr(left), 'right', repr(right) )
                    #DBLLanguage[sectionName][left] = right
                #else: print( "What's this language line? {!r}".format( line ) )

        ##print( '\n', DBLLanguage )
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} language sections.".format( len(DBLLanguage) ) )
        #print( 'DBLLanguage', DBLLanguage ); halt
    ## end of DBLBible.loadDBLLanguage


    def loadBooks( self ):
        """
        Load the USX XML Bible text files.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadBooks()") )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("DBLBible: Loading {} books from {}…").format( self.name, self.sourceFilepath ) )

        if not self.preloadDone: self.preload()

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: print( "ERROR: Not sure what '{}' is in {}!".format( somepath, self.sourceFilepath ) )
        if not foundFolders: # We need a USX folder
            print( "DBLBible.loadBooks: Couldn't find any folders in '{}'".format( self.sourceFilepath ) )
            return # No use continuing

        # Determine which is the USX subfolder
        possibilities = []
        haveDefault = False
        for someKey in self.suppliedMetadata['DBL']['contents']:
            if someKey.startswith( 'bookList' ): possibilities.append( someKey )
            if '(default)' in someKey: haveDefault = someKey
        #print( "possibilities", possibilities )
        bookListKey = haveDefault if haveDefault else possibilities[0]
        USXFolderName = 'USX_' + bookListKey[9:10]
        #print( "USXFolderName", USXFolderName )
        self.USXFolderPath = os.path.join( self.sourceFilepath, USXFolderName + '/' )

        ## Work out our filenames
        #self.USXFilenamesObject = USXFilenames( self.USXFolderPath )
        #print( "fo", self.USXFilenamesObject )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        #print( "bookListKey", bookListKey )
        for USFMBookCode in self.suppliedMetadata['DBL']['contents'][bookListKey]['books']:
            #print( "USFMBookCode", USFMBookCode )
            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
            filename = USFMBookCode + '.usx'
            UBB = USXXMLBibleBook( self, BBB )
            UBB.load( filename, self.USXFolderPath, self.encoding )
            UBB.validateMarkers()
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
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "DBLBible.loadBooks: Didn't find any regularly named USX files in '{}'".format( self.USXFolderPath ) )

        self.doPostLoadProcessing()
    # end of DBLBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class DBLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    testFolder = "Tests/DataFilesForTests/DBLTest/"

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = DBLBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DBL TestA1", result1 )
        result2 = DBLBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DBL TestA2", result2 )
        result3 = DBLBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "DBL TestA3", result3 )

    if 0: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDBL B/ Trying single module in {}".format( testFolder ) )
        XXXtestDBL_B( testFolder )

    if 1: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDBL C/ Trying installed {} module".format( singleModule ) )
        DBL_Bible = DBLBible( testFolder, singleModule )
        DBL_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in DBL_Bible:
                DBL_Bible.books[BBB].debugPrint()
                for entryKey in DBL_Bible.books[BBB]._CVIndex:
                    print( BBB, entryKey, DBL_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 1: # specified installed modules
        good = ('eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30',
                'eng-rv_dbl_40072c4a5aba4022-rev1-2014-09-24',
                'eng-webbe_dbl_7142879509583d59-rev2-2014-09-24',
                'engwmb_dbl_f72b840c855f362c-rev1-2014-09-24',
                'engwmbb_dbl_04da588535d2f823-rev1-2014-09-24',
                'ton_dbl_25210406001d9aae-rev2-2014-09-24',)
        nonEnglish = ( 'ton_dbl_25210406001d9aae-rev2-2014-09-24', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDBL D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            DBL_Bible = DBLBible( testFolder, testFilename )
            DBL_Bible.load()


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( DBLBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDBL E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                DBLBible( testFolder, someFolder )
    if 0:
        testFolders = (
                    "Tests/DataFilesForTests/DBLTest/",
                    ) # You can put your DBL test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = DBLBible( testFolder )
                DB.loadDBLMetadata()
                DB.preload()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                DB.loadBooks()
                #DBErrors = DB.getErrors()
                # print( DBErrors )
                #print( DB.getVersification () )
                #print( DB.getAddedUnits () )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    if 0:
        testFolders = (
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/acfDBL 2013-02-03",
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/aucDBL 2013-02-26",
                    ) # You can put your DBL test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = DBLBible( testFolder )
                DB.loadDBLBooksNames()
                #DB.preload()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                #DBErrors = DB.getErrors()
                # print( DBErrors )
                #print( DB.getVersification () )
                #print( DB.getAddedUnits () )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( ProgName, ProgVersion ) )
    #       pass

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of DBLBible.py
