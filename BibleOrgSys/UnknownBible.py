#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# UnknownBible.py
#
# Module handling a unknown Bible object
#
# Copyright (C) 2013-2022 Robert Hunt
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
Module handling an unknown Bible object.

Given a folder name, analyses the files in it
    and tries to determine what type of Bible it probably contains (if any).

Currently aware of the following Bible types:
    USFM
    Unbound Bible (table based), theWord (line based), MySword (SQLite based), e-Sword (SQLite based)
    OSIS, USX, USFX, OpenSong, Zefania, Haggai, VerseView (all XML)
    Digital Bible Library (DB) which is USX (XML) plus XML metadata
    Scripture Burrito which is JSON metadata plus USFM or USX
    Sword modules (binary).
"""
import logging
import os.path
from pathlib import Path

import bible_organisational_system

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Formats.ESFMBible import ESFMBibleFileCheck
from BibleOrgSys.Formats.PTX8Bible import PTX8BibleFileCheck
from BibleOrgSys.Formats.USFMBible import USFMBibleFileCheck
from BibleOrgSys.Formats.ScriptureBurritoBible import ScriptureBurritoBibleFileCheck
from BibleOrgSys.Formats.DBLBible import DBLBibleFileCheck
from BibleOrgSys.Formats.USXXMLBible import USXXMLBibleFileCheck
from BibleOrgSys.Formats.USFXXMLBible import USFXXMLBibleFileCheck
from BibleOrgSys.Formats.OpenSongXMLBible import OpenSongXMLBibleFileCheck
from BibleOrgSys.Formats.OSISXMLBible import OSISXMLBibleFileCheck
from BibleOrgSys.Formats.ZefaniaXMLBible import ZefaniaXMLBibleFileCheck
from BibleOrgSys.Formats.HaggaiXMLBible import HaggaiXMLBibleFileCheck
from BibleOrgSys.Formats.VerseViewXMLBible import VerseViewXMLBibleFileCheck
from BibleOrgSys.Formats.UnboundBible import UnboundBibleFileCheck
from BibleOrgSys.Formats.DrupalBible import DrupalBibleFileCheck
from BibleOrgSys.Formats.YETBible import YETBibleFileCheck
from BibleOrgSys.Formats.theWordBible import theWordBibleFileCheck
from BibleOrgSys.Formats.MySwordBible import MySwordBibleFileCheck
from BibleOrgSys.Formats.ESwordBible import ESwordBibleFileCheck
from BibleOrgSys.Formats.ESwordCommentary import ESwordCommentaryFileCheck
from BibleOrgSys.Formats.MyBibleBible import MyBibleBibleFileCheck
from BibleOrgSys.Formats.PalmDBBible import PalmDBBibleFileCheck
from BibleOrgSys.Formats.GoBible import GoBibleFileCheck
from BibleOrgSys.Formats.PickledBible import PickledBibleFileCheck
from BibleOrgSys.Formats.PierceOnlineBible import PierceOnlineBibleFileCheck
from BibleOrgSys.Formats.EasyWorshipBible import EasyWorshipBibleFileCheck
from BibleOrgSys.Formats.SwordBible import SwordBibleFileCheck
from BibleOrgSys.Formats.CSVBible import CSVBibleFileCheck
from BibleOrgSys.Formats.ForgeForSwordSearcherBible import ForgeForSwordSearcherBibleFileCheck
from BibleOrgSys.Formats.VPLBible import VPLBibleFileCheck
#from BibleOrgSys.Formats.SwordResources import SwordInterface # What about these?


LAST_MODIFIED_DATE = '2022-04-22' # by RJH
SHORT_PROGRAM_NAME = "UnknownBible"
PROGRAM_NAME = "Unknown Bible object handler"
PROGRAM_VERSION = '0.38'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


logger = logging.getLogger(SHORT_PROGRAM_NAME)



class UnknownBible:
    """
    Class for handling an entire Bible.
    """

    def __init__( self, givenPathname:Path ) -> None:
        """
        Constructor: creates an empty Bible object.
        """
        if BibleOrgSysGlobals.debugFlag: assert givenPathname and isinstance( givenPathname, (str,Path) )
        self.givenFolderName = givenPathname # NOTE: givenPathname can actually be zip file for PickledBible

        # Check that the given folder is readable
        if not os.access( givenPathname, os.R_OK ):
            logger.critical( f"Given {givenPathname!r} pathname is unreadable" )
            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
            self.folderReadable = False
        else: self.folderReadable = True

        self.foundType = None
    # end of UnknownBible.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Unknown Bible object"
        result += ('\n' if result else '') + "  " + f"Folder: {self.givenFolderName}{'' if self.folderReadable else ' UNREADABLE'}"
        if self.foundType: result += ('\n' if result else '') + "  " + f"Found type: {self.foundType} "
        return result
    # end of UnknownBible.__str__


    def search( self, strictCheck=True, autoLoad=False, autoLoadAlways=False, autoLoadBooks=False ):
        """
        Search our folder to find what if any Bible versions can be found.
        Optimized version using Rust-based parallel detection.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"UnknownBible.search( {strictCheck}, {autoLoad}, {autoLoadAlways}, {autoLoadBooks} )" )

        if not self.folderReadable: return None
        if autoLoadAlways or autoLoadBooks: autoLoad = True

        # Use the optimized Rust detector
        try:
            detected = bible_organisational_system.detectBibles(str(self.givenFolderName), strictCheck)
        except Exception as e:
            logger.error(f"Error in Rust detectBibles: {e}")
            return None
        
        # Handle retry logic similar to original Python version
        if not detected and strictCheck and not BibleOrgSysGlobals.strictCheckingFlag:
            vPrint('Info', DEBUGGING_THIS_MODULE, "UnknownBible.search: retrying without strict checking criteria")
            detected = bible_organisational_system.detectBibles(str(self.givenFolderName), False)
        elif len(detected) > 1 and not strictCheck:
            vPrint('Info', DEBUGGING_THIS_MODULE, "UnknownBible.search: retrying with strict checking criteria")
            detected = bible_organisational_system.detectBibles(str(self.givenFolderName), True)

        totalBibleCount = len(detected)
        if totalBibleCount == 0:
            self.foundType = 'None found'
            return 'None found'

        # Group by format to match original logic expectations
        formats_found = {}
        for b in detected:
            formats_found[b.format] = formats_found.get(b.format, 0) + 1
        
        totalBibleTypes = len(formats_found)
        if totalBibleCount > 1:
            if totalBibleTypes == 1:
                format_name = list(formats_found.keys())[0]
                vPrint('Quiet', DEBUGGING_THIS_MODULE, f"UnknownBible.search: Multiple ({totalBibleCount}) {format_name} Bibles found")
                self.foundType = f"Multiple found: {format_name} Bibles"
            else:
                vPrint('Quiet', DEBUGGING_THIS_MODULE, f"UnknownBible.search: Multiple ({totalBibleCount}) Bibles found: {list(formats_found.keys())}")
                self.foundType = 'Many types found'
            
            if not autoLoadAlways:
                return self.foundType

        # If exactly one found (or autoLoadAlways is set), identify the one to load
        best_match = detected[0] # Just pick the first one if multiple
        self.foundType = best_match.format
        
        # Mapping to actual Python file checkers for loading
        CHECKERS = {
            'pickled Bible': PickledBibleFileCheck,
            'theWord Bible': theWordBibleFileCheck,
            'MySword Bible': MySwordBibleFileCheck,
            'e-Sword Bible': ESwordBibleFileCheck,
            'e-Sword Commentary': ESwordCommentaryFileCheck,
            'MyBible Bible': MyBibleBibleFileCheck,
            'PalmDB Bible': PalmDBBibleFileCheck,
            'GoBible Bible': GoBibleFileCheck,
            'Sword Bible': SwordBibleFileCheck,
            'Unbound Bible': UnboundBibleFileCheck,
            'Drupal Bible': DrupalBibleFileCheck,
            'YET Bible': YETBibleFileCheck,
            'ESFM Bible': ESFMBibleFileCheck,
            'PTX8 Bible': PTX8BibleFileCheck,
            'SB Bible': ScriptureBurritoBibleFileCheck,
            'USFM Bible': USFMBibleFileCheck,
            'DBL Bible': DBLBibleFileCheck,
            'USX XML Bible': USXXMLBibleFileCheck,
            'USFX XML Bible': USFXXMLBibleFileCheck,
            'OSIS XML Bible': OSISXMLBibleFileCheck,
            'OpenSong XML Bible': OpenSongXMLBibleFileCheck,
            'Zefania XML Bible': ZefaniaXMLBibleFileCheck,
            'Haggai XML Bible': HaggaiXMLBibleFileCheck,
            'VerseView XML Bible': VerseViewXMLBibleFileCheck,
            'CSV Bible': CSVBibleFileCheck,
            'Forge Bible': ForgeForSwordSearcherBibleFileCheck,
            'VPL Bible': VPLBibleFileCheck,
        }

        checker = CHECKERS.get(best_match.format)
        if checker:
            # We call the Python checker but it's only for the actual loading/init now
            # since we've already done the detection.
            return checker(best_match.path, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks)
        
        return self.foundType
    # end of UnknownBible.search
# end of class UnknownBible



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    import random

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Now demo the class
    if 0: # Just test one folder
        testFolder = 'Put your folder here/'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A1/ Trying (but not loading) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result1 = uB.search( autoLoad=False )
        result2 = uB.search( autoLoadBooks=True ) if result1 else None
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A1 result1 is: {result1}" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A1 result2 is: {result2}" )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( autoLoadAlways=False )
            result4 = uB.search( autoLoadAlways=True ) if result3 else None
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A1 result3 is: {result3}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A1 result4 is: {result4}" )

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A2/ (Strict as per BDB). Trying (but not loading) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result1 = uB.search( strictCheck=True, autoLoad=False )
        result2 = uB.search( strictCheck=True, autoLoadBooks=True ) if result1 else None
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A2 strict result1 is: {result1}" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A2 strict result2 is: {result2}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( strictCheck=True, autoLoadAlways=False )
            result4 = uB.search( strictCheck=True, autoLoadAlways=True ) if result3 else None
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A2 strict result3 is: {result3}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A2 strict result4 is: {result4}" )
            if result3 == 'Many types found':
                uB = UnknownBible( testFolder )
                result5 = uB.search( strictCheck=True, autoLoadAlways=False, autoLoadBooks=True )
                result6 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True ) if result5 else None
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A2 strict result5 is: {result5}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A2 strict result6 is: {result6}" )

        #from BibleOrgSys.Bible import Bible
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A3/ (Strict as per BDB). Trying {testFolder}…" )
        #uB = UnknownBible( testFolder )
        #result1 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A3 result1 is: {result1}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        #if isinstance( result1, Bible ):
            #thisBible = result1
            #thisBible.check()
            #errorDictionary = thisBible.getCheckResults()


    BiblesFolderpath = Path( '/srv/Bibles/' )
    testFolders = ( os.path.join( os.path.expanduser('~'), 'Logs/'), # Shouldn't have any Bibles here
                    BiblesFolderpath.joinpath( 'Biola Unbound modules/' ),
                    BiblesFolderpath.joinpath( 'EasyWorship Bibles/' ),
                    BiblesFolderpath.joinpath( 'OpenSong Bibles/' ),
                    BiblesFolderpath.joinpath( 'Zefania modules/' ),
                    BiblesFolderpath.joinpath( 'YET modules/' ),
                    BiblesFolderpath.joinpath( 'GoBible modules/' ),
                    BiblesFolderpath.joinpath( 'MyBible modules/' ),
                    Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ),
                    Path( '/srv/AutoProcesses/Processed/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-ASV/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'HaggaiTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MyBibleTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MySwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'YETTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PDBTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DrupalTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH, # Up a level
                    )
    if 1: # Just find the files
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible B/ Trying (but not loading) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoad=False )
        #result2 = uB.search( autoLoad=True ) if result1 else None
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Just load the Bible objects (only if exactly one found)
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible C/ Single loading (but not books) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoad=True )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Fully load the Bible objects (only if exactly one found)
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible D/ Single loading (incl. books) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoadBooks=True )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Always load the Bible objects
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible E/ Always loading (but not books) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoadAlways=True )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Always fully load the Bible objects
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible F/ Always loading (incl. books) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 0: # Load, check, and export the files
        testFolder = random.choice( testFolders )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible G/ Processing {testFolder}…" )
        uB = UnknownBible( testFolder )
        result = uB.search( autoLoad=True )
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Results are: {result1} and {result2}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        if result:
            result.check()
            results = result.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Results are: {results}" )
# end of UnknownBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Now demo the class
    if 1: # Just test one folder
        testFolder = 'Put your folder here/'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A1/ Trying (but not loading) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result1 = uB.search( autoLoad=False )
        result2 = uB.search( autoLoadBooks=True ) if result1 else None
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A1 result1 is: {result1}" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A1 result2 is: {result2}" )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( autoLoadAlways=False )
            result4 = uB.search( autoLoadAlways=True ) if result3 else None
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A1 result3 is: {result3}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A1 result4 is: {result4}" )

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A2/ (Strict as per BDB). Trying (but not loading) {testFolder}…" )
        uB = UnknownBible( testFolder )
        result1 = uB.search( strictCheck=True, autoLoad=False )
        result2 = uB.search( strictCheck=True, autoLoadBooks=True ) if result1 else None
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A2 strict result1 is: {result1}" )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  A2 strict result2 is: {result2}" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( strictCheck=True, autoLoadAlways=False )
            result4 = uB.search( strictCheck=True, autoLoadAlways=True ) if result3 else None
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A2 strict result3 is: {result3}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  A2 strict result4 is: {result4}" )
            if result3 == 'Many types found':
                uB = UnknownBible( testFolder )
                result5 = uB.search( strictCheck=True, autoLoadAlways=False, autoLoadBooks=True )
                result6 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True ) if result5 else None
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A2 strict result5 is: {result5}" )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A2 strict result6 is: {result6}" )

        #from BibleOrgSys.Bible import Bible
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible A3/ (Strict as per BDB). Trying {testFolder}…" )
        #uB = UnknownBible( testFolder )
        #result1 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  A3 result1 is: {result1}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
        #if isinstance( result1, Bible ):
            #thisBible = result1
            #thisBible.check()
            #errorDictionary = thisBible.getCheckResults()


    BiblesFolderpath = Path( '/srv/Bibles/' )
    testFolders = ( os.path.join( os.path.expanduser('~'), 'Logs/'), # Shouldn't have any Bibles here
                    BiblesFolderpath.joinpath( 'Biola Unbound modules/' ),
                    BiblesFolderpath.joinpath( 'EasyWorship Bibles/' ),
                    BiblesFolderpath.joinpath( 'OpenSong Bibles/' ),
                    BiblesFolderpath.joinpath( 'Zefania modules/' ),
                    BiblesFolderpath.joinpath( 'YET modules/' ),
                    BiblesFolderpath.joinpath( 'GoBible modules/' ),
                    BiblesFolderpath.joinpath( 'MyBible modules/' ),
                    Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ),
                    Path( '/srv/AutoProcesses/Processed/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DBLTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-ASV/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFX-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'HaggaiTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MyBibleTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'MySwordTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'YETTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PDBTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PierceOnlineBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EasyWorshipBible/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'DrupalTest/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VPLTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH, # Up a level
                    )
    if 1: # Just find the files
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible B{j+1}/ Trying (but not loading) {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=False )
            #result2 = uB.search( autoLoad=True ) if result1 else None
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Just load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible C{j+1}/ Single loading (but not books) {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Fully load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible D{j+1}/ Single loading (incl. books) {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadBooks=True )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Always load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible E{j+1}/ Always loading (but not books) {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 1: # Always fully load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible F{j+1}/ Always loading (incl. books) {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Result is: {result}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )

    if 0: # Load, check, and export the files
        for j, testFolder in enumerate( testFolders ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nUnknownBible G{j+1}/ Processing {testFolder}…" )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            #dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Results are: {result1} and {result2}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, uB )
            if result:
                result.check()
                results = result.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Results are: {results}" )
# end of UnknownBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of UnknownBible.py
