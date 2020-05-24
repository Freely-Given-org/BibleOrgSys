#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleOrgSysGlobals.py
#
# Module handling Global variables for our Bible Organisational System
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module handling global variables
    and some useful general functions.

Contains functions:
    setupLoggingToFile( PROGRAM_NAME, PROGRAM_VERSION, loggingFolderpath=None )
    addConsoleLogging()
    addLogfile( projectName, folderName=None )
    removeLogfile( projectHandler )

    findHomeFolderpath()
    findUsername()

    getLatestPythonModificationDate()

    makeSafeFilename( someName )
    makeSafeXML( someString )
    makeSafeString( someString )
    removeAccents( someString )

    backupAnyExistingFile( filenameOrFilepath, numBackups=1 )
    peekIntoFile( filenameOrFilepath, folderName=None, numLines=1 )

    totalSize( obj, handlers={} )

    fileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 )
    fileCompareUSFM( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 )
    fileCompareXML( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10, ignoreWhitespace=True )

    elementStr( element )
    checkXMLNoAttributes( element, locationString, idString=None )
    checkXMLNoText( element, locationString, idString=None )
    checkXMLNoTail( element, locationString, idString=None )
    checkXMLNoSubelements( element, locationString, idString=None )
    checkXMLNoSubelementsWithText( element, locationString, idString=None )
    getFlattenedXML( element, locationString, idString=None, level=0 )
    isBlank( elementText )

    applyStringAdjustments( originalText, adjustmentList )
    stripWordPunctuation( wordToken )

    pickleObject( theObject, filename, folderName=None )
    unpickleObject( filename, folderName=None )

    setup( PROGRAM_NAME, PROGRAM_VERSION, loggingFolder=None )

    setVerbosity( verbosityLevelParameter )
    vPrint( level:str, debuggingThatModule:bool/int, printString:str )
    dPrint( level:str, debuggingThatModule:bool/int, printString:str )
    fnPrint( debuggingThatModule:bool/int, printString:str )
    introduceProgram( name:str, programNameVersion:str, LAST_MODIFIED_DATE:str ) -> None:

    setDebugFlag( newValue=True )
    setStrictCheckingFlag( newValue=True )

    addStandardOptionsAndProcess( parserObject )
    printAllGlobals( indent=None )

    closedown( PROGRAM_NAME, PROGRAM_VERSION )

    fullDemo()
"""
from gettext import gettext as _
from typing import List, Tuple, Optional, Union
import sys
import logging
import os.path
from pathlib import Path
import pickle
from datetime import datetime
import unicodedata
from argparse import ArgumentParser, Namespace
import configparser

# pwd:Optional[Any] # Should be Module
try: import pwd
except ImportError:
    pwd = None
    import getpass

if __name__ == '__main__':
    aboveFolderpath = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
    if aboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveFolderpath )


LAST_MODIFIED_DATE = '2020-05-24' # by RJH
SHORT_PROGRAM_NAME = "BibleOrgSysGlobals"
PROGRAM_NAME = "BibleOrgSys (BOS) Globals"
PROGRAM_VERSION = '0.88'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False
haltOnXMLWarning = False # Used for XML debugging


# Global variables
#=================

# Online settings
# TODO: Should be https as soon as supported by the site
SUPPORT_SITE_NAME = 'Freely-Given.org'
SUPPORT_SITE_URL = f'http://{SUPPORT_SITE_NAME}/'
DISTRIBUTABLE_RESOURCES_URL = f'{SUPPORT_SITE_URL}Software/BibleOrganisationalSystem/DistributableResources/'

PICKLED_BIBLE_VERSION = '1' # Must be incremented if Bible internals get changed


programStartTime = datetime.now()
commandLineArguments = Namespace()

strictCheckingFlag = debugFlag = False
maxProcesses = 1
alreadyMultiprocessing = False # Not used in this module, but set to prevent multiple levels of multiprocessing (illegal)
verbosityLevel = 2
verbosityString = 'Normal'


##########################################################################################################


COMMONLY_IGNORED_FOLDERS = '.hg', '.git','.gitignore','.github', '__MACOSX' # Used when searching for Bibles
if debuggingThisModule:
    LOGGING_NAME_DICT = {logging.DEBUG:'DEBUG', logging.INFO:'INFO', logging.WARNING:'WARNING', logging.ERROR:'ERROR', logging.CRITICAL:'CRITICAL'}


# Some language independant punctuation help
OPENING_SPEECH_CHARACTERS = """“«"‘‹¿¡""" # The length and order of these two strings must match
CLOSING_SPEECH_CHARACTERS = """”»"’›?!"""
MATCHING_OPENING_CHARACTERS = {'(':')', '[':']', '{':'}', '<':'>', '<<':'>>', '“':'”', '‘':'‘', '«':'»', '‹':'›', '¿':'?', '¡':'!', }
MATCHING_CLOSING_CHARACTERS = {')':'(', ']':'[', '}':'{', '>':'<', '>>':'<<', '”':'“', '‘':'‘', '»':'«', '›':'‹', '?':'¿', '!':'¡', }
MATCHING_CHARACTERS = {'(':')',')':'(', '[':']',']':'[', '{':'}','}':'{', '<':'>','>':'<', '<<':'>>','>>':'<<',
                      '“':'”','”':'“', '‘':'’','’':'‘', '«':'»','»':'«', '‹':'›','›':'‹', '¿':'?','?':'¿', '¡':'!','!':'¡', }
LEADING_WORD_PUNCT_CHARS = """“«„"‘¿¡‹'([{<"""
MEDIAL_WORD_PUNCT_CHARS = '-'
DASH_CHARS = '–—' # en-dash and em-dash
TRAILING_WORD_PUNCT_CHARS = """,.”»"’›'?)!;:]}>%…—।""" # Last one is from Hindi: DEVANAGARI DANDA / purna viram
TRAILING_WORD_END_CHARS = ' ' + TRAILING_WORD_PUNCT_CHARS
ALL_WORD_PUNCT_CHARS = LEADING_WORD_PUNCT_CHARS + MEDIAL_WORD_PUNCT_CHARS + DASH_CHARS + TRAILING_WORD_PUNCT_CHARS
MAX_NESTED_QUOTE_LEVELS = 5

if debuggingThisModule:
    assert len(OPENING_SPEECH_CHARACTERS) == len(CLOSING_SPEECH_CHARACTERS)
    assert len(MATCHING_OPENING_CHARACTERS) == len(MATCHING_CLOSING_CHARACTERS)
    assert len(MATCHING_OPENING_CHARACTERS) + len(MATCHING_CLOSING_CHARACTERS) == len(MATCHING_CHARACTERS)
    for o_char in OPENING_SPEECH_CHARACTERS: assert o_char in LEADING_WORD_PUNCT_CHARS
    for c_char in CLOSING_SPEECH_CHARACTERS: assert c_char in TRAILING_WORD_PUNCT_CHARS

    ##import unicodedata
    #BibleOrgSysGlobals.printUnicodeInfo( LEADING_WORD_PUNCT_CHARS, "LEADING_WORD_PUNCT_CHARS" )
    #BibleOrgSysGlobals.printUnicodeInfo( TRAILING_WORD_PUNCT_CHARS, "TRAILING_WORD_PUNCT_CHARS" )


ALLOWED_ORGANISATIONAL_TYPES = ( 'edition', 'revision', 'translation', 'original', ) # NOTE: The order is important here


##########################################################################################################
#
# Readable folder paths (Writeable ones are further down)
BOS_SOURCE_BASE_FOLDERPATH = Path( __file__ ).parent.resolve() # Folder containing this file
#dPrint( 'Quiet', debuggingThisModule, f"BOS_SOURCE_BASE_FOLDERPATH = {BOS_SOURCE_BASE_FOLDERPATH}" )
BOS_DATAFILES_FOLDERPATH = BOS_SOURCE_BASE_FOLDERPATH.joinpath( 'DataFiles/' )
BOS_DERIVED_DATAFILES_FOLDERPATH = BOS_DATAFILES_FOLDERPATH.joinpath( 'DerivedFiles/' )
BOS_DISTRIBUTED_FILES_FOLDERPATH = BOS_SOURCE_BASE_FOLDERPATH.joinpath( 'DistributedFiles/' )

BOS_LIBRARY_BASE_FOLDERPATH = BOS_SOURCE_BASE_FOLDERPATH.parent # Folder above the one containing this file
#dPrint( 'Quiet', debuggingThisModule, f"BOS_LIBRARY_BASE_FOLDERPATH = {BOS_LIBRARY_BASE_FOLDERPATH}" )
BOS_TESTS_FOLDERPATH = BOS_LIBRARY_BASE_FOLDERPATH.joinpath( 'Tests/' )
BOS_TEST_DATA_FOLDERPATH = BOS_TESTS_FOLDERPATH.joinpath( 'DataFilesForTests/' )

# Resources like original language lexicons should be based from this folder
BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH = BOS_LIBRARY_BASE_FOLDERPATH.parent # Two folders above the one containing this file


##########################################################################################################
#

LEVEL_NAME_DICT = { 'Quiet':1, 'Q':1,
                    'Normal':2, 'N':2,
                    'Informative':3, 'Info':3, 'I':3,
                    'Verbose':4, 'V':4,
                    'Never': 5, # Will only ever print if increaseLevel is set
                    }
def vPrint( requestedLevel:Union[int,str], increaseLevel:Union[bool,int], *args, **kwargs ) -> None:
    """
    verbose print -- intended for user notifications
                    (unlike the following two functions intended for programmers).

    Only print the given string, if the verbosity level is correct.
    """
    if isinstance( requestedLevel, str ):
        try: requestedLevel = LEVEL_NAME_DICT[requestedLevel]
        except KeyError: requestedLevel = 4 # default to verbose
    if debugFlag or strictCheckingFlag or debuggingThisModule: assert isinstance( requestedLevel, int )
    if increaseLevel is True: # (could also be an int)
        increaseLevel = 1 # Should always be an int now
    if debugFlag or strictCheckingFlag or debuggingThisModule: assert isinstance( increaseLevel, int )
    # Make one or more levels more verbose if increaseLevel is set
    if increaseLevel: requestedLevel -= increaseLevel # Doesn't matter if it goes negative
    if verbosityLevel >= requestedLevel:
        print( *args, **kwargs )
# end of BibleOrgSysGlobals.vPrint function

def dPrint( requestedLevel:Union[int,str], increaseLevel:Union[bool,int], *args, **kwargs ) -> None:
    """
    debug print -- intended for debug display of internal variables.

    Only print the given string, if the verbosity level is correct.

    Automatically prints more if the global debug flag is set.
    """
    if increaseLevel is True: # (could also be an int)
        increaseLevel = 1 # Should always be an int now
    if debugFlag or strictCheckingFlag or debuggingThisModule: assert isinstance( increaseLevel, int )
    if debugFlag: increaseLevel += 1
    vPrint( requestedLevel, increaseLevel, *args, **kwargs )
# end of BibleOrgSysGlobals.dPrint function

def fnPrint( increaseLevel:Union[bool,int], *args, **kwargs ) -> None:
    """
    function print -- intended only for function introduction notifications
                        for debugging of programme flow.

    Only print the given string, if the verbosity level is correct.
    """
    if increaseLevel is True: # (could also be an int)
        increaseLevel = 1 # Should always be an int now
    if debugFlag or strictCheckingFlag or debuggingThisModule: assert isinstance( increaseLevel, int )
    if debugFlag: increaseLevel += 1
    # dPrint( 'Info', debuggingThisModule, "args1", len(args), repr(args) )
    if not kwargs and args \
    and isinstance( args[-1], str ) and not args[-1].endswith( '…' ):
        args = ( f'{args[0]}…', ) if len(args)==1 else ( args[:-1], f'{args[-1]}…', ) # Append an ellipsis
    # dPrint( 'Info', debuggingThisModule, "args2", len(args), repr(args) )
    # dPrint( 'Quiet', increaseLevel, *args, **kwargs ) # Only for debugging programme flow
    vPrint( 'Verbose', increaseLevel, *args, **kwargs )
# end of BibleOrgSysGlobals.fnPrint function


##########################################################################################################
#

def findHomeFolderpath() -> Optional[Path]:
    """
    Attempt to find the path to the user's home folder and return it.
    """
    fnPrint( debuggingThisModule, "BibleOrgSysGlobals.findHomeFolderpath()" )
    possibleHomeFolders = ( os.path.expanduser('~'), os.getcwd(), os.curdir, os.pardir )
    dPrint( 'Info', debuggingThisModule, f"Possible home folders = {possibleHomeFolders}" )
    for folder in possibleHomeFolders:
        thisPath = Path( folder )
        if thisPath.is_dir and os.access( folder, os.W_OK ):
            return thisPath
# end of BibleOrgSysGlobals.findHomeFolderpath


##########################################################################################################
#
# These writeable folder paths might need to be adjusted by user programs!

APP_NAME = 'BibleOrgSys'
SETTINGS_VERSION = '1.00'
BOS_HOME_FOLDERPATH = findHomeFolderpath().joinpath( f'{APP_NAME}Data/' )
if not BOS_HOME_FOLDERPATH.exists():
    os.mkdir( BOS_HOME_FOLDERPATH )

BOS_SETTINGS_FOLDERPATH = BOS_HOME_FOLDERPATH.joinpath( 'BOSSettings/' )
if not BOS_SETTINGS_FOLDERPATH.exists():
    os.mkdir( BOS_SETTINGS_FOLDERPATH )
BOS_SETTINGS_FILEPATH = BOS_SETTINGS_FOLDERPATH.joinpath( 'BibleOrgSys.ini' )
settingsData = configparser.ConfigParser()
settingsData.optionxform = lambda option: option # Force true case matches for options (default is all lower case)
settingsData['Default'] = { 'OutputBaseFolder':f'{BOS_HOME_FOLDERPATH}/' }
# dPrint( 'Quiet', debuggingThisModule, "settingsData Default OutputFolder", settingsData['Default']['OutputFolder'] )
if BOS_SETTINGS_FILEPATH.is_file():
    settingsData.read( BOS_SETTINGS_FILEPATH )
else: # we don't seem to have a pre-existing settings file -- save our default one
    vPrint( 'Quiet', debuggingThisModule, f"Writing default {APP_NAME} settings file v{SETTINGS_VERSION} to {BOS_SETTINGS_FILEPATH}")
    with open( BOS_SETTINGS_FILEPATH, 'wt', encoding='utf-8' ) as settingsFile: # It may or may not have previously existed
        # Put a (comment) heading in the file first
        settingsFile.write( '# ' + _("{} settings file v{}").format( APP_NAME, SETTINGS_VERSION ) + '\n' )
        settingsFile.write( '# ' + _("Originally saved {} as {}") \
            .format( datetime.now().strftime('%Y-%m-%d %H:%M:%S'), BOS_SETTINGS_FILEPATH ) + '\n\n' )

        settingsData.write( settingsFile )
if debugFlag and debuggingThisModule:
    for section in settingsData:
        dPrint( 'Quiet', debuggingThisModule, f"  Settings.load: s.d main section = {section}" )

# BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH = BOS_LIBRARY_BASE_FOLDERPATH
BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH = Path( settingsData['Default']['OutputBaseFolder'] )
# dPrint( 'Quiet', debuggingThisModule, f"BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH = {BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH}")

DEFAULT_WRITEABLE_LOG_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSLogs/' )
DEFAULT_WRITEABLE_CACHE_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSObjectCache/' )
DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSOutputFiles/' )
DEFAULT_WRITEABLE_DATAFILES_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSDataFiles/' )
DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSDerivedDataFiles/' )
DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH = BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSDownloadedResources/' )


##########################################################################################################


def findUsername() -> str:
    """
    Attempt to find the current user name and return it.
    """
    fnPrint( debuggingThisModule, "BibleOrgSysGlobals.findUsername()" )
    if pwd:
        return pwd.getpwuid(os.geteuid()).pw_name
    else:
        return getpass.getuser()
# end of BibleOrgSysGlobals.findUsername


##########################################################################################################
#
# Handling logging
#

#def function_with_a_bug(params):
#    """Just sitting here to remind me how to do it"""
#    old_log_level = logging.getLogger().getEffectiveLevel()
#    logging.getLogger().setLevel( logging.DEBUG )
#    logging.debug( "Entering function_with_a_bug" )
#    logging.debug( "Params were {}", params )
#    for item in params:
#        logging.debug( "Processing {}", item )
#        result = do_something_with( item )
#        logging.debug( "Result was: {}", result )
#    logging.getLogger().setLevel( old_log_level )
## end of function_with_a_bug


loggingDateFormat = "%Y-%m-%d %H:%M"
loggingConsoleFormat = '%(levelname)s: %(message)s'
loggingShortFormat = '%(levelname)8s: %(message)s'
loggingLongFormat = '%(asctime)s %(levelname)8s: %(message)s'

def setupLoggingToFile( SHORT_PROGRAM_NAMEParameter:str, programVersionParameter:str, folderpath:Optional[Path]=None ) -> None:
    """
    Sets up the main logfile for the program and returns the full pathname.

    Gets called from our demo() function when program starts up.
    """
    fnPrint( debuggingThisModule, f"BibleOrgSysGlobals.setupLoggingToFile( {SHORT_PROGRAM_NAMEParameter!r}, {programVersionParameter!r}, {folderpath!r} )" )

    filename = SHORT_PROGRAM_NAMEParameter.replace('/','-').replace(':','_').replace('\\','_') + '_log.txt'
    if folderpath is None: folderpath = DEFAULT_WRITEABLE_LOG_FOLDERPATH
    filepath = Path( folderpath, filename )

    # Create the folderpath if necessary
    if not os.access( folderpath, os.W_OK ):
        os.makedirs( folderpath ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    backupAnyExistingFile( filepath, numBackups=4 )
    #if os.access( filepath, os.F_OK ):
        #if debuggingThisModule or __name__ == '__main__':
            #dPrint( 'Quiet', debuggingThisModule, "setupLoggingToFile: {!r} already exists -- renaming it first!".format( filepath ) )
        #if os.access( filepath+'.bak', os.F_OK ):
            #os.remove( filepath+'.bak' )
        #os.rename( filepath, filepath+'.bak' )

    # Now setup our new log file -- DOESN'T SEEM TO WORK IN WINDOWS!!!
    # In Windows, doesn't seem to create the log file, even if given a filename rather than a filepath
    setLevel = logging.DEBUG if debugFlag else logging.INFO
    if debuggingThisModule: # otherwise the list of strings isn't declared above
        dPrint( 'Verbose', debuggingThisModule, "BibleOrgSysGlobals.setBasicConfig to( {!r}, {}={}, {!r}, {!r} )".format( filepath, setLevel, LOGGING_NAME_DICT[setLevel], loggingLongFormat, loggingDateFormat ) )
    # NOTE: This call to basicConfig MUST occur BEFORE any modules make any logging calls
    #   i.e., be careful of putting executable calls at module level that might log at module load time
    logging.basicConfig( filename=filepath, level=setLevel, format=loggingLongFormat, datefmt=loggingDateFormat )

    #return filepath
# end of BibleOrgSysGlobals.setupLoggingToFile


def addConsoleLogging( consoleLoggingLevel:Optional[int]=None ) -> None:
    """
    Adds a handler to also send ERROR and higher to console (depending on verbosity)
    """
    # fnPrint( debuggingThisModule, f"BibleOrgSysGlobals.addConsoleLogging( {consoleLoggingLevel}={LOGGING_NAME_DICT[consoleLoggingLevel]} )" )

    stderrHandler = logging.StreamHandler() # StreamHandler with no parameters defaults to sys.stderr
    stderrHandler.setFormatter( logging.Formatter( loggingConsoleFormat, None ) )
    if consoleLoggingLevel is None: # work it out for ourselves
        if verbosityLevel == 0: # Silent
            consoleLoggingLevel = logging.CRITICAL
        elif verbosityLevel == 4: # Verbose
            consoleLoggingLevel = logging.WARNING
        else: # Quiet or normal
            consoleLoggingLevel = logging.ERROR
    if debuggingThisModule: # otherwise the list of strings isn't declared above
        vPrint( 'Verbose', debuggingThisModule, "  addConsoleLogging setting it to {}={}".format( consoleLoggingLevel, LOGGING_NAME_DICT[consoleLoggingLevel] ) )
    stderrHandler.setLevel( consoleLoggingLevel )
    root = logging.getLogger()  # No param means get the root logger
    root.addHandler(stderrHandler)
# end of BibleOrgSysGlobals.addConsoleLogging


def addLogfile( projectName:str, folderName:Optional[Path]=None ) -> Tuple[Path,logging.FileHandler]:
    """
    Adds an extra project specific log file to the logger.
    """
    fnPrint( debuggingThisModule, "BibleOrgSysGlobals.addLogfile( {}, {} )".format( projectName, folderName ) )

    filename = projectName + '_log.txt'
    if folderName is None: folderName = DEFAULT_WRITEABLE_LOG_FOLDERPATH
    filepath = Path( folderName, filename )

    # Create the folderName if necessary
    if not os.access( folderName, os.W_OK ):
        os.makedirs( folderName ) # Works for an absolute or a relative pathname

    # Rename the existing file to a backup copy if it already exists
    backupAnyExistingFile( filepath, numBackups=4 )
    #if os.access( filepath, os.F_OK ):
        #if __name__ == '__main__':
            #dPrint( 'Quiet', debuggingThisModule, filepath, 'already exists -- renaming it first!' )
        #if os.access( filepath+'.bak', os.F_OK ):
            #os.remove( filepath+'.bak' )
        #os.rename( filepath, filepath+'.bak' )

    projectHandler = logging.FileHandler( filepath )
    projectHandler.setFormatter( logging.Formatter( loggingShortFormat, loggingDateFormat ) )
    projectHandler.setLevel( logging.INFO )
    root = logging.getLogger()
    root.addHandler( projectHandler )
    return filepath, projectHandler
# end of BibleOrgSysGlobals.addLogfile


def removeLogfile( projectHandler ) -> None:
    """
    Removes the project specific logger.
    """
    fnPrint( debuggingThisModule, "BibleOrgSysGlobals.removeLogfile( {} )".format( projectHandler ) )

    root = logging.getLogger()  # No param means get the root logger
    root.removeHandler( projectHandler )
# end of BibleOrgSysGlobals.removeLogfile


##########################################################################################################
#

def getLatestPythonModificationDate() -> str:
    """
    Goes through the .py files in the current folder
        and tries to find the latest modification date.
    """
    fnPrint( debuggingThisModule, "getLatestPythonModificationDate()" )

    #collectedFilepaths = []
    latestYYYY, latestMM, latestDD = 1999, 0, 0
    startFolderpath = Path( __file__ ).parent
    for folderpath in (startFolderpath,
                       startFolderpath.joinpath( 'Internals/'),
                       startFolderpath.joinpath( 'InputOutput/'),
                       startFolderpath.joinpath( 'Reference/'),
                       startFolderpath.joinpath( 'Formats/'),
                       startFolderpath.joinpath( 'OriginalLanguages/'),
                       startFolderpath.joinpath( 'Online/'),
                       startFolderpath.joinpath( 'Misc/'),
                       ):
        #dPrint( 'Quiet', debuggingThisModule, f"folderpath = '{folderpath}'" )
        searchString = 'LAST_MODIFIED_DATE = '
        for filename in os.listdir( folderpath ):
            # dPrint( 'Quiet', debuggingThisModule, f"filename = '{filename}'" )
            filepath = folderpath.joinpath( filename )
            #dPrint( 'Quiet', debuggingThisModule, f"filepath = '{filepath}'" )
            if filepath.is_file() and filepath.name.endswith( '.py' ):
                #dPrint( 'Quiet', debuggingThisModule, f"  Checking '{filepath}' …" )
                with open( filepath, 'rt', encoding='utf-8' ) as pythonFile:
                    for line in pythonFile:
                        if line.startswith( searchString ):
                            # dPrint( 'Quiet', debuggingThisModule, filepath, line )
                            #dPrint( 'Quiet', debuggingThisModule, filepath )
                            lineBit = line[len(searchString):]
                            if '#' in lineBit: lineBit = lineBit.split('#',1)[0]
                            if lineBit[-1]=='\n': lineBit = lineBit[:-1] # Removing trailing newline character
                            lineBit = lineBit.replace("'",'').replace('"','').strip()
                            #dPrint( 'Quiet', debuggingThisModule, '  {!r}'.format( lineBit ) )
                            lineBits = lineBit.split( '-' )
                            assert len(lineBits) == 3 # YYYY MM DD
                            YYYY, MM, DD = int(lineBits[0]), int(lineBits[1]), int(lineBits[2])
                            #dPrint( 'Quiet', debuggingThisModule, '  ', YYYY, MM, DD )
                            if YYYY > latestYYYY:
                                latestYYYY, latestMM, latestDD = YYYY, MM, DD
                                #collectedFilepaths.append( (filepath,lineBit) )
                            elif YYYY==latestYYYY and MM>latestMM:
                                latestMM, latestDD = MM, DD
                                #collectedFilepaths.append( (filepath,lineBit) )
                            elif YYYY==latestYYYY and MM==latestMM and DD>latestDD:
                                latestDD = DD
                                #collectedFilepaths.append( (filepath,lineBit) )
                            break
    #dPrint( 'Quiet', debuggingThisModule, latestYYYY, latestMM, latestDD ); halt
    return f'{latestYYYY}-{latestMM:02}-{latestDD:02}'
# end of BibleOrgSysGlobals.getLatestPythonModificationDate


##########################################################################################################
#

def printUnicodeInfo( text:str, description:str ) -> None:
    """
    """
    fnPrint( debuggingThisModule, "{}:".format( description ) )
    for j,char in enumerate(text):
        dPrint( 'Quiet', debuggingThisModule, "{:2} {:04x} {} {!r}   (cat={} bid={} comb={} mirr={})" \
            .format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )

##########################################################################################################
#
# Make a string safe if it's going to be used as a filename
#
#       We don't want a malicious user to be able to gain access to the filesystem
#               by putting a filepath into a filename string.

def makeSafeFilename( someName:str ) -> str:
    """
    Replaces potentially unsafe characters in a name to make it suitable for a filename.

    NOTE: This leaves spaces as they were.
    """
    return someName.replace('/','-') \
        .replace('\\','_BACKSLASH_').replace(':','_COLON_').replace(';','_SEMICOLON_') \
        .replace('#','_HASH_').replace('?','_QUESTIONMARK_').replace('*','_ASTERISK_') \
        .replace('<','_LT_').replace('>','_GT_')
# end of BibleOrgSysGlobals.makeSafeFilename


##########################################################################################################
#
# Make a string safe if it could be used in an XML document
#

def makeSafeXML( someString:str ) -> str:
    """
    Replaces special characters in a string to make it for XML.
    """
    return someString.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
# end of BibleOrgSysGlobals.makeSafeXML


##########################################################################################################
#
# Make a string safe if it could be used in an HTML or other document
#
#       We don't want a malicious user to be able to gain access to the system
#               by putting system commands into a string that's then used in a webpage or something.

def makeSafeString( someString:str ) -> str:
    """
    Replaces potentially unsafe characters in a string to make it safe for display.
    """
    #return someString.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return someString.replace('<','_LT_').replace('>','_GT_')
# end of BibleOrgSysGlobals.makeSafeString


##########################################################################################################
#
# Remove accents

ACCENT_DICT = { 'À':'A','Á':'A','Â':'A','Ã':'A','Ä':'A','Å':'A','Ă':'A','Ą':'A', 'Æ':'AE',
              'Ç':'C','Ć':'C','Ĉ':'C','Ċ':'C','Č':'C',
              'Ð':'D','Ď':'D','Đ':'D',
              'È':'E','É':'E','Ê':'E','Ë':'E','Ē':'E','Ĕ':'E','Ė':'E','Ę':'E','Ě':'E',
              'Ĝ':'G','Ğ':'G','Ġ':'G','Ģ':'G',
              'Ì':'I','Í':'I','Î':'I','Ï':'I',
              'Ñ':'N',
              'Ò':'O','Ó':'O','Ô':'O','Õ':'O','Ö':'O','Ø':'O',
              'Ù':'U','Ú':'U','Û':'U','Ü':'U',
              'Ý':'Y',
              'à':'a','á':'a','â':'a','ã':'a','ä':'a','å':'a','ā':'a','ă':'a','ą':'a', 'æ':'ae',
              'ç':'c','ć':'c','ĉ':'c','ċ':'c','č':'c',
              'ð':'d','ď':'d','đ':'d',
              'è':'e','é':'e','ê':'e','ë':'e','ē':'e','ĕ':'e','ė':'e','ę':'e','ě':'e',
              'ģ':'g','ğ':'g','ġ':'g',
              'ì':'i','í':'i','î':'i','ï':'i',
              'ñ':'n',
              'ò':'o','ó':'o','ô':'o','õ':'o','ö':'o','ø':'o',
              'ù':'u','ú':'u','û':'u','ü':'u',
              'ý':'y','ÿ':'y',
              }

def removeAccents( someString:str ) -> str:
    """
    Remove accents from the string and return it (used for fuzzy matching)

    Not that this doesn't remove Hebrew vowel pointing.
    """
    # Try 1
    #return unicodedata.normalize('NFKD', someString).encode('ASCII', 'ignore')

    # Try 2
    #resultString = ''
    #for someChar in someString:
        #desc = unicodedata.name( someChar )
        #cutoff = desc.find( ' WITH ' )
        ##if cutoff != -1:
            ##desc = desc[:cutoff]
        #resultString += someChar if cutoff==-1 else unicodedata.lookup( desc[:cutoff] )
    #return resultString

    # The next two use our ACCENT_DICT above
    # Try 3
    #resultString = ''
    #for someChar in someString:
        #resultString += ACCENT_DICT[someChar] if someChar in ACCENT_DICT else someChar
    #return resultString

    # Try 4
    return ''.join( ACCENT_DICT[someChar] if someChar in ACCENT_DICT else someChar for someChar in someString )
# end of BibleOrgSysGlobals.makeSafeString


##########################################################################################################
#
# Make a backup copy of a file that's about to be written by renaming it
#   Note that this effectively "deletes" the file.

def backupAnyExistingFile( filenameOrFilepath:Union[Path,str], numBackups:int=1, extension:str='bak' ) -> None:
    """
    Make a backup copy/copies of a file if it exists.
    """
    fnPrint( debuggingThisModule, "backupAnyExistingFile( {!r}, {}, {!r} )".format( filenameOrFilepath, numBackups, extension ) )
    if debugFlag and debuggingThisModule:
        assert not str(filenameOrFilepath).lower().endswith( '.bak' )

    if extension[0] != '.': extension = '.' + extension
    for n in range( numBackups, 0, -1 ): # e.g., 4,3,2,1
        source = str(filenameOrFilepath) + ('' if n==1 else (extension + ('' if n<3 else str(n-1))))
        destination = str(filenameOrFilepath) + extension + ('' if n==1 else str(n))
        if os.access( source, os.F_OK ):
            if n==1 and debugFlag:
                logging.info( "backupAnyExistingFile: {!r} already exists -- renaming it first!".format( source ) )
            if os.access( destination, os.F_OK ): os.remove( destination )
            os.rename( source, destination )
# end of BibleOrgSysGlobals.backupAnyExistingFile


##########################################################################################################
#
# Peek at the first line(s) of a file
#
# If one line is requested, returns the line (string)
# Otherwise, returns a list of lines

def peekIntoFile( filenameOrFilepath, folderName=None, numLines:int=1, encoding:str=None ):
    """
    Reads and returns the first line of a text file as a string
        unless more than one line is requested
        in which case a list of strings is returned (including empty strings for empty lines).
    """
    if debugFlag: assert 1 <= numLines < 5
    if encoding is None: encodingList = ['utf-8', 'iso-8859-1', 'iso-8859-15',]
    else: encodingList = [encoding]
    filepath = Path( folderName, filenameOrFilepath ) if folderName else filenameOrFilepath
    for tryEncoding in encodingList:
        lines = []
        try:
            with open( filepath, 'rt', encoding=tryEncoding ) as possibleBibleFile: # Automatically closes the file when done
                lineNumber = 0
                for line in possibleBibleFile:
                    lineNumber += 1
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    #dPrint( 'Never', debuggingThisModule, filenameOrFilepath, lineNumber, line )
                    if numLines==1: return line # Always returns the first line (string)
                    lines.append( line )
                    if lineNumber >= numLines: return lines # Return a list of lines
        except UnicodeDecodeError: # Could be binary or a different encoding
            #if not filepath.lower().endswith( 'usfm-color.sty' ): # Seems this file isn't UTF-8, but we don't need it here anyway so ignore it
            thisLogger = logging.warning if debuggingThisModule or debugFlag else logging.info
            thisLogger( f"{'BibleOrgSysGlobals.' if debugFlag else ''}peekIntoFile: Seems we couldn't decode Unicode in {filepath}" )
# end of BibleOrgSysGlobals.peekIntoFile


##########################################################################################################
#
# For debugging, etc.

def totalSize( obj, handlers={} ):
    """
    Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    from itertools import chain

    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = sys.getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(obj):
        if id(obj) in seen:       # do not double count the same object
            return 0
        seen.add(id(obj))
        s = sys.getsizeof(obj, default_size)

        dPrint( 'Verbose', debuggingThisModule, s, type(obj), repr(obj) )

        for typ, handler in all_handlers.items():
            if isinstance(obj, typ):
                s += sum(map(sizeof, handler(obj)))
                break
        return s

    return sizeof(obj)
# end of BibleOrgSysGlobals.totalSize


##########################################################################################################
#
# File comparisons
#

def fileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount:int=10 ):
    """
    Compare the two utf-8 files.
    """
    filepath1 = Path( folder1, filename1 ) if folder1 else filename1
    filepath2 = Path( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2:
            vPrint( 'Quiet', debuggingThisModule, "Comparing {!r} files in folders {!r} and {!r}…".format( filename1, folder1, folder2 ) )
        else: vPrint( 'Quiet', debuggingThisModule, "Comparing files {!r} and {!r}…".format( filename1, filename2 ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( f"fileCompare: File1 {filepath1!r} is unreadable" )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( f"fileCompare: File2 {filepath2!r} is unreadable" )
        return None

    # Read the files into lists
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt', encoding='utf-8' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    vPrint( 'Quiet', debuggingThisModule, "      fileCompare: Detected Unicode Byte Order Marker (BOM) in file1" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt', encoding='utf-8' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    vPrint( 'Quiet', debuggingThisModule, "      fileCompare: Detected Unicode Byte Order Marker (BOM) in file2" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines2.append( line )

    # Compare the length of the lists/files
    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: vPrint( 'Quiet', debuggingThisModule, "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    # Now compare the actual lines
    diffCount = 0
    for k in range( min( len1, len2 ) ):
        if lines1[k] != lines2[k]:
            if printFlag:
                vPrint( 'Quiet', debuggingThisModule, "  {}a:{!r} ({} chars)\n  {}b:{!r} ({} chars)" \
                    .format( k+1, lines1[k], len(lines1[k]), k+1, lines2[k], len(lines2[k]) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "fileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of BibleOrgSysGlobals.fileCompare


def fileCompareUSFM( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount:int=10 ):
    """
    Compare the two utf-8 USFM files,
        ignoring little things like \\s vs \\s1.
    """
    filepath1 = Path( folder1, filename1 ) if folder1 else filename1
    filepath2 = Path( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2:
            vPrint( 'Quiet', debuggingThisModule, "Comparing USFM {!r} files in folders {!r} and {!r}…".format( filename1, folder1, folder2 ) )
        else: vPrint( 'Quiet', debuggingThisModule, "Comparing USFM files {!r} and {!r}…".format( filename1, filename2 ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( f"fileCompare: File1 {filepath1!r} is unreadable" )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( f"fileCompare: File2 {filepath2!r} is unreadable" )
        return None

    # Read the files into lists
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt', encoding='utf-8' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    vPrint( 'Quiet', debuggingThisModule, "      fileCompare: Detected Unicode Byte Order Marker (BOM) in file1" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt', encoding='utf-8' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and verbosityLevel > 2:
                    vPrint( 'Quiet', debuggingThisModule, "      fileCompare: Detected Unicode Byte Order Marker (BOM) in file2" )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            lines2.append( line )

    # Compare the length of the lists/files
    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: vPrint( 'Quiet', debuggingThisModule, "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    # Now compare the actual lines
    diffCount = 0
    C, V = '-1', '-1' # So first/id line starts at -1:0
    for k in range( min( len1, len2 ) ):
        originalLine1, originalLine2 = lines1[k], lines2[k]
        adjustedLine1, adjustedLine2 = originalLine1, originalLine2
        while adjustedLine1 and adjustedLine1[-1]==' ': adjustedLine1 = adjustedLine1[:-1] # Remove the final space
        while adjustedLine2 and adjustedLine2[-1]==' ': adjustedLine2 = adjustedLine2[:-1] # Remove the final space
        if adjustedLine1.startswith( '\\c '): C = adjustedLine1[3:]
        if adjustedLine1.startswith( '\\v '): V = adjustedLine1[3:].split()[0]
        for unnumbered,numbered in ( ('mt','mt1'),('mte','mte1'), ('imt','imt1'),('imte','imte1'),
                                    ('is','is1'), ('iq','iq1'), ('io','io1'), ('ili','ili1'),
                                    ('ms','ms1'), ('s','s1'), ('li','li1'), ('q','q1'), ('pi','pi1'), ('ph','ph1'), ):
            if adjustedLine1 == '\\'+unnumbered: adjustedLine1 = '\\'+numbered
            else: adjustedLine1 = adjustedLine1.replace( '\\'+unnumbered+' ', '\\'+numbered+' ' )
            if adjustedLine2 == '\\'+unnumbered: adjustedLine2 = '\\'+numbered
            else: adjustedLine2 = adjustedLine2.replace( '\\'+unnumbered+' ', '\\'+numbered+' ' )
        if adjustedLine1 != adjustedLine2:
            if printFlag:
                vPrint( 'Quiet', debuggingThisModule, "  {}:{} {}a:{!r} ({} chars)\n  {}:{} {}b:{!r} ({} chars)" \
                    .format( C, V, k+1, originalLine1, len(originalLine1), C, V, k+1, originalLine2, len(originalLine1) ) )
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "fileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of BibleOrgSysGlobals.fileCompareUSFM


def fileCompareXML( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount:int=10, ignoreWhitespace=True ):
    """
    Compare the two files.
    """
    filepath1 = Path( folder1, filename1 ) if folder1 else filename1
    filepath2 = Path( folder2, filename2 ) if folder2 else filename2
    if verbosityLevel > 1:
        if filename1==filename2:
            vPrint( 'Quiet', debuggingThisModule, "Comparing XML {!r} files in folders {!r} and {!r}…".format( filename1, folder1, folder2 ) )
        else: vPrint( 'Quiet', debuggingThisModule, "Comparing XML files {!r} and {!r}…".format( filename1, filename2 ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( f"fileCompareXML: File1 {filepath1!r} is unreadable" )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( f"fileCompareXML: File2 {filepath2!r} is unreadable" )
        return None

    # Load the files
    from xml.etree.ElementTree import ElementTree
    tree1 = ElementTree().parse( filepath1 )
    tree2 = ElementTree().parse( filepath2 )

    def compareElements( element1, element2 ):
        """
        """
        nonlocal diffCount, location
        if element1.tag != element2.tag:
            if printFlag:
                vPrint( 'Quiet', debuggingThisModule, "Element tags differ ({!r} and {!r})".format( element1.tag, element2.tag ) )
                vPrint( 'Info', debuggingThisModule, "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
            location.append( "{}/{}".format( element1.tag, element2.tag ) )
        else: location.append( element1.tag )
        attribs1, attribs2 = element1.items(), element2.items()
        if len(attribs1) != len(attribs2):
            if printFlag:
                vPrint( 'Quiet', debuggingThisModule, "Number of attributes differ ({} and {})".format( len(attribs1), len(attribs2) ) )
                vPrint( 'Info', debuggingThisModule, "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
        for avPair in attribs1:
            if avPair not in attribs2:
                if printFlag:
                    vPrint( 'Quiet', debuggingThisModule, "File1 has {} but not in file2 {}".format( avPair, attribs2 ) )
                    vPrint( 'Info', debuggingThisModule, "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        for avPair in attribs2:
            if avPair not in attribs1:
                if printFlag:
                    vPrint( 'Quiet', debuggingThisModule, "File2 has {} but not in file1 {}".format( avPair, attribs1 ) )
                    vPrint( 'Info', debuggingThisModule, "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.text != element2.text:
            if ignoreWhitespace:
                if element1.text is None and not element2.text.strip(): pass
                elif element2.text is None and not element1.text.strip(): pass
                elif element1.text and element2.text and element1.text.strip()==element2.text.strip(): pass
                else:
                    if printFlag:
                        vPrint( 'Quiet', debuggingThisModule, "Element text differs:\n {!r}\n {!r}".format( element1.text, element2.text ) )
                        vPrint( 'Info', debuggingThisModule, "  at", location )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag:
                    vPrint( 'Quiet', debuggingThisModule, "Element text differs:\n {!r}\n {!r}".format( element1.text, element2.text ) )
                    vPrint( 'Info', debuggingThisModule, "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if element1.tail != element2.tail:
            if ignoreWhitespace:
                if element1.tail is None and not element2.tail.strip(): pass
                elif element2.tail is None and not element1.tail.strip(): pass
                elif element1.tail and element2.tail and element1.tail.strip()==element2.tail.strip(): pass
                else:
                    if printFlag:
                        vPrint( 'Quiet', debuggingThisModule, "Element tail differs:\n {!r}\n {!r}".format( element1.tail, element2.tail ) )
                        vPrint( 'Info', debuggingThisModule, "  at", location )
                    diffCount += 1
                    if diffCount > exitCount: return
            else:
                if printFlag:
                    vPrint( 'Quiet', debuggingThisModule, "Element tail differs:\n {!r}\n {!r}".format( element1.tail, element2.tail ) )
                    vPrint( 'Info', debuggingThisModule, "  at", location )
                diffCount += 1
                if diffCount > exitCount: return
        if len(element1) != len(element2):
            if printFlag:
                vPrint( 'Quiet', debuggingThisModule, "Number of subelements differ ({} and {})".format( len(element1), len(element2) ) )
                vPrint( 'Info', debuggingThisModule, "  at", location )
            diffCount += 1
            if diffCount > exitCount: return
        # Compare the subelements
        for j in range( min( len(element1), len(element2) ) ):
            compareElements( element1[j], element2[j] ) # Recursive call
            if diffCount > exitCount: return

    # Compare the files
    diffCount = 0
    location:List[str] = []
    compareElements( tree1, tree2 )
    if diffCount:
        vPrint( 'Normal', debuggingThisModule, "{} differences discovered.".format( diffCount if diffCount<=exitCount else 'Many' ) )
    return diffCount==0
# end of BibleOrgSysGlobals.fileCompareXML


##########################################################################################################
#
# Validating XML fields (from element tree)
#

def elementStr( element, level:int=0 ):
    """
    Return a string representation of an element (from element tree).

    This is suitable for debugging
    """
    resultStr = '{}Element {!r}: '.format( 'Sub'*level, element.tag )

    # Do attributes first
    printed = False
    for attrib,value in element.items():
        if printed: resultStr += ','
        else: resultStr += 'Attribs: '; printed = True
        resultStr += '{}={!r}'.format( attrib, value )

    if element.text is not None:
        if resultStr[-1] != ' ': resultStr += ' '
        resultStr += 'Text={!r}'.format( element.text )

    # Now do subelements
    printed = False
    for subelement in element:
        if printed: resultStr += ','
        else:
            if resultStr[-1] != ' ': resultStr += ' '
            resultStr += 'Children: '; printed = True
        resultStr += elementStr( subelement, level+1 ) # recursive call

    if element.tail is not None:
        if resultStr[-1] != ' ': resultStr += ' '
        resultStr += 'Tail={!r}'.format( element.tail )
    return resultStr
# end of BibleOrgSysGlobals.elementStr


def checkXMLNoAttributes( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give a warning if the element contains any attributes.
    """
    for attrib,value in element.items():
        warningString = "{}Unexpected {!r} XML attribute ({}) in {}" \
                        .format( (idString+' ') if idString else '', attrib, value, locationString )
        logging.warning( warningString )
        if loadErrorsDict is not None: loadErrorsDict.append( warningString )
        if strictCheckingFlag or debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoAttributes


def checkXMLNoText( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give an error if the element text contains anything other than whitespace.
    """
    if element.text and element.text.strip():
        errorString = "{}Unexpected {!r} XML element text in {}" \
                        .format( (idString+' ') if idString else '', element.text, locationString )
        logging.error( errorString )
        if loadErrorsDict is not None: loadErrorsDict.append( errorString )
        if strictCheckingFlag or debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoText

def checkXMLNoTail( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give a warning if the element tail contains anything other than whitespace.
    """
    if element.tail and element.tail.strip():
        warningString = "{}Unexpected {!r} XML element tail in {}" \
                        .format( (idString+' ') if idString else '', element.tail, locationString )
        logging.warning( warningString )
        if loadErrorsDict is not None: loadErrorsDict.append( warningString )
        if strictCheckingFlag or debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoTail


def checkXMLNoSubelements( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Give an error if the element contains any sub-elements.
    """
    for subelement in element:
        errorString = "{}Unexpected {!r} XML sub-element ({}) in {}" \
                        .format( (idString+' ') if idString else '', subelement.tag, subelement.text, locationString )
        logger = logging.critical if subelement.text else logging.error
        logger( errorString )
        if loadErrorsDict is not None: loadErrorsDict.append( errorString )
        if strictCheckingFlag or debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoSubelements

def checkXMLNoSubelementsWithText( element, locationString, idString=None, loadErrorsDict=None ):
    """
    Checks that the element doesn't have text AND subelements
    """
    if ( element.text and element.text.strip() ) \
    or ( element.tail and element.tail.strip() ):
        for subelement in element:
            warningString = "{}Unexpected {!r} XML sub-element ({}) in {} with text/tail {}/{}" \
                            .format( (idString+' ') if idString else '', subelement.tag, subelement.text, locationString,
                                element.text.strip() if element.text else element.text,
                                element.tail.strip() if element.tail else element.tail )
            logging.warning( warningString )
            if loadErrorsDict is not None: loadErrorsDict.append( warningString )
            if strictCheckingFlag or debugFlag and haltOnXMLWarning: halt
# end of BibleOrgSysGlobals.checkXMLNoSubelementsWithText


def getFlattenedXML( element, locationString, idString=None, level=0 ):
    """
    Return the XML nested inside the element as a text string.

    The last two parameters are used for handling recursion.

    Strips the tail (which often contains excess nl characters).
    """
    result = ''
    # Get attributes
    attributes = ''
    for attribName,attribValue in element.items():
        attributes += '{}{}="{}"'.format( ' ' if attributes else '', attribName, attribValue )
    if level: # For lower levels (other than the called one) need to add the tags
        result += '<' + element.tag
        if attributes: result += ' ' + attributes
        result += '>'
    elif attributes:
        #dPrint( 'Quiet', debuggingThisModule, "We are losing attributes here:", attributes ); halt
        result += '<' + attributes + '>'
    if element.text: result += element.text
    for subelement in element:
        result += getFlattenedXML( subelement, subelement.tag + ' in ' + locationString, idString, level+1 ) # Recursive call
    if level:
        result += '</' + element.tag + '>'
    if element.tail and element.tail.strip(): result += ' ' + element.tail.strip()
    #else: dPrint( 'Quiet', debuggingThisModule, "getFlattenedXML: Result is {!r}".format( result ) )
    return result
# end of BibleOrgSysGlobals.getFlattenedXML


def isBlank( elementText ):
    """
    Given some text from an XML element text or tail field (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.

    If the text is None, returns None
    """
    # fnPrint( debuggingThisModule, "isBlank( {!r} )".format( elementText ) )
    if elementText is None: return True
    #dPrint( 'Quiet', debuggingThisModule, "isspace()", elementText.isspace() )
    return elementText.isspace()
# end of BibleOrgSysGlobals.isBlank



##########################################################################################################
#
# Fixing strings
#

def applyStringAdjustments( originalText, adjustmentList ):
    """
    Applies the list of adjustments to the text and returns the new text.

    The adjustmentList is a list object containing 3-tuples with:
        1/ index where field should be found (in originalText)
        2/ findString (null for a pure insert)
        3/ replaceString (often a different length)

    For example, given "The quick brown fox jumped over the lazy brown dog."
                        012345678901234567890123456789012345678901234567890
                                  1         2         3         4         5
        applying adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
            (note that all of the above indexes refer to the original string before any substitutions)
        gives "A very quick orange fox tripped over the fat dog."
    """
    text = originalText
    offset = 0
    for ix, findStr, replaceStr in sorted(adjustmentList): # sorted with lowest index first
        lenFS, lenRS = len(findStr), len(replaceStr)
        if debugFlag: assert text[ix+offset:ix+offset+lenFS] == findStr # Our find string must be there
        elif text[ix+offset:ix+offset+lenFS] != findStr:
            logging.error( "applyStringAdjustments programming error -- given bad data for {!r}: {}".format( originalText, adjustmentList ) )
        #dPrint( 'Quiet', debuggingThisModule, "before", repr(text) )
        text = text[:ix+offset] + replaceStr + text[ix+offset+lenFS:]
        #dPrint( 'Quiet', debuggingThisModule, " after", repr(text) )
        offset += lenRS - lenFS
    return text
# end of BibleOrgSysGlobals.applyStringAdjustments


def stripWordPunctuation( wordToken ):
    """
    Removes leading and trailing punctuation from a word.

    Returns the "clean" word.

    Note: Words like 'you(pl)' will be returned unchanged (because matching parenthesis is inside the word).
    """
    if debugFlag or strictCheckingFlag or debuggingThisModule:
        for badChar in ' \t\r\n': assert badChar not in wordToken

    # First remove matching punctuation
    for startChar,endChar in MATCHING_OPENING_CHARACTERS.items():
        #if wordToken and wordToken[0]==startChar and wordToken[-1]==endChar:
            #wordToken = wordToken[1:-1] # Remove front and back matching/opposite characters
        if wordToken.startswith(startChar) and wordToken.endswith(endChar):
            wordToken = wordToken[len(startChar):-len(endChar)] # Remove front and back matching/opposite characters
    # Now remove non-matching punctuation
    while wordToken and wordToken[0] in LEADING_WORD_PUNCT_CHARS:
        if wordToken[0] in MATCHING_CHARACTERS and MATCHING_CHARACTERS[wordToken[0]] in wordToken: break
        wordToken = wordToken[1:] # Remove leading punctuation
    while wordToken and wordToken[-1] in TRAILING_WORD_PUNCT_CHARS:
        if wordToken[-1] in MATCHING_CHARACTERS and MATCHING_CHARACTERS[wordToken[-1]] in wordToken: break
        wordToken = wordToken[:-1] # Remove trailing punctuation
    # Now remove any remaining matching punctuation
    for startChar,endChar in MATCHING_OPENING_CHARACTERS.items():
        if wordToken.startswith(startChar) and wordToken.endswith(endChar):
            wordToken = wordToken[len(startChar):-len(endChar)] # Remove front and back matching/opposite characters
    return wordToken
# end of BibleOrgSysGlobals.stripWordPunctuation


##########################################################################################################
#
# Reloading a saved Python object from the cache
#

def pickleObject( theObject, filename, folderName=None, disassembleObjectFlag=False ):
    """
    Writes the object to a .pickle file that can be easily loaded into a Python3 program.
        If folderName is None (or missing), defaults to the default cache folderName specified above.
        Creates the folderName(s) if necessary.

    disassembleObjectFlag is used to find segfaults by pickling the object piece by piece.

    Returns True if successful.
    """
    assert theObject is not None
    assert filename
    if folderName is None: folderName = DEFAULT_WRITEABLE_CACHE_FOLDERPATH
    filepath = filename # default
    if folderName:
        if not os.access( folderName, os.R_OK ): # Make the folderName hierarchy if necessary
            os.makedirs( folderName )
        filepath = Path( folderName, filename )
    vPrint( 'Info', debuggingThisModule, _("Saving object to {}…").format( filepath ) )

    if disassembleObjectFlag: # Pickles an object attribute by attribute (to help narrow down segfault)
        dPrint( 'Quiet', debuggingThisModule, '\nobject', disassembleObjectFlag, dir(theObject) )
        for name in dir( theObject ):
            a = theObject.__getattribute__( name )
            t = type( a )
            ts = str( t )
            f = 'pickle' + name
            dPrint( 'Quiet', debuggingThisModule, 'attrib', name, ts )
            if '__' not in name and 'method' not in ts:
                dPrint( 'Quiet', debuggingThisModule, '  go' )
                if name=='books':
                    dPrint( 'Quiet', debuggingThisModule, '  books' )
                    for bn in a:
                        dPrint( 'Quiet', debuggingThisModule, '     ', bn )
                        b = a[bn]
                        dPrint( 'Quiet', debuggingThisModule, b.BBB )
                        pickleObject( b, f, folderName )
                else:
                    pickleObject( a, f, folderName, disassembleObjectFlag=True )
            else: dPrint( 'Quiet', debuggingThisModule, '  skip' )

    with open( filepath, 'wb' ) as pickleOutputFile:
        try:
            pickle.dump( theObject, pickleOutputFile, pickle.HIGHEST_PROTOCOL )
        except pickle.PicklingError as err:
            logging.error( "BibleOrgSysGlobals: Unexpected error in pickleObject: {0} {1}".format( sys.exc_info()[0], err ) )
            logging.critical( "BibleOrgSysGlobals.pickleObject: Unable to pickle into {}".format( filename ) )
            return False
    return True
# end of BibleOrgSysGlobals.pickleObject


def unpickleObject( filename, folderName=None ):
    """
    Reads the object from the file and returns it.

    NOTE: The class for the object must, of course, be loaded already (at the module level).
    """
    assert filename
    if folderName is None: folderName = DEFAULT_WRITEABLE_CACHE_FOLDERPATH
    filepath = Path( folderName, filename )
    vPrint( 'Info', debuggingThisModule, _("Loading object from pickle file {}…").format( filepath ) )
    with open( filepath, 'rb') as pickleInputFile:
        return pickle.load( pickleInputFile ) # The protocol version used is detected automatically, so we do not have to specify it
# end of BibleOrgSysGlobals.unpickleObject


##########################################################################################################
#
# Default program setup routine

def setup( shortProgName:str, progVersion:str, lastModDate:str='', loggingFolderpath=None ) -> ArgumentParser:
    """
    Does the initial set-up for our scripts / programs.

    Sets up logging to a file in the default logging folderName.

    Returns the parser object
        so that custom command line parameters can be added
        then addStandardOptionsAndProcess must be called on it.
    """
    fnPrint( debuggingThisModule, f"BibleOrgSysGlobals.setup( {shortProgName!r}, {progVersion!r}, {lastModDate} {loggingFolderpath!r} )" )
    setupLoggingToFile( shortProgName, progVersion, folderpath=loggingFolderpath )
    logging.info( f"{shortProgName} v{progVersion} started at {programStartTime.strftime('%H:%M')}" )

    # Handle command line parameters
    parser = ArgumentParser( description='{} v{} {} {}'.format( shortProgName, progVersion, _("last modified"), lastModDate ) )
    parser.add_argument( '--version', action='version', version='v{}'.format( progVersion ) )
    return parser
# end of BibleOrgSysGlobals.setup


########################## ################################################################################
#
# Verbosity and debug settings
#

def setVerbosity( verbosityLevelParameter ):
    """
    Sets the VerbosityLevel global variable to an integer value depending on the Verbosity control.
    """
    global verbosityString, verbosityLevel

    if isinstance( verbosityLevelParameter, str ):
        if verbosityLevelParameter == 'Silent':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 0
        elif verbosityLevelParameter == 'Quiet':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 1
        elif verbosityLevelParameter == 'Normal':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 2
        elif verbosityLevelParameter == 'Informative':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 3
        elif verbosityLevelParameter == 'Verbose':
            verbosityString = verbosityLevelParameter
            verbosityLevel = 4
        else: logging.error( f"Invalid '{verbosityLevelParameter}' verbosity parameter" )

    else: # assume it's an integer
        if verbosityLevelParameter == 0:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Silent'
        elif verbosityLevelParameter == 1:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Quiet'
        elif verbosityLevelParameter == 2:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Normal'
        elif verbosityLevelParameter == 3:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Informative'
        elif verbosityLevelParameter == 4:
            verbosityLevel = verbosityLevelParameter
            verbosityString = 'Verbose'
        else: logging.error( "Invalid '" + verbosityLevelParameter + "' verbosity parameter" )

    dPrint( 'Verbose', debuggingThisModule, '  Verbosity =', verbosityString )
    dPrint( 'Verbose', debuggingThisModule, '  VerbosityLevel =', verbosityLevel )
# end of BibleOrgSysGlobals.setVerbosity function


def introduceProgram( theirName:str, theirProgramNameVersion:str, theirLastModifiedDate:str ) -> None:
    """
    Introduces the program name and version
        and maybe some modification dates if more verbose.
    """
    if verbosityLevel > 2:
        vPrint( 'Quiet', debuggingThisModule, f'{theirProgramNameVersion} {_("last modified")} {theirLastModifiedDate}' )
        if theirName == '__main__':
            latestPythonModificationDate = getLatestPythonModificationDate()
            if verbosityLevel > 3 \
            or latestPythonModificationDate != theirLastModifiedDate:
                vPrint( 'Quiet', debuggingThisModule, f"  ({_('Last BibleOrgSys code update was')} {latestPythonModificationDate})" )
    else:
        vPrint( 'Quiet', debuggingThisModule, theirProgramNameVersion )

    vPrint( 'Normal', debuggingThisModule, """  This program comes with ABSOLUTELY NO WARRANTY.
  It is free software, and you are welcome to redistribute it under certain conditions.
  See the license in file 'gpl-3.0.txt' for more details.
  """ )
# end of BibleOrgSysGlobals.introduceProgram function


def setDebugFlag( newValue=True ) -> None:
    """
    Set the debug flag.
    """
    global debugFlag
    debugFlag = newValue
    dPrint( 'Verbose', debuggingThisModule, '  debugFlag =', debugFlag )
# end of BibleOrgSysGlobals.setDebugFlag


def setStrictCheckingFlag( newValue=True ):
    """
    See the strict checking flag.
    """
    global strictCheckingFlag
    strictCheckingFlag = newValue
    dPrint( 'Verbose', debuggingThisModule, '  strictCheckingFlag =', strictCheckingFlag )
# end of BibleOrgSysGlobals.setStrictCheckingFlag


# Some global variables
loadedBibleBooksCodes:Optional[List[str]] = None
loadedUSFMMarkers:Optional[List[str]] = None
USFMParagraphMarkers:Optional[List[str]] = None
internal_SFMs_to_remove:Optional[List[str]] = None

def preloadCommonData() -> None:
    """
    Preload common data structures (used by many modules)
        This includes BibleBooksCode and USFMMarkers
    """
    # Load Bible data sets that are globally useful
    global loadedBibleBooksCodes, loadedUSFMMarkers, USFMParagraphMarkers, internal_SFMs_to_remove
    from BibleOrgSys.Reference.BibleBooksCodes import BibleBooksCodes
    loadedBibleBooksCodes = BibleBooksCodes().loadData()
    assert loadedBibleBooksCodes # Why didn't this load ???
    #from BibleOrgSys.Reference.USFM2Markers import USFM2Markers
    #USFM2Markers = USFM2Markers().loadData()
    #USFM2ParagraphMarkers = USFM2Markers.getNewlineMarkersList( 'CanonicalText' )
    #USFM2ParagraphMarkers.remove( 'qa' ) # This is actually a heading marker
    #dPrint( 'Quiet', debuggingThisModule, len(USFM2ParagraphMarkers), sorted(USFM2ParagraphMarkers) )
    #for marker in ( ):
        #dPrint( 'Quiet', debuggingThisModule, marker )
        #USFM2ParagraphMarkers.remove( marker )
    # was 30 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    #    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4',
    #    'qm1', 'qm2', 'qm3', 'qm4']
    # now 33 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'nb', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    #    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4', 'qc',
    #    'qm1', 'qm2', 'qm3', 'qm4', 'qr'] without 'qa'
    #dPrint( 'Quiet', debuggingThisModule, len(USFM2ParagraphMarkers), sorted(USFM2ParagraphMarkers) ); halt
    from BibleOrgSys.Reference.USFM3Markers import USFM3Markers
    loadedUSFMMarkers = USFM3Markers().loadData()
    assert loadedUSFMMarkers # Why didn't this load ???
    USFMParagraphMarkers = loadedUSFMMarkers.getNewlineMarkersList( 'CanonicalText' )
    assert USFMParagraphMarkers # Why didn't this work ???
    USFMParagraphMarkers.remove( 'qa' ) # This is actually a heading marker
    internal_SFMs_to_remove = loadedUSFMMarkers.getCharacterMarkersList( includeBackslash=True, includeNestedMarkers=True, includeEndMarkers=True )
    internal_SFMs_to_remove.sort( key=len, reverse=True ) # List longest first
# end of BibleOrgSysGlobals.preloadCommonData


def addStandardOptionsAndProcess( parserObject, exportAvailable=False ) -> None:
    """
    Add our standardOptions to the command line parser.
    Determine multiprocessing strategy.

    Then preloads common data structures.
    """
    global commandLineArguments
    fnPrint( debuggingThisModule, "BibleOrgSysGlobals.addStandardOptionsAndProcess( …, {} )".format( exportAvailable ) )

    verbosityGroup = parserObject.add_argument_group( 'Verbosity Group', 'Console verbosity controls' )
    mainVerbosityGroup = verbosityGroup.add_mutually_exclusive_group()
    mainVerbosityGroup.add_argument( '-s', '--silent', action='store_const', dest='verbose', const=0, help="output no information to the console" )
    mainVerbosityGroup.add_argument( '-q', '--quiet', action='store_const', dest='verbose', const=1, help="output less information to the console" )
    mainVerbosityGroup.add_argument( '-i', '--informative', action='store_const', dest='verbose', const=3, help="output more information to the console" )
    mainVerbosityGroup.add_argument( '-v', '--verbose', action='store_const', dest='verbose', const=4, help="output lots of information for the user" )
    EWgroup = verbosityGroup.add_mutually_exclusive_group()
    EWgroup.add_argument( '-e', '--errors', action='store_true', dest='errors', default=False, help="log errors to console" )
    EWgroup.add_argument( '-w', '--warnings', action='store_true', dest='warnings', default=False, help="log warnings and errors to console" )
    verbosityGroup.add_argument( '-d', '--debug', action='store_true', dest='debug', default=False, help="output even more information for the programmer/debugger" )
    parserObject.add_argument( '-1', '--single', action='store_true', dest='single', default=False, help="don't use multiprocessing (that's the digit one)" )
    parserObject.add_argument( '-c', '--strict', action='store_true', dest='strict', default=False, help="perform very strict checking of all input" )
    if exportAvailable:
        parserObject.add_argument('-x', '--export', action='store_true', dest='export', default=False, help="export the data file(s)")
    commandLineArguments = parserObject.parse_args()
    #if commandLineArguments.errors and commandLineArguments.warnings:
        #parserObject.error( "options -e and -w are mutually exclusive" )

    setVerbosity( commandLineArguments.verbose if commandLineArguments.verbose is not None else 2)
    if commandLineArguments.debug: setDebugFlag()

    # Determine console logging levels
    if commandLineArguments.warnings: addConsoleLogging( logging.WARNING if not debugFlag else logging.DEBUG )
    elif commandLineArguments.errors: addConsoleLogging( logging.ERROR )
    else: addConsoleLogging( logging.CRITICAL ) # default
    if commandLineArguments.strict: setStrictCheckingFlag()

    # Determine multiprocessing strategy
    global maxProcesses
    maxProcesses = os.cpu_count()
    if maxProcesses > 1:
        # Don't use 1-3 processes
        reservedProcesses = max( 1, maxProcesses*15//100 )
        # dPrint( 'Quiet', debuggingThisModule, "reservedProcesses", reservedProcesses )
        maxProcesses = maxProcesses - reservedProcesses
        # dPrint( 'Quiet', debuggingThisModule, "maxProcesses", maxProcesses )
    if commandLineArguments.single: maxProcesses = 1
    if debugFlag or debuggingThisModule:
        if maxProcesses > 1:
            dPrint( 'Quiet', debuggingThisModule, f"DEBUG/SINGLE MODE: Reducing maxProcesses from {maxProcesses} down to 1" )
        maxProcesses = 1 # Limit to one process
        dPrint( 'Quiet', debuggingThisModule, "commandLineArguments: {}".format( commandLineArguments ) )

    preloadCommonData()
# end of BibleOrgSysGlobals.addStandardOptionsAndProcess


def printAllGlobals( indent=None ):
    """
    Print all global variables (for debugging usually).
    """
    if indent is None: indent = 2
    dPrint( 'Quiet', debuggingThisModule, "{}commandLineArguments: {}".format( ' '*indent, commandLineArguments ) )
    dPrint( 'Quiet', debuggingThisModule, "{}debugFlag: {}".format( ' '*indent, debugFlag ) )
    dPrint( 'Quiet', debuggingThisModule, "{}maxProcesses: {}".format( ' '*indent, maxProcesses ) )
    dPrint( 'Quiet', debuggingThisModule, "{}verbosityString: {}".format( ' '*indent, verbosityString ) )
    dPrint( 'Quiet', debuggingThisModule, "{}verbosityLevel: {}".format( ' '*indent, verbosityLevel ) )
    dPrint( 'Quiet', debuggingThisModule, "{}strictCheckingFlag: {}".format( ' '*indent, strictCheckingFlag ) )
# end of BibleOrgSysGlobals.printAllGlobals


def elapsedTime( startTime ):
    """
    Returns a formatted string containing the elapsed time since startTime.
    """
    timeElapsed = ( datetime.now() - startTime )
    seconds = timeElapsed.seconds # This is an integer
    if seconds == 0:
        return f'{timeElapsed.microseconds // 1_000} milliseconds'
    minutes = seconds / 60.0
    hours = minutes / 60.0
    if minutes > 90:
        return '{0:.2g} hours'.format( hours ).lstrip()
    if seconds > 90:
        return '{0:.2g} minutes'.format( minutes ).lstrip()
    secondsString = str(seconds)
    return secondsString + (' second' if secondsString=='1' else ' seconds')
# end of elapsedTime


def closedown( cProgName, cProgVersion ):
    """
    Does all the finishing off for the program.
    """
    msg = f"{cProgName} v{cProgVersion} finished at {datetime.now().strftime('%H:%M')} after {elapsedTime(programStartTime)}."
    logging.info( msg )
    vPrint( 'Normal', debuggingThisModule, msg )
# end of BibleOrgSysGlobals.closedown


setVerbosity( verbosityString )
#if 0 and __name__ != '__main__':
    ## Load Bible data sets that are globally useful
    #from BibleOrgSys.Reference.BibleBooksCodes import BibleBooksCodes
    #BibleBooksCodes = BibleBooksCodes().loadData()
    #from BibleOrgSys.Reference.USFM3Markers import USFM3Markers
    #USFMMarkers = USFM3Markers().loadData()
    #USFMParagraphMarkers = USFMMarkers.getNewlineMarkersList( 'CanonicalText' )
    ##dPrint( 'Quiet', debuggingThisModule, len(USFMParagraphMarkers), sorted(USFMParagraphMarkers) )
    ##for marker in ( ):
        ##dPrint( 'Quiet', debuggingThisModule, marker )
        ##USFMParagraphMarkers.remove( marker )
    ## was 30 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    ##    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4',
    ##    'qm1', 'qm2', 'qm3', 'qm4']
    ## now 34 ['cls', 'li1', 'li2', 'li3', 'li4', 'm', 'mi', 'nb', 'p', 'pc', 'ph1', 'ph2', 'ph3', 'ph4',
    ##    'pi1', 'pi2', 'pi3', 'pi4', 'pm', 'pmc', 'pmo', 'pmr', 'pr', 'q1', 'q2', 'q3', 'q4', 'qa', 'qc',
    ##    'qm1', 'qm2', 'qm3', 'qm4', 'qr']
    ##dPrint( 'Quiet', debuggingThisModule, len(USFMParagraphMarkers), sorted(USFMParagraphMarkers) ); halt



def briefDemo() -> None:
    """
    Demo program to handle command line parameters
        and then demonstrate some basic functions.
    """
    introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )
    if verbosityLevel>2: printAllGlobals()

    # Demonstrate peekAtFirstLine function
    line1a = peekIntoFile( BOS_SOURCE_BASE_FOLDERPATH.joinpath( 'Bible.py' ), numLines=2 ) # Simple filename
    vPrint( 'Quiet', debuggingThisModule, "\nBible.py starts with {!r}".format( line1a ) )
    line1b = peekIntoFile( 'README.rst', BOS_LIBRARY_BASE_FOLDERPATH, 3 ) # Filename and folderName
    vPrint( 'Quiet', debuggingThisModule, "README.rst starts with {!r}".format( line1b ) )
    line1c = peekIntoFile( BOS_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes.xml' ) ) # Filepath
    vPrint( 'Quiet', debuggingThisModule, "BibleBooksCodes.xml starts with {!r}".format( line1c ) )

    vPrint( 'Quiet', debuggingThisModule, "\nFirst one made string safe: {!r}".format( makeSafeString( line1a[0] ) ) )
    vPrint( 'Quiet', debuggingThisModule, "First one made filename safe: {!r}".format( makeSafeFilename( line1a[0] ) ) )
    vPrint( 'Quiet', debuggingThisModule, "Last one made string safe: {!r}".format( makeSafeString( line1c ) ) )
    vPrint( 'Quiet', debuggingThisModule, "Last one made filename safe: {!r}".format( makeSafeFilename( line1c ) ) )

    accentedString1 = 'naïve café'
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    vPrint( 'Quiet', debuggingThisModule, "\nRemoving accents…" )
    for accentedString in ( accentedString1, dan11, ):
        for thisAccentedString in ( accentedString, accentedString.lower(), accentedString.upper(), ):
            vPrint( 'Quiet', debuggingThisModule, "  Given: {}".format( thisAccentedString ) )
            vPrint( 'Quiet', debuggingThisModule, "    removeAccents gave: {}".format( removeAccents( thisAccentedString ) ) )
    for accentedChar in ACCENT_DICT:
        got = removeAccents(accentedChar)
        wanted = ACCENT_DICT[accentedChar]
        vPrint( 'Quiet', debuggingThisModule, "  Given: {!r} got {!r}{}".format( accentedChar, got, '' if got==wanted else ' (hoped for {!r})'.format( wanted ) ) )

    longText = "The quick brown fox jumped over the lazy brown dog."
    vPrint( 'Quiet', debuggingThisModule, "\nGiven: {}".format( longText ) )
    adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
    vPrint( 'Quiet', debuggingThisModule, "  {!r}->adj->{!r}".format( longText, applyStringAdjustments( longText, adjustments ) ) )

    vPrint( 'Quiet', debuggingThisModule, '\nstripWordPunctuation() tests…' )
    for someText in ( '(hello', 'again', '(hello)', '"Hello"', 'there)', 'you(sg)', 'you(pl),', '(we(incl))!', '(in)front', '(in)front.', '(wow).', '(wow.)', 'it_work(s)', 'it_work(s)_now!', 'Is_','he','still','_alive?', ):
        vPrint( 'Quiet', debuggingThisModule, '  {!r} -> {!r}'.format( someText, stripWordPunctuation(someText) ) )

    vPrint( 'Quiet', debuggingThisModule, "\ncpu_count", os.cpu_count() )
# end of BibleOrgSysGlobals.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )
    if verbosityLevel>2: printAllGlobals()

    # Demonstrate peekAtFirstLine function
    line1a = peekIntoFile( BOS_SOURCE_BASE_FOLDERPATH.joinpath( 'Bible.py' ), numLines=2 ) # Simple filename
    vPrint( 'Quiet', debuggingThisModule, "\nBible.py starts with {!r}".format( line1a ) )
    line1b = peekIntoFile( 'README.rst', BOS_LIBRARY_BASE_FOLDERPATH, 3 ) # Filename and folderName
    vPrint( 'Quiet', debuggingThisModule, "README.rst starts with {!r}".format( line1b ) )
    line1c = peekIntoFile( BOS_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes.xml' ) ) # Filepath
    vPrint( 'Quiet', debuggingThisModule, "BibleBooksCodes.xml starts with {!r}".format( line1c ) )

    vPrint( 'Quiet', debuggingThisModule, "\nFirst one made string safe: {!r}".format( makeSafeString( line1a[0] ) ) )
    vPrint( 'Quiet', debuggingThisModule, "First one made filename safe: {!r}".format( makeSafeFilename( line1a[0] ) ) )
    vPrint( 'Quiet', debuggingThisModule, "Last one made string safe: {!r}".format( makeSafeString( line1c ) ) )
    vPrint( 'Quiet', debuggingThisModule, "Last one made filename safe: {!r}".format( makeSafeFilename( line1c ) ) )

    accentedString1 = 'naïve café'
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    vPrint( 'Quiet', debuggingThisModule, "\nRemoving accents…" )
    for accentedString in ( accentedString1, dan11, ):
        for thisAccentedString in ( accentedString, accentedString.lower(), accentedString.upper(), ):
            vPrint( 'Quiet', debuggingThisModule, "  Given: {}".format( thisAccentedString ) )
            vPrint( 'Quiet', debuggingThisModule, "    removeAccents gave: {}".format( removeAccents( thisAccentedString ) ) )
    for accentedChar in ACCENT_DICT:
        got = removeAccents(accentedChar)
        wanted = ACCENT_DICT[accentedChar]
        vPrint( 'Quiet', debuggingThisModule, "  Given: {!r} got {!r}{}".format( accentedChar, got, '' if got==wanted else ' (hoped for {!r})'.format( wanted ) ) )

    longText = "The quick brown fox jumped over the lazy brown dog."
    vPrint( 'Quiet', debuggingThisModule, "\nGiven: {}".format( longText ) )
    adjustments = [(36,'lazy','fat'),(0,'The','A'),(20,'jumped','tripped'),(4,'','very '),(10,'brown','orange')]
    vPrint( 'Quiet', debuggingThisModule, "  {!r}->adj->{!r}".format( longText, applyStringAdjustments( longText, adjustments ) ) )

    vPrint( 'Quiet', debuggingThisModule, '\nstripWordPunctuation() tests…' )
    for someText in ( '(hello', 'again', '(hello)', '"Hello"', 'there)', 'you(sg)', 'you(pl),', '(we(incl))!', '(in)front', '(in)front.', '(wow).', '(wow.)', 'it_work(s)', 'it_work(s)_now!', 'Is_','he','still','_alive?', ):
        vPrint( 'Quiet', debuggingThisModule, '  {!r} -> {!r}'.format( someText, stripWordPunctuation(someText) ) )

    vPrint( 'Quiet', debuggingThisModule, "\ncpu_count", os.cpu_count() )
# end of BibleOrgSysGlobals.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
    addStandardOptionsAndProcess( parser )

    fullDemo()

    closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleOrgSysGlobals.py
