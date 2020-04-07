#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HebrewLexicon.py
#
# Module handling the Hebrew lexicon
#
# Copyright (C) 2011-2017 Robert Hunt
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
Module handling the OpenScriptures Hebrew lexicon.

    The first classes are the ones that read and parse the XML source files.

    The later classes are the ones for users to
        access the Strongs and Brown, Driver, Briggs lexical entries
        via various keys and in various formats.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2017-12-09' # by RJH
SHORT_PROGRAM_NAME = "HebrewLexicon"
PROGRAM_NAME = "Hebrew Lexicon format handler"
PROGRAM_VERSION = '0.19'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging
import os.path
import sys
import re
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( SHORT_PROGRAM_NAME, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, errorBit )



class AugmentedStrongsIndexFileConverter:
    """
    Class for reading, validating, and converting Hebrew Strongs database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The HebrewLexicon class has functions more generally useful.

    This class reads the augmented Strongs Hebrew index
        which maps Strongs Hebrew numbers (without any leading 'H') to an internal id number.

    The data file looks like this:
        …
        <w aug="8671">nyr</w>
        <w aug="8672">nys</w>
        <w aug="8673">nyt</w>
        <w aug="8674">pdc</w>

    """
    indexFilename = "AugIndex.xml"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    HebLexNameSpace = "{http://openscriptures.github.com/morphhb/namespace}"
    treeTag = HebLexNameSpace + "index"


    def __init__( self ):
        """
        Constructor: just sets up the Hebrew Index file converter object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("AugmentedStrongsIndexFileConverter.__init__()") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries1 = self.entries2 = None
    # end of AugmentedStrongsIndexFileConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Hebrew Index converter object.

        @return: the name of a Hebrew Index converter object formatted as a string
        @rtype: string
        """
        result = "Augmented Strongs Hebrew Index File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.entries1) == len(self.entries2)
        result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.entries1) )
        #result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.entries2) )
        return result
    # end of AugmentedStrongsIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading from {}…").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, AugmentedStrongsIndexFileConverter.indexFilename )
        try: self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        except FileNotFoundError:
            logging.critical( t("HebrewStrongsFileConverter could not find database at {}").format( XMLFileOrFilepath ) )
            raise FileNotFoundError
        except ParseError as err:
            logging.critical( _("Loader parse error in xml file {}: {} {}").format( AugmentedStrongsIndexFileConverter.indexFilename, sys.exc_info()[0], err ) )
            raise ParseError
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        self.entries1, self.entries2 = {}, {}
        if self.XMLTree.tag == AugmentedStrongsIndexFileConverter.treeTag:
            for entry in self.XMLTree:
                self.validateEntry( entry )
        else: logging.error( "Expected to load {!r} but got {!r}".format( AugmentedStrongsIndexFileConverter.treeTag, self.XMLTree.tag ) )
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
    # end of AugmentedStrongsIndexFileConverter.loadAndValidate


    def validateEntry( self, entry ):
        """
        Check/validate the given OSIS div record.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert entry.tag == AugmentedStrongsIndexFileConverter.HebLexNameSpace+"w"
            assert entry.text
        BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "hjg8" )
        BibleOrgSysGlobals.checkXMLNoSubelements( entry, entry.tag, "jk95" )

        # Process the entry attributes first
        aug = None
        for attrib,value in entry.items():
            if attrib=="aug":
                aug = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in index entry element".format( attrib, value ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert aug is not None

        self.entries1[aug] = entry.text
        self.entries2[entry.text] = aug
    # end of AugmentedStrongsIndexFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree )
            assert self.entries1 and self.entries2
        return self.entries1, self.entries2 # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of AugmentedStrongsIndexFileConverter.importDataToPython
# end of AugmentedStrongsIndexFileConverter class




class LexicalIndexFileConverter:
    """
    Class for reading, validating, and converting Hebrew lexical database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The HebrewLexicon class has functions more generally useful.

    This index contains two parts (Hebrew and Aramaic)
        and entries are similar to the following:
            <entry id="aaa">
                <w xlit="ʾ">א</w>
                <xref bdb="a.aa.aa"/>
                <etym type="main"/>
            </entry>
            <entry id="aab">
                <w xlit="ʾēb">אֵב</w> <pos>N</pos> <def>freshness</def>
                <xref bdb="a.ab.ab" strong="3" twot="1a"/>
                <etym type="sub">aad</etym>
            </entry>
            <entry id="aac">
                <w xlit="ʾāb">אָב</w> <pos>N</pos> <def>father</def>
                <xref bdb="a.ae.ab" strong="1" twot="4a"/>
                <etym type="sub">aao</etym>
            </entry>
    """
    indexFilename = "LexicalIndex.xml"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    HebLexNameSpace = "{http://openscriptures.github.com/morphhb/namespace}"
    treeTag = HebLexNameSpace + "index"


    def __init__( self ):
        """
        Constructor: just sets up the Hebrew Index file converter object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("LexicalIndexFileConverter.__init__()") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of LexicalIndexFileConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Hebrew Index converter object.

        @return: the name of a Hebrew Index converter object formatted as a string
        @rtype: string
        """
        result = "Hebrew Lexical Index File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.entries) ==  2
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {}").format( len(self.entries['arc']) )
        return result
    # end of LexicalIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading from {}…").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, LexicalIndexFileConverter.indexFilename )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.XMLTree.tag == LexicalIndexFileConverter.treeTag:
            for part in self.XMLTree:
                self.validatePart( part )
        else: logging.error( "Expected to load {!r} but got {!r}".format( LexicalIndexFileConverter.treeTag, self.XMLTree.tag ) )
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
    # end of LexicalIndexFileConverter.loadAndValidate


    def validatePart( self, part ):
        """
        Check/validate the given lexical index part.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert part.tag == LexicalIndexFileConverter.HebLexNameSpace+"part"
        BibleOrgSysGlobals.checkXMLNoText( part, part.tag, "hjg8" )
        BibleOrgSysGlobals.checkXMLNoTail( part, part.tag, "jk95" )

        # Process the part's attributes first
        lang = None
        for attrib,value in part.items():
            if attrib==LexicalIndexFileConverter.XMLNameSpace+'lang':
                lang = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in index part element".format( attrib, value ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert lang in ('heb','arc',)
        self.entries[lang] = {}
        for entry in part:
            self.validateEntry( entry, lang )
    # end of LexicalIndexFileConverter.validatePart


    def validateEntry( self, entry, lang ):
        """
        Check/validate the given lexical index record.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert entry.tag == LexicalIndexFileConverter.HebLexNameSpace+"entry"
        BibleOrgSysGlobals.checkXMLNoText( entry, entry.tag, "hjg8" )
        BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "hjg8" )

        ID = xlit = None
        pos = definition = etym = None
        BrDrBrXref = strongsXref = strongsAugXref = twotXref = None
        etym = etymType = etymRoot = None

        # Process the entry attributes first
        for attrib,value in entry.items():
            if attrib=='id':
                ID = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in index entry element".format( attrib, value ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert ID is not None

        # Now process the subelements
        for element in entry:
            BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "ksw1" )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "d52d" )
            if element.tag == LexicalIndexFileConverter.HebLexNameSpace+"w":
                location = "w of " + ID
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert element.text
                word = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "fca4" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "ghb2" )
                # Process the attributes
                xlit = None
                for attrib,value in element.items():
                    if attrib=="xlit": xlit = value
                    else: logging.warning( "svd6 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"pos":
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert element.text
                pos = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "dcs2" )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag, "d4hg" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "d4hg" )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+'def':
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert element.text
                definition = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "dcf2" )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag, "d4hg" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "d4hg" )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"xref":
                location = "xref of " + ID
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag, "jd52" )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "dvj3" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "d4hg" )
                # Process the attributes
                for attrib,value in element.items():
                    if attrib=='bdb': BrDrBrXref = value
                    elif attrib=='strong': strongsXref = value
                    elif attrib=='aug': strongsAugXref = value
                    elif attrib=='twot': twotXref = value
                    else: logging.warning( "scs4 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"etym":
                location = "etym of " + ID
                #assert element.text
                etym = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "caw2" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "d4hg" )
                # Process the attributes
                for attrib,value in element.items():
                    if attrib=='type': etymType = value
                    elif attrib=="root": etymRoot = value
                    else: logging.warning( "dsv2 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
            else: logging.warning( "sdv1 Unprocessed {!r} sub-element ({}) in entry".format( element.tag, element.text ) )
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element in entry".format( element.tail, element.tag ) )

        self.entries[lang][ID] = (xlit, pos, definition, BrDrBrXref,strongsXref,strongsAugXref,twotXref, etym,etymRoot,etymType)
    # end of LexicalIndexFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree )
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of LexicalIndexFileConverter.importDataToPython
# end of LexicalIndexFileConverter class


class HebrewStrongsFileConverter:
    """
    Class for reading, validating, and converting Hebrew Strongs database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The HebrewLexicon class has functions more generally useful.

    Typical entries are:
        <entry id="H1">
            <w pos="n-m" pron="awb" xlit="ʼâb" xml:lang="heb">אָב</w>
            <source>a primitive word;</source>
            <meaning><def>father</def>, in a literal and immediate, or figurative and remote application</meaning>
            <usage>chief, (fore-) father(-less), × patrimony, principal. Compare names in 'Abi-'.</usage>
        </entry>
        <entry id="H2">
            <w pos="n-m" pron="ab" xlit="ʼab" xml:lang="arc">אַב</w>
            <source>(Aramaic) corresponding to <w src="H1">1</w></source>
            <usage>father.</usage>
        </entry>
        …
        <entry id="H8673">
            <w pos="n" pron="tish-eem'" xlit="tishʻîym" xml:lang="heb">תִּשְׁעִים</w>
            <source>multiple from <w src="H8672">8672</w>;</source>
            <meaning><def>ninety</def></meaning>
            <usage>ninety.</usage>
        </entry>
        <entry id="H8674">
            <w pos="n-pr-m" pron="tat-ten-ah'-ee" xlit="Tattᵉnay" xml:lang="x-pn">תַּתְּנַי</w>
            <source>of foreign derivation;</source>
            <meaning><def>Tattenai</def>, a Persian</meaning>
            <usage>Tatnai.</usage>
        </entry>
    """
    databaseFilename = "HebrewStrong.xml"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    HebLexNameSpace = "{http://openscriptures.github.com/morphhb/namespace}"
    treeTag = HebLexNameSpace + "lexicon"


    def __init__( self ):
        """
        Constructor: just sets up the file converter object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewStrongsFileConverter.__init__()") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of HebrewStrongsFileConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Hebrew Lexicon converter object.

        @return: the name of a Hebrew Lexicon converter object formatted as a string
        @rtype: string
        """
        result = "Hebrew Strongs Lexicon File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.entries) )
        return result
    # end of HebrewStrongsFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading from {}…").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, HebrewStrongsFileConverter.databaseFilename )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.XMLTree.tag == HebrewStrongsFileConverter.treeTag:
            for entry in self.XMLTree:
                self.validateEntry( entry )
        else: logging.error( "Expected to load {!r} but got {!r}".format( HebrewStrongsFileConverter.treeTag, self.XMLTree.tag ) )
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
    # end of HebrewStrongsFileConverter.loadAndValidate


    def validateEntry( self, entry ):
        """
        Check/validate the given OSIS div record.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert entry.tag == HebrewStrongsFileConverter.HebLexNameSpace+"entry"
        BibleOrgSysGlobals.checkXMLNoText( entry, entry.tag, "na19" )
        BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "kaq9" )

        # Process the entry attributes first
        entryID = None
        for attrib,value in entry.items():
            if attrib=='id':
                entryID = value
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Validating {} entry…".format( entryID ) )
            else: logging.warning( "Unprocessed {!r} attribute ({}) in main entry element".format( attrib, value ) )

        entryResults = {}
        for element in entry:
            if element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"w":
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert element.text
                word = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "d4hg" )
                # Process the attributes
                pos = pron = xlit = src = lang = None
                for attrib,value in element.items():
                    if attrib=="pos": pos = value
                    elif attrib=="pron": pron = value
                    elif attrib=="xlit": xlit = value
                    elif attrib=="src": src = value
                    elif attrib==HebrewStrongsFileConverter.XMLNameSpace+'lang':
                        lang = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in {}".format( attrib, value, element.tag ) )
                if word: entryResults['word'] = (word,pos,pron,xlit,src,)
                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == HebrewStrongsFileConverter.HebLexNameSpace+"w":
                        location = "w of w"
                        self.w = subelement.text
                        tail = subelement.tail
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location )
                        src = None
                        for attrib,value in subelement.items():
                            if attrib=="src": src = value
                            #elif attrib=="pron": pron = value
                            #elif attrib=="xlit": xlit = value
                            else: logging.warning( "Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
                    else: logging.warning( "Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, element.tag ) )
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'source':
                source = BibleOrgSysGlobals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( entryID, 'source', repr(source) )
                if BibleOrgSysGlobals.debugFlag and entryID!='H5223':
                    assert source and '\t' not in source and '\n' not in source
                entryResults['source'] = source
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'meaning':
                meaning = BibleOrgSysGlobals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( entryID, 'meaning', repr(meaning) )
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert meaning and '\t' not in meaning and '\n' not in meaning
                entryResults['meaning'] = meaning
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'usage':
                usage = BibleOrgSysGlobals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( 'usage', repr(usage) )
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert usage and '\t' not in usage and '\n' not in usage
                entryResults['usage'] = usage
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'note':
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert element.text
                note = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "f3g7" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "m56g" )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag, "md3d" )
                entryResults['note'] = note
            else:
                logging.error( "2d4f Unprocessed {!r} element ({}) in entry".format( element.tag, element.text ) )
                if BibleOrgSysGlobals.debugFlag: halt
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element in entry".format( element.tail, element.tag ) )

        #print( entryID, entryResults )
        assert entryID and entryID[0]=='H' and entryID[1:].isdigit()
        self.entries[entryID[1:]] = entryResults # leave off the H
    # end of HebrewStrongsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree )
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of HebrewStrongsFileConverter.importDataToPython
# end of HebrewStrongsFileConverter class




class BrownDriverBriggsFileConverter:
    """
    Class for reading, validating, and converting Brown, Driver, Briggs database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The HebrewLexicon class has functions more generally useful.

    Typical entries are:
        <section id="a.ae">
            <entry id="a.ae.ai" cite="full"><w>אֲבִיָּ֫הוּ</w> <pos>n.pr.m</pos>. &amp; <pos>f</pos>. (<def>Yah</def>(<def>u</def>) <def>is</def> (<def>my</def>) <def>father</def>)—so † <ref r="2Chr.13.20">2 Ch 13:20</ref>, <ref r="2Chr.13.21">21</ref> = <w>אֲבִיָּם</w> † <ref r="1Kgs.14.31">1 K 14:31</ref> <ref r="1Kgs.15.1">15:1</ref>, <ref r="1Kgs.15.7">7</ref>, <ref r="1Kgs.15.7">7</ref>, <ref r="1Kgs.15.8">8</ref> (𝔊 <foreign xml:lang="grc">Ἀβιου</foreign>, <foreign xml:lang="grc">Ἀβια</foreign>); = <w>אֲבִי</w> † <ref r="2Kgs.18.2">2 K 18:2</ref> (𝔊 <foreign xml:lang="grc">Ἀβου</foreign>, <foreign xml:lang="grc">Ἀβουθ</foreign>); = <w>אֲבִיָּה</w> <ref r="1Sam.8.2">1 S 8:2</ref> 22 t.—
                <sense n="1">king of Judah, son &amp; successor of Rehoboam</sense>
                <sense n="2">2nd son of Samuel</sense>
                <sense n="3">son of Jerob.</sense>
                <sense n="4">son of Becher, a Benjamite</sense>
                <sense n="5">head of a priestly house</sense>
                <sense n="6"><em>id</em>.</sense>
                <sense n="7">wife of Hezron</sense>
                <sense n="8">mother of Hezekiah</sense>
                <status p="4">base</status>
            </entry>
            <entry id="a.ae.aj"><w>אֲבִיהוּא</w> <pos>n.pr.m</pos>. (<def>he is father</def>) a son of Aaron
                <status p="4">base</status>
            </entry>
            <entry id="a.ae.ak" cite="full"><w>אֲבִיהוּד</w> <pos>n.pr.m</pos>. (<def>my father is majesty</def>) son of Bela, a Benjamite
                <status p="4">base</status>
            </entry>
        </section>
    """
    databaseFilename = "BrownDriverBriggs.xml"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    HebLexNameSpace = "{http://openscriptures.github.com/morphhb/namespace}"
    treeTag = HebLexNameSpace + "lexicon"


    def __init__( self ):
        """
        Constructor: just sets up the file converter object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("BrownDriverBriggsFileConverter.__init__()") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of BrownDriverBriggsFileConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Hebrew Lexicon converter object.

        @return: the name of a Hebrew Lexicon converter object formatted as a string
        @rtype: string
        """
        result = "Brown, Driver, Briggs Hebrew Lexicon File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.entries) ==  2
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {}").format( len(self.entries['arc']) )
        return result
    # end of BrownDriverBriggsFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading from {}…").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, BrownDriverBriggsFileConverter.databaseFilename )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.XMLTree.tag == BrownDriverBriggsFileConverter.treeTag:
            for entry in self.XMLTree:
                self.validatePart( entry )
        else: logging.error( "Expected to load {!r} but got {!r}".format( BrownDriverBriggsFileConverter.treeTag, self.XMLTree.tag ) )
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip(): logging.error( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
    # end of BrownDriverBriggsFileConverter.loadAndValidate


    def validatePart( self, part ):
        """
        Check/validate the given lexical index part.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert part.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"part"
        BibleOrgSysGlobals.checkXMLNoText( part, part.tag, "vgb4" )
        BibleOrgSysGlobals.checkXMLNoTail( part, part.tag, "scd1" )

        # Process the part's attributes first
        partID = title = lang = None
        for attrib,value in part.items():
            if attrib == 'id':
                partID = value
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Validating {!r} part…".format( partID ) )
            elif attrib == 'title':
                title = value
            elif attrib == LexicalIndexFileConverter.XMLNameSpace+'lang':
                lang = value
            else: logging.warning( "scd2 Unprocessed {!r} attribute ({}) in index part element".format( attrib, value ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert lang in ('heb','arc',)
        if lang not in self.entries: self.entries[lang] = {}

        for section in part:
            self.validateSection( section, partID, title, lang )
    # end of BrownDriverBriggsFileConverter.validatePart


    def validateSection( self, section, partID, title, lang ):
        """
        Check/validate the given lexical index section.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert section.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"section"
        BibleOrgSysGlobals.checkXMLNoText( section, section.tag, "na19" )
        BibleOrgSysGlobals.checkXMLNoTail( section, section.tag, "kaq9" )

        # Process the section's attributes first
        sectionID = None
        for attrib,value in section.items():
            if attrib == 'id':
                sectionID = value
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Validating {!r} section…".format( sectionID ) )
            else: logging.warning( "js19 Unprocessed {!r} attribute ({}) in index section element".format( attrib, value ) )
        for entry in section:
            if entry.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+'page':
                # We don't care about the book pages (page elements only have a 'p' attribute)
                BibleOrgSysGlobals.checkXMLNoText( entry, entry.tag, "dv20" )
                BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "jsq2" )
                BibleOrgSysGlobals.checkXMLNoSubelements( entry, entry.tag, "kdd0" )
            else: self.validateEntry( entry, partID, sectionID, title, lang )
    # end of BrownDriverBriggsFileConverter.validateSection


    def validateEntry( self, entry, partID, sectionID, title, lang ):
        """
        Check/validate the given OSIS div record.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert entry.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"entry"
        #BibleOrgSysGlobals.checkXMLNoText( entry, entry.tag, "na19" )
        BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "kaq9" )

        # Process the entry attributes first
        entryID = entryType = entryMod = entryCite = entryForm = None
        for attrib,value in entry.items():
            if attrib == 'id':
                entryID = value
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Validating {!r} entry…".format( entryID ) )
            elif attrib == 'type': entryType = value
            elif attrib == 'mod': entryMod = value
            elif attrib == 'cite': entryCite = value
            elif attrib == 'form': entryForm = value
            else: logging.warning( "ngs9 Unprocessed {!r} attribute ({}) in main entry element".format( attrib, value ) )

        flattenedXML = BibleOrgSysGlobals.getFlattenedXML( entry, entryID ) \
                            .replace( BrownDriverBriggsFileConverter.HebLexNameSpace, '' ) \
                            .replace( '\t', '' ).replace( '\n', '' )
        if entryID == "m.ba.ab": flattenedXML = flattenedXML.rstrip() # Seems to have a space at the start of the XML line
        #print( entryID, repr(flattenedXML) )
        match = re.search( '<status p="(\d{1,4})">(.+?)</status>', flattenedXML )
        if match:
            #logging.warning( "Removed {} status field {} from {}" \
                #.format( entryID, repr(flattenedXML[match.start():match.end()]), repr(flattenedXML) ) )
            resultXML = flattenedXML[:match.start()] + flattenedXML[match.end():]
            statusP, status = match.group(1), match.group(2)
            #print( "statusP", repr(statusP), "st", repr(status) )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                assert status in ('new','made','base','ref','added','done',)
        else:
            logging.warning( "Missing status in {} BrDrBr entry: {!r}".format( entryID, flattenedXML ) )
            resultXML = flattenedXML

        #print( repr(partID), repr(sectionID), repr(title), repr(lang) )
        #print( entryID, status, repr(resultXML) )
        self.entries[lang][entryID] = (resultXML,statusP,status,)
    # end of BrownDriverBriggsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len( self.XMLTree )
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of BrownDriverBriggsFileConverter.importDataToPython
# end of BrownDriverBriggsFileConverter class




class HebrewLexiconIndex:
    """
    Class for handling an Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconIndex.__init__( {} )").format( XMLFolder ) )
        hASIndex = AugmentedStrongsIndexFileConverter() # Create the empty object
        hASIndex.loadAndValidate( XMLFolder ) # Load the XML
        self.IndexEntries1, self.IndexEntries2 = hASIndex.importDataToPython()
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.IndexEntries1) == len(self.IndexEntries2)
        hLexIndex = LexicalIndexFileConverter() # Create the empty object
        hLexIndex.loadAndValidate( XMLFolder ) # Load the XML
        self.IndexEntries = hLexIndex.importDataToPython()
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(self.IndexEntries) == 2
    # end of HebrewLexiconIndex.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew Lexicon Index object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of augmented Strong's index entries = {}").format( len(self.IndexEntries1) )
        result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {}").format( len(self.IndexEntries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {}").format( len(self.IndexEntries['arc']) )
        return result
    # end of HebrewLexiconIndex.__str__


    def getLexiconCodeFromStrongsNumber( self, key ):
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'.
        """
        if key and key[0]=='H': key = key[1:] # Remove any leading 'H'
        keyDigits = key[1:]
        if key in self.IndexEntries1: return self.IndexEntries1[key]
    # end of HebrewLexiconIndex.getLexiconCodeFromStrongsNumber


    def _getStrongsNumberFromLexiconCode1( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        if key in self.IndexEntries2: return self.IndexEntries2[key]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode1


    def _getStrongsNumberFromLexiconCode2( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a Hebrew Strong's number (but only the digits -- no preceding H)
        """
        keyDigits = key[1:]
        if key in self.IndexEntries['heb']: return self.IndexEntries['heb'][key][4]
        if key in self.IndexEntries['arc']: return self.IndexEntries['arc'][key][4]
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
        if key in self.IndexEntries2: return self.IndexEntries2[key]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode


    def getBrDrBrCodeFromLexiconCode( self, key ):
        """
        The key is a three letter internal code like 'aac'.

        Returns a BrDrBr code, e.g., 'm.ba.aa'
        """
        keyDigits = key[1:]
        if key in self.IndexEntries['heb']: return self.IndexEntries['heb'][key][3]
        if key in self.IndexEntries['arc']: return self.IndexEntries['arc'][key][3]
    # end of HebrewLexiconIndex.getBrDrBrCodeFromLexiconCode


    def getBrDrBrCodeFromStrongsNumber( self, key ):
        """
        The key is a digit string like '172' (optional preceding H).

        Returns a lexicon internal code like 'acd'.
        """
        #print( "HebrewLexiconIndex.getBrDrBrCodeFromStrongsNumber( {} )".format( key ) )

        if key and key[0]=='H': key = key[1:] # Remove any leading 'H'
        #keyDigits = key[1:]
        if key in self.IndexEntries1:
            internalCode = self.IndexEntries1[key]
            return self.getBrDrBrCodeFromLexiconCode( internalCode )
    # end of HebrewLexiconIndex.getBrDrBrCodeFromStrongsNumber


    def getTWOTCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BrDrBr code, e.g., '4a'
        """
        keyDigits = key[1:]
        if key in self.IndexEntries['heb']: return self.IndexEntries['heb'][key][6]
        if key in self.IndexEntries['arc']: return self.IndexEntries['arc'][key][6]
    # end of HebrewLexiconIndex.getTWOTCodeFromLexiconCode

# end of HebrewLexiconIndex class




class HebrewLexiconSimple:
    """
    Simple class for handling a Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder, preload=False ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.__init__( {} )").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        self.StrongsEntries = self.BrownDriverBriggsEntries = None
        if preload: self.load()
    # end of HebrewLexiconSimple.__init__


    def load( self ):
        """
        Load the actual lexicon (slow).
        """
        hStr = HebrewStrongsFileConverter() # Create the empty object
        hStr.loadAndValidate( self.XMLFolder ) # Load the XML
        self.StrongsEntries = hStr.importDataToPython()

        hBrDrBr = BrownDriverBriggsFileConverter() # Create the empty object
        hBrDrBr.loadAndValidate( self.XMLFolder ) # Load the XML
        self.BrownDriverBriggsEntries = hBrDrBr.importDataToPython()
    # end of HebrewLexiconSimple.load


    def __str__( self ):
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
            result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {}").format( len(self.StrongsEntries) )
        if self.BrownDriverBriggsEntries:
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Hebrew entries = {}").format( len(self.BrownDriverBriggsEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Aramaic entries = {}").format( len(self.BrownDriverBriggsEntries['arc']) )
        return result
    # end of HebrewLexiconSimple.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.getStrongsEntryData( {!r} )").format( key ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
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
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.getStrongsEntryField( {!r}, {!r} )").format( key, fieldName ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of HebrewLexiconSimple.getStrongsEntryField


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
            print( t("HebrewLexiconSimple.getStrongsEntryHTML( {!r} )").format( key ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key[0]=='H' and key[1:].isdigit()
        if self.StrongsEntries is None: self.load()

        keyDigits = key[1:]
        #if key == 'H1':
            #print( "Should be:" )
            #print( 'sHTML: <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word; father, in a literal and immediate, or figurative and remote application): <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>. Compare names in "Abi-".</li>' )
        while len(keyDigits)>1 and keyDigits[0]=='0': keyDigits = keyDigits[1:] # Remove leading zeroes
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            #for j, subentry in enumerate(entry):
                #print( "  {} {}={}".format( j, subentry, repr(entry[subentry]) ) )
            #for subentry in entry:
                #print( "  ", subentry, repr(entry[subentry]) )
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
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert src[0] == 'H'
                sourceHTML = sourceHTML[:match.start()] + '<span class="Strongs" ref="{}">H'.format( src ) + sourceHTML[match.end():]
            meaningHTML = '<span class="Meaning"><b>Meaning:</b> {}</span>'.format( entry['meaning'] \
                        .replace('<def>','<span class="Def">').replace('</def>','</span>') ) \
                        if 'meaning' in entry else ''
            usageHTML = '<span class="KJVUsage"><b>KJV:</b> {}</span>'.format( entry['usage'] ) \
                        if 'usage' in entry else ''
            #html = '<li value="{}" id="ot:{}"><span class="originalWord" title="{{{}}}" xml:lang="hbo">{}</span><br>{}<br>{}<br>{}</li>' \
                #.format( keyDigits, keyDigits, entry['word'][2], entry['word'][0], sourceHTML, meaningHTML, usageHTML )
            html = '{}<br>{}<br>{}<br>{}'.format( wordHTML, sourceHTML, meaningHTML, usageHTML )
            return html.replace( ' ,', ',' ).replace( ' ;', ';' ) # clean it up and return it
    # end of HebrewLexiconSimple.getStrongsEntryHTML


    def getBrDrBrEntryData( self, key ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.getBrDrBrEntryData( {!r} )").format( key ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
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
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.getBrDrBrEntryField( {!r}, {!r} )").format( key, fieldName ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key )
        #print( "HebrewLexiconSimple.getBrDrBrEntryField entry: {}".format( entry ) )
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
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexiconSimple.getBrDrBrEntryHTML( {!r} )").format( key ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert key and key.count('.')==2
        if self.BrownDriverBriggsEntries is None: self.load()

        entry =  self.getBrDrBrEntryData( key )
        #print( "HebrewLexiconSimple.getBrDrBrEntryHTML entry: {}".format( entry ) )
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
            html = '{} <span class="Status">{{{}}}</span>'.format( mainEntry, entry[1] )
            print( "hls html", repr(html) )
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
    def __init__( self, XMLFolder, preload=False ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexicon.__init__( {} )").format( XMLFolder ) )
        HebrewLexiconSimple.__init__( self, XMLFolder )
        self.XMLFolder = XMLFolder
        self.hix = None
        if preload: self.load()
    # end of HebrewLexicon.__init__


    def load( self ):
        """
        Load the actual lexicon (slow).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HebrewLexicon.load()") )
        HebrewLexiconSimple.load( self )
        assert self.hix is None
        self.hix = HebrewLexiconIndex( self.XMLFolder ) # Load and process the XML
    # end of HebrewLexicon.load


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Hebrew Lexicon object formatted as a string
        @rtype: string
        """
        result = "Hebrew Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.hix is not None:
            result += ('\n' if result else '') + "  " + _("Number of augmented Strong's index entries = {}").format( len(self.hix.IndexEntries1) )
            result += ('\n' if result else '') + "  " + _("Number of Hebrew lexical index entries = {}").format( len(self.hix.IndexEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of Aramaic lexical index entries = {}").format( len(self.hix.IndexEntries['arc']) )
        if self.StrongsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {}").format( len(self.StrongsEntries) )
        if self.BrownDriverBriggsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Hebrew entries = {}").format( len(self.BrownDriverBriggsEntries['heb']) )
            result += ('\n' if result else '') + "  " + _("Number of BrDrBr Aramaic entries = {}").format( len(self.BrownDriverBriggsEntries['arc']) )
        return result
    # end of HebrewLexicon.__str__


    def getBrDrBrEntryData( self, key ):
        """
        The key is a BrDrBr number (string) like 'a.ca.ab'.
            but can also be a Strong's number (with or without the leading H)

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexicon.getBrDrBrEntryData( {!r} )").format( key ) )
        if '.' not in key: # assume it's a Strongs code then
            if self.hix is None: self.load()
            key = self.hix.getBrDrBrCodeFromStrongsNumber( key )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryData( self, key )
    # end of HebrewLexicon.getBrDrBrEntryData


    def getBrDrBrEntryField( self, key, fieldName ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
            but can also be a Strong's number (with or without the leading H)
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexicon.getBrDrBrEntryField( {!r}, {!r} )").format( key, fieldName ) )

        if '.' not in key: # assume it's a Strongs code then
            if self.hix is None: self.load()
            key = self.hix.getBrDrBrCodeFromStrongsNumber( key )
            #print( "HebrewLexicon.getBrDrBrEntryField got key: {}".format( key ) )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryField( self, key, fieldName ) # Recursive call
    # end of HebrewLexicon.getBrDrBrEntryField


    def getBrDrBrEntryHTML( self, key ):
        """
        The key is a BrDrBr number (string) like 'ah.ba.aa'.
            but can also be a Strong's number (with or without the leading H)

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HebrewLexicon.getBrDrBrEntryHTML( {!r} )").format( key ) )
        if '.' not in key: # assume it's a Strongs code then
            if self.hix is None: self.load()
            key = self.hix.getBrDrBrCodeFromStrongsNumber( key )
        if key:
            return HebrewLexiconSimple.getBrDrBrEntryHTML( self, key )
    # end of HebrewLexicon.getBrDrBrEntryHTML
# end of HebrewLexicon class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'HebrewLexicon/' ) # Hebrew lexicon folder


    if 1: # demonstrate the Hebrew Lexicon converter classes
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the converter classes…" )

        print()
        hix = AugmentedStrongsIndexFileConverter()
        hix.loadAndValidate( testFolder ) # Load the XML
        print( hix ) # Just print a summary

        print()
        lix = LexicalIndexFileConverter()
        lix.loadAndValidate( testFolder ) # Load the XML
        print( lix ) # Just print a summary

        print()
        hlc = HebrewStrongsFileConverter()
        hlc.loadAndValidate( testFolder ) # Load the XML
        print( hlc ) # Just print a summary

        print()
        bdb = BrownDriverBriggsFileConverter()
        bdb.loadAndValidate( testFolder ) # Load the XML
        print( bdb ) # Just print a summary

        if BibleOrgSysGlobals.commandLineArguments.export:
            print( "Exports aren't written yet!" )
            #hlc.exportDataToPython() # Produce the .py tables
            #hlc.exportDataToC() # Produce the .h tables
            halt


    if 1: # demonstrate the Hebrew Lexicon Index class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the Hebrew Lexicon Index class…" )
        hix = HebrewLexiconIndex( testFolder ) # Load and process the XML
        print( hix ) # Just print a summary
        print()
        print( "Code for 2 is", hix.getLexiconCodeFromStrongsNumber( '2' ) )
        print( "Code for H8674 is", hix.getLexiconCodeFromStrongsNumber( 'H8674' ) )
        print( "Code for H8675 is", hix.getLexiconCodeFromStrongsNumber( 'H8675' ) )
        print( "Codes for aac are", hix.getStrongsNumberFromLexiconCode('aac'), hix.getBrDrBrCodeFromLexiconCode('aac'), hix.getTWOTCodeFromLexiconCode('aac') )
        print( "Codes for nyy are", hix.getStrongsNumberFromLexiconCode('nyy'), hix.getBrDrBrCodeFromLexiconCode('nyy'), hix.getTWOTCodeFromLexiconCode('nyy') )
        print( "Codes for pdc are", hix.getStrongsNumberFromLexiconCode('pdc'), hix.getBrDrBrCodeFromLexiconCode('pdc'), hix.getTWOTCodeFromLexiconCode('pdc') )
        print( "Codes for pdd are", hix.getStrongsNumberFromLexiconCode('pdd'), hix.getBrDrBrCodeFromLexiconCode('pdd'), hix.getTWOTCodeFromLexiconCode('pdd') )


    if 1: # demonstrate the simple Hebrew Lexicon class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the simple Hebrew Lexicon class…" )
        hl = HebrewLexiconSimple( testFolder ) # Load and process the XML
        print( hl ) # Just print a summary
        print()
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            print( '\n' + strongsKey )
            print( " Data:", hl.getStrongsEntryData( strongsKey ) )
            print( " Usage:", hl.getStrongsEntryField( strongsKey, 'usage' ) )
            print( " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            print( '\n' + BrDrBrKey )
            print( " Data:", hl.getBrDrBrEntryData( BrDrBrKey ) )
            print( " Status:", hl.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            print( " HTML:", hl.getBrDrBrEntryHTML( BrDrBrKey ) )

    if 1: # demonstrate the Hebrew Lexicon class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the Hebrew Lexicon class…" )
        hl = HebrewLexicon( testFolder ) # Load and process the XML
        print( hl ) # Just print a summary
        print()
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            print( '\n' + strongsKey )
            print( " Data:", hl.getStrongsEntryData( strongsKey ) )
            print( " Usage:", hl.getStrongsEntryField( strongsKey, 'usage' ) )
            print( " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
            print( " Data:", hl.getBrDrBrEntryData( strongsKey ) )
            print( " Status:", hl.getBrDrBrEntryField( strongsKey, 'status' ) )
            print( " HTML:", hl.getBrDrBrEntryHTML( strongsKey ) )
        for BrDrBrKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            print( '\n' + BrDrBrKey )
            print( " Data:", hl.getBrDrBrEntryData( BrDrBrKey ) )
            print( " Status:", hl.getBrDrBrEntryField( BrDrBrKey, 'status' ) )
            print( " HTML:", hl.getBrDrBrEntryHTML( BrDrBrKey ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HebrewLexicon.py
