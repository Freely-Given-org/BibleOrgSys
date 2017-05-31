#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PTX8Bible.py
#
# Module handling UBS/SIL Paratext (PTX 8) collections of USFM Bible books
#                                   along with XML and other metadata
#
# Copyright (C) 2015-2017 Robert Hunt
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
Module for defining and manipulating complete or partial Paratext 8 Bibles
    along with any enclosed metadata.

On typical Windows installations, Paratext 8 projects are in folders inside
    'C:\My Paratext 8 Projects' and contain the project settings information
    in a Settings.xml file inside that project folder.

The Paratext 8 Bible (PTX8Bible) object contains USFMBibleBooks.

The raw material for this module is produced by the UBS/SIL Paratext program
    if the File / Backup Project / To File… menu is used.

TODO: Check if PTX8Bible object should be based on USFMBible.
"""

from gettext import gettext as _

LastModifiedDate = '2017-06-01' # by RJH
ShortProgName = "Paratext8Bible"
ProgName = "Paratext-8 Bible handler"
ProgVersion = '0.12'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, os, logging
from collections import OrderedDict
import multiprocessing
from xml.etree.ElementTree import ElementTree
import json

import BibleOrgSysGlobals
from Bible import Bible
from USFMFilenames import USFMFilenames
from USFMBibleBook import USFMBibleBook



# NOTE: File names and extensions must all be UPPER-CASE
MARKER_FILENAMES = ( 'BOOKNAMES.XML', 'CHECKINGSTATUS.XML', 'COMMENTTAGS.XML', 'LICENSE.JSON',
                    'PROJECTPROGRESS.CSV', 'PROJECTPROGRESS.XML', 'PROJECTUSERACCESS.XML',
                    'SETTINGS.XML', 'TERMRENDERINGS.XML', 'UNIQUE.ID', 'WORDANALYSES.XML', )
EXCLUDE_FILENAMES = ( 'PROJECTUSERS.XML', 'PROJECTUSERFIELDS.XML', )
MARKER_FILE_EXTENSIONS = ( '.LDML', '.VRS', ) # Shouldn't be included in the above filenames lists
EXCLUDE_FILE_EXTENSIONS = ( '.SSF', '.LDS' ) # Shouldn't be included in the above filenames lists
MARKER_THRESHOLD = 6 # How many of the above must be found (after EXCLUDEs are subtracted)


def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



def getFlagFromAttribute( attributeName, attributeValue ):
    """
    Get a 'true' or 'false' string and convert to True/False.
    """
    if attributeValue == 'true': return True
    if attributeValue == 'false': return False
    logging.error( _("Unexpected {} attribute value of {}").format( attributeName, attributeValue ) )
    return attributeValue
# end of getFlagFromAttribute



def PTX8BibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Paratext Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one Paratext Bible bundle is found,
        returns the loaded PTX8Bible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "PTX8BibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag:
        assert givenFolderName and isinstance( givenFolderName, str )
        assert strictCheck in (True,False,)
        assert autoLoad in (True,False,)
        assert autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("PTX8BibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PTX8BibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Check that there's a USFM Bible here first
    from USFMBible import USFMBibleFileCheck
    if not USFMBibleFileCheck( givenFolderName, strictCheck ): # no autoloads
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PTX8BibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something == '__MACOSX': continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )

    # See if the compulsory files are here in this given folder
    numFound = numFilesFound = numFoldersFound = 0
    for filename in foundFiles:
        filenameUpper = filename.upper()
        if filenameUpper in MARKER_FILENAMES: numFilesFound += 1
        elif filenameUpper in EXCLUDE_FILENAMES: numFilesFound -= 2
        for extension in MARKER_FILE_EXTENSIONS:
            if filenameUpper.endswith( extension ): numFilesFound += 1; break
        for extension in EXCLUDE_FILE_EXTENSIONS:
            if filenameUpper.endswith( extension ): numFilesFound -= 2; break
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "numFilesFound1 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
    #for folderName in foundFolders:
        #if folderName.upper().startswith('USX_'): numFoldersFound += 1
    if numFilesFound >= MARKER_THRESHOLD: numFound += 1

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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX8BibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTX8Bible( givenFolderName )
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
            logging.warning( _("PTX8BibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PTX8BibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if the compulsory files are here in this given folder
        numFilesFound = numFoldersFound = 0
        for filename in foundFiles:
            filenameUpper = filename.upper()
            if filenameUpper in MARKER_FILENAMES: numFilesFound += 1
            elif filenameUpper in EXCLUDE_FILENAMES: numFilesFound -= 2
            for extension in MARKER_FILE_EXTENSIONS:
                if filenameUpper.endswith( extension ): numFilesFound += 1; break
            for extension in EXCLUDE_FILE_EXTENSIONS:
                if filenameUpper.endswith( extension ): numFilesFound -= 2; break
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "numFilesFound2 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
        #for folderName in foundSubfolders:
            #if folderName.upper().startswith('USX_'): numFoldersFound += 1
        if numFilesFound >= MARKER_THRESHOLD:
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX8BibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTX8Bible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            return dB
        return numFound
# end of PTX8BibleFileCheck



# The following loadPTX8…() functions are placed here because
#   they are also used by the DBL and/or other Bible importers
def loadPTX8ProjectData( BibleObject, settingsFilepath, encoding='utf-8' ):
    """
    Process the Paratext 8 project settings data file (XML) from the given filepath into PTXSettingsDict.

    Returns a dictionary.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( exp("Loading Paratext project settings data from {!r} ({})").format( settingsFilepath, encoding ) )
    #if encoding is None: encoding = 'utf-8'
    BibleObject.settingsFilepath = settingsFilepath

    PTXSettingsDict = {}

    settingsTree = ElementTree().parse( settingsFilepath )
    assert len( settingsTree ) # Fail here if we didn't load anything at all

    # Find the main container
    if settingsTree.tag=='ScriptureText':
        treeLocation = "PTX8 settings file"
        BibleOrgSysGlobals.checkXMLNoAttributes( settingsTree, treeLocation )
        BibleOrgSysGlobals.checkXMLNoText( settingsTree, treeLocation )
        BibleOrgSysGlobals.checkXMLNoTail( settingsTree, treeLocation )

        # Now process the actual entries
        for element in settingsTree:
            elementLocation = element.tag + ' in ' + treeLocation
            #print( "  Processing settings {}…".format( elementLocation ) )
            BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
            if element.tag == 'Naming':
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                prePart = postPart = bookNameForm = None
                for attrib,value in element.items():
                    if attrib=='PrePart': prePart = value
                    elif attrib=='PostPart': postPart = value
                    elif attrib=='BookNameForm': bookNameForm = value
                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                PTXSettingsDict[element.tag] = { 'PrePart':prePart, 'PostPart':postPart, 'BookNameForm':bookNameForm }
            else:
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                PTXSettingsDict[element.tag] = element.text

    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  " + exp("Got {} PTX8 settings entries:").format( len(PTXSettingsDict) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for key in sorted(PTXSettingsDict):
                print( "    {}: {}".format( key, PTXSettingsDict[key] ) )

    if debuggingThisModule: print( '\nPTX8SettingsDict', len(PTXSettingsDict), PTXSettingsDict )
    return PTXSettingsDict
# end of loadPTX8ProjectData



def loadPTX8Languages( BibleObject ):
    """
    Load the something.ldml file (which is an LDML file) and parse it into the dictionary PTXLanguages.

    LDML = Locale Data Markup Language (see http://unicode.org/reports/tr35/tr35-4.html)
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( exp("loadPTX8Languages()") )

    debuggingThisFunction = False

    urnPrefix = '{urn://www.sil.org/ldml/0.1}'
    lenUrnPrefix = len( urnPrefix )
    def removeSILPrefix( someText ):
        """
        Remove the SIL URN which might be prefixed to the element tag.
        """
        if someText and someText.startswith( urnPrefix ): return someText[lenUrnPrefix:]
        return someText
    # end of removeSILPrefix

    languageFilenames = []
    for something in os.listdir( BibleObject.sourceFilepath ):
        somepath = os.path.join( BibleObject.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.LDML'): languageFilenames.append( something )
    #if len(languageFilenames) > 1:
        #logging.error( "Got more than one language file: {}".format( languageFilenames ) )
    if not languageFilenames: return

    PTXLanguages = {}

    for languageFilename in languageFilenames:
        languageName = languageFilename[:-5] # Remove the .ldml

        languageFilepath = os.path.join( BibleObject.sourceFilepath, languageFilename )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading language from {}…".format( languageFilepath ) )

        assert languageName not in PTXLanguages
        PTXLanguages[languageName] = OrderedDict()

        languageTree = ElementTree().parse( languageFilepath )
        assert len( languageTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if languageTree.tag=='ldml':
            treeLocation = "PTX8 {} file for {}".format( languageTree.tag, languageName )
            BibleOrgSysGlobals.checkXMLNoAttributes( languageTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( languageTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( languageTree, treeLocation )

            # Now process the actual entries
            for element in languageTree:
                elementLocation = element.tag + ' in ' + treeLocation
                if debuggingThisFunction: print( "  Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                assert element.tag not in PTXLanguages[languageName]
                PTXLanguages[languageName][element.tag] = OrderedDict()

                if element.tag == 'identity':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'version':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            number = None
                            for attrib,value in subelement.items():
                                if attrib=='number': number = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = number
                        elif subelement.tag == 'generation':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            date = None
                            for attrib,value in subelement.items():
                                if attrib=='date': date = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = date
                        elif subelement.tag == 'language':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            lgType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': lgType = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = lgType
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                windowsLCID = None
                                for attrib,value in sub2element.items():
                                    if attrib=='windowsLCID': windowsLCID = value
                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                assert subelement.tag not in PTXLanguages[languageName][element.tag]
                                PTXLanguages[languageName][element.tag][subelement.tag] = (sub2element.tag,windowsLCID)
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

                elif element.tag == 'characters':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'exemplarCharacters':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            ecType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': ecType = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if subelement.tag not in PTXLanguages[languageName][element.tag]:
                                PTXLanguages[languageName][element.tag][subelement.tag] = []
                            PTXLanguages[languageName][element.tag][subelement.tag].append( (ecType,subelement.text) )
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                secType = None
                                for attrib,value in sub2element.items():
                                    if attrib=='type': secType = value
                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                if sub2element.tag not in PTXLanguages[languageName][element.tag][subelement.tag]:
                                    PTXLanguages[languageName][element.tag][subelement.tag][sub2element.tag] = []
                                PTXLanguages[languageName][element.tag][subelement.tag][sub2element.tag].append( (secType,sub2element.text) )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

                elif element.tag == 'delimiters':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag in ('quotationStart','quotationEnd','alternateQuotationStart','alternateQuotationEnd',):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = subelement.text
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = OrderedDict()
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                adjusted2Tag = removeSILPrefix( sub2element.tag )
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if adjusted2Tag not in PTXLanguages[languageName][element.tag]:
                                    PTXLanguages[languageName][element.tag][subelement.tag][adjusted2Tag] = {}
                                paraContinueType = None
                                for attrib,value in sub2element.items():
                                    #print( "here9", attrib, value )
                                    if attrib=='paraContinueType': paraContinueType = value
                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                for sub3element in sub2element:
                                    sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                    adjusted3Tag = removeSILPrefix( sub3element.tag )
                                    if debuggingThisFunction: print( "        Processing {}…".format( sub3elementLocation ) )
                                    #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation, "ABC" )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    openA = close = level = paraClose = pattern = context = qContinue = qType = None
                                    for attrib,value in sub3element.items():
                                        #print( attrib, value )
                                        if attrib=='open': openA = value
                                        elif attrib=='close': close = value
                                        elif attrib=='level':
                                            level = value
                                            if debuggingThisModule: assert level in '123'
                                        elif attrib=='paraClose':
                                            paraClose = value
                                            if debuggingThisModule: assert paraClose in ('false',)
                                        elif attrib=='pattern': pattern = value
                                        elif attrib=='context':
                                            context = value
                                            if debuggingThisModule: assert context in ('medial','final',)
                                        elif attrib=='continue':
                                            qContinue = value
                                        elif attrib=='type':
                                            qType = value
                                        else: logging.error( _("DS Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                    if adjusted3Tag not in PTXLanguages[languageName][element.tag][subelement.tag][adjusted2Tag]:
                                        PTXLanguages[languageName][element.tag][subelement.tag][adjusted2Tag][adjusted3Tag] = []
                                    PTXLanguages[languageName][element.tag][subelement.tag][adjusted2Tag][adjusted3Tag] \
                                            .append( (openA,close,level,paraClose,pattern,context,paraContinueType,qContinue,qType,sub3element.text) )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    #print( '\n', element.tag, PTXLanguages[languageName][element.tag] )

                elif element.tag == 'layout':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'orientation':
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                assert sub2element.tag not in PTXLanguages[languageName][element.tag][subelement.tag]
                                PTXLanguages[languageName][element.tag][subelement.tag][sub2element.tag] = sub2element.text
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

                elif element.tag == 'numbers':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                        if subelement.tag == 'defaultNumberingSystem':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag]  = subelement.text
                        elif subelement.tag == 'numberingSystem':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            nID = digits = nType = None
                            for attrib,value in subelement.items():
                                if attrib=='id': nID = value
                                elif attrib=='digits': digits = value
                                elif attrib=='type': nType = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = (nID,digits,nType)
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

                elif element.tag == 'collations':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'defaultCollation':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag]  = subelement.text
                        elif subelement.tag == 'collation':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in PTXLanguages[languageName][element.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag] = {}
                            cType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': cType = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            assert cType not in PTXLanguages[languageName][element.tag][subelement.tag]
                            PTXLanguages[languageName][element.tag][subelement.tag][cType] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag not in PTXLanguages[languageName][element.tag][subelement.tag][cType]:
                                    PTXLanguages[languageName][element.tag][subelement.tag][cType][sub2element.tag] = {}
                                for sub3element in sub2element:
                                    sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                    if debuggingThisFunction: print( "        Processing {}…".format( sub3elementLocation ) )
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    if sub3element.tag not in PTXLanguages[languageName][element.tag][subelement.tag][cType][sub2element.tag]:
                                        PTXLanguages[languageName][element.tag][subelement.tag][cType][sub2element.tag][sub3element.tag] = []
                                    PTXLanguages[languageName][element.tag][subelement.tag][cType][sub2element.tag][sub3element.tag].append( sub3element.text )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

                elif element.tag == 'special':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        if debuggingThisFunction: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                        assert subelement.tag not in PTXLanguages[languageName][element.tag]
                        if subelement.tag.endswith( 'external-resources' ):
                            adjustedTag = removeSILPrefix( subelement.tag )
                            PTXLanguages[languageName][element.tag][adjustedTag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                if debuggingThisFunction: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                name = None
                                for attrib,value in sub2element.items():
                                    #print( "here7", attrib, value )
                                    if attrib=='name': name = value
                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                assert name
                                if sub2element.tag not in PTXLanguages[languageName][element.tag][adjustedTag]:
                                    PTXLanguages[languageName][element.tag][adjustedTag][sub2element.tag] = []
                                PTXLanguages[languageName][element.tag][adjustedTag][sub2element.tag].append( name )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        else:
            logging.critical( _("Unrecognised PTX8 {} language settings tag: {}").format( languageName, languageTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  Loaded {} languages.".format( len(PTXLanguages) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for lgKey in PTXLanguages:
                print( "    {}:".format( lgKey ) )
                for key in PTXLanguages[lgKey]:
                    print( "      {}: ({}) {}".format( key, len(PTXLanguages[lgKey][key]), PTXLanguages[lgKey][key] ) )
    if debuggingThisModule: print( '\nPTX8Languages', len(PTXLanguages), PTXLanguages )
    return PTXLanguages
# end of PTX8Bible.loadPTX8Languages



def loadPTXVersifications( BibleObject ):
    """
    Load the versification files (which is a text file)
        and parse it into the dictionary PTXVersifications.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( exp("loadPTXVersifications()") )

    #versificationFilename = 'versification.vrs'
    #versificationFilepath = os.path.join( BibleObject.sourceFilepath, versificationFilename )
    #if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX8Bible.loading versification from {}…".format( versificationFilepath ) )

    #PTXVersifications = { 'VerseCounts':{}, 'Mappings':{}, 'Omitted':[] }

    versificationFilenames = []
    for something in os.listdir( BibleObject.sourceFilepath ):
        somepath = os.path.join( BibleObject.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.VRS'): versificationFilenames.append( something )
    #if len(versificationFilenames) > 1:
        #logging.error( "Got more than one versification file: {}".format( versificationFilenames ) )
    if not versificationFilenames: return

    PTXVersifications = {}

    for versificationFilename in versificationFilenames:
        versificationName = versificationFilename[:-4] # Remove the .vrs

        versificationFilepath = os.path.join( BibleObject.sourceFilepath, versificationFilename )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading versification from {}…".format( versificationFilepath ) )

        assert versificationName not in PTXVersifications
        PTXVersifications[versificationName] = {}

        lineCount = 0
        with open( versificationFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXVersifications: Detected Unicode Byte Order Marker (BOM) in {}".format( versificationFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#' and not line.startswith('#!'): continue # Just discard comment lines
                #print( versificationName, "versification line", repr(line) )

                if len(line)<7:
                    if debuggingThisModule: print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    continue

                if line.startswith( '#! -' ): # It's an excluded verse (or passage???)
                    assert line[7] == ' '
                    USFMBookCode = line[4:7]
                    BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                    C,V = line[8:].split( ':', 1 )
                    #print( "CV", repr(C), repr(V) )
                    if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                    #print( "Omitted {} {}:{}".format( BBB, C, V ) )
                    if 'Omitted' not in PTXVersifications[versificationName]:
                        PTXVersifications[versificationName]['Omitted'] = []
                    PTXVersifications[versificationName]['Omitted'].append( (BBB,C,V) )
                elif line[0] == '#': # It's a comment line
                    pass # Just ignore it
                elif line[0] == '-': # It's an excluded verse line -- similar to above
                    assert line[4] == ' '
                    USFMBookCode = line[1:4]
                    BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                    C,V = line[5:].split( ':', 1 )
                    #print( "CV", repr(C), repr(V) )
                    if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                    #print( "Omitted {} {}:{}".format( BBB, C, V ) )
                    if 'Omitted' not in PTXVersifications[versificationName]:
                        PTXVersifications[versificationName]['Omitted'] = []
                    PTXVersifications[versificationName]['Omitted'].append( (BBB,C,V) )
                elif '=' in line: # it's a verse mapping, e.g.,
                    left, right = line.split( ' = ', 1 )
                    #print( "left", repr(left), 'right', repr(right) )
                    USFMBookCode1, USFMBookCode2 = left[:3], right[:3]
                    BBB1 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode1 )
                    BBB2 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode2 )
                    if 'Mappings' not in PTXVersifications[versificationName]:
                        PTXVersifications[versificationName]['Mappings'] = {}
                    PTXVersifications[versificationName]['Mappings'][BBB1+left[3:]] = BBB2+right[3:]
                    #print( PTXVersifications[versificationName]['Mappings'] )
                else: # It's a verse count line, e.g., LAM 1:22 2:22 3:66 4:22 5:22
                    assert line[3] == ' '
                    USFMBookCode = line[:3]
                    #if USFMBookCode == 'ODA': USFMBookCode = 'ODE'
                    try:
                        BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                        if 'VerseCounts' not in PTXVersifications[versificationName]:
                            PTXVersifications[versificationName]['VerseCounts'] = {}
                        PTXVersifications[versificationName]['VerseCounts'][BBB] = OrderedDict()
                        for CVBit in line[4:].split():
                            #print( "CVBit", repr(CVBit) )
                            assert ':' in CVBit
                            C,V = CVBit.split( ':', 1 )
                            #print( "CV", repr(C), repr(V) )
                            if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                            PTXVersifications[versificationName]['VerseCounts'][BBB][C] = V
                    except KeyError:
                        logging.error( "Unknown {!r} USFM book code in loadPTXVersifications from {}".format( USFMBookCode, versificationFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} versifications.".format( len(PTXVersifications) ) )
    if debuggingThisModule: print( '\nPTXVersifications', len(PTXVersifications), PTXVersifications )
    return PTXVersifications
# end of PTX8Bible.loadPTXVersifications



class PTX8Bible( Bible ):
    """
    Class to load and manipulate Paratext Bible bundles.

    The PTX8Bible object contains USFMBibleBooks.
        (i.e., there's not PTX8BibleBook object types.)
    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal Paratext Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Paratext-8 Bible object'
        self.objectTypeString = 'PTX8'

        self.sourceFolder, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        if givenName:
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.error( "PTX8Bible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        else: self.sourceFilepath = self.sourceFolder
        if self.sourceFilepath and not os.access( self.sourceFilepath, os.R_OK ):
            logging.error( "PTX8Bible: Folder '{}' is unreadable".format( self.sourceFilepath ) )

        self.settingsFilepath = None

        # Create empty containers for loading the XML metadata files
        #projectUsersDict = self.PTXStyles = self.PTXVersification = self.PTXLanguage = None
    # end of PTX8Bible.__init__


    def preload( self ):
        """
        Loads the settings file if it can be found.
        Loads other metadata files that are provided.
        Tries to determine USFM filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("preload() from {}").format( self.sourceFolder ) )
            assert self.sourceFolder

        #if self.suppliedMetadata is None: self.suppliedMetadata = {}

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            #print( "PTX.preload something", repr(something) )
            #somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something ) # Adds even .BAK files, but result is not used much anyway!
            else: logging.error( exp("preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in ('__MACOSX'): continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( exp("preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( exp("preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['PTX8'] = {}

        if self.settingsFilepath is None: # it might have been loaded first
            # Attempt to load the settings file
            #self.suppliedMetadata, self.settingsDict = {}, {}
            settingsFilepath = os.path.join( self.sourceFolder, 'Settings.xml' )
            #print( "settingsFilepath", settingsFilepath )
            PTXSettingsDict = loadPTX8ProjectData( self, settingsFilepath )
            if PTXSettingsDict:
                self.suppliedMetadata['PTX8']['Settings'] = PTXSettingsDict
                self.applySuppliedMetadata( 'PTX8' ) # Copy some to self.settingsDict

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "USFM Bible"

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.availableBBBs.add( BBB )
            self.possibleFilenameDict[BBB] = filename

        if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            # Load the paratext metadata (and stop if any of them fail)
            self.loadPTXBooksNames() # from XML (if it exists)
            self.loadPTX8ProjectUserAccess() # from XML (if it exists)
            self.loadPTXLexicon() # from XML (if it exists)
            self.loadPTXSpellingStatus() # from XML (if it exists)
            self.loadPTXWordAnalyses() # from XML (if it exists)
            self.loadPTXCheckingStatus() # from XML (if it exists)
            self.loadPTXComments() # from XML (if they exist)
            self.loadPTXCommentTags() # from XML (if they exist)
            self.loadPTXTermRenderings() # from XML (if they exist)
            self.loadPTXProgress() # from XML (if it exists)
            self.loadPTXPrintConfig()  # from XML (if it exists)
            self.loadPTXAutocorrects() # from text file (if it exists)
            self.loadPTXStyles() # from text files (if they exist)
            result = loadPTXVersifications( self ) # from text file (if it exists)
            if result: self.suppliedMetadata['PTX8']['Versifications'] = result
            result = loadPTX8Languages( self ) # from INI file (if it exists)
            if result: self.suppliedMetadata['PTX8']['Languages'] = result
            self.loadPTX8Licence() # from JSON file (if it exists)
        else: # normal operation
            # Put all of these in try blocks so they don't crash us if they fail
            try: self.loadPTXBooksNames() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXBooksNames failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8ProjectUserAccess() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ProjectUserAccess failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXLexicon() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXLexicon failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXSpellingStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXSpellingStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            self.loadPTXWordAnalyses() # from XML (if it exists)
            #except Exception as err: logging.error( 'loadPTXWordAnalyses failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXCheckingStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXCheckingStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXComments() # from XML (if they exist) but we don't do the CommentTags.xml file yet
            except Exception as err: logging.error( 'loadPTXComments failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXCommentTags() # from XML (if they exist)
            except Exception as err: logging.error( 'loadPTXCommentTags failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXTermRenderings() # from XML (if they exist)
            except Exception as err: logging.error( 'loadPTXTermRenderings failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXProgress() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXProgress failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXPrintConfig() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXPrintConfig failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXAutocorrects() # from text file (if it exists)
            except Exception as err: logging.error( 'loadPTXAutocorrects failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXStyles() # from text files (if they exist)
            except Exception as err: logging.error( 'loadPTXStyles failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                result = loadPTXVersifications( self ) # from text file (if it exists)
                if result: self.suppliedMetadata['PTX8']['Versifications'] = result
            except Exception as err: logging.error( 'loadPTXVersifications failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                result = loadPTX8Languages( self ) # from INI file (if it exists)
                if result: self.suppliedMetadata['PTX8']['Languages'] = result
            except Exception as err: logging.error( 'loadPTX8Languages failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Licence() # from JSON file (if it exists)
            except Exception as err: logging.error( 'loadPTX8Licence failed with {} {}'.format( sys.exc_info()[0], err ) )

        self.preloadDone = True
    # end of PTX8Bible.preload


    def loadPTXBooksNames( self ):
        """
        Load the BookNames.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXBooksNames()") )

        bookNamesFilepath = os.path.join( self.sourceFilepath, 'BookNames.xml' )
        if not os.path.exists( bookNamesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading books names data from {}…".format( bookNamesFilepath ) )
        self.tree = ElementTree().parse( bookNamesFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        booksNamesDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='BookNames':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            # Now process the actual book data
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                if element.tag == 'book':
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                    bnCode = bnAbbr = bnShort = bnLong = None
                    for attrib,value in element.items():
                        if attrib=='code': bnCode = value
                        elif attrib=='abbr': bnAbbr = value
                        elif attrib=='short': bnShort = value
                        elif attrib=='long': bnLong = value
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    #print( bnCode, booksNamesDict[bnCode] )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert len(bnCode)==3
                    try: BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( bnCode )
                    except:
                        logging.warning( "loadPTXBooksNames can't find BOS code for PTX8 {!r} book".format( bnCode ) )
                        BBB = bnCode # temporarily use their code
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert BBB not in booksNamesDict
                    booksNamesDict[BBB] = (bnCode,bnAbbr,bnShort,bnLong,)
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 bookname settings tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} book names.".format( len(booksNamesDict) ) )
        if debuggingThisModule: print( "\nbooksNamesDict", len(booksNamesDict), booksNamesDict )
        if booksNamesDict: self.suppliedMetadata['PTX8']['BooksNames'] = booksNamesDict
    # end of PTX8Bible.loadPTXBooksNames


    def loadPTX8ProjectUserAccess( self ):
        """
        Load the ProjectUsers.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTX8ProjectUserAccess()") )

        projectUsersFilepath = os.path.join( self.sourceFilepath, 'ProjectUserAccess.xml' )
        if not os.path.exists( projectUsersFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading project user data from {}…".format( projectUsersFilepath ) )
        self.tree = ElementTree().parse( projectUsersFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        projectUsersDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='ProjectUserAccess':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            # Process the attributes first
            peerSharingFlag = None
            for attrib,value in self.tree.items():
                if attrib=='PeerSharing': peerSharingFlag = getFlagFromAttribute( attrib, value )
                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            projectUsersDict['PeerSharingFlag'] = peerSharingFlag

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'User':
                    # Process the user attributes first
                    userName = firstUserFlag = unregisteredUserFlag = None
                    for attrib,value in element.items():
                        if attrib=='UserName': userName = value
                        elif attrib=='FirstUser': firstUserFlag = getFlagFromAttribute( attrib, value )
                        elif attrib=='UnregisteredUser': unregisteredUserFlag = getFlagFromAttribute( attrib, value )
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if 'Users' not in projectUsersDict: projectUsersDict['Users'] = {}
                    assert userName not in projectUsersDict['Users'] # no duplicates allowed presumably
                    projectUsersDict['Users'][userName] = {}
                    projectUsersDict['Users'][userName]['FirstUserFlag'] = firstUserFlag
                    projectUsersDict['Users'][userName]['UnregisteredUserFlag'] = unregisteredUserFlag

                    for subelement in element:
                        sublocation = subelement.tag + ' in ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )

                        if subelement.tag in ('Role', 'AllBooks', ):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in projectUsersDict['Users'][userName]
                            projectUsersDict['Users'][userName][subelement.tag] = subelement.text
                        elif subelement.tag in ('Books','AutomaticBooks',):
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            if subelement.tag not in projectUsersDict['Users'][userName]:
                                projectUsersDict['Users'][userName][subelement.tag] = []
                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' in ' + sublocation
                                #print( "  Processing {}…".format( sub2location ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                if sub2element.tag == 'Book':
                                    bookID = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='Id': bookID = value
                                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    projectUsersDict['Users'][userName][subelement.tag].append( bookID )
                                else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                        elif subelement.tag in ('Permissions','AutomaticPermissions',):
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            if subelement.tag not in projectUsersDict['Users'][userName]:
                                projectUsersDict['Users'][userName][subelement.tag] = {}
                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' in ' + sublocation
                                #print( "  Processing {}…".format( sub2location ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                if sub2element.tag == 'Permission':
                                    permissionType = grantedFlag = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='Type':
                                            permissionType = value
                                            if debuggingThisModule:
                                                assert permissionType in ('TermsList','Renderings','Spellings','Passages','Progress',)
                                        elif attrib=='Granted': grantedFlag = getFlagFromAttribute( attrib, value )
                                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    projectUsersDict['Users'][userName][subelement.tag][permissionType] = grantedFlag
                                else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 project users settings tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(projectUsersDict['Users']) ) )
        if debuggingThisModule:
            #print( "\nprojectUsersDict", len(projectUsersDict), projectUsersDict )
            for somekey in projectUsersDict:
                if somekey == 'Users':
                    for userKey in projectUsersDict['Users']: print( '\n   User', userKey, projectUsersDict['Users'][userKey] )
                else: print( '\n  ', somekey, projectUsersDict[somekey] )
        if projectUsersDict: self.suppliedMetadata['PTX8']['ProjectUsers'] = projectUsersDict
    # end of PTX8Bible.loadPTX8ProjectUserAccess


    def loadPTXLexicon( self ):
        """
        Load the Lexicon.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXLexicon()") )

        lexiconFilepath = os.path.join( self.sourceFilepath, 'Lexicon.xml' )
        if not os.path.exists( lexiconFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading project lexicon data from {}…".format( lexiconFilepath ) )
        self.tree = ElementTree().parse( lexiconFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        lexiconDict = { 'Entries':{} }
        #loadErrors = []

        def processLexiconItem( element, treeLocation ):
            """
            """
            #print( "processLexiconItem()" )

            # Now process the actual items
            for subelement in element:
                elementLocation = subelement.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )

                # Now process the subelements
                if subelement.tag == 'Lexeme':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, elementLocation )
                    # Process the attributes
                    lexemeType = lexemeForm = lexemeHomograph = None
                    for attrib,value in subelement.items():
                        if attrib=='Type': lexemeType = value
                        elif attrib=='Form': lexemeForm = value
                        elif attrib=='Homograph': lexemeHomograph = value
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                    #print( "Lexeme {} form={!r} homograph={}".format( lexemeType, lexemeForm, lexemeHomograph ) )
                    assert lexemeType in ( 'Word', 'Phrase', 'Stem', )
                    if lexemeType not in lexiconDict['Entries']: lexiconDict['Entries'][lexemeType] = {}
                    assert lexemeForm not in lexiconDict['Entries'][lexemeType]
                    lexiconDict['Entries'][lexemeType][lexemeForm] = { 'Homograph':lexemeHomograph, 'senseIDs':{} }
                elif subelement.tag == 'Entry': # Can't see any reason to save this level
                    BibleOrgSysGlobals.checkXMLNoText( subelement, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, elementLocation )
                    for sub2element in subelement:
                        sublocation = sub2element.tag + ' in ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        if sub2element.tag == 'Sense':
                            BibleOrgSysGlobals.checkXMLNoText( sub2element, sublocation )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sublocation )
                            # Process the attributes first
                            senseID = None
                            for attrib,value in sub2element.items():
                                if attrib=='Id': senseID = value
                                else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            #print( 'senseID={!r}'.format( senseID ) )
                            assert senseID and senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs']
                            for sub3element in sub2element:
                                sub2location = sub3element.tag + ' in ' + sublocation
                                #print( "    Processing {}…".format( sub2location ) )
                                if sub3element.tag == 'Gloss':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub2location )
                                    # Process the attributes first
                                    glossLanguage = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='Language': glossLanguage = value
                                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub2location ) )
                                assert senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs']
                                lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'][senseID] = (sub3element.text, glossLanguage)
                        else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, elementLocation ) )
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
        # end of processLexiconItem


        # Find the main container
        if self.tree.tag == 'Lexicon':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.tree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            #lexiconDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )

                # Now process the subelements
                if element.tag in ( 'Language', 'FontName', 'FontSize', ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                    lexiconDict[element.tag] = element.text
                elif element.tag == 'Analyses':
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                elif element.tag == 'Entries':
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                    for subelement in element:
                        sublocation = subelement.tag + ' in ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        if subelement.tag == 'item':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                            processLexiconItem( subelement, sublocation )
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 lexicon tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2:
            totalEntries = 0
            for lType in lexiconDict['Entries']: totalEntries += len( lexiconDict['Entries'][lType] )
            print( "  Loaded {} lexicon types ({:,} total entries).".format( len(lexiconDict['Entries']), totalEntries ) )
        if debuggingThisModule: print( "\nlexiconDict", len(lexiconDict), lexiconDict )
        if lexiconDict: self.suppliedMetadata['PTX8']['Lexicon'] = lexiconDict
    # end of PTX8Bible.loadPTXLexicon


    def loadPTXSpellingStatus( self ):
        """
        Load the SpellingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXSpellingStatus()") )

        spellingStatusFilepath = os.path.join( self.sourceFilepath, 'SpellingStatus.xml' )
        if not os.path.exists( spellingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading spelling status data from {}…".format( spellingStatusFilepath ) )
        self.tree = ElementTree().parse( spellingStatusFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        spellingStatusDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag == 'SpellingStatus':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.tree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            #spellingStatusDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Status':
                    # Process the user attributes first
                    word = state = None
                    for attrib,value in element.items():
                        if attrib=='Word': word = value
                        elif attrib=='State': state = value
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    assert word not in spellingStatusDict # no duplicates allowed presumably
                    spellingStatusDict[word] = {}
                    spellingStatusDict[word]['State'] = state

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag in ( 'SpecificCase', 'Correction', ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in spellingStatusDict[word]
                            spellingStatusDict[word][subelement.tag] = subelement.text
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 spelling tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} spelling status entries.".format( len(spellingStatusDict) ) )
        if debuggingThisModule: print( "\nspellingStatusDict", len(spellingStatusDict), spellingStatusDict )
        if spellingStatusDict: self.suppliedMetadata['PTX8']['SpellingStatus'] = spellingStatusDict
    # end of PTX8Bible.loadPTXSpellingStatus


    def loadPTXCheckingStatus( self ):
        """
        Load the CheckingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXCheckingStatus()") )

        checkingStatusFilepath = os.path.join( self.sourceFilepath, 'CheckingStatus.xml' )
        if not os.path.exists( checkingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading checking status data from {}…".format( checkingStatusFilepath ) )
        self.tree = ElementTree().parse( checkingStatusFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        checkingStatusByBookDict, checkingStatusByCheckDict = OrderedDict(), OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag == 'CheckingStatuses':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.tree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            #checkingStatusDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'CheckingStatus':
                    tempDict = OrderedDict()
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag in ( 'BookName', 'Check', 'MD5', 'Date', 'Errors', 'DeniedErrors', ):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in tempDict
                            tempDict[subelement.tag] = subelement.text
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    assert tempDict and 'BookName' in tempDict and 'Check' in tempDict
                    bn, chk = tempDict['BookName'], tempDict['Check']
                    del tempDict['BookName'], tempDict['Check']
                    if bn not in checkingStatusByBookDict: checkingStatusByBookDict[bn] = {}
                    if chk not in checkingStatusByCheckDict: checkingStatusByCheckDict[chk] = {}
                    assert chk not in checkingStatusByBookDict[bn] # Duplicates not expected
                    checkingStatusByBookDict[bn][chk] = tempDict
                    assert bn not in checkingStatusByCheckDict[chk] # Duplicates not expected
                    checkingStatusByCheckDict[chk][bn] = tempDict # Saved both ways
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 checking tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  Loaded {:,} checking status books.".format( len(checkingStatusByBookDict) ) )
            print( "  Loaded {:,} checking status checks.".format( len(checkingStatusByCheckDict) ) )
        if debuggingThisModule:
            print( "\ncheckingStatusByBookDict", len(checkingStatusByBookDict), checkingStatusByBookDict )
            print( "\ncheckingStatusByCheckDict", len(checkingStatusByCheckDict), checkingStatusByCheckDict )
        #for something in checkingStatusDict:
            #print( "\n  {} = {}".format( something, checkingStatusDict[something] ) )
        if checkingStatusByBookDict: self.suppliedMetadata['PTX8']['CheckingStatusByBook'] = checkingStatusByBookDict
        if checkingStatusByCheckDict: self.suppliedMetadata['PTX8']['CheckingStatusByCheck'] = checkingStatusByCheckDict
    # end of PTX8Bible.loadPTXCheckingStatus


    def loadPTXWordAnalyses( self ):
        """
        Load the WordAnalyses.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXWordAnalyses()") )

        wordAnalysesFilepath = os.path.join( self.sourceFilepath, 'WordAnalyses.xml' )
        if not os.path.exists( wordAnalysesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading word analysis data from {}…".format( wordAnalysesFilepath ) )
        self.tree = ElementTree().parse( wordAnalysesFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        wordAnalysesDict = OrderedDict()
        #loadErrors = []


        def processWordAnalysis( word, element, treeLocation ):
            """
            """
            #print( "processWordAnalysis( {} )".format( word ) )

            analysisDict = {}

            # Now process the actual items
            for subelement in element:
                elementLocation = subelement.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, elementLocation )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, elementLocation )

                # Now process the subelements
                if subelement.tag == 'Lexeme':
                    assert subelement.tag not in analysisDict
                    analysisDict[subelement.tag] = subelement.text
                else:
                    logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, elementLocation ) )
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
            return analysisDict
        # end of processWordAnalysis


        # Find the main container
        if self.tree.tag == 'WordAnalyses':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Entry':
                    # Process the user attributes first
                    word = None
                    for attrib,value in element.items():
                        if attrib=='Word': word = value
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    assert word not in wordAnalysesDict # no duplicates allowed presumably
                    #wordAnalysesDict[word] = {}

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag == 'Analysis':
                            #assert subelement.tag not in wordAnalysesDict[word]
                            assert word not in wordAnalysesDict
                            wordAnalysesDict[word] = processWordAnalysis( word, subelement, sublocation )
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 spelling tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} spelling status entries.".format( len(wordAnalysesDict) ) )
        if debuggingThisModule: print( "\nwordAnalysesDict", len(wordAnalysesDict), wordAnalysesDict )
        if wordAnalysesDict: self.suppliedMetadata['PTX8']['WordAnalyses'] = wordAnalysesDict
    # end of PTX8Bible.loadPTXWordAnalyses



    def loadPTXComments( self ):
        """
        Load the Comments_*.xml files (if they exist) and parse them into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXComments()") )

        commentFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('COMMENTS_') and somethingUPPER.endswith('.XML'):
                commentFilenames.append( something )
        #if len(commentFilenames) > 1:
            #logging.error( "Got more than one comment file: {}".format( commentFilenames ) )
        if not commentFilenames: return

        commentsList = {}
        #loadErrors = []

        for commentFilename in commentFilenames:
            commenterName = commentFilename[9:-4] # Remove the .xml
            assert commenterName not in commentsList
            commentsList[commenterName] = []

            commentFilepath = os.path.join( self.sourceFilepath, commentFilename )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "PTX8Bible.loading comments from {}…".format( commentFilepath ) )

            self.tree = ElementTree().parse( commentFilepath )
            assert len( self.tree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.tree.tag == 'CommentList':
                treeLocation = "PTX8 {} file for {}".format( self.tree.tag, commenterName )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

                ## Process the attributes first
                #peerSharing = None
                #for attrib,value in self.tree.items():
                    #if attrib=='PeerSharing': peerSharing = value
                    #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                #commentsList['PeerSharing'] = peerSharing

                # Now process the actual entries
                for element in self.tree:
                    elementLocation = element.tag + ' in ' + treeLocation
                    #print( "Processing {}…".format( elementLocation ) )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                    # Now process the subelements
                    if element.tag == 'Comment':
                        commentDict = {}
                        ## Process the user attributes first
                        #word = state = None
                        #for attrib,value in element.items():
                            #if attrib=='Word': word = value
                            #elif attrib=='State': state = value
                            #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                        #if 'SpellingWords' not in commentsList: commentsList = {}
                        #assert word not in commentsList # no duplicates allowed presumably

                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                            assert subelement.tag not in commentDict # No duplicates please
                            if subelement.tag in ( 'Thread', 'User', 'Date', 'VerseRef', 'SelectedText', 'StartPosition', 'ContextBefore', 'ContextAfter', 'Status', 'Type' ):
                                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                                commentDict[subelement.tag] = subelement.text # can be None
                            elif subelement.tag == 'Contents':
                                contentsText = ''
                                if subelement.text: contentsText += subelement.text.lstrip()
                                for sub2element in subelement:
                                    sub2location = sub2element.tag + ' ' + sublocation
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                    if sub2element.text:
                                        contentsText += '<{}>{}</{}>'.format( sub2element.tag, sub2element.text, sub2element.tag )
                                    else: contentsText += '<{}/>'.format( sub2element.tag )
                                #print( 'contentsText', repr(contentsText) )
                                commentDict[subelement.tag] = contentsText
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    #print( "commentDict", commentDict )
                    commentsList[commenterName].append( commentDict )
            else:
                logging.critical( _("Unrecognised PTX8 {} comment list tag: {}").format( commenterName, self.tree.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} commenters.".format( len(commentsList) ) )
        if debuggingThisModule: print( "\ncommentsList", len(commentsList), commentsList )
        # Call this 'PTXComments' rather than just 'Comments' which might just be a note on the particular version
        if commentsList: self.suppliedMetadata['PTX8']['PTXComments'] = commentsList
    # end of PTX8Bible.loadPTXComments


    def loadPTXCommentTags( self ):
        """
        Load the CommentTags_*.xml files (if they exist) and parse them into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXCommentTags()") )

        commentTagFilepath = os.path.join( self.sourceFilepath, 'CommentTags.xml' )
        if not os.path.exists( commentTagFilepath ): return

        commentTagDict = {}
        #loadErrors = []

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading comment tags from {}…".format( commentTagFilepath ) )

        self.tree = ElementTree().parse( commentTagFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.tree.tag == 'TagList':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Tag':
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    # Process the tag attributes
                    Id = name = icon = creatorResolveFlag = None
                    for attrib,value in element.items():
                        if attrib=='Id': Id = value
                        elif attrib=='Name': name = value
                        elif attrib=='Icon': icon = value
                        elif attrib=='CreatorResolve': creatorResolveFlag = getFlagFromAttribute( attrib, value )
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    commentTagDict[element.tag] = { 'Id':Id, 'Name':name, 'Icon':icon, 'CreatorResolve':creatorResolveFlag }
                elif element.tag == 'LastUsedID':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    commentTagDict[element.tag] = element.text
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unrecognised PTX8 comment tag list tag: {}").format( self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} comment tags.".format( len(commentTagDict) ) )
        if debuggingThisModule: print( "\ncommentTagDict", len(commentTagDict), commentTagDict )
        if commentTagDict: self.suppliedMetadata['PTX8']['CommentTags'] = commentTagDict
    # end of PTX8Bible.loadPTXCommentTags


    def loadPTXTermRenderings( self ):
        """
        Load the TermRenderings*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXTermRenderings()") )

        renderingTermsFilepath = os.path.join( self.sourceFilepath, 'TermRenderings.xml' )
        if not os.path.exists( renderingTermsFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading TermRenderings from {}…".format( renderingTermsFilepath ) )

        TermRenderingsDict = OrderedDict()

        self.tree = ElementTree().parse( renderingTermsFilepath )
        assert len( self.tree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.tree.tag == 'TermRenderingsList':
            treeLocation = "PTX8 {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

            # Now process the actual entries
            for element in self.tree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the elements
                termRenderingEntryDict = {}
                if element.tag == 'TermRendering':
                    Id =  guessFlag = None
                    for attrib,value in element.items():
                        if attrib=='Id': Id = value
                        elif attrib=='Guess': guessFlag = getFlagFromAttribute( attrib, value )
                        else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    termRenderingEntryDict['guessFlag'] = guessFlag

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        assert element.tag not in termRenderingEntryDict # No duplicates please
                        if subelement.tag in ( 'Tag', 'Notes', 'Changes', 'Glossary', ):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            termRenderingEntryDict[subelement.tag] = subelement.text # can be None
                        elif subelement.tag == 'Renderings':
                            # This seems to be a string containing a comma separated list!
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            termRenderingEntryDict[subelement.tag] = subelement.text.split( ', ' ) if subelement.text else None
                        #elif subelement.tag == 'Notes':
                            #termRenderingEntryDict[subelement.tag] = []
                            #for sub2element in subelement:
                                #sub2location = sub2element.tag + ' ' + sublocation
                                #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                #termRenderingEntryDict[subelement.tag].append( sub2element.text )
                        elif subelement.tag == 'Denials':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            termRenderingEntryDict[subelement.tag] = None
                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' ' + sublocation
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                if termRenderingEntryDict[subelement.tag] == None:
                                    termRenderingEntryDict[subelement.tag] = []
                                #if sub2element.tag == 'VerseRef':
                                    ## Process the VerseRef attributes first
                                    #versification = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='Versification': versification = value
                                        #else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    #termRenderingEntryDict[subelement.tag].append( (sub2element.text,versification) )
                                if sub2element.tag == 'Denial':
                                    termRenderingEntryDict[subelement.tag].append ( (sub2element.tag,sub2element.text) )
                                else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                #print( "termRenderingEntryDict", termRenderingEntryDict ); halt
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else: logging.error( _("Unprocessed {} element '{}' in {}").format( element.tag, element.text, elementLocation ) )
                #print( "termRenderingEntryDict", termRenderingEntryDict )
                assert Id not in TermRenderingsDict # No duplicate ids allowed
                TermRenderingsDict[Id] = termRenderingEntryDict
                #print( "termRenderingEntryDict", termRenderingEntryDict ); halt
        else:
            logging.critical( _("Unrecognised PTX8 {} term renderings tag: {}").format( versionName, self.tree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} term renderings.".format( len(TermRenderingsDict) ) )
        if debuggingThisModule: print( "\nTermRenderingsDict", len(TermRenderingsDict), TermRenderingsDict )
        #print( TermRenderingsDict['חָנוּן'] )
        if TermRenderingsDict: self.suppliedMetadata['PTX8']['TermRenderings'] = TermRenderingsDict
    # end of PTX8Bible.loadPTXTermRenderings


    def loadPTXProgress( self ):
        """
        Load the Progress*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXProgress()") )

        progressFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('PROGRESS') and somethingUPPER.endswith('.XML'):
                progressFilenames.append( something )
        #if len(progressFilenames) > 1:
            #logging.error( "Got more than one progress file: {}".format( progressFilenames ) )
        if not progressFilenames: return

        progressDict = {}
        #loadErrors = []

        for progressFilename in progressFilenames:
            versionName = progressFilename[8:-4] # Remove the .xml
            assert versionName not in progressDict
            progressDict[versionName] = {}

            progressFilepath = os.path.join( self.sourceFilepath, progressFilename )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "PTX8Bible.loading Progress from {}…".format( progressFilepath ) )

            self.tree = ElementTree().parse( progressFilepath )
            assert len( self.tree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.tree.tag=='ProjectProgress':
                treeLocation = "PTX8 {} file for {}".format( self.tree.tag, versionName )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

                # Now process the actual entries
                for element in self.tree:
                    elementLocation = element.tag + ' in ' + treeLocation
                    #print( "Processing {}…".format( elementLocation ) )

                    # Now process the subelements
                    if element.tag in ( 'ProgressBase', 'GetTextStage', 'ScrTextName' ):
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        assert element.tag not in progressDict[versionName] # Detect duplicates
                        progressDict[versionName][element.tag] = element.text
                    elif element.tag == 'StageNames':
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        assert element.tag not in progressDict[versionName] # Detect duplicates
                        progressDict[versionName][element.tag] = []
                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            if subelement.tag == 'string':
                                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                                progressDict[versionName][element.tag].append( subelement.text )
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    elif element.tag == 'PlannedBooks':
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            if subelement.tag == 'Books':
                                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                                assert element.tag not in progressDict[versionName] # Detect duplicates
                                progressDict[versionName][element.tag] = subelement.text
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    elif element.tag == 'BookStatusList':
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        assert 'BookStatusDict' not in progressDict[versionName]
                        progressDict[versionName]['BookStatusDict'] = {}
                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            bookStatusDict = {}
                            if subelement.tag == 'BookStatus':
                                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                                # Process the BookStatus attributes first
                                bookNumber = None
                                for attrib,value in subelement.items():
                                    if attrib=='BookNum': bookNumber = value
                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                                assert 'BookNumber' not in bookStatusDict
                                bookStatusDict['BookNumber'] = bookNumber
                                for sub2element in subelement:
                                    sub2location = sub2element.tag + ' ' + sublocation
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                    assert subelement.tag not in bookStatusDict # No duplicates please
                                    if sub2element.tag in ( 'Versification', 'Summaries' ):
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                        bookStatusDict[sub2element.tag] = sub2element.text # can be None
                                    elif sub2element.tag == 'StageStatus':
                                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                        assert sub2element.tag not in bookStatusDict
                                        bookStatusDict[sub2element.tag] = []
                                        for sub3element in sub2element:
                                            sub3location = sub3element.tag + ' ' + sub2location
                                            if sub3element.tag == 'VerseSet':
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                                # Process the VerseSet attributes first
                                                references = None
                                                for attrib,value in sub3element.items():
                                                    if attrib=='References': references = value
                                                    else: logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                                bookStatusDict[sub2element.tag].append( (references,sub3element.text) )
                                            else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                    elif sub2element.tag == 'VersesPerDay':
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                        assert sub2element.tag not in bookStatusDict
                                        bookStatusDict[sub2element.tag] = []
                                        for sub3element in sub2element:
                                            sub3location = sub3element.tag + ' ' + sub2location
                                            if sub3element.tag == 'int':
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                                bookStatusDict[sub2element.tag].append( sub3element.text )
                                            else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                    elif sub2element.tag == 'StageContents':
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                        assert sub2element.tag not in bookStatusDict
                                        bookStatusDict[sub2element.tag] = []
                                        for sub3element in sub2element:
                                            sub3location = sub3element.tag + ' ' + sub2location
                                            if sub3element.tag == 'BookStageContents':
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                                BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                                bookStageContentsList = []
                                                for sub4element in sub3element:
                                                    sub4location = sub4element.tag + ' ' + sub3location
                                                    if sub4element.tag == 'ChapterHead':
                                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location )
                                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                                        chapterHeadList = []
                                                        for sub5element in sub4element:
                                                            sub5location = sub5element.tag + ' ' + sub4location
                                                            if sub5element.tag == 'string':
                                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5location )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5location )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5location )
                                                                chapterHeadList.append( sub5element.text )
                                                            else: logging.error( _("Unprocessed {} sub5element '{}' in {}").format( sub5element.tag, sub5element.text, sub5location ) )
                                                        bookStageContentsList.append( chapterHeadList )
                                                    else: logging.error( _("Unprocessed {} sub4element '{}' in {}").format( sub4element.tag, sub4element.text, sub4location ) )
                                                bookStatusDict[sub2element.tag].append( bookStageContentsList )
                                            else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                    else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            #print( "bookStatusDict", bookStatusDict )
                            bookNumber = bookStatusDict['BookNumber']
                            del bookStatusDict['BookNumber']
                            progressDict[versionName]['BookStatusDict'][bookNumber] = bookStatusDict
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    #print( "bookStatusDict", bookStatusDict )
                    #progressDict[versionName].append( bookStatusDict )
            else:
                logging.critical( _("Unrecognised PTX8 {} project progress tag: {}").format( versionName, self.tree.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} progress.".format( len(progressDict) ) )
        if debuggingThisModule: print( "\nprogressDict", len(progressDict), progressDict )
        if progressDict: self.suppliedMetadata['PTX8']['Progress'] = progressDict
    # end of PTX8Bible.loadPTXProgress


    def loadPTXPrintConfig( self ):
        """
        Load the PrintConfig*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXPrintConfig()") )

        printConfigFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('PRINT') and somethingUPPER.endswith('.XML'):
                printConfigFilenames.append( something )
        #if len(printConfigFilenames) > 1:
            #logging.error( "Got more than one printConfig file: {}".format( printConfigFilenames ) )
        if not printConfigFilenames: return

        printConfigDict = {}
        #loadErrors = []

        for printConfigFilename in printConfigFilenames:
            printConfigType = printConfigFilename[5:-4] # Remove the .xml
            assert printConfigType not in printConfigDict
            printConfigDict[printConfigType] = {}

            printConfigFilepath = os.path.join( self.sourceFilepath, printConfigFilename )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "PTX8Bible.loading PrintConfig from {}…".format( printConfigFilepath ) )

            self.tree = ElementTree().parse( printConfigFilepath )
            assert len( self.tree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.tree.tag == 'PrintDraftConfiguration':
                treeLocation = "PTX8 {} file for {}".format( self.tree.tag, printConfigType )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.tree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.tree, treeLocation )

                # Now process the actual entries
                for element in self.tree:
                    elementLocation = element.tag + ' in ' + treeLocation
                    #print( "Processing {}…".format( elementLocation ) )

                    # Now process the subelements
                    if element.tag in ( 'Stylesheet', 'PaperWidth', 'PaperHeight', 'MarginUnit', 'TopMarginFactor',
                                    'BottomMarginFactor', 'SideMarginFactor', 'TitleColumns', 'IntroColumns',
                                    'BodyColumns', 'LineSpacing', 'LineSpacingFactor', 'FontSize', 'FontSizeUnit',
                                    'FontRegular', 'FontRegularFace', 'FontBold', 'FontBoldFace', 'FontItalic',
                                    'FontItalicFace', 'FontBoldItalic', 'FontBoldItalicFace', 'ScriptName',
                                    'LangID', 'CombineBooks', 'JustifyParagraphs', 'Hyphenate', 'Remark',
                                    'HeaderPosition', 'FooterPosition', 'HeaderInside', 'HeaderCenter',
                                    'HeaderOutside', 'HeaderMirrorLayout', 'HeaderIncludeVerseRefs', 'IncludeFigures',
                                    'FigurePath', 'DigitStyle', 'ChooseBooks', 'OneBook', 'PrintedBooks', 'TextBooks',
                                    'FirstChapterSelectedIndex', 'LastChapterSelectedIndex', 'LastChapterCount',
                                    'FirstChapterText', 'LastChapterText', 'HyphenPenalty', 'XetexFontStylefontRegular',
                                    'XetexFontStylefontBold', 'XetexFontStylefontItalic', 'XetexFontBoldItalic' ):
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        assert element.tag not in printConfigDict[printConfigType] # Detect duplicates
                        printConfigDict[printConfigType][element.tag] = element.text
                    elif element.tag == 'SelectedBooks':
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            if subelement.tag == 'Books':
                                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                                assert element.tag not in printConfigDict[printConfigType] # Detect duplicates
                                printConfigDict[printConfigType][element.tag] = subelement.text
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    #print( "bookStatusDict", bookStatusDict )
                    #printConfigDict[printConfigType].append( bookStatusDict )
            else:
                logging.critical( _("Unrecognised PTX8 {} print configuration tag: {}").format( printConfigType, self.tree.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} printConfig.".format( len(printConfigDict) ) )
        if debuggingThisModule: print( "\nprintConfigDict", len(printConfigDict), printConfigDict )
        if printConfigDict: self.suppliedMetadata['PTX8']['PrintConfig'] = printConfigDict
    # end of PTX8Bible.loadPTXPrintConfig


    def loadPTXAutocorrects( self ):
        """
        Load the AutoCorrect.txt file (which is a text file)
            and parse it into the ordered dictionary PTXAutocorrects.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXAutocorrects()") )

        autocorrectFilename = 'AutoCorrect.txt'
        autocorrectFilepath = os.path.join( self.sourceFilepath, autocorrectFilename )
        if not os.path.exists( autocorrectFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading autocorrect from {}…".format( autocorrectFilepath ) )
        PTXAutocorrects = {}

        lineCount = 0
        with open( autocorrectFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXAutocorrects: Detected Unicode Byte Order Marker (BOM) in {}".format( autocorrectFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "Autocorrect line", repr(line) )

                if len(line)<4:
                    print( "Why was autocorrect line #{} so short? {!r}".format( lineCount, line ) )
                    continue
                if len(line)>6:
                    print( "Why was autocorrect line #{} so long? {!r}".format( lineCount, line ) )

                if '-->' in line:
                    bits = line.split( '-->', 1 )
                    #print( 'bits', bits )
                    PTXAutocorrects[bits[0]] = bits[1]
                else: logging.error( "Invalid {!r} autocorrect line in PTX8Bible.loading autocorrect".format( line ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} autocorrect elements.".format( len(PTXAutocorrects) ) )
        if debuggingThisModule: print( '\nPTXAutocorrects', len(PTXAutocorrects), PTXAutocorrects )
        if PTXAutocorrects: self.suppliedMetadata['PTX8']['Autocorrects'] = PTXAutocorrects
    # end of PTX8Bible.loadPTXAutocorrects


    def loadPTXStyles( self ):
        """
        Load the something.sty file (which is a SFM file) and parse it into the dictionary PTXStyles.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTXStyles()") )

        styleFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and something.upper().endswith('.STY'): styleFilenames.append( something )
        #if len(styleFilenames) > 1:
            #logging.error( "Got more than one style file: {}".format( styleFilenames ) )
        if not styleFilenames: return

        PTXStyles = {}

        for styleFilename in styleFilenames:
            styleName = styleFilename[:-4] # Remove the .sty

            styleFilepath = os.path.join( self.sourceFilepath, styleFilename )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "PTX8Bible.loading style from {}…".format( styleFilepath ) )

            assert styleName not in PTXStyles
            PTXStyles[styleName] = {}

            lineCount = 0
            encodings = ['utf-8', 'ISO-8859-1', 'ISO-8859-2', 'ISO-8859-15']
            currentStyle = {}
            for encoding in encodings: # Start by trying the given encoding
                try:
                    with open( styleFilepath, 'rt', encoding=encoding ) as vFile: # Automatically closes the file when done
                        for line in vFile:
                            lineCount += 1
                            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                                logging.info( "loadPTXStyles: Detected Unicode Byte Order Marker (BOM) in {}".format( styleFilename ) )
                                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            if not line: continue # Just discard blank lines
                            lastLine = line
                            if line[0]=='#': continue # Just discard comment lines
                            #print( lineCount, "line", repr(line) )

                            if len(line)<5: # '\Bold' is the shortest valid line
                                logging.warning( "Why was PTX8 style line #{} so short? {!r}".format( lineCount, line ) )
                                continue

                            if line[0] == '\\':
                                bits = line[1:].split( ' ', 1 )
                                #print( "style bits", bits )
                                name, value = bits[0], bits[1] if len(bits)==2 else None
                                if name == 'Marker':
                                    if currentStyle:
                                        assert styleMarker not in PTXStyles
                                        PTXStyles[styleName][styleMarker] = currentStyle
                                        currentStyle = {}
                                    styleMarker = value
                                elif name in ( 'Name', 'Description', 'OccursUnder', 'Rank', 'StyleType', 'Endmarker', 'SpaceBefore', 'SpaceAfter', 'LeftMargin', 'RightMargin', 'FirstLineIndent', 'TextType', 'TextProperties', 'Justification', 'FontSize', 'Bold', 'Italic', 'Smallcaps', 'Superscript', 'Underline', 'Color', 'color', ):
                                    if name == 'color': name = 'Color' # fix inconsistency
                                    if name in currentStyle: # already
                                        logging.error( "loadPTXStyles found duplicate {!r}={!r} in {} {} at line #{}".format( name, value, styleName, styleMarker, lineCount ) )
                                    currentStyle[name] = value
                                else: logging.error( "What's this style marker? {!r}".format( line ) )
                            else: logging.error( "What's this style line? {!r}".format( line ) )
                    break; # Get out of decoding loop because we were successful
                except UnicodeDecodeError:
                    logging.error( _("loadPTXStyles fails with encoding: {} on {}{}").format( encoding, styleFilepath, {} if encoding==encodings[-1] else ' -- trying again' ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} style files.".format( len(PTXStyles) ) )
        if debuggingThisModule: print( '\nPTXStyles', len(PTXStyles), PTXStyles )
        if PTXStyles: self.suppliedMetadata['PTX8']['Styles'] = PTXStyles
    # end of PTX8Bible.loadPTXStyles


    def loadPTX8Licence( self ):
        """
        Load the license.json file and parse it into the dictionary.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("loadPTX8Licence()") )

        licenceFilename = 'license.json'
        licenceFilepath = os.path.join( self.sourceFilepath, licenceFilename )
        if not os.path.exists( licenceFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading PTX8 licence from {}…".format( licenceFilepath ) )

        with open( licenceFilepath, 'rt', encoding='utf-8' ) as lFile: # Automatically closes the file when done
            licenceString = lFile.read()
        #print( "licenceString", licenceString )
        if licenceString[0]==chr(65279): #U+FEFF
            logging.info( "loadPTX8Licence: Detected Unicode Byte Order Marker (BOM) in {}".format( licenceFilename ) )
            licenceString = licenceString[1:] # Remove the Unicode Byte Order Marker (BOM)
        jsonData = json.loads( licenceString )
        #print( "jsonData", jsonData )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule: assert isinstance( jsonData, dict )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} licence elements.".format( len(jsonData) ) )
        if debuggingThisModule: print( '\nPTX8Licence', len(jsonData), jsonData )
        if jsonData: self.suppliedMetadata['PTX8']['Licence'] = jsonData
    # end of PTX8Bible.loadPTX8Licence


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "PTX8Bible.loadBook( {}, {} )".format( BBB, filename ) )

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  PTX8Bible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "PTX8Bible.loadBook: Unable to find file for {}".format( BBB ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.stashBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
        self.bookNeedsReloading[BBB] = False
    # end of PTX8Bible.loadBook


    def _loadBookMP( self, BBB_Filename ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( exp("loadBookMP( {} )").format( BBB_Filename ) )

        BBB, filename = BBB_Filename
        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return self.books[BBB] # Already loaded
        #if BBB in self.triedLoadingBook:
            #logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            #return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( '  ' + exp("Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of PTX8Bible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( exp("Loading {} from {}…").format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( exp("Loading {} PTX8 books using {} CPUs…").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  PTX8Bible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    #if BBB not in self.books:
                    self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( exp("No books to load in {}!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of PTX8Bible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class PTX8Bible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in ( 'Tests/DataFilesForTests/USFMTest1/',
                            'Tests/DataFilesForTests/USFMTest2/',
                            'Tests/DataFilesForTests/USFMTest3/',
                            'Tests/DataFilesForTests/USFMAllMarkersProject/',
                            'Tests/DataFilesForTests/USFMErrorProject/',
                            'Tests/DataFilesForTests/PTX7Test/',
                            'Tests/DataFilesForTests/PTX8Test1/',
                            'Tests/DataFilesForTests/PTX8Test2/',
                            '../../../../../Data/Work/Matigsalug/Bible/MBTV/',
                            'OutputFiles/BOS_USFM_Export/',
                            'OutputFiles/BOS_USFM_Reexport/',
                            'MadeUpFolder/',
                            ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nTestfolder is: {}".format( testFolder ) )
            result1 = PTX8BibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA1", result1 )
            result2 = PTX8BibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA2", result2 )
            result3 = PTX8BibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA3", result3 )

    testFolder = 'Tests/DataFilesForTests/PTX8Test2/'
    if 0: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 B/ Trying single module in {}".format( testFolder ) )
        PTX_Bible = PTX8Bible( testFolder )
        PTX_Bible.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )

    if 0: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 C/ Trying installed {} module".format( singleModule ) )
        PTX_Bible = PTX8Bible( testFolder, singleModule )
        PTX_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in PTX_Bible:
                PTX_Bible.books[BBB].debugPrint()
                for entryKey in PTX_Bible.books[BBB]._CVIndex:
                    print( BBB, entryKey, PTX_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 0: # specified installed modules
        good = ( '',)
        nonEnglish = ( '', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            PTX_Bible = PTX8Bible( testFolder, testFilename )
            PTX_Bible.load()


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
                results = pool.map( PTX8Bible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                PTX8Bible( testFolder, someFolder )
    if 1:
        testFolders = (
                    'Tests/DataFilesForTests/PTX8Test1/',
                    'Tests/DataFilesForTests/PTX8Test2/',
                    '../../../../../Data/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTV',
                    '../../../../../Data/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTBT',
                    '../../../../../Data/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTBC',
                    ) # You can put your PTX8 test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTX8Bible( testFolder )
                PTX_Bible.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )
                if BibleOrgSysGlobals.strictCheckingFlag: PTX_Bible.check()
                #DBErrors = PTX_Bible.getErrors()
                # print( DBErrors )
                #print( PTX_Bible.getVersification () )
                #print( PTX_Bible.getAddedUnits () )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )

                # Test BDB code for display PTX8 metadata files
                import sys; sys.path.append( '../../../../../../home/autoprocesses/Scripts/' )
                from ProcessUploadFunctions import doGlobalTemplateFixes
                from ProcessTemplates import webPageTemplate
                readyWebPageTemplate = doGlobalTemplateFixes( 'Matigsalug', 'MBTV', "Test", webPageTemplate )
                from ProcessLoadedBible import makeSettingsPage
                outputFolderPath = 'OutputFiles/BDBSettingsPages/'
                if not os.path.exists( outputFolderPath ):
                        os.makedirs( outputFolderPath, 0o755 )
                makeSettingsPage( 'Matigsalug', PTX_Bible, readyWebPageTemplate, outputFolderPath )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    if 0:
        testFolders = (
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/acfPTX 2013-02-03",
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/aucPTX 2013-02-26",
                    ) # You can put your PTX8 test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTX8Bible( testFolder )
                PTX_Bible.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )
                if BibleOrgSysGlobals.strictCheckingFlag: PTX_Bible.check()
                #DBErrors = PTX_Bible.getErrors()
                # print( DBErrors )
                #print( PTX_Bible.getVersification () )
                #print( PTX_Bible.getAddedUnits () )
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
# end of PTX8Bible.py
