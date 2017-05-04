#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXXMLBibleBook.py
#
# Module handling USX Bible Book xml
#
# Copyright (C) 2012-2017 Robert Hunt
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

LastModifiedDate = '2017-05-02' # by RJH
ShortProgName = "USXXMLBibleBookHandler"
ProgName = "USX XML Bible book handler"
ProgVersion = '0.19'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os, sys
from xml.etree.ElementTree import ElementTree, ParseError

import BibleOrgSysGlobals
from Bible import BibleBook


def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



sortedNLMarkers = None



class USXXMLBibleBook( BibleBook ):
    """
    Class to load, validate, and manipulate a single Bible book in USX XML.
    """
    def __init__( self, name, BBB ):
        """
        Create the USX Bible book object.
        """
        BibleBook.__init__( self, name, BBB ) # Initialise the base class
        self.objectNameString = 'USX XML Bible Book object'
        self.objectTypeString = 'USX'

        global sortedNLMarkers
        if sortedNLMarkers is None:
            sortedNLMarkers = sorted( BibleOrgSysGlobals.USFMMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )
        #self.BBB = BBB
    # end of USXXMLBibleBook.__init__


    def load( self, filename, folder=None, encoding='utf-8' ):
        """
        Load a single source USX XML file and extract the information.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("load( {}, {}, {} )").format( filename, folder, encoding ) )

        def loadParagraph( paragraphXML, paragraphlocation ):
            """
            Load a paragraph from the USX XML.
            In this context, paragraph means heading and intro lines,
                as well as paragraphs of verses.

            Uses (and updates) C,V information from the containing function.
            """
            nonlocal C, V

            # Process the attributes first
            paragraphStyle = None
            for attrib,value in paragraphXML.items():
                if attrib=='style':
                    paragraphStyle = value # This is basically the USFM marker name
                else:
                    logging.warning( _("CH46 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )

            # Now process the paragraph text (or write a paragraph marker anyway)
            paragraphText = paragraphXML.text if paragraphXML.text and paragraphXML.text.strip() else ''
            if version is None: paragraphText = paragraphText.rstrip() # Don't need to strip extra spaces in v2
            self.addLine( paragraphStyle, paragraphText )

            # Now process the paragraph subelements
            for element in paragraphXML:
                location = element.tag + ' ' + paragraphlocation
                #print( "USXXMLBibleBook.load", C, V, element.tag, location )
                if element.tag == 'verse': # milestone (not a container)
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    # Process the attributes first
                    verseStyle = altNumber = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            V = value
                        elif attrib=='style':
                            verseStyle = value
                        elif attrib=='altnumber':
                            altNumber = value
                        else:
                            logging.error( _("KR60 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if verseStyle != 'v':
                        logging.error( _("Unexpected style attribute ({}) in {}").format( verseStyle, location ) )
                    #if altNumber: print( repr(verseStyle), repr(altNumber) ); halt
                    altStuff = ' \\va {}\\va*'.format( altNumber ) if altNumber else ''
                    self.addLine( verseStyle, V + altStuff + ' ' )
                    # Now process the tail (if there's one) which is the verse text
                    if element.tail:
                        vText = element.tail
                        if vText[0]=='\n': vText = vText.lstrip() # Paratext puts cross references on a new line
                        if vText:
                            #print( repr(vText) )
                            self.appendToLastLine( vText )
                elif element.tag == 'char':
                    # Process the attributes first
                    charStyle = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            charStyle = value # This is basically the USFM character marker name
                            #print( "  charStyle", charStyle )
                            assert not BibleOrgSysGlobals.USFMMarkers.isNewlineMarker( charStyle )
                        else:
                            logging.error( _("QU52 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    charLine = "\\{} {} ".format( charStyle, element.text )
                    # Now process the subelements -- chars are one of the few multiply embedded fields in USX
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + location
                        #print( '{} {}:{} {}'.format( self.BBB, C, V, element.tag ) )
                        if subelement.tag == 'char': # milestone (not a container)
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            # Process the attributes first
                            subCharStyle, charClosed = None, True
                            for attrib,value in subelement.items():
                                if attrib=='style': subCharStyle = value
                                elif attrib=='closed':
                                    assert value=='false'
                                    charClosed = False
                                else:
                                    logging.error( _("KS41 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            charLine += "\\{} {}".format( subCharStyle, subelement.text )
                            if charClosed: charLine += "\\{}*".format( subCharStyle )
                            #if subelement.tail is not None: print( "  tail1", repr(subelement.tail) )
                            charLine += '' if subelement.tail is None else subelement.tail
                        else:
                            logging.error( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, C, V, sublocation ) )
                            self.addPriorityError( 1, C, V, _("Unprocessed {} subelement").format( subelement.tag ) )
                    # A character field must be added to the previous field
                    #if element.tail is not None: print( " tail2", repr(element.tail) )
                    charTail = ''
                    if element.tail:
                        charTail = element.tail
                        if charTail[0]=='\n': charTail = charTail.lstrip() # Paratext puts footnote parts on new lines
                    charLine += "\\{}*{}".format( charStyle, charTail )
                    #if debuggingThisModule: print( "USX.loadParagraph:", C, V, paragraphStyle, charStyle, repr(charLine) )
                    self.appendToLastLine( charLine )
                elif element.tag == 'note':
                    #print( "NOTE", BibleOrgSysGlobals.elementStr( element ) )
                    # Process the attributes first
                    noteStyle = noteCaller = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            noteStyle = value # This is basically the USFM marker name
                            assert noteStyle in ('x','f',)
                        elif attrib=='caller': noteCaller = value # Usually hyphen or a symbol to be used for the note
                        else:
                            logging.error( _("CY38 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if noteCaller=='' and self.BBB=='NUM' and C=='10' and V=='36': noteCaller = '+' # Hack
                    assert noteStyle and noteCaller # both compulsory
                    noteLine = "\\{} {} ".format( noteStyle, noteCaller )
                    if element.text:
                        noteText = element.text.strip()
                        noteLine += noteText
                    # Now process the subelements -- notes are one of the few multiply embedded fields in USX
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + location
                        #print( C, V, subelement.tag )
                        if subelement.tag == 'char': # milestone (not a container)
                            # Process the attributes first
                            charStyle, charClosed = None, True
                            for attrib,value in subelement.items():
                                if attrib=='style':
                                    charStyle = value
                                elif attrib=='closed':
                                    assert value=='false'
                                    charClosed = False
                                else:
                                    logging.warning( _("GJ67 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            noteLine += "\\{} {}".format( charStyle, subelement.text )
                            # Now process the subelements -- notes are one of the few multiply embedded fields in USX
                            for sub2element in subelement:
                                sub2location = sub2element.tag + ' ' + sublocation
                                #print( C, V, sub2element.tag )
                                if sub2element.tag == 'char': # milestone (not a container)
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location )
                                    # Process the attributes first
                                    char2Style, char2Closed = None, True
                                    for attrib,value in sub2element.items():
                                        if attrib=='style':
                                            char2Style = value
                                        elif attrib=='closed':
                                            assert value=='false'
                                            char2Closed = False
                                        else:
                                            logging.warning( _("VH36 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    assert char2Closed
                                    noteLine += "\\{} {}\\{}*{}".format( char2Style, sub2element.text, char2Style, sub2element.tail if sub2element.tail else '' )
                            if charClosed: noteLine += "\\{}*".format( charStyle )
                            if subelement.tail:
                                charTail = subelement.tail
                                if charTail[0]=='\n': charTail = charTail.lstrip() # Paratext puts cross reference parts on a new line
                                noteLine += charTail
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
                            self.addPriorityError( 2, C, V, _("Unmatched subelement for {} in {}").format( repr(unmmatchedMarker), sublocation) if unmmatchedMarker else _("Unmatched subelement in {}").format( sublocation) )
                        else:
                            logging.warning( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, C, V, sublocation ) )
                            self.addPriorityError( 1, C, V, _("Unprocessed {} subelement").format( subelement.tag ) )
                        if subelement.tail and subelement.tail.strip(): noteLine += subelement.tail
                    #noteLine += "\\{}*".format( charStyle )
                    noteLine += "\\{}*".format( noteStyle )
                    if element.tail:
                        #if '\n' in element.tail: halt
                        noteTail = element.tail
                        if noteTail[0]=='\n': noteTail = noteTail.lstrip() # Paratext puts multiple cross-references on new lines
                        noteLine += noteTail
                    #print( "NoteLine", repr(noteLine) )
                    self.appendToLastLine( noteLine )
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
                    self.addPriorityError( 3, C, V, _("Unprocessed {} link to {} in {}").format( repr(linkDisplay), repr(linkTarget), location) )
                elif element.tag == 'unmatched': # Used to denote errors in the source text
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    self.addPriorityError( 2, C, V, _("Unmatched element in {}").format( location) )
                else:
                    logging.warning( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, location ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )
                    for x in range(max(0,len(self)-10),len(self)): print( x, self._rawLines[x] )
                    if BibleOrgSysGlobals.debugFlag: halt
        # end of loadParagraph

        C, V = '0', '-1' # So id line starts at 0:0
        loadErrors = []
        lastMarker = None

        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + _("Loading {} from {}…").format( filename, folder ) )
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading {}…").format( filename ) )
        self.isOneChapterBook = self.BBB in BibleOrgSysGlobals.BibleBooksCodes.getSingleChapterBooksList()
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        try: self.tree = ElementTree().parse( self.sourceFilepath )
        except ParseError as err:
            logging.critical( exp("Loader parse error in xml file {}: {} {}").format( filename, sys.exc_info()[0], err ) )
            loadErrors.append( exp("Loader parse error in xml file {}: {} {}").format( filename, sys.exc_info()[0], err ) )
            self.addPriorityError( 100, C, V, _("Loader parse error in xml file {}: {}").format( filename, err ) )
        if BibleOrgSysGlobals.debugFlag: assert len( self.tree ) # Fail here if we didn't load anything at all

        # Find the main container
        if 'tree' in dir(self) \
        and ( self.tree.tag=='usx' or self.tree.tag=='usfm' ): # Not sure why both are allowable
            location = "USX ({}) file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Process the attributes first
            self.schemaLocation = ''
            version = None
            for attrib,value in self.tree.items():
                if attrib=='version': version = value
                else: logging.warning( _("DG84 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
            if version not in ( None, '2.0' ):
                logging.warning( _("Not sure if we can handle v{} USX files").format( version ) )

            # Now process the data
            for element in self.tree:
                sublocation = element.tag + " " + location
                if element.tag == 'book': # milestone (not a container)
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    # Process the attributes
                    idField = bookStyle = None
                    for attrib,value in element.items():
                        if attrib=='id' or attrib=='code':
                            idField = value # Should be USFM bookcode (not like BBB which is BibleOrgSys BBB bookcode)
                            #if idField != BBB:
                            #    logging.warning( _("Unexpected book code ({}) in {}").format( idField, sublocation ) )
                        elif attrib=='style':
                            bookStyle = value
                        else:
                            logging.warning( _("MD12 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if bookStyle != 'id':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( bookStyle, sublocation ) )
                    idLine = idField
                    if element.text and element.text.strip(): idLine += ' ' + element.text
                    self.addLine( 'id', idLine )
                elif element.tag == 'chapter': # milestone (not a container)
                    V = '0'
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    # Process the attributes
                    chapterStyle = pubNumber = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            C = value
                        elif attrib=='style':
                            chapterStyle = value
                        elif attrib=='pubnumber':
                            pubNumber = value
                        else:
                            logging.error( _("LY76 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if chapterStyle != 'c':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( chapterStyle, sublocation ) )
                    #if pubNumber: print( self.BBB, C, repr(pubNumber) ); halt
                    self.addLine( 'c', C )
                    if pubNumber: self.addLine( 'cp', pubNumber )
                elif element.tag == 'para':
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    USFMMarker = element.attrib['style'] # Get the USFM code for the paragraph style
                    if BibleOrgSysGlobals.USFMMarkers.isNewlineMarker( USFMMarker ):
                        #if lastMarker: self.addLine( lastMarker, lastText )
                        #lastMarker, lastText = USFMMarker, text
                        loadParagraph( element, sublocation )
                    elif BibleOrgSysGlobals.USFMMarkers.isInternalMarker( USFMMarker ): # the line begins with an internal USFM Marker -- append it to the previous line
                        text = element.text
                        if text is None: text = ''
                        if BibleOrgSysGlobals.debugFlag:
                            print( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {}").format( self.BBB, C, V, USFMMarker, text ) )
                            #halt # Not checked yet
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {}").format( self.BBB, C, V, USFMMarker, text ) )
                            logging.warning( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line with text: {}").format( USFMMarker, self.BBB, C, V, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM Marker at beginning of line (with no text)").format( self.BBB, C, V, USFMMarker ) )
                            logging.warning( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, C, V ) )
                        self.addPriorityError( 97, C, V, _("Found \\{} internal USFM Marker on new line in file").format( USFMMarker ) )
                        #lastText += '' if lastText.endswith(' ') else ' ' # Not always good to add a space, but it's their fault!
                        lastText =  '\\' + USFMMarker + ' ' + text
                        #print( "{} {} {} Now have {}:{!r}".format( self.BBB, C, V, lastMarker, lastText ) )
                    else: # the line begins with an unknown USFM Marker
                        try: status = element.attrib['status']
                        except KeyError: status = None
                        text = element.text
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line with text: {}").format( self.BBB, C, V, USFMMarker, text ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line with text: {}").format( USFMMarker, self.BBB, C, V, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line (with no text").format( self.BBB, C, V, USFMMarker ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, C, V ) )
                        self.addPriorityError( 100, C, V, _("Found \\{} unknown USFM Marker on new line in file").format( USFMMarker ) )
                        if status == 'unknown': # USX exporter already knew it was a bad marker
                            pass # Just drop it completely
                        else:
                            for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                                if USFMMarker.startswith( tryMarker ): # Let's try changing it
                                    if lastMarker: self.addLine( lastMarker, lastText )
                                    lastMarker, lastText = tryMarker, USFMMarker[len(tryMarker):] + ' ' + text
                                    loadErrors.append( _("{} {}:{} Changed '\\{}' unknown USFM Marker to {!r} at beginning of line: {}").format( self.BBB, C, V, USFMMarker, tryMarker, text ) )
                                    logging.warning( _("Changed '\\{}' unknown USFM Marker to {!r} after {} {}:{} at beginning of line: {}").format( USFMMarker, tryMarker, self.BBB, C, V, text ) )
                                    break
                        # Otherwise, don't bother processing this line -- it'll just cause more problems later on
                else:
                    logging.error( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, C, V, sublocation ) )
                    self.addPriorityError( 1, C, V, _("Unprocessed {} element").format( element.tag ) )

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
    # end of USXXMLBibleBook.load
# end of class USXXMLBibleBook



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    def getShortVersion( someString ):
        maxLen = 140
        if len(someString)<maxLen: return someString
        return someString[:int(maxLen/2)]+'…'+someString[-int(maxLen/2):]

    import USXFilenames, USFMFilenames, USFMBibleBook
    #name, testFolder = "Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/" # You can put your USX test folder here
    #name, testFolder = "Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/" # You can put your USX test folder here
    name, testFolder = "Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.5 Exports/USX/MBTV/" # You can put your USX test folder here
    name2, testFolder2 = "Matigsalug", "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your USFM test folder here (for comparing the USX with)
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
                UxBBVersification = UxBB.getVersification ()
                if BibleOrgSysGlobals.verbosityLevel > 2: print( UxBBVersification )
                UxBBAddedUnits = UxBB.getAddedUnits ()
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
                                    print( "\n{} line {} not equal: {}({}) from {}({})".format( BBB, i, UxBB._processedLines[i].getCleanText(), UxBB._processedLines[i].getMarker(), UBB._processedLines[i].getCleanText(), UBB._processedLines[i].getMarker() ) )
                                    if 1:
                                        print( "usx ", repr(UxBB._processedLines[i]) )
                                        print( "usx ", i, len(UxBB._processedLines[i]), UxBB._processedLines[i].getMarker(), UxBB._processedLines[i].getOriginalText() )
                                        print( "usfm", repr(UBB._processedLines[i]) )
                                        print( "usfm", i, len(UBB._processedLines[i]), UBB._processedLines[i].getMarker() )
                                    if UxBB._processedLines[i].getAdjustedText() != UBB._processedLines[i].getAdjustedText():
                                        print( "   UsxBB[adj]: {!r}".format( getShortVersion( UxBB._processedLines[i].getAdjustedText() ) ) )
                                        print( "   UsfBB[adj]: {!r}".format( getShortVersion( UBB._processedLines[i].getAdjustedText() ) ) )
                                    if (UxBB._processedLines[i].getCleanText() or UBB._processedLines[i].getCleanText()) and UxBB._processedLines[i].getCleanText()!=UBB._processedLines[i].getCleanText():
                                        print( "   UdsBB[clT]: {!r}".format( getShortVersion( UxBB._processedLines[i].getCleanText() ) ) )
                                        print( "   UsfBB[clT]: {!r}".format( getShortVersion( UBB._processedLines[i].getCleanText() ) ) )
                                    mismatchCount += 1
                            else: # one has more lines
                                print( "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                                mismatchCount += 1
                                break
                            if mismatchCount > 5: print( "…" ); break
                        if mismatchCount == 0 and BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "All {} processedLines matched!".format( UxL ) )
                    else: print( "Sorry, USFM test folder doesn't contain the {} book.".format( BBB ) )
                else: print( "Sorry, USFM test folder {!r} doesn't exist on this computer.".format( testFolder2 ) )
            elif BibleOrgSysGlobals.verbosityLevel > 2: print( "*** Skipped USX/USFM compare on {}", BBB )
    else: print( "Sorry, USX test folder {!r} doesn't exist on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ShortProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ShortProgName, ProgVersion )
# end of USXXMLBibleBook.py
