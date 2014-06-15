#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ZefaniaXMLBible.py
#   Last modified: 2014-06-15 by RJH (also update ProgVersion below)
#
# Module handling Zefania XML Bibles
#
# Copyright (C) 2013-2014 Robert Hunt
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
    <!--Nice Viewer for this file are found here-->     # May or may not have these editor lines
    <!--http://www.theword.gr-->
    <!--http://www.mybible.de-->
    <!--http://bgfdb.de/zefaniaxml/bml/-->
    <!--Visit the online documentation for Zefania XML Markup-->
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

ProgName = "Zefania XML Bible format handler"
ProgVersion = "0.28"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )


import logging, os
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import Globals
from BibleOrganizationalSystems import BibleOrganizationalSystem
#from InternalBible import InternalBible
#from InternalBibleBook import InternalBibleBook
#from BibleWriter import BibleWriter
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML', 'JAR',
                    'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'STY', 'SSF', 'TXT', 'USFM', 'USFX', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def ZefaniaXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for Zefania XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one Zefania Bible is found,
        returns the loaded ZefaniaXMLBible object.
    """
    if Globals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ZefaniaXMLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ZefaniaXMLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " ZefaniaXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories
    #print( 'ff', foundFiles )

    # See if there's an Zefania project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or Globals.strictCheckingFlag:
            firstLines = Globals.peekIntoFile( thisFilename, givenFolderName, numLines=2 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if Globals.verbosityLevel > 2: print( "ZB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                continue
            if not firstLines[1].startswith( '<XMLBIBLE' ) \
            and not firstLines[1].startswith( '<!--Nice Viewer' ) \
            and not firstLines[1].startswith( '<!--Builded with' ) \
            and not firstLines[1].startswith( '<!--For Programmers' ) \
            and not firstLines[1].startswith( '<!--http://zefania' ):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            ub = ZefaniaXMLBible( givenFolderName, lastFilenameFound )
            ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if Globals.verbosityLevel > 3: print( "    ZefaniaXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )
        #print( 'fsf', foundSubfiles )

        # See if there's an Zefania project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLines = Globals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if Globals.verbosityLevel > 2: print( "ZB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<XMLBIBLE' ) \
                and not firstLines[1].startswith( '<!--Nice Viewer' ) \
                and not firstLines[1].startswith( '<!--Builded with' ) \
                and not firstLines[1].startswith( '<!--For Programmers' ) \
                and not firstLines[1].startswith( '<!--http://zefania' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            ub = ZefaniaXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            ub.load() # Load and process the file
            return ub
        return numFound
# end of ZefaniaXMLBibleFileCheck



class ZefaniaXMLBible( Bible ):
    """
    Class for reading, validating, and converting ZefaniaXMLBible XML.
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


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Zefania Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "Zefania XML Bible object"
        self.objectTypeString = "Zefania"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.tree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "ZefaniaXMLBible: File '{}' is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of ZefaniaXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        self.tree = ElementTree().parse( self.sourceFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.tree.tag == ZefaniaXMLBible.treeTag:
            location = "Zefania XML file"
            Globals.checkXMLNoText( self.tree, location, '4f6h' )
            Globals.checkXMLNoTail( self.tree, location, '1wk8' )

            schema = None
            name = status = BibleType = revision = version = lgid = None
            for attrib,value in self.tree.items():
                if attrib == ZefaniaXMLBible.XMLNameSpace + 'noNamespaceSchemaLocation':
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
                if element.tag == ZefaniaXMLBible.bookTag:
                    sublocation = "book in " + location
                    Globals.checkXMLNoText( element, sublocation, 'g3g5' )
                    Globals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load '{}' but got '{}'".format( ZefaniaXMLBible.treeTag, self.tree.tag ) )
        self.doPostLoadProcessing()
    # end of ZefaniaXMLBible.load


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
        if Globals.debugFlag: assert( self.header )
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
                if Globals.debugFlag: assert( element.text )
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
                if Globals.debugFlag: assert( element.text )
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
                if Globals.debugFlag: assert( element.text )
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
                if Globals.debugFlag: assert( element.text )
                if Globals.debugFlag: assert( element.text == 'Zefania XML Bible Markup Language' )
            elif element.tag == 'identifier':
                sublocation = "identifier in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if Globals.debugFlag: assert( element.text )
                self.identifier = element.text
            elif element.tag == 'source':
                sublocation = "source in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if Globals.debugFlag: assert( element.text )
                self.source = element.text
            elif element.tag == 'language':
                sublocation = "language in {}".format( location )
                Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                Globals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                Globals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if Globals.debugFlag: assert( element.text )
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
    # end of ZefaniaXMLBible.__validateAndExtractHeader


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
            thisBook = BibleBook( self.name, BBB )
            thisBook.objectNameString = "Zefania XML Bible Book object"
            thisBook.objectTypeString = "Zefania"
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == ZefaniaXMLBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    Globals.checkXMLNoText( element, sublocation, 'j3jd' )
                    Globals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaXMLBible.chapterTag, element.tag ) )
            if Globals.verbosityLevel > 2: print( "  Saving {} into results...".format( BBB ) )
            self.saveBook( thisBook )
    # end of ZefaniaXMLBible.__validateAndExtractBook


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
            if element.tag == ZefaniaXMLBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            elif element.tag == ZefaniaXMLBible.captionTag: # Used in Psalms
                location = "caption in {} {}".format( BBB, chapterNumber )
                Globals.checkXMLNoTail( element, location, 'k5k8' )
                Globals.checkXMLNoSubelements( element, location, 'd3f5' )
                # Handle caption attributes
                vRef = None
                for attrib,value in element.items():
                    if attrib=="vref":
                        vRef = value
                        if Globals.debugFlag: assert( vRef == '1' )
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in caption element".format( attrib, value ) )
                if Globals.debugFlag: assert( vRef )
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, vRef ) )
                if vText: # This is the main text of the caption
                    #print( "{} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, vText ) )
                    thisBook.appendLine( 'v', '0' + ' ' + vText ) # We save it as verse zero
            else: logging.error( "Expected to find '{}' but got '{}'".format( ZefaniaXMLBible.verseTag, element.tag ) )
    # end of ZefaniaXMLBible.__validateAndExtractChapter


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
        if Globals.debugFlag: assert( verseNumber )
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.appendLine( 'v', verseNumber )
        vText = verse.text
        if vText: vText = vText.strip()
        #if not vText: # This happens if a verse starts immediately with a style or note
            #logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )

        # Handle verse subelements (notes and styled portions)
        for subelement in verse:
            if subelement.tag == ZefaniaXMLBible.noteTag:
                sublocation = "note in " + location
                noteType = None
                for attrib,value in subelement.items():
                    if attrib=="type":
                        noteType = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                if noteType not in ('n-studynote','x-studynote',):
                    logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                if Globals.debugFlag: assert( noteType )
                nText, nTail = subelement.text, subelement.tail
                #print( "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                #thisBook.appendLine( 'ST', css ) # XXXXXXXXXXXXXXXXXXXXXXXXXX Losing data here (for now)
                #thisBook.appendLine( 'ST=', nText )
                if nTail:
                    if '\n' in nTail:
                        print( "ZefaniaXMLBible.__validateAndExtractVerse: nTail {} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, nTail ) )
                        nTail = nTail.replace( '\n', ' ' )
                    thisBook.appendLine( 'v~', nTail )
                for subsubelement in subelement:
                    if subsubelement.tag == ZefaniaXMLBible.styleTag:
                        subsublocation = "style in " + sublocation
                        Globals.checkXMLNoSubelements( subsubelement, subsublocation, 'fyt4' )
                        css = idStyle = None
                        for attrib,value in subsubelement.items():
                            if attrib=="css":
                                css = value
                            elif attrib=="id":
                                idStyle = value
                            else: logging.warning( "Unprocessed '{}' attribute ({}) in style subsubelement".format( attrib, value ) )
                        if Globals.debugFlag: assert( css or idStyle )
                        SFM = None
                        if css == "font-style:italic": SFM = '\\it'
                        elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        elif css == "color:#FF0000": SFM = '\\em'
                        elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        else: print( "css is", css, "idStyle is", idStyle ); halt
                        sText, sTail = subsubelement.text.strip(), subsubelement.tail
                        if Globals.debugFlag: assert( sText )
                        if SFM: vText += SFM+' ' + sText + SFM+'*'
                        else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        if sTail: vText += sTail.strip()
                    else: logging.error( "Expected to find {} but got '{}' in {}".format( ZefaniaXMLBible.styleTag, subsubelement.tag, sublocation ) )

            elif subelement.tag == ZefaniaXMLBible.styleTag:
                sublocation = "style in " + location
                Globals.checkXMLNoSubelements( subelement, sublocation, 'f5gh' )
                css = idStyle = None
                for attrib,value in subelement.items():
                    if attrib=="css":
                        css = value
                    elif attrib=="id":
                        idStyle = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                if Globals.debugFlag: assert( css or idStyle )
                SFM = None
                if css == "font-style:italic": SFM = '\\it'
                elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                elif css == "color:#FF0000": SFM = '\\em'
                elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                else: print( "css is", css, "idStyle is", idStyle ); halt
                sText, sTail = subelement.text.strip(), subelement.tail
                if Globals.debugFlag: assert( sText )
                if SFM: vText += SFM+' ' + sText + SFM+'*'
                else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                if sTail: vText += sTail.strip()

            elif subelement.tag == ZefaniaXMLBible.breakTag:
                sublocation = "line break in " + location
                Globals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                Globals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                art = None
                for attrib,value in subelement.items():
                    if attrib=="art":
                        art = value
                    else: logging.warning( "Unprocessed '{}' attribute ({}) in style subelement".format( attrib, value ) )
                if Globals.debugFlag: assert( art == 'x-nl' )
                #print( BBB, chapterNumber, verseNumber )
                #assert( vText )
                if vText:
                    thisBook.appendLine( 'v', verseNumber + ' ' + vText )
                    vText = ''
                thisBook.appendLine( 'm', subelement.tail.strip() if subelement.tail else '' )
                #bTail = subelement.tail
                #if bTail: vText = bTail.strip()
            else: logging.error( "Expected to find NOTE or STYLE but got '{}' in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            if '\n' in vText:
                print( "ZefaniaXMLBible.__validateAndExtractVerse: vText {} {}:{} '{}'".format( BBB, chapterNumber, verseNumber, vText ) )
                vText = vText.replace( '\n', ' ' )
            thisBook.appendLine( 'v', verseNumber + ' ' + vText )
    # end of ZefaniaXMLBible.__validateAndExtractVerse
# end of ZefaniaXMLBible class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = "Tests/DataFilesForTests/ZefaniaTest/"
        #testFolder = "../../../../../Data/Work/Bibles/Zefania modules/"
        print( "TestA1", ZefaniaXMLBibleFileCheck( testFolder ) )
        print( "TestA2", ZefaniaXMLBibleFileCheck( testFolder, autoLoad=True ) )
        #testSubfolder = os.path.join( testFolder, 'something/' )
        #print( "TestB1", ZefaniaXMLBibleFileCheck( testSubfolder ) )
        #print( "TestB2", ZefaniaXMLBibleFileCheck( testSubfolder, autoLoad=True ) )
    halt

    if 1:
        testFolder = "../../../../../Data/Work/Bibles/Zefania modules/"
        #testFolder = "Tests/DataFilesForTests/ZefaniaTest/"
        single = ( "kjv.xml", )
        good = ( "BWE_zefania.xml", "en_gb_KJV2000.xml", "Etheridge_zefania.xml", "kjv.xml", "OEB_zefania.xml", \
            'sf_elb_1871_original_NT_rev1.xml', 'sf_wycliffe.xml', 'ylt.xml')
        nonEnglish = ( "italian.xml", )
        bad = (  )
        allOfThem = good + nonEnglish + bad

        for j, testFilename in enumerate( allOfThem ): # Choose one of the above lists for testing
            testFilepath = os.path.join( testFolder, testFilename )

            # Demonstrate the XML Bible class
            if Globals.verbosityLevel > 1: print( "\nZ B{}/ Demonstrating the Zefania Bible class...".format( j+1 ) )
            if Globals.verbosityLevel > 0: print( "  Test filepath is '{}'".format( testFilepath ) )
            zb = ZefaniaXMLBible( testFolder, testFilename )
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
                    svk = VerseReferences.SimpleVerseKey( b, c, v )
                    #print( svk, ob.getVerseDataList( reference ) )
                    try: print( reference, svk.getShortText(), zb.getVerseText( svk ) )
                    except KeyError: print( testFilename, reference, "doesn't exist" )


    #if 1: # See how well Haggai XML modules load using this program
        #testFolder = "../../../../../Data/Work/Bibles/Formats/Haggai XML/"
        #count = totalBooks = 0
        #if os.access( testFolder, os.R_OK ): # check that we can read the test data
            #for something in sorted( os.listdir( testFolder ) ):
                #somepath = os.path.join( testFolder, something )
                #if os.path.isfile( somepath ) and something.endswith( '.xml' ):
                    #count += 1
                    #if Globals.verbosityLevel > 0: print( "\nZH C{}/ {}".format( count, something ) )
                    #zb = ZefaniaXMLBible( testFolder, something )
                    #zb.load()
                    #if Globals.verbosityLevel > 0: print( zb )
                    #if Globals.strictCheckingFlag:
                        #zb.check()
                        ##UBErrors = UB.getErrors()
                        ## print( UBErrors )
                    ##print( UB.getVersification () )
                    ##print( UB.getAddedUnits () )
                    ##for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                        ###print( "Looking for", ref )
                        ##print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
                    #if 1: # Test verse lookup
                        #import VerseReferences
                        #for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                            #('OT','DAN','1','21'),
                                            #('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                            #('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                            #(t, b, c, v) = reference
                            #if t=='OT' and len(zb)==27: continue # Don't bother with OT references if it's only a NT
                            #if t=='NT' and len(zb)==39: continue # Don't bother with NT references if it's only a OT
                            #if t=='DC' and len(zb)<=66: continue # Don't bother with DC references if it's too small
                            #svk = VerseReferences.SimpleVerseKey( b, c, v )
                            ##print( svk, ob.getVerseDataList( reference ) )
                            #try: print( reference, svk.getShortText(), zb.getVerseText( svk ) )
                            #except KeyError: print( something, reference, "doesn't exist" )
                    #if Globals.commandLineOptions.export:
                        #zb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                #else: print( "Sorry, skipping {}.".format( something ) )
            #if count: print( "\n{} total Zefania Bibles processed.".format( count ) )
        #else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testBaseFolder ) )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of ZefaniaXMLBible.py