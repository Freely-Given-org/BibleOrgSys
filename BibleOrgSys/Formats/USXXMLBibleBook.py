#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBibleBook.py
#
# Module handling USX Bible Book xml
#
# Copyright (C) 2012-2020 Robert Hunt
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
Module handling USX Bible book xml to parse and load as an internal Bible book.
"""
from gettext import gettext as _
from typing import List
import logging
import os
from pathlib import Path
import sys
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import BibleBook


LAST_MODIFIED_DATE = '2020-04-20' # by RJH
SHORT_PROGRAM_NAME = "USXXMLBibleBookHandler"
PROGRAM_NAME = "USX XML Bible book handler"
PROGRAM_VERSION = '0.27'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


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
    # end of USXXMLBibleBook.__init__


    def load( self, filename:str, folder=None, encoding:str='utf-8' ) -> None:
        """
        Load a single source USX XML file and extract the information.
        """
        vPrint( 'Never', debuggingThisModule, "load( {}, {}, {} )".format( filename, folder, encoding ) )

        C, V = '-1', '-1' # So first/id line starts at -1:0
        loadErrors:List[str] = []


        def loadChapterNumberField( chapterNumberElement, chapterNumberLocation:str ) -> None:
            """
            """
            nonlocal C, V
            vPrint( 'Never', debuggingThisModule, "USXXMLBibleBook.loadChapterNumberField( {}, {} @ {} {}:{} )".format( chapterNumberElement.tag, chapterNumberElement, self.BBB, C, V ) )
            assert chapterNumberElement.tag == 'chapter'

            BibleOrgSysGlobals.checkXMLNoText( chapterNumberElement, chapterNumberLocation )
            BibleOrgSysGlobals.checkXMLNoTail( chapterNumberElement, chapterNumberLocation )
            BibleOrgSysGlobals.checkXMLNoSubelements( chapterNumberElement, chapterNumberLocation )

            if ( version is None or version.startswith('3.') ) \
            and 'eid' in chapterNumberElement.keys():
                # It's a chapter end marker
                BibleOrgSysGlobals.checkXMLNoTail( chapterNumberElement, chapterNumberLocation )
                chapterEndId = None
                for attrib,value in chapterNumberElement.items():
                    if attrib=='eid':
                        chapterEndId = value
                        assert chapterEndId[:3] in filename
                        assert chapterEndId[3] == ' '
                        assert chapterEndId[4:] == C
                    else:
                        logging.error( _("MG53 Unprocessed {} attribute ({}) in {}").format( attrib, value, chapterNumberLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            else: # it's a chapter start marker
                V = '0'
                # Process the attributes
                chapterStyle = pubNumber = chapterStartId = None
                for attrib,value in chapterNumberElement.items():
                    if attrib=='number': C = value
                    elif attrib=='style': chapterStyle = value
                    elif attrib=='pubnumber': pubNumber = value
                    elif attrib=='sid':
                        chapterStartId = value
                        assert chapterStartId[:3] in filename
                        assert chapterStartId[3] == ' '
                        assert chapterStartId[4:] == C
                    else:
                        logging.error( _("MG52 Unprocessed {} attribute ({}) in {}").format( attrib, value, chapterNumberLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if chapterStyle != 'c':
                    logging.warning( _("Unexpected style attribute ({}) in {}").format( chapterStyle, chapterNumberLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #if pubNumber: vPrint( 'Quiet', debuggingThisModule, self.BBB, C, repr(pubNumber) ); halt
                self.addLine( 'c', C )
                if pubNumber: self.addLine( 'cp', pubNumber )
        # end of load.loadChapterNumberField


        def loadVerseNumberField( verseNumberElement, verseNumberLocation ) -> None:
            """
            Load a verse field from the USX XML.

            Note that this is a milestone in USX (not a container).
                USX 3.0 adds a start ID field to the verse marker
                as well as adding a verse end milestone (with end ID)

            Has no return value -- updates the data fields directly.
            """
            nonlocal V
            vPrint( 'Never', debuggingThisModule, "USXXMLBibleBook.loadVerseNumberField( {}, {} @ {} {}:{} )".format( verseNumberElement.tag, verseNumberLocation, self.BBB, C, V ) )
            assert verseNumberElement.tag == 'verse'

            BibleOrgSysGlobals.checkXMLNoText( verseNumberElement, verseNumberLocation )
            BibleOrgSysGlobals.checkXMLNoSubelements( verseNumberElement, verseNumberLocation )

            if ( version is None or version.startswith('3.') ) \
            and 'eid' in verseNumberElement.keys():
                # It's a verse end marker
                BibleOrgSysGlobals.checkXMLNoTail( verseNumberElement, verseNumberLocation )
                verseEndId = None
                for attrib,value in verseNumberElement.items():
                    if attrib=='eid':
                        verseEndId = value
                        assert verseEndId[:3] in filename
                        assert verseEndId[3] == ' '
                        colonIx = verseEndId.index( ':' )
                        assert verseEndId[4:colonIx] == C
                        assert verseEndId[colonIx+1:] == V
                    else:
                        logging.error( _("KR61 Unprocessed {} attribute ({}) in {}").format( attrib, value, verseNumberLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            else: # it's a verse start marker
                # Process the attributes first
                verseStyle = altNumber = pubNumber = verseStartId = None
                for attrib,value in verseNumberElement.items():
                    if attrib=='number': V = value
                    elif attrib=='style': verseStyle = value
                    elif attrib=='altnumber': altNumber = value
                    elif attrib=='pubnumber': pubNumber = value # TODO: not used anywhere!
                    elif attrib=='sid':
                        verseStartId = value
                        assert verseStartId[:3] in filename
                        assert verseStartId[3] == ' '
                        colonIx = verseStartId.index( ':' )
                        assert verseStartId[4:colonIx] == C
                        assert verseStartId[colonIx+1:] == V
                    else:
                        logging.error( _("KR60 Unprocessed {} attribute ({}) in {}").format( attrib, value, verseNumberLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if verseStyle != 'v':
                    vLogger = logging.error if verseStyle else logging.critical
                    vLogger( _("Unexpected style attribute ({}) in {}").format( verseStyle, verseNumberLocation ) )
                    if not verseStyle or BibleOrgSysGlobals.strictCheckingFlag \
                    or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt # Bad verse style
                #if altNumber: vPrint( 'Quiet', debuggingThisModule, repr(verseStyle), repr(altNumber) ); halt
                altStuff = ' \\va {}\\va*'.format( altNumber ) if altNumber else ''
                self.addLine( verseStyle, V + altStuff + ' ' )
                # Now process the tail (if there's one) which is the verse text
                if verseNumberElement.tail:
                    vText = verseNumberElement.tail
                    if vText[0]=='\n': vText = vText.lstrip() # Paratext puts cross references on a new line
                    if vText:
                        #vPrint( 'Quiet', debuggingThisModule, repr(vText) )
                        self.appendToLastLine( vText )
        # end of load.loadVerseNumberField


        def loadCharField( charElement, charLocation:str ) -> str:
            """
            Load a formatted / char field from the USX XML.

            Note that this can contain other nested fields.

            Results the result as a string (to be appended to whatever came before)
            """
            vPrint( 'Never', debuggingThisModule, "loadCharField( {}, {} @ {} {}:{} )".format( charElement.tag, charLocation, self.BBB, C, V ) )
            assert charElement.tag == 'char'

            # Process the attributes first
            charStyle = charClosed = None
            for attrib,value in charElement.items():
                if attrib=='style':
                    charStyle = value # This is basically the USFM character marker name
                    #vPrint( 'Quiet', debuggingThisModule, "  charStyle", charStyle )
                    assert not BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( charStyle )
                elif attrib == 'closed':
                    assert value == 'false'
                    charClosed = False
                else:
                    logging.error( _("QU52 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if BibleOrgSysGlobals.isBlank( charElement.text): charLine = '\\{} '.format( charStyle )
            else: charLine = '\\{} {}'.format( charStyle, charElement.text )
            assert '\n' not in charLine

            # Now process the subelements -- chars are one of the few multiply embedded fields in USX
            for subelement in charElement:
                sublocation = subelement.tag + ' ' + location
                #vPrint( 'Quiet', debuggingThisModule, '{} {}:{} {}'.format( self.BBB, C, V, charElement.tag ) )
                if subelement.tag == 'char': # milestone (not a container)
                    charLine += loadCharField( subelement, sublocation ) # recursive call
                elif subelement.tag == 'ref':
                    #vPrint( 'Quiet', debuggingThisModule, "ref", BibleOrgSysGlobals.elementStr( subelement ) )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                    # Process the attribute first
                    refLoc = None
                    for attrib,value in subelement.items():
                        if attrib=='loc': refLoc = value
                        else:
                            logging.error( _("KF24 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "ref", refLoc, repr(charElement.text), repr(charElement.tail), repr(charElement.text + (charElement.tail if element.tail else '')) )
                    charLine += (subelement.text if not BibleOrgSysGlobals.isBlank(subelement.text) else '') \
                                + (subelement.tail if not BibleOrgSysGlobals.isBlank(subelement.tail) else '')
                    # TODO: How do we save reference in USFM???
                elif subelement.tag == 'note':
                    #vPrint( 'Quiet', debuggingThisModule, "NOTE", BibleOrgSysGlobals.elementStr( subelement ) )
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
            if charClosed != False: # None or True
                # assert not charLine.endswith( ' ' )
                charLine += '\\{}*'.format( charStyle )
            # A character field must be added to the previous field
            #if charElement.tail is not None: vPrint( 'Quiet', debuggingThisModule, " tail2", repr(charElement.tail) )
            charTail = ''
            if charElement.tail:
                charTail = charElement.tail
                if charTail[0]=='\n': charTail = charTail.lstrip() # Paratext puts footnote parts on new lines
                if charTail and charTail[-1] in ('\n','\t'): charTail = charTail.rstrip()
            #vPrint( 'Quiet', debuggingThisModule, "charLine", repr(charLine), "charStyle", repr(charStyle), "charTail", repr(charTail) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert '\n' not in charLine
                assert '\n' not in charStyle
                assert '\n' not in charTail
            charLine += charTail
            vPrint( 'Never', debuggingThisModule, f"USX.loadCharField: {self.BBB} {C}:{V} {charStyle} {charLine!r}" )
            assert '\n' not in charLine
            # assert ' \\bk*' not in charLine
            return charLine
        # end of load.loadCharField


        def loadNoteField( noteElement, noteLocation:str ) -> str:
            """
            Load a formatted / note field from the USX XML.

            Note that this can contain other nested fields.

            Results the result as a string (to be appended to whatever came before)
            """
            vPrint( 'Never', debuggingThisModule, "loadNoteField( {}, {} @ {} {} {}:{} )".format( noteElement.tag, noteLocation, self.workName, self.BBB, C, V ) )
            vPrint( 'Never', debuggingThisModule, "  {}".format( BibleOrgSysGlobals.elementStr( noteElement ) ) )
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
                #vPrint( 'Quiet', debuggingThisModule, C, V, subelement.tag, repr(noteField) )
                if subelement.tag == 'char': # milestone (not a container)
                    noteCharField = loadCharField( subelement, sublocation )
                    #vPrint( 'Quiet', debuggingThisModule, "noteCharField: {!r}".format( noteCharField ) )
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
                            logging.error( _("NV21 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    self.addPriorityError( 2, C, V, _("Unmatched subelement for {} in {}").format( repr(unmmatchedMarker), sublocation) if unmmatchedMarker else _("Unmatched subelement in {}").format( sublocation) )
                else:
                    logging.error( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, C, V, sublocation ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} subelement").format( subelement.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #vPrint( 'Quiet', debuggingThisModule, BibleOrgSysGlobals.isBlank( subelement.tail ), repr(subelement.tail), repr(noteField) )
                if not BibleOrgSysGlobals.isBlank( subelement.tail ): noteField += subelement.tail
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in noteField
            noteField += '\\{}*'.format( noteStyle )

            if not noteElement.text and len(noteElement) == 0: # no subelements either
                logging.error( _("Note ({}) has no text at {} {}:{} {} -- note will be ignored").format( noteStyle, self.BBB, C, V, noteLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning and debuggingThisModule: halt
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in noteField

            # Now process the left-overs (tail)
            if noteElement.tail:
                #if '\n' in noteElement.tail: halt
                noteTail = noteElement.tail
                if noteTail[0] in ('\n','\t'): noteTail = noteTail.lstrip() # Paratext puts multiple cross-references on new lines
                if noteTail and noteTail[-1] in ('\n','\t'): noteTail = noteTail.rstrip()
                noteField += noteTail

            vPrint( 'Never', debuggingThisModule, "  loadNoteField returning noteField: {!r}".format( noteField ) )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in noteField
            noteField = noteField.replace( ' \\f*', '\\f*' ) # TODO: WHY!!!
            return noteField.replace( '  ', ' ' ) # TODO: Why do we get doubled spaces before \\ft fields in footnotes and \\xt fields in cross-references?
        # end of load.loadNoteField


        def loadParagraph( paragraphXML, paragraphlocation ):
            """
            Load a paragraph from the USX XML.
            In this context, paragraph means heading and intro lines,
                as well as paragraphs of verses.

            Uses (and updates) C,V information from the containing function.
            """
            nonlocal C, V
            #vPrint( 'Quiet', debuggingThisModule, "USXXMLBibleBook.loadParagraph( {} {} )".format( paragraphXML, paragraphlocation ) )

            # Process the attributes first
            paragraphStyle = paragraphVerseId = None
            for attrib,value in paragraphXML.items():
                if attrib=='style': paragraphStyle = value # This is basically the USFM marker name
                elif attrib=='vid':
                    paragraphVerseId = value
                    assert paragraphVerseId[:3] in filename
                    assert paragraphVerseId[3] == ' '
                    colonIx = paragraphVerseId.index( ':' )
                    assert paragraphVerseId[4:colonIx] == C
                    assert paragraphVerseId[colonIx+1:] == V
                else:
                    logging.error( _("CH46 Unprocessed {} attribute ({}) in {}").format( attrib, value, paragraphlocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            # Now process the paragraph text (or write a paragraph marker anyway)
            paragraphText = paragraphXML.text if paragraphXML.text and paragraphXML.text.strip() else ''
            if version is None: paragraphText = paragraphText.rstrip() # Don't need to strip extra spaces in v2
            #vPrint( 'Quiet', debuggingThisModule, "USXXMLBibleBook.load newLine: {!r} {!r}".format( paragraphStyle, paragraphText ) )
            self.addLine( paragraphStyle, paragraphText )

            # Now process the paragraph subelements
            for element in paragraphXML:
                location = element.tag + ' ' + paragraphlocation
                #vPrint( 'Quiet', debuggingThisModule, "USXXMLBibleBook.load {}:{} {!r} in {}".format( C, V, element.tag, location ) )
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
                    ##if altNumber: vPrint( 'Quiet', debuggingThisModule, repr(verseStyle), repr(altNumber) ); halt
                    #altStuff = ' \\va {}\\va*'.format( altNumber ) if altNumber else ''
                    #self.addLine( verseStyle, V + altStuff + ' ' )
                    ## Now process the tail (if there's one) which is the verse text
                    #if element.tail:
                        #vText = element.tail
                        #if vText[0]=='\n': vText = vText.lstrip() # Paratext puts cross references on a new line
                        #if vText:
                            ##vPrint( 'Quiet', debuggingThisModule, repr(vText) )
                            #self.appendToLastLine( vText )
                elif element.tag == 'char':
                    charLine = loadCharField( element, location )
                    self.appendToLastLine( charLine )
                elif element.tag == 'note':
                    #vPrint( 'Quiet', debuggingThisModule, "NOTE", BibleOrgSysGlobals.elementStr( element ) )
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
                            logging.error( _("KW54 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
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
                            logging.error( _("KW74 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #vPrint( 'Quiet', debuggingThisModule, "ref", refLoc, repr(element.text), repr(element.tail), repr(element.text + (element.tail if element.tail else '')) )
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
                            logging.error( _("KW84 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    figCaption = element.text
                    figLine = '\\fig {}|{}|{}|{}|{}|{}|{}\\fig*'.format( figDesc, figFile, figSize, figLoc, figCopy, figCaption, figRef )
                    #vPrint( 'Quiet', debuggingThisModule, "figLine", figLine )
                    self.appendToLastLine( figLine )
                    if not BibleOrgSysGlobals.isBlank( element.tail ): self.appendToLastLine( element.tail )
                else:
                    logging.error( _("SW22 Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, location ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )
                    for x in range(max(0,len(self)-10),len(self)): vPrint( 'Quiet', debuggingThisModule, x, self._rawLines[x] )
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt
        # end of load.loadParagraph


        # Main code for load()
        #lastMarker = None
        if BibleOrgSysGlobals.verbosityLevel > 3:
            vPrint( 'Quiet', debuggingThisModule, "  " + _("Loading {} from {}…").format( filename, folder ) )
        else: vPrint( 'Info', debuggingThisModule, "  " + _("Loading {}…").format( filename ) )
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
            assert self.XMLTree # Fail here if we didn't load anything at all

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
                    logging.error( _("DG84 Unprocessed {} attribute ({}) in {}").format( attrib, value, treeLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if version not in ( None, '2.0','2.5','2.6','3.0' ):
                logging.critical( _("Not sure if we can handle v{} USX files").format( version ) )
                if debuggingThisModule: halt
            vPrint( 'Quiet', debuggingThisModule, f"  Parsing USX v{version} file for {self.workName} {self.BBB}…" )

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
                            logging.error( _("MD12 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if bookStyle != 'id':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( bookStyle, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    idLine = idField
                    if element.text and element.text.strip(): idLine += ' ' + element.text
                    self.addLine( 'id', idLine )
                elif element.tag == 'chapter': # milestone (not a container)
                    loadChapterNumberField( element, location )
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
                            vPrint( 'Quiet', debuggingThisModule, _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {!r}").format( self.BBB, C, V, USFMMarker, text ) )
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
                        #vPrint( 'Quiet', debuggingThisModule, "{} {} {} Now have {}:{!r}".format( self.BBB, C, V, lastMarker, lastText ) )
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
                                vPrint( 'Quiet', debuggingThisModule, "USX unknown marker={!r} text={!r} status={} @ {} {} {}:{}".format( USFMMarker, text, status, self.workName, self.BBB, C, V ) )
                            for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                                if USFMMarker.startswith( tryMarker ): # Let's try changing it
                                    #vPrint( 'Quiet', debuggingThisModule, "  tryMarker={!r}".format( tryMarker ) )
                                    loadErrors.append( _("{} {}:{} Changed '\\{}' unknown USFM Marker to {!r} at beginning of line: {}").format( self.BBB, C, V, USFMMarker, tryMarker, text ) )
                                    logging.warning( _("Changed '\\{}' unknown USFM Marker to {!r} after {} {}:{} at beginning of line: {}").format( USFMMarker, tryMarker, self.BBB, C, V, text ) )
                                    paragraphText = element.text if element.text and element.text.strip() else ''
                                    if version is None: paragraphText = element.text.rstrip() # Don't need to strip extra spaces in v2
                                    #vPrint( 'Quiet', debuggingThisModule, "USXXMLBibleBook.load newLine: {!r} {!r}".format( paragraphStyle, paragraphText ) )
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
                        #vPrint( 'Quiet', debuggingThisModule, "here1", sublocation )
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
                            #vPrint( 'Quiet', debuggingThisModule, "  hereT {} {} {}:{} {}".format( self.workName, self.BBB, C, V, sub2location ) )
                            #vPrint( 'Quiet', debuggingThisModule, "  {}".format( BibleOrgSysGlobals.elementStr( sub2element ) ) )
                            #vPrint( 'Quiet', debuggingThisModule, "  tC = {}".format( tableCode ) )
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
                                #vPrint( 'Quiet', debuggingThisModule, "cS", cellStyle, "aM", alignMode )
                                if BibleOrgSysGlobals.strictCheckingFlag:
                                    assert cellStyle in ('th1','th2','th3','th4', 'thr1','thr2','thr3','thr4', 'tc1','tc2','tc3','tc4', 'tcr1','tcr2','tcr3','tcr4')
                                    assert alignMode in (None, 'start', 'end')
                                tableCode += '\\{} {}'.format( cellStyle,
                                                sub2element.text if not BibleOrgSysGlobals.isBlank(sub2element.text) else '' )
                                assert '\n' not in tableCode
                                for sub3element in sub2element:
                                    sub3location = sub3element.tag + " in " + sub2location
                                    #vPrint( 'Quiet', debuggingThisModule, "    here3", sub3location )
                                    if sub3element.tag == 'note':
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'TY47' )
                                        #vPrint( 'Quiet', debuggingThisModule, "NOTE", BibleOrgSysGlobals.elementStr( sub3element ) )
                                        processedNoteField = loadNoteField( sub3element, sub3location )
                                        if BibleOrgSysGlobals.strictCheckingFlag: assert '\n' not in processedNoteField
                                        tableCode += processedNoteField
                                        #for sub4element in sub3element:
                                            #sub4location = sub4element.tag + " in " + sub3location
                                            ##vPrint( 'Quiet', debuggingThisModule, "    here4", sub4location )
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
                        #vPrint( 'Quiet', debuggingThisModule, "tableCode: {}".format( tableCode ) )
                        self.addLine( 'tr', tableCode )
                else:
                    logging.error( _("DV60 Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, location ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if loadErrors: self.checkResultsDictionary['Load Errors'] = loadErrors
    # end of USXXMLBibleBook.load
# end of class USXXMLBibleBook



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    from BibleOrgSys.InputOutput import USXFilenames, USFMFilenames
    from BibleOrgSys.Formats import USFMBibleBook

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    def getShortVersion( someString ):
        maxLen = 140
        if len(someString)<maxLen: return someString
        return someString[:int(maxLen/2)]+'…'+someString[-int(maxLen/2):]

    #name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/' ) # You can put your USX test folder here
    #name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/' ) # You can put your USX test folder here
    name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/' ) # You can put your USX test folder here
    name2, testFolder2 = "Matigsalug", Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your USFM test folder here (for comparing the USX with)
    if os.access( testFolder, os.R_OK ):
        vPrint( 'Normal', debuggingThisModule, _("Scanning USX  {} from {}…").format( name, testFolder ) )
        vPrint( 'Normal', debuggingThisModule, _("Scanning USFM {} from {}…").format( name, testFolder2 ) )
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
                vPrint( 'Normal', debuggingThisModule, _("Loading USX {} from {}…").format( BBB, filename ) )
                UxBB = USXXMLBibleBook( name, BBB )
                UxBB.load( filename, testFolder )
                vPrint( 'Info', debuggingThisModule, "  ID is {!r}".format( UxBB.getField( 'id' ) ) )
                vPrint( 'Info', debuggingThisModule, "  Header is {!r}".format( UxBB.getField( 'h' ) ) )
                vPrint( 'Info', debuggingThisModule, "  Main titles are {!r} and {!r}".format( UxBB.getField( 'mt1' ), UxBB.getField( 'mt2' ) ) )
                vPrint( 'Info', debuggingThisModule, UxBB )
                UxBB.validateMarkers()
                UxBBVersification = UxBB.getVersification()
                vPrint( 'Info', debuggingThisModule, UxBBVersification )
                UxBBAddedUnits = UxBB.getAddedUnits()
                vPrint( 'Info', debuggingThisModule, UxBBAddedUnits )
                UxBB.check()
                UxBBErrors = UxBB.getCheckResults()
                vPrint( 'Info', debuggingThisModule, UxBBErrors )
                break

                # # Test our USX code by comparing with the original USFM books
                # if os.access( testFolder2, os.R_OK ):
                #     fileList2 = USFMFilenames.USFMFilenames( testFolder2 ).getConfirmedFilenameTuples()
                #     found2 = False
                #     for BBB2,filename2 in fileList2:
                #         if BBB2 == BBB:
                #             found2 = True; break
                #     if found2:
                #         vPrint( 'Info', debuggingThisModule, _("Loading USFM {} from {}…").format( BBB2, filename2 ) )
                #         UBB = USFMBibleBook.USFMBibleBook( name, BBB )
                #         UBB.load( filename2, testFolder2 )
                #         #vPrint( 'Quiet', debuggingThisModule, "  ID is {!r}".format( UBB.getField( 'id' ) ) )
                #         #vPrint( 'Quiet', debuggingThisModule, "  Header is {!r}".format( UBB.getField( 'h' ) ) )
                #         #vPrint( 'Quiet', debuggingThisModule, "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
                #         vPrint( 'Info', debuggingThisModule, UBB )
                #         UBB.validateMarkers()

                #         # Now compare the USX and USFM projects
                #         if 0:
                #             vPrint( 'Quiet', debuggingThisModule, "\nPRINTING COMPARISON" )
                #             ixFrom, ixTo = 8, 40
                #             if ixTo-ixFrom < 10:
                #                 vPrint( 'Quiet', debuggingThisModule, "UsxBB[{}-{}]".format( ixFrom, ixTo ) )
                #                 for ix in range( ixFrom, ixTo ): vPrint( 'Quiet', debuggingThisModule, "  {} {}".format( '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                #                 vPrint( 'Quiet', debuggingThisModule, "UsfBB[{}-{}]".format( ixFrom, ixTo ) )
                #                 for ix in range( ixFrom, ixTo ): vPrint( 'Quiet', debuggingThisModule, "  {} {}".format( '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                #             else:
                #                 for ix in range( ixFrom, ixTo ):
                #                     vPrint( 'Quiet', debuggingThisModule, "UsxBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                #                     vPrint( 'Quiet', debuggingThisModule, "UsfBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                #             vPrint( 'Quiet', debuggingThisModule, "END COMPARISON\n" )

                #         mismatchCount = 0
                #         UxL, UL = len(UxBB), len(UBB)
                #         for i in range(0, max( UxL, UL ) ):
                #             if i<UxL and i<UL:
                #                 if UxBB._processedLines[i] != UBB._processedLines[i]:
                #                     if BibleOrgSysGlobals.verbosityLevel > 0:
                #                         vPrint( 'Quiet', debuggingThisModule, "\n{} line {} not equal: {}({}) from {}({})".format( BBB, i, UxBB._processedLines[i].getCleanText(), UxBB._processedLines[i].getMarker(), UBB._processedLines[i].getCleanText(), UBB._processedLines[i].getMarker() ) )
                #                     if 1 and BibleOrgSysGlobals.verbosityLevel > 0:
                #                         vPrint( 'Quiet', debuggingThisModule, "usx ", repr(UxBB._processedLines[i]) )
                #                         vPrint( 'Quiet', debuggingThisModule, "usx ", i, len(UxBB._processedLines[i]), UxBB._processedLines[i].getMarker(), UxBB._processedLines[i].getOriginalText() )
                #                         vPrint( 'Quiet', debuggingThisModule, "usfm", repr(UBB._processedLines[i]) )
                #                         vPrint( 'Quiet', debuggingThisModule, "usfm", i, len(UBB._processedLines[i]), UBB._processedLines[i].getMarker() )
                #                     if UxBB._processedLines[i].getAdjustedText() != UBB._processedLines[i].getAdjustedText():
                #                         if BibleOrgSysGlobals.verbosityLevel > 0:
                #                             vPrint( 'Quiet', debuggingThisModule, "   UsxBB[adj]: {!r}".format( getShortVersion( UxBB._processedLines[i].getAdjustedText() ) ) )
                #                             vPrint( 'Quiet', debuggingThisModule, "   UsfBB[adj]: {!r}".format( getShortVersion( UBB._processedLines[i].getAdjustedText() ) ) )
                #                     if (UxBB._processedLines[i].getCleanText() or UBB._processedLines[i].getCleanText()) and UxBB._processedLines[i].getCleanText()!=UBB._processedLines[i].getCleanText():
                #                         if BibleOrgSysGlobals.verbosityLevel > 0:
                #                             vPrint( 'Quiet', debuggingThisModule, "   UdsBB[clT]: {!r}".format( getShortVersion( UxBB._processedLines[i].getCleanText() ) ) )
                #                             vPrint( 'Quiet', debuggingThisModule, "   UsfBB[clT]: {!r}".format( getShortVersion( UBB._processedLines[i].getCleanText() ) ) )
                #                     mismatchCount += 1
                #             else: # one has more lines
                #                 if BibleOrgSysGlobals.verbosityLevel > 0:
                #                     vPrint( 'Quiet', debuggingThisModule, "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                #                 mismatchCount += 1
                #                 break
                #             if mismatchCount > 5 and BibleOrgSysGlobals.verbosityLevel > 0:
                #                 vPrint( 'Quiet', debuggingThisModule, "…" ); break
                #         if mismatchCount == 0 and BibleOrgSysGlobals.verbosityLevel > 2:
                #             vPrint( 'Quiet', debuggingThisModule, "All {} processedLines matched!".format( UxL ) )
                #     else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USFM test folder doesn't contain the {} book.".format( BBB ) )
                # else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USFM test folder {!r} doesn't exist on this computer.".format( testFolder2 ) )
            else: vPrint( 'Info', debuggingThisModule, "*** Skipped USX/USFM compare on {}", BBB )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USX test folder {!r} doesn't exist on this computer.".format( testFolder ) )
# end of USXXMLBibleBook.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    from BibleOrgSys.InputOutput import USXFilenames, USFMFilenames
    from BibleOrgSys.Formats import USFMBibleBook

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    def getShortVersion( someString ):
        maxLen = 140
        if someString is None or len(someString)<maxLen: return someString
        return someString[:int(maxLen/2)]+'…'+someString[-int(maxLen/2):]

    #name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/' ) # You can put your USX test folder here
    #name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/' ) # You can put your USX test folder here
    name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/Exports/USX/MBTV/' )
    # name, testFolder = "Matigsalug", Path( '/home/robert/BibleOrgSysData/BOSOutputFiles/BOS_USX3_Export/USX3Files/' )
    name2, testFolder2 = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/My Paratext 8 Projects Latest/Exports/USX/MBTV/USFM.save/' )
    # name, testFolder = "Matigsalug", Path( '/mnt/SSDs/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/' ) # You can put your USX test folder here
    # name2, testFolder2 = "Matigsalug", Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your USFM test folder here (for comparing the USX with)
    if os.access( testFolder, os.R_OK ):
        vPrint( 'Normal', debuggingThisModule, _("Scanning USX  {} from {}…").format( name, testFolder ) )
        vPrint( 'Normal', debuggingThisModule, _("Scanning USFM {} from {}…").format( name, testFolder2 ) )
        fileList = USXFilenames.USXFilenames( testFolder ).getConfirmedFilenameTuples()
        for BBB,filename in fileList:
            if BBB in (
                    'GEN','EXO','LEV','NUM','DEU',
                    'JOS','JDG',
                    'RUT','SA1','SA2','KI1','KI2','CH1','CH2'
                    'EZR','NEH','EST',
                    'PSA','PRO','SNG',
                    'ISA','JER',
                    'DAN', 'JNA',
                    'MAT','MRK','LUK','JHN','ACT',
                    'ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT','PHM',
                    'HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV'
                    ):
                vPrint( 'Normal', debuggingThisModule, _("Loading USX {} from {}…").format( BBB, filename ) )
                UxBB = USXXMLBibleBook( name, BBB )
                UxBB.load( filename, testFolder )
                vPrint( 'Info', debuggingThisModule, "  ID is {!r}".format( UxBB.getField( 'id' ) ) )
                vPrint( 'Info', debuggingThisModule, "  Header is {!r}".format( UxBB.getField( 'h' ) ) )
                vPrint( 'Info', debuggingThisModule, "  Main titles are {!r} and {!r}".format( UxBB.getField( 'mt1' ), UxBB.getField( 'mt2' ) ) )
                vPrint( 'Info', debuggingThisModule, UxBB )
                UxBB.validateMarkers()
                UxBBVersification = UxBB.getVersification()
                vPrint( 'Info', debuggingThisModule, UxBBVersification )
                UxBBAddedUnits = UxBB.getAddedUnits()
                vPrint( 'Info', debuggingThisModule, UxBBAddedUnits )
                UxBB.check()
                UxBBErrors = UxBB.getCheckResults()
                vPrint( 'Info', debuggingThisModule, UxBBErrors )

                # Test our USX code by comparing with the original USFM books
                if os.access( testFolder2, os.R_OK ):
                    fileList2 = USFMFilenames.USFMFilenames( testFolder2 ).getConfirmedFilenameTuples()
                    found2 = False
                    for BBB2,filename2 in fileList2:
                        if BBB2 == BBB:
                            found2 = True; break
                    if found2:
                        vPrint( 'Info', debuggingThisModule, _("Loading USFM {} from {}…").format( BBB2, filename2 ) )
                        UBB = USFMBibleBook.USFMBibleBook( name, BBB )
                        UBB.load( filename2, testFolder2 )
                        #vPrint( 'Quiet', debuggingThisModule, "  ID is {!r}".format( UBB.getField( 'id' ) ) )
                        #vPrint( 'Quiet', debuggingThisModule, "  Header is {!r}".format( UBB.getField( 'h' ) ) )
                        #vPrint( 'Quiet', debuggingThisModule, "  Main titles are {!r} and {!r}".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
                        vPrint( 'Info', debuggingThisModule, UBB )
                        UBB.validateMarkers()

                        if 0: # Display a given chunk of each book
                            ixFrom, ixTo = 400, 415 # Set the beginning and end ranges here
                            vPrint( 'Quiet', debuggingThisModule, "\nPRINTING COMPARISON" )
                            if ixTo-ixFrom < 10: # Only a few -- display USX block then USFM block
                                vPrint( 'Quiet', debuggingThisModule, "UsxBB[{}-{}]".format( ixFrom, ixTo ) )
                                for ix in range( ixFrom, min( ixTo, len(UxBB._processedLines) ) ):
                                    vPrint( 'Quiet', debuggingThisModule, "  {} {}".format( '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                                vPrint( 'Quiet', debuggingThisModule, "UsfBB[{}-{}]".format( ixFrom, ixTo ) )
                                for ix in range( ixFrom, min( ixTo, len(UBB._processedLines) ) ):
                                    vPrint( 'Quiet', debuggingThisModule, "  {} {}".format( '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                            else: # Too many -- display USX then USFM lines interleaved
                                for ix in range( ixFrom, ixTo ):
                                    try:
                                        vPrint( 'Quiet', debuggingThisModule, "UsxBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UxBB._processedLines[ix] ) )
                                        vPrint( 'Quiet', debuggingThisModule, "UsfBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix]==UBB._processedLines[ix] else 'BAD', UBB._processedLines[ix] ) )
                                        if UxBB._processedLines[ix].extras:
                                            vPrint( 'Quiet', debuggingThisModule, "UsxBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix].extras==UBB._processedLines[ix].extras else 'BAD', UxBB._processedLines[ix].extras ) )
                                        if UBB._processedLines[ix].extras:
                                            vPrint( 'Quiet', debuggingThisModule, "UsfBB[{}]: {} {}".format( ix, '   ' if UxBB._processedLines[ix].extras==UBB._processedLines[ix].extras else 'BAD', UBB._processedLines[ix].extras ) )
                                    except IndexError:
                                        vPrint( 'Quiet', debuggingThisModule, f"     [{ix}] Oops Usx has {len(UxBB._processedLines)} entries, Usfm has {len(UBB._processedLines)}." )
                            vPrint( 'Quiet', debuggingThisModule, "END COMPARISON\n" )

                        # Now compare the USX and USFM projects
                        mismatchCount = 0
                        UxL, UL = len(UxBB), len(UBB)
                        for i in range(0, max( UxL, UL ) ):
                            if i<UxL and i<UL:
                                if UxBB._processedLines[i] != UBB._processedLines[i]:
                                    vPrint( 'Quiet', debuggingThisModule, f"\n{BBB} line {i} not equal:\n  USX  {UxBB._processedLines[i].getCleanText()}({UxBB._processedLines[i].getMarker()}) \n  USFM {UBB._processedLines[i].getCleanText()}({UBB._processedLines[i].getMarker()})" )
                                    vPrint( 'Quiet', debuggingThisModule, "usx ", repr(UxBB._processedLines[i]) )
                                    vPrint( 'Quiet', debuggingThisModule, "usx ", i, len(UxBB._processedLines[i]), UxBB._processedLines[i].getMarker(), UxBB._processedLines[i].getOriginalText() )
                                    vPrint( 'Quiet', debuggingThisModule, "usfm", repr(UBB._processedLines[i]) )
                                    vPrint( 'Quiet', debuggingThisModule, "usfm", i, len(UBB._processedLines[i]), UBB._processedLines[i].getMarker() )
                                    if UxBB._processedLines[i].getAdjustedText() != UBB._processedLines[i].getAdjustedText():
                                        vPrint( 'Quiet', debuggingThisModule, "   UsxBB[adj]: {!r}".format( getShortVersion( UxBB._processedLines[i].getAdjustedText() ) ) )
                                        vPrint( 'Quiet', debuggingThisModule, "   UsfBB[adj]: {!r}".format( getShortVersion( UBB._processedLines[i].getAdjustedText() ) ) )
                                    if (UxBB._processedLines[i].getCleanText() or UBB._processedLines[i].getCleanText()) and UxBB._processedLines[i].getCleanText()!=UBB._processedLines[i].getCleanText():
                                        vPrint( 'Quiet', debuggingThisModule, "   UdsBB[clT]: {!r}".format( getShortVersion( UxBB._processedLines[i].getCleanText() ) ) )
                                        vPrint( 'Quiet', debuggingThisModule, "   UsfBB[clT]: {!r}".format( getShortVersion( UBB._processedLines[i].getCleanText() ) ) )
                                    mismatchCount += 1
                            else: # one has more lines
                                if BibleOrgSysGlobals.verbosityLevel > 0:
                                    vPrint( 'Quiet', debuggingThisModule, "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                                mismatchCount += 1
                                break
                            if mismatchCount > 5 and BibleOrgSysGlobals.verbosityLevel > 0:
                                vPrint( 'Quiet', debuggingThisModule, "…" ); break
                        if mismatchCount == 0 and BibleOrgSysGlobals.verbosityLevel > 2:
                            vPrint( 'Quiet', debuggingThisModule, "All {} processedLines matched!".format( UxL ) )
                    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USFM test folder doesn't contain the {} book.".format( BBB ) )
                else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USFM test folder {!r} doesn't exist on this computer.".format( testFolder2 ) )
            else: vPrint( 'Never', debuggingThisModule, "*** Skipped USX/USFM compare on {}", BBB )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, USX test folder {!r} doesn't exist on this computer.".format( testFolder ) )
# end of USXXMLBibleBook.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USXXMLBibleBook.py
