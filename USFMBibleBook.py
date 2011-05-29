#!/usr/bin/python3
#
# USFMBibleBook.py
#
# Module handling the USFM markers for Bible books
#   Last modified: 2011-05-27 by RJH (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
Module for defining and manipulating USFM Bible books.
"""

progName = "USFM Bible book handler"
versionString = "0.20"


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from BibleBooksCodes import BibleBooksCodes
from USFMMarkers import USFMMarkers


# define allowed punctuation
leadingWordPunctChars = '“‘([{<'
medialWordPunctChars = '-'
dashes = '—–' # em-dash and en-dash
trailingWordPunctChars = ',.”’?)!;:]}>'
allWordPunctChars = leadingWordPunctChars + medialWordPunctChars + dashes + trailingWordPunctChars


class USFMBibleBook:
    """
    Class to load and manipulate a single USFM file / book.
    """

    def __init__( self ):
        """
        Create the object.
        """
        self.lines = []
        self.USFMMarkers = USFMMarkers().loadData()
        self.errorDictionary = OrderedDict()
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
        self.givenAngleBracketWarning, self.givenDoubleQuoteWarning = False, False

        # Set up filled containers for the object
        self.BibleBooksCodes = BibleBooksCodes().loadData()
    # end of __init_

    def __str__( self ):
        """
        This method returns the string representation of a Bible book.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = _("USFM Bible Book object")
        if self.bookReferenceCode: result += ('\n' if result else '') + "  " + self.bookReferenceCode
        if self.sourceFilepath: result += ('\n' if result else '') + "  " + _("From: ") + self.sourceFilepath
        result += ('\n' if result else '') + "  " + _("Number of lines = ") + str(len(self.lines))
        if Globals.verbosityLevel > 1: result += ('\n' if result else '') + "  " + _("Deduced short book name is '{}'").format( self.getBookName() )
        return result
    # end of __str__


    def addPriorityError( self, priority, bookReferenceCode, c, v, string ):
        """Adds a priority error to self.errorDictionary."""
        assert( isinstance( priority, int ) and ( 0 <= priority <= 100 ) )
        assert( isinstance( string, str ) and string)
        if not 'Priority Errors' in self.errorDictionary: self.errorDictionary['Priority Errors'] = [] # Just in case getErrors() deleted it

        if self.errorDictionary['Priority Errors']:
            LastPriority, lastString, (lastBookReferenceCode,lastC,lastV,) = self.errorDictionary['Priority Errors'][-1]
            if priority==LastPriority and string==lastString and bookReferenceCode==lastBookReferenceCode: # Remove unneeded repetitive information
                bookReferenceCode = ''
                if c==lastC: c = ''

        self.errorDictionary['Priority Errors'].append( (priority,string,(bookReferenceCode,c,v,),) )
    # end of addPriorityError


    def load( self, bookReferenceCode, folder, filename, encoding='utf-8', logErrors=False ):
        """
        Load the USFM Bible book from a file.
        """

        def processLineFix( marker, text ):
            """ Does character fixes on a specific line and moves footnotes and cross-references out of the main text. """
            adjText = text

            # Fix up quote marks
            if '<' in adjText or '>' in adjText:
                if not self.givenAngleBracketWarning: # Just give the warning once
                    fixErrors.append( _("{} {}:{} Found angle brackets in {}: {}").format( bookReferenceCode, c, v, marker, text ) )
                    if logErrors: logging.warning( _("Found angle bracket(s) after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, text ) )
                    self.givenAngleBracketWarning = True
                adjText = adjText.replace('<<','“').replace('>>','”').replace('<','‘').replace('>','’') # Replace angle brackets with the proper opening and close quote marks
            if '"' in adjText:
                if not self.givenDoubleQuoteWarning: # Just give the warning once
                    fixErrors.append( _("{} {}:{} Found \" in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                    if logErrors: logging.warning( _("Found \" after {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                    self.givenDoubleQuoteWarning = True
                adjText = adjText.replace(' "',' “').replace('"','”') # Try to replace double-quote marks with the proper opening and closing quote marks

            # Move footnotes and crossreferences out to extras
            extras = []
            ixFN = adjText.find( '\\f ' )
            ixXR = adjText.find( '\\x ' )
            while ixFN!=-1 or ixXR!=-1: # We have one or the other
                if ixFN!=-1 and ixXR!=-1: # We have both
                    assert( ixFN != ixXR )
                    ix1 = min( ixFN, ixXR ) # Process the first one
                else: ix1 = ixFN if ixXR==-1 else ixXR
                if ix1 == ixFN:
                    ix2 = adjText.find( '\\f*' )
                    thisOne, this1 = "footnote", "fn"
                else:
                    assert( ix1 == ixXR )
                    ix2 = adjText.find( '\\x*' )
                    thisOne, this1 = "cross-reference", "xr"
                if ix2 == -1: # no closing marker
                    fixErrors.append( _("{} {}:{} Found unmatched {} open in {}: {}").format( bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    if logErrors: logging.error( _("Found unmatched {} open after {} {}:{} in {}: {}").format( thisOne, bookReferenceCode, c, v, marker, adjText ) )
                    ix2 = 99999 # Go to the end
                elif ix2 < ix1: # closing marker is before opening marker
                    fixErrors.append( _("{} {}:{} Found unmatched {} in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                    if logErrors: logging.error( _("Found unmatched {} after {} {}:{} in {}: {}").format( thisOne, bookReferenceCode, c, v, thisOne, marker, adjText ) )
                    ix1, ix2 = ix2, ix1 # swap them then
                # Remove the footnote or xref
                #print( "Found {} at {} {} in '{}'".format( thisOne, ix1, ix2, adjText ) )
                note = adjText[ix1+3:ix2] # Get the note text (without the beginning and end markers)
                adjText = adjText[:ix1] + adjText[ix2+3:] # Remove the note completely from the text
                extras.append( (this1,ix1,note,) ) # Saves a 3-tuple: type ('fn' or 'xr'), index into the main text line, the actual fn or xref contents
                ixFN = adjText.find( '\\f ' )
                ixXR = adjText.find( '\\x ' )
            #if extras: print( "Fix gave '{}' and '{}'".format( adjText, extras ) )
            #if len(extras)>1: print( "Mutiple fix gave '{}' and '{}'".format( adjText, extras ) )

            if '\\f' in adjText or '\\x' in adjText:
                fixErrors.append( _("{} {}:{} Unable to properly process footnotes and cross-references in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )
                if logErrors: logging.error( _("Unable to properly process footnotes and cross-references {} {}:{} in {}: {}").format( bookReferenceCode, c, v, marker, adjText ) )

            if '<' in adjText or '>' in adjText or '"' in adjText: print( marker, adjText ); halt
            return marker, adjText, extras
        # end of processLineFix


        def processLine( marker, text ):
            """ Process one USFM line. """
            assert( marker and isinstance( marker, str ) )

            # Convert markers like s to standard markers like s1
            adjMarker = self.USFMMarkers.toStandardMarker( marker )
            #if adjMarker!=marker: print( marker, "->", adjMarker )

            if text:
                # Check markers inside the lines
                markerList = self.USFMMarkers.getMarkerListFromText( text )
                #if markerList: print( "\nText {} {}:{} = {}:'{}'".format(self.bookReferenceCode, c, v, marker, text)); print( markerList )
                closed = True
                for insideMarker, nextSignificantChar, iMIndex in markerList: # check character markers
                    if self.USFMMarkers.isInternalMarker(insideMarker) and closed==True and nextSignificantChar in ('',' '): closed = insideMarker
                    if closed!=True and nextSignificantChar=='*' and insideMarker==closed: closed = True
                if closed!=True:
                    loadErrors.append( _("{} {}:{} Marker '{}' doesn't appear to be closed in {}: {}").format( self.bookReferenceCode, c, v, closed, marker, text ) )
                    if logErrors: logging.warning( _("Marker '{}' doesn't appear to be closed after {} {}:{} in {}: {}").format( closed, self.bookReferenceCode, c, v, marker, text ) )
                ix = 0
                for insideMarker, nextSignificantChar, iMIndex in markerList: # check paragraph markers
                    if self.USFMMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            loadErrors.append( _("{} {}:{} Marker '{}' shouldn't appear within line in {}: '{}'").format( self.bookReferenceCode, c, v, insideMarker, marker, text ) )
                            if logErrors: logging.error( _("Marker '{}' shouldn't appear within line after {} {}:{} in {}: '{}'").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) ) # Only log the first error in the line
                        #thisText = text[ix:iMIndex]
                        thisText = text[ix:iMIndex].rstrip()
                        #print( "got {}:'{}'".format( adjMarker, thisText ) )
                        self.lines.append( processLineFix( adjMarker, thisText ) )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        adjMarker = self.USFMMarkers.toStandardMarker( insideMarker ) # setup for the next line
                if ix != 0: # We must have separated multiple lines
                    #print( "Here '{}' {} {}".format( text, ix, ix+len(insideMarker)+1 ) )
                    text = text[ix:]
                    #print( "leaving {}:'{}'".format( adjMarker, text ) )

            # Save the corrected data
            self.lines.append( processLineFix( adjMarker, text ) )
        # end of processLine


        import SFMFile

        if Globals.verbosityLevel > 2: print( "  " + _("Loading {}...").format( filename ) )
        self.bookReferenceCode = bookReferenceCode
        self.isOneChapterBook = bookReferenceCode in self.BibleBooksCodes.getSingleChapterBooksList()
        self.sourceFolder = folder
        self.sourceFilename = filename
        self.sourceFilepath = os.path.join( folder, filename )
        originalBook = SFMFile.SFMLines()
        originalBook.read( self.sourceFilepath, encoding=encoding )

        # Do some important cleaning up before we save the data
        c, v = '0', '0'
        lastMarker, lastText = '', ''
        loadErrors, fixErrors = [], []
        for marker,text in originalBook.lines: # Always process a line behind in case we have to combine lines
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if self.USFMMarkers.isNewlineMarker( marker ):
                if lastMarker: processLine( lastMarker, lastText )
                lastMarker, lastText = marker, text
            else: # the line begins with an internal marker -- append it to the previous line
                loadErrors.append( _("{} {}:{} Found '{}' internal marker at beginning of line with text: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                if logErrors: logging.error( _("Found '{}' internal marker after {} {}:{} at beginning of line with text: {}").format( marker, self.bookReferenceCode, c, v, text ) )
                #lastText += '' if lastText.endswith(' ') else ' ' # Not always good to add a space, but it's their fault!
                lastText +=  '\\' + marker + ' ' + text
                #print( "{} {} {} Now have {}:'{}'".format( self.bookReferenceCode, c, v, lastMarker, lastText ) )
        if lastMarker: processLine( lastMarker, lastText ) # Process the final line

        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        if fixErrors: self.errorDictionary['Fix Text Errors'] = fixErrors
    # end of load


    def validateUSFM( self, logErrors=False ):
        """
        Validate the loaded book.
        """
        assert( self.lines )
        validationErrors = []

        c, v = '0', '0'
        for j, (marker,text,extras) in enumerate(self.lines):
            #print( marker, text[:40] )

            # Keep track of where we are for more helpful error messages
            if marker == 'c':
                if text: c = text.split()[0]
                else:
                    validationErrors.append( _("{} {}:{} Missing chapter number").format( self.bookReferenceCode, c, v ) )
                    if logErrors: logging.error( _("Missing chapter number after {} {}:{}").format( self.bookReferenceCode, c, v ) )
                v = '0'
            if marker == 'v':
                if text: v = text.split()[0]
                else:
                    validationErrors.append( _("{} {}:{} Missing verse number").format( self.bookReferenceCode, c, v ) )
                    if logErrors: logging.error( _("Missing verse number after {} {}:{}").format( self.bookReferenceCode, c, v ) )

            # Do a rough check of the SFMs
            if marker=='id' and j!=0:
                validationErrors.append( _("{} {}:{} Marker 'id' should only appear as the first marker in a book but found on line {} in {}: {}").format( self.bookReferenceCode, c, v, j, marker, text ) )
                if logErrors: logging.error( _("Marker 'id' should only appear as the first marker in a book but found on line {} after {} {}:{} in {}: {}").format( j, self.bookReferenceCode, c, v, marker, text ) )
            if not self.USFMMarkers.isNewlineMarker( marker ):
                validationErrors.append( _("{} {}:{} Unexpected '{}' new line marker in Bible book (Text is '{}')").format( self.bookReferenceCode, c, v, marker, text ) )
                if logErrors: logging.warning( _("Unexpected '{}' paragraph marker in Bible book after {} {}:{} (Text is '{}')").format( marker, self.bookReferenceCode, c, v, text ) )
            markerList = self.USFMMarkers.getMarkerListFromText( text )
            #if markerList: print( "\nText = {}:'{}'".format(marker,text)); print( markerList )
            closed = True
            for insideMarker, nextSignificantChar, iMIndex in markerList: # check character markers
                if self.USFMMarkers.isInternalMarker(insideMarker) and closed==True and nextSignificantChar in ('',' '): closed = insideMarker
                if closed!=True and nextSignificantChar=='*' and insideMarker==closed: closed = True
            if closed!=True:
                validationErrors.append( _("{} {}:{} Marker '{}' doesn't appear to be closed in {}: {}").format( self.bookReferenceCode, c, v, closed, marker, text ) )
                if logErrors: logging.warning( _("Marker '{}' doesn't appear to be closed after {} {}:{} in {}: {}").format( closed, self.bookReferenceCode, c, v, marker, text ) )
            ix = 0
            for insideMarker, nextSignificantChar, iMIndex in markerList: # check newline markers
                if self.USFMMarkers.isNewlineMarker(insideMarker):
                    validationErrors.append( _("{} {}:{} Marker '{}' shouldn't appear within line in {}: {}").format( self.bookReferenceCode, c, v, insideMarker, marker, text ) )
                    if logErrors: logging.error( _("Marker '{}' shouldn't appear within line after {} {}:{} in {}: {}").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) )

        if validationErrors: self.errorDictionary['Validation Errors'] = validationErrors
    # end of validateUSFM


    def getField( self, fieldName ):
        """
        Extract a SFM field from the loaded book.
        """
        assert( fieldName and isinstance( fieldName, str ) )
        assert( self.lines )
        adjFieldName = self.USFMMarkers.toStandardMarker( fieldName )

        for marker,text,extras in self.lines:
            if marker == adjFieldName:
                assert( not extras )
                return text
    # end of getField


    def getBookName( self ):
        """
        Attempts to deduce a bookname from the loaded book.
        Use the English name as a last resort
        """
        from BibleBooksCodes import BibleBooksCodes
        assert( self.lines )

        header = self.getField( 'h' )
        if header is not None and header.isupper(): header = header.title()
        mt1 = self.getField( 'mt1' )
        if mt1 is not None and mt1.isupper(): mt1 = mt1.title()

        if header is not None: bookName = header
        elif mt1 is not None: bookName = mt1
        else: # no helpful fields in file
            bbc = BibleBooksCodes().loadData()
            bookName = bbc.getEnglishName_NR( self.bookReferenceCode )

        if Globals.debugFlag or Globals.verbosityLevel > 3: # Print our level of confidence
            if header is not None and header==mt1: assert( bookName == header ); print( "getBookName: header and main title are both '{}'".format( bookName ) )
            elif header is not None and mt1 is not None: print( "getBookName: header '{}' and main title '{}' are both different so selected '{}'".format( header, mt1, bookName ) )
            elif header is not None or mt1 is not None: print( "getBookName: only have one of header '{}' or main title '{}'".format( header, mt1 ) )
            else: print( "getBookName: no header or main title so used English book name '{}'".format( bookName ) )

        return bookName
    # end of getBookName


    def getVersification( self, logErrors=False ):
        """
        Get the versification of the book into a two lists of (c, v) tuples.
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
        Note that all chapter and verse values are returned as strings not integers.
        """
        assert( self.lines )
        versificationErrors = []

        versification, omittedVerses, combinedVerses, reorderedVerses = [], [], [], []
        chapterText, chapterNumber, lastChapterNumber = '0', 0, 0
        verseText, verseNumberString, lastVerseNumberString = '0', '0', '0'
        for marker,text,extras in self.lines:
            #print( marker, text )
            if marker == 'c':
                if chapterNumber > 0:
                    versification.append( (chapterText, lastVerseNumberString,) )
                chapterText = text.strip()
                if ' ' in chapterText: # Seems that we can have footnotes here :)
                    versificationErrors.append( _("{} {}:{} Unexpected space in USFM chapter number field '{}'").format( self.bookReferenceCode, lastChapterNumber, lastVerseNumberString, chapterText, lastChapterNumber ) )
                    if logErrors: logging.info( _("Unexpected space in USFM chapter number field '{}' after chapter {} of {}").format( chapterText, lastChapterNumber, self.bookReferenceCode ) )
                    chapterText = chapterText.split( None, 1)[0]
                #print( "{} chapter {}".format( self.bookReferenceCode, chapterText ) )
                chapterNumber = int( chapterText)
                if chapterNumber != lastChapterNumber+1:
                    versificationErrors.append( _("{} ({} after {}) USFM chapter numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                    if logErrors: logging.error( _("USFM chapter numbers out of sequence in Bible book {} ({} after {})").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                lastChapterNumber = chapterNumber
                verseText, verseNumberString, lastVerseNumberString = '0', '0', '0'
            elif marker == 'cp':
                versificationErrors.append( _("{} {}:{} Encountered cp field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, text ) )
                if logErrors: logging.warning( _("Encountered cp field {} after {}:{} of {}").format( text, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
            elif marker == 'v':
                if not text:
                    versificationErrors.append( _("{} {} Missing USFM verse number after {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString ) )
                    if logErrors: logging.warning( _("Missing USFM verse number after {} in chapter {} of {}").format( lastVerseNumberString, chapterNumber, self.bookReferenceCode ) )
                    continue
                try:
                    verseText = text.split( None, 1 )[0]
                except:
                    print( "verseText is '{}'".format(verseText) )
                    halt
                doneWarning = False
                for char in 'abcdefghijklmnopqrstuvwxyz[]()\\':
                    if char in verseText:
                        if not doneWarning:
                            versificationErrors.append( _("{} {} Removing letter(s) from USFM verse number {} in Bible book").format( self.bookReferenceCode, chapterText, verseText ) )
                            if logErrors: logging.info( _("Removing letter(s) from USFM verse number {} in Bible book {} {}").format( verseText, self.bookReferenceCode, chapterText ) )
                            doneWarning = True
                        verseText = verseText.replace( char, '' )
                if '-' in verseText or '–' in verseText: # we have a range like 7-9 with hyphen or en-dash
                    versificationErrors.append( _("{} {}:{} Encountered combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    if logErrors: logging.info( _("Encountered combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.replace('–','-').split( '-', 1 ) # Make sure that it's a hyphen then split once
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse range start '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, verseText ) )
                        if logErrors: logging.error( _("Invalid USFM verse range start '{}' in '{}' in Bible book {} {}").format( verseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse range end '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, endVerseNumberString, verseText ) )
                        if logErrors: logging.error( _("Invalid USFM verse range end '{}' in '{}' in Bible book {} {}").format( endVerseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse range out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        if logErrors: logging.error( _("USFM verse range out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                elif ',' in verseText: # we have a range like 7,8
                    versificationErrors.append( _("{} {}:{} Encountered comma combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    if logErrors: logging.info( _("Encountered comma combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.split( ',', 1 )
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse list start '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, verseText ) )
                        if logErrors: logging.error( _("Invalid USFM verse list start '{}' in '{}' in Bible book {} {}").format( verseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse list end '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, endVerseNumberString, verseText ) )
                        if logErrors: logging.error( _("Invalid USFM verse list end '{}' in '{}' in Bible book {} {}").format( endVerseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse list out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        if logErrors: logging.error( _("USFM verse list out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                else: # Should be just a single verse number
                    verseNumberString = verseText
                    endVerseNumberString = verseNumberString
                try:
                    verseNumber = int( verseNumberString )
                except:
                    versificationErrors.append( _("{} {} {} Invalid verse number digits in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString ) )
                    if logErrors: logging.error( _("Invalid verse number digits in Bible book {} {} {}").format( self.bookReferenceCode, chapterText, verseNumberString ) )
                    newString = ''
                    for char in verseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    verseNumber = int(newString) if newString else 999
                try:
                    lastVerseNumber = int( lastVerseNumberString )
                except:
                    newString = ''
                    for char in lastVerseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    lastVerseNumber = int(newString) if newString else 999
                if verseNumber != lastVerseNumber+1:
                    if verseNumber <= lastVerseNumber:
                        versificationErrors.append( _("{} {} ({} after {}) USFM verse numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        if logErrors: logging.warning( _("USFM verse numbers out of sequence in Bible book {} {} ({} after {})").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        reorderedVerses.append( (chapterText, lastVerseNumberString, verseText,) )
                    else: # Must be missing some verse numbers
                        versificationErrors.append( _("{} {} Missing USFM verse number(s) between {} and {} in Bible book").format( self.bookReferenceCode, chapterText, lastVerseNumberString, verseNumberString ) )
                        if logErrors: logging.info( _("Missing USFM verse number(s) between {} and {} in Bible book {} {}").format( lastVerseNumberString, verseNumberString, self.bookReferenceCode, chapterText ) )
                        for number in range( lastVerseNumber+1, verseNumber ):
                            omittedVerses.append( (chapterText, str(number),) )
                lastVerseNumberString = endVerseNumberString
        versification.append( (chapterText, lastVerseNumberString,) ) # Append the verse count for the final chapter
        #if reorderedVerses: print( "Reordered verses in", self.bookReferenceCode, "are:", reorderedVerses )
        if versificationErrors: self.errorDictionary['Versification Errors'] = versificationErrors
        return versification, omittedVerses, combinedVerses, reorderedVerses
    # end of getVersification


    def checkSFMs( self ):
        """Runs a number of checks on the USFM codes in this Bible book."""
        allAvailableNewlineMarkers = self.USFMMarkers.getNewlineMarkersList()

        newlineMarkerCounts, internalMarkerCounts, noteMarkerCounts = OrderedDict(), OrderedDict(), OrderedDict()
        #newlineMarkerCounts['Total'], internalMarkerCounts['Total'], noteMarkerCounts['Total'] = 0, 0, 0 # Put these first in the ordered dict
        newlineMarkerErrors, internalMarkerErrors, noteMarkerErrors = [], [], []
        functionalCounts = {}
        modifiedMarkerList = []
        c, v, section = '0', '0', ''
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                c = text.split()[0]; v = '0'
                functionalCounts['Chapters'] = 1 if 'Chapters' not in functionalCounts else (functionalCounts['Chapters'] + 1)
            elif marker=='v' and text:
                v = text.split()[0]
                functionalCounts['Verses'] = 1 if 'Verses' not in functionalCounts else (functionalCounts['Verses'] + 1)
            # Do other useful functional counts
            elif marker=='p':
                functionalCounts['Paragraphs'] = 1 if 'Paragraphs' not in functionalCounts else (functionalCounts['Paragraphs'] + 1)
            elif marker=='h1':
                functionalCounts['Section Headers'] = 1 if 'Section Headers' not in functionalCounts else (functionalCounts['Section Headers'] + 1)
            elif marker=='r':
                functionalCounts['Section Cross-References'] = 1 if 'Section Cross-References' not in functionalCounts else (functionalCounts['Section Cross-References'] + 1)

            assert( marker in allAvailableNewlineMarkers ) # Should have been checked at load time
            newlineMarkerCounts[marker] = 1 if marker not in newlineMarkerCounts else (newlineMarkerCounts[marker] + 1)

            # Check the progression through the various sections
            newSection = self.USFMMarkers.markerOccursIn( marker )
            if newSection != section: # Check changes into new sections
                #print( section, marker, newSection )
                if section=='' and newSection!='Header': newlineMarkerErrors.append( _("{} {}:{} Missing Header section (went straight to {} section with {} marker)").format( self.bookReferenceCode, c, v, newSection, marker ) )
                elif section!='' and newSection=='Header': newlineMarkerErrors.append( _("{} {}:{} Didn't expect Header section after {} section (with {} marker)").format( self.bookReferenceCode, c, v, section, marker ) )
                if section=='Header' and newSection!='Introduction': newlineMarkerErrors.append( _("{} {}:{} Missing Introduction section (went straight to {} section with {} marker)").format( self.bookReferenceCode, c, v, newSection, marker ) )
                elif section!='Header' and newSection=='Introduction': newlineMarkerErrors.append( _("{} {}:{} Didn't expect Introduction section after {} section (with {} marker)").format( self.bookReferenceCode, c, v, section, marker ) )
                section = newSection

            # Note the newline SFM order -- create a list of markers in order (with duplicates combined, e.g., \v \v -> \v)
            if not modifiedMarkerList or modifiedMarkerList[-1] != marker: modifiedMarkerList.append( marker )

            # Check the internal SFMs
            if '\\' in text:
                #print( text )
                #assert( '\\f ' not in text and '\\f*' not in text and '\\x ' not in text and '\\x*' not in text ) # The contents of these fields should now be in extras (unless there were errors)
                #assert( '\\fr ' not in text and '\\ft' not in text and '\\xo ' not in text and '\\xt' not in text ) # The contents of these fields should now be in extras (unless there were errors)
                internalTextMarkers = []
                ixStart = text.find( '\\' )
                while( ixStart != -1 ):
                    ixSpace = text.find( ' ', ixStart+1 )
                    ixAsterisk = text.find( '*', ixStart+1 )
                    if ixSpace==-1 and ixAsterisk==-1: ixEnd = len(text) - 1
                    elif ixSpace!=-1 and ixAsterisk==-1: ixEnd = ixSpace
                    elif ixSpace==-1 and ixAsterisk!=-1: ixEnd = ixAsterisk+1 # The asterisk is considered part of the marker
                    else: ixEnd = min( ixSpace, ixAsterisk+1 ) # Both were found
                    internalMarker = text[ixStart+1:ixEnd]
                    internalTextMarkers.append( internalMarker )
                    ixStart = text.find( '\\', ixStart+1 )
                #print( "Found", internalTextMarkers )
                hierarchy = []
                for internalMarker in internalTextMarkers: # count the SFMs and check the hierarchy
                    internalMarkerCounts[internalMarker] = 1 if internalMarker not in internalMarkerCounts else (internalMarkerCounts[internalMarker] + 1)
                    if internalMarker and internalMarker[-1] == '*':
                        closedMarkerText = internalMarker[:-1]
                        shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                        if shouldBeClosed == 'N': internalMarkerErrors.append( _("{} {}:{} Marker {} cannot be closed").format( self.bookReferenceCode, c, v, closedMarkerText ) )
                        elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                        elif closedMarkerText in hierarchy: internalMarkerErrors.append( _("{} {}:{} Internal markers appear to overlap: {}").format( self.bookReferenceCode, c, v, internalTextMarkers ) )
                        else: internalMarkerErrors.append( _("{} {}:{} Unexpected internal closing marker: {} in {}").format( self.bookReferenceCode, c, v, internalMarker, internalTextMarkers ) )
                    else: # it's not a closing marker
                        shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( internalMarker )
                        if shouldBeClosed == 'N': continue # N for never
                        else: hierarchy.append( internalMarker ) # but what if it's optional ????????????????????????????????
                if hierarchy: # it should be empty
                    internalMarkerErrors.append( _("{} {}:{} These markers {} appear not to be closed in {}").format( self.bookReferenceCode, c, v, hierarchy, internalTextMarkers ) )

            if extras:
                #print( extras )
                extraMarkers = []
                for extraType, extraIndex, extraText in extras:
                    assert( extraText ) # Shouldn't be blank
                    assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    ( 0 <= extraIndex <= len(text) )
                    assert( extraType in ('fn','xr',) )
                    extraName = 'footnote' if extraType=='fn' else 'cross-reference'
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                    thisExtraMarkers = []
                    if '\\\\' in extraText:
                        noteMarkerErrors.append( _("{} {}:{} doubled backslash characters in  {}: {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )
                        while '\\\\' in extraText: extraText = extraText.replace( '\\\\', '\\' )
                    #if '  ' in extraText:
                    #    noteMarkerErrors.append( _("{} {}:{} doubled space characters in  {}: {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )
                    #    while '  ' in extraText: extraText = extraText.replace( '  ', ' ' )
                    if '\\' in extraText:
                        #print( extraText )
                        assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # These beginning and end markers should already be removed
                        thisExtraMarkers = []
                        ixStart = extraText.find( '\\' )
                        while( ixStart != -1 ):
                            ixSpace = extraText.find( ' ', ixStart+1 )
                            ixAsterisk = extraText.find( '*', ixStart+1 )
                            if ixSpace==-1 and ixAsterisk==-1: ixEnd = len(extraText) - 1
                            elif ixSpace!=-1 and ixAsterisk==-1: ixEnd = ixSpace
                            elif ixSpace==-1 and ixAsterisk!=-1: ixEnd = ixAsterisk+1 # The asterisk is considered part of the marker
                            else: ixEnd = min( ixSpace, ixAsterisk+1 ) # Both were found
                            extraMarker = extraText[ixStart+1:ixEnd]
                            thisExtraMarkers.append( extraMarker )
                            ixStart = extraText.find( '\\', ixStart+1 )
                        #print( "Found", thisExtraMarkers )
                        hierarchy = []
                        for extraMarker in thisExtraMarkers: # count the SFMs and check the hierarchy
                            noteMarkerCounts[extraMarker] = 1 if extraMarker not in noteMarkerCounts else (noteMarkerCounts[extraMarker] + 1)
                            if extraMarker and extraMarker[-1] == '*':
                                closedMarkerText = extraMarker[:-1]
                                shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                                #print( "here with", extraType, extraText, thisExtraMarkers, hierarchy, closedMarkerText, shouldBeClosed )
                                if shouldBeClosed == 'N': noteMarkerErrors.append( _("{} {}:{} Marker {} is not closeable").format( self.bookReferenceCode, c, v, closedMarkerText ) )
                                elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                                elif closedMarkerText in hierarchy: noteMarkerErrors.append( _("{} {}:{} Internal {} markers appear to overlap: {}").format( self.bookReferenceCode, c, v, extraName, thisExtraMarkers ) )
                                else: noteMarkerErrors.append( _("{} {}:{} Unexpected {} closing marker: {} in {}").format( self.bookReferenceCode, c, v, extraName, extraMarker, thisExtraMarkers ) )
                            else: # it's not a closing marker -- for extras, it probably automatically closes the previous marker
                                shouldBeClosed = self.USFMMarkers.markerShouldBeClosed( extraMarker )
                                if shouldBeClosed == 'N': continue # N for never
                                elif hierarchy: # Maybe the previous one is automatically closed by this one
                                    previousMarker = hierarchy[-1]
                                    previousShouldBeClosed = self.USFMMarkers.markerShouldBeClosed( previousMarker )
                                    if previousShouldBeClosed == 'S': # S for sometimes
                                        hierarchy.pop() # That they are not overlapped, but rather that the previous one is automatically closed by this one
                                hierarchy.append( extraMarker )
                        if len(hierarchy)==1 and self.USFMMarkers.markerShouldBeClosed(hierarchy[0])=='S': # Maybe the last marker can be automatically closed
                            hierarchy.pop()
                        if hierarchy: # it should be empty
                            #print( "here with remaining", extraType, extraText, thisExtraMarkers, hierarchy )
                            noteMarkerErrors.append( _("{} {}:{} These {} markers {} appear not to be closed in {}").format( self.bookReferenceCode, c, v, extraName, hierarchy, extraText ) )
                    adjExtraMarkers = thisExtraMarkers
                    for uninterestingMarker in ('it*','it','nd*','nd','sc*','sc','bk*','bk'): # Remove character formatting markers so we can check the footnote/xref hierarchy
                        while uninterestingMarker in adjExtraMarkers: adjExtraMarkers.remove( uninterestingMarker )
                    if adjExtraMarkers not in self.USFMMarkers.getTypicalNoteSets( extraType ):
                        #print( "Got", extraType, extraText, thisExtraMarkers )
                        if thisExtraMarkers: noteMarkerErrors.append( _("{} {}:{} Unusual {} marker set: {} in {}").format( self.bookReferenceCode, c, v, extraName, thisExtraMarkers, extraText ) )
                        else: noteMarkerErrors.append( _("{} {}:{} Missing {} formatting in {}").format( self.bookReferenceCode, c, v, extraName, extraText ) )

                    # Moved to checkNotes
                    #if len(extraText) > 2 and extraText[1] == ' ':
                    #    leaderChar = extraText[0] # Leader character should be followed by a space
                    #    if extraType == 'fn':
                    #        functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                    #        leaderName = "Footnote leader '{}'".format( leaderChar )
                    #        functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                    #    elif extraType == 'xr':
                    #        functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)
                    #        leaderName = "Cross-reference leader '{}'".format( leaderChar )
                    #        functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                    #else: noteMarkerErrors.append( _("{} {}:{} {} seems to be missing a leader character in {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )
                    if extraType == 'fn':
                        functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                    elif extraType == 'xr':
                        functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)


        # Check the relative ordering of newline markers
        #print( "modifiedMarkerList", modifiedMarkerList )
        if modifiedMarkerList[0] != 'id':
            newlineMarkerErrors.append( _("{} First USFM field in file should have been 'id' not '{}'").format( self.bookReferenceCode, modifiedMarkerList[0] ) )
            self.addPriorityError( 100, self.bookReferenceCode, '', '', _("id line not first in file") )
        for otherHeaderMarker in ( 'ide','sts', ):
            if otherHeaderMarker in modifiedMarkerList and modifiedMarkerList.index(otherHeaderMarker) > 8:
                newlineMarkerErrors.append( _("{} {}:{} USFM '{}' field in file should have been earlier in {}...").format( self.bookReferenceCode, c, v, otherHeaderMarker, modifiedMarkerList[:10] ) )
        if 'mt2' in modifiedMarkerList: # Must be before or after a mt1
            ix = modifiedMarkerList.index( 'mt2' )
            if (ix==0 or modifiedMarkerList[ix-1]!='mt1') and (ix==len(modifiedMarkerList)-1 or modifiedMarkerList[ix+1]!='mt1'):
                newlineMarkerErrors.append( _("{} Expected mt2 marker to be next to an mt1 marker in {}...").format( self.bookReferenceCode, modifiedMarkerList[:10] ) )

        if 'SFMs' not in self.errorDictionary: self.errorDictionary['SFMs'] = OrderedDict()
        if newlineMarkerErrors: self.errorDictionary['SFMs']['Newline Marker Errors'] = newlineMarkerErrors
        if internalMarkerErrors: self.errorDictionary['SFMs']['Internal Marker Errors'] = internalMarkerErrors
        if noteMarkerErrors: self.errorDictionary['SFMs']['Footnote and Cross-Reference Marker Errors'] = noteMarkerErrors
        if modifiedMarkerList:
            modifiedMarkerList.insert( 0, '['+self.bookReferenceCode+']' )
            self.errorDictionary['SFMs']['Modified Marker List'] = modifiedMarkerList
        if newlineMarkerCounts:
            total = 0
            for marker in newlineMarkerCounts: total += newlineMarkerCounts[marker]
            self.errorDictionary['SFMs']['All Newline Marker Counts'] = newlineMarkerCounts
            self.errorDictionary['SFMs']['All Newline Marker Counts']['Total'] = total
        if internalMarkerCounts:
            total = 0
            for marker in internalMarkerCounts: total += internalMarkerCounts[marker]
            self.errorDictionary['SFMs']['All Text Internal Marker Counts'] = internalMarkerCounts
            self.errorDictionary['SFMs']['All Text Internal Marker Counts']['Total'] = total
        if noteMarkerCounts:
            total = 0
            for marker in noteMarkerCounts: total += noteMarkerCounts[marker]
            self.errorDictionary['SFMs']['All Footnote and Cross-Reference Internal Marker Counts'] = noteMarkerCounts
            self.errorDictionary['SFMs']['All Footnote and Cross-Reference Internal Marker Counts']['Total'] = total
        if functionalCounts: self.errorDictionary['SFMs']['Functional Marker Counts'] = functionalCounts
    # end of checkSFMs


    def checkCharacters( self ):
        """Runs a number of checks on the characters used."""

        def countCharacters( adjText ):
            """ Counts the characters for the given text (with internal markers already removed). """
            if '  ' in adjText:
                characterErrors.append( _("{} {}:{} Multiple spaces in '{}'").format( self.bookReferenceCode, c, v, adjText ) )
                self.addPriorityError( 7, self.bookReferenceCode, c, v, _("Multiple spaces in text line") )
            if adjText[-1] == ' ':
                characterErrors.append( _("{} {}:{} Trailing space in '{}'").format( self.bookReferenceCode, c, v, adjText ) )
                self.addPriorityError( 5, self.bookReferenceCode, c, v, _("Trailing space in text line") )
            if self.USFMMarkers.isPrinted( marker ): # Only do character counts on lines that will be printed
                for char in adjText:
                    lcChar = char.lower()
                    characterCounts[char] = 1 if char not in characterCounts else characterCounts[char] + 1
                    if char==' ' or char =='-' or char.isalpha():
                        letterCounts[lcChar] = 1 if lcChar not in letterCounts else letterCounts[lcChar] + 1
                    elif not char.isalnum(): # Assume it's punctuation
                        punctuationCounts[char] = 1 if char not in punctuationCounts else punctuationCounts[char] + 1
                        if char not in allWordPunctChars:
                            characterErrors.append( _("{} {}:{} Invalid '{}' word-building character").format( self.bookReferenceCode, c, v, char ) )
                            self.addPriorityError( 10, self.bookReferenceCode, c, v, _("Invalid '{}' word-building character").format( char ) )
                for char in leadingWordPunctChars:
                    if adjText[-1]==char or char+' ' in adjText:
                            characterErrors.append( _("{} {}:{} Misplaced '{}' word leading character").format( self.bookReferenceCode, c, v, char ) )
                            self.addPriorityError( 21, self.bookReferenceCode, c, v, _("Misplaced '{}' word leading character").format( char ) )
                for char in trailingWordPunctChars:
                    if adjText[0]==char or ' '+char in adjText:
                            characterErrors.append( _("{} {}:{} Misplaced '{}' word trailing character").format( self.bookReferenceCode, c, v, char ) )
                            self.addPriorityError( 20, self.bookReferenceCode, c, v, _("Misplaced '{}' word trailing character").format( char ) )
        # end of countCharacters

        characterCounts, letterCounts, punctuationCounts = {}, {}, {} # We don't care about the order in which they appeared
        characterErrors = []
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            adjText = text
            internalSFMsToRemove = ('\\bk*','\\bk','\\it*','\\it','\\wd*','\\wd') # List longest first
            for internalMarker in internalSFMsToRemove: adjText = adjText.replace( internalMarker, '' )
            if adjText: countCharacters( adjText )

            for extraType, extraIndex, extraText in extras: # Now process the characters in the notes
                assert( extraText ) # Shouldn't be blank
                assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                ( 0 <= extraIndex <= len(text) )
                assert( extraType in ('fn','xr',) )
                assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                cleanText = extraText
                for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    cleanText = cleanText.replace( sign, '' )
                for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',) + internalSFMsToRemove:
                    cleanText = cleanText.replace( marker, '' )
                if cleanText: countCharacters( cleanText )

        # Add up the totals
        if (characterCounts or letterCounts or punctuationCounts) and 'Characters' not in self.errorDictionary: self.errorDictionary['Characters'] = OrderedDict()
        if characterCounts:
            total = 0
            for character in characterCounts: total += characterCounts[character]
            self.errorDictionary['Characters']['All Character Counts'] = characterCounts
            self.errorDictionary['Characters']['All Character Counts']['Total'] = total
        if letterCounts:
            total = 0
            for character in letterCounts: total += letterCounts[character]
            self.errorDictionary['Characters']['Letter Counts'] = letterCounts
            self.errorDictionary['Characters']['Letter Counts']['Total'] = total
        if punctuationCounts:
            total = 0
            for character in punctuationCounts: total += punctuationCounts[character]
            self.errorDictionary['Characters']['Punctuation Counts'] = punctuationCounts
            self.errorDictionary['Characters']['Punctuation Counts']['Total'] = total
    # end of checkCharacters


    def checkWords( self ):
        """Runs a number of checks on the words used."""

        def countWords( marker, segment, lastWordTuple=None ):
            """Breaks the segment into words and counts them.
                Also checks for repeated words.
                If lastWordTuple is given, checks for words repeated across segments (and returns the new value).
            """

            def stripWordPunctuation( word ):
                """Removes leading and trailing punctuation from a word.
                    Returns the "clean" word."""
                while word and word[0] in leadingWordPunctChars:
                    word = word[1:] # Remove leading punctuation
                while word and word[-1] in trailingWordPunctChars:
                    word = word[:-1] # Remove trailing punctuation
                return word
            # end of stripWordPunctuation

            allowedWordPunctuation = '-'
            internalSFMsToRemove = ('\\bk*','\\bk','\\it*','\\it','\\wd*','\\wd') # List longest first

            words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            if lastWordTuple is None: ourLastWord, ourLastRawWord = '', '' # No need to check words repeated across segment boundaries
            else: # Check in case a word has been repeated (e.g., at the end of one verse and then again at the beginning of the next verse)
                assert( isinstance( lastWordTuple, tuple ) )
                assert( len(lastWordTuple) == 2)
                ourLastWord, ourLastRawWord = lastWordTuple
            for j,rawWord in enumerate(words):
                if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                word = rawWord
                for internalMarker in internalSFMsToRemove: word = word.replace( internalMarker, '' )
                word = stripWordPunctuation( word )
                if word and not word[0].isalnum():
                    wordErrors.append( _("{} {}:{} Have unexpected character starting word '{}'").format( self.bookReferenceCode, c, v, word ) )
                    word = word[1:]
                if word: # There's still some characters remaining after all that stripping
                    if Globals.verbosityLevel > 3: # why???
                        for k,char in enumerate(word):
                            if not char.isalnum() and (k==0 or k==len(word)-1 or char not in allowedWordPunctuation):
                                wordErrors.append( _("{} {}:{} Have unexpected '{}' in word '{}'").format( self.bookReferenceCode, c, v, char, word ) )
                    lcWord = word.lower()
                    isAReferenceOrNumber = True
                    for char in word:
                        if not char.isdigit() and char!=':' and char!='-' and char!=',': isAReferenceOrNumber = False; break
                    if not isAReferenceOrNumber:
                        wordCounts[word] = 1 if word not in wordCounts else wordCounts[word] + 1
                        caseInsensitiveWordCounts[lcWord] = 1 if lcWord not in caseInsensitiveWordCounts else caseInsensitiveWordCounts[lcWord] + 1
                    #else: print( "excluded reference or number", word )

                    # Check for repeated words (case insensitive comparison)
                    if lcWord==ourLastWord.lower(): # Have a repeated word (might be across sentences)
                        repeatedWordErrors.append( _("{} {}:{} Have possible repeated word with {} {}").format( self.bookReferenceCode, c, v, ourLastRawWord, rawWord ) )
                    ourLastWord, ourLastRawWord = word, rawWord
            return ourLastWord, ourLastRawWord
        # end of countWords


        # Count all the words
        wordCounts, caseInsensitiveWordCounts = {}, {}
        wordErrors, repeatedWordErrors = [], []
        lastTextWordTuple = ('','')
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if text and self.USFMMarkers.isPrinted(marker): # process this main text
                lastTextWordTuple = countWords( marker, text, lastTextWordTuple )

            for extraType, extraIndex, extraText in extras: # do any footnotes and cross-references
                assert( extraText ) # Shouldn't be blank
                assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                ( 0 <= extraIndex <= len(text) )
                assert( extraType in ('fn','xr',) )
                assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                cleanText = extraText
                for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    cleanText = cleanText.replace( sign, '' )
                for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                    cleanText = cleanText.replace( marker, '' )
                countWords( extraType, cleanText )

        # Add up the totals
        if (wordErrors or wordCounts or caseInsensitiveWordCounts) and 'Words' not in self.errorDictionary: self.errorDictionary['Words'] = {} # Don't think it needs to be OrderedDict()
        if wordErrors: self.errorDictionary['Words']['Possible Word Errors'] = wordErrors
        if wordCounts:
            total = 0
            for word in wordCounts: total += wordCounts[word]
            self.errorDictionary['Words']['All Word Counts'] = wordCounts
            self.errorDictionary['Words']['All Word Counts']['--Total--'] = total
        if caseInsensitiveWordCounts:
            total = 0
            for word in caseInsensitiveWordCounts: total += caseInsensitiveWordCounts[word]
            self.errorDictionary['Words']['Case Insensitive Word Counts'] = caseInsensitiveWordCounts
            self.errorDictionary['Words']['Case Insensitive Word Counts']['--Total--'] = total
    # end of checkWords


    def checkHeadings( self ):
        """Runs a number of checks on headings and section cross-references."""
        titleList, headingList, sectionReferenceList, headingErrors = [], [], [], []
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if marker.startswith('mt'):
                titleList.append( "{} {}:{} Main Title {}: '{}'".format( self.bookReferenceCode, c, v, marker[2:], text ) )
                if not text:
                    headingErrors.append( _("{} {}:{} Missing title text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 59, self.bookReferenceCode, c, v, _("Missing title text") )
                elif text[-1]=='.':
                    headingErrors.append( _("{} {}:{} {} title ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 69, self.bookReferenceCode, c, v, _("Title ends with a period") )
            elif marker in ('s1','s2','s3','s4',):
                if marker=='s1': headingList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: headingList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not text:
                    headingErrors.append( _("{} {}:{} Missing heading text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 58, self.bookReferenceCode, c, v, _("Missing heading text") )
                elif text[-1]=='.':
                    headingErrors.append( _("{} {}:{} {} heading ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 68, self.bookReferenceCode, c, v, _("Heading ends with a period") )
            elif marker=='r':
                sectionReferenceList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                if not text:
                    headingErrors.append( _("{} {}:{} Missing section cross-reference text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 57, self.bookReferenceCode, c, v, _("Missing section cross-reference text") )
                elif text[0]!='(' or text[-1]!=')':
                    headingErrors.append( _("{} {}:{} Section cross-reference not in parenthesis: {}").format( self.bookReferenceCode, c, v, text ) )
                    self.addPriorityError( 67, self.bookReferenceCode, c, v, _("Section cross-reference not in parenthesis") )

        if (headingErrors or titleList or headingList or sectionReferenceList) and 'Headings' not in self.errorDictionary: self.errorDictionary['Headings'] = {} # Don't think it needs to be OrderedDict()
        if headingErrors: self.errorDictionary['Headings']['Possible Heading Errors'] = headingErrors
        if titleList: self.errorDictionary['Headings']['Title Lines'] = titleList
        if headingList: self.errorDictionary['Headings']['Section Heading Lines'] = headingList
        if sectionReferenceList: self.errorDictionary['Headings']['Section Cross-reference Lines'] = sectionReferenceList
    # end of checkHeadings


    def checkNotes( self ):
        """Runs a number of checks on footnotes and cross-references."""
        footnoteList, xrefList = [], []
        footnoteLeaderList, xrefLeaderList, CVSeparatorList = [], [], []
        footnoteErrors, xrefErrors, noteMarkerErrors = [], [], []
        leaderCounts = {}
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            for extraType, extraIndex, extraText in extras: # do any footnotes and cross-references
                assert( extraText ) # Shouldn't be blank
                assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                ( 0 <= extraIndex <= len(text) )
                assert( extraType in ('fn','xr',) )
                assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras

                # Get a copy of the note text without any formatting
                cleanText = extraText
                for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    cleanText = cleanText.replace( sign, '' )
                for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                    cleanText = cleanText.replace( marker, '' )

                # Get a list of markers and their contents
                status, myString, lastCode, lastString, extraList = 0, '', '', '', []
                #print( extraText )
                for char in extraText.replace('\\it','__IT__').replace('\\nd','__ND__'): # Change character formatting
                    if status==0: # waiting for leader char
                        if char==' ' and myString:
                            extraList.append( ('leader',myString,) )
                            status, myString = 1, ''
                        else: myString += char
                    elif status==1: # waiting for a backslash code
                        assert( not lastCode )
                        if char=='\\':
                            if myString and myString!=' ':
                                #print( "Something funny in", extraText, extraList, myString ) # Perhaps a fv field embedded in another field???
                                #assert( len(extraList)>=2 and extraList[-2][1] == '' ) # If so, the second to last field is often blank
                                extraList.append( ('',myString.rstrip(),) ) # Handle it by listing a blank field
                            status, myString = 2, ''
                        else: myString += char
                    elif status==2: # getting a backslash code
                        if char==' ' and myString and not lastCode:
                            lastCode = myString
                            status, myString = 3, ''
                        #elif char=='*' and lastCode and lastString and myString==lastCode: # closed a marker
                        #    extraList.append( (lastCode,lastString,) )
                        else: myString += char
                    elif status==3: # getting a backslash code entry text
                        if char=='\\' and lastCode and myString: # getting the next backslash code
                            extraList.append( (lastCode,myString.rstrip(),) )
                            status, myString = 4, ''
                        elif char=='\\' and lastCode and not myString: # Getting another (embedded?) backslash code instead
                            #print( "here", lastCode, extraList, extraText )
                            extraList.append( (lastCode,'',) )
                            status, myString, lastCode = 4, '', ''
                        else: myString += char
                    elif status==4: # getting the backslash closing code or the next code
                        if char=='*':
                            if myString==lastCode: # closed the last one
                                status, myString, lastCode = 1, '', ''
                            else:
                                print( "error with", lastCode, extraList, myString ); halt
                        elif char==' ' and myString:
                            lastCode = myString
                            status, myString = 3, ''
                        else: myString += char
                    else: raise KeyError
                if lastCode and myString: extraList.append( (lastCode,myString.rstrip(),) ) # Append the final part of the note
                #if len(extraList)<3 or '\\ft \\fq' in extraText:                
                #print( "extraList", extraList, "'"+extraText+"'" )
                
                # List all of the similar types of notes
                #   plus check which ones end with a period
                extract = (extraText[:70] + '...' + extraText[-5:]) if len(extraText)>80 else extraText
                line = "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, extract )
                if extraType == 'fn':
                    footnoteList.append( line )
                    if not cleanText.endswith('.') and not cleanText.endswith('.)') and not cleanText.endswith('.”'):
                        footnoteErrors.append( _("{} {}:{} Footnote seems to be missing a final period: '{}'").format( self.bookReferenceCode, c, v, extraText ) )
                        self.addPriorityError( 32, self.bookReferenceCode, c, v, _("Missing period at end of footnote") )
                elif extraType == 'xr':
                    xrefList.append( line )
                    if not cleanText.endswith('.') and not cleanText.endswith('.)') and not cleanText.endswith('.”'):
                        xrefErrors.append( _("{} {}:{} Cross-reference seems to be missing a final period: '{}'").format( self.bookReferenceCode, c, v, extraText ) )
                        self.addPriorityError( 31, self.bookReferenceCode, c, v, _("Missing period at end of cross-reference") )

                # Check leader characters
                leader = ''
                if len(extraText) > 2 and extraText[1] == ' ':
                    leader = extraText[0] # Leader character should be followed by a space
                elif len(extraText) > 3 and extraText[2] == ' ':
                    leader = extraText[:2] # Leader character should be followed by a space
                if leader:
                    if extraType == 'fn':
                        leaderCounts['Footnotes'] = 1 if 'Footnotes' not in leaderCounts else (leaderCounts['Footnotes'] + 1)
                        leaderName = "Footnote leader '{}'".format( leader )
                        leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                        if leader not in footnoteLeaderList: footnoteLeaderList.append( leader )
                    elif extraType == 'xr':
                        leaderCounts['Cross-References'] = 1 if 'Cross-References' not in leaderCounts else (leaderCounts['Cross-References'] + 1)
                        leaderName = "Cross-reference leader '{}'".format( leader )
                        leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                        if leader not in xrefLeaderList: xrefLeaderList.append( leader )
                else: noteMarkerErrors.append( _("{} {}:{} {} seems to be missing a leader character in {}").format( self.bookReferenceCode, c, v, extraType, extraText ) )

                # Find, count and check CVSeparators
                #  and also check that the references match
                fnCVSeparator, xrCVSeparator, fnTrailer, xfTrailer = '', '', '', ''
                for noteMarker,noteText in extraList:
                    if noteMarker=='fr':
                        for j,char in enumerate(noteText):
                            if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                fnCVSeparator = char
                                leaderName = "Footnote CV separator '{}'".format( char )
                                leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                if char not in CVSeparatorList: CVSeparatorList.append( char )
                                break
                        if not noteText[-1].isdigit(): fnTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                        CV1 = v if self.isOneChapterBook else (c + fnCVSeparator + v) # Make up our own reference string
                        CV2 = CV1 + fnTrailer # Make up our own reference string
                        if CV2 != noteText:
                            if CV1 not in noteText:
                                #print( 'fn', CV1, noteText )
                                footnoteErrors.append( _("{} {}:{} Footnote anchor reference seems not to match: '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                                self.addPriorityError( 42, self.bookReferenceCode, c, v, _("Footnote anchor reference mismatch") )
                            else: footnoteErrors.append( _("{} {}:{} Footnote anchor reference possibly does not match: '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                        break # Only process the first fr field
                    elif noteMarker=='xo':
                        for j,char in enumerate(noteText):
                            if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                xrCVSeparator = char
                                leaderName = "Cross-reference CV separator '{}'".format( char )
                                leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                if char not in CVSeparatorList: CVSeparatorList.append( char )
                                break
                        if not noteText[-1].isdigit(): xrTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                        CV1 = v if self.isOneChapterBook else (c + xrCVSeparator + v) # Make up our own reference string
                        CV2 = CV1 + xrTrailer # Make up our own reference string
                        if CV2 != noteText:
                            if CV1 not in noteText:
                                #print( 'xr', CV1, noteText )
                                xrefErrors.append( _("{} {}:{} Cross-reference anchor reference seems not to match: '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                                self.addPriorityError( 41, self.bookReferenceCode, c, v, _("Cross-reference anchor reference mismatch") )
                            else: xrefErrors.append( _("{} {}:{} Cross-reference anchor reference possibly does not match: '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                        break # Only process the first xo field
                                
                # much more yet to be written ................

        if (footnoteErrors or xrefErrors or noteMarkerErrors or footnoteList or xrefList or leaderCounts) and 'Notes' not in self.errorDictionary:
            self.errorDictionary['Notes'] = {} # Don't think it needs to be OrderedDict()
        if footnoteErrors: self.errorDictionary['Notes']['Footnote Errors'] = footnoteErrors
        if xrefErrors: self.errorDictionary['Notes']['Cross-reference Errors'] = xrefErrors
        if noteMarkerErrors: self.errorDictionary['Notes']['Note Marker Errors'] = noteMarkerErrors
        if footnoteList: self.errorDictionary['Notes']['Footnote Lines'] = footnoteList
        if xrefList: self.errorDictionary['Notes']['Cross-reference Lines'] = xrefList
        if leaderCounts:
            self.errorDictionary['Notes']['Leader Counts'] = leaderCounts
            if len(footnoteLeaderList) > 1: self.addPriorityError( 26, self.bookReferenceCode, '-', '-', _("Mutiple different footnote leader characters: {}").format( footnoteLeaderList ) )
            if len(xrefLeaderList) > 1: self.addPriorityError( 25, self.bookReferenceCode, '-', '-', _("Mutiple different cross-reference leader characters: {}").format( xrefLeaderList ) )
            if len(CVSeparatorList) > 1: self.addPriorityError( 27, self.bookReferenceCode, '-', '-', _("Mutiple different chapter/verse separator characters: {}").format( CVSeparatorList ) )
    # end of checkNotes


    def checkIntroduction( self ):
        """Runs a number of checks on introductory parts."""
        mainTitleList, headingList, titleList, outlineList, introductionErrors = [], [], [], [], []
        c, v = '0', '0'
        for marker,text,extras in self.lines:
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if marker in ('imt1','imt2','imt3','imt4',):
                if marker=='imt1': mainTitleList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: mainTitleList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not text:
                    introductionErrors.append( _("{} {}:{} Missing heading text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 39, self.bookReferenceCode, c, v, _("Missing heading text") )
                elif text[-1]=='.':
                    introductionErrors.append( _("{} {}:{} {} heading ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 49, self.bookReferenceCode, c, v, _("Heading ends with a period") )
            elif marker in ('is1','is2','is3','is4',):
                if marker=='is1': headingList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: headingList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not text:
                    introductionErrors.append( _("{} {}:{} Missing heading text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 39, self.bookReferenceCode, c, v, _("Missing heading text") )
                elif text[-1]=='.':
                    introductionErrors.append( _("{} {}:{} {} heading ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 49, self.bookReferenceCode, c, v, _("Heading ends with a period") )
            elif marker=='iot':
                titleList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                if not text:
                    introductionErrors.append( _("{} {}:{} Missing outline title text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 38, self.bookReferenceCode, c, v, _("Missing outline title text") )
                elif text[-1]=='.':
                    introductionErrors.append( _("{} {}:{} {} heading ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 48, self.bookReferenceCode, c, v, _("Heading ends with a period") )
            elif marker in ('io1','io2','io3','io4',):
                if marker=='io1': outlineList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: outlineList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not text:
                    introductionErrors.append( _("{} {}:{} Missing outline text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 37, self.bookReferenceCode, c, v, _("Missing outline text") )
                elif text[-1]=='.':
                    introductionErrors.append( _("{} {}:{} {} outline entry ends with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 47, self.bookReferenceCode, c, v, _("Outline entry ends with a period") )
            elif marker in ('ip','ipi','im','imi',):
                if not text:
                    introductionErrors.append( _("{} {}:{} Missing introduction text for marker {}").format( self.bookReferenceCode, c, v, marker ) )
                    self.addPriorityError( 36, self.bookReferenceCode, c, v, _("Missing introduction text") )
                elif not text.endswith('.') and not text.endswith('.)'):
                    introductionErrors.append( _("{} {}:{} {} introduction text does not end with a period: {}").format( self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 46, self.bookReferenceCode, c, v, _("Introduction text ends without a period") )

        if (introductionErrors or mainTitleList or headingList or titleList or outlineList) and 'Introduction' not in self.errorDictionary:
            self.errorDictionary['Introduction'] = {} # Don't think it needs to be OrderedDict()
        if introductionErrors: self.errorDictionary['Introduction']['Possible Introduction Errors'] = introductionErrors
        if mainTitleList: self.errorDictionary['Introduction']['Main Title Lines'] = mainTitleList
        if headingList: self.errorDictionary['Introduction']['Section Heading Lines'] = headingList
        if titleList: self.errorDictionary['Introduction']['Outline Title Lines'] = titleList
        if outlineList: self.errorDictionary['Introduction']['Outline Entry Lines'] = outlineList
    # end of checkIntroduction


    def check( self ):
        """Runs a number of checks on the book and returns the error dictionary."""
        self.getVersification() # This checks CV ordering, etc.
        self.checkSFMs()
        self.checkCharacters()
        self.checkWords()
        self.checkHeadings()
        self.checkNotes() # footnotes and cross-references
        self.checkIntroduction()
    # end of check


    def getErrors( self ):
        """Returns the error dictionary."""
        if 'Priority Errors' in self.errorDictionary and not self.errorDictionary['Priority Errors']:
            self.errorDictionary.pop( 'Priority Errors' ) # Remove empty dictionary entry if unused
        return self.errorDictionary
# end of class USFMBibleBook


def main():
    """
    Demonstrate reading and processing some Bible databases.
    """
    import USFMFilenames

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    logErrors = False

    name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Data/Matigsalug/Scripture/MBTV/" # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        if Globals.verbosityLevel > 1: print( _("Loading {} from {}...").format( name, testFolder ) )
        fileList = USFMFilenames.USFMFilenames( testFolder ).getActualFilenames()
        for bookReferenceCode,filename in fileList:
            print( _("Loading {} from {}...").format( bookReferenceCode, filename ) )
            UBB = USFMBibleBook()
            UBB.load( bookReferenceCode, testFolder, filename, encoding, logErrors )
            print( "  ID is '{}'".format( UBB.getField( 'id' ) ) )
            print( "  Header is '{}'".format( UBB.getField( 'h' ) ) )
            print( "  Main titles are '{}' and '{}'".format( UBB.getField( 'mt1' ), UBB.getField( 'mt2' ) ) )
            print( UBB )
            UBB.validateUSFM()
            result = UBB.getVersification ()
            #print( result )
            UBB.check()
            UBErrors = UBB.getErrors()
            #print( UBErrors )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    main()
## End of USFMBibleBook.py
