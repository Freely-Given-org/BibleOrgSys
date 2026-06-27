#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# HebrewLexicon.py
#
# Module handling the Hebrew lexicon
#
# Copyright (C) 2011-2026 Robert Hunt
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

CHANGELOG:
    2026-06-05 Handling BrDrBr passing the full XML entry
"""
from pathlib import Path
import logging
import re

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2026-06-12' # by RJH
SHORT_PROGRAM_NAME = "HebrewLexicon"
PROGRAM_NAME = "Hebrew Lexicon handler"
PROGRAM_VERSION = '0.30'
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
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconIndex.__init__( {XMLFolder} )" )
        self.XMLFolder = XMLFolder
    # end of HebrewLexiconIndex.__init__


    def load( self ) -> None:
        """
        Load from the XML
        """
        from BibleOrgSys.OriginalLanguages.Converters.HebrewLexiconConverter import AugmentedStrongsIndexFileConverter, LexicalIndexFileConverter

        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "HebrewLexiconIndex.load()" )
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
        result = "Hebrew Lexicon Index object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + f"Version: {self.version} "
        #if self.date: result += ('\n' if result else '') + f"Date: {self.date}"
        result += ('\n' if result else '') + "  " + f"Number of augmented Strong's index entries = {len(self.indexEntries1):,}"
        result += ('\n' if result else '') + "  " + f"Number of Hebrew lexical index entries = {len(self.indexEntries['heb']):,}"
        result += ('\n' if result else '') + "  " + f"Number of Aramaic lexical index entries = {len(self.indexEntries['arc']):,}"
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
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HebrewLexiconIndex.getBrDrBrCodeFromStrongsNumber( {key} )" )

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
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.__init__( {XMLFolder} )" )
        self.XMLFolder = XMLFolder
        self.StrongsEntries = self.BrownDriverBriggsXMLEntries = self.BrownDriverBriggsEntries = None
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
        self.BrownDriverBriggsXMLEntries, self.BrownDriverBriggsEntries = hBrDrBr.importDataToPython()
    # end of HebrewLexiconSimple.load


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew Simple Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + f"Version: {self.version} "
        #if self.date: result += ('\n' if result else '') + f"Date: {self.date}"
        if self.StrongsEntries:
            result += ('\n' if result else '') + "  " + f"Number of Strong's Hebrew entries = {len(self.StrongsEntries):,}"
        if self.BrownDriverBriggsEntries:
            result += ('\n' if result else '') + "  " + f"Number of BrDrBr Hebrew entries = {len(self.BrownDriverBriggsEntries['heb']):,}"
            result += ('\n' if result else '') + "  " + f"Number of BrDrBr Aramaic entries = {len(self.BrownDriverBriggsEntries['arc']):,}"
        return result
    # end of HebrewLexiconSimple.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getStrongsEntryData( {key!r} )" )
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
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getStrongsEntryField( {key!r}, {fieldName!r} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of HebrewLexiconSimple.getStrongsEntryField


    simple_wRE = re.compile( '<w src="([^"]+?)">' )
    complex_wRE1 = re.compile( '<w pron="(.+?)" xlit="(.+?)">' )
    complex_wRE2 = re.compile( '<w xlit="(.+?)" pron="(.+?)">' )
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

        # def repairField( compiledRE, field ) -> str:
        #     """
        #     """
        #     for _ in range( 9 ):
        #         match = compiledRE.search( field )
        #         if match:
        #             src = match.group( 1 )
        #             assert src[0] == 'H' and src[1:].isdigit(), f"{entry=} {match=}"
        #             field = f'{field[:match.start()]}<span class="Strongs" ref="{src}">H{field[match.end():]}'
        #         else: break
        #     else: need_more_repair_field_range
        #     return field.replace( '</w>', '</span>' )
        # # end of repairField
        
        #if key == 'H1':
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Should be:" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'sHTML: <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word; father, in a literal and immediate, or figurative and remote application): <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>. Compare names in "Abi-".</li>' )
        keyDigits = key[1:].lstrip( '0' ) # Remove leading zeroes
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            if DEBUGGING_THIS_MODULE:
                for j, (subentry,article) in enumerate( entry.items() ):
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Strongs entry {j}: {subentry}={article}" )
            wordEntry = entry['word']
            wordHTML = f'<span class="HebrewWord" xml:lang="hbo">{wordEntry[0]}</span> ({wordEntry[3]}) {wordEntry[1]} ({wordEntry[2]})'

            sourceHTML = '<span class="Source"><b>Source:</b> {}</span>'.format( entry['source'].replace('<w>','<span class="Word">').replace('</w>','</span>') \
                        .replace('<def>','<span class="Def">').replace('</def>','</span>') ) \
                            if 'source' in entry else ''
            for _ in range( 5 ):
                match = self.complex_wRE2.search( sourceHTML )
                if match:
                    sourceHTML = sourceHTML[:match.start()] + '<span class="Hebrew" xml:lang="hbo" dir="rtl">' + sourceHTML[match.end():]
                    #xlit, pron = match.group(1), match.group(2)
                else: break
            else: bad_wRE2
            for _ in range( 10 ):
                match = self.complex_wRE1.search( sourceHTML )
                if match:
                    sourceHTML = sourceHTML[:match.start()] + '<span class="Hebrew" xml:lang="hbo" dir="rtl">' + sourceHTML[match.end():]
                    #pron, xlit = match.group(1), match.group(2)
                else: break
            else: bad_wRE1
            for _ in range( 8 ):
                match = self.simple_wRE.search( sourceHTML )
                if match:
                    src = match.group( 1 )
                    assert src[0] == 'H' and src[1:].isdigit(), f"{entry=} {match=}"
                    sourceHTML = f'{sourceHTML[:match.start()]}<span class="Strongs" ref="{src}">H{sourceHTML[match.end():]}'
                else: break
            else: need_more_source_w_range
            sourceHTML = sourceHTML.replace( '</w>', '</span>' )

            meaningHTML = '<span class="Meaning"><b>Meaning:</b> {}</span>'.format( entry['meaning'] \
                        .replace('<def>','<span class="Def">').replace('</def>','</span>') ) \
                            if 'meaning' in entry else ''
            for _ in range( 5 ):
                match = self.simple_wRE.search( meaningHTML )
                if match:
                    src = match.group( 1 )
                    assert src[0] == 'H' and src[1:].isdigit(), f"{entry=} {match=}"
                    meaningHTML = f'{meaningHTML[:match.start()]}<span class="Strongs" ref="{src}">H{meaningHTML[match.end():]}'
                else: break
            else: need_more_usage_w_range
            meaningHTML = meaningHTML.replace( '</w>', '</span>' )

            usageHTML = '<span class="KJVUsage"><b>KJV:</b> {}</span>'.format( entry['usage'] ) \
                            if 'usage' in entry else ''
            for _ in range( 5 ):
                match = self.simple_wRE.search( usageHTML )
                if match:
                    src = match.group( 1 )
                    assert src[0] == 'H' and src[1:].isdigit(), f"{entry=} {match=}"
                    usageHTML = f'{usageHTML[:match.start()]}<span class="Strongs" ref="{src}">H{usageHTML[match.end():]}'
                else: break
            else: need_more_usage_w_range
            for _ in range( 5 ):
                match = self.complex_wRE1.search( usageHTML )
                if match:
                    usageHTML = usageHTML[:match.start()] + '<span class="Hebrew" xml:lang="hbo" dir="rtl">' + usageHTML[match.end():]
                    #pron, xlit = match.group(1), match.group(2)
                else: break
            else: bad_wRE1
            usageHTML = usageHTML.replace( '</w>', '</span>' )

            #html = '<li value="{}" id="ot:{}"><span class="originalWord" title="{{{}}}" xml:lang="hbo">{}</span><br>{}<br>{}<br>{}</li>' \
                #.format( keyDigits, keyDigits, entry['word'][2], entry['word'][0], sourceHTML, meaningHTML, usageHTML )
            html = f'<p class=Strongs>{wordHTML}<br>{sourceHTML}<br>{meaningHTML}<br>{usageHTML}</p>' \
                            .replace( ' ,', ',' ).replace( ' ;', ';' ) # clean it up
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexiconSimple.getStrongsEntryHTML about to return: {html}" )
            assert '<w ' not in html, f"HebrewLexiconSimple.getStrongsEntryHTML: Unexpected {key} w span {html.count('<span')} {html.count('</span>')} from {html=}"
            assert html.count('<p') == html.count('</p>'), f"HebrewLexiconSimple.getStrongsEntryHTML: Mismatched {key} paragraphs {html.count('<p')} {html.count('</p>')} from {html=}"
            assert html.count('<span') == html.count('</span>'), f"HebrewLexiconSimple.getStrongsEntryHTML: Mismatched {key} spans {html.count('<span')} {html.count('</span>')} from {html=}"
            return html
    # end of HebrewLexiconSimple.getStrongsEntryHTML


    def getBrDrBrEntryData( self, key, getXML:bool=False ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getBrDrBrEntryData( {key!r} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        if key in self.BrownDriverBriggsEntries['heb']: return self.BrownDriverBriggsXMLEntries['heb'][key] if getXML else self.BrownDriverBriggsEntries['heb'][key]
        if key in self.BrownDriverBriggsEntries['arc']: return self.BrownDriverBriggsXMLEntries['arc'][key] if getXML else self.BrownDriverBriggsEntries['arc'][key]
    # end of HebrewLexiconSimple.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key, fieldName ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getBrDrBrEntryField( {key!r}, {fieldName!r} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getBrDrBrEntryField entry: {entry}" )
        if entry:
            if fieldName == 'status': return entry[2]
            return entry[0] # Return the name entry
    # end of HebrewLexiconSimple.getBrDrBrEntryField


    def getBrDrBrEntryHTML( self, key, getFull=False ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexiconSimple.getBrDrBrEntryHTML( {key!r} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key, getXML=getFull )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  HebrewLexiconSimple.getBrDrBrEntryHTML got entry: {entry}" )
        # print( f"  HebrewLexiconSimple.getBrDrBrEntryHTML {key=} got entry: {entry}" )
        if getFull: # We have the full XML entry to format
            namespace1 = '{http://openscriptures.github.com/morphhb/namespace}'
            namespace2 = '{http://www.w3.org/XML/1998/namespace}'

            openPcount = openLcount = 0
            def processDictEntries( upperEntry, level ):
                """
                For recursive calls
                """
                nonlocal openPcount, openLcount
                # print( f"{'  '*(level-1)}processDictEntries( {upperEntry.tag=}, {level=} ) {openPcount=} {openLcount=}" )
                # See if there's more than one definition
                defCount = 0
                for subEntry in upperEntry: # 'w','pos' (can be multiple),'def' (can be multiple),'status'
                    if subEntry.tag == f'{namespace1}def':
                        defCount += 1

                entriesHtml = ''
                if openLcount > level:
                    entriesHtml = f'{entriesHtml}</ul>'
                    openLcount-= 1

                for subEntry in upperEntry: # 'w','pos' (can be multiple),'def' (can be multiple),'status'
                    subEntryTag = subEntry.tag.replace( namespace1, '' )
                    if subEntryTag == 'status': continue # Not interested here
                    # print( f"{'  '*level}{key=} {level=} {defCount=} {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)} {subEntry.text=} {subEntry.tail=}" )
                    if subEntryTag == 'w':
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        wSrc = None
                        for attribName,attribValue in subEntry.items():
                            if attribName == 'src':
                                wSrc = attribValue
                            else: logging.critical( f"Unprocessed {attribName} {attribValue=} attribute in 'w' entry"); assert False
                        if openPcount > 0:
                            entriesHtml = f'{entriesHtml}</p>'
                            openPcount -= 1
                        entriesHtml = f'''{entriesHtml}\n<p><span class="word" dir="rtl">{subEntry.text}</span> {subEntry.tail}{"occurrences" if subEntry.tail and subEntry.tail.strip().isdigit() else ''}'''
                        openPcount += 1
                    elif subEntryTag == 'pos':
                        assert BibleOrgSysGlobals.checkXMLNoAttributes( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        if openPcount == 0:
                            entriesHtml = f'{entriesHtml}\n<p>'
                            openPcount += 1
                        entriesHtml = f'{entriesHtml} <span class="POS">{subEntry.text}</span>{subEntry.tail}'
                    elif subEntryTag == 'foreign':
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        if openPcount == 0:
                            entriesHtml = f'{entriesHtml}\n<p>'
                            openPcount += 1
                        fLang = None
                        for attribName,attribValue in subEntry.items():
                            if attribName == f'{namespace2}lang':
                                fLang = attribValue
                            else: logging.critical( f"Unprocessed {attribName} {attribValue=} attribute in 'foreign' entry"); assert False
                        entriesHtml = f'{entriesHtml} <span class="foreign">lang={fLang}: {subEntry.text}</span>{subEntry.tail}'
                    elif subEntryTag == 'stem':
                        assert BibleOrgSysGlobals.checkXMLNoAttributes( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        if openPcount == 0:
                            entriesHtml = f'{entriesHtml}\n<p>'
                            openPcount += 1
                        entriesHtml = f'{entriesHtml} <span class="Stem">{subEntry.text}</span>{subEntry.tail}'
                    elif subEntryTag == 'def':
                        assert BibleOrgSysGlobals.checkXMLNoAttributes( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        entriesHtml = f'{entriesHtml} <span class="Def">{subEntry.text}</span>{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}'
                    elif subEntryTag == 'sense': # we ignore the 'n' attribute here
                        if openPcount > 0:
                            entriesHtml = f'{entriesHtml}</p>'
                            openPcount -= 1
                        if openLcount < level:
                            entriesHtml = f'{entriesHtml}\n<ul>'
                            openLcount += 1
                        senseN = None
                        for attribName,attribValue in subEntry.items():
                            if attribName == 'n':
                                senseN = attribValue # Can be a digit '1', or a character 'a', or a Roman numeral 'II
                            else: logging.critical( f"Unprocessed {attribName} {attribValue=} attribute in 'sense' entry"); assert False
                        insertHtml = processDictEntries( subEntry, level+1 ) # Recursive call
                        entriesHtml = f'''{entriesHtml}\n<li class="Sense">{f'<span class="senseNum">{senseN}</span> ' if senseN else ''}{subEntry.text if subEntry.text else ''}{insertHtml}{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}</li>'''
                        if openLcount > level:
                            entriesHtml = f'{entriesHtml}</ul>'
                            openLcount -= 1
                    elif subEntryTag == 'ref': # We ignore the 'r' attribute which is an OSIS ref (useful for making a link)
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        refR = None
                        for attribName,attribValue in subEntry.items():
                            if attribName == 'r':
                                refR = attribValue
                            else: logging.critical( f"Unprocessed {attribName} {attribValue=} attribute in 'ref' entry"); assert False
                        # print( f"Why is ref {key=} {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)=} {subEntry.text=} {subEntry.tail=}" )
                        entriesHtml = f'{entriesHtml} <span class="ref"">{subEntry.text}</span>{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}'
                    elif subEntryTag == 'em':
                        assert BibleOrgSysGlobals.checkXMLNoAttributes( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        # print( f"What is EM {key=} {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)=} {subEntry.text=} {subEntry.tail=}" )
                        entriesHtml = f'{entriesHtml} <span class="Em">{subEntry.text}</span>{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}'
                    elif subEntryTag == 'asp':
                        assert BibleOrgSysGlobals.checkXMLNoAttributes( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        # print( f"What is ASP {key=} {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)=} {subEntry.text=} {subEntry.tail=}" )
                        entriesHtml = f'{entriesHtml} <span class="Asp">{subEntry.text}</span>{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}'
                    elif subEntryTag == 'page': # has attribute like 'p=2'
                        assert BibleOrgSysGlobals.checkXMLNoText( subEntry, subEntryTag )
                        assert BibleOrgSysGlobals.checkXMLNoSubelements( subEntry, subEntryTag )
                        # print( f"Why is page {key=} {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)=} {subEntry.text=} {subEntry.tail=}" )
                        entriesHtml = f'{entriesHtml}\n<br>{'' if BibleOrgSysGlobals.isBlank(subEntry.tail) else subEntry.tail}'
                    else:
                        logging.critical( f"    Unprocessed {subEntryTag=} {[f'{attribName}={attribValue}' for attribName,attribValue in subEntry.items()]} {len(subEntry)=} {subEntry.text=} {subEntry.tail=}" )
                        assert False, "We want to stop here"
                    assert openPcount < 2 # Shouldn't have nested paragraphs in HTML
                if openPcount:
                    entriesHtml = f'{entriesHtml}</p>'
                    openPcount -= 1
                if openLcount >= level:
                    entriesHtml = f'{entriesHtml}</ul>'
                    openLcount -= 1
                assert namespace1 not in entriesHtml, f"{namespace1=} left in {key} {entriesHtml=}"
                assert namespace2 not in entriesHtml, f"{namespace2=} left in {key} {entriesHtml=}"
                assert '<d' not in entriesHtml, f"<d left in {key} {entriesHtml=}"
                assert '<n' not in entriesHtml, f"<n left in {key} {entriesHtml=}"
                assert entriesHtml.count('<p') == entriesHtml.count('</p>'), f"HebrewLexiconSimple.getBrDrBrEntryHTML: Mismatched {key} paragraphs {entriesHtml.count('<p')} {entriesHtml.count('</p>')} from {entriesHtml=}"
                assert entriesHtml.count('<span') == entriesHtml.count('</span>'), f"HebrewLexiconSimple.getBrDrBrEntryHTML: Mismatched {key} spans {entriesHtml.count('<span')} {entriesHtml.count('</span>')} from {entriesHtml=}"
                return entriesHtml
            # end of processDictEntries


            html = f'<p class="Key">{key}</p>{processDictEntries( entry, 1 )}'
            if openPcount:
                assert not html.endswith( '</p>' )
                html = f'{html}</p>'
                openPcount -= 1
                assert openPcount == 0
            while openLcount:
                html = f'{html}</ul>'
                openLcount-= 1

            assert namespace1 not in html, f"{namespace1=} left in {key} {html=}"
            assert namespace2 not in html, f"{namespace2=} left in {key} {html=}"
            assert '<d' not in html, f"<d left in {key} {html=}"
            assert '<n' not in html, f"<n left in {key} {html=}"
            assert html.count('<p') == html.count('</p>'), f"HebrewLexiconSimple.getBrDrBrEntryHTML: Mismatched {key} paragraphs {html.count('<p')} {html.count('</p>')} from {html=}"
            assert html.count('<span') == html.count('</span>'), f"HebrewLexiconSimple.getBrDrBrEntryHTML: Mismatched {key} spans {html.count('<span')} {html.count('</span>')} from {html=}"
            return html #.replace( namespace1, '' )
    # end of HebrewLexiconSimple.getBrDrBrEntryHTML
# end of HebrewLexiconSimple class



class HebrewLexicon( HebrewLexiconSimple ):
    """
    Class for handling a Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    However, it does also use the HebrewLexiconSimple class
        so it can be more intelligent with converting code systems.

    It automagically accepts Hebrew and Greek Strong's numbers (like H123 and G532)
        plus BrDrBr (Hebrew) codes (like a.gq.ab).
    """
    def __init__( self, XMLFolder=None, preload=False ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexicon.__init__( {XMLFolder} )" )
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
        #if self.version: result += ('\n' if result else '') + f"Version: {self.version} "
        #if self.date: result += ('\n' if result else '') + f"Date: {self.date}"
        if self.hlix is not None:
            result += ('\n' if result else '') + "  " + f"Number of augmented Strong's index entries = {len(self.hlix.indexEntries1):,}"
            result += ('\n' if result else '') + "  " + f"Number of Hebrew lexical index entries = {len(self.hlix.indexEntries['heb']):,}"
            result += ('\n' if result else '') + "  " + f"Number of Aramaic lexical index entries = {len(self.hlix.indexEntries['arc']):,}"
        if self.StrongsEntries is not None:
            result += ('\n' if result else '') + "  " + f"Number of Strong's Hebrew entries = {len(self.StrongsEntries):,}"
        if self.BrownDriverBriggsEntries is not None:
            result += ('\n' if result else '') + "  " + f"Number of BrDrBr Hebrew entries = {len(self.BrownDriverBriggsEntries['heb']):,}"
            result += ('\n' if result else '') + "  " + f"Number of BrDrBr Aramaic entries = {len(self.BrownDriverBriggsEntries['arc']):,}"
        return result
    # end of HebrewLexicon.__str__


    def getBrDrBrEntryData( self, key:str, getXML:bool=False ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.
            but can also be a Strong's number (with or without the leading H)

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexicon.getBrDrBrEntryData( {key!r} )" )
        if '.' not in key: # assume it's a Strongs code then
            if self.hlix is None: self.load()
            key = self.hlix.getBrDrBrCodeFromStrongsNumber( key )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryData( self, key, getXML )
    # end of HebrewLexicon.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key:str, fieldName:str ) -> str|None:
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
            but can also be a Strong's number (with or without the leading H)
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.

        Returns None if the key or fieldName is not found.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"HebrewLexicon.getBrDrBrEntryField( {key!r}, {fieldName!r} )" )

        if '.' not in key: # assume it's a Strongs code then
            if self.hlix is None: self.load()
            key = self.hlix.getBrDrBrCodeFromStrongsNumber( key )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"HebrewLexicon.getBrDrBrEntryField got key: {key}" )
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
            html = HebrewLexiconSimple.getBrDrBrEntryHTML( self, key, getFull=True )
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
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HebrewLexicon.py
