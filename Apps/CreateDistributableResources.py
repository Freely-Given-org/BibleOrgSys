#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CreateDistributableResources.py
#
# App to create zipped PickledBible for distributable Bible/commentary resources.
#
# Copyright (C) 2018-2023 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
App to create zipped PickledBible for distributable Bible/commentary resources,
    e.g., Open Scriptures Hebrew Bible,
            WEB and related versions,
            older public domain Bible versions.

Made to be run from the BibleOrgSys folder, i.e.,
    Apps/CreateDistributableResources.py

Use --export (-x) to also do BibleDropBox submissions.

CHANGELOG:
    2022-06-05 reenabled all demos
    2023-02-16 added OET RV & LV
"""
from gettext import gettext as _
import os
from pathlib import Path
import multiprocessing
import subprocess

# BibleOrgSys imports
if __name__ == '__main__':
    import sys
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../BibleOrgSys/') ) ) # So we can run it from the folder above and still do these imports
    sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(__file__), '../') ) ) # So we can run it from the folder above and still do these imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.OriginalLanguages.HebrewWLCBible import OSISHebrewWLCBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Formats.PTX8Bible import PTX8Bible
from BibleOrgSys.Formats.PickledBible import PickledBible, ZIPPED_PICKLE_FILENAME_END

from Extras.BibleDropBoxHelpers import submitBDBFolder


LAST_MODIFIED_DATE = '2023-02-16' # by RJH
SHORT_PROGRAM_NAME = "CreateDistributableResources"
PROGRAM_NAME = "Create Distributable Resources"
PROGRAM_VERSION = '0.32'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
PROGRAM_NAME_VERSION_DATE = f'{PROGRAM_NAME_VERSION} {_("last modified")} {LAST_MODIFIED_DATE}'

DEBUGGING_THIS_MODULE = False


BIBLES_FOLDERPATH = Path( '/mnt/SSDs/Bibles/' )
OPEN_SCRIPTURES_INPUT_RESOURCES_FOLDERPATH = Path( '/home/robert/Programming/WebDevelopment/OpenScriptures/' )

WRITEABLE_DISTRIBUTABLE_RESOURCES_FOLDERPATH = BibleOrgSysGlobals.BOS_DEFAULT_WRITEABLE_BASE_FOLDERPATH.joinpath( 'BOSDistributableResources/' )
TEST_OUTPUT_FOLDERPATH = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Test_DistributableResources/' )
DEFAULT_DATA_LEVEL = 1 # We use level 1 of PickledBible which saves minimal data used for displaying the resource
HAIOLA_SOURCE_FOLDERPATH = BIBLES_FOLDERPATH.joinpath( 'USFM Bibles/Haiola USFM test versions/' )
DOOR43_SOURCE_FOLDERPATH = BIBLES_FOLDERPATH.joinpath( 'Door43CatalogVersions/' )
OPEN_BIBLE_SOURCE_FOLDERPATH = BIBLES_FOLDERPATH.joinpath( 'Biblica_Open.Bible_Versions/' )

FG_REPOS_FOLDERPATH = Path( '/srv/Documents/FreelyGiven/' )
OET_REPO_FOLDERPATH = FG_REPOS_FOLDERPATH.joinpath( 'OpenEnglishTranslation--OET/' )


# NOTE: Use --export (-x) to also do BibleDropBox submissions

# Demo function will process all modules (e.g., when called from Tests/DemoTests.py)
#   but main won't.
PROCESS_ONE = 'OET' # Will disable all others if set to an abbreviation, e.g., 'ASV' or 'WLC'
PROCESS_ALL_FLAG = (True or __name__ != '__main__') and not PROCESS_ONE
PROCESS_OET_FLAG = False and not PROCESS_ONE
PROCESS_WLC_FLAG = False and not PROCESS_ONE
PROCESS_EBIBLE_FLAG = False and not PROCESS_ONE
PROCESS_UNFOLDING_WORD_FLAG = False and not PROCESS_ONE
PROCESS_DOOR43_FLAG = False and not PROCESS_ONE
PROCESS_OPEN_BIBLE_FLAG = False and not PROCESS_ONE
PROCESS_OTHERS_FLAG = False and not PROCESS_ONE

PROCESS_CHANGES_ONLY = False and not PROCESS_ONE



def runGitPull( gitFolderpath ) -> bool:
    """
    Do a git pull on the given folder (to ensure that the files are up-to-date).

    Return True if changes were made.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"\nrunGitPull( {gitFolderpath} )" )
    gitPullTimeout = '30s'

    cwdSave = os.getcwd() # Save the current working directory before changing (below) to the output directory
    os.chdir( gitFolderpath ) # So the paths for the Bible.cls file are correct

    parameters = ['/usr/bin/timeout', gitPullTimeout, '/usr/bin/git', 'pull']
    myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
    programOutputBytes, programErrorOutputBytes = myProcess.communicate()
    os.chdir( cwdSave ) # Restore the original path again
    if myProcess.returncode == 124: # it timed out
        programErrorOutputBytes += "git pull for {}: Timed out after {}".format( gitFolderpath, gitPullTimeout ).encode( 'utf-8' )
    # Process the output
    if programOutputBytes:
        programOutputString = programOutputBytes.decode( encoding='utf-8', errors='replace' )
        #programOutputString = programOutputString.replace( baseFolder + ('' if baseFolder[-1]=='/' else '/'), '' ) # Remove long file paths to make it easier for the user to read
        #with open( os.path.join( outputFolderpath, 'ScriptOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programOutputString )
        if programOutputString.endswith( '\n' ):
            programOutputString = programOutputString[:-1] # Remove unneeded EOL character
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {gitFolderpath} git response: {programOutputString!r}" ) # Use REPR so it all stays on one line
    else: programOutputString = None
    if programErrorOutputBytes:
        programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
        #with open( os.path.join( outputFolderpath, 'ScriptErrorOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programErrorOutputString )
        if programErrorOutputString.endswith( '\n' ):
            programErrorOutputString = programErrorOutputString[:-1] # Remove unneeded EOL character
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  git ERROR response: {programErrorOutputString!r}" ) # Use REPR so it all stays on one line
    changedFlag = programOutputString!='Already up to date.' and not programErrorOutputBytes
    if PROCESS_CHANGES_ONLY: print( f"    Returning haveChanges={changedFlag}" )
    return changedFlag
# end of CreateDistributableResources.runGitPull



def makePickle( abbreviation:str, BibleObject, metadataDict:dict, outputFolderpath:Path ) -> None:
    """
    Given a BibleObject with the books already loaded, make a pickled Bible.

    Test if necessary.
    """
    fnPrint( DEBUGGING_THIS_MODULE, "makePickle( {}, {}, {}, {} )".format( abbreviation, BibleObject.getAName(), len(metadataDict), outputFolderpath ) )
    assert isinstance( abbreviation, str )
    assert 1 < len(abbreviation) < 10
    assert isinstance( BibleObject, Bible )
    assert isinstance( metadataDict, dict )
    assert isinstance( outputFolderpath, Path )

    BibleObject.toPickledBible( outputFolderpath=outputFolderpath, metadataDict=metadataDict,
                        dataLevel=DEFAULT_DATA_LEVEL, zipOnly=True )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Created {} zipped PickledBible in {}".format( abbreviation, outputFolderpath ) )

    if BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
        pickledBible = PickledBible( outputFolderpath.joinpath( abbreviation+ZIPPED_PICKLE_FILENAME_END ) )
        pickledBible.preload()
        assert pickledBible.abbreviation, f"{pickledBible=} {pickledBible.abbreviation=}"
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, pickledBible ) # Just print a summary
        pickledBible.loadBooks() # Test all the books
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, pickledBible ) # Now print a new summary
# end of CreateDistributableResources.makePickle



def submitBDBEntry( abbreviation:str, BibleObject, metadataDict:dict ) -> None:
    """
    Given a BibleObject with the books already loaded, make and submit a Bible Drop Box entry.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"submitBDBEntry( {abbreviation}, {BibleObject.getAName()}, {metadataDict} )" )

    submitBDBFolder( BibleObject.sourceFolder, BibleObject.getAName(), abbreviation, BibleObject.objectTypeString, 'Demo', metadataDict )
# end of CreateDistributableResources.submitBDBEntry



def makeIt( abbreviation:str, BibleObject, metadataDict, outputFolderpath:Path, submit2BDB:bool=False ) -> None:
    """
    Given a BibleObject, load the books and then make a pickled Bible.

    Test if necessary.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeIt( {abbreviation}, {BibleObject.getAName()}, {len(metadataDict)}, {outputFolderpath} )" )
    assert isinstance( abbreviation, str )
    assert 1 < len(abbreviation) < 10
    assert isinstance( BibleObject, Bible )
    assert isinstance( metadataDict, dict )
    assert isinstance( outputFolderpath, Path )
    assert isinstance( submit2BDB, bool )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("\nLoading {}…").format( abbreviation ) )
    BibleObject.loadBooks() # Load and process the books (if that applies to this kind of Bible)

    if BibleObject.suppliedMetadata is None: BibleObject.suppliedMetadata = {}
    BibleObject.suppliedMetadata['File'] = metadataDict
    BibleObject.applySuppliedMetadata( 'File' )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BibleObject ) # Just print a summary

    makePickle( abbreviation, BibleObject, metadataDict, outputFolderpath )
    if submit2BDB:
        submitBDBEntry( abbreviation, BibleObject, metadataDict )
# end of CreateDistributableResources.makeIt



def runCreateAll( outputFolderpath:Path, submit2BDB:bool=False ) -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS.

    Note: See https://Freely-Given.org/Software/BibleDropBox/Metadata.html
            for info about metadata fields.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"runCreateAll( {outputFolderpath} )" )
    assert os.path.isdir( outputFolderpath )


### Freely-Given.org Open English Translation Readers' Version & Literal Version (OET-RV & OET-LV)
    if PROCESS_WLC_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE=='OET':
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nUpdating OET from internet…" )
        repo_changed = runGitPull( OET_REPO_FOLDERPATH ) # Make sure we have the latest version
        if repo_changed or not PROCESS_CHANGES_ONLY:
            abbreviation, name = 'OET-RV', 'Open English Translation Readers’ Version'
            thisBible = USFMBible( OET_REPO_FOLDERPATH.joinpath( 'translatedTexts/ReadersVersion/' ),
                                                    givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'A still-being-translated, exciting new Bible translation viewable at https://OpenEnglishTranslation.Bible',
                            'Source': 'https://github.com/Freely-Given-org/OpenEnglishTranslation--OET',
                            'Licence': 'Creative Commons Attribution 4.0 International (CC BY 4.0)',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )

            abbreviation, name = 'OET-LV', 'Open English Translation Literal Version'
            thisBible = USFMBible( OET_REPO_FOLDERPATH.joinpath( 'intermediateTexts/auto_edited_VLT_USFM/' ),
                                                    givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'A still-being-developed, very literal English Bible translation viewable at https://OpenEnglishTranslation.Bible',
                            'Source': 'https://github.com/Freely-Given-org/OpenEnglishTranslation--OET',
                            'Licence': 'Creative Commons Attribution 4.0 International (CC BY 4.0)',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )


### OPEN SCRIPTURES HEBREW WLC
    if PROCESS_WLC_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE=='WLC': # Open Scriptures Hebrew WLC
        abbreviation, name = 'WLC', 'Westminster Leningrad Codex'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nUpdating Hebrew {abbreviation} from internet…" )
        repo_changed = runGitPull( OPEN_SCRIPTURES_INPUT_RESOURCES_FOLDERPATH.joinpath( 'morphhb/' ) ) # Make sure we have the latest version
        if repo_changed or not PROCESS_CHANGES_ONLY:
            thisBible = OSISHebrewWLCBible()
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb',
                            'Source': 'https://github.com/openscriptures/morphhb',
                            'Licence': 'Creative Commons Attribution 4.0 International (CC BY 4.0)',
                            'LanguageName': 'Hebrew',
                            'ISOLanguageCode': 'heb',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )


### eBIBLE.org
    if PROCESS_EBIBLE_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE: # eBible.org versions
        # The downloads for these eBible files are updated every month by a boss script
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='ASV'):
            abbreviation, name = 'ASV', 'American Standard Version (1901)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-asv_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The American Standard Version of the Holy Bible, first published in 1901.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-asv',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='BBE'):
            abbreviation, name = 'BBE', 'The Bible in Basic English'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engBBE_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Bible In Basic English (translated by Samuel Henry Hooke) was printed in 1965 by Cambridge Press in England.',
                            'Source': 'https://eBible.org/find/details.php?id=engBBE',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='Brenton'):
            abbreviation, name = 'Brenton', 'Brenton Septuagint Translation (1844)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-Brenton_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'Translation of the Greek Septuagint into English by Sir Lancelot Charles Lee Brenton.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-Brenton',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='DBY'):
            abbreviation, name = 'DBY', 'Darby Translation (1890)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engDBY_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Scriptures, a New Translation from the Original Languages by J. N. Darby.',
                            'Source': 'https://eBible.org/find/details.php?id=engDBY',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='DRV'):
            abbreviation, name = 'DRV', 'Douay-Rheims (1899)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engDRA_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible in English, Douay-Rheims American Edition of 1899, translated from the Latin Vulgate.',
                            'Source': 'https://eBible.org/find/details.php?id=engDRA',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        #if 1 or PROCESS_ALL_FLAG: # NOT FREELY DISTRIBUTABLE
            #abbreviation, name = 'ERV', 'The Holy Bible, Easy-to-Read Version'
            #thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engerv_usfm/' ),
                            #givenName=name, givenAbbreviation=abbreviation )
            #metadataDict = {
                            #'Abbreviation': abbreviation,
                            #'WorkName': name,
                            #'About': 'The Holy Bible, Easy-to-Read Version. Translation by: World Bible Translation Center.',
                            #'Source': 'https://eBible.org/find/details.php?id=engerv',
                            #'CopyrightNotice': 'Copyright © 1987, 1999, 2006 Bible League International',
                           #'LanguageName': '',
                           #'ISOLanguageCode': '',
                            #}
            #makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='GNV'):
            abbreviation, name = 'GNV', 'Geneva Bible (1599)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'enggnv_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Geneva Bible in Old English of 1599.',
                            'Source': 'https://eBible.org/find/details.php?id=enggnv',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Old English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='GLW'):
            abbreviation, name = 'GLW', 'God’s Living Word (1996)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-glw_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'God’s Living Word—a translation of John and John’s Letters into modern English by Michael Paul Johnson.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-glw',
                            'CopyrightNotice': 'Copyright © 1996 Michael Paul Johnson.',
                            'Licence': 'This translation is made available to you under the terms of the Creative Commons Attribution-No Derivatives license 4.0.',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='KJV'):
            abbreviation, name = 'KJV', 'King James (Authorized) Version (1769)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-kjv2006_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The King James Version or Authorized Version of the Holy Bible, using the standardized text of 1769, with Strongs numbers added.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-kjv2006',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='KJVD'):
            abbreviation, name = 'KJVD', 'King James (Authorized) Version with Apocrypha (1769)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-kjv_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The King James Version or Authorized Version of the Holy Bible, using the standardized text of 1769, with Strongs numbers added, with Apocrypha/Deuterocanon.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-kjv',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='LXX2012'):
            abbreviation, name = 'LXX2012', 'Septuagint in American English (2012)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-lxx2012_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Septuagint with Apocrypha, translated from Greek to English by Sir Lancelot C. L. Brenton and published in 1885, with some language updates (American English).',
                            'Source': 'https://eBible.org/find/details.php?id=eng-lxx2012',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='LXX2012UK'):
            abbreviation, name = 'LXX2012UK', 'Septuagint in British/International English (2012)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-uk-lxx2012_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Septuagint with Apocrypha, translated from Greek to English by Sir Lancelot C. L. Brenton and published in 1885, with some language updates (British/International English).',
                            'Source': 'https://eBible.org/find/details.php?id=eng-uk-lxx2012',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='NOY'):
            abbreviation, name = 'NOY', 'George Noyes Bible (1869)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engnoy_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible, translated into English by George Noyes (1869).',
                            'Source': 'https://eBible.org/Scriptures/details.php?id=engnoy',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='OEB'):
            abbreviation, name = 'OEB', 'Open English Bible (U.S. spelling)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engoebus_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible, Open English Bible translation, U. S. spelling edition.',
                            'Source': 'https://eBible.org/find/details.php?id=engoebusw',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='OEBCW'):
            abbreviation, name = 'OEBCW', 'Open English Bible (Commonwealth spelling)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engoebcw_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible, Open English Bible translation, Commonwealth spelling edition.',
                            'Source': 'https://eBible.org/find/details.php?id=engoebcww',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='OURB'):
            abbreviation, name = 'OURB', 'One Unity Resource Bible (2016)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engourb_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The One Unity Resource Bible translation of the Holy Bible into American English with some transliterated Hebrew notations.',
                            'Source': 'https://eBible.org/find/details.php?id=engourb',
                            'Licence': 'Creative Commons Attribution Share-Alike license 4.0.',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='RV'):
            abbreviation, name = 'RV', 'Revised Version with Apocrypha (1895)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-rv_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Revised Version of the Holy Bible (1895) with Apocrypha.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-rv',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='T4T'):
            abbreviation, name = 'T4T', 'Translation for Translators'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-t4t_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'A Bible Translation for Bible Translators which makes implied information explicit in the text as an aid to the translator who may need that information to correctly translate into a particular language.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-t4t',
                            'CopyrightNotice': 'Copyright © 2008-2017 Ellis W. Deibler, Jr.',
                            'Licence': 'Creative Commons Attribution Share-Alike license 4.0.',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='FLS'):
            abbreviation, name = 'FLS', 'Louis Segond Bible (1910)' # or F10
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'fraLSG_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'French Louis Segond 1910 Bible.',
                            'Source': 'https://eBible.org/find/details.php?id=fraLSG',
                            'CopyrightNotice': "Cette Bible est dans le domaine public. Il n'est pas protégé par copyright. This Bible is in the Public Domain. It is not copyrighted.",
                            'Licence': 'Public Domain',
                            'LanguageName': 'Français (French)',
                            'ISOLanguageCode': 'fra',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='FOB'):
            abbreviation, name = 'FOB', 'La Sainte Bible'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'fra_fob_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible in French, by Ostervald.',
                            'Source': 'https://eBible.org/find/details.php?id=fra_fob',
                            #'CopyrightNotice': '',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Français (French)',
                            'ISOLanguageCode': 'fra',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='SBL'):
            abbreviation, name = 'SBL', 'Sainte Bible libre pour le monde'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'frasbl_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible in French, Sainte Bible Libre pour le monde translation (2022). Il s’agit d’un brouillon de traduction. Il est en cours de relecture et d’édition. Si vous trouvez des erreurs, veuillez nous en informer à https://eBible.org/cgi-bin/contact.cgi. This is a draft translation. It is being proofread and edited. If you find errors, please let us know at https://eBible.org/cgi-bin/contact.cgi.',
                            'Source': 'https://ebible.org/find/details.php?id=frasbl',
                            #'CopyrightNotice': '',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Français (French)',
                            'ISOLanguageCode': 'fra',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='LB'):
            abbreviation, name = 'LB', 'Luther Bibel (1912)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'deu1912_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The Holy Bible in German, by Martin Luther.',
                            'Source': 'https://eBible.org/find/details.php?id=deu1912',
                            #'CopyrightNotice': '',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Deutsch (German, Standard)',
                            'ISOLanguageCode': 'deu',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='VBL'):
            abbreviation, name = 'VBL', 'Versión Biblia Libre, Nuevo Testamento (2018)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'spavbl_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The New Testament in Spanish, Free Bible Version.',
                            'Source': 'https://eBible.org/find/details.php?id=spavbl',
                            'CopyrightNotice': 'Copyright © 2018 Jonathan Gallagher y Shelly Barrios de Avila',
                            'Licence': 'Creative Commons Attribution-No Derivatives license 4.0',
                            'LanguageName': 'Español (Spanish)',
                            'ISOLanguageCode': 'spa',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='RUSSYN'):
            abbreviation, name = 'RUSSYN', 'Синодальный перевод'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'russyn_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'Synodal Translation of the Holy Bible in Russian by Orthodox theological academies of Moscow, Saint Petersburg, Kazan, and Kiev.',
                            'Source': 'https://eBible.org/find/details.php?id=russyn',
                            #'CopyrightNotice': '',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Deutsch (German, Standard)',
                            'ISOLanguageCode': 'rus',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='VULC'):
            abbreviation, name = 'VULC', 'Clementine Vulgate (1598)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'latVUC_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'Clementine Vulgate of 1598 with Glossa Ordinaria Migne edition 1880 in Latin.',
                            'Source': 'https://eBible.org/find/details.php?id=latVUC',
                            'Licence': 'Public Domain',
                            'LanguageName': 'Latin',
                            'ISOLanguageCode': 'lat',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WEB'):
            abbreviation, name = 'WEB', 'World English Bible with Deuterocanon'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-web_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World English Bible is a Public Domain translation of the Holy Bible into modern English. Includes Apocrypha/Deuterocanon.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-web',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WEBP'):
            abbreviation, name = 'WEBP', 'World English Bible (Protestant)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engwebp_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World English Bible is a Public Domain translation of the Holy Bible into modern English.',
                            'Source': 'https://eBible.org/find/details.php?id=engwebp',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WEBC'):
            abbreviation, name = 'WEBC', 'World English Bible (Catholic)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-web-c_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World English Bible is a Public Domain translation of the Holy Bible into modern English with Catholic book order.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-web-c',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WEBBE'):
            abbreviation, name = 'WEBBE', 'World English Bible (British edition)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'eng-webbe_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World English Bible British Edition is a Public Domain translation of the Holy Bible into contemporary British/International English. Includes Apocrypha/Deuterocanon.',
                            'Source': 'https://eBible.org/find/details.php?id=eng-webbe',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WEBPB'):
            abbreviation, name = 'WEBPB', 'World English Bible (British, Protestant)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engwebpb_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World English Bible British Edition is a Public Domain translation of the Holy Bible into contemporary British/International English. Protestant edition.',
                            'Source': 'https://eBible.org/find/details.php?id=engwebpb',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WMB'):
            abbreviation, name = 'WMB', 'World Messianic Bible'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engwmb_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World Messianic Bible is a Public Domain translation of the Holy Bible into modern English as spoken among Messianic Jews. It has also been called the World English Bible: Messianic Edition and the Hebrew Names Version.',
                            'Source': 'https://eBible.org/find/details.php?id=engwmb',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='WMBB'):
            abbreviation, name = 'WMBB', 'World Messianic Bible (British edition)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engwmbb_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The World Messianic Bible British Edition is a Public Domain translation of the Holy Bible into modern English as spoken among Messianic Jews outside of the United States of America. This translation is also known as the World English Bible: British Messianic Edition.',
                            'Source': 'https://eBible.org/find/details.php?id=engwmbb',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_EBIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='Wycliffe'):
            abbreviation, name = 'Wycliffe', 'Wycliffe Bible (portions)'
            thisBible = USFMBible( HAIOLA_SOURCE_FOLDERPATH.joinpath( 'engWycliffe_usfm/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'This is the Pentateuch and Gospels from The Holy Bible, containing the Old and New Testaments, with the apocryphal books, in the earliest English version made from the Latin Vulgate by John Wycliffe and his followers. c.1395.',
                            'Source': 'https://eBible.org/find/details.php?id=engWycliffe',
                            'Licence': 'Public Domain',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )


### UNFOLDING WORD / DOOR43
    if PROCESS_UNFOLDING_WORD_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE: # UnfoldingWord/Door43 versions
        if (1 or PROCESS_ALL_FLAG or PROCESS_UNFOLDING_WORD_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='UHB'):
            abbreviation, name = 'UHB', 'unfoldingWord® Hebrew Bible'
            uwFolderpath = BIBLES_FOLDERPATH.joinpath( 'Original languages/UHB/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( uwFolderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( uwFolderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True # TODO: Shouldn't be required ???
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'The unfoldingWord® Hebrew Bible is based on the Open Scriptures Hebrew Bible, from https://github.com/openscriptures/morphhb, which is licensed as CC BY 4.0.',
                                'Source': 'https://unfoldingWord.Bible/uhb/',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'Hebrew',
                                'ISOLanguageCode': 'heb',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_UNFOLDING_WORD_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='UGNT'):
            abbreviation, name = 'UGNT', 'unfoldingWord® Hebrew Bible'
            uwFolderpath = BIBLES_FOLDERPATH.joinpath( 'Original languages/UGNT/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( uwFolderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( uwFolderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True # TODO: Shouldn't be required ???
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'The unfoldingWord® Greek New Testament is based on the Bunning Heuristic Prototype Greek New Testament, from https://greekcntr.org/, which is licensed as CC BY-SA 4.0.',
                                'Source': 'https://unfoldingWord.Bible/ugnt/',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'Greek',
                                'ISOLanguageCode': 'grk',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_UNFOLDING_WORD_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='ULT'):
            abbreviation, name = 'ULT', 'unfoldingWord® Literal Text'
            uwFolderpath = BIBLES_FOLDERPATH.joinpath( 'English translations/unfoldingWordVersions/en_ult/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( uwFolderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( uwFolderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'An open-licensed update of the ASV, intended to provide a ‘form-centric’ understanding of the Bible. It increases the translator’s understanding of the lexical and grammatical composition of the underlying text by adhering closely to the word order and structure of the originals.',
                                'Source': 'https://unfoldingWord.Bible/ult/',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'English',
                                'ISOLanguageCode': 'eng',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_UNFOLDING_WORD_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='UST'):
            abbreviation, name = 'UST', 'unfoldingWord® Simplified Text'
            uwFolderpath = BIBLES_FOLDERPATH.joinpath( 'English translations/unfoldingWordVersions/en_ust/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( uwFolderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( uwFolderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'An open-licensed translation, intended to provide a ‘functional’ understanding of the Bible. It increases the translator’s understanding of the text by translating theological terms as descriptive phrases.',
                                'Source': 'https://unfoldingWord.Bible/ust/',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'English',
                                'ISOLanguageCode': 'eng',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )

### DOOR43 (but NOT unfoldingWord's own resources)
    if PROCESS_DOOR43_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE: # Door43 (non-unfoldingWord) versions
        if (1 or PROCESS_ALL_FLAG or PROCESS_DOOR43_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='HI-IRV'):
            abbreviation, name = 'HI-IRV', 'हिन्दी (Hindi)'
            door43Folderpath = DOOR43_SOURCE_FOLDERPATH.joinpath( 'hi_irv/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating Door43 {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( door43Folderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( door43Folderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True # TODO: Shouldn't be required ???
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': ' Hindi: Indian Revised Version (IRV) Hindi - 2020',
                                'Source': 'https://git.door43.org/Door43-Catalog/hi_irv',
                                'CopyrightNotice': 'Copyright © 2020 by Bridge Connectivity Solutions Pvt. Ltd.',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'Hindi',
                                'ISOLanguageCode': 'hi',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_DOOR43_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='TA-IRV'):
            abbreviation, name = 'TA-IRV', 'இண்டியன் ரிவைஸ்டு வெர்ஸன் (IRV) - தமிழ்'
            door43Folderpath = DOOR43_SOURCE_FOLDERPATH.joinpath( 'ta_irv/' )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating Door43 {} from internet…".format( abbreviation ) )
            repo_changed = runGitPull( door43Folderpath ) # Make sure we have the latest version
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( door43Folderpath, givenName=name, givenAbbreviation=abbreviation )
                thisBible.uWencoded = True # TODO: Shouldn't be required ???
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': ' Tamil: Indian Revised Version (IRV) Tamil - 2019',
                                'Source': 'https://git.door43.org/Door43-Catalog/ta_irv',
                                'CopyrightNotice': 'Copyright © 2019 by Bridge Connectivity Solutions Pvt. Ltd.',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'Tamil',
                                'ISOLanguageCode': 'ta',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        # if 1 or PROCESS_ALL_FLAG:
        #     abbreviation, name = 'UEB', 'Unlocked English Bible'
        #     door43Folderpath = BIBLES_FOLDERPATH.joinpath( 'English translations/Door43Versions/UEB/en_ueb/' )
        #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating Door43 {} from internet…".format( abbreviation ) )
        #     repo_changed = runGitPull( door43Folderpath ) # Make sure we have the latest version
        #     if repo_changed or not PROCESS_CHANGES_ONLY:
        #         thisBible = USFMBible( door43Folderpath, givenName=name, givenAbbreviation=abbreviation )
        #         metadataDict = {
        #                         'Abbreviation': abbreviation,
        #                         'WorkName': name,
        #                         'About': 'An open-licensed update of the ASV, in modern English. It provides speakers of English with a faithful, unrestricted, and understandable version of the Bible.',
        #                         'Source': 'https://unfoldingWord.Bible/ueb/',
        #                         'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
        #                         'LanguageName': 'English',
        #                         'ISOLanguageCode': 'eng',
        #                         }
        #         makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        #if 1 or PROCESS_ALL_FLAG:
            #abbreviation, name = 'UDB', 'Unlocked Dynamic Bible (obsolete)'
            #door43Folderpath = BIBLES_FOLDERPATH.joinpath( 'English translations/Door43Versions/UDB/en_udb/' )
            #vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating Door43 {} from internet…".format( abbreviation ) )
            #repo_changed = runGitPull( door43Folderpath ) # Make sure we have the latest version
            #if repo_changed or not PROCESS_CHANGES_ONLY:
                #thisBible = USFMBible( door43Folderpath, givenName=name, givenAbbreviation=abbreviation )
                #metadataDict = {
                                #'Abbreviation': abbreviation,
                                #'WorkName': name,
                                #'About': 'An open-licensed translation, intended to provide a ‘functional’ understanding of the Bible. It increases the translator’s understanding of the text by translating theological terms as descriptive phrases.',
                                #'Source': 'https://unfoldingWord.Bible/udb/',
                                #'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                #'LanguageName': 'English',
                                #'ISOLanguageCode': 'eng',
                                #}
                #makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        #if 1 or PROCESS_ALL_FLAG:
            #abbreviation, name = 'ULB', 'Unlocked Literal Bible (obsolete)'
            #door43Folderpath = BIBLES_FOLDERPATH.joinpath( 'English translations/Door43Versions/ULB/en_ulb/' )
            #vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating Door43 {} from internet…".format( abbreviation ) )
            #repo_changed = runGitPull( door43Folderpath ) # Make sure we have the latest version
            #if repo_changed or not PROCESS_CHANGES_ONLY:
                #thisBible = USFMBible( door43Folderpath, givenName=name, givenAbbreviation=abbreviation )
                #metadataDict = {
                                #'Abbreviation': abbreviation,
                                #'WorkName': name,
                                #'About': 'An open-licensed update of the ASV, intended to provide a ‘form-centric’ understanding of the Bible. It increases the translator’s understanding of the lexical and grammatical composition of the underlying text by adhering closely to the word order and structure of the originals.',
                                #'Source': 'https://unfoldingWord.Bible/ulb/',
                                #'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                #'LanguageName': 'English',
                                #'ISOLanguageCode': 'eng',
                                #}
                #makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )


### Open.Bible / Biblica
    if PROCESS_OPEN_BIBLE_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE: # Open.Bible versions
        if (1 or PROCESS_ALL_FLAG or PROCESS_OPEN_BIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='ELBBK'):
            abbreviation, name = 'ELBBK', 'Elberfelder Übersetzung (Version von bibelkommentare.de)'
            obFolderpath = OPEN_BIBLE_SOURCE_FOLDERPATH.joinpath( 'Elberfelder/f492a38d0e52db0f-rev4/release/USX_1/' )
            # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            # repo_changed = runGitPull( obFolderpath ) # Make sure we have the latest version
            repo_changed = False
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( obFolderpath, givenName=name, givenAbbreviation=abbreviation )
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'Linguistically revised text of the Unrevised Elberfelder Translation with footnotes',
                                'Source': 'https://open.bible/resources/german_standard-verbreitung-text-bible/',
                                'CopyrightNotice': '© 2019 by Verbreitung des christlichen Glaubens e.V.',
                                'Licence': 'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)',
                                'LanguageName': 'German',
                                'ISOLanguageCode': 'ge',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        # if 0 or PROCESS_ALL_FLAG:
        #     abbreviation, name = 'TAM-IRV', 'இண்டியன் ரிவைஸ்டு வெர்ஸன் (IRV) - தமிழ்'
        #     obFolderpath = OPEN_BIBLE_SOURCE_FOLDERPATH.joinpath( 'IRV/03a021185023710b-rev3/release/USX_1/' )
        #     # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
        #     # repo_changed = runGitPull( obFolderpath ) # Make sure we have the latest version
        #     repo_changed = False
        #     if repo_changed or not PROCESS_CHANGES_ONLY:
        #         thisBible = USFMBible( obFolderpath, givenName=name, givenAbbreviation=abbreviation )
        #         metadataDict = {
        #                         'Abbreviation': abbreviation,
        #                         'WorkName': name,
        #                         'About': ' Tamil: Indian Revised Version (IRV) Tamil - 2019',
        #                         'Source': 'https://open.bible/resources/tamil-bridge-text-bible/',
        #                         'CopyrightNotice': 'Copyright © 2019 by Bridge Connectivity Solutions Pvt. Ltd.',
        #                         'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
        #                         'LanguageName': 'Tamil',
        #                         'ISOLanguageCode': 'tam',
        #                         }
        #         makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_OPEN_BIBLE_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='KCV'):
            abbreviation, name = 'KCV', 'Biblica® Open Kiswahili Contemporary Version'
            obFolderpath = OPEN_BIBLE_SOURCE_FOLDERPATH.joinpath( 'swONEN14_USFM/' )
            # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nUpdating unfoldingWord® {} from internet…".format( abbreviation ) )
            # repo_changed = runGitPull( obFolderpath ) # Make sure we have the latest version
            repo_changed = False
            if repo_changed or not PROCESS_CHANGES_ONLY:
                thisBible = USFMBible( obFolderpath, givenName=name, givenAbbreviation=abbreviation )
                metadataDict = {
                                'Abbreviation': abbreviation,
                                'WorkName': name,
                                'About': 'Swahili: Biblica® Toleo Wazi la Neno: Biblia Takatifu™ (Bible) 2015',
                                'Source': 'https://open.bible/resources/swahili-biblica-text-bible/',
                                'CopyrightNotice': 'Copyright © 1984, 1989, 2009, 2015 by Biblica, Inc.',
                                'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                                'LanguageName': 'Kiswahili',
                                'ISOLanguageCode': 'sw',
                                }
                makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )


### OTHER / VARIOUS
    if PROCESS_OTHERS_FLAG or PROCESS_ALL_FLAG or PROCESS_ONE: # Other various versions
        if (1 or PROCESS_ALL_FLAG or PROCESS_OTHERS_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='FBV'):
            abbreviation, name = 'FBV', 'Free Bible Version (NT) 2.1.1'
            thisBible = USFMBible( BIBLES_FOLDERPATH.joinpath( 'English translations/Free Bible/USFM/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The translation is directly from the standard Nestle-Aland Greek text. Its intent is to be as faithful as possible to the original meaning without being awkward or misleading. The style is contemporary English, avoiding slang or colloquialisms, speaking to our modern society in a way people will understand.',
                            'Source': 'http://FreeBibleVersion.org/',
                            'author': 'Dr. Jonathan Gallagher',
                            'Licence': 'This work is licensed under a Creative Commons Attribution-NoDerivs 3.0 Unported License.',
                            'LanguageName': 'English',
                            'ISOLanguageCode': 'eng',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_OTHERS_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='SpaRV'):
            abbreviation, name = 'SpaRV', 'Reina-Valera 1865 Spanish translation'
            thisBible = USFMBible( BIBLES_FOLDERPATH.joinpath( 'Spanish translations/RV1865 USFM/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The translation is the Public Domain Reina-Valera 1865 Spanish translation.',
                            'Source': 'https://www.Valera1865.org/',
                            'Licence': 'This work is licensed as Creative Commons CC0 Public Domain.',
                            'LanguageName': 'Spanish',
                            'ISOLanguageCode': 'spa',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
        if (1 or PROCESS_ALL_FLAG or PROCESS_OTHERS_FLAG) and (not PROCESS_ONE or PROCESS_ONE=='MBTV'):
            abbreviation, name = 'MBTV', 'Matigsalug Bible (2021)'
            thisBible = PTX8Bible( Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/MBTV/' ),
                            givenName=name, givenAbbreviation=abbreviation )
            metadataDict = {
                            'Abbreviation': abbreviation,
                            'WorkName': name,
                            'About': 'The complete Matigsalug Bible from the southern Philippines.',
                            'Source': 'https://SUMALCA.info/Resources/Pages/Bible/index.htm',
                            'CopyrightNotice': 'Copyright © 2010-2021 Sinuda United Matigsalug Christian Association (SUMALCA), Inc.',
                            'Licence': 'Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)',
                            'LanguageName': 'Matigsalug',
                            'ISOLanguageCode': 'mbt',
                            }
            makeIt( abbreviation, thisBible, metadataDict, outputFolderpath, submit2BDB=submit2BDB )
#end of CreateDistributableResources.runCreateAll



def briefDemo() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS
        but don't save them in the normal output folder.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if not os.path.exists( TEST_OUTPUT_FOLDERPATH ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Creating folder {}…").format( TEST_OUTPUT_FOLDERPATH ) )
        os.makedirs( TEST_OUTPUT_FOLDERPATH )

    global PROCESS_ALL_FLAG, PROCESS_WLC_FLAG, PROCESS_UNFOLDING_WORD_FLAG, PROCESS_DOOR43_FLAG, PROCESS_OPEN_BIBLE_FLAG, PROCESS_EBIBLE_FLAG, PROCESS_OTHERS_FLAG
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Setting only PROCESS_DOOR43_FLAG to True")
    PROCESS_ALL_FLAG = PROCESS_WLC_FLAG = PROCESS_OTHERS_FLAG = PROCESS_EBIBLE_FLAG = PROCESS_OPEN_BIBLE_FLAG = False
    PROCESS_UNFOLDING_WORD_FLAG = False
    PROCESS_DOOR43_FLAG = True

    runCreateAll( TEST_OUTPUT_FOLDERPATH, submit2BDB=False )
# end of CreateDistributableResources.briefDemo

def fullDemo() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS
        but don't save them in the normal output folder.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if not os.path.exists( TEST_OUTPUT_FOLDERPATH ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Creating folder {}…".format( TEST_OUTPUT_FOLDERPATH ) )
        os.makedirs( TEST_OUTPUT_FOLDERPATH )

    global PROCESS_ALL_FLAG
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Setting PROCESS_ALL_FLAG to True")
    PROCESS_ALL_FLAG = True

    runCreateAll( TEST_OUTPUT_FOLDERPATH, submit2BDB=False )
# end of CreateDistributableResources.fullDemo


def main() -> None:
    """
    Create freely-licenced resources which can be distributed with the BOS.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if not os.path.exists( WRITEABLE_DISTRIBUTABLE_RESOURCES_FOLDERPATH ):
        #vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Creating folder {}…".format( WRITEABLE_DISTRIBUTABLE_RESOURCES_FOLDERPATH ) )
        os.makedirs( WRITEABLE_DISTRIBUTABLE_RESOURCES_FOLDERPATH )
        # halt # This folder should already exist

    runCreateAll( WRITEABLE_DISTRIBUTABLE_RESOURCES_FOLDERPATH, submit2BDB=BibleOrgSysGlobals.commandLineArguments.export )
# end of CreateDistributableResources.main

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of CreateDistributableResources.py
