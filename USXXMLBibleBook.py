#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USXXMLBibleBook.py
#
# Module handling USX Bible Book xml
#
# Copyright (C) 2012-2015 Robert Hunt
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

LastModifiedDate = '2015-05-20' # by RJH
ShortProgName = "USXXMLBibleBookHandler"
ProgName = "USX XML Bible book handler"
ProgVersion = '0.14'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals
from Bible import BibleBook


sortedNLMarkers = sorted( BibleOrgSysGlobals.USFMMarkers.getNewlineMarkersList('Combined'), key=len, reverse=True )



def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )
# end of t



class USXXMLBibleBook( BibleBook ):
    """
    Class to load, validate, and manipulate a single Bible book in USX XML.
    """
    def __init__( self, name, BBB ):
        """
        Create the USX Bible book object.
        """
        BibleBook.__init__( self, name, BBB ) # Initialise the base class
        self.objectNameString = "USX XML Bible Book object"
        self.objectTypeString = "USX"

        #self.BBB = BBB
    # end of USXXMLBibleBook.__init__


    def load( self, filename, folder=None, encoding='utf-8' ):
        """
        Load a single source USX XML file and extract the information.
        """

        def loadParagraph( paragraphXML, paragraphlocation ):
            """ Load a paragraph from the USX XML.
                Uses (and updates) c,v information from the containing function. """
            nonlocal c, v

            # Process the attributes first
            paragraphStyle = None
            for attrib,value in paragraphXML.items():
                if attrib=='style':
                    paragraphStyle = value # This is basically the USFM marker name
                else:
                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )

            # Now process the paragraph text (or write a paragraph marker anyway)
            self.addLine( paragraphStyle, paragraphXML.text if paragraphXML.text and paragraphXML.text.strip() else '' )

            # Now process the paragraph subelements
            for element in paragraphXML:
                location = element.tag + ' ' + paragraphlocation
                #print( "USXXMLBibleBook.load", c, v, element.tag, location )
                if element.tag == 'verse': # milestone (not a container)
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    # Process the attributes first
                    verseStyle = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            v = value
                        elif attrib=='style':
                            verseStyle = value
                        else:
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if verseStyle != 'v':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( verseStyle, location ) )
                    self.addLine( verseStyle, v + ' ' )
                    # Now process the tail (if there's one) which is the verse text
                    if element.tail:
                        vText = element.tail.strip()
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
                            assert( not BibleOrgSysGlobals.USFMMarkers.isNewlineMarker( charStyle ) )
                        else:
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    charLine = "\\{} {} ".format( charStyle, element.text )
                    # Now process the subelements -- chars are one of the few multiply embedded fields in USX
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + location
                        #print( c, v, element.tag )
                        if subelement.tag == 'char': # milestone (not a container)
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            # Process the attributes first
                            subCharStyle, charClosed = None, True
                            for attrib,value in subelement.items():
                                if attrib=='style': subCharStyle = value
                                elif attrib=='closed':
                                    assert( value=='false' )
                                    charClosed = False
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            charLine += "\\{} {}".format( subCharStyle, subelement.text )
                            if charClosed: charLine += "\\{}*".format( subCharStyle )
                            charLine += '' if subelement.tail is None else subelement.tail.strip()
                        else:
                            logging.warning( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, c, v, sublocation ) )
                            self.addPriorityError( 1, c, v, _("Unprocessed {} subelement").format( subelement.tag ) )
                    # A character field must be added to the previous field
                    charLine += "\\{}*{}".format( charStyle, '' if element.tail is None else element.tail.strip() )
                    if debuggingThisModule: print( "USX.loadParagraph:", c, v, paragraphStyle, charStyle, repr(charLine) )
                    self.appendToLastLine( charLine )
                elif element.tag == 'note':
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    # Process the attributes first
                    noteStyle = noteCaller = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            noteStyle = value # This is basically the USFM marker name
                            assert( noteStyle in ('x','f',) )
                        elif attrib=='caller': noteCaller = value # Usually hyphen or a symbol to be used for the note
                        else:
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    assert( noteStyle and noteCaller ) # both compulsory
                    noteLine = "\\{} {} ".format( noteStyle, noteCaller )
                    # Now process the subelements -- notes are one of the few multiply embedded fields in USX
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + location
                        #print( c, v, element.tag )
                        if subelement.tag == 'char': # milestone (not a container)
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            # Process the attributes first
                            charStyle, charClosed = None, True
                            for attrib,value in subelement.items():
                                if attrib=='style':
                                    charStyle = value
                                elif attrib=='closed':
                                    assert( value=='false' )
                                    charClosed = False
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            noteLine += "\\{} {}".format( charStyle, subelement.text )
                            if charClosed: noteLine += "\\{}*".format( charStyle )
                            noteLine += '' if subelement.tail is None else subelement.tail.strip()
                        elif subelement.tag == 'unmatched': # Used to denote errors in the source text
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation )
                            # Process the attributes first
                            unmmatchedMarker = None
                            for attrib,value in subelement.items():
                                if attrib=='marker':
                                    unmmatchedMarker = value
                                else:
                                    logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            self.addPriorityError( 2, c, v, _("Unmatched subelement for {} in {}").format( repr(unmmatchedMarker), sublocation) if unmmatchedMarker else _("Unmatched subelement in {}").format( sublocation) )
                        else:
                            logging.warning( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, self.BBB, c, v, sublocation ) )
                            self.addPriorityError( 1, c, v, _("Unprocessed {} subelement").format( subelement.tag ) )
                        if subelement.tail and subelement.tail.strip(): noteLine += subelement.tail
                    #noteLine += "\\{}*".format( charStyle )
                    noteLine += "\\{}*".format( noteStyle )
                    if element.tail:
                        noteText = element.tail.strip()
                        noteLine += noteText
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
                            assert( linkStyle in ('jmp',) )
                        elif attrib=='display':
                            linkDisplay = value # e.g., "click here"
                        elif attrib=='target':
                            linkTarget = value # e.g., some reference
                        else:
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    self.addPriorityError( 3, c, v, _("Unprocessed {} link to {} in {}").format( repr(linkDisplay), repr(linkTarget), location) )
                elif element.tag == 'unmatched': # Used to denote errors in the source text
                    BibleOrgSysGlobals.checkXMLNoText( element, location )
                    BibleOrgSysGlobals.checkXMLNoTail( element, location )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, location )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, location )
                    self.addPriorityError( 2, c, v, _("Unmatched element in {}").format( location) )
                else:
                    logging.warning( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, c, v, location ) )
                    self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                    for x in range(max(0,len(self)-10),len(self)): print( x, self._rawLines[x] )
                    if BibleOrgSysGlobals.debugFlag: halt
        # end of loadParagraph

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Loading {}...").format( filename ) )
        self.isOneChapterBook = self.BBB in BibleOrgSysGlobals.BibleBooksCodes.getSingleChapterBooksList()
        self.sourceFilename = filename
        self.sourceFolder = folder
        self.sourceFilepath = os.path.join( folder, filename ) if folder else filename
        self.tree = ElementTree().parse( self.sourceFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        c = v = '0'
        loadErrors = []
        lastMarker = None

        # Find the main container
        if self.tree.tag=='usx' or self.tree.tag=='usfm': # Not sure why both are allowable
            location = "USX ({}) file".format( self.tree.tag )
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location )

            # Process the attributes first
            self.schemaLocation = ''
            version = None
            for attrib,value in self.tree.items():
                if attrib=='version': version = value
                else: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
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
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if bookStyle != 'id':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( bookStyle, sublocation ) )
                    idLine = idField
                    if element.text and element.text.strip(): idLine += ' ' + element.text
                    self.addLine( 'id', idLine )
                elif element.tag == 'chapter': # milestone (not a container)
                    v = '0'
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation )
                    # Process the attributes
                    chapterStyle = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            c = value
                        elif attrib=='style':
                            chapterStyle = value
                        else:
                            logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if chapterStyle != 'c':
                        logging.warning( _("Unexpected style attribute ({}) in {}").format( chapterStyle, sublocation ) )
                    self.addLine( 'c', c )
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
                            print( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {}").format( self.BBB, c, v, USFMMarker, text ) )
                            #halt # Not checked yet
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM marker at beginning of line with text: {}").format( self.BBB, c, v, USFMMarker, text ) )
                            logging.warning( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line with text: {}").format( USFMMarker, self.BBB, c, v, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' internal USFM Marker at beginning of line (with no text)").format( self.BBB, c, v, USFMMarker ) )
                            logging.warning( _("Found '\\{}' internal USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, c, v ) )
                        self.addPriorityError( 97, c, v, _("Found \\{} internal USFM Marker on new line in file").format( USFMMarker ) )
                        #lastText += '' if lastText.endswith(' ') else ' ' # Not always good to add a space, but it's their fault!
                        lastText =  '\\' + USFMMarker + ' ' + text
                        #print( "{} {} {} Now have {}:{!r}".format( self.BBB, c, v, lastMarker, lastText ) )
                    else: # the line begins with an unknown USFM Marker
                        text = element.text
                        if text:
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line with text: {}").format( self.BBB, c, v, USFMMarker, text ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line with text: {}").format( USFMMarker, self.BBB, c, v, text ) )
                        else: # no text
                            loadErrors.append( _("{} {}:{} Found '\\{}' unknown USFM Marker at beginning of line (with no text").format( self.BBB, c, v, USFMMarker ) )
                            logging.error( _("Found '\\{}' unknown USFM Marker after {} {}:{} at beginning of line (with no text)").format( USFMMarker, self.BBB, c, v ) )
                        self.addPriorityError( 100, c, v, _("Found \\{} unknown USFM Marker on new line in file").format( USFMMarker ) )
                        for tryMarker in sortedNLMarkers: # Try to do something intelligent here -- it might be just a missing space
                            if USFMMarker.startswith( tryMarker ): # Let's try changing it
                                if lastMarker: self.addLine( lastMarker, lastText )
                                lastMarker, lastText = tryMarker, USFMMarker[len(tryMarker):] + ' ' + text
                                loadErrors.append( _("{} {}:{} Changed '\\{}' unknown USFM Marker to {!r} at beginning of line: {}").format( self.BBB, c, v, USFMMarker, tryMarker, text ) )
                                logging.warning( _("Changed '\\{}' unknown USFM Marker to {!r} after {} {}:{} at beginning of line: {}").format( USFMMarker, tryMarker, self.BBB, c, v, text ) )
                                break
                        # Otherwise, don't bother processing this line -- it'll just cause more problems later on
                else:
                    logging.warning( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, self.BBB, c, v, sublocation ) )
                    self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )

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
        return someString[:int(maxLen/2)]+'...'+someString[-int(maxLen/2):]

    import USXFilenames, USFMFilenames, USFMBibleBook
    #name, testFolder = "Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/" # You can put your USX test folder here
    name, testFolder = "Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/" # You can put your USX test folder here
    name2, testFolder2 = "Matigsalug", "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your USFM test folder here (for comparing the USX with)
    if os.access( testFolder, os.R_OK ):
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Scanning {} from {}...").format( name, testFolder ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Scanning {} from {}...").format( name, testFolder2 ) )
        fileList = USXFilenames.USXFilenames( testFolder ).getConfirmedFilenames()
        for BBB,filename in fileList:
            if BBB in (
                     'GEN',
                    'RUT', 'EST',
                    'DAN', 'JNA',
                    'MAT','MRK','LUK','JHN','ACT',
                    'ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT','PHM',
                    'HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV'
                    ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading {} from {}...").format( BBB, filename ) )
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
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} from {}...").format( BBB2, filename2 ) )
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
                                    #print( "usx ", i, len(UxBB._processedLines[i]), str(UxBB._processedLines[i])[:2] )
                                    #print( "usfm", i, len(UBB._processedLines[i]), UBB._processedLines[i][0]) #[:2] )
                                    print( "\n{} line {} not equal: {}({}) from {}({})".format( BBB, i, UxBB._processedLines[i][0], UxBB._processedLines[i][1], UBB._processedLines[i][0], UBB._processedLines[i][1] ) )
                                    if UxBB._processedLines[i][2] != UBB._processedLines[i][2]:
                                        print( "   UsxBB[2]: {!r}".format( getShortVersion( UxBB._processedLines[i][2] ) ) )
                                        print( "   UsfBB[2]: {!r}".format( getShortVersion( UBB._processedLines[i][2] ) ) )
                                    if (UxBB._processedLines[i][3] or UBB._processedLines[i][3]) and UxBB._processedLines[i][3]!=UBB._processedLines[i][3]:
                                        print( "   UdsBB[3]: {!r}".format( getShortVersion( UxBB._processedLines[i][3] ) ) )
                                        print( "   UsfBB[3]: {!r}".format( getShortVersion( UBB._processedLines[i][3] ) ) )
                                    mismatchCount += 1
                            else: # one has more lines
                                print( "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                                mismatchCount += 1
                                break
                            if mismatchCount > 5: print( "..." ); break
                        if mismatchCount == 0 and BibleOrgSysGlobals.verbosityLevel > 2: print( "All {} processedLines matched!".format( UxL ) )
                    else: print( "Sorry, USFM test folder doesn't contain the {} book.".format( BBB ) )
                else: print( "Sorry, USFM test folder {!r} doesn't exist on this computer.".format( testFolder2 ) )
            elif BibleOrgSysGlobals.verbosityLevel > 2: print( "*** Skipped USX/USFM compare on {}", BBB )
    else: print( "Sorry, USX test folder {!r} doesn't exist on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of USXXMLBibleBook.py