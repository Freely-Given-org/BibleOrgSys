#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordInstallManager.py
#
# Module handling downloading and installing of Sword resources
#
# Copyright (C) 2016 Robert Hunt
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
This is the interface module used to give a unified interface to either:
    1/ The Crosswire Sword engine (libsword) via Python3 SWIG bindings,
        or, if that's not available, to
    2/ Our own (still primitive module that reads Sword files directly
        called SwordModules.py

Currently only uses FTP.
"""

from gettext import gettext as _

LastModifiedDate = '2016-04-19' # by RJH
ShortProgName = "SwordInstallManager"
ProgName = "Sword download handler"
ProgVersion = '0.04'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


#from singleton import singleton
import os, logging, re
import ftplib
#import urllib.request
import tarfile
import shutil
from collections import OrderedDict

import BibleOrgSysGlobals
#from VerseReferences import SimpleVerseKey
#from InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry



DEFAULT_SWORD_DOWNLOAD_SOURCES = OrderedDict([
    ('CrossWire Main', ('FTP', 'ftp.CrossWire.org', '/pub/sword/raw/' )),
    ('CrossWire Attic', ('FTP', 'ftp.CrossWire.org', '/pub/sword/atticraw/' )),
    ('Crosswire Beta', ('FTP', 'ftp.CrossWire.org', '/pub/sword/betaraw/' )),
    ('Crosswire Wycliffe', ('FTP', 'ftp.CrossWire.org', '/pub/sword/wyclifferaw/' )),
    ('Crosswire Alt Versification', ('FTP', 'ftp.CrossWire.org', '/pub/sword/avraw/' )),
    ('Crosswire Alt Vrsfctn Attic', ('FTP', 'ftp.CrossWire.org', '/pub/sword/avatticraw/' )),
    ('Crosswire IBT', ('FTP', 'ftp.CrossWire.org', '/pub/modsword/raw/' )),
    ('NET Bible', ('FTP', 'ftp.bible.org', '/sword/' )),
    ('Xiphos', ('FTP', 'ftp.Xiphos.org', '' )),
    #('eBible', ('FTP', 'ftp.Xiphos.org', '' )),
    ])

DEFAULT_SWORD_INSTALL_FOLDERS = (
    'usr/share/sword/',
    os.path.join( os.path.expanduser('~'), '.sword/'),
    )



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



IMPORTANT_SWORD_CONF_FIELD_NAMES = ( 'Name', 'Abbreviation', 'Font', 'Lang', 'Direction', 'Version', 'History', 'Description',
            'TextSource', 'Source', 'LCSH', 'ShortPromo', 'Promo', 'Obsoletes', 'GlossaryFrom', 'GlossaryTo',
            'DistributionSource', 'DistributionNotes', 'DistributionLicense',
            'Category', 'Feature', 'Versification', 'Scope', 'About',
            'Notes', 'NoticeLink', 'NoticeText',
            'Copyright', 'CopyrightHolder', 'CopyrightDate', 'CopyrightContactName', 'CopyrightContactEmail',
                'CopyrightContactAddress', 'CopyrightContactNotes', 'ShortCopyright',
                'CopyrightNotes', 'CopyrightYear',
            'DictionaryModule', 'ReferenceBible',
            'Siglum1', 'Siglum2', )
TECHNICAL_SWORD_CONF_FIELD_NAMES = ( 'ModDrv', 'DataPath', 'Encoding', 'SourceType', 'GlobalOptionFilter',
            'CaseSensitiveKeys', 'SearchOption',
            'CompressType', 'BlockType',
            'MinimumVersion', 'MinimumSwordVersion', 'SwordVersionDate', 'OSISVersion', 'minMKVersion',
            'DisplayLevel', 'LangSortOrder', 'LangSortSkipChars', 'StrongsPadding',
            'CipherKey', 'InstallSize', 'BlockCount', 'OSISqToTick', 'MinimumBlockNumber', 'MaximumBlockNumber', )
ALL_SWORD_CONF_FIELD_NAMES = IMPORTANT_SWORD_CONF_FIELD_NAMES + TECHNICAL_SWORD_CONF_FIELD_NAMES
SPECIAL_SWORD_CONF_FIELD_NAMES = ('History','Description','About','Copyright','DistributionNotes',) # Ones that have an underline and then a subfield



def processConfLines( abbreviation, openFile, confDict ):
    """
    Process a line from a Sword .conf file
        and saves the results in the confDict.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("processConfLines( {}, … )").format( abbreviation ) )

    lastLine, lineCount, continuationFlag, result = None, 0, False, []
    for line in openFile:
        lineCount += 1
        if lineCount==1:
            if line[0]==chr(65279): #U+FEFF
                logging.info( "SwordModuleConfiguration.loadConf1: Detected Unicode Byte Order Marker (BOM) in {}".format( filename ) )
                line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
            elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                logging.info( "SwordModuleConfiguration.loadConf2: Detected Unicode Byte Order Marker (BOM) in {}".format( filename ) )
                line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
        if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
        #print( lineCount, repr(line) )
        if not line: continue # Just discard blank lines
        #print ( "SwordModuleConfiguration.loadConf: Conf file line {} is {!r}".format( lineCount, line ) )
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
                #print( "lastLine = '"+lastLine+"'" )
                #print( "thisLine = '"+thisLine+"'" )
                if '=' not in thisLine:
                    logging.error( "Missing = in {} conf file line (line will be ignored): {!r}".format( abbreviation, thisLine ) )
                    continue
                if 'History=1.4-081031=' in thisLine: thisLine = thisLine.replace( '=', '_', 1 ) # Fix module error in strongsrealgreek.conf
                bits = thisLine.split( '=', 1 )
                #print( bits )
                assert len(bits) == 2
                for fieldName in SPECIAL_SWORD_CONF_FIELD_NAMES:
                    if bits[0].startswith(fieldName+'_'): # Just extract the various versions and put into a tuple
                        bits = [fieldName, (bits[0][len(fieldName)+1:],bits[1]) ]
                if bits[0]=='MinumumVersion': bits[0] = 'MinimumVersion' # Fix spelling error in several modules: nheb,nhebje,nhebme,cslelizabeth,khmernt, morphgnt, etc.
                if bits[0]=='CompressType' and bits[1]=='Zip': bits[1] = 'ZIP' # Fix error in romcor.conf
                if bits[0] in confDict: # already
                    if bits[1]==confDict[bits[0]]:
                        logging.info( "Conf file for {!r} has duplicate '{}={}' lines".format( abbreviation, bits[0], bits[1] ) )
                    else: # We have multiple different entries for this field name
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( "Sword Modules loadConf found inconsistency", abbreviation, bits[0], bits[1] )
                            assert bits[0] in SPECIAL_SWORD_CONF_FIELD_NAMES or bits[0] in ('GlobalOptionFilter','DictionaryModule','DistributionLicense','Feature','LCSH','Obsoletes','TextSource',) # These are the only ones where we expect multiple values (and some of these are probably module bugs)
                        if bits[0] in SPECIAL_SWORD_CONF_FIELD_NAMES: # Try to handle these duplicate entries -- we're expecting 2-tuples later
                            try: confDict[bits[0]].append( ('???',bits[1]) ) #; print( bits[0], 'lots' )
                            except AttributeError: confDict[bits[0]] = [('???',confDict[bits[0]]), ('???',bits[1]) ] #; print( bits[0], 'made list' )
                        else:
                            try: confDict[bits[0]].append( bits[1] ) #; print( bits[0], 'lots' )
                            except AttributeError: confDict[bits[0]] = [confDict[bits[0]], bits[1] ] #; print( bits[0], 'made list' )
                else: confDict[bits[0]] = bits[1] # Most fields only occur once
        lastLine = line

    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        #print( 'confDict', confDict )
        for cdKey,cdValue in confDict.items(): print( " {} = {}".format( cdKey, cdValue ) )
# end of processConfLines



class SwordInstallManager():
    """
    This is the class that gets a requested module from the web,
        downloads it, and installs it.
    """
    def __init__( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.__init__()") )

        self.userDisclaimerConfirmed = False

        # We default to allowing all of the default sources
        self.downloadSources = DEFAULT_SWORD_DOWNLOAD_SOURCES # OrderedDict
        self.currentRepoName = None

        self.installFolders = list( DEFAULT_SWORD_INSTALL_FOLDERS )
        self.currentInstallFolder = None

        self.availableModules = OrderedDict() # Contains a 2-tuple: confName (not including .conf) and confDict
    # end of SwordInstallManager.__init__


    def clearSources( self ):
        """
        Clear our list of available sources.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.clearSources()") )

        self.downloadSources = OrderedDict()
        self.currentRepoName = None
    # end of SwordInstallManager.clearSources


    def addSource( self, repoName, repoType, repoSite, repoFolder, setAsDefault=False ):
        """
        Adds a source to our ordered dict.

        The entry should contain four fields:
            1/ type (FTP)
            2/ name (string)
            3/ Site url (not including folders)
            4/ Site folders (starts with '/' )
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.addSource( {}, {}, {}, {}, {} )").format( repoName, repoType, repoSite, repoFolder, setAsDefault ) )
            assert repoType in ( 'FTP', )

        self.downloadSources[repoName] = (repoType,repoSite,repoFolder)
        if setAsDefault: source.currentRepoName = repoName
    # end of SwordInstallManager.addSource


    def isUserDisclaimerConfirmed( self ):
        """
        Ask the user to confirm the recommended disclaimer.

        This function can be overriden (esp. if you have a GUI).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.isUserDisclaimerConfirmed()") )

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


    def setUserDisclaimerConfirmed( self, flag=True ):
        """
        Set the flag to show that the user disclaimer has been confirmed.

        Use this if you don't want to override isUserDisclaimerConfirmed().
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.setUserDisclaimerConfirmed( {} )").format( flag ) )
            assert flag in (True, False)

        self.userDisclaimerConfirmed = flag
    # end of SwordInstallManager.setUserDisclaimerConfirmed


    def refreshRemoteSource( self, clearFirst=True ):
        """
        Get a list of available modules from the selected remote repository.

        Places the information in self.availableModules
            (which may need to be cleared to prevent obsolete entries being held).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.refreshRemoteSource( {} )").format( clearFirst ) )

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

        if clearFirst: self.availableModules = OrderedDict()

        # Assume that we're good to go
        repoType, repoSite, repoFolder = self.downloadSources[self.currentRepoName]
        assert repoType == 'FTP'
        if repoFolder:
            assert repoFolder[0] == '/'
            assert repoFolder[-1] == '/'

        repoConfFolderName = 'mods.d'
        repoCompressedFilename = repoConfFolderName + '.tar.gz'
        repoSaveFolder = '/tmp/'
        repoCompressedSaveFilepath = os.path.join( repoSaveFolder, repoCompressedFilename )
        if os.path.isfile( repoCompressedSaveFilepath ): # delete file if it exists
            #print( "Delete1", repoCompressedSaveFilepath )
            os.remove( repoCompressedSaveFilepath )
        repoConfFolder = os.path.join( repoSaveFolder, repoConfFolderName )
        if os.path.isdir( repoConfFolder ): # delete folder if it exists
            #print( "Delete2", repoConfFolder )
            shutil.rmtree( repoConfFolder )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("Refreshing/Downloading index files from {} repository…").format( self.currentRepoName ) )

        # Download the config files
        ftp = ftplib.FTP( repoSite )
        ftp.login() # anonymous:anonymous
        if repoFolder:
            assert repoFolder[0] == '/'
            ftp.cwd( repoFolder )
        ftp.retrbinary( 'RETR ' + repoCompressedFilename, open( repoCompressedSaveFilepath, 'wb' ).write )
        ftp.quit()

        # Extract the files from the compressed tar.gz file
        if os.path.isfile( repoCompressedSaveFilepath ):
            allConfigsTar = tarfile.open( repoCompressedSaveFilepath, mode='r:gz')
            allConfigsTar.extractall( path=repoSaveFolder )
        repoConfFolder = os.path.join( repoSaveFolder, repoConfFolderName )
        #print( 'repoConfFolder', repoConfFolder )

        # Find the names of the .conf files
        confNames = []
        for something in os.listdir( repoConfFolder ):
            somepath = os.path.join( repoConfFolder, something )
            if os.path.isfile( somepath ):
                if something.lower().endswith( '.conf' ):
                    confNames.append( something[:-5] ) # Remove .conf from filename
                else: print( "why", something )
            else: print( "got", something )
        #print( 'confNames', len(confNames), confNames )

        # Tried to do this all in memory using streams but couldn't make it work :(
        #repoPath = repoSite + repoFolder + repoCompressedFilename
        #print( _("Getting {!r} module list from {}…").format( repoName, repoPath ) )
        #ftpstream = urllib.request.urlopen( 'ftp://' + repoPath )
        #allConfigsTar = tarfile.open( fileobj=ftpstream, mode='r|gz')
        ##allConfigsTar.extractall()
        #for member in allConfigsTar:
            #print( '  m', member, member.name, member.size )
            #assert isinstance( member, tarfile.TarInfo )
            #print( '  mf', member.isfile() )
            #print( '  md', member.isdir() )
            #if member.isfile():
                #configData = allConfigsTar.extractfile( member.name )
                #print( '  cD', configData )

                #with gzip.open( configData, 'rt') as cFile1:
                    #print( '  cFile1', cFile1, dir(cFile1), cFile1.tell() )
                    ##print( 'ww', ww )
                    #configStuff = cFile1.readlines()
                    ##for x in cFile1:
                        ##print( 'x', x )
                    ##with open( cFile1, mode='rt' ) as cFile2:
                        ##print( '  cFile2', cFile2 )
                        ##configStuff = cFile2.read()
                #print( '  cS', configStuff )

        #print( allConfigs )

        # Place the conf files information into a dictionary
        for confName in confNames:
            confPath = os.path.join( repoConfFolder, confName+'.conf' )
            confDict = self._getConfFile( confName, confPath )
            self.availableModules[confDict['Name']] = (self.currentRepoName,confName,confDict)
        #print( 'availableModules', len(self.availableModules), self.availableModules.keys() )
        return True
    # end of SwordInstallManager.refreshRemoteSource


    def refreshAllRemoteSources( self ):
        """
        Get a list of available modules from all the remote repositories
            (irrespective of self.currentRepoName).

        Places the information in self.availableModules
            (which is cleared first).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.refreshRemoteSource()") )

        if not self.downloadSources:
            logging.critical( _("No remote Sword repository/repositories specified.") )
            return False
        if not self.userDisclaimerConfirmed:
            logging.critical( _("User security disclaimer not yet confirmed.") )
            return False

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("Refreshing/Downloading index files from {} repositories…").format( len(self.downloadSources) ) )

        saveRepo = self.currentRepoName # Remember this
        self.availableModules = OrderedDict()

        # Go through each repo and get the source list
        for repoName in self.downloadSources:
            self.currentRepoName = repoName
            self.refreshRemoteSource( clearFirst=False )

        self.currentRepoName = saveRepo
    # end of SwordInstallManager.refreshAllRemoteSources


    def _getConfFile( self, confName, confPath ):
        """
        Read a conf file that has already been download from a repository
            and parse the information into self.availableModules.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager._getConfFile( {}, {} )").format( confName, confPath ) )

        # Read the conf file
        confDict = OrderedDict()
        with open( confPath, 'rt' ) as confFile:
            processConfLines( confName, confFile, confDict )

        #print( 'confDict', confDict )
        return confDict
    # end of SwordInstallManager._getConfFile


    def installModule( self, moduleName ):
        """
        Install the requested module from the remote repository.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordInstallManager.installModule( {} )").format( moduleName ) )

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
        if not self.currentInstallFolder:
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

        moduleName = confDict['Name']
        moduleRelativePath = confDict['DataPath']
        if moduleRelativePath.startswith( './' ): moduleRelativePath = moduleRelativePath[2:]
        if moduleRelativePath[-1] != '/': moduleRelativePath += '/'
        #print( repr(moduleName), repr(moduleRelativePath) )
        fileSaveFolder = os.path.join( self.currentInstallFolder, moduleRelativePath )
        #print( "Save folder is", fileSaveFolder )
        if not os.path.isdir( fileSaveFolder): os.makedirs( fileSaveFolder )

        # Assume that we're good to go
        repoType, repoSite, repoFolder = self.downloadSources[repoName]
        assert repoType == 'FTP'
        if repoFolder:
            assert repoFolder[0] == '/'
            assert repoFolder[-1] == '/'

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("Downloading {!r} files from {} to {} …").format( moduleName, repoName, fileSaveFolder ) )

        # Download the files we need
        ftp = ftplib.FTP( repoSite )
        ftp.login() # anonymous:anonymous
        if repoFolder:
            assert repoFolder[0] == '/'
            ftp.cwd( repoFolder )
        for filename,filedict in ftp.mlsd( moduleRelativePath ):
            #print( '  ff', repr(filename), filedict )
            if filename not in ( '.','..', ): # Ignore these
                #print( "    Need to download", filename )
                fileSaveFilepath = os.path.join( fileSaveFolder, filename )
                #print( "    Save filepath is", fileSaveFilepath )
                ftp.retrbinary( 'RETR ' + moduleRelativePath + filename, open( fileSaveFilepath, 'wb' ).write )
        ftp.quit()
        return True
    # end of SwordInstallManager.installModule
# end of class SwordInstallManager



def demo():
    """
    Sword Manager
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    im = SwordInstallManager()
    if 0 and __name__ == '__main__': im.isUserDisclaimerConfirmed()
    else: im.setUserDisclaimerConfirmed()

    if 1: # try refreshing one repository
        im.currentRepoName = 'NET Bible'
        im.currentInstallFolder = '/tmp/'
        im.refreshRemoteSource()

    if 1: # try installing a module
        #im.installFolders.append( '.' )
        im.currentInstallFolder = 'TempTestData/'
        im.installModule( 'NETfree' )

    if 1: # try refreshing all repositories
        im.refreshAllRemoteSources()

    if 1: # try installing another module
        #im.installFolders.append( '.' )
        im.currentInstallFolder = 'TempTestData/'
        im.installModule( 'ESV' )
# end of demo

if __name__ == '__main__':
    #from multiprocessing import freeze_support
    #freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of SwordInstallManager.py