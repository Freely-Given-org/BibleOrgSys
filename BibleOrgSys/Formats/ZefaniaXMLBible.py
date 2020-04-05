#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ZefaniaXMLBible.py
#
# Module handling Zefania XML Bibles
#
# Copyright (C) 2013-2020 Robert Hunt
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

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-03-15' # by RJH
SHORT_PROGRAM_NAME = "ZefaniaBible"
PROGRAM_NAME = "Zefania XML Bible format handler"
PROGRAM_VERSION = '0.36'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USFX', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def ZefaniaXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Zefania XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one Zefania Bible is found,
        returns the loaded ZefaniaXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ZefaniaXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ZefaniaXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ZefaniaXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    #print( 'ff', foundFiles )

    # See if there's an Zefania project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=2 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "ZB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if not firstLines[1].startswith( '<XMLBIBLE' ) \
            and not firstLines[1].startswith( '<!--Nice Viewer' ) \
            and not firstLines[1].startswith( '<!--Builded with' ) \
            and not firstLines[1].startswith( '<!--For Programmers' ) \
            and not firstLines[1].startswith( '<!--Visit the' ) \
            and not firstLines[1].startswith( '<!--http://zefania' ):
                if BibleOrgSysGlobals.debugFlag: print( "ZefaniaXMLBibleFileCheck rejecting1 second line: {}".format( firstLines[1] ) )
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = ZefaniaXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ZefaniaXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "ZB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<XMLBIBLE' ) \
                and not firstLines[1].startswith( '<!--Nice Viewer' ) \
                and not firstLines[1].startswith( '<!--Builded with' ) \
                and not firstLines[1].startswith( '<!--For Programmers' ) \
                and not firstLines[1].startswith( '<!--Visit the' ) \
                and not firstLines[1].startswith( '<!--http://zefania' ):
                    if BibleOrgSysGlobals.debugFlag: print( "ZefaniaXMLBibleFileCheck rejecting1 second line: {}".format( firstLines[1] ) )
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ZefaniaXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = ZefaniaXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
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
    divTag = 'DIV'
    verseTag = 'VERS'
    noteTag = 'NOTE'
    styleTag = 'STYLE'
    breakTag = 'BR'
    grTag = 'gr'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Zefania Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Zefania XML Bible object'
        self.objectTypeString = 'Zefania'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.XMLTree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.warning( "ZefaniaXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of ZefaniaXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        self.XMLTree = ElementTree().parse( self.sourceFilepath )
        if BibleOrgSysGlobals.debugFlag: assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.XMLTree.tag == ZefaniaXMLBible.treeTag:
            location = "Zefania XML file"
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8' )

            schema = name = status = BibleType = revision = version = lgid = None
            for attrib,value in self.XMLTree.items():
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
                elif attrib == 'version':
                    version = value
                else: logging.warning( "Unprocessed {!r} attribute ({}) in main element".format( attrib, value ) )
            if name: self.name = name
            if status: self.status = status
            if revision: self.revision = revision
            if version: self.version = version

            if self.XMLTree[0].tag == 'INFORMATION':
                self.header = self.XMLTree[0]
                self.XMLTree.remove( self.header )
                self.__validateAndExtractHeader()
            else: # Handle information records at the END of the file
                ix = len(self.XMLTree) - 1
                if self.XMLTree[ix].tag == 'INFORMATION':
                    self.header = self.XMLTree[ix]
                    self.XMLTree.remove( self.header )
                    self.__validateAndExtractHeader()

            # Find the submain (book) containers
            for element in self.XMLTree:
                if element.tag == ZefaniaXMLBible.bookTag:
                    sublocation = "book in " + location
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'g3g5' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                else: logging.error( "Expected to find {!r} but got {!r}".format( ZefaniaXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( ZefaniaXMLBible.treeTag, self.XMLTree.tag ) )
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
        if BibleOrgSysGlobals.debugFlag: assert self.header
        location = 'Header'
        BibleOrgSysGlobals.checkXMLNoAttributes( self.header, location, 'j4j6' )
        BibleOrgSysGlobals.checkXMLNoText( self.header, location, 'sk4l' )
        BibleOrgSysGlobals.checkXMLNoTail( self.header, location, 'a2d4' )

        # TODO: We probably need to rationalise some of the self.xxx stores
        for element in self.header:
            #print( 'header', element.tag )
            if element.tag == 'title':
                sublocation = "title in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.title = element.text
            elif element.tag == 'creator':
                sublocation = "creator in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.creator = element.text
            elif element.tag == 'subject':
                sublocation = "subject in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.subject = element.text
            elif element.tag == 'description':
                sublocation = "description in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.description = element.text
            elif element.tag == 'publisher':
                sublocation = "publisher in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.publisher = element.text
            elif element.tag == 'contributors':
                sublocation = "contributors in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.contributors = element.text
            elif element.tag == 'date':
                sublocation = "date in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.date = element.text
            elif element.tag == 'type':
                sublocation = "type in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.documentType = element.text
            elif element.tag == 'format':
                sublocation = "format in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text == 'Zefania XML Bible Markup Language'
            elif element.tag == 'identifier':
                sublocation = "identifier in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.identifier = element.text
            elif element.tag == 'source':
                sublocation = "source in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.source = element.text
            elif element.tag == 'language':
                sublocation = "language in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert element.text
                self.language = element.text
            elif element.tag == 'coverage':
                sublocation = "coverage in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.coverage = element.text
            elif element.tag == 'rights':
                sublocation = "rights in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.rights = element.text
            else: logging.error( "Found unexpected {!r} tag in {}".format( element.tag, location ) )
    # end of ZefaniaXMLBible.__validateAndExtractHeader


    def __validateAndExtractBook( self, book ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML book…") )

        # Process the div attributes first
        BBB = bookName = bookShortName = bookNumber = None
        for attrib,value in book.items():
            if attrib=="bnumber":
                bookNumber = value
            elif attrib=="bname":
                bookName = value
            elif attrib=="bsname":
                bookShortName = value
            else: logging.error( "Unprocessed {!r} attribute ({}) in book element".format( attrib, value ) )
        if bookNumber:
            try: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber )
            except (KeyError, ValueError):
                logging.critical( "Unable to deduce which book is number={}, name={}, shortName={} -- ignoring it" \
                                                                        .format( bookNumber, bookName, bookShortName ) )
        if BBB is None and bookName:
            BBB = self.genericBOS.getBBBFromText( bookName )

        if BBB:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Validating {} {}…").format( BBB, bookName ) )
            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'Zefania XML Bible Book object'
            thisBook.objectTypeString = 'Zefania'
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == ZefaniaXMLBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'j3jd' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "Expected to find {!r} but got {!r}".format( ZefaniaXMLBible.chapterTag, element.tag ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {} into results…".format( BBB ) )
            self.stashBook( thisBook )
    # end of ZefaniaXMLBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML chapter…") )

        # Process the chapter attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="cnumber":
                chapterNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #print( BBB, 'c', chapterNumber )
            thisBook.addLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for {}".format( BBB ) )

        for element in chapter:
            if element.tag == ZefaniaXMLBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            elif element.tag == ZefaniaXMLBible.captionTag: # Used in Psalms
                location = "caption in {} {}".format( BBB, chapterNumber )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'k5k8' )
                # TODO: Seems we can have xref subelements here !!!
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'd3f5' )
                # Handle caption attributes
                vRef = None
                for attrib,value in element.items():
                    if attrib == 'vref':
                        vRef = value
                        if vRef != '1':
                            logging.error( "Expected to find vRef of '1' but got {!r}".format( vRef ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in caption element".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert vRef
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, vRef ) )
                if vText: # This is the main text of the caption
                    #print( "{} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                    if '\n' in vText:
                        logging.warning( "ZefaniaXMLBible.__validateAndExtractChapter: newline in vText {} {} {!r}".format( BBB, chapterNumber, vText ) )
                        vText = vText.replace( '\n', ' ' )
                    thisBook.addLine( 'v', '0' + ' ' + vText ) # We save it as verse zero
            else: logging.error( "Expected to find {!r} but got {!r}".format( ZefaniaXMLBible.verseTag, element.tag ) )
    # end of ZefaniaXMLBible.__validateAndExtractChapter


    def __validateAndExtractVerse( self, BBB, chapterNumber, thisBook, verse ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML verse…") )

        location = "verse in {} {}".format( BBB, chapterNumber )
        BibleOrgSysGlobals.checkXMLNoTail( verse, location, 'l5ks' )

        # Handle verse attributes
        verseNumber = toVerseNumber = None
        for attrib,value in verse.items():
            if attrib == 'vnumber':
                verseNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in verse element".format( attrib, value ) )
        if BibleOrgSysGlobals.debugFlag: assert verseNumber
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.addLine( 'v', verseNumber )
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
                    if attrib == 'type':
                        noteType = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if noteType not in ('n-studynote','x-studynote',):
                    logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                if BibleOrgSysGlobals.debugFlag: assert noteType
                nText, nTail = subelement.text, subelement.tail
                #print( "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                #thisBook.addLine( 'ST', css ) # XXXXXXXXXXXXXXXXXXXXXXXXXX Losing data here (for now)
                #thisBook.addLine( 'ST=', nText )
                if nTail:
                    if '\n' in nTail:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                            print( "ZefaniaXMLBible.__validateAndExtractVerse: nTail {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, nTail ) )
                        nTail = nTail.replace( '\n', ' ' )
                    thisBook.addLine( 'v~', nTail )
                for sub2element in subelement:
                    if sub2element.tag == ZefaniaXMLBible.styleTag:
                        sub2location = "style in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'fyt4' )
                        css = idStyle = None
                        for attrib,value in sub2element.items():
                            if attrib == 'css':
                                css = value
                            elif attrib == 'id':
                                idStyle = value
                            else: logging.warning( "Unprocessed {!r} attribute ({}) in style sub2element".format( attrib, value ) )
                        if BibleOrgSysGlobals.debugFlag: assert css or idStyle
                        SFM = None
                        if css=='font-style:italic' or css=='font-style:italic;': SFM = '\\it'
                        elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        elif css == "color:#FF0000": SFM = '\\em'
                        elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        else:
                            logging.error( "Ignored1 css is {!r} idStyle is {!r}".format( css, idStyle ) )
                            if BibleOrgSysGlobals.debugFlag: halt
                        sText, sTail = sub2element.text.strip(), sub2element.tail
                        if BibleOrgSysGlobals.debugFlag: assert sText
                        if SFM: vText += SFM+' ' + sText + SFM+'*'
                        else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        if sTail: vText += sTail.strip()
                    else: logging.error( "Expected to find {} but got {!r} in {}".format( ZefaniaXMLBible.styleTag, sub2element.tag, sublocation ) )

            elif subelement.tag == ZefaniaXMLBible.styleTag:
                sublocation = "style in " + location
                css = idStyle = None
                for attrib,value in subelement.items():
                    if attrib == 'css':
                        css = value
                    elif attrib == 'id':
                        idStyle = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert css or idStyle
                SFM = None
                if css=='font-style:italic' or css=='font-style:italic;': SFM = '\\it'
                elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                elif css == "color:#FF0000": SFM = '\\em'
                elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                else:
                    logging.error( "Ignored2 css is {!r} idStyle is {!r}".format( css, idStyle ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                for sub2element in subelement:
                    if sub2element.tag == ZefaniaXMLBible.grTag:
                        sub2location = "gr in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location, 'ks12' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'dl36' )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, 'js24' )
                        grText = sub2element.text.strip() if sub2element.text else ''
                        logging.error( "Unfinished to process 'gr' {!r} sub2element ({}) in style subelement".format( grText, sublocation ) )
                    else: logging.error( "Expected to find 'gr' but got {!r} in {}".format( sub2element.tag, sublocation ) )

                #sText, sTail = subelement.text.strip(), subelement.tail
                sText = subelement.text.strip() if subelement.text else ''
                sTail = subelement.tail.strip() if subelement.tail else None
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert sText
                if SFM: vText += SFM+' ' + sText + SFM+'*'
                else: vText += '\\sc ' + '['+(css if css else '')+']' + sText + '\\sc* ' # Use sc for unknown styles
                if sTail: vText += sTail

            elif subelement.tag == ZefaniaXMLBible.breakTag:
                sublocation = "line break in " + location
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                art = None
                for attrib,value in subelement.items():
                    if attrib == 'art':
                        art = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert art == 'x-nl'
                #print( BBB, chapterNumber, verseNumber )
                #assert vText
                if vText:
                    if '\n' in vText:
                        logging.warning( "ZefaniaXMLBible.__validateAndExtractVerse_a: newline in vText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                        vText = vText.replace( '\n', ' ' )
                    thisBook.addLine( 'v', verseNumber + ' ' + vText )
                    vText = ''
                breakText = subelement.tail.strip() if subelement.tail else ''
                if '\n' in breakText:
                    logging.warning( "ZefaniaXMLBible.__validateAndExtractVerse: newline in breakText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, breakText ) )
                    breakText = breakText.replace( '\n', ' ' )
                thisBook.addLine( 'm', breakText )

            elif subelement.tag == ZefaniaXMLBible.divTag:
                sublocation = "div break in " + location
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'ld46' )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'kx10' )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'las9' )
                for sub2element in subelement:
                    if sub2element.tag == 'NOTE':
                        sub2location = "NOTE in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location, 'lc35' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'ks27' )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, 'ksd1' )
                        noteText = sub2element.text.strip() if sub2element.text else ''
                        vText += '\\f {}\\f*'.format( noteText )
                    else: logging.error( "Expected to find 'NOTE' but got {!r} in {}".format( sub2element.tag, sublocation ) )

            elif subelement.tag == ZefaniaXMLBible.grTag:
                sublocation = "gr in " + location
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'ksd2' )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ls10' )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'cg27' )
                grText = subelement.text.strip() if subelement.text else ''
                logging.error( "Unfinished to process 'gr' {!r} subelement ({}) in style subelement".format( grText, location ) )

            else: logging.error( "Expected to find NOTE or STYLE or BREAK or DIV but got {!r} in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            if '\n' in vText:
                logging.warning( "ZefaniaXMLBible.__validateAndExtractVerse_b: newline in vText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                vText = vText.replace( '\n', ' ' )
            thisBook.addLine( 'v', verseNumber + ' ' + vText )
    # end of ZefaniaXMLBible.__validateAndExtractVerse
# end of ZefaniaXMLBible class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( programNameVersionDate if BibleOrgSysGlobals.verbosityLevel > 1 else programNameVersion )
        if __name__ == '__main__' and BibleOrgSysGlobals.verbosityLevel > 1:
            latestPythonModificationDate = BibleOrgSysGlobals.getLatestPythonModificationDate()
            if latestPythonModificationDate != LAST_MODIFIED_DATE:
                print( f"  (Last BibleOrgSys code update was {latestPythonModificationDate})" )

    if 1: # demo the file checking code
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' )
        #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/Zefania modules/' )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Z TestA1", ZefaniaXMLBibleFileCheck( testFolder ) )
            print( "Z TestA2", ZefaniaXMLBibleFileCheck( testFolder, autoLoad=True ) )
            print( "Z TestA3", ZefaniaXMLBibleFileCheck( testFolder, autoLoadBooks=True ) )

    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # demo the file checking code
        testFolder = BiblesFolderpath.joinpath( 'Zefania modules/' )
        #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/Zefania modules/' )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Z TestB1", ZefaniaXMLBibleFileCheck( testFolder ) )
            print( "Z TestB2", ZefaniaXMLBibleFileCheck( testFolder, autoLoad=True ) )
            print( "Z TestB3", ZefaniaXMLBibleFileCheck( testFolder, autoLoadBooks=True ) )

    if 1:
        testFolder = BiblesFolderpath.joinpath( 'Zefania modules/' )
        #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ZefaniaTest/' )
        single = ( "kjv.xml", )
        good = ( "BWE_zefania.xml", "en_gb_KJV2000.xml", "Etheridge_zefania.xml", "kjv.xml", "OEB_zefania.xml", \
            'sf_elb_1871_original_NT_rev1.xml', 'sf_wycliffe.xml', 'ylt.xml')
        nonEnglish = ( "italian.xml", )
        bad = (  )
        allOfThem = good + nonEnglish + bad

        for j, testFilename in enumerate( allOfThem ): # Choose one of the above lists for testing
            testFilepath = os.path.join( testFolder, testFilename )

            # Demonstrate the XML Bible class
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nZ C{}/ Demonstrating the Zefania Bible class…".format( j+1 ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test filepath is {!r}".format( testFilepath ) )
            zb = ZefaniaXMLBible( testFolder, testFilename )
            zb.load() # Load and process the XML
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( zb ) # Just print a summary
            #print( zb.books['JDE']._processedLines )
            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
                for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                    (t, b, c, v) = reference
                    if t=='OT' and len(zb)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(zb)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(zb)<=66: continue # Don't bother with DC references if it's too small
                    svk = VerseReferences.SimpleVerseKey( b, c, v )
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        #print( svk, ob.getVerseDataList( reference ) )
                        try: print( reference, svk.getShortText(), zb.getVerseText( svk ) )
                        except KeyError: print( testFilename, reference, "doesn't exist" )

    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1:
        testFolder = BiblesFolderpath.joinpath( 'Zefania modules/' )
        fileList = []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if something.endswith( '.xml') and os.path.isfile( somepath ):
                fileList.append( something )

        for j, testFilename in enumerate( fileList ):
            testFilepath = os.path.join( testFolder, testFilename )

            # Demonstrate the XML Bible class
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nZ D{}/ Demonstrating the Zefania Bible class…".format( j+1 ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test filepath is {!r}".format( testFilepath ) )
            zb = ZefaniaXMLBible( testFolder, testFilename )
            zb.load() # Load and process the XML
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( zb ) # Just print a summary
                #print( zb.books['JDE']._processedLines )
            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
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
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ZefaniaXMLBible.py
