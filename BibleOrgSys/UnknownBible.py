#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# UnknownBible.py
#
# Module handling a unknown Bible object
#
# Copyright (C) 2013-2019 Robert Hunt
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
Module handling an unknown Bible object.

Given a folder name, analyses the files in it
    and tries to determine what type of Bible it probably contains (if any).

Currently aware of the following Bible types:
    USFM
    Unbound Bible (table based), theWord (line based), MySword (SQLite based), e-Sword (SQLite based)
    OSIS, USX, USFX, OpenSong, Zefania, Haggai, VerseView (all XML)
    Digital Bible Library (DB) which is USX (XML) plus XML metadata
    Sword modules (binary).
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-23' # by RJH
SHORT_PROGRAM_NAME = "UnknownBible"
PROGRAM_NAME = "Unknown Bible object handler"
PROGRAM_VERSION = '0.35'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os.path
from pathlib import Path

if __name__ == '__main__':
    import sys
    aboveFolderPath = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
    if aboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.ESFMBible import ESFMBibleFileCheck
from BibleOrgSys.Formats.PTX8Bible import PTX8BibleFileCheck
from BibleOrgSys.Formats.PTX7Bible import PTX7BibleFileCheck
from BibleOrgSys.Formats.USFMBible import USFMBibleFileCheck
from BibleOrgSys.Formats.USFM2Bible import USFM2BibleFileCheck
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
            logger.critical( _("Given {!r} pathname is unreadable").format( givenPathname ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            self.folderReadable = False
        else: self.folderReadable = True

        self.foundType = None
    # end of UnknownBible.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("Unknown Bible object")
        result += ('\n' if result else '') + "  " + _("Folder: {}{}").format( self.givenFolderName, '' if self.folderReadable else ' UNREADABLE' )
        if self.foundType: result += ('\n' if result else '') + "  " + _("Found type: {} ").format( self.foundType )
        return result
    # end of UnknownBible.__str__


    def search( self, strictCheck=True, autoLoad=False, autoLoadAlways=False, autoLoadBooks=False ):
        """
        Search our folder to found what if any Bible versions can be found.
            These searches are best done in a certain order to avoid false detections.

        If autoLoad is set and exactly one Bible is found, it will load it.
        If autoLoadAlways is set and one or more Bibles are found, it will load one.

        returns either a string:
            'None found'
            "Multiple found: {} Bibles"
            'Many types found'
        or
            '{} Bible', e.g., 'USFM Bible'
        or
            a loaded Bible
        """
        if debuggingThisModule:
            print( "UnknownBible.search( {}, {}, {}, {} )".format( strictCheck, autoLoad, autoLoadAlways, autoLoadBooks ) )

        if not self.folderReadable: return None
        if autoLoadAlways or autoLoadBooks: autoLoad = True

        def recheckStrict( folderName, oppositeStrictFlag ):
            """
            If we didn't check with the strict flag the first time,
                try it again with the strict mode set.
            OR maybe vice versa!

            Returns the three counters.
            """
            if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                print( "UnknownBible.recheckStrict( {}, {} )".format( folderName, oppositeStrictFlag ) )

            totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound = 0, 0, []

            # Search for pickled Bibles -- can be given a folder, or a zip file name
            PickledBibleStrictCount = PickledBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
            if PickledBibleStrictCount:
                totalBibleStrictCount += PickledBibleStrictCount
                totalBibleStrictTypes += 1
                typesStrictlyFound.append( 'Pickled:' + str(PickledBibleStrictCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "PickledBible.recheckStrict: PickledBibleStrictCount", PickledBibleStrictCount )

            if os.path.isdir( self.givenFolderName ):
                # Search for theWord Bibles
                theWordBibleStrictCount = theWordBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if theWordBibleStrictCount:
                    totalBibleStrictCount += theWordBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'theWord:' + str(theWordBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "theWordBible.recheckStrict: theWordBibleStrictCount", theWordBibleStrictCount )

                # Search for MySword Bibles
                MySwordBibleStrictCount = MySwordBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if MySwordBibleStrictCount:
                    totalBibleStrictCount += MySwordBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'MySword:' + str(MySwordBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "MySwordBible.recheckStrict: MySwordBibleStrictCount", MySwordBibleStrictCount )

                # Search for e-Sword Bibles and commentaries
                ESwordBibleStrictCount = ESwordBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if ESwordBibleStrictCount:
                    totalBibleStrictCount += ESwordBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'e-Sword-Bible:' + str(ESwordBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBible.recheckStrict: ESwordBibleStrictCount", ESwordBibleStrictCount )
                ESwordCommentaryStrictCount = ESwordCommentaryFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if ESwordCommentaryStrictCount:
                    totalBibleStrictCount += ESwordCommentaryStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'e-Sword-Commentary:' + str(ESwordCommentaryStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordCommentary.recheckStrict: ESwordCommentaryStrictCount", ESwordCommentaryStrictCount )

                # Search for MyBible Bibles
                MyBibleBibleStrictCount = MyBibleBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if MyBibleBibleStrictCount:
                    totalBibleStrictCount += MyBibleBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'MyBible:' + str(MyBibleBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBible.recheckStrict: MyBibleBibleStrictCount", MyBibleBibleStrictCount )

                # Search for PalmDB Bibles
                PDBBibleStrictCount = PalmDBBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if PDBBibleStrictCount:
                    totalBibleStrictCount += PDBBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'PalmDB:' + str(PDBBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: PDBBibleStrictCount", PDBBibleStrictCount )

                # Search for GoBibles
                GoBibleStrictCount = GoBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if GoBibleStrictCount:
                    totalBibleStrictCount += GoBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'GoBible:' + str(GoBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: GoBibleStrictCount", GoBibleStrictCount )

                # Search for Online Bibles
                PierceOnlineBibleStrictCount = PierceOnlineBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if PierceOnlineBibleStrictCount:
                    totalBibleStrictCount += PierceOnlineBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'PierceOnline:' + str(PierceOnlineBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: PierceOnlineBibleStrictCount", PierceOnlineBibleStrictCount )

                # Search for EasyWorship Bibles
                EasyWorshipBibleStrictCount = EasyWorshipBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if EasyWorshipBibleStrictCount:
                    totalBibleStrictCount += EasyWorshipBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'EasyWorship:' + str(EasyWorshipBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: EasyWorshipBibleStrictCount", EasyWorshipBibleStrictCount )

                # Search for Sword Bibles
                SwordBibleStrictCount = SwordBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if SwordBibleStrictCount:
                    totalBibleStrictCount += SwordBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Sword:' + str(SwordBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: SwordBibleStrictCount", SwordBibleStrictCount )

                # Search for Unbound Bibles
                UnboundBibleStrictCount = UnboundBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if UnboundBibleStrictCount:
                    totalBibleStrictCount += UnboundBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Unbound:' + str(UnboundBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: UnboundBibleStrictCount", UnboundBibleStrictCount )

                # Search for Drupal Bibles
                DrupalBibleStrictCount = DrupalBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if DrupalBibleStrictCount:
                    totalBibleStrictCount += DrupalBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Drupal:' + str(DrupalBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: DrupalBibleStrictCount", DrupalBibleStrictCount )

                # Search for YET Bibles
                YETBibleStrictCount = YETBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if YETBibleStrictCount:
                    totalBibleStrictCount += YETBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'YET:' + str(YETBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: YETBibleStrictCount", YETBibleStrictCount )

                # Search for ESFM Bibles -- put BEFORE USFM
                ESFMBibleStrictCount = ESFMBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if ESFMBibleStrictCount:
                    totalBibleStrictCount += ESFMBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'ESFM:' + str(ESFMBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: ESFMBibleStrictCount", ESFMBibleStrictCount )

                # Search for Paratext (PTX) Bibles -- put BEFORE USFM
                PTX8BibleStrictCount = PTX8BibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if PTX8BibleStrictCount:
                    totalBibleStrictCount += PTX8BibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'PTX8:' + str(PTX8BibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: PTX8BibleStrictCount", PTX8BibleStrictCount )
                PTX7BibleStrictCount = PTX7BibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if PTX7BibleStrictCount:
                    totalBibleStrictCount += PTX7BibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'PTX7:' + str(PTX7BibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: PTX7BibleStrictCount", PTX7BibleStrictCount )

                # Search for USFM Bibles
                USFM2BibleStrictCount = USFM2BibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if USFM2BibleStrictCount:
                    totalBibleStrictCount += USFM2BibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'USFM:' + str(USFM2BibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: USFM2BibleStrictCount", USFM2BibleStrictCount )
                USFMBibleStrictCount = USFMBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if USFMBibleStrictCount:
                    totalBibleStrictCount += USFMBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'USFM:' + str(USFMBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: USFMBibleStrictCount", USFMBibleStrictCount )

                # Search for DBL Bibles -- put BEFORE USX
                DBLBibleStrictCount = DBLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if DBLBibleStrictCount:
                    totalBibleStrictCount += DBLBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'DBL:' + str(DBLBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: DBLBibleStrictCount", DBLBibleStrictCount )

                # Search for USX XML Bibles
                USXBibleStrictCount = USXXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if USXBibleStrictCount:
                    totalBibleStrictCount += USXBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'USX:' + str(USXBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: USXBibleStrictCount", USXBibleStrictCount )

                # Search for USFX XML Bibles
                USFXBibleStrictCount = USFXXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if USFXBibleStrictCount:
                    totalBibleStrictCount += USFXBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'USFX:' + str(USFXBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: USFXBibleStrictCount", USFXBibleStrictCount )

                # Search for OSIS XML Bibles
                OSISBibleStrictCount = OSISXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if OSISBibleStrictCount:
                    totalBibleStrictCount += OSISBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'OSIS:' + str(OSISBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: OSISBibleStrictCount", OSISBibleStrictCount )

                # Search for OpenSong XML Bibles
                OpenSongBibleStrictCount = OpenSongXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if OpenSongBibleStrictCount:
                    totalBibleStrictCount += OpenSongBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'OpenSong:' + str(OpenSongBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: OpenSongBibleStrictCount", OpenSongBibleStrictCount )

                # Search for Zefania XML Bibles
                ZefaniaBibleStrictCount = ZefaniaXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if ZefaniaBibleStrictCount:
                    totalBibleStrictCount += ZefaniaBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Zefania:' + str(ZefaniaBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: ZefaniaBibleStrictCount", ZefaniaBibleStrictCount )

                # Search for Haggai XML Bibles
                HaggaiBibleStrictCount = HaggaiXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if HaggaiBibleStrictCount:
                    totalBibleStrictCount += HaggaiBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Haggai:' + str(HaggaiBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: HaggaiBibleStrictCount", HaggaiBibleStrictCount )

                # Search for VerseView XML Bibles
                VerseViewBibleStrictCount = VerseViewXMLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if VerseViewBibleStrictCount:
                    totalBibleStrictCount += VerseViewBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'VerseView:' + str(VerseViewBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: VerseViewBibleStrictCount", VerseViewBibleStrictCount )

                # Search for CSV text Bibles
                CSVBibleStrictCount = CSVBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if CSVBibleStrictCount:
                    totalBibleStrictCount += CSVBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'CSV:' + str(CSVBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: CSVBibleStrictCount", CSVBibleStrictCount )

                # Search for Forge for SwordSearcher VPL text Bibles
                F4SSBibleStrictCount = ForgeForSwordSearcherBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if F4SSBibleStrictCount:
                    totalBibleStrictCount += F4SSBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'Forge:' + str(F4SSBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: F4SSBibleStrictCount", F4SSBibleStrictCount )

                # Search for VPL text Bibles
                VPLBibleStrictCount = VPLBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
                if VPLBibleStrictCount:
                    totalBibleStrictCount += VPLBibleStrictCount
                    totalBibleStrictTypes += 1
                    typesStrictlyFound.append( 'VPL:' + str(VPLBibleStrictCount) )
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: VPLBibleStrictCount", VPLBibleStrictCount )
            else:
                theWordBibleStrictCount = MySwordBibleStrictCount = ESwordBibleStrictCount = ESwordCommentaryStrictCount = 0
                MyBibleBibleStrictCount = PDBBibleStrictCount = PierceOnlineBibleStrictCount = EasyWorshipBibleStrictCount = 0
                SwordBibleStrictCount = UnboundBibleStrictCount = DrupalBibleStrictCount = YETBibleStrictCount = 0
                ESFMBibleStrictCount = PTX8BibleStrictCount = PTX7BibleStrictCount = USFM2BibleStrictCount = USFMBibleStrictCount = 0
                DBLBibleStrictCount = USXBibleStrictCount = USFXBibleStrictCount = OSISBibleStrictCount = 0
                OpenSongBibleStrictCount = ZefaniaBibleStrictCount = HaggaiBibleStrictCount = VerseViewBibleStrictCount = 0
                GoBibleStrictCount = CSVBibleStrictCount = F4SSBibleStrictCount = VPLBibleStrictCount = 0

            return totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound
        # end of recheckStrict


        # Main code for UnknownBible.search()
        # We first do a normal (non-strict) check (unless strict was requested by the caller)
        totalBibleCount, totalBibleTypes, typesFound = 0, 0, []

        # Search for pickled Bibles -- can be given a folder, or a zip file name
        PickledBibleCount = PickledBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if PickledBibleCount:
            totalBibleCount += PickledBibleCount
            totalBibleTypes += 1
            typesFound.append( 'Pickled:' + str(PickledBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "PickledBible.search: PickledBibleCount", PickledBibleCount )

        if os.path.isdir( self.givenFolderName ):
            # Search for theWord Bibles
            theWordBibleCount = theWordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if theWordBibleCount:
                totalBibleCount += theWordBibleCount
                totalBibleTypes += 1
                typesFound.append( 'theWord:' + str(theWordBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "theWordBible.search: theWordBibleCount", theWordBibleCount )

            # Search for MySword Bibles
            MySwordBibleCount = MySwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if MySwordBibleCount:
                totalBibleCount += MySwordBibleCount
                totalBibleTypes += 1
                typesFound.append( 'MySword:' + str(MySwordBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "MySwordBible.search: MySwordBibleCount", MySwordBibleCount )

            # Search for e-Sword Bibles and Commentaries
            ESwordBibleCount = ESwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if ESwordBibleCount:
                totalBibleCount += ESwordBibleCount
                totalBibleTypes += 1
                typesFound.append( 'e-Sword-Bible:' + str(ESwordBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBible.search: ESwordBibleCount", ESwordBibleCount )
            ESwordCommentaryCount = ESwordCommentaryFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if ESwordCommentaryCount:
                totalBibleCount += ESwordCommentaryCount
                totalBibleTypes += 1
                typesFound.append( 'e-Sword-Commentary:' + str(ESwordCommentaryCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordCommentary.search: ESwordCommentaryCount", ESwordCommentaryCount )

            # Search for MyBible Bibles
            MyBibleBibleCount = MyBibleBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if MyBibleBibleCount:
                totalBibleCount += MyBibleBibleCount
                totalBibleTypes += 1
                typesFound.append( 'MyBible:' + str(MyBibleBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBible.search: MyBibleBibleCount", MyBibleBibleCount )

            # Search for PalmDB Bibles
            PDBBibleCount = PalmDBBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if PDBBibleCount:
                totalBibleCount += PDBBibleCount
                totalBibleTypes += 1
                typesFound.append( 'PalmDB:' + str(PDBBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: PDBBibleCount", PDBBibleCount )

            # Search for GoBibles
            GoBibleCount = GoBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if GoBibleCount:
                totalBibleCount += GoBibleCount
                totalBibleTypes += 1
                typesFound.append( 'GoBible:' + str(GoBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: GoBibleCount", GoBibleCount )

            # Search for Online Bibles
            PierceOnlineBibleCount = PierceOnlineBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if PierceOnlineBibleCount:
                totalBibleCount += PierceOnlineBibleCount
                totalBibleTypes += 1
                typesFound.append( 'PierceOnline:' + str(PierceOnlineBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: PierceOnlineBibleCount", PierceOnlineBibleCount )

            # Search for EasyWorship Bibles
            EasyWorshipBibleCount = EasyWorshipBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if EasyWorshipBibleCount:
                totalBibleCount += EasyWorshipBibleCount
                totalBibleTypes += 1
                typesFound.append( 'EasyWorship:' + str(EasyWorshipBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: EasyWorshipBibleCount", EasyWorshipBibleCount )

            # Search for Sword Bibles
            SwordBibleCount = SwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if SwordBibleCount:
                totalBibleCount += SwordBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Sword:' + str(SwordBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: SwordBibleCount", SwordBibleCount )

            # Search for Unbound Bibles
            UnboundBibleCount = UnboundBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if UnboundBibleCount:
                totalBibleCount += UnboundBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Unbound:' + str(UnboundBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: UnboundBibleCount", UnboundBibleCount )

            # Search for Drupal Bibles
            DrupalBibleCount = DrupalBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if DrupalBibleCount:
                totalBibleCount += DrupalBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Drupal:' + str(DrupalBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: DrupalBibleCount", DrupalBibleCount )

            # Search for YET Bibles
            YETBibleCount = YETBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if YETBibleCount:
                totalBibleCount += YETBibleCount
                totalBibleTypes += 1
                typesFound.append( 'YET:' + str(YETBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: YETBibleCount", YETBibleCount )

            # Search for ESFM Bibles -- put BEFORE USFM
            ESFMBibleCount = ESFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if ESFMBibleCount:
                totalBibleCount += ESFMBibleCount
                totalBibleTypes += 1
                typesFound.append( 'ESFM:' + str(ESFMBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: ESFMBibleCount", ESFMBibleCount )

            # Search for Paratext (PTX) Bibles -- put BEFORE USFM
            PTX8BibleCount = PTX8BibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if PTX8BibleCount:
                totalBibleCount += PTX8BibleCount
                totalBibleTypes += 1
                typesFound.append( 'PTX8:' + str(PTX8BibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: PTX8BibleCount", PTX8BibleCount )
            PTX7BibleCount = PTX7BibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if PTX7BibleCount:
                totalBibleCount += PTX7BibleCount
                totalBibleTypes += 1
                typesFound.append( 'PTX7:' + str(PTX7BibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: PTX7BibleCount", PTX7BibleCount )

            # Search for USFM Bibles
            USFM2BibleCount = USFM2BibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if USFM2BibleCount:
                totalBibleCount += USFM2BibleCount
                totalBibleTypes += 1
                typesFound.append( 'USFM2:' + str(USFM2BibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: USFM2BibleCount", USFM2BibleCount )
            USFMBibleCount = USFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if USFMBibleCount:
                totalBibleCount += USFMBibleCount
                totalBibleTypes += 1
                typesFound.append( 'USFM:' + str(USFMBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: USFMBibleCount", USFMBibleCount )

            # Search for DBL Bibles -- put BEFORE USX
            DBLBibleCount = DBLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if DBLBibleCount:
                totalBibleCount += DBLBibleCount
                totalBibleTypes += 1
                typesFound.append( 'DBL:' + str(DBLBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: DBLBibleCount", DBLBibleCount )

            # Search for USX XML Bibles
            USXBibleCount = USXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if USXBibleCount:
                totalBibleCount += USXBibleCount
                totalBibleTypes += 1
                typesFound.append( 'USX:' + str(USXBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: USXBibleCount", USXBibleCount )

            # Search for USFX XML Bibles
            USFXBibleCount = USFXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if USFXBibleCount:
                totalBibleCount += USFXBibleCount
                totalBibleTypes += 1
                typesFound.append( 'USFX:' + str(USFXBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: USFXBibleCount", USFXBibleCount )

            # Search for OSIS XML Bibles
            OSISBibleCount = OSISXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if OSISBibleCount:
                totalBibleCount += OSISBibleCount
                totalBibleTypes += 1
                typesFound.append( 'OSIS:' + str(OSISBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: OSISBibleCount", OSISBibleCount )

            # Search for OpenSong XML Bibles
            OpenSongBibleCount = OpenSongXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if OpenSongBibleCount:
                totalBibleCount += OpenSongBibleCount
                totalBibleTypes += 1
                typesFound.append( 'OpenSong:' + str(OpenSongBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: OpenSongBibleCount", OpenSongBibleCount )

            # Search for Zefania XML Bibles
            ZefaniaBibleCount = ZefaniaXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if ZefaniaBibleCount:
                totalBibleCount += ZefaniaBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Zefania:' + str(ZefaniaBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: ZefaniaBibleCount", ZefaniaBibleCount )

            # Search for Haggai XML Bibles
            HaggaiBibleCount = HaggaiXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if HaggaiBibleCount:
                totalBibleCount += HaggaiBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Haggai:' + str(HaggaiBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: HaggaiBibleCount", HaggaiBibleCount )

            # Search for VerseView XML Bibles
            VerseViewBibleCount = VerseViewXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if VerseViewBibleCount:
                totalBibleCount += VerseViewBibleCount
                totalBibleTypes += 1
                typesFound.append( 'VerseView:' + str(VerseViewBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: VerseViewBibleCount", VerseViewBibleCount )

            # Search for CSV text Bibles
            CSVBibleCount = CSVBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if CSVBibleCount:
                totalBibleCount += CSVBibleCount
                totalBibleTypes += 1
                typesFound.append( 'CSV:' + str(CSVBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: CSVBibleCount", CSVBibleCount )

            # Search for Forge for SwordSearcher text Bibles
            F4SSBibleCount = ForgeForSwordSearcherBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if F4SSBibleCount:
                totalBibleCount += F4SSBibleCount
                totalBibleTypes += 1
                typesFound.append( 'Forge:' + str(F4SSBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: F4SSBibleCount", F4SSBibleCount )

            # Search for VPL text Bibles
            VPLBibleCount = VPLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
            if VPLBibleCount:
                totalBibleCount += VPLBibleCount
                totalBibleTypes += 1
                typesFound.append( 'VPL:' + str(VPLBibleCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: VPLBibleCount", VPLBibleCount )
        else: # we weren't given a folder to look in
            theWordBibleCount = MySwordBibleCount = ESwordBibleCount = ESwordCommentaryCount = 0
            MyBibleBibleCount = PDBBibleCount = PierceOnlineBibleCount = EasyWorshipBibleCount = 0
            SwordBibleCount = UnboundBibleCount = DrupalBibleCount = YETBibleCount = 0
            ESFMBibleCount = PTX8BibleCount = PTX7BibleCount = USFM2BibleCount = USFMBibleCount = 0
            DBLBibleCount = USXBibleCount = USFXBibleCount = OSISBibleCount = 0
            OpenSongBibleCount = ZefaniaBibleCount = HaggaiBibleCount = VerseViewBibleCount = 0
            GoBibleCount = CSVBibleCount = F4SSBibleCount = VPLBibleCount = 0

        assert len(typesFound) == totalBibleTypes
        if totalBibleCount == 0:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "UnknownBible.search: No Bibles found" )
            self.foundType = 'None found'
            if strictCheck and not BibleOrgSysGlobals.strictCheckingFlag:
                # We did a strict check the first time, but strict checking wasn't specified on the command line
                #   so let's try again without the strict check
                if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "UnknownBible.search: retrying without strict checking criteria" )
                totalBibleUnstrictCount, totalBibleStrictTypes, typesUnstrictlyFound = recheckStrict( self.givenFolderName, oppositeStrictFlag=False )
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    print ( "  UnknownBible.recheck: After {} {} {}".format( totalBibleCount, totalBibleTypes, typesFound ) )
                    print ( "  UnknownBible.recheck: Found {} {} {}".format( totalBibleUnstrictCount, totalBibleStrictTypes, typesUnstrictlyFound ) )
                totalBibleCount, totalBibleTypes, typesFound = totalBibleUnstrictCount, totalBibleStrictTypes, typesUnstrictlyFound
        elif totalBibleCount > 1:
            if totalBibleTypes == 1:
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "UnknownBible.search: Multiple ({}) {} Bibles found in {}" \
                                                        .format( totalBibleCount, typesFound[0], self.givenFolderName ) )
                elif BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "UnknownBible.search: Multiple ({}) {} Bibles found".format( totalBibleCount, typesFound[0] ) )
                self.foundType = "Multiple found: {} Bibles".format( typesFound[0] )
            else:
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "UnknownBible.search: Multiple ({}) Bibles found: {} in {}" \
                                                        .format( totalBibleCount, typesFound, self.givenFolderName ) )
                elif BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "UnknownBible.search: Multiple ({}) Bibles found: {}".format( totalBibleCount, typesFound ) )
                self.foundType = 'Many types found'
                if not strictCheck:
                    # We didn't do a strict check the first time, so let's try that to try to reduce our found Bibles
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        print( "UnknownBible.search: retrying with strict checking criteria" )
                    totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound = recheckStrict( self.givenFolderName, oppositeStrictFlag=True )
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        print ( "  UnknownBible.recheck: After {} {} {}".format( totalBibleCount, totalBibleTypes, typesFound ) )
                        print ( "  UnknownBible.recheck: Found {} {} {}".format( totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound ) )
                    totalBibleCount, totalBibleTypes, typesFound = totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound
            if autoLoadAlways and BibleOrgSysGlobals.verbosityLevel > 0:
                # If there's only one of a particular type, we'll go for that one
                haveSingle = False
                for entry in typesFound:
                    if entry.endswith( ':1' ): haveSingle = True; break
                if haveSingle and BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "UnknownBible.search: Will try to find one Bible to autoload anyway!" )

        #if 1 or debuggingThisModule:
            #print( 'pB={} tW={} MSw={} ESw={} EswC={} MyB={} PDB={} Onl={} EW={} Sw={}' \
                #.format( PickledBibleCount, theWordBibleCount, MySwordBibleCount, ESwordBibleCount, ESwordCommentaryCount, MyBibleBibleCount, PDBBibleCount, PierceOnlineBibleCount, EasyWorshipBibleCount, SwordBibleCount ) )
            #print( '  Unb={} Dr={} YET={} ESFM={} PTX8={} PTX7={} USFM2={} USFM={}' \
                #.format( UnboundBibleCount, DrupalBibleCount, YETBibleCount, ESFMBibleCount, PTX8BibleCount, PTX7BibleCount, DBLBibleCount ) )
            #print( '  GB={} CSV={} F4SS={} VPL={}' \
                #.format( GoBibleCount, CSVBibleCount, F4SSBibleCount, VPLBibleCount ) )
            #print( '  USX={} USFX={} OSIS={} OSng={} Zef={} Hag={} VsVw={}' \
                #.format( USXBibleCount, USFXBibleCount, OSISBibleCount, OpenSongBibleCount, ZefaniaBibleCount, HaggaiBibleCount, VerseViewBibleCount ) )
        #if 0 and debuggingThisModule:
            #print( 'pB={} tW={} MSw={} ESw={} EswC={} MyB={} PDB={} Onl={} EW={} Sw={}' \
                #.format( PickledBibleStrictCount, theWordBibleStrictCount, MySwordBibleStrictCount, ESwordBibleStrictCount, ESwordCommentaryStrictCount, MyBibleBibleStrictCount, PDBBibleStrictCount, PierceOnlineBibleStrictCount, EasyWorshipBibleStrictCount, SwordBibleStrictCount ) )
            #print( '  Unb={} Dr={} YET={} ESFM={} PTX8={} PTX7={} USFM2={} USFM={}' \
                #.format( UnboundBibleStrictCount, DrupalBibleStrictCount, YETBibleStrictCount, ESFMBibleStrictCount, PTX8BibleStrictCount, PTX7BibleStrictCount, DBLBibleStrictCount ) )
            #print( '  GB={} CSV={} F4SS={} VPL={}' \
                #.format( GoBibleStrictCount, CSVBibleStrictCount, F4SSBibleStrictCount, VPLBibleStrictCount ) )
            #print( '  USX={} USFX={} OSIS={} OSng={} Zef={} Hag={} VsVw={}' \
                #.format( USXBibleStrictCount, USFXBibleStrictCount, OSISBibleStrictCount, OpenSongBibleStrictCount, ZefaniaBibleStrictCount, HaggaiBibleStrictCount, VerseViewBibleStrictCount ) )

        if autoLoadAlways or totalBibleCount == 1:
            # Put the binary formats first here because they can be detected more reliably
            if PickledBibleCount == 1:
                self.foundType = 'pickled Bible'
                if autoLoad: return PickledBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif theWordBibleCount == 1:
                self.foundType = 'theWord Bible'
                if autoLoad: return theWordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif MySwordBibleCount == 1:
                self.foundType = 'MySword Bible'
                if autoLoad: return MySwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESwordBibleCount == 1:
                self.foundType = 'e-Sword Bible'
                if autoLoad: return ESwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESwordCommentaryCount == 1:
                self.foundType = 'e-Sword Commentary'
                if autoLoad: return ESwordCommentaryFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif MyBibleBibleCount == 1:
                self.foundType = 'MyBible Bible'
                if autoLoad: return MyBibleBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PDBBibleCount == 1:
                self.foundType = 'PalmDB Bible'
                if autoLoad: return PalmDBBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif GoBibleCount == 1:
                self.foundType = 'GoBible Bible'
                if autoLoad: return GoBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PierceOnlineBibleCount == 1:
                self.foundType = 'Pierce Online Bible'
                if autoLoad: return PierceOnlineBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif EasyWorshipBibleCount == 1:
                self.foundType = 'EasyWorship Bible'
                if autoLoad: return EasyWorshipBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif SwordBibleCount == 1:
                self.foundType = 'Sword Bible'
                if autoLoad: return SwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            # And now plain text formats
            elif UnboundBibleCount == 1:
                self.foundType = 'Unbound Bible'
                if autoLoad: return UnboundBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif DrupalBibleCount == 1:
                self.foundType = 'Drupal Bible'
                if autoLoad: return DrupalBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif YETBibleCount == 1:
                self.foundType = 'YET Bible'
                if autoLoad: return YETBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESFMBibleCount == 1: # Must be ahead of USFM
                self.foundType = 'ESFM Bible'
                if autoLoad: return ESFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PTX8BibleCount == 1: # Must be ahead of USFM
                self.foundType = 'PTX8 Bible'
                if autoLoad: return PTX8BibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PTX7BibleCount == 1: # Must be ahead of USFM
                self.foundType = 'PTX7 Bible'
                if autoLoad: return PTX7BibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFM2BibleCount == 1:
                self.foundType = 'USFM2 Bible'
                if autoLoad: return USFM2BibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFMBibleCount == 1:
                self.foundType = 'USFM Bible'
                if autoLoad: return USFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif DBLBibleCount == 1: # Must be ahead of USX
                self.foundType = 'DBL Bible'
                if autoLoad: return DBLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif CSVBibleCount == 1:
                self.foundType = 'CSV Bible'
                if autoLoad: return CSVBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif F4SSBibleCount == 1:
                self.foundType = 'Forge Bible'
                if autoLoad: return ForgeForSwordSearcherBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif VPLBibleCount == 1:
                self.foundType = 'VPL Bible'
                if autoLoad: return VPLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            # And now XML text formats
            elif USXBibleCount == 1:
                self.foundType = 'USX XML Bible'
                if autoLoad: return USXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFXBibleCount == 1:
                self.foundType = 'USFX XML Bible'
                if autoLoad: return USFXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OSISBibleCount == 1:
                self.foundType = 'OSIS XML Bible'
                if autoLoad: return OSISXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OpenSongBibleCount == 1:
                self.foundType = 'OpenSong XML Bible'
                if autoLoad: return OpenSongXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ZefaniaBibleCount == 1:
                self.foundType = 'Zefania XML Bible'
                if autoLoad: return ZefaniaXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif HaggaiBibleCount == 1:
                self.foundType = 'Haggai XML Bible'
                if autoLoad: return HaggaiXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif VerseViewBibleCount == 1:
                self.foundType = 'VerseView XML Bible'
                if autoLoad: return VerseViewXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
        return self.foundType
    # end of UnknownBible.search
# end of class UnknownBible



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} V{}".format(PROGRAM_NAME, PROGRAM_VERSION ) )

    # Now demo the class
    if 0: # Just test one folder
        testFolder = 'Put your folder here/'
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible A1/ Trying (but not loading) {}…".format( testFolder ) )
        uB = UnknownBible( testFolder )
        result1 = uB.search( autoLoad=False )
        result2 = uB.search( autoLoadBooks=True ) if result1 else None
        if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  A1 result1 is: {}".format( result1 ) )
            print( "  A1 result2 is: {}".format( result2 ) )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( autoLoadAlways=False )
            result4 = uB.search( autoLoadAlways=True ) if result3 else None
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  A1 result3 is: {}".format( result3 ) )
                print( "  A1 result4 is: {}".format( result4 ) )

        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible A2/ (Strict as per BDB). Trying (but not loading) {}…".format( testFolder ) )
        uB = UnknownBible( testFolder )
        result1 = uB.search( strictCheck=True, autoLoad=False )
        result2 = uB.search( strictCheck=True, autoLoadBooks=True ) if result1 else None
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  A2 result1 is: {}".format( result1 ) )
            print( "  A2 result2 is: {}".format( result2 ) )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
        if result1 == 'Many types found':
            uB = UnknownBible( testFolder )
            result3 = uB.search( strictCheck=True, autoLoadAlways=False )
            result4 = uB.search( strictCheck=True, autoLoadAlways=True ) if result3 else None
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  A2 result3 is: {}".format( result3 ) )
                print( "  A2 result4 is: {}".format( result4 ) )
            if result3 == 'Many types found':
                uB = UnknownBible( testFolder )
                result5 = uB.search( strictCheck=True, autoLoadAlways=False, autoLoadBooks=True )
                result6 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True ) if result5 else None
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "  A2 result5 is: {}".format( result5 ) )
                    print( "  A2 result6 is: {}".format( result6 ) )

        #from BibleOrgSys.Bible import Bible
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible A3/ (Strict as per BDB). Trying {}…".format( testFolder ) )
        #uB = UnknownBible( testFolder )
        #result1 = uB.search( strictCheck=True, autoLoadAlways=True, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 2:
            #print( "  A3 result1 is: {}".format( result1 ) )
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
        #if isinstance( result1, Bible ):
            #thisBible = result1
            #thisBible.check()
            #errorDictionary = thisBible.getErrors()


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    testFolders = ( os.path.join( os.path.expanduser('~'), 'Logs/'), # Shouldn't have any Bibles here
                    BiblesFolderpath.joinpath( 'Biola Unbound modules/' ),
                    BiblesFolderpath.joinpath( 'EasyWorship Bibles/' ),
                    BiblesFolderpath.joinpath( 'OpenSong Bibles/' ),
                    BiblesFolderpath.joinpath( 'Zefania modules/' ),
                    BiblesFolderpath.joinpath( 'YET modules/' ),
                    BiblesFolderpath.joinpath( 'GoBible modules/' ),
                    BiblesFolderpath.joinpath( 'MyBible modules/' ),
                    BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/' ),
                    Path( '/srv/AutoProcesses/Processed/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PickledBibleTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/' ),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/' ),
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
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible B{}/ Trying (but not loading) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=False )
            #result2 = uB.search( autoLoad=True ) if result1 else None
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Just load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible C{}/ Single loading (but not books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Fully load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible D{}/ Single loading (incl. books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible E{}/ Always loading (but not books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always fully load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible F{}/ Always loading (incl. books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 0: # Load, check, and export the files
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible G{}/ Processing {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            #if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Results are: {} and {}".format( result1, result2 ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )
            if result:
                result.check()
                results = result.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Results are: {}".format( results ) )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of UnknownBible.py
