#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# HebrewLexicon.py
#
# Module handling the Hebrew lexicon
#
# Copyright (C) 2011-2025 Robert Hunt
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
Module handling the OpenScriptures Hebrew lexicon.

    The classes are the ones for users to
        access the Strongs and Brown,Driver,Briggs lexical entries
        via various keys and in various formats.
"""
from gettext import gettext as _
import os.path
from pathlib import Path
import re

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2025-03-17' # by RJH
SHORT_PROGRAM_NAME = "HebrewLexicon"
PROGRAM_NAME = "Hebrew Lexicon handler"
PROGRAM_VERSION = '0.21'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



class HebrewLexiconIndex:
    """
    Class for handling an Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder=None ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconIndex.__init__( {} )".format( XMLFolder ) )
        self.XMLFolder = XMLFolder
    # end of HebrewLexiconIndex.__init__


    def load( self ) -> None:
        """
        Load from the XML
        """
        from BibleOrgSys.OriginalLanguages.Converters.HebrewLexiconConverter import AugmentedStrongsIndexFileConverter, LexicalIndexFileConverter

        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, _("HebrewLexiconIndex.load()") )
        if self.XMLFolder is None:
            self.XMLFolder = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'HebrewLexicon/' ) # Hebrew lexicon folder

        hASIndex = AugmentedStrongsIndexFileConverter() # Create the empty object
        hASIndex.loadAndValidate( self.XMLFolder ) # Load the XML
        self.indexEntries1, self.indexEntries2 = hASIndex.importDataToPython()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.indexEntries1) == len(self.indexEntries2)
        hLexIndex = LexicalIndexFileConverter() # Create the empty object
        hLexIndex.loadAndValidate( self.XMLFolder ) # Load the XML
        self.indexEntries = hLexIndex.importDataToPython()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.indexEntries) == 2
    # end of HebrewLexiconIndex.load()


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        print( "Here in HebrewLexiconIndex.__str__" )
        result = "Hebrew Lexicon Index object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of augmented Strong's index entries = {:,}").format( len(self.indexEntries1) )
        result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {:,}").format( len(self.indexEntries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {:,}").format( len(self.indexEntries['arc']) )
        return result
    # end of HebrewLexiconIndex.__str__


    def getBrDrBrCodeFromHebrewStrongsNumber( self, key:str ) -> str|None:
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'
            or raises KeyError
        """
        if key and key[0]=='H': key = key[1:] # Remove any leading 'H'
        # keyDigits = key[1:]
        return self.indexEntries1[key]
    # end of HebrewLexiconIndex.getBrDrBrCodeFromHebrewStrongsNumber


    def _getStrongsNumberFromLexiconCode1( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if key in self.indexEntries2: return self.indexEntries2[key]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode1


    def _getStrongsNumberFromLexiconCode2( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        keyDigits = key[1:]
        if key in self.indexEntries['heb']: return self.indexEntries['heb'][key][4]
        if key in self.indexEntries['arc']: return self.indexEntries['arc'][key][4]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode2


    def getStrongsNumberFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        keyDigits = key[1:]
        if BibleOrgSysGlobals.debugFlag:
            result1 = self._getStrongsNumberFromLexiconCode1( key )
            result2 = self._getStrongsNumberFromLexiconCode2( key )
            assert result1 == result2
            return result1
        # Normally…
        if key in self.indexEntries2: return self.indexEntries2[key]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode


    def getBrDrBrCodeFromLexiconCode( self, key ):
        """
        The key is a three letter internal code like 'aac'.

        Returns a BrDrBr code, e.g., 'm.ba.aa'
        """
        keyDigits = key[1:]
        if key in self.indexEntries['heb']: return self.indexEntries['heb'][key][3]
        if key in self.indexEntries['arc']: return self.indexEntries['arc'][key][3]
    # end of HebrewLexiconIndex.getBrDrBrCodeFromLexiconCode


    def getBrDrBrCodeFromStrongsNumber( self, key ):
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HebrewLexiconIndex.getBrDrBrCodeFromStrongsNumber( {} )".format( key ) )

        if key and key[0]=='H': key = key[1:] # Remove any leading 'H'
        #keyDigits = key[1:]
        if key in self.indexEntries1:
            internalCode = self.indexEntries1[key]
            return self.getBrDrBrCodeFromLexiconCode( internalCode )
    # end of HebrewLexiconIndex.getBrDrBrCodeFromStrongsNumber


    def getTWOTCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BrDrBr code, e.g., '4a'
        """
        keyDigits = key[1:]
        if key in self.indexEntries['heb']: return self.indexEntries['heb'][key][6]
        if key in self.indexEntries['arc']: return self.indexEntries['arc'][key][6]
    # end of HebrewLexiconIndex.getTWOTCodeFromLexiconCode
# end of HebrewLexiconIndex class



class HebrewLexiconSimple:
    """
    Simple class for handling a Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder=None, preload=False ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.__init__( {} )".format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        self.StrongsEntries = self.BrownDriverBriggsEntries = None
        if preload: self.load()
    # end of HebrewLexiconSimple.__init__


    def load( self ):
        """
        Load the actual lexicon (slow).
        """
        from BibleOrgSys.OriginalLanguages.Converters.HebrewLexiconConverter import HebrewStrongsFileConverter, BrownDriverBriggsFileConverter

        if self.XMLFolder is None:
            self.XMLFolder = Path( '/srv/Programming/WebDevelopment/OpenScriptures/HebrewLexicon/' ) # Hebrew lexicon folder

        hStr = HebrewStrongsFileConverter() # Create the empty object
        hStr.loadAndValidate( self.XMLFolder ) # Load the XML
        self.StrongsEntries = hStr.importDataToPython()

        hBrDrBr = BrownDriverBriggsFileConverter() # Create the empty object
        hBrDrBr.loadAndValidate( self.XMLFolder ) # Load the XML
        self.BrownDriverBriggsEntries = hBrDrBr.importDataToPython()
    # end of HebrewLexiconSimple.load


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew Simple Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.StrongsEntries:
            result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {:,}").format( len(self.StrongsEntries) )
        if self.BrownDriverBriggsEntries:
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Hebrew entries = {:,}").format( len(self.BrownDriverBriggsEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Aramaic entries = {:,}").format( len(self.BrownDriverBriggsEntries['arc']) )
        return result
    # end of HebrewLexiconSimple.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getStrongsEntryData( {!r} )".format( key ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries: return self.StrongsEntries[keyDigits]
    # end of HebrewLexiconSimple.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getStrongsEntryField( {!r}, {!r} )".format( key, fieldName ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of HebrewLexiconSimple.getStrongsEntryField


    def getStrongsEntryHTML( self, key:str ) -> str|None:
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
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getStrongsEntryHTML( {key} )…" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        #if key == 'H1':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Should be:" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'sHTML: <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word; father, in a literal and immediate, or figurative and remote application): <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>. Compare names in "Abi-".</li>' )
        keyDigits = key[1:].lstrip( '0' ) # Remove leading zeroes
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            for j, (subentry,article) in enumerate( entry.items() ):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {j} {subentry}={article}" )
            wordEntry = entry['word']
            wordHTML = '<span class="HebrewWord" xml:lang="hbo">{}</span> ({}) {} ({})'.format( wordEntry[0], wordEntry[3], wordEntry[1], wordEntry[2] )
            sourceHTML = '<span class="Source"><b>Source:</b> {}</span>'.format( entry['source'].replace('<w>','<span class="Word">').replace('</w>','</span>') \
                        .replace('<def>','<span class="Def">').replace('</def>','</span>') ) \
                            if 'source' in entry else ''
            match = re.search( '<w xlit="(.+?)" pron="(.+?)">', sourceHTML )
            if match:
                sourceHTML = sourceHTML[:match.start()] + '<span class="Hebrew" xml:lang="hbo">' + sourceHTML[match.end():]
                #xlit, pron = match.group(1), match.group(2)
            match = re.search( '<w pron="(.+?)" xlit="(.+?)">', sourceHTML )
            if match:
                sourceHTML = sourceHTML[:match.start()] + '<span class="Hebrew" xml:lang="hbo">' + sourceHTML[match.end():]
                #pron, xlit = match.group(1), match.group(2)
            match = re.search( '<w src="(.+?)">', sourceHTML )
            if match:
                src = match.group(1)
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert src[0] == 'H'
                sourceHTML = sourceHTML[:match.start()] + '<span class="Strongs" ref="{}">H'.format( src ) + sourceHTML[match.end():]
            meaningHTML = '<span class="Meaning"><b>Meaning:</b> {}</span>'.format( entry['meaning'] \
                        .replace('<def>','<span class="Def">').replace('</def>','</span>') ) \
                            if 'meaning' in entry else ''
            usageHTML = '<span class="KJVUsage"><b>KJV:</b> {}</span>'.format( entry['usage'] ) \
                            if 'usage' in entry else ''
            #html = '<li value="{}" id="ot:{}"><span class="originalWord" title="{{{}}}" xml:lang="hbo">{}</span><br>{}<br>{}<br>{}</li>' \
                #.format( keyDigits, keyDigits, entry['word'][2], entry['word'][0], sourceHTML, meaningHTML, usageHTML )
            html = f'{wordHTML}<br>{sourceHTML}<br>{meaningHTML}<br>{usageHTML}' \
                            .replace( ' ,', ',' ).replace( ' ;', ';' ) # clean it up
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexiconSimple.getStrongsEntryHTML about to return: {html}" )
            return html
    # end of HebrewLexiconSimple.getStrongsEntryHTML


    def getBrDrBrEntryData( self, key ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getBrDrBrEntryData( {!r} )".format( key ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        if key in self.BrownDriverBriggsEntries['heb']: return self.BrownDriverBriggsEntries['heb'][key]
        if key in self.BrownDriverBriggsEntries['arc']: return self.BrownDriverBriggsEntries['arc'][key]
    # end of HebrewLexiconSimple.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key, fieldName ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getBrDrBrEntryField( {!r}, {!r} )".format( key, fieldName ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getBrDrBrEntryField entry: {}".format( entry ) )
        if entry:
            if fieldName == 'status': return entry[2]
            return entry[0] # What are these fields?
    # end of HebrewLexiconSimple.getBrDrBrEntryField


    def getBrDrBrEntryHTML( self, key ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexiconSimple.getBrDrBrEntryHTML( {!r} )".format( key ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexiconSimple.getBrDrBrEntryHTML got entry: {entry}" )
        if entry:
            mainEntry = entry[0] \
                .replace( '<sense>', '<span class="Sense">' ).replace( '</sense>', '</span>' ) \
                .replace( '<w>', '<span class="HebrewWord">' ).replace( '</w>', '</span>' ) \
                .replace( '<pos>', '<span class="POS">' ).replace( '</pos>', '</span>' ) \
                .replace( '<ref>', '<span class="Ref">' ).replace( '</ref>', '</span>' ) \
                .replace( '<def>', '<span class="Def">' ).replace( '</def>', '</span>' )
            match = re.search( '<type="(.+?)" id="(.+?)">', mainEntry )
            if match:
                #logging.warning( "Removed {} status field {} from {}" \
                    #.format( entryID, repr(mainEntry[match.start():match.end()]), repr(mainEntry) ) )
                hType, hId = match.group(1), match.group(2)
                mainEntry = mainEntry[:match.start()] + '<b>Type:</b> {}<br>'.format( hType) + mainEntry[match.end():]
            match = re.search( '<id="(.+?)" type="(.+?)">', mainEntry )
            if match:
                #logging.warning( "Removed {} status field {} from {}" \
                    #.format( entryID, repr(mainEntry[match.start():match.end()]), repr(mainEntry) ) )
                hId, hType = match.group(1), match.group(2)
                mainEntry = mainEntry[:match.start()] + '<b>Type:</b> {}<br>'.format( hType) + mainEntry[match.end():]
            html = f'{mainEntry} <span class="Status">{{{entry[1]}}}</span>'
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexiconSimple.getBrDrBrEntryHTML about to return: {html}" )
            return html
    # end of HebrewLexiconSimple.getBrDrBrEntryHTML
# end of HebrewLexiconSimple class



class HebrewLexicon( HebrewLexiconSimple ):
    """
    Class for handling a Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    However, it does also use the HebrewLexiconSimple class
        so it can be more intelligent with coverting code systems.

    It automagically accepts Hebrew and Greek Strong's numbers (like H123 and G532)
        plus BrDrBr (Hebrew) codes (like a.gq.ab).
    """
    def __init__( self, XMLFolder=None, preload=False ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexicon.__init__( {} )".format( XMLFolder ) )
        HebrewLexiconSimple.__init__( self, XMLFolder )
        self.XMLFolder = XMLFolder
        self.hlix = None
        if preload: self.load()
    # end of HebrewLexicon.__init__


    def load( self ) -> None:
        """
        Load the pickled data if possible.

        Otherwise lLoad the actual XML lexicon (slow).
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexicon.load()" )
        standardPickleFilepath = BibleOrgSysGlobals.BOS_DISTRIBUTED_FILES_FOLDERPATH.joinpath( 'HebrewLexicon_Tables.1.pickle' )
        if standardPickleFilepath.is_file():
            import pickle
            self.hlix = HebrewLexiconIndex()
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading pickle file {standardPickleFilepath}…" )
            with open( standardPickleFilepath, 'rb') as pickleFile: # The protocol version used is detected automatically, so we do not have to specify it
                self.hlix.indexEntries1 = pickle.load( pickleFile ) # Augmented Strongs
                self.hlix.indexEntries2 = pickle.load( pickleFile ) # Augmented Strongs
                self.hlix.indexEntries = pickle.load( pickleFile ) # lix.entries
                self.StrongsEntries = pickle.load( pickleFile ) # hlc.entries
                self.BrownDriverBriggsEntries = pickle.load( pickleFile ) # bdb.entries
        else: # Load the original XML
            HebrewLexiconSimple.load( self )
            assert self.hlix is None
            self.hlix = HebrewLexiconIndex( self.XMLFolder ) # Load and process the XML
            self.hlix.load()
    # end of HebrewLexicon.load


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Hebrew Lexicon object formatted as a string
        @rtype: string
        """
        result = "Hebrew Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.hlix is not None:
            result += ('\n' if result else '') + "  " + _("Number of augmented Strong's index entries = {:,}").format( len(self.hlix.indexEntries1) )
            result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {:,}").format( len(self.hlix.indexEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {:,}").format( len(self.hlix.indexEntries['arc']) )
        if self.StrongsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {:,}").format( len(self.StrongsEntries) )
        if self.BrownDriverBriggsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Hebrew entries = {:,}").format( len(self.BrownDriverBriggsEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Aramaic entries = {:,}").format( len(self.BrownDriverBriggsEntries['arc']) )
        return result
    # end of HebrewLexicon.__str__


    def getBrDrBrEntryData( self, key:str ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.
            but can also be a Strong's number (with or without the leading H)

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexicon.getBrDrBrEntryData( {!r} )".format( key ) )
        if '.' not in key: # assume it's a Strongs code then
            if self.hlix is None: self.load()
            key = self.hlix.getBrDrBrCodeFromStrongsNumber( key )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryData( self, key )
    # end of HebrewLexicon.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key:str, fieldName:str ) -> str|None:
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
            but can also be a Strong's number (with or without the leading H)
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.

        Returns None if the key or fieldName is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "HebrewLexicon.getBrDrBrEntryField( {!r}, {!r} )".format( key, fieldName ) )

        if '.' not in key: # assume it's a Strongs code then
            if self.hlix is None: self.load()
            key = self.hlix.getBrDrBrCodeFromStrongsNumber( key )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HebrewLexicon.getBrDrBrEntryField got key: {}".format( key ) )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryField( self, key, fieldName ) # Recursive call
    # end of HebrewLexicon.getBrDrBrEntryField


    def getBrDrBrEntryHTML( self, key:str ) -> str|None:
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
            but can also be a Strong's number (with or without the leading H)

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexicon.getBrDrBrEntryHTML( {key} )…" )
        if '.' not in key: # assume it's a Strongs code then
            if self.hlix is None: self.load()
            key = self.hlix.getBrDrBrCodeFromStrongsNumber( key )
        if key:
            html = HebrewLexiconSimple.getBrDrBrEntryHTML( self, key )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexicon.getBrDrBrEntryHTML about to return: {html}" )
            return html
    # end of HebrewLexicon.getBrDrBrEntryHTML
# end of HebrewLexicon class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # demonstrate the Hebrew Lexicon Index class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the Hebrew Lexicon Index class…" )
        hlix = HebrewLexiconIndex() # Load and process the XML
        hlix.load()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hlix ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for 2 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( '2' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for H8674 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( 'H8674' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for H8675 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( 'H8675' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for aac are", hlix.getStrongsNumberFromLexiconCode('aac'), hlix.getBrDrBrCodeFromLexiconCode('aac'), hlix.getTWOTCodeFromLexiconCode('aac') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for nyy are", hlix.getStrongsNumberFromLexiconCode('nyy'), hlix.getBrDrBrCodeFromLexiconCode('nyy'), hlix.getTWOTCodeFromLexiconCode('nyy') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for pdc are", hlix.getStrongsNumberFromLexiconCode('pdc'), hlix.getBrDrBrCodeFromLexiconCode('pdc'), hlix.getTWOTCodeFromLexiconCode('pdc') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for pdd are", hlix.getStrongsNumberFromLexiconCode('pdd'), hlix.getBrDrBrCodeFromLexiconCode('pdd'), hlix.getTWOTCodeFromLexiconCode('pdd') )

    if 1: # demonstrate the simple Hebrew Lexicon class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the simple Hebrew Lexicon class…" )
        hls = HebrewLexiconSimple() # Load and process the XML
        hls.load()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hls ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + strongsKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hls.getStrongsEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Usage:", hls.getStrongsEntryField( strongsKey, 'usage' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hls.getStrongsEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + BrDrBrKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hls.getBrDrBrEntryData( BrDrBrKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hls.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hls.getBrDrBrEntryHTML( BrDrBrKey ) )

    if 1: # demonstrate the Hebrew Lexicon class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the Hebrew Lexicon class…" )
        hl = HebrewLexicon() # Load and process the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hl ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + strongsKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getStrongsEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Usage:", hl.getStrongsEntryField( strongsKey, 'usage' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getBrDrBrEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hl.getBrDrBrEntryField( strongsKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getBrDrBrEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + BrDrBrKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getBrDrBrEntryData( BrDrBrKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hl.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getBrDrBrEntryHTML( BrDrBrKey ) )
# end of HebrewLexicon.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # demonstrate the Hebrew Lexicon Index class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the Hebrew Lexicon Index class…" )
        hlix = HebrewLexiconIndex() # Load and process the XML
        hlix.load()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hlix ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for 2 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( '2' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for H8674 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( 'H8674' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Code for H8675 is", hlix.getBrDrBrCodeFromHebrewStrongsNumber( 'H8675' ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for aac are", hlix.getStrongsNumberFromLexiconCode('aac'), hlix.getBrDrBrCodeFromLexiconCode('aac'), hlix.getTWOTCodeFromLexiconCode('aac') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for nyy are", hlix.getStrongsNumberFromLexiconCode('nyy'), hlix.getBrDrBrCodeFromLexiconCode('nyy'), hlix.getTWOTCodeFromLexiconCode('nyy') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for pdc are", hlix.getStrongsNumberFromLexiconCode('pdc'), hlix.getBrDrBrCodeFromLexiconCode('pdc'), hlix.getTWOTCodeFromLexiconCode('pdc') )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Codes for pdd are", hlix.getStrongsNumberFromLexiconCode('pdd'), hlix.getBrDrBrCodeFromLexiconCode('pdd'), hlix.getTWOTCodeFromLexiconCode('pdd') )

    if 1: # demonstrate the simple Hebrew Lexicon class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the simple Hebrew Lexicon class…" )
        hls = HebrewLexiconSimple() # Load and process the XML
        hls.load()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hls ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + strongsKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hls.getStrongsEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Usage:", hls.getStrongsEntryField( strongsKey, 'usage' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hls.getStrongsEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + BrDrBrKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hls.getBrDrBrEntryData( BrDrBrKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hls.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hls.getBrDrBrEntryHTML( BrDrBrKey ) )

    if 1: # demonstrate the Hebrew Lexicon class
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nDemonstrating the Hebrew Lexicon class…" )
        hl = HebrewLexicon() # Load and process the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, hl ) # Just print a summary
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + strongsKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getStrongsEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Usage:", hl.getStrongsEntryField( strongsKey, 'usage' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getBrDrBrEntryData( strongsKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hl.getBrDrBrEntryField( strongsKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getBrDrBrEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\n' + BrDrBrKey )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Data:", hl.getBrDrBrEntryData( BrDrBrKey ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " Status:", hl.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " HTML:", hl.getBrDrBrEntryHTML( BrDrBrKey ) )
# end of HebrewLexicon.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HebrewLexicon.py
