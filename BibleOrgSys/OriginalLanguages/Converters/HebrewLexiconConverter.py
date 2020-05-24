#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HebrewLexiconConverter.py
#
# Module handling the Hebrew lexicon
#
# Copyright (C) 2011-2020 Robert Hunt
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
Module handling the OpenScriptures Hebrew lexicon.

    The classes are the ones that read and parse the XML source files.
"""
from gettext import gettext as _
import logging
import os.path
import sys
import re
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    aboveAboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) ) )
    if aboveAboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint


LAST_MODIFIED_DATE = '2020-05-04' # by RJH
SHORT_PROGRAM_NAME = "HebrewLexicon"
PROGRAM_NAME = "Hebrew Lexicon format handler"
PROGRAM_VERSION = '0.20'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


# Hebrew lexicon folder
DEFAULT_LEXICON_FOLDERPATH = BibleOrgSysGlobals.BADBAD_PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'HebrewLexicon/' )



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
        vPrint( 'Never', debuggingThisModule, _("AugmentedStrongsIndexFileConverter.__init__()…") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries1 = self.entries2 = None
    # end of AugmentedStrongsIndexFileConverter.__init__


    def __str__( self ) -> str:
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
        result += ('\n' if result else '') + "  " + _("Number of entries = {:,}").format( len(self.entries1) )
        #result += ('\n' if result else '') + "  " + _("Number of entries = {:,}").format( len(self.entries2) )
        return result
    # end of AugmentedStrongsIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder=None ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Never', debuggingThisModule, "loadAndValidate( {XMLFolder} )…" )
        if XMLFolder is None:
            XMLFolder = DEFAULT_LEXICON_FOLDERPATH # Hebrew lexicon folder
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, AugmentedStrongsIndexFileConverter.indexFilename )
        vPrint( 'Info', debuggingThisModule, _("Loading from {}…").format( XMLFileOrFilepath ) )
        try: self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        except FileNotFoundError:
            logging.critical( _("AugmentedStrongsIndexFileConverter could not find database at {}").format( XMLFileOrFilepath ) )
            raise FileNotFoundError
        except ParseError as err:
            logging.critical( _("Loader parse error in xml file {}: {} {}").format( AugmentedStrongsIndexFileConverter.indexFilename, sys.exc_info()[0], err ) )
            raise ParseError
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree # Fail here if we didn't load anything at all

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
            assert self.XMLTree
            assert self.entries1 and self.entries2
        return self.entries1, self.entries2 # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of AugmentedStrongsIndexFileConverter.importDataToPython


    def pickle( self, filepath=None ) -> None:
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python program.
        """
        import pickle

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert self.XMLTree
            assert self.entries1
            assert self.entries2

        if not filepath:
            folderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not folderpath.exists(): os.mkdir( folderpath )
            filepath = os.path.join( folderpath, 'HebrewLexicon_AugStrongsIndex_Tables.pickle' )
        vPrint( 'Normal', debuggingThisModule, _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.entries1, myFile )
            pickle.dump( self.entries2, myFile )
    # end of GreekStrongsFileConverter.pickle
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
        vPrint( 'Never', debuggingThisModule, _("LexicalIndexFileConverter.__init__()…") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of LexicalIndexFileConverter.__init__


    def __str__( self ) -> str:
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
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {:,}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {:,}").format( len(self.entries['arc']) )
        return result
    # end of LexicalIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder=None ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Never', debuggingThisModule, "loadAndValidate( {XMLFolder} )…" )
        if XMLFolder is None:
            XMLFolder = DEFAULT_LEXICON_FOLDERPATH # Hebrew lexicon folder
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, LexicalIndexFileConverter.indexFilename )
        vPrint( 'Info', debuggingThisModule, _("Loading from {}…").format( XMLFileOrFilepath ) )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree # Fail here if we didn't load anything at all

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
            assert self.XMLTree
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of LexicalIndexFileConverter.importDataToPython


    def pickle( self, filepath=None ) -> None:
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python program.
        """
        import pickle

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert self.XMLTree
            assert self.entries

        if not filepath:
            folderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not folderpath.exists(): os.mkdir( folderpath )
            filepath = os.path.join( folderpath, 'HebrewLexicon_Index_Table.pickle' )
        vPrint( 'Normal', debuggingThisModule, _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.entries, myFile )
    # end of GreekStrongsFileConverter.pickle
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
        vPrint( 'Never', debuggingThisModule, _("HebrewStrongsFileConverter.__init__()…") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of HebrewStrongsFileConverter.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Hebrew Lexicon converter object.

        @return: the name of a Hebrew Lexicon converter object formatted as a string
        @rtype: string
        """
        result = "Hebrew Strongs Lexicon File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of entries = {:,}").format( len(self.entries) )
        return result
    # end of HebrewStrongsFileConverter.__str__


    def loadAndValidate( self, XMLFolder=None ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Never', debuggingThisModule, "loadAndValidate( {XMLFolder} )…" )
        if XMLFolder is None:
            XMLFolder = DEFAULT_LEXICON_FOLDERPATH # Hebrew lexicon folder
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, HebrewStrongsFileConverter.databaseFilename )
        vPrint( 'Info', debuggingThisModule, _("Loading from {}…").format( XMLFileOrFilepath ) )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree # Fail here if we didn't load anything at all

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
                # dPrint( 'Info', debuggingThisModule, "Validating {} entry…".format( entryID ) )
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
                for subelement in element:
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
                #dPrint( 'Quiet', debuggingThisModule, entryID, 'source', repr(source) )
                if BibleOrgSysGlobals.debugFlag and entryID!='H5223':
                    assert source and '\t' not in source and '\n' not in source
                entryResults['source'] = source
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'meaning':
                meaning = BibleOrgSysGlobals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #dPrint( 'Quiet', debuggingThisModule, entryID, 'meaning', repr(meaning) )
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert meaning and '\t' not in meaning and '\n' not in meaning
                entryResults['meaning'] = meaning
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+'usage':
                usage = BibleOrgSysGlobals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #dPrint( 'Quiet', debuggingThisModule, 'usage', repr(usage) )
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

        #dPrint( 'Quiet', debuggingThisModule, entryID, entryResults )
        assert entryID and entryID[0]=='H' and entryID[1:].isdigit()
        self.entries[entryID[1:]] = entryResults # leave off the H
    # end of HebrewStrongsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of HebrewStrongsFileConverter.importDataToPython


    def pickle( self, filepath=None ) -> None:
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python program.
        """
        import pickle

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert self.XMLTree
            assert self.entries

        if not filepath:
            folderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not folderpath.exists(): os.mkdir( folderpath )
            filepath = os.path.join( folderpath, 'HebrewLexicon_Strongs_Table.pickle' )
        vPrint( 'Normal', debuggingThisModule, _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.entries, myFile )
    # end of GreekStrongsFileConverter.pickle
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
        vPrint( 'Never', debuggingThisModule, _("BrownDriverBriggsFileConverter.__init__()…") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.entries = None
    # end of BrownDriverBriggsFileConverter.__init__


    def __str__( self ) -> str:
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
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {:,}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {:,}").format( len(self.entries['arc']) )
        return result
    # end of BrownDriverBriggsFileConverter.__str__


    def loadAndValidate( self, XMLFolder=None ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        vPrint( 'Never', debuggingThisModule, "loadAndValidate( {XMLFolder} )…" )
        if XMLFolder is None:
            XMLFolder = DEFAULT_LEXICON_FOLDERPATH # Hebrew lexicon folder
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, BrownDriverBriggsFileConverter.databaseFilename )
        vPrint( 'Info', debuggingThisModule, _("Loading from {}…").format( XMLFileOrFilepath ) )
        self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree # Fail here if we didn't load anything at all

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
                # dPrint( 'Info', debuggingThisModule, "Validating {!r} part…".format( partID ) )
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
                # dPrint( 'Info', debuggingThisModule, "Validating {!r} section…".format( sectionID ) )
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
                # dPrint( 'Info', debuggingThisModule, "Validating {!r} entry…".format( entryID ) )
            elif attrib == 'type': entryType = value
            elif attrib == 'mod': entryMod = value
            elif attrib == 'cite': entryCite = value
            elif attrib == 'form': entryForm = value
            else: logging.warning( "ngs9 Unprocessed {!r} attribute ({}) in main entry element".format( attrib, value ) )

        flattenedXML = BibleOrgSysGlobals.getFlattenedXML( entry, entryID ) \
                            .replace( BrownDriverBriggsFileConverter.HebLexNameSpace, '' ) \
                            .replace( '\t', '' ).replace( '\n', '' )
        if entryID == "m.ba.ab": flattenedXML = flattenedXML.rstrip() # Seems to have a space at the start of the XML line
        #dPrint( 'Quiet', debuggingThisModule, entryID, repr(flattenedXML) )
        match = re.search( '<status p="(\d{1,4})">(.+?)</status>', flattenedXML )
        if match:
            #logging.warning( "Removed {} status field {} from {}" \
                #.format( entryID, repr(flattenedXML[match.start():match.end()]), repr(flattenedXML) ) )
            resultXML = flattenedXML[:match.start()] + flattenedXML[match.end():]
            statusP, status = match.group(1), match.group(2)
            #dPrint( 'Quiet', debuggingThisModule, "statusP", repr(statusP), "st", repr(status) )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                assert status in ('new','made','base','ref','added','done',)
        else:
            logging.warning( "Missing status in {} BrDrBr entry: {!r}".format( entryID, flattenedXML ) )
            resultXML = flattenedXML

        #dPrint( 'Quiet', debuggingThisModule, repr(partID), repr(sectionID), repr(title), repr(lang) )
        #dPrint( 'Quiet', debuggingThisModule, entryID, status, repr(resultXML) )
        self.entries[lang][entryID] = (resultXML,statusP,status,)
    # end of BrownDriverBriggsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert self.XMLTree
            assert self.entries
        return self.entries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of BrownDriverBriggsFileConverter.importDataToPython


    def pickle( self, filepath=None ) -> None:
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python program.
        """
        import pickle

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert self.XMLTree
            assert self.entries

        if not filepath:
            folderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not folderpath.exists(): os.mkdir( folderpath )
            filepath = os.path.join( folderpath, 'HebrewLexicon_BDB_Table.pickle' )
        vPrint( 'Normal', debuggingThisModule, _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.entries, myFile )
    # end of GreekStrongsFileConverter.pickle
# end of BrownDriverBriggsFileConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    if 1: # demonstrate the Hebrew Lexicon converter classes
        vPrint( 'Normal', debuggingThisModule, "\nDemonstrating the converter classes…" )

        vPrint( 'Quiet', debuggingThisModule, '' )
        asixfc = AugmentedStrongsIndexFileConverter()
        asixfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, asixfc ) # Just print a summary

        vPrint( 'Quiet', debuggingThisModule, '' )
        lixfc = LexicalIndexFileConverter()
        lixfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, lixfc ) # Just print a summary

        vPrint( 'Quiet', debuggingThisModule, '' )
        hsfc = HebrewStrongsFileConverter()
        hsfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, hsfc ) # Just print a summary

        vPrint( 'Quiet', debuggingThisModule, '' )
        bdb = BrownDriverBriggsFileConverter()
        bdb.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, bdb ) # Just print a summary

        if BibleOrgSysGlobals.commandLineArguments.export:
            vPrint( 'Quiet', debuggingThisModule, "Exports aren't written yet!" )
            #hsfc.exportDataToPython() # Produce the .py tables
            #hsfc.exportDataToC() # Produce the .h tables
# end of HebrewLexiconConverter.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    if 1: # demonstrate the Hebrew Lexicon converter classes
        vPrint( 'Normal', debuggingThisModule, "\nDemonstrating the converter classes…" )

        vPrint( 'Quiet', debuggingThisModule, '' )
        asixfc = AugmentedStrongsIndexFileConverter()
        asixfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, asixfc ) # Just print a summary
        if BibleOrgSysGlobals.commandLineArguments.export:
            asixfc.pickle() # Produce a pickle output file

        vPrint( 'Quiet', debuggingThisModule, '' )
        lixfc = LexicalIndexFileConverter()
        lixfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, lixfc ) # Just print a summary
        if BibleOrgSysGlobals.commandLineArguments.export:
            lixfc.pickle() # Produce a pickle output file

        vPrint( 'Quiet', debuggingThisModule, '' )
        hsfc = HebrewStrongsFileConverter()
        hsfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, hsfc ) # Just print a summary
        if BibleOrgSysGlobals.commandLineArguments.export:
            hsfc.pickle() # Produce a pickle output file

        vPrint( 'Quiet', debuggingThisModule, '' )
        bdbfc = BrownDriverBriggsFileConverter()
        bdbfc.loadAndValidate() # Load the XML
        vPrint( 'Quiet', debuggingThisModule, bdbfc ) # Just print a summary
        if BibleOrgSysGlobals.commandLineArguments.export:
            bdbfc.pickle() # Produce a pickle output file

        if BibleOrgSysGlobals.commandLineArguments.export:
            import pickle
            folderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not folderpath.exists(): os.mkdir( folderpath )
            filepath = os.path.join( folderpath, 'HebrewLexicon_Tables.1.pickle' )
            vPrint( 'Normal', debuggingThisModule, _("Exporting to {}…").format( filepath ) )
            with open( filepath, 'wb' ) as myFile:
                pickle.dump( asixfc.entries1, myFile )
                pickle.dump( asixfc.entries2, myFile )
                pickle.dump( lixfc.entries, myFile )
                pickle.dump( hsfc.entries, myFile )
                pickle.dump( bdbfc.entries, myFile )
            vPrint( 'Quiet', debuggingThisModule, "Other exports aren't written yet!" )
            #hsfc.exportDataToPython() # Produce the .py tables
            #hsfc.exportDataToC() # Produce the .h tables
# end of HebrewLexiconConverter.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HebrewLexiconConverter.py
