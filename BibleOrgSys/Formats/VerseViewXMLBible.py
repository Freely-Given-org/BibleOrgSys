#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# VerseViewXMLBible.py
#
# Module handling VerseView XML Bibles
#
# Copyright (C) 2015-2020 Robert Hunt
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
Module reading and loading VerseView XML Bibles:
    <?xml version="1.0" encoding='utf-8' standalone="yes"?>
    <bible>
    <fname>finnish_1938.xml</fname>
    <revision>1</revision>
    <title>Finnish (1938)</title>
    <font>Arial,Helvetica,sans-serif,Calibri</font>
    <copyright>Public Domain</copyright>
    <sizefactor>1</sizefactor>
    <b n="Genesis">
        <c n="1">
        <v n="1">
    Alussa loi Jumala taivaan ja maan.</v>
        <v n="2">
    Ja maa oli autio ja tyhjä, ja pimeys oli syvyyden päällä, ja Jumalan Henki liikkui vetten päällä.</v>
    …


    <?xml version="1.0" encoding="utf-8"?>
    <bible>
    <fname>portuguese-almeida-recebida.xml</fname>
    <revision>3</revision>
    <title>Almeida Recebida (Bíblia em Português)</title>
    <font>Arial,Helvetica,sans-serif,Calibri</font>
    <copyright>Public Domain</copyright>
    <sizefactor>1</sizefactor>
    <b n="Gênesis">
        <c n="1">
        <v n="1">No princípio criou Deus os céus e a terra.</v>
        <v n="2">E a terra estava sem forma e vazia; e havia trevas sobre a face do abismo, e o Espírito de Deus pairava sobre a face das águas.</v>
        <v n="3">E disse Deus: haja luz. E houve luz.</v>
    …
"""
from gettext import gettext as _
from pathlib import Path
import logging
import os
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Bible import Bible, BibleBook


LAST_MODIFIED_DATE = '2020-04-18' # by RJH
SHORT_PROGRAM_NAME = "VerseViewBible"
PROGRAM_NAME = "VerseView XML Bible format handler"
PROGRAM_VERSION = '0.17'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USFX', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def VerseViewXMLBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for VerseView XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one VerseView Bible is found,
        returns the loaded VerseViewXMLBible object.
    """
    fnPrint( debuggingThisModule, "VerseViewXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("VerseViewXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("VerseViewXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', debuggingThisModule, " VerseViewXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
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
    #dPrint( 'Quiet', debuggingThisModule, 'ff', foundFiles )

    # See if there's an VerseView project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<3: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                vPrint( 'Verbose', debuggingThisModule, "VVB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if '<bible>' not in firstLines[1]: continue
            if '<fname>' not in firstLines[2]: continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, "VerseViewXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad and autoLoadBooks):
            ub = VerseViewXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', debuggingThisModule, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        vPrint( 'Verbose', debuggingThisModule, "    VerseViewXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
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
        except PermissionError: pass # can't read folder, e.g., system folder
        #dPrint( 'Quiet', debuggingThisModule, 'fsf', foundSubfiles )

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=3 )
                if not firstLines or len(firstLines)<3: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    vPrint( 'Verbose', debuggingThisModule, "VVB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if '<bible>' not in firstLines[1]: continue
                if '<fname>' not in firstLines[2]: continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, "VerseViewXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = VerseViewXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of VerseViewXMLBibleFileCheck



class VerseViewXMLBible( Bible ):
    """
    Class for reading, validating, and converting VerseViewXMLBible XML.
    """
    XMLNameSpace = "{http://www.w3.org/2001/XMLSchema-instance}"
    treeTag = 'bible'
    filenameTag = 'fname'
    revisionTag = 'revision'
    titleTag = 'title'
    fontTag = 'font'
    copyrightTag = 'copyright'
    sizefactorTag = 'sizefactor'
    bookTag = 'b'
    chapterTag = 'c'
    verseTag = 'v'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the VerseView Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'VerseView XML Bible object'
        self.objectTypeString = 'VerseView'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.XMLTree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            vPrint( 'Quiet', debuggingThisModule, "VerseViewXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of VerseViewXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        vPrint( 'Info', debuggingThisModule, _("Loading {}…").format( self.sourceFilepath ) )
        self.XMLTree = ElementTree().parse( self.sourceFilepath )
        if BibleOrgSysGlobals.debugFlag: assert self.XMLTree # Fail here if we didn't load anything at all

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['VerseView'] = {}

        # Find the main (bible) container
        if self.XMLTree.tag == VerseViewXMLBible.treeTag:
            location = "VerseView XML file"
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.XMLTree, location, 'js24' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8' )

            # Find the submain (various info and then book) containers
            bookNumber = 0
            for element in self.XMLTree:
                if element.tag == VerseViewXMLBible.filenameTag:
                    sublocation = "filename in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    #self.filename = element.text
                elif element.tag == VerseViewXMLBible.revisionTag:
                    sublocation = "revision in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Revision'] = element.text
                elif element.tag == VerseViewXMLBible.titleTag:
                    sublocation = "title in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Title'] = element.text
                elif element.tag == VerseViewXMLBible.fontTag:
                    sublocation = "font in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Font'] = element.text
                elif element.tag == VerseViewXMLBible.copyrightTag:
                    sublocation = "copyright in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Copyright'] = element.text
                elif element.tag == VerseViewXMLBible.sizefactorTag:
                    sublocation = "sizefactor in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    if BibleOrgSysGlobals.debugFlag: assert element.text == '1'
                elif element.tag == VerseViewXMLBible.bookTag:
                    sublocation = "book in " + location
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'g3g5' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    bookNumber += 1
                    self.__validateAndExtractBook( element, bookNumber )
                else: logging.error( "xk15 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( VerseViewXMLBible.treeTag, self.XMLTree.tag ) )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            # These are all compulsory so they should all exist
            #dPrint( 'Quiet', debuggingThisModule, "Filename is {!r}".format( self.filename ) )
            vPrint( 'Quiet', debuggingThisModule, "Revision is {!r}".format( self.suppliedMetadata['VerseView']['Revision'] ) )
            vPrint( 'Quiet', debuggingThisModule, "Title is {!r}".format( self.suppliedMetadata['VerseView']['Title'] ) )
            vPrint( 'Quiet', debuggingThisModule, "Font is {!r}".format( self.suppliedMetadata['VerseView']['Font'] ) )
            vPrint( 'Quiet', debuggingThisModule, "Copyright is {!r}".format( self.suppliedMetadata['VerseView']['Copyright'] ) )
            #dPrint( 'Quiet', debuggingThisModule, "SizeFactor is {!r}".format( self.sizeFactor ) )

        self.applySuppliedMetadata( 'VerseView' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of VerseViewXMLBible.load



    def __validateAndExtractBook( self, book, bookNumber ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """

        vPrint( 'Verbose', debuggingThisModule, _("Validating XML book…") )

        # Process the div attributes first
        BBB = bookName = None
        for attrib,value in book.items():
            if attrib=="n":
                bookName = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in book element".format( attrib, value ) )

        if bookName:
            BBB = self.genericBOS.getBBBFromText( bookName )
        if BBB is None:
            adjustedBookName = BibleOrgSysGlobals.removeAccents( bookName )
            if adjustedBookName != bookName:
                BBB = self.genericBOS.getBBBFromText( adjustedBookName )
        BBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber )
        if BBB2 != BBB: # Just double check using the book number
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', debuggingThisModule, "Assuming that book {} {!r} is {} (not {})".format( bookNumber, bookName, BBB2, BBB ) )
            BBB = BBB2
            #dPrint( 'Quiet', debuggingThisModule, BBB ); halt

        if BBB:
            vPrint( 'Info', debuggingThisModule, _("Validating {} {}…").format( BBB, bookName ) )
            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = 'VerseView XML Bible Book object'
            thisBook.objectTypeString = 'VerseView'
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == VerseViewXMLBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'j3jd' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "vb26 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.chapterTag, element.tag ) )
            vPrint( 'Info', debuggingThisModule, "  Saving {} into results…".format( BBB ) )
            self.stashBook( thisBook )
    # end of VerseViewXMLBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB:str, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 3:
            vPrint( 'Quiet', debuggingThisModule, _("Validating XML chapter…") )

        # Process the chapter attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="n":
                chapterNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #dPrint( 'Quiet', debuggingThisModule, BBB, 'c', chapterNumber )
            thisBook.addLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for {}".format( BBB ) )

        for element in chapter:
            if element.tag == VerseViewXMLBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            else: logging.error( "sv34 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.verseTag, element.tag ) )
    # end of VerseViewXMLBible.__validateAndExtractChapter


    def __validateAndExtractVerse( self, BBB:str, chapterNumber, thisBook, verse ):
        """
        Check/validate and extract verse data from the given XML book record
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 3:
            vPrint( 'Quiet', debuggingThisModule, _("Validating XML verse…") )

        location = "verse in {} {}".format( BBB, chapterNumber )
        BibleOrgSysGlobals.checkXMLNoSubelements( verse, location, 'sg20' )
        BibleOrgSysGlobals.checkXMLNoTail( verse, location, 'l5ks' )

        # Handle verse attributes
        verseNumber = toVerseNumber = None
        for attrib,value in verse.items():
            if attrib=="n":
                verseNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in verse element".format( attrib, value ) )
        if BibleOrgSysGlobals.debugFlag: assert verseNumber
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.addLine( 'v', verseNumber )
        vText = '' if verse.text is None else verse.text
        if vText: vText = vText.strip()
        #if not vText: # This happens if a verse starts immediately with a style or note
            #logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )

        ## Handle verse subelements (notes and styled portions)
        #for subelement in verse:
            #if subelement.tag == VerseViewXMLBible.noteTag:
                #sublocation = "note in " + location
                #noteType = None
                #for attrib,value in subelement.items():
                    #if attrib=="type": noteType = value
                    #else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                #if noteType and noteType not in ('variant',):
                    #logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                #nText, nTail = subelement.text, subelement.tail
                ##dPrint( 'Quiet', debuggingThisModule, "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                #vText += "\\f + \\fk {} \\ft {}\\f*".format( noteType, nText ) if noteType else "\\f + \\ft {}\\f*".format( nText )
                #if nTail:
                    #if '\n' in nTail:
                        #dPrint( 'Quiet', debuggingThisModule, "VerseViewXMLBible.__validateAndExtractVerse: nTail {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, nTail ) )
                        #nTail = nTail.replace( '\n', ' ' )
                    #vText += nTail
                #for sub2element in subelement:
                    #if sub2element.tag == VerseViewXMLBible.styleTag:
                        #sub2location = "style in " + sublocation
                        #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'fyt4' )
                        #fs = css = idStyle = None
                        #for attrib,value in sub2element.items():
                            #if attrib=='fs': fs = value
                            ##elif attrib=="css": css = value
                            ##elif attrib=="id": idStyle = value
                            #else: logging.warning( "Unprocessed {!r} attribute ({}) in style sub2element".format( attrib, value ) )
                        #if BibleOrgSysGlobals.debugFlag: assert fs or css or idStyle
                        #SFM = None
                        #if fs == 'italic': SFM = '\\it'
                        #elif fs == 'super': SFM = '\\bdit'
                        #elif fs == 'emphasis': SFM = '\\em'
                        #else: vPrint( 'Quiet', debuggingThisModule, "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                        ##if css == "font-style:italic": SFM = '\\it'
                        ##elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        ##elif css == "color:#FF0000": SFM = '\\em'
                        ##elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        ##elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        ##else: vPrint( 'Quiet', debuggingThisModule, "css is", css, "idStyle is", idStyle ); halt
                        #sText, sTail = sub2element.text.strip(), sub2element.tail
                        #if BibleOrgSysGlobals.debugFlag: assert sText
                        #if SFM: vText += SFM+' ' + sText + SFM+'*'
                        #else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        #if sTail: vText += sTail.strip()
                    #else: logging.error( "df20 Expected to find {} but got {!r} in {}".format( VerseViewXMLBible.styleTag, sub2element.tag, sublocation ) )

            #elif subelement.tag == VerseViewXMLBible.styleTag:
                #sublocation = "style in " + location
                #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'f5gh' )
                #fs = css = idStyle = None
                #for attrib,value in subelement.items():
                    #if attrib=="fs": fs = value
                    ##elif attrib=="css": css = value
                    ##elif attrib=="id": idStyle = value
                    #else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                #if BibleOrgSysGlobals.debugFlag: assert fs
                #SFM = None
                #if fs == 'super': SFM = '\\bdit'
                #elif fs == 'emphasis': SFM = '\\em'
                #else: vPrint( 'Quiet', debuggingThisModule, "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                ##if css == "font-style:italic": SFM = '\\it'
                ##elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                ##elif css == "color:#FF0000": SFM = '\\em'
                ##elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                ##elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                ##else: vPrint( 'Quiet', debuggingThisModule, "css is", css, "idStyle is", idStyle ); halt
                #sText, sTail = subelement.text.strip(), subelement.tail
                #if BibleOrgSysGlobals.debugFlag: assert sText
                ##dPrint( 'Quiet', debuggingThisModule, BBB, chapterNumber, sublocation )
                #if SFM: vText += SFM+' ' + sText + SFM+'*'
                #else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                #if sTail: vText += sTail.strip()

            #elif subelement.tag == VerseViewXMLBible.breakTag:
                #sublocation = "line break in " + location
                #BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                #art = None
                #for attrib,value in subelement.items():
                    #if attrib=="art":
                        #art = value
                    #else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                #if BibleOrgSysGlobals.debugFlag: assert art == 'x-nl'
                ##dPrint( 'Quiet', debuggingThisModule, BBB, chapterNumber, verseNumber )
                ##assert vText
                #if vText:
                    #thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
                    #vText = ''
                #thisBook.addLine( 'm', subelement.tail.strip() if subelement.tail else '' )
                ##bTail = subelement.tail
                ##if bTail: vText = bTail.strip()
            #else: logging.error( "bd47 Expected to find NOTE or STYLE but got {!r} in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            if '\n' in vText:
                vPrint( 'Quiet', debuggingThisModule, "VerseViewXMLBible.__validateAndExtractVerse: vText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                vText = vText.replace( '\n', ' ' )
            thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
    # end of VerseViewXMLBible.__validateAndExtractVerse
# end of VerseViewXMLBible class


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    #testFolder = Path( '/mnt/SSDs/Bibles/OpenSong Bibles/' ) # These are quite similar
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' )

    if 1: # demo the file checking code
        vPrint( 'Quiet', debuggingThisModule, "TestA1", VerseViewXMLBibleFileCheck( testFolder ) )
        vPrint( 'Quiet', debuggingThisModule, "TestA2", VerseViewXMLBibleFileCheck( testFolder, autoLoad=True ) )
        vPrint( 'Quiet', debuggingThisModule, "TestA3", VerseViewXMLBibleFileCheck( testFolder, autoLoadBooks=True ) )


    if 1:
        count = totalBooks = 0
        if os.access( testFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isfile( somepath ) and something.endswith( '.xml' ):
                    count += 1
                    vPrint( 'Quiet', debuggingThisModule, "\nH B{}/ {}".format( count, something ) )
                    vvB = VerseViewXMLBible( testFolder, something )
                    vvB.load()
                    vPrint( 'Quiet', debuggingThisModule, vvB )
                    if BibleOrgSysGlobals.strictCheckingFlag:
                        vvB.check()
                        #UBErrors = UB.getCheckResults()
                        # dPrint( 'Quiet', debuggingThisModule, UBErrors )
                    #dPrint( 'Quiet', debuggingThisModule, UB.getVersification() )
                    #dPrint( 'Quiet', debuggingThisModule, UB.getAddedUnits() )
                    #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                        ##dPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                        #dPrint( 'Quiet', debuggingThisModule, "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
                    if 1: # Test verse lookup
                        from BibleOrgSys.Reference import VerseReferences
                        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                            ('OT','DAN','1','21'),
                                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                            (t, b, c, v) = reference
                            if t=='OT' and len(vvB)==27: continue # Don't bother with OT references if it's only a NT
                            if t=='NT' and len(vvB)==39: continue # Don't bother with NT references if it's only a OT
                            if t=='DC' and len(vvB)<=66: continue # Don't bother with DC references if it's too small
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #dPrint( 'Quiet', debuggingThisModule, svk, ob.getVerseDataList( reference ) )
                            try: vPrint( 'Quiet', debuggingThisModule, reference, svk.getShortText(), vvB.getVerseText( svk ) )
                            except KeyError: vPrint( 'Quiet', debuggingThisModule, something, reference, "doesn't exist" )
                    if BibleOrgSysGlobals.commandLineArguments.export:
                        vvB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    #else:
                        #vvB.toHaggaiXML()
                    break
                else: vPrint( 'Quiet', debuggingThisModule, "Sorry, skipping {}.".format( something ) )
            if count: vPrint( 'Quiet', debuggingThisModule, "\n{} total VerseView Bibles processed.".format( count ) )
        else: vPrint( 'Quiet', debuggingThisModule, f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of VerseViewXMLBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    #testFolder = Path( '/mnt/SSDs/Bibles/OpenSong Bibles/' ) # These are quite similar
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'VerseViewXML/' )

    if 1: # demo the file checking code
        vPrint( 'Quiet', debuggingThisModule, "TestA1", VerseViewXMLBibleFileCheck( testFolder ) )
        vPrint( 'Quiet', debuggingThisModule, "TestA2", VerseViewXMLBibleFileCheck( testFolder, autoLoad=True ) )
        vPrint( 'Quiet', debuggingThisModule, "TestA3", VerseViewXMLBibleFileCheck( testFolder, autoLoadBooks=True ) )


    if 1:
        count = totalBooks = 0
        if os.access( testFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isfile( somepath ) and something.endswith( '.xml' ):
                    count += 1
                    vPrint( 'Quiet', debuggingThisModule, "\nH B{}/ {}".format( count, something ) )
                    vvB = VerseViewXMLBible( testFolder, something )
                    vvB.load()
                    vPrint( 'Quiet', debuggingThisModule, vvB )
                    if BibleOrgSysGlobals.strictCheckingFlag:
                        vvB.check()
                        #UBErrors = UB.getCheckResults()
                        # dPrint( 'Quiet', debuggingThisModule, UBErrors )
                    #dPrint( 'Quiet', debuggingThisModule, UB.getVersification() )
                    #dPrint( 'Quiet', debuggingThisModule, UB.getAddedUnits() )
                    #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                        ##dPrint( 'Quiet', debuggingThisModule, "Looking for", ref )
                        #dPrint( 'Quiet', debuggingThisModule, "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
                    if 1: # Test verse lookup
                        from BibleOrgSys.Reference import VerseReferences
                        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                            ('OT','DAN','1','21'),
                                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                            (t, b, c, v) = reference
                            if t=='OT' and len(vvB)==27: continue # Don't bother with OT references if it's only a NT
                            if t=='NT' and len(vvB)==39: continue # Don't bother with NT references if it's only a OT
                            if t=='DC' and len(vvB)<=66: continue # Don't bother with DC references if it's too small
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #dPrint( 'Quiet', debuggingThisModule, svk, ob.getVerseDataList( reference ) )
                            try: vPrint( 'Quiet', debuggingThisModule, reference, svk.getShortText(), vvB.getVerseText( svk ) )
                            except KeyError: vPrint( 'Quiet', debuggingThisModule, something, reference, "doesn't exist" )
                    if BibleOrgSysGlobals.commandLineArguments.export:
                        vvB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    #else:
                        #vvB.toHaggaiXML()
                else: vPrint( 'Quiet', debuggingThisModule, "Sorry, skipping {}.".format( something ) )
            if count: vPrint( 'Quiet', debuggingThisModule, "\n{} total VerseView Bibles processed.".format( count ) )
        else: vPrint( 'Quiet', debuggingThisModule, f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of VerseViewXMLBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of VerseViewXMLBible.py
