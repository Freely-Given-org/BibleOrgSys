#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBibleBook.py
#   Last modified: 2013-12-13 by RJH (also update ProgVersion below)
#
# Module handling the internal markers for individual Bible books
#
# Copyright (C) 2010-2013 Robert Hunt
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
Module for defining and manipulating Bible books in our internal USFM-based 'lines' format.

The calling class needs to call this base class __init__ routine and also set:
    self.objectTypeString (with "OSIS", "USFM", "USX" or "XML")
    self.objectNameString (with a description of the type of BibleBook object)
It also needs to provide a "load" routine that sets one or more of:
    self.sourceFolder
    self.sourceFilename
    self.sourceFilepath = os.path.join( sourceFolder, sourceFilename )
and then calls
    self.appendLine (in order to fill self._rawLines)
"""

ProgName = "Internal Bible book handler"
ProgVersion = "0.54"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry, InternalBibleIndex, InternalBibleExtra, InternalBibleExtraList
from BibleReferences import BibleAnchorReference


# Define allowed punctuation
leadingWordPunctChars = """“«"‘‹'([{<"""
medialWordPunctChars = '-'
dashes = '—–' # em-dash and en-dash
trailingWordPunctChars = """,.”»"’›'?)!;:]}>"""
allWordPunctChars = leadingWordPunctChars + medialWordPunctChars + dashes + trailingWordPunctChars


PSEUDO_USFM_MARKERS = ( 'c~', 'c#', 'v-', 'v+', 'v~', 'vw', 'g', 'p~', )
"""
    c~  anything after the chapter number on a \c line
    c#  the chapter number (duplicated) in the correct position to be printed -- can be ignored for exporting
    v-  ???
    v+  ???
    v~  verse text -- anything after the verse number on a \v line
            or anything on a \p or \q line
    vw  ???
    g   ???
    p~  verse text -- anything that was on a paragraph line (e.g., \p \q, etc.)
"""
PSEUDO_OSIS_MARKERS = ( 'pp+', )
NON_USFM_MARKERS = PSEUDO_USFM_MARKERS + PSEUDO_OSIS_MARKERS


MAX_NONCRITICAL_ERRORS_PER_BOOK = 5



class InternalBibleBook:
    """
    Class to create and manipulate a single internal Bible file / book.
    The load routine (which populates self._rawLines) by calling appendLine must be provided.
    """

    def __init__( self, name, BBB ):
        """
        Create the USFM Bible book object.

        Parameters are:
            name: version name
            BBB: book reference code
        """
        #print( "InternalBibleBook.__init__( {} )".format( BBB ) )
        self.name, self.bookReferenceCode = name, BBB
        if Globals.debugFlag: assert( self.bookReferenceCode in Globals.BibleBooksCodes )

        self.isSingleChapterBook = Globals.BibleBooksCodes.isSingleChapterBook( self.bookReferenceCode )

        self._rawLines = [] # Contains 2-tuples which contain the actual Bible text -- see appendLine below
        self._processedFlag = self._indexedFlag = False
        self.errorDictionary = OrderedDict()
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
        self.givenAngleBracketWarning = self.givenDoubleQuoteWarning = False

        # Options
        self.checkAddedUnitsFlag = False
        self.checkUSFMSequencesFlag = False
        self.replaceAngleBracketsFlag, self.replaceStraightDoubleQuotesFlag = True, False

        self.badMarkers, self.badMarkerCounts = [], []
        self.pntsCount = 0
    # end of InternalBibleBook.__init__


    def __str__( self ):
        """
        This method returns the string representation of a USFM Bible book object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        if Globals.debugFlag or Globals.verbosityLevel>2: result += ' v' + ProgVersion
        if self.bookReferenceCode: result += ('\n' if result else '') + "  " + self.bookReferenceCode
        try:
            if self.sourceFilepath: result += ('\n' if result else '') + "  " + _("From: ") + self.sourceFilepath
        except AttributeError: pass # Not all Bibles have a separate filepath per book
        if self._processedFlag: result += ('\n' if result else '') + "  " + _("Number of processed lines = ") + str(len(self._processedLines))
        else: result += ('\n' if result else '') + "  " + _("Number of raw lines = ") + str(len(self._rawLines))
        if self.bookReferenceCode and (self._processedFlag or self._rawLines) and Globals.verbosityLevel > 1:
            result += ('\n' if result else '') + "  " + _("Deduced short book name(s) are {}").format( self.getAssumedBookNames() )

        if Globals.debugFlag or Globals.verbosityLevel>2:
            if self._processedFlag: result += '\n' + str( self._processedLines )
            if self._indexedFlag: result += '\n' + str( self.self._CVIndex )
        return result
    # end of InternalBibleBook.__str__


    def __len__( self ):
        """ This method returns the number of lines in the internal Bible book object. """
        return len( self._processedLines if self._processedFlag else self._rawLines )


    def addPriorityError( self, priority, c, v, string ):
        """Adds a priority error to self.errorDictionary."""
        if Globals.debugFlag:
            assert( isinstance( priority, int ) and ( 0 <= priority <= 100 ) )
            assert( isinstance( string, str ) and string)
        if not 'Priority Errors' in self.errorDictionary: self.errorDictionary['Priority Errors'] = [] # Just in case getErrors() deleted it

        bookReferenceCode = self.bookReferenceCode
        if self.errorDictionary['Priority Errors']:
            LastPriority, lastString, (lastBookReferenceCode,lastC,lastV,) = self.errorDictionary['Priority Errors'][-1]
            if priority==LastPriority and string==lastString and bookReferenceCode==lastBookReferenceCode: # Remove unneeded repetitive information
                bookReferenceCode = ''
                if c==lastC: c = ''

        self.errorDictionary['Priority Errors'].append( (priority,string,(bookReferenceCode,c,v,),) )
    # end of InternalBibleBook.addPriorityError


    def appendLine( self, marker, text ):
        """
        Append a (USFM-based) 2-tuple to self._rawLines.
            This is a very simple function,
                but having it allows us to have a single point in order to catch particular bugs or errors.
        """
        forceDebugHere = False
        if forceDebugHere or Globals.debugFlag:
            if forceDebugHere or debuggingThisModule: print( "InternalBibleBook.appendLine( {}, {} ) for {} {} {}".format( repr(marker), repr(text), self.objectTypeString, self.name, self.bookReferenceCode ) )
            #if len(self._rawLines ) > 200: halt
            #if 'xyz' in text: halt
        if text and ( '\n' in text or '\r' in text ):
            logging.critical( "InternalBibleBook.appendLine found newLine in {} text: {}={}".format( self.objectTypeString, marker, repr(text) ) )
        if Globals.debugFlag:
            assert( not self._processedFlag )
            assert( marker and isinstance( marker, str ) )
            if text:
                assert( isinstance( text, str ) )
                assert( '\n' not in text and '\r' not in text )

        if not ( marker in Globals.USFMMarkers or marker in NON_USFM_MARKERS ):
            logging.critical( "InternalBibleBook.appendLine marker for {} not in lists: {}={}".format( self.objectTypeString, marker, repr(text) ) )
            if marker in self.badMarkers:
                ix = self.badMarkers.index( marker )
                assert( 0 <= ix < len(self.badMarkers) )
                self.badMarkerCounts[ix] += 1
            else:
                self.badMarkers.append( marker )
                self.badMarkerCounts.append( 1 )
        if Globals.debugFlag: assert( marker in Globals.USFMMarkers or marker in NON_USFM_MARKERS )

        if marker not in NON_USFM_MARKERS and not Globals.USFMMarkers.isNewlineMarker( marker ):
            logging.critical( "IBB.appendLine: Not a NL marker: {}='{}'".format( marker, text ) )
            if Globals.debugFlag:
                print( self, repr(marker), repr(text) )
                halt

        if text is None:
            logging.critical( "InternalBibleBook.appendLine: Received {} {} {}={}".format( self.objectTypeString, self.bookReferenceCode, marker, repr(text) ) )
            if Globals.debugFlag: halt # Programming error in the calling routine, sorry
            text = '' # Try to recover

        if text.strip() != text:
            if marker=='v' and len(text)<=4 and self.objectTypeString in ('USX',): pass
            else:
                if self.pntsCount != -1:
                    self.pntsCount += 1
                    if self.pntsCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                        logging.warning( "InternalBibleBook.appendLine: Possibly needed to strip {} {} {}={}".format( self.objectTypeString, self.bookReferenceCode, marker, repr(text) ) )
                    else: # we've reached our limit
                        logging.warning( _('Additional "Possibly needed to strip" messages suppressed...') )
                        self.pntsCount = -1 # So we don't do this again (for this book)

        rawLineTuple = ( marker, text )
        self._rawLines.append( rawLineTuple )
    # end of InternalBibleBook.appendLine


    def appendToLastLine( self, additionalText, expectedLastMarker=None ):
        """ Append some extra text to the previous line in self._rawLines
            Doesn't add any additional spaces.
            (Used by USXXMLBibleBook.py) """
        forceDebugHere = False
        if forceDebugHere or ( Globals.debugFlag and debuggingThisModule ):
            print( " InternalBibleBook.appendToLastLine( {}, {} )".format( repr(additionalText), repr(expectedLastMarker) ) )
            assert( not self._processedFlag )
            assert( self._rawLines )
        if additionalText and ( '\n' in additionalText or '\r' in additionalText ):
            logging.critical( "InternalBibleBook.appendToLastLine found newLine in {} additionalText: {}={}".format( self.objectTypeString, expectedLastMarker, repr(additionalText) ) )
        if Globals.debugFlag:
            assert( not self._processedFlag )
            assert( additionalText and isinstance( additionalText, str ) )
            if additionalText: assert( '\n' not in additionalText and '\r' not in additionalText )
            if expectedLastMarker: assert( isinstance( expectedLastMarker, str ) )

        marker, text = self._rawLines[-1]
        #print( "additionalText for {} '{}' is '{}'".format( marker, text, additionalText ) )
        if expectedLastMarker and marker!=expectedLastMarker: # Not what we were expecting
            logging.critical( _("InternalBibleBook.appendToLastLine: expected \\{} but got \\{}").format( expectedLastMarker, marker ) )
        if expectedLastMarker and Globals.debugFlag: assert( marker == expectedLastMarker )
        #if marker in ('v','c',) and ' ' not in text: text += ' ' # Put a space after the verse or chapter number
        text += additionalText
        if forceDebugHere: print( "  newText for {} is {}".format( repr(marker), repr(text) ) )
        self._rawLines[-1] = (marker, text,)
    # end of InternalBibleBook.appendToLastLine


    def processLines( self ):
        """ Move notes out of the text into a separate area.
            Also, splits lines if a paragraph marker appears within a line.

            Uses self._rawLines and fills self._processedLines.
        """
        #if self._processedFlag: return # Can only do it once
        if Globals.verbosityLevel > 2: print( "  " + _("Processing {} ({} {}) {} lines...").format( self.objectNameString, self.objectTypeString, self.name, self.bookReferenceCode ) )
        if Globals.debugFlag: assert( not self._processedFlag ) # Can only do it once
        if Globals.debugFlag: assert( self._rawLines ) # or else the book was totally blank
        #print( self._rawLines[:20] ); halt

        internalSFMsToRemove = Globals.USFMMarkers.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True )
        internalSFMsToRemove = sorted( internalSFMsToRemove, key=len, reverse=True ) # List longest first


        def processLineFix( originalMarker, text ):
            """
            Does character fixes on a specific line and moves footnotes and cross-references out of the main text.
                Returns:
                    adjText: Text without notes and leading/trailing spaces
                    cleanText: adjText without character formatting as well
                    extras: a special list containing
                        extraType: 'fn' or 'xr'
                        extraIndex: the index into adjText above
                        extraText: the text of the note
                        cleanExtraText: extraText without character formatting as well

            NOTE: You must NOT strip the text any more AFTER calling this (or the note insert indices will be incorrect!
            """
            nonlocal rtsCount
            #print( "InternalBibleBook.processLineFix( {}, '{}' ) for {} ({})".format( originalMarker, text, self.bookReferenceCode, self.objectTypeString ) )
            if Globals.debugFlag:
                assert( originalMarker and isinstance( originalMarker, str ) )
                assert( isinstance( text, str ) )
            adjText = text
            cleanText = text.replace( 'xa0', ' ' ) # Replace non-break spaces

            # Remove trailing spaces
            if adjText and adjText[-1].isspace():
                #print( 10, self.bookReferenceCode, c, v, _("Trailing space at end of line") )
                fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Removed trailing space in {}: {}").format( originalMarker, text ) )
                if rtsCount != -1:
                    rtsCount += 1
                    if rtsCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                        logging.warning( _("processLineFix: Removed trailing space after {} {}:{} in \\{}: '{}'").format( self.bookReferenceCode, c, v, originalMarker, text ) )
                    else: # we've reached our limit
                        logging.error( _('processLineFix: Additional "Removed trailing space" messages suppressed...') )
                        rtsCount = -1 # So we don't do this again (for this book)
                self.addPriorityError( 10, c, v, _("Trailing space at end of line") )
                adjText = adjText.rstrip()
                #print( "QQQ1: rstrip ok" )
                #print( originalMarker, "'"+text+"'", "'"+adjText+"'" )

            if self.objectTypeString in ('USFM','USX',):
                # Fix up quote marks
                if '<' in adjText or '>' in adjText:
                    if not self.givenAngleBracketWarning: # Just give the warning once (per book)
                        if self.replaceAngleBracketsFlag:
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Replaced angle bracket(s) in {}: {}").format( originalMarker, text ) )
                            logging.info( _("processLineFix: Replaced angle bracket(s) after {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, text ) )
                            self.addPriorityError( 3, '', '', _("Book contains angle brackets (which we attempted to replace)") )
                        else:
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found (first) angle bracket in {}: {}").format( originalMarker, text ) )
                            logging.info( _("processLineFix: Found (first) angle bracket after {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, text ) )
                            self.addPriorityError( 3, '', '', _("Book contains angle bracket(s)") )
                        self.givenAngleBracketWarning = True
                    if self.replaceAngleBracketsFlag:
                        adjText = adjText.replace('<<','“').replace('>>','”').replace('<','‘').replace('>','’') # Replace angle brackets with the proper opening and close quote marks
                if '"' in adjText:
                    if not self.givenDoubleQuoteWarning: # Just give the warning once (per book)
                        if self.replaceStraightDoubleQuotesFlag:
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Replaced straight quote sign(s) (\") in \\{}: {}").format( originalMarker, adjText ) )
                            logging.info( _("processLineFix: Replaced straight quote sign(s) (\") after {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                            self.addPriorityError( 8, '', '', _("Book contains straight quote signs (which we attempted to replace)") )
                        else: # we're not attempting to replace them
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found (first) straight quote sign (\") in \\{}: {}").format( originalMarker, adjText ) )
                            logging.info( _("processLineFix: Found (first) straight quote sign (\") after {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                            self.addPriorityError( 58, '', '', _("Book contains straight quote sign(s)") )
                        self.givenDoubleQuoteWarning = True
                    if self.replaceStraightDoubleQuotesFlag:
                        if adjText[0]=='"': adjText = adjText.replace('"','“',1) # Replace initial double-quote mark with a proper open quote mark
                        adjText = adjText.replace(' "',' “').replace(';"',';“').replace('("','(“').replace('["','[“') # Try to replace double-quote marks with the proper opening and closing quote marks
                        adjText = adjText.replace('."','.”').replace(',"',',”').replace('?"','?”').replace('!"','!”').replace(')"',')”').replace(']"',']”').replace('*"','*”')
                        adjText = adjText.replace('";','”;').replace('"(','”(').replace('"[','”[') # Including the questionable ones
                        adjText = adjText.replace('" ','” ').replace('",','”,').replace('".','”.').replace('"?','”?').replace('"!','”!') # Even the bad ones!
                        if '"' in adjText:
                            logging.warning( "processLineFix: {} {}:{} still has straight quotes in {}:'{}'".format( originalMarker, adjText ) )

                # Do XML/HTML common character replacements
                adjText = adjText.replace( '&', '&amp;' )
                #adjText = adjText.replace( "'", '&#39;' ) # XML does contain &apos; for optional use, but not recognised in all versions of HTML
                if '<' in adjText or '>' in adjText:
                    logging.error( "processLineFix: {} {}:{} still has angle-brackets in {}:'{}'".format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                    self.addPriorityError( 12, c, v, _("Contains angle-bracket(s)") )
                    adjText = adjText.replace( '<', '&lt;' ).replace( '>', '&gt;' )
                if '"' in adjText:
                    logging.warning( "processLineFix: {} {}:{} straight-quotes in {}:'{}'".format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                    self.addPriorityError( 11, c, v, _("Contains straight-quote(s)") )
                    adjText = adjText.replace( '"', '&quot;' )


            # Prepare for extras
            extras = InternalBibleExtraList()
            lcAdjText = adjText.lower()

            #print( "QQQ MOVE OUT NOTES" )
            if self.objectTypeString in ('USFM','USX',): # Move USFM footnotes and crossreferences out to extras
                ixFN = lcAdjText.find( '\\f ' )
                ixXR = lcAdjText.find( '\\x ' )
                while ixFN!=-1 or ixXR!=-1: # We have one or the other
                    if ixFN!=-1 and ixXR!=-1: # We have both
                        if Globals.debugFlag: assert( ixFN != ixXR )
                        ix1 = min( ixFN, ixXR ) # Process the first one
                    else: ix1 = ixFN if ixXR==-1 else ixXR
                    if ix1 == ixFN:
                        ix2 = lcAdjText.find( '\\f*' )
                        thisOne, this1 = "footnote", "fn"
                        if ixFN and lcAdjText[ixFN-1]==' ':
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found footnote preceded by a space in \\{}: {}").format( originalMarker, adjText ) )
                            logging.error( _("processLineFix: Found footnote preceded by a space after {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                            self.addPriorityError( 52, c, v, _("Footnote is preceded by a space") )
                    else:
                        if Globals.debugFlag: assert( ix1 == ixXR )
                        ix2 = lcAdjText.find( '\\x*' )
                        thisOne, this1 = "cross-reference", "xr"
                    if ix2 == -1: # no closing marker
                        fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found unmatched {} open in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                        logging.error( _("processLineFix: Found unmatched {} open after {} {}:{} in \\{}: {}").format( thisOne, self.bookReferenceCode, c, v, originalMarker, adjText ) )
                        self.addPriorityError( 84, c, v, _("Marker {} is unmatched").format( thisOne ) )
                        ix2 = 99999 # Go to the end
                    elif ix2 < ix1: # closing marker is before opening marker
                        fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found unmatched {} in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                        logging.error( _("processLineFix: Found unmatched {} after {} {}:{} in \\{}: {}").format( thisOne, self.bookReferenceCode, c, v, thisOne, originalMarker, adjText ) )
                        self.addPriorityError( 84, c, v, _("Marker {} is unmatched").format( thisOne ) )
                        ix1, ix2 = ix2, ix1 # swap them then
                    # Remove the footnote or xref
                    #print( "Found {} at {} {} in '{}'".format( thisOne, ix1, ix2, adjText ) )
                    note = adjText[ix1+3:ix2] # Get the note text (without the beginning and end markers)
                    if not note:
                        fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found empty {} in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                        logging.error( _("processLineFix: Found empty {} after {} {}:{} in \\{}: {}").format( thisOne, self.bookReferenceCode, c, v, originalMarker, adjText ) )
                        self.addPriorityError( 53, c, v, _("Empty {}").format( thisOne ) )
                    else: # there is a note
                        if note[0].isspace():
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found {} starting with space in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                            logging.error( _("processLineFix: Found {} starting with space after {} {}:{} in \\{}: {}").format( thisOne, self.bookReferenceCode, c, v, originalMarker, adjText ) )
                            self.addPriorityError( 12, c, v, _("{} starts with space").format( thisOne.title() ) )
                            note = note.lstrip()
                            #print( "QQQ2: lstrip in note" ); halt
                        if note and note[-1].isspace():
                            fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found {} ending with space in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                            logging.error( _("processLineFix: Found {} ending with space after {} {}:{} in \\{}: {}").format( thisOne, self.bookReferenceCode, c, v, originalMarker, adjText ) )
                            self.addPriorityError( 11, c, v, _("{} ends with space").format( thisOne.title() ) )
                            note = note.rstrip()
                            #print( "QQQ3: rstrip in note" )
                        if '\\f ' in note or '\\f*' in note or '\\x ' in note or '\\x*' in note: # Only the contents of these fields should be here now
                            print( "processLineFix: {} {}:{} What went wrong here: '{}' from \\{} '{}' (Is it an embedded note?)".format( self.bookReferenceCode, c, v, note, originalMarker, text ) )
                            print( "processLineFix: Have an embedded note perhaps! Not handled correctly yet" )
                            note = note.replace( '\\f ', ' ' ).replace( '\\f*','').replace( '\\x ', ' ').replace('\\x*','') # Temporary fix ..................
                    adjText = adjText[:ix1] + adjText[ix2+3:] # Remove the note completely from the text
                    lcAdjText = adjText.lower()
                    # Now prepare a cleaned version
                    cleanedNote = note.replace( '&amp;', '&' ).replace( '&#39;', "'" ).replace( '&lt;', '<' ).replace( '&gt;', '>' ).replace( '&quot;', '"' ) # Undo any replacements above
                    for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                        cleanedNote = cleanedNote.replace( sign, '' )
                    for marker in ['\\xo*','\\xo ', '\\xt*','\\xt ', '\\xk*','\\xk ', '\\xq*','\\xq ',
                                   '\\xot*','\\xot ', '\\xnt*','\\xnt ', '\\xdc*','\\xdc ',
                                   '\\fr*','\\fr ','\\ft*','\\ft ','\\fqa*','\\fqa ','\\fq*','\\fq ',
                                   '\\fv*','\\fv ','\\fk*','\\fk ','\\fl*','\\fl ','\\fdc*','\\fdc ',] \
                                       + internalSFMsToRemove:
                        cleanedNote = cleanedNote.replace( marker, '' )
                    if '\\' in cleanedNote:
                        fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Found unexpected backslash in {}: {}").format( thisOne, cleanedNote ) )
                        logging.error( _("processLineFix: Found unexpected backslash after {} {}:{} in {}: {}").format( self.bookReferenceCode, c, v, thisOne, cleanedNote ) )
                        self.addPriorityError( 81, c, v, _("{} contains unexpected backslash").format( thisOne.title() ) )
                        cleanedNote = cleanedNote.replace( '\\', '' )
                    # Save it all and finish off
                    extras.append( InternalBibleExtra(this1,ix1,note,cleanedNote) ) # Saves a 4-tuple: type ('fn' or 'xr'), index into the main text line, the actual fn or xref contents, then a cleaned version
                    ixFN = lcAdjText.find( '\\f ' )
                    ixXR = lcAdjText.find( '\\x ' )
                #if extras: print( "Fix gave '{}' and '{}'".format( adjText, extras ) )
                #if len(extras)>1: print( "Mutiple fix gave '{}' and '{}'".format( adjText, extras ) )

                # Check for anything left over
                if '\\f' in lcAdjText or '\\x' in lcAdjText:
                    fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unable to properly process footnotes and cross-references in \\{}: {}").format( originalMarker, adjText ) )
                    logging.error( _("processLineFix: Unable to properly process footnotes and cross-references {} {}:{} in \\{}: {}").format( self.bookReferenceCode, c, v, originalMarker, adjText ) )
                    self.addPriorityError( 82, c, v, _("Invalid footnotes or cross-references") )

            elif self.objectTypeString == 'SwordBibleModule': # Move Sword notes out to extras
                #print( "\nhere", adjText )
                ixStart = 0 # Start searching from here
                indexDigits = [] # For Sword <RF>n<Rf> note markers
                while '<' in adjText:
                    ixStart = adjText.find( '<', ixStart )
                    if ixStart==-1: break
                    remainingText = adjText[ixStart:]
                    if remainingText.startswith( '<w ' ):
                        ixClose = adjText.find( '>', ixStart+1 )
                        ixEnd = adjText.find( '</w>', ixClose+1 )
                        #if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'w s c e', ixStart, ixClose, ixEnd )
                        if Globals.debugFlag:
                            assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                            assert( ixStart < ixClose < ixEnd )
                        stuff = adjText[ixStart+3:ixClose]
                        adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+4:]
                        #print( "st", "'"+stuff+"'", )
                        extras.append( InternalBibleExtra('sr',ixStart+ixEnd-ixClose,stuff,stuff) )
                        ixStart += ixEnd-ixClose-1
                    elif remainingText.startswith( '<note ' ):
                        ixClose = adjText.find( '>', ixStart+1 )
                        ixEnd = adjText.find( '</note>' )
                        #if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'n s c e', ixStart, ixClose, ixEnd )
                        if Globals.debugFlag:
                            assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                            assert( ixStart < ixClose < ixEnd )
                        stuff = adjText[ixStart+6:ixClose]
                        adjText = adjText[:ixStart] + adjText[ixEnd+7:]
                        noteContents = adjText[ixClose+1:ixEnd]
                        #print( "now" "'"+adjText+"'" )
                        #print( "st", "'"+stuff+"'", )
                        if stuff == 'type="study"': code = 'sn'
                        else: halt
                        extras.append( InternalBibleExtra(code,ixStart+ixEnd-ixClose,stuff,stuff) )
                        #ixStart += 0
                    elif remainingText.startswith('<RF>1<Rf>') or remainingText.startswith('<RF>2<Rf>') \
                    or remainingText.startswith('<RF>3<Rf>') or remainingText.startswith('<RF>4<Rf>'):
                        indexDigit = remainingText[4]
                        if Globals.debugFlag: assert( indexDigit.isdigit() )
                        adjText = adjText[:ixStart] + adjText[ixStart+9:]
                        indexDigits.append( (indexDigit,ixStart,) )
                        #ixStart += 0
                    elif remainingText.startswith( '<RF>1) ' ):
                        #print( "iT", c, v, indexDigits, remainingText )
                        if Globals.debugFlag: assert( indexDigits )
                        ixEnd = adjText.find( '<Rf>' )
                        if Globals.debugFlag: assert( ixStart!=-1 and ixEnd!=-1 )
                        if Globals.debugFlag: assert( ixStart < ixEnd )
                        notes = adjText[ixStart+4:ixEnd]
                        adjText = adjText[:ixStart] # Remove these notes from the end
                        newList = []
                        for indexDigit, stringIndex in reversed( indexDigits ):
                            ixN = notes.find( indexDigit+') ' )
                            noteContents = notes[ixN+3:].strip()
                            #print( "QQQ4: strip" ); halt
                            if not noteContents: noteContents = lastNoteContents # Might have same note twice
                            cleanNoteContents = noteContents.replace( '\\add ', '' ).replace( '\\add*', '').strip()
                            #print( (indexDigit, stringIndex, noteContents, cleanNoteContents) )
                            newList.append( ('fn',stringIndex,noteContents,cleanNoteContents) )
                            notes = notes[:ixN] # Remove this last note from the end
                            lastNoteContents = noteContents
                        extras.extend( reversed( newList ) )
                        #print( extras )
                        #ixStart += 0
                    elif remainingText.startswith( '<RF>' ):
                        print( "Something is wrong here:", c, v, text )
                        print( "iT", c, v, indexDigits, remainingText )
                        if Globals.debugFlag: assert( indexDigits )
                        ixEnd = adjText.find( '<Rf>' )
                        if Globals.debugFlag:
                            assert( ixStart!=-1 and ixEnd!=-1 )
                            assert( ixStart < ixEnd )
                        notes = adjText[ixStart+4:ixEnd]
                        adjText = adjText[:ixStart] # Remove these notes from the end
                        newList = []
                        for indexDigit, stringIndex in reversed( indexDigits ):
                            #ixN = notes.find( indexDigit+') ' )
                            noteContents = notes.strip()
                            #print( "QQQ5: strip" ); halt
                            if not noteContents: noteContents = lastNoteContents # Might have same note twice
                            cleanNoteContents = noteContents.replace( '\\add ', '' ).replace( '\\add*', '').strip()
                            print( (indexDigit, stringIndex, noteContents, cleanNoteContents) )
                            newList.append( ('fn',stringIndex,noteContents,cleanNoteContents) )
                            #notes = notes[:ixN] # Remove this last note from the end
                            lastNoteContents = noteContents
                        extras.extend( reversed( newList ) )
                        #print( extras )
                        #ixStart += 0
                    #elif adjText[ixStart:].startswith( '<transChange ' ):
                        #ixEnd = adjText.find( '</transChange>' )
                        ##if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'ts s c e', ixStart, ixClose, ixEnd )
                        #assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                        #assert( ixStart < ixClose < ixEnd )
                        #stuff = adjText[ixStart+13:ixClose]
                        #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+14:]
                        ##print( "st", "'"+stuff+"'", )
                        #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                    #elif adjText[ixStart:].startswith( '<seg>' ):
                        #ixEnd = adjText.find( '</seg>' )
                        ##if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'sg s c e', ixStart, ixClose, ixEnd )
                        #assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                        #assert( ixStart < ixClose < ixEnd )
                        #stuff = adjText[ixStart+5:ixClose]
                        #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+6:]
                        ##print( "st", "'"+stuff+"'", )
                        #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                    #elif adjText[ixStart:].startswith( '<divineName>' ):
                        #ixEnd = adjText.find( '</divineName>' )
                        ##if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'sg s c e', ixStart, ixClose, ixEnd )
                        #assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                        #assert( ixStart < ixClose < ixEnd )
                        #stuff = adjText[ixStart+12:ixClose]
                        #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+13:]
                        ##print( "st", "'"+stuff+"'", )
                        #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                    #elif adjText[ixStart:].startswith( '<milestone ' ):
                        #ixEnd = adjText.find( '/>' )
                        ##if ixEnd != -1: ixEnd += 3
                        #print( adjText, 'ms s e', ixStart, ixEnd )
                        #assert( ixStart!=-1 and ixEnd!=-1 )
                        #assert( ixStart < ixEnd )
                        #stuff = adjText[ixStart+11:ixEnd]
                        #adjText = adjText[:ixStart] + adjText[ixEnd+2:]
                        #print( "st", "'"+stuff+"'", )
                        #extras.append( ('ms',ixStart,stuff,stuff) )
                    #elif adjText[ixStart:].startswith( '<title ' ):
                        #ixEnd = adjText.find( '</title>' )
                        ##if ixEnd != -1: ixEnd += 3
                        #print( adjText, 't s c e', ixStart, ixClose, ixEnd )
                        #assert( ixStart!=-1 and ixClose!=-1 and ixEnd!=-1 )
                        #assert( ixStart < ixClose < ixEnd )
                        #stuff = adjText[ixStart+7:ixClose]
                        #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+8:]
                        ##print( "st", "'"+stuff+"'", )
                        #extras.append( ('ti',ixStart+ixEnd-ixClose,stuff,stuff) )
                    else:
                        #print( "Ok. Still have < in:", adjText )
                        ixStart += 1 # So it steps past fields that we don't remove, e.g., <divineName>xx</divineName>
                #print( "aT", adjText )
                #print( "ex", extras )
                #adjText = adjText.replace( '<transChange type="added">', '<it>' ).replace( '</transChange>', '</it>' )
                #halt

            # Check trailing spaces again now
            if adjText and adjText[-1].isspace():
                #print( 10, self.bookReferenceCode, c, v, _("Trailing space before note at end of line") )
                fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Removed trailing space before note in \\{}: '{}'").format( originalMarker, text ) )
                logging.warning( _("processLineFix: Removed trailing space before note after {} {}:{} in \\{}: '{}'").format( self.bookReferenceCode, c, v, originalMarker, text ) )
                self.addPriorityError( 10, c, v, _("Trailing space before note at end of line") )
                adjText = adjText.rstrip()
                #print( "QQQ6: rstrip" ); halt
                #print( originalMarker, "'"+text+"'", "'"+adjText+"'" )

            # Now remove all character formatting from the cleanText string (to make it suitable for indexing and search routines
            #   This includes markers like \em, \bd, \wj, etc.
            #print( "here", self.objectTypeString )
            if self.objectTypeString == 'SwordBibleModule': # remove character formatting
                cleanText = adjText
                cleanText = cleanText.replace( '<title type="chapter">', '' ).replace( '</title>', '' )
                cleanText = cleanText.replace( '<transChange type="added">', '' ).replace( '</transChange>', '' )
                #cleanText = cleanText.replace( '<milestone marker="Â¶" subType="x-added" type="x-p"/>', '' )
                #cleanText = cleanText.replace( '<milestone marker="Â¶" type="x-p"/>', '' )
                #cleanText = cleanText.replace( '<milestone type="x-extra-p"/>', '' )
                cleanText = cleanText.replace( '<seg><divineName>', '' ).replace( '</divineName></seg>', '' )
                if '<' in cleanText or '>' in cleanText:
                    print( "\nFrom:", c, v, text )
                    print( " Still have angle brackets left in:", cleanText )
                    #halt
            else: # not Sword
                cleanText = adjText.replace( '&amp;', '&' ).replace( '&#39;', "'" ).replace( '&lt;', '<' ).replace( '&gt;', '>' ).replace( '&quot;', '"' ) # Undo any replacements above
                if '\\' in cleanText: # we will first remove known USFM character formatting markers
                    for possibleCharacterMarker in Globals.USFMMarkers.getCharacterMarkersList():
                        tryMarkers = []
                        if Globals.USFMMarkers.isNumberableMarker( possibleCharacterMarker ):
                            for d in ('1','2','3','4','5'):
                                tryMarkers.append( '\\'+possibleCharacterMarker+d+' ' )
                        tryMarkers.append( '\\'+possibleCharacterMarker+' ' )
                        #print( "tryMarkers", tryMarkers )
                        for tryMarker in tryMarkers:
                            while tryMarker in cleanText:
                                #print( "Removing '{}' from '{}'".format( tryMarker, cleanText ) )
                                cleanText = cleanText.replace( tryMarker, '', 1 ) # Remove it
                                tryCloseMarker = '\\'+possibleCharacterMarker+'*'
                                shouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( possibleCharacterMarker )
                                if shouldBeClosed == 'A' \
                                or shouldBeClosed == 'S' and tryCloseMarker in cleanText:
                                    #print( "Removing '{}' from '{}'".format( tryCloseMarker, cleanText ) )
                                    cleanText = cleanText.replace( tryCloseMarker, '', 1 ) # Remove it
                        if not '\\' in cleanText: break # no point in looping further
                    while '\\' in cleanText: # we will now try to remove any bad markers
                        ixBS = cleanText.index( '\\' )
                        ixSP = cleanText.find( ' ', ixBS )
                        ixAS = cleanText.find( '*', ixBS )
                        if ixSP == -1: ixSP=99999
                        if ixAS == -1: ixAS=99999
                        ixEND = min( ixSP, ixAS )
                        if ixEND != 99999: # remove the marker and the following space or asterisk
                            #print( "Removing unknown marker '{}' from '{}'".format( cleanText[ixBS:ixEND+1], cleanText ) )
                            cleanText = cleanText[:ixBS] + cleanText[ixEND+1:]
                        else: # we didn't find a space or asterisk so it's at the end of the line
                            #print( "text: '{}'".format( text ) )
                            #print( "adjText: '{}'".format( adjText ) )
                            #print( "cleanText: '{}'".format( cleanText ) )
                            #print( ixBS, ixSP, ixAS, ixEND )
                            if Globals.debugFlag: assert( ixSP==99999 and ixAS==99999 and ixEND==99999 )
                            cleanText = cleanText[:ixBS].rstrip()
                            #print( "QQQ7: rstrip" ); halt
                            #print( "cleanText: '{}'".format( cleanText ) )
                    if '\\' in cleanText: logging.error( "processLineFix: Why do we still have a backslash in '{}' from '{}'?".format( cleanText, adjText ) ); halt

            if Globals.debugFlag: # Now do a final check that we did everything right
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    assert( extraText ) # Shouldn't be blank
                    #if self.objectTypeString == 'USFM': assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                    assert( extraIndex >= 0 )
                    # This can happen with multiple notes at the end separated by spaces
                    #if extraIndex > len(adjText)+1: print( "Programming Note: extraIndex {} is way more than text length of {} with '{}'".format( extraIndex, len(adjText), text ) )
                    assert( extraType in ('fn','xr','sr','sn',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras

            return adjText, cleanText, extras
        # end of InternalBibleBook.processLines.processLineFix


        def doAppend( adjMarker, originalMarker, text, originalText ):
            """
            Append the entry to self._processedLines
            """
            nonlocal sahtCount

            if adjMarker=='b' and text:
                fixErrors.append( _("{} {}:{} Paragraph marker '{}' should not contain text").format( self.bookReferenceCode, c, v, originalMarker ) )
                logging.error( _("doAppend: Illegal text for '{}' paragraph marker {} {}:{}").format( originalMarker, self.bookReferenceCode, c, v ) )
                self.addPriorityError( 97, c, v, _("Should not have text following character marker '{}").format( originalMarker ) )

            if (adjMarker=='b' or adjMarker in Globals.USFMParagraphMarkers) and text:
                # Separate the verse text from the paragraph markers
                self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, '', '', InternalBibleExtraList(), '') )
                adjMarker = 'p~'
                if not text.strip():
                    fixErrors.append( _("{} {}:{} Paragraph marker '{}' seems to contain only whitespace").format( self.bookReferenceCode, c, v, originalMarker ) )
                    logging.error( _("doAppend: Only whitespace for '{}' paragraph marker {} {}:{}").format( originalMarker, self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 68, c, v, _("Only whitespace following character marker '{}").format( originalMarker ) )
                    return # nothing more to do here

            # Separate out the notes (footnotes and cross-references)
            adjText, cleanText, extras = processLineFix( adjMarker, text )
            #if adjMarker=='v~' and not cleanText:
                #if text or adjText:
                    #print( "Suppressed blank v~ for", self.bookReferenceCode, c, v, "'"+text+"'", "'"+adjText+"'" ); halt

            # From here on, we use adjText (not text)
            #print( "marker '{}' text '{}', adjText '{}'".format( adjMarker, text, adjText ) )
            if not adjText and not extras and ( Globals.USFMMarkers.markerShouldHaveContent(adjMarker)=='A' or adjMarker in ('v~','c~','c#',) ): # should always have text
                #print( "processLine: marker should always have text (ignoring it):", self.bookReferenceCode, c, v, originalMarker, adjMarker, " originally '"+text+"'" )
                fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '{}' should always have text").format( originalMarker ) )
                if self.objectTypeString in ('USFM','USX',):
                    if sahtCount != -1:
                        sahtCount += 1
                        if sahtCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                            logging.error( _("doAppend: Marker '{}' at {} {}:{} should always have text").format( originalMarker, self.bookReferenceCode, c, v ) )
                        else: # we've reached our limit
                            logging.error( _('doAppend: Additional "Marker should always have text" messages suppressed...') )
                            sahtCount = -1 # So we don't do this again (for this book)
                self.addPriorityError( 96, c, v, _("Marker \\{} should always have text").format( originalMarker ) )
                # Don't bother even saving the marker since it's useless
                # Wrong -- save the empty marker
                if adjMarker != 'v~': # Save all other empty markers
                    self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, adjText, cleanText, extras, originalText) )
            else:
                #if c=='5' and v=='29': print( "processLine: {} '{}' to {} aT='{}' cT='{}' {}".format( originalMarker, text, adjMarker, adjText, cleanText, extras ) );halt
                self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, adjText, cleanText, extras, originalText) )
        # end of doAppend


        def processLine( originalMarker, originalText ):
            """
            Process one USFM line by
                normalizing USFM markers (e.g., q -> q1, s -> s1 )
                separating out the notes
                    and producing clean text suitable for searching
                    and then save the line.
            """
            nonlocal c, v, haveWaitingC
            nonlocal nfvnCount, owfvnCount, rtsCount, sahtCount
            #print( "processLine: {} '{}' '{}'".format( self.bookReferenceCode, originalMarker, originalText ) )
            if Globals.debugFlag:
                assert( originalMarker and isinstance( originalMarker, str ) )
                assert( isinstance( originalText, str ) )
            text = originalText

            # Convert USFM markers like s to standard markers like s1
            try:
                adjustedMarker = originalMarker if originalMarker in NON_USFM_MARKERS else Globals.USFMMarkers.toStandardMarker( originalMarker )
            except KeyError: # unknown marker
                logging.error( "processLine-check: unknown {} originalMarker = {}".format( self.objectTypeString, originalMarker ) )
                adjustedMarker = originalMarker # temp....................

            # Keep track of where we are
            if originalMarker=='c' and text:
                if haveWaitingC: logging.warning( "Note: Two c markers with no intervening v markers at {} {}:{}".format( self.bookReferenceCode, c, v ) )
                #c = text.split()[0]; v = '0'
                cBits = text.split( None, 1 )
                c, v = cBits[0], '0'
                if c == '0':
                    fixErrors.append( _("{} {}:{} Chapter zero is not allowed '{}'").format( self.bookReferenceCode, c, v, text ) )
                    logging.error( _("Found zero '{}' in chapter marker {} {}:{}").format( text, self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 97, c, v, _("Chapter zero '{}' not allowed").format( text ) )
                    if len(self._processedLines) < 30: # It's near the beginning of the file
                        logging.info( "Converting given chapter zero to chapter one in {}".format( self.bookReferenceCode ) )
                        c = '1' # Our best guess
                        text = c + text[1:]
                haveWaitingC = c
                if len(cBits) > 1: # We have extra stuff on the c line after the chapter number and a space
                    fixErrors.append( _("{} {}:{} Chapter marker seems to contain extra material '{}'").format( self.bookReferenceCode, c, v, cBits[1] ) )
                    logging.error( _("Extra '{}' material in chapter marker {} {}:{}").format( cBits[1], self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 98, c, v, _("Extra '{}' material after chapter marker").format( cBits[1] ) )
                    #print( "Something on c line", "'"+text+"'", "'"+cBits[1]+"'" )
                    self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, c, c, InternalBibleExtraList(), c) ) # Write the chapter number as a separate line
                    adjustedMarker, text = 'c~', cBits[1]
            elif originalMarker=='v' and text:
                v = text.split()[0] # Get the actual verse number
                if c == '0': # Some single chapter books don't have an explicit chapter 1 marker -- we'll make it explicit here
                    if not self.isSingleChapterBook:
                        fixErrors.append( _("{} {}:{} Chapter marker seems to be missing before first verse").format( self.bookReferenceCode, c, v ) )
                        logging.error( _("Missing chapter number before first verse {} {}:{}").format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 98, c, v, _("Missing chapter number before first verse") )
                    c = '1'
                    if self.isSingleChapterBook and v!='1':
                        fixErrors.append( _("{} {}:{} Expected single chapter book to start with verse 1").format( self.bookReferenceCode, c, v ) )
                        logging.error( _("Expected single chapter book to start with verse 1 at {} {}:{}").format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 38, c, v, _("Expected single chapter book to start with verse 1") )
                    poppedStuff = self._processedLines.pop()
                    if poppedStuff is not None:
                        lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText = poppedStuff
                    else: lastAdjustedMarker = lastOriginalMarker = lastAdjustedText = lastCleanText = lastExtras = lastOriginalText = None
                    print( self.bookReferenceCode, "lastMarker (popped) was", lastAdjustedMarker, lastAdjustedText )
                    if lastAdjustedMarker in ('p','q1','m','nb',): # The chapter marker should go before this
                        self._processedLines.append( InternalBibleEntry('c', 'c', '1', '1', InternalBibleExtraList(), '1') ) # Write the explicit chapter number
                        self._processedLines.append( InternalBibleEntry(lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText) )
                    else: # Assume that the last marker was part of the introduction, so write it first
                        if lastAdjustedMarker not in ( 'ip', ):
                            logging.info( "{} {}:{} Assumed {} was part of intro after {}".format( self.bookReferenceCode, c, v, lastAdjustedMarker, marker ) )
                            #if v!='13': halt # Just double-checking this code (except for one weird book that starts at v13)
                        if lastOriginalText:
                            self._processedLines.append( InternalBibleEntry(lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText) )
                        self._processedLines.append( InternalBibleEntry('c', 'c', '1', '1', InternalBibleExtraList(), '1') ) # Write the explicit chapter number
                    #print( self._processedLines ); halt

                if haveWaitingC: # Add a false chapter number at the place where we normally want it printed
                    self._processedLines.append( InternalBibleEntry('c#', 'c', haveWaitingC, haveWaitingC, InternalBibleExtraList(), haveWaitingC) ) # Write the additional chapter number
                    haveWaitingC = False

                # Convert v markers to milestones only
                text = text.lstrip()
                #print( "QQQ8: lstrip" )
                ixSP = text.find( ' ' )
                ixBS = text.find( '\\' )
                if ixSP == -1: ixSP=99999
                if ixBS == -1: ixBS=99999
                ix = min( ixSP, ixBS ) # Break at the first space or backslash
                if ix<ixSP: # It must have been the backslash first
                    #print( "processLine had an unusual case in {} {}:{}: '{}' '{}'".format( self.bookReferenceCode, c, v, originalMarker, originalText ) )
                    fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unusual field (after verse number): '{}'").format( originalText ) )
                    logging.error( _("Unexpected backslash touching verse number (missing space?) after {} {}:{} in \\{}: '{}'").format( self.bookReferenceCode, c, v, originalMarker, originalText ) )
                    self.addPriorityError( 94, c, v, _("Unexpected backslash touching verse number (missing space?) in '{}'").format( originalText ) )
                if ix==99999: # There's neither -- not unexpected if this is a translation in progress
                    #print( "processLine had an empty verse field in {} {}:{}: '{}' '{}' {} {} {}".format( self.bookReferenceCode, c, v, originalMarker, originalText, ix, ixSP, ixBS ) )
                    fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Nothing after verse number: '{}'").format( originalText ) )
                    if self.objectTypeString in ('USFM','USX',):
                        if nfvnCount != -1:
                            nfvnCount += 1
                            if nfvnCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                                logging.error( _("Nothing following verse number after {} {}:{} in \\{}: '{}'").format( self.bookReferenceCode, c, v, originalMarker, originalText ) )
                            else: # we've reached our limit
                                logging.error( _('Additional "Nothing following verse number" messages suppressed...') )
                                nfvnCount = -1 # So we don't do this again (for this book)
                    self.addPriorityError( 92, c, v, _("Nothing following verse number in '{}'").format( originalText ) )
                    verseNumberBit = text
                    #print( "verseNumberBit is '{}'".format( verseNumberBit ) )
                    if Globals.debugFlag:
                        assert( verseNumberBit )
                        assert( ' ' not in verseNumberBit )
                        assert( '\\' not in verseNumberBit )
                    self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, verseNumberBit, verseNumberBit, InternalBibleExtraList(), verseNumberBit) ) # Write the verse number (or range) as a separate line
                    return # Don't write a blank v~ field
                    #adjustedMarker, text = 'v~', ''
                else: # there is something following the verse number digits (starting with space or backslash)
                    verseNumberBit, verseNumberRest = text[:ix], text[ix:]
                    #print( "verseNumberBit is '{}', verseNumberRest is '{}'".format( verseNumberBit, verseNumberRest ) )
                    if Globals.debugFlag:
                        assert( verseNumberBit and verseNumberRest )
                        assert( '\\' not in verseNumberBit )
                    self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, verseNumberBit, verseNumberBit, InternalBibleExtraList(), verseNumberBit) ) # Write the verse number (or range) as a separate line
                    strippedVerseText = verseNumberRest.lstrip()
                    #print( "QQQ9: lstrip" )
                    if not strippedVerseText:
                        if owfvnCount != -1:
                            owfvnCount += 1
                            if owfvnCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                                logging.error( _("Only whitespace following verse number after {} {}:{} in \\{}: '{}'").format( self.bookReferenceCode, c, v, originalMarker, originalText ) )
                            else: # we've reached our limit
                                logging.error( _('Additional "Only whitespace following verse number" messages suppressed...') )
                                owfvnCount = -1 # So we don't do this again (for this book)
                        self.addPriorityError( 91, c, v, _("Only whitespace following verse number in '{}'").format( originalText ) )
                        return # Don't write a blank v~ field
                    #print( "Ouch", self.bookReferenceCode, c, v )
                    #assert( strippedVerseText )
                    adjustedMarker, text = 'v~', strippedVerseText

            if 1 or text: # check markers inside the lines and separate them if they're paragraph markers
                if self.objectTypeString == 'USFM':
                    markerList = Globals.USFMMarkers.getMarkerListFromText( text )
                    ix = 0
                    for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                        if Globals.USFMMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                            if ix==0:
                                fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '{}' shouldn't appear within line in \\{}: '{}'").format( insideMarker, originalMarker, text ) )
                                logging.error( _("Marker '{}' shouldn't appear within line after {} {}:{} in \\{}: '{}'").format( insideMarker, self.bookReferenceCode, c, v, originalMarker, text ) ) # Only log the first error in the line
                                self.addPriorityError( 96, c, v, _("Marker \\{} shouldn't be inside a line").format( insideMarker ) )
                            thisText = text[ix:iMIndex].rstrip()
                            #print( "QQQ10: rstrip" ); halt
                            adjText, cleanText, extras = processLineFix( originalMarker, thisText )
                            self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, adjText, cleanText, extras, originalText) )
                            ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                            adjMarker = Globals.USFMMarkers.toStandardMarker( insideMarker ) # setup for the next line
                    if ix != 0: # We must have separated multiple lines
                        text = text[ix:]
                elif self.objectTypeString == 'SwordBibleModule':
                    # First replace fixed strings
                    ixLT = text.find( '<' )
                    while ixLT != -1:
                        beforeText = text[:ixLT]
                        thisText = text[ixLT:]
                        for pText in ( '<milestone type="x-extra-p"/>', '<milestone marker="Â¶" type="x-p"/>', '<milestone marker="Â¶" subType="x-added" type="x-p"/>' ):
                            if thisText.startswith( pText ):
                                afterText = text[ixLT+len(pText):]
                                #print( "\n", c, v, "'"+text+"'" )
                                #print( "'"+beforeText+"'", pText, "'"+afterText+"'" )
                                adjText, cleanText, extras = processLineFix( originalMarker, beforeText )
                                lastAM, lastOM, lastAT, lastCT, lastX, lastOT = self._processedLines.pop() # Get the previous line
                                if adjText or lastAM != 'v': # Just return it again
                                    self._processedLines.append( InternalBibleEntry(lastAM, lastOM, lastAT, lastCT, lastX, lastOT) )
                                self._processedLines.append( InternalBibleEntry('p', originalMarker, adjText, cleanText, extras,originalText) )
                                if lastAM == 'v' and not adjText: # Put the empty paragraph marker BEFORE verse number marker
                                    self._processedLines.append( InternalBibleEntry(lastAM, lastOM, lastAT, lastCT, lastX, lastOT) ) # Return it
                                text = afterText
                                ixLT = -1
                        ixLT = text.find( '<', ixLT+1 )
                    # OSIS strings aren't fixed coz they contain varying ID and reference fields
                    ixLT = text.find( '<' )
                    #if ixLT != -1: print( "text", "'"+text+"'" )
                    while ixLT != -1:
                        ixGT = text.find( '>', ixLT+1 )
                        if Globals.debugFlag: assert( ixGT != -1 )
                        beforeText = text[:ixLT]
                        thisField = text[ixLT:ixGT+1]
                        afterText = text[ixGT+1:]
                        #print( "before", "'"+beforeText+"'" )
                        #print( "this", "'"+thisField+"'" )
                        #print( "after", "'"+afterText+"'" )
                        if thisField.startswith( '<div type="x-milestone" subType="x-preverse" sID="' ) and thisField.endswith( '"/>' ):
                            ixEnd = afterText.index( '<div type="x-milestone" subType="x-preverse" eID="' )
                            ixFinal = afterText.index( '>', ixEnd+30 )
                            preverseText = afterText[:ixEnd].strip()
                            #print( "QQQ11: strip" ); halt
                            if preverseText.startswith( '<div sID="' ) and preverseText.endswith( '" type="paragraph"/>' ):
                                self._processedLines.append( InternalBibleEntry('p', originalMarker, '', '', InternalBibleExtraList(), originalText) )
                            else: print( "preverse", "'"+preverseText+"'" )
                            text = beforeText + afterText[ixFinal+1:]
                        elif thisField.startswith( '<div sID="' ) and thisField.endswith( '" type="paragraph"/>' ):
                            self._processedLines.append( InternalBibleEntry('p', originalMarker, '', '', InternalBibleExtraList(), originalText) )
                            text = beforeText + afterText
                        #elif thisField.startswith( '<div eID="' ) and thisField.endswith( '" type="paragraph"/>' ):
                            #self._processedLines.append( InternalBibleEntry('m', originalMarker, '', '', InternalBibleExtraList()) )
                            #text = beforeText + afterText
                        elif thisField == '<note>':
                            ixEND = afterText.index( '</note>' )
                            note = afterText[:ixEND]
                            #print( "note", "'"+note+"'" )
                            noteIX = len( beforeText )
                            # Save note in extras
                            text = beforeText + afterText[ixEND+7:]
                        elif thisField.startswith( '<l level="' ) and thisField.endswith( '"/>' ):
                            levelDigit = thisField[10]
                            if Globals.debugFlag:
                                assert( thisField[11] == '"' )
                                assert( levelDigit.isdigit() )
                            self._processedLines.append( InternalBibleEntry('q'+levelDigit, originalMarker, '', '', InternalBibleExtraList(), originalText) )
                            text = beforeText + afterText
                        elif thisField.startswith( '<lg sID="' ) and thisField.endswith( '"/>' ):
                            self._processedLines.append( InternalBibleEntry('qx', originalMarker, '', '', InternalBibleExtraList(), originalText) )
                            text = beforeText + afterText
                        elif thisField.startswith( '<chapter osisID="' ) and thisField.endswith( '"/>' ):
                            if 0: # Don't actually need this stuff
                                ixDQ = thisField.index( '"', 17 )
                                #assert( ixDQ != -1 )
                                osisID = thisField[17:ixDQ]
                                #print( "osisID", "'"+osisID+"'" )
                                ixDOT = osisID.index( '.' )
                                #assert( ixDOT != -1 )
                                chapterDigits = osisID[ixDOT+1:]
                                #print( "chapter", chapterDigits )
                                self._processedLines.append( InternalBibleEntry('c~', originalMarker, chapterDigits, chapterDigits, InternalBibleExtraList(), originalText) )
                            text = beforeText + afterText
                        elif ( thisField.startswith( '<chapter eID="' ) or thisField.startswith( '<l eID="' ) or thisField.startswith( '<lg eID="' ) or thisField.startswith( '<div eID="' ) ) \
                        and thisField.endswith( '"/>' ):
                            text = beforeText + afterText # We just ignore it
                        ixLT = text.find( '<', ixLT+1 )
            #if v == '5':
                #for n in range( 0, 30 ): print( "\n{}: {}".format( n, self._processedLines[n] ) )
                #halt

            #print( "doAppend", adjustedMarker, originalMarker, repr(text), repr(originalText) )
            #print( " ", verseNumberRest if originalMarker=='v' and adjustedMarker=='v~' else originalText )
            doAppend( adjustedMarker, originalMarker, text, verseNumberRest if originalMarker=='v' and adjustedMarker=='v~' else originalText )
            ## Separate out the notes (footnotes and cross-references)
            #adjText, cleanText, extras = processLineFix( originalMarker, text )

            ##if adjustedMarker=='v~' and not cleanText:
                ##if text or adjText:
                    ##print( "Suppressed blank v~ for", self.bookReferenceCode, c, v, "'"+text+"'", "'"+adjText+"'" ); halt

            ## From here on, we use adjText (not text)
            ##print( "marker '{}' text '{}', adjText '{}'".format( adjustedMarker, text, adjText ) )
            #if not adjText and not extras and ( Globals.USFMMarkers.markerShouldHaveContent(adjustedMarker)=='A' or adjustedMarker in ('v~','c~','c#',) ): # should always have text
                ##print( "processLine: marker should always have text (ignoring it):", self.bookReferenceCode, c, v, originalMarker, adjustedMarker, " originally '"+text+"'" )
                #fixErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '{}' should always have text").format( originalMarker ) )
                #if self.objectTypeString in ('USFM','USX',):
                    #if sahtCount != -1:
                        #sahtCount += 1
                        #if sahtCount <= MAX_NONCRITICAL_ERRORS_PER_BOOK:
                            #logging.error( _("Marker '{}' at {} {}:{} should always have text").format( originalMarker, self.bookReferenceCode, c, v ) )
                        #else: # we've reached our limit
                            #logging.error( _('Additional "Marker should always have text" messages suppressed...') )
                            #sahtCount = -1 # So we don't do this again (for this book)
                #self.addPriorityError( 96, c, v, _("Marker \\{} should always have text").format( originalMarker ) )
                ## Don't bother even saving the marker since it's useless
                ## Wrong -- save the empty marker
                #if adjustedMarker != 'v~': # Save all other empty markers
                    #self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, adjText, cleanText, extras) )
            #else:
                ##if c=='5' and v=='29': print( "processLine: {} '{}' to {} aT='{}' cT='{}' {}".format( originalMarker, text, adjustedMarker, adjText, cleanText, extras ) );halt
                #self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, adjText, cleanText, extras) )
        # end of InternalBibleBook.processLines.processLine


        nfvnCount = owfvnCount = rtsCount = sahtCount = 0
        fixErrors = []
        self._processedLines = InternalBibleEntryList() # Contains more-processed tuples which contain the actual Bible text -- see below
        c = v = '0'
        haveWaitingC = False
        for marker,text in self._rawLines:
            #print( "\nQQQ" )
            if self.objectTypeString=='USX' and text and text[-1]==' ': text = text[:-1] # Removing extra trailing space from USX files
            processLine( marker, text ) # Saves its results in self._processedLines
        #self.debugPrint(); halt
        #if not Globals.debugFlag:
        del self._rawLines # if short of memory
        try: del self.tree # for xml Bible types (some Bible books caused a segfault when pickled with this data)
        except AttributeError: pass

        if fixErrors: self.errorDictionary['Fix Text Errors'] = fixErrors
        self._processedFlag = True
        self.makeIndex()
    # end of InternalBibleBook.processLines


    def makeIndex( self ):
        """
        Index the lines for faster reference.

        """
        if Globals.debugFlag:
            assert( self._processedFlag )
            assert( not self._indexedFlag )
        if self._indexedFlag: return # Can only do it once

        if Globals.verbosityLevel > 2: print( "  " + _("Indexing {} {} {} text...").format( self.objectNameString, self.name, self.bookReferenceCode ) )
        self._CVIndex = InternalBibleIndex( self.name, self.bookReferenceCode )
        self._CVIndex.makeIndex( self._processedLines )

        if 0 and self.bookReferenceCode=='GEN':
            for j, entry in enumerate( self._processedLines):
                cleanText = entry.getCleanText()
                print( j, entry.getMarker(), cleanText[:60] + ('' if len(cleanText)<60 else '...') )
                #if j>breakAt: break
            def getKey( CVALX ):
                CV, ALX = CVALX
                C, V = CV
                try: Ci = int(C)
                except: Ci = 300
                try: Vi = int(V)
                except: Vi = 300
                return Ci*1000 + Vi
            for CV,ALX in sorted(self._CVIndex.items(), key=getKey): #lambda s: int(s[0][0])*1000+int(s[0][1])): # Sort by C*1000+V
                C, V = CV
                #A, L, X = ALX
                print( "{}:{}={},{},{}".format( C, V, ALX.getEntryIndex(), ALX.getEntryCount(), ALX.getContext() ), end='  ' )
            halt
        self._indexedFlag = True
    # end of InternalBibleBook.makeIndex


    def debugPrint( self ):
        """
        """
        print( "InternalBibleBook.debugPrint: {}".format( self.bookReferenceCode ) )
        numLines = 30
        for j in range( 0, min( numLines, len(self._rawLines) ) ):
            print( " Raw {}: {} = {}".format( j, self._rawLines[j][0], repr(self._rawLines[j][1]) ) )
        for j in range( 0, min( numLines, len(self._processedLines) ) ):
            print( " Proc {}: {}{} = {}".format( j, self._processedLines[j][0], '('+self._processedLines[j][1]+')' if self._processedLines[j][1]!=self._processedLines[j][0] else '', repr(self._processedLines[j][2]) ) )
    # end of InternalBibleBook.debugPrint


    def validateMarkers( self ):
        """
        Validate the loaded book.

        This does a quick check for major SFM errors. It is not as thorough as checkSFMs below.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )
        validationErrors = []

        c = v = '0'
        for j, entry in enumerate(self._processedLines):
            marker, text = entry.getMarker(), entry.getText()
            #print( marker, text[:40] )

            # Keep track of where we are for more helpful error messages
            if marker == 'c':
                if text: c = text.split()[0]
                else:
                    validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing chapter number").format( self.bookReferenceCode, c, v ) )
                    logging.error( _("Missing chapter number after") + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                v = '0'
            if marker == 'v':
                if text: v = text.split()[0]
                else:
                    validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing verse number").format( self.bookReferenceCode, c, v ) )
                    logging.error( _("Missing verse number after") + " {} {}:{}".format( self.bookReferenceCode, c, v ) )

            # Temporarily substitute some markers just to make this check go easier
            if marker == 'v~': marker = 'v'
            if marker == 'p~': marker = 'v'

            # Do a rough check of the SFMs
            if marker=='id' and j!=0:
                validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker 'id' should only appear as the first marker in a book but found on line {} in {}: {}").format( j+1, marker, text ) )
                logging.error( _("Marker 'id' should only appear as the first marker in a book but found on line {} after {} {}:{} in {}: {}").format( j+1, self.bookReferenceCode, c, v, marker, text ) )
            if not Globals.USFMMarkers.isNewlineMarker( marker ) and marker not in ('c#',):
                validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected '\\{}' newline marker in Bible book (Text is '{}')").format( marker, text ) )
                logging.warning( _("Unexpected '\\{}' newline marker in Bible book after {} {}:{} (Text is '{}')").format( marker, self.bookReferenceCode, c, v, text ) )
            if Globals.USFMMarkers.isDeprecatedMarker( marker ):
                validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Deprecated '\\{}' newline marker in Bible book (Text is '{}')").format( marker, text ) )
                logging.warning( _("Deprecated '\\{}' newline marker in Bible book after {} {}:{} (Text is '{}')").format( marker, self.bookReferenceCode, c, v, text ) )
            markerList = Globals.USFMMarkers.getMarkerListFromText( text )
            #if markerList: print( "\nText = {}:'{}'".format(marker,text)); print( markerList )
            for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check character markers
                if Globals.USFMMarkers.isDeprecatedMarker( insideMarker ):
                    validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Deprecated '\\{}' internal marker in Bible book (Text is '{}')").format( insideMarker, text ) )
                    logging.warning( _("Deprecated '\\{}' internal marker in Bible book after {} {}:{} (Text is '{}')").format( insideMarker, self.bookReferenceCode, c, v, text ) )
            ix = 0
            for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check newline markers
                if Globals.USFMMarkers.isNewlineMarker(insideMarker):
                    validationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '\\{}' must not appear within line in {}: {}").format( insideMarker, marker, text ) )
                    logging.error( _("Marker '\\{}' must not appear within line after {} {}:{} in {}: {}").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) )

        if validationErrors: self.errorDictionary['Validation Errors'] = validationErrors
    # end of InternalBibleBook.validateMarkers


    def getField( self, fieldName ):
        """
        Extract a SFM field from the loaded book.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag:
            assert( self._processedLines )
            assert( fieldName and isinstance( fieldName, str ) )
        adjFieldName = Globals.USFMMarkers.toStandardMarker( fieldName )

        for entry in self._processedLines:
            if entry.getMarker() == adjFieldName:
                if Globals.debugFlag: assert( not entry.getExtras() )
                return entry.getText()
    # end of InternalBibleBook.getField


    def getAssumedBookNames( self ):
        """
        Attempts to deduce a bookname from the loaded book.
        Use the English name as a last resort.
        Returns a list with the best guess first.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )
        results = []

        header = self.getField( 'h' )
        if header:
            if header.isupper(): header = header.title()
            results.append( header )

        if (not header or len(header)<4 or not header[0].isdigit() or header[1]!=' ') and self.getField('mt2') is not None: # Ignore the main title if it's a book like "Corinthians" and there's a mt2 (like "First")
            mt1 = self.getField( 'mt1' )
            if mt1:
                if mt1.isupper(): mt1 = mt1.title()
                if mt1 not in results: results.append( mt1 )

        if not results: # no helpful fields in file
            results.append( Globals.BibleBooksCodes.getEnglishName_NR( self.bookReferenceCode ) )

        #if Globals.debugFlag or Globals.verbosityLevel > 3: # Print our level of confidence
        #    if header is not None and header==mt1: assert( bookName == header ); print( "getBookName: header and main title are both '{}'".format( bookName ) )
        #    elif header is not None and mt1 is not None: print( "getBookName: header '{}' and main title '{}' are both different so selected '{}'".format( header, mt1, bookName ) )
        #    elif header is not None or mt1 is not None: print( "getBookName: only have one of header '{}' or main title '{}'".format( header, mt1 ) )
        #    else: print( "getBookName: no header or main title so used English book name '{}'".format( bookName ) )
        if (Globals.debugFlag and debuggingThisModule) or Globals.verbosityLevel > 3: # Print our level of confidence
            print( "Assumed bookname(s) of {} for {}".format( results, self.bookReferenceCode ) )

        return results
    # end of InternalBibleBook.getAssumedBookNames


    def getVersification( self ):
        """
        Get the versification of the book into a two lists of (c, v) tuples.
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
        Note that all chapter and verse values are returned as strings not integers.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )
        versificationErrors = []

        versification, omittedVerses, combinedVerses, reorderedVerses = [], [], [], []
        chapterText, chapterNumber, lastChapterNumber = '0', 0, 0
        verseText = verseNumberString = lastVerseNumberString = '0'
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            #print( marker, text )
            if marker == 'c':
                if chapterNumber > 0:
                    versification.append( (chapterText, lastVerseNumberString,) )
                chapterText = text.strip()
                if ' ' in chapterText: # Seems that we can have footnotes here :)
                    versificationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, chapterText, verseNumberString ) + _("Unexpected space in USFM chapter number field '{}'").format( self.bookReferenceCode, lastChapterNumber, lastVerseNumberString, chapterText, lastChapterNumber ) )
                    logging.info( _("Unexpected space in USFM chapter number field '{}' after chapter {} of {}").format( chapterText, lastChapterNumber, self.bookReferenceCode ) )
                    chapterText = chapterText.split( None, 1)[0]
                #print( "{} chapter {}".format( self.bookReferenceCode, chapterText ) )
                chapterNumber = int( chapterText)
                if chapterNumber != lastChapterNumber+1:
                    versificationErrors.append( _("{} ({} after {}) USFM chapter numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                    logging.error( _("USFM chapter numbers out of sequence in Bible book {} ({} after {})").format( self.bookReferenceCode, chapterNumber, lastChapterNumber ) )
                lastChapterNumber = chapterNumber
                verseText = verseNumberString = lastVerseNumberString = '0'
            elif marker == 'cp':
                versificationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, chapterText, verseNumberString ) + _("Encountered cp field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, text ) )
                logging.warning( _("Encountered cp field {} after {}:{} of {}").format( text, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
            elif marker == 'v':
                if chapterText == '0':
                    versificationErrors.append( _("{} {} Missing chapter number field before verse {}").format( self.bookReferenceCode, chapterText, text ) )
                    logging.warning( _("Missing chapter number field before verse {} in chapter {} of {}").format( text, chapterText, self.bookReferenceCode ) )
                if not text:
                    versificationErrors.append( _("{} {} Missing USFM verse number after v{}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString ) )
                    logging.warning( _("Missing USFM verse number after v{} in chapter {} of {}").format( lastVerseNumberString, chapterNumber, self.bookReferenceCode ) )
                    continue
                verseText = text
                doneWarning = False
                for char in 'abcdefghijklmnopqrstuvwxyz[]()\\':
                    if char in verseText:
                        if not doneWarning:
                            versificationErrors.append( _("{} {} Removing letter(s) from USFM verse number {} in Bible book").format( self.bookReferenceCode, chapterText, verseText ) )
                            logging.info( _("Removing letter(s) from USFM verse number {} in Bible book {} {}").format( verseText, self.bookReferenceCode, chapterText ) )
                            doneWarning = True
                        verseText = verseText.replace( char, '' )
                if '-' in verseText or '–' in verseText: # we have a range like 7-9 with hyphen or en-dash
                    #versificationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, chapterText, verseNumberString ) + _("Encountered combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    logging.info( _("Encountered combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.replace('–','-').split( '-', 1 ) # Make sure that it's a hyphen then split once
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse range start '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse range start '{}' in '{}' in Bible book {} {}").format( verseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse range end '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, endVerseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse range end '{}' in '{}' in Bible book {} {}").format( endVerseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse range out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        logging.error( _("USFM verse range out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                elif ',' in verseText: # we have a range like 7,8
                    versificationErrors.append( "{} {}:{} ".format( self.bookReferenceCode, chapterText, verseNumberString ) + _("Encountered comma combined verses field {}").format( self.bookReferenceCode, chapterNumber, lastVerseNumberString, verseText ) )
                    logging.info( _("Encountered comma combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.bookReferenceCode ) )
                    bits = verseText.split( ',', 1 )
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse list start '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse list start '{}' in '{}' in Bible book {} {}").format( verseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except:
                        versificationErrors.append( _("{} {} Invalid USFM verse list end '{}' in '{}' in Bible book").format( self.bookReferenceCode, chapterText, endVerseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse list end '{}' in '{}' in Bible book {} {}").format( endVerseNumberString, verseText, self.bookReferenceCode, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse list out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                        logging.error( _("USFM verse list out of sequence in Bible book {} {} ({}-{})").format( self.bookReferenceCode, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                else: # Should be just a single verse number
                    verseNumberString = verseText
                    endVerseNumberString = verseNumberString
                try:
                    verseNumber = int( verseNumberString )
                except:
                    versificationErrors.append( _("{} {} {} Invalid verse number digits in Bible book").format( self.bookReferenceCode, chapterText, verseNumberString ) )
                    logging.error( _("Invalid verse number digits in Bible book {} {} {}").format( self.bookReferenceCode, chapterText, verseNumberString ) )
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
                        versificationErrors.append( _("{} {} ({} after v{}) USFM verse numbers out of sequence in Bible book").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        logging.warning( _("USFM verse numbers out of sequence in Bible book {} {} ({} after v{})").format( self.bookReferenceCode, chapterText, verseText, lastVerseNumberString ) )
                        reorderedVerses.append( (chapterText, lastVerseNumberString, verseText,) )
                    else: # Must be missing some verse numbers
                        versificationErrors.append( _("{} {} Missing USFM verse number(s) between {} and {} in Bible book").format( self.bookReferenceCode, chapterText, lastVerseNumberString, verseNumberString ) )
                        logging.info( _("Missing USFM verse number(s) between {} and {} in Bible book {} {}").format( lastVerseNumberString, verseNumberString, self.bookReferenceCode, chapterText ) )
                        for number in range( lastVerseNumber+1, verseNumber ):
                            omittedVerses.append( (chapterText, str(number),) )
                lastVerseNumberString = endVerseNumberString
        versification.append( (chapterText, lastVerseNumberString,) ) # Append the verse count for the final chapter
        #if reorderedVerses: print( "Reordered verses in", self.bookReferenceCode, "are:", reorderedVerses )
        if versificationErrors: self.errorDictionary['Versification Errors'] = versificationErrors
        return versification, omittedVerses, combinedVerses, reorderedVerses
    # end of InternalBibleBook.getVersification


    def discover( self, resultDictionary ):
        """
        Do a precheck on the book to try to determine its features.

        We later use these discoveries to note when the translation veers from their norm.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )
        #print( "InternalBibleBook:discover", self.bookReferenceCode )
        if Globals.debugFlag: assert( isinstance( resultDictionary, dict ) )

        bkDict = {}
        bkDict['chapterCount'] = bkDict['verseCount'] = bkDict['percentageProgress'] = None
        bkDict['completedVerseCount'] = 0
        bkDict['havePopulatedCVmarkers'] = bkDict['haveParagraphMarkers'] = bkDict['haveIntroductoryMarkers'] = False
        bkDict['haveSectionHeadings'] = False; bkDict['sectionHeadingsCount'] = 0
        bkDict['haveSectionReferences'] = False
        bkDict['haveFootnotes'] = bkDict['haveFootnoteOrigins'] = False
        bkDict['haveCrossReferences'] = bkDict['haveCrossReferenceOrigins'] = False
        bkDict['sectionReferencesCount'] = bkDict['footnotesCount'] = bkDict['crossReferencesCount'] = 0
        bkDict['sectionReferencesParenthesisRatio'] = bkDict['footnotesPeriodsRatio'] = bkDict['xrefsPeriodsRatio'] = -1.0
        bkDict['haveIntroductoryText'] = bkDict['haveVerseText'] = False
        bkDict['haveNestedUSFMarkers'] = False
        bkDict['seemsFinished'] = None

        sectionRefParenthCount = footnotesPeriodCount = xrefsPeriodCount = 0

        c = v = '0'
        lastMarker = None
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                c = text.split()[0]; v = '0'
                if bkDict['chapterCount'] is None: bkDict['chapterCount'] = 1
                else: bkDict['chapterCount'] += 1
            elif marker=='v' and text:
                v = text.split()[0]
                if bkDict['verseCount'] is None: bkDict['verseCount'] = 1
                else: bkDict['verseCount'] += 1
                if bkDict['chapterCount'] is None: # Some single chapter books don't have \c 1 explicitly encoded
                    if Globals.debugFlag: assert( c == '0' )
                    c = '1'
                    bkDict['chapterCount'] = 1
                bkDict['havePopulatedCVmarkers'] = True
                if bkDict['seemsFinished'] is None: bkDict['seemsFinished'] = True
            elif marker=='v~' and text:
                bkDict['haveVerseText'] = True
                bkDict['completedVerseCount'] += 1
            elif marker in ('s1','s2','s3'):
                bkDict['haveSectionHeadings'] = True
                bkDict['sectionHeadingsCount'] += 1
            elif marker=='r' and text:
                bkDict['haveSectionReferences'] = True
                bkDict['sectionReferencesCount'] += 1
                if cleanText[0]=='(' and cleanText[-1]==')': sectionRefParenthCount += 1
            elif marker in Globals.USFMParagraphMarkers:
                bkDict['haveParagraphMarkers'] = True
                if text: bkDict['haveVerseText'] = True
            elif marker in ('ip',):
                bkDict['haveIntroductoryMarkers'] = True
                if text: bkDict['haveIntroductoryText'] = True

            if '\\+' in text: bkDict['haveNestedUSFMarkers'] = True
            if lastMarker=='v' and (marker!='v~' or not text): bkDict['seemsFinished'] = False

            for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras():
                if Globals.debugFlag:
                    assert( extraText ) # Shouldn't be blank
                    #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                    assert( extraIndex >= 0 )
                    #assert( 0 <= extraIndex <= len(text)+3 )
                    assert( extraType in ('fn','xr',) )
                if extraType=='fn':
                    bkDict['haveFootnotes'] = True
                    bkDict['footnotesCount'] += 1
                    if '\\fr' in extraText: bkDict['haveFootnoteOrigins'] = True
                    if cleanExtraText.endswith('.') or cleanExtraText.endswith('.”'): footnotesPeriodCount += 1
                elif extraType=='xr':
                    bkDict['haveCrossReferences'] = True
                    bkDict['crossReferencesCount'] += 1
                    if '\\xo' in extraText: bkDict['haveCrossReferenceOrigins'] = True
                    if cleanExtraText.endswith('.') or cleanExtraText.endswith('.”'): xrefsPeriodCount += 1
            lastMarker = marker

        if bkDict['verseCount'] is None: # Things like front and end matter (don't have verse numbers)
            for aKey in ('verseCount','seemsFinished','chapterCount','percentageProgress',):
                #assert( bkDict[aKey] is None \
                    #or ( aKey=='chapterCount' and bkDict[aKey]==1 ) ) # Some people put a chapter count in their front matter, glossary, etc.
                if bkDict[aKey] is not None and ( aKey!='chapterCount' or bkDict[aKey]!=1 ):
                    # Some people put a chapter count in their front matter, glossary, etc.
                    logging.debug( "InternalBibleBook.discover: ToProgrammer -- Some wrong in {} here. Why? '{}' '{}'".format( self.bookReferenceCode, aKey, bkDict[aKey] ) )
                del bkDict[aKey]
        else: # Do some finalizing to do with verse counts
            if bkDict['verseCount'] is not None:
                bkDict['percentageProgress'] = round( bkDict['completedVerseCount'] * 100 / bkDict['verseCount'] )
                if bkDict['percentageProgress'] > 100:
                    logging.info( "Adjusting percentageProgress from {} back to 100%".format( bkDict['percentageProgress'] ) )
                    bkDict['percentageProgress'] = 100

            #print( self.bookReferenceCode, bkDict )
            if bkDict['seemsFinished']:
                #print( self.bookReferenceCode )
                #print( bkDict['percentageProgress'] )
                #print( bkDict['havePopulatedCVmarkers'] )
                #print( bkDict['haveVerseText'] )
                assert( bkDict['percentageProgress']==100 and bkDict['havePopulatedCVmarkers'] and bkDict['haveVerseText'] )
            if not bkDict['haveVerseText']: assert( bkDict['percentageProgress']==0 and not bkDict['seemsFinished'] )
            bkDict['notStarted'] = not bkDict['haveVerseText']
            bkDict['partlyDone'] = bkDict['haveVerseText'] and not bkDict['seemsFinished']

        if bkDict['sectionReferencesCount']:
            bkDict['sectionReferencesParenthesisRatio'] = sectionRefParenthCount / bkDict['sectionReferencesCount']
            bkDict['sectionReferencesParenthesisFlag'] = bkDict['sectionReferencesParenthesisRatio'] > 0.8
        if bkDict['footnotesCount']:
            bkDict['footnotesPeriodRatio'] = footnotesPeriodCount / bkDict['footnotesCount']
            bkDict['footnotesPeriodFlag'] = bkDict['footnotesPeriodRatio'] > 0.7
        if bkDict['crossReferencesCount']:
            bkDict['crossReferencesPeriodRatio'] = xrefsPeriodCount / bkDict['crossReferencesCount']
            bkDict['crossReferencesPeriodFlag'] = bkDict['crossReferencesPeriodRatio'] > 0.7
        #print( self.bookReferenceCode, bkDict['sectionReferencesParenthesisRatio'] )

        # Put the result for this book into the main dictionary
        resultDictionary[self.bookReferenceCode] = bkDict
    # end of InternalBibleBook.discover


    def getAddedUnits( self ):
        """
        Get the units added to the text of the book including paragraph breaks, section headings, and section references.
        Note that all chapter and verse values are returned as strings not integers.
        """
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )
        addedUnitErrors = []

        paragraphReferences, qReferences, sectionHeadingReferences, sectionHeadings, sectionReferenceReferences, sectionReferences, wordsOfJesus = [], [], [], [], [], [], []
        chapterNumberStr = verseNumberStr = '0'
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            #print( "InternalBibleBook.getAddedUnits", chapterNumberStr, verseNumberStr, marker, cleanText )
            if marker == 'c':
                chapterNumberStr = text.split( None, 1 )[0]
                verseNumberStr = '0'
            elif marker == 'cp':
                cpChapterText = text.split( None, 1 )[0]
                if Globals.verbosityLevel > 2: print( "In {}, chapter text went from '{}' to '{}' with cp marker".format( self.bookReferenceCode, chapterNumberStr, cpChapterText ) )
                chapterNumberStr = cpChapterText
                if len(chapterNumberStr)>2 and chapterNumberStr[0]=='(' and chapterNumberStr[-1]==')': chapterNumberStr = chapterNumberStr[1:-1] # Remove parenthesis -- NOT SURE IF WE REALLY WANT TO DO THIS OR NOT ???
                verseNumberStr = '0'
            elif marker == 'v':
                #print( self.bookReferenceCode, chapterNumberStr, marker, text )
                if not text:
                    addedUnitErrors.append( _("{} {} Missing USFM verse number after v{}").format( self.bookReferenceCode, chapterNumberStr, verseNumberStr ) )
                    logging.warning( _("Missing USFM verse number after v{} in chapter {} of {}").format( verseNumberStr, chapterNumberStr, self.bookReferenceCode ) )
                    self.addPriorityError( 86, chapterNumberStr, verseNumberStr, _("Missing verse number") )
                    continue
                verseNumberStr = text
            elif marker == 'p':
                reference = primeReference = (chapterNumberStr,verseNumberStr,)
                while reference in paragraphReferences: # Must be a single verse broken into multiple paragraphs
                    if Globals.debugFlag: assert( primeReference in paragraphReferences )
                    if reference == primeReference: reference = (chapterNumberStr,verseNumberStr,'a',) # Append a suffix
                    else: # Already have a suffix
                        reference = (chapterNumberStr,verseNumberStr,chr(ord(reference[2])+1),) # Just increment the suffix
                paragraphReferences.append( reference )
            elif len(marker)==2 and marker[0]=='q' and marker[1].isdigit():# q1, q2, etc.
                reference = primeReference = (chapterNumberStr,verseNumberStr,)
                while reference in qReferences: # Must be a single verse broken into multiple segments
                    if Globals.debugFlag: assert( primeReference in qReferences )
                    if reference == primeReference: reference = (chapterNumberStr,verseNumberStr,'a',) # Append a suffix
                    else: # Already have a suffix
                        reference = (chapterNumberStr,verseNumberStr,chr(ord(reference[2])+1),) # Just increment the suffix
                level = int( marker[1] ) # 1, 2, etc.
                qReferences.append( (reference,level,) )
            elif len(marker)==2 and marker[0]=='s' and marker[1].isdigit():# s1, s2, etc.
                if text and text[-1].isspace(): print( self.bookReferenceCode, chapterNumberStr, verseNumberStr, marker, "'"+text+"'" )
                reference = (chapterNumberStr,verseNumberStr,)
                level = int( marker[1] ) # 1, 2, etc.
                #levelReference = (level,reference,)
                adjText = text.strip().replace('\\nd ','').replace('\\nd*','')
                #print( self.bookReferenceCode, reference, levelReference, marker, text )
                #assert( levelReference not in sectionHeadingReferences ) # Ezra 10:24 can have two s3's in one verse (first one is blank so it uses the actual verse text)
                #sectionHeadingReferences.append( levelReference ) # Just for checking
                sectionHeadings.append( (reference,level,adjText,) ) # This is the real data
            elif marker == 'r':
                reference = (chapterNumberStr,verseNumberStr,)
                if Globals.debugFlag: assert( reference not in sectionReferenceReferences ) # Shouldn't be any cases of two lots of section references within one verse boundary
                sectionReferenceReferences.append( reference ) # Just for checking
                sectionReferenceText = text
                if sectionReferenceText and sectionReferenceText[0]=='(' and sectionReferenceText[-1]==')':
                    sectionReferenceText = sectionReferenceText[1:-1] # Remove parenthesis
                sectionReferences.append( (reference,sectionReferenceText,) ) # This is the real data

            if 'wj' in text:
                reference = (chapterNumberStr,verseNumberStr)
                #print( "InternalBibleBook.getAddedUnits", chapterNumberStr, verseNumberStr, marker, cleanText )
                #print( " ", marker, text )
                wjCount = text.count( 'wj' ) // 2 # Assuming that half of them are \wj* end markers
                wjFirst, wjLast = text.startswith( '\\wj ' ), text.endswith( '\\wj*' )
                wjInfo = (entry.getOriginalMarker(),wjCount,wjFirst,wjLast,)
                wordsOfJesus.append( (reference,wjInfo,) ) # This is the real data

        if addedUnitErrors: self.errorDictionary['Added Unit Errors'] = addedUnitErrors
        if Globals.debugFlag: assert( len(paragraphReferences) == len(set(paragraphReferences)) ) # No duplicates
        return paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus
    # end of InternalBibleBook.getAddedUnits


    def doCheckAddedUnits( self, typicalAddedUnitData, severe=False ):
        """
        Get the units added to the text of the book including paragraph breaks, section headings, and section references.
        Note that all chapter and verse values are returned as strings not integers.
        """
        typicalParagraphs, typicalQParagraphs, typicalSectionHeadings, typicalSectionReferences, typicalWordsOfJesus = typicalAddedUnitData
        paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = self.getAddedUnits() # For this object

        addedUnitNotices = []
        if self.bookReferenceCode in typicalParagraphs:
            for reference in typicalParagraphs[self.bookReferenceCode]:
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                c, v = reference[0], reference[1]
                if len(reference)==3: v += reference[2] # append the suffix
                typical = typicalParagraphs[self.bookReferenceCode][reference]
                if Globals.debugFlag: assert( typical in ('A','S','M','F') )
                if reference in paragraphReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Paragraph break is less common after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Paragraph break is less common after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 17, c, v, _("Less common to have a paragraph break after field") )
                        #print( "Surprise", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, c, v, _("Less common to have a paragraph break after field") )
                        #print( "Yeah", self.bookReferenceCode, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Paragraph break normally inserted after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Paragraph break normally inserted after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 27, c, v, _("Paragraph break normally inserted after field") )
                        #print( "All", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, c, v, _("Paragraph break often inserted after field") )
                        #print( "Most", self.bookReferenceCode, reference, typical, present )
            for reference in paragraphReferences: # now check for ones in this book but not typically there
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                if reference not in typicalParagraphs[self.bookReferenceCode]:
                    c, v = reference[0], reference[1]
                    if len(reference)==3: v += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Paragraph break is unusual after v{}").format( self.bookReferenceCode, c, v ) )
                    logging.info( _("Paragraph break is unusual after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                    self.addPriorityError( 37, c, v, _("Unusual to have a paragraph break after field") )
                    #print( "Weird paragraph after", self.bookReferenceCode, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no paragraph info available").format( self.bookReferenceCode ) )
            logging.info( _("{} No paragraph info available").format( self.bookReferenceCode ) )
            self.addPriorityError( 3, '-', '-', _("No paragraph info for '{}' book").format( self.bookReferenceCode ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = OrderedDict() # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Paragraphing Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.bookReferenceCode in typicalQParagraphs:
            for entry in typicalQParagraphs[self.bookReferenceCode]:
                reference, level = entry
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                c, v = reference[0], reference[1]
                if len(reference)==3: v += reference[2] # append the suffix
                typical = typicalQParagraphs[self.bookReferenceCode][entry]
                #print( reference, c, v, level, typical )
                if Globals.debugFlag: assert( typical in ('A','S','M','F') )
                if reference in qReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Quote Paragraph is less common after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Quote Paragraph is less common after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 17, c, v, _("Less common to have a Quote Paragraph after field") )
                        #print( "Surprise", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, c, v, _("Less common to have a Quote Paragraph after field") )
                        #print( "Yeah", self.bookReferenceCode, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Quote Paragraph normally inserted after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Quote Paragraph normally inserted after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 27, c, v, _("Quote Paragraph normally inserted after field") )
                        #print( "All", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, c, v, _("Quote Paragraph often inserted after field") )
                        #print( "Most", self.bookReferenceCode, reference, typical, present )
            for reference in qReferences: # now check for ones in this book but not typically there
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                if reference not in typicalQParagraphs[self.bookReferenceCode]:
                    c, v = reference[0], reference[1]
                    if len(reference)==3: v += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Quote Paragraph is unusual after v{}").format( self.bookReferenceCode, c, v ) )
                    logging.info( _("Quote Paragraph is unusual after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                    self.addPriorityError( 37, c, v, _("Unusual to have a Quote Paragraph after field") )
                    #print( "Weird qParagraph after", self.bookReferenceCode, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no quote paragraph info available").format( self.bookReferenceCode ) )
            logging.info( _("{} No quote paragraph info available").format( self.bookReferenceCode ) )
            self.addPriorityError( 3, '-', '-', _("No quote paragraph info for '{}' book").format( self.bookReferenceCode ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = OrderedDict() # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Indenting Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.bookReferenceCode in typicalSectionHeadings:
            for entry in typicalSectionHeadings[self.bookReferenceCode]:
                reference, level = entry
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                c, v = reference[0], reference[1]
                if len(reference)==3: v += reference[2] # append the suffix
                typical = typicalSectionHeadings[self.bookReferenceCode][entry]
                #print( reference, c, v, level, typical )
                if Globals.debugFlag: assert( typical in ('A','S','M','F') )
                if reference in sectionHeadings:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Section Heading is less common after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Section Heading is less common after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 17, c, v, _("Less common to have a Section Heading after field") )
                        #print( "Surprise", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, c, v, _("Less common to have a Section Heading after field") )
                        #print( "Yeah", self.bookReferenceCode, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Section Heading normally inserted after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Section Heading normally inserted after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 27, c, v, _("Section Heading normally inserted after field") )
                        #print( "All", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, c, v, _("Section Heading often inserted after field") )
                        #print( "Most", self.bookReferenceCode, reference, typical, present )
            for entry in sectionHeadings: # now check for ones in this book but not typically there
                reference, level, text = entry
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                if (reference,level) not in typicalSectionHeadings[self.bookReferenceCode]:
                    c, v = reference[0], reference[1]
                    if len(reference)==3: v += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Section Heading is unusual after v{}").format( self.bookReferenceCode, c, v ) )
                    logging.info( _("Section Heading is unusual after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                    self.addPriorityError( 37, c, v, _("Unusual to have a Section Heading after field") )
                    #print( "Weird section heading after", self.bookReferenceCode, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no section heading info available").format( self.bookReferenceCode ) )
            logging.info( _("{} No section heading info available").format( self.bookReferenceCode ) )
            self.addPriorityError( 3, '-', '-', _("No section heading info for '{}' book").format( self.bookReferenceCode ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = OrderedDict() # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Section Heading Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.bookReferenceCode in typicalSectionReferences:
            for reference in typicalSectionReferences[self.bookReferenceCode]:
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                c, v = reference[0], reference[1]
                if len(reference)==3: v += reference[2] # append the suffix
                typical = typicalSectionReferences[self.bookReferenceCode][reference]
                #print( reference, c, v, typical )
                if Globals.debugFlag: assert( typical in ('A','S','M','F') )
                if reference in sectionReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Section Reference is less common after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Section Reference is less common after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 17, c, v, _("Less common to have a Section Reference after field") )
                        #print( "Surprise", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, c, v, _("Less common to have a Section Reference after field") )
                        #print( "Yeah", self.bookReferenceCode, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Section Reference normally inserted after v{}").format( self.bookReferenceCode, c, v ) )
                        logging.info( _("Section Reference normally inserted after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                        self.addPriorityError( 27, c, v, _("Section Reference normally inserted after field") )
                        #print( "All", self.bookReferenceCode, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, c, v, _("Section Reference often inserted after field") )
                        #print( "Most", self.bookReferenceCode, reference, typical, present )
            for entry in sectionReferences: # now check for ones in this book but not typically there
                reference, text = entry
                if Globals.debugFlag: assert( 2 <= len(reference) <= 3 )
                if reference not in typicalSectionReferences[self.bookReferenceCode]:
                    c, v = reference[0], reference[1]
                    if len(reference)==3: v += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Section Reference is unusual after v{}").format( self.bookReferenceCode, c, v ) )
                    logging.info( _("Section Reference is unusual after v{} in chapter {} of {}").format( v, c, self.bookReferenceCode ) )
                    self.addPriorityError( 37, c, v, _("Unusual to have a Section Reference after field") )
                    #print( "Weird Section Reference after", self.bookReferenceCode, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no section reference info available").format( self.bookReferenceCode ) )
            logging.info( _("{} No section reference info available").format( self.bookReferenceCode ) )
            self.addPriorityError( 3, '-', '-', _("No section reference info for '{}' book").format( self.bookReferenceCode ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = OrderedDict() # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Section Reference Errors'] = addedUnitNotices
    # end of InternalBibleBook.doCheckAddedUnits


    def doCheckSFMs( self ):
        """Runs a number of comprehensive checks on the USFM codes in this Bible book."""
        allAvailableNewlineMarkers = Globals.USFMMarkers.getNewlineMarkersList( 'Numbered' )
        allAvailableCharacterMarkers = Globals.USFMMarkers.getCharacterMarkersList( includeEndMarkers=True )

        newlineMarkerCounts, internalMarkerCounts, noteMarkerCounts = OrderedDict(), OrderedDict(), OrderedDict()
        #newlineMarkerCounts['Total'], internalMarkerCounts['Total'], noteMarkerCounts['Total'] = 0, 0, 0 # Put these first in the ordered dict
        newlineMarkerErrors, internalMarkerErrors, noteMarkerErrors = [], [], []
        functionalCounts = {}
        modifiedMarkerList = []
        c = v = '0'
        section, lastMarker = '', ''
        lastMarkerEmpty = True
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            markerEmpty = len(text) == 0
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

            if marker == 'v~':
                lastMarker, lastMarkerEmpty = 'v', markerEmpty
                continue
            elif marker == 'p~':
                lastMarker, lastMarkerEmpty = 'p', markerEmpty # not sure if this is correct here ?????
                continue
            elif marker == 'c~':
                lastMarker, lastMarkerEmpty = 'c', markerEmpty
                continue
            elif marker == 'c#':
                lastMarker, lastMarkerEmpty = 'c', markerEmpty
                continue
            else: # it's not our (non-USFM) c~,c#,v~ markers
                if marker not in allAvailableNewlineMarkers: print( "Unexpected marker is '{}'".format( marker ) )
                if Globals.debugFlag: assert( marker in allAvailableNewlineMarkers ) # Should have been checked at load time
                newlineMarkerCounts[marker] = 1 if marker not in newlineMarkerCounts else (newlineMarkerCounts[marker] + 1)

            # Check the progression through the various sections
            try: newSection = Globals.USFMMarkers.markerOccursIn( marker if marker!='v~' else 'v' )
            except: logging.error( "IBB:doCheckSFMs: markerOccursIn failed for '{}'".format( marker ) )
            if newSection != section: # Check changes into new sections
                #print( section, marker, newSection )
                if section=='' and newSection!='Header': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing Header section (went straight to {} section with {} marker)").format( newSection, marker ) )
                elif section!='' and newSection=='Header': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                if section=='Header' and newSection!='Introduction': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing Introduction section (went straight to {} section with {} marker)").format( newSection, marker ) )
                elif section!='Header' and newSection=='Introduction': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                if section=='Introduction' and newSection!='Text': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing Text section (went straight to {} section with {} marker)").format( newSection, marker ) )
                if section=='Text' and newSection!='Text, Poetry': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected section after {} section (went to {} section with {} marker)").format( section, newSection, marker ) )
                elif section!='Text' and newSection=='Text, Poetry': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                if section!='Introduction' and section!='Text, Poetry' and newSection=='Text': newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                #print( "section", newSection )
                section = newSection

            # Note the newline SFM order -- create a list of markers in order (with duplicates combined, e.g., \v \v -> \v)
            if not modifiedMarkerList or modifiedMarkerList[-1] != marker: modifiedMarkerList.append( marker )
            # Check for known bad combinations
            if marker=='nb' and lastMarker in ('s','s1','s2','s3','s4','s5'):
                newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("'nb' not allowed immediately after '{}' section heading").format( marker ) )
            if self.checkUSFMSequencesFlag: # Check for known good combinations
                commonGoodNewlineMarkerCombinations = (
                    # If a marker has nothing after it, it must contain data
                    # If a marker has =E after it, it must NOT contain data
                    # (If data is optional, enter both sets)
                    # Heading stuff (in order of occurrence)
                    ('=E','id'), ('id','h1'),('id','ide'), ('ide','h1'), ('h1','toc1'),('h1','mt1'),('h1','mt2'), ('toc1','toc2'), ('toc2','toc3'),('toc2','mt1'),('toc2','mt2'), ('toc3','mt1'),('toc3','mt2'),
                    ('mt1','mt2'),('mt1','imt1'),('mt1','is1'), ('mt2','mt1'),('mt2','imt1'),('mt2','is1'),
                    ('imt1','ip'),('is1','ip'), ('ip','ip'),('ip','iot'), ('imt','iot'), ('iot','io1'), ('io1','io1'),('io1','io2'),('io1','c'), ('io2','io1'),('io2','io2'),('io2','c'),
                    # Regular chapter stuff (in alphabetical order)
                    ('b=E','q1'),('b=E','q1=E'),
                    ('c','p=E'),('c','q1=E'),('c','s1'),('c','s2'),('c','s3'),
                    ('m=E','p'),('m=E','v'),
                    ('p','c'),('p','p=E'),('p=E','q1'),('p','s1'),('p','v'),('p=E','v'),
                    ('pi1','c'),('pi1','pi1=E'), ('pi1','s1'),('pi1','v'),('pi1=E','v'),
                    ('q1','b=E'),('q1','c'),('q1','m=E'),('q1','p=E'),('q1','q1'),('q1','q1=E'),('q1','q2'),('q1','q2=E'),('q1','s1'),('q1','v'),('q1=E','v'),
                    ('q2','b=E'),('q2','c'),('q2','m=E'),('q2','p=E'),('q2','q1'),('q2','q1=E'),('q2','q2'),('q2','q2=E'),('q2','q3'),('q2','s1'),('q2','v'),('q2=E','v'),
                    ('q3','b=E'),('q3','c'),('q3','m=E'),('q3','p=E'),('q3','q2'),('q3','q3'),('q3','s1'),('q3','v'),('q3=E','v'),
                    ('li1','li1'),('li1','v'),('li1=E','v'),('li1','p=E'),
                    ('r','p=E'),
                    ('s1','p=E'),('s1','q1=E'),('s1','r'),
                    ('s2','p=E'),('s2','q1=E'),('s2','r'),
                    ('s3','p=E'),('s3','q1=E'),('s3','r'),
                    ('v','c'),('v','li1'),('v','m'),
                    ('v','p'),('v','p=E'), ('v','pi1'),('v','pi1=E'),('v','pc'),
                    ('v','q1'),('v','q1=E'),('v','q2'),('v','q2=E'),('v','q3'),('v','q3=E'),
                    ('v','s1'),('v','s2'),('v','s3'),
                    ('v','v'), )
                rarerGoodNewlineMarkerCombinations = (
                    ('mt2','mt3'), ('mt3','mt1'), ('io1','cl'), ('io2','cl'), ('ip','c'),
                    ('c','cl'), ('cl','c'),('cl','p=E'),('cl','q1=E'),('cl','s1'),('cl','s2'),('cl','s3'),
                    ('m','c'),('m','p=E'),('m','q1'),('m','v'),
                    ('p','p'),('p','q1'),
                    ('q1','m'),('q1','q3'), ('q2','m'), ('q3','q1'),
                    ('r','p'), ('s1','p'),('s1','pi1=E'), ('v','b=E'),('v','m=E'), )
                #for tuple2 in rarerGoodNewlineMarkerCombinations: print( tuple2); assert( tuple2 not in commonGoodNewlineMarkerCombinations ) # Just check our tables for unwanted duplicates
                for tuple2 in rarerGoodNewlineMarkerCombinations: assert( tuple2 not in commonGoodNewlineMarkerCombinations ) # Just check our tables for unwanted duplicates
                # We allow rem (remark) markers to be anywhere without a warning
                if lastMarkerEmpty and markerEmpty:
                    if (lastMarker+'=E',marker+'=E') not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker+'=E',marker+'=E') in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) Empty '{}' not commonly used following empty '{}' marker").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) Empty '{}' not commonly used following empty '{}' marker").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Empty '{}' not normally used following empty '{}' marker").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Empty '{}' not normally used following empty '{}' marker").format( marker, lastMarker ) )
                elif lastMarkerEmpty and not markerEmpty and marker!='rem':
                    if (lastMarker+'=E',marker) not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker+'=E',marker) in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) '{}' with text not commonly used following empty '{}' marker").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) '{}' with text not commonly used following empty '{}' marker").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("'{}' with text not normally used following empty '{}' marker").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("'{}' with text not normally used following empty '{}' marker").format( marker, lastMarker ) )
                elif not lastMarkerEmpty and markerEmpty and lastMarker!='rem':
                    if (lastMarker,marker+'=E') not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker,marker+'=E') in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) Empty '{}' not commonly used following '{}' with text").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) Empty '{}' not commonly used following '{}' with text").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Empty '{}' not normally used following '{}' with text").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Empty '{}' not normally used following '{}' with text").format( marker, lastMarker ) )
                elif lastMarker!='rem' and marker!='rem': # both not empty
                    if (lastMarker,marker) not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker,marker) in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) '{}' with text not commonly used following '{}' with text").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("(Warning only) '{}' with text not commonly used following '{}' with text").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("'{}' with text not normally used following '{}' with text").format( marker, lastMarker ) )
                            #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("'{}' with text not normally used following '{}' with text").format( marker, lastMarker ) )

            markerShouldHaveContent = Globals.USFMMarkers.markerShouldHaveContent( marker )
            if text:
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
                            shouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                            if shouldBeClosed == 'N': internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker {} cannot be closed").format( closedMarkerText ) )
                            elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                            elif closedMarkerText in hierarchy: internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Internal markers appear to overlap: {}").format( internalTextMarkers ) )
                            else: internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected internal closing marker: {} in {}").format( internalMarker, internalTextMarkers ) )
                        else: # it's not a closing marker
                            shouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( internalMarker )
                            if shouldBeClosed == 'N': continue # N for never
                            else: hierarchy.append( internalMarker ) # but what if it's optional ????????????????????????????????
                    if hierarchy: # it should be empty
                        internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("These markers {} appear not to be closed in {}").format( hierarchy, internalTextMarkers ) )

                if markerShouldHaveContent == 'N': # Never
                    newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '{}' should not have content: '{}'").format( marker, text ) )
                    logging.warning( _("Marker '{}' should not have content after {} {}:{} with: '{}'").format( marker, self.bookReferenceCode, c, v, text ) )
                    self.addPriorityError( 83, c, v, _("Marker {} shouldn't have content").format( marker ) )
                markerList = Globals.USFMMarkers.getMarkerListFromText( text )
                #if markerList: print( "\nText {} {}:{} = {}:'{}'".format(self.bookReferenceCode, c, v, marker, text)); print( markerList )
                openList = []
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check character markers
                    if not Globals.USFMMarkers.isInternalMarker( insideMarker ): # these errors have probably been noted already
                        internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Non-internal {} marker in {}: {}").format( insideMarker, marker, text ) )
                        logging.warning( _("Non-internal {} marker after {} {}:{} in {}: {}").format( insideMarker, self.bookReferenceCode, c, v, marker, text ) )
                        self.addPriorityError( 66, c, v, _("Non-internal {} marker").format( insideMarker, ) )
                    else:
                        if not openList: # no open markers
                            if nextSignificantChar in ('',' '): openList.append( insideMarker ) # Got a new marker
                            else:
                                internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected {}{} marker in {}: {}").format( insideMarker, nextSignificantChar, marker, text ) )
                                logging.warning( _("Unexpected {}{} marker after {} {}:{} in {}: {}").format( insideMarker, nextSignificantChar, self.bookReferenceCode, c, v, marker, text ) )
                                self.addPriorityError( 66, c, v, _("Unexpected {}{} marker").format( insideMarker, nextSignificantChar ) )
                        else: # have at least one open marker
                            if nextSignificantChar=='*':
                                if insideMarker==openList[-1]: openList.pop() # We got the correct closing marker
                                else:
                                    internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Wrong {}* closing marker for {} in {}: {}").format( insideMarker, openList[-1], marker, text ) )
                                    logging.warning( _("Wrong {}* closing marker for {} after {} {}:{} in {}: {}").format( insideMarker, openList[-1], self.bookReferenceCode, c, v, marker, text ) )
                                    self.addPriorityError( 66, c, v, _("Wrong {}* closing marker for {}").format( insideMarker, openList[-1] ) )
                            else: # it's not an asterisk so appears to be another marker
                                if not Globals.USFMMarkers.isNestingMarker( openList[-1] ): openList.pop() # Let this marker close the last one
                                openList.append( insideMarker ) # Now have multiple entries in the openList
                if len(openList) == 1: # only one marker left open
                    closedFlag = Globals.USFMMarkers.markerShouldBeClosed( openList[0] )
                    if closedFlag != 'A': # always
                        if closedFlag == 'S': # sometimes
                            internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker(s) {} don't appear to be (optionally) closed in {}: {}").format( openList, marker, text ) )
                            logging.info( _("Marker(s) {} don't appear to be (optionally) closed after {} {}:{} in {}: {}").format( openList, self.bookReferenceCode, c, v, marker, text ) )
                            self.addPriorityError( 26, c, v, _("Marker(s) {} isn't closed").format( openList ) )
                        openList.pop() # This marker can (always or sometimes) be closed by the end of line
                if openList:
                    internalMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker(s) {} don't appear to be closed in {}: {}").format( openList, marker, text ) )
                    logging.warning( _("Marker(s) {} don't appear to be closed after {} {}:{} in {}: {}").format( openList, self.bookReferenceCode, c, v, marker, text ) )
                    self.addPriorityError( 36, c, v, _("Marker(s) {} should be closed").format( openList ) )
                    if len(openList) == 1: text += '\\' + openList[-1] + '*' # Try closing the last one for them
            else: # There's no text
                if markerShouldHaveContent == 'A': # Always
                    newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker '{}' has no content").format( marker ) )
                    logging.warning( _("Marker '{}' has no content after").format( marker ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 47, c, v, _("Marker {} should have content").format( marker ) )

            extras = entry.getExtras()
            if extras:
                #print( "InternalBibleBook:doCheckSFMs-Extras-A {} {}:{} ".format( self.bookReferenceCode, c, v ), extras )
                extraMarkers = []
                for extraType, extraIndex, extraText, cleanExtraText in extras:
                    if Globals.debugFlag:
                        assert( extraText ) # Shouldn't be blank
                        #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                        assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        print( "InternalBibleBook:doCheckSFMs-Extras-B {} {}:{} ".format( self.bookReferenceCode, c, v ), extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert( extraIndex >= 0 )
                        #assert( 0 <= extraIndex <= len(text)+3 )
                        assert( extraType in ('fn','xr',) )
                    extraName = 'footnote' if extraType=='fn' else 'cross-reference'
                    if '\\f ' in extraText or '\\f*' in extraText or '\\x ' in extraText or '\\x*' in extraText: # Only the contents of these fields should be in extras
                        newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Programming error with extras: {}").format( extraText ) )
                        logging.warning( _("Programming error with {} notes after").format( extraText ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 99, c, v, _("Extras {} have a programming error").format( extraText ) )
                        continue # we have a programming error -- just skip this one
                    thisExtraMarkers = []
                    if '\\\\' in extraText:
                        noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("doubled backslash characters in  {}: {}").format( extraType, extraText ) )
                        while '\\\\' in extraText: extraText = extraText.replace( '\\\\', '\\' )
                    #if '  ' in extraText:
                    #    noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("doubled space characters in  {}: {}").format( extraType, extraText ) )
                    #    while '  ' in extraText: extraText = extraText.replace( '  ', ' ' )
                    if '\\' in extraText:
                        #print( extraText )
                        if Globals.debugFlag: assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # These beginning and end markers should already be removed
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
                                shouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( closedMarkerText )
                                #print( "here with", extraType, extraText, thisExtraMarkers, hierarchy, closedMarkerText, shouldBeClosed )
                                if shouldBeClosed == 'N': noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Marker {} is not closeable").format( closedMarkerText ) )
                                elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                                elif closedMarkerText in hierarchy: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Internal {} markers appear to overlap: {}").format( extraName, thisExtraMarkers ) )
                                else: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected {} closing marker: {} in {}").format( extraName, extraMarker, thisExtraMarkers ) )
                            else: # it's not a closing marker -- for extras, it probably automatically closes the previous marker
                                shouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( extraMarker )
                                if shouldBeClosed == 'N': continue # N for never
                                elif hierarchy: # Maybe the previous one is automatically closed by this one
                                    previousMarker = hierarchy[-1]
                                    previousShouldBeClosed = Globals.USFMMarkers.markerShouldBeClosed( previousMarker )
                                    if previousShouldBeClosed == 'S': # S for sometimes
                                        hierarchy.pop() # That they are not overlapped, but rather that the previous one is automatically closed by this one
                                hierarchy.append( extraMarker )
                        if len(hierarchy)==1 and Globals.USFMMarkers.markerShouldBeClosed(hierarchy[0])=='S': # Maybe the last marker can be automatically closed
                            hierarchy.pop()
                        if hierarchy: # it should be empty
                            #print( "here with remaining", extraType, extraText, thisExtraMarkers, hierarchy )
                            noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("These {} markers {} appear not to be closed in {}").format( extraName, hierarchy, extraText ) )
                    adjExtraMarkers = thisExtraMarkers
                    for uninterestingMarker in allAvailableCharacterMarkers: # Remove character formatting markers so we can check the footnote/xref hierarchy
                        while uninterestingMarker in adjExtraMarkers: adjExtraMarkers.remove( uninterestingMarker )
                    if adjExtraMarkers not in Globals.USFMMarkers.getTypicalNoteSets( extraType ):
                        #print( "Got", extraType, extraText, thisExtraMarkers )
                        if thisExtraMarkers: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unusual {} marker set: {} in {}").format( extraName, thisExtraMarkers, extraText ) )
                        else: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing {} formatting in {}").format( extraName, extraText ) )

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
                    #else: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} seems to be missing a leader character in {}").format( extraType, extraText ) )
                    if extraType == 'fn':
                        functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                    elif extraType == 'xr':
                        functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)
            lastMarker, lastMarkerEmpty = marker, markerEmpty


        # Check the relative ordering of newline markers
        #print( "modifiedMarkerList", modifiedMarkerList, self.bookReferenceCode )
        if self.objectTypeString in ('USFM','USX') and modifiedMarkerList and modifiedMarkerList[0] != 'id':
            newlineMarkerErrors.append( _("{} First USFM field in file should have been 'id' not '{}'").format( self.bookReferenceCode, modifiedMarkerList[0] ) )
            self.addPriorityError( 100, '', '', _("id line not first in file") )
        for otherHeaderMarker in ( 'ide','sts', ):
            if otherHeaderMarker in modifiedMarkerList and modifiedMarkerList.index(otherHeaderMarker) > 8:
                newlineMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("USFM '{}' field in file should have been earlier in {}...").format( otherHeaderMarker, modifiedMarkerList[:10] ) )
        if 'mt2' in modifiedMarkerList: # Must be before or after a mt1
            ix = modifiedMarkerList.index( 'mt2' )
            if (ix==0 or modifiedMarkerList[ix-1]!='mt1') and (ix==len(modifiedMarkerList)-1 or modifiedMarkerList[ix+1]!='mt1'):
                newlineMarkerErrors.append( _("{} Expected mt2 marker to be next to an mt1 marker in {}...").format( self.bookReferenceCode, modifiedMarkerList[:10] ) )

        if 'USFMs' not in self.errorDictionary: self.errorDictionary['USFMs'] = OrderedDict() # So we hopefully get the errors first
        if newlineMarkerErrors: self.errorDictionary['USFMs']['Newline Marker Errors'] = newlineMarkerErrors
        if internalMarkerErrors: self.errorDictionary['USFMs']['Internal Marker Errors'] = internalMarkerErrors
        if noteMarkerErrors: self.errorDictionary['USFMs']['Footnote and Cross-Reference Marker Errors'] = noteMarkerErrors
        if modifiedMarkerList:
            modifiedMarkerList.insert( 0, '['+self.bookReferenceCode+']' )
            self.errorDictionary['USFMs']['Modified Marker List'] = modifiedMarkerList
        if newlineMarkerCounts:
            total = 0
            for marker in newlineMarkerCounts: total += newlineMarkerCounts[marker]
            self.errorDictionary['USFMs']['All Newline Marker Counts'] = newlineMarkerCounts
            self.errorDictionary['USFMs']['All Newline Marker Counts']['Total'] = total
        if internalMarkerCounts:
            total = 0
            for marker in internalMarkerCounts: total += internalMarkerCounts[marker]
            self.errorDictionary['USFMs']['All Text Internal Marker Counts'] = internalMarkerCounts
            self.errorDictionary['USFMs']['All Text Internal Marker Counts']['Total'] = total
        if noteMarkerCounts:
            total = 0
            for marker in noteMarkerCounts: total += noteMarkerCounts[marker]
            self.errorDictionary['USFMs']['All Footnote and Cross-Reference Internal Marker Counts'] = noteMarkerCounts
            self.errorDictionary['USFMs']['All Footnote and Cross-Reference Internal Marker Counts']['Total'] = total
        if functionalCounts: self.errorDictionary['USFMs']['Functional Marker Counts'] = functionalCounts
    # end of InternalBibleBook.doCheckSFMs


    def doCheckCharacters( self ):
        """Runs a number of checks on the characters used."""
        if Globals.verbosityLevel > 2: import unicodedata

        def countCharacters( adjText ):
            """ Counts the characters for the given text (with internal markers already removed). """
            #print( "countCharacters: '{}'".format( adjText ) )
            if '  ' in adjText:
                characterErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Multiple spaces in '{}'").format( adjText ) )
                self.addPriorityError( 7, c, v, _("Multiple spaces in text line") )
            if adjText[-1].isspace(): # Most trailing spaces have already been removed, but this can happen in a note after the markers have been removed
                characterErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Trailing space in '{}'").format( adjText ) )
                self.addPriorityError( 5, c, v, _("Trailing space in text line") )
                #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Trailing space in {} '{}'").format( marker, adjText ) )
            if Globals.USFMMarkers.isPrinted( marker ): # Only do character counts on lines that will be printed
                for char in adjText:
                    lcChar = char.lower()
                    if Globals.verbosityLevel > 2:
                        try: charName = unicodedata.name( char )
                        except ValueError: charName = char
                        try: lcCharName = unicodedata.name( lcChar )
                        except ValueError: lcCharName = lcChar
                    else: # normal verbosity
                        if char==' ': charName = lcCharName = 'Space'
                        elif char==chr(0): charName = lcCharName = 'Null'
                        else: charName, lcCharName = char, lcChar
                    characterCounts[charName] = 1 if charName not in characterCounts else characterCounts[charName] + 1
                    if char==' ' or char =='-' or char.isalpha():
                        letterCounts[lcCharName] = 1 if lcCharName not in letterCounts else letterCounts[lcCharName] + 1
                    elif not char.isalnum(): # Assume it's punctuation
                        punctuationCounts[charName] = 1 if charName not in punctuationCounts else punctuationCounts[charName] + 1
                        if char not in allWordPunctChars:
                            characterErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Invalid '{}' word-building character").format( charName ) )
                            self.addPriorityError( 10, c, v, _("Invalid '{}' word-building character").format( charName ) )
                for char in leadingWordPunctChars:
                    if char not in trailingWordPunctChars and len(adjText)>1 \
                    and ( adjText[-1]==char or char+' ' in adjText ):
                        if Globals.verbosityLevel > 2: charName = unicodedata.name( char )
                        else: # normal verbosity
                            if char==' ': charName = 'Space'
                            elif char==chr(0): charName = 'Null'
                            else: charName = char
                        #print( "{} {}:{} char is '{}' {}".format( char, charName ) )
                        characterErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Misplaced '{}' word leading character").format( charName ) )
                        self.addPriorityError( 21, c, v, _("Misplaced '{}' word leading character").format( charName ) )
                for char in trailingWordPunctChars:
                    if char not in leadingWordPunctChars and len(adjText)>1 \
                    and ( adjText[0]==char or ' '+char in adjText ):
                        if Globals.verbosityLevel > 2: charName = unicodedata.name( char )
                        else: # normal verbosity
                            if char==' ': charName = 'Space'
                            elif char==chr(0): charName = 'Null'
                            else: charName = char
                        #print( "{} {}:{} char is '{}' {}".format( char, charName ) )
                        characterErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Misplaced '{}' word trailing character").format( charName ) )
                        self.addPriorityError( 20, c, v, _("Misplaced '{}' word trailing character").format( charName ) )
        # end of countCharacters

        characterCounts, letterCounts, punctuationCounts = {}, {}, {} # We don't care about the order in which they appeared
        characterErrors = []
        c = v = '0'
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if cleanText: countCharacters( cleanText )

            internalSFMsToRemove = Globals.USFMMarkers.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True )
            internalSFMsToRemove = sorted( internalSFMsToRemove, key=len, reverse=True ) # List longest first
            for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras(): # Now process the characters in the notes
                if Globals.debugFlag:
                    assert( extraText ) # Shouldn't be blank
                    #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                    assert( extraIndex >= 0 )
                    #assert( 0 <= extraIndex <= len(text)+3 )
                    assert( extraType in ('fn','xr',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                #cleanExtraText = extraText
                #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                #    cleanExtraText = cleanExtraText.replace( sign, '' )
                #for marker in ['\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',] + internalSFMsToRemove:
                #    cleanExtraText = cleanExtraText.replace( marker, '' )
                if cleanExtraText: countCharacters( cleanExtraText )

        # Add up the totals
        if (characterErrors or characterCounts or letterCounts or punctuationCounts) and 'Characters' not in self.errorDictionary: self.errorDictionary['Characters'] = OrderedDict()
        if characterErrors: self.errorDictionary['Characters']['Possible Character Errors'] = characterErrors
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
    # end of InternalBibleBook.doCheckCharacters


    def doCheckSpeechMarks( self ):
        """Runs a number of checks on the speech marks in the Bible book."""

        reopenQuotesAtParagraph = True # Opening quotes are reused after a paragraph break if the speech is continuing
        closeQuotesAtParagraphEnd = False # Closing quotes are used at the end of a paragraph even if the speech is continuing into the next paragraph
        closeQuotesAtSectionEnd = False # Closing quotes are used at the end of a section even if the speech is continuing into the next section

        openingSpeechChars = '“«‘‹' # The length and order of these two strings must match
        closingSpeechChars = '”»’›'
        if Globals.debugFlag: assert( len(openingSpeechChars) == len(closingSpeechChars) )

        speechMarkErrors, openChars = [], []
        newSection = newParagraph = newBit = False
        bitMarker = ''
        startsWithOpen = endedWithClose = False
        c = v = '0'
        for entry in self._processedLines:
            marker, originalMarker, text, cleanText = entry.getMarker(), entry.getOriginalMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                c = text.split()[0]; v = '0'
                if c=='1': newSection = True # A new section after any introduction even if it doesn't start with an actual section heading
                continue # c fields contain no quote signs and don't affect formatting blocks
            if marker=='v':
                if text: v = text.split()[0]
                continue # v fields contain no quote signs and don't affect formatting blocks

            if marker in ('s1','s2','s3','s4', ): newSection = True; bitMarker = originalMarker; continue # Nothing more to process here (although will miss check rare notes in section headings)
            if marker in ('p','ip','b', ): # Note 'm' is NOT included in this list
                newParagraph = True
                if not bitMarker: bitMarker = originalMarker
            if marker in ('m', ): newBit = True; bitMarker = originalMarker

            if marker in ('r', ): continue # We don't care about these
            if not cleanText: continue # Nothing to do for an empty field

            # From here on, we have relevant markers and something in cleanText
            startsWithOpen = False
            if cleanText[0] in openingSpeechChars:
                startsWithOpen = True
                openQuoteIndex = openingSpeechChars.index( cleanText[0] )
            elif len(cleanText)>1 and cleanText[0]==' ' and cleanText[1] in openingSpeechChars: # This can occur after a leading xref with an extra space after it
                startsWithOpen = True
                openQuoteIndex = openingSpeechChars.index( cleanText[1] )

            #print( c, v, "nS =",newSection, "nP =",newParagraph, "nB =",newBit, "sWO =",startsWithOpen, "eWC = ",endedWithClose, openChars, marker, "'"+cleanText+"'" )
            if openChars:
                if newSection and closeQuotesAtSectionEnd \
                or newParagraph and closeQuotesAtParagraphEnd:
                    match = openChars if len(openChars)>1 else "'{}'".format( openChars[0] )
                    speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unclosed speech marks matching {} before {} marker").format( match, bitMarker ) )
                    logging.error( _("Unclosed speech marks matching {} before {} marker at").format( match, bitMarker ) \
                                                            + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 56, c, v, _("Unclosed speech marks matching {} after {} marker").format( match, bitMarker ) )
                    openChars = []
                elif newParagraph and reopenQuotesAtParagraph and not startsWithOpen:
                    match = openChars if len(openChars)>1 else "'{}'".format( openChars[0] )
                    speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) \
                                                + _("Unclosed speech marks matching {} before {} marker or missing reopening quotes").format( match, originalMarker ) )
                    logging.error( _("Unclosed speech marks matching {} before {} marker or missing reopening quotes at").format( match, originalMarker ) \
                                                            + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 55, c, v, _("Unclosed speech marks matching {} after {} marker or missing reopening quotes").format( match, originalMarker ) )
                    openChars = []

            if newSection and startsWithOpen and endedWithClose and not closeQuotesAtSectionEnd:
                if openQuoteIndex == closeQuoteIndex:
                    speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unnecessary closing of speech marks before section heading") )
                    logging.error( _("Unnecessary closing of speech marks before section heading") + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 50, c, v, _("Unnecessary closing of speech marks before section heading") )

            #print( c, v, openChars, newParagraph, marker, '<' + cleanText + '>' )
            for j,char in enumerate(cleanText): # Go through each character handling speech marks
                if char in openingSpeechChars:
                    if reopenQuotesAtParagraph and newParagraph and (j==0 or (j==1 and cleanText[0]==' ')) and openChars and char==openChars[-1]:
                        # This above also handles cross-references with an extra space at the beginning of a verse causing the opening quote(s) to be the second character
                        #print( c, v, "Ignored (restarting new paragraph quotation)", char, "with", openChars )
                        pass
                    else:
                        #print( "here0 with ", char, c, v, openChars )
                        if openChars and char==openChars[-1]:
                            if newBit:
                                speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) \
                                                                            + _("Seemed to reopen '{}' speech marks after {}").format( char, bitMarker ) )
                                logging.warning( _("Seemed to reopen '{}' speech marks after {} at").format( char, bitMarker ) \
                                                                            + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                                self.addPriorityError( 43, c, v, _("Seemed to reopen '{}' speech marks after {}").format( char, bitMarker ) )
                                openChars.pop()
                            else:
                                speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) \
                                                                            + _("Unclosed '{}' speech marks (or improperly nested speech marks) after {}").format( char, openChars ) )
                                logging.error( _("Unclosed '{}' speech marks (or improperly nested speech marks) after {} at").format( char, openChars ) \
                                                                            + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                                self.addPriorityError( 53, c, v, _("Unclosed '{}' speech marks (or improperly nested speech marks) after {}").format( char, openChars ) )
                        openChars.append( char )
                    if len(openChars)>4:
                        speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Excessive nested speech marks {}").format( openChars ) )
                        logging.error( _("Excessive nested speech marks {} at").format( openChars ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 50, c, v, _("Excessive nested speech marks {}").format( openChars ) )
                    elif len(openChars)>3:
                        speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Lots of nested speech marks {}").format( openChars ) )
                        logging.warning( _("Lots of nested speech marks {} at").format( openChars ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 40, c, v, _("Lots of nested speech marks {}").format( openChars ) )
                elif char in closingSpeechChars:
                    closeIndex = closingSpeechChars.index( char )
                    if not openChars:
                        #print( "here1 with ", char, c, v, openChars )
                        speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected '{}' speech closing character").format( char ) )
                        logging.error( _("Unexpected '{}' speech closing character at").format( char ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 52, c, v, _("Unexpected '{}' speech closing character").format( char ) )
                    elif closeIndex==openingSpeechChars.index(openChars[-1]): # A good closing match
                        #print( "here2 with ", char, c, v )
                        openChars.pop()
                    else: # We have closing marker that doesn't match
                        #print( "here3 with ", char, c, v, openChars )
                        speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Mismatched '{}' speech closing character after {}").format( char, openChars ) )
                        logging.error( _("Mismatched '{}' speech closing character after {} at").format( char, openChars ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                        self.addPriorityError( 51, c, v, _("Mismatched '{}' speech closing character after {}").format( char, openChars ) )

            # End of processing clean-up
            endedWithClose = cleanText[-1] in closingSpeechChars
            if endedWithClose: closeQuoteIndex = closingSpeechChars.index( cleanText[-1] )
            newSection = newParagraph = newBit = False
            bitMarker = ''

            #if c=='9': halt
            # Check the notes also -- each note is complete in itself so it's much simpler
            for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras(): # Now process the characters in the notes
                if Globals.debugFlag:
                    assert( extraText ) # Shouldn't be blank
                    #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( "InternalBibleBook:doCheckSpeechMarks {} {}:{} ".format( self.bookReferenceCode, c, v ), extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                    assert( extraIndex >= 0 )
                    #assert( 0 <= extraIndex <= len(text)+3 )
                    assert( extraType in ('fn','xr',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                extraOpenChars = []
                for char in extraText:
                    if char in openingSpeechChars:
                        if extraOpenChars and char==extraOpenChars[-1]:
                            speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Improperly nested speech marks {} after {} in note").format( char, extraOpenChars ) )
                            logging.error( _("Improperly nested speech marks {} after {} in note in").format( char, extraOpenChars ) \
                                                                    + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                            self.addPriorityError( 45, c, v, _("Improperly nested speech marks {} after {} in note").format( char, extraOpenChars ) )
                        extraOpenChars.append( char )
                    elif char in closingSpeechChars:
                        closeIndex = closingSpeechChars.index( char )
                        if not extraOpenChars:
                            #print( "here1 with ", char, c, v, extraOpenChars )
                            speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unexpected '{}' speech closing character in note").format( char ) )
                            logging.error( _("Unexpected '{}' speech closing character in note in").format( char ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                            self.addPriorityError( 43, c, v, _("Unexpected '{}' speech closing character in note").format( char ) )
                        elif closeIndex==openingSpeechChars.index(extraOpenChars[-1]): # A good closing match
                            #print( "here2 with ", char, c, v )
                            extraOpenChars.pop()
                        else: # We have closing marker that doesn't match
                            #print( "here3 with ", char, c, v, extraOpenChars )
                            speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Mismatched '{}' speech closing character after {} in note").format( char, extraOpenChars ) )
                            logging.error( _("Mismatched '{}' speech closing character after {} in note in").format( char, extraOpenChars ) \
                                                                        + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                            self.addPriorityError( 42, c, v, _("Mismatched '{}' speech closing character after {} in note").format( char, extraOpenChars ) )
                if extraOpenChars: # We've finished the note but some things weren't closed
                    speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unclosed {} speech marks at end of note").format( extraOpenChars ) )
                    logging.error( _("Unclosed {} speech marks at end of note in").format( extraOpenChars ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
                    self.addPriorityError( 47, c, v, _("Unclosed {} speech marks at end of note").format( extraOpenChars ) )

        if openChars: # We've finished the book but some things weren't closed
            #print( "here9 with ", openChars )
            speechMarkErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Unclosed {} speech marks at end of book").format( openChars ) )
            logging.error( _("Unclosed {} speech marks at end of book after").format( openChars ) + " {} {}:{}".format( self.bookReferenceCode, c, v ) )
            self.addPriorityError( 54, c, v, _("Unclosed {} speech marks at end of book").format( openChars ) )

        # Add up the totals
        if (speechMarkErrors) and 'Speech Marks' not in self.errorDictionary: self.errorDictionary['Speech Marks'] = OrderedDict()
        if speechMarkErrors: self.errorDictionary['Speech Marks']['Possible Matching Errors'] = speechMarkErrors
    # end of InternalBibleBook.doCheckSpeechMarks


    def doCheckWords( self ):
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

            internalSFMsToRemove = Globals.USFMMarkers.getCharacterMarkersList( includeBackslash=True, includeEndMarkers=True )
            internalSFMsToRemove = sorted( internalSFMsToRemove, key=len, reverse=True ) # List longest first

            words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            if lastWordTuple is None: ourLastWord = ourLastRawWord = '' # No need to check words repeated across segment boundaries
            else: # Check in case a word has been repeated (e.g., at the end of one verse and then again at the beginning of the next verse)
                if Globals.debugFlag:
                    assert( isinstance( lastWordTuple, tuple ) )
                    assert( len(lastWordTuple) == 2)
                ourLastWord, ourLastRawWord = lastWordTuple
            for j,rawWord in enumerate(words):
                if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                word = rawWord
                for internalMarker in internalSFMsToRemove: word = word.replace( internalMarker, '' )
                word = stripWordPunctuation( word )
                if word and not word[0].isalnum():
                    #print( word, stripWordPunctuation( word ) )
                    #print( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Have unexpected character starting word '{}'").format( word ) )
                    wordErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Have unexpected character starting word '{}'").format( word ) )
                    word = word[1:]
                if word: # There's still some characters remaining after all that stripping
                    if Globals.verbosityLevel > 3: # why???
                        for k,char in enumerate(word):
                            if not char.isalnum() and (k==0 or k==len(word)-1 or char not in medialWordPunctChars):
                                wordErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Have unexpected '{}' in word '{}'").format( char, word ) )
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
                        repeatedWordErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Have possible repeated word with {} {}").format( ourLastRawWord, rawWord ) )
                    ourLastWord, ourLastRawWord = word, rawWord
            return ourLastWord, ourLastRawWord
        # end of countWords


        # Count all the words
        wordCounts, caseInsensitiveWordCounts = {}, {}
        wordErrors, repeatedWordErrors = [], []
        lastTextWordTuple = ('','')
        c = v = '0'
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if text and Globals.USFMMarkers.isPrinted(marker): # process this main text
                lastTextWordTuple = countWords( marker, cleanText, lastTextWordTuple )

            for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras(): # do any footnotes and cross-references
                if Globals.debugFlag:
                    assert( extraText ) # Shouldn't be blank
                    #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                    assert( extraIndex >= 0 )
                    #assert( 0 <= extraIndex <= len(text)+3 )
                    assert( extraType in ('fn','xr',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                #cleanExtraText = extraText
                #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                #    cleanExtraText = cleanExtraText.replace( sign, '' )
                #for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                #    cleanExtraText = cleanExtraText.replace( marker, '' )
                countWords( extraType, cleanExtraText )

        # Add up the totals
        if (wordErrors or wordCounts or caseInsensitiveWordCounts) and 'Words' not in self.errorDictionary: self.errorDictionary['Words'] = OrderedDict() # So we hopefully get the errors first
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
    # end of InternalBibleBook.doCheckWords


    def doCheckFileControls( self ):
        """Runs a number of checks on headings and section cross-references."""
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )

        IDList, encodingList = [], []
        c = v = '0'
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            elif marker == 'id': IDList.append( "{} '{}'".format( self.bookReferenceCode, text ) )
            elif marker == 'ide': encodingList.append( "{} '{}'".format( self.bookReferenceCode, text ) )

        if (IDList or encodingList) and 'Controls' not in self.errorDictionary: self.errorDictionary['Controls'] = OrderedDict() # So we hopefully get the errors first
        if IDList: self.errorDictionary['Controls']['ID Lines'] = IDList
        if encodingList: self.errorDictionary['Controls']['Encoding Lines'] = encodingList
    # end of InternalBibleBook.doCheckFileControls


    def doCheckHeadings( self, discoveryDict ):
        """Runs a number of checks on headings and section cross-references."""
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )

        titleList, headingList, sectionReferenceList, headingErrors = [], [], [], []
        c = v = '0'
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            if marker.startswith('mt'):
                titleList.append( "{} {}:{} Main Title {}: '{}'".format( self.bookReferenceCode, c, v, marker[2:], text ) )
                if not text:
                    headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing title text for marker {}").format( marker ) )
                    self.addPriorityError( 59, c, v, _("Missing title text") )
                elif text[-1]=='.':
                    headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} title ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 69, c, v, _("Title ends with a period") )
            elif marker in ('s1','s2','s3','s4',):
                if marker=='s1': headingList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: headingList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not text:
                    headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing heading text for marker {}").format( marker ) )
                    self.addPriorityError( 58, c, v, _("Missing heading text") )
                elif text[-1]=='.':
                    headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 68, c, v, _("Heading ends with a period") )
            elif marker=='r':
                sectionReferenceList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                if not text:
                    headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing section cross-reference text for marker {}").format( marker ) )
                    self.addPriorityError( 57, c, v, _("Missing section cross-reference text") )
                else: # We have a section reference with text
                    if discoveryDict and 'sectionReferencesParenthesisFlag' in discoveryDict and discoveryDict['sectionReferencesParenthesisFlag']==False:
                        if text[0]=='(' or text[-1]==')':
                            headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Section cross-reference not expected to have parenthesis: {}").format( text ) )
                            self.addPriorityError( 67, c, v, _("Section cross-reference not expected to have parenthesis") )
                    else: # assume that parenthesis are required
                        if text[0]!='(' or text[-1]!=')':
                            headingErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Section cross-reference not in parenthesis: {}").format( text ) )
                            self.addPriorityError( 67, c, v, _("Section cross-reference not in parenthesis") )

        if (headingErrors or titleList or headingList or sectionReferenceList) and 'Headings' not in self.errorDictionary: self.errorDictionary['Headings'] = OrderedDict() # So we hopefully get the errors first
        if headingErrors: self.errorDictionary['Headings']['Possible Heading Errors'] = headingErrors
        if titleList: self.errorDictionary['Headings']['Title Lines'] = titleList
        if headingList: self.errorDictionary['Headings']['Section Heading Lines'] = headingList
        if sectionReferenceList: self.errorDictionary['Headings']['Section Cross-reference Lines'] = sectionReferenceList
    # end of InternalBibleBook.doCheckHeadings


    def doCheckIntroduction( self ):
        """Runs a number of checks on introductory parts."""
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )

        mainTitleList, headingList, titleList, outlineList, introductionErrors = [], [], [], [], []
        c = v = '0'
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            elif marker in ('imt1','imt2','imt3','imt4',):
                if marker=='imt1': mainTitleList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: mainTitleList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not cleanText:
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing heading text for marker {}").format( marker ) )
                    self.addPriorityError( 39, c, v, _("Missing heading text") )
                elif cleanText[-1]=='.':
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 49, c, v, _("Heading ends with a period") )
            elif marker in ('is1','is2','is3','is4',):
                if marker=='is1': headingList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: headingList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not cleanText:
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing heading text for marker {}").format( marker ) )
                    self.addPriorityError( 39, c, v, _("Missing heading text") )
                elif cleanText[-1]=='.':
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 49, c, v, _("Heading ends with a period") )
            elif marker=='iot':
                titleList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                if not cleanText:
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing outline title text for marker {}").format( marker ) )
                    self.addPriorityError( 38, c, v, _("Missing outline title text") )
                elif cleanText[-1]=='.':
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 48, c, v, _("Heading ends with a period") )
            elif marker in ('io1','io2','io3','io4',):
                if marker=='io1': outlineList.append( "{} {}:{} '{}'".format( self.bookReferenceCode, c, v, text ) )
                else: outlineList.append( "{} {}:{} ({}) '{}'".format( self.bookReferenceCode, c, v, marker, text ) )
                if not cleanText:
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing outline text for marker {}").format( marker ) )
                    self.addPriorityError( 37, c, v, _("Missing outline text") )
                elif cleanText[-1]=='.':
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} outline entry ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 47, c, v, _("Outline entry ends with a period") )
            elif marker in ('ip','ipi','im','imi',):
                if not cleanText:
                    introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Missing introduction text for marker {}").format( marker ) )
                    self.addPriorityError( 36, c, v, _("Missing introduction text") )
                elif not cleanText.endswith('.') and not cleanText.endswith('.)') and not cleanText.endswith('.]') \
                and not cleanText.endswith('."') and not cleanText.endswith(".'") \
                and not cleanText.endswith('.”') and not cleanText.endswith('.’') \
                and not cleanText.endswith('.»') and not cleanText.endswith('.›'): # \
                #and not cleanText.endswith('.\\it*') and not text.endswith('.&quot;') and not text.endswith('.&#39;'):
                    if cleanText.endswith(')') or cleanText.endswith(']'):
                        introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} introduction text possibly does not end with a period: {}").format( marker, text ) )
                        self.addPriorityError( 26, c, v, _("Introduction text possibly ends without a period") )
                    else:
                        introductionErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} introduction text does not end with a period: {}").format( marker, text ) )
                        self.addPriorityError( 46, c, v, _("Introduction text ends without a period") )

        if (introductionErrors or mainTitleList or headingList or titleList or outlineList) and 'Introduction' not in self.errorDictionary:
            self.errorDictionary['Introduction'] = OrderedDict() # So we hopefully get the errors first
        if introductionErrors: self.errorDictionary['Introduction']['Possible Introduction Errors'] = introductionErrors
        if mainTitleList: self.errorDictionary['Introduction']['Main Title Lines'] = mainTitleList
        if headingList: self.errorDictionary['Introduction']['Section Heading Lines'] = headingList
        if titleList: self.errorDictionary['Introduction']['Outline Title Lines'] = titleList
        if outlineList: self.errorDictionary['Introduction']['Outline Entry Lines'] = outlineList
    # end of InternalBibleBook.doCheckIntroduction


    def doCheckNotes( self, discoveryDict ):
        """Runs a number of checks on footnotes and cross-references."""
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )

        allAvailableCharacterMarkers = Globals.USFMMarkers.getCharacterMarkersList( includeBackslash=True )

        footnoteList, xrefList = [], []
        footnoteLeaderList, xrefLeaderList, CVSeparatorList = [], [], []
        footnoteErrors, xrefErrors, noteMarkerErrors = [], [], []
        leaderCounts = {}
        c = v = '0'
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: c = text.split()[0]; v = '0'
            elif marker=='v' and text: v = text.split()[0]

            for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras(): # do any footnotes and cross-references
                if Globals.debugFlag:
                    assert( extraText ) # Shouldn't be blank
                    #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    #assert( 0 <= extraIndex <= len(text) ) -- not necessarily true for multiple notes
                    assert( extraType in ('fn','xr',) )
                    assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the CONTENTS of these fields should be in extras

                # Get a copy of the note text without any formatting
                #cleanExtraText = extraText
                #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                #    cleanExtraText = cleanExtraText.replace( sign, '' )
                #for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                #    cleanExtraText = cleanExtraText.replace( marker, '' )

                # Create a list of markers and their contents
                status, myString, lastCode, lastString, extraList = 0, '', '', '', []
                #print( extraText )
                adjExtraText = extraText
                for chMarker in allAvailableCharacterMarkers: adjExtraText = adjExtraText.replace( chMarker, '__' + chMarker[1:].upper() + '__' ) # Change character formatting
                for char in adjExtraText:
                    if status==0: # waiting for leader char
                        if char==' ' and myString:
                            extraList.append( ('leader',myString,) )
                            status, myString = 1, ''
                        else: myString += char
                    elif status==1: # waiting for a backslash code
                        if Globals.debugFlag: assert( not lastCode )
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
                                if extraType == 'fn':
                                    footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote markers don't match: '{}' and '{}'").format( lastCode, myString+'*' ) )
                                    self.addPriorityError( 32, c, v, _("Mismatching footnote markers") )
                                elif extraType == 'xr':
                                    xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference don't match: '{}' and '{}'").format( lastCode, myString+'*' ) )
                                    self.addPriorityError( 31, c, v, _("Mismatching cross-reference markers") )
                                #print( "checkNotes: error with", lastCode, extraList, myString, self.bookReferenceCode, c, v, ); halt
                                status, myString, lastCode = 1, '', '' # Treat the last one as closed
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
                    haveFinalPeriod = True
                    footnoteList.append( line )
                    if cleanExtraText.endswith(' '):
                        footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote seems to have an extra space at end: '{}'").format( extraText ) )
                        self.addPriorityError( 32, c, v, _("Extra space at end of footnote") )
                    elif not cleanExtraText.endswith('.') and not cleanExtraText.endswith('.”') and not cleanExtraText.endswith('."') and not cleanExtraText.endswith('.»') \
                                                        and not cleanExtraText.endswith('.’') and not cleanExtraText.endswith(".'") and not cleanExtraText.endswith('.›') \
                    and not cleanExtraText.endswith('?') and not cleanExtraText.endswith('?”') and not cleanExtraText.endswith('?"') and not cleanExtraText.endswith('?»') \
                                                        and not cleanExtraText.endswith('?’') and not cleanExtraText.endswith("?'") and not cleanExtraText.endswith('?›') \
                    and not cleanExtraText.endswith('!') and not cleanExtraText.endswith('!”') and not cleanExtraText.endswith('!"') and not cleanExtraText.endswith('!»') \
                                                        and not cleanExtraText.endswith('!’') and not cleanExtraText.endswith("!'") and not cleanExtraText.endswith('!›') \
                    and not cleanExtraText.endswith('.)') and not cleanExtraText.endswith('.]'):
                    #and not cleanExtraText.endswith('.&quot;') and not text.endswith('.&#39;'):
                        haveFinalPeriod = False
                    if discoveryDict and 'footnotesPeriodFlag' in discoveryDict:
                        if discoveryDict['footnotesPeriodFlag']==True and not haveFinalPeriod:
                            footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote seems to be missing a final period: '{}'").format( extraText ) )
                            self.addPriorityError( 33, c, v, _("Missing period at end of footnote") )
                        if discoveryDict['footnotesPeriodFlag']==False and haveFinalPeriod:
                            footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote seems to include possible unnecessary final period: '{}'").format( extraText ) )
                            self.addPriorityError( 32, c, v, _("Possible unnecessary period at end of footnote") )
                elif extraType == 'xr':
                    haveFinalPeriod = True
                    xrefList.append( line )
                    if cleanExtraText.endswith(' '):
                        xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference seems to have an extra space at end: '{}'").format( extraText ) )
                        self.addPriorityError( 30, c, v, _("Extra space at end of cross-reference") )
                    elif not cleanExtraText.endswith('.') and not cleanExtraText.endswith('?') and not cleanExtraText.endswith('!') \
                    and not cleanExtraText.endswith('.)') and not cleanExtraText.endswith('.]') \
                    and not cleanExtraText.endswith('.”') and not cleanExtraText.endswith('."') and not cleanExtraText.endswith('.»') \
                    and not cleanExtraText.endswith('.’') and not cleanExtraText.endswith(".'") and not cleanExtraText.endswith('.›'): # \
                    #and not cleanExtraText.endswith('.&quot;') and not text.endswith('.&#39;'):
                        haveFinalPeriod = False
                    if discoveryDict and 'crossReferencesPeriodFlag' in discoveryDict:
                        if discoveryDict['crossReferencesPeriodFlag']==True and not haveFinalPeriod:
                            xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference seems to be missing a final period: '{}'").format( extraText ) )
                            self.addPriorityError( 31, c, v, _("Missing period at end of cross-reference") )
                        if discoveryDict['crossReferencesPeriodFlag']==False and haveFinalPeriod:
                            xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference seems to include possible unnecessary final period: '{}'").format( extraText ) )
                            self.addPriorityError( 32, c, v, _("Possible unnecessary period at end of cross-reference") )

                # Check for two identical fields in a row
                lastNoteMarker = None
                for noteMarker,noteText in extraList:
                    if noteMarker == lastNoteMarker: # Have two identical fields in a row
                        if extraType == 'fn':
                            footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Consecutive {} fields in footnote: '{}'").format( noteMarker, extraText ) )
                            self.addPriorityError( 35, c, v, _("Consecutive {} fields in footnote").format( noteMarker ) )
                        elif extraType == 'xr':
                            xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Consecutive {} fields in cross-reference: '{}'").format( noteMarker, extraText ) )
                            self.addPriorityError( 35, c, v, _("Consecutive {} fields in cross-reference").format( noteMarker ) )
                        #print( "Consecutive fields in '{}'".format( extraText ) )
                    lastNoteMarker = noteMarker

                # Check leader characters
                leader = ''
                if len(extraText) > 2 and extraText[0]!='\\':
                    if extraText[1] == ' ':
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
                else: noteMarkerErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("{} seems to be missing a leader character in {}").format( extraType, extraText ) )

                # Find, count and check CVSeparators
                #  and also check that the references match
                fnCVSeparator = xrCVSeparator = fnTrailer = xrTrailer = ''
                haveAnchor = False
                for noteMarker,noteText in extraList:
                    if noteMarker=='fr':
                        haveAnchor = True
                        if 1: # new code
                            anchor = BibleAnchorReference( self.bookReferenceCode, c, v )
                            #print( "here at BibleAnchorReference", self.bookReferenceCode, c, v, anchor )
                            if not anchor.matchesAnchorString( noteText, 'footnote' ):
                                footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote anchor reference seems not to match: '{}'").format( noteText ) )
                                logging.error( _("Footnote anchor reference seems not to match after {} {}:{} in '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                                self.addPriorityError( 42, c, v, _("Footnote anchor reference mismatch") )
                                #print( self.bookReferenceCode, c, v, 'FN0', '"'+noteText+'"' )
                        else: # old code
                            for j,char in enumerate(noteText):
                                if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                    fnCVSeparator = char
                                    leaderName = "Footnote CV separator '{}'".format( char )
                                    leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                    if char not in CVSeparatorList: CVSeparatorList.append( char )
                                    break
                            if not noteText[-1].isdigit(): fnTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                            myV = v # Temporary copy
                            if myV.isdigit() and marker=='s1': myV=str(int(myV)+1) # Assume that a section heading goes with the next verse (bad assumption if the break is in the middle of a verse)
                            CV1 = (c + fnCVSeparator + myV) if fnCVSeparator and fnCVSeparator in noteText else myV # Make up our own reference string
                            CV2 = CV1 + fnTrailer # Make up our own reference string
                            if CV2 != noteText:
                                if CV1 not in noteText and noteText not in CV2: # This crudely handles a range in either the verse number or the anchor (as long as the individual one is at the start of the range)
                                    #print( "{} fn m='{}' v={} myV={} CV1='{}' CV2='{}' nT='{}'".format( self.bookReferenceCode, marker, v, myV, CV1, CV2, noteText ) )
                                    footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote anchor reference seems not to match: '{}'").format( noteText ) )
                                    self.addPriorityError( 42, c, v, _("Footnote anchor reference mismatch") )
                                    print( self.bookReferenceCode, 'FN1', '"'+noteText+'"', "'"+fnCVSeparator+"'", "'"+fnTrailer+"'", CV1, CV2 )
                                else:
                                    footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote anchor reference possibly does not match: '{}'").format( noteText ) )
                                    print( self.bookReferenceCode, 'FN2', '"'+noteText+'"', "'"+fnCVSeparator+"'", "'"+fnTrailer+"'", CV1, CV2 )
                        break # Only process the first fr field
                    elif noteMarker=='xo':
                        haveAnchor = True
                        if 1: # new code
                            anchor = BibleAnchorReference( self.bookReferenceCode, c, v )
                            if not anchor.matchesAnchorString( noteText, 'cross-reference' ):
                                footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference anchor reference seems not to match: '{}'").format( noteText ) )
                                logging.error( _("Cross-reference anchor reference seems not to match after {} {}:{} in '{}'").format( self.bookReferenceCode, c, v, noteText ) )
                                self.addPriorityError( 41, c, v, _("Cross-reference anchor reference mismatch") )
                                #print( self.bookReferenceCode, c, v, 'XR0', '"'+noteText+'"' )
                        else: # old code
                            for j,char in enumerate(noteText):
                                if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                    xrCVSeparator = char
                                    leaderName = "Cross-reference CV separator '{}'".format( char )
                                    leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                    if char not in CVSeparatorList: CVSeparatorList.append( char )
                                    break
                            if not noteText[-1].isalnum(): xrTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                            elif len(noteText)>3 and noteText[-2:]==' a' and not noteText[-3].isalnum(): xrTrailer = noteText[-3:] # This is a hack to handle something like "12:5: a"
                            CV1 = (c + xrCVSeparator + v) if xrCVSeparator and xrCVSeparator in noteText else v # Make up our own reference string
                            CV2 = CV1 + xrTrailer # Make up our own reference string
                            if CV2 != noteText:
                                #print( "v='{}'  xrT='{}'  CV1='{}'  CV2='{}'  NT='{}'".format( v, xrTrailer, CV1, CV2, noteText ) )
                                if CV1 not in noteText and noteText not in CV2: # This crudely handles a range in either the verse number or the anchor (as long as the individual one is at the start of the range)
                                    #print( 'xr', CV1, noteText )
                                    xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference anchor reference seems not to match: '{}'").format( noteText ) )
                                    self.addPriorityError( 41, c, v, _("Cross-reference anchor reference mismatch") )
                                    print( self.bookReferenceCode, 'XR1', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                                elif noteText.startswith(CV2) or noteText.startswith(CV1+',') or noteText.startswith(CV1+'-'):
                                    #print( "  ok" )
                                    pass # it seems that the reference is contained there in the anchor
                                    #print( self.bookReferenceCode, 'XR2', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                                else:
                                    xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference anchor reference possibly does not match: '{}'").format( noteText ) )
                                    print( self.bookReferenceCode, 'XR3', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                        break # Only process the first xo field
                if not haveAnchor:
                    if extraType == 'fn':
                        footnoteErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Footnote seems to have no anchor reference: '{}'").format( extraText ) )
                        self.addPriorityError( 39, c, v, _("Missing anchor reference for footnote") )
                    elif extraType == 'xr':
                        xrefErrors.append( "{} {}:{} ".format( self.bookReferenceCode, c, v ) + _("Cross-reference seems to have no anchor reference: '{}'").format( extraText ) )
                        self.addPriorityError( 38, c, v, _("Missing anchor reference for cross-reference") )

                # much more yet to be written ................

        if (footnoteErrors or xrefErrors or noteMarkerErrors or footnoteList or xrefList or leaderCounts) and 'Notes' not in self.errorDictionary:
            self.errorDictionary['Notes'] = OrderedDict() # So we hopefully get the errors first
        if footnoteErrors: self.errorDictionary['Notes']['Footnote Errors'] = footnoteErrors
        if xrefErrors: self.errorDictionary['Notes']['Cross-reference Errors'] = xrefErrors
        if noteMarkerErrors: self.errorDictionary['Notes']['Note Marker Errors'] = noteMarkerErrors
        if footnoteList: self.errorDictionary['Notes']['Footnote Lines'] = footnoteList
        if xrefList: self.errorDictionary['Notes']['Cross-reference Lines'] = xrefList
        if leaderCounts:
            self.errorDictionary['Notes']['Leader Counts'] = leaderCounts
            if len(footnoteLeaderList) > 1: self.addPriorityError( 26, '-', '-', _("Mutiple different footnote leader characters: {}").format( footnoteLeaderList ) )
            if len(xrefLeaderList) > 1: self.addPriorityError( 25, '-', '-', _("Mutiple different cross-reference leader characters: {}").format( xrefLeaderList ) )
            if len(CVSeparatorList) > 1: self.addPriorityError( 27, '-', '-', _("Mutiple different chapter/verse separator characters: {}").format( CVSeparatorList ) )
    # end of InternalBibleBook.doCheckNotes


    def check( self, discoveryDict=None, typicalAddedUnitData=None ):
        """Runs a number of checks on the book and returns the error dictionary."""
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag: assert( self._processedLines )

        # Ignore the result of these next ones -- just use any errors collected
        #self.getVersification() # This checks CV ordering, etc. at the same time
        # Further checks
        self.doCheckSFMs()
        self.doCheckCharacters()
        self.doCheckSpeechMarks()
        self.doCheckWords()
        self.doCheckHeadings( discoveryDict )
        self.doCheckIntroduction()
        self.doCheckNotes( discoveryDict ) # footnotes and cross-references

        if self.checkAddedUnitsFlag: # This code is temporary XXXXXXXXXXXXXXXXXXXXXXXX ........................................................................
            if typicalAddedUnitData is None: # Get our recommendations for added units
                import pickle
                folder = os.path.join( os.path.dirname(__file__), "DataFiles/", "ScrapedFiles/" ) # Relative to module, not cwd
                filepath = os.path.join( folder, "AddedUnitData.pickle" )
                if Globals.verbosityLevel > 1: print( _("Importing from {}...").format( filepath ) )
                with open( filepath, 'rb' ) as pickleFile:
                    typicalAddedUnitData = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            self.doCheckAddedUnits( typicalAddedUnitData )
    # end of InternalBibleBook.check


    def getErrors( self ):
        """Returns the error dictionary."""
        if 'Priority Errors' in self.errorDictionary and not self.errorDictionary['Priority Errors']:
            self.errorDictionary.pop( 'Priority Errors' ) # Remove empty dictionary entry if unused
        return self.errorDictionary


    def getCVRef( self, ref ):
        """
        Returns a list of processed lines for the given Bible reference.

        Raises a KeyError if the C:V reference is not found
        """
        #print( "InternalBibleBook.getCVRef( {} ) for {}".format( ref, self.bookReferenceCode ) )
        if isinstance( ref, tuple ): assert( ref[0] == self.bookReferenceCode )
        else: assert( ref.getBBB() == self.bookReferenceCode )
        if not self._processedFlag: self.processLines()
        if Globals.debugFlag:
            assert( self._processedLines )
            assert( self._indexedFlag )
        if isinstance( ref, tuple ): C, V = ref[1], ref[2]
        else: C,V = ref.getChapterNumberStr(), ref.getVerseNumberStr()
        #print( "CV", repr(C), repr(V) )
        #if (C,V,) in self._CVIndex:
        return self._CVIndex.getEntries( (C,V,) )
        #else: # old code
            #startIndex, count, context = self._CVIndex[ C,V ]
            ##print( "data", ref, startIndex, count, context, InternalBibleEntryList(self._processedLines[startIndex:startIndex+count]) )
            ##print( "IBB getRef:", ref, startIndex, self._processedLines[startIndex:startIndex+5] )
            ##if 0: # old stuff
                ##result = []
                ##for index in range( startIndex, len(self._processedLines) ):
                    ##stuff = self._processedLines[index]
                    ##adjustedMarker, originalMarker, adjText, cleanText, extras = stuff
                    ##if adjustedMarker== 'c' and cleanText!=C: break # Gone past our chapter
                    ##if adjustedMarker== 'v' and cleanText!=V: break # Gone past our verse
                    ##result.append( stuff )
                ### Remove any empty final paragraph (that belongs with the next verse )
                ##if result[-1][0]=='p' and not result[-1][3]: result.pop()
                ###print( ref, result )
                ##return result
            #return InternalBibleEntryList( self._processedLines[startIndex:startIndex+count] ), context
        #else: raise KeyError( "{}:{} not found in  {} index".format( C, V, self.bookReferenceCode ) )
        #else: print( self.bookReferenceCode, C, V, "not in index", self._CVIndex )
    # end of InternalBibleBook.getCVRef
# end of class InternalBibleBook


def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    print( "Since this is only designed to be a base class, it can't actually do much at all." )
    print( "  Try running USFMBibleBook or USXXMLBibleBook which use this class." )

    IBB = InternalBibleBook( 'Dummy', 'GEN' )
    # The following fields would normally be filled in a by "load" routine in the derived class
    IBB.objectNameString = "Dummy test Internal Bible Book object"
    IBB.objectTypeString = "DUMMY"
    IBB.sourceFilepath = "Nowhere"
    if Globals.verbosityLevel > 0: print( IBB )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of InternalBibleBook.py