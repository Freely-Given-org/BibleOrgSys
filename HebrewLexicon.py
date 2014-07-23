#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# HebrewLexicon.py
#   Last modified: 2014-07-23 (also update ProgVersion below)
#
# Module handling the Hebrew lexicon
#
# Copyright (C) 2011-2014 Robert Hunt
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

ProgName = "Hebrew Lexicon format handler"
ProgVersion = "0.11"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os.path
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import Globals




class AugmentedStrongsIndexFileConverter:
    """
    Class for reading, validating, and converting Hebrew Strongs database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The HebrewLexicon class has functions more generally useful.

    This class reads the augmented Strongs Hebrew index
        which maps Strongs Hebrew numbers (without any leading 'H') to an internal id number.

    The data file looks like this:
        ...
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
        self.title = self.version = self.date = None
        self.tree = self.header = self.entries1 = self.entries2 = None
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
        if Globals.debugFlag: assert( len(self.entries1) == len(self.entries2) )
        result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.entries1) )
        #result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.entries2) )
        return result
    # end of AugmentedStrongsIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if Globals.verbosityLevel > 2: print( _("Loading from {}...").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFilepath = os.path.join( XMLFolder, AugmentedStrongsIndexFileConverter.indexFilename )
        self.tree = ElementTree().parse( XMLFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        self.entries1, self.entries2 = {}, {}
        if self.tree.tag == AugmentedStrongsIndexFileConverter.treeTag:
            for entry in self.tree:
                self.validateEntry( entry )
        else: logging.error( "Expected to load '{}' but got '{}'".format( AugmentedStrongsIndexFileConverter.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element".format( self.tree.tail, self.tree.tag ) )
    # end of AugmentedStrongsIndexFileConverter.loadAndValidate


    def validateEntry( self, entry ):
        """
        Check/validate the given OSIS div record.
        """
        if Globals.debugFlag:
            assert( entry.tag == AugmentedStrongsIndexFileConverter.HebLexNameSpace+"w" )
            assert( entry.text )
        Globals.checkXMLNoTail( entry, entry.tag, "hjg8" )
        Globals.checkXMLNoSubelements( entry, entry.tag, "jk95" )

        # Process the entry attributes first
        aug = None
        for attrib,value in entry.items():
            if attrib=="aug":
                aug = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in index entry element".format( attrib, value ) )
        if Globals.debugFlag: assert( aug is not None )

        self.entries1[aug] = entry.text
        self.entries2[entry.text] = aug
    # end of AugmentedStrongsIndexFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.tree if you prefer.)
        """
        if Globals.debugFlag:
            assert( len ( self.tree ) )
            assert( self.entries1 and self.entries2 )
        return self.entries1, self.entries2 # temp................................XXXXXXXXXXXXXXXXXXXXXXXXXXXXX......................
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
        self.title = self.version = self.date = None
        self.tree = self.header = self.entries = None
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
        if Globals.debugFlag: assert( len(self.entries) ==  2 )
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {}").format( len(self.entries['arc']) )
        return result
    # end of LexicalIndexFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if Globals.verbosityLevel > 2: print( _("Loading from {}...").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFilepath = os.path.join( XMLFolder, LexicalIndexFileConverter.indexFilename )
        self.tree = ElementTree().parse( XMLFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.tree.tag == LexicalIndexFileConverter.treeTag:
            for part in self.tree:
                self.validatePart( part )
        else: logging.error( "Expected to load '{}' but got '{}'".format( LexicalIndexFileConverter.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element".format( self.tree.tail, self.tree.tag ) )
    # end of LexicalIndexFileConverter.loadAndValidate


    def validatePart( self, part ):
        """
        Check/validate the given lexical index part.
        """
        if Globals.debugFlag: assert( part.tag == LexicalIndexFileConverter.HebLexNameSpace+"part" )
        Globals.checkXMLNoText( part, part.tag, "hjg8" )
        Globals.checkXMLNoTail( part, part.tag, "jk95" )

        # Process the part's attributes first
        lang = None
        for attrib,value in part.items():
            if attrib==LexicalIndexFileConverter.XMLNameSpace+"lang":
                lang = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in index part element".format( attrib, value ) )
        if Globals.debugFlag: assert( lang in ('heb','arc',) )
        self.entries[lang] = {}
        for entry in part:
            self.validateEntry( entry, lang )
    # end of LexicalIndexFileConverter.validatePart


    def validateEntry( self, entry, lang ):
        """
        Check/validate the given lexical index record.
        """
        if Globals.debugFlag: assert( entry.tag == LexicalIndexFileConverter.HebLexNameSpace+"entry" )
        Globals.checkXMLNoText( entry, entry.tag, "hjg8" )
        Globals.checkXMLNoTail( entry, entry.tag, "hjg8" )

        ID = xlit = None
        pos = definition = etym = None
        bdbXref = strongsXref = strongsAugXref = twotXref = None
        etym = etymType = etymRoot = None

        # Process the entry attributes first
        for attrib,value in entry.items():
            if attrib=="id":
                ID = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in index entry element".format( attrib, value ) )
        if Globals.debugFlag: assert( ID is not None )

        # Now process the subelements
        for element in entry:
            Globals.checkXMLNoTail( element, element.tag, "ksw1" )
            Globals.checkXMLNoSubelements( element, element.tag, "d52d" )
            if element.tag == LexicalIndexFileConverter.HebLexNameSpace+"w":
                location = "w of " + ID
                if Globals.debugFlag: assert( element.text )
                word = element.text
                Globals.checkXMLNoTail( element, element.tag, "fca4" )
                Globals.checkXMLNoSubelements( element, element.tag, "ghb2" )
                # Process the attributes
                xlit = None
                for attrib,value in element.items():
                    if attrib=="xlit": xlit = value
                    else: logging.warning( "svd6 Unprocessed '{}' attribute ({}) in {}".format( attrib, value, location ) )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"pos":
                if Globals.debugFlag: assert( element.text )
                pos = element.text
                Globals.checkXMLNoTail( element, element.tag, "dcs2" )
                Globals.checkXMLNoAttributes( element, element.tag, "d4hg" )
                Globals.checkXMLNoSubelements( element, element.tag, "d4hg" )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"def":
                if Globals.debugFlag: assert( element.text )
                definition = element.text
                Globals.checkXMLNoTail( element, element.tag, "dcf2" )
                Globals.checkXMLNoAttributes( element, element.tag, "d4hg" )
                Globals.checkXMLNoSubelements( element, element.tag, "d4hg" )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"xref":
                location = "xref of " + ID
                Globals.checkXMLNoText( element, element.tag, "jd52" )
                Globals.checkXMLNoTail( element, element.tag, "dvj3" )
                Globals.checkXMLNoSubelements( element, element.tag, "d4hg" )
                # Process the attributes
                for attrib,value in element.items():
                    if attrib=="bdb": bdbXref = value
                    elif attrib=="strong": strongsXref = value
                    elif attrib=="aug": strongsAugXref = value
                    elif attrib=="twot": twotXref = value
                    else: logging.warning( "scs4 Unprocessed '{}' attribute ({}) in {}".format( attrib, value, location ) )
            elif element.tag == LexicalIndexFileConverter.HebLexNameSpace+"etym":
                location = "etym of " + ID
                #assert( element.text )
                etym = element.text
                Globals.checkXMLNoTail( element, element.tag, "caw2" )
                Globals.checkXMLNoSubelements( element, element.tag, "d4hg" )
                # Process the attributes
                for attrib,value in element.items():
                    if attrib=="type": etymType = value
                    elif attrib=="root": etymRoot = value
                    else: logging.warning( "dsv2 Unprocessed '{}' attribute ({}) in {}".format( attrib, value, location ) )
            else: logging.warning( "sdv1 Unprocessed '{}' sub-element ({}) in entry".format( element.tag, element.text ) )
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element in entry".format( element.tail, element.tag ) )

        self.entries[lang][ID] = (xlit, pos, definition, bdbXref,strongsXref,strongsAugXref,twotXref, etym,etymRoot,etymType)
    # end of LexicalIndexFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.tree if you prefer.)
        """
        if Globals.debugFlag:
            assert( len ( self.tree ) )
            assert( self.entries )
        return self.entries # temp................................XXXXXXXXXXXXXXXXXXXXXXXXXXXXX......................
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
        ...
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
        self.title = self.version = self.date = None
        self.tree = self.header = self.entries = None
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
        if Globals.verbosityLevel > 2: print( _("Loading from {}...").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFilepath = os.path.join( XMLFolder, HebrewStrongsFileConverter.databaseFilename )
        self.tree = ElementTree().parse( XMLFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.tree.tag == HebrewStrongsFileConverter.treeTag:
            for entry in self.tree:
                self.validateEntry( entry )
        else: logging.error( "Expected to load '{}' but got '{}'".format( HebrewStrongsFileConverter.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element".format( self.tree.tail, self.tree.tag ) )
    # end of HebrewStrongsFileConverter.loadAndValidate


    def validateEntry( self, entry ):
        """
        Check/validate the given OSIS div record.
        """
        if Globals.debugFlag: assert( entry.tag == HebrewStrongsFileConverter.HebLexNameSpace+"entry" )
        Globals.checkXMLNoText( entry, entry.tag, "na19" )
        Globals.checkXMLNoTail( entry, entry.tag, "kaq9" )

        # Process the entry attributes first
        entryID = None
        for attrib,value in entry.items():
            if attrib=="id":
                entryID = value
                if Globals.verbosityLevel > 2: print( "Validating {} entry...".format( entryID ) )
            else: logging.warning( "Unprocessed '{}' attribute ({}) in main entry element".format( attrib, value ) )

        entryResults = {}
        for element in entry:
            if element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"w":
                if Globals.debugFlag: assert( element.text )
                word = element.text
                Globals.checkXMLNoTail( element, element.tag, "d4hg" )
                # Process the attributes
                pos = pron = xlit = src = lang = None
                for attrib,value in element.items():
                    if attrib=="pos": pos = value
                    elif attrib=="pron": pron = value
                    elif attrib=="xlit": xlit = value
                    elif attrib=="src": src = value
                    elif attrib==HebrewStrongsFileConverter.XMLNameSpace+"lang":
                        lang = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in {}".format( attrib, value, element.tag ) )
                if word: entryResults['word'] = (word,pos,pron,xlit,src,)
                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == HebrewStrongsFileConverter.HebLexNameSpace+"w":
                        location = "w of w"
                        self.w = subelement.text
                        tail = subelement.tail
                        Globals.checkXMLNoSubelements( subelement, location )
                        src = None
                        for attrib,value in subelement.items():
                            if attrib=="src": src = value
                            #elif attrib=="pron": pron = value
                            #elif attrib=="xlit": xlit = value
                            else: logging.warning( "Unprocessed '{}' attribute ({}) in {}".format( attrib, value, location ) )
                    else: logging.warning( "Unprocessed '{}' sub-element ({}) in {}".format( subelement.tag, subelement.text, element.tag ) )
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"source":
                source = Globals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( entryID, "source", repr(source) )
                if Globals.debugFlag and entryID!='H5223': assert( source and '\t' not in source and '\n' not in source )
                entryResults['source'] = source
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"meaning":
                meaning = Globals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( entryID, "meaning", repr(meaning) )
                if Globals.debugFlag: assert( meaning and '\t' not in meaning and '\n' not in meaning )
                entryResults['meaning'] = meaning
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"usage":
                usage = Globals.getFlattenedXML( element, entryID ) \
                            .replace( HebrewStrongsFileConverter.HebLexNameSpace, '' )
                #print( "usage", repr(usage) )
                if Globals.debugFlag: assert( usage and '\t' not in usage and '\n' not in usage )
                entryResults['usage'] = usage
            elif element.tag == HebrewStrongsFileConverter.HebLexNameSpace+"note":
                if Globals.debugFlag: assert( element.text )
                note = element.text
                Globals.checkXMLNoTail( element, element.tag, "f3g7" )
                Globals.checkXMLNoSubelements( element, element.tag, "m56g" )
                Globals.checkXMLNoAttributes( element, element.tag, "md3d" )
                entryResults['note'] = note
            else: logging.error( "2d4f Unprocessed '{}' element ({}) in entry".format( element.tag, element.text ) ); halt
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element in entry".format( element.tail, element.tag ) )

        #print( entryID, entryResults )
        assert( entryID and entryID[0]=='H' and entryID[1:].isdigit() )
        self.entries[entryID[1:]] = entryResults # leave off the H
    # end of HebrewStrongsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.tree if you prefer.)
        """
        if Globals.debugFlag:
            assert( len ( self.tree ) )
            assert( self.entries )
        return self.entries # temp................................XXXXXXXXXXXXXXXXXXXXXXXXXXXXX......................
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
        self.title = self.version = self.date = None
        self.tree = self.header = self.entries = None
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
        if Globals.debugFlag: assert( len(self.entries) ==  2 )
        result += ('\n' if result else '') + "  " + _("Number of Hebrew entries = {}").format( len(self.entries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of Aramaic entries = {}").format( len(self.entries['arc']) )
        return result
    # end of BrownDriverBriggsFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if Globals.verbosityLevel > 2: print( _("Loading from {}...").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFilepath = os.path.join( XMLFolder, BrownDriverBriggsFileConverter.databaseFilename )
        self.tree = ElementTree().parse( XMLFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        self.entries = {}
        if self.tree.tag == BrownDriverBriggsFileConverter.treeTag:
            for entry in self.tree:
                self.validatePart( entry )
        else: logging.error( "Expected to load '{}' but got '{}'".format( BrownDriverBriggsFileConverter.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element".format( self.tree.tail, self.tree.tag ) )
    # end of BrownDriverBriggsFileConverter.loadAndValidate


    def validatePart( self, part ):
        """
        Check/validate the given lexical index part.
        """
        if Globals.debugFlag: assert( part.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"part" )
        Globals.checkXMLNoText( part, part.tag, "vgb4" )
        Globals.checkXMLNoTail( part, part.tag, "scd1" )

        # Process the part's attributes first
        partID = title = lang = None
        for attrib,value in part.items():
            if attrib == "id":
                partID = value
                if Globals.verbosityLevel > 2: print( "Validating {} part...".format( repr(partID) ) )
            elif attrib == "title":
                title = value
            elif attrib == LexicalIndexFileConverter.XMLNameSpace+"lang":
                lang = value
            else: logging.warning( "scd2 Unprocessed '{}' attribute ({}) in index part element".format( attrib, value ) )
        if Globals.debugFlag: assert( lang in ('heb','arc',) )
        if lang not in self.entries: self.entries[lang] = {}

        for section in part:
            self.validateSection( section, partID, title, lang )
    # end of BrownDriverBriggsFileConverter.validatePart


    def validateSection( self, section, partID, title, lang ):
        """
        Check/validate the given lexical index section.
        """
        if Globals.debugFlag: assert( section.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"section" )
        Globals.checkXMLNoText( section, section.tag, "na19" )
        Globals.checkXMLNoTail( section, section.tag, "kaq9" )

        # Process the section's attributes first
        sectionID = None
        for attrib,value in section.items():
            if attrib == "id":
                sectionID = value
                if Globals.verbosityLevel > 2: print( "Validating {} section...".format( repr(sectionID) ) )
            else: logging.warning( "js19 Unprocessed '{}' attribute ({}) in index section element".format( attrib, value ) )
        for entry in section:
            if entry.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"page":
                # We don't care about the book pages (page elements only have a 'p' attribute)
                Globals.checkXMLNoText( entry, entry.tag, "dv20" )
                Globals.checkXMLNoTail( entry, entry.tag, "jsq2" )
                Globals.checkXMLNoSubelements( entry, entry.tag, "kdd0" )
            else: self.validateEntry( entry, partID, sectionID, title, lang )
    # end of BrownDriverBriggsFileConverter.validateSection


    def validateEntry( self, entry, partID, sectionID, title, lang ):
        """
        Check/validate the given OSIS div record.
        """
        if Globals.debugFlag: assert( entry.tag == BrownDriverBriggsFileConverter.HebLexNameSpace+"entry" )
        #Globals.checkXMLNoText( entry, entry.tag, "na19" )
        Globals.checkXMLNoTail( entry, entry.tag, "kaq9" )

        # Process the entry attributes first
        entryID = entryType = entryMod = entryCite = entryForm = None
        for attrib,value in entry.items():
            if attrib == "id":
                entryID = value
                if Globals.verbosityLevel > 2: print( "Validating {} entry...".format( repr(entryID) ) )
            elif attrib == "type": entryType = value
            elif attrib == "mod": entryMod = value
            elif attrib == "cite": entryCite = value
            elif attrib == "form": entryForm = value
            else: logging.warning( "ngs9 Unprocessed '{}' attribute ({}) in main entry element".format( attrib, value ) )

        flattenedXML = Globals.getFlattenedXML( entry, entryID ) \
                            .replace( BrownDriverBriggsFileConverter.HebLexNameSpace, '' ) \
                            .replace( '\t', '' ).replace( '\n', '' )
        if entryID == "m.ba.ab": flattenedXML = flattenedXML.rstrip() # Seems to have a space at the start of the XML line
        if flattenedXML.endswith( '</status>' ):
            bits = flattenedXML.split( '<status>' )
            if Globals.debugFlag: assert( len(bits) == 2)
            resultXML = bits[0]
            if Globals.debugFlag: assert( bits[1].endswith( '</status>' ) )
            status = bits[1][:-9]
            #print( "st", repr(status) )
            if Globals.debugFlag: assert( status in ('new','made','base','ref','added','done',) )
        else:
            logging.warning( "Missing status in BDB entry: {}".format( repr(flattenedXML) ) )
            resultXML = flattenedXML

        #print( repr(partID), repr(sectionID), repr(title), repr(lang) )
        #print( entryID, status, repr(resultXML) )
        self.entries[lang][entryID] = (resultXML,status,)
    # end of BrownDriverBriggsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.tree if you prefer.)
        """
        if Globals.debugFlag:
            assert( len ( self.tree ) )
            assert( self.entries )
        return self.entries # temp................................XXXXXXXXXXXXXXXXXXXXXXXXXXXXX......................
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
        hASIndex = AugmentedStrongsIndexFileConverter() # Create the empty object
        hASIndex.loadAndValidate( XMLFolder ) # Load the XML
        self.IndexEntries1, self.IndexEntries2 = hASIndex.importDataToPython()
        if Globals.debugFlag: assert( len(self.IndexEntries1) == len(self.IndexEntries2) )
        hLexIndex = LexicalIndexFileConverter() # Create the empty object
        hLexIndex.loadAndValidate( XMLFolder ) # Load the XML
        self.IndexEntries = hLexIndex.importDataToPython()
        if Globals.debugFlag: assert( len(self.IndexEntries) == 2 )
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
        if Globals.debugFlag:
            result1 = self._getStrongsNumberFromLexiconCode1( key )
            result2 = self._getStrongsNumberFromLexiconCode2( key )
            assert( result1 == result2 )
            return result1
        # Normally...
        if key in self.IndexEntries2: return self.IndexEntries2[key]
    # end of HebrewLexiconIndex.getStrongsNumberFromLexiconCode

    def getBDBCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BDB code, e.g., 'm.ba.aa'
        """
        keyDigits = key[1:]
        if key in self.IndexEntries['heb']: return self.IndexEntries['heb'][key][3]
        if key in self.IndexEntries['arc']: return self.IndexEntries['arc'][key][3]
    # end of HebrewLexiconIndex.getBDBCodeFromLexiconCode

    def getTWOTCodeFromLexiconCode( self, key ):
        """
        The key is a three letter code like 'aac'.

        Returns a BDB code, e.g., '4a'
        """
        keyDigits = key[1:]
        if key in self.IndexEntries['heb']: return self.IndexEntries['heb'][key][6]
        if key in self.IndexEntries['arc']: return self.IndexEntries['arc'][key][6]
    # end of HebrewLexiconIndex.getTWOTCodeFromLexiconCode

# end of HebrewLexiconIndex class




class HebrewLexicon:
    """
    Class for handling an Hebrew Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        hStr = HebrewStrongsFileConverter() # Create the empty object
        hStr.loadAndValidate( XMLFolder ) # Load the XML
        self.StrongsEntries = hStr.importDataToPython()
        hBDB = BrownDriverBriggsFileConverter() # Create the empty object
        hBDB.loadAndValidate( XMLFolder ) # Load the XML
        self.BrownDriverBriggsEntries = hBDB.importDataToPython()
    # end of HebrewLexicon.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of Strong's Hebrew entries = {}").format( len(self.StrongsEntries) )
        result += ('\n' if result else '') + "  " + _("Number of BDB Hebrew entries = {}").format( len(self.BrownDriverBriggsEntries['heb']) )
        result += ('\n' if result else '') + "  " + _("Number of BDB Aramaic entries = {}").format( len(self.BrownDriverBriggsEntries['arc']) )
        return result
    # end of HebrewLexicon.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if Globals.debugFlag: assert( key and key[0]=='H' and key[1:].isdigit() )
        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries: return self.StrongsEntries[keyDigits]
    # end of HebrewLexicon.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Hebrew Strong's number (string) like 'H1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if Globals.debugFlag: assert( key and key[0]=='H' and key[1:].isdigit() )
        keyDigits = key[1:]
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of HebrewLexicon.getStrongsEntryField


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
        if Globals.debugFlag: assert( key and key[0]=='H' and key[1:].isdigit() )
        keyDigits = key[1:]
        #if key == 'H1':
            #print( "Should be:" )
            #print( 'sHTML: <li value="1" id="ot:1"><i title="{awb}" xml:lang="hbo">אָב</i> a primitive word; father, in a literal and immediate, or figurative and remote application): <span class="kjv_def">chief, (fore-)father(-less), X patrimony, principal</span>. Compare names in "Abi-".</li>' )
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            source = '{}'.format( entry['source'].replace('<w>','<span class="word">').replace('</w>','</span>').replace('<def>','<span class="def">').replace('</def>','</span>') ) \
                        if 'source' in entry else ''
            meaning = '{}'.format( entry['meaning'].replace('<def>','<span class="def">').replace('</def>','</span>') ) \
                        if 'meaning' in entry else ''
            usage = '<span class="kjv_def">{}</span>'.format( entry['usage'] ) if 'usage' in entry else ''
            html = '<li value="{}" id="ot:{}"><span class="originalWord" title="{{{}}}" xml:lang="hbo">{}</span> {} {} {}</li>' \
                .format( keyDigits, keyDigits, entry['word'][2], entry['word'][0], source, meaning, usage )
            #for j, subentry in enumerate(entry):
                #print( "{} {}={}".format( j, subentry, repr(entry[subentry]) ) )
            return html
    # end of HebrewLexicon.getStrongsEntryHTML


    def getBDBEntryData( self, key ):
        """
        The key is a BDB number (string) like 'a.ca.ab'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g.,

        Returns None if the key is not found.
        """
        if Globals.debugFlag: assert( key and key.count('.')==2 )
        if key in self.BrownDriverBriggsEntries['heb']: return self.BrownDriverBriggsEntries['heb'][key]
        if key in self.BrownDriverBriggsEntries['arc']: return self.BrownDriverBriggsEntries['arc'][key]
    # end of HebrewLexicon.getBDBEntryData


    def getBDBEntryField( self, key, fieldName ):
        """
        The key is a BDB number (string) like 'ah.ba.aa'.
        The fieldName is a name (string) like 'status'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if Globals.debugFlag: assert( key and key.count('.')==2 )
        entry =  self.getBDBEntryData( key )
        if entry:
            if fieldName == 'status': return entry[1]
    # end of HebrewLexicon.getBDBEntryField


    def getBDBEntryHTML( self, key ):
        """
        The key is a BDB number (string) like 'ah.ba.aa'.

        Returns an HTML entry for the given key.
        Returns None if the key is not found.
        """
        if Globals.debugFlag: assert( key and key.count('.')==2 )
        entry =  self.getBDBEntryData( key )
        if entry:
            mainEntry = entry[0] \
                .replace( '<sense>', '<span class="sense">' ).replace( '</sense>', '</span>' ) \
                .replace( '<w>', '<span class="word">' ).replace( '</w>', '</span>' ) \
                .replace( '<pos>', '<span class="pos">' ).replace( '</pos>', '</span>' ) \
                .replace( '<ref>', '<span class="ref">' ).replace( '</ref>', '</span>' ) \
                .replace( '<def>', '<span class="def">' ).replace( '</def>', '</span>' )
            html = '{} <span class="status">{{{}}}</span>'.format( mainEntry, entry[1] )
            return html
    # end of HebrewLexicon.getBDBEntryHTML
# end of HebrewLexicon class




def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    testFolder = "../HebrewLexicon/" # Hebrew lexicon folder


    if 1: # demonstrate the Hebrew Lexicon converter classes
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the converter classes..." )

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

        if Globals.commandLineOptions.export:
            print( "Exports aren't written yet!" )
            #hlc.exportDataToPython() # Produce the .py tables
            #hlc.exportDataToC() # Produce the .h tables
            halt


    if 1: # demonstrate the Hebrew Lexicon Index class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Hebrew Lexicon Index class..." )
        hix = HebrewLexiconIndex( testFolder ) # Load and process the XML
        print( hix ) # Just print a summary
        print()
        print( "Code for 2 is", hix.getLexiconCodeFromStrongsNumber( '2' ) )
        print( "Code for H8674 is", hix.getLexiconCodeFromStrongsNumber( 'H8674' ) )
        print( "Code for H8675 is", hix.getLexiconCodeFromStrongsNumber( 'H8675' ) )
        print( "Codes for aac are", hix.getStrongsNumberFromLexiconCode('aac'), hix.getBDBCodeFromLexiconCode('aac'), hix.getTWOTCodeFromLexiconCode('aac') )
        print( "Codes for nyy are", hix.getStrongsNumberFromLexiconCode('nyy'), hix.getBDBCodeFromLexiconCode('nyy'), hix.getTWOTCodeFromLexiconCode('nyy') )
        print( "Codes for pdc are", hix.getStrongsNumberFromLexiconCode('pdc'), hix.getBDBCodeFromLexiconCode('pdc'), hix.getTWOTCodeFromLexiconCode('pdc') )
        print( "Codes for pdd are", hix.getStrongsNumberFromLexiconCode('pdd'), hix.getBDBCodeFromLexiconCode('pdd'), hix.getTWOTCodeFromLexiconCode('pdd') )


    if 1: # demonstrate the Hebrew Lexicon class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Hebrew Lexicon class..." )
        hl = HebrewLexicon( testFolder ) # Load and process the XML
        print( hl ) # Just print a summary
        print()
        for strongsKey in ('H1','H123','H165','H1732','H1979','H2011','H8674','H8675',): # Last one is invalid
            print( '\n' + strongsKey )
            print( " Data:", hl.getStrongsEntryData( strongsKey ) )
            print( " Usage:", hl.getStrongsEntryField( strongsKey, 'usage' ) )
            print( " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
        for BDBKey in ('a.ab.ac','a.gq.ab','b.aa.aa','xw.ah.ah','xy.zz.zz',): # Last one is invalid
            print( '\n' + BDBKey )
            print( " Data:", hl.getBDBEntryData( BDBKey ) )
            print( " Status:", hl.getBDBEntryField( BDBKey, 'status' ) )
            print( " HTML:", hl.getBDBEntryHTML( BDBKey ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of HebrewLexicon.py