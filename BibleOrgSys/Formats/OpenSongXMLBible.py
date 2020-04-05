#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# OpenSongXMLBible.py
#
# Module handling OpenSong XML Bibles
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
Module reading and loading OpenSong XML Bibles.

Details of the XML file format can be found at
    http://www.opensong.org/home/file-formats

As of Jan 2018 it said:
    Bible File Format Specification
        As of OpenSong v1.6.2
        Copyright 2003-2010 Sean Lickfold.
        Released under the terms of the GPL.

    File Structure
        OpenSong Scripture files are standard XML files with the following layout:
            <?xml version="1.0" encoding="[W3C encoding code]"?>
            <bible>
            <b n="[book name]">
                <c n="#">
                <v n="#"></v>
                </c>
            </b>
            </bible>

    Notes
        Encoding
            Any W3C encoding can be used. Generally western languages use ISO-8859-1. The best option, however, is to use UTF-8 encoding, to preserve any special characters.
            Book Name

            Book names are the full-length name (e.g. “Genesis”) They can be in the language that the Scripture file is saved in (e.g. in German Genesis would be “1. Mose”). Whatever the book names are is how they will be displayed in the index of the Scripture Lookup dialog.
            Chapter and Verse Numbers

            The ”#” sign refers to the chapter and verse number of a given book chapter and verse.


Sample:
    <?xml version="1.0" encoding="ISO-8859-1"?>
    <bible>
    <b n="Genesis">
    <c n="1">
    <v n="1">In the beginning God created the heaven and the earth.</v>
    <v n="2">And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.</v>
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "OpenSongBible"
PROGRAM_NAME = "OpenSong XML Bible format handler"
PROGRAM_VERSION = '0.39'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, zipfile
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Reference.BibleBooksNames import BibleBooksNamesSystems
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, \
                            USFM_PRECHAPTER_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS
from BibleOrgSys.InputOutput.MLWriter import MLWriter


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot
BibleBooksNames = None



def OpenSongXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for OpenSong XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OpenSong Bible is found,
        returns the loaded OpenSongXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)
    if BibleOrgSysGlobals.debugFlag: assert autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("OpenSongXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("OpenSongXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " OpenSongXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    #print( 'osx1', foundFiles )

    # See if there's an OpenSong project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=2 )
            #print( 'osx1b', firstLines )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "OSB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if not firstLines[1].startswith( '<bible>' ):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            osb = OpenSongXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: osb.load() # Load and process the file
            return osb
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    OpenSongXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
        #print( 'osx2', foundSubfiles )

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "OSB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<bible>' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OpenSongXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            osb = OpenSongXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: osb.load() # Load and process the file
            return osb
        return numFound
# end of OpenSongXMLBibleFileCheck



def createOpenSongXML( BibleObject, outputFolder=None, controlDict=None, validationSchema=None ):
    """
    Using settings from the given control file,
        converts the USFM information to a UTF-8 OpenSong XML file.

    This format is roughly documented at http://de.wikipedia.org/wiki/OpenSong_XML
        but more fields can be discovered by looking at downloaded files.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running createOpenSongXML…" )
    if BibleOrgSysGlobals.debugFlag: assert BibleObject.books

    ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

    def writeOpenSongBook( writerObject, BBB, bkData ):
        """Writes a book to the OpenSong XML writerObject."""
        #print( 'BIBLEBOOK', [('bnumber',BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(BBB)), ('bname',BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation(BBB))] )
        OSISAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
        if not OSISAbbrev:
            logging.warning( "toOpenSong: Can't write {} OpenSong book because no OSIS code available".format( BBB ) )
            unhandledBooks.append( BBB )
            return
        writerObject.writeLineOpen( 'b', ('n',bkData.getAssumedBookNames()[0]) )
        haveOpenChapter, startedFlag, gotVP, accumulator = False, False, None, ""
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
            marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getCleanText(), processedBibleEntry.getExtras()
            #print( marker, repr(text) )
            #if text: assert text[0] != ' '
            if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            if marker in USFM_PRECHAPTER_MARKERS:
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    assert C=='-1' or marker=='rem' or marker.startswith('mte')
                V = str( int(V) + 1 )

            if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                ignoredMarkers.add( marker )
            elif marker == 'c':
                if accumulator:
                    writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
                    accumulator = ''
                if haveOpenChapter:
                    writerObject.writeLineClose ( 'c' )
                C, V = text, '0'
                writerObject.writeLineOpen ( 'c', ('n',text) )
                haveOpenChapter = True
            elif marker in ('c#',): # These are the markers that we can safely ignore for this export
                ignoredMarkers.add( marker )
            elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                gotVP = text # Just remember it for now
            elif marker == 'v':
                V = text
                if gotVP: # this is the verse number to be published
                    text = gotVP
                    gotVP = None
                startedFlag = True
                if accumulator:
                    writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
                    accumulator = ''
                #print( "Text {!r}".format( text ) )
                if not text: logging.warning( "createOpenSongXML: Missing text for v" ); continue
                verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later

            elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4', 'ms1','ms2','ms3','ms4', ) \
            or marker in USFM_ALL_INTRODUCTION_MARKERS \
            or marker in ('s1','s2','s3','s4', 'r','sr','mr', 'd','sp','cd', 'cl','lit', ):
                ignoredMarkers.add( marker )
            elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                if BibleOrgSysGlobals.debugFlag: assert not text and not extras
                ignoredMarkers.add( marker )
            elif marker in ('b', 'nb', 'ib', ):
                if BibleOrgSysGlobals.debugFlag: assert not text and not extras
                ignoredMarkers.add( marker )
            elif marker in ('v~', 'p~',):
                if BibleOrgSysGlobals.debugFlag: assert text or extras
                if not text: # this is an empty (untranslated) verse
                    text = '- - -' # but we'll put in a filler
                if startedFlag: accumulator += (' ' if accumulator else '') + BibleOrgSysGlobals.makeSafeXML( text )
            else:
                if text:
                    logging.warning( "toOpenSong: lost text in {} field in {} {}:{} {!r}".format( marker, BBB, C, V, text ) )
                    #if BibleOrgSysGlobals.debugFlag: halt
                if extras:
                    logging.warning( "toOpenSong: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                    #if BibleOrgSysGlobals.debugFlag: halt
                unhandledMarkers.add( marker )
            if extras and marker not in ('v~','p~',) and marker not in ignoredMarkers:
                logging.critical( "toOpenSong: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
        if accumulator:
            writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
        if haveOpenChapter:
            writerObject.writeLineClose ( 'c' )
        writerObject.writeLineClose( 'b' )
    # end of createOpenSongXML.writeOpenSongBook

    # Set-up our Bible reference system
    if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
        BOS = BibleObject.genericBOS
        BRL = BibleObject.genericBRL
    else:
        BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
        BRL = BibleReferenceList( BOS, BibleObject=None )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to OpenSong format…") )
    try: osOFn = controlDict['OpenSongOutputFilename']
    except KeyError: osOFn = 'Bible.osong'
    filename = BibleOrgSysGlobals.makeSafeFilename( osOFn )
    xw = MLWriter( filename, outputFolder )
    xw.setHumanReadable()
    xw.start()
    xw.writeLineOpen( 'Bible' )
    for BBB,bookData in BibleObject.books.items():
        writeOpenSongBook( xw, BBB, bookData )
    xw.writeLineClose( 'Bible' )
    xw.close()

    if ignoredMarkers:
        logging.info( "createOpenSongXML: Ignored markers were {}".format( ignoredMarkers ) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  " + _("WARNING: Ignored createOpenSongXML markers were {}").format( ignoredMarkers ) )
    if unhandledMarkers:
        logging.warning( "createOpenSongXML: Unhandled markers were {}".format( unhandledMarkers ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toOpenSong markers were {}").format( unhandledMarkers ) )
    if unhandledBooks:
        logging.warning( "createOpenSongXML: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled createOpenSongXML books were {}").format( unhandledBooks ) )

    # Now create a zipped version
    filepath = os.path.join( outputFolder, filename )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} OpenSong file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if validationSchema: return xw.validate( validationSchema )
    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  createOpenSongXML finished successfully." )
    return True
# end of createOpenSongXML



class OpenSongXMLBible( Bible ):
    """
    Class for reading, validating, and converting OpenSong Bible XML.
    """
    treeTag = 'bible'
    bookTag = 'b'
    chapterTag = 'c'
    verseTag = 'v'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the XML Bible file converter object.
        """
        # Setup and initialise the base class first
        if BibleOrgSysGlobals.debugFlag: print( "OpenSongXMLBible( {}, {}, {} )".format( sourceFolder, givenName, encoding ) )
        Bible.__init__( self )
        self.objectNameString = 'OpenSong XML Bible object'
        self.objectTypeString = 'OpenSong'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.XMLTree = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "OpenSongXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of OpenSongXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        self.XMLTree = ElementTree().parse( self.sourceFilepath )
        if BibleOrgSysGlobals.debugFlag: assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main (bible) container
        if self.XMLTree.tag == OpenSongXMLBible.treeTag:
            location = "XML file"
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8' )

            name = shortName = None
            for attrib,value in self.XMLTree.items():
                if attrib=="n":
                    name = value
                elif attrib=="sn":
                    shortName = value
                else: logging.warning( "Unprocessed {!r} attribute ({}) in main element".format( attrib, value ) )

            # Find the submain (book) containers
            for element in self.XMLTree:
                if element.tag == OpenSongXMLBible.bookTag:
                    sublocation = "book in " + location
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'g3g5' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    self.__validateAndExtractBook( element )
                elif element.tag == 'OT':
                    pass
                elif element.tag == 'NT':
                    pass
                else: logging.error( "Expected to find {!r} but got {!r}".format( OpenSongXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( OpenSongXMLBible.treeTag, self.XMLTree.tag ) )
        self.doPostLoadProcessing()
    # end of OpenSongXMLBible.load


    def __validateAndExtractBook( self, book ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """
        global BibleBooksNames

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating OpenSong XML book…") )

        # Process the div attributes first
        BBB = bookName = None
        for attrib,value in book.items():
            if attrib=="n":
                bookName = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in book element".format( attrib, value ) )
        if bookName:
            BBB = self.genericBOS.getBBBFromText( bookName ) # Booknames are usually in English
            if not BBB: # wasn't English
                if BibleBooksNames is None:
                    BibleBooksNames = BibleBooksNamesSystems().loadData()
                BBB = BibleBooksNames.getBBBFromText( bookName ) # Try non-English booknames
                #print( "bookName", bookName, BBB )
            if BBB:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Validating {} {}…").format( BBB, bookName ) )
                thisBook = BibleBook( self, BBB )
                thisBook.objectNameString = 'OpenSong XML Bible Book object'
                thisBook.objectTypeString = 'OpenSong'
                #thisBook.sourceFilepath = self.sourceFilepath
                USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                thisBook.addLine( 'id', '{} imported by {}'.format( USFMAbbreviation.upper(), programNameVersion ) )
                thisBook.addLine( 'h', bookName )
                thisBook.addLine( 'mt1', bookName )
                for element in book:
                    if element.tag == OpenSongXMLBible.chapterTag:
                        sublocation = "chapter in {}".format( BBB )
                        BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'j3jd' )
                        BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                        self.__validateAndExtractChapter( BBB, thisBook, element )
                    else: logging.error( "Expected to find {!r} but got {!r}".format( OpenSongXMLBible.chapterTag, element.tag ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {} into results…".format( BBB ) )
                self.stashBook( thisBook )
            else: logging.error( _("OpenSong load doesn't recognize book name: {!r}").format( bookName ) ) # no BBB
        else: logging.error( _("OpenSong load can't find a book name") ) # no bookName
    # end of OpenSongXMLBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML chapter…") )

        # Process the div attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="n":
                chapterNumber = value
            elif attrib=="VERSES":
                numVerses = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #print( BBB, 'c', chapterNumber )
            chapterNumber = chapterNumber.replace( 'of Solomon ', '' ) # Fix a mistake in the Chinese_SU module
            thisBook.addLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for {}".format( BBB ) )

        for element in chapter:
            if element.tag == OpenSongXMLBible.verseTag:
                sublocation = "verse in {} {}".format( BBB, chapterNumber )
                BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'l5ks' )
                verseNumber = toVerseNumber = None
                for attrib,value in element.items():
                    if attrib=="n":
                        verseNumber = value
                    elif attrib=="t":
                        toVerseNumber = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in verse element".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert verseNumber
                #thisBook.addLine( 'v', verseNumber )
                vText = element.text if element.text else ''
                for subelement in element:
                    sub2location = "{} in {}".format( subelement.tag, sublocation )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sub2location, 'ks03' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sub2location, 'ks05' )
                    if subelement.tag == 'i':
                        vText += '\\it {}\\it*{}'.format( subelement.text, subelement.tail )
                    else: logging.error( "Expected to find 'i' but got {!r}".format( subelement.tag ) )
                vText += element.tail if element.tail else ''
                if not vText:
                    logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )
                #print( 'vText1', vText )
                if vText: # This is the main text of the verse (follows the verse milestone)
                    #print( "{} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                    if '\n' in vText: # This is how they represent poety
                        #print( "vText", repr(vText), repr(element.text) )
                        for j, textBit in enumerate( vText.split( '\n' ) ):
                            if j==0:
                                thisBook.addLine( 'q1', '' )
                                thisBook.addLine( 'v', verseNumber + ' ' + textBit )
                            else: thisBook.addLine( 'q1', textBit )
                    else: # Just one verse line
                        thisBook.addLine( 'v', verseNumber + ' ' + vText )
                #print( 'vText2', vText )
            else: logging.error( "Expected to find {!r} but got {!r}".format( OpenSongXMLBible.verseTag, element.tag ) )
    # end of OpenSongXMLBible.__validateAndExtractChapter
# end of OpenSongXMLBible class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' ) # These are very similar
    testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/OpenSong Bibles/' )
    single1 = ( "KJV.xmm", )
    single2 = ( "BIBLIA warszawska", )
    good = ( "KJV.xmm", "AMP.xmm", "Chinese_SU.xmm", "Contemporary English Version.xmm", "ESV", "MKJV", \
        "MSG.xmm", "NASB.xmm", "NIV", "NKJV.xmm", "NLT", "telugu.xmm", )
    nonEnglish = ( "BIBLIA warszawska", "Chinese Union Version Simplified.txt", "hun_karoli", "KNV_HU", "LBLA.xmm", \
        "Nowe Przymierze", "NVI.xmm", "NVI_PT", "PRT-IBS.xmm", "RV1960", "SVL.xmm", "UJPROT_HU", "vdc", \
        "Vietnamese Bible.xmm", )
    bad = ( "EPS99", )
    allOfThem = good + nonEnglish + bad


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        resultA1 = OpenSongXMLBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA1", resultA1 )
        resultA2 = OpenSongXMLBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA2", resultA2 )
        resultA3 = OpenSongXMLBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA3", resultA3 )

        testSubfolder = os.path.join( testFolder, 'nrsv_update/' )
        resultB1 = OpenSongXMLBibleFileCheck( testSubfolder )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestB1", resultB1 )
        resultB2 = OpenSongXMLBibleFileCheck( testSubfolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestB2", resultB2 )
        resultB3 = OpenSongXMLBibleFileCheck( testSubfolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestB3", resultB3 )


    if 0:
        for j, testFilename in enumerate( allOfThem ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "\n\nOpnSng B{}/ {}".format( j+1, testFilename ) )
            testFilepath = os.path.join( testFolder, testFilename )

            # Demonstrate the OpenSong XML Bible class
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "Demonstrating the OpenSong XML Bible class…" )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test filepath is {!r}".format( testFilepath ) )
            xb = OpenSongXMLBible( testFolder, testFilename )
            xb.load() # Load and process the XML
            if BibleOrgSysGlobals.verbosityLevel > 0: print( xb ) # Just print a summary
            #print( xb.books['JDE']._processedLines )
            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
                for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                    (t, b, c, v) = reference
                    if t=='OT' and len(xb)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(xb)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(xb)<=66: continue # Don't bother with DC references if it's too small
                    svk = VerseReferences.SimpleVerseKey( b, c, v )
                    #print( svk, ob.getVerseDataList( reference ) )
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, svk.getShortText(), xb.getVerseText( svk ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and not xb: halt # if no books
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of OpenSongXMLBible.py
