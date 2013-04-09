#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ZefaniaBible.py
#   Last modified: 2013-04-09 by RJH (also update versionString below)
#
# Module handling simple XML Bibles
#
# Copyright (C) 2013 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
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
Module reading and loading Zefania XML Bibles:
    <?xml version="1.0" encoding="utf-8"?>
    <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status="v" biblename="King James Version" type="x-bible" revision="0">
    <INFORMATION>
        <title>King James Version</title>
        <creator></creator>
        <subject>The Holy Bible</subject>
        <description>In 1604, King James I of England authorized that a new translation of the Bible into English be started. It was finished in 1611, just 85 years after the first translation of the New Testament into English appeared (Tyndale, 1526). The Authorized Version, or King James Version, quickly became the standard for English-speaking Protestants. Its flowing language and prose rhythm has had a profound influence on the literature of the past 300 years.</description>
        <publisher>FREE BIBLE SOFTWARE GROUP</publisher>
        <contributors />
        <date>2009-01-23</date>
        <type>Bible</type>
        <format>Zefania XML Bible Markup Language</format>
        <identifier>kjv</identifier>
        <source>http://www.unboundbible.com/zips/index.cfm?lang=English</source>
        <language>ENG</language>
        <coverage>provide the Bible to the nations of the world</coverage>
        <rights>We believe that this Bible is found in the Public Domain.</rights>
    </INFORMATION>
    <BIBLEBOOK bnumber="1" bname="Genesis" bsname="Gen">
        <CHAPTER cnumber="1">
        <VERS vnumber="1">In the beginning God created the heaven and the earth.</VERS>
        <VERS vnumber="2">And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.</VERS>

or

    <CHAPTER cnumber="3">
      <CAPTION vref="1">A Psalm of David, when he fled from Absalom his son.</CAPTION>
      <VERS vnumber="1">LORD, how are they increased that trouble me! many are they that rise up against me.</VERS>

or
      <VERS vnumber="3">to snap their bondsand fling their cords away? <BR art="x-nl" /></VERS>
"""

progName = "Zefania Bible format handler"
versionString = "0.20"

import logging, os
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

import Globals
from BibleOrganizationalSystems import BibleOrganizationalSystem
from InternalBible import InternalBible
from InternalBibleBook import InternalBibleBook


class ZefaniaBible( InternalBible ):
    """
    Class for reading, validating, and converting ZefaniaBible XML.
    """
    XMLNameSpace = "{http://www.w3.org/2001/XMLSchema-instance}"
    treeTag = 'XMLBIBLE'
    infoTag = 'INFORMATION'
    bookTag = 'BIBLEBOOK'
    chapterTag = 'CHAPTER'
    captionTag = 'CAPTION'
    verseTag = 'VERS'
    noteTag = 'NOTE'
    styleTag = 'STYLE'
    breakTag = 'BR'


    def __init__( self, sourceFilepath, givenName=None, encoding='utf-8', logErrorsFlag=False  ):
        """
        Constructor: just sets up the Zefania Bible object.
        """
         # Setup and initialise the base class first
        self.objectType = "Zefania"
        self.objectNameString = "Zefania Bible object"
        InternalBible.__init__( self )

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.encoding, self.logErrorsFlag = sourceFilepath, givenName, encoding, logErrorsFlag

        self.tree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "ZefaniaBible: File '{}' is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of ZefaniaBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        self.tree = ElementTree().parse( self.sourceFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.tree.tag == ZefaniaBible.treeTag:
            location = "Zefania XML file"
            Globals.checkXMLNoText( self.tree, location, '4f6h' )
            Globals.checkXMLNoTail( self.tree, location, '1wk8' )

            schema = None
            name = status = BibleType = revision = lgid = None
            for attrib,value in self.tree.items():
                if attrib == ZefaniaBible.XMLNameSpace + 'noNamespaceSchemaLocation':
                    schema = value
                elif attrib == "biblename":
                    name = value
                elif attrib == "lgid":
                    lgid = value # In italian.xml this is set to "german"
                elif attrib == "status":
                    status = value
                elif attrib == "type":
                    BibleType = value
                elif attrib == "revision":
                    revision = value
                elif attrib == "version":
                    version = value
                else: logging.warning( "Unprocessed '{}' attribute ({}) in main element".format( attrib, value ) )
            if name: self.name = name
            if status: self.status = status
            if revision: self.revision = revision
            if version: self.version = version

            if self.tree[0].tag == 'INFORMATION':
                self.header = self.tree[0]
                self.tree.remove( self.header )
                self.__validateAndExtractHeader()
            else: # Handle information records at the END of the file
                ix = len(self.tree) - 1
                if self.tree[ix].tag == 'INFORMATION':
                    self.header = self.tree[ix]
                    self.tree.remove( self.header )
                    self.__validateAndExtractHeader()

            # Find the submain (book) containers
            for element in self.tree:
                if element.tag == ZefaniaBible.bookTag:
                    sublocation = "book in " + location
                    Globals.checkXMLNoText( element, sublocation, 'g3g5' )
                    Globals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load '{}' but got '{}'".format( ZefaniaBible.treeTag, self.tree.tag ) )
    # end of ZefaniaBible.load


    def __validateAndExtractHeader( self ):
        """
        Extracts information out of the header record, such as:
            <INFORMATION>
            <title>King James Version</title>
            <creator></creator>
            <subject>The Holy Bible</subject>
            <description>In 1604, King James I of England authorized that a new translation of the Bible into English be started. It was finished in 1611, just 85 years after the first translation of the New Testament into English appeared (Tyndale, 1526). The Authorized Version, or King James Version, quickly became the standard for English-speaking Protestants. Its flowing language and prose rhythm has had a profound influence on the literature of the past 300 years.</description>
            <publisher>FREE BIBLE SOFTWARE GROUP</publisher>
            <contributors />
            <date>2009-01-23</date>
            <type>Bible</type>
            <format>Zefania XML Bible Markup Language</format>
            <identifier>kjv</identifier>
            <source>http://www.unboundbible.com/zips/index.cfm?lang=English</source>
            <language>ENG</language>
            <coverage>provide the Bible to the nations of the world</coverage>
            <rights>We believe that this Bible is found in the Public Domain.</rights>
        </INFORMATION>
        """
        assert( self.header )
        location = 'Header'
        Globals.checkXMLNoAttributes( self.header, location, 'j4j6' )
        Globals.checkXMLNoText( self.header, location, 'sk4l' )
        Globals.checkXMLNoTail( self.header, location, 'a2d4' )

        # TODO: We probably need to rationalise some of the self.xxx stores
        for element in self.header:
            #print( "header", element.tag )
            if element.tag == 'title':
                sublocation = "title in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.title = element.text
            elif element.tag == 'creator':
                sublocation = "creator in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.creator = element.text
            elif element.tag == 'subject':
                sublocation = "subject in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.subject = element.text
            elif element.tag == 'description':
                sublocation = "description in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.description = element.text
            elif element.tag == 'publisher':
                sublocation = "publisher in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.publisher = element.text
            elif element.tag == 'contributors':
                sublocation = "contributors in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.contributors = element.text
            elif element.tag == 'date':
                sublocation = "date in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.date = element.text
            elif element.tag == 'type':
                sublocation = "type in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.documentType = element.text
            elif element.tag == 'format':
                sublocation = "format in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                assert( element.text == 'Zefania XML Bible Markup Language' )
            elif element.tag == 'identifier':
                sublocation = "identifier in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.identifier = element.text
            elif element.tag == 'source':
                sublocation = "source in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.source = element.text
            elif element.tag == 'language':
                sublocation = "language in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                assert( element.text )
                self.language = element.text
            elif element.tag == 'coverage':
                sublocation = "coverage in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.coverage = element.text
            elif element.tag == 'rights':
                sublocation = "rights in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.rights = element.text
            else: logging.error( "Found unexpected '{}' tag in {}".format( element.tag, location ) )
    # end of ZefaniaBible.__validateAndExtractHeader


    def __validateAndExtractBook( self, book ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """

        if Globals.verbosityLevel > 3: print( _("Validating XML book...") )

        # Process the div attributes first
        BBB = bookName = bookShortName = bookNumber = None
        for attrib,value in book.items():
            if attrib=="bnumber":
                bookNumber = value
            elif attrib=="bname":
                bookName = value
            elif attrib=="bsname":
                bookShortName = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in book element".format( attrib, value ) )
        if bookNumber:
            try: BBB = Globals.BibleBooksCodes.getBBBFromReferenceNumber( bookNumber )
            except KeyError:
                logging.warning( "Unable to deduce which book is number={}, name={}, shortName={} -- ignoring it" \
                                                                        .format( bookNumber, bookName, bookShortName ) )
        elif bookName:
            BBB = self.genericBOS.getBBB( bookName )

        if BBB:
            if Globals.verbosityLevel > 2: print( _("Validating {} {}...").format( BBB, bookName ) )
            thisBook = InternalBibleBook( BBB, self.logErrorsFlag )
            thisBook.objectType = "XML"
            thisBook.objectNameString = "XML Bible Book object"
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == ZefaniaBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    Globals.checkXMLNoText( element, sublocation, 'j3jd' )
                    Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaBible.chapterTag, element.tag ) )
            if Globals.verbosityLevel > 2: print( "  Saving {} into results...".format( BBB ) )
            self.saveBook( BBB, thisBook )
    # end of ZefaniaBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if Globals.verbosityLevel > 3: print( _("Validating XML chapter...") )

        # Process the chapter attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="cnumber":
                chapterNumber = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #print( BBB, 'c', chapterNumber )
            thisBook.appendLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for BBB".format( BBB ) )

        for element in chapter:
            if element.tag == ZefaniaBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            elif element.tag == ZefaniaBible.captionTag: # Used in Psalms
                location = "caption in {} {}".format( BBB, chapterNumber )
                Globals.checkXMLNoTail( element, location, 'k5k8' )
                Globals.checkXMLNoSubelements( element, location, 'd3f5' )
                # Handle caption attributes
                vRef = None
                for attrib,value in element.items():
                    if attrib=="vref":
                        vRef = value
                        assert( vRef == '1' )
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in caption element".format( attrib, value ) )
                assert( vRef )
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, vRef ) )
                if vText: # This is the main text of the caption
                    #print( "{} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, vText ) )
                    thisBook.appendLine( 'v', '0' + ' ' + vText ) # We save it as verse zero
            else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaBible.verseTag, element.tag ) )
    # end of ZefaniaBible.__validateAndExtractChapter


    def __validateAndExtractVerse( self, BBB, chapterNumber, thisBook, verse ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if Globals.verbosityLevel > 3: print( _("Validating XML verse...") )

        location = "verse in {} {}".format( BBB, chapterNumber )
        Globals.checkXMLNoTail( verse, location, 'l5ks' )

        # Handle verse attributes
        verseNumber = toVerseNumber = None
        for attrib,value in verse.items():
            if attrib=="vnumber":
                verseNumber = value
            else: logging.warning( "Unprocessed '{}' attribute ({}) in verse element".format( attrib, value ) )
        assert( verseNumber )
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.appendLine( 'v', verseNumber )
        vText = verse.text
        if vText: vText = vText.strip()
        #if not vText: # This happens if a verse starts immediately with a style or note
            #logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )

        # Handle verse subelements (notes and styled portions)
        for subelement in verse:
            if subelement.tag == ZefaniaBible.noteTag:
                sublocation = "note in " + location
                noteType = None
                for attrib,value in subelement.items():
                    if attrib=="type":
                        noteType = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                if noteType not in ('n-studynote','x-studynote',):
                    logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                assert( noteType )
                nText, nTail = subelement.text, subelement.tail
                #print( "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                #thisBook.appendLine( 'ST', css ) # XXXXXXXXXXXXXXXXXXXXXXXXXX Losing data here (for now)
                #thisBook.appendLine( 'ST=', nText )
                if nTail: thisBook.appendLine( 'v=', nTail )
                for subsubelement in subelement:
                    if subsubelement.tag == ZefaniaBible.styleTag:
                        subsublocation = "style in " + sublocation
                        Globals.checkXMLNoSubelements( subsubelement, subsublocation, 'fyt4' )
                        css = idStyle = None
                        for attrib,value in subsubelement.items():
                            if attrib=="css":
                                css = value
                            elif attrib=="id":
                                idStyle = value
                            else: logging.warning( "Unprocessed '{}' attribute ({}) in style subsubelement".format( attrib, value ) )
                        assert( css or idStyle )
                        SFM = None
                        if css == "font-style:italic": SFM = '\\it'
                        elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        elif css == "color:#FF0000": SFM = '\\em'
                        elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        else: print( "css is", css, "idStyle is", idStyle ); halt
                        sText, sTail = subsubelement.text.strip(), subsubelement.tail
                        assert( sText )
                        if SFM: vText += SFM+' ' + sText + SFM+'*'
                        else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        if sTail: vText += sTail.strip()
                    else: logging.error( "Expected to find {} but got '{}' in {}".format( ZefaniaBible.styleTag, subsubelement.tag, sublocation ) )

            elif subelement.tag == ZefaniaBible.styleTag:
                sublocation = "style in " + location
                Globals.checkXMLNoSubelements( subelement, sublocation, 'f5gh' )
                css = idStyle = None
                for attrib,value in subelement.items():
                    if attrib=="css":
                        css = value
                    elif attrib=="id":
                        idStyle = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                assert( css or idStyle )
                SFM = None
                if css == "font-style:italic": SFM = '\\it'
                elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                elif css == "color:#FF0000": SFM = '\\em'
                elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                else: print( "css is", css, "idStyle is", idStyle ); halt
                sText, sTail = subelement.text.strip(), subelement.tail
                assert( sText )
                if SFM: vText += SFM+' ' + sText + SFM+'*'
                else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                if sTail: vText += sTail.strip()

            elif subelement.tag == ZefaniaBible.breakTag:
                sublocation = "line break in " + location
                Globals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                Globals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                art = None
                for attrib,value in subelement.items():
                    if attrib=="art":
                        art = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                assert( art == 'x-nl' )
                if vText:
                    thisBook.appendLine( 'v', verseNumber + ' ' + vText )
                    vText = ''
                    thisBook.appendLine( 'p', '' )
                bTail = subelement.tail
                if bTail: vText = bTail.strip()
            else: logging.error( "Expected to find NOTE or STYLE but got '{}' in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            #if '\\' in vText: print( "{} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, vText ) )
            thisBook.appendLine( 'v', verseNumber + ' ' + vText )
    # end of ZefaniaBible.__validateAndExtractVerse
# end of ZefaniaBible class


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    testFolder = "/mnt/Data/Work/Bibles/Zefania modules/"
    #testFolder = "Tests/DataFilesForTests/ZefaniaTest/"
    single = ( "kjv.xml", )
    good = ( "BWE_zefania.xml", "en_gb_KJV2000.xml", "Etheridge_zefania.xml", "kjv.xml", "OEB_zefania.xml", \
        'sf_elb_1871_original_NT_rev1.xml', 'sf_wycliffe.xml', 'ylt.xml')
    nonEnglish = ( "italian.xml", )
    bad = (  )

    for testFilename in good: # Choose one of the above lists for testing
        testFilepath = os.path.join( testFolder, testFilename )

        # Demonstrate the XML Bible class
        if Globals.verbosityLevel > 1: print( "\nDemonstrating the Zefania Bible class..." )
        if Globals.verbosityLevel > 0: print( "  Test filepath is '{}'".format( testFilepath ) )
        zb = ZefaniaBible( testFilepath )
        zb.load() # Load and process the XML
        print( zb ) # Just print a summary
        #print( zb.books['JDE']._processedLines )
        if 1: # Test verse lookup
            import VerseReferences
            for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                ('OT','DAN','1','21'),
                                ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                (t, b, c, v) = reference
                if t=='OT' and len(zb)==27: continue # Don't bother with OT references if it's only a NT
                if t=='NT' and len(zb)==39: continue # Don't bother with NT references if it's only a OT
                if t=='DC' and len(zb)<=66: continue # Don't bother with DC references if it's too small
                svk = VerseReferences.simpleVerseKey( b, c, v )
                #print( svk, ob.getVerseDataList( reference ) )
                print( reference, svk.getShortText(), zb.getVerseText( svk ) )
# end of main

if __name__ == '__main__':
    main()
# end of ZefaniaBible.py