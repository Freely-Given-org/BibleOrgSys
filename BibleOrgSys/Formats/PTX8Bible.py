#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PTX8Bible.py
#
# Module handling UBS/SIL Paratext (PTX 8) collections of USFM Bible books
#                                   along with XML and other metadata
#
# Copyright (C) 2015-2019 Robert Hunt
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

The Paratext 8 Bible (PTX8Bible) object contains USFM 2 or 3 BibleBooks.

The raw material for this module is produced by the UBS/SIL Paratext program
    if the File / Backup Project / To File… menu is used.

TODO: Check if PTX8Bible object should be based on USFMBible.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-16' # by RJH
SHORT_PROGRAM_NAME = "Paratext8Bible"
PROGRAM_NAME = "Paratext-8 Bible handler"
PROGRAM_VERSION = '0.27'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import sys
import os
import logging
import multiprocessing
from xml.etree.ElementTree import ElementTree
import json

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible
from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames
from BibleOrgSys.Formats.USFMBibleBook import USFMBibleBook
from BibleOrgSys.Reference.LDML import LDMLFile



# NOTE: File names and extensions must all be UPPER-CASE
MARKER_FILENAMES = ( 'BOOKNAMES.XML', 'CHECKINGSTATUS.XML', 'COMMENTTAGS.XML',
                    'DERIVEDTRANSLATIONSTATUS.XML', 'LICENSE.JSON', 'PARALLELPASSAGESTATUS.XML',
                    'PROJECTPROGRESS.CSV', 'PROJECTPROGRESS.XML', 'PROJECTUSERACCESS.XML',
                    'SETTINGS.XML', 'TERMRENDERINGS.XML', 'UNIQUE.ID', 'WORDANALYSES.XML', )
EXCLUDE_FILENAMES = ( 'PROJECTUSERS.XML', 'PROJECTUSERFIELDS.XML', )
MARKER_FILE_EXTENSIONS = ( '.LDML', '.VRS', ) # Shouldn't be included in the above filenames lists
EXCLUDE_FILE_EXTENSIONS = ( '.SSF', '.LDS' ) # Shouldn't be included in the above filenames lists
MARKER_THRESHOLD = 6 # How many of the above must be found (after EXCLUDEs are subtracted)
# NOTE: Folder names must be exact case -- used to give warnings if additional folders are found
EXPECTED_FOLDER_NAMES = ( 'Figures', 'PrintDraft', 'Interlinear_en', 'shared', # PTX8 folders
                         '.hg', 'cache', 'store', 'data', 'gather', '_interlinear___english', '_interlinear__en', '_print_draft', # Mercurial sub-folders
                         ) # but these aren't compulsory


def PTX8BibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Paratext Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one Paratext Bible bundle is found,
        returns the loaded PTX8Bible object.
    """
    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( f"PTX8BibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
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
    from BibleOrgSys.Formats.USFM2Bible import USFM2BibleFileCheck
    from BibleOrgSys.Formats.USFMBible import USFMBibleFileCheck
    check2Result = USFM2BibleFileCheck( givenFolderName, strictCheck, discountSSF=True ) # no autoloads
    if not check2Result:
        check3Result =  USFMBibleFileCheck( givenFolderName, strictCheck, discountSSF=True ) # no autoloads
    if not check2Result and not check3Result:
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print("PTX8BibleFileCheck: No USFMBible found (preliminary check)")
        return False

    # Find all the files and folders in this folder
    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
        print( f" PTX8BibleFileCheck: Looking for files in given {givenFolderName}" )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
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
        print( "PTX8 numFilesFound1 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
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
        for filename in foundSubfiles:
            filenameUpper = filename.upper()
            if filenameUpper in MARKER_FILENAMES: numFilesFound += 1
            elif filenameUpper in EXCLUDE_FILENAMES: numFilesFound -= 2
            for extension in MARKER_FILE_EXTENSIONS:
                if filenameUpper.endswith( extension ): numFilesFound += 1; break
            for extension in EXCLUDE_FILE_EXTENSIONS:
                if filenameUpper.endswith( extension ): numFilesFound -= 2; break
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "PTX8 numFilesFound2 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
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



def getFlagFromAttribute( attributeName, attributeValue ):
    """
    Get a 'true' or 'false' string and convert to True/False.
    """
    if attributeValue == 'true': return True
    if attributeValue == 'false': return False
    logging.error( _("Unexpected {} attribute value of {}").format( attributeName, attributeValue ) )
    return attributeValue
# end of getFlagFromAttribute

def getFlagFromText( subelement ):
    """
    Get a 'true' or 'false' string and convert to True/False.
    """
    if subelement.text == 'true': return True
    if subelement.text == 'false': return False
    logging.error( _("Unexpected {} text value of {}").format( subelement.tag, subelement.text ) )
    return subelement.text
# end of getFlagFromText



# The following loadPTX8…() functions are placed here because
#   they are also used by the DBL and/or other Bible importers
def loadPTX8ProjectData( BibleObject, sourceFolder, encoding='utf-8' ):
    """
    Process the Paratext 8 project settings data file (XML) from the given filepath into PTXSettingsDict.

    Returns a dictionary.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "Loading Paratext project settings data from {!r} ({})".format( sourceFolder, encoding ) )

    #if encoding is None: encoding = 'utf-8'
    BibleObject.sourceFolder = BibleObject.sourceFilepath = sourceFolder
    settingsFilepath = os.path.join( BibleObject.sourceFolder, 'Settings.xml' )
    #print( "settingsFilepath", settingsFilepath )
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
                    else:
                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                PTXSettingsDict[element.tag] = { 'PrePart':prePart, 'PostPart':postPart, 'BookNameForm':bookNameForm }
            else:
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                PTXSettingsDict[element.tag] = element.text

    try: BibleObject.filepathsNotYetLoaded.remove( settingsFilepath )
    except ValueError: logging.critical( "PTX8 settings file seemed unexpected: {}".format( settingsFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  " + "Got {} PTX8 settings entries:".format( len(PTXSettingsDict) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for key in sorted(PTXSettingsDict):
                print( "    {}: {}".format( key, PTXSettingsDict[key] ) )

    if debuggingThisModule: print( '\nPTX8SettingsDict', len(PTXSettingsDict), PTXSettingsDict )
    return PTXSettingsDict
# end of loadPTX8ProjectData



def loadPTX8Languages( BibleObject ):
    """
    Load the something.ldml files (which are LDML XML files) and parse them into the dictionary PTXLanguages.

    LDML = Locale Data Markup Language (see http://unicode.org/reports/tr35/tr35-4.html)
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "loadPTX8Languages()" )

    languageFilenames = []
    for something in os.listdir( BibleObject.sourceFilepath ):
        somepath = os.path.join( BibleObject.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.LDML'): languageFilenames.append( something )
    #if len(languageFilenames) > 1:
        #logging.error( "Got more than one language file: {}".format( languageFilenames ) )
    if not languageFilenames: return

    PTXLanguages = {}

    for languageFilename in languageFilenames:
        assert languageFilename.endswith( '.ldml' )
        languageName = languageFilename[:-5] # Remove the .ldml
        assert languageName not in PTXLanguages

        languageFilepath = os.path.join( BibleObject.sourceFilepath, languageFilename )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading language from {}…".format( languageFilepath ) )

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            thisLDMLFile = LDMLFile( BibleObject.sourceFilepath, languageFilename )
            PTXLanguages[languageName] = thisLDMLFile.load()
        else:
            try:
                thisLDMLFile = LDMLFile( BibleObject.sourceFilepath, languageFilename )
                PTXLanguages[languageName] = thisLDMLFile.load()
            except Exception as err:
                logging.error( 'LDMLFile load of {} failed with {} {}' \
                                    .format( languageFilename, sys.exc_info()[0], err ) )

        try: BibleObject.filepathsNotYetLoaded.remove( languageFilepath )
        except ValueError: logging.critical( "PTX8 language file seemed unexpected: {}".format( languageFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  Loaded {} languages.".format( len(PTXLanguages) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for lgKey in PTXLanguages:
                print( "    {}:".format( lgKey ) )
                for key in PTXLanguages[lgKey]:
                    print( "      {}: ({}) {}".format( key, len(PTXLanguages[lgKey][key]), PTXLanguages[lgKey][key] ) )
    elif debuggingThisModule: print( '\nPTX8Languages', len(PTXLanguages), PTXLanguages )
    return PTXLanguages
# end of PTX8Bible.loadPTX8Languages



def loadPTX8Versifications( BibleObject ):
    """
    Load the versification files (which is a text file)
        and parse it into the dictionary PTXVersifications.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "loadPTX8Versifications()" )

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
                    logging.info( "loadPTX8Versifications: Detected Unicode Byte Order Marker (BOM) in {}".format( versificationFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
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
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
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
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
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
                    BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode1 )
                    BBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode2 )
                    if 'Mappings' not in PTXVersifications[versificationName]:
                        PTXVersifications[versificationName]['Mappings'] = {}
                    PTXVersifications[versificationName]['Mappings'][BBB1+left[3:]] = BBB2+right[3:]
                    #print( PTXVersifications[versificationName]['Mappings'] )
                else: # It's a verse count line, e.g., LAM 1:22 2:22 3:66 4:22 5:22
                    assert line[3] == ' '
                    USFMBookCode = line[:3]
                    #if USFMBookCode == 'ODA': USFMBookCode = 'ODE'
                    try:
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                        if 'VerseCounts' not in PTXVersifications[versificationName]:
                            PTXVersifications[versificationName]['VerseCounts'] = {}
                        PTXVersifications[versificationName]['VerseCounts'][BBB] = {}
                        for CVBit in line[4:].split():
                            #print( "CVBit", repr(CVBit) )
                            assert ':' in CVBit
                            C,V = CVBit.split( ':', 1 )
                            #print( "CV", repr(C), repr(V) )
                            if BibleOrgSysGlobals.debugFlag: assert C.isdigit() and V.isdigit()
                            PTXVersifications[versificationName]['VerseCounts'][BBB][C] = V
                    except KeyError:
                        logging.error( "Unknown {!r} USFM book code in loadPTX8Versifications from {}".format( USFMBookCode, versificationFilepath ) )

        try: BibleObject.filepathsNotYetLoaded.remove( versificationFilepath )
        except ValueError: logging.critical( "PTX8 versification file seemed unexpected: {}".format( versificationFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} versifications.".format( len(PTXVersifications) ) )
    if debuggingThisModule: print( '\nPTXVersifications', len(PTXVersifications), PTXVersifications )
    return PTXVersifications
# end of PTX8Bible.loadPTX8Versifications



class PTX8Bible( Bible ):
    """
    Class to load and manipulate Paratext Bible bundles.

    The PTX8Bible object contains USFM 2 or 3 BibleBooks.
        (i.e., there's not PTX8BibleBook object types.)
    """
    def __init__( self, givenFolderName, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Create the internal Paratext Bible object.
        """
        if debuggingThisModule:
            print( "PTX8Bible.__init__( {!r}, {!r}, {!r}, {!r} )".format( givenFolderName, givenName, givenAbbreviation, encoding ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Paratext-8 Bible object'
        self.objectTypeString = 'PTX8'

        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = givenFolderName, givenName, givenAbbreviation, encoding # Remember our parameters

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
        #print( "self.sourceFolder", self.sourceFolder )
        #print( "self.sourceFilepath", self.sourceFilepath )

        self.settingsFilepath = None
        self.filepathsNotYetLoaded = []
        self.conflicts = []

        # Create empty containers for loading the XML metadata files
        #projectUsersDict = self.PTXStyles = self.PTXVersification = self.PTXLanguage = None
    # end of PTX8Bible.__init__


    def preload( self ):
        """
        Loads the settings file if it can be found.
        Loads other metadata files that are provided.
        Tries to determine USFM filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "preload() from {}".format( self.sourceFolder ) )
            assert self.sourceFolder

        #if self.suppliedMetadata is None: self.suppliedMetadata = {}

        def recurseFolder( folderPath, level=1 ):
            """
            """
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( ('  '*level) + "recurseFolder( {}, {} )".format( folderPath, level ) )
            for something in os.listdir( folderPath ):
                somethingUPPER = something.upper()
                somepath = os.path.join( folderPath, something )
                if os.path.isfile( somepath ):
                    foundFiles.append( something ) # Adds even .BAK files, but result is not used much anyway!
                    if not somethingUPPER.endswith( '.BAK' ):
                        self.filepathsNotYetLoaded.append( somepath )
                elif os.path.isdir( somepath ):
                    foundFolders.append( something )
                    recurseFolder( somepath, level+1 ) # recursive call
                else: logging.error( "preload: Not sure what {!r} is in {}!".format( somepath, self.sourceFolder ) )
        # end of preload recurseFolder

        # Main code for preload
        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        recurseFolder( self.sourceFolder )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                #if folderName.startswith( 'Interlinear_'): continue
                #if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS: continue
                if folderName not in EXPECTED_FOLDER_NAMES:
                    unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.warning( _("PTX8 preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "preload: Couldn't find any files in {!r}".format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['PTX8'] = {}

        if self.settingsFilepath is None: # it might have been loaded first
            # Attempt to load the settings file
            #self.suppliedMetadata, self.settingsDict = {}, {}
            PTXSettingsDict = loadPTX8ProjectData( self, self.sourceFolder )
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

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            # Load the paratext metadata (and stop if any of them fail)
            self.loadPTX8Autocorrects() # from text file (if it exists)
            self.loadPTX8BooksNames() # from XML (if it exists)
            self.loadPTX8Canons() # from XML (if it exists)
            self.loadPTX8CheckingStatus() # from XML (if it exists)
            self.loadPTX8CommentTags() # from XML (if they exist)
            self.loadPTX8DerivedTranslationStatus() # from XML (if it exists)
            result = loadPTX8Languages( self ) # from LDML file(s)
            if result: self.suppliedMetadata['PTX8']['Languages'] = result
            self.loadPTX8Lexicon() # from XML (if it exists)
            self.loadPTX8Licence() # from JSON file (if it exists)
            self.loadPTX8Notes() # from XML (if they exist)
            self.loadPTX8TermRenderings() # from XML (if they exist)
            self.loadPTX8ParallelPassageStatus() # from XML (if it exists)
            self.loadPTX8ProjectBiblicalTerms() # from XML (if it exists)
            self.loadPTX8ProjectProgress() # from XML (if it exists)
            self.loadPTX8ProjectProgressCSV() # from text file (if it exists)
            self.loadPTX8ProjectUserAccess() # from XML (if it exists)
            self.loadPTX8PrintConfig()  # from XML (if it exists)
            self.loadPTX8SpellingStatus() # from XML (if it exists)
            self.loadPTX8Styles() # from text files (if they exist)
            self.loadPTX8PrintDraftChanges() # from text file (if it exists)
            self.loadUniqueId() # Text file
            result = loadPTX8Versifications( self ) # from text file (if it exists)
            if result: self.suppliedMetadata['PTX8']['Versifications'] = result
            self.loadPTX8WordAnalyses() # from XML (if it exists)
        else: # normal operation
            # Put all of these in try blocks so they don't crash us if they fail
            try: self.loadUniqueId() # Text file
            except Exception as err: logging.error( 'loadUniqueId failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8BooksNames() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8BooksNames failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8ProjectUserAccess() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ProjectUserAccess failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                result = loadPTX8Languages( self ) # from LDML file(s)
                if result: self.suppliedMetadata['PTX8']['Languages'] = result
            except Exception as err: logging.error( 'loadPTX8Languages failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Lexicon() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8Lexicon failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8SpellingStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8SpellingStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8WordAnalyses() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8WordAnalyses failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Canons() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8Canons failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8CheckingStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8CheckingStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8CommentTags() # from XML (if they exist)
            except Exception as err: logging.error( 'loadPTX8CommentTags failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8DerivedTranslationStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8DerivedTranslationStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Notes() # from XML (if they exist) but we don't do the CommentTags.xml file yet
            except Exception as err: logging.error( 'loadPTX8Notes failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8TermRenderings() # from XML (if they exist)
            except Exception as err: logging.error( 'loadPTX8TermRenderings failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:self.loadPTX8ParallelPassageStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ParallelPassageStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:self.loadPTX8ProjectBiblicalTerms() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ProjectBiblicalTerms failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:self.loadPTX8ProjectProgress() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ProjectProgress failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:self.loadPTX8ProjectProgressCSV() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8ProjectProgressCSV failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8PrintConfig() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX8PrintConfig failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Autocorrects() # from text file (if it exists)
            except Exception as err: logging.error( 'loadPTX8Autocorrects failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Styles() # from text files (if they exist)
            except Exception as err: logging.error( 'loadPTX8Styles failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8PrintDraftChanges() # from text files (if they exist)
            except Exception as err: logging.error( 'loadPTX8PrintDraftChanges failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                result = loadPTX8Versifications( self ) # from text file (if it exists)
                if result: self.suppliedMetadata['PTX8']['Versifications'] = result
            except Exception as err: logging.error( 'loadPTX8Versifications failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTX8Licence() # from JSON file (if it exists)
            except Exception as err: logging.error( 'loadPTX8Licence failed with {} {}'.format( sys.exc_info()[0], err ) )

        self.preloadDone = True
    # end of PTX8Bible.preload


    def loadPTX8Autocorrects( self ):
        """
        Load the AutoCorrect.txt file (which is a text file)
            and parse it into the ordered dictionary PTXAutocorrects.

        These lines use --> as the main operator.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Autocorrects()" )

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
                    logging.info( "loadPTX8Autocorrects: Detected Unicode Byte Order Marker (BOM) in {}".format( autocorrectFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "Autocorrect line", repr(line) )

                if BibleOrgSysGlobals.verbosityLevel > 0:
                    if len(line)<4:
                        print( "Why was PTX8 autocorrect line #{} so short? {!r}".format( lineCount, line ) )
                        continue
                    if len(line)>6:
                        print( "Why was PTX8 autocorrect line #{} so long? {!r}".format( lineCount, line ) )

                if '-->' in line:
                    bits = line.split( '-->', 1 )
                    #print( 'bits', bits )
                    PTXAutocorrects[bits[0]] = bits[1]
                else: logging.error( "Invalid {!r} autocorrect line in PTX8Bible.loading autocorrect".format( line ) )

        try: self.filepathsNotYetLoaded.remove( autocorrectFilepath )
        except ValueError: logging.critical( "PTX8 autocorrect file seemed unexpected: {}".format( autocorrectFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} autocorrect elements.".format( len(PTXAutocorrects) ) )
        if debuggingThisModule: print( '\nPTXAutocorrects', len(PTXAutocorrects), PTXAutocorrects )
        if PTXAutocorrects: self.suppliedMetadata['PTX8']['Autocorrects'] = PTXAutocorrects
    # end of PTX8Bible.loadPTX8Autocorrects


    def loadPTX8BooksNames( self ):
        """
        Load the BookNames.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8BooksNames()" )

        bookNamesFilepath = os.path.join( self.sourceFilepath, 'BookNames.xml' )
        if not os.path.exists( bookNamesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading books names data from {}…".format( bookNamesFilepath ) )
        self.XMLTree = ElementTree().parse( bookNamesFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        booksNamesDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='BookNames':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual book data
            for element in self.XMLTree:
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
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( bnCode, booksNamesDict[bnCode] )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert len(bnCode)==3
                    try: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bnCode )
                    except:
                        logging.warning( "loadPTX8BooksNames can't find BOS code for PTX8 {!r} book".format( bnCode ) )
                        BBB = bnCode # temporarily use their code
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert BBB not in booksNamesDict
                    booksNamesDict[BBB] = (bnCode,bnAbbr,bnShort,bnLong,)
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 bookname settings tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( bookNamesFilepath )
        except ValueError: logging.critical( "PTX8 books names file seemed unexpected: {}".format( bookNamesFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} book names.".format( len(booksNamesDict) ) )
        if debuggingThisModule: print( "\nbooksNamesDict", len(booksNamesDict), booksNamesDict )
        if booksNamesDict: self.suppliedMetadata['PTX8']['BooksNames'] = booksNamesDict
    # end of PTX8Bible.loadPTX8BooksNames


    def loadPTX8Lexicon( self ):
        """
        Load the Lexicon.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Lexicon()" )

        lexiconFilepath = os.path.join( self.sourceFilepath, 'Lexicon.xml' )
        if not os.path.exists( lexiconFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading project lexicon data from {}…".format( lexiconFilepath ) )
        self.XMLTree = ElementTree().parse( lexiconFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

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
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( "Lexeme {} form={!r} homograph={}".format( lexemeType, lexemeForm, lexemeHomograph ) )
                    assert lexemeType in ( 'Word', 'Phrase', 'Stem', 'Prefix' )
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
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                else:
                                    logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                assert senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs']
                                lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'][senseID] = (sub3element.text, glossLanguage)
                        else:
                            logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
        # end of processLexiconItem


        # Find the main container
        if self.XMLTree.tag == 'Lexicon':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
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
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 lexicon tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( lexiconFilepath )
        except ValueError: logging.critical( "PTX8 lexicon file seemed unexpected: {}".format( lexiconFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            totalEntries = 0
            for lType in lexiconDict['Entries']: totalEntries += len( lexiconDict['Entries'][lType] )
            print( "  Loaded {} lexicon types ({:,} total entries).".format( len(lexiconDict['Entries']), totalEntries ) )
        if debuggingThisModule: print( "\nlexiconDict", len(lexiconDict), lexiconDict )
        if lexiconDict: self.suppliedMetadata['PTX8']['Lexicon'] = lexiconDict
    # end of PTX8Bible.loadPTX8Lexicon


    def loadPTX8ProjectUserAccess( self ):
        """
        Load the ProjectUsers.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8ProjectUserAccess()" )

        projectUsersFilepath = os.path.join( self.sourceFilepath, 'ProjectUserAccess.xml' )
        if not os.path.exists( projectUsersFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading project user data from {}…".format( projectUsersFilepath ) )
        self.XMLTree = ElementTree().parse( projectUsersFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        projectUsersDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='ProjectUserAccess':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Process the attributes first
            peerSharingFlag = None
            for attrib,value in self.XMLTree.items():
                if attrib=='PeerSharing': peerSharingFlag = getFlagFromAttribute( attrib, value )
                else:
                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            projectUsersDict['PeerSharingFlag'] = peerSharingFlag

            # Now process the actual entries
            for element in self.XMLTree:
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
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    projectUsersDict['Users'][userName][subelement.tag].append( bookID )
                                else:
                                    logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    projectUsersDict['Users'][userName][subelement.tag][permissionType] = grantedFlag
                                else:
                                    logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 project users settings tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( projectUsersFilepath )
        except ValueError: logging.critical( "PTX8 project users file seemed unexpected: {}".format( projectUsersFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(projectUsersDict['Users']) ) )
        if debuggingThisModule:
            #print( "\nprojectUsersDict", len(projectUsersDict), projectUsersDict )
            for somekey in projectUsersDict:
                if somekey == 'Users':
                    for userKey in projectUsersDict['Users']: print( '\n   User', userKey, projectUsersDict['Users'][userKey] )
                else: print( '\n  ', somekey, projectUsersDict[somekey] )
        if projectUsersDict: self.suppliedMetadata['PTX8']['ProjectUsers'] = projectUsersDict
    # end of PTX8Bible.loadPTX8ProjectUserAccess


    def loadPTX8Canons( self ):
        """
        Load the Canons.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Canons()" )

        canonsFilepath = os.path.join( self.sourceFilepath, 'Canons.xml' )
        if not os.path.exists( canonsFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading canons data from {}…".format( canonsFilepath ) )
        self.XMLTree = ElementTree().parse( canonsFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        canonsDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag == 'Canons':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation, 'CA01' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation, 'CA02' )

            # Process the attributes first
            nextId = None
            for attrib,value in self.XMLTree.items():
                if attrib=='NextId': nextId = value
                else:
                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )

                # Now process the subelements
                if element.tag == 'Canon':
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                    tempDict = {}

                    # Process the canon attributes
                    Id = defaultFlag = Psa151inPsaFlag = LjeInBarFlag = DagPartialFlag = None
                    for attrib,value in element.items():
                        if attrib=='Id': Id = value
                        elif attrib=='Default': defaultFlag = getFlagFromAttribute( attrib, value )
                        elif attrib=='Psa151inPsa': Psa151inPsaFlag = getFlagFromAttribute( attrib, value )
                        elif attrib=='LjeInBar': LjeInBarFlag = getFlagFromAttribute( attrib, value )
                        elif attrib=='DagPartial': DagPartialFlag = getFlagFromAttribute( attrib, value )
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    tempDict['DefaultFlag'] = defaultFlag
                    tempDict['Psa151inPsaFlag'] = Psa151inPsaFlag
                    tempDict['LjeInBarFlag'] = LjeInBarFlag
                    tempDict['DagPartialFlag'] = DagPartialFlag

                    bookList = []
                    for subelement in element:
                        sublocation = subelement.tag + ' in ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )

                        if subelement.tag in ( 'Name', 'NameLocal', 'Abbreviation', 'AbbreviationLocal', 'Description', 'DescriptionLocal', ):
                            if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in tempDict
                            tempDict[subelement.tag] = subelement.text
                        elif subelement.tag == 'Book':
                            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( subelement.text )
                            bookList.append( BBB )
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if bookList:
                        assert 'BookList' not in tempDict
                        tempDict['BookList'] = bookList
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert Id not in canonsDict
                canonsDict[Id] = tempDict
        else:
            logging.critical( _("Unrecognised PTX8 checking tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( canonsFilepath )
        except ValueError: logging.critical( "PTX8 checking status file seemed unexpected: {}".format( canonsFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} canons.".format( len(canonsDict) ) )
        if debuggingThisModule: print( "\ncanonsDict", len(canonsDict), canonsDict )
        #for something in canonsDict:
            #print( "\n  {} = {}".format( something, canonsDict[something] ) )
        if canonsDict: self.suppliedMetadata['PTX8']['Canons'] = canonsDict
    # end of PTX8Bible.loadPTX8Canons


    def loadPTX8CheckingStatus( self ):
        """
        Load the CheckingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8CheckingStatus()" )

        checkingStatusFilepath = os.path.join( self.sourceFilepath, 'CheckingStatus.xml' )
        if not os.path.exists( checkingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading checking status data from {}…".format( checkingStatusFilepath ) )
        self.XMLTree = ElementTree().parse( checkingStatusFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        checkingStatusByBookDict, checkingStatusByCheckDict = {}, {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag == 'CheckingStatuses':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'CheckingStatus':
                    tempDict = {}
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
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 checking tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( checkingStatusFilepath )
        except ValueError: logging.critical( "PTX8 checking status file seemed unexpected: {}".format( checkingStatusFilepath ) )

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
    # end of PTX8Bible.loadPTX8CheckingStatus


    def loadPTX8CommentTags( self ):
        """
        Load the CommentTags_*.xml files (if they exist) and parse them into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8CommentTags()" )

        commentTagFilepath = os.path.join( self.sourceFilepath, 'CommentTags.xml' )
        if not os.path.exists( commentTagFilepath ): return

        commentTagDict = {}
        #loadErrors = []

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading comment tags from {}…".format( commentTagFilepath ) )

        self.XMLTree = ElementTree().parse( commentTagFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.XMLTree.tag == 'TagList':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
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
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    commentTagDict[element.tag] = { 'Id':Id, 'Name':name, 'Icon':icon, 'CreatorResolve':creatorResolveFlag }
                elif element.tag == 'LastUsedID':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    commentTagDict[element.tag] = element.text
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 comment tag list tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( commentTagFilepath )
        except ValueError: logging.critical( "PTX8 comment tag file seemed unexpected: {}".format( commentTagFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} comment tags.".format( len(commentTagDict) ) )
        if debuggingThisModule: print( "\ncommentTagDict", len(commentTagDict), commentTagDict )
        if commentTagDict: self.suppliedMetadata['PTX8']['CommentTags'] = commentTagDict
    # end of PTX8Bible.loadPTX8CommentTags


    def loadPTX8DerivedTranslationStatus( self ):
        """
        Load the DerivedTranslationStatus.xml file (if it exists)
            and parse it into the dictionary self.suppliedMetadata.

        This is usually used for a project like a back translation or daughter translation.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8DerivedTranslationStatus()" )

        derivedTranslationStatusFilepath = os.path.join( self.sourceFilepath, 'DerivedTranslationStatus.xml' )
        if not os.path.exists( derivedTranslationStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading derived translation status data from {}…".format( derivedTranslationStatusFilepath ) )
        self.XMLTree = ElementTree().parse( derivedTranslationStatusFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        derivedTranslationStatusByBookDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag == 'DerivedTranslationVerseList':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Verse':

                    # Process the entry attributes first
                    referenceString = derivedCode = None
                    for attrib,value in element.items():
                        if attrib=='ref': referenceString = value
                        elif attrib=='derived': derivedCode = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert referenceString.count( ' ' ) == 1
                    assert referenceString.count( ':' ) == 1
                    assert len(derivedCode) == 8
                    ptBookCode, CV = referenceString.split( ' ', 1 )
                    C, V = CV.split( ':', 1 )

                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( ptBookCode )
                    if BBB not in derivedTranslationStatusByBookDict:
                        derivedTranslationStatusByBookDict[BBB] = {}

                    derivedFrom = element.text
                    derivedTranslationStatusByBookDict[BBB][(C,V)] = (derivedCode,derivedFrom)
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 derived translation tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictDerivedTranslationFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( derivedTranslationStatusFilepath )
        except ValueError: logging.critical( "PTX8 derived translation status file seemed unexpected: {}".format( derivedTranslationStatusFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  Loaded {:,} derived translation status books.".format( len(derivedTranslationStatusByBookDict) ) )
        if debuggingThisModule:
            print( "\nderivedTranslationStatusByBookDict", len(derivedTranslationStatusByBookDict), derivedTranslationStatusByBookDict )
        #for something in derivedTranslationStatusByBookDict:
            #print( "\n  {} = {}".format( something, derivedTranslationStatusByBookDict[something] ) )
        if derivedTranslationStatusByBookDict: self.suppliedMetadata['PTX8']['DerivedTranslationStatusByBook'] = derivedTranslationStatusByBookDict
    # end of PTX8Bible.loadPTX8DerivedTranslationStatus


    def loadPTX8Licence( self ):
        """
        Load the license.json file and parse it into the dictionary.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Licence()" )

        licenceFilename = 'license.json'
        licenceFilepath = os.path.join( self.sourceFilepath, licenceFilename )
        if not os.path.exists( licenceFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading PTX8 license from {}…".format( licenceFilepath ) )

        with open( licenceFilepath, 'rt', encoding='utf-8' ) as lFile: # Automatically closes the file when done
            licenceString = lFile.read()
        #print( "licenceString", licenceString )
        if licenceString[0]==chr(65279): #U+FEFF
            logging.info( "loadPTX8Licence: Detected Unicode Byte Order Marker (BOM) in {}".format( licenceFilename ) )
            licenceString = licenceString[1:] # Remove the Unicode Byte Order Marker (BOM)
        jsonData = json.loads( licenceString )
        #print( "jsonData", jsonData )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule: assert isinstance( jsonData, dict )

        try: self.filepathsNotYetLoaded.remove( licenceFilepath )
        except ValueError: logging.critical( "PTX8 license file seemed unexpected: {}".format( licenceFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} license elements.".format( len(jsonData) ) )
        if debuggingThisModule: print( '\nPTX8Licence', len(jsonData), jsonData )
        if jsonData: self.suppliedMetadata['PTX8']['Licence'] = jsonData
    # end of PTX8Bible.loadPTX8Licence


    def loadPTX8Notes( self ):
        """
        Load the Notes_*.xml files (if they exist) and parse them into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Notes()" )

        noteFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('NOTES_') and somethingUPPER.endswith('.XML'):
                noteFilenames.append( something )
        #if len(noteFilenames) > 1:
            #logging.error( "Got more than one note file: {}".format( noteFilenames ) )
        if not noteFilenames: return

        notesDictByName, notesDictByThread = {}, {}
        #loadErrors = []

        for noteFilename in noteFilenames:
            noterName = noteFilename[6:-4] # Remove the Notes_ and the .xml
            assert noterName not in notesDictByName
            notesDictByName[noterName] = []

            noteFilepath = os.path.join( self.sourceFilepath, noteFilename )
            if BibleOrgSysGlobals.verbosityLevel > 3:
                print( "PTX8Bible.loading notes from {}…".format( noteFilepath ) )

            self.XMLTree = ElementTree().parse( noteFilepath )
            if not len( self.XMLTree ):
                logging.info( "Notes for {} seems empty.".format( noterName ) )

            # Find the main container
            if self.XMLTree.tag == 'CommentList':
                treeLocation = "PTX8 notes file ({}) for {}".format( self.XMLTree.tag, noterName )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

                # Now process the actual entries
                for element in self.XMLTree:
                    elementLocation = element.tag + ' in ' + treeLocation
                    #print( "Processing {}…".format( elementLocation ) )
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                    # Now process the subelements
                    if element.tag == 'Comment':
                        # Process the user attributes first
                        thread = user = verseRef = language = date = None
                        for attrib,value in element.items():
                            if attrib=='Thread': thread = value
                            elif attrib=='User': user = value
                            elif attrib=='VerseRef': verseRef = value
                            elif attrib=='Language': language = value
                            elif attrib=='Date': date = value
                            else:
                                logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        commentDict = { 'Noter':noterName, 'Thread':thread, 'User':user,
                                        'VerseRef':verseRef, 'Language':language, 'Date':date }

                        for subelement in element:
                            sublocation = subelement.tag + ' in ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'CM01' )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'CM02' )
                            assert subelement.tag not in commentDict # No duplicates please
                            if subelement.tag in ( 'AcceptedChangeXml', 'AssignedUser', 'BiblicalTermId',
                                            'ContextBefore', 'ContextAfter',
                                            'ConflictResolutionAction', 'ConflictType',
                                            'ExtraHeadingInfo', 'HideInTextWindow',
                                            'ReplyToUser', 'SelectedText', 'Status', 'StartPosition',
                                            'TagAdded', 'Type', 'Verse', ):
                                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                                commentDict[subelement.tag] = subelement.text # can be None
                            elif subelement.tag == 'Contents':
                                #print( "QQQ", BibleOrgSysGlobals.getFlattenedXML( subelement, sublocation ) )
                                #contentsText = ''
                                #if subelement.text: contentsText += subelement.text.lstrip()
                                #for sub2element in subelement:
                                    #sub2location = sub2element.tag + ' ' + sublocation
                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                    #if sub2element.text:
                                        #contentsText += '<{}>{}</{}>'.format( sub2element.tag, sub2element.text, sub2element.tag )
                                    #else: contentsText += '<{}/>'.format( sub2element.tag )
                                ##print( 'contentsText', repr(contentsText) )
                                commentDict[subelement.tag] = BibleOrgSysGlobals.getFlattenedXML( subelement, sublocation )
                            else:
                                logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #elif element.tag == 'ConflictType':halt
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( "commentDict", commentDict )
                    if commentDict['ConflictType'] == 'verseText':
                        #print( "{}/ Noter: {} @ {} @ {}".format( len(self.conflicts)+1, noterName, commentDict['VerseRef'], commentDict['Date'].split('T',1)[0] ) )
                        #print( "  Type: {}".format( commentDict['Type'] ) )
                        #print( "  ConflictType: {}".format( commentDict['ConflictType'] ) )
                        #print( "  Status: {}".format( commentDict['Status'] ) )
                        #try: print( "  ConflictResolutionAction: {}".format( commentDict['ConflictResolutionAction'] ) )
                        #except KeyError: pass
                        ##print( "  AcceptedChangeXml: {}".format( commentDict['AcceptedChangeXml'] ) )
                        self.conflicts.append( commentDict )
                    notesDictByName[noterName].append( commentDict )
                    assert thread
                    if thread not in notesDictByThread: notesDictByThread[thread] = []
                    notesDictByThread[thread].append( commentDict )
            else:
                logging.critical( _("Unrecognised PTX8 {} note/comment list tag: {}").format( noterName, self.XMLTree.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

            #print( "\nNotes for {}: ({}) {}".format( noterName, len(notesDictByName[noterName]), notesDictByName[noterName] ) )

            try: self.filepathsNotYetLoaded.remove( noteFilepath )
            except ValueError: logging.critical( "PTX8 notes file seemed unexpected: {}".format( noteFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            print( "  Checking {} possible conflicts…".format( len(self.conflicts) ) )
        for commentDict1 in self.conflicts[:]: # Work on a copy since we modify it
            noterName = commentDict1['Noter']
            threadNumber = commentDict1['Thread']
            #print( "Have possible conflict thread {} by {}".format( threadNumber, noterName ) )
            threadNotes = notesDictByThread[threadNumber]
            #print( "  {}".format( threadNotes ) )
            for threadNoteDict in threadNotes:
                assert threadNoteDict['Thread'] == threadNumber
                #print( "  {} status is {}".format( threadNoteDict['Noter'], threadNoteDict['Status'] ) )
                if threadNoteDict['Status'] == 'deleted': # Remove from conflicts
                    self.conflicts.remove( commentDict1 )
                    #print( "  removed!" )
                    break
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            print( "    Now have {} remaining conflicts".format( len(self.conflicts) ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} noters.".format( len(notesDictByName) ) )
        if debuggingThisModule: print( "\nnotesDictByName", len(notesDictByName), notesDictByName )
        # Call this 'PTXNotes' rather than just 'Notes' which might just be a note on the particular version
        if notesDictByName: self.suppliedMetadata['PTX8']['PTXNotesByName'] = notesDictByName
        if notesDictByThread: self.suppliedMetadata['PTX8']['PTXNotesByThread'] = notesDictByThread
    # end of PTX8Bible.loadPTX8Notes


    def loadPTX8ParallelPassageStatus( self ):
        """
        Load the ParallelPassageStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8ParallelPassageStatus()" )

        parallelPassageStatusFilepath = os.path.join( self.sourceFilepath, 'ParallelPassageStatus.xml' )
        if not os.path.exists( parallelPassageStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading parallel passage status data from {}…".format( parallelPassageStatusFilepath ) )
        self.XMLTree = ElementTree().parse( parallelPassageStatusFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        parallelPassageStatusDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag == 'PassageStatus':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )

                # Now process the subelements
                if element.tag == 'Status':
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                    # Process the status attributes first
                    passageKey = passageStatus = None
                    for attrib,value in element.items():
                        if attrib=='passageKey':
                            passageKey = value # A semicolon separated string of Bible references like "1CH 29:27;1KI 2:11;1CH 29:27"
                        elif attrib=='status':
                            passageStatus = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert passageKey
                    assert passageKey not in parallelPassageStatusDict # no duplicates allowed presumably
                    parallelPassageStatusDict[passageKey] = {}
                    assert passageStatus in 'UF' # unfixed? fixed? uncertain? finished?
                    parallelPassageStatusDict[passageKey]['Status'] = passageStatus

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag == 'Content':
                            #print( BibleOrgSysGlobals.elementStr( subelement ) )
                            if passageStatus == 'U':
                                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            else:
                                assert passageStatus == 'F'
                                assert subelement.text
                                assert subelement.tag not in parallelPassageStatusDict[passageKey]
                                parallelPassageStatusDict[passageKey][subelement.tag] = subelement.text
                        elif subelement.tag == 'History':
                            #print( BibleOrgSysGlobals.elementStr( subelement ) )
                            if passageStatus == 'U':
                                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            else:
                                assert passageStatus == 'F'
                                if subelement.text:
                                    assert subelement.tag not in parallelPassageStatusDict[passageKey]
                                    parallelPassageStatusDict[passageKey][subelement.tag] = subelement.text
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 parallel passage status tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( parallelPassageStatusFilepath )
        except ValueError: logging.critical( "PTX8 parallel passage status file seemed unexpected: {}".format( parallelPassageStatusFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} parallel passage status entries.".format( len(parallelPassageStatusDict) ) )
        if debuggingThisModule: print( "\nparallelPassageStatusDict", len(parallelPassageStatusDict), parallelPassageStatusDict )
        if parallelPassageStatusDict: self.suppliedMetadata['PTX8']['ParallelPassageStatus'] = parallelPassageStatusDict
    # end of PTX8Bible.loadPTX8ParallelPassageStatus


    def loadPTX8ProjectBiblicalTerms( self ):
        """
        Load the BiblicalTerms*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8ProjectBiblicalTerms()" )

        projectBiblicalTermsFilepath = os.path.join( self.sourceFilepath, 'ProjectBiblicalTerms.xml' )
        if not os.path.exists( projectBiblicalTermsFilepath ): return

        projectBiblicalTermsDict = {}
        #loadErrors = []

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading Biblical terms from {}…".format( projectBiblicalTermsFilepath ) )

        self.XMLTree = ElementTree().parse( projectBiblicalTermsFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.XMLTree.tag=='BiblicalTermsList':
            treeLocation = "PTX8 {} in project Biblical terms".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the elements
                if element.tag == 'Term':
                    termRenderingEntryDict = {}
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )

                    termId =  None
                    for attrib,value in element.items():
                        if attrib=='Id': termId = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        assert element.tag not in termRenderingEntryDict # No duplicates please
                        if subelement.tag in ( 'Transliteration', 'Domain', 'Language', 'Category', 'Gloss', ):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            termRenderingEntryDict[subelement.tag] = subelement.text
                        elif subelement.tag == 'References':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            referenceList = []
                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' in ' + sublocation
                                #print( "  Processing {}…".format( sub2location ) )

                                if sub2element.tag == 'Verse':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                    verseCode = sub2element.text
                                    assert len(verseCode) == 11
                                    assert verseCode.isdigit()
                                    referenceList.append( verseCode )
                                else:
                                    logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if referenceList: termRenderingEntryDict['referenceList'] = referenceList
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert termId not in projectBiblicalTermsDict
                    projectBiblicalTermsDict[termId] = termRenderingEntryDict
                elif element.tag == 'Versification':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                    projectBiblicalTermsDict[element.tag] = element.text
                else:
                    logging.error( _("Unprocessed {} element '{}' in {}").format( element.tag, element.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 {} project Biblical terms tag: {}").format( versionName, self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( projectBiblicalTermsFilepath )
        except ValueError: logging.critical( "PTX8 project Biblical terms file seemed unexpected: {}".format( projectBiblicalTermsFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project Biblical terms entries.".format( len(projectBiblicalTermsDict) ) )
        if debuggingThisModule: print( "\nprojectBiblicalTermsDict", len(projectBiblicalTermsDict), projectBiblicalTermsDict )
        #for someKey, someValue in projectBiblicalTermsDict.items():
            #print( "\n  {} = {}".format( someKey, someValue ) )
        if projectBiblicalTermsDict: self.suppliedMetadata['PTX8']['ProjectBiblicalTerms'] = projectBiblicalTermsDict
    # end of PTX8Bible.loadPTX8ProjectBiblicalTerms


    def loadPTX8ProjectProgress( self ):
        """
        Load the Progress*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8ProjectProgress()" )

        projectProgressFilepath = os.path.join( self.sourceFilepath, 'ProjectProgress.xml' )
        if not os.path.exists( projectProgressFilepath ): return

        projectProgressDict = {}
        #loadErrors = []

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading Progress from {}…".format( projectProgressFilepath ) )

        self.XMLTree = ElementTree().parse( projectProgressFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.XMLTree.tag=='ProgressInfo':
            treeLocation = "PTX8 {} in Project Progress".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                assert element.tag not in projectProgressDict
                projectProgressDict[element.tag] = {}

                # Now process the subelements
                if element.tag == 'Stages':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    stages = {}
                    for subelement in element:
                        sublocation = subelement.tag + ' in ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )

                        if subelement.tag == 'Stage':
                            StageId = None
                            for attrib,value in subelement.items():
                                if attrib=='id': StageId = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            stage = {}

                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' in ' + sublocation
                                #print( "  Processing {}…".format( sub2location ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                assert sub2element.tag not in stage
                                stage[sub2element.tag] = {}

                                if sub2element.tag == 'BookStatus':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    for sub3element in sub2element:
                                        sub3location = sub3element.tag + ' in ' + sub2location
                                        #print( "  Processing {}…".format( sub3location ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                        if sub3element.tag not in stage['BookStatus']:
                                            stage['BookStatus'][sub3element.tag] = {}

                                        if sub3element.tag == 'HiddenChapters':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            for sub4element in sub3element:
                                                sub4location = sub4element.tag + ' in ' + sub3location
                                                #print( "  Processing {}…".format( sub4location ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                                stage['BookStatus']['HiddenChapters'] = 'XXX'
                                        elif sub3element.tag == 'CompletedChapters':
                                            bookNum = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='BookNum': bookNum = value
                                                else:
                                                    logging.error( _("Unprocessed sub3 {!r} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                                            for j,sub4element in enumerate( sub3element ):
                                                sub4location = sub4element.tag + ' in ' + sub3location
                                                #print( "  Processing {}…".format( sub4location ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )

                                                if sub4element.tag == 'ChapRevId':
                                                    stage['BookStatus']['CompletedChapters'][bookNum] = ('ChapRevId',j+1,'XXX')
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element '{}' in {}").format( sub4element.tag, sub4element.text, sub4location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                elif sub2element.tag == 'TargetCompletionDateMap':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location, 'TCDM11' )
                                    if stage['TargetCompletionDateMap']:
                                        logging.critical( "Got extra TargetCompletionDateMap (ignored): {}".format( BibleOrgSysGlobals.elementStr(sub2element) ) )
                                        print( "Had", stage['TargetCompletionDateMap'] )
                                        halt

                                    for sub3element in sub2element:
                                        sub3location = sub3element.tag + ' in ' + sub2location
                                        #print( "  Processing {}…".format( sub3location ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location, 'TCDM21' )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'TCDM22' )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'TCDM24' )
                                        if sub3element.tag == 'item':
                                            for sub4element in sub3element:
                                                sub4location = sub4element.tag + ' in ' + sub3location
                                                #print( "    Processing {}…".format( sub4location ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location, 'INT11' )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location, 'INT12' )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location, 'INT14' )
                                                if sub4element.tag in ('int','string'):
                                                    assert sub4element.tag not in stage['TargetCompletionDateMap']
                                                    stage['TargetCompletionDateMap'][sub4element.tag] = sub4element.text
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element '{}' in {}").format( sub4element.tag, sub4element.text, sub4location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                elif sub2element.tag == 'Task':
                                    taskId = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='id': taskId = value
                                        else:
                                            logging.error( _("Unprocessed sub2 {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                                    taskDict = {}
                                    for sub3element in sub2element:
                                        sub3location = sub3element.tag + ' in ' + sub2location
                                        #print( "  Processing {}…".format( sub3location ) )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                        if sub3element.tag == 'Assignments':
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            bookAbbrev = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='book': bookAbbrev = value
                                                else:
                                                    logging.error( _("Unprocessed sub3 {!r} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        elif sub3element.tag in ( 'Type', 'EasiestBooksVPD', 'EasyBooksVPD', 'ModerateBooksVPD', 'DifficultBooksVPD', 'Availability', ):
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            taskDict[sub3element.tag] = sub3element.text
                                        elif sub3element.tag == 'AutoGrantEditRights':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            taskDict[sub3element.tag] = getFlagFromText( sub3element )
                                        elif sub3element.tag == 'Names':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            for sub4element in sub3element:
                                                sub4location = sub4element.tag + ' in ' + sub3location
                                                #print( "  Processing {}…".format( sub4location ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                                if sub4element.tag == 'item':
                                                    for sub5element in sub4element:
                                                        sub5location = sub5element.tag + ' in ' + sub4location
                                                        #print( "  Processing {}…".format( sub5location ) )
                                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5location )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5location )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5location )
                                                        if sub5element.tag == 'string':
                                                            pass
                                                        else:
                                                            logging.error( _("Unprocessed {} sub5element '{}' in {}").format( sub5element.tag, sub5element.text, sub5location ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element '{}' in {}").format( sub4element.tag, sub4element.text, sub4location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        elif sub3element.tag == 'Descriptions':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                        else:
                                            logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    if sub2element.tag not in stage:
                                        stage[sub2element.tag] = {}
                                    stage['Task'][taskId] = taskDict
                                elif sub2element.tag == 'Check':
                                    checkId = None
                                    for attrib,value in sub2element.items():
                                        if attrib=='id': checkId = value
                                        else:
                                            logging.error( _("Unprocessed sub2 {!r} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                                    checkDict = {}
                                    for sub3element in sub2element:
                                        sub3location = sub3element.tag + ' in ' + sub2location
                                        #print( "  Processing {}…".format( sub3location ) )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                        if sub3element.tag == 'Assignments':
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            bookAbbrev = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='book': bookAbbrev = value
                                                else:
                                                    logging.error( _("Unprocessed sub3 {!r} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            if sub3element.tag not in checkDict: checkDict[sub3element.tag] = []
                                            checkDict[sub3element.tag].append( bookAbbrev )
                                        elif sub3element.tag in ( 'Type', ):
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            checkDict[sub3element.tag] = sub3element.text
                                        elif sub3element.tag == 'AutoGrantEditRights':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            checkDict[sub3element.tag] = getFlagFromText( sub3element )
                                        elif sub3element.tag in ( 'BasicCheckType', 'PostponedBooks', ):
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            pass
                                        else:
                                            logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    if sub2element.tag not in stage:
                                        stage[sub2element.tag] = {}
                                    stage['Check'][checkId] = checkDict
                                elif sub2element.tag == 'Names':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    namesDict = []
                                    for sub3element in sub2element:
                                        sub3location = sub3element.tag + ' in ' + sub2location
                                        #print( "  Processing {}…".format( sub3location ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                        if sub3element.tag == 'item':
                                            for sub4element in sub3element:
                                                sub4location = sub4element.tag + ' in ' + sub3location
                                                #print( "  Processing {}…".format( sub4location ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location )
                                                if sub4element.tag == 'string':
                                                    pass
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element '{}' in {}").format( sub4element.tag, sub4element.text, sub4location ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    #if sub2element.tag not in stage:
                                        #stage[sub2element.tag] = {}
                                    stage['Names']= namesDict
                                elif sub2element.tag == 'Descriptions':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                    pass
                                else:
                                    logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if stage:
                                assert StageId not in stages
                                stages[StageId] = stage
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if stages:
                        assert not projectProgressDict['Stages']
                        projectProgressDict['Stages'] = stages
                elif element.tag in ('PlannedBooks', 'EasiestBooks', 'EasyBooks', 'ModerateBooks', 'DifficultBooks', ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                    #assert element.tag not in projectProgressDict # Detect duplicates
                    #projectProgressDict[element.tag] = {}
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        if subelement.tag == 'Books':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                            assert subelement.tag not in projectProgressDict[element.tag] # Detect duplicates
                            projectProgressDict[element.tag][subelement.tag] = subelement.text
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif element.tag == 'BasePlanType':
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                    projectProgressDict[element.tag] = element.text
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #print( "bookStatusDict", bookStatusDict )
                #projectProgressDict.append( bookStatusDict )
        else:
            logging.critical( _("Unrecognised PTX8 {} project progress tag: {}").format( versionName, self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( projectProgressFilepath )
        except ValueError: logging.critical( "PTX8 project progress file seemed unexpected: {}".format( projectProgressFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project progress entries.".format( len(projectProgressDict) ) )
        if debuggingThisModule: print( "\nprojectProgressDict", len(projectProgressDict), projectProgressDict )
        #for someKey, someValue in projectProgressDict.items():
            #print( "\n  {} = {}".format( someKey, someValue ) )
        if projectProgressDict: self.suppliedMetadata['PTX8']['ProjectProgress'] = projectProgressDict
    # end of PTX8Bible.loadPTX8ProjectProgress


    def loadPTX8ProjectProgressCSV( self ):
        """
        Load the Progress*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8ProjectProgressCSV()" )

        projectProgressCSVFilename = 'ProjectProgress.csv'
        projectProgressCSVFilepath = os.path.join( self.sourceFilepath, projectProgressCSVFilename )
        if not os.path.exists( projectProgressCSVFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading project progress CSV from {}…".format( projectProgressCSVFilepath ) )
        lineCount = 0
        lines = []
        with open( projectProgressCSVFilepath, 'rt', encoding='utf-8' ) as projectProgressCSVFile:
            for line in projectProgressCSVFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTX8ProjectProgressCSV: Detected Unicode Byte Order Marker (BOM) in {}".format( projectProgressCSVFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                lastLine = line
                #print( "  loadPTX8ProjectProgressCSV: ({}) {!r}".format( lineCount, line ) )
                # Each line is in the format: '2PE,61,0,10,0,30'
                if line: assert line.count( ',' ) == 5 # five commas between six values
                lines.append( line )
        assert len( lines ) == 66
        self.suppliedMetadata['PTX8']['ProjectProgressCSV'] = lines

        try: self.filepathsNotYetLoaded.remove( projectProgressCSVFilepath )
        except ValueError: logging.critical( "PTX8 project progress CSV file seemed unexpected: {}".format( projectProgressCSVFilepath ) )
    # end of PTX8Bible.loadPTX8ProjectProgressCSV


    def loadPTX8PrintConfig( self ):
        """
        Load the PrintConfig*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8PrintConfig()" )

# XXXXXXXXXXXXXXX IS THERE REALLY MORE THAN ONE OF THESE???
        printConfigFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('PRINT') and somethingUPPER.endswith('.XML'):
                printConfigFilenames.append( something )
        if len(printConfigFilenames) > 1:
            print( "Got more than one printConfig file: {}".format( printConfigFilenames ) )
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

            self.XMLTree = ElementTree().parse( printConfigFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.XMLTree.tag == 'PrintDraftConfiguration':
                treeLocation = "PTX8 {} file for {}".format( self.XMLTree.tag, printConfigType )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

                # Now process the actual entries
                for element in self.XMLTree:
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
                            else:
                                logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( "bookStatusDict", bookStatusDict )
                    #printConfigDict[printConfigType].append( bookStatusDict )
            else:
                logging.critical( _("Unrecognised PTX8 {} print configuration tag: {}").format( printConfigType, self.XMLTree.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

            try: self.filepathsNotYetLoaded.remove( printConfigFilepath )
            except ValueError: logging.critical( "PTX8 print config file seemed unexpected: {}".format( progressFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} printConfig.".format( len(printConfigDict) ) )
        if debuggingThisModule: print( "\nprintConfigDict", len(printConfigDict), printConfigDict )
        if printConfigDict: self.suppliedMetadata['PTX8']['PrintConfig'] = printConfigDict
    # end of PTX8Bible.loadPTX8PrintConfig


    def loadPTX8PrintDraftChanges( self ):
        """
        Load the AutoCorrect.txt file (which is a text file)
            and parse it into the ordered dictionary PTXPrintDraftChanges.

        These lines use the CC (Consisent Changes) format and so use > as the main operator.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8PrintDraftChanges()" )

        autocorrectFilename = 'PrintDraftChanges.txt'
        autocorrectFilepath = os.path.join( self.sourceFilepath, autocorrectFilename )
        if not os.path.exists( autocorrectFilepath ): return


        def processUnicode( changesString ):
            """
            """
            #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                #print( "processUnicode( {} {!r}={} )".format( len(changesString), changesString, changesString ) )

            import re
            while True:
                match = re.search( '\\\\u[a-fA-F0-9]{4,4}', changesString )
                if match:
                    newOrd = int( match.group(0)[2:], 16 )
                    #print( "NO", newOrd )
                    newChar = chr(newOrd)
                    #print( "NC", len(newChar), newChar )
                    assert len(newChar) == 1
                    changesString = changesString[:match.start()] + newChar + changesString[match.end():]
                else:
                    #print( "Return {} {!r}={}".format( len(changesString), changesString, changesString ) )
                    break

            return changesString
        # end of processUnicode


        def processPrintDraftChangesLine( line, lineNumber ):
            """
            Uses a state machine to process the line from the PrintDraftChanges files.

            Updates PTXPrintDraftChanges dictionary.

            States:
                0: looking for left side
                1: inside quotes for left side
                2: processing left side
                3: searching for >
                4: looking for right side
                5: inside quotes for right side
                6: processing right side
                7: processing after right side
                8: processing comment
            """
            #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                #print( "processPrintDraftChangesLine( {}, {!r} )".format( lineNumber, line ) )

            pdState = ix = 0
            quoteStart = leftSide = rightSide = comment = ''
            lenLine = len( line )
            while ix < lenLine:
                char = line[ix]
                #print( "processPrintDraftChangesLine {}: {!r} at state {} position {}".format( lineNumber, char, pdState, ix ) )

                if pdState == 0:
                    if char.isspace(): pass
                    elif char in ( '"', "'" ):
                        quoteStart = char
                        pdState = 1
                    elif char == '#':
                        pdState = 8
                    else:
                        logging.error( "Unexpected print-draft changes {!r} char at state {} position {} in line {}: {!r}" \
                                        .format( char, pdState, ix+1, lineNumber, line ) )
                elif pdState == 1:
                    if char == quoteStart:
                        pdState = 3
                    else: leftSide += char

                elif pdState == 3:
                    if char.isspace(): pass
                    elif char == '>':
                        pdState = 4
                    else:
                        logging.error( "Unexpected print-draft changes {!r} char at state {} position {} in line {}: {!r}" \
                                        .format( char, pdState, ix+1, lineNumber, line ) )
                elif pdState == 4:
                    if char.isspace(): pass
                    elif char in ( '"', "'" ):
                        quoteStart = char
                        pdState = 5
                    elif char == '#':
                        pdState = 8
                    else:
                        logging.error( "Unexpected print-draft changes {!r} char at state {} position {} in line {}: {!r}" \
                                        .format( char, pdState, ix+1, lineNumber, line ) )

                elif pdState == 5:
                    if char == quoteStart:
                        pdState = 7
                    else: rightSide += char

                elif pdState == 7:
                    if char.isspace(): pass
                    elif char == '#':
                        pdState = 8
                    else:
                        logging.error( "Unexpected print-draft changes {!r} char at state {} position {} in line {}: {!r}" \
                                        .format( char, pdState, ix+1, lineNumber, line ) )

                elif pdState == 8: # accept anything in a comment
                    comment += char

                else:
                    logging.error( "Unexpected print-draft changes {} state at position {} in line {}: {!r}" \
                                    .format( pdState, ix+1, lineNumber, line ) )
                ix += 1

            if pdState < 7:
                logging.error( "Unexpected print-draft changes {} end state at end of line {}: {!r}" \
                                .format( pdState, lineNumber, line ) )
            else:
                assert leftSide or comment
                if leftSide:
                    assert rightSide
                    assert leftSide not in PTXPrintDraftChanges
                    PTXPrintDraftChanges[processUnicode(leftSide)] = (processUnicode(rightSide),comment.strip())
        # end of processPrintDraftChangesLine


        # Main code for loadPTX8PrintDraftChanges
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading print draft changes from {}…".format( autocorrectFilepath ) )
        PTXPrintDraftChanges = {}

        # NOTE: These lines are actually regex's on the left side
        lineCount = 0
        with open( autocorrectFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTX8PrintDraftChanges: Detected Unicode Byte Order Marker (BOM) in {}".format( autocorrectFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "Print draft changes line", repr(line) )

                if len(line)<4:
                    logging.error( "Why was print draft changes line #{} so short? {!r}".format( lineCount, line ) )
                    continue
                if len(line)>100:
                    logging.warning( "Why was print draft changes line #{} so long? {!r}".format( lineCount, line ) )
                if line and '>' not in line and '#' not in line:
                    logging.error( "What is this print draft changes line #{}? {!r}".format( lineCount, line ) )
                else: processPrintDraftChangesLine( line, lineCount )

        try: self.filepathsNotYetLoaded.remove( autocorrectFilepath )
        except ValueError: logging.critical( "PTX8 print draft changes file seemed unexpected: {}".format( autocorrectFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} print draft changes elements.".format( len(PTXPrintDraftChanges) ) )
        if debuggingThisModule: print( '\nPTXPrintDraftChanges', len(PTXPrintDraftChanges), PTXPrintDraftChanges )
        if PTXPrintDraftChanges: self.suppliedMetadata['PTX8']['PrintDraftChanges'] = PTXPrintDraftChanges
    # end of PTX8Bible.loadPTX8PrintDraftChanges


    def loadPTX8SpellingStatus( self ):
        """
        Load the SpellingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8SpellingStatus()" )

        spellingStatusFilepath = os.path.join( self.sourceFilepath, 'SpellingStatus.xml' )
        if not os.path.exists( spellingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading spelling status data from {}…".format( spellingStatusFilepath ) )
        self.XMLTree = ElementTree().parse( spellingStatusFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        spellingStatusDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag == 'SpellingStatus':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Status':
                    # Process the status attributes first
                    word = state = None
                    for attrib,value in element.items():
                        if attrib=='Word': word = value
                        elif attrib=='State': state = value; assert state in 'RW' # right/wrong
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 spelling status tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( spellingStatusFilepath )
        except ValueError: logging.critical( "PTX8 spelling status file seemed unexpected: {}".format( spellingStatusFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} spelling status entries.".format( len(spellingStatusDict) ) )
        if debuggingThisModule: print( "\nspellingStatusDict", len(spellingStatusDict), spellingStatusDict )
        if spellingStatusDict: self.suppliedMetadata['PTX8']['SpellingStatus'] = spellingStatusDict
    # end of PTX8Bible.loadPTX8SpellingStatus


    def loadPTX8Styles( self ):
        """
        Load the something.sty file (which is a SFM file) and parse it into the dictionary PTXStyles.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8Styles()" )

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
                            #print( lineCount, "line1", repr(line) )
                            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                                logging.info( "loadPTX8Styles: Detected Unicode Byte Order Marker (BOM) in {}".format( styleFilename ) )
                                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                            #print( lineCount, "line2", repr(line) )
                            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            if not line: continue # Just discard blank lines
                            lastLine = line
                            if line[0]=='#': continue # Just discard comment lines
                            #print( lineCount, "line3", repr(line) )

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
                                elif name in ( 'Name', 'Description', 'OccursUnder', 'Rank', 'StyleType', 'Endmarker',
                                                'SpaceBefore', 'SpaceAfter', 'LeftMargin', 'RightMargin',
                                                'FirstLineIndent', 'TextType', 'TextProperties',
                                                'Justification', 'FontSize', 'Fontsize',
                                                'Bold', 'Italic', 'Smallcaps', 'Superscript', 'Underline',
                                                'Color', 'color', ):
                                    if name == 'color': name = 'Color' # fix inconsistency
                                    elif name == 'Fontsize': name = 'FontSize' # fix inconsistency
                                    if name in currentStyle: # already
                                        logging.error( "loadPTX8Styles found duplicate {!r}={!r} in {} {} at line #{}".format( name, value, styleName, styleMarker, lineCount ) )
                                    currentStyle[name] = value
                                else:
                                    logging.error( "What's this style marker? {!r}".format( line ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            else:
                                logging.error( "What's this style line? {!r}".format( line ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    break; # Get out of decoding loop because we were successful
                except UnicodeDecodeError:
                    logging.error( _("loadPTX8Styles fails with encoding: {} on {}{}").format( encoding, styleFilepath, {} if encoding==encodings[-1] else ' -- trying again' ) )

            try: self.filepathsNotYetLoaded.remove( styleFilepath )
            except ValueError: logging.critical( "PTX8 style file seemed unexpected: {}".format( styleFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} style files.".format( len(PTXStyles) ) )
        if debuggingThisModule: print( '\nPTXStyles', len(PTXStyles), PTXStyles )
        if PTXStyles: self.suppliedMetadata['PTX8']['Styles'] = PTXStyles
    # end of PTX8Bible.loadPTX8Styles


    def loadPTX8TermRenderings( self ):
        """
        Load the TermRenderings*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX8'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8TermRenderings()" )

        renderingTermsFilepath = os.path.join( self.sourceFilepath, 'TermRenderings.xml' )
        if not os.path.exists( renderingTermsFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading TermRenderings from {}…".format( renderingTermsFilepath ) )

        TermRenderingsDict = {}

        self.XMLTree = ElementTree().parse( renderingTermsFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if self.XMLTree.tag == 'TermRenderingsList':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
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
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                else:
                                    logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                #print( "termRenderingEntryDict", termRenderingEntryDict ); halt
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element '{}' in {}").format( element.tag, element.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #print( "termRenderingEntryDict", termRenderingEntryDict )
                assert Id not in TermRenderingsDict # No duplicate ids allowed
                TermRenderingsDict[Id] = termRenderingEntryDict
                #print( "termRenderingEntryDict", termRenderingEntryDict ); halt
        else:
            logging.critical( _("Unrecognised PTX8 {} term renderings tag: {}").format( versionName, self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( renderingTermsFilepath )
        except ValueError: logging.critical( "PTX8 rendering terms file seemed unexpected: {}".format( renderingTermsFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} term renderings.".format( len(TermRenderingsDict) ) )
        if debuggingThisModule: print( "\nTermRenderingsDict", len(TermRenderingsDict), TermRenderingsDict )
        #print( TermRenderingsDict['חָנוּן'] )
        if TermRenderingsDict: self.suppliedMetadata['PTX8']['TermRenderings'] = TermRenderingsDict
    # end of PTX8Bible.loadPTX8TermRenderings


    def loadUniqueId( self ):
        """
        Load the unique.id file (if it exists) and parse it into the dictionary self.suppliedMetadata.

        unique.id is just a file that Paratext uses to forcibly add a revision to the project history.
            Paratext writes a random string in there to force the file to change in Mercurial
            so that a commit can be created even if nothing else in the project has changed
            (e.g. when using Project > Mark Point in Project History).
            It has no other use.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadUniqueId()" )

        uniqueIdFilename = 'unique.id'
        uniqueIdFilepath = os.path.join( self.sourceFilepath, uniqueIdFilename )
        if not os.path.exists( uniqueIdFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading unique id from {}…".format( uniqueIdFilepath ) )
        with open( uniqueIdFilepath, 'rt', encoding='utf-8' ) as uniqueIdFile:
            uniqueId = uniqueIdFile.read() # This is a Windows GUID

        if uniqueId[0] == chr(65279): #U+FEFF
            logging.info( "loadUniqueId: Detected Unicode Byte Order Marker (BOM) in {}".format( uniqueIdFilename ) )
            uniqueId = uniqueId[1:] # Delete the BOM

        #print( "uniqueId: ({}) {}".format( len(uniqueId), uniqueId ))
        assert len( uniqueId ) == 36 # 12-4-4-4-8 lowercase hex chars (128-bits)
        assert uniqueId.count( '-' ) == 4
        for char in uniqueId: assert char in '0123456789abcdef-'
        self.suppliedMetadata['PTX8']['UniqueId'] = uniqueId

        try: self.filepathsNotYetLoaded.remove( uniqueIdFilepath )
        except ValueError: logging.critical( "PTX8 unique id file seemed unexpected: {}".format( uniqueIdFilepath ) )
    # end of PTX8Bible.loadUniqueId


    def loadPTX8WordAnalyses( self ):
        """
        Load the WordAnalyses.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( "loadPTX8WordAnalyses()" )

        wordAnalysesFilepath = os.path.join( self.sourceFilepath, 'WordAnalyses.xml' )
        if not os.path.exists( wordAnalysesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "PTX8Bible.loading word analysis data from {}…".format( wordAnalysesFilepath ) )
        self.XMLTree = ElementTree().parse( wordAnalysesFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        wordAnalysesDict = {}
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
                    #assert subelement.tag not in analysisDict # TODO: XXXXXXXXXXXXXXXXXXXXX DISABLED!!!
                    analysisDict[subelement.tag] = subelement.text
                else:
                    logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
            return analysisDict
        # end of processWordAnalysis


        # Find the main container
        if self.XMLTree.tag == 'WordAnalyses':
            treeLocation = "PTX8 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'Entry':
                    # Process the entry attributes first
                    word = None
                    for attrib,value in element.items():
                        if attrib=='Word': word = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                        else:
                            logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.critical( _("Unrecognised PTX8 word analysis tag: {}").format( self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        try: self.filepathsNotYetLoaded.remove( wordAnalysesFilepath )
        except ValueError: logging.critical( "PTX8 word analyses file seemed unexpected: {}".format( wordAnalysesFilepath ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {:,} word analysis entries.".format( len(wordAnalysesDict) ) )
        if debuggingThisModule: print( "\nwordAnalysesDict", len(wordAnalysesDict), wordAnalysesDict )
        if wordAnalysesDict: self.suppliedMetadata['PTX8']['WordAnalyses'] = wordAnalysesDict
    # end of PTX8Bible.loadPTX8WordAnalyses



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
                logging.warning( "We had already tried loading PTX8 USFM {} for {}".format( BBB, self.name ) )
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
        else: logging.info( "PTX8 USFM book {} was completely blank".format( BBB ) )
        bookfilepath = os.path.join( self.sourceFolder, filename )
        try: self.filepathsNotYetLoaded.remove( bookfilepath )
        except ValueError: logging.critical( "PTX8 {} book file seemed unexpected: {}".format( BBB, bookfilepath ) )
        self.bookNeedsReloading[BBB] = False
    # end of PTX8Bible.loadBook


    def _loadBookMP( self, BBB_Filename_Tuple ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "_loadBookMP( {} )".format( BBB_Filename_Tuple ) )

        BBB, filename = BBB_Filename_Tuple
        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading PTX8 USFM {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( '  ' + "Loading {} from {} from {}…".format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "PTX8Bible._loadBookMP: Unable to find file for {}".format( BBB ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        else: logging.info( "PTX8 USFM book {} was completely blank".format( BBB ) )
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of PTX8Bible._loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Loading {} from {}…".format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Loading {} PTX8 books using {} processes…".format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results:
                        self.stashBook( bBook ) # Saves them in the correct order
                        try: self.filepathsNotYetLoaded.remove( bBook.sourceFilepath ) # Can't do this in _loadBookMP() because it's not atomic
                        except ValueError: logging.critical( "PTX8 {} book file seemed unexpected: {}".format( bBook.BBB, bBook.sourceFilepath ) )
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  PTX8Bible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    #if BBB not in self.books:
                    self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( "PTX8Bible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of PTX8Bible.loadBooks

    def load( self ):
        self.loadBooks()


    def discoverPTX8( self ):
        """
        Discover statistics from BibleOrgSys.Formats.PTX8 metadata files
            and put the results into self.discoveryResults list (which must already exist)
            and will already be populated with dictionaries for each book.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Discovering PTX8 stats for {}…".format( self.name ) )

        for BBB in self.books: # Do individual book prechecks
            if BibleOrgSysGlobals.verbosityLevel > 3: print( '  ' + "PTX8 discovery for {}…".format( BBB ) )
            assert BBB in self.discoveryResults
            #print( self.discoveryResults[BBB].keys() )

            if 'DerivedTranslationStatusByBook' in self.suppliedMetadata['PTX8']:
                if BBB in self.suppliedMetadata['PTX8']['DerivedTranslationStatusByBook']:
                    derivedVersesCompleted = len(self.suppliedMetadata['PTX8']['DerivedTranslationStatusByBook'][BBB])
                else: derivedVersesCompleted = 0
                self.discoveryResults[BBB]['derivedVersesCompletedCount'] = derivedVersesCompleted
                if 'verseCount' in self.discoveryResults[BBB] and isinstance( self.discoveryResults[BBB]['verseCount'], int ):
                    self.discoveryResults[BBB]['percentageDerivedVersesCompleted'] = \
                        round( derivedVersesCompleted * 100 / self.discoveryResults[BBB]['verseCount'] )
    # end of PTX8Bible.discoverPTX8
# end of class PTX8Bible



def __processPTX8Bible( parametersTuple ): # for demo
    """
    Special shim function used for multiprocessing.
    """
    codeLetter, mainFolderName, subFolderName = parametersTuple
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 {} Trying {}".format( codeLetter, subFolderName ) )
    PTX8_Bible = PTX8Bible( mainFolderName, subFolderName )
    PTX8_Bible.load()
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
        BBB = 'JN1'
        if BBB in PTX8_Bible:
            PTX8_Bible.books[BBB].debugPrint()
            for entryKey in PTX8_Bible.books[BBB]._CVIndex:
                print( BBB, entryKey, PTX8_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )
# end of __processPTX8Bible


def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for standardTestFolder in (
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                            'MadeUpFolder/',
                            ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nStandard testfolder is: {}".format( standardTestFolder ) )
            result1 = PTX8BibleFileCheck( standardTestFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA1", result1 )
            result2 = PTX8BibleFileCheck( standardTestFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA2", result2 )
            result3 = PTX8BibleFileCheck( standardTestFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX8 TestA3", result3 )

    specificTestFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/MBTV/' )
    if 0: # specify specificTestFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 B/ Trying single module in {}".format( specificTestFolder ) )
        PTX8_Bible = PTX8Bible( specificTestFolder )
        PTX8_Bible.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX8_Bible )

    if 00: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 C/ Trying installed {} module".format( singleModule ) )
        PTX8_Bible = PTX8Bible( specificTestFolder, singleModule )
        PTX8_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in PTX8_Bible:
                PTX8_Bible.books[BBB].debugPrint()
                for entryKey in PTX8_Bible.books[BBB]._CVIndex:
                    print( BBB, entryKey, PTX8_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 00: # specified installed modules
        good = ( '',)
        nonEnglish = ( '', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( specificTestFolder, testFilename+'/' )
            #testFilepath = os.path.join( specificTestFolder, testFilename+'/', testFilename+'_utf8.txt' )
            PTX8_Bible = PTX8Bible( specificTestFolder, testFilename )
            PTX8_Bible.load()

    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( specificTestFolder ):
            somepath = os.path.join( specificTestFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('E',specificTestFolder,folderName) for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processPTX8Bible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( specificTestFolder, someFolder+'/' )
                PTX8Bible( specificTestFolder, someFolder )

    if 0 and debuggingThisModule: # Test statistics discovery and creation of BDB stats page
        testFolders = (
                    ( 'Test1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/') ),
                    ( 'Test2', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/') ),
                    ( 'MBTV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTV' ) ),
                    ( 'MBTBT', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTBT' ) ),
                    ( 'MBTBC', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects/MBTBC' ) ),
                    ) # You can put your PTX8 test folder here

        for testName,testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX8_Bible = PTX8Bible( testFolder )
                PTX8_Bible.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX8_Bible )
                if BibleOrgSysGlobals.strictCheckingFlag: PTX8_Bible.check()

                #DBErrors = PTX8_Bible.getErrors()
                # print( DBErrors )
                #print( PTX8_Bible.getVersification() )
                #print( PTX8_Bible.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )

                # Print unloaded metadata filepaths
                if PTX8_Bible.filepathsNotYetLoaded and BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "\nFollowing {} file paths have not been processed in folder {}:" \
                                .format( len(PTX8_Bible.filepathsNotYetLoaded), testFolder ) )
                    for filepath in PTX8_Bible.filepathsNotYetLoaded:
                        print( "  Failed to load PTX8 file: {}".format( filepath ) )
                    print()

                # Test discovery code
                try:
                    if PTX8_Bible.discoveryResults is None: # (Can be already done above in strict-checking mode)
                        PTX8_Bible.discover() # Quite time-consuming
                except AttributeError: # no discoveryResults variable yet
                    PTX8_Bible.discover() # Quite time-consuming

                if 0: # Test BDB code for display PTX8 metadata files
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( "Creating test settings page for {}…".format( testName ) )
                    import sys; sys.path.insert( 0, BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../home/autoprocesses/Scripts/' ) )
                    from ProcessTemplates import webPageTemplate, doGlobalTemplateFixes
                    readyWebPageTemplate = doGlobalTemplateFixes( 'Test', testName, "Test", webPageTemplate )
                    from ProcessLoadedBible import makeSettingsPage
                    outputFolderPath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BDBSettingsPages/' )
                    if not os.path.exists( outputFolderPath ):
                            os.makedirs( outputFolderPath, 0o755 )
                    makeSettingsPage( 'Matigsalug', PTX8_Bible, readyWebPageTemplate, outputFolderPath )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    if 1:
        # Look at various projects inside various copies of the Paratext 8 folder made over time
        searchFolderName = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/' )
        searchFolderHead = 'My Paratext 8 Projects' # often followed by a date
        possibleProjectFolders = (
                    'engWEB14',
                    'MBTV', 'MBTBT', 'MBTBC',
                    'OET-BV', 'OET-LV', 'OET-RV', 'OET-CV', 'OET-SV', 'OET-EV'
                    )

        for something in sorted( os.listdir( searchFolderName ) ):
            somepath = os.path.join( searchFolderName, something )
            if os.path.isdir( somepath ):
                if something.startswith( searchFolderHead ):
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( "\n\nG Looking for projects in folder: {}".format( somepath ) )

                    for something2 in sorted( os.listdir( somepath ) ):
                        somepath2 = os.path.join( somepath, something2 )
                        if os.path.isdir( somepath2 ):
                            if something2 in possibleProjectFolders:
                                if BibleOrgSysGlobals.verbosityLevel > 0:
                                    print( "  Found {}".format( somepath2 ) )

                                if os.access( somepath2, os.R_OK ):
                                    PTX8_Bible = PTX8Bible( somepath2 )
                                    PTX8_Bible.loadBooks()
                                    if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX8_Bible )
                                    if BibleOrgSysGlobals.strictCheckingFlag: PTX8_Bible.check()
                                    #DBErrors = PTX8_Bible.getErrors()
                                    # print( DBErrors )
                                    #print( PTX8_Bible.getVersification() )
                                    #print( PTX8_Bible.getAddedUnits() )
                                    #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                                        ##print( "Looking for", ref )
                                        #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
                                else: print( "Sorry, test folder '{}' is not readable on this computer.".format( somepath2 ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( PROGRAM_NAME, PROGRAM_VERSION ) )
    #       pass

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of PTX8Bible.py
