#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SwordBible.py
#
# Module handling Sword Bible files
#
# Copyright (C) 2015-2023 Robert Hunt
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
Module detecting and loading Crosswire Sword Bible binary files.

Files are usually:
    ot
    ot.vss
    nt
    nt.vss

It uses the SwordInterface in SwordResources,
    which will either use the Sword SWIG code, or our SwordModules.py

Note: The demo takes about 4 minutes with our Sword code,
        cf. 13 minutes using the Sword library! (Why?)
"""
import logging
import os
from pathlib import Path
import multiprocessing


from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible #, BibleBook
from BibleOrgSys.Formats import SwordResources # import SwordType, SwordInterface -- the SwordType gets the old value if SwordType is rebound
                      # Normally it wouldn't be a problem, but we adjust SwordType in DemoTests to test both modes
#from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


LAST_MODIFIED_DATE = '2023-02-02' # by RJH
SHORT_PROGRAM_NAME = "SwordBible"
PROGRAM_NAME = "Sword Bible format handler"
PROGRAM_VERSION = '0.36'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Must be lowercase
compulsoryTopFolders = ( 'mods.d', 'modules', ) # Both should be there -- the first one contains the .conf file(s)
#compulsoryBottomFolders = ( 'rawtext', 'ztext', ) # Either one
compulsoryFiles = ( 'ot','ot.vss', 'ot.bzs','ot.bzv','ot.bzz', 'nt','nt.vss', 'nt.bzs','nt.bzv','nt.bzz', ) # At least two


# Sword enums
#DIRECTION_LTR = 0; DIRECTION_RTL = 1; DIRECTION_BIDI = 2
#FMT_UNKNOWN = 0; FMT_PLAIN = 1; FMT_THML = 2; FMT_GBF = 3; FMT_HTML = 4; FMT_HTMLHREF = 5; FMT_RTF = 6; FMT_OSIS = 7; FMT_WEBIF = 8; FMT_TEI = 9; FMT_XHTML = 10
#FMT_DICT = { 1:'PLAIN', 2:'THML', 3:'GBF', 4:'HTML', 5:'HTMLHREF', 6:'RTF', 7:'OSIS', 8:'WEBIF', 9:'TEI', 10:'XHTML', 11:'LaTeX' }
#ENC_UNKNOWN = 0; ENC_LATIN1 = 1; ENC_UTF8 = 2; ENC_UTF16 = 3; ENC_RTF = 4; ENC_HTML = 5



def SwordBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Sword Bible is found,
        returns the loaded SwordBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"SwordBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( f"SwordBibleFileCheck: Given {givenFolderName!r} folder is unreadable" )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( f"SwordBibleFileCheck: Given {givenFolderName!r} path is not a folder" )
        return False

    def confirmThisFolder( checkFolderpath ):
        """
        We are given the path to a folder that contains the two main top level folders.

        Now we need to find one or more .conf files and the associated Bible folders.

        Returns a list of Bible module names (without the .conf) -- they are the case of the folder name.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f" SwordBibleFileCheck.confirmThisFolder: Looking for files in given {checkFolderpath}" )

        # See if there's any .conf files in the mods.d folder
        confFolder = os.path.join( checkFolderpath, 'mods.d/' )
        foundConfFiles = []
        for something in os.listdir( confFolder ):
            somepath = os.path.join( confFolder, something )
            if os.path.isdir( somepath ):
                if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue # don't visit these directories
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"SwordBibleFileCheck: Didn't expect a subfolder in conf folder: {something}" )
            elif os.path.isfile( somepath ):
                if something.endswith( '.conf' ):
                    foundConfFiles.append( something[:-5].upper() ) # Remove the .conf bit and make it UPPERCASE
                else:
                    logging.warning( f"SwordBibleFileCheck: Didn't expect this file in conf folder: {something}" )
        if not foundConfFiles: return 0
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "confirmThisFolder:foundConfFiles", foundConfFiles )

        # See if there's folders for the Sword module files matching the .conf files
        compressedFolder = os.path.join( checkFolderpath, 'modules/', 'texts/', 'ztext/' )
        foundTextFolders = []
        for folderType,subfolderType in ( ('texts','rawtext'), ('texts','ztext'), ('comments','zcom'), ('comments','rawcom'), ('comments','rawcom4'), ):
            mainTextFolder = os.path.join( checkFolderpath, 'modules/', folderType+'/', subfolderType+'/' )
            if os.access( mainTextFolder, os.R_OK ): # The subfolder is readable
                for something in os.listdir( mainTextFolder ):
                    somepath = os.path.join( mainTextFolder, something )
                    if os.path.isdir( somepath ):
                        if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                            continue # don't visit these directories
                        potentialName = something.upper()
                        if potentialName in foundConfFiles:
                            foundTextFiles = []
                            textFolder = os.path.join( mainTextFolder, something+'/' )
                            for something2 in os.listdir( textFolder ):
                                somepath2 = os.path.join( textFolder, something2 )
                                if os.path.isdir( somepath2 ):
                                    if something2 in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                                        continue # don't visit these directories
                                    if something2 != 'lucene':
                                        logging.warning( f"SwordBibleFileCheck1: Didn't expect a subfolder in {something} text folder: {something2}" )
                                elif os.path.isfile( somepath2 ):
                                    if subfolderType == 'rawtext' and something2 in ( 'ot','ot.vss', 'nt','nt.vss' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType == 'ztext' and something2 in ( 'ot.bzs','ot.bzv','ot.bzz', 'nt.bzs','nt.bzv','nt.bzz' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType == 'zcom' and something2 in ( 'ot.czs','ot.czv','ot.czz', 'nt.czs','nt.czv','nt.czz' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType in ('rawcom','rawcom4',):
                                        logging.critical( f"Program not finished yet: confirmThisFolder( {checkFolderpath} ) for rawcom/rawcom4" )
                                    else:
                                        if something2 not in ( 'errata', 'appendix', ):
                                            logging.warning( f"SwordBibleFileCheck1: Didn't expect this file in {something} text folder: {something2}" )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, foundTextFiles )
                            if len(foundTextFiles) >= 2:
                                foundTextFolders.append( something )
                        else:
                            logging.warning( f"SwordBibleFileCheck2: Didn't expect a subfolder in {folderType} folder: {something}" )
                    elif os.path.isfile( somepath ):
                        logging.warning( f"SwordBibleFileCheck2: Didn't expect this file in {folderType} folder: {something}" )
        if not foundTextFolders:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual module folders or files found" )
            return None
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "confirmThisFolder: foundTextFolders", foundTextFolders )
        return foundTextFolders
    # end of confirmThisFolder

    # Main part of SwordBibleFileCheck
    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" SwordBibleFileCheck: Looking for files in given {givenFolderName}" )
    foundFolders, foundFiles = [], []
    numFound = foundFolderCount = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something ) # Save folder name in case we have to go a level down
            if something in compulsoryTopFolders:
                foundFolderCount += 1
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper in compulsoryFiles: foundFileCount += 1
    if foundFolderCount == len(compulsoryTopFolders):
        assert foundFileCount == 0
        foundConfNames = confirmThisFolder( givenFolderName )
        numFound = 0 if foundConfNames is None else len(foundConfNames)
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "SwordBibleFileCheck got", numFound, givenFolderName, foundConfNames )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = SwordBible( givenFolderName )
            if autoLoadBooks: oB.loadBooks() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFolderCount = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( f"SwordBibleFileCheck: {tryFolderName!r} subfolder is unreadable" )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    SwordBibleFileCheck: Looking for files in {tryFolderName}" )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ):
                    foundSubfolders.append( something )
                    if something in compulsoryTopFolders: foundFolderCount += 1
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    if somethingUpper in compulsoryFiles: foundFileCount += 1
        except PermissionError: pass # can't read folder, e.g., system folder
        if foundFolderCount == len(compulsoryTopFolders):
            assert foundFileCount == 0
            foundConfNames = confirmThisFolder( tryFolderName )
            if foundConfNames:
                for confName in foundConfNames:
                    foundProjects.append( (tryFolderName,confName) )
                    numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "SwordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = SwordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: oB.loadBooks() # Load and process the file
            return oB
        return numFound
# end of SwordBibleFileCheck



class SwordBible( Bible ):
    """
    Class for reading, validating, and converting SwordBible files.
    """
    def __init__( self, sourceFolder=None, moduleName=None, encoding='utf-8' ) -> None:
        """
        Constructor: just sets up the Bible object.

        The sourceFolder should be the one containing mods.d and modules folders.
        The module name (if needed) should be the name of one of the .conf files in the mods.d folder
            (with or without the .conf on it).
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"SwordBible.__init__( {sourceFolder} {moduleName} {encoding} ) for '{SwordResources.SwordType}'" )

        if not sourceFolder and not moduleName:
            logging.critical( "SwordBible must be passed either a folder path or a module name!" )
            return

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Sword Bible object'
        self.objectTypeString = 'CrosswireSword' if SwordResources.SwordType=='CrosswireLibrary' else 'Sword'

        # Now we can set our object variables
        self.sourceFolder, self.moduleName, self.encoding = sourceFolder, moduleName, encoding
        self.SwordInterface = None

        if self.sourceFolder:
            # Do a preliminary check on the readability of our folder
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.critical( f"SwordBible: Folder {self.sourceFolder!r} is unreadable" )

            if not self.moduleName: # If we weren't passed the module name, we need to assume that there's only one
                confFolder = os.path.join( self.sourceFolder, 'mods.d/' )
                foundConfs = []
                for something in os.listdir( confFolder ):
                    somepath = os.path.join( confFolder, something )
                    if os.path.isfile( somepath ) and something.endswith( '.conf' ):
                        foundConfs.append( something[:-5] ) # Drop the .conf bit
                if foundConfs == 0:
                    logging.critical( f"No .conf files found in {confFolder}" )
                elif len(foundConfs) > 1:
                    logging.critical( f"Too many .conf files found in {confFolder}" )
                else:
                    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "SwordBible.__init__ got", foundConfs[0] )
                    self.moduleName = foundConfs[0]
        self.abbreviation = self.moduleName # First attempt

        # Load the Sword manager and find our module
        if self.SwordInterface is None and SwordResources.SwordType is not None:
            self.SwordInterface = SwordResources.SwordInterface() # Load the Sword library
        if self.SwordInterface is None: # still
            logging.critical( "SwordBible: no Sword interface available" )
            return
        #try: self.SWMgr = Sword.SWMgr()
        #except NameError:
            #logging.critical( f"Unable to initialise {self.moduleName!r} module -- no Sword manager available" )
            #return # our Sword import must have failed
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE and SwordResources.SwordType=='CrosswireLibrary':
            availableGlobalOptions = [str(option) for option in self.SwordInterface.library.getGlobalOptions()]
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "availableGlobalOptions", availableGlobalOptions )
        # Don't need to set options if we use getRawEntry() rather than stripText() or renderText()
        #for optionName in ( 'Headings', 'Footnotes', 'Cross-references', "Strong's Numbers", 'Morphological Tags', ):
            #self.SWMgr.setGlobalOption( optionName, 'On' )

        if self.sourceFolder:
            self.SwordInterface.library.augmentModules( str(self.sourceFolder), False ) # Add our folder to the SW Mgr

        availableModuleCodes = []
        for j,something in enumerate(self.SwordInterface.library.getModules()):
            # something can be a moduleBuffer (Crosswire) or just a string (BOS)
            if SwordResources.SwordType == 'CrosswireLibrary':
                if BibleOrgSysGlobals.strictCheckingFlag: assert not isinstance( something, str )
                moduleID = something.getRawData()
            else:
                if BibleOrgSysGlobals.strictCheckingFlag: assert isinstance( something, str )
                moduleID = something
            if BibleOrgSysGlobals.strictCheckingFlag: assert isinstance( moduleID, str )

            if moduleID.upper() == self.moduleName.upper(): self.moduleName = moduleID # Get the case correct
            #module = SWMgr.getModule( moduleID )
            #if 0:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{j} {module.getName()} ({module.getType()}) {module.getLanguage()} {module.getEncoding()!r}" )
                #try: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'    {module.getDescription()} {module.getMarkup()!r} {module.getDirection()} {""}' )
                #except UnicodeDecodeError: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "   Description is not Unicode!" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "moduleID", repr(moduleID) )
            availableModuleCodes.append( moduleID )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Available module codes:", availableModuleCodes )

        if self.moduleName not in availableModuleCodes:
            logging.critical( f"Unable to find {self.moduleName!r} Sword module" )
            if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Available module codes:", availableModuleCodes )

        self.abbreviation = self.moduleName # Perhaps a better attempt
    # end of SwordBible.__init__


    def loadBooks( self ):
        """
        Load the compressed data file and import book elements.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "SwordBible.loadBooks()" )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLoading {self.moduleName} module…" )

        self.SwordInterface.loadBooks( self, self.moduleName )

        #try: module = self.SwordInterface.library.getModule( self.moduleName )
        #except AttributeError: # probably no SWMgr
            #logging.critical( f"Unable to load {self.moduleName!r} module -- no Sword loader available" )
            #return
        #if module is None:
            #logging.critical( f"Unable to load {self.moduleName!r} module -- not known by Sword" )
            #return

        #if SwordResources.SwordType=='CrosswireLibrary': # need to load the module
            #markupCode = ord( module.getMarkup() )
            #encoding = ord( module.getEncoding() )
            #if encoding == ENC_LATIN1: self.encoding = 'latin-1'
            #elif encoding == ENC_UTF8: self.encoding = 'utf-8'
            #elif encoding == ENC_UTF16: self.encoding = 'utf-16'
            #elif BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt

            #if BibleOrgSysGlobals.verbosityLevel > 3:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Description: {module.getDescription()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Direction: {ord(module.getDirection())!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Encoding: {encoding!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Language: {module.getLanguage()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Markup: {markupCode!r}={FMT_DICT[markupCode]}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Name: {module.getName()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'RenderHeader: {module.getRenderHeader()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'Type: {module.getType()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'IsSkipConsecutiveLinks: {module.isSkipConsecutiveLinks()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'IsUnicode: {module.isUnicode()!r}' )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'IsWritable: {module.isWritable()!r}' )
                ##return

            #bookCount = 0
            #currentBBB = None
            #for index in range( 999999 ):
                #module.setIndex( index )
                #if module.getIndex() != index: break # Gone too far

                ## Find where we're at
                #verseKey = module.getKey()
                #verseKeyText = verseKey.getShortText()
                ##if '2' in verseKeyText: halt # for debugging first verses
                ##if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'\nvkst={verseKeyText!r} vkix={verseKey.getIndex()}' )

                ##nativeVerseText = module.renderText().decode( self.encoding, 'replace' )
                ##nativeVerseText = str( module.renderText() ) if self.encoding=='utf-8' else str( module.renderText(), encoding=self.encoding )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'getRenderHeader: {len(module.getRenderHeader())} {module.getRenderHeader()!r}' )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'stripText: {len(module.stripText())} {module.stripText()!r}' )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'renderText: {len(str(module.renderText()))} {str(module.renderText())!r}' )
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'getRawEntry: {len(module.getRawEntry())} {module.getRawEntry()!r}' )
                #try: nativeVerseText = module.getRawEntry()
                ##try: nativeVerseText = str( module.renderText() )
                #except UnicodeDecodeError: nativeVerseText = ''

                #if ':' not in verseKeyText:
                    #if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Unusual Sword verse key: {verseKeyText} (gave {nativeVerseText!r})" )
                    #if BibleOrgSysGlobals.debugFlag:
                        #assert verseKeyText in ( '[ Module Heading ]', '[ Testament 1 Heading ]', '[ Testament 2 Heading ]', )
                    #if BibleOrgSysGlobals.verbosityLevel > 3:
                        #if markupCode == FMT_OSIS:
                            #match = re.search( '<milestone ([^/>]*?)type="x-importer"([^/>]*?)/>', nativeVerseText )
                            #if match:
                                #attributes = match.group(1) + match.group(2)
                                #match2 = re.search( 'subType="(.+?)"', attributes )
                                #subType = match2.group(1) if match2 else None
                                #if subType and subType.startswith( 'x-' ): subType = subType[2:] # Remove the x- prefix
                                #match2 = re.search( 'n="(.+?)"', attributes )
                                #n = match2.group(1) if match2 else None
                                #if n: n = n.replace( '$', '' ).strip()
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Module created by {subType} {n}" )
                    #continue
                #vkBits = verseKeyText.split()
                #assert len(vkBits) == 2
                #osisBBB = vkBits[0]
                #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBBB )
                #if isinstance( BBB, list ): BBB = BBB[0] # We sometimes get a list of options -- take the first = most likely one
                #vkBits = vkBits[1].split( ':' )
                #assert len(vkBits) == 2
                #C, V = vkBits
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'At {BBB} {C}:{V}' )

                ## Start a new book if necessary
                #if BBB != currentBBB:
                    #if currentBBB is not None and haveText: # Save the previous book
                        #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Saving", currentBBB, bookCount )
                        #self.stashBook( thisBook )
                    ## Create the new book
                    #if BibleOrgSysGlobals.verbosityLevel > 2:  vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  Loading {self.moduleName} {BBB}…' )
                    #thisBook = BibleBook( self, BBB )
                    #thisBook.objectNameString = 'Sword Bible Book object'
                    #thisBook.objectTypeString = 'Sword Bible'
                    #currentBBB, currentC, haveText = BBB, '0', False
                    #bookCount += 1

                #if C != currentC:
                    #thisBook.addLine( 'c', C )
                    ##if C == '2': halt
                    #currentC = C

                #if nativeVerseText:
                    #haveText = True
                    #if markupCode == FMT_OSIS: importOSISVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                    #elif markupCode == FMT_GBF: importGBFVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                    #elif markupCode == FMT_THML: importTHMLVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                    #else:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'markupCode', repr(markupCode) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                        #return

            #if currentBBB is not None and haveText: # Save the very last book
                #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Saving", self.moduleName, currentBBB, bookCount )
                #self.stashBook( thisBook )


        #elif SwordResources.SwordType=='OurCode': # module is already loaded above
            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "moduleConfig =", module.SwordModuleConfiguration )
            #self.books = module.books

        self.doPostLoadProcessing()
    # end of SwordBible.load
# end of SwordBible class



def testSwB( SwFolderpath, SwModuleName=None ):
    """
    Crudely demonstrate and test the Sword Bible class
    """
    from BibleOrgSys.Reference import VerseReferences

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Demonstrating the Sword Bible class…" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test folder is {SwFolderpath!r} {SwModuleName!r}" )
    SwBible = SwordBible( SwFolderpath, SwModuleName )
    SwBible.loadBooks() # Load and process the file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, SwBible ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        SwBible.check()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        SwBErrors = SwBible.getCheckResults()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, SwBErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##SwBible.toDrupalBible()
        SwBible.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                        ('OT','DAN','1','21'),
                        ('NT','MAT','1','1'), ('NT','MAT','3','5'), ('NT','MAT','3','8'),
                        ('NT','JDE','1','4'), ('NT','REV','22','21'),
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (T, BBB, C, V) = reference
        if T=='OT' and len(SwBible)==27: continue # Don't bother with OT references if it's only a NT
        if T=='NT' and len(SwBible)==39: continue # Don't bother with NT references if it's only a OT
        if T=='DC' and len(SwBible)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( BBB, C, V )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, SwBible.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = SwBible.getVerseText( svk )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "verseText", verseText )
            fullVerseText = SwBible.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, shortText, verseText )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {fullVerseText}' )
    return SwBible
# end of testSwB


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = os.path.join( os.path.expanduser('~'), '.sword/')
    # Matigsalug_Test module
    MSTestFolder = Path( '/srv/Websites/Freely-Given.org/Software/BibleDropBox/Demos/MBTV.PTX8.Demo/Sword_(from OSIS_Crosswire_Python)/CompressedSwordModule' )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = SwordBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA1", result1 )
        result2 = SwordBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA2", result2 )
        result3 = SwordBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA3", result3 )

    if 1: # specify testFolder containing a single module
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword B/ Trying single module in {MSTestFolder}" )
        testSwB( MSTestFolder )

    if 1: # specified single installed module
        singleModule = 'ASV'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword C/ Trying installed {singleModule} module" )
        SwBible = testSwB( None, singleModule )
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
            BBB = 'JN1'
            if BBB in SwBible:
                SwBible.books[BBB].debugPrint()
                for entryKey in SwBible.books[BBB]._CVIndex:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SwBible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )

    if 1: # specified installed modules (Removed 'ESV2001','ESV2011', 'TS1998',)
        good = ('KJV','WEB','KJVA','YLT','ASV','LEB', 'ISV','NET','OEB',
                'AB','ABP','ACV','AKJV','BBE','BSV','BWE','CPDV','Common','DRC','Darby',
                'EMTV','Etheridge','Geneva1599','Godbey','GodsWord','JPS','KJVPCE','LITV','LO','Leeser',
                'MKJV','Montgomery','Murdock','NETfree','NETtext','NHEB','NHEBJE','NHEBME','Noyes',
                'OEBcth','OrthJBC','RKJNT','RNKJV','RWebster','RecVer','Rotherham',
                'SPE','Twenty','Tyndale','UKJV','WEBBE','WEBME','Webster','Weymouth','Worsley',)
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testSwB( testFolder, testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testSwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testSwB( testFolder, someFolder )
# end of SwordBible.briefDemo


def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = os.path.join( os.path.expanduser('~'), '.sword/')
    # Matigsalug_Test module
    MSTestFolder = Path( '/srv/Websites/Freely-Given.org/Software/BibleDropBox/Demos/MBTV.PTX8.Demo/Sword_(from OSIS_Crosswire_Python)/CompressedSwordModule' )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = SwordBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA1", result1 )
        result2 = SwordBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA2", result2 )
        result3 = SwordBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Sword TestA3", result3 )

    if 1: # specify testFolder containing a single module
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword B/ Trying single module in {MSTestFolder}" )
        testSwB( MSTestFolder )

    if 1: # specified single installed module
        singleModule = 'ASV'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword C/ Trying installed {singleModule} module" )
        SwBible = testSwB( None, singleModule )
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
            BBB = 'JN1'
            if BBB in SwBible:
                SwBible.books[BBB].debugPrint()
                for entryKey in SwBible.books[BBB]._CVIndex:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SwBible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )

    if 1: # specified installed modules (Removed 'ESV2001','ESV2011', 'TS1998',)
        good = ('KJV','WEB','KJVA','YLT','ASV','LEB', 'ISV','NET','OEB',
                'AB','ABP','ACV','AKJV','BBE','BSV','BWE','CPDV','Common','DRC','Darby',
                'EMTV','Etheridge','Geneva1599','Godbey','GodsWord','JPS','KJVPCE','LITV','LO','Leeser',
                'MKJV','Montgomery','Murdock','NETfree','NETtext','NHEB','NHEBJE','NHEBME','Noyes',
                'OEBcth','OrthJBC','RKJNT','RNKJV','RWebster','RecVer','Rotherham',
                'SPE','Twenty','Tyndale','UKJV','WEBBE','WEBME','Webster','Weymouth','Worsley',)
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testSwB( testFolder, testFilename )
            break


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testSwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSword E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testSwB( testFolder, someFolder )
# end of SwordBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SwordBible.py
