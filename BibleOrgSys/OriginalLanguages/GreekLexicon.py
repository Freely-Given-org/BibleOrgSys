#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GreekLexicon.py
#
# Module handling the Greek lexicon
#
# Copyright (C) 2014-2020 Robert Hunt
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
Module handling the Greek lexicon.

    The later class is the one for users to
        access the Strongs lexical entries
        via various keys and in various formats.
"""
from gettext import gettext as _
from typing import Optional
# import logging
import os.path
import sys

if __name__ == '__main__':
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint


LAST_MODIFIED_DATE = '2020-05-03' # by RJH
SHORT_PROGRAM_NAME = "GreekLexicon"
PROGRAM_NAME = "Greek Lexicon handler"
PROGRAM_VERSION = '0.17'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False



class GreekLexicon:
    """
    Class for handling an Greek Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder=None, preload:bool=False ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        vPrint( 'Never', debuggingThisModule, _("GreekLexicon.__init__( {} )").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        self.StrongsEntries = None
        if preload: self.load()
    # end of GreekLexicon.__init__


    def load( self ) -> None:
        """
        Load the pickle file if it's there,
            Otherwise use the converter to load the XML (slower).
        """
        vPrint( 'Never', debuggingThisModule, _("GreekLexicon.load()…") )
        assert self.StrongsEntries is None

        standardPickleFilepath = BibleOrgSysGlobals.BOS_DISTRIBUTED_FILES_FOLDERPATH.joinpath( 'GreekLexicon_Strongs_Table.1.pickle' )
        if standardPickleFilepath.is_file():
            import pickle
            vPrint( 'Info', debuggingThisModule, f"Loading pickle file {standardPickleFilepath}…" )
            with open( standardPickleFilepath, 'rb') as pickleFile:
                self.StrongsEntries = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
        else: # Load the original XML
            from BibleOrgSys.OriginalLanguages.Converters.GreekLexiconConverter import GreekStrongsFileConverter
            gStr = GreekStrongsFileConverter() # Create the empty object
            gStr.loadAndValidate( self.XMLFolder ) # Load the XML
            self.StrongsEntries = gStr.importDataToPython()
    # end of GreekLexicon.load


    def __str__( self ) -> str:
        """
        This method returns the string representation of the GreekLexicon object.

        @return: the name of the object formatted as a string
        @rtype: string
        """
        result = "Greek Strongs Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.StrongsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of Strong's Greek entries = {:,}").format( len(self.StrongsEntries) )
        return result
    # end of GreekLexicon.__str__


    def getStrongsEntryData( self, key:str ) -> Optional[str]:
        """
        The key is a Greek Strong's number (string) like 'G1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert key and key[0]=='G' and key[1:].isdigit()

        keyDigits = key[1:]
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries:
            return self.StrongsEntries[keyDigits]
    # end of GreekLexicon.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Greek Strong's number (string) like 'G1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert key and key[0]=='G' and key[1:].isdigit()
        keyDigits = key[1:]
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of GreekLexicon.getStrongsEntryField


    def getStrongsEntryHTML( self, key:str ) -> Optional[str]:
        """
        The key is a Greek Strong's number (string) like 'G1979'.

        Returns an HTML li entry for the given key.
        Returns None if the key is not found.

        e.g., for G1, returns:
            <li value="1" id="nt:1">
            <span class="originalWord" title="{A}" xml:lang="grk">Α</span>
                of Hebrew origin; the first letter of the alphabet; figuratively, only (from its use as a numeral) the first:
                --Alpha. Often used (usually <translit="án" unicode="ἄν" BETA="A)/N">,
                before a vowel) also in composition (as a contraction from <span class="StrongsRef">G427</span> )
                in the sense of privation; so, in many words, beginning with this letter;
                occasionally in the sense of union (as a contraction of <span class="StrongsRef">G260</span> ).
            </li>
        """
        vPrint( 'Never', debuggingThisModule, f"GreekLexicon.getStrongsEntryHTML( {key} )…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert key and key[0]=='G' and key[1:].isdigit()
        keyDigits = key[1:].lstrip( '0' ) # Remove leading zeroes
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            vPrint( 'Verbose', debuggingThisModule, f"  GreekLexicon.getStrongsEntryHTML got entry: {entry}" )
            wordEntry = '{}'.format( entry['Entry'].replace('<StrongsRef>','<span class="StrongsRef">').replace('</StrongsRef>','</span>').replace('<def>','<span class="def">').replace('</def>','</span>') ) \
                        if 'Entry' in entry else ''
            vPrint( 'Verbose', debuggingThisModule, f"  GreekLexicon.getStrongsEntryHTML created wordEntry: {wordEntry}" )
            html = f'<span class="GreekWord" title="{keyDigits}" xml:lang="grk">{entry["word"][0]} ({entry["word"][1]})</span> {wordEntry}'
            vPrint( 'Verbose', debuggingThisModule, f"  GreekLexicon.getStrongsEntryHTML about to return: {html}" )
            return html
    # end of GreekLexicon.getStrongsEntryHTML
# end of GreekLexicon class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/morphgnt/strongs-dictionary-xml/' ) # Greek lexicon folder

    # Demonstrate the Greek Lexicon class
    vPrint( 'Normal', debuggingThisModule, "\nDemonstrating the Greek Lexicon class…" )
    hl = GreekLexicon( testFolder ) # Load and process the XML
    vPrint( 'Quiet', debuggingThisModule, hl ) # Just print a summary
    vPrint( 'Quiet', debuggingThisModule, '' )
    for strongsKey in ('G1','G123','G165','G1732','G1979','G2011','G5624','G5625',): # Last one is invalid
        vPrint( 'Quiet', debuggingThisModule, '\n' + strongsKey )
        vPrint( 'Quiet', debuggingThisModule, " Data:", hl.getStrongsEntryData( strongsKey ) )
        vPrint( 'Quiet', debuggingThisModule, " Pronunciation:", hl.getStrongsEntryField( strongsKey, 'pronunciation' ) )
        vPrint( 'Quiet', debuggingThisModule, " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
        break
# end of GreekLexicon.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/morphgnt/strongs-dictionary-xml/' ) # Greek lexicon folder

    # demonstrate the Greek Lexicon class
    vPrint( 'Normal', debuggingThisModule, "\nDemonstrating the Greek Lexicon class…" )
    hl = GreekLexicon( testFolder ) # Load and process the XML
    vPrint( 'Quiet', debuggingThisModule, hl ) # Just print a summary
    vPrint( 'Quiet', debuggingThisModule, '' )
    for strongsKey in ('G1','G123','G165','G1732','G1979','G2011','G5624','G5625',): # Last one is invalid
        vPrint( 'Quiet', debuggingThisModule, '\n' + strongsKey )
        vPrint( 'Quiet', debuggingThisModule, " Data:", hl.getStrongsEntryData( strongsKey ) )
        vPrint( 'Quiet', debuggingThisModule, " Pronunciation:", hl.getStrongsEntryField( strongsKey, 'pronunciation' ) )
        vPrint( 'Quiet', debuggingThisModule, " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
# end of GreekLexicon.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GreekLexicon.py
