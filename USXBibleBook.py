#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USXBibleBook.py
#   Last modified: 2012-05-28 (also update versionString below)
#
# Module handling USX Bible Book xml
#
# Copyright (C) 2012 Robert Hunt
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
Module handling USX Bible book xml to produce C and Python data tables.
"""

progName = "USX Bible book handler"
versionString = "0.02"

import logging, os
from gettext import gettext as _
#from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

import Globals
from InternalBibleBook import InternalBibleBook


class USXBibleBook( InternalBibleBook ):
    """
    Class to load, validate, and manipulate a single Bible book in USX XML.
    """
    def __init__( self ):
        """
        Create the USX Bible book object.
        """
        InternalBibleBook.__init__( self ) # Initialise the base class
        self.objectType = "USX"
        self.objectNameString = "USX Bible Book object"
    # end of __init__


    def load( self, bookReferenceCode, folder, filename, encoding ):
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
                    if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )

            # Now process the paragraph text (or write a paragraph marker anyway)
            self.appendLine( paragraphStyle, paragraphXML.text if paragraphXML.text and paragraphXML.text.strip() else '' )

            # Now process the paragraph subelements
            for element in paragraphXML:
                location = element.tag + ' ' + paragraphlocation
                #print( c, v, element.tag )
                if element.tag == 'verse': # milestone (not a container)
                    Globals.checkXMLNoText( element, location )
                    Globals.checkXMLNoSubelements( element, location )
                    # Process the attributes first
                    verseStyle = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            v = value
                        elif attrib=='style':
                            verseStyle = value
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    if verseStyle != 'v':
                        if self.logErrors: logging.warning( _("Unexpected style attribute ({}) in {}").format( verseStyle, location ) )
                    self.appendLine( verseStyle, v + ' ' )
                    # Now process the tail (if there's one) which is the verse text
                    if element.tail:
                        vText = element.tail
                        if vText:
                            self.appendToLastLine( vText )
                elif element.tag == 'char':
                    Globals.checkXMLNoSubelements( element, location )
                    # Process the attributes first
                    charStyle = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            charStyle = value # This is basically the USFM character marker name
                            assert( not self.USFMMarkers.isNewlineMarker( charStyle ) )
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    # A character field must be added to the previous field
                    additionalText = "\\{} {}\\{}*{}".format( charStyle, element.text, charStyle, element.tail )
                    #print( c, v, paragraphStyle, charStyle )
                    self.appendToLastLine( additionalText )
                elif element.tag == 'note':
                    Globals.checkXMLNoText( element, location )
                    # Process the attributes first
                    noteStyle = noteCaller = None
                    for attrib,value in element.items():
                        if attrib=='style':
                            noteStyle = value # This is basically the USFM marker name
                            assert( noteStyle in ('x','f',) )
                        elif attrib=='caller':
                            noteCaller = value # Usually hyphen or a symbol to be used for the note
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    assert( noteStyle and noteCaller ) # both compulsory
                    noteLine = "\\{} {} ".format( noteStyle, noteCaller )
                    # Now process the subelements -- notes are one of the few multiply embedded fields in USX
                    for subelement in element:
                        sublocation = subelement.tag + ' ' + location
                        #print( c, v, element.tag )
                        if subelement.tag == 'char': # milestone (not a container)
                            Globals.checkXMLNoTail( subelement, sublocation )
                            Globals.checkXMLNoSubelements( subelement, sublocation )
                            # Process the attributes first
                            charStyle, charClosed = None, True
                            for attrib,value in subelement.items():
                                if attrib=='style':
                                    charStyle = value
                                elif attrib=='closed':
                                    assert( value=='false' )
                                    charClosed = False
                                else:
                                    if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                            noteLine += "\\{} {}".format( charStyle, subelement.text )
                            if charClosed: noteLine += "\\{}*".format( charStyle )
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} subelement after {} {}:{} in {}").format( subelement.tag, bookReferenceCode, c, v, sublocation ) )
                            self.addPriorityError( 1, self.bookReferenceCode, c, v, _("Unprocessed {} subelement").format( subelement.tag ) )
                    if subelement.tail and subelement.tail.strip(): noteLine += subelement.tail
                    #noteLine += "\\{}*".format( charStyle )
                    noteLine += "\\{}*".format( noteStyle )
                    if element.tail: noteLine += element.tail
                    self.appendToLastLine( noteLine )
                else:
                    if self.logErrors: logging.warning( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, bookReferenceCode, c, v, location ) )
                    self.addPriorityError( 1, self.bookReferenceCode, c, v, _("Unprocessed {} element").format( element.tag ) )
                    for x in range(max(0,len(self)-10),len(self)): print( x, self._lines[x] )
                    halt
        # end of loadParagraph

        if Globals.verbosityLevel > 2: print( "  " + _("Loading {}...").format( filename ) )
        self.bookReferenceCode = bookReferenceCode
        self.isOneChapterBook = bookReferenceCode in self.BibleBooksCodes.getSingleChapterBooksList()
        self.sourceFolder = folder
        self.sourceFilename = filename
        self.sourceFilepath = os.path.join( folder, filename )
        self.tree = ElementTree().parse( self.sourceFilepath )
        assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        c = v = '0'
        #loadErrors = []

        # Find the main container
        if self.tree.tag=='usx' or self.tree.tag=='usfm': # Not sure why both are allowable
            location = "USX ({}) file".format( self.tree.tag )
            Globals.checkXMLNoText( self.tree, location )
            Globals.checkXMLNoTail( self.tree, location )

            # Process the attributes first
            self.schemaLocation = ''
            for attrib,value in self.tree.items():
                if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )

            # Now process the data
            for element in self.tree:
                sublocation = element.tag + " " + location
                if element.tag == 'book': # milestone (not a container)
                    Globals.checkXMLNoSubelements( element, sublocation )
                    Globals.checkXMLNoTail( element, sublocation )
                    # Process the attributes
                    idField = bookStyle = None
                    for attrib,value in element.items():
                        if attrib=='id' or attrib=='code':
                            idField = value # Should be USFM bookcode (not like bookReferenceCode which is BibleOrgSys BBB bookcode)
                            #if idField != bookReferenceCode:
                            #    if self.logErrors: logging.warning( _("Unexpected book code ({}) in {}").format( idField, sublocation ) )
                        elif attrib=='style':
                            bookStyle = value
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if bookStyle != 'id':
                        if self.logErrors: logging.warning( _("Unexpected style attribute ({}) in {}").format( bookStyle, sublocation ) )
                    idLine = idField
                    if element.text and element.text.strip(): idLine += ' ' + element.text
                    self.appendLine( 'id', idLine )
                elif element.tag == 'chapter': # milestone (not a container)
                    v = '0'
                    Globals.checkXMLNoText( element, sublocation )
                    Globals.checkXMLNoTail( element, sublocation )
                    Globals.checkXMLNoSubelements( element, sublocation )
                    # Process the attributes
                    chapterStyle = None
                    for attrib,value in element.items():
                        if attrib=='number':
                            c = value
                        elif attrib=='style':
                            chapterStyle = value
                        else:
                            if self.logErrors: logging.warning( _("Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                    if chapterStyle != 'c':
                        if self.logErrors: logging.warning( _("Unexpected style attribute ({}) in {}").format( chapterStyle, sublocation ) )
                    self.appendLine( 'c', c )
                elif element.tag == 'para':
                    Globals.checkXMLNoTail( element, sublocation )
                    loadParagraph( element, sublocation )
                else:
                    if self.logErrors: logging.warning( _("Unprocessed {} element after {} {}:{} in {}").format( element.tag, bookReferenceCode, c, v, sublocation ) )
                    self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )

        #if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
    # end of load


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    import USXFilenames, USFMFilenames, USFMBibleBook

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Work/VirtualBox_Shared_Folder/USXExports/Projects/MBTV/" # You can put your USX test folder here
    name2, encoding2, testFolder2 = "Matigsalug", "utf-8", "/mnt/Data/Matigsalug/Scripture/MBTV/" # You can put your USFM test folder here (for comparing the USX with)
    if os.access( testFolder, os.R_OK ):
        if Globals.verbosityLevel > 1: print( _("Scanning {} from {}...").format( name, testFolder ) )
        if Globals.verbosityLevel > 1: print( _("Scanning {} from {}...").format( name, testFolder2 ) )
        fileList = USXFilenames.USXFilenames( testFolder ).getActualFilenames()
        for bookReferenceCode,filename in fileList:
            if bookReferenceCode in ('GEN','RUT','EST','DAN','JNA', \
                                        'MAT','MRK','LUK','JHN','ACT', \
                                        'ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT','PHM', \
                                        'HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV'):
                if Globals.verbosityLevel > 1: print( _("Loading {} from {}...").format( bookReferenceCode, filename ) )
                UxBB = USXBibleBook()
                UxBB.logErrors = True
                UxBB.load( bookReferenceCode, testFolder, filename, encoding )
                if Globals.verbosityLevel > 1: print( "  ID is '{}'".format( UxBB.getField( 'id' ) ) )
                if Globals.verbosityLevel > 1: print( "  Header is '{}'".format( UxBB.getField( 'h' ) ) )
                if Globals.verbosityLevel > 1: print( "  Main titles are '{}' and '{}'".format( UxBB.getField( 'mt1' ), UxBB.getField( 'mt2' ) ) )
                if Globals.verbosityLevel > 0: print( UxBB )
                UxBB.validateUSFM()
                UxBBVersification = UxBB.getVersification ()
                if Globals.verbosityLevel > 2: print( UxBBVersification )
                UxBBAddedUnits = UxBB.getAddedUnits ()
                if Globals.verbosityLevel > 2: print( UxBBAddedUnits )
                UxBB.check()
                UxBBErrors = UxBB.getErrors()
                if Globals.verbosityLevel > 2: print( UxBBErrors )

                # Test our USX code by comparing with the original USFM books
                if os.access( testFolder2, os.R_OK ):
                    fileList2 = USFMFilenames.USFMFilenames( testFolder2 ).getActualFilenames()
                    found2 = False
                    for bookReferenceCode2,filename2 in fileList2:
                        if bookReferenceCode2 == bookReferenceCode:
                            found2 = True; break
                    if found2:
                        if Globals.verbosityLevel > 2: print( _("Loading {} from {}...").format( bookReferenceCode2, filename2 ) )
                        UBB = USFMBibleBook.USFMBibleBook()
                        UBB.logErrors = False
                        UBB.load( bookReferenceCode, testFolder2, filename2, encoding2 )
                        #print( "  ID is '{}'".format( UBB.getField( 'id' ) ) )
                        #print( "  Header is '{}'".format( UBB.getField( 'h' ) ) )
                        #print( "  Main titles are '{}' and '{}'".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
                        if Globals.verbosityLevel > 2: print( UBB )
                        UBB.validateUSFM()

                        # Now compare the USX and USFM projects
                        mismatchCount = 0
                        UxL, UL = len(UxBB), len(UBB)
                        for i in range(0, max( UxL, UL ) ):
                            if i<UxL and i<UL:
                                if UxBB._processedLines[i] != UBB._processedLines[i]:
                                    print( "\n{} line {} not equal: {} from {}".format( bookReferenceCode, i, UxBB._processedLines[i][0:2], UBB._processedLines[i][0:2] ) )
                                    print( "   ", "'"+UxBB._processedLines[i][2]+"'" )
                                    print( "   ", "'"+UBB._processedLines[i][2]+"'" )
                                    if UxBB._processedLines[i][3] or UBB._processedLines[i][3]:
                                        print( "   ", UxBB._processedLines[i][3] )
                                        print( "   ", UBB._processedLines[i][3] )
                                    mismatchCount += 1
                            else: # one has more lines
                                print( "Linecount not equal: {} from {}".format( i, UxL, UL ) )
                                mismatchCount += 1
                                break
                            if mismatchCount > 10: print( "..." ); halt
                        if mismatchCount == 0 and Globals.verbosityLevel > 2: print( "All {} processedLines matched!".format( UxL ) )
                    else: print( "Sorry, USFM test folder doesn't contain the {} book.".format( bookReferenceCode ) )
                else: print( "Sorry, USFM test folder '{}' doesn't exist on this computer.".format( testFolder2 ) )
            elif Globals.verbosityLevel > 1: print( "*** Skipped USX/USFM compare on {}", bookReferenceCode )
    else: print( "Sorry, USX test folder '{}' doesn't exist on this computer.".format( testFolder ) )
# end of main

if __name__ == '__main__':
    main()
# end of USXBibleBook.py
