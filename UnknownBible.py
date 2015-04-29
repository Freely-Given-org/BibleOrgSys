#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UnknownBible.py
#
# Module handling a unknown Bible object
#
# Copyright (C) 2013-2015 Robert Hunt
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
    Sword modules (binary).
"""

from gettext import gettext as _

LastModifiedDate = '2015-04-28' # by RJH
ShortProgName = "UnknownBible"
ProgName = "Unknown Bible object handler"
ProgVersion = '0.20'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os.path

import BibleOrgSysGlobals
from ESFMBible import ESFMBibleFileCheck, ESFMBible
from USFMBible import USFMBibleFileCheck, USFMBible
from USXXMLBible import USXXMLBibleFileCheck, USXXMLBible
from USFXXMLBible import USFXXMLBibleFileCheck, USFXXMLBible
from OpenSongXMLBible import OpenSongXMLBibleFileCheck, OpenSongXMLBible
from OSISXMLBible import OSISXMLBibleFileCheck, OSISXMLBible
from ZefaniaXMLBible import ZefaniaXMLBibleFileCheck, ZefaniaXMLBible
from HaggaiXMLBible import HaggaiXMLBibleFileCheck, HaggaiXMLBible
from VerseViewXMLBible import VerseViewXMLBibleFileCheck, VerseViewXMLBible
from UnboundBible import UnboundBibleFileCheck, UnboundBible
from DrupalBible import DrupalBibleFileCheck, DrupalBible
from YETBible import YETBibleFileCheck, YETBible
from TheWordBible import TheWordBibleFileCheck, TheWordBible
from MySwordBible import MySwordBibleFileCheck, MySwordBible
from ESwordBible import ESwordBibleFileCheck, ESwordBible
from PalmDBBible import PalmDBBibleFileCheck, PalmDBBible
from OnlineBible import OnlineBibleFileCheck, OnlineBible
from SwordBible import SwordBibleFileCheck, SwordBible
from CSVBible import CSVBibleFileCheck, CSVBible
from VPLBible import VPLBibleFileCheck, VPLBible
#from SwordResources import SwordInterface # What about these?



class UnknownBible:
    """
    Class for handling an entire Bible.
    """

    def __init__( self, givenFolderName ):
        """
        Constructor: creates an empty Bible object.
        """
        if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
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

        totalBibleCount, totalBibleTypes, typesFound = 0, 0, []

        # Search for TheWord Bibles
        theWordBibleCount = TheWordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if theWordBibleCount:
            totalBibleCount += theWordBibleCount
            totalBibleTypes += 1
            typesFound.append( 'theWord:' + str(theWordBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "TheWordBible.search: theWordBibleCount", theWordBibleCount )

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

        # Search for ESFM Bibles
        ESFMBibleCount = ESFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if ESFMBibleCount:
            totalBibleCount += ESFMBibleCount
            totalBibleTypes += 1
            typesFound.append( 'ESFM:' + str(ESFMBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: ESFMBibleCount", ESFMBibleCount )

        # Search for USFM Bibles
        USFMBibleCount = USFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if USFMBibleCount:
            totalBibleCount += USFMBibleCount
            totalBibleTypes += 1
            typesFound.append( 'USFM:' + str(USFMBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: USFMBibleCount", USFMBibleCount )

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

        # Search for VPL text Bibles
        VPLBibleCount = VPLBibleFileCheck( self.givenFolderName, strictCheck=strictCheck )
        if VPLBibleCount:
            totalBibleCount += VPLBibleCount
            totalBibleTypes += 1
            typesFound.append( 'VPL:' + str(VPLBibleCount) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "UnknownBible.search: VPLBibleCount", VPLBibleCount )


        assert( len(typesFound) == totalBibleTypes )
        if totalBibleCount == 0:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "UnknownBible.search: No Bibles found" )
            self.foundType = 'None found'
        elif totalBibleCount > 1:
            if totalBibleTypes == 1:
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "UnknownBible.search: Multiple ({}) {} Bibles found".format( totalBibleCount, typesFound[0] ) )
                self.foundType = "Multiple found: {} Bibles".format( typesFound[0] )
            else:
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "UnknownBible.search: Multiple ({}) Bibles found: {}".format( totalBibleCount, typesFound ) )
                self.foundType = 'Many types found'
            if autoLoadAlways and BibleOrgSysGlobals.verbosityLevel > 0:
                print( "UnknownBible.search: Will try to find one Bible to autoload anyway!" )

        if autoLoadAlways or totalBibleCount == 1:
            # Put the binary formats first here because they can be detected more reliably
            if theWordBibleCount == 1:
                self.foundType = "theWord Bible"
                if autoLoad: return TheWordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif MySwordBibleCount == 1:
                self.foundType = "MySword Bible"
                if autoLoad: return MySwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif ESwordBibleCount == 1:
                self.foundType = "e-Sword Bible"
                if autoLoad: return ESwordBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif PDBBibleCount == 1:
                self.foundType = "PalmDB Bible"
                if autoLoad: return PalmDBBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif OnlineBibleCount == 1:
                self.foundType = "Online Bible"
                if autoLoad: return OnlineBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
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
            elif ESFMBibleCount == 1:
                self.foundType = "ESFM Bible"
                if autoLoad: return ESFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif USFMBibleCount == 1:
                self.foundType = "USFM Bible"
                if autoLoad: return USFMBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
                else: return self.foundType
            elif CSVBibleCount == 1:
                self.foundType = "CSV Bible"
                if autoLoad: return CSVBibleFileCheck( self.givenFolderName, strictCheck=strictCheck, autoLoad=autoLoad, autoLoadBooks=autoLoadBooks )
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
    testFolders = ( "/home/robert/Logs", # Shouldn't have any Bibles here
                    #"../../../../../Data/Work/Bibles/theWord modules/",
                    #"../../../../../Data/Work/Bibles/Biola Unbound modules/",
                    #"../../../../../Data/Work/Bibles/OpenSong Bibles/",
                    #"../../../../../Data/Work/Bibles/Zefania modules/",
                    #"../../../../../Data/Work/Bibles/YET modules/",
                    #"../../../../../Data/Work/Matigsalug/Bible/MBTV/",
                    #"../../../../AutoProcesses/Processed/",
                    "Tests/DataFilesForTests/USFMTest1/", "Tests/DataFilesForTests/USFMTest2/",
                    "Tests/DataFilesForTests/USFM-OEB/", "Tests/DataFilesForTests/USFM-WEB/",
                    "Tests/DataFilesForTests/ESFMTest1/", "Tests/DataFilesForTests/ESFMTest2/",
                    "Tests/DataFilesForTests/USXTest1/", "Tests/DataFilesForTests/USXTest2/",
                    "Tests/DataFilesForTests/USFXTest1/", "Tests/DataFilesForTests/USFXTest2/",
                    "Tests/DataFilesForTests/USFX-ASV/", "Tests/DataFilesForTests/USFX-WEB/",
                    "Tests/DataFilesForTests/OSISTest1/", "Tests/DataFilesForTests/OSISTest2/",
                    "Tests/DataFilesForTests/ZefaniaTest/", "Tests/DataFilesForTests/HaggaiTest/",
                    "Tests/DataFilesForTests/ZefaniaTest/", "Tests/DataFilesForTests/VerseViewXML/",
                    "Tests/DataFilesForTests/e-SwordTest/",
                    "Tests/DataFilesForTests/theWordTest/", "Tests/DataFilesForTests/MySwordTest/",
                    "Tests/DataFilesForTests/YETTest/", "Tests/DataFilesForTests/PDBTest/",
                    "Tests/DataFilesForTests/OnlineBible/",
                    #"Tests/DataFilesForTests/DrupalTest/",
                    "Tests/DataFilesForTests/CSVTest1/", "Tests/DataFilesForTests/CSVTest2/",
                    "Tests/DataFilesForTests/VPLTest1/", "Tests/DataFilesForTests/VPLTest2/",
                    #"Tests/DataFilesForTests/", # Up a level
                    )
    if 1: # Just find the files
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible A{}/ Trying {}...".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=False )
            #result2 = uB.search( autoLoad=True ) if result1 else None
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Just load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible B{}/ Single loading (no files) {}...".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Fully load the Bible objects (only if exactly one found)
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible C{}/ Single loading (with files) {}...".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible D{}/ Always loading {}...".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 1: # Always fully load the Bible objects
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible E{}/ Always loading {}...".format( j+1, testFolder ) )
            uB = UnknownBible( testFolder )
            result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Result is: {}".format( result ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( uB )

    if 0: # Load, check, and export the files
        for j, testFolder in enumerate( testFolders ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nUnknownBible F{}/ Processing {}...".format( j+1, testFolder ) )
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
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of UnknownBible.py