#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# PTXBible.py
#
# Module handling UBS Paratext (PTX) collections of USFM Bible books
#                                   along with XML and other metadata
#
# Copyright (C) 2015 Robert Hunt
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
Module for defining and manipulating complete or partial Paratext Bibles
    along with any enclosed metadata.

The raw material for this module is produced by the UBS Paratext program
    if the File / Backup Project / To File... menu is used.
"""

from gettext import gettext as _

LastModifiedDate = '2015-06-11' # by RJH
ShortProgName = "ParatextBible"
ProgName = "Paratext Bible handler"
ProgVersion = '0.03'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import os, logging
from collections import OrderedDict
import multiprocessing
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals
from Bible import Bible
from USFMFilenames import USFMFilenames
from USFMBibleBook import USFMBibleBook



MARKER_FILENAMES = ( 'AUTOCORRECT.TXT', 'BOOKNAMES.XML', 'CHECKINGSTATUS.XML', 'COMMENTTAGS.XML',
                    'LEXICON.XML', 'PRINTDRAFTCONFIGBASIC.XML', 'PROJECTUSERS.XML',
                    'PROJECTUSERFIELDS.XML', 'SPELLINGSTATUS.XML', 'USFM-COLOR.STY', ) # Must all be UPPER-CASE
MARKER_FILE_EXTENSIONS = ( '.SSF', '.VRS', '.LDS' ) # Must all be UPPER-CASE plus shouldn't be included in the above list
MARKER_THRESHOLD = 3 # How many of the above must be found


def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )
# end of t



def PTXBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Paratext Bible bundles in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of bundles found.

    if autoLoad is true and exactly one Paratext Bible bundle is found,
        returns the loaded PTXBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "PTXBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag:
        assert( givenFolderName and isinstance( givenFolderName, str ) )
        assert( strictCheck in (True,False,) )
        assert( autoLoad in (True,False,) )
        assert( autoLoadBooks in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("PTXBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("PTXBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Check that there's a USFM Bible here first
    from USFMBible import USFMBibleFileCheck
    if not USFMBibleFileCheck( givenFolderName, strictCheck ): # no autoloads
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " PTXBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if the compulsory files are here in this given folder
    numFound = numFilesFound = numFoldersFound = 0
    for filename in foundFiles:
        filenameUpper = filename.upper()
        if filenameUpper in MARKER_FILENAMES: numFilesFound += 1
        for extension in MARKER_FILE_EXTENSIONS:
            if filenameUpper.endswith( extension ): numFilesFound += 1; break
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTXBible( givenFolderName )
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
            logging.warning( _("PTXBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    PTXBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
            for extension in MARKER_FILE_EXTENSIONS:
                if filenameUpper.endswith( extension ): numFilesFound += 1; break
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            dB = PTXBible( foundProjects[0] )
            if autoLoad or autoLoadBooks:
                dB.preload() # Load and process the metadata files
                if autoLoadBooks: dB.loadBooks() # Load and process the book files
            return dB
        return numFound
# end of PTXBibleFileCheck



def loadPTXSSFData( BibleObject, ssfFilepath, encoding='utf-8' ):
    """
    Process the Paratext SSF data file from the given filepath into SSFDict.

    Returns a dictionary.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( t("Loading Paratext SSF data from {!r} ({})").format( ssfFilepath, encoding ) )
    #if encoding is None: encoding = 'utf-8'
    BibleObject.ssfFilepath = ssfFilepath

    SSFDict = {}

    lastLine, lineCount, status = '', 0, 0
    with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
        for line in myFile:
            lineCount += 1
            if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                logging.info( t("loadPTXSSFData: Detected UTF-16 Byte Order Marker in {}").format( ssfFilepath ) )
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
                status = 9
                processed = True
            elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a BibleObject-closing (empty) field
                fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
                if ' ' not in fieldname:
                    SSFDict[fieldname] = ''
                    processed = True
                elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                    bits = fieldname.split( None, 1 )
                    if BibleOrgSysGlobals.debugFlag: assert( len(bits)==2 )
                    fieldname = bits[0]
                    attributes = bits[1]
                    #print( "attributes = {!r}".format( attributes) )
                    SSFDict[fieldname] = (contents, attributes)
                    processed = True
            elif status==1 and line[0]=='<' and line[-1]=='>' and '/' in line:
                ix1 = line.find('>')
                ix2 = line.find('</')
                if ix1!=-1 and ix2!=-1 and ix2>ix1:
                    fieldname = line[1:ix1]
                    contents = line[ix1+1:ix2]
                    if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                        SSFDict[fieldname] = contents
                        processed = True
                    elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                        bits = fieldname.split( None, 1 )
                        if BibleOrgSysGlobals.debugFlag: assert( len(bits)==2 )
                        fieldname = bits[0]
                        attributes = bits[1]
                        #print( "attributes = {!r}".format( attributes) )
                        if line[ix2+2:-1]==fieldname:
                            SSFDict[fieldname] = (contents, attributes)
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
            if not processed: print( _("ERROR: Unexpected {} line in SSF file").format( repr(line) ) )
    if status == 0:
        logging.error( "SSF file was empty: {}".format( BibleObject.ssfFilepath ) )
        status = 9
    if BibleOrgSysGlobals.debugFlag: assert( status == 9 )
    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( "  " + t("Got {} SSF entries:").format( len(SSFDict) ) )
        if BibleOrgSysGlobals.verbosityLevel > 3:
            for key in sorted(SSFDict):
                try: print( "    {}: {}".format( key, SSFDict[key] ) )
                except UnicodeEncodeError: print( "    {}: UNICODE ENCODING ERROR".format( key ) )

    #BibleObject.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

    ## Determine our encoding while we're at it
    #if BibleObject.encoding is None and 'Encoding' in SSFDict: # See if the SSF file gives some help to us
        #ssfEncoding = SSFDict['Encoding']
        #if ssfEncoding == '65001': BibleObject.encoding = 'utf-8'
        #else:
            #if BibleOrgSysGlobals.verbosityLevel > 0:
                #print( t("__init__: File encoding in SSF is set to {!r}").format( ssfEncoding ) )
            #if ssfEncoding.isdigit():
                #BibleObject.encoding = 'cp' + ssfEncoding
                #if BibleOrgSysGlobals.verbosityLevel > 0:
                    #print( t("__init__: Switched to {!r} file encoding").format( BibleObject.encoding ) )
            #else:
                #logging.critical( t("__init__: Unsure how to handle {!r} file encoding").format( ssfEncoding ) )

    #print( 'SSFDict', SSFDict )
    return SSFDict
# end of loadPTXSSFData



def loadPTXLanguages( self ):
    """
    Load the something.lds file (which is an INI file) and parse it into the dictionary PTXLanguages.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( t("loadPTXLanguagess()") )

    languageFilenames = []
    for something in os.listdir( self.sourceFilepath ):
        somepath = os.path.join( self.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.LDS'): languageFilenames.append( something )
    #if len(languageFilenames) > 1:
        #logging.error( "Got more than one language file: {}".format( languageFilenames ) )

    PTXLanguages = {}

    for languageFilename in languageFilenames:
        languageName = languageFilename[:-4] # Remove the .lds

        languageFilepath = os.path.join( self.sourceFilepath, languageFilename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading language from {}...".format( languageFilepath ) )

        assert( languageName not in PTXLanguages )
        PTXLanguages[languageName] = {}

        lineCount = 0
        sectionName = None
        with open( languageFilepath, 'rt' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXLanguages: Detected UTF-16 Byte Order Marker in {}".format( languageFilename ) )
                    line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#': continue # Just discard comment lines
                #print( "line", repr(line) )

                if len(line)<5:
                    print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    continue

                if line[0]=='[' and line[-1]==']': # it's a new section name
                    sectionName = line[1:-1]
                    assert( sectionName not in PTXLanguages[languageName] )
                    PTXLanguages[languageName][sectionName] = {}
                elif '=' in line: # it's a mapping, e.g., UpperCaseLetters=ABCDEFGHIJKLMNOPQRSTUVWXYZ
                    left, right = line.split( '=', 1 )
                    #print( "left", repr(left), 'right', repr(right) )
                    PTXLanguages[languageName][sectionName][left] = right
                else: print( "What's this language line? {!r}".format( line ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} languages.".format( len(PTXLanguages) ) )
    #print( 'PTXLanguages', PTXLanguages )
    return PTXLanguages
# end of PTXBible.loadPTXLanguages



def loadPTXVersifications( self ):
    """
    Load the versification files (which is a text file)
        and parse it into the dictionary PTXVersifications.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
        print( t("loadPTXVersifications()") )

    #versificationFilename = 'versification.vrs'
    #versificationFilepath = os.path.join( self.sourceFilepath, versificationFilename )
    #if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading versification from {}...".format( versificationFilepath ) )

    #PTXVersifications = { 'VerseCounts':{}, 'Mappings':{}, 'Omitted':[] }

    versificationFilenames = []
    for something in os.listdir( self.sourceFilepath ):
        somepath = os.path.join( self.sourceFilepath, something )
        if os.path.isfile(somepath) and something.upper().endswith('.VRS'): versificationFilenames.append( something )
    #if len(versificationFilenames) > 1:
        #logging.error( "Got more than one versification file: {}".format( versificationFilenames ) )

    PTXVersifications = {}

    for versificationFilename in versificationFilenames:
        versificationName = versificationFilename[:-4] # Remove the .vrs

        versificationFilepath = os.path.join( self.sourceFilepath, versificationFilename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading versification from {}...".format( versificationFilepath ) )

        assert( versificationName not in PTXVersifications )
        PTXVersifications[versificationName] = {}

        lineCount = 0
        with open( versificationFilepath, 'rt' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXVersifications: Detected UTF-16 Byte Order Marker in {}".format( versificationFilename ) )
                    line = line[1:] # Remove the UTF-8 Byte Order Marker
                if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                lastLine = line
                if line[0]=='#' and not line.startswith('#!'): continue # Just discard comment lines
                #print( "Versification line", repr(line) )

                if len(line)<7:
                    print( "Why was line #{} so short? {!r}".format( lineCount, line ) )
                    continue

                if line.startswith( '#! -' ): # It's an excluded verse (or passage???)
                    assert( line[7] == ' ' )
                    USFMBookCode = line[4:7]
                    BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                    C,V = line[8:].split( ':', 1 )
                    #print( "CV", repr(C), repr(V) )
                    if BibleOrgSysGlobals.debugFlag: assert( C.isdigit() and V.isdigit() )
                    #print( "Omitted {} {}:{}".format( BBB, C, V ) )
                    if 'Omitted' not in PTXVersifications[versificationName]:
                        PTXVersifications[versificationName]['Omitted'] = []
                    PTXVersifications[versificationName]['Omitted'].append( (BBB,C,V) )
                elif line[0] == '#': # It's a comment line
                    pass # Just ignore it
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
                    assert( line[3] == ' ' )
                    USFMBookCode = line[:3]
                    #if USFMBookCode == 'ODA': USFMBookCode = 'ODE'
                    try:
                        BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode )
                        if 'VerseCounts' not in PTXVersifications[versificationName]:
                            PTXVersifications[versificationName]['VerseCounts'] = {}
                        PTXVersifications[versificationName]['VerseCounts'][BBB] = OrderedDict()
                        for CVBit in line[4:].split():
                            #print( "CVBit", repr(CVBit) )
                            assert( ':' in CVBit )
                            C,V = CVBit.split( ':', 1 )
                            #print( "CV", repr(C), repr(V) )
                            if BibleOrgSysGlobals.debugFlag: assert( C.isdigit() and V.isdigit() )
                            PTXVersifications[versificationName]['VerseCounts'][BBB][C] = V
                    except KeyError:
                        logging.error( "Unknown {!r} USFM book code in loadPTXVersifications from {}".format( USFMBookCode, versificationFilepath ) )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} versifications.".format( len(PTXVersifications) ) )
    #print( 'PTXVersifications', PTXVersifications )
    return PTXVersifications
# end of PTXBible.loadPTXVersifications



class PTXBible( Bible ):
    """
    Class to load and manipulate Paratext Bible bundles.
    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal Paratext Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Paratext Bible object'
        self.objectTypeString = 'PTX'

        self.sourceFolder, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName

        # Do a preliminary check on the readability of our folder
        if givenName:
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.error( "PTXBible: Folder '{}' is unreadable".format( self.sourceFolder ) )
            self.sourceFilepath = os.path.join( self.sourceFolder, self.givenName )
        else: self.sourceFilepath = self.sourceFolder
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.error( "PTXBible: Folder '{}' is unreadable".format( self.sourceFilepath ) )

        self.ssfFilepath = None

        # Create empty containers for loading the XML metadata files
        #projectUsersDict = self.PTXStyles = self.PTXVersification = self.PTXLanguage = None
    # end of PTXBible.__init__


    def preload( self ):
        """
        Loads the SSF file if it can be found.
        Loads other metadata files that are provided.
        Tries to determine USFM filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("preload() from {}").format( self.sourceFolder ) )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( t("preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in ('__MACOSX'): continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( t("preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( t("preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['PTX'] = {}

        if self.ssfFilepath is None: # it might have been loaded first
            # Attempt to load the SSF file
            #self.suppliedMetadata, self.settingsDict = {}, {}
            ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            #print( "ssfFilepathList", ssfFilepathList )
            if len(ssfFilepathList) > 1:
                logging.error( t("preload: Found multiple possible SSF files -- using first one: {}").format( ssfFilepathList ) )
            if len(ssfFilepathList) >= 1: # Seems we found the right one
                from PTXBible import loadPTXSSFData
                SSFDict = loadPTXSSFData( self, ssfFilepathList[0] )
                if SSFDict:
                    self.suppliedMetadata['PTX']['SSF'] = SSFDict
                    self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

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
            self.possibleFilenameDict[BBB] = filename

        self.loadPTXBooksNames() # from XML (if it exists)
        self.loadPTXProjectUsers() # from XML (if it exists)
        self.loadPTXLexicon() # from XML (if it exists)
        self.loadPTXSpellingStatus() # from XML (if it exists)
        self.loadPTXAutocorrects() # from text file (if it exists)
        self.loadPTXStyles() # from text files (if they exist)
        result = loadPTXVersifications( self ) # from text file (if it exists)
        if result: self.suppliedMetadata['PTX']['Versifications'] = result
        result = loadPTXLanguages( self ) # from INI file (if it exists)
        if result: self.suppliedMetadata['PTX']['Languages'] = result

        self.preloadDone = True
    # end of PTXBible.preload


    def loadPTXBooksNames( self ):
        """
        Load the BookNames.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXBooksNames()") )

        bookNamesFilepath = os.path.join( self.sourceFilepath, 'BookNames.xml' )
        if not os.path.exists( bookNamesFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading books names data from {}...".format( bookNamesFilepath ) )
        self.tree = ElementTree().parse( bookNamesFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        booksNamesDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='BookNames':
            location = "PTX {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Now process the actual book data
            for element in self.tree:
                sublocation = element.tag + ' in ' + location
                if element.tag == 'book':
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )

                    bnCode = bnAbbr = bnShort = bnLong = None
                    for attrib,value in element.items():
                        if attrib=='code': bnCode = value
                        elif attrib=='abbr': bnAbbr = value
                        elif attrib=='short': bnShort = value
                        elif attrib=='long': bnLong = value
                        else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    #print( bnCode, booksNamesDict[bnCode] )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert( len(bnCode)==3 )
                    try: BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( bnCode )
                    except:
                        logging.warning( "loadPTXBooksNames can't find BOS code for PTX {!r} book".format( bnCode ) )
                        BBB = bnCode # temporarily use their code
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: assert( BBB not in booksNamesDict )
                    booksNamesDict[BBB] = (bnCode,bnAbbr,bnShort,bnLong,)
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} book names.".format( len(booksNamesDict) ) )
        #print( "booksNamesDict", booksNamesDict )
        if booksNamesDict: self.suppliedMetadata['PTX']['BooksNames'] = booksNamesDict
    # end of PTXBible.loadPTXBooksNames


    def loadPTXProjectUsers( self ):
        """
        Load the ProjectUsers.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXProjectUsers()") )

        projectUsersFilepath = os.path.join( self.sourceFilepath, 'ProjectUsers.xml' )
        if not os.path.exists( projectUsersFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading project user data from {}...".format( projectUsersFilepath ) )
        self.tree = ElementTree().parse( projectUsersFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        projectUsersDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='ProjectUsers':
            location = "PTX {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Process the attributes first
            peerSharing = None
            for attrib,value in self.tree.items():
                if attrib=='PeerSharing': peerSharing = value
                else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            projectUsersDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                sublocation = element.tag + ' in ' + location
                #print( "Processing {}...".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )

                # Now process the subelements
                if element.tag == 'User':
                    # Process the user attributes first
                    userName = firstUserFlag = None
                    for attrib,value in element.items():
                        if attrib=='UserName': userName = value
                        elif attrib=='FirstUser': firstUserFlag = value
                        else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if 'Users' not in projectUsersDict: projectUsersDict['Users'] = {}
                    assert( userName not in projectUsersDict['Users'] ) # no duplicates allowed presumably
                    projectUsersDict['Users'][userName] = {}
                    projectUsersDict['Users'][userName]['FirstUser'] = firstUserFlag

                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        #print( "  Processing {}...".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ('Role', 'AllBooks', 'Books', ):
                            #if BibleOrgSysGlobals.debugFlag: assert( subelement.text ) # These can be blank!
                            assert( subelement.tag not in projectUsersDict['Users'][userName] )
                            projectUsersDict['Users'][userName][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(projectUsersDict['Users']) ) )
        #print( "projectUsersDict", projectUsersDict )
        if projectUsersDict: self.suppliedMetadata['PTX']['ProjectUsers'] = projectUsersDict
    # end of PTXBible.loadPTXProjectUsers


    def loadPTXLexicon( self ):
        """
        Load the Lexicon.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXLexicon()") )

        lexiconFilepath = os.path.join( self.sourceFilepath, 'Lexicon.xml' )
        if not os.path.exists( lexiconFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading project user data from {}...".format( lexiconFilepath ) )
        self.tree = ElementTree().parse( lexiconFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        lexiconDict = { 'Entries':{} }
        #loadErrors = []

        def processLexiconItem( element, location ):
            """
            """
            #print( "processLexiconItem()" )

            # Now process the actual items
            for subelement in element:
                sublocation = subelement.tag + ' in ' + location
                #print( "Processing {}...".format( sublocation ) )

                # Now process the subelements
                if subelement.tag == 'Lexeme':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                    # Process the attributes
                    lexemeType = lexemeForm = lexemeHomograph = None
                    for attrib,value in subelement.items():
                        if attrib=='Type': lexemeType = value
                        elif attrib=='Form': lexemeForm = value
                        elif attrib=='Homograph': lexemeHomograph = value
                        else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    #print( "Lexeme {} form={!r} homograph={}".format( lexemeType, lexemeForm, lexemeHomograph ) )
                    assert( lexemeType in ( 'Word', 'Phrase', ) )
                    if lexemeType not in lexiconDict['Entries']: lexiconDict['Entries'][lexemeType] = {}
                    assert( lexemeForm not in lexiconDict['Entries'][lexemeType] )
                    lexiconDict['Entries'][lexemeType][lexemeForm] = { 'Homograph':lexemeHomograph, 'senseIDs':{} }
                elif subelement.tag == 'Entry': # Can't see any reason to save this level
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation )
                    for sub2element in subelement:
                        sub2location = sub2element.tag + ' in ' + sublocation
                        #print( "  Processing {}...".format( sub2location ) )
                        if sub2element.tag == 'Sense':
                            BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location )
                            # Process the attributes first
                            senseID = None
                            for attrib,value in sub2element.items():
                                if attrib=='Id': senseID = value
                                else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                            #print( 'senseID={!r}'.format( senseID ) )
                            assert( senseID and senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'] )
                            for sub3element in sub2element:
                                sub3location = sub3element.tag + ' in ' + sub2location
                                #print( "    Processing {}...".format( sub3location ) )
                                if sub3element.tag == 'Gloss':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location )
                                    # Process the attributes first
                                    glossLanguage = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='Language': glossLanguage = value
                                        else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sub3location ) )
                                else: logging.warning( _("Unprocessed {} sub3element '{}' in {}").format( sub3element.tag, sub3element.text, sub3location ) )
                                assert( senseID not in lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'] )
                                lexiconDict['Entries'][lexemeType][lexemeForm]['senseIDs'][senseID] = (sub3element.text, glossLanguage)
                        else: logging.warning( _("Unprocessed {} sub2element '{}' in {}").format( sub2element.tag, sub2element.text, sub2location ) )
                else:
                    logging.warning( _("Unprocessed {} subelement in {}").format( subelement.tag, sublocation ) )
            #print( "  returning", lexiconDict['Entries'][lexemeType][lexemeForm] )
        # end of processLexiconItem


        # Find the main container
        if self.tree.tag=='Lexicon':
            location = "PTX {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.tree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            #lexiconDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                sublocation = element.tag + ' in ' + location
                #print( "Processing {}...".format( sublocation ) )

                # Now process the subelements
                if element.tag in ( 'Language', 'FontName', 'FontSize', ):
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    lexiconDict[element.tag] = element.text
                elif element.tag == 'Analyses':
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                elif element.tag == 'Entries':
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    for subelement in element:
                        sub2location = subelement.tag + ' in ' + sublocation
                        #print( "  Processing {}...".format( sub2location ) )
                        if subelement.tag == 'item':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                            processLexiconItem( subelement, sub2location )
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} lexicon entries.".format( len(lexiconDict['Entries']) ) )
        #print( "lexiconDict", lexiconDict )
        if lexiconDict: self.suppliedMetadata['PTX']['Lexicon'] = lexiconDict
    # end of PTXBible.loadPTXLexicon


    def loadPTXSpellingStatus( self ):
        """
        Load the SpellingStatus.xml file (if it exists) and parse it into the dictionary self.suppliedMetadata.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXSpellingStatus()") )

        spellingStatusFilepath = os.path.join( self.sourceFilepath, 'SpellingStatus.xml' )
        if not os.path.exists( spellingStatusFilepath ): return

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading project user data from {}...".format( spellingStatusFilepath ) )
        self.tree = ElementTree().parse( spellingStatusFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        spellingStatusDict = OrderedDict()
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='SpellingStatus':
            location = "PTX {} file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            ## Process the attributes first
            #peerSharing = None
            #for attrib,value in self.tree.items():
                #if attrib=='PeerSharing': peerSharing = value
                #else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            #spellingStatusDict['PeerSharing'] = peerSharing

            # Now process the actual entries
            for element in self.tree:
                sublocation = element.tag + ' in ' + location
                #print( "Processing {}...".format( sublocation ) )
                BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )

                # Now process the subelements
                if element.tag == 'Status':
                    # Process the user attributes first
                    word = state = None
                    for attrib,value in element.items():
                        if attrib=='Word': word = value
                        elif attrib=='State': state = value
                        else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if 'SpellingWords' not in spellingStatusDict: spellingStatusDict['SpellingWords'] = {}
                    assert( word not in spellingStatusDict['SpellingWords'] ) # no duplicates allowed presumably
                    spellingStatusDict['SpellingWords'][word] = {}
                    spellingStatusDict['SpellingWords'][word]['State'] = state

                    for subelement in element:
                        sub2location = subelement.tag + ' ' + sublocation
                        #print( "  Processing {}...".format( sub2location ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sub2location )
                        if subelement.tag in ( 'SpecificCase', 'Correction', ):
                            #if BibleOrgSysGlobals.debugFlag: assert( subelement.text ) # These can be blank!
                            assert( subelement.tag not in spellingStatusDict['SpellingWords'][word] )
                            spellingStatusDict['SpellingWords'][word][subelement.tag] = subelement.text
                        else: logging.warning( _("Unprocessed {} subelement '{}' in {}").format( subelement.tag, subelement.text, sub2location ) )
                else:
                    logging.warning( _("Unprocessed {} element in {}").format( element.tag, sublocation ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} project users.".format( len(spellingStatusDict['SpellingWords']) ) )
        #print( "spellingStatusDict", spellingStatusDict )
        if spellingStatusDict: self.suppliedMetadata['PTX']['SpellingStatus'] = spellingStatusDict
    # end of PTXBible.loadPTXSpellingStatus


    def loadPTXAutocorrects( self ):
        """
        Load the AutoCorrect.txt file (which is a text file)
            and parse it into the ordered dictionary PTXAutocorrects.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXAutocorrects()") )

        autocorrectFilename = 'AutoCorrect.txt'
        autocorrectFilepath = os.path.join( self.sourceFilepath, autocorrectFilename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading autocorrect from {}...".format( autocorrectFilepath ) )

        PTXAutocorrects = {}

        lineCount = 0
        with open( autocorrectFilepath, 'rt' ) as vFile: # Automatically closes the file when done
            for line in vFile:
                lineCount += 1
                if lineCount==1 and line[0]==chr(65279): #U+FEFF
                    logging.info( "loadPTXAutocorrects: Detected UTF-16 Byte Order Marker in {}".format( autocorrectFilename ) )
                    line = line[1:] # Remove the UTF-8 Byte Order Marker
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
                else: logging.error( "Unknown {!r} autocorrect line in PTXBible.loading autocorrect".format( line ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} autocorrect elements.".format( len(PTXAutocorrects) ) )
        #print( 'PTXAutocorrects', PTXAutocorrects )
        if PTXAutocorrects: self.suppliedMetadata['PTX']['Autocorrects'] = PTXAutocorrects
    # end of PTXBible.loadPTXAutocorrects


    def loadPTXStyles( self ):
        """
        Load the something.sty file (which is a SFM file) and parse it into the dictionary PTXStyles.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("loadPTXStyles()") )

        styleFilenames = []
        for something in os.listdir( self.sourceFilepath ):
            somepath = os.path.join( self.sourceFilepath, something )
            if os.path.isfile(somepath) and something.upper().endswith('.STY'): styleFilenames.append( something )
        #if len(styleFilenames) > 1:
            #logging.error( "Got more than one style file: {}".format( styleFilenames ) )

        PTXStyles = {}

        for styleFilename in styleFilenames:
            styleName = styleFilename[:-4] # Remove the .sty

            styleFilepath = os.path.join( self.sourceFilepath, styleFilename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loading style from {}...".format( styleFilepath ) )

            assert( styleName not in PTXStyles )
            PTXStyles[styleName] = {}

            lineCount = 0
            encodings = ['utf-8', 'ISO-8859-1', 'ISO-8859-15']
            currentStyle = {}
            for encoding in encodings: # Start by trying the given encoding
                try:
                    with open( styleFilepath, 'rt', encoding=encoding ) as vFile: # Automatically closes the file when done
                        for line in vFile:
                            lineCount += 1
                            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                                logging.info( "loadPTXStyles: Detected UTF-16 Byte Order Marker in {}".format( styleFilename ) )
                                line = line[1:] # Remove the UTF-8 Byte Order Marker
                            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                            if not line: continue # Just discard blank lines
                            lastLine = line
                            if line[0]=='#': continue # Just discard comment lines
                            #print( lineCount, "line", repr(line) )

                            if len(line)<5: # '\Bold' is the shortest valid line
                                logging.warning( "Why was PTX style line #{} so short? {!r}".format( lineCount, line ) )
                                continue

                            if line[0] == '\\':
                                bits = line[1:].split( ' ', 1 )
                                #print( "style bits", bits )
                                name, value = bits[0], bits[1] if len(bits)==2 else None
                                if name == 'Marker':
                                    if currentStyle:
                                        assert( styleMarker not in PTXStyles )
                                        PTXStyles[styleName][styleMarker] = currentStyle
                                        currentStyle = {}
                                    styleMarker = value
                                elif name in ( 'Name', 'Description', 'OccursUnder', 'Rank', 'StyleType', 'Endmarker', 'SpaceBefore', 'SpaceAfter', 'LeftMargin', 'RightMargin', 'FirstLineIndent', 'TextType', 'TextProperties', 'Justification', 'FontSize', 'Bold', 'Italic', 'Smallcaps', 'Superscript', 'Underline', 'Color', 'color', ):
                                    if name == 'color': name = 'Color' # fix inconsistency
                                    if name in currentStyle: # already
                                        logging.error( "loadPTXStyles found duplicate {!r}={!r} in {} {} at line #{}".format( name, value, styleName, styleMarker, lineCount ) )
                                    currentStyle[name] = value
                                else: print( "What's this style marker? {!r}".format( line ) )
                            else: print( "What's this style line? {!r}".format( line ) )
                    break; # Get out of decoding loop because we were successful
                except UnicodeDecodeError:
                    logging.error( _("loadPTXStyles fails with encoding: {} on {}{}").format( encoding, styleFilepath, {} if encoding==encodings[-1] else ' -- trying again' ) )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Loaded {} style files.".format( len(PTXStyles) ) )
        #print( 'PTXStyles', PTXStyles )
        if PTXStyles: self.suppliedMetadata['PTX']['Styles'] = PTXStyles
    # end of PTXBible.loadPTXStyles


    def xxxapplySuppliedMetadata( self, applyMetadataType ): # Overrides the default one in InternalBible.py
        """
        Using the dictionary at self.suppliedMetadata,
            load the fields into self.settingsDict
            and try to standardise it at the same time.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( t("applySuppliedMetadata({} )").format( applyMetadataType ) )
        assert( applyMetadataType == 'PTX' )

        self.name = self.suppliedMetadata['PTX']['identification']['name']
        self.abbreviation = self.suppliedMetadata['PTX']['identification']['abbreviation']

        # Now we'll flatten the supplied metadata and remove empty values
        flattenedMetadata = {}
        for mainKey,value in self.suppliedMetadata['PTX'].items():
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
                                assert( sub2Key == 'books' )
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
    # end of PTXBible.applySuppliedMetadata


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "PTXBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  PTXBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "PTXBible.loadBook: Unable to find file for {}".format( BBB ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.saveBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
    # end of PTXBible.loadBook


    def _loadBookMP( self, BBB_Filename ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( t("loadBookMP( {} )").format( BBB_Filename ) )
        BBB, filename = BBB_Filename
        assert( BBB not in self.books )
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( '  ' + t("Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of PTXBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( t("Loading {} from {}...").format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( t("Loading {} books using {} CPUs...").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert( len(results) == len(self.maximumPossibleFilenameTuples) )
                    for bBook in results: self.saveBook( bBook ) # Saves them in the correct order
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  PTXBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
                    loadedBook = self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( t("No books to load in {}!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of PTXBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class PTXBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in ( "Tests/DataFilesForTests/USFMTest1/",
                            "Tests/DataFilesForTests/USFMTest2/",
                            "Tests/DataFilesForTests/USFMTest3/",
                            "Tests/DataFilesForTests/USFMAllMarkersProject/",
                            "Tests/DataFilesForTests/USFMErrorProject/",
                            "Tests/DataFilesForTests/PTXTest/",
                            "OutputFiles/BOS_USFM_Export/",
                            "OutputFiles/BOS_USFM_Reexport/",
                            "MadeUpFolder/",
                            ):
            print( "\nTestfolder is: {}".format( testFolder ) )
            result1 = PTXBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX TestA1", result1 )
            result2 = PTXBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX TestA2", result2 )
            result3 = PTXBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "PTX TestA3", result3 )

    testFolder = "Tests/DataFilesForTests/PTXTest/"
    if 0: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX B/ Trying single module in {}".format( testFolder ) )
        testPTX_B( testFolder )

    if 0: # specified single installed module
        singleModule = 'eng-asv_dbl_06125adad2d5898a-rev1-2014-08-30'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX C/ Trying installed {} module".format( singleModule ) )
        PTX_Bible = PTXBible( testFolder, singleModule )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            PTX_Bible = PTXBible( testFolder, testFilename )
            PTX_Bible.load()


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( PTXBible, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                PTXBible( testFolder, someFolder )
    if 0:
        testFolders = (
                    "Tests/DataFilesForTests/PTXTest/",
                    ) # You can put your PTX test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTXBible( testFolder )
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

    if 0:
        testFolders = (
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/acfPTX 2013-02-03",
                    "Tests/DataFilesForTests/theWordRoundtripTestFiles/aucPTX 2013-02-26",
                    ) # You can put your PTX test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                PTX_Bible = PTXBible( testFolder )
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

    #if BibleOrgSysGlobals.commandLineOptions.export:
    #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( ProgName, ProgVersion ) )
    #       pass

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of PTXBible.py