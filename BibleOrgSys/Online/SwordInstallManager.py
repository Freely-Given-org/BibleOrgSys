#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordInstallManager.py
#
# Module handling downloading and installing of Sword resources
#
# Copyright (C) 2016-2020 Robert Hunt
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
This is the interface module used to give a unified interface to either:
    1/ The Crosswire Sword engine (libsword) via Python3 SWIG bindings,
        or, if that's not available, to
    2/ Our own (still primitive module that reads Sword files directly
        called SwordModules.py

TODO: Currently only uses FTP which is about to be obsoleted!!!!
"""
from gettext import gettext as _
from typing import Dict, Any
import os
import logging
from pathlib import Path
import ftplib
#import urllib.request
import tempfile
import tarfile
import shutil

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint


LAST_MODIFIED_DATE = '2020-05-01' # by RJH
SHORT_PROGRAM_NAME = "SwordInstallManager"
PROGRAM_NAME = "Sword download handler"
PROGRAM_VERSION = '0.12'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


DEFAULT_SWORD_DOWNLOAD_SOURCES = { # Put these in priority order -- highest priority first
    'CrossWire Main': ('FTP', 'ftp.CrossWire.org', '/pub/sword/raw/' ),
    'CrossWire Attic': ('FTP', 'ftp.CrossWire.org', '/pub/sword/atticraw/' ),
    'Crosswire Beta': ('FTP', 'ftp.CrossWire.org', '/pub/sword/betaraw/' ),
    'Crosswire Wycliffe': ('FTP', 'ftp.CrossWire.org', '/pub/sword/wyclifferaw/' ),
    'Crosswire Alt Versification': ('FTP', 'ftp.CrossWire.org', '/pub/sword/avraw/' ),
    # Seems gone 'Crosswire Alt Vrsfctn Attic': ('FTP', 'ftp.CrossWire.org', '/pub/sword/avatticraw/' ),
    'Crosswire IBT': ('FTP', 'ftp.CrossWire.org', '/pub/modsword/raw/' ),
    'NET Bible': ('FTP', 'ftp.bible.org', '/sword/' ),
    'Xiphos': ('FTP', 'ftp.Xiphos.org', '' ),
    'eBible': ('FTP', 'ftp.eBible.org', '/pub/sword/' ),
    'eBible Beta': ('FTP', 'ftp.eBible.org', '/pub/swordbeta/' ),
}

DEFAULT_SWORD_INSTALL_FOLDERS = (
    Path( 'usr/share/sword/' ), # Traditional Linux global install folder
    os.path.join( os.path.expanduser('~'), '.sword/'), # Traditional local install folder
    )

DEFAULT_SWORD_CONF_ENCODING = 'iso-8859-1'



IMPORTANT_SWORD_CONF_FIELD_NAMES = ( 'Name', 'Abbreviation', 'Font', 'Lang', 'Direction', 'Version',
            'History', 'Description',
            'TextSource', 'Source', 'LCSH', 'ShortPromo', 'Promo', 'Obsoletes', 'GlossaryFrom', 'GlossaryTo',
            'DistributionSource', 'DistributionNotes', 'DistributionLicense',
            'Category', 'Feature', 'Versification', 'Scope', 'About',
            'Notes', 'NoticeLink', 'NoticeText',
            'Copyright',
            'CopyrightHolder',
            'CopyrightDate', 'CopyrightContact', 'CopyrightContactName', 'CopyrightContactEmail',
                'CopyrightContactAddress', 'CopyrightContactNotes', 'ShortCopyright',
                'CopyrightNotes', 'CopyrightYear', 'CopyrightLicense',
            'FontSizeAdjust', 'LineHeight',
            'DictionaryModule', 'ReferenceBible', 'Companion',
            'AudioCode',
            'PreferredCSSXHTML', # e.g., swmodule.css
            'TabLabel',
            'Siglum1', 'Siglum2', )
TECHNICAL_SWORD_CONF_FIELD_NAMES = ( 'ModDrv', 'DataPath', 'Encoding', 'SourceType', 'GlobalOptionFilter',
            'CaseSensitiveKeys',
            'KeyType', # e.g., TreeKey
            'SearchOption',
            'CompressType', 'BlockType',
            'MinimumVersion', 'MinimumSwordVersion', 'SwordVersion', 'SwordVersionDate', 'OSISVersion', 'minMKVersion',
            'DisplayLevel', 'LangSortOrder', 'LangSortSkipChars', 'StrongsPadding',
            'CipherKey', 'InstallSize', 'BlockCount', 'OSISqToTick', 'MinimumBlockNumber', 'MaximumBlockNumber', )
POSSIBLE_ERROR_SWORD_CONF_FIELD_NAMES = ( 'Copyright+por', 'onDate', 'Abour_sr', 'ModuleType', )
ALL_SWORD_CONF_FIELD_NAMES = IMPORTANT_SWORD_CONF_FIELD_NAMES + TECHNICAL_SWORD_CONF_FIELD_NAMES + POSSIBLE_ERROR_SWORD_CONF_FIELD_NAMES

# Ones that have an underline and then a subfield such as a language _en or _ru
SWORD_CONF_FIELD_NAMES_ALLOWED_VERSIONING = ('History', 'Description', 'About',
                                             'Copyright', 'CopyrightHolder', 'CopyrightContactAddress',
                                             'DistributionNotes', 'DistributionLicense', )

# These are the only ones where we expect multiple values (and some of these are probably module bugs)
SWORD_CONF_FIELD_NAMES_ALLOWED_DUPLICATES = ('Feature', 'GlobalOptionFilter', 'DistributionLicense', 'LCSH',
                                             'TextSource', 'DictionaryModule', 'Obsoletes', )
    # LCSH in sentiment.conf
    # DictionaryModule in ruscars.conf (rubbish) and tkl.conf (seems genuine)
    # TextSource in spavnt.conf
    # Obsoletes in tr.conf



def processConfLines( abbreviation:str, openFile, confDict ):
    """
    Process a line from a Sword .conf file
        and saves the results in the given confDict.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, _("processConfLines( {}, … )").format( abbreviation ) )

    lastLine, lineCount, continuationFlag, result = None, 0, False, []
    for line in openFile:
        lineCount += 1
        if lineCount==1:
            if line[0]==chr(65279): #U+FEFF
                logging.info( "processConfLines1: Detected Unicode Byte Order Marker (BOM) in {!r} conf file".format( abbreviation ) )
                line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
            elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                logging.info( "processConfLines2: Detected Unicode Byte Order Marker (BOM) in {!r} conf file".format( abbreviation ) )
                line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
        if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
        if not line: continue # Just discard blank lines
        #vPrint( 'Quiet', debuggingThisModule, "processConfLines: Conf file line {} is {!r}".format( lineCount, line ) )
        if line[0] in '#;': continue # Just discard comment lines
        if continuationFlag: thisLine += line; continuationFlag = False
        else: thisLine = line
        if thisLine and thisLine[-1]=='\\': thisLine = thisLine[:-1]; continuationFlag = True # This line should be continued
        if abbreviation=='burjudson' and thisLine.endswith(" available from "): continuationFlag = True # Bad module it seems

        if not continuationFlag: # process the line
            if lineCount==1 or lastLine==None: # First (non-blank) line should contain a name in square brackets
                assert '=' not in thisLine and thisLine[0]=='[' and thisLine[-1]==']'
                confDict['Name'] = thisLine[1:-1]
            else: # not the first line in the conf file
                #vPrint( 'Quiet', debuggingThisModule, "lastLine = '"+lastLine+"'" )
                #vPrint( 'Quiet', debuggingThisModule, "thisLine = '"+thisLine+"'" )
                if '=' not in thisLine:
                    logging.error( "Missing = in {} conf file line (line will be ignored): {!r}".format( abbreviation, thisLine ) )
                    continue
                if 'History=1.4-081031=' in thisLine and not BibleOrgSysGlobals.strictCheckingFlag:
                    thisLine = thisLine.replace( '=', '_', 1 ) # Fix module error in strongsrealgreek.conf
                bits = thisLine.split( '=', 1 )
                #vPrint( 'Quiet', debuggingThisModule, "processConfLines", abbreviation, bits )
                assert len(bits) == 2
                fieldName, fieldContents = bits
                for specialFieldName in SWORD_CONF_FIELD_NAMES_ALLOWED_VERSIONING:
                    if fieldName.startswith(specialFieldName+'_'): # Just extract the various versions and put into a tuple
                        fieldName, fieldContents = specialFieldName, (fieldName[len(specialFieldName)+1:],fieldContents)
                    elif fieldName.startswith(specialFieldName) and len(fieldName) > len(specialFieldName) \
                    and fieldName[len(specialFieldName)].isdigit() and '.' in fieldName[len(specialFieldName):] \
                    and not BibleOrgSysGlobals.strictCheckingFlag: # Could this be like History.1.0 in kapingamarangi
                        logging.warning( "{} conf file encountered badly formed {!r} field ({})" \
                                        .format( abbreviation, fieldName, fieldContents ) )
                        fieldName, fieldContents = specialFieldName, (fieldName[len(specialFieldName):],fieldContents)
                        #vPrint( 'Quiet', debuggingThisModule, repr(fieldName), repr(fieldContents) )
                if fieldName in SWORD_CONF_FIELD_NAMES_ALLOWED_VERSIONING and fieldContents and isinstance( fieldContents, str ) \
                and fieldContents[0].isdigit() and fieldContents[1] in '1234567890.' and fieldContents[2] in '1234567890.' \
                and '.' in fieldContents[0:3] and ' ' in fieldContents[2:5] \
                and not BibleOrgSysGlobals.strictCheckingFlag: # Could this be one also like in pohnold???
                    logging.warning( "{} conf file encountered badly formed {!r} field ({})" \
                                    .format( abbreviation, fieldName, fieldContents ) )
                    fieldContents = tuple( fieldContents.split( None, 1 ) )
                    #vPrint( 'Quiet', debuggingThisModule, "processConfLinesFC", abbreviation, "fieldContents", repr(fieldContents) )
                    assert len(fieldContents) == 2
                    #vPrint( 'Quiet', debuggingThisModule, j, "Now", abbreviation, repr(fieldName), repr(fieldContents) )
                if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                    assert '_' not in fieldName # now
                if fieldName=='MinumumVersion': fieldName = 'MinimumVersion' # Fix spelling error in several modules: nheb,nhebje,nhebme,cslelizabeth,khmernt, morphgnt, etc.
                if fieldName=='CompressType' and fieldContents=='Zip': fieldContents = 'ZIP' # Fix error in romcor.conf
                if fieldName in confDict and abbreviation!='ruscars': # ruscars has very untidy conf file
                    if fieldContents==confDict[fieldName]: # already
                        logging.info( "Conf file for {!r} has duplicate '{}={}' lines".format( abbreviation, fieldName, fieldContents ) )
                    else: # We have multiple different entries for this field name
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            vPrint( 'Quiet', debuggingThisModule, _("processConfLines found inconsistency"), abbreviation, fieldName, repr(fieldContents) )
                            vPrint( 'Quiet', debuggingThisModule, "  existing entry is", repr(confDict[fieldName]) )
                            assert fieldName in SWORD_CONF_FIELD_NAMES_ALLOWED_VERSIONING or fieldName in SWORD_CONF_FIELD_NAMES_ALLOWED_DUPLICATES
                        #if fieldName in SWORD_CONF_FIELD_NAMES_ALLOWED_VERSIONING: # Try to handle these duplicate entries
                            #try: confDict[fieldName].append( ('???',fieldContents) ) #; vPrint( 'Quiet', debuggingThisModule, fieldName, 'lots' )
                            #except AttributeError: confDict[fieldName] = [('???',confDict[fieldName]), ('???',fieldContents) ] #; vPrint( 'Quiet', debuggingThisModule, fieldName, 'made list' )
                        #else:
                        try: confDict[fieldName].append( fieldContents ) #; vPrint( 'Quiet', debuggingThisModule, fieldName, 'lots' )
                        except AttributeError: confDict[fieldName] = [confDict[fieldName], fieldContents ] #; vPrint( 'Quiet', debuggingThisModule, fieldName, 'made list' )
                    #vPrint( 'Quiet', debuggingThisModule, "here", repr(fieldName), confDict[fieldName] )
                else: confDict[fieldName] = fieldContents # Most fields only occur once
                #vPrint( 'Quiet', debuggingThisModule, "done", repr(fieldName), confDict[fieldName] )
        lastLine = line

    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        #vPrint( 'Quiet', debuggingThisModule, 'confDict', confDict )
        for cdKey,cdValue in confDict.items(): vPrint( 'Quiet', debuggingThisModule, " {} = {}".format( cdKey, cdValue ) )
# end of processConfLines



class SwordInstallManager():
    """
    This is the class that gets a requested module from the web,
        downloads it, and installs it.
    """
    def __init__( self ) -> None:
        """
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.__init__()…") )

        self.userDisclaimerConfirmed = False

        self.currentTempFolder = tempfile.gettempdir()

        # We default to allowing all of the default sources
        self.downloadSources = DEFAULT_SWORD_DOWNLOAD_SOURCES # dict
        self.currentRepoName = None

        self.installFolders = list( DEFAULT_SWORD_INSTALL_FOLDERS )
        self.currentInstallFolderpath = None

        self.availableModules = {} # Contains a 2-tuple: confName (not including .conf) and confDict
    # end of SwordInstallManager.__init__


    def clearSources( self ) -> None:
        """
        Clear our list of available sources.
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.clearSources()…") )

        self.downloadSources = {}
        self.currentRepoName = None
    # end of SwordInstallManager.clearSources


    def addSource( self, repoName:str, repoType:str, repoSite:str, repoFolderpath:Path, setAsDefault:bool=False ) -> None:
        """
        Adds a source to our ordered dict.

        The entry should contain four fields:
            1/ type (FTP)
            2/ name (string)
            3/ Site url (not including folders)
            4/ Site folders (starts with '/' )
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.addSource( {}, {}, {}, {}, {} )").format( repoName, repoType, repoSite, repoFolderpath, setAsDefault ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert repoType in ( 'FTP', )

        self.downloadSources[repoName] = (repoType,repoSite,repoFolderpath)
        if setAsDefault: source.currentRepoName = repoName
    # end of SwordInstallManager.addSource


    def isUserDisclaimerConfirmed( self ) -> None:
        """
        Ask the user to confirm the recommended disclaimer.

        This function can be overriden (esp. if you have a GUI).
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.isUserDisclaimerConfirmed()…") )

        prompt1 = _("\nAlthough Install Manager provides a convenient way for installing and upgrading SWORD " \
                    "components, it also uses a systematic method for accessing sites which gives packet " \
                    "sniffers a target to lock into for singling out users.\n" \
                    "IF YOU LIVE IN A PERSECUTED COUNTRY AND DO NOT WISH TO RISK DETECTION, YOU SHOULD " \
                    "*NOT* USE INSTALL MANAGER'S REMOTE SOURCE FEATURES.\n" \
                    "Also, some remote sources may contain lower quality modules, modules with " \
                    "unorthodox content, or even modules which are not legitimately distributable. " \
                    "On the other hand, many repositories contain wonderfully useful content. " \
                    "The quality of the content is dependent on the repository owner. " \
                    "If you understand this and are willing to enable remote source features " \
                    "then type yes at the prompt: " )
        userInput = input( prompt1 ).lower()
        if userInput == 'yes': self.userDisclaimerConfirmed = True
    # end of SwordInstallManager.isUserDisclaimerConfirmed


    def setUserDisclaimerConfirmed( self, flag:bool=True ) -> None:
        """
        Set the flag to show that the user disclaimer has been confirmed.

        Use this if you don't want to override isUserDisclaimerConfirmed().
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.setUserDisclaimerConfirmed( {} )").format( flag ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert flag in (True, False)

        self.userDisclaimerConfirmed = flag
    # end of SwordInstallManager.setUserDisclaimerConfirmed


    def refreshRemoteSource( self, clearFirst:bool=True ) -> bool:
        """
        Get a list of available modules from the selected remote repository.

        Places the information in self.availableModules
            (which may need to be cleared to prevent obsolete entries being held).
        """
        vPrint( 'Verbose', debuggingThisModule, f"SwordInstallManager.refreshRemoteSource( clearFirst={clearFirst} )…" )
        vPrint( 'Never', debuggingThisModule, f"self.downloadSources ({len(self.downloadSources)}) {self.downloadSources}" )
        vPrint( 'Never', debuggingThisModule, f"self.currentRepoName='{self.currentRepoName}'" )
        vPrint( 'Never', debuggingThisModule, f"self.userDisclaimerConfirmed={self.userDisclaimerConfirmed}" )
        vPrint( 'Never', debuggingThisModule, f"self.downloadSources[self.currentRepoName] ({len(self.downloadSources[self.currentRepoName])}) {self.downloadSources[self.currentRepoName]}" )

        if not self.downloadSources:
            logging.critical( _("No remote Sword repository/repositories specified.") )
            return False
        if not self.currentRepoName:
            logging.critical( _("No remote Sword repository selected.") )
            return False
        if self.currentRepoName not in self.downloadSources:
            logging.critical( _("No valid remote Sword repository selected.") )
            return False
        if not self.userDisclaimerConfirmed:
            logging.critical( _("User security disclaimer not yet confirmed.") )
            return False

        if clearFirst: self.availableModules = {}

        # Assume that we're good to go
        repoType, repoSite, repoFolderpath = self.downloadSources[self.currentRepoName]
        assert repoType == 'FTP'
        if repoFolderpath:
            assert repoFolderpath[0] == '/'
            assert repoFolderpath[-1] == '/'

        repoConfFolderName = 'mods.d'
        repoCompressedFilename = repoConfFolderName + '.tar.gz'
        repoSaveFolder = self.currentTempFolder
        repoCompressedSaveFilepath = os.path.join( repoSaveFolder, repoCompressedFilename )
        if os.path.isfile( repoCompressedSaveFilepath ): # delete file if it exists
            #vPrint( 'Quiet', debuggingThisModule, "Delete1", repoCompressedSaveFilepath )
            os.remove( repoCompressedSaveFilepath )
        repoConfFolder = os.path.join( repoSaveFolder, repoConfFolderName )
        if os.path.isdir( repoConfFolder ): # delete folder if it exists
            #vPrint( 'Quiet', debuggingThisModule, "Delete2", repoConfFolder )
            shutil.rmtree( repoConfFolder )

        vPrint( 'Normal', debuggingThisModule, _("Refreshing/Downloading index files from {} repository…").format( self.currentRepoName ) )

        # Download the config files
        ftp = ftplib.FTP( repoSite )
        ftp.login() # anonymous:anonymous
        if repoFolderpath:
            assert repoFolderpath[0] == '/'
            try: ftp.cwd( repoFolderpath )
            except ftplib.error_perm as err:
                #logging.error( "refreshRemoteSource: FTP error:", sys.exc_info()[0], err )
                logging.error( "refreshRemoteSource: Unable to reach {} on {} with {!r}" \
                                                .format( repoFolderpath, repoSite, err ) )
                return False
        ftp.retrbinary( 'RETR ' + repoCompressedFilename, open( repoCompressedSaveFilepath, 'wb' ).write )
        ftp.quit()

        # Extract the files from the compressed tar.gz file
        if os.path.isfile( repoCompressedSaveFilepath ):
            allConfigsTar = tarfile.open( repoCompressedSaveFilepath, mode='r:gz')
            allConfigsTar.extractall( path=repoSaveFolder )
        repoConfFolder = os.path.join( repoSaveFolder, repoConfFolderName )
        #vPrint( 'Quiet', debuggingThisModule, 'repoConfFolder', repoConfFolder )

        # Find the names of the .conf files
        confNames = []
        for something in os.listdir( repoConfFolder ):
            somepath = os.path.join( repoConfFolder, something )
            if os.path.isfile( somepath ):
                if something.lower().endswith( '.conf' ):
                    confNames.append( something[:-5] ) # Remove .conf from filename
                else: vPrint( 'Quiet', debuggingThisModule, "why", something )
            else: vPrint( 'Quiet', debuggingThisModule, "got", something )
        #vPrint( 'Quiet', debuggingThisModule, 'confNames', len(confNames), confNames )

        # Tried to do this all in memory using streams but couldn't make it work :(
        #repoPath = repoSite + repoFolderpath + repoCompressedFilename
        #vPrint( 'Quiet', debuggingThisModule, _("Getting {!r} module list from {}…").format( repoName, repoPath ) )
        #ftpstream = urllib.request.urlopen( 'ftp://' + repoPath )
        #allConfigsTar = tarfile.open( fileobj=ftpstream, mode='r|gz')
        ##allConfigsTar.extractall()
        #for member in allConfigsTar:
            #vPrint( 'Quiet', debuggingThisModule, '  m', member, member.name, member.size )
            #assert isinstance( member, tarfile.TarInfo )
            #vPrint( 'Quiet', debuggingThisModule, '  mf', member.isfile() )
            #vPrint( 'Quiet', debuggingThisModule, '  md', member.isdir() )
            #if member.isfile():
                #configData = allConfigsTar.extractfile( member.name )
                #vPrint( 'Quiet', debuggingThisModule, '  cD', configData )

                #with gzip.open( configData, 'rt', encoding='utf-8' ) as cFile1:
                    #vPrint( 'Quiet', debuggingThisModule, '  cFile1', cFile1, dir(cFile1), cFile1.tell() )
                    ##vPrint( 'Quiet', debuggingThisModule, 'ww', ww )
                    #configStuff = cFile1.readlines()
                    ##for x in cFile1:
                        ##vPrint( 'Quiet', debuggingThisModule, 'x', x )
                    ##with open( cFile1, mode='rt', encoding='utf-8' ) as cFile2:
                        ##vPrint( 'Quiet', debuggingThisModule, '  cFile2', cFile2 )
                        ##configStuff = cFile2.read()
                #vPrint( 'Quiet', debuggingThisModule, '  cS', configStuff )

        #vPrint( 'Quiet', debuggingThisModule, allConfigs )

        # Place the conf files information into a dictionary
        for confName in confNames:
            confPath = os.path.join( repoConfFolder, confName+'.conf' )
            confDict = self._getConfFile( confName, confPath )
            moduleName = confDict['Name']
            newTuple = (self.currentRepoName,confName,confDict)
            if moduleName in self.availableModules: # already
                logging.warning( "refreshRemoteSource: {} module already in {}, now found in {}".format( moduleName, self.availableModules[moduleName][0], self.currentRepoName ) )
                existing = self.availableModules[moduleName]
                if isinstance( existing, tuple): self.availableModules[moduleName] = [existing,newTuple]
                else: self.availableModules[moduleName].append( newTuple )
            else: # add it
                self.availableModules[moduleName] = newTuple
        #vPrint( 'Quiet', debuggingThisModule, 'availableModules', len(self.availableModules), self.availableModules.keys() )
        return True
    # end of SwordInstallManager.refreshRemoteSource


    def refreshAllRemoteSources( self ) -> None:
        """
        Get a list of available modules from all the remote repositories
            (irrespective of self.currentRepoName).

        Places the information in self.availableModules
            (which is cleared first).
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.refreshRemoteSource()…") )

        if not self.downloadSources:
            logging.critical( _("No remote Sword repository/repositories specified.") )
            return False
        if not self.userDisclaimerConfirmed:
            logging.critical( _("User security disclaimer not yet confirmed.") )
            return False

        vPrint( 'Normal', debuggingThisModule, _("Refreshing/Downloading index files from {} repositories…").format( len(self.downloadSources) ) )

        saveRepo = self.currentRepoName # Remember this
        self.availableModules = {}

        # Go through each repo and get the source list
        for repoName in self.downloadSources:
            self.currentRepoName = repoName
            self.refreshRemoteSource( clearFirst=False )

        self.currentRepoName = saveRepo
    # end of SwordInstallManager.refreshAllRemoteSources


    def _getConfFile( self, confName:str, confPath:Path ) -> Dict[str,Any]:
        """
        Read a conf file that has already been download from a repository
            and parse the information into self.availableModules.
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager._getConfFile( {}, {} )").format( confName, confPath ) )

        # Read the conf file
        confDict = {}
        with open( confPath, 'rt', encoding=DEFAULT_SWORD_CONF_ENCODING ) as confFile:
            processConfLines( confName, confFile, confDict )

        #vPrint( 'Quiet', debuggingThisModule, 'confDict', confDict )
        return confDict
    # end of SwordInstallManager._getConfFile


    def installModule( self, moduleName:str ):
        """
        Install the requested module from the remote repository.
        """
        vPrint( 'Never', debuggingThisModule, _("SwordInstallManager.installModule( {} )").format( moduleName ) )

        if not self.downloadSources:
            logging.critical( _("No remote Sword repository/repositories specified.") )
            return False
        if not self.currentRepoName:
            logging.critical( _("No remote Sword repository selected.") )
            return False
        if self.currentRepoName not in self.downloadSources:
            logging.critical( _("No valid remote Sword repository selected.") )
            return False
        if not self.userDisclaimerConfirmed:
            logging.critical( _("User security disclaimer not yet confirmed.") )
            return False
        if not self.installFolders:
            logging.critical( _("No valid folder(s) specified to save files in.") )
            return False
        if not self.currentInstallFolderpath:
            logging.critical( _("No valid folder selected to save files in.") )
            return False
        if not self.availableModules:
            logging.critical( _("No valid module list available.") )
            return False
        if moduleName not in self.availableModules:
            logging.critical( _("{!r} module not available.").format( moduleName ) )
            return False

        # Get the config info
        repoName, confName, confDict = self.availableModules[moduleName]
        if repoName != self.currentRepoName:
            vPrint( 'Quiet', debuggingThisModule, "installModule: You requested {!r} from {} but it's in {}!".format( moduleName, self.currentRepoName, repoName ) )
            return False

        moduleName = confDict['Name']
        moduleRelativePath = confDict['DataPath']
        if moduleRelativePath.startswith( './' ): moduleRelativePath = moduleRelativePath[2:]
        if str(moduleRelativePath)[-1] != '/':
            moduleRelativePath = f'{moduleRelativePath}/'
        #vPrint( 'Quiet', debuggingThisModule, repr(moduleName), repr(moduleRelativePath) )
        fileSaveFolder = os.path.join( self.currentInstallFolderpath, moduleRelativePath )
        #vPrint( 'Quiet', debuggingThisModule, "Save folder is", fileSaveFolder )
        if not os.path.isdir( fileSaveFolder): os.makedirs( fileSaveFolder )

        # Assume that we're good to go
        repoType, repoSite, repoFolderpath = self.downloadSources[repoName]
        assert repoType == 'FTP'
        if repoFolderpath:
            assert repoFolderpath[0] == '/'
            assert repoFolderpath[-1] == '/'

        vPrint( 'Normal', debuggingThisModule, _("Downloading {!r} files from {} to {} …").format( moduleName, repoName, fileSaveFolder ) )

        # Download the files we need
        ftp = ftplib.FTP( repoSite )
        ftp.login() # anonymous:anonymous
        if repoFolderpath:
            assert repoFolderpath[0] == '/'
            try: ftp.cwd( repoFolderpath )
            except ftplib.error_perm as err:
                #logging.error( "installModule: FTP error:", sys.exc_info()[0], err )
                logging.error( "installModule: Unable to reach {} on {} with {!r}" \
                                            .format( repoFolderpath, repoSite, err ) )
                return False
        for filename,filedict in ftp.mlsd( moduleRelativePath ):
            #vPrint( 'Quiet', debuggingThisModule, '  ff', repr(filename), filedict )
            if filename not in ( '.','..', ): # Ignore these
                #vPrint( 'Quiet', debuggingThisModule, "    Need to download", filename )
                fileSaveFilepath = os.path.join( fileSaveFolder, filename )
                #vPrint( 'Quiet', debuggingThisModule, "    Save filepath is", fileSaveFilepath )
                ftp.retrbinary( 'RETR ' + moduleRelativePath + filename,
                                    open( fileSaveFilepath, 'wb' ).write )

        # Finally download and install the .conf file
        confFullname = confName+'.conf'
        confFolderpath = os.path.join( self.currentInstallFolderpath, 'mods.d/' )
        if not os.path.isdir( confFolderpath): os.makedirs( confFolderpath )
        confFilePath = os.path.join( confFolderpath, confFullname )
        vPrint( 'Quiet', debuggingThisModule, 'confFilePath', confFilePath )
        ftp.retrbinary( 'RETR ' + 'mods.d/' + confFullname,
                        open( confFilePath, 'wb' ).write ) # , encoding=DEFAULT_SWORD_CONF_ENCODING
        ftp.quit()
        return True
    # end of SwordInstallManager.installModule
# end of class SwordInstallManager



def briefDemo() -> None:
    """
    Sword Manager demo
    """
    from BibleOrgSys.Formats import SwordModules

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    im = SwordInstallManager()
    if 0 and __name__ == '__main__': im.isUserDisclaimerConfirmed()
    else: im.setUserDisclaimerConfirmed()

    if 1: # try refreshing one repository
        getRepoName = 'NET Bible'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh {} repository…".format( getRepoName ) )
        im.currentRepoName = getRepoName
        im.currentInstallFolderpath = im.currentTempFolder
        im.refreshRemoteSource()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                for modName in im.availableModules:
                    vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

        if 1: # try installing and testing a module from the above repository
            getModuleName = 'NETfree'
            vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
            im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
            if im.installModule( getModuleName ):
                confData = im.availableModules[getModuleName]
                if isinstance( confData, tuple ): confName = confData[1]
                elif isinstance( confData, list ): confName = confData[0][1]
                swMC = SwordModules.SwordModuleConfiguration( confName, im.currentInstallFolderpath )
                swMC.loadConf()
                vPrint( 'Quiet', debuggingThisModule, swMC )

                swM = SwordModules.SwordModule( swMC )
                swM.loadBooks( inMemoryFlag=True )
                vPrint( 'Verbose', debuggingThisModule, swM )
                if not swM.SwordModuleConfiguration.locked: swM.test()


    if 0: # try refreshing one repository
        getRepoName = 'eBible'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh {} repository…".format( getRepoName ) )
        im.currentRepoName = getRepoName
        im.currentInstallFolderpath = im.currentTempFolder
        im.refreshRemoteSource()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                for modName in im.availableModules:
                    vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

        if 1: # try installing and testing a module from the above repository
            getModuleName = 'engWEBBE2015eb'
            vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
            im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
            if im.installModule( getModuleName ):
                swMC = SwordModules.SwordModuleConfiguration( getModuleName, im.currentInstallFolderpath )
                swMC.loadConf()
                vPrint( 'Quiet', debuggingThisModule, swMC )

                swM = SwordModules.SwordModule( swMC )
                swM.loadBooks( inMemoryFlag=True )
                vPrint( 'Verbose', debuggingThisModule, swM )
                if not swM.SwordModuleConfiguration.locked: swM.test()


    if 0: # try refreshing all repositories
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh all repositories…" )
        im.refreshAllRemoteSources()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            for modName in im.availableModules:
                vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

    if 0: # try installing another module
        getModuleName = 'JPS'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
        im.currentRepoName = 'CrossWire Main'
        im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
        if im.installModule( getModuleName ): # See if we can read it
            confData = im.availableModules[getModuleName]
            if isinstance( confData, tuple ): confName = confData[1]
            elif isinstance( confData, list ): confName = confData[0][1]
            swMC = SwordModules.SwordModuleConfiguration( confName, im.currentInstallFolderpath )
            swMC.loadConf()
            vPrint( 'Quiet', debuggingThisModule, swMC )

            swM = SwordModules.SwordModule( swMC )
            swM.loadBooks( inMemoryFlag=True )
            vPrint( 'Verbose', debuggingThisModule, swM )
            if not swM.SwordModuleConfiguration.locked: swM.test()
# end of SwordInstallManager.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    from BibleOrgSys.Formats import SwordModules

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    im = SwordInstallManager()
    if 0 and __name__ == '__main__': im.isUserDisclaimerConfirmed()
    else: im.setUserDisclaimerConfirmed()

    if 1: # try refreshing one repository
        getRepoName = 'NET Bible'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh {} repository…".format( getRepoName ) )
        im.currentRepoName = getRepoName
        im.currentInstallFolderpath = im.currentTempFolder
        im.refreshRemoteSource()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                for modName in im.availableModules:
                    vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

        if 1: # try installing and testing a module from the above repository
            getModuleName = 'NETfree'
            vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
            im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
            if im.installModule( getModuleName ):
                confData = im.availableModules[getModuleName]
                if isinstance( confData, tuple ): confName = confData[1]
                elif isinstance( confData, list ): confName = confData[0][1]
                swMC = SwordModules.SwordModuleConfiguration( confName, im.currentInstallFolderpath )
                swMC.loadConf()
                vPrint( 'Quiet', debuggingThisModule, swMC )

                swM = SwordModules.SwordModule( swMC )
                swM.loadBooks( inMemoryFlag=True )
                vPrint( 'Verbose', debuggingThisModule, swM )
                if not swM.SwordModuleConfiguration.locked: swM.test()


    if 0: # try refreshing one repository
        getRepoName = 'eBible'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh {} repository…".format( getRepoName ) )
        im.currentRepoName = getRepoName
        im.currentInstallFolderpath = im.currentTempFolder
        im.refreshRemoteSource()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                for modName in im.availableModules:
                    vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

        if 1: # try installing and testing a module from the above repository
            getModuleName = 'engWEBBE2015eb'
            vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
            im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
            if im.installModule( getModuleName ):
                swMC = SwordModules.SwordModuleConfiguration( getModuleName, im.currentInstallFolderpath )
                swMC.loadConf()
                vPrint( 'Quiet', debuggingThisModule, swMC )

                swM = SwordModules.SwordModule( swMC )
                swM.loadBooks( inMemoryFlag=True )
                vPrint( 'Verbose', debuggingThisModule, swM )
                if not swM.SwordModuleConfiguration.locked: swM.test()


    if 0: # try refreshing all repositories
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Refresh all repositories…" )
        im.refreshAllRemoteSources()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "{} modules: {}".format( len(im.availableModules), im.availableModules.keys() ) )
            for modName in im.availableModules:
                vPrint( 'Quiet', debuggingThisModule, "  {}: {}".format( modName, im.availableModules[modName][0] ) )

    if 1: # try installing another module
        getModuleName = 'JPS'
        vPrint( 'Quiet', debuggingThisModule, "\nDemo: Install {}…".format( getModuleName ) )
        im.currentRepoName = 'CrossWire Main'
        im.currentInstallFolderpath = 'TempSwInstMgrTestData/'
        if im.installModule( getModuleName ): # See if we can read it
            confData = im.availableModules[getModuleName]
            if isinstance( confData, tuple ): confName = confData[1]
            elif isinstance( confData, list ): confName = confData[0][1]
            swMC = SwordModules.SwordModuleConfiguration( confName, im.currentInstallFolderpath )
            swMC.loadConf()
            vPrint( 'Quiet', debuggingThisModule, swMC )

            swM = SwordModules.SwordModule( swMC )
            swM.loadBooks( inMemoryFlag=True )
            vPrint( 'Verbose', debuggingThisModule, swM )
            if not swM.SwordModuleConfiguration.locked: swM.test()
# end of SwordInstallManager.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SwordInstallManager.py
