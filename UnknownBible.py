#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# UnknownBible.py
#
# Module handling a unknown Bible object
#
# Copyright (C) 2013-2016 Robert Hunt
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

LastModifiedDate = '2016-04-07' # by RJH
ShortProgName = "UnknownBible"
ProgName = "Unknown Bible object handler"
ProgVersion = '0.29'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os.path

import BibleOrgSysGlobals
from ESFMBible import ESFMBibleFileCheck
from PTXBible import PTXBibleFileCheck
from USFMBible import USFMBibleFileCheck
from DBLBible import DBLBibleFileCheck
from USXXMLBible import USXXMLBibleFileCheck
from USFXXMLBible import USFXXMLBibleFileCheck
from OpenSongXMLBible import OpenSongXMLBibleFileCheck
from OSISXMLBible import OSISXMLBibleFileCheck
from ZefaniaXMLBible import ZefaniaXMLBibleFileCheck
from HaggaiXMLBible import HaggaiXMLBibleFileCheck
from VerseViewXMLBible import VerseViewXMLBibleFileCheck
from UnboundBible import UnboundBibleFileCheck
from DrupalBible import DrupalBibleFileCheck
from YETBible import YETBibleFileCheck
from theWordBible import theWordBibleFileCheck
from MySwordBible import MySwordBibleFileCheck
from ESwordBible import ESwordBibleFileCheck
from MyBibleBible import MyBibleBibleFileCheck
from PalmDBBible import PalmDBBibleFileCheck
from OnlineBible import OnlineBibleFileCheck
from EasyWorshipBible import EasyWorshipBibleFileCheck
from SwordBible import SwordBibleFileCheck
from CSVBible import CSVBibleFileCheck
from ForgeForSwordSearcherBible import ForgeForSwordSearcherBibleFileCheck
from VPLBible import VPLBibleFileCheck
#from SwordResources import SwordInterface # What about these?



class UnknownBible:
    """
    Class for handling an entire Bible.
    """

    def __init__( self, givenFolderName ):
        """
        Constructor: creates an empty Bible object.
        """
        if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
        self.givenFolderName = givenFolderName

        # Check that the given folder is readable
        if not os.access( givenFolderName, os.R_OK ):
            logging.critical( _("UnknownBible: Given {!r} folder is unreadable").format( self.givenFolderName ) )
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
        if not self.folderReadable: return None
        if autoLoadAlways or autoLoadBooks: autoLoad = True

        def recheckStrict( folderName, oppositeStrictFlag ):
            """
            If we didn't check with the strict flag the first time,
                try it again with the strict mode set.

            Returns the three counters.
            """
            if BibleOrgSysGlobals.debugFlag: print( "UnknownBible.recheckStrict( {} )".format( folderName ) )

            totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound = 0, 0, []

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

            # Search for e-Sword Bibles
            ESwordBibleStrictCount = ESwordBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
            if ESwordBibleStrictCount:
                totalBibleStrictCount += ESwordBibleStrictCount
                totalBibleStrictTypes += 1
                typesStrictlyFound.append( 'e-Sword:' + str(ESwordBibleStrictCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBible.recheckStrict: ESwordBibleStrictCount", ESwordBibleStrictCount )

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

            # Search for Online Bibles
            OnlineBibleStrictCount = OnlineBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
            if OnlineBibleStrictCount:
                totalBibleStrictCount += OnlineBibleStrictCount
                totalBibleStrictTypes += 1
                typesStrictlyFound.append( 'Online:' + str(OnlineBibleStrictCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: OnlineBibleStrictCount", OnlineBibleStrictCount )

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

            # Search for PTX Bibles -- put BEFORE USFM
            PTXBibleStrictCount = PTXBibleFileCheck( folderName, strictCheck=oppositeStrictFlag )
            if PTXBibleStrictCount:
                totalBibleStrictCount += PTXBibleStrictCount
                totalBibleStrictTypes += 1
                typesStrictlyFound.append( 'PTX:' + str(PTXBibleStrictCount) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.recheckStrict: PTXBibleStrictCount", PTXBibleStrictCount )

            # Search for USFM Bibles
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

            return totalBibleStrictCount, totalBibleStrictTypes, typesStrictlyFound
        # end of recheckStrict


        # Main code
        # We first do a normal (non-strict) check (unless strict was requested by the caller)
        totalBibleCount, totalBibleTypes, typesFound = 0, 0, []

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

        # Search for e-Sword Bibles
        ESwordBibleCount = ESwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if ESwordBibleCount:
            totalBibleCount += ESwordBibleCount
            totalBibleTypes += 1
            typesFound.append( 'e-Sword:' + str(ESwordBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBible.search: ESwordBibleCount", ESwordBibleCount )

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

        # Search for Online Bibles
        OnlineBibleCount = OnlineBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if OnlineBibleCount:
            totalBibleCount += OnlineBibleCount
            totalBibleTypes += 1
            typesFound.append( 'Online:' + str(OnlineBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: OnlineBibleCount", OnlineBibleCount )

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

        # Search for PTX Bibles -- put BEFORE USFM
        PTXBibleCount = PTXBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if PTXBibleCount:
            totalBibleCount += PTXBibleCount
            totalBibleTypes += 1
            typesFound.append( 'PTX:' + str(PTXBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: PTXBibleCount", PTXBibleCount )

        # Search for USFM Bibles
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


        assert len(typesFound) == totalBibleTypes
        if totalBibleCount == 0:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "UnknownBible.search: No Bibles found" )
            self.foundType = 'None found'
            if strictCheck and not BibleOrgSysGlobals.strictCheckingFlag:
                # We did a strict check the first time, but strict checking wasn't specified on the command line
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
                if haveSingle and BibleOrgSysGlobals.verbosityLevel > 0: print( "UnknownBible.search: Will try to find one Bible to autoload anyway!" )

        if autoLoadAlways or totalBibleCount == 1:
            # Put the binary formats first here because they can be detected more reliably
            if theWordBibleCount == 1:
                self.foundType = "theWord Bible"
                if autoLoad: return theWordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif MySwordBibleCount == 1:
                self.foundType = "MySword Bible"
                if autoLoad: return MySwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESwordBibleCount == 1:
                self.foundType = "e-Sword Bible"
                if autoLoad: return ESwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif MyBibleBibleCount == 1:
                self.foundType = "MyBible Bible"
                if autoLoad: return MyBibleBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PDBBibleCount == 1:
                self.foundType = "PalmDB Bible"
                if autoLoad: return PalmDBBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OnlineBibleCount == 1:
                self.foundType = "Online Bible"
                if autoLoad: return OnlineBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif EasyWorshipBibleCount == 1:
                self.foundType = "EasyWorship Bible"
                if autoLoad: return EasyWorshipBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif SwordBibleCount == 1:
                self.foundType = "Sword Bible"
                if autoLoad: return SwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            # And now plain text formats
            elif UnboundBibleCount == 1:
                self.foundType = "Unbound Bible"
                if autoLoad: return UnboundBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif DrupalBibleCount == 1:
                self.foundType = "Drupal Bible"
                if autoLoad: return DrupalBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif YETBibleCount == 1:
                self.foundType = "YET Bible"
                if autoLoad: return YETBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESFMBibleCount == 1: # Must be ahead of USFM
                self.foundType = "ESFM Bible"
                if autoLoad: return ESFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PTXBibleCount == 1: # Must be ahead of USFM
                self.foundType = "PTX Bible"
                if autoLoad: return PTXBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFMBibleCount == 1:
                self.foundType = "USFM Bible"
                if autoLoad: return USFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif DBLBibleCount == 1: # Must be ahead of USX
                self.foundType = "DBL Bible"
                if autoLoad: return DBLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif CSVBibleCount == 1:
                self.foundType = "CSV Bible"
                if autoLoad: return CSVBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif F4SSBibleCount == 1:
                self.foundType = "Forge Bible"
                if autoLoad: return ForgeForSwordSearcherBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif VPLBibleCount == 1:
                self.foundType = "VPL Bible"
                if autoLoad: return VPLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            # And now XML text formats
            elif USXBibleCount == 1:
                self.foundType = "USX XML Bible"
                if autoLoad: return USXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFXBibleCount == 1:
                self.foundType = "USFX XML Bible"
                if autoLoad: return USFXXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OSISBibleCount == 1:
                self.foundType = "OSIS XML Bible"
                if autoLoad: return OSISXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OpenSongBibleCount == 1:
                self.foundType = "OpenSong XML Bible"
                if autoLoad: return OpenSongXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ZefaniaBibleCount == 1:
                self.foundType = "Zefania XML Bible"
                if autoLoad: return ZefaniaXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif HaggaiBibleCount == 1:
                self.foundType = "Haggai XML Bible"
                if autoLoad: return HaggaiXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif VerseViewBibleCount == 1:
                self.foundType = "VerseView XML Bible"
                if autoLoad: return VerseViewXMLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
        return self.foundType
    # end of UnknownBible.search
# end of class UnknownBible



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} V{}".format(ProgName, ProgVersion ) )

    # Now demo the class
    testFolders = ( os.path.join( os.path.expanduser('~'), 'Logs/'), # Shouldn't have any Bibles here
                    'Tests/DataFilesForTests/PTXTest/',
                    'Tests/DataFilesForTests/DBLTest/',
                    '../../../../../Data/Work/Bibles/theWord modules/',
                    '../../../../../Data/Work/Bibles/Biola Unbound modules/',
                    '../../../../../Data/Work/Bibles/EasyWorship Bibles/',
                    '../../../../../Data/Work/Bibles/OpenSong Bibles/',
                    '../../../../../Data/Work/Bibles/Zefania modules/',
                    '../../../../../Data/Work/Bibles/YET modules/',
                    '../../../../../Data/Work/Bibles/MyBible modules/',
                    '../../../../../Data/Work/Matigsalug/Bible/MBTV/',
                    '../../../../AutoProcesses/Processed/',
                    'Tests/DataFilesForTests/USFMTest1/', 'Tests/DataFilesForTests/USFMTest2/',
                    'Tests/DataFilesForTests/USFM-OEB/', 'Tests/DataFilesForTests/USFM-WEB/',
                    'Tests/DataFilesForTests/ESFMTest1/', 'Tests/DataFilesForTests/ESFMTest2/',
                    'Tests/DataFilesForTests/DBLTest/',
                    'Tests/DataFilesForTests/USXTest1/', 'Tests/DataFilesForTests/USXTest2/',
                    'Tests/DataFilesForTests/USFXTest1/', 'Tests/DataFilesForTests/USFXTest2/',
                    'Tests/DataFilesForTests/USFX-ASV/', 'Tests/DataFilesForTests/USFX-WEB/',
                    'Tests/DataFilesForTests/OSISTest1/', 'Tests/DataFilesForTests/OSISTest2/',
                    'Tests/DataFilesForTests/ZefaniaTest/', 'Tests/DataFilesForTests/HaggaiTest/',
                    'Tests/DataFilesForTests/ZefaniaTest/', 'Tests/DataFilesForTests/VerseViewXML/',
                    'Tests/DataFilesForTests/e-SwordTest/',
                    'Tests/DataFilesForTests/MyBibleTest/',
                    'Tests/DataFilesForTests/theWordTest/', 'Tests/DataFilesForTests/MySwordTest/',
                    'Tests/DataFilesForTests/YETTest/', 'Tests/DataFilesForTests/PDBTest/',
                    'Tests/DataFilesForTests/OnlineBible/',
                    'Tests/DataFilesForTests/EasyWorshipBible/',
                    'Tests/DataFilesForTests/DrupalTest/',
                    'Tests/DataFilesForTests/CSVTest1/', 'Tests/DataFilesForTests/CSVTest2/',
                    'Tests/DataFilesForTests/VPLTest1/', 'Tests/DataFilesForTests/VPLTest2/', 'Tests/DataFilesForTests/VPLTest3/',
                    'Tests/DataFilesForTests/', # Up a level
                    )
    if 1: # Just find the files
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible A{}/ Trying (but not loading) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=False )
            #result2 = uB.search( autoLoad=True ) if result1 else None
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Just load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible B{}/ Single loading (but not books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Fully load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible C{}/ Single loading (incl. books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible D{}/ Always loading (but not books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always fully load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible E{}/ Always loading (incl. books) {}…".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 0: # Load, check, and export the files
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible F{}/ Processing {}…".format( j+1, testFolder ) )
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
    #from multiprocessing import freeze_support
    #freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of UnknownBible.py