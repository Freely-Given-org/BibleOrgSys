#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBibleBook.py
#
# Module handling USX Bible Book xml
#
# Copyright (C) 2012-2020 Robert Hunt
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
Module handling USX Bible book xml to parse and load as an internal Bible book.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-03-18' # by RJH
SHORT_PROGRAM_NAME = "USXXMLBibleBookHandler"
PROGRAM_NAME = "USX XML Bible book handler"
PROGRAM_VERSION = '0.26'
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
from BibleOrgSys.Bible import BibleBook


sortedNLMarkers = None



class USXXMLBibleBook( BibleBook ):
    """
    Class to load, validate, and manipulate a single Bible book in USX XML.
    """
    def __init__( self, containerBibleObject, BBB ):
        """
        Create the USX Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'USX XML Bible Book object'
        self.objectTypeString = 'USX'

        global sortedNLMarkers
        if sortedNLMarkers is None:
            sortedNLMarkers = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )
        #self.BBB = BBB
    # end of USXXMLBibleBook.__init__


    def load( self, filename, folder=None, encoding='utf-8' ):
        """
        Load a single source USX XML file and extract the information.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "load( {}, {}, {} )".format( filename, folder, encoding ) )

        C, V = '-1', '-1' # So first/id line starts at -1:0
        loadErrors = []


        def loadVerseNumberField( verseNumberElement, verseNumberLocation ):
            """
            Load a verse field from the USX XML.

            Note that this is a milestone in USX (not a container).

            Has no return value -- updates the data fields directly.
            """
            nonlocal V
            #print( "USXXMLBibleBook.loadVerseNumberField( {}, {} @ {} {}:{} )".format( verseNumberElement.tag, verseNumberLocation, self.BBB, C, V ) )
            assert verseNumberElement.tag == 'verse'

            BibleOrgSysGlobals.checkXMLNoText( verseNumberElement, verseNumberLocation )
            BibleOrgSysGlobals.checkXMLNoSubelements( verseNumberElement, verseNumberLocation )
            # Process the attributes first
            verseStyle = altNumber = pubNumber = None
            for attrib,value in verseNumberElement.items():
                if attrib=='number': V = value
                elif attrib=='style': verseStyle = value
                elif attrib=='altnumber': altNumber = value
                elif attrib=='pubnumber': pubNumber = value # TODO: not used anywhere!
                else:
                    logging.error( _("KR60 Unprocessed {} attribute ({}) in {}").format( attrib, value, verseNumberLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if verseStyle != 'v':
                logging.error( _("Unexpected style attribute ({}) in {}").format( verseStyle, verseNumberLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #if altNumber: print( repr(verseStyle), repr(altNumber) ); halt
            altStuff = ' \\va {}\\va*'.format( altNumber ) if altNumber else ''
            self.addLine( verseStyle, V + altStuff + ' ' )
            # Now process the tail (if there's one) which is the verse text
            if verseNumberElement.tail:
                vText = verseNumberElement.tail
                if vText[0]=='\n': vText = vText.lstrip() # Paratext puts cross references on a new line
                if vText:
                    #print( repr(vText) )
                    self.appendToLastLine( vText )
        # end of load.loadVerseNumberField


        def loadCharField( charElement, charLocation ):
            """
            Load a formatted / char field from the USX XML.

            Note that this can contain other nested fields.

            Results the result as a string (to be appended to whatever came before)
            """
            #print( "loadCharField( {}, {} @ {} {}:{} )".format( charElement.tag, charLocation, self.BBB, C, V ) )
            assert charElement.tag == 'char'

            # Process the attributes first
            charStyle = charClosed = None
            for attrib,value in charElement.items():
                if attrib=='style':
                    charStyle = value # This is basically the USFM character marker name
                    #print( "  charStyle", charStyle )
                    assert not BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( charStyle )
                elif attrib == 'closed':
                    assert value == 'false'
                    charClosed = False
                else:
                    logging.error( _("QU52 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if BibleOrgSysGlobals.isBlank( charElement.text): charLine = '\\{} '.format( charStyle )
            else: charLine = '\\{} {} '.format( charStyle, charElement.text )
            assert '\n' not in charLine

            # Now process the subelements -- chars are one of the few multiply embedded fields in USX
            for subelement in charElement:
                sublocation = subelement.tag + ' ' + location
                #print( '{} {}:{} {}'.format( self.BBB, C, V, charElement.tag ) )
                if subelement.tag == 'char': # milestone (not a container)
                    charLine += loadCharField( subelement, sublocation ) # recursive call
                elif subelement.tag == 'ref':
                    #print( "ref", BibleOrgSysGlobals.elementStr( subelement ) )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                    # Process the attribute first
                    refLoc = None
                    for attrib,value in subelement.items():
                        if attrib=='loc': refLoc = value
                        else:
                            logging.warning( _("KF24 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( "ref", refLoc, repr(charElement.text), repr(charElement.tail), repr(charElement.text + (charElement.tail if element.tail else '')) )
                    charLine += (charElement.text if not BibleOrgSysGlobals.isBlank(charElement.text) else '') \
                                + (charElement.tail if not BibleOrgSysGlobals.isBlank(charElement.tail) else '')
                    # TODO: How do we save reference in USFM???
                elif subelement.tag == 'note':
                    #print( "NOTE", BibleOrgSysGlobals.elementStr( subelement ) )
                    processedNoteField = loadNoteField( subelement, sublocation )
                    if BibleOrgSysGlobals.strictCheckingFlag:
                        assert '\n' not in processedNoteField
                        assert '\t' not in processedNoteField
                    charLine += processedNoteField
                else:
                    logging.error( _("BD23 Unprocessed {} subelement ({}) after {} {}:{} in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, self.BBB, C, V, sublocation ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} subelement").format( subelement.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if BibleOrgSysGlobals.strictCheckingFlag:
                    assert '\n' not in charLine
                    assert '\t' not in charLine
            if charClosed != False:
                charLine += '\\{}*'.format( charStyle )
            # A character field must be added to the previous field
            #if charElement.tail is not None: print( " tail2", repr(charElement.tail) )
            charTail = ''
            if charElement.tail:
                charTail = charElement.tail
                if charTail[0]=='\n': charTail = charTail.lstrip() # Paratext puts footnote parts on new lines
                if charTail and charTail[-1] in ('\n','\t'): charTail = charTail.rstrip()
            #print( "charLine", repr(charLine), "charStyle", repr(charStyle), "charTail", repr(charTail) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert '\n' not in charLine
                assert '\n' not in charStyle
                assert '\n' not in charTail
            charLine += charTail
            if debuggingThisModule: print( "USX.loadCharField: {} {}:{} {} {!r}".format( self.BBB, C, V, charStyle, charLine ) )
            assert '\n' not in charLine
            return charLine
        # end of load.loadCharField


        def loadNoteField( noteElement, noteLocation ):
            """
            Load a formatted / note field from the USX XML.

            Note that this can contain other nested fields.

            Results the result as a string (to be appended to whatever came before)
            """
            #print( "loadNoteField( {}, {} @ {} {} {}:{} )".format( noteElement.tag, noteLocation, self.workName, self.BBB, C, V ) )
            #print( "  {}".format( BibleOrgSysGlobals.elementStr( noteElement ) ) )
            assert noteElement.tag == 'note'

            # Process the attributes first
            noteStyle = noteCaller = None
            for attrib,value in noteElement.items():
                if attrib=='style':
                    noteStyle = value # This is basically the USFM marker name
                    assert noteStyle in ('x','f','fe')
                elif attrib=='caller':
                    noteCaller = value # Usually hyphen or plus or a symbol to be used for the note
                else:
                    logging.error( _("CY38 Unprocessed {} attribute ({}) in {}").format( attrib, value, noteLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #if noteCaller=='' and self.BBB=='NUM' and C=='10' and V=='36': noteCaller = '+' # Hack
            if BibleOrgSysGlobals.strictCheckingFlag: assert noteStyle and noteCaller # both compulsory
            if not noteCaller:
                logging.error( "Missing {} note caller in {} {} {}:{}".format( noteStyle, self.workName, self.BBB, C, V ) )
                noteCaller = '+'
            assert noteStyle and noteCaller # both compulsory
            noteField = '\\{} {} '.format( noteStyle, noteCaller )
            if noteElement.text:
                noteText = noteElement.text.strip()
                noteField += noteText

            # Now process the subelements -- notes are one of the few multiply embedded fields in USX
            for subelement in noteElement:
                sublocation = subelement.tag + ' ' + noteLocation
                #print( C, V, subelement.tag, repr(noteField) )
                if subelement.tag == 'char': # milestone (not a container)
                    noteCharField = loadCharField( subelement, sublocation )
                    #print( "noteCharField: {!r}".format( noteCharField ) )
                    noteField += noteCharField
                elif subelement.tag == 'unmatched': # Used to denote errors in the source text
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                    # Process the attributes first
                    unmmatchedMarker = None
                    for attrib,value in subelement.items():
                        if attrib=='marker':
                            unmmatchedMarker = value
                        else:
                            logging.warning( _("NV21 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    self.addPriorityError( 2, C, V, _("Unmatched subelement for {} in {}").format( repr(unmmatchedMarker), sublocation) if unmmatchedMarker else _("Unmatched subelement in {}").format( sublocation) )
                else:
                    logging.error( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, C, V, sublocation ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} subelement").format( subelement.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #print( BibleOrgSysGlobals.isBlank( subelement.tail ), repr(subelement.tail), repr(noteField) )
                if not BibleOrgSysGlobals.isBlank( subelement.tail ): noteField += subelement.tail
                assert '\n' not in noteField
            noteField += '\\{}*'.format( noteStyle )

            if not noteElement.text and len(noteElement) == 0: # no subelements either
                logging.error( _("Note ({}) has no text at {} {}:{} {} -- note will be ignored").format( noteStyle, self.BBB, C, V, noteLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning and debuggingThisModule: halt
            assert '\n' not in noteField

            # Now process the left-overs (tail)
            if noteElement.tail:
                #if '\n' in noteElement.tail: halt
                noteTail = noteElement.tail
                if noteTail[0] in ('\n','\t'): noteTail = noteTail.lstrip() # Paratext puts multiple cross-references on new lines
                if noteTail and noteTail[-1] in ('\n','\t'): noteTail = noteTail.rstrip()
                noteField += noteTail

            #print( "  loadNoteField returning noteField: {!r}".format( noteField ) )
            assert '\n' not in noteField
            return noteField
        # end of load.loadNoteField


        def loadParagraph( paragraphXML, paragraphlocation ):
            """
            Load a paragraph from the USX XML.
            In this context, paragraph means heading and intro lines,
                as well as paragraphs of verses.

            Uses (and updates) C,V information from the containing function.
            """
            nonlocal C, V
            #print( "USXXMLBibleBook.loadParagraph( {} {} )".format( paragraphXML, paragraphlocation ) )

            # Process the attributes first
            paragraphStyle = None
            for attrib,value in paragraphXML.items():
                if attrib=='style': paragraphStyle = value # This is basically the USFM marker name
                else:
                    logging.warning( _("CH46 Unprocessed {} attribute ({}) in {}").format( attrib, value, paragraphlocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            # Now process the paragraph text (or write a paragraph marker anyway)
            paragraphText = paragraphXML.text if paragraphXML.text and paragraphXML.text.strip() else ''
            if version is None: paragraphText = paragraphText.rstrip() # Don't need to strip extra spaces in v2
            #print( "USXXMLBibleBook.load newLine: {!r} {!r}".format( paragraphStyle, paragraphText ) )
            self.addLine( paragraphStyle, paragraphText )

            # Now process the paragraph subelements
            for element in paragraphXML:
                location = element.tag + ' ' + paragraphlocation
                #print( "USXXMLBibleBook.load {}:{} {!r} in {}".format( C, V, element.tag, location ) )
                if element.tag == 'verse': # milestone (not a container in USX)
                    loadVerseNumberField( element, location )
                    #BibleOrgSysGlobals.checkXMLNoText( element, location )
                    #BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    ## Process the attributes first
                    #verseStyle = altNumber = pubNumber = None
                    #for attrib,value in element.items():
                        #if attrib=='number': V = value
                        #elif attrib=='style': verseStyle = value
                        #elif attrib=='altnumber': altNumber = value
                        #elif attrib=='pubnumber': pubNumber = value # TODO: not used anywhere!
                        #else:
                            #logging.error( _("KR60 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #if verseStyle != 'v':
                        #logging.error( _("Unexpected style attribute ({}) in {}").format( verseStyle, location ) )
                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    ##if altNumber: print( repr(verseStyle), repr(altNumber) ); halt
                    #altStuff = ' \\va {}\\va*'.format( altNumber ) if altNumber else ''
                    #self.addLine( verseStyle, V + altStuff + ' ' )
                    ## Now process the tail (if there's one) which is the verse text
                    #if element.tail:
                        #vText = element.tail
                        #if vText[0]=='\n': vText = vText.lstrip() # Paratext puts cross references on a new line
                        #if vText:
                            ##print( repr(vText) )
                            #self.appendToLastLine( vText )
                elif element.tag == 'char':
                    charLine = loadCharField( element, location )
                    self.appendToLastLine( charLine )
                elif element.tag == 'note':
                    #print( "NOTE", BibleOrgSysGlobals.elementStr( element ) )
                    processedNoteField = loadNoteField( element, location )
                    if BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in processedNoteField
                    self.appendToLastLine( processedNoteField )
                elif element.tag == 'link': # Used to include extra resources
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    # Process the attributes first
                    linkStyle = linkDisplay = linkTarget = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            linkStyle = value
                            assert linkStyle in ('jmp',)
                        elif attrib=='display':
                            linkDisplay = value # e.g., "click here"
                        elif attrib=='target':
                            linkTarget = value # e.g., some reference
                        else:
                            logging.warning( _("KW54 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    self.addPriorityError( 3, C, V, _("Unprocessed {} link to {} in {}").format( repr(linkDisplay), repr(linkTarget), location) )
                elif element.tag == 'unmatched': # Used to denote errors in the source text
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( element, location ) # We ignore attributes!!! XXXXXXXXXX
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    self.addPriorityError( 2, C, V, _("Unmatched element in {}").format( location) )
                    if not BibleOrgSysGlobals.isBlank( element.tail ): self.appendToLastLine( element.tail )
                elif element.tag == 'optbreak':
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    if not BibleOrgSysGlobals.isBlank( element.tail ): self.appendToLastLine( '//' + element.tail )
                elif element.tag == 'ref': # In later USX versions
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    # Process the attribute first
                    refLoc = None
                    for attrib,value in element.items():
                        if attrib=='loc': refLoc = value
                        else:
                            logging.warning( _("KW74 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( "ref", refLoc, repr(element.text), repr(element.tail), repr(element.text + (element.tail if element.tail else '')) )
                    self.appendToLastLine( element.text + (element.tail if element.tail else '') )
                    # TODO: How do we save reference in USFM???
                elif element.tag == 'figure':
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'FG11' )
                    # Process the attributes first
                    figStyle = figDesc = figFile = figSize = figLoc = figCopy = figRef = ''
                    for attrib,value in element.items():
                        if attrib=='style': figStyle = value; assert figStyle == 'fig'
                        elif attrib=='desc': figDesc = value
                        elif attrib=='file': figFile = value
                        elif attrib=='size': figSize = value
                        elif attrib=='loc': figLoc = value
                        elif attrib=='copy': figCopy = value
                        elif attrib=='ref': figRef = value
                        else:
                            logging.warning( _("KW84 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    figCaption = element.text
                    figLine = '\\fig {}|{}|{}|{}|{}|{}|{}\\fig*'.format( figDesc, figFile, figSize, figLoc, figCopy, figCaption, figRef )
                    #print( "figLine", figLine )
                    self.appendToLastLine( figLine )
                    if not BibleOrgSysGlobals.isBlank( element.tail ): self.appendToLastLine( element.tail )
                else:
                    logging.warning( _("SW22 Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, location ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )
                    for x in range(max(0,len(self)-10),len(self)): print( x, self._rawLines[x] )
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt
        # end of load.loadParagraph


        # Main code for load()
        #lastMarker = None
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + _("Loading {} from {}…").format( filename, folder ) )
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading {}…").format( filename ) )
        self.isOneChapterBook = self.BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getSingleChapterBooksList()
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        try: self.XMLTree = ElementTree().parse( self.sourceFilepath )
        except ParseError as err:
            logging.critical( "Loader parse error in xml file {}: {} {}".format( filename, sys.exc_info()[0], err ) )
            loadErrors.append( "Loader parse error in xml file {}: {} {}".format( filename, sys.exc_info()[0], err ) )
            self.addPriorityError( 100, C, V, _("Loader parse error in xml file {}: {}").format( filename, err ) )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if 'XMLTree' in self.__dict__ \
        and ( self.XMLTree.tag=='usx' or self.XMLTree.tag=='usfm' ): # Not sure why both are allowable
            treeLocation = "USX ({}) file".format( self.XMLTree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, treeLocation )

            # Process the attributes first
            self.schemaLocation = ''
            version = None
            for attrib,value in self.XMLTree.items():
                if attrib=='version': version = value
                else:
                    logging.warning( _("DG84 Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if version not in ( None, '2.0','2.5','2.6', ):
                logging.warning( _("Not sure if we can handle v{} USX files").format( version ) )
                if debuggingThisModule: halt

            # Now process the data
            for element in self.XMLTree:
                location = element.tag + " " + treeLocation
                if element.tag == 'book': # milestone (not a container)
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    # Process the attributes
                    idField = bookStyle = None
                    for attrib,value in element.items():
                        if attrib=='id' or attrib=='code':
                            idField = value # Should be USFM bookcode (not like BBB which is BibleOrgSys BBB bookcode)
                            #if idField != BBB:
                            #    logging.warning( _("Unexpected book code ({}) in {}").format( idField, location ) )
                        elif attrib=='style':
                            bookStyle = value
                        else:
                            logging.warning( _("MD12 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if bookStyle != 'id':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( bookStyle, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    idLine = idField
                    if element.text and element.text.strip(): idLine += ' ' + element.text
                    self.addLine( 'id', idLine )
                elif element.tag == 'chapter': # milestone (not a container)
                    V = '0'
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    # Process the attributes
                    chapterStyle = pubNumber = None
                    for attrib,value in element.items():
                        if attrib=='number': C = value
                        elif attrib=='style': chapterStyle = value
                        elif attrib=='pubnumber': pubNumber = value
                        else:
                            logging.error( _("LY76 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if chapterStyle != 'c':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( chapterStyle, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #if pubNumber: print( self.BBB, C, repr(pubNumber) ); halt
                    self.addLine( 'c', C )
                    if pubNumber: self.addLine( 'cp', pubNumber )
                elif element.tag == 'verse': # milestone (not a container in USX)
                    loadVerseNumberField( element, location ) # Not in a paragraph!
                elif element.tag == 'para':
                    if C == '-1': V = str( int(V) + 1 ) # first/id line will be 0:0
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    USFMMarker = element.attrib['style'] # Get the USFM code for the paragraph style
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( USFMMarker ):
                        loadParagraph( element, location )
                    elif BibleOrgSysGlobals.loadedUSFMMarkers.isInternalMarker( USFMMarker ): # the line begins with an internal USFM Marker -- append it to the previous line
                        text = element.text
                        if text is None: text = ''
                        if BibleOrgSysGlobals.debugFlag:
                            print( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {!r}").format( self.BBB, C, V, USFMMarker, text ) )
                            #halt # Not checked yet
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {!r}").format( self.BBB, C, V, USFMMarker, text ) )
                            logging.critical( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line with text: {!r}").format( USFMMarker, self.BBB, C, V, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM Marker at beginning of line (with no text)").format( self.BBB, C, V, USFMMarker ) )
                            logging.critical( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, C, V ) )
                        self.addPriorityError( 97, C, V, _("Found \\{} internal USFM Marker on new line in file").format( USFMMarker ) )
                        #lastText += '' if lastText.endswith(' ') else ' ' # Not always good to add a space, but it's their fault!
                        #lastText =  '\\' + USFMMarker + ' ' + text
                        #print( "{} {} {} Now have {}:{!r}".format( self.BBB, C, V, lastMarker, lastText ) )
                    else: # the line begins with an unknown USFM Marker
                        try: status = element.attrib['status']
                        except KeyError: status = None
                        text = element.text
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line with text: {!r}").format( self.BBB, C, V, USFMMarker, text ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line with text: {!r}").format( USFMMarker, self.BBB, C, V, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line (with no text)").format( self.BBB, C, V, USFMMarker ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, C, V ) )
                        self.addPriorityError( 100, C, V, _("Found \\{} unknown USFM Marker on new line in file").format( USFMMarker ) )
                        fixed = False
                        if status == 'unknown': # USX exporter already knew it was a bad marker
                            pass # Just drop it completely
                        else:
                            if debuggingThisModule:
                                print( "USX unknown marker={!r} text={!r} status={} @ {} {} {}:{}".format( USFMMarker, text, status, self.workName, self.BBB, C, V ) )
                            for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                                if USFMMarker.startswith( tryMarker ): # Let's try changing it
                                    #print( "  tryMarker={!r}".format( tryMarker ) )
                                    loadErrors.append( _("{} {}:{} Changed '\\{}' unknown USFM Marker to {!r} at beginning of line: {}").format( self.BBB, C, V, USFMMarker, tryMarker, text ) )
                                    logging.warning( _("Changed '\\{}' unknown USFM Marker to {!r} after {} {}:{} at beginning of line: {}").format( USFMMarker, tryMarker, self.BBB, C, V, text ) )
                                    paragraphText = element.text if element.text and element.text.strip() else ''
                                    if version is None: paragraphText = element.text.rstrip() # Don't need to strip extra spaces in v2
                                    #print( "USXXMLBibleBook.load newLine: {!r} {!r}".format( paragraphStyle, paragraphText ) )
                                    self.addLine( tryMarker, paragraphText )
                                    fixed = True
                                    break
                        if not fixed: # Otherwise, don't bother processing this line -- it'll just cause more problems later on
                            loadErrors.append( _("{} {}:{} Ignoring '\\{}' unknown USFM Marker at beginning of line (with no text)").format( self.BBB, C, V, USFMMarker ) )
                            logging.critical( _("Ignoring '\\{}' unknown USFM Marker after {} {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.workName, self.BBB, C, V ) )
                elif element.tag == 'table':
                    if C == '-1': V = str( int(V) + 1 ) # first/id line will be 0:0
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'TT33' )
                    BibleOrgSysGlobals.checkXMLNoText( element, location, 'TT42' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location, 'TT88' )
                    for subelement in element:
                        sublocation = subelement.tag + " in " + location
                        #print( "here1", sublocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'GR12' )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'JG78' )
                        assert subelement.tag == 'row'
                        # Process the attribute
                        rowStyle = None
                        for attrib,value in subelement.items():
                            if attrib=='style': rowStyle = value
                            else:
                                logging.error( _("LK46 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        assert rowStyle == 'tr'
                        tableCode = ''
                        for sub2element in subelement:
                            sub2location = sub2element.tag + " in " + sublocation
                            #print( "  hereT {} {} {}:{} {}".format( self.workName, self.BBB, C, V, sub2location ) )
                            #print( "  {}".format( BibleOrgSysGlobals.elementStr( sub2element ) ) )
                            #print( "  tC = {}".format( tableCode ) )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, 'TY45' )
                            if sub2element.tag == 'cell':
                                # Process the cell attributes
                                cellStyle = alignMode = None
                                for attrib,value in sub2element.items():
                                    if attrib=='style': cellStyle = value
                                    elif attrib=='align': alignMode = value
                                    else:
                                        logging.error( _("LP16 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                #print( "cS", cellStyle, "aM", alignMode )
                                if BibleOrgSysGlobals.strictCheckingFlag:
                                    assert cellStyle in ('th1','th2','th3','th4', 'thr1','thr2','thr3','thr4', 'tc1','tc2','tc3','tc4', 'tcr1','tcr2','tcr3','tcr4')
                                    assert alignMode in (None, 'start', 'end')
                                tableCode += '\\{} {}'.format( cellStyle,
                                                sub2element.text if not BibleOrgSysGlobals.isBlank(sub2element.text) else '' )
                                assert '\n' not in tableCode
                                for sub3element in sub2element:
                                    sub3location = sub3element.tag + " in " + sub2location
                                    #print( "    here3", sub3location )
                                    if sub3element.tag == 'note':
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'TY47' )
                                        #print( "NOTE", BibleOrgSysGlobals.elementStr( sub3element ) )
                                        processedNoteField = loadNoteField( sub3element, sub3location )
                                        if BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in processedNoteField
                                        tableCode += processedNoteField
                                        #for sub4element in sub3element:
                                            #sub4location = sub4element.tag + " in " + sub3location
                                            ##print( "    here4", sub4location )
                                            #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location, 'TZ49' )
                                            #if sub4element.tag == 'char':
                                                #tableCode += loadCharField( sub4element, sub4location )
                                            #else:
                                                #logging.error( _("KA28 Unprocessed {} sub4element after {} {}:{} in {}").format( sub3element.tag, self.BBB, C, V, sub4location ) )
                                                #self.addPriorityError( 1, C, V, _("Unprocessed {} sub4element").format( sub4element.tag ) )
                                                #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        #if not BibleOrgSysGlobals.isBlank( sub3element.tail ):
                                            #tableCode += sub3element.tail
                                    elif sub3element.tag == 'verse': # Have a verse number inside a table
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'TY47' )
                                        loadVerseNumberField( sub3element, sub3location )
                                    elif sub3element.tag == 'char': # Have formatting inside a table
                                        charLine = loadCharField( sub3element, sub3location )
                                        self.appendToLastLine( charLine )
                                    else:
                                        logging.error( _("KA29 Unprocessed {} sub3element after {} {}:{} in {}").format( sub3element.tag, self.BBB, C, V, sub3location ) )
                                        self.addPriorityError( 1, C, V, _("Unprocessed {} sub3element").format( sub3element.tag ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    assert '\n' not in tableCode
                            elif sub2element.tag == 'verse':
                                loadVerseNumberField( sub2element, sub2location )
                            else:
                                logging.error( _("VA81 Unprocessed {} sub2element after {} {}:{} in {}").format( sub2element.tag, self.BBB, C, V, sub2location ) )
                                self.addPriorityError( 1, C, V, _("Unprocessed {} sub2element").format( sub3element.tag ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        assert '\n' not in tableCode
                        #print( "tableCode: {}".format( tableCode ) )
                        self.addLine( 'tr', tableCode )
                else:
                    logging.error( _("DV60 Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, location ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
    # end of USXXMLBibleBook.load
# end of class USXXMLBibleBook



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    def getShortVersion( someString ):
        maxLen = 140
        if len(someString)<maxLen: return someString
        return someString[:int(maxLen/2)]+'…'+someString[-int(maxLen/2):]

    from BibleOrgSys.InputOutput import USXFilenames, USFMFilenames
    from BibleOrgSys.Formats import USFMBibleBook
    #name, testFolder = "Matigsalug", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/' ) # You can put your USX test folder here
    #name, testFolder = "Matigsalug", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/' ) # You can put your USX test folder here
    name, testFolder = "Matigsalug", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/' ) # You can put your USX test folder here
    name2, testFolder2 = "Matigsalug", BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your USFM test folder here (for comparing the USX with)
    if os.access( testFolder, os.R_OK ):
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Scanning USX  {} from {}…").format( name, testFolder ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Scanning USFM {} from {}…").format( name, testFolder2 ) )
        fileList = USXFilenames.USXFilenames( testFolder ).getConfirmedFilenameTuples()
        for BBB,filename in fileList:
            if BBB in (
                     'GEN',
                    'RUT', 'EST',
                    'DAN', 'JNA',
                    'MAT','MRK','LUK','JHN','ACT',
                    'ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT','PHM',
                    'HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV'
                    ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading USX {} from {}…").format( BBB, filename ) )
                UxBB = USXXMLBibleBook( name, BBB )
                UxBB.load( filename, testFolder )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  ID is {!r}".format( UxBB.getField( 'id' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Header is {!r}".format( UxBB.getField( 'h' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Main titles are {!r} and {!r}".format( UxBB.getField( 'mt1' ), UxBB.getField( 'mt2' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( UxBB )
                UxBB.validateMarkers()
                UxBBVersification = UxBB.getVersification()
                if BibleOrgSysGlobals.verbosityLevel > 2: print( UxBBVersification )
                UxBBAddedUnits = UxBB.getAddedUnits()
                if BibleOrgSysGlobals.verbosityLevel > 2: print( UxBBAddedUnits )
                UxBB.check()
                UxBBErrors = UxBB.getErrors()
                if BibleOrgSysGlobals.verbosityLevel > 2: print( UxBBErrors )

                # Test our USX code by comparing with the original USFM books
                if os.access( testFolder2, os.R_OK ):
                    fileList2 = USFMFilenames.USFMFilenames( testFolder2 ).getConfirmedFilenameTuples()
                    found2 = False
                    for BBB2,filename2 in fileList2:
                        if BBB2 == BBB:
                            found2 = True; break
                    if found2:
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading USFM {} from {}…").format( BBB2, filename2 ) )
                        UBB = USFMBibleBook.USFMBibleBook( name, BBB )
                        UBB.load( filename2, testFolder2 )
                        #print( "  ID is {!r}".format( UBB.getField( 'id' ) ) )
                        #print( "  Header is {!r}".format( UBB.getField( 'h' ) ) )
                        #print( "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( UBB )
                        UBB.validateMarkers()

                        # Now compare the USX and USFM projects
                        if 0:
                            print( "\nPRINTING COMPARISON" )
                            ixFrom, ixTo = 8, 40
                            if ixTo-ixFrom < 10:
                                print( "UsxBB[{}-{}]".format( ixFrom, ixTo ) )
                                for ix in range( ixFrom, ixTo ): print( "  {} {}".format( 'GUD' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                                print( "UsfBB[{}-{}]".format( ixFrom, ixTo ) )
                                for ix in range( ixFrom, ixTo ): print( "  {} {}".format( 'GUD' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                            else:
                                for ix in range( ixFrom, ixTo ):
                                    print( "UsxBB[{}]: {} {}".format( ix, 'GUD' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                                    print( "UsfBB[{}]: {} {}".format( ix, 'GUD' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                            print( "END COMPARISON\n" )

                        mismatchCount = 0
                        UxL, UL = len(UxBB), len(UBB)
                        for i in range(0, max( UxL, UL ) ):
                            if i<UxL and i<UL:
                                if UxBB._processedLines[i] != UBB._processedLines[i]:
                                    if BibleOrgSysGlobals.verbosityLevel > 0:
                                        print( "\n{} line {} not equal: {}({}) from {}({})".format( BBB, i, UxBB._processedLines[i].getCleanText(), UxBB._processedLines[i].getMarker(), UBB._processedLines[i].getCleanText(), UBB._processedLines[i].getMarker() ) )
                                    if 1 and BibleOrgSysGlobals.verbosityLevel > 0:
                                        print( "usx ", repr(UxBB._processedLines[i]) )
                                        print( "usx ", i, len(UxBB._processedLines[i]), UxBB._processedLines[i].getMarker(), UxBB._processedLines[i].getOriginalText() )
                                        print( "usfm", repr(UBB._processedLines[i]) )
                                        print( "usfm", i, len(UBB._processedLines[i]), UBB._processedLines[i].getMarker() )
                                    if UxBB._processedLines[i].getAdjustedText() != UBB._processedLines[i].getAdjustedText():
                                        if BibleOrgSysGlobals.verbosityLevel > 0:
                                            print( "   UsxBB[adj]: {!r}".format( getShortVersion( UxBB._processedLines[i].getAdjustedText() ) ) )
                                            print( "   UsfBB[adj]: {!r}".format( getShortVersion( UBB._processedLines[i].getAdjustedText() ) ) )
                                    if (UxBB._processedLines[i].getCleanText() or UBB._processedLines[i].getCleanText()) and UxBB._processedLines[i].getCleanText()!=UBB._processedLines[i].getCleanText():
                                        if BibleOrgSysGlobals.verbosityLevel > 0:
                                            print( "   UdsBB[clT]: {!r}".format( getShortVersion( UxBB._processedLines[i].getCleanText() ) ) )
                                            print( "   UsfBB[clT]: {!r}".format( getShortVersion( UBB._processedLines[i].getCleanText() ) ) )
                                    mismatchCount += 1
                            else: # one has more lines
                                if BibleOrgSysGlobals.verbosityLevel > 0:
                                    print( "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                                mismatchCount += 1
                                break
                            if mismatchCount > 5 and BibleOrgSysGlobals.verbosityLevel > 0:
                                print( "…" ); break
                        if mismatchCount == 0 and BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "All {} processedLines matched!".format( UxL ) )
                    else: print( "Sorry, USFM test folder doesn't contain the {} book.".format( BBB ) )
                else: print( "Sorry, USFM test folder {!r} doesn't exist on this computer.".format( testFolder2 ) )
            elif BibleOrgSysGlobals.verbosityLevel > 2: print( "*** Skipped USX/USFM compare on {}", BBB )
    else: print( "Sorry, USX test folder {!r} doesn't exist on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USXXMLBibleBook.py
