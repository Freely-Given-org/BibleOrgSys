#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PTX7Bible.py
#
# Module handling UBS/SIL Paratext (PTX 7) collections of USFM2 Bible books
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
Module for defining and manipulating complete or partial Paratext 7 Bibles
    along with any enclosed metadata.

On typical Windows installations, Paratext 7 projects are in folders inside
    'C:\My Paratext Projects' and contain the project settings information
    in a .SSF (XML) file in the above folder (not in the project folder).

The Paratext 7 Bible (PTX7Bible) object contains USFM 2 BibleBooks.

The raw material for this module is produced by the UBS/SIL Paratext program
    if the File / Backup Project / To File… menu is used.

TODO: Check if PTX7Bible object should be based on USFM2Bible.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "Paratext7Bible"
PROGRAM_NAME = "Paratext-7 Bible handler"
PROGRAM_VERSION = '0.31'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import sys
import os
import logging
import multiprocessing
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible
from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames
from BibleOrgSys.Formats.USFM2BibleBook import USFM2BibleBook



MARKER_FILENAMES = ( 'AUTOCORRECT.TXT', 'BOOKNAMES.XML', 'CHECKINGSTATUS.XML', 'COMMENTTAGS.XML',
                    'LEXICON.XML', 'PRINTDRAFTCONFIGBASIC.XML', 'PROJECTUSERS.XML',
                    'PROJECTUSERFIELDS.XML', 'SPELLINGSTATUS.XML', 'USFM-COLOR.STY', ) # Must all be UPPER-CASE
EXCLUDE_FILENAMES = ( 'LICENSE.JSON', 'PROJECTUSERACCESS.XML', 'SETTINGS.XML', 'TERMRENDERINGS.XML', 'UNIQUE.ID', ) # Must all be UPPER-CASE
MARKER_FILE_EXTENSIONS = ( '.SSF', '.VRS', '.LDS' ) # Must all be UPPER-CASE plus shouldn't be included in the above filenames lists
EXCLUDE_FILE_EXTENSIONS = ( '.LDML', ) # Must all be UPPER-CASE plus shouldn't be included in the above filenames lists
MARKER_THRESHOLD = 3 # How many of the above must be found


def PTX7BibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Paratext Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one Paratext Bible bundle is found,
        returns the loaded PTX7Bible object.
    """
    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "PTX7BibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        assert givenFolderName and isinstance( givenFolderName, str )
        assert strictCheck in (True,False,)
        assert autoLoad in (True,False,)
        assert autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("PTX7BibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        if debuggingThisModule: print ("  PTX7 returningA1", False )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PTX7BibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        if debuggingThisModule: print ("  PTX7 returningA2", False )
        return False

    # Check that there's a USFM Bible here first
    from BibleOrgSys.Formats.USFM2Bible import USFM2BibleFileCheck
    if not USFM2BibleFileCheck( givenFolderName, strictCheck, discountSSF=False ): # no autoloads
        if debuggingThisModule: print ("  PTX7 returningA3", False )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PTX7BibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
        print( "PTX7 numFilesFound1 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7BibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTX7Bible( givenFolderName )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            if debuggingThisModule: print ("  PTX7 returningB1", dB )
            return dB
        if debuggingThisModule: print ("  PTX7 returningB2", numFound )
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("PTX7BibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PTX7BibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
            print( "PTX7 numFilesFound2 is", numFilesFound, "Threshold is >=", MARKER_THRESHOLD )
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7BibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTX7Bible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            if debuggingThisModule: print ("  PTX7 returningC1", dB )
            return dB
        if debuggingThisModule: print ("  PTX7 returningC2", numFound )
        return numFound
    if debuggingThisModule: print ("  PTX7 returningN", None )
# end of PTX7BibleFileCheck



# The following loadPTX7…() functions are placed here because
#   they are also used by the DBL and/or other Bible importers
def loadPTX7ProjectData( BibleObject, ssfFilepath, encoding='utf-8' ):
    """
    Process the Paratext 7 SSF data file (XML) from the given filepath into PTXSettingsDict.

    Returns a dictionary.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( _("Loading Paratext 7 SSF data from {!r} ({})").format( ssfFilepath, encoding ) )
    #if encoding is None: encoding = 'utf-8'
    BibleObject.ssfFilepath = ssfFilepath

    PTXSettingsDict = {}

    # This is actually an XML file, but we'll assume it's nicely formed with one XML field per line
    lastLine, lineCount, status = '', 0, 0
    with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
        ssfData = myFile.read() # Read it all first
    #print( "ssfData", ssfData )

    # Handle Paratext 'bug' that produces XML files in different format
    ssfData = ssfData.replace( '></', '=QwErTy=' ) # Protect a blank field like in "<CallerSequence></CallerSequence>"
    ssfData = ssfData.replace( '><', '>\n<' )
    ssfData = ssfData.replace( '=QwErTy=', '></' )

    for line in ssfData.split( '\n' ):
        #print( "ssfData line", repr(line) )
        lineCount += 1
        if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
            logging.info( _("loadPTX7ProjectData: Detected Unicode Byte Order Marker (BOM) in {}").format( ssfFilepath ) )
            line = line[1:] # Remove the Byte Order Marker (BOM)
        #if line[-1]=='\n': line = line[:-1] # Remove trailing newline character
        line = line.strip() # Remove leading and trailing whitespace
        if not line: continue # Just discard blank lines
        lastLine = line
        processed = False
        if status==0 and line=="<ScriptureText>":
            status = 1
            processed = True
        elif status==1 and line=="</ScriptureText>":
            status = 9
            processed = True
        elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a BibleObject-closing (empty) field
            fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
            if ' ' not in fieldname:
                PTXSettingsDict[fieldname] = ''
                processed = True
            elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                bits = fieldname.split( None, 1 )
                if BibleOrgSysGlobals.debugFlag: assert len(bits)==2
                fieldname = bits[0]
                attributes = bits[1]
                #print( "attributes = {!r}".format( attributes) )
                PTXSettingsDict[fieldname] = (contents, attributes)
                processed = True
        elif status==1 and line[0]=='<' and line[-1]=='>' and '/' in line:
            ix1 = line.find('>')
            ix2 = line.find('</')
            if ix1!=-1 and ix2!=-1 and ix2>ix1:
                fieldname = line[1:ix1]
                contents = line[ix1+1:ix2]
                if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                    PTXSettingsDict[fieldname] = contents
                    processed = True
                elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                    bits = fieldname.split( None, 1 )
                    if BibleOrgSysGlobals.debugFlag: assert len(bits)==2
                    fieldname = bits[0]
                    attributes = bits[1]
                    #print( "attributes = {!r}".format( attributes) )
                    if line[ix2+2:-1]==fieldname:
                        PTXSettingsDict[fieldname] = (contents, attributes)
                        processed = True
        elif status==1 and line.startswith( '<ValidCharacters>' ):
            fieldname = 'ValidCharacters'
            contents = line[len(fieldname)+2:]
            #print( "Got {} opener {!r} from {!r}".format( fieldname, contents, line ) )
            status = 2
            processed = True
        elif status==2: # in the middle of processing an extension line
            if line.endswith( '</' + fieldname + '>' ):
                line = line[:-len(fieldname)-3]
                status = 1
            contents += ' ' + line
            #print( "Added {!r} to get {!r} for {}".format( line, contents, fieldname ) )
            processed = True
        if not processed: print( _("ERROR: Unexpected {} line in PTX7 SSF file").format( repr(line) ) )
    if status == 0:
        logging.critical( _("PTX7 SSF file was empty: {}").format( BibleObject.ssfFilepath ) )
        status = 9
    if status != 9:
        logging.critical( _("PTX7 SSF file parsing error: {}").format( BibleObject.ssfFilepath ) )
    if BibleOrgSysGlobals.debugFlag: assert status == 9
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  " + _("Got {} PTX7 SSF entries:").format( len(PTXSettingsDict) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for key in sorted(PTXSettingsDict):
                print( "    {}: {}".format( key, PTXSettingsDict[key] ) )

    #BibleObject.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

    ## Determine our encoding while we're at it
    #if BibleObject.encoding is None and 'Encoding' in PTXSettingsDict: # See if the SSF file gives some help to us
        #ssfEncoding = PTXSettingsDict['Encoding']
        #if ssfEncoding == '65001': BibleObject.encoding = 'utf-8'
        #else:
            #if BibleOrgSysGlobals.verbosityLevel > 0:
                #print( _("__init__: File encoding in SSF is set to {!r}").format( ssfEncoding ) )
            #if ssfEncoding.isdigit():
                #BibleObject.encoding = 'cp' + ssfEncoding
                #if BibleOrgSysGlobals.verbosityLevel > 0:
                    #print( _("__init__: Switched to {!r} file encoding").format( BibleObject.encoding ) )
            #else:
                #logging.critical( _("__init__: Unsure how to handle {!r} file encoding").format( ssfEncoding ) )

    #print( 'PTXSettingsDict', PTXSettingsDict )
    return PTXSettingsDict
# end of loadPTX7ProjectData



def loadPTX7Languages( BibleObject ):
    """
    Load the something.lds file (which is an INI file) and parse it into the dictionary PTXLanguages.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( _("loadPTX7Languages()") )

    languageFilenames = []
    for something in os.listdir( BibleObject.sourceFilepath ):
        somepath = os.path.join( BibleObject.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.LDS'): languageFilenames.append( something )
    #if len(languageFilenames) > 1:
        #logging.error( "Got more than one language file: {}".format( languageFilenames ) )
    if not languageFilenames: return

    PTXLanguages = {}

    for languageFilename in languageFilenames:
        languageName = languageFilename[:-4] # Remove the .lds

        languageFilepath = os.path.join( BibleObject.sourceFilepath, languageFilename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading language from {}…".format( languageFilepath ) )

        assert languageName not in PTXLanguages
        PTXLanguages[languageName] = {}

        lineCount = 0
        sectionName = None
        with open( languageFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTX7Languages: Detected Unicode Byte Order Marker (BOM) in {}".format( languageFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "line", repr(line) )

                if len(line)<5:
                    if debuggingThisModule: print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    continue

                if line[0]=='[' and line[-1]==']': # it's a new section name
                    sectionName = line[1:-1]
                    assert sectionName not in PTXLanguages[languageName]
                    PTXLanguages[languageName][sectionName] = {}
                elif '=' in line: # it's a mapping, e.g., UpperCaseLetters=ABCDEFGHIJKLMNOPQRSTUVWXYZ
                    left, right = line.split( '=', 1 )
                    #print( "left", repr(left), 'right', repr(right) )
                    PTXLanguages[languageName][sectionName][left] = right
                else: print( "What's this language line? {!r}".format( line ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} languages.".format( len(PTXLanguages) ) )
    #print( 'PTXLanguages', PTXLanguages )
    return PTXLanguages
# end of PTX7Bible.loadPTX7Languages



def loadPTXVersifications( BibleObject ):
    """
    Load the versification files (which is a text file)
        and parse it into the dictionary PTXVersifications.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( _("loadPTXVersifications()") )

    #versificationFilename = 'versification.vrs'
    #versificationFilepath = os.path.join( BibleObject.sourceFilepath, versificationFilename )
    #if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading versification from {}…".format( versificationFilepath ) )

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
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading versification from {}…".format( versificationFilepath ) )

        assert versificationName not in PTXVersifications
        PTXVersifications[versificationName] = {}

        lineCount = 0
        with open( versificationFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXVersifications: Detected Unicode Byte Order Marker (BOM) in {}".format( versificationFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#' and not line.startswith('#!'): continue # Just discard comment lines
                #print( versificationName, "versification line", repr(line) )

                if len(line)<7:
                    print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
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
                        logging.error( "Unknown {!r} USFM book code in loadPTXVersifications from {}".format( USFMBookCode, versificationFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} versifications.".format( len(PTXVersifications) ) )
    #print( 'PTXVersifications', PTXVersifications )
    return PTXVersifications
# end of PTX7Bible.loadPTXVersifications



class PTX7Bible( Bible ):
    """
    Class to load and manipulate Paratext Bible bundles.

    The PTX7Bible object contains USFM 2 BibleBooks.
        (i.e., there's not PTX7BibleBook object types.)
    """
    def __init__( self, givenFolderName, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Create the internal Paratext Bible object.
        """
        if debuggingThisModule:
            print( "PTX7Bible.__init__( {!r}, {!r}, {!r}, {!r} )".format( givenFolderName, givenName, givenAbbreviation, encoding ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Paratext-7 Bible object'
        self.objectTypeString = 'PTX7'

        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = givenFolderName, givenName, givenAbbreviation, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        if givenName:
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.error( "PTX7Bible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        else: self.sourceFilepath = self.sourceFolder
        #print( "HEREPTX7 self.sourceFilepath:", repr( self.sourceFilepath ) )
        if self.sourceFilepath and not os.access( self.sourceFilepath, os.R_OK ):
            logging.error( "PTX7Bible: Folder '{}' is unreadable".format( self.sourceFilepath ) )

        self.ssfFilepath = None

        # Create empty containers for loading the XML metadata files
        #projectUsersDict = self.PTXStyles = self.PTXVersification = self.PTXLanguage = None
    # end of PTX7Bible.__init__


    def preload( self ):
        """
        Loads the SSF file if it can be found.
        Loads other metadata files that are provided.
        Tries to determine USFM filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("preload() from {}").format( self.sourceFolder ) )
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
            else: logging.error( _("preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("PTX7 preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( _("preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['PTX7'] = {}

        if self.ssfFilepath is None: # it might have been loaded first
            # Attempt to load the SSF file
            #self.suppliedMetadata, self.settingsDict = {}, {}
            ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            #print( "ssfFilepathList", ssfFilepathList )
            if len(ssfFilepathList) > 1:
                logging.error( _("preload: Found multiple possible SSF files -- using first one: {}").format( ssfFilepathList ) )
            if len(ssfFilepathList) >= 1: # Seems we found the right one
                PTXSettingsDict = loadPTX7ProjectData( self, ssfFilepathList[0] )
                if PTXSettingsDict:
                    self.suppliedMetadata['PTX7']['SSF'] = PTXSettingsDict
                    self.applySuppliedMetadata( 'SSF' ) # Copy some to self.settingsDict

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
            self.loadPTX7ProjectUsers() # from XML (if it exists)
            if 'ProjectUsers' in self.suppliedMetadata['PTX7']:
                self.loadPTX7ProjectUserFields() # from XML (if it exists)
            self.loadPTXLexicon() # from XML (if it exists)
            self.loadPTXSpellingStatus() # from XML (if it exists)
            self.loadPTXComments() # from XML (if they exist) but we don't do the CommentTags.xml file yet
            self.loadPTXBiblicalTermRenderings() # from XML (if they exist)
            self.loadPTXProgress() # from XML (if it exists)
            self.loadPTXPrintConfig()  # from XML (if it exists)
            self.loadPTXAutocorrects() # from text file (if it exists)
            self.loadPTXStyles() # from text files (if they exist)
            result = loadPTXVersifications( self ) # from text file (if it exists)
            if result: self.suppliedMetadata['PTX7']['Versifications'] = result
            result = loadPTX7Languages( self ) # from INI file (if it exists)
            if result: self.suppliedMetadata['PTX7']['Languages'] = result
        else: # normal operation
            # Put all of these in try blocks so they don't crash us if they fail
            try: self.loadPTXBooksNames() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXBooksNames failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                self.loadPTX7ProjectUsers() # from XML (if it exists)
                if 'ProjectUsers' in self.suppliedMetadata['PTX7']:
                    self.loadPTX7ProjectUserFields() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTX7ProjectUsers failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXLexicon() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXLexicon failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXSpellingStatus() # from XML (if it exists)
            except Exception as err: logging.error( 'loadPTXSpellingStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXComments() # from XML (if they exist) but we don't do the CommentTags.xml file yet
            except Exception as err: logging.error( 'loadPTXComments failed with {} {}'.format( sys.exc_info()[0], err ) )
            try: self.loadPTXBiblicalTermRenderings() # from XML (if they exist)
            except Exception as err: logging.error( 'loadPTXBiblicalTermRenderings failed with {} {}'.format( sys.exc_info()[0], err ) )
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
                if result: self.suppliedMetadata['PTX7']['Versifications'] = result
            except Exception as err: logging.error( 'loadPTXVersifications failed with {} {}'.format( sys.exc_info()[0], err ) )
            try:
                result = loadPTX7Languages( self ) # from INI file (if it exists)
                if result: self.suppliedMetadata['PTX7']['Languages'] = result
            except Exception as err: logging.error( 'loadPTX7Languages failed with {} {}'.format( sys.exc_info()[0], err ) )

        self.preloadDone = True
    # end of PTX7Bible.preload


    def loadPTXBooksNames( self ):
        """
        Load the BookNames.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXBooksNames()") )

        thisFilename = 'BookNames.xml'
        bookNamesFilepath = os.path.join( self.sourceFilepath, thisFilename )
        if not os.path.exists( bookNamesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading books names data from {}…".format( bookNamesFilepath ) )
        self.XMLTree = ElementTree().parse( bookNamesFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        booksNamesDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='BookNames':
            treeLocation = "PTX7 {} file".format( self.XMLTree.tag )
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
                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    #print( bnCode, booksNamesDict[bnCode] )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert len(bnCode)==3
                    try: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bnCode )
                    except:
                        logging.warning( "loadPTXBooksNames can't find BOS code for PTX7 {!r} book".format( bnCode ) )
                        BBB = bnCode # temporarily use their code
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert BBB not in booksNamesDict
                    booksNamesDict[BBB] = (bnCode,bnAbbr,bnShort,bnLong,)
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, thisFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} book names.".format( len(booksNamesDict) ) )
        #print( "booksNamesDict", booksNamesDict )
        if booksNamesDict: self.suppliedMetadata['PTX7']['BooksNames'] = booksNamesDict
    # end of PTX7Bible.loadPTXBooksNames


    def loadPTX7ProjectUsers( self ):
        """
        Load the ProjectUsers.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTX7ProjectUsers()") )

        thisFilename = 'ProjectUsers.xml'
        projectUsersFilepath = os.path.join( self.sourceFilepath, thisFilename )
        if not os.path.exists( projectUsersFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading project user data from {}…".format( projectUsersFilepath ) )
        self.XMLTree = ElementTree().parse( projectUsersFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        projectUsersDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='ProjectUsers':
            treeLocation = "PTX7 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Process the attributes first
            peerSharingFlag = None
            for attrib,value in self.XMLTree.items():
                if attrib=='PeerSharing': peerSharingFlag = value
                else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
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
                    userName = firstUserFlag = None
                    for attrib,value in element.items():
                        if attrib=='UserName': userName = value
                        elif attrib=='FirstUser': firstUserFlag = value
                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if 'Users' not in projectUsersDict: projectUsersDict['Users'] = {}
                    assert userName not in projectUsersDict['Users'] # no duplicates allowed presumably
                    projectUsersDict['Users'][userName] = {}
                    projectUsersDict['Users'][userName]['FirstUserFlag'] = firstUserFlag

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag in ('Role', 'AllBooks', 'Books', ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in projectUsersDict['Users'][userName]
                            projectUsersDict['Users'][userName][subelement.tag] = subelement.text
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, thisFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(projectUsersDict['Users']) ) )
        #print( "projectUsersDict", projectUsersDict )
        if projectUsersDict: self.suppliedMetadata['PTX7']['ProjectUsers'] = projectUsersDict
    # end of PTX7Bible.loadPTX7ProjectUsers


    def loadPTX7ProjectUserFields( self ):
        """
        Load the ProjectUserFields.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTX7ProjectUserFields()") )

        thisFilename = 'ProjectUserFields.xml'
        projectUsersFilepath = os.path.join( self.sourceFilepath, thisFilename )
        if not os.path.exists( projectUsersFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading project user field data from {}…".format( projectUsersFilepath ) )
        self.XMLTree = ElementTree().parse( projectUsersFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        projectUsersDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='ProjectUserFields':
            treeLocation = "PTX7 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Process the attributes first
            peerSharing = None
            for attrib,value in self.XMLTree.items():
                if attrib=='PeerSharing': peerSharing = value
                else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            projectUsersDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.XMLTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #print( "Processing {}…".format( elementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )

                # Now process the subelements
                if element.tag == 'User':
                    # Process the user attributes first
                    userName = firstUserFlag = None
                    for attrib,value in element.items():
                        if attrib=='UserName': userName = value
                        elif attrib=='FirstUser': firstUserFlag = value
                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if 'Users' not in projectUsersDict: projectUsersDict['Users'] = {}
                    assert userName not in projectUsersDict['Users'] # no duplicates allowed presumably
                    projectUsersDict['Users'][userName] = {}
                    projectUsersDict['Users'][userName]['FirstUser'] = firstUserFlag

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag in ('Role', 'AllBooks', 'Books', ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in projectUsersDict['Users'][userName]
                            projectUsersDict['Users'][userName][subelement.tag] = subelement.text
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, thisFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(projectUsersDict['Users']) ) )
        #print( "projectUsersDict", projectUsersDict )
        if projectUsersDict: self.suppliedMetadata['PTX7']['ProjectUserFields'] = projectUsersDict
    # end of PTX7Bible.loadPTX7ProjectUserFields


    def loadPTXLexicon( self ):
        """
        Load the Lexicon.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXLexicon()") )

        thisFilename = 'Lexicon.xml'
        lexiconFilepath = os.path.join( self.sourceFilepath, thisFilename )
        if not os.path.exists( lexiconFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading project user data from {}…".format( lexiconFilepath ) )
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
                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                    #print( "Lexeme {} form={!r} homograph={}".format( lexemeType, lexemeForm, lexemeHomograph ) )
                    assert lexemeType in ( 'Word', 'Phrase', )
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
                                else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
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
                                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub2location ) )
                                assert senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs']
                                lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'][senseID] = (sub3element.text, glossLanguage)
                        else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, elementLocation ) )
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
        # end of processLexiconItem


        # Find the main container
        if self.XMLTree.tag=='Lexicon':
            treeLocation = "PTX7 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.XMLTree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            #lexiconDict['PeerSharing'] = peerSharing

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
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, thisFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} lexicon entries.".format( len(lexiconDict['Entries']) ) )
        #print( "lexiconDict", lexiconDict )
        if lexiconDict: self.suppliedMetadata['PTX7']['Lexicon'] = lexiconDict
    # end of PTX7Bible.loadPTXLexicon


    def loadPTXSpellingStatus( self ):
        """
        Load the SpellingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXSpellingStatus()") )

        thisFilename = 'SpellingStatus.xml'
        spellingStatusFilepath = os.path.join( self.sourceFilepath, thisFilename )
        if not os.path.exists( spellingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading spelling status data from {}…".format( spellingStatusFilepath ) )
        self.XMLTree = ElementTree().parse( spellingStatusFilepath )
        assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        spellingStatusDict = {}
        #loadErrors = []

        # Find the main container
        if self.XMLTree.tag=='SpellingStatus':
            treeLocation = "PTX7 {} file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.XMLTree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
            #spellingStatusDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.XMLTree:
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
                        elif attrib=='State': state = value; assert state in 'RW' # right/wrong
                        else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if 'SpellingWords' not in spellingStatusDict: spellingStatusDict['SpellingWords'] = {}
                    assert word not in spellingStatusDict['SpellingWords'] # no duplicates allowed presumably
                    spellingStatusDict['SpellingWords'][word] = {}
                    spellingStatusDict['SpellingWords'][word]['State'] = state

                    for subelement in element:
                        sublocation = subelement.tag + ' ' + elementLocation
                        #print( "  Processing {}…".format( sublocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                        if subelement.tag in ( 'SpecificCase', 'Correction', ):
                            #if BibleOrgSysGlobals.debugFlag: assert subelement.text # These can be blank!
                            assert subelement.tag not in spellingStatusDict['SpellingWords'][word]
                            spellingStatusDict['SpellingWords'][word][subelement.tag] = subelement.text
                        else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
        else:
            logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, thisFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} spelling status entries.".format( len(spellingStatusDict['SpellingWords']) ) )
        #print( "spellingStatusDict", spellingStatusDict )
        if spellingStatusDict: self.suppliedMetadata['PTX7']['SpellingStatus'] = spellingStatusDict
    # end of PTX7Bible.loadPTXSpellingStatus


    def loadPTXComments( self ):
        """
        Load the Comments_*.xml files (if they exist) and parse them into the dictionary self.suppliedMetadata['PTX7'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXComments()") )

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
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading comments from {}…".format( commentFilepath ) )

            self.XMLTree = ElementTree().parse( commentFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.XMLTree.tag=='CommentList':
                treeLocation = "PTX7 {} file for {}".format( self.XMLTree.tag, commenterName )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

                ## Process the attributes first
                #peerSharing = None
                #for attrib,value in self.XMLTree.items():
                    #if attrib=='PeerSharing': peerSharing = value
                    #else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                #commentsList['PeerSharing'] = peerSharing

                # Now process the actual entries
                for element in self.XMLTree:
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
                            #else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                        #if 'SpellingWords' not in commentsList: commentsList['SpellingWords'] = {}
                        #assert word not in commentsList['SpellingWords'] # no duplicates allowed presumably

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
                logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, commentFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} commenters.".format( len(commentsList) ) )
        #print( "commentsList", commentsList )
        # Call this 'PTXComments' rather than just 'Comments' which might just be a note on the particular version
        if commentsList: self.suppliedMetadata['PTX7']['PTXComments'] = commentsList
    # end of PTX7Bible.loadPTXComments


    def loadPTXBiblicalTermRenderings( self ):
        """
        Load the BiblicalTerms*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX7'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXBiblicalTermRenderings()") )

        BiblicalTermsFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somethingUPPER = something.upper()
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and somethingUPPER.startswith('BIBLICALTERMS') and somethingUPPER.endswith('.XML'):
                BiblicalTermsFilenames.append( something )
        #if len(BiblicalTermsFilenames) > 1:
            #logging.error( "Got more than one BiblicalTerms file: {}".format( BiblicalTermsFilenames ) )
        if not BiblicalTermsFilenames: return

        BiblicalTermsDict = {}
        #loadErrors = []

        for BiblicalTermsFilename in BiblicalTermsFilenames:
            versionName = BiblicalTermsFilename[13:-4] # Remove the .xml
            assert versionName not in BiblicalTermsDict
            BiblicalTermsDict[versionName] = {}

            BiblicalTermsFilepath = os.path.join( self.sourceFilepath, BiblicalTermsFilename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading BiblicalTerms from {}…".format( BiblicalTermsFilepath ) )

            self.XMLTree = ElementTree().parse( BiblicalTermsFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.XMLTree.tag=='TermRenderingsList':
                treeLocation = "PTX7 {} file for {}".format( self.XMLTree.tag, versionName )
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
                    if element.tag == 'Renderings':
                        for subelement in element:
                            sublocation = subelement.tag + ' ' + elementLocation
                            #print( "  Processing {}…".format( sublocation ) )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                            termRenderingDict = {}
                            if subelement.tag == 'TermRendering':
                                for sub2element in subelement:
                                    sub2location = sub2element.tag + ' ' + sublocation
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                                    assert subelement.tag not in termRenderingDict # No duplicates please
                                    if sub2element.tag in ( 'Id', 'Guess', 'Tag', 'Notes', ):
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                        termRenderingDict[sub2element.tag] = sub2element.text # can be None
                                    elif sub2element.tag == 'Renderings':
                                        # This seems to be a string containing a comma separated list!
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                        termRenderingDict[sub2element.tag] = sub2element.text.split( ', ' ) if sub2element.text else None
                                    #elif sub2element.tag == 'Notes':
                                        #termRenderingDict[sub2element.tag] = []
                                        #for sub3element in sub2element:
                                            #sub3location = sub3element.tag + ' ' + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location )
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                            #termRenderingDict[sub2element.tag].append( sub3element.text )
                                    elif sub2element.tag == 'Denials':
                                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                                        termRenderingDict[sub2element.tag] = []
                                        for sub3element in sub2element:
                                            sub3location = sub3element.tag + ' ' + sub2location
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                            if sub3element.tag == 'VerseRef':
                                                # Process the VerseRef attributes first
                                                versification = None
                                                for attrib,value in sub3element.items():
                                                    if attrib=='Versification': versification = value
                                                    else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                                termRenderingDict[sub2element.tag].append( (sub3element.text,versification) )
                                            else: logging.error( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                            #print( "termRenderingDict", termRenderingDict ); halt
                                    else: logging.error( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                            #print( "termRenderingDict", termRenderingDict )
                            Id = termRenderingDict['Id']
                            del termRenderingDict['Id']
                            assert Id not in BiblicalTermsDict[versionName] # No duplicate ids allowed
                            BiblicalTermsDict[versionName][Id] = termRenderingDict
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    #print( "termRenderingDict", termRenderingDict )
                    #BiblicalTermsDict[versionName].append( termRenderingDict )
            else:
                logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, BiblicalTermsFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} Biblical terms.".format( len(BiblicalTermsDict) ) )
        #print( "BiblicalTermsDict", BiblicalTermsDict )
        #print( BiblicalTermsDict['MBTV']['חָנוּן'] )
        if BiblicalTermsDict: self.suppliedMetadata['PTX7']['BiblicalTerms'] = BiblicalTermsDict
    # end of PTX7Bible.loadPTXBiblicalTermRenderings


    def loadPTXProgress( self ):
        """
        Load the Progress*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX7'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXProgress()") )

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
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading Progress from {}…".format( progressFilepath ) )

            self.XMLTree = ElementTree().parse( progressFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.XMLTree.tag=='ProjectProgress':
                treeLocation = "PTX7 {} file for {}".format( self.XMLTree.tag, versionName )
                BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
                BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

                # Now process the actual entries
                for element in self.XMLTree:
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
                                    else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
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
                                                    else: logging.error( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
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
                logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, progressFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} progress.".format( len(progressDict) ) )
        #print( "progressDict", progressDict )
        if progressDict: self.suppliedMetadata['PTX7']['Progress'] = progressDict
    # end of PTX7Bible.loadPTXProgress


    def loadPTXPrintConfig( self ):
        """
        Load the PrintConfig*.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata['PTX7'].
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXPrintConfig()") )

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
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading PrintConfig from {}…".format( printConfigFilepath ) )

            self.XMLTree = ElementTree().parse( printConfigFilepath )
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

            # Find the main container
            if self.XMLTree.tag=='PrintDraftConfiguration':
                treeLocation = "PTX7 {} file for {}".format( self.XMLTree.tag, printConfigType )
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
                            else: logging.error( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sublocation ) )
                    else:
                        logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    #print( "bookStatusDict", bookStatusDict )
                    #printConfigDict[printConfigType].append( bookStatusDict )
            else:
                logging.critical( _("Unprocessed {} tree in {}").format( self.XMLTree.tag, printConfigFilename ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} printConfig.".format( len(printConfigDict) ) )
        #print( "printConfigDict", printConfigDict )
        if printConfigDict: self.suppliedMetadata['PTX7']['PrintConfig'] = printConfigDict
    # end of PTX7Bible.loadPTXPrintConfig


    def loadPTXAutocorrects( self ):
        """
        Load the AutoCorrect.txt file (which is a text file)
            and parse it into the ordered dictionary PTXAutocorrects.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXAutocorrects()") )

        autocorrectFilename = 'AutoCorrect.txt'
        autocorrectFilepath = os.path.join( self.sourceFilepath, autocorrectFilename )
        if not os.path.exists( autocorrectFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading autocorrect from {}…".format( autocorrectFilepath ) )
        PTXAutocorrects = {}

        lineCount = 0
        with open( autocorrectFilepath, 'rt', encoding='utf-8' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXAutocorrects: Detected Unicode Byte Order Marker (BOM) in {}".format( autocorrectFilename ) )
                    line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "Autocorrect line", repr(line) )

                if BibleOrgSysGlobals.verbosityLevel > 0:
                    if len(line)<4:
                        print( "Why was PTX7 autocorrect line #{} so short? {!r}".format( lineCount, line ) )
                        continue
                    if len(line)>8:
                        print( "Why was PTX7 autocorrect line #{} so long? {!r}".format( lineCount, line ) )

                if '-->' in line:
                    bits = line.split( '-->', 1 )
                    #print( 'bits', bits )
                    PTXAutocorrects[bits[0]] = bits[1]
                else: logging.error( "Invalid {!r} autocorrect line in PTX7Bible.loading autocorrect".format( line ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} autocorrect elements.".format( len(PTXAutocorrects) ) )
        #print( 'PTXAutocorrects', PTXAutocorrects )
        if PTXAutocorrects: self.suppliedMetadata['PTX7']['Autocorrects'] = PTXAutocorrects
    # end of PTX7Bible.loadPTXAutocorrects


    def loadPTXStyles( self ):
        """
        Load the something.sty file (which is a SFM file) and parse it into the dictionary PTXStyles.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("loadPTXStyles()") )

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
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTX7Bible.loading style from {}…".format( styleFilepath ) )

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
                            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            if not line: continue # Just discard blank lines
                            lastLine = line
                            if line[0]=='#': continue # Just discard comment lines
                            #print( lineCount, "line", repr(line) )

                            if len(line)<5: # '\Bold' is the shortest valid line
                                logging.warning( "Why was PTX7 style line #{} so short? {!r}".format( lineCount, line ) )
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
        #print( 'PTXStyles', PTXStyles )
        if PTXStyles: self.suppliedMetadata['PTX7']['Styles'] = PTXStyles
    # end of PTX7Bible.loadPTXStyles


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "PTX7Bible.loadBook( {}, {} )".format( BBB, filename ) )

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  PTX7Bible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "PTX7Bible.loadBook: Unable to find file for {}".format( BBB ) )
        UBB = USFM2BibleBook( self, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.stashBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
        self.bookNeedsReloading[BBB] = False
    # end of PTX7Bible.loadBook


    def _loadBookMP( self, BBB_Filename ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("loadBookMP( {} )").format( BBB_Filename ) )

        BBB, filename = BBB_Filename
        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return self.books[BBB] # Already loaded
        #if BBB in self.triedLoadingBook:
            #logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            #return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( '  ' + _("Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFM2BibleBook( self, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of PTX7Bible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading {} from {}…").format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( _("Loading {} PTX7 books using {} processes…").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  PTX7Bible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    #if BBB not in self.books and not self.bookNeedsReloading[BBB]:
                    self.loadBook( BBB, filename ) # also saves it in our Bible object
        else:
            logging.critical( "PTX7Bible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of PTX7Bible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class PTX7Bible



def __processPTX7Bible( parametersTuple ): # for demo
    """
    Special shim function used for multiprocessing.
    """
    codeLetter, mainFolderName, subFolderName = parametersTuple
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX7 {} Trying {}".format( codeLetter, subFolderName ) )
    PTX7_Bible = PTX7Bible( mainFolderName, subFolderName )
    PTX7_Bible.load()
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
        BBB = 'JN1'
        if BBB in PTX7_Bible:
            PTX7_Bible.books[BBB].debugPrint()
            for entryKey in PTX7_Bible.books[BBB]._CVIndex:
                print( BBB, entryKey, PTX7_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )
# end of __processPTX7Bible


def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in (
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/'),
                            "OutputFiles/BOS_USFM2_Export/",
                            "OutputFiles/BOS_USFM2_Reexport/",
                            "OutputFiles/BOS_USFM3_Export/",
                            "OutputFiles/BOS_USFM3_Reexport/",
                            "MadeUpFolder/",
                            ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nTestfolder is: {}".format( testFolder ) )
            result1 = PTX7BibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX7 TestA1", result1 )
            result2 = PTX7BibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX7 TestA2", result2 )
            result3 = PTX7BibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX7 TestA3", result3 )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' )
    if 1: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX7 B/ Trying single module in {}".format( testFolder ) )
        PTX_Bible = PTX7Bible( testFolder )
        PTX_Bible.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )

    if 1: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX7 C/ Trying installed {} module".format( singleModule ) )
        PTX_Bible = PTX7Bible( testFolder, singleModule )
        PTX_Bible.load()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in PTX_Bible:
                PTX_Bible.books[BBB].debugPrint()
                for entryKey in PTX_Bible.books[BBB]._CVIndex:
                    print( BBB, entryKey, PTX_Bible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 1: # specified installed modules
        good = ( '',)
        nonEnglish = ( '', )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX7 D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            PTX_Bible = PTX7Bible( testFolder, testFilename )
            PTX_Bible.load()


    if 1: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('E',testFolder,folderName) for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processPTX7Bible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX7 E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                PTX7Bible( testFolder, someFolder )
    if 1:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                    ) # You can put your PTX7 test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTX7Bible( testFolder )
                PTX_Bible.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )
                if BibleOrgSysGlobals.strictCheckingFlag: PTX_Bible.check()
                #DBErrors = PTX_Bible.getErrors()
                # print( DBErrors )
                #print( PTX_Bible.getVersification() )
                #print( PTX_Bible.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    if 1:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/acfPTX 2013-02-03' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/aucPTX 2013-02-26' ),
                    ) # You can put your PTX7 test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTX7Bible( testFolder )
                PTX_Bible.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( PTX_Bible )
                if BibleOrgSysGlobals.strictCheckingFlag: PTX_Bible.check()
                #DBErrors = PTX_Bible.getErrors()
                # print( DBErrors )
                #print( PTX_Bible.getVersification() )
                #print( PTX_Bible.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

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
# end of PTX7Bible.py
