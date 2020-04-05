#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordBible.py
#
# Module handling Sword Bible files
#
# Copyright (C) 2015-2020 Robert Hunt
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

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-03-13' # by RJH
SHORT_PROGRAM_NAME = "SwordBible"
PROGRAM_NAME = "Sword Bible format handler"
PROGRAM_VERSION = '0.36'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os
import multiprocessing


if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible #, BibleBook
from BibleOrgSys.Formats import SwordResources # import SwordType, SwordInterface -- the SwordType gets the old value if SwordType is rebound
                      # Normally it wouldn't be a problem, but we adjust SwordType in DemoTests to test both modes
#from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


 # Must be lowercase
compulsoryTopFolders = ( 'mods.d', 'modules', ) # Both should be there -- the first one contains the .conf file(s)
#compulsoryBottomFolders = ( 'rawtext', 'ztext', ) # Either one
compulsoryFiles = ( 'ot','ot.vss', 'ot.bzs','ot.bzv','ot.bzz', 'nt','nt.vss', 'nt.bzs','nt.bzv','nt.bzz', ) # At least two


# Sword enums
#DIRECTION_LTR = 0; DIRECTION_RTL = 1; DIRECTION_BIDI = 2
#FMT_UNKNOWN = 0; FMT_PLAIN = 1; FMT_THML = 2; FMT_GBF = 3; FMT_HTML = 4; FMT_HTMLHREF = 5; FMT_RTF = 6; FMT_OSIS = 7; FMT_WEBIF = 8; FMT_TEI = 9; FMT_XHTML = 10
#FMT_DICT = { 1:'PLAIN', 2:'THML', 3:'GBF', 4:'HTML', 5:'HTMLHREF', 6:'RTF', 7:'OSIS', 8:'WEBIF', 9:'TEI', 10:'XHTML', 11:'LaTeX' }
#ENC_UNKNOWN = 0; ENC_LATIN1 = 1; ENC_UTF8 = 2; ENC_UTF16 = 3; ENC_RTF = 4; ENC_HTML = 5



def SwordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Sword Bible is found,
        returns the loaded SwordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("SwordBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("SwordBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    def confirmThisFolder( checkFolderPath ):
        """
        We are given the path to a folder that contains the two main top level folders.

        Now we need to find one or more .conf files and the associated Bible folders.

        Returns a list of Bible module names (without the .conf) -- they are the case of the folder name.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( " SwordBibleFileCheck.confirmThisFolder: Looking for files in given {}".format( checkFolderPath ) )

        # See if there's any .conf files in the mods.d folder
        confFolder = os.path.join( checkFolderPath, 'mods.d/' )
        foundConfFiles = []
        for something in os.listdir( confFolder ):
            somepath = os.path.join( confFolder, something )
            if os.path.isdir( somepath ):
                if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue # don't visit these directories
                print( _("SwordBibleFileCheck: Didn't expect a subfolder in conf folder: {}").format( something ) )
            elif os.path.isfile( somepath ):
                if something.endswith( '.conf' ):
                    foundConfFiles.append( something[:-5].upper() ) # Remove the .conf bit and make it UPPERCASE
                else:
                    logging.warning( _("SwordBibleFileCheck: Didn't expect this file in conf folder: {}").format( something ) )
        if not foundConfFiles: return 0
        #print( "confirmThisFolder:foundConfFiles", foundConfFiles )

        # See if there's folders for the Sword module files matching the .conf files
        compressedFolder = os.path.join( checkFolderPath, 'modules/', 'texts/', 'ztext/' )
        foundTextFolders = []
        for folderType,subfolderType in ( ('texts','rawtext'), ('texts','ztext'), ('comments','zcom'), ('comments','rawcom'), ('comments','rawcom4'), ):
            mainTextFolder = os.path.join( checkFolderPath, 'modules/', folderType+'/', subfolderType+'/' )
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
                                        logging.warning( _("SwordBibleFileCheck1: Didn't expect a subfolder in {} text folder: {}").format( something, something2 ) )
                                elif os.path.isfile( somepath2 ):
                                    if subfolderType == 'rawtext' and something2 in ( 'ot','ot.vss', 'nt','nt.vss' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType == 'ztext' and something2 in ( 'ot.bzs','ot.bzv','ot.bzz', 'nt.bzs','nt.bzv','nt.bzz' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType == 'zcom' and something2 in ( 'ot.czs','ot.czv','ot.czz', 'nt.czs','nt.czv','nt.czz' ):
                                        foundTextFiles.append( something2 )
                                    elif subfolderType in ('rawcom','rawcom4',):
                                        logging.critical( "Program not finished yet: confirmThisFolder( {} ) for rawcom/rawcom4".format( checkFolderPath ) )
                                    else:
                                        if something2 not in ( 'errata', 'appendix', ):
                                            logging.warning( _("SwordBibleFileCheck1: Didn't expect this file in {} text folder: {}").format( something, something2 ) )
                            #print( foundTextFiles )
                            if len(foundTextFiles) >= 2:
                                foundTextFolders.append( something )
                        else:
                            logging.warning( _("SwordBibleFileCheck2: Didn't expect a subfolder in {} folder: {}").format( folderType, something ) )
                    elif os.path.isfile( somepath ):
                        logging.warning( _("SwordBibleFileCheck2: Didn't expect this file in {} folder: {}").format( folderType, something ) )
        if not foundTextFolders:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual module folders or files found" )
            return None
        #print( "confirmThisFolder: foundTextFolders", foundTextFolders )
        return foundTextFolders
    # end of confirmThisFolder

    # Main part of SwordBibleFileCheck
    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3:
        print( " SwordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck got", numFound, givenFolderName, foundConfNames )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = SwordBible( givenFolderName )
            if autoLoadBooks: oB.loadBooks() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFolderCount = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("SwordBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    SwordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ):
                foundSubfolders.append( something )
                if something in compulsoryTopFolders: foundFolderCount += 1
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                if somethingUpper in compulsoryFiles: foundFileCount += 1
        if foundFolderCount == len(compulsoryTopFolders):
            assert foundFileCount == 0
            foundConfNames = confirmThisFolder( tryFolderName )
            if foundConfNames:
                for confName in foundConfNames:
                    foundProjects.append( (tryFolderName,confName) )
                    numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck foundProjects", numFound, foundProjects )
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
    def __init__( self, sourceFolder=None, moduleName=None, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.

        The sourceFolder should be the one containing mods.d and modules folders.
        The module name (if needed) should be the name of one of the .conf files in the mods.d folder
            (with or without the .conf on it).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"SwordBible.__init__( {sourceFolder} {moduleName} {encoding} ) for '{SwordResources.SwordType}'" )

        if not sourceFolder and not moduleName:
            logging.critical( _("SwordBible must be passed either a folder path or a module name!" ) )
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
                logging.critical( _("SwordBible: Folder {!r} is unreadable").format( self.sourceFolder ) )

            if not self.moduleName: # If we weren't passed the module name, we need to assume that there's only one
                confFolder = os.path.join( self.sourceFolder, 'mods.d/' )
                foundConfs = []
                for something in os.listdir( confFolder ):
                    somepath = os.path.join( confFolder, something )
                    if os.path.isfile( somepath ) and something.endswith( '.conf' ):
                        foundConfs.append( something[:-5] ) # Drop the .conf bit
                if foundConfs == 0:
                    logging.critical( "No .conf files found in {}".format( confFolder ) )
                elif len(foundConfs) > 1:
                    logging.critical( "Too many .conf files found in {}".format( confFolder ) )
                else:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "SwordBible.__init__ got", foundConfs[0] )
                    self.moduleName = foundConfs[0]
        self.abbreviation = self.moduleName # First attempt

        # Load the Sword manager and find our module
        if self.SwordInterface is None and SwordResources.SwordType is not None:
            self.SwordInterface = SwordResources.SwordInterface() # Load the Sword library
        if self.SwordInterface is None: # still
            logging.critical( _("SwordBible: no Sword interface available") )
            return
        #try: self.SWMgr = Sword.SWMgr()
        #except NameError:
            #logging.critical( _("Unable to initialise {!r} module -- no Sword manager available").format( self.moduleName ) )
            #return # our Sword import must have failed
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and SwordResources.SwordType=='CrosswireLibrary':
            availableGlobalOptions = [str(option) for option in self.SwordInterface.library.getGlobalOptions()]
            print( "availableGlobalOptions", availableGlobalOptions )
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
                #print( "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                #try: print( "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                #except UnicodeDecodeError: print( "   Description is not Unicode!" )
            #print( "moduleID", repr(moduleID) )
            availableModuleCodes.append( moduleID )
        #print( "Available module codes:", availableModuleCodes )

        if self.moduleName not in availableModuleCodes:
            logging.critical( "Unable to find {!r} Sword module".format( self.moduleName ) )
            if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                print( "Available module codes:", availableModuleCodes )

        self.abbreviation = self.moduleName # Perhaps a better attempt
    # end of SwordBible.__init__


    def loadBooks( self ):
        """
        Load the compressed data file and import book elements.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("SwordBible.loadBooks()") )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("\nLoading {} module…").format( self.moduleName ) )

        self.SwordInterface.loadBooks( self, self.moduleName )

        #try: module = self.SwordInterface.library.getModule( self.moduleName )
        #except AttributeError: # probably no SWMgr
            #logging.critical( _("Unable to load {!r} module -- no Sword loader available").format( self.moduleName ) )
            #return
        #if module is None:
            #logging.critical( _("Unable to load {!r} module -- not known by Sword").format( self.moduleName ) )
            #return

        #if SwordResources.SwordType=='CrosswireLibrary': # need to load the module
            #markupCode = ord( module.getMarkup() )
            #encoding = ord( module.getEncoding() )
            #if encoding == ENC_LATIN1: self.encoding = 'latin-1'
            #elif encoding == ENC_UTF8: self.encoding = 'utf-8'
            #elif encoding == ENC_UTF16: self.encoding = 'utf-16'
            #elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

            #if BibleOrgSysGlobals.verbosityLevel > 3:
                #print( 'Description: {!r}'.format( module.getDescription() ) )
                #print( 'Direction: {!r}'.format( ord(module.getDirection()) ) )
                #print( 'Encoding: {!r}'.format( encoding ) )
                #print( 'Language: {!r}'.format( module.getLanguage() ) )
                #print( 'Markup: {!r}={}'.format( markupCode, FMT_DICT[markupCode] ) )
                #print( 'Name: {!r}'.format( module.getName() ) )
                #print( 'RenderHeader: {!r}'.format( module.getRenderHeader() ) )
                #print( 'Type: {!r}'.format( module.getType() ) )
                #print( 'IsSkipConsecutiveLinks: {!r}'.format( module.isSkipConsecutiveLinks() ) )
                #print( 'IsUnicode: {!r}'.format( module.isUnicode() ) )
                #print( 'IsWritable: {!r}'.format( module.isWritable() ) )
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
                ##if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    ##print( '\nvkst={!r} vkix={}'.format( verseKeyText, verseKey.getIndex() ) )

                ##nativeVerseText = module.renderText().decode( self.encoding, 'replace' )
                ##nativeVerseText = str( module.renderText() ) if self.encoding=='utf-8' else str( module.renderText(), encoding=self.encoding )
                ##print( 'getRenderHeader: {} {!r}'.format( len(module.getRenderHeader()), module.getRenderHeader() ) )
                ##print( 'stripText: {} {!r}'.format( len(module.stripText()), module.stripText() ) )
                ##print( 'renderText: {} {!r}'.format( len(str(module.renderText())), str(module.renderText()) ) )
                ##print( 'getRawEntry: {} {!r}'.format( len(module.getRawEntry()), module.getRawEntry() ) )
                #try: nativeVerseText = module.getRawEntry()
                ##try: nativeVerseText = str( module.renderText() )
                #except UnicodeDecodeError: nativeVerseText = ''

                #if ':' not in verseKeyText:
                    #if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                        #print( "Unusual Sword verse key: {} (gave {!r})".format( verseKeyText, nativeVerseText ) )
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
                                #print( "Module created by {} {}".format( subType, n ) )
                    #continue
                #vkBits = verseKeyText.split()
                #assert len(vkBits) == 2
                #osisBBB = vkBits[0]
                #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBBB )
                #if isinstance( BBB, list ): BBB = BBB[0] # We sometimes get a list of options -- take the first = most likely one
                #vkBits = vkBits[1].split( ':' )
                #assert len(vkBits) == 2
                #C, V = vkBits
                ##print( 'At {} {}:{}'.format( BBB, C, V ) )

                ## Start a new book if necessary
                #if BBB != currentBBB:
                    #if currentBBB is not None and haveText: # Save the previous book
                        #if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", currentBBB, bookCount )
                        #self.stashBook( thisBook )
                    ## Create the new book
                    #if BibleOrgSysGlobals.verbosityLevel > 2:  print( '  Loading {} {}…'.format( self.moduleName, BBB ) )
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
                        #print( 'markupCode', repr(markupCode) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                        #return

            #if currentBBB is not None and haveText: # Save the very last book
                #if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", self.moduleName, currentBBB, bookCount )
                #self.stashBook( thisBook )


        #elif SwordResources.SwordType=='OurCode': # module is already loaded above
            ##print( "moduleConfig =", module.SwordModuleConfiguration )
            #self.books = module.books

        self.doPostLoadProcessing()
    # end of SwordBible.load
# end of SwordBible class



def testSwB( SwFolderPath, SwModuleName=None ):
    """
    Crudely demonstrate and test the Sword Bible class
    """
    from BibleOrgSys.Reference import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the Sword Bible class…") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( SwFolderPath, SwModuleName ) )
    SwBible = SwordBible( SwFolderPath, SwModuleName )
    SwBible.loadBooks() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( SwBible ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        SwBible.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        SwBErrors = SwBible.getErrors()
        # print( SwBErrors )
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
        #print( svk, SwBible.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = SwBible.getVerseText( svk )
            #print( "verseText", verseText )
            fullVerseText = SwBible.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if BibleOrgSysGlobals.debugFlag: print()
            print( reference, shortText, verseText )
            if BibleOrgSysGlobals.debugFlag: print( '  {}'.format( fullVerseText ) )
    return SwBible
# end of testSwB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    testFolder = os.path.join( os.path.expanduser('~'), '.sword/')
    # Matigsalug_Test module
    MSTestFolderOld = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../srv/Websites/Freely-Given.org/Software/BibleDropBox/Matigsalug.USFM.Demo/Sword_(from OSIS_Crosswire_Python)/CompressedSwordModule' ).resolve()
    MSTestFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../srv/Websites/Freely-Given.org/Software/BibleDropBox/MBTV.PTX8.Demo/Sword_(from OSIS_Crosswire_Python)/CompressedSwordModule' ).resolve()

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = SwordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA1", result1 )
        result2 = SwordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA2", result2 )
        result3 = SwordBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA3", result3 )

    if 1: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword B/ Trying single module in {}".format( MSTestFolder ) )
        testSwB( MSTestFolder )

    if 1: # specified single installed module
        singleModule = 'ASV'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword C/ Trying installed {} module".format( singleModule ) )
        SwBible = testSwB( None, singleModule )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in SwBible:
                SwBible.books[BBB].debugPrint()
                for entryKey in SwBible.books[BBB]._CVIndex:
                    print( BBB, entryKey, SwBible.books[BBB]._CVIndex.getEntries( entryKey ) )

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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword D{}/ Trying {}".format( j+1, testFilename ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testSwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testSwB( testFolder, someFolder )
# end of demo


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SwordBible.py
