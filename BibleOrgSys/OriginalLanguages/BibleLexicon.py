#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleLexicon.py
#
# Module handling the combined Hebrew and Greek lexicons
#
# Copyright (C) 2014-2016 Robert Hunt
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
Module handling the OpenScriptures Hebrew and morphgnt Greek lexicons.

    Hebrew has Strongs and BrDrBr
    Greek has Strongs only.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2016-02-25' # by RJH
SHORT_PROGRAM_NAME = "BibleLexicon"
PROGRAM_NAME = "Bible Lexicon format handler"
PROGRAM_VERSION = '0.24'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging
import os.path

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.OriginalLanguages import HebrewLexicon
from BibleOrgSys.OriginalLanguages import GreekLexicon



class BibleLexiconIndex:
    """
    Class for handling a Bible Lexicon (Hebrew -- not applicable yet to Greek).

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, HebrewXMLFolder, GreekXMLFolder, preload=False ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexiconIndex.__init__( {}, {} )").format( HebrewXMLFolder, GreekXMLFolder ) )
        self.HebrewXMLFolder, self.GreekXMLFolder = HebrewXMLFolder, GreekXMLFolder
        self.hIndex = None
        if preload: self.load()
    # end of BibleLexiconIndex.__init__


    def load( self ):
        self.hIndex = HebrewLexicon.HebrewLexiconIndex( self.HebrewXMLFolder ) # Create the object
    # end of BibleLexiconIndex.load


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Lexicon Index object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.hIndex is not None:
            result += ('\n' if result else '') + "  " + _("Number of augmented Hebrew Strong's index entries = {}").format( len(self.hIndex.IndexEntries1) )
            result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {}").format( len(self.hIndex.IndexEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {}").format( len(self.hIndex.IndexEntries['arc']) )
        return result
    # end of BibleLexiconIndex.__str__


    def getLexiconCodeFromStrongsNumber( self, key ):
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'.
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex.getLexiconCodeFromStrongsNumber( key )
    # end of BibleLexiconIndex.getLexiconCodeFromStrongsNumber


    def _getStrongsNumberFromLexiconCode1( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex._getStrongsNumberFromLexiconCode1( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode1


    def _getStrongsNumberFromLexiconCode2( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex._getStrongsNumberFromLexiconCode2( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode2


    def getStrongsNumberFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex.getStrongsNumberFromLexiconCode( key )
    # end of BibleLexiconIndex.getStrongsNumberFromLexiconCode


    def getBrDrBrCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BrDrBr code, e.g., 'm.ba.aa'
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex.getBrDrBrCodeFromLexiconCode( key )
    # end of BibleLexiconIndex.getBrDrBrCodeFromLexiconCode


    def getTWOTCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BrDrBr code, e.g., '4a'
        """
        if self.hIndex is None: self.load()
        if key.startswith( 'H' ): return self.hIndex.getTWOTCodeFromLexiconCode( key )
    # end of BibleLexiconIndex.getTWOTCodeFromLexiconCode
# end of BibleLexiconIndex class



class BibleLexicon:
    """
    Class for handling a Bible Lexicon (Hebrew and Greek)

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, HebrewXMLFolder, GreekXMLFolder, preload=False ):
        """
        Constructor: expects the filepath of the source XML file.

        Does not actually cause the XML to be loaded (very slow).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.__init__( {}, {}, {} )").format( HebrewXMLFolder, GreekXMLFolder, preload ) )
        self.HebrewXMLFolder, self.GreekXMLFolder = HebrewXMLFolder, GreekXMLFolder
        fnfCount = 0
        try: self.hLexicon = HebrewLexicon.HebrewLexicon( self.HebrewXMLFolder, preload ) # Create the object
        except FileNotFoundError:
            logging.critical( _("BibleLexicon could not find Hebrew lexicon at {}").format( HebrewXMLFolder ) )
            fnfCount += 1
            self.hLexicon = None
        try: self.gLexicon = GreekLexicon.GreekLexicon( self.GreekXMLFolder, preload ) # Create the object
        except FileNotFoundError:
            logging.critical( _("BibleLexicon could not find Greek lexicon at {}").format( GreekXMLFolder ) )
            fnfCount += 1
            self.gLexicon = None
        if fnfCount >= 2: raise FileNotFoundError
    # end of BibleLexicon.__init__


    def __str__( self ):
        """
        This method returns the string representation of the Bible lexicon.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.hLexicon is not None:
            if self.hLexicon.StrongsEntries is not None:
                result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {}").format( len(self.hLexicon.StrongsEntries) )
            if self.hLexicon.BrownDriverBriggsEntries is not None:
                result += ('\n' if result else '') + "  " + _("Number of BrDrBr Hebrew entries = {}").format( len(self.hLexicon.BrownDriverBriggsEntries['heb']) )
                result += ('\n' if result else '') + "  " + _("Number of BrDrBr Aramaic entries = {}").format( len(self.hLexicon.BrownDriverBriggsEntries['arc']) )
            if self.gLexicon.StrongsEntries is not None:
                result += ('\n' if result else '') + "  " + _("Number of Strong's Greek entries = {}").format( len(self.gLexicon.StrongsEntries) )
        return result
    # end of BibleLexicon.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getStrongsEntryData( {} )").format( repr(key) ) )
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryData( key )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryData( key )
    # end of BibleLexicon.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getStrongsEntryField( {}, {} )").format( repr(key), repr(fieldName) ) )
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryField( key, fieldName )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryField( key, fieldName )
    # end of BibleLexicon.getStrongsEntryField


    def getStrongsEntryHTML( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an HTML li entry for the given key.
        Returns None if the key is not found.

        e.g., for H1, returns:
            <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word;
                father, in a literal and immediate, or figurative and remote application):
                <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>.
                Compare names in "Abi-".</li>
            <li value="165" id="ot:165"><i title="{e-hee'}" xml:lang="hbo">אֱהִי</i> apparently an
                orthographical variation for <a href="#ot:346"><i title="{ah-yay'}" xml:lang="hbo">אַיֵּה</i></a>;
                where: <span class="kjv_def">I will be (Hos</span>. 13:10, 14) (which is often the rendering of
                the same Hebrew form from <a href="#ot:1961"><i title="{haw-yaw}" xml:lang="hbo">הָיָה</i></a>).</li>

        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getStrongsEntryHTML( {} )").format( repr(key) ) )
        if key.startswith( 'H' ): return self.hLexicon.getStrongsEntryHTML( key )
        if key.startswith( 'G' ): return self.gLexicon.getStrongsEntryHTML( key )
    # end of BibleLexicon.getStrongsEntryHTML


    def getBrDrBrEntryData( self, key ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getBrDrBrEntryData( {} )").format( repr(key) ) )
        return self.hLexicon.getBrDrBrEntryData( key )
    # end of BibleLexicon.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key, fieldName ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getBrDrBrEntryField( {}, {} )").format( repr(key), repr(fieldName) ) )
        return self.hLexicon.getBrDrBrEntryField( key, fieldName )
    # end of BibleLexicon.getBrDrBrEntryField


    def getBrDrBrEntryHTML( self, key ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getBrDrBrEntryHTML( {} )").format( repr(key) ) )
        return self.hLexicon.getBrDrBrEntryHTML( key )
    # end of BibleLexicon.getBrDrBrEntryHTML


    def getEntryData( self, key ):
        """
        The key can be a Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getEntryData( {} )").format( repr(key) ) )
        if not key: return
        if key[0]=='H' and key[1:].isdigit(): return self.hLexicon.getStrongsEntryData( key )
        if key[0]=='G' and key[1:].isdigit(): return self.gLexicon.getStrongsEntryData( key )
        if '.' in key: return self.hLexicon.getBrDrBrEntryData( key )
    # end of BibleLexicon.getEntryData


    def getEntryField( self, key, fieldName ):
        """
        The key can be a Hebrew Strong's number (string) like 'H1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getEntryField( {}, {} )").format( repr(key), repr(fieldName) ) )
        if not key: return
        if key[0]=='H' and key[1:].isdigit(): return self.hLexicon.getStrongsEntryField( key, fieldName )
        if key[0]=='G' and key[1:].isdigit(): return self.gLexicon.getStrongsEntryField( key, fieldName )
        if '.' in key: return self.hLexicon.getBrDrBrEntryField( key, fieldName )
    # end of BibleLexicon.getEntryField


    def getEntryHTML( self, key ):
        """
        The key can be a Hebrew Strong's number (string) like 'H1979'.

        Returns an HTML li entry for the given key.
        Returns None if the key is not found.

        e.g., for H1, returns:
            <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word;
                father, in a literal and immediate, or figurative and remote application):
                <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>.
                Compare names in "Abi-".</li>
            <li value="165" id="ot:165"><i title="{e-hee'}" xml:lang="hbo">אֱהִי</i> apparently an
                orthographical variation for <a href="#ot:346"><i title="{ah-yay'}" xml:lang="hbo">אַיֵּה</i></a>;
                where: <span class="kjv_def">I will be (Hos</span>. 13:10, 14) (which is often the rendering of
                the same Hebrew form from <a href="#ot:1961"><i title="{haw-yaw}" xml:lang="hbo">הָיָה</i></a>).</li>

        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("BibleLexicon.getEntryHTML( {} )").format( repr(key) ) )
        if not key: return
        if key[0]=='H' and key[1:].isdigit(): return self.hLexicon.getStrongsEntryHTML( key )
        if key[0]=='G' and key[1:].isdigit(): return self.gLexicon.getStrongsEntryHTML( key )
        if '.' in key: return self.hLexicon.getBrDrBrEntryHTML( key )
    # end of BibleLexicon.getEntryHTML
# end of BibleLexicon class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    HebrewLexiconFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'HebrewLexicon/' ) # Open Scriptures Hebrew lexicon folder
    GreekLexiconFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/morphgnt/strongs-dictionary-xml/' ) # morphgnt Greek lexicon folder


    if 0: # demonstrate the Bible Lexicon Index class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the Bible Lexicon Index class…" )
        blix = BibleLexiconIndex( HebrewLexiconFolder, GreekLexiconFolder ) # Load and process the XML
        print( blix ) # Just print a summary
        print()
        print( "Code for 2 is", blix.getLexiconCodeFromStrongsNumber( '2' ) )
        print( "Code for H8674 is", blix.getLexiconCodeFromStrongsNumber( 'H8674' ) )
        print( "Code for H8675 is", blix.getLexiconCodeFromStrongsNumber( 'H8675' ) )
        print( "Codes for aac are", blix.getStrongsNumberFromLexiconCode('aac'), blix.getBrDrBrCodeFromLexiconCode('aac'), blix.getTWOTCodeFromLexiconCode('aac') )
        print( "Codes for nyy are", blix.getStrongsNumberFromLexiconCode('nyy'), blix.getBrDrBrCodeFromLexiconCode('nyy'), blix.getTWOTCodeFromLexiconCode('nyy') )
        print( "Codes for pdc are", blix.getStrongsNumberFromLexiconCode('pdc'), blix.getBrDrBrCodeFromLexiconCode('pdc'), blix.getTWOTCodeFromLexiconCode('pdc') )
        print( "Codes for pdd are", blix.getStrongsNumberFromLexiconCode('pdd'), blix.getBrDrBrCodeFromLexiconCode('pdd'), blix.getTWOTCodeFromLexiconCode('pdd') )


    if 1: # demonstrate the Bible Lexicon class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the Bible Lexicon class…" )
        bl = BibleLexicon( HebrewLexiconFolder, GreekLexiconFolder ) # Load and process the XML
        print( bl ) # Just print a summary
        print()
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',
                           'G1','G123','G165','G1732','G1979','G2011','G5624','G5625',): # Last ones of each are invalid
            print( '\n' + strongsKey )
            print( " Data (all):", bl.getStrongsEntryData( strongsKey ) )
            print( " 'Usage' field:", bl.getStrongsEntryField( strongsKey, 'usage' ) )
            print( " HTML entry:", bl.getStrongsEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            print( '\n' + BrDrBrKey )
            print( " Data (all):", bl.getBrDrBrEntryData( BrDrBrKey ) )
            print( " 'Status' field:", bl.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            print( " HTML entry:", bl.getBrDrBrEntryHTML( BrDrBrKey ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleLexicon.py
