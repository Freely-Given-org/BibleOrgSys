#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HaggaiXMLBible.py
#
# Module handling Haggai XML Bibles
#
# Copyright (C) 2013-2019 Robert Hunt
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
Module reading and loading Haggai XML Bibles:
    <?xml version="1.0" encoding="utf-8"?>
    <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="haggai_20130620.xsd" biblename="Elberfelder 1871" status="v" version="haggai_3.0.0.9.1" revision="0">
    <INFORMATION>
        <title>Elberfelder 1871</title>
        <creator>Stephan Kreutzer, Michael Ott, Michael Mustun, Markus Oehler, Thomas Laidler, Wolfgang Schultz, Hans Jürgen Herbst, Claas-Fridtjof Lisowski</creator>
        <description>Elberfelder-Bibel von 1871</description>
        <publisher>http://www.freie-bibel.de</publisher>
        <contributor>John Nelson Darby</contributor>
        <contributor>Julius Anton Eugen von Poseck</contributor>
        <contributor>Carl Friedrich Wilhelm Brockhaus</contributor>
        <contributor>Hermanus Cornelis Voorhoeve</contributor>
        <date>2013-08-03</date>
        <type>Text</type>
        <format>Haggai XML Bible Markup Language</format>
        <identifier>elberfelder_1871</identifier>
        <source>Elberfelder 1871, 3. durchgesehene Ausgabe NT</source>
        <language>de-DE</language>
        <coverage>Matthäus, Johannes 1, Apostelgeschichte 1-2, Hebräer, Jakobus</coverage>
        <rights>
        Gemeinfrei seit 1972-01-01.
        </rights>
    </INFORMATION>
    <BIBLEBOOK bnumber="40" bname="Matthäus">
        <CAPTION>Evangelium nach Matthäus.</CAPTION>
        <CHAPTER cnumber="1">
        <PARAGRAPH>
            <VERSE vnumber="1">Das Buch des Geschlechtes Jesu Christi, Sohnes Davids, Sohnes Abrahams.</VERSE>
        </PARAGRAPH>
        <PARAGRAPH>
            <VERSE vnumber="2">Abraham zeugte Isaak, Isaak aber zeugte Jakob, Jakob aber zeugte Juda und seine Brüder,</VERSE>
            <VERSE vnumber="3">Juda aber zeugte Phares und Zarah von der Thamar, Phares aber zeugte Hezron, Hezron aber zeugte Aram,</VERSE>
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "HaggaiBible"
PROGRAM_NAME = "Haggai XML Bible format handler"
PROGRAM_VERSION = '0.33'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, sys
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
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



def HaggaiXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Haggai XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one Haggai Bible is found,
        returns the loaded HaggaiXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "HaggaiXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("HaggaiXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("HaggaiXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " HaggaiXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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

    # See if there's an Haggai project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=2 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "HB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if 'haggai_' not in firstLines[1]: continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "HaggaiXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = HaggaiXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    HaggaiXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "HB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if 'haggai_' not in firstLines[1]: continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "HaggaiXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = HaggaiXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of HaggaiXMLBibleFileCheck



class HaggaiXMLBible( Bible ):
    """
    Class for reading, validating, and converting HaggaiXMLBible XML.
    """
    XMLNameSpace = "{http://www.w3.org/2001/XMLSchema-instance}"
    treeTag = 'XMLBIBLE'
    infoTag = 'INFORMATION'
    bookTag = 'BIBLEBOOK'
    chapterTag = 'CHAPTER'
    captionTag = 'CAPTION'
    paragraphTag = 'PARAGRAPH'
    verseTag = 'VERSE'
    noteTag = 'NOTE'
    styleTag = 'STYLE'
    breakTag = 'BR'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the Haggai Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Haggai XML Bible object'
        self.objectTypeString = 'Haggai'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.XMLTree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "HaggaiXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of HaggaiXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        try: self.XMLTree = ElementTree().parse( self.sourceFilepath )
        except ParseError as err:
            logging.critical( "Loader parse error in xml file {}: {} {}".format( self.givenName, sys.exc_info()[0], err ) )
            #loadErrors.append( "Loader parse error in xml file {}: {} {}".format( self.givenName, sys.exc_info()[0], err ) )
            #self.addPriorityError( 100, C, V, _("Loader parse error in xml file {}: {}").format( self.givenName, err ) )
        if BibleOrgSysGlobals.debugFlag: assert self.XMLTree # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.XMLTree.tag == HaggaiXMLBible.treeTag:
            location = "Haggai XML file"
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8' )

            schema = name = status = BibleType = revision = version = lgid = None
            for attrib,value in self.XMLTree.items():
                if attrib == HaggaiXMLBible.XMLNameSpace + 'noNamespaceSchemaLocation':
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
                if element.tag == HaggaiXMLBible.bookTag:
                    sublocation = "book in " + location
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'g3g5' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                else: logging.error( "Expected to find {!r} but got {!r}".format( HaggaiXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( HaggaiXMLBible.treeTag, self.XMLTree.tag ) )
        self.doPostLoadProcessing()
    # end of HaggaiXMLBible.load


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
            <format>Haggai XML Bible Markup Language</format>
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
                if BibleOrgSysGlobals.debugFlag: assert element.text
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
                if BibleOrgSysGlobals.debugFlag: assert element.text
                self.description = element.text
            elif element.tag == 'publisher':
                sublocation = "publisher in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if element.text: self.publisher = element.text
            elif element.tag == 'contributor':
                sublocation = "contributor in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'alj1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jjd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5gk78' )
                if element.text:
                    try: self.contributor = [ self.contributor, element.text ] # Put multiples into a list
                    except AttributeError: self.contributor = element.text # Must be the first (and possibly only) one
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
                if BibleOrgSysGlobals.debugFlag: assert element.text
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
                if BibleOrgSysGlobals.debugFlag: assert element.text
                if BibleOrgSysGlobals.debugFlag: assert element.text == 'Haggai XML Bible Markup Language'
            elif element.tag == 'identifier':
                sublocation = "identifier in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag: assert element.text
                self.identifier = element.text
            elif element.tag == 'source':
                sublocation = "source in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag: assert element.text
                self.source = element.text
            elif element.tag == 'language':
                sublocation = "language in {}".format( location )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'j3jd' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '5g78' )
                if BibleOrgSysGlobals.debugFlag: assert element.text
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
    # end of HaggaiXMLBible.__validateAndExtractHeader


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
            else: logging.warning( "Unprocessed {!r} attribute ({}) in book element".format( attrib, value ) )
        if bookNumber:
            try: BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber )
            except KeyError:
                logging.warning( "Unable to deduce which book is number={}, name={}, shortName={} -- ignoring it" \
                                                                        .format( bookNumber, bookName, bookShortName ) )
        elif bookName:
            BBB = self.genericBOS.getBBBFromText( bookName )

        if BBB:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Validating {} {}…").format( BBB, bookName ) )
            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'Haggai XML Bible Book object'
            thisBook.objectTypeString = 'Haggai'
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == HaggaiXMLBible.captionTag:
                    sublocation = "caption in {}".format( BBB )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jhl6' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'jk21' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'kjh6' )
                    thisBook.addLine( 'mt', element.text )
                elif element.tag == HaggaiXMLBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'j3jd' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "Expected to find {!r} but got {!r}".format( HaggaiXMLBible.chapterTag, element.tag ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {} into results…".format( BBB ) )
            self.stashBook( thisBook )
    # end of HaggaiXMLBible.__validateAndExtractBook


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
            if element.tag == HaggaiXMLBible.paragraphTag:
                location = "paragraph in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractParagraph( BBB, chapterNumber, thisBook, element )
            elif element.tag == HaggaiXMLBible.verseTag+'disabled':
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            elif element.tag == HaggaiXMLBible.captionTag+'disabled': # Used in Psalms
                location = "caption in {} {}".format( BBB, chapterNumber )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'k5k8' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'd3f5' )
                # Handle caption attributes
                vRef = None
                for attrib,value in element.items():
                    if attrib=="vref":
                        vRef = value
                        if BibleOrgSysGlobals.debugFlag: assert vRef == '1'
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in caption element".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert vRef
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, vRef ) )
                if vText: # This is the main text of the caption
                    #print( "{} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                    thisBook.addLine( 'v', '0' + ' ' + vText ) # We save it as verse zero
            else: logging.error( "Expected to find {!r} but got {!r}".format( HaggaiXMLBible.verseTag, element.tag ) )
    # end of HaggaiXMLBible.__validateAndExtractChapter


    def __validateAndExtractParagraph( self, BBB, chapterNumber, thisBook, paragraph ):
        """
        Check/validate and extract paragraph data from the given XML book record
            finding and saving paragraphs and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML paragraph…") )

        location = "paragraph in {} {}".format( BBB, chapterNumber )
        BibleOrgSysGlobals.checkXMLNoAttributes( paragraph, location, 'brgw3' )
        BibleOrgSysGlobals.checkXMLNoText( paragraph, location, 'brgw3' )
        BibleOrgSysGlobals.checkXMLNoTail( paragraph, location, 'brgw3' )
        thisBook.addLine( 'p', '' )

        # Handle verse subelements (verses)
        for element in paragraph:
            if element.tag == HaggaiXMLBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            elif element.tag == HaggaiXMLBible.captionTag+'disabled': # Used in Psalms
                location = "caption in {} {}".format( BBB, chapterNumber )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'k5k8' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'd3f5' )
                # Handle caption attributes
                vRef = None
                for attrib,value in element.items():
                    if attrib=="vref":
                        vRef = value
                        if BibleOrgSysGlobals.debugFlag: assert vRef == '1'
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in caption element".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert vRef
                vText = element.text
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, vRef ) )
                if vText: # This is the main text of the caption
                    #print( "{} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                    thisBook.addLine( 'v', '0' + ' ' + vText ) # We save it as verse zero
            else: logging.error( "Expected to find {!r} but got {!r}".format( HaggaiXMLBible.verseTag, element.tag ) )
    # end of HaggaiXMLBible.__validateAndExtractParagraph


    def __validateAndExtractVerse( self, BBB, chapterNumber, thisBook, verse ):
        """
        Check/validate and extract verse data from the given XML book record
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML verse…") )

        location = "verse in {} {}".format( BBB, chapterNumber )
        BibleOrgSysGlobals.checkXMLNoTail( verse, location, 'l5ks' )

        # Handle verse attributes
        verseNumber = toVerseNumber = None
        for attrib,value in verse.items():
            if attrib=="vnumber":
                verseNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in verse element".format( attrib, value ) )
        if BibleOrgSysGlobals.debugFlag: assert verseNumber
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.addLine( 'v', verseNumber )
        vText = '' if verse.text is None else verse.text
        if vText: vText = vText.strip()
        #if not vText: # This happens if a verse starts immediately with a style or note
            #logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )

        # Handle verse subelements (notes and styled portions)
        for subelement in verse:
            if subelement.tag == HaggaiXMLBible.noteTag:
                sublocation = "note in " + location
                noteType = None
                for attrib,value in subelement.items():
                    if attrib=="type": noteType = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if noteType and noteType not in ('variant',):
                    logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                nText, nTail = subelement.text, subelement.tail
                #print( "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                vText += "\\f + \\fk {} \\ft {}\\f*".format( noteType, nText ) if noteType else "\\f + \\ft {}\\f*".format( nText )
                if nTail:
                    if '\n' in nTail:
                        print( "HaggaiXMLBible.__validateAndExtractVerse: nTail {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, nTail ) )
                        nTail = nTail.replace( '\n', ' ' )
                    vText += nTail
                for sub2element in subelement:
                    if sub2element.tag == HaggaiXMLBible.styleTag:
                        sub2location = "style in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'fyt4' )
                        fs = css = idStyle = None
                        for attrib,value in sub2element.items():
                            if attrib=='fs': fs = value
                            #elif attrib=="css": css = value
                            #elif attrib=="id": idStyle = value
                            else: logging.warning( "Unprocessed {!r} attribute ({}) in style sub2element".format( attrib, value ) )
                        if BibleOrgSysGlobals.debugFlag: assert fs or css or idStyle
                        SFM = None
                        if fs == 'italic': SFM = '\\it'
                        elif fs == 'super': SFM = '\\bdit'
                        elif fs == 'emphasis': SFM = '\\em'
                        else: print( "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                        #if css == "font-style:italic": SFM = '\\it'
                        #elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        #elif css == "color:#FF0000": SFM = '\\em'
                        #elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        #elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        #else: print( "css is", css, "idStyle is", idStyle ); halt
                        sText, sTail = sub2element.text.strip(), sub2element.tail
                        if BibleOrgSysGlobals.debugFlag: assert sText
                        if SFM: vText += SFM+' ' + sText + SFM+'*'
                        else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        if sTail: vText += sTail.strip()
                    else: logging.error( "Expected to find {} but got {!r} in {}".format( HaggaiXMLBible.styleTag, sub2element.tag, sublocation ) )

            elif subelement.tag == HaggaiXMLBible.styleTag:
                sublocation = "style in " + location
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'f5gh' )
                fs = css = idStyle = None
                for attrib,value in subelement.items():
                    if attrib=="fs": fs = value
                    #elif attrib=="css": css = value
                    #elif attrib=="id": idStyle = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert fs
                SFM = None
                if fs == 'super': SFM = '\\bdit'
                elif fs == 'emphasis': SFM = '\\em'
                else: print( "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                #if css == "font-style:italic": SFM = '\\it'
                #elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                #elif css == "color:#FF0000": SFM = '\\em'
                #elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                #elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                #else: print( "css is", css, "idStyle is", idStyle ); halt
                sText, sTail = subelement.text.strip(), subelement.tail
                if BibleOrgSysGlobals.debugFlag: assert sText
                #print( BBB, chapterNumber, sublocation )
                if SFM: vText += SFM+' ' + sText + SFM+'*'
                else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                if sTail: vText += sTail.strip()

            elif subelement.tag == HaggaiXMLBible.breakTag:
                sublocation = "line break in " + location
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                art = None
                for attrib,value in subelement.items():
                    if attrib=="art":
                        art = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert art == 'x-nl'
                #print( BBB, chapterNumber, verseNumber )
                #assert vText
                if vText:
                    thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
                    vText = ''
                thisBook.addLine( 'm', subelement.tail.strip() if subelement.tail else '' )
                #bTail = subelement.tail
                #if bTail: vText = bTail.strip()
            else: logging.error( "Expected to find NOTE or STYLE but got {!r} in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            if '\n' in vText:
                print( "HaggaiXMLBible.__validateAndExtractVerse: vText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                vText = vText.replace( '\n', ' ' )
            thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
    # end of HaggaiXMLBible.__validateAndExtractVerse
# end of HaggaiXMLBible class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if 1: # demo the file checking code
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'HaggaiTest/' )
        print( "TestA1", HaggaiXMLBibleFileCheck( testFolder ) )
        print( "TestA2", HaggaiXMLBibleFileCheck( testFolder, autoLoad=True ) )
        print( "TestA3", HaggaiXMLBibleFileCheck( testFolder, autoLoadBooks=True ) )


    if 1:
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'HaggaiTest/' )
        count = totalBooks = 0
        if os.access( testFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isfile( somepath ) and something.endswith( '.xml' ):
                    count += 1
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nH B{}/ {}".format( count, something ) )
                    hB = HaggaiXMLBible( testFolder, something )
                    hB.load()
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( hB )
                    if BibleOrgSysGlobals.strictCheckingFlag:
                        hB.check()
                        #UBErrors = UB.getErrors()
                        # print( UBErrors )
                    #print( UB.getVersification() )
                    #print( UB.getAddedUnits() )
                    #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                        ##print( "Looking for", ref )
                        #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
                    if 1: # Test verse lookup
                        from BibleOrgSys.Reference import VerseReferences
                        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                            ('OT','DAN','1','21'),
                                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                            (t, b, c, v) = reference
                            if t=='OT' and len(hB)==27: continue # Don't bother with OT references if it's only a NT
                            if t=='NT' and len(hB)==39: continue # Don't bother with NT references if it's only a OT
                            if t=='DC' and len(hB)<=66: continue # Don't bother with DC references if it's too small
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #print( svk, ob.getVerseDataList( reference ) )
                            try: print( reference, svk.getShortText(), hB.getVerseText( svk ) )
                            except KeyError: print( something, reference, "doesn't exist" )
                    if BibleOrgSysGlobals.commandLineArguments.export:
                        hB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else:
                        hB.toHaggaiXML()
                else: print( "Sorry, skipping {}.".format( something ) )
            if count: print( "\n{} total Haggai Bibles processed.".format( count ) )
        else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of HaggaiXMLBible.py
