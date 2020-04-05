#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InternalBibleBook.py
#
# Module handling the internal markers for individual Bible books
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module for defining and manipulating Bible books in our internal USFM-based 'lines' format.

The calling class needs to call this base class __init__ routine and also set:
    self.objectTypeString (with 'OSIS', 'USFM2', 'USX' or 'XML', etc.)
    self.objectNameString (with a description of the type of BibleBook object)
It also needs to provide a 'load' routine that sets one or more of:
    self.sourceFolder
    self.sourceFilename
    self.sourceFilepath = os.path.join( sourceFolder, sourceFilename )
and then calls
    self.addLine (in order to fill self._rawLines)
    self.appendToLastLine (where something has to be appended to the previous line)

Required improvements:
    Need to be able to accept encoded cross references as well as text (USFX and YET modules).

To use the InternalBibleBook class,
    use addLine( marker, text ) to add lines to _rawLines
        which is a list containing 2-tuples (marker,text) which contain the actual Bible text
    Then call processLines() which works through _rawLines
        removes footnotes and other additional info
        and places the processed Bible info into _processedLines.
    Finally, call makeCVIndex() to index _processedLines by CV.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-03-18' # by RJH
SHORT_PROGRAM_NAME = "InternalBibleBook"
PROGRAM_NAME = "Internal Bible book handler"
PROGRAM_VERSION = '0.97'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

BCV_VERSION = '1.0'

debuggingThisModule = False
MAX_NONCRITICAL_ERRORS_PER_BOOK_NORMAL = 3
MAX_NONCRITICAL_ERRORS_PER_BOOK_VERBOSE = 5


from typing import List, Tuple, Optional, Union
import os
import logging
import re
import unicodedata

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.USFM3Markers import USFM_ALL_INTRODUCTION_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS, \
    USFM_ALL_BIBLE_PARAGRAPH_MARKERS
from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_CONTENT_MARKERS, BOS_ADDED_NESTING_MARKERS, \
    BOS_END_MARKERS, BOS_ALL_ADDED_MARKERS, BOS_EXTRA_TYPES, BOS_PRINTABLE_MARKERS, \
    InternalBibleEntryList, InternalBibleEntry, \
    InternalBibleExtra, InternalBibleExtraList, \
    parseWordAttributes, parseFigureAttributes
from BibleOrgSys.Internals.InternalBibleIndexes import InternalBibleCVIndex, InternalBibleSectionIndex
from BibleOrgSys.Reference.BibleReferences import BibleAnchorReference



def hasClosingPeriod( text:str ) -> bool:
    """
    Return True if the text ends with a period or something like '.)'
    """
    if not text: return False
    for period in '.።':
        if text[-1] == period: return True
        for closingPunctuation in ''')]"'”’»›''':
            if text.endswith( period + closingPunctuation ): return True
    return False
# end of hasClosingPeriod


def hasClosingPunctuation( text:str ) -> bool:
    """
    Return True if the text ends with a period or question mark or exclamation mark, or something like '.)'

    Note that the colon, etc. is not included here because it's a special case.
    """
    if not text: return False
    for period in '.።?!':
        if text[-1] == period: return True
        for closingPunctuation in ''')]"'”’»›''':
            if text.endswith( period + closingPunctuation ): return True
    return False
# end of hasClosingPunctuation


def cleanUWalignments( abbreviation:str, BBB:str, originalAlignments:List[Tuple[str,str,str,str,str]] ) \
                        -> List[Tuple[str,str,List[Tuple[str,str,str,str,str,str]],str,List[Tuple[str,str,str]]]]:
    """
    Cleans up the unfoldingWord alignment info first

    Returns the cleaned-up list
    """
    import re
    #debuggingThisModule = True

    if BibleOrgSysGlobals.verbosityLevel > 2:
        print( f"cleanUWalignments( {abbreviation}, {BBB}, … )" )
    if BibleOrgSysGlobals.verbosityLevel > 3:
        print( f"Cleaning {len(originalAlignments):,} {abbreviation} alignments…" )
    assert originalAlignments
    assert isinstance( originalAlignments, list )

    maxOriginalWords = maxTranslatedWords = 0
    cleanedAlignmentList:List[Tuple[str,str,str,str]] = []
    for j, (C,V, textString,wordsString) in enumerate( originalAlignments, start=1 ):
        if debuggingThisModule: print( f"{j} {BBB} {C}:{V} '{textString}'\n    = '{wordsString}'" )

        assert isinstance( C, str ) and C
        assert isinstance( V, str ) and V

        assert isinstance( textString, str ) and textString
        assert textString.startswith( 'x-strong="' )
        assert '\\w' not in textString
        assert 'x-strong="' in textString
        assert 'x-lemma="' in textString
        assert 'x-morph="' in textString
        assert 'x-occurrence="' in textString
        assert 'x-occurrences="' in textString
        assert 'x-content="' in textString

        assert isinstance( wordsString, str ) and wordsString
        #print( f"wordsString1='{wordsString}'" )
        #assert not wordsString.startswith( ' ' )
        wordsString = wordsString.lstrip()
        assert not wordsString.endswith( ' ' )

        while True:
            changedSomething = False
            for paragraphMarker in ('q','q1','q2','q3', 'p','m','pi','pi1',):
                if wordsString.startswith( f'\\{paragraphMarker} ' ):
                    if debuggingThisModule: print( f"             Removing \\{paragraphMarker} number from '{wordsString}'" )
                    wordsString = wordsString[len(paragraphMarker)+2:] # Remove the unwanted paragraph formatting
                    changedSomething = True
                    break
            if not changedSomething: break
        wordsString = wordsString.lstrip()

        while '\\v ' in wordsString: # Remove the verse number
            ix = wordsString.find( '\\v ' )
            assert ix != -1
            if debuggingThisModule: print( f"             Removing verse number from '{wordsString}'" )
            assert wordsString[ix+3].isdigit()
            ixSpace = wordsString[ix+3:].find( ' ' )
            assert ixSpace != -1
            wordsString = wordsString[:ix] + wordsString[ix+ixSpace+4:]
            if debuggingThisModule: print( f"               Removed verse number now '{wordsString[:20]}'…" )
        assert '\\v' not in wordsString

        if wordsString.startswith( '\\q '): wordsString = wordsString[3:] # Handle a bug in ULT Acts 4:25

        #print( f"wordsString2='{wordsString}'" )
        # Note the following code fails with two leading punct chars at Rev 16:15 ("\wLook …
        if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
            assert wordsString.startswith( '\\w ' ) \
                or ( wordsString[0] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS + '—'
                        and wordsString[1:].startswith( '\\w ' ) )
        assert 'x-occurrence="' in wordsString
        assert 'x-occurrences="' in wordsString

        textCount = textString.count( '|' ) + 1 # Our separator character
        if textCount > maxOriginalWords: maxOriginalWords = textCount
        #if textCount > 1 and debuggingThisModule:
            #print( f"  This one has {textCount} original language words" )
        # Allow for x-strong, x-lemma and x-morph to be empty (originally it was just x-lemma)
        textRE = re.compile( r'x-strong="(.*?)" x-lemma="(.*?)" x-morph="(.*?)" x-occurrence="(\d{1,3})" x-occurrences="(\d{1,3})" x-content="(.+?)"' )
        textList = []
        match =  textRE.search( textString )
        while match:
            textList.append( (match.group(1),match.group(2),match.group(3),match.group(4),match.group(5),match.group(6)) )
            for xx in range(1,7):
                if not match.group(xx):
                    logging.warning( f"Got an empty uW {abbreviation} alignment field at {BBB} {C}:{V} in {textString}" )
                    # assert xx == 2 # It's the lemma field that's empty
            #index = match.end()
            textString = f'{textString[:match.start()]}{textString[match.end():]}'
            match =  textRE.search( textString )
        #print( f"{abbreviation} {BBB} {C}:{V} textString={textString!r}" )
        if textString.replace( '|', '' ):
            logging.critical( f"Got an unexpected uW {abbreviation} alignment field at {BBB} {C}:{V} in {textString}" )
        else: assert len(textList) == textCount

        wordsCount = wordsString.count( '\\w ' )
        if wordsCount > maxTranslatedWords: maxTranslatedWords = wordsCount
        assert wordsString.count( '\\w*' ) == wordsCount
        #if debuggingThisModule: print( f"  This one has {wordsCount} translated words" )
        wordRE = re.compile( r'\\w (.+?)\|x-occurrence="(\d{1,3})" x-occurrences="(\d{1,3})"\\w\*' )
        wordsList = []
        match =  wordRE.search( wordsString )
        while match:
            for xx in range(1,4): assert match.group(xx)
            wordsList.append( (match.group(1),match.group(2),match.group(3)) )
            #index = match.end()
            wordsString = f'{wordsString[:match.start()]}{match.group(1)}{wordsString[match.end():]}'
            match =  wordRE.search( wordsString )
        assert len(wordsList) == wordsCount

        cleanedAlignmentList.append( (C,V, textList, wordsString,wordsList) )

    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
        print( f"\nHave {len(cleanedAlignmentList):,} alignment entries for {abbreviation} {BBB}" )
        print( f"  Maximum of {maxOriginalWords} original language words in one {abbreviation} {BBB} entry" )
        print( f"  Maximum of {maxTranslatedWords} translated words in one {abbreviation} {BBB} entry" )
        if debuggingThisModule:
            for j, (C,V, textList, wordsString,wordsList) in enumerate( cleanedAlignmentList, start=1 ):
                print( f"{j} {BBB} {C}:{V} {textList} '{wordsString}' {wordsList}" )
                if j > 8: break

    return cleanedAlignmentList
# end of cleanUWalignments function




class InternalBibleBook:
    """
    Class to create and manipulate a single internal Bible file / book.
    The load routine (which populates self._rawLines) by calling addLine must be provided by the superclass.
    """

    def __init__( self, parameter1, BBB:str ) -> None:
        """
        Create the USFM Bible book object.

        Parameters are:
            parameter1: owner of the work (e.g., My English Bible)
                but can be a string (usually only for testing)
            BBB: book reference code
        """
        #print( "InternalBibleBook.__init__( {} )".format( BBB ) )
        if isinstance( parameter1, str ):
            logging.warning( "InternalBibleBook.constructor( {!r}, {} ): Not passed a containing Bible object".format( parameter1, BBB ) )
            self.containerBibleObject = None
            self.workName = parameter1
        else:
            self.containerBibleObject = parameter1
            self.workName = self.containerBibleObject.getAName( abbrevFirst=True )
        self.BBB = BBB
        if BibleOrgSysGlobals.debugFlag: assert self.BBB in BibleOrgSysGlobals.loadedBibleBooksCodes

        self.isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( self.BBB )

        self._rawLines = [] # Contains 2-tuples (marker,text) which contain the actual Bible text -- see addLine below
        self._processedFlag = self._indexedCVFlag = self._indexedSectionsFlag = False
        self.errorDictionary = {}
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
        self.givenAngleBracketWarning = self.givenDoubleQuoteWarning = False

        # Options
        self.checkAddedUnitsFlag = False
        self.checkUSFMSequencesFlag = False
        self.replaceAngleBracketsFlag, self.replaceStraightDoubleQuotesFlag = True, False

        self.badMarkers, self.badMarkerCounts = [], []
        self.versificationList = self.omittedVersesList = self.combinedVersesList = self.reorderedVersesList = None
        self.pntsCount = self.nfvnCount = self.owfvnCount = self.rtsCount = self.sahtCount = self.fwmifCount = self.fswncCount = 0

        self.maxNoncriticalErrorsPerBook = MAX_NONCRITICAL_ERRORS_PER_BOOK_VERBOSE \
                        if BibleOrgSysGlobals.debugFlag or debuggingThisModule \
                            or BibleOrgSysGlobals.verbosityLevel>2 \
                        else MAX_NONCRITICAL_ERRORS_PER_BOOK_NORMAL
    # end of InternalBibleBook.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a USFM Bible book object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.BBB: result += ('\n' if result else '') + "  " + self.BBB
        try:
            if self.sourceFilepath: result += ('\n' if result else '') + "  " + _("From: ") + self.sourceFilepath
        except AttributeError: pass # Not all Bibles have a separate filepath per book
        if self._processedFlag: result += ('\n' if result else '') + "  " + _("Number of processed lines = ") + str(len(self._processedLines))
        else: result += ('\n' if result else '') + "  " + _("Number of raw lines = ") + str(len(self._rawLines))
        if self.BBB and (self._processedFlag or self._rawLines) and BibleOrgSysGlobals.verbosityLevel > 1:
            result += ('\n' if result else '') + "  " + _("Deduced short book name(s) are {}").format( self.getAssumedBookNames() )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            if self._processedFlag: result += '\n' + str( self._processedLines )
            if self._indexedCVFlag: result += '\n' + str( self._CVIndex )
        return result
    # end of InternalBibleBook.__str__


    def __len__( self ) -> int:
        """ This method returns the number of lines in the internal Bible book object. """
        return len( self._processedLines if self._processedFlag else self._rawLines )
    # end of InternalBibleBook.__len__


    def __iter__( self ):
        """
        Yields the next processed line.

        Returns an InternalBibleEntry object.
        """
        assert self._processedFlag
        for line in self._processedLines:
            yield line
    # end of InternalBibleBook.__iter__


    def addPriorityError( self, priority, C, V, string ):
        """
        Adds a priority error to self.errorDictionary.
        """
        if BibleOrgSysGlobals.debugFlag:
            assert isinstance( priority, int ) and ( 0 <= priority <= 100 )
            assert isinstance( string, str ) and string
        if not 'Priority Errors' in self.errorDictionary: self.errorDictionary['Priority Errors'] = [] # Just in case getErrors() deleted it

        BBB = self.BBB
        if self.errorDictionary['Priority Errors']:
            LastPriority, lastString, (lastBBB,lastC,lastV,) = self.errorDictionary['Priority Errors'][-1]
            if priority==LastPriority and string==lastString and BBB==lastBBB: # Remove unneeded repetitive information
                BBB = ''
                if C==lastC: C = ''

        self.errorDictionary['Priority Errors'].append( (priority,string,(BBB,C,V,),) )
    # end of InternalBibleBook.addPriorityError


    def __makeErrorRef( self, C, V ):
        """
        Makes up an error reference string consisting of the BCV reference,
            and if verbose enough, preceded by the work name.

        Returns a string.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: # includes the work name
            return '{!r} {} {}:{}'.format( self.workName, self.BBB, C, V )
        # else verbosityLevel is 0 or 1
        return '{} {}:{}'.format( self.BBB, C, V )
    # end of InternalBibleBook.__makeErrorRef


    def addLine( self, marker, text ):
        """
        Append a (USFM-based) 2-tuple to self._rawLines.
            This is a very simple function,
                but having it allows us to have a single point in order to catch particular bugs or errors.
        """
        forceDebugHere = False
        if forceDebugHere or BibleOrgSysGlobals.debugFlag:
            if forceDebugHere or debuggingThisModule: print( "InternalBibleBook.addLine( {!r}, {!r} ) for {} {!r} {}".format( marker, text, self.objectTypeString, self.workName, self.BBB ) )
            #if len(self._rawLines ) > 200: halt
            #if 'xyz' in text: halt
        if text and ( '\n' in text or '\r' in text ):
            logging.critical( "InternalBibleBook.addLine found newLine in {} text: {}={!r}".format( self.objectTypeString, marker, text ) )
            if forceDebugHere or BibleOrgSysGlobals.debugFlag: halt
        if BibleOrgSysGlobals.debugFlag:
            assert not self._processedFlag
            assert marker and isinstance( marker, str )
            assert marker[0] != '\\'
            if text:
                assert isinstance( text, str )
                assert '\n' not in text and '\r' not in text

        if not ( marker in BibleOrgSysGlobals.loadedUSFMMarkers or marker in BOS_ADDED_CONTENT_MARKERS ):
            logging.critical( "InternalBibleBook.addLine marker for {} not in USFM/BOS lists: {}={!r}" \
                                                        .format( self.objectTypeString, marker, text ) )
            if marker in self.badMarkers:
                ix = self.badMarkers.index( marker )
                assert 0 <= ix < len(self.badMarkers)
                self.badMarkerCounts[ix] += 1
            else:
                self.badMarkers.append( marker )
                self.badMarkerCounts.append( 1 )
        if BibleOrgSysGlobals.debugFlag: assert marker in BibleOrgSysGlobals.loadedUSFMMarkers or marker in BOS_ADDED_CONTENT_MARKERS

        if marker not in BOS_ADDED_CONTENT_MARKERS and not BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
            logging.warning( "IBB.addLine: Not a NL marker: {}={!r}".format( marker, text ) )
            if marker != 'w': # This can happen with unfoldingWord aligned Bibles
                if BibleOrgSysGlobals.debugFlag: print( self, repr(marker), repr(text) ); halt # How did this happen?

        if text is None:
            logging.critical( "InternalBibleBook.addLine: Received {} {} {}={!r}".format( self.objectTypeString, self.BBB, marker, text ) )
            if BibleOrgSysGlobals.debugFlag: halt # Programming error in the calling routine, sorry
            text = '' # Try to recover

        if text.strip() != text:
            if marker=='v' and len(text)<=4 and self.objectTypeString in ('USX',): pass
            else:
                if self.pntsCount != -1:
                    self.pntsCount += 1
                    stripLogger = logging.warning if debuggingThisModule else logging.info
                    if self.pntsCount <= self.maxNoncriticalErrorsPerBook:
                        stripLogger( "InternalBibleBook.addLine: Possibly needed to strip {} {} {}={!r}".format( self.objectTypeString, self.BBB, marker, text ) )
                    else: # we've reached our limit
                        stripLogger( _('Additional "Possibly needed to strip" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                        self.pntsCount = -1 # So we don't do this again (for this book)

        rawLineTuple = ( marker, text )
        self._rawLines.append( rawLineTuple )
    # end of InternalBibleBook.addLine


    def appendToLastLine( self, additionalText, expectedLastMarker=None ):
        """
        Append some extra text to the previous line in self._rawLines
            Doesn't add any additional spaces.
            (Used by USXXMLBibleBook.py)

        No return value.
        """
        forceDebugHere = False
        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
            print( " InternalBibleBook.appendToLastLine( {!r}, {!r} )".format( additionalText, expectedLastMarker ) )
            assert not self._processedFlag
            assert self._rawLines # Must be an existing line to append to
        if additionalText and ( '\n' in additionalText or '\r' in additionalText ):
            logging.critical( "InternalBibleBook.appendToLastLine found newLine in {} additionalText: {}={!r}".format( self.objectTypeString, expectedLastMarker, additionalText ) )
            if forceDebugHere or BibleOrgSysGlobals.debugFlag: halt
        if BibleOrgSysGlobals.debugFlag:
            assert not self._processedFlag
            assert additionalText and isinstance( additionalText, str )
            if additionalText: assert '\n' not in additionalText and '\r' not in additionalText
            if expectedLastMarker: assert isinstance( expectedLastMarker, str )

        marker, text = self._rawLines[-1]
        #print( "additionalText for {} {!r} is {!r}".format( marker, text, additionalText ) )
        if expectedLastMarker and marker!=expectedLastMarker: # Not what we were expecting
            logging.critical( _("InternalBibleBook.appendToLastLine: expected \\{} but got \\{}").format( expectedLastMarker, marker ) )
        if expectedLastMarker and BibleOrgSysGlobals.debugFlag: assert marker == expectedLastMarker
        #if marker in ('v','c',) and ' ' not in text: text += ' ' # Put a space after the verse or chapter number
        text += additionalText
        if forceDebugHere: print( "  newText for {!r} is {!r}".format( marker, text ) )
        #if 'there is no longer any that is' in text: halt
        self._rawLines[-1] = (marker, text,)
    # end of InternalBibleBook.appendToLastLine


    def addVerseSegments( self, V, text, location=None ):
        """
        Takes a text line that might optionally include
            \\NL** markers to indicate a new line.
        Splits the line at those markers, and adds the individual lines to the book.

        The optional location parameter is for better error messages.

        Currently only used by SwordBible.py

        No return value.
        """
        forceDebugHere = False
        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
            print( "\nInternalBibleBook.addVerseSegments( {!r}, {!r}, {!r} )".format( V, text, location ) )
            assert not self._processedFlag
        ourText = text # Work on a copy so we can still print the original for error messages

        for loopCounter in range( 10 ): # Do this a few times to iron every thing out
            if forceDebugHere: print( loopCounter, "LOOPSTART", repr(ourText) )
            savedText = ourText

            while '  ' in ourText: ourText = ourText.replace( '  ', ' ' ) # Reduce double spaces
            while '\\NL** ' in ourText: ourText = ourText.replace( '\\NL** ', '\\NL**' ) # Remove spaces after newlines
            #while ' \\NL**' in ourText: ourText = ourText.replace( ' \\NL**', '\\NL**' ) # Remove spaces before newlines
            while '\\NL**\\NL**' in ourText: ourText = ourText.replace( '\\NL**\\NL**', '\\NL**' ) # Don't need double-ups
            if ourText.startswith( '\\NL**' ): ourText = ourText[5:] # Don't need nl at start of ourText
            if ourText.endswith( '\\p \\NL**'): ourText = ourText[:-6] # Don't need nl and then space at end of ourText
            if ourText.endswith( '\\q1 \\NL**'): ourText = ourText[:-6] # Don't need nl and then space at end of ourText
            if ourText.endswith( '\\q2 \\NL**'): ourText = ourText[:-6] # Don't need nl and then space at end of ourText
            if ourText.endswith( '\\q3 \\NL**'): ourText = ourText[:-6] # Don't need nl and then space at end of ourText
            if ourText.endswith( '\\q4 \\NL**'): ourText = ourText[:-6] # Don't need nl and then space at end of ourText
            if ourText.endswith( '\\NL**' ): ourText = ourText[:-5] # Don't need nl at end of ourText

            for marker in BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True ):
                if '\\{}'.format(marker) in ourText:
                    ourText = ourText.replace( '\\{} \\{} '.format(marker,marker),'\\{} '.format(marker) ) # Remove double start markers
                    ourText = ourText.replace( '\\{} \\NL**'.format(marker), '\\NL**\\{} '.format(marker) ) # Put character start markers after NL
                    ourText = ourText.replace( '\\{}*\\{}*'.format(marker,marker),'\\{}*'.format(marker) ) # Remove double end markers
                    ourText = ourText.replace( '\\NL**\\{}*'.format(marker), '\\{}*\\NL**'.format(marker) ) # Put character end markers before NL
                    ourText = ourText.replace( '\\p\\{}*'.format(marker), '\\{}*\\p'.format(marker) ) # Put character end markers before NL

            for marker in BibleOrgSysGlobals.loadedUSFMMarkers.getNewlineMarkersList( 'Combined' ):
                if '\\{}'.format(marker) in ourText:
                    #ourText = ourText.replace( ' \\{}'.format(marker), '\\{}'.format(marker) ) # Delete useless spaces at ends of lines
                    ourText = ourText.replace( '\\{} \\p'.format(marker), '\\p' ) # Delete useless markers
                    ourText = ourText.replace( '\\{}\\p'.format(marker), '\\p' ) # Delete useless markers

            #ourText = ourText.replace( '\\s1 \\p', '\\p' ) # Delete useless s1 heading marker
            ourText = ourText.replace( '\\wj\\NL**\\p\\NL**', '\\NL**\\p\\NL**\\wj ' ) # Start wj AFTER paragraph marker
            ourText = ourText.replace( '\\wj\\NL**\\q1 ', '\\NL**\\q1 \\wj ' ) # Start wj AFTER paragraph marker
            ourText = ourText.replace( '\\wj\\NL**\\q2 ', '\\NL**\\q2 \\wj ' ) # Start wj AFTER paragraph marker
            #ourText = ourText.replace( '\\NL**\\wj*', '\\wj*\\NL**' )
            #ourText = ourText.replace( '\\tl \\tl ','\\tl ' ).replace( '\\tl*\\tl*','\\tl*' ) # From both highlight and foreign fields
            if forceDebugHere: print( "GGGGGGGGGG", repr(ourText) )
            ourText = ourText.strip()
            if ourText == savedText: break # we didn't change anything
        if forceDebugHere: print( "HHHHHHHH", repr(ourText) )

        writtenV = False
        if '\\NL**' in ourText: # We need to break the original line into different USFM markers
            if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
                print( "\nMessing with segments: {!r}\n  from {!r}{}".format( ourText, text, ('\n  from '+location) if location else '' ) )
            segments = ourText.split( '\\NL**' )
            if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
                assert len(segments) >= 2
                print( "\nSegments (split by \\NL**):", segments )

            leftovers = ''
            for segment in segments:
                if segment and segment[0] == '\\':
                    bits = segment.split( None, 1 )
                    #print( " bits", bits )
                    marker = bits[0][1:]
                    if len(bits) == 1:
                        #if bits[0] in ('\\p','\\b'):
                        if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                            #if C==1 and V==1 and not appendedCFlag: self.addLine( 'c', str(C) ); appendedCFlag = True
                            self.addLine( marker, '' )
                        else:
                            logging.error( "It seems that we had a blank {!r} field \nin {!r}".format( bits[0], ourText ) )
                            if BibleOrgSysGlobals.debugFlag: halt
                    else:
                        assert len(bits) == 2
                        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
                            if location: print( "\nHere @ {}".format( location ) )
                            print( "ourText", repr(ourText) )
                            print( "seg", repr(segment) )
                            print( "segments:", segments )
                            print( "bits", bits )
                            print( "marker", marker )
                            print( "leftovers", repr(leftovers) )
                            #if marker[-1] == '*': marker = marker[:-1]
                            assert marker in ( 'id', 'toc1','toc2','toc3', 'mt1','mt2','mt3', 'ip', 'iot','io1','io2','io3','io4',
                                            's1','s2','s3','s4', 'qa', 'r','sr','sp','d', 'q1','q2','q3','q4', 'v', 'li1','li2','li3','li4', 'pc', ) \
                                or marker in ( 'f','x', 'bk', 'wj', 'nd', 'add', 'k','tl','sig', 'bd','bdit','it','em','sc', 'str', ) # These ones are character markers which can start a new line
                        if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                            self.addLine( marker, bits[1] )
                        elif not writtenV:
                            self.addLine( 'v', '{} {}'.format( V, segment ) )
                            writtenV = True
                        else: leftovers += segment
                else: # What is segment is blank (\\NL** at end of ourText)???
                    #if C==1 and V==1 and not appendedCFlag: self.addLine( 'c', str(C) ); appendedCFlag = True
                    if not writtenV:
                        self.addLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                        writtenV = True
                    else:
                        self.addLine( 'v~', leftovers+segment )
                    leftovers = ''

            if leftovers:
                if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and debuggingThisModule ):
                    print( "\nOriginalText", repr(text) )
                    print( "\nourText", repr(ourText) )
                #logging.critical( "Had leftovers {}".format( repr(leftovers) ) )
                self.appendToLastLine( leftovers )

        elif ourText: # No newlines in result -- just add the simple line
            self.addLine( 'v', V + ' ' + ourText )
    # end of InternalBibleBook.addVerseSegments


    def processLineFix( self, C,V, originalMarker, text, fixErrors ):
        """
        Does character fixes on a specific line and moves the following out of the main text:
            footnotes, cross-references, and figures, Strongs numbers.
        Returns:
            adjText: Text without notes and leading/trailing spaces
            cleanText: adjText without character formatting as well
            extras: a special list containing
                extraType: 'fn' or 'xr' or 'fig'
                extraIndex: the index into adjText above
                extraText: the text of the note
                cleanExtraText: extraText without character formatting as well

        NOTE: You must NOT strip adjText any more AFTER calling this (or the note insert indices will be incorrect)!
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule:
                print( f"\n\nInternalBibleBook.processLineFix( {C}:{V}, {originalMarker}, '{text}' ) for {self.BBB} ({self.objectTypeString})" )
            assert originalMarker and isinstance( originalMarker, str )
            assert isinstance( text, str )
        lineLocation = '{} {}:{}'.format( self.BBB, C, V )
        lineLocationSpace = lineLocation + ' '
        adjText = text
        cleanText = text.replace( ' ', ' ' ) # Replace non-break spaces for this
        #if self.objectTypeString == 'ESFM': cleanText = cleanText.replace( '_', ' ' ) # Replace underlines/underscores for this

        # Remove trailing spaces
        if adjText and adjText[-1].isspace():
            #print( 10, self.BBB, C, V, _("Trailing space at end of line") )
            fixErrors.append( lineLocationSpace + _("Removed trailing space in {}: {}").format( originalMarker, text ) )
            if self.rtsCount != -1:
                self.rtsCount += 1
                if self.rtsCount <= self.maxNoncriticalErrorsPerBook:
                    logging.warning( _("processLineFix: Removed trailing space after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, originalMarker, text ) )
                else: # we've reached our limit
                    logging.warning( _('processLineFix: Additional "Removed trailing space" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                    self.rtsCount = -1 # So we don't do this again (for this book)
            self.addPriorityError( 10, C, V, _("Trailing space at end of line") )
            adjText = adjText.rstrip()
            #print( "QQQ1: rstrip ok" )
            #print( originalMarker, "'"+text+"'", "'"+adjText+"'" )

        #print( 'oTS', self.objectTypeString )
        if self.objectTypeString in ('USFM2','USFM3','USX',):
            if originalMarker not in ('id','ide','h','rem',):
                # Fix up quote marks
                if '<' in adjText or '>' in adjText:
                    if not self.givenAngleBracketWarning: # Just give the warning once (per book)
                        if self.replaceAngleBracketsFlag:
                            fixErrors.append( lineLocationSpace + _("Replaced angle bracket(s) in {}: {}").format( originalMarker, text ) )
                            logging.info( _("processLineFix: Replaced angle bracket(s) after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, text ) )
                            self.addPriorityError( 3, '', '', _("Book contains angle brackets (which we attempted to replace)") )
                        else:
                            fixErrors.append( lineLocationSpace + _("Found (first) angle bracket in {}: {}").format( originalMarker, text ) )
                            logging.info( _("processLineFix: Found (first) angle bracket after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, text ) )
                            self.addPriorityError( 3, '', '', _("Book contains angle bracket(s)") )
                        self.givenAngleBracketWarning = True
                    if self.replaceAngleBracketsFlag:
                        adjText = adjText.replace('<<','“').replace('>>','”').replace('<','‘').replace('>','’') # Replace angle brackets with the proper opening and close quote marks
                if '"' in adjText:
                    if not self.givenDoubleQuoteWarning: # Just give the warning once (per book)
                        if self.replaceStraightDoubleQuotesFlag:
                            fixErrors.append( lineLocationSpace + _("Replaced straight quote sign(s) (\") in \\{}: {}").format( originalMarker, adjText ) )
                            logging.info( _("processLineFix: Replaced straight quote sign(s) (\") after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                            self.addPriorityError( 8, '', '', _("Book contains straight quote signs (which we attempted to replace)") )
                        else: # we're not attempting to replace them
                            fixErrors.append( lineLocationSpace + _("Found (first) straight quote sign (\") in \\{}: {}").format( originalMarker, adjText ) )
                            logging.info( _("processLineFix: Found (first) straight quote sign (\") after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                            self.addPriorityError( 58, '', '', _("Book contains straight quote sign(s)") )
                        self.givenDoubleQuoteWarning = True
                    if self.replaceStraightDoubleQuotesFlag:
                        if adjText[0]=='"': adjText = adjText.replace('"','“',1) # Replace initial double-quote mark with a proper open quote mark
                        adjText = adjText.replace(' "',' “').replace(';"',';“').replace('("','(“').replace('["','[“') # Try to replace double-quote marks with the proper opening and closing quote marks
                        adjText = adjText.replace('."','.”').replace(',"',',”').replace('?"','?”').replace('!"','!”').replace(')"',')”').replace(']"',']”').replace('*"','*”')
                        adjText = adjText.replace('";','”;').replace('"(','”(').replace('"[','”[') # Including the questionable ones
                        adjText = adjText.replace('" ','” ').replace('",','”,').replace('".','”.').replace('"?','”?').replace('"!','”!') # Even the bad ones!
                        if '"' in adjText:
                            logging.warning( "processLineFix: {} {}:{} still has straight quotes in {}:{!r}".format( self.BBB, C, V, originalMarker, adjText ) )

            # Do XML/HTML common character replacements
            #adjText = adjText.replace( '&', '&amp;' )
            #adjText = adjText.replace( "'", '&#39;' ) # XML does contain &apos; for optional use, but not recognised in all versions of HTML
            if '<' in adjText or '>' in adjText:
                logging.error( "processLineFix: {} still has angle-brackets in {}:{!r}".format( self.__makeErrorRef(C,V), originalMarker, adjText ) )
                self.addPriorityError( 12, C, V, _("Contains angle-bracket(s)") )
                #adjText = adjText.replace( '<', '&lt;' ).replace( '>', '&gt;' )
            if '"' in adjText:
                logging.warning( "processLineFix: {} straight-quotes in {}:{!r}".format( self.__makeErrorRef(C,V), originalMarker, adjText ) )
                self.addPriorityError( 11, C, V, _("Contains straight-quote(s)") )
                #adjText = adjText.replace( '"', '&quot;' )

        largeDummyValue = 99999

        # Adjust \w fields to remove attributes (and copy the word) into a separate \ww field
        #   (This then makes the \w field into a regular "formatting field"
        #       since the contents of it need to be included in the regular text.
        if '|' in adjText: # Mostly won't happen
            # print( f"\nW adjText @ {self.BBB} {C}:{V} = {adjText}" )
            ixW = adjText.find( '\\w ' )
            if not BibleOrgSysGlobals.strictCheckingFlag:
                if ixW == -1:
                    ixW = adjText.find( '\\W ' )
                    if ixW != -1:
                        fixErrors.append( lineLocationSpace + _("Found UPPERCASE word marker in \\{}: {}").format( originalMarker, adjText ) )
                        logging.warning( _("processLineFix: Found UPPERCASE word marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                        self.addPriorityError( 9, C, V, _("Word marker is UPPERCASE") )
            if ixW == -1: ixW = largeDummyValue
            while ixW < largeDummyValue: # We have one or the other
                #print( "  ixW={} {!r}".format( ixW, adjText[ixW:ixW+5] ) )
                ixWend = adjText.find( '\\w*', ixW+3 )
                if ixWend == -1: ixWend = adjText.find( '\\W*', ixW+3 )
                if ixWend == -1: ixWend = largeDummyValue
                ixPipe = adjText.find( '|', ixW+3 )
                if ixPipe == -1: break # No pipe -- just a plain \w word\w* field
                #print( "  ixPipe={} {!r} ixWend={} {!r}".format( ixPipe, adjText[ixPipe:ixPipe+3], ixWend, adjText[ixWend:ixWend+6] ) )
                if ixPipe < ixWend: # There is a pipe inside this particular \w field
                    # Convert attributes into a \ww note field (that will then be removed below)
                    word = adjText[ixW+3:ixPipe] # We also copy the word into the \ww field
                    adjText = adjText[:ixPipe] + '\\w*\\ww ' + word + adjText[ixPipe:ixWend+2] + 'w' + adjText[ixWend+2:]
                    #print( "  now adjText = {}".format( adjText ) )
                ixW = adjText.find( '\\w ', ixWend+4 )
                if not BibleOrgSysGlobals.strictCheckingFlag:
                    if ixW == -1:
                        ixW = adjText.find( '\\W ', ixWend+4 )
                        if ixW != -1:
                            fixErrors.append( lineLocationSpace + _("Found UPPERCASE word marker in \\{}: {}").format( originalMarker, adjText ) )
                            logging.warning( _("processLineFix: Found UPPERCASE word marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                            self.addPriorityError( 9, C, V, _("Word marker is UPPERCASE") )
                if ixW == -1: ixW = largeDummyValue

        # Move all footnotes and cross-references, etc. from the main text out to extras
        #  (This includes our \ww fields which contain the atttributes from \w fields)
        extras = InternalBibleExtraList() # Prepare for extras

        #print( "QQQ MOVE OUT NOTES" )
        # This particular little piece of code can also mostly handle it if the markers are UPPER CASE
        ixFN = adjText.find( '\\f ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixFN == -1:
                ixFN = adjText.find( '\\F ' )
                if ixFN != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE footnote marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE footnote marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Footnote marker is UPPERCASE") )
        if ixFN == -1: ixFN = largeDummyValue
        ixEN = adjText.find( '\\fe ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixEN == -1:
                ixEN = adjText.find( '\\FE ' )
                if ixEN != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE endnote marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE endnote marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Endnote marker is UPPERCASE") )
        if ixEN == -1: ixEN = largeDummyValue
        ixXR = adjText.find( '\\x ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixXR == -1:
                ixXR = adjText.find( '\\X ' )
                if ixXR != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE cross-reference marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE cross-reference marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Cross-reference marker is UPPERCASE") )
        if ixXR == -1: ixXR = largeDummyValue
        ixFIG = adjText.find( '\\fig ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixFIG == -1:
                ixFIG = adjText.find( '\\FIG ' )
                if ixFIG != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE figure marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE figure marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Figure marker is UPPERCASE") )
        if ixFIG == -1: ixFIG = largeDummyValue
        ixSTR = adjText.find( '\\str ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixSTR == -1:
                ixSTR = adjText.find( '\\STR ' )
                if ixSTR != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE Strongs marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE Strongs marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Strongs marker is UPPERCASE") )
        if ixSTR == -1: ixSTR = largeDummyValue
        ixSEM = adjText.find( '\\sem ' )
        if not BibleOrgSysGlobals.strictCheckingFlag:
            if ixSEM == -1:
                ixSEM = adjText.find( '\\SEM ' )
                if ixSEM != -1:
                    fixErrors.append( lineLocationSpace + _("Found UPPERCASE semantic marker in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found UPPERCASE semantic marker {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 9, C, V, _("Semantic marker is UPPERCASE") )
        if ixSEM == -1: ixSEM = largeDummyValue
        ixWW = adjText.find( '\\ww ' )
        if ixWW == -1: ixWW = adjText.find( '\\WW ' )
        if ixWW == -1: ixWW = largeDummyValue
        ixVP = adjText.find( '\\vp ' )
        if ixVP == -1: ixVP = adjText.find( '\\VP ' )
        if ixVP == -1: ixVP = largeDummyValue
        #print( 'ixFN =',ixFN, ixEN, 'ixXR = ',ixXR, ixFIG, ixSTR )
        ix1 = min( ixFN, ixEN, ixXR, ixFIG, ixSTR, ixSEM, ixWW, ixVP )
        while ix1 < largeDummyValue: # We have one or the other
            if ix1 == ixFN:
                ix2 = adjText.find( '\\f*' )
                if ix2 == -1: ix2 = adjText.find( '\\F*' )
                #print( 'A', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'f', 1, 'footnote', 'fn'
                if ixFN and adjText[ixFN-1]==' ':
                    fixErrors.append( lineLocationSpace + _("Found footnote preceded by a space in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found footnote preceded by a space after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 52, C, V, _("Footnote is preceded by a space") )
            elif ix1 == ixEN:
                ix2 = adjText.find( '\\fe*' )
                if ix2 == -1: ix2 = adjText.find( '\\FE*' )
                #print( 'A', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'fe', 2, 'endnote', 'en'
                if ixEN and adjText[ixEN-1]==' ':
                    fixErrors.append( lineLocationSpace + _("Found endnote preceded by a space in \\{}: {}").format( originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found endnote preceded by a space after {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 52, C, V, _("Endnote is preceded by a space") )
            elif ix1 == ixXR:
                ix2 = adjText.find( '\\x*' )
                if ix2 == -1: ix2 = adjText.find( '\\X*' )
                #print( 'B', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'x', 1, 'cross-reference', 'xr'
            elif ix1 == ixFIG:
                ix2 = adjText.find( '\\fig*' )
                if ix2 == -1: ix2 = adjText.find( '\\FIG*' )
                #print( 'C', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'fig', 3, 'figure', 'fig'
                parseFigureAttributes( 'workname', self.BBB, C, V,
                                      adjText[ixFIG+5:ix2].replace( '&quot;', '"' ), fixErrors )
                # (returned dictionary above is just ignored here)
            elif ix1 == ixSTR:
                ix2 = adjText.find( '\\str*' )
                if ix2 == -1: ix2 = adjText.find( '\\STR*' )
                #print( 'C', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'str', 3, 'Strongs-number', 'str'
            elif ix1 == ixSEM:
                ix2 = adjText.find( '\\sem*' )
                if ix2 == -1: ix2 = adjText.find( '\\SEM*' )
                #print( 'C', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'sem', 3, 'Semantic info', 'sem'
            elif ix1 == ixWW:
                ix2 = adjText.find( '\\ww*' )
                if ix2 == -1: ix2 = adjText.find( '\\WW*' )
                #print( 'C', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'ww', 2, 'Word attributes', 'ww'
                parseWordAttributes( 'workname', self.BBB, C, V,
                                    adjText[ixWW+4:ix2].replace( '&quot;', '"' ), fixErrors )
                # (returned dictionary above is just ignored here)
            elif ix1 == ixVP:
                if originalMarker != 'v~': # We only expect vp fields in v (now converted to v~) lines
                    fixErrors.append( lineLocationSpace + _("Found unexpected 'vp' field in \\{} line: {}").format( originalMarker, adjText ) )
                    logging.error( _("processLineFix: Found unexpected 'vp' field after {} in \\{}: {}").format( self.__makeErrorRef(C,V), originalMarker, adjText ) )
                    self.addPriorityError( 95, C, V, _("Misplaced 'vp' field") )
                ix2 = adjText.find( '\\vp*' )
                if ix2 == -1: ix2 = adjText.find( '\\VP*' )
                #print( 'C', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
                noteSFM, lenSFM, thisOne, this1 = 'vp', 2, 'verse-character', 'vp'
            elif BibleOrgSysGlobals.debugFlag: halt # programming error
            if ix2 == -1: # no closing marker
                fixErrors.append( lineLocationSpace + _("Found unmatched {} open in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                logging.error( _("processLineFix: Found unmatched {} open after {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                self.addPriorityError( 84, C, V, _("Marker {} is unmatched").format( thisOne ) )
                ix2 = largeDummyValue # Go to the end
            elif ix2 < ix1: # closing marker is before opening marker
                fixErrors.append( lineLocationSpace + _("Found unmatched {} in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                logging.error( _("processLineFix: Found unmatched {} after {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                self.addPriorityError( 84, C, V, _("Marker {} is unmatched").format( thisOne ) )
                ix1, ix2 = ix2, ix1 # swap them then
            # Remove the footnote or endnote or xref or figure
            #print( "\nFound {} at {} {} in {!r}".format( repr(thisOne), ix1, ix2, repr(adjText) ) )
            #print( '\nB', 'ix1 =',ix1,repr(adjText[ix1]), 'ix2 = ',ix2,repr(adjText[ix2]) )
            note = adjText[ix1+lenSFM+2:ix2] # Get the note text (without the beginning and end markers)
            #print( "\nNote is", repr(note) )
            if not note:
                fixErrors.append( lineLocationSpace + _("Found empty {} in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                logging.error( _("processLineFix: Found empty {} after {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                self.addPriorityError( 53, C, V, _("Empty {}").format( thisOne ) )
            else: # there is a note
                if note[0].isspace():
                    fixErrors.append( lineLocationSpace + _("Found {} starting with space in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found {} starting with space after {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                    self.addPriorityError( 12, C, V, _("{} starts with space").format( thisOne.title() ) )
                    note = note.lstrip()
                    #print( "QQQ2: lstrip in note" ); halt
                if note and note[-1].isspace():
                    fixErrors.append( lineLocationSpace + _("Found {} ending with space in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.warning( _("processLineFix: Found {} ending with space after {} {}:{} in \\{}: {}").format( thisOne, self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 11, C, V, _("{} ends with space").format( thisOne.title() ) )
                    note = note.rstrip()
                    #print( "QQQ3: rstrip in note" )
                if '\\f ' in note or '\\f*' in note or '\\x ' in note or '\\x*' in note: # Only the contents of these fields should be here now
                    fixErrors.append( lineLocationSpace + _("Found illegal nested footnote or cross-reference in {} in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.error( _("processLineFix: Found illegal nested footnote or cross-reference in {} after {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                    self.addPriorityError( 85, C, V, _("{} seems to have illegal nested footnote or cross-reference").format( thisOne.title() ) )
                    if debuggingThisModule:
                        print( "processLineFix: {} {}:{} What went wrong here: {!r} from \\{} {!r} (Is it an embedded note?)".format( self.BBB, C, V, note, originalMarker, text ) )
                        print( "processLineFix: Have an embedded note perhaps! Not handled correctly yet" )
                    note = note.replace( '\\f ', ' ' ).replace( '\\f*','').replace( '\\x ', ' ').replace('\\x*','') # Temporary fix …
                minNoteLength = 2 if thisOne=='Strongs-number' else 6 # Strongs numbers can be quite short, e.g., H3, G314
                if len(note)<minNoteLength:
                    fixErrors.append( lineLocationSpace + _("{} seems too short in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.warning( _("processLineFix: {} seems to short after {} {}:{} in \\{}: {}").format( thisOne, self.BBB, C, V, originalMarker, adjText ) )
                    self.addPriorityError( 43, C, V, _("{} seems too short").format( thisOne.title() ) )

            # Now fix some common errors
            if thisOne in ('footnote','endnote','cross-reference'):
                if note.startswith( '\\' ):
                    fixErrors.append( lineLocationSpace + _("Found {} without any caller in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.error( _("processLineFix: Found {} without any caller at {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                    self.addPriorityError( 86, C, V, _("{} should have a caller").format( thisOne.title() ) )
                    note = '+ ' + note
                if len(note)>2 and note[0] in '+-' and note[1] == '\\':
                    fixErrors.append( lineLocationSpace + _("Found {} specified with no space after caller in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    logging.error( _("processLineFix: Found {} specified with no space after caller at {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                    self.addPriorityError( 76, C, V, _("{} should have space after caller").format( thisOne.title() ) )
                    note = note[0] + ' ' + note[1:] # Add in the space
                if note.startswith( '- ' ):
                    if self.fswncCount != -1:
                        self.fswncCount += 1
                        if self.fswncCount <= self.maxNoncriticalErrorsPerBook:
                            logging.error( _("processLineFix: Found {} specified with no caller at {} in \\{}: {}").format( thisOne, self.__makeErrorRef(C,V), originalMarker, adjText ) )
                        else: # we've reached our limit
                            logging.error( _('processLineFix: Additional "Found specified with no caller" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                            self.fswncCount = -1 # So we don't do this again (for this book)
                    fixErrors.append( lineLocationSpace + _("Found {} specified with no caller in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    self.addPriorityError( 8, C, V, _("{} should not have specified no caller").format( thisOne.title() ) )
                    note = '+ ' + note[2:] # Replace - (no caller) with + (automatic caller)
                try: caller,rest = note.split( None, 1 ) # Split off the caller and get the rest
                except ValueError: # presumably no spaces in note
                    caller, rest = note.strip(), ''
                #print( "\ncaller {!r}, rest {!r}".format( caller, rest ) )
                if not rest.startswith( '\\' ):
                    if self.fwmifCount != -1:
                        self.fwmifCount += 1
                        if self.fwmifCount <= self.maxNoncriticalErrorsPerBook:
                            logging.warning( _("processLineFix: Found {} without marked internal fields at {} {}:{} in \\{}: {}").format( thisOne, self.BBB, C, V, originalMarker, adjText ) )
                        else: # we've reached our limit
                            logging.warning( _('processLineFix: Additional "Found without marked internal fields" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                            self.fwmifCount = -1 # So we don't do this again (for this book)
                    fixErrors.append( lineLocationSpace + _("Found {} without marked internal fields in \\{}: {}").format( thisOne, originalMarker, adjText ) )
                    self.addPriorityError( 44, C, V, _("{} should have an internal field marked").format( thisOne.title() ) )
                    # Add the expected fields (could be the wrong ones, but saves lots of problems later, especially if exporting)
                    add = 'xt' if thisOne=='cross-reference' else 'ft'
                    note = '{} \\{} {}'.format( caller, add, rest ) # Add in a default field

            # Now prepare a cleaned version
            adjText = adjText[:ix1] + adjText[ix2+lenSFM+2:] # Remove the note completely from the text
            cleanedNote = note \
                            .replace( '&amp;', '&' ) \
                            .replace( '&#39;', "'" ) \
                            .replace( '&lt;',  '<' ) \
                            .replace( '&gt;',  '>' ) \
                            .replace( '&quot;', '"' ) # Undo any replacements above
            for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                cleanedNote = cleanedNote.replace( sign, '' )
            for marker in ['\\xo*','\\xo ', '\\xt*','\\xt ', '\\xk*','\\xk ', '\\xq*','\\xq ',
                            '\\xot*','\\xot ', '\\xnt*','\\xnt ', '\\xdc*','\\xdc ',
                            '\\fr*','\\fr ','\\ft*','\\ft ','\\fqa*','\\fqa ','\\fq*','\\fq ',
                            '\\fv*','\\fv ','\\fk*','\\fk ','\\fl*','\\fl ','\\fdc*','\\fdc ',] \
                                + BibleOrgSysGlobals.internal_SFMs_to_remove:
                cleanedNote = cleanedNote.replace( marker, '' )
            if '\\z' in cleanedNote:
                fixErrors.append( lineLocationSpace + _("Found custom marker in {}: {}").format( thisOne, cleanedNote ) )
                logging.warning( _("processLineFix: Found custom marker after {} {}:{} in {}: {}").format( self.BBB, C, V, thisOne, cleanedNote ) )
                self.addPriorityError( 21, C, V, _("{} contains custom marker").format( thisOne.title() ) )
                cleanedNote = re.sub( '\\\\z.+? ', '', cleanedNote ) # Remove custom markers
                cleanedNote = re.sub( '\\\\z.+?\*', '', cleanedNote ) # Remove custom marker closings (don't normally occur in footnotes)
            if '\\' in cleanedNote:
                fixErrors.append( lineLocationSpace + _("Found unexpected backslash in {}: {}").format( thisOne, cleanedNote ) )
                logging.error( _("processLineFix: Found unexpected backslash after {} {}:{} in {}: {}").format( self.BBB, C, V, thisOne, cleanedNote ) )
                self.addPriorityError( 81, C, V, _("{} contains unexpected backslash").format( thisOne.title() ) )
                cleanedNote = cleanedNote.replace( '\\', '' )
            #print( "Note: {!r} Cleaned note: {!r}".format( note, cleanedNote ) )

            # Save it all and finish off
            if note: extras.append( InternalBibleExtra(this1,ix1,note,cleanedNote,lineLocation) ) # Saves 4 bits: type ('fn' or 'xr', etc.), index into the main text line, the actual fn or xref contents, then a cleaned version
            if this1 == 'vp': # Insert a new pseudo vp# newline entry BEFORE the v field that it presumably came from
                #print( "InternalBibleBook.processLineFix insertvp# (before)", self.BBB, C, V, repr(originalMarker), repr(cleanedNote) )
                if BibleOrgSysGlobals.debugFlag: assert originalMarker in ('v~','p~',) # Shouldn't occur in other fields
                vEntry = self._processedLines.pop() # because the v field has already been written
                self._processedLines.append( InternalBibleEntry('vp#', 'vp', cleanedNote, cleanedNote, None, cleanedNote) )
                self._processedLines.append( vEntry ) # Put the original v entry back afterwards
            # Get ready for the next loop
            ixFN = adjText.find( '\\f ' )
            if ixFN == -1: ixFN = adjText.find( '\\F ' )
            if ixFN == -1: ixFN = largeDummyValue
            ixEN = adjText.find( '\\fe ' )
            if ixEN == -1: ixEN = adjText.find( '\\FE ' )
            if ixEN == -1: ixEN = largeDummyValue
            ixXR = adjText.find( '\\x ' )
            if ixXR == -1: ixXR = adjText.find( '\\X ' )
            if ixXR == -1: ixXR = largeDummyValue
            ixFIG = adjText.find( '\\fig ' )
            if ixFIG == -1: ixFIG = adjText.find( '\\FIG ' )
            if ixFIG == -1: ixFIG = largeDummyValue
            ixSTR = adjText.find( '\\str ' )
            if ixSTR == -1: ixSTR = adjText.find( '\\STR ' )
            if ixSTR == -1: ixSTR = largeDummyValue
            ixSEM = adjText.find( '\\sem ' )
            if ixSEM == -1: ixSEM = adjText.find( '\\SEM ' )
            if ixSEM == -1: ixSEM = largeDummyValue
            ixWW = adjText.find( '\\ww ' )
            if ixWW == -1: ixWW = adjText.find( '\\WW ' )
            if ixWW == -1: ixWW = largeDummyValue
            ixVP = adjText.find( '\\vp ' )
            if ixVP == -1: ixVP = adjText.find( '\\VP ' )
            if ixVP == -1: ixVP = largeDummyValue
            ix1 = min( ixFN, ixEN, ixXR, ixFIG, ixSTR, ixSEM, ixWW, ixVP )
        #if extras: print( "Fix gave {!r} and {!r}".format( adjText, extras ) )
        #if len(extras)>1: print( "Mutiple fix gave {!r} and {!r}".format( adjText, extras ) )

        # Check for anything left over
        if '\\f ' in adjText or '\\f*' in adjText or '\\x ' in adjText or '\\x*' in adjText:
            fixErrors.append( lineLocationSpace + _("Unable to properly process footnotes and cross-references in \\{}: {}").format( originalMarker, adjText ) )
            logging.error( _("processLineFix: Unable to properly process footnotes and cross-references {} {}:{} in \\{}: {}").format( self.BBB, C, V, originalMarker, adjText ) )
            self.addPriorityError( 82, C, V, _("Invalid footnotes or cross-references") )
            if BibleOrgSysGlobals.strictCheckingFlag: halt


        if self.objectTypeString == 'SwordBibleModule': # Move Sword notes out to extras
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
                    if BibleOrgSysGlobals.debugFlag:
                        assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                        assert ixStart < ixClose < ixEnd
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
                    if BibleOrgSysGlobals.debugFlag:
                        assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                        assert ixStart < ixClose < ixEnd
                    stuff = adjText[ixStart+6:ixClose]
                    adjText = adjText[:ixStart] + adjText[ixEnd+7:]
                    noteContents = adjText[ixClose+1:ixEnd]
                    #print( "now" "'"+adjText+"'" )
                    #print( "st", "'"+stuff+"'", )
                    if stuff == 'type="study"': code = 'sn'
                    else: halt # programming error
                    extras.append( InternalBibleExtra(code,ixStart+ixEnd-ixClose,stuff,stuff) )
                    #ixStart += 0
                elif remainingText.startswith('<RF>1<Rf>') or remainingText.startswith('<RF>2<Rf>') \
                or remainingText.startswith('<RF>3<Rf>') or remainingText.startswith('<RF>4<Rf>'):
                    indexDigit = remainingText[4]
                    if BibleOrgSysGlobals.debugFlag: assert indexDigit.isdigit()
                    adjText = adjText[:ixStart] + adjText[ixStart+9:]
                    indexDigits.append( (indexDigit,ixStart,) )
                    #ixStart += 0
                elif remainingText.startswith( '<RF>1) ' ):
                    #print( "iT", C, V, indexDigits, remainingText )
                    if BibleOrgSysGlobals.debugFlag: assert indexDigits
                    ixEnd = adjText.find( '<Rf>' )
                    if BibleOrgSysGlobals.debugFlag: assert ixStart!=-1 and ixEnd!=-1
                    if BibleOrgSysGlobals.debugFlag: assert ixStart < ixEnd
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
                    print( "Something is wrong here:", C, V, text )
                    print( "iT", C, V, indexDigits, remainingText )
                    if BibleOrgSysGlobals.debugFlag: assert indexDigits
                    ixEnd = adjText.find( '<Rf>' )
                    if BibleOrgSysGlobals.debugFlag:
                        assert ixStart!=-1 and ixEnd!=-1
                        assert ixStart < ixEnd
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
                    #assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                    #assert ixStart < ixClose < ixEnd
                    #stuff = adjText[ixStart+13:ixClose]
                    #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+14:]
                    ##print( "st", "'"+stuff+"'", )
                    #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                #elif adjText[ixStart:].startswith( '<seg>' ):
                    #ixEnd = adjText.find( '</seg>' )
                    ##if ixEnd != -1: ixEnd += 3
                    #print( adjText, 'sg s c e', ixStart, ixClose, ixEnd )
                    #assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                    #assert ixStart < ixClose < ixEnd
                    #stuff = adjText[ixStart+5:ixClose]
                    #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+6:]
                    ##print( "st", "'"+stuff+"'", )
                    #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                #elif adjText[ixStart:].startswith( '<divineName>' ):
                    #ixEnd = adjText.find( '</divineName>' )
                    ##if ixEnd != -1: ixEnd += 3
                    #print( adjText, 'sg s c e', ixStart, ixClose, ixEnd )
                    #assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                    #assert ixStart < ixClose < ixEnd
                    #stuff = adjText[ixStart+12:ixClose]
                    #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+13:]
                    ##print( "st", "'"+stuff+"'", )
                    #extras.append( ('tc',ixStart+ixEnd-ixClose,stuff,stuff) )
                #elif adjText[ixStart:].startswith( '<milestone ' ):
                    #ixEnd = adjText.find( '/>' )
                    ##if ixEnd != -1: ixEnd += 3
                    #print( adjText, 'ms s e', ixStart, ixEnd )
                    #assert ixStart!=-1 and ixEnd!=-1
                    #assert ixStart < ixEnd
                    #stuff = adjText[ixStart+11:ixEnd]
                    #adjText = adjText[:ixStart] + adjText[ixEnd+2:]
                    #print( "st", "'"+stuff+"'", )
                    #extras.append( ('ms',ixStart,stuff,stuff) )
                #elif adjText[ixStart:].startswith( '<title ' ):
                    #ixEnd = adjText.find( '</title>' )
                    ##if ixEnd != -1: ixEnd += 3
                    #print( adjText, 't s c e', ixStart, ixClose, ixEnd )
                    #assert ixStart!=-1 and ixClose!=-1 and ixEnd!=-1
                    #assert ixStart < ixClose < ixEnd
                    #stuff = adjText[ixStart+7:ixClose]
                    #adjText = adjText[:ixStart] + adjText[ixClose+1:ixEnd] + adjText[ixEnd+8:]
                    ##print( "st", "'"+stuff+"'", )
                    #extras.append( ('ti',ixStart+ixEnd-ixClose,stuff,stuff) )
                else:
                    #print( "Ok. Still have < in:", adjText )
                    ixStart += 1 # So it steps past fields that we don't remove, e.g., <divineName>xx</divineName>
            #print( "aT", adjText )
            #print( "exp", extras )
            #adjText = adjText.replace( '<transChange type="added">', '<it>' ).replace( '</transChange>', '</it>' )

        # Check trailing spaces again now
        if adjText and adjText[-1].isspace():
            #print( 10, self.BBB, C, V, _("Trailing space before note at end of line") )
            fixErrors.append( lineLocationSpace + _("Removed trailing space before note in \\{}: {!r}").format( originalMarker, text ) )
            logging.warning( _("processLineFix: Removed trailing space before note after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, originalMarker, text ) )
            self.addPriorityError( 10, C, V, _("Trailing space before note at end of line") )
            adjText = adjText.rstrip()
            #print( "QQQ6: rstrip" ); halt
            #print( originalMarker, "'"+text+"'", "'"+adjText+"'" )

        # Now remove all character formatting from the cleanText string (to make it suitable for indexing and search routines
        #   This includes markers like \em, \bd, \wj, etc. as well as \w with any attributes already removed
        #if "Cook" in adjText:
            #print( "\nhere", self.objectTypeString )
            #print( "adjT", repr(adjText) )
        if self.objectTypeString == 'SwordBibleModule': # remove character formatting
            cleanText = adjText \
                .replace( '<title type="chapter">', '' ).replace( '</title>', '' ) \
                .replace( '<transChange type="added">', '' ).replace( '</transChange>', '' ) \
                .replace( '<seg><divineName>', '' ).replace( '</divineName></seg>', '' )
                # .replace( '<milestone marker="Â¶" subType="x-added" type="x-p"/>', '' )
                # .replace( '<milestone marker="Â¶" type="x-p"/>', '' )
                # .replace( '<milestone type="x-extra-p"/>', '' )
            if '<' in cleanText or '>' in cleanText:
                print( "\nFrom:", C, V, text )
                print( " Still have angle brackets left in:", cleanText )
        else: # not Sword
            #print( BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList() )
            cleanText = adjText \
                            .replace( '&amp;', '&' ) \
                            .replace( '&#39;', "'" ) \
                            .replace( '&lt;',  '<' ) \
                            .replace( '&gt;',  '>' ) \
                            .replace( '&quot;', '"' ) # Undo any replacements above
            if '\\' in cleanText: # we will first remove known USFM character formatting markers
                for possibleCharacterMarker in BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList():
                    tryMarkers = []
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNumberableMarker( possibleCharacterMarker ):
                        for d in ('1','2','3','4','5'):
                            tryMarkers.append( '\\'+possibleCharacterMarker+d+' ' )
                    tryMarkers.append( '\\'+possibleCharacterMarker+' ' )
                    #print( "tryMarkers", tryMarkers )
                    for tryMarker in tryMarkers:
                        while tryMarker in cleanText:
                            #print( "Removing {!r} from {!r}".format( tryMarker, cleanText ) )
                            cleanText = cleanText.replace( tryMarker, '', 1 ) # Remove it
                            tryCloseMarker = '\\'+possibleCharacterMarker+'*'
                            shouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( possibleCharacterMarker )
                            if shouldBeClosed == 'A' \
                            or shouldBeClosed == 'O' and tryCloseMarker in cleanText:
                                #print( "Removing {!r} from {!r}".format( tryCloseMarker, cleanText ) )
                                cleanText = cleanText.replace( tryCloseMarker, '', 1 ) # Remove it
                    if not '\\' in cleanText: break # no point in looping further
                while '\\' in cleanText: # we will now try to remove any bad markers
                    ixBS = cleanText.index( '\\' )
                    ixSP = cleanText.find( ' ', ixBS )
                    ixAS = cleanText.find( '*', ixBS )
                    if ixSP == -1: ixSP=largeDummyValue
                    if ixAS == -1: ixAS=largeDummyValue
                    ixEND = min( ixSP, ixAS )
                    if ixEND != largeDummyValue: # remove the marker and the following space or asterisk
                        #print( "Removing unknown marker {!r} from {!r}".format( cleanText[ixBS:ixEND+1], cleanText ) )
                        cleanText = cleanText[:ixBS] + cleanText[ixEND+1:]
                    else: # we didn't find a space or asterisk so it's at the end of the line
                        #print( "text: {!r}".format( text ) )
                        #print( "adjText: {!r}".format( adjText ) )
                        #print( "cleanText: {!r}".format( cleanText ) )
                        #print( "len={} ixBS={} ixSP={} ixAS={} ixEND={}".format( len(cleanText), ixBS, ixSP, ixAS, ixEND ) )
                        #print( "cleanText part: …{!r}<<HERE>>{!r}…".format( cleanText[ixBS-10:ixBS], cleanText[ixBS:ixBS+20] ) )
                        if BibleOrgSysGlobals.debugFlag:
                            assert ixSP==largeDummyValue and ixAS==largeDummyValue and ixEND==largeDummyValue
                            logging.critical( "InternalBibleBook.processLines.processLineFix: truncating {} {}:{} {} line".format( self.BBB, C, V, originalMarker ) )
                        cleanText = cleanText[:ixBS].rstrip()
                        #print( "QQQ7: rstrip" ); halt
                        #print( "cleanText: {!r}".format( cleanText ) )
                if '\\' in cleanText:
                    logging.critical( "processLineFix: Why do we still have a backslash in {!r} from {!r}?".format( cleanText, adjText ) )
                    if BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.debugFlag: # Now do a final check that we did everything right
            for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                assert extraText # Shouldn't be blank
                #if self.objectTypeString == 'USFM': assert extraText[0] != '\\' # Shouldn't start with backslash code
                assert extraText[-1] != '\\' # Shouldn't end with backslash code
                #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                assert extraIndex >= 0
                # This can happen with multiple notes at the end separated by spaces
                #if extraIndex > len(adjText)+1: print( "Programming Note: extraIndex {} is way more than text length of {} with {!r}".format( extraIndex, len(adjText), text ) )
                assert extraType in BOS_EXTRA_TYPES
                assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the contents of these fields should be in extras

        # if 'afterMoses' in cleanText or 'andthe' in cleanText: halt
        # if 'afterMoses' in adjText or 'andthe' in adjText: halt
        # print( f"{self.BBB} Returning '{adjText}' '{cleanText}'" )
        # if self.BBB == 'JOS' and C == '2': halt
        return adjText, cleanText, extras
    # end of InternalBibleBook.processLines.processLineFix


    def addNestingMarkers( self ) -> None:
        """
        Or 'addEndMarkers'. End/Closing markers start with not sign ¬.
            (This is called BEFORE addVerseStartMarkers().)

        Go through self._processedLines and add entries
            for the end of verses, chapters, etc.

        NOTE: This is complex because sometimes different nestings overlap,
            e.g., often s1 sections open and close within a chapter
                    but chapters might open and close within a s1 section (esp. a ms1 section)
                  or chapters and s1 sections might partially overlap.

        We put matching end markers on c and v markers,
            paragraph markers, e.g., p, q,
            XXXX NO XXXX section headings, e.g., s1
            iot section (enclosing io fields), and
            lists (and intro lists).

        Example:
            p
            v       7
            v~      Verse seven text
            ¬v      7
            ¬p
            ¬c      4
            c       5
            v=      1
            s       Section heading (could also be s1)
            p
            c#      5
            v       1
            v~      Verse one text
            q1
            p~      More verse one text
            ¬v      1
            v       2

        Note: the six parameters for InternalBibleEntry are
            marker, originalMarker, adjustedText, cleanText, extras, originalText
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"addNestingMarkers() for {self.BBB}" )

        newLines:List[InternalBibleEntry] = InternalBibleEntryList()
        openMarkers:List[str] = []

        def openMarker( newMarker:str ) -> None:
            """
            Insert a new open marker into the book.
            """
            if BibleOrgSysGlobals.debugFlag: assert newMarker not in openMarkers
            newLines.append( InternalBibleEntry(newMarker, None, None, '', None, None) )
            openMarkers.append( newMarker )
        # end of addNestingMarkers.openMarker

        def getLastOpenMarker() -> Optional[str]:
            """
            Return the last open marker if there's any
                otherwise return None.
            """
            if openMarkers: return openMarkers[-1]
            return None # if no open markers

        def closeLastOpenMarker( withText:Optional[str]='' ) -> None:
            """
            Close the last marker (with the "not" sign) and pop it off our list
            """
            if debuggingThisModule:
                print( f"InternalBibleBook.addNestingMarkers.closeLastOpenMarker( withText={withText!r} ) for {openMarkers[-1] if openMarkers else 'INVALID'} from {openMarkers}" )
            #print( "  add", '¬'+openMarkers[-1], withText, "in closeLastOpenMarker" )
            newLines.append( InternalBibleEntry('¬'+openMarkers.pop(), None, None, withText, None, None) )
        # end of addNestingMarkers.closeLastOpenMarker

        def closeOpenMarker( endMarker:str, withText:str='' ) -> None:
            """
            Close the given marker (with the "not" sign) and delete it out of our list

            Don't use this if you can use closeLASTopenMarker
                because you are closing markers out of order
            """
            assert openMarkers
            lastMarker = openMarkers[-1]
            if debuggingThisModule:
                print( f"InternalBibleBook.addNestingMarkers.closeOpenMarker( {endMarker}, {withText!r} ) @ {self.BBB} {C}:{V} rather than {lastMarker} from {openMarkers}" )
            if endMarker == lastMarker:
                print( f"  You should have called closeLastOpenMarker for closing {endMarker} with {openMarkers} @ {self.BBB} {C}:{V}" )
                halt # You should have called closeLastOpenMarker()
            if endMarker=='c' and lastMarker=='s1':
                logging.info( f"  We have a {lastMarker} section crossing a chapter boundary at {self.BBB} {C}:{V}" )
                # There's too many of these to document
                #if (self.BBB,C,V) not in (('GEN','1','31'),('GEN','27','46'),('GEN','29','35'),('GEN','46','34'),('GEN','49','33'),):
                    #halt # Add ref of section crossing chapter boundary please
            elif endMarker != lastMarker:
                logging.info( f"  We have a {lastMarker} in a segment at {self.BBB} {C}:{V} that previously crossed a boundary" )
                # There's too many of these to document
                #if (self.BBB,C,V) not in (('GEN','2','4'),  # section heading from chapter 1
                                          #('GEN','2','23'),('GEN','3','13')): # paragraphs starting inside verses
                    #halt # Why are we closing them out of order???
            ie = openMarkers.index( endMarker ) # Must be there
            #print( "  add", '¬'+openMarkers[ie], withText, "in closeOpenMarker" )
            newLines.append( InternalBibleEntry('¬'+openMarkers.pop( ie ), None, None, withText, None, None) )
        # end of addNestingMarkers.closeOpenMarker


        # Main code for addNestingMarkers
        ourHeadingMarkers = ( 's','s1','s2','s3','s4', 'is','is1','is2','is3','is4', 'qa' )
        ourIntroOutlineMarkers = ( 'io','io1','io2','io3','io4' )
        ourIntroListMarkers = ( 'ili','ili1','ili2','ili3','ili4' )
        ourMainListMarkers = ( 'li','li1','li2','li3','li4' )
        haveIntro = 0 # Count them to detect errors
        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastJ = len(self._processedLines) - 1
        lastMarker = lastPMarker = lastSMarker = None
        number_of_processed_lines = len( self._processedLines )
        for j,dataLine in enumerate( self._processedLines ):

            def chapterHasEnded( currentIndex:int ) -> bool:
                """
                Determines if future lines start a new chapter or are still in this chapter?
                """
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextMarker = self._processedLines[k].getMarker()
                    if nextMarker == 'c':
                        #print( "  cE = True1", nextMarker )
                        return True
                    if nextMarker in ( 's1', 'v', 'v~','p~', ):
                        #print( "  cE = False", nextMarker )
                        return False
                #print( "  cE = True2" )
                return True # at end of file
            # end of addNestingMarkers.chapterHasEnded

            def verseHasEnded( currentIndex:int ) -> bool:
                """
                Determines if future lines start a new verse or are still in this verse?
                """
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextMarker = self._processedLines[k].getMarker()
                    if nextMarker == 'v':
                        #print( "  vE = True1", nextMarker )
                        return True
                    if nextMarker in ( 'v~','p~', ):
                        #print( "  vE = False", nextMarker )
                        return False
                #print( "  vE = True2" )
                return True # at end of file
            # end of addNestingMarkers.verseHasEnded

            def sectionHasEnded( currentSectionMarker:str, currentIndex:int ) -> bool:
                """
                Determines if future lines start a new verse or are still in this verse?
                """
                assert currentSectionMarker
                otherPossibilities:List[str] = []
                if currentSectionMarker[-1] in '234':
                    for z in range( 1, int(currentSectionMarker[-1]) ):
                        otherPossibilities.append( f'{currentSectionMarker[:-1]}{z}' )
                if currentSectionMarker in ('s1','s2','s3','s4'):
                    otherPossibilities.append( 'ms1' )
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextMarker = self._processedLines[k].getMarker()
                    if nextMarker == currentSectionMarker:
                        #print( "  sE = True1", nextMarker )
                        return True
                    if nextMarker in otherPossibilities: # A higher-level section
                        #print( "  sE = True1", nextMarker )
                        return True
                    if nextMarker in ( 'c', 'v', 'v~','p~', ):
                        #print( "  sE = False", nextMarker )
                        return False
                #print( "  sE = True2" )
                return True # at end of file
            # end of addNestingMarkers.sectionHasEnded

            def paragraphHasEnded( currentIndex:int ) -> bool:
                """
                Determines if future lines start a new paragraph or are still in this paragraph?
                """
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextMarker = self._processedLines[k].getMarker()
                    if nextMarker in USFM_BIBLE_PARAGRAPH_MARKERS \
                    or nextMarker in ourMainListMarkers:
                        #print( "  pE = True1", nextMarker )
                        return True
                    if nextMarker in ( 'v', 'v~','p~', ):
                        #print( "  pE = False", nextMarker )
                        return False
                #print( "  pE = True2" )
                return True # at end of file
            # end of addNestingMarkers.paragraphHasEnded

            def findNextRelevantMarker( currentIndex:int ) -> Optional[str]:
                """
                Returns the next v=, v, v~ or p~ marker.

                Returns None if we're at the end of the book.
                """
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextRelevantMarker = self._processedLines[k].getMarker()
                    if nextRelevantMarker in ( 'v=', 'v', 'v~','p~', ) \
                    or nextRelevantMarker in ourHeadingMarkers \
                    or nextRelevantMarker in USFM_BIBLE_PARAGRAPH_MARKERS:
                        #print( "  nRM =", nextRelevantMarker )
                        return nextRelevantMarker # Found one
                return None
            # end of addNestingMarkers.findNextRelevantMarker

            def findNextRelevantListMarker( currentIndex:int ) -> Optional[str]:
                """
                Returns the next c, v=, v, v~ or p~ marker.

                Returns None if we're at the end of the book.
                """
                for k in range( currentIndex+1, number_of_processed_lines ):
                    nextRelevantListMarker = self._processedLines[k].getMarker()
                    if nextRelevantListMarker not in ( 'c', 'v=', 'v', 'v~','p~', ):
                        #print( "  nRLM1 =", nextRelevantListMarker )
                        return nextRelevantListMarker # Found one
                return None
            # end of addNestingMarkers.findNextRelevantListMarker


            # Main loop in addNestingMarkers
            marker, text = dataLine.getMarker(), dataLine.getCleanText()
            #nextDataLine = self._processedLines[j+1] if j<lastJ else None
            #nextMarker = nextDataLine.getMarker() if nextDataLine is not None else None
            try: nextMarker = self._processedLines[j+1].getMarker()
            except IndexError: nextMarker = None
            try: nextNextMarker = self._processedLines[j+2].getMarker()
            except IndexError: nextNextMarker = None
            try: nextNextNextMarker = self._processedLines[j+1].getMarker()
            except IndexError: nextNextNextMarker = None
            if debuggingThisModule:
                print( f"InternalBibleBook.processLines.addNestingMarkers: {j:4} {self.BBB} {C}:{V} {marker}={text!r} then {nextMarker} now have {openMarkers}" )

            if marker in USFM_ALL_INTRODUCTION_MARKERS and 'intro' not in openMarkers:
                openMarker( 'intro' )
                haveIntro += 1 # now 'true' but counted to detect errors
                if haveIntro > 1:
                    logging.warning( "Multiple introduction sections in {}!!!".format( self.BBB ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

            lastOpenMarker = getLastOpenMarker()
            if lastOpenMarker=='iot' and marker not in ourIntroOutlineMarkers: closeLastOpenMarker()
            if lastOpenMarker=='ilist' and marker not in ourIntroListMarkers: closeLastOpenMarker()
            if lastOpenMarker=='list' and marker not in ourMainListMarkers and marker not in ('v~','p~',):
                # This is more complex coz can cross v and c boundaries
                #print( "Shall we close", marker, findNextRelevantListMarker(j), findNextRelevantMarker(j) )
                if findNextRelevantListMarker(j) not in ourMainListMarkers:
                    closeOpenMarker( 'list' )

            if marker == 'c':
                if 'intro' in openMarkers:
                    for lMarker in openMarkers[::-1]: # Get a reversed copy (coz we are deleting members)
                        closeLastOpenMarker()
                    #haveIntro = False # Just so we don't repeat this
                if getLastOpenMarker() == 'v':
                    closeLastOpenMarker( withText=V )
                elif 'v' in openMarkers: closeOpenMarker( 'v', V )
                if 'c' not in openMarkers: # we're just starting chapter one
                    openMarker( 'chapters' )
                else: # 'c' is in openMarkers so we're not just starting chapter one -- we're already in a chapter
                    nextRelevantMarker = findNextRelevantMarker( j )
                    if openMarkers[-1] in USFM_BIBLE_PARAGRAPH_MARKERS \
                    and (nextRelevantMarker in USFM_BIBLE_PARAGRAPH_MARKERS or nextRelevantMarker in ourHeadingMarkers):
                        # New paragraph starts immediately in next chapter, so close this paragraph now
                        closeLastOpenMarker() # Close whatever paragraph marker that was
                    if openMarkers[-1] in ourHeadingMarkers and nextRelevantMarker in ourHeadingMarkers:
                        closeLastOpenMarker() # Close whatever heading marker that was
                if openMarkers and openMarkers[-1]=='c': closeLastOpenMarker( withText=C )
                elif 'c' in openMarkers: closeOpenMarker( 'c', C )
                C, V = text, '0'
                if BibleOrgSysGlobals.debugFlag: assert marker not in openMarkers
                openMarkers.append( marker )
            elif marker == 'vp#':
                #print( "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.name ) )
                if debuggingThisModule:
                    if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                if getLastOpenMarker() == 'v': closeLastOpenMarker()
                elif 'v' in openMarkers: # we're not starting the first verse
                    closeOpenMarker( 'v', V )
            elif marker == 'v':
                while True:
                    madeChange = False
                    lastOpenMarker = getLastOpenMarker()
                    if lastOpenMarker=='v': closeLastOpenMarker( withText=V ); madeChange = True
                    elif lastPMarker and lastOpenMarker in USFM_BIBLE_PARAGRAPH_MARKERS and paragraphHasEnded( j ):
                        if lastOpenMarker == lastPMarker: lastPMarker = None
                        closeLastOpenMarker(); madeChange = True
                    if not madeChange: break
                if 'v' in openMarkers: # still, we're not starting the first verse
                    #print( "Why didn't the above work????" ); halt
                    closeOpenMarker( 'v', V )
                V = text
                #if C=='3' and V=='3': break
                if BibleOrgSysGlobals.debugFlag: assert marker not in openMarkers
                openMarkers.append( marker )
            elif marker == 'iot':
                if BibleOrgSysGlobals.debugFlag: assert 'iot' not in openMarkers
                openMarkers.append( 'iot' ) # to ensure that we add an iot closing marker later
            elif marker in ourIntroOutlineMarkers:
                if lastMarker not in ourIntroOutlineMarkers:
                    if lastMarker != 'iot': # Seems we didn't have an iot in the file :-(
                        #print( "InternalBibleBook.processLines.addNestingMarkers: {} {}:{} Adding iot marker before {}".format( self.BBB, C, V, marker ) )
                        openMarker( 'iot' )
                #haveIntro = True
            elif marker in ourIntroListMarkers:
                if lastMarker not in ourIntroListMarkers:
                    #print( "InternalBibleBook.processLines.addNestingMarkers: {} {}:{} Adding ilist marker before {} after {}".format( self.BBB, C, V, marker, lastMarker ) )
                    openMarker( 'ilist' )
                #haveIntro = True
            elif marker in ourHeadingMarkers: # must be checked BEFORE USFM_ALL_INTRODUCTION_MARKERS because they overlap
                #if marker=='is' or marker=='is1': print( "XX", marker, openMarkers, lastPMarker )
                while True:
                    madeChange = False
                    lastOpenMarker = getLastOpenMarker()
                    if lastOpenMarker=='v' and verseHasEnded( j ):
                        closeLastOpenMarker( withText=V ); madeChange = True
                    elif lastPMarker and lastOpenMarker == lastPMarker:
                        closeLastOpenMarker(); madeChange = True
                        lastPMarker = None
                    elif lastSMarker and lastOpenMarker in ourHeadingMarkers and sectionHasEnded( lastSMarker, j ):
                        closeLastOpenMarker(); madeChange = True
                        if lastOpenMarker == lastSMarker: lastSMarker = None
                    if not madeChange: break
                if 'v' in openMarkers and verseHasEnded( j ): closeOpenMarker( 'v', V )
                if lastPMarker in openMarkers:
                    logging.info( f"We have a {marker} section heading possibly inside a verse @ {self.BBB} {C}:{V}" )
                    closeOpenMarker( lastPMarker ); lastPMarker = None
                lastOpenMarker = getLastOpenMarker()
                if lastSMarker and lastOpenMarker == lastSMarker:
                    closeLastOpenMarker(); lastSMarker = None
                elif lastSMarker in openMarkers: closeOpenMarker( lastSMarker ); lastSMarker = None
                if BibleOrgSysGlobals.debugFlag: assert marker not in openMarkers
                openMarkers.append( marker )
                lastSMarker = marker
                #if marker=='is' or marker=='is1': print( "YY", marker, openMarkers, lastPMarker )
            #elif marker in USFM_ALL_INTRODUCTION_MARKERS:
                #haveIntro = True
            elif marker in ourMainListMarkers:
                assert not text
                while True:
                    madeChange = False
                    lastOpenMarker = getLastOpenMarker()
                    if lastOpenMarker=='v' and verseHasEnded( j ):
                        closeLastOpenMarker( withText=V ); madeChange = True
                    elif lastPMarker and lastOpenMarker == lastPMarker:
                        closeLastOpenMarker(); madeChange = True
                        lastPMarker = None
                    if not madeChange: break
                if 'v' in openMarkers and verseHasEnded( j ): closeOpenMarker( 'v', V )
                if lastPMarker in openMarkers: closeOpenMarker( lastPMarker ); lastPMarker = None
                if 'list' not in openMarkers:
                    #print( "InternalBibleBook.processLines.addNestingMarkers: {} {}:{} Adding list marker before {}".format( self.BBB, C, V, marker ) )
                    openMarker( 'list' )
                if BibleOrgSysGlobals.debugFlag: assert marker not in openMarkers
                openMarkers.append( marker )
                lastPMarker = marker
            elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                assert not text
                #print( f"Got {marker} @ {self.BBB} {C}:{V} lastPMarker={lastPMarker}" )
                while True:
                    madeChange = False
                    lastOpenMarker = getLastOpenMarker()
                    if lastOpenMarker=='v' and verseHasEnded( j ):
                        closeLastOpenMarker( withText=V ); madeChange = True
                    elif lastPMarker and lastOpenMarker == lastPMarker:
                        closeLastOpenMarker(); madeChange = True
                        lastPMarker = None
                    if not madeChange: break
                if 'v' in openMarkers and verseHasEnded( j ): closeOpenMarker( 'v', V )
                if lastPMarker in openMarkers: closeOpenMarker( lastPMarker ); lastPMarker = None
                if BibleOrgSysGlobals.debugFlag: assert marker not in openMarkers
                openMarkers.append( marker )
                lastPMarker = marker
            #else: print( "  Ignore {}={}".format( marker, repr(text) ) )

            newLines.append( dataLine )
            if BibleOrgSysGlobals.debugFlag and len(openMarkers) > 7: # Should only be 7: e.g., chapters c s1 p v list li1
                print( newLines[-20:] )
                print(openMarkers); halt
            lastMarker = marker

        if openMarkers: # Close any left-over open markers
            if 'ilist' in openMarkers or 'iot' in openMarkers:
                print( "InternalBibleBook.processLines.addNestingMarkers: stillOpen", self.BBB, openMarkers )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    if self.BBB not in ('GLS','BAK',): halt
            for lMarker in openMarkers[::-1]: # Get a reversed copy (coz we are deleting members)
                if lMarker == 'v': closeLastOpenMarker( withText=V )
                elif lMarker == 'c': closeLastOpenMarker( withText=C )
                else: closeLastOpenMarker()
        assert not openMarkers

        if 0:
            markerListString = ' '.join(entry.getMarker() for entry in newLines)
            print( '\n'+self.BBB, "aNM markerListString1", markerListString )
            assert 'v= ¬v' not in markerListString
            #assert 'q1 p~ ¬v ¬q1' not in markerListString
            #if self.BBB=='GEN': halt

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            # Check the results of this function
            #if 1: # Display indented markers
                #from BibleOrgSys.Internals.InternalBibleInternals import BOS_NESTING_MARKERS
                ##markerList:List[str] = []
                #indentLevel = maxNestingLevel = 0
                #for j in range( len(newLines) ):
                    #entry = newLines[j]
                    #assert isinstance( entry, InternalBibleEntry )
                    ##print( f"{j:4}/ {entry}" )
                    #marker, cleanText = entry.getMarker(), entry.getCleanText()
                    #cleanTextString = f'={cleanText}' if cleanText else ''
                    #if marker in BOS_NESTING_MARKERS:
                        #indentLevel += 1
                        #if indentLevel > maxNestingLevel: maxNestingLevel = indentLevel
                    #print( f"{j:4} {indentLevel} {'  '*indentLevel}{marker}{cleanTextString}" )
                    #if marker[0] == '¬':
                        #if indentLevel > 0: indentLevel -= 1
                        #else: print( "INDENT LEVEL PROBLEM" ); halt
                    ##markerList.append( marker )
                #print( f"Maximum nesting level was {maxNestingLevel}" )

            # Find overlapping nesting (that's not necessarily an error, but could be)
            # Reorder if we need to
            # TODO: Try to get it right first time so doesn't need correcting!!!
            from BibleOrgSys.Internals.InternalBibleInternals import BOS_NESTING_MARKERS
            indentLevel = maxNestingLevel = 0
            markerContext:List[str] = []
            newLines2:List[InternalBibleEntry] = []
            C, V = '-1', '0'
            print( "\nChecking marker hierarchy…" )
            for j in range( len(newLines) ):
                thisEntry = newLines[j]
                assert isinstance( thisEntry, InternalBibleEntry )
                #print( f"{j:4}/ {thisEntry}" )
                marker, cleanText = thisEntry.getMarker(), thisEntry.getCleanText()
                if marker == 'c': C, V = cleanText, '0'
                elif marker == 'v': V = cleanText
                try: lastMarker = newLines[j-1].getMarker()
                except IndexError: lastMarker = None # Out of range
                try: nextMarker = newLines[j+1].getMarker()
                except IndexError: nextMarker = None # Out of range
                try: nextNextMarker = newLines[j+2].getMarker()
                except IndexError: nextNextMarker = None # Out of range
                cleanTextString = f'={cleanText}' if cleanText else f' in {self.BBB} {C}:{V}'
                if marker in BOS_NESTING_MARKERS:
                    markerContext.append( marker )
                    indentLevel += 1
                    if indentLevel > maxNestingLevel: maxNestingLevel = indentLevel
                print( f"CheckingNesting: {j:4} {indentLevel} {'  '*indentLevel}{marker}{cleanTextString} {markerContext} ({lastMarker}… …{nextMarker} {nextNextMarker})" )
                if marker[0] == '¬':
                    if indentLevel > 0: indentLevel -= 1
                    else: print( "INDENT LEVEL PROBLEM" ); halt

                    poppedMarker = markerContext.pop()
                    #print( f"poppedMarker={poppedMarker} marker[1:]={marker[1:]}" )
                    if marker[1:] != poppedMarker: # Then something is unusual with the nesting
                        if marker=='¬c' and poppedMarker=='s1' and nextMarker=='c':
                            logging.info( f"NESTING: Section ({poppedMarker}) crosses {self.BBB} {int(C)+1} chapter boundary: Got {marker} but expected ¬{poppedMarker}" )
                            # Fix up our context again
                            poppedMarker2 = markerContext.pop()
                            #print( f"poppedMarker2={poppedMarker2}" )
                            #assert poppedMarker2 == 'c' # FAILS BUT I THINK THE CHECKING CODE IS THE FAULT
                            markerContext.append( poppedMarker )
                            newLines2.append( thisEntry )
                        else:
                            logging.warning( f"CHECK {self.BBB} {C}:{V} NESTING: Got {marker} but expected ¬{poppedMarker}" )
                            #halt
                            newLines2.append( thisEntry )
                else:
                    newLines2.append( thisEntry )
                #markerList.append( marker )
            logging.info( f"Maximum {self.BBB} nesting level was {maxNestingLevel}" )
            newLines = newLines2

            if 0:
                markerListString = ' '.join(entry.getMarker() for entry in newLines)
                print( '\n'+self.BBB, "aNM markerListString2", markerListString )
                assert 'v= ¬v' not in markerListString
                assert 'q1 p~ ¬v ¬q1' not in markerListString
                #if self.BBB=='GEN': halt

        if debuggingThisModule and (len(newLines) != len(self._processedLines)):
            print( "  addNestingMarkers adjusted {} from {} lines to {} lines".format( self.BBB, len(self._processedLines), len(newLines) ) )
        self._processedLines = newLines # replace the old set
    # end of InternalBibleBook.processLines.addNestingMarkers


    def addVerseStartMarkers( self ) -> None:
        """
        We add v= lines here.
            (This is called AFTER addNestingMarkers().)

            c       5
            v=      1
            s       Section heading (could also be s1)
            p
            c#      5 (where it should be printed)
            v       1 (where it should be printed)
            v~      Verse one text
            q1
            p~      More verse one text

        or
            v       6
            v~      First part of verse six text
            q1
            p~      Last part of verse six text
            v=      7
            ms1     Main Section heading (esp. in Job or Psalms)
            mr1     (42:7-19) (Verse range for the ms1)
            s      Section heading
            p
            v       7 (where it should be printed)
            v~      Verse seven text

        Note: we don't number lines in the introduction (i.e., before c 1).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( f"addVerseStartMarkers() for {self.BBB}" )

        newLines:List[InternalBibleEntry] = InternalBibleEntryList()
        fieldsPreceded = ('s','s1','s2','s3','s4','sp')
        fieldsAlsoPreceded = USFM_ALL_BIBLE_PARAGRAPH_MARKERS \
                                + ('c#','r','d','ms1','mr','sr','sp','ib','b','nb','cl¤','tr')
        # NOTE: This code can add multiple v= lines if a sp follows a s1, etc.

        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastJ = len(self._processedLines) - 1
        for j,dataEntry in enumerate( self._processedLines ):
            assert isinstance( dataEntry, InternalBibleEntry )
            marker, text = dataEntry.getMarker(), dataEntry.getCleanText()
            if marker == 'c': C, V = text, '0'
            elif marker == 'v': V = text

            if marker in fieldsPreceded:
                #print( "  Looking ahead after {} {}:{} {!r} field…".format( self.BBB, C, V, marker ) )
                for k in range( 1, 5 ): # Number of lines to look ahead
                    if j+k <= lastJ:
                        nextDataEntry = self._processedLines[j+k]
                        assert isinstance( nextDataEntry, InternalBibleEntry )
                        nextMarker = nextDataEntry.getMarker()
                        if nextMarker == 'v':
                            vText = nextDataEntry.getCleanText()
                            #print( "  Adding v= {} at {} {}:{}".format( vText, self.BBB, C, V ) )
                            newLines.append( InternalBibleEntry('v=', 'v', nextDataEntry.getAdjustedText(), vText, None, nextDataEntry.getOriginalText()) )
                        #elif nextMarker in fieldsAlsoPreceded: print( "  Noting {} line".format( nextMarker ) )
                        elif nextMarker not in fieldsAlsoPreceded: break # got something else
            newLines.append( dataEntry ) # Put pre-existing line in

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            # Check the results of this function
            if 0: # Display indented markers
                from BibleOrgSys.Internals.InternalBibleInternals import BOS_NESTING_MARKERS
                #markerList:List[str] = []
                indentLevel = 0
                for j in range( len(newLines) ):
                    entry = newLines[j]
                    assert isinstance( entry, InternalBibleEntry )
                    #print( f"{j:4}/ {entry}" )
                    marker, cleanText = entry.getMarker(), entry.getCleanText()
                    if marker in BOS_NESTING_MARKERS:
                        indentLevel += 1
                    elif marker[0] == '¬':
                        if indentLevel > 0: indentLevel -= 1
                        else: print( "INDENT LEVEL PROBLEM" ); halt
                    print( f"{j:4} {'  '*indentLevel}{marker}={cleanText}" )
                    #markerList.append( marker )
            if 0:
                markerListString = ' '.join(entry.getMarker() for entry in newLines)
                print( self.BBB, "aVSM markerListString", markerListString )
                assert 'v= ¬v' not in markerListString
                assert 'q1 p~ ¬v ¬q1' not in markerListString
            #if self.BBB=='GEN': halt

        if debuggingThisModule and (len(newLines) != len(self._processedLines)):
            print( "  addVerseStartMarkers adjusted {} from {} lines to {} lines".format( self.BBB, len(self._processedLines), len(newLines) ) )
        self._processedLines = newLines # replace the old set
    # end of addVerseStartMarkers


    def reorderRawOsisLines( self ):
        """
        Using self._rawLines from OSIS input, reorder them before further processing.
        This is because processing the XML provides the markers in a different order from USFM
            and our internal format is more aligned to the USFM way of doing things.

        Footnotes etc have not yet been extracted from any of the lines
            but there are already v~ (and a few p~) lines created as the XML was extracted.
        """
        assert self.objectTypeString == 'OSIS'

        # For OSIS, change lines like:
        #    1/ p = ''
        #    2/ v = 17
        #    3/ p = ''
        #    4/ q1 = Text of verse 17.
        # to
        #    1/ p = ''
        #    2/ v = 17
        #    3/ q1 = Text of verse 17.
        newLines:List[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
        lastMarker = lastText = None
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for j,(marker,text) in enumerate( self._rawLines ):
            # Keep track of where we are
            #if marker == 'c': C, V = text, '0'
            #elif marker == 'v': V = text

            if lastMarker in USFM_BIBLE_PARAGRAPH_MARKERS and not lastText and marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                #if self.BBB=='JHN':
                    #print( "zap: {} {}:{} lines: {}={} {}={}".format( self.BBB, C, V, lastMarker, lastText, marker, text ) )
                lastMarker = None

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None: newLines.append( (lastMarker,lastText) ) # Save the very last line
        self._rawLines = newLines # replace the old set
        #print( 'RO-1', len(self._rawLines) )

        # For OSIS, change lines like:
        #    1/ v = 2 Text of verse 2.
        #    2/ v = 3
        #    3/ p = Text of verse 3.
        # to
        #    1/ v = 2 Text of verse 2.
        #    2/ p = ''
        #    2/ v = 3
        #    3/ v~ = Text of verse 3.
        newLines:List[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
        #lastJ = len(self._rawLines) - 1
        lastMarker = lastText = None
        #skip = False
        C, V = '-1', '-1' # So first/id line starts at -1:0
        #for j,(marker,text) in enumerate( self._rawLines ):
        for marker,text in self._rawLines:
            # Keep track of where we are
            #if marker == 'c': C, V = text, '0'
            #elif marker == 'v': V = text

            #if skip:
                #assert not text
                #skip = False
                #continue # skip this empty p or q marker completely now

            #nextMarker, nextText = self._rawLines[j+1] if j<lastJ else (None,None,)

            if lastMarker=='v' and marker in USFM_BIBLE_PARAGRAPH_MARKERS and text:
                #print( "increase: {} {}:{} lines: {}={} {}={}".format( self.BBB, C, V, lastMarker, lastText, marker, text ) )
                newLines.append( (marker,'') ) # Put the new blank paragraph marker before the v
                marker = 'v~' # Change the p marker to v~

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None: newLines.append( (lastMarker,lastText) ) # Save the very last line
        self._rawLines = newLines # replace the old set
        #print( 'RO-2', len(self._rawLines) )
        #print( self.BBB, "RL" )
        #for j in range( 50 ): print( "", j, self._rawLines[j] )

        # For OSIS, change lines like:
        #    1/ p = ''
        #    2/ q1 = ''
        #    3/ v = 3 Text of verse 3.
        # to
        #    1/ q1 = ''
        #    2/ v = 3 Text of verse 3.
        # Seems to only occur in the NT of the KJV
        # Also change
        #    1/ v = 25
        #    2/ v~ = Some text
        #    3/ p = '' (last line in file)
        # to remove that last line.
        newLines:List[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
        #lastJ = len(self._rawLines) - 1
        lastMarker = lastText = None
        #skip = False
        C, V = '-1', '-1' # So first/id line starts at -1:0
        #for j,(marker,text) in enumerate( self._rawLines ):
        for marker,text in self._rawLines:
            # Keep track of where we are
            #if marker == 'c': C, V = text, '0'
            #elif marker == 'v': V = text[:3]

            #if skip:
                #assert not text
                #skip = False
                #continue # skip this empty p or q marker completely now

            #nextMarker, nextText = self._rawLines[j+1] if j<lastJ else (None,None,)

            if lastMarker in USFM_BIBLE_PARAGRAPH_MARKERS and not lastText:
                if marker in USFM_BIBLE_PARAGRAPH_MARKERS and not text:
                    #print( "reduce: {} {}:{} lines: {}={} {}={}".format( self.BBB, C, V, lastMarker, lastText, marker, text ) )
                    lastMarker = None
                if marker=='c':
                    #print( "remove: {} {}:{} lines: {}={} {}={}".format( self.BBB, C, V, lastMarker, lastText, marker, text ) )
                    lastMarker = None

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None \
        and (lastText or lastMarker not in USFM_BIBLE_PARAGRAPH_MARKERS): # Don't write a blank p type marker at the end of the book
            newLines.append( (lastMarker,lastText) )
        self._rawLines = newLines # replace the old set
        #print( 'RO-3', len(self._rawLines) )
        #print( self.BBB, "RL" )
        #for j in range( 50 ): print( "", j, self._rawLines[j] )
    # end of InternalBibleBook.processLines.reorderRawOsisLines


    def processLines( self ):
        """
        Move notes out of the text into a separate area.
            Also, splits lines if a paragraph marker appears within a line.

            Uses self._rawLines and fills self._processedLines.
        """
        #if self._processedFlag: return # Can only do it once
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "  " + _("Processing {} ({} {!r}) {} lines…").format( self.objectNameString, self.objectTypeString, self.workName, self.BBB ) )
        if BibleOrgSysGlobals.debugFlag: assert not self._processedFlag # Can only do it once
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            assert self._rawLines # or else the book was totally blank
        #print( self._rawLines[:20] ); halt # for debugging


        def __doAppendEntry( adjMarker, originalMarker, text, originalText ):
            """
            Append the entry to self._processedLines
            """
            #nonlocal self.sahtCount

            if adjMarker=='b' and text:
                fixErrors.append( _("{} {}:{} Paragraph marker {!r} should not contain text").format( self.BBB, C, V, originalMarker ) )
                logging.error( "doAppendEntry: " + _("Illegal text for {!r} paragraph marker {} {}:{}").format( originalMarker, self.BBB, C, V ) )
                self.addPriorityError( 97, C, V, _("Should not have text following character marker '{}").format( originalMarker ) )

            if (adjMarker=='b' or adjMarker in BibleOrgSysGlobals.USFMParagraphMarkers) and text:
                # Separate the verse text from the paragraph markers
                self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, '', '', None, '') )
                adjMarker = 'p~'
                if not text.strip():
                    fixErrors.append( _("{} {}:{} Paragraph marker {!r} seems to contain only whitespace").format( self.BBB, C, V, originalMarker ) )
                    logging.error( "doAppendEntry: " + _("Only whitespace for {!r} paragraph marker {} {}:{}").format( originalMarker, self.BBB, C, V ) )
                    self.addPriorityError( 68, C, V, _("Only whitespace following character marker '{}").format( originalMarker ) )
                    return # nothing more to do here

            # Separate out the notes (footnotes and cross-references)
            adjText, cleanText, extras = self.processLineFix( C, V, adjMarker, text, fixErrors )
            #if adjMarker=='v~' and not cleanText:
                #if text or adjText:
                    #print( "Suppressed blank v~ for", self.BBB, C, V, "'"+text+"'", "'"+adjText+"'" ); halt
            # From here on, we use adjText (not text)

            #print( "marker {!r} text {!r}, adjText {!r}".format( adjMarker, text, adjText ) )
            if not adjText and not extras and ( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType(adjMarker)=='A' or adjMarker in ('v~','c~','c#',) ): # should always have text
                #print( "processLine: marker should always have text (ignoring it):", self.BBB, C, V, originalMarker, adjMarker, " originally '"+text+"'" )
                #fixErrors.append( lineLocationSpace + _("Marker {!r} should always have text").format( originalMarker ) )
                if self.objectTypeString in ('USFM2','USFM3','USX',):
                    if self.sahtCount != -1:
                        self.sahtCount += 1
                        if self.sahtCount <= self.maxNoncriticalErrorsPerBook:
                            logging.error( "doAppendEntry: " + _("Marker {!r} at {} should always have text").format( originalMarker, self.__makeErrorRef(C,V) ) )
                        else: # we've reached our limit
                            logging.error( "doAppendEntry: " + _("Additional \"Marker should always have text\" messages suppressed for {} {}").format( self.workName, self.BBB ) )
                            self.sahtCount = -1 # So we don't do this again (for this book)
                #self.addPriorityError( 96, C, V, _("Marker \\{} should always have text").format( originalMarker ) )
                if adjMarker != 'v~': # Save all other empty markers
                    self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, adjText, cleanText, extras, originalText) )
            else: # it's not an empty field
                #if C=='5' and V=='29': print( "processLine: {} {!r} to {} aT={!r} cT={!r} {}".format( originalMarker, text, adjMarker, adjText, cleanText, extras ) );halt
                self._processedLines.append( InternalBibleEntry(adjMarker, originalMarker, adjText, cleanText, extras, originalText) )
        # end of __doAppendEntry


        def processLine( originalMarker, originalText ):
            """
            Process one USFM line by
                normalizing USFM markers (e.g., q -> q1, s -> s1 )
                separating out the notes
                    and producing clean text suitable for searching
                    and then save the line.
            """
            nonlocal C, V, haveWaitingC
            if BibleOrgSysGlobals.debugFlag:
                if debuggingThisModule:
                    print( "processLine: {} {}:{} {!r} {!r}".format( self.BBB, C, V, originalMarker, originalText ) )
                assert originalMarker and isinstance( originalMarker, str )
                assert isinstance( originalText, str )
            if C=='-1': V = int(V) + 1 # Count intro lines
            #if self.BBB == 'PSA':
                #print( "processLine: {} {}:{} {!r} {!r}".format( self.BBB, C, V, originalMarker, originalText ) )
            text = originalText

            # Convert USFM markers like s to standard markers like s1
            try:
                adjustedMarker = originalMarker if originalMarker in BOS_ADDED_CONTENT_MARKERS else BibleOrgSysGlobals.loadedUSFMMarkers.toStandardMarker( originalMarker )
            except KeyError: # unknown marker
                logging.error( f"processLine-check: unknown {self.objectTypeString} originalMarker = {originalMarker}" )
                adjustedMarker = originalMarker # temp……

            def splitCNumber( inputString ):
                """
                Splits a chapter number and returns a list of bits (normally 1, maximum 2 if there's a foonote on the chapter number))
                """
                #print( "splitCNumber( {} )".format( repr(inputString) ) )
                bit1, bit2 = '', ''
                snStatus = 0 # 0 = idle, 1 = getting chapter number, 2 = getting rest
                for char in inputString:
                    if snStatus == 0:
                        if char.isdigit(): bit1 += char; snStatus = 1
                        else: bit2 += char; snStatus = 2
                    elif snStatus == 1:
                        if char.isdigit() or char in ('a','b','c','d','e','f'): bit1 += char
                        else: bit2 += char; snStatus = 2
                    elif snStatus == 2: bit2 += char
                    else: halt # programming error
                #nBits = [bit1]
                #if bit2: nBits.append( bit2 )
                #print( "  splitNumber is returning:", nBits )
                return [bit1,bit2] if bit2 else [bit1]
            # end of splitCNumber

            def splitVNumber( inputString ):
                """
                Splits a verse number and returns a list of bits (normally 2, maximum 3 if there's a foonote on the verse number)
                """
                #print( "splitVNumber( {} )".format( repr(inputString) ) )
                bit1, bit2, bit3 = '', '', ''
                snStatus = 0 # 0 = idle, 1 = getting verseNumber, 2 = getting footnote, 3 = getting rest
                for char in inputString:
                    if snStatus == 0:
                        if char.isdigit(): bit1 += char; snStatus = 1
                        elif char == '\\': bit2 += char; snStatus = 2
                        elif char == ' ': snStatus = 3
                        else: bit3 += char; snStatus = 3
                    elif snStatus == 1:
                        if char.isdigit() or char in ('a','b','c','d','e','f'): bit1 += char
                        elif char == '\\': bit2 += char; snStatus = 2
                        elif char == ' ': snStatus = 3
                        else: bit3 += char; snStatus = 3
                    elif snStatus == 2:
                        bit2 += char
                        if char == '*': snStatus = 3
                    elif snStatus == 3:
                        if bit3 or char != ' ':
                            bit3 += char
                    else: halt # programming error
                nBits = [bit1]
                if bit2: nBits.append( bit2 )
                nBits.append( bit3 )
                #print( "  splitCNumber is returning:", nBits )
                #if bit2: halt
                return nBits
            # end of splitCNumber


            # Main code of processLine -- keep track of where we are
            if originalMarker=='c' and text:
                if haveWaitingC: logging.warning( "Note: Two c markers with no intervening v markers at {} {}:{}".format( self.BBB, C, V ) )
                #C = text.split()[0]; V = '0'
                if text.lstrip() != text:
                    fixErrors.append( _("{} {}:{} Extra whitespace before chapter number").format( self.BBB, C, V ) )
                    logging.warning( "InternalBibleBook.processLine: " + _("Extra whitespace before chapter number around {}").format( self.__makeErrorRef(C,V) ) )
                    self.addPriorityError( 20, C, V, _("Extra whitespace before chapter number") )
                    text = text.lstrip()
                cBits = splitCNumber( text )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule and len(cBits)>1:
                    print( "InternalBibleBook.processLine: cbits", cBits )
                C, V = cBits[0], '0'
                #if C == '-1':
                    #fixErrors.append( _("{} {}:{} Chapter -1 is not allowed {!r}").format( self.BBB, C, V, text ) )
                    #logging.error( "InternalBibleBook.processLine: " + _("Found -1 {!r} in chapter marker {} {}:{}").format( text, self.BBB, C, V ) )
                    #self.addPriorityError( 97, C, V, _("Chapter -1 {!r} not allowed").format( text ) )
                    #if len(self._processedLines) < 30: # It's near the beginning of the file
                        #logging.warning( "Converting given chapter -1 to chapter zero in {}".format( self.BBB ) )
                        #C = '0' # Our best guess
                        #text = C + text[1:]
                haveWaitingC = C
                if len(cBits) > 1: # We have extra stuff on the c line after the chapter number
                    if cBits[1] == ' ': # It's just a space
                        fixErrors.append( _("{} {}:{} Extra space after chapter number").format( self.BBB, C, V ) )
                        logging.warning( "InternalBibleBook.processLine: " + _("Extra space after chapter number at {}").format( self.__makeErrorRef(C,V) ) )
                        self.addPriorityError( 10, C, V, _("Extra space after chapter number") )
                    elif not cBits[1].strip(): # It's more than a space but just whitespace
                        fixErrors.append( _("{} {}:{} Extra whitespace after chapter number").format( self.BBB, C, V ) )
                        logging.warning( "InternalBibleBook.processLine: " + _("Extra whitespace after chapter number at {}").format( self.__makeErrorRef(C,V) ) )
                        self.addPriorityError( 20, C, V, _("Extra whitespace after chapter number") )
                    else: # it's more than just whitespace
                        fixErrors.append( _("{} {}:{} Chapter number seems to contain extra material {!r}").format( self.BBB, C, V, cBits[1] ) )
                        logging.error( "InternalBibleBook.processLine: " + _("Extra {!r} material in chapter number {}").format( cBits[1], self.__makeErrorRef(C,V) ) )
                        self.addPriorityError( 30 if '\f ' in cBits[1] else 98, C, V, _("Extra {!r} material after chapter number").format( cBits[1] ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( "InternalBibleBook.processLine: Something on c line", self.BBB, C, V, repr(text), repr(cBits[1]) )
                        adjText, cleanText, extras = self.processLineFix( C, V, originalMarker, cBits[1], fixErrors )
                        if (adjText or cleanText or extras) and BibleOrgSysGlobals.debugFlag:
                            print( "InternalBibleBook.processLine: Something on c line", self.BBB, C, V, repr(text), repr(cBits[1]) )
                            if adjText: print( " adjText:", repr(adjText) )
                            if cleanText: print( " cleanText:", repr(cleanText) )
                            if extras: print( " extras:", extras )
                        self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, C, C, extras, C) ) # Write the chapter number as a separate line
                        adjustedMarker, text = 'c~', cBits[1]
            elif originalMarker=='cp' and text:
                V = '0'
                # Assertion is not correct in RSV52 ESG -- has cp in between verses
                if BibleOrgSysGlobals.debugFlag and self.BBB!='ESG': assert haveWaitingC # coz this should follow the c and precede the v
                haveWaitingC = text # We need to use this one instead of the c text
            elif originalMarker=='cl' and text:
                if BibleOrgSysGlobals.debugFlag:
                    if C != '-1':
                        print( "InternalBibleBook.processLine: Something before cl", self.workName, self.BBB, C, V, repr(text) )
                    if debuggingThisModule: assert V == '0' # coz this should precede the first c, or follow the c and precede the v
                if C == '-1': # it's before the first c
                    adjustedMarker = 'cl¤' # to distinguish it from the ones after the c's
            elif originalMarker=='v' and text:
                vBits = splitVNumber( text )
                V = vBits[0] # Get the actual verse number
                if C == '-1': # Some single chapter books don't have an explicit chapter 1 marker -- we'll make it explicit here
                    if not self.isSingleChapterBook:
                        fixErrors.append( _("{} {}:{} Chapter marker seems to be missing before first verse").format( self.BBB, C, V ) )
                        logging.error( "InternalBibleBook.processLine: " + _("Missing chapter number before first verse {} {}:{}").format( self.BBB, C, V ) )
                        self.addPriorityError( 98, C, V, _("Missing chapter number before first verse") )
                    C = '1'
                    if self.isSingleChapterBook and V!='1':
                        fixErrors.append( _("{} {}:{} Expected single chapter book to start with verse 1").format( self.BBB, C, V ) )
                        logging.error( "InternalBibleBook.processLine: " + _("Expected single chapter book to start with verse 1 at {} {}:{}").format( self.BBB, C, V ) )
                        self.addPriorityError( 38, C, V, _("Expected single chapter book to start with verse 1") )
                    poppedStuff = self._processedLines.pop()
                    if poppedStuff is not None:
                        lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText = poppedStuff
                    else: lastAdjustedMarker = lastOriginalMarker = lastAdjustedText = lastCleanText = lastExtras = lastOriginalText = None
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( self.BBB, "lastMarker (popped) was", lastAdjustedMarker, lastAdjustedText )
                    if lastAdjustedMarker in ('p','q1','m','nb',): # The chapter marker should go before this
                        self._processedLines.append( InternalBibleEntry('c', 'c', '1', '1', None, '1') ) # Write the explicit chapter number
                        self._processedLines.append( InternalBibleEntry(lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText) )
                    else: # Assume that the last marker was part of the introduction, so write it first
                        if lastAdjustedMarker not in ( 'ip', ):
                            logging.info( "{} {}:{} Assumed {} was part of intro after {}".format( self.BBB, C, V, lastAdjustedMarker, marker ) )
                            #if V!='13': halt # Just double-checking this code (except for one weird book that starts at v13)
                        if lastOriginalText:
                            self._processedLines.append( InternalBibleEntry(lastAdjustedMarker, lastOriginalMarker, lastAdjustedText, lastCleanText, lastExtras, lastOriginalText) )
                        self._processedLines.append( InternalBibleEntry('c', 'c', '1', '1', None, '1') ) # Write the explicit chapter number

                if haveWaitingC: # Add a false chapter number at the place where we normally want it printed
                    self._processedLines.append( InternalBibleEntry('c#', 'c', haveWaitingC, haveWaitingC, None, haveWaitingC) ) # Write the additional chapter number
                    haveWaitingC = False

                # Convert v markers to milestones only
                largeDummyValue = 99999
                text = text.lstrip()
                #print( "QQQ8: lstrip" )
                ixSP = text.find( ' ' )
                ixBS = text.find( '\\' )
                if ixSP == -1: ixSP=largeDummyValue
                if ixBS == -1: ixBS=largeDummyValue
                ix = min( ixSP, ixBS ) # Break at the first space or backslash
                if ix<ixSP: # It must have been the backslash first
                    #print( "processLine had an unusual case in {} {}:{}: {!r} {!r}".format( self.BBB, C, V, originalMarker, originalText ) )
                    fixErrors.append( '{} {}:{} '.format( self.BBB, C, V ) + _("Unusual field (after verse number): {!r}").format( originalText ) )
                    logging.error( "InternalBibleBook.processLine: " + _("Unexpected backslash touching verse number (missing space?) after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, originalMarker, originalText ) )
                    self.addPriorityError( 94, C, V, _("Unexpected backslash touching verse number (missing space?) in {!r}").format( originalText ) )
                if ix==largeDummyValue: # There's neither -- not unexpected if this is a translation in progress
                    #print( "processLine had an empty verse field in {} {}:{}: {!r} {!r} {} {} {}".format( self.BBB, C, V, originalMarker, originalText, ix, ixSP, ixBS ) )
                    # Removed these fix and priority errors, coz it seems to be covered in checkSFMs
                    # (and especially coz we don't know yet if this is a finished translation)
                    #fixErrors.append( lineLocationSpace + _("Nothing after verse number: {!r}").format( originalText ) )
                    #priority = 92
                    if self.objectTypeString in ('USFM2','USFM3','USX',):
                        #if self.nfvnCount == -1:
                            #priority = 12
                        #else:
                        if self.nfvnCount != -1:
                            self.nfvnCount += 1
                            if self.nfvnCount <= self.maxNoncriticalErrorsPerBook:
                                logging.error( "InternalBibleBook.processLine: " + _("Nothing following verse number after {} in \\{}: {!r}").format( self.__makeErrorRef(C,V), originalMarker, originalText ) )
                            else: # we've reached our limit
                                logging.error( "InternalBibleBook.processLine: " + _('Additional "Nothing following verse number" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                                self.nfvnCount = -1 # So we don't do this again (for this book)
                                #priority = 12
                    #self.addPriorityError( priority, C, V, _("Nothing following verse number in {!r}").format( originalText ) )
                    verseNumberBit = text
                    #print( "verseNumberBit is {!r}".format( verseNumberBit ) )
                    if BibleOrgSysGlobals.debugFlag:
                        assert verseNumberBit
                        assert ' ' not in verseNumberBit
                        assert '\\' not in verseNumberBit
                    self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, verseNumberBit, verseNumberBit, None, verseNumberBit) ) # Write the verse number (or range) as a separate line
                    return # Don't write a blank v~ field
                    #adjustedMarker, text = 'v~', ''
                else: # there is something following the verse number digits (starting with space or backslash)
                    verseNumberBit, verseNumberRest = text[:ix], text[ix:]
                    # Set flag to True if there's exactly one space between the verse number and the rest
                    goodStart =  len(verseNumberRest)>1 and verseNumberRest[0]==' ' and verseNumberRest[1]!=' '
                    #print( "verseNumberBit is {!r}, verseNumberRest is {!r}".format( verseNumberBit, verseNumberRest ) )
                    if BibleOrgSysGlobals.debugFlag:
                        assert verseNumberBit and verseNumberRest
                        assert '\\' not in verseNumberBit
                    if len(vBits)>2: # rarely happens (e.g., footnote on verse number)
                        adjText, cleanText, extras = self.processLineFix( C, V, originalMarker, vBits[1], fixErrors )
                        if (adjText or cleanText or extras) and BibleOrgSysGlobals.debugFlag:
                            print( "InternalBibleBook.processLine: Something on v line", self.BBB, C, V, repr(text), repr(vBits[1]) )
                            if adjText: print( " adjText:", repr(adjText) )
                            if cleanText: print( " cleanText:", repr(cleanText) )
                            if extras: print( " extras:", extras )
                        self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, verseNumberBit, verseNumberBit, extras, verseNumberBit) ) # Write the verse number (or range) as a separate line
                    else:
                        self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, verseNumberBit, verseNumberBit, None, verseNumberBit) ) # Write the verse number (or range) as a separate line

                    strippedVerseText = verseNumberRest.lstrip()
                    #print( "QQQ9: lstrip" )
                    if not strippedVerseText:
                        if self.owfvnCount != -1:
                            self.owfvnCount += 1
                            if self.owfvnCount <= self.maxNoncriticalErrorsPerBook:
                                logging.error( "InternalBibleBook.processLine: " + _("Only whitespace following verse number after {} in \\{}: {!r}").format( self.__makeErrorRef(C,V), originalMarker, originalText ) )
                            else: # we've reached our limit
                                logging.error( "InternalBibleBook.processLine: " + _('Additional "Only whitespace following verse number" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                                self.owfvnCount = -1 # So we don't do this again (for this book)
                        # Removed these fix and priority errors, coz it seems to be covered in checkSFMs
                        # (and especially coz we don't know yet if this is a finished translation)
                        #self.addPriorityError( 91, C, V, _("Only whitespace following verse number in {!r}").format( originalText ) )
                        return # Don't write a blank v~ field
                    # Set flag to True if there's exactly one space between the verse number and the rest
                    goodStart =  len(verseNumberRest)>1 and verseNumberRest[0]==' ' and verseNumberRest[1]!=' '
                    #print( 'Gs', goodStart, repr(verseNumberRest[1:] if goodStart else strippedVerseText) )
                    adjustedMarker, text = 'v~', verseNumberRest[1:] if goodStart else strippedVerseText

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if self.objectTypeString in ('USFM2','USFM3'):
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( text )
                ix = 0
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
                        if ix==0:
                            fixErrors.append( lineLocationSpace + _("Marker {!r} shouldn't appear within line in \\{}: {!r}").format( insideMarker, originalMarker, text ) )
                            logging.error( "InternalBibleBook.processLine: " + _("Marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, originalMarker, text ) ) # Only log the first error in the line
                            self.addPriorityError( 96, C, V, _("Marker \\{} shouldn't be inside a line").format( insideMarker ) )
                        thisText = text[ix:iMIndex].rstrip()
                        #print( "QQQ10: rstrip" ); halt
                        adjText, cleanText, extras = self.processLineFix( C, V, originalMarker, thisText, fixErrors )
                        self._processedLines.append( InternalBibleEntry(adjustedMarker, originalMarker, adjText, cleanText, extras, originalText) )
                        ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
                        adjMarker = BibleOrgSysGlobals.loadedUSFMMarkers.toStandardMarker( insideMarker ) # setup for the next line
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
                            #print( "\n", C, V, "'"+text+"'" )
                            #print( "'"+beforeText+"'", pText, "'"+afterText+"'" )
                            adjText, cleanText, extras = self.processLineFix( C, V, originalMarker, beforeText, fixErrors )
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
                    if BibleOrgSysGlobals.debugFlag: assert ixGT != -1
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
                            self._processedLines.append( InternalBibleEntry('p', originalMarker, '', '', None, originalText) )
                        else: print( "preverse", "'"+preverseText+"'" )
                        text = beforeText + afterText[ixFinal+1:]
                    elif thisField.startswith( '<div sID="' ) and thisField.endswith( '" type="paragraph"/>' ):
                        self._processedLines.append( InternalBibleEntry('p', originalMarker, '', '', None, originalText) )
                        text = beforeText + afterText
                    #elif thisField.startswith( '<div eID="' ) and thisField.endswith( '" type="paragraph"/>' ):
                        #self._processedLines.append( InternalBibleEntry('m', originalMarker, '', '', None) )
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
                        if BibleOrgSysGlobals.debugFlag:
                            assert thisField[11] == '"'
                            assert levelDigit.isdigit()
                        self._processedLines.append( InternalBibleEntry('q'+levelDigit, originalMarker, '', '', None, originalText) )
                        text = beforeText + afterText
                    elif thisField.startswith( '<lg sID="' ) and thisField.endswith( '"/>' ):
                        self._processedLines.append( InternalBibleEntry('qx', originalMarker, '', '', None, originalText) )
                        text = beforeText + afterText
                    elif thisField.startswith( '<chapter osisID="' ) and thisField.endswith( '"/>' ):
                        if 0: # Don't actually need this stuff
                            ixDQ = thisField.index( '"', 17 )
                            #assert ixDQ != -1
                            osisID = thisField[17:ixDQ]
                            #print( "osisID", "'"+osisID+"'" )
                            ixDOT = osisID.index( '.' )
                            #assert ixDOT != -1
                            chapterDigits = osisID[ixDOT+1:]
                            #print( "chapter", chapterDigits )
                            self._processedLines.append( InternalBibleEntry('c~', originalMarker, chapterDigits, chapterDigits, None, originalText) )
                        text = beforeText + afterText
                    elif ( thisField.startswith( '<chapter eID="' ) or thisField.startswith( '<l eID="' ) or thisField.startswith( '<lg eID="' ) or thisField.startswith( '<div eID="' ) ) \
                    and thisField.endswith( '"/>' ):
                        text = beforeText + afterText # We just ignore it
                    ixLT = text.find( '<', ixLT+1 )

            #print( "__doAppendEntry", adjustedMarker, originalMarker, repr(text), repr(originalText) )
            #print( " ", verseNumberRest if originalMarker=='v' and adjustedMarker=='v~' else originalText )
            # Set flag to True if there's exactly one space between the verse number and the rest
            #goodStart =  len(originalText)>1 and originalText[0]==' ' and originalText[1]!=' '
            #print( 'Gs', goodStart, repr(verseNumberRest[1:] if goodStart else originalText) )
            #__doAppendEntry( adjustedMarker, originalMarker, text, verseNumberRest if originalMarker=='v' and adjustedMarker=='v~' else originalText )
            __doAppendEntry( adjustedMarker, originalMarker, text, text if originalMarker=='v' and adjustedMarker=='v~' else originalText )
        # end of InternalBibleBook.processLines.processLine


        # This is the main processLines code
        if self.objectTypeString == 'OSIS': self.reorderRawOsisLines()
        fixErrors = []
        self._processedLines = InternalBibleEntryList() # Contains more-processed tuples which contain the actual Bible text -- see below
        C, V = '-1', '-1' # So first/id line starts at -1:0
        haveWaitingC = False
        for marker,text in self._rawLines:
            #print( "\nQQQ" )
            if self.objectTypeString=='USX' and text and text[-1]==' ': text = text[:-1] # Removing extra trailing space from BibleOrgSys.Formats.USX files
            processLine( marker, text ) # Saves its results in self._processedLines
        del self.pntsCount, self.nfvnCount, self.owfvnCount, self.rtsCount, self.sahtCount, self.fwmifCount, self.fswncCount

        # Both of the next two function calls affect self._processedLines
        # Go through the lines and add nesting markers like 'intro', 'chapter', etc.
        self.addNestingMarkers()
        # Go through and add v= markers (for "logical" verses before section headings, etc.)
        self.addVerseStartMarkers()

        # Get rid of data that we don't need
        #if not BibleOrgSysGlobals.debugFlag:
        del self._rawLines # if short of memory
        try: del self.XMLTree # for xml Bible types (some Bible books caused a segfault when pickled with this data)
        except AttributeError: pass # we didn't have an xml tree to delete

        if fixErrors: self.errorDictionary['Fix Text Errors'] = fixErrors
        self._processedFlag = True
        self.makeCVIndex()
        #self.makeSectionIndex() # Not created by default
    # end of InternalBibleBook.processLines


    def makeCVIndex( self ) -> None:
        """
        Index the InternalBibleBook processed lines InternalBibleEntryList for faster reference.

        Works by calling makeCVIndex in InternalBibleIndexes.py
            to update self._CVIndex
        """
        if BibleOrgSysGlobals.debugFlag:
            assert self._processedFlag
            assert not self._indexedCVFlag
        if self._indexedCVFlag: return # Can only do it once

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Indexing {} {!r} {} text…").format( self.objectNameString, self.workName, self.BBB ) )
        self._CVIndex = InternalBibleCVIndex( self.workName, self.BBB )
        self._CVIndex.makeCVIndex( self._processedLines )

        #if self.BBB=='GEN':
            #for j, entry in enumerate( self._processedLines):
                #cleanText = entry.getCleanText()
                #print( j, entry.getMarker(), cleanText[:60] + ('' if len(cleanText)<60 else '…') )
                ##if j>breakAt: break
            #def getKey( CVALX ):
                #CV, ALX = CVALX
                #C, V = CV
                #try: Ci = int(C)
                #except: Ci = 300
                #try: Vi = int(V)
                #except: Vi = 300
                #return Ci*1000 + Vi
            #for CV,ALX in sorted(self._CVIndex.items(), key=getKey): #lambda s: int(s[0][0])*1000+int(s[0][1])): # Sort by C*1000+V
                #C, V = CV
                ##A, L, X = ALX
                #print( "{}:{}={},{},{}".format( C, V, ALX.getEntryIndex(), ALX.getEntryCount(), ALX.getContext() ), end='  ' )
            #halt

        self._indexedCVFlag = True
    # end of InternalBibleBook.makeCVIndex


    def _makeSectionIndex( self ) -> None:
        """
        Index the InternalBibleBook processed lines InternalBibleEntryList for faster reference.

        Works by calling makeSectionIndex in InternalBibleIndexes.py
            to update self._SectionIndex
        """
        if BibleOrgSysGlobals.debugFlag:
            assert self._processedFlag
            assert not self._indexedSectionsFlag
        if self._indexedSectionsFlag: return # Can only do it once

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Indexing {} {!r} {} text…").format( self.objectNameString, self.workName, self.BBB ) )
        self._SectionIndex = InternalBibleSectionIndex( self, self.containerBibleObject )
        self._SectionIndex.makeSectionIndex()

        self._indexedSectionsFlag = True
    # end of InternalBibleBook._makeSectionIndex


    def debugPrint( self ):
        """
        """
        print( "InternalBibleBook.debugPrint: {}".format( self.BBB ) )
        numLines = 50
        if '_rawLines' in self.__dict__:
            for j in range( min( numLines, len(self._rawLines) ) ):
                print( " Raw {}: {} = {!r}".format( j, self._rawLines[j][0], self._rawLines[j][1] ) )
        for j in range( min( numLines, len(self._processedLines) ) ):
            print( " Proc {}: {}{} = {!r}".format( j, self._processedLines[j][0], '({})'.format(self._processedLines[j][1]) if self._processedLines[j][1]!=self._processedLines[j][0] else '', self._processedLines[j][2] ) )
    # end of InternalBibleBook.debugPrint


    def validateMarkers( self ):
        """
        Validate the loaded book.
        This is usually called from loadBook() in the various Bible importers.

        This does a quick check for major SFM errors. It is not as thorough as checkSFMs below.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'validateMarkers'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            assert self._processedLines
        validationErrors = []

        C, V = '-1', '-1' # So first/id line starts at -1:0
        for j, entry in enumerate(self._processedLines):
            marker, text = entry.getMarker(), entry.getText()
            #print( "{} {}:{} {!r} {!r}".format( self.BBB, C, V, marker, text ) )

            # Keep track of where we are for more helpful error messages
            if marker == 'c':
                if text: C = text.split()[0]
                else:
                    validationErrors.append( '{} {}:{} '.format( self.BBB, C, V ) + _("Missing chapter number").format( self.BBB, C, V ) )
                    logging.error( _("Missing chapter number after") + " {} {}:{}".format( self.BBB, C, V ) )
                    if C == '-1': C = '1' # Makes it more robust since we had a chapter marker at least
                V = '0'
            elif marker == 'v':
                if text: V = text.split()[0]
                else:
                    validationErrors.append( '{} {}:{} '.format( self.BBB, C, V ) + _("Missing verse number").format( self.BBB, C, V ) )
                    logging.error( _("Missing verse number after") + " {} {}:{}".format( self.BBB, C, V ) )
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            # Temporarily substitute some markers just to make this check go easier
            if marker == 'c~': marker = 'v'
            if marker == 'v~': marker = 'v'
            if marker == 'p~': marker = 'v'

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            # Do a rough check of the SFMs
            if marker=='id' and j!=0:
                validationErrors.append( lineLocationSpace + _("Marker 'id' should only appear as the first marker in a book but found on line {} in {}: {}").format( j+1, marker, text ) )
                logging.error( _("Marker 'id' should only appear as the first marker in a book but found on line {} after {} {}:{} in {}: {}").format( j+1, self.BBB, C, V, marker, text ) )
                self.addPriorityError( 99, C, V, _("'id' marker should only be in first line of file") )
            #if ( marker[0]=='¬' and marker not in BOS_END_MARKERS and not BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker[1:] ) ) \
            if ( marker[0]=='¬' and marker not in BOS_END_MARKERS ) \
            or ( marker[0]!='¬' and marker not in ('c#','vp#',) and marker not in BOS_ADDED_NESTING_MARKERS and not BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ) ):
                validationErrors.append( lineLocationSpace + _("Unexpected {!r} newline marker in Bible book (Text is {!r})").format( marker, text ) )
                logging.warning( _("Unexpected {!r} newline marker in Bible book after {} {}:{} (Text is {!r})").format( marker, self.BBB, C, V, text ) )
                self.addPriorityError( 80, C, V, _("Marker {!r} not expected at beginning of line").format( marker ) )
            if BibleOrgSysGlobals.loadedUSFMMarkers.isDeprecatedMarker( marker ):
                validationErrors.append( lineLocationSpace + _("Deprecated {!r} newline marker in Bible book (Text is {!r})").format( marker, text ) )
                logging.warning( _("Deprecated {!r} newline marker in Bible book after {} {}:{} (Text is {!r})").format( marker, self.BBB, C, V, text ) )
                self.addPriorityError( 90, C, V, _("Newline marker {!r} is deprecated in USFM standard").format( marker ) )
            markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( text )
            #if markerList: print( "\nText = {}:{!r}".format(marker,text)); print( markerList )
            for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check character markers
                if BibleOrgSysGlobals.loadedUSFMMarkers.isDeprecatedMarker( insideMarker ):
                    validationErrors.append( lineLocationSpace + _("Deprecated {!r} internal marker in Bible book (Text is {!r})").format( insideMarker, text ) )
                    logging.warning( _("Deprecated {!r} internal marker in Bible book after {} {}:{} (Text is {!r})").format( insideMarker, self.BBB, C, V, text ) )
                    self.addPriorityError( 89, C, V, _("Internal marker {!r} is deprecated in USFM standard").format( insideMarker ) )
            ix = 0
            for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check newline markers
                if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(insideMarker):
                    validationErrors.append( lineLocationSpace + _("Marker {!r} must not appear within line in {}: {}").format( insideMarker, marker, text ) )
                    logging.error( _("Marker {!r} must not appear within line after {} {}:{} in {}: {}").format( insideMarker, self.BBB, C, V, marker, text ) )
                    self.addPriorityError( 90, C, V, _("Newline marker {!r} should be at start of line").format( insideMarker ) )

        if validationErrors: self.errorDictionary['Validation Errors'] = validationErrors
    # end of InternalBibleBook.validateMarkers


    def getField( self, fieldName ):
        """
        Extract a SFM field from the loaded book.
        """
        if not self._processedFlag:
            if debuggingThisModule: print( "InternalBibleBook {}: calling processLines from 'getField'".format( self.BBB ) )
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            assert self._processedLines
        if BibleOrgSysGlobals.debugFlag:
            assert fieldName and isinstance( fieldName, str )
        adjFieldName = fieldName if fieldName in ('cl¤',) else BibleOrgSysGlobals.loadedUSFMMarkers.toStandardMarker( fieldName )

        for entry in self._processedLines:
            if entry.getMarker() == adjFieldName:
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert not entry.getExtras() # We're maybe losing some info here
                return entry.getText()
    # end of InternalBibleBook.getField


    def getAssumedBookNames( self ):
        """
        Attempts to deduce a bookname and book abbreviations from the loaded book.
        Use the English name as a last resort.

        Sets:   self.longTOCName
                self.shortTOCName
                self.booknameAbbreviation
                self.chapterLabel

        Returns a list with the best guess for the bookname first.
        The assumedBookName defaults to the long book name from \toc1 field.
        """
        #print( "InternalBibleBook.getAssumedBookNames()" )
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'getAssumedBookNames'".format( self.BBB, self.workName ) ) # This is usually the first call from the Bible Drop Box
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            assert self._processedLines
        results = []

        toc1Field = self.getField( 'toc1' ) # Long table of contents text
        if toc1Field:
            #print( "Got toc1 of", repr(toc1Field) )
            #if toc1Field.isupper(): field = toc1Field.title()
            results.append( toc1Field )
            self.longTOCName = toc1Field
        elif self.containerBibleObject is not None and self.BBB+'LongName' in self.containerBibleObject.settingsDict:
            self.longTOCName = self.containerBibleObject.settingsDict[self.BBB+'LongName']
            results.append( self.longTOCName )

        header = self.getField( 'h' )
        if header:
            if header.isupper(): header = header.title()
            results.append( header )

        if (not header or len(header)<4 or not header[0].isdigit() or header[1]!=' ') and self.getField('mt2') is not None:
        # Ignore the main title if it's a book like "Corinthians" and there's a mt2 (like "First")
            mt1 = self.getField( 'mt1' )
            if mt1:
                if mt1.isupper(): mt1 = mt1.title()
                #print( "Got mt1 of", repr(mt1) )
                if mt1 not in results: results.append( mt1 )

        toc2Field = self.getField( 'toc2' ) # Short table of contents text
        if toc2Field:
            #print( "Got toc2 of", repr(toc2Field) )
            #if toc2Field.isupper(): field = toc2Field.title()
            results.append( toc2Field )
            self.shortTOCName = toc2Field
        elif self.containerBibleObject is not None and self.BBB+'ShortName' in self.containerBibleObject.settingsDict:
            self.shortTOCName = self.containerBibleObject.settingsDict[self.BBB+'ShortName']
            results.append( self.shortTOCName )

        toc3Field = self.getField( 'toc3' ) # Bookname abbreviation
        if toc3Field:
            #print( "Got toc3 of", repr(toc3Field) )
            #if toc3Field.isupper(): toc3Field = toc3Field.title()
            results.append( toc3Field )
            self.booknameAbbreviation = toc3Field
        elif self.containerBibleObject is not None and self.BBB+'Abbreviation' in self.containerBibleObject.settingsDict:
            self.booknameAbbreviation = self.containerBibleObject.settingsDict[self.BBB+'Abbreviation']
            results.append( self.booknameAbbreviation )

        clField = self.getField( 'cl¤' ) # Chapter label for whole book (cl before ch.1 -> cl¤ in processLine)
        if clField:
            #print( "Got cl of", repr(clField) )
            self.chapterLabel = clField

        if not results: # no helpful fields in file -- just use an English name
            results.append( BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR( self.BBB ) )
        self.assumedBookName = results[0]
        #print( "Got assumedBookName of", repr(self.assumedBookName) )

        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 3: # Print our level of confidence
        #    if header is not None and header==mt1: assert bookName == header; print( "getBookName: header and main title are both {!r}".format( bookName ) )
        #    elif header is not None and mt1 is not None: print( "getBookName: header {!r} and main title {!r} are both different so selected {!r}".format( header, mt1, bookName ) )
        #    elif header is not None or mt1 is not None: print( "getBookName: only have one of header {!r} or main title {!r}".format( header, mt1 ) )
        #    else: print( "getBookName: no header or main title so used English book name {!r}".format( bookName ) )
        if (BibleOrgSysGlobals.debugFlag and debuggingThisModule) or BibleOrgSysGlobals.verbosityLevel > 3: # Print our level of confidence
            print( "Assumed bookname(s) of {} for {}".format( results, self.BBB ) )

        return results
    # end of InternalBibleBook.getAssumedBookNames


    def getVersification( self ):
        """
        Get the versification of the book into four lists of (C, V) tuples.
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
            The third list contains an entry for all combined verses in the book.
            The fourth list contains an entry for all reordered verse in the book.
        Note that all chapter and verse values are returned as strings not integers.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'getVersification'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines
        versificationErrors = []

        versification, omittedVerses, combinedVerses, reorderedVerses = [], [], [], []
        chapterText, chapterNumber, lastChapterNumber = '0', 0, 0
        verseText = verseNumberString = lastVerseNumberString = '0'
        for j, entry in enumerate( self._processedLines ):
            marker, text = entry.getMarker(), entry.getText()
            #print( marker, text )
            if marker == 'c':
                if chapterNumber == 0: # it's the book introduction
                    versification.append( (chapterText, str(j-1),) ) # Count each line as a 'verse'
                else: # it's a regular chapter
                    versification.append( (chapterText, lastVerseNumberString,) )
                chapterText = text.strip()
                if ' ' in chapterText: # Seems that we can have footnotes here :)
                    versificationErrors.append( "{} {}:{} ".format( self.BBB, chapterText, verseNumberString ) + _("Unexpected space in USFM chapter number field {!r}").format( self.BBB, lastChapterNumber, lastVerseNumberString, chapterText, lastChapterNumber ) )
                    logging.info( _("Unexpected space in USFM chapter number field {!r} after chapter {} of {}").format( chapterText, lastChapterNumber, self.BBB ) )
                    chapterText = chapterText.split( None, 1)[0]
                #print( "{} chapter {}".format( self.BBB, chapterText ) )
                chapterNumber = int( chapterText)
                if chapterNumber != lastChapterNumber+1:
                    versificationErrors.append( _("{} ({} after {}) USFM chapter numbers out of sequence in Bible book").format( self.BBB, chapterNumber, lastChapterNumber ) )
                    logging.error( _("USFM chapter numbers out of sequence in Bible book {} ({} after {})").format( self.BBB, chapterNumber, lastChapterNumber ) )
                lastChapterNumber = chapterNumber
                verseText = verseNumberString = lastVerseNumberString = '0'
            elif marker == 'cp':
                versificationErrors.append( "{} {}:{} ".format( self.BBB, chapterText, verseNumberString ) + _("Encountered cp field {}").format( self.BBB, chapterNumber, lastVerseNumberString, text ) )
                logging.warning( _("Encountered cp field {} after {}:{} of {}").format( text, chapterNumber, lastVerseNumberString, self.BBB ) )
            elif marker == 'v':
                if chapterText == '0':
                    versificationErrors.append( _("{} {} Missing chapter number field before verse {}").format( self.BBB, chapterText, text ) )
                    logging.warning( _("Missing chapter number field before verse {} in chapter {} of {}").format( text, chapterText, self.BBB ) )
                if not text:
                    versificationErrors.append( _("{} {} Missing USFM verse number after v{}").format( self.BBB, chapterNumber, lastVerseNumberString ) )
                    logging.warning( _("Missing USFM verse number after v{} in chapter {} of {}").format( lastVerseNumberString, chapterNumber, self.BBB ) )
                    continue
                verseText = text
                doneWarning = False
                for char in 'abcdefghijklmnopqrstuvwxyz[]()\\':
                    if char in verseText:
                        if not doneWarning:
                            versificationErrors.append( _("{} {} Removing letter(s) from USFM verse number {} in Bible book").format( self.BBB, chapterText, verseText ) )
                            logging.info( _("Removing letter(s) from USFM verse number {} in Bible book {} {}").format( verseText, self.BBB, chapterText ) )
                            doneWarning = True
                        verseText = verseText.replace( char, '' )
                if '-' in verseText or '–' in verseText: # we have a range like 7-9 with hyphen or en-dash
                    #versificationErrors.append( "{} {}:{} ".format( self.BBB, chapterText, verseNumberString ) + _("Encountered combined verses field {}").format( self.BBB, chapterNumber, lastVerseNumberString, verseText ) )
                    logging.info( _("Encountered combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.BBB ) )
                    bits = verseText.replace('–','-').split( '-', 1 ) # Make sure that it's a hyphen then split once
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except ValueError:
                        versificationErrors.append( _("{} {} Invalid USFM verse range start {!r} in {!r} in Bible book").format( self.BBB, chapterText, verseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse range start {!r} in {!r} in Bible book {} {}").format( verseNumberString, verseText, self.BBB, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except ValueError:
                        versificationErrors.append( _("{} {} Invalid USFM verse range end {!r} in {!r} in Bible book").format( self.BBB, chapterText, endVerseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse range end {!r} in {!r} in Bible book {} {}").format( endVerseNumberString, verseText, self.BBB, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse range out of sequence in Bible book").format( self.BBB, chapterText, verseNumberString, endVerseNumberString ) )
                        logging.error( _("USFM verse range out of sequence in Bible book {} {} ({}-{})").format( self.BBB, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                elif ',' in verseText: # we have a range like 7,8
                    versificationErrors.append( "{} {}:{} ".format( self.BBB, chapterText, verseNumberString ) + _("Encountered comma combined verses field {}").format( self.BBB, chapterNumber, lastVerseNumberString, verseText ) )
                    logging.info( _("Encountered comma combined verses field {} after {}:{} of {}").format( verseText, chapterNumber, lastVerseNumberString, self.BBB ) )
                    bits = verseText.split( ',', 1 )
                    verseNumberString, verseNumber = bits[0], 0
                    endVerseNumberString, endVerseNumber = bits[1], 0
                    try:
                        verseNumber = int( verseNumberString )
                    except ValueError:
                        versificationErrors.append( _("{} {} Invalid USFM verse list start {!r} in {!r} in Bible book").format( self.BBB, chapterText, verseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse list start {!r} in {!r} in Bible book {} {}").format( verseNumberString, verseText, self.BBB, chapterText ) )
                    try:
                        endVerseNumber = int( endVerseNumberString )
                    except ValueError:
                        versificationErrors.append( _("{} {} Invalid USFM verse list end {!r} in {!r} in Bible book").format( self.BBB, chapterText, endVerseNumberString, verseText ) )
                        logging.error( _("Invalid USFM verse list end {!r} in {!r} in Bible book {} {}").format( endVerseNumberString, verseText, self.BBB, chapterText ) )
                    if verseNumber >= endVerseNumber:
                        versificationErrors.append( _("{} {} ({}-{}) USFM verse list out of sequence in Bible book").format( self.BBB, chapterText, verseNumberString, endVerseNumberString ) )
                        logging.error( _("USFM verse list out of sequence in Bible book {} {} ({}-{})").format( self.BBB, chapterText, verseNumberString, endVerseNumberString ) )
                    #else:
                    combinedVerses.append( (chapterText, verseText,) )
                else: # Should be just a single verse number
                    verseNumberString = verseText
                    endVerseNumberString = verseNumberString
                try:
                    verseNumber = int( verseNumberString )
                except ValueError:
                    versificationErrors.append( _("{} {} {} Invalid verse number digits in Bible book").format( self.BBB, chapterText, verseNumberString ) )
                    logging.error( _("Invalid verse number digits in Bible book {} {} {}").format( self.BBB, chapterText, verseNumberString ) )
                    newString = ''
                    for char in verseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    verseNumber = int(newString) if newString else 999
                try:
                    lastVerseNumber = int( lastVerseNumberString )
                except ValueError:
                    newString = ''
                    for char in lastVerseNumberString:
                        if char.isdigit(): newString += char
                        else: break
                    lastVerseNumber = int(newString) if newString else 999
                if verseNumber != lastVerseNumber+1:
                    if verseNumber <= lastVerseNumber:
                        versificationErrors.append( _("{} {} ({} after v{}) USFM verse numbers out of sequence in Bible book").format( self.BBB, chapterText, verseText, lastVerseNumberString ) )
                        logging.warning( _("USFM verse numbers out of sequence in Bible book {} {} ({} after v{})").format( self.BBB, chapterText, verseText, lastVerseNumberString ) )
                        reorderedVerses.append( (chapterText, lastVerseNumberString, verseText,) )
                    else: # Must be missing some verse numbers
                        versificationErrors.append( _("{} {} Missing USFM verse number(s) between {} and {} in Bible book").format( self.BBB, chapterText, lastVerseNumberString, verseNumberString ) )
                        logging.info( _("Missing USFM verse number(s) between {} and {} in Bible book {} {}").format( lastVerseNumberString, verseNumberString, self.BBB, chapterText ) )
                        for number in range( lastVerseNumber+1, verseNumber ):
                            omittedVerses.append( (chapterText, str(number),) )
                lastVerseNumberString = endVerseNumberString
        versification.append( (chapterText, lastVerseNumberString,) ) # Append the verse count for the final chapter
        #if reorderedVerses: print( "Reordered verses in", self.BBB, "are:", reorderedVerses )
        if versificationErrors: self.errorDictionary['Versification Errors'] = versificationErrors
        return versification, omittedVerses, combinedVerses, reorderedVerses
    # end of InternalBibleBook.getVersification


    def getVersificationIfNecessary( self ):
        """
        Obtain the versification for this book if we haven't done it already.

        Stores it in self.versification and self.missingVersesList
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "getVersificationIfNecessary()" )
        if self.versificationList is None:
            assert self.omittedVersesList is None and self.combinedVersesList is None and self.reorderedVersesList is None # also
            versificationResult = self.getVersification()
            #print( self.BBB, versificationResult )
            if versificationResult is None: logging.critical( "getVersificationIfNecessary() got nothing!" )
            else:
                self.versificationList, self.omittedVersesList, self.combinedVersesList, self.reorderedVersesList = versificationResult
    # end of InternalBibleBook.getVersificationIfNecessary


    def _discover( self ):
        """
        Do a precheck on the book to try to determine its features.

        We later use these discoveries to note when the translation veers from their norm.

        Called from InternalBible.py (which first creates the Bible-wide dictionary
            and then consolidates the individual results).

        Returns a dictionary containing the results for the book.
            Note: Because this function can run in multiprocessing,
                    saving class variables won't persist.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'discover'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines
        if debuggingThisModule: print( f"InternalBibleBook._discover() for {self.BBB}…" )

        bkDict = {}
        bkDict['chapterCount'] = bkDict['verseCount'] = bkDict['percentageProgress'] = None
        bkDict['completedVerseCount'] = 0
        bkDict['havePopulatedCVmarkers'] = bkDict['haveParagraphMarkers'] = bkDict['haveIntroductoryMarkers'] = False
        bkDict['haveMainHeadings'] = False; bkDict['mainHeadingsCount'] = 0
        bkDict['haveSectionHeadings'] = False; bkDict['sectionHeadingsCount'] = 0
        bkDict['haveSectionReferences'] = False
        bkDict['haveFootnotes'] = bkDict['haveFootnoteOrigins'] = False
        bkDict['haveCrossReferences'] = bkDict['haveCrossReferenceOrigins'] = False
        bkDict['sectionReferencesCount'] = bkDict['footnotesCount'] = bkDict['crossReferencesCount'] = 0
        bkDict['sectionReferencesParenthesisRatio'] = bkDict['footnotesPeriodRatio'] = bkDict['crossReferencesPeriodRatio'] = -1.0
        bkDict['haveIntroductoryText'] = bkDict['haveVerseText'] = False
        bkDict['haveNestedUSFMarkers'] = False
        bkDict['seemsFinished'] = None

        sectionRefParenthCount = footnotesPeriodCount = xrefsPeriodCount = 0

        # Initialise all our word counters
        bkDict['wordCount'] = 0 #bkDict['uniqueWordCount'] = 0
        bkDict['allWordCounts'], bkDict['allCaseInsensitiveWordCounts'] = {}, {}
        bkDict['mainTextWordCounts'], bkDict['mainTextCaseInsensitiveWordCounts'] = {}, {}


        def countWords( marker, segment, location ):
            """
            Breaks the segment into words and counts them.
            """
            #def stripWordPunctuation( word ):
                #"""Removes leading and trailing punctuation from a word.
                    #Returns the "clean" word."""
                #while word and word[0] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS:
                    #word = word[1:] # Remove leading punctuation
                #while word and word[-1] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                    #word = word[:-1] # Remove trailing punctuation
                #if  '<' in word or '>' in word or '"' in word: print( "InternalBibleBook.discover: Need to escape HTML chars here 3s42", self.BBB, C, V, repr(word) )
                #return word
            ## end of stripWordPunctuation

            # countWords() main code
            words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            for j,rawWord in enumerate(words):
                if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                word = rawWord
                for internalMarker in BibleOrgSysGlobals.internal_SFMs_to_remove: word = word.replace( internalMarker, '' )
                word = BibleOrgSysGlobals.stripWordPunctuation( word )
                if word and not word[0].isalnum():
                    #print( word, BibleOrgSysGlobals.stripWordPunctuation( word ) )
                    if len(word) > 1:
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( "InternalBibleBook.discover: {} {}:{} ".format( self.BBB, C, V ) \
                                                + _("Have unexpected character starting word {!r}").format( word ) )
                        word = word[1:]
                if word: # There's still some characters remaining after all that stripping
                    if BibleOrgSysGlobals.verbosityLevel > 3: # why???
                        for k,char in enumerate(word):
                            if not char.isalnum() and (k==0 or k==len(word)-1 or char not in BibleOrgSysGlobals.MEDIAL_WORD_PUNCT_CHARS):
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                    print( "InternalBibleBook.discover: {} {}:{} ".format( self.BBB, C, V ) + _("Have unexpected {!r} in word {!r}").format( char, word ) )
                    lcWord = word.lower()
                    isAReferenceOrNumber = True
                    for char in word:
                        if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                    if not isAReferenceOrNumber:
                        bkDict['wordCount'] += 1
                        #if word not in bkDict['allWordCounts']:
                            #bkDict['uniqueWordCount'] += 1
                            #bkDict['allWordCounts'][word] = 1
                        #else: bkDict['allWordCounts'][word] += 1
                        bkDict['allWordCounts'][word] = 1 if word not in bkDict['allWordCounts'] else bkDict['allWordCounts'][word] + 1
                        bkDict['allCaseInsensitiveWordCounts'][lcWord] = 1 if lcWord not in bkDict['allCaseInsensitiveWordCounts'] else bkDict['allCaseInsensitiveWordCounts'][lcWord] + 1
                        if location == 'main':
                            bkDict['mainTextWordCounts'][word] = 1 if word not in bkDict['mainTextWordCounts'] else bkDict['mainTextWordCounts'][word] + 1
                            bkDict['mainTextCaseInsensitiveWordCounts'][lcWord] = 1 if lcWord not in bkDict['mainTextCaseInsensitiveWordCounts'] else bkDict['mainTextCaseInsensitiveWordCounts'][lcWord] + 1
                    #else: print( "excluded reference or number", word )
        # end of countWords


        # _discover() main code
        C, V = '-1', '-1' # So first/id line starts at -1:0
        lastMarker = None
        for entry in self._processedLines:
            marker = entry.getMarker()
            if '¬' in marker: continue # Just ignore end markers -- not needed here
            text, cleanText, extras = entry.getText(), entry.getCleanText(), entry.getExtras()
            #print(f"Discover {self.BBB} {C}:{V} {marker}={text}")

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                C, V = text.split()[0], '0'
                if bkDict['chapterCount'] is None: bkDict['chapterCount'] = 1
                else: bkDict['chapterCount'] += 1
            elif marker=='v' and text:
                V = text.split()[0]
                if bkDict['verseCount'] is None: bkDict['verseCount'] = 1
                else: bkDict['verseCount'] += 1
                if bkDict['chapterCount'] is None: # Some single chapter books don't have \c 1 explicitly encoded
                    if BibleOrgSysGlobals.debugFlag: assert C == '-1'
                    C = '1'
                    bkDict['chapterCount'] = 1
                bkDict['havePopulatedCVmarkers'] = True
                if bkDict['seemsFinished'] is None: bkDict['seemsFinished'] = True
            elif marker=='v~' and text:
                bkDict['haveVerseText'] = True
                bkDict['completedVerseCount'] += 1
            elif marker in ('mt1','mt2','mt3','mt4'):
                bkDict['haveMainHeadings'] = True
                bkDict['mainHeadingsCount'] += 1
            elif marker in ('s1','s2','s3','s4', 'qa'):
                bkDict['haveSectionHeadings'] = True
                bkDict['sectionHeadingsCount'] += 1
            elif marker=='r' and text:
                bkDict['haveSectionReferences'] = True
                bkDict['sectionReferencesCount'] += 1
                if cleanText[0]=='(' and cleanText[-1]==')': sectionRefParenthCount += 1
            elif marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                bkDict['haveParagraphMarkers'] = True
                if text: bkDict['haveVerseText'] = True
            elif marker in ('ip',):
                bkDict['haveIntroductoryMarkers'] = True
                if text: bkDict['haveIntroductoryText'] = True

            if text and '\\+' in text: bkDict['haveNestedUSFMarkers'] = True
            if lastMarker=='v' and (marker!='v~' or not text): bkDict['seemsFinished'] = False

            if text and marker in BOS_PRINTABLE_MARKERS: # process this main text
                countWords( marker, cleanText, 'main' )
            #elif text: print( "Ignoring {} {}:{} {}={}".format( self.BBB, C, V, marker, repr(text) ) )

            if extras:
                for extraType, extraIndex, extraText, cleanExtraText in extras:
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert extraIndex >= 0
                        #assert 0 <= extraIndex <= len(text)+3
                        assert extraType in BOS_EXTRA_TYPES
                    if extraType=='fn':
                        bkDict['haveFootnotes'] = True
                        bkDict['footnotesCount'] += 1
                        if '\\fr' in extraText: bkDict['haveFootnoteOrigins'] = True
                        if cleanExtraText and cleanExtraText[-1] in '.።' or cleanExtraText.endswith('.”'):
                            footnotesPeriodCount += 1
                    elif extraType=='xr':
                        bkDict['haveCrossReferences'] = True
                        bkDict['crossReferencesCount'] += 1
                        if '\\xo' in extraText: bkDict['haveCrossReferenceOrigins'] = True
                        if cleanExtraText and cleanExtraText[-1] in '.።' or cleanExtraText.endswith('.”'):
                            xrefsPeriodCount += 1
                    countWords( extraType, cleanExtraText, "notes" )
            lastMarker = marker
        #print( 'wordCount', self.BBB, bkDict['wordCount'] )
        #print( 'uniqueWordCount', self.BBB, bkDict['uniqueWordCount'] )
        bkDict['uniqueWordCount'] = len( bkDict['allWordCounts'] )

        if bkDict['verseCount'] is None: # Things like front and end matter (don't have verse numbers)
            for aKey in ('verseCount','seemsFinished','chapterCount','percentageProgress',):
                #assert bkDict[aKey] is None \
                    #or ( aKey=='chapterCount' and bkDict[aKey]==1 ) # Some people put a chapter count in their front matter, glossary, etc.
                if bkDict[aKey] is not None and ( aKey!='chapterCount' or bkDict[aKey]!=1 ):
                    # Some people put a chapter count in their front matter, glossary, etc.
                    logging.debug( "InternalBibleBook.discover: ToProgrammer -- Some wrong in {} here. Why? {!r} {!r}".format( self.BBB, aKey, bkDict[aKey] ) )
                del bkDict[aKey]
        else: # Do some finalizing to do with verse counts
            if not bkDict['haveVerseText']: bkDict['seemsFinished'] = False
            if bkDict['verseCount'] is not None:
                bkDict['percentageProgress'] = round( bkDict['completedVerseCount'] * 100 / bkDict['verseCount'] )
                if bkDict['percentageProgress'] > 100:
                    logging.info( "Adjusting percentageProgress from {} back to 100%".format( bkDict['percentageProgress'] ) )
                    bkDict['percentageProgress'] = 100

            #print( self.BBB, bkDict )
            if bkDict['seemsFinished']:
                #print( self.BBB )
                #print( bkDict['percentageProgress'] )
                #print( bkDict['havePopulatedCVmarkers'] )
                #print( bkDict['haveVerseText'] )
                assert bkDict['percentageProgress']==100 and bkDict['havePopulatedCVmarkers'] and bkDict['haveVerseText']
            if not bkDict['haveVerseText']: assert bkDict['percentageProgress']==0 and not bkDict['seemsFinished']
            bkDict['notStarted'] = not bkDict['haveVerseText']
            bkDict['partlyDone'] = bkDict['haveVerseText'] and not bkDict['seemsFinished']

        if bkDict['sectionReferencesCount']:
            bkDict['sectionReferencesParenthesisRatio'] = round( sectionRefParenthCount / bkDict['sectionReferencesCount'], 2 )
            bkDict['sectionReferencesParenthesisFlag'] = bkDict['sectionReferencesParenthesisRatio'] > 0.8
        if bkDict['footnotesCount']:
            bkDict['footnotesPeriodRatio'] = round( footnotesPeriodCount / bkDict['footnotesCount'], 2 )
            bkDict['footnotesPeriodFlag'] = bkDict['footnotesPeriodRatio'] > 0.7
        if bkDict['crossReferencesCount']:
            bkDict['crossReferencesPeriodRatio'] = round( xrefsPeriodCount / bkDict['crossReferencesCount'], 2 )
            bkDict['crossReferencesPeriodFlag'] = bkDict['crossReferencesPeriodRatio'] > 0.7
        #print( self.BBB, bkDict['sectionReferencesParenthesisRatio'] )

        return bkDict
    # end of InternalBibleBook._discover


    def getAddedUnits( self ):
        """
        Get the units added to the text of the book including paragraph breaks, section headings, and section references.
        Note that all chapter and verse values are returned as strings not integers.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'getAddedUnits'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines
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
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "In {}, chapter text went from {!r} to {!r} with cp marker".format( self.BBB, chapterNumberStr, cpChapterText ) )
                chapterNumberStr = cpChapterText
                if len(chapterNumberStr)>2 and chapterNumberStr[0]=='(' and chapterNumberStr[-1]==')': chapterNumberStr = chapterNumberStr[1:-1] # Remove parenthesis -- NOT SURE IF WE REALLY WANT TO DO THIS OR NOT ???
                verseNumberStr = '0'
            elif marker == 'v':
                #print( self.BBB, chapterNumberStr, marker, text )
                if not text:
                    addedUnitErrors.append( _("{} {} Missing USFM verse number after v{}").format( self.BBB, chapterNumberStr, verseNumberStr ) )
                    logging.warning( _("Missing USFM verse number after v{} in chapter {} of {}").format( verseNumberStr, chapterNumberStr, self.BBB ) )
                    self.addPriorityError( 86, chapterNumberStr, verseNumberStr, _("Missing verse number") )
                    continue
                verseNumberStr = text
            elif marker == 'p':
                reference = primeReference = (chapterNumberStr,verseNumberStr,)
                while reference in paragraphReferences: # Must be a single verse broken into multiple paragraphs
                    if BibleOrgSysGlobals.debugFlag: assert primeReference in paragraphReferences
                    if reference == primeReference: reference = (chapterNumberStr,verseNumberStr,'a',) # Append a suffix
                    else: # Already have a suffix
                        reference = (chapterNumberStr,verseNumberStr,chr(ord(reference[2])+1),) # Just increment the suffix
                paragraphReferences.append( reference )
            elif len(marker)==2 and marker[0]=='q' and marker[1].isdigit():# q1, q2, etc.
                reference = primeReference = (chapterNumberStr,verseNumberStr,)
                while reference in qReferences: # Must be a single verse broken into multiple segments
                    if BibleOrgSysGlobals.debugFlag: assert primeReference in qReferences
                    if reference == primeReference: reference = (chapterNumberStr,verseNumberStr,'a',) # Append a suffix
                    else: # Already have a suffix
                        reference = (chapterNumberStr,verseNumberStr,chr(ord(reference[2])+1),) # Just increment the suffix
                level = int( marker[1] ) # 1, 2, etc.
                qReferences.append( (reference,level,) )
            elif marker in ('s1','s2','s3','s4', 'd','r', 'qa'):
                # \d is Psalm description, \r is section reference, \qa is Acrostic Heading
                if text and text[-1].isspace(): print( self.BBB, chapterNumberStr, verseNumberStr, marker, "'"+text+"'" )
                reference = (chapterNumberStr,verseNumberStr,)
                # if marker == 'qa': level = 1
                # else: level = int( marker[1] ) # 1, 2, etc.
                #levelReference = (level,reference,)
                adjText = text.strip().replace('\\nd ','').replace('\\nd*','')
                #print( self.BBB, reference, levelReference, marker, text )
                #assert levelReference not in sectionHeadingReferences # Ezra 10:24 can have two s3's in one verse (first one is blank so it uses the actual verse text)
                #sectionHeadingReferences.append( levelReference ) # Just for checking
                sectionHeadings.append( (reference,marker,adjText,) ) # This is the real data
            elif marker == 'r':
                reference = (chapterNumberStr,verseNumberStr,)
                if BibleOrgSysGlobals.debugFlag: assert reference not in sectionReferenceReferences # Shouldn't be any cases of two lots of section references within one verse boundary
                sectionReferenceReferences.append( reference ) # Just for checking
                sectionReferenceText = text
                if sectionReferenceText and sectionReferenceText[0]=='(' and sectionReferenceText[-1]==')':
                    sectionReferenceText = sectionReferenceText[1:-1] # Remove parenthesis
                sectionReferences.append( (reference,sectionReferenceText,) ) # This is the real data

            if text and 'wj' in text:
                reference = (chapterNumberStr,verseNumberStr)
                #print( "InternalBibleBook.getAddedUnits", chapterNumberStr, verseNumberStr, marker, cleanText )
                #print( " ", marker, text )
                wjCount = text.count( 'wj' ) // 2 # Assuming that half of them are \wj* end markers
                wjFirst, wjLast = text.startswith( '\\wj ' ), text.endswith( '\\wj*' )
                wjInfo = (entry.getOriginalMarker(),wjCount,wjFirst,wjLast,)
                wordsOfJesus.append( (reference,wjInfo,) ) # This is the real data

        if addedUnitErrors: self.errorDictionary['Added Unit Errors'] = addedUnitErrors
        if BibleOrgSysGlobals.debugFlag: assert len(paragraphReferences) == len(set(paragraphReferences)) # No duplicates
        return paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus
    # end of InternalBibleBook.getAddedUnits


    def doCheckAddedUnits( self, typicalAddedUnitData, severe=False ):
        """
        Checkthe units added to the text of the book including paragraph breaks, section headings, and section references.
        """
        typicalParagraphs, typicalQParagraphs, typicalSectionHeadings, typicalSectionReferences, typicalWordsOfJesus = typicalAddedUnitData
        paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = self.getAddedUnits() # For this object

        addedUnitNotices = []
        if self.BBB in typicalParagraphs:
            for reference in typicalParagraphs[self.BBB]:
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalParagraphs[self.BBB][reference]
                if BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in paragraphReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Paragraph break is less common after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Paragraph break is less common after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 17, C, V, _("Less common to have a paragraph break after field") )
                        #print( "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, _("Less common to have a paragraph break after field") )
                        #print( "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Paragraph break normally inserted after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Paragraph break normally inserted after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 27, C, V, _("Paragraph break normally inserted after field") )
                        #print( "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, _("Paragraph break often inserted after field") )
                        #print( "Most", self.BBB, reference, typical, present )
            for reference in paragraphReferences: # now check for ones in this book but not typically there
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalParagraphs[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Paragraph break is unusual after v{}").format( self.BBB, C, V ) )
                    logging.info( _("Paragraph break is unusual after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                    self.addPriorityError( 37, C, V, _("Unusual to have a paragraph break after field") )
                    #print( "Weird paragraph after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no paragraph info available").format( self.BBB ) )
            logging.info( _("{} No paragraph info available").format( self.BBB ) )
            self.addPriorityError( 3, '-', '-', _("No paragraph info for {!r} book").format( self.BBB ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Paragraphing Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalQParagraphs:
            for entry in typicalQParagraphs[self.BBB]:
                reference, level = entry
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalQParagraphs[self.BBB][entry]
                #print( reference, C, V, level, typical )
                if BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in qReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Quote Paragraph is less common after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Quote Paragraph is less common after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 17, C, V, _("Less common to have a Quote Paragraph after field") )
                        #print( "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, _("Less common to have a Quote Paragraph after field") )
                        #print( "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Quote Paragraph normally inserted after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Quote Paragraph normally inserted after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 27, C, V, _("Quote Paragraph normally inserted after field") )
                        #print( "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, _("Quote Paragraph often inserted after field") )
                        #print( "Most", self.BBB, reference, typical, present )
            for reference in qReferences: # now check for ones in this book but not typically there
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalQParagraphs[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Quote Paragraph is unusual after v{}").format( self.BBB, C, V ) )
                    logging.info( _("Quote Paragraph is unusual after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                    self.addPriorityError( 37, C, V, _("Unusual to have a Quote Paragraph after field") )
                    #print( "Weird qParagraph after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no quote paragraph info available").format( self.BBB ) )
            logging.info( _("{} No quote paragraph info available").format( self.BBB ) )
            self.addPriorityError( 3, '-', '-', _("No quote paragraph info for {!r} book").format( self.BBB ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Indenting Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalSectionHeadings:
            for entry in typicalSectionHeadings[self.BBB]:
                reference, level = entry
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalSectionHeadings[self.BBB][entry]
                #print( reference, C, V, level, typical )
                if BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in sectionHeadings:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Section Heading is less common after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Section Heading is less common after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 17, C, V, _("Less common to have a Section Heading after field") )
                        #print( "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, _("Less common to have a Section Heading after field") )
                        #print( "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Section Heading normally inserted after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Section Heading normally inserted after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 27, C, V, _("Section Heading normally inserted after field") )
                        #print( "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, _("Section Heading often inserted after field") )
                        #print( "Most", self.BBB, reference, typical, present )
            for entry in sectionHeadings: # now check for ones in this book but not typically there
                reference, level, text = entry
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if (reference,level) not in typicalSectionHeadings[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Section Heading is unusual after v{}").format( self.BBB, C, V ) )
                    logging.info( _("Section Heading is unusual after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                    self.addPriorityError( 37, C, V, _("Unusual to have a Section Heading after field") )
                    #print( "Weird section heading after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no section heading info available").format( self.BBB ) )
            logging.info( _("{} No section heading info available").format( self.BBB ) )
            self.addPriorityError( 3, '-', '-', _("No section heading info for {!r} book").format( self.BBB ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Section Heading Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalSectionReferences:
            for reference in typicalSectionReferences[self.BBB]:
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalSectionReferences[self.BBB][reference]
                #print( reference, C, V, typical )
                if BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in sectionReferences:
                    if typical == 'F':
                        addedUnitNotices.append( _("{} {} Section Reference is less common after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Section Reference is less common after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 17, C, V, _("Less common to have a Section Reference after field") )
                        #print( "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, _("Less common to have a Section Reference after field") )
                        #print( "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( _("{} {} Section Reference normally inserted after v{}").format( self.BBB, C, V ) )
                        logging.info( _("Section Reference normally inserted after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                        self.addPriorityError( 27, C, V, _("Section Reference normally inserted after field") )
                        #print( "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, _("Section Reference often inserted after field") )
                        #print( "Most", self.BBB, reference, typical, present )
            for entry in sectionReferences: # now check for ones in this book but not typically there
                reference, text = entry
                if BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalSectionReferences[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( _("{} {} Section Reference is unusual after v{}").format( self.BBB, C, V ) )
                    logging.info( _("Section Reference is unusual after v{} in chapter {} of {}").format( V, C,self.BBB ) )
                    self.addPriorityError( 37, C, V, _("Unusual to have a Section Reference after field") )
                    #print( "Weird Section Reference after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( _("{} has no section reference info available").format( self.BBB ) )
            logging.info( _("{} No section reference info available").format( self.BBB ) )
            self.addPriorityError( 3, '-', '-', _("No section reference info for {!r} book").format( self.BBB ) )
        if addedUnitNotices:
            if 'Added Formatting' not in self.errorDictionary: self.errorDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.errorDictionary['Added Formatting']['Possible Section Reference Errors'] = addedUnitNotices
    # end of InternalBibleBook.doCheckAddedUnits


    def doCheckSFMs( self, discoveryDict ):
        """
        Runs a number of comprehensive checks on the USFM codes in this Bible book.
        """
        allAvailableNewlineMarkers = BibleOrgSysGlobals.loadedUSFMMarkers.getNewlineMarkersList( 'Numbered' )
        allAvailableCharacterMarkers = BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList( includeEndMarkers=True )

        logger = None
        MEDIUM_EMPTY_FIELD_PRIORITY, HIGH_EMPTY_FIELD_PRIORITY = 87, 97
        emptyFieldPriority = 17 # e.g., if book is not started
        if discoveryDict:
            if 'partlyDone' in discoveryDict and discoveryDict['partlyDone']: emptyFieldPriority = 47
            if 'percentageProgress' in discoveryDict and discoveryDict['percentageProgress']>95:
                emptyFieldPriority = MEDIUM_EMPTY_FIELD_PRIORITY
                logger = logging.warning
            if 'seemsFinished' in discoveryDict and discoveryDict['seemsFinished']:
                emptyFieldPriority = HIGH_EMPTY_FIELD_PRIORITY
                logger = logging.error

        newlineMarkerCounts, internalMarkerCounts, noteMarkerCounts = {}, {}, {}
        #newlineMarkerCounts['Total'], internalMarkerCounts['Total'], noteMarkerCounts['Total'] = 0, 0, 0 # Put these first in the ordered dict
        newlineMarkerErrors, internalMarkerErrors, noteMarkerErrors = [], [], []
        functionalCounts = {}
        modifiedMarkerList = []
        C, V = '-1', '-1' # So first/id line starts at -1:0
        section, lastMarker, lastModifiedMarker = '', '', None
        lastMarkerEmpty = True
        for entry in self._processedLines:
            marker, originalMarker, text, extras = entry.getMarker(), entry.getOriginalMarker(), entry.getText(), entry.getExtras()
            markerEmpty = not text
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                C, V = text.split()[0], '0'
                functionalCounts['Chapters'] = 1 if 'Chapters' not in functionalCounts else (functionalCounts['Chapters'] + 1)
            elif marker=='v' and text:
                V = text.split()[0]
                functionalCounts['Verses'] = 1 if 'Verses' not in functionalCounts else (functionalCounts['Verses'] + 1)
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            # Do other useful functional counts
            if marker=='id':
                functionalCounts['Book ID'] = 1 if 'Book ID' not in functionalCounts else (functionalCounts['Book ID'] + 1)
            elif marker=='h':
                functionalCounts['Book Header'] = 1 if 'Book Header' not in functionalCounts else (functionalCounts['Book Header'] + 1)
            elif marker=='p':
                functionalCounts['Paragraphs'] = 1 if 'Paragraphs' not in functionalCounts else (functionalCounts['Paragraphs'] + 1)
            elif marker=='r':
                functionalCounts['Section Cross-References'] = 1 if 'Section Cross-References' not in functionalCounts else (functionalCounts['Section Cross-References'] + 1)

            # Check for markers that shouldn't be empty
            if markerEmpty and not extras and ( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType(marker)=='A' or marker in ('v~','c~','c#',) ): # should always have text
                #if self.objectTypeString in ('USFM','USX',):
                    #if self.sahtCount != -1:
                        #self.sahtCount += 1
                        #if self.sahtCount <= self.maxNoncriticalErrorsPerBook:
                            #logging.warning( _("doCheckSFMs: Marker {!r} at {} {}:{} should always have text").format( originalMarker, self.BBB, C, V ) )
                        #else: # we've reached our limit
                            #logging.warning( _('doCheckSFMs: Additional "Marker should always have text" messages suppressed for {} {}').format( self.workName, self.BBB ) )
                            #self.sahtCount = -1 # So we don't do this again (for this book)
                self.addPriorityError( emptyFieldPriority, C, V, _("Marker \\{} should always have text").format( originalMarker ) )
                if emptyFieldPriority >= HIGH_EMPTY_FIELD_PRIORITY:
                    newlineMarkerErrors.append( lineLocationSpace + _("Marker {!r} has no content").format( marker ) )
                else:
                    newlineMarkerErrors.append( lineLocationSpace + _("Marker {!r} should always have text").format( originalMarker ) )
                if logger is not None:
                    logger( _("Marker {!r} has no content after").format( marker ) + " {} {}:{}".format( self.BBB, C, V ) )

            if marker[0] == '¬' or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                continue # Just ignore these added markers
            elif marker == 'v~':
                lastMarker, lastMarkerEmpty = 'v', markerEmpty
                continue
            elif marker == 'p~':
                lastMarker, lastMarkerEmpty = 'p', markerEmpty # not sure if this is correct here ?????
                continue
            elif marker == 'c~':
                lastMarker, lastMarkerEmpty = 'c', markerEmpty
                continue
            elif marker == 'cl¤':
                lastMarker, lastMarkerEmpty = 'c', markerEmpty
                continue
            elif marker == 'c#':
                lastMarker, lastMarkerEmpty = 'c', markerEmpty
                continue
            elif marker == 'vp#':
                lastMarker, lastMarkerEmpty = 'v', markerEmpty
                continue
            else: # it's not our (non-USFM) c~,c#,v~ markers
                if marker not in allAvailableNewlineMarkers: print( "Unexpected marker is {!r}".format( marker ) )
                if BibleOrgSysGlobals.debugFlag: assert marker in allAvailableNewlineMarkers or marker in BOS_ALL_ADDED_MARKERS # Should have been checked at load time
                newlineMarkerCounts[marker] = 1 if marker not in newlineMarkerCounts else (newlineMarkerCounts[marker] + 1)

            # Check the progression through the various sections
            try: newSection = BibleOrgSysGlobals.loadedUSFMMarkers.markerOccursIn( marker if marker!='v~' else 'v' )
            except KeyError: logging.error( "IBB:doCheckSFMs: markerOccursIn failed for {!r}".format( marker ) )
            if newSection != section: # Check changes into new sections
                #print( "{} {}:{} {} takes us from {} to {}".format( self.BBB, C, V, marker, section, newSection ) )

                if section=='' and newSection!='Header':
                    if discoveryDict and 'haveMainHeadings' in discoveryDict and discoveryDict['haveMainHeadings']:
                        newlineMarkerErrors.append( lineLocationSpace + _("Missing Header section (went straight to {} section with {} marker)").format( newSection, marker ) )
                elif section!='' and newSection=='Header':
                    newlineMarkerErrors.append( lineLocationSpace + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )

                if section=='Header' and newSection!='Introduction':
                    if discoveryDict and 'haveIntroductoryText' in discoveryDict and discoveryDict['haveIntroductoryText']:
                        newlineMarkerErrors.append( lineLocationSpace + _("Missing Introduction section (went from {} straight to {} section with {} marker)").format( section, newSection, marker ) )
                elif section!='Header' and newSection=='Introduction': newlineMarkerErrors.append( lineLocationSpace + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                if section=='Introduction' and newSection!='Numbering':
                    newlineMarkerErrors.append( lineLocationSpace + _("Missing Numbering section (went from {} straight to {} section with {} marker)").format( section, newSection, marker ) )
                if section=='Numbering' and newSection not in ('Text','Canonical Text','Text, Poetry',):
                    newlineMarkerErrors.append( lineLocationSpace + _("Missing Text section (went from {} straight to {} section with {} marker)").format( section, newSection, marker ) )
                if section=='Text' and newSection not in ('Canonical Text','Text, Poetry',):
                    newlineMarkerErrors.append( lineLocationSpace + _("Unexpected section after {} section (went to {} section with {} marker)").format( section, newSection, marker ) )
                #elif section!='Text' and newSection=='Text, Poetry':
                    #newlineMarkerErrors.append( lineLocationSpace + _("Didn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )

                if newSection=='Text' and section not in ('Introduction','Numbering','Canonical Text','Text, Poetry',):
                    newlineMarkerErrors.append( lineLocationSpace + _("DDidn't expect {} section after {} section (with {} marker)").format( newSection, section, marker ) )
                #print( "section", newSection )
                section = newSection

            # Note the newline SFM order -- create a list of markers in order (with duplicates combined, e.g., \v \v -> \v+)
            if marker != lastModifiedMarker: modifiedMarkerList.append( marker )
            else: # same marker in a row -- we append a sign to the saved marker to indicate multiple occurrences
                oldMarker = modifiedMarkerList.pop()
                assert oldMarker == marker or oldMarker == marker+'*'
                modifiedMarkerList.append( marker+'*' ) # Save the marker with the sign
            lastModifiedMarker = marker

            # Check for known bad combinations
            if marker=='nb' and lastMarker in ('s','s1','s2','s3','s4', 'qa'):
                newlineMarkerErrors.append( lineLocationSpace + _("'nb' not allowed immediately after {!r} section heading").format( marker ) )
            if self.checkUSFMSequencesFlag: # Check for known good combinations
                commonGoodNewlineMarkerCombinations = (
                    # If a marker has nothing after it, it must contain data
                    # If a marker has =E after it, it must NOT contain data
                    # (If data is optional, enter both sets)
                    # Heading stuff (in order of occurrence)
                    ('=E','id'), ('id','h'),('id','ide'), ('ide','h'), ('h','toc1'),('h','mt1'),('h','mt2'), ('toc1','toc2'), ('toc2','toc3'),('toc2','mt1'),('toc2','mt2'), ('toc3','mt1'),('toc3','mt2'),
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
                #for tuple2 in rarerGoodNewlineMarkerCombinations: print( tuple2); assert tuple2 not in commonGoodNewlineMarkerCombinations # Just check our tables for unwanted duplicates
                for tuple2 in rarerGoodNewlineMarkerCombinations: assert tuple2 not in commonGoodNewlineMarkerCombinations # Just check our tables for unwanted duplicates
                # We allow rem (remark) markers to be anywhere without a warning
                if lastMarkerEmpty and markerEmpty:
                    if (lastMarker+'=E',marker+'=E') not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker+'=E',marker+'=E') in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( lineLocationSpace + _("(Warning only) Empty {!r} not commonly used following empty {!r} marker").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("(Warning only) Empty {!r} not commonly used following empty {!r} marker").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( lineLocationSpace + _("Empty {!r} not normally used following empty {!r} marker").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("Empty {!r} not normally used following empty {!r} marker").format( marker, lastMarker ) )
                elif lastMarkerEmpty and not markerEmpty and marker!='rem':
                    if (lastMarker+'=E',marker) not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker+'=E',marker) in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( lineLocationSpace + _("(Warning only) {!r} with text not commonly used following empty {!r} marker").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("(Warning only) {!r} with text not commonly used following empty {!r} marker").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( lineLocationSpace + _("{!r} with text not normally used following empty {!r} marker").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("{!r} with text not normally used following empty {!r} marker").format( marker, lastMarker ) )
                elif not lastMarkerEmpty and markerEmpty and lastMarker!='rem':
                    if (lastMarker,marker+'=E') not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker,marker+'=E') in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( lineLocationSpace + _("(Warning only) Empty {!r} not commonly used following {!r} with text").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("(Warning only) Empty {!r} not commonly used following {!r} with text").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( lineLocationSpace + _("Empty {!r} not normally used following {!r} with text").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("Empty {!r} not normally used following {!r} with text").format( marker, lastMarker ) )
                elif lastMarker!='rem' and marker!='rem': # both not empty
                    if (lastMarker,marker) not in commonGoodNewlineMarkerCombinations:
                        if (lastMarker,marker) in rarerGoodNewlineMarkerCombinations:
                            newlineMarkerErrors.append( lineLocationSpace + _("(Warning only) {!r} with text not commonly used following {!r} with text").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("(Warning only) {!r} with text not commonly used following {!r} with text").format( marker, lastMarker ) )
                        else:
                            newlineMarkerErrors.append( lineLocationSpace + _("{!r} with text not normally used following {!r} with text").format( marker, lastMarker ) )
                            #print( lineLocationSpace + _("{!r} with text not normally used following {!r} with text").format( marker, lastMarker ) )

            getMarkerContentType = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType( marker )
            if text:
                # Check the internal SFMs
                if '\\' in text:
                    #print( text )
                    #assert '\\f ' not in text and '\\f*' not in text and '\\x ' not in text and '\\x*' not in text # The contents of these fields should now be in extras (unless there were errors)
                    #assert '\\fr ' not in text and '\\ft' not in text and '\\xo ' not in text and '\\xt' not in text # The contents of these fields should now be in extras (unless there were errors)
                    internalTextMarkers = []
                    ixStart = text.find( '\\' )
                    while ixStart != -1:
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
                            shouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( closedMarkerText )
                            if shouldBeClosed == 'N': internalMarkerErrors.append( lineLocationSpace + _("Marker {} cannot be closed").format( closedMarkerText ) )
                            elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                            elif closedMarkerText in hierarchy: internalMarkerErrors.append( lineLocationSpace + _("Internal markers appear to overlap: {}").format( internalTextMarkers ) )
                            else: internalMarkerErrors.append( lineLocationSpace + _("Unexpected internal closing marker: {} in {}").format( internalMarker, internalTextMarkers ) )
                        else: # it's not a closing marker
                            shouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( internalMarker )
                            if shouldBeClosed == 'N': continue # N for never
                            else: hierarchy.append( internalMarker ) # but what if it's optional ????????????????????????????????
                    if hierarchy: # it should be empty
                        internalMarkerErrors.append( lineLocationSpace + _("These markers {} appear not to be closed in {}").format( hierarchy, internalTextMarkers ) )

                if getMarkerContentType == 'N': # Never
                    newlineMarkerErrors.append( lineLocationSpace + _("Marker {!r} should not have content: {!r}").format( marker, text ) )
                    logging.warning( _("Marker {!r} should not have content after {} {}:{} with: {!r}").format( marker, self.BBB, C, V, text ) )
                    self.addPriorityError( 83, C, V, _("Marker {} shouldn't have content").format( marker ) )
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( text )
                #if markerList: print( "\nText {} {}:{} = {}:{!r}".format(self.BBB, C, V, marker, text)); print( markerList )
                openList = []
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check character markers
                    if not BibleOrgSysGlobals.loadedUSFMMarkers.isInternalMarker( insideMarker ): # these errors have probably been noted already
                        internalMarkerErrors.append( lineLocationSpace + _("Non-internal {} marker in {}: {}").format( insideMarker, marker, text ) )
                        logging.warning( _("Non-internal {} marker after {} {}:{} in {}: {}").format( insideMarker, self.BBB, C, V, marker, text ) )
                        self.addPriorityError( 66, C, V, _("Non-internal {} marker").format( insideMarker, ) )
                    else:
                        if not openList: # no open markers
                            if nextSignificantChar in ('',' '): openList.append( insideMarker ) # Got a new marker
                            else:
                                internalMarkerErrors.append( lineLocationSpace + _("Unexpected {}{} marker in {}: {}").format( insideMarker, nextSignificantChar, marker, text ) )
                                logging.warning( _("Unexpected {}{} marker after {} {}:{} in {}: {}").format( insideMarker, nextSignificantChar, self.BBB, C, V, marker, text ) )
                                self.addPriorityError( 66, C, V, _("Unexpected {}{} marker").format( insideMarker, nextSignificantChar ) )
                        else: # have at least one open marker
                            if nextSignificantChar=='*':
                                if insideMarker==openList[-1]: openList.pop() # We got the correct closing marker
                                else:
                                    internalMarkerErrors.append( lineLocationSpace + _("Wrong {}* closing marker for {} in {}: {}").format( insideMarker, openList[-1], marker, text ) )
                                    logging.warning( _("Wrong {}* closing marker for {} after {} {}:{} in {}: {}").format( insideMarker, openList[-1], self.BBB, C, V, marker, text ) )
                                    self.addPriorityError( 66, C, V, _("Wrong {}* closing marker for {}").format( insideMarker, openList[-1] ) )
                            else: # it's not an asterisk so appears to be another marker
                                if not BibleOrgSysGlobals.loadedUSFMMarkers.isNestingMarker( openList[-1] ): openList.pop() # Let this marker close the last one
                                openList.append( insideMarker ) # Now have multiple entries in the openList
                if len(openList) == 1: # only one marker left open
                    closedFlag = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( openList[0] )
                    if closedFlag != 'A': # always
                        if closedFlag == 'O': # optional
                            internalMarkerErrors.append( lineLocationSpace + _("Marker(s) {} don't appear to be (optionally) closed in {}: {}").format( openList, marker, text ) )
                            logging.info( _("Marker(s) {} don't appear to be (optionally) closed after {} {}:{} in {}: {}").format( openList, self.BBB, C, V, marker, text ) )
                            self.addPriorityError( 26, C, V, _("Marker(s) {} isn't closed").format( openList ) )
                        openList.pop() # This marker can (always or sometimes) be closed by the end of line
                if openList:
                    internalMarkerErrors.append( lineLocationSpace + _("Marker(s) {} don't appear to be closed in {}: {}").format( openList, marker, text ) )
                    logging.warning( _("Marker(s) {} don't appear to be closed after {} {}:{} in {}: {}").format( openList, self.BBB, C, V, marker, text ) )
                    self.addPriorityError( 36, C, V, _("Marker(s) {} should be closed").format( openList ) )
                    if len(openList) == 1: text += '\\' + openList[-1] + '*' # Try closing the last one for them
            # The following is handled above
            #else: # There's no text
                #if getMarkerContentType == 'A': # Always
                    #newlineMarkerErrors.append( lineLocationSpace + _("Marker {!r} has no content").format( marker ) )
                    #logging.warning( _("Marker {!r} has no content after").format( marker ) + " {} {}:{}".format( self.BBB, C, V ) )
                    #self.addPriorityError( 47, C, V, _("Marker {} should have content").format( marker ) )

            if extras:
                #print( "InternalBibleBook:doCheckSFMs-Extras-A {} {}:{} ".format( self.BBB, C, V ), extras )
                extraMarkers = []
                for extraType, extraIndex, extraText, cleanExtraText in extras:
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        if debuggingThisModule:
                            print( "InternalBibleBook:doCheckSFMs-Extras-B {} {}:{} ".format( self.BBB, C, V ), extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert extraIndex >= 0
                        #assert 0 <= extraIndex <= len(text)+3
                        assert extraType in BOS_EXTRA_TYPES
                    extraName = 'footnote' if extraType=='fn' else 'cross-reference'
                    if '\\f ' in extraText or '\\f*' in extraText or '\\x ' in extraText or '\\x*' in extraText: # Only the contents of these fields should be in extras
                        newlineMarkerErrors.append( lineLocationSpace + _("Programming error with extras: {}").format( extraText ) )
                        logging.warning( _("Programming error with {} notes after").format( extraText ) + " {} {}:{}".format( self.BBB, C, V ) )
                        self.addPriorityError( 99, C, V, _("Extras {} have a programming error").format( extraText ) )
                        continue # we have a programming error -- just skip this one
                    thisExtraMarkers = []
                    if '\\\\' in extraText:
                        noteMarkerErrors.append( lineLocationSpace + _("doubled backslash characters in  {}: {}").format( extraType, extraText ) )
                        while '\\\\' in extraText: extraText = extraText.replace( '\\\\', '\\' )
                    #if '  ' in extraText:
                    #    noteMarkerErrors.append( lineLocationSpace + _("doubled space characters in  {}: {}").format( extraType, extraText ) )
                    #    while '  ' in extraText: extraText = extraText.replace( '  ', ' ' )
                    if '\\' in extraText:
                        #print( extraText )
                        if BibleOrgSysGlobals.debugFlag: assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # These beginning and end markers should already be removed
                        thisExtraMarkers = []
                        ixStart = extraText.find( '\\' )
                        while ixStart != -1:
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
                                shouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( closedMarkerText )
                                #print( "here with", extraType, extraText, thisExtraMarkers, hierarchy, closedMarkerText, shouldBeClosed )
                                if shouldBeClosed == 'N': noteMarkerErrors.append( lineLocationSpace + _("Marker {} is not closeable").format( closedMarkerText ) )
                                elif hierarchy and hierarchy[-1] == closedMarkerText: hierarchy.pop(); continue # all ok
                                elif closedMarkerText in hierarchy: noteMarkerErrors.append( lineLocationSpace + _("Internal {} markers appear to overlap: {}").format( extraName, thisExtraMarkers ) )
                                else: noteMarkerErrors.append( lineLocationSpace + _("Unexpected {} closing marker: {} in {}").format( extraName, extraMarker, thisExtraMarkers ) )
                            else: # it's not a closing marker -- for extras, it probably automatically closes the previous marker
                                shouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( extraMarker )
                                if shouldBeClosed == 'N': continue # N for never
                                elif hierarchy: # Maybe the previous one is automatically closed by this one
                                    previousMarker = hierarchy[-1]
                                    previousShouldBeClosed = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType( previousMarker )
                                    if previousShouldBeClosed == 'O': # O for optional
                                        hierarchy.pop() # That they are not overlapped, but rather that the previous one is automatically closed by this one
                                hierarchy.append( extraMarker )
                        if len(hierarchy)==1 and BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerClosureType(hierarchy[0])=='S': # Maybe the last marker can be automatically closed
                            hierarchy.pop()
                        if hierarchy: # it should be empty
                            #print( "here with remaining", extraType, extraText, thisExtraMarkers, hierarchy )
                            noteMarkerErrors.append( lineLocationSpace + _("These {} markers {} appear not to be closed in {}").format( extraName, hierarchy, extraText ) )
                    adjExtraMarkers = thisExtraMarkers
                    for uninterestingMarker in allAvailableCharacterMarkers: # Remove character formatting markers so we can check the footnote/xref hierarchy
                        while uninterestingMarker in adjExtraMarkers: adjExtraMarkers.remove( uninterestingMarker )
                    if adjExtraMarkers and adjExtraMarkers not in BibleOrgSysGlobals.loadedUSFMMarkers.getTypicalNoteSets( extraType ):
                        #print( "Got", extraType, extraText, thisExtraMarkers )
                        if thisExtraMarkers: noteMarkerErrors.append( lineLocationSpace + _("Unusual {} marker set: {} in {}").format( extraName, thisExtraMarkers, extraText ) )
                        else: noteMarkerErrors.append( lineLocationSpace + _("Missing {} formatting in {}").format( extraName, extraText ) )

                    # Moved to checkNotes
                    #if len(extraText) > 2 and extraText[1] == ' ':
                    #    leaderChar = extraText[0] # Leader character should be followed by a space
                    #    if extraType == 'fn':
                    #        functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                    #        leaderName = "Footnote leader {!r}".format( leaderChar )
                    #        functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                    #    elif extraType == 'xr':
                    #        functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)
                    #        leaderName = "Cross-reference leader {!r}".format( leaderChar )
                    #        functionalCounts[leaderName] = 1 if leaderName not in functionalCounts else (functionalCounts[leaderName] + 1)
                    #else: noteMarkerErrors.append( lineLocationSpace + _("{} seems to be missing a leader character in {}").format( extraType, extraText ) )
                    if extraType == 'fn':
                        functionalCounts['Footnotes'] = 1 if 'Footnotes' not in functionalCounts else (functionalCounts['Footnotes'] + 1)
                    elif extraType == 'xr':
                        functionalCounts['Cross-References'] = 1 if 'Cross-References' not in functionalCounts else (functionalCounts['Cross-References'] + 1)
            lastMarker, lastMarkerEmpty = marker, markerEmpty


        # Check the relative ordering of newline markers
        #print( "modifiedMarkerList", modifiedMarkerList, self.BBB )
        if self.objectTypeString in ('USFM2','USFM3','USX'):
            if 'Book ID' not in functionalCounts or functionalCounts['Book ID']==0:
                newlineMarkerErrors.append( _("{} Missing 'id' USFM field in file").format( self.BBB ) )
                self.addPriorityError( 100, '', '', _("No id line in file") )
            elif modifiedMarkerList and modifiedMarkerList[0] != 'id':
                newlineMarkerErrors.append( _("{} First USFM field in file should have been 'id' not {!r}").format( self.BBB, modifiedMarkerList[0] ) )
                self.addPriorityError( 100, '', '', _("id line not first in file") )
            if 'Book ID' in functionalCounts and functionalCounts['Book ID']>1:
                newlineMarkerErrors.append( _("{} Multiple 'id' USFM fields in file").format( self.BBB ) )
                self.addPriorityError( 100, '', '', _("Multiple id lines in file") )

            if 'Book Header' not in functionalCounts or functionalCounts['Book Header']==0:
                newlineMarkerErrors.append( _("{} Missing 'h' USFM field in file").format( self.BBB ) )
                self.addPriorityError( 99, '', '', _("No h line in file") )
            elif 'Book Header' in functionalCounts and functionalCounts['Book Header']>1:
                newlineMarkerErrors.append( _("{} Multiple 'h' USFM fields in file").format( self.BBB ) )
                self.addPriorityError( 100, '', '', _("Multiple h lines in file") )

        for otherHeaderMarker in ( 'ide','sts', ):
            if otherHeaderMarker in modifiedMarkerList and modifiedMarkerList.index(otherHeaderMarker) > 8:
                newlineMarkerErrors.append( lineLocationSpace + _("USFM {!r} field in file should have been earlier in {}…").format( otherHeaderMarker, modifiedMarkerList[:10] ) )
        if 'mt2' in modifiedMarkerList: # Must be before or after a mt1
            ix = modifiedMarkerList.index( 'mt2' )
            if (ix==0 or modifiedMarkerList[ix-1]!='mt1') and (ix==len(modifiedMarkerList)-1 or modifiedMarkerList[ix+1]!='mt1'):
                newlineMarkerErrors.append( _("{} Expected mt2 marker to be next to an mt1 marker in {}…").format( self.BBB, modifiedMarkerList[:10] ) )

        if 'USFMs' not in self.errorDictionary: self.errorDictionary['USFMs'] = {} # So we hopefully get the errors first
        if newlineMarkerErrors: self.errorDictionary['USFMs']['Newline Marker Errors'] = newlineMarkerErrors
        #if newlineMarkerErrors and self.BBB not in ('NEH','GLS',): print( newlineMarkerErrors ); halt
        if internalMarkerErrors: self.errorDictionary['USFMs']['Internal Marker Errors'] = internalMarkerErrors
        if noteMarkerErrors: self.errorDictionary['USFMs']['Footnote and Cross-Reference Marker Errors'] = noteMarkerErrors
        if modifiedMarkerList:
            modifiedMarkerList.insert( 0, '['+self.BBB+']' )
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

        def countCharacters( adjText ):
            """
            Counts the characters for the given text (with internal markers already removed).

            Displays multiple spaces as middle-dots so more visible.
            """
            nonlocal haveNonAsciiChars
            #print( "countCharacters: {!r}".format( adjText ) )
            if '  ' in adjText:
                characterErrors.append( lineLocationSpace + _("Multiple spaces in {!r}").format( adjText.replace( '  ', '··' ) ) )
                self.addPriorityError( 7, C, V, _("Multiple spaces in text line") )
            if '  ' in adjText:
                characterErrors.append( lineLocationSpace + _("Multiple non-breaking spaces in {!r}").format( adjText.replace( '  ', '··' ) ) )
                self.addPriorityError( 9, C, V, _("Multiple non-breaking spaces in text line") )
            if adjText[-1].isspace(): # Most trailing spaces have already been removed, but this can happen in a note after the markers have been removed
                characterErrors.append( lineLocationSpace + _("Trailing space in {!r}").format( adjText ) )
                self.addPriorityError( 5, C, V, _("Trailing space in text line") )
                #print( lineLocationSpace + _("Trailing space in {} {!r}").format( marker, adjText ) )
            if BibleOrgSysGlobals.loadedUSFMMarkers.isPrinted( marker ): # Only do character counts on lines that will be printed
                for char in adjText:
                    lcChar = char.lower()

                    if char==' ': simpleCharName = simpleLCCharName = 'Space'
                    elif char==' ': simpleCharName = simpleLCCharName = 'NBSpace'
                    elif char==chr(0): simpleCharName = simpleLCCharName = 'Null'
                    else: simpleCharName = simpleLCCharName = char

                    try: unicodeCharName = unicodedata.name( char )
                    except ValueError: unicodeCharName = simpleCharName
                    try: unicodeLCCharName = unicodedata.name( lcChar )
                    except (ValueError,TypeError):
                        logging.error( "InternalBibleBook.countCharacters has error getting Unicode name of {!r} (from {!r})".format( lcChar, char ) )
                        unicodeLCCharName = simpleLCCharName

                    charNum = ord(char)
                    if charNum > 255 and char not in BibleOrgSysGlobals.ALL_WORD_PUNCT_CHARS: # Have special characters
                        haveNonAsciiChars = True
                    charHex = "0x{0:04x}".format( charNum )
                    #print( repr(char), repr(simpleCharName), unicodeCharName, charNum, charHex, haveNonAsciiChars )
                    #if haveNonAsciiChars: halt

                    simpleCharacterCounts[simpleCharName] = 1 if simpleCharName not in simpleCharacterCounts \
                                                                else simpleCharacterCounts[simpleCharName] + 1
                    isCommon = unicodeCharName in ('SPACE', 'COMMA', 'FULL STOP', 'COLON', 'SEMICOLON', 'QUESTION MARK',
                                                   'LEFT PARENTHESIS', 'RIGHT PARENTHESIS',
                                                   'DIGIT ONE','DIGIT TWO','DIGIT THREE','DIGIT FOUR','DIGIT FIVE',
                                                   'DIGIT SIX','DIGIT SEVEN','DIGIT EIGHT','DIGIT NINE','DIGIT ZERO', )
                    if not isCommon:
                        for commonString in ('LATIN SMALL LETTER ','LATIN CAPITAL LETTER ',):
                            if unicodeCharName.startswith(commonString) \
                            and len(unicodeCharName) == len(commonString)+1: # prevents things like letter ENG
                                isCommon = True; break
                    if not isCommon:
                        unicodeCharacterCounts[unicodeCharName] = 1 if unicodeCharName not in unicodeCharacterCounts \
                                                                else unicodeCharacterCounts[unicodeCharName] + 1
                    if char==' ' or char =='-' or char.isalpha():
                        letterCounts[simpleLCCharName] = 1 if simpleLCCharName not in letterCounts else letterCounts[simpleLCCharName] + 1
                    elif not char.isalnum(): # Assume it's punctuation
                        punctuationCounts[simpleCharName] = 1 if simpleCharName not in punctuationCounts else punctuationCounts[simpleCharName] + 1
                        if char not in BibleOrgSysGlobals.ALL_WORD_PUNCT_CHARS:
                            characterErrors.append( lineLocationSpace + _("Invalid {!r} ({}) word-building character ({})").format( simpleCharName, unicodeCharName, charHex ) )
                            self.addPriorityError( 10, C, V, _("Invalid {!r} ({}) word-building character ({})").format( simpleCharName, unicodeCharName, charHex ) )
                for char in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS:
                    if char not in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS and len(adjText)>1 \
                    and ( adjText[-1]==char or char+' ' in adjText ):
                        if char==' ': simpleCharName = 'Space'
                        elif char==' ': simpleCharName = 'NBSpace'
                        elif char==chr(0): simpleCharName = 'Null'
                        else: simpleCharName = char
                        unicodeCharName = unicodedata.name( char )
                        #print( "{} {}:{} char is {!r} {}".format( char, simpleCharName ) )
                        characterErrors.append( lineLocationSpace + _("Misplaced {!r} ({}) word leading character").format( simpleCharName, unicodeCharName ) )
                        self.addPriorityError( 21, C, V, _("Misplaced {!r} ({}) word leading character").format( simpleCharName, unicodeCharName ) )
                for char in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                    if char not in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS and len(adjText)>1 \
                    and ( adjText[0]==char or ' '+char in adjText ):
                        if char==' ': simpleCharName = 'Space'
                        elif char==' ': simpleCharName = 'NBSpace'
                        elif char==chr(0): simpleCharName = 'Null'
                        else: simpleCharName = char
                        unicodeCharName = unicodedata.name( char )
                        #print( "{} {}:{} char is {!r} {}".format( char, simpleCharName ) )
                        characterErrors.append( lineLocationSpace + _("Misplaced {!r} ({}) word trailing character").format( simpleCharName, unicodeCharName ) )
                        self.addPriorityError( 20, C, V, _("Misplaced {!r} ({}) word trailing character").format( simpleCharName, unicodeCharName ) )
        # end of countCharacters

        haveNonAsciiChars = False
        simpleCharacterCounts, unicodeCharacterCounts, letterCounts, punctuationCounts = {}, {}, {}, {} # We don't care about the order in which they appeared
        characterErrors = []
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V= text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if cleanText: countCharacters( cleanText )

            extras = entry.getExtras()
            if extras:
                for extraType, extraIndex, extraText, cleanExtraText in extras: # Now process the characters in the notes
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert extraIndex >= 0
                        #assert 0 <= extraIndex <= len(text)+3
                        assert extraType in BOS_EXTRA_TYPES
                        assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the contents of these fields should be in extras
                    #cleanExtraText = extraText
                    #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    #    cleanExtraText = cleanExtraText.replace( sign, '' )
                    #for marker in ['\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',] + BibleOrgSysGlobals.internal_SFMs_to_remove:
                    #    cleanExtraText = cleanExtraText.replace( marker, '' )
                    if cleanExtraText: countCharacters( cleanExtraText )

        # Add up the totals
        if (characterErrors or simpleCharacterCounts or unicodeCharacterCounts or letterCounts or punctuationCounts) and 'Characters' not in self.errorDictionary:
            self.errorDictionary['Characters'] = {}
        if characterErrors: self.errorDictionary['Characters']['Possible Character Errors'] = characterErrors
        if simpleCharacterCounts:
            total = 0
            for character in simpleCharacterCounts: total += simpleCharacterCounts[character]
            self.errorDictionary['Characters']['All Character Counts'] = simpleCharacterCounts
            self.errorDictionary['Characters']['All Character Counts']['Total'] = total
        if haveNonAsciiChars and unicodeCharacterCounts:
            total = 0
            for character in unicodeCharacterCounts: total += unicodeCharacterCounts[character]
            self.errorDictionary['Characters']['Special Character Counts'] = unicodeCharacterCounts
            self.errorDictionary['Characters']['Special Character Counts']['Total'] = total
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
        """
        Runs a number of checks on the speech marks in the Bible book.
        """
        goodNow = False # Yes, this code needs fixing badly

        reopenQuotesAtParagraph = True # Opening quotes are reused after a paragraph break if the speech is continuing
        closeQuotesAtParagraphEnd = False # Closing quotes are used at the end of a paragraph even if the speech is continuing into the next paragraph
        closeQuotesAtSectionEnd = False # Closing quotes are used at the end of a section even if the speech is continuing into the next section

        #OPENING_SPEECH_CHARACTERS = '“«‘‹' # The length and order of these two strings must match
        #CLOSING_SPEECH_CHARACTERS = '”»’›'
        #if BibleOrgSysGlobals.debugFlag: assert len(OPENING_SPEECH_CHARACTERS) == len(CLOSING_SPEECH_CHARACTERS)

        speechMarkErrors, openChars = [], []
        newSection = newParagraph = newBit = False
        bitMarker = ''
        startsWithOpen = endedWithClose = False
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, originalMarker, text, cleanText = entry.getMarker(), entry.getOriginalMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text:
                C, V = text.split()[0], '0'
                if C=='1': newSection = True # A new section after any introduction even if it doesn't start with an actual section heading
                continue # c fields contain no quote signs and don't affect formatting blocks
            elif marker=='v':
                if text: V = text.split()[0]
                continue # v fields contain no quote signs and don't affect formatting blocks
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if marker in ('s1','s2','s3','s4', 'qa'):
                newSection = True; bitMarker = originalMarker; continue # Nothing more to process here (although will miss check rare notes in section headings)
            if marker in ('p','ip','b', ): # Note 'm' is NOT included in this list
                newParagraph = True
                if not bitMarker: bitMarker = originalMarker
            if marker in ('m', ): newBit = True; bitMarker = originalMarker

            if marker in ('r', ): continue # We don't care about these
            if not cleanText: continue # Nothing to do for an empty field

            # From here on, we have relevant markers and something in cleanText
            startsWithOpen = False
            if cleanText[0] in BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS:
                startsWithOpen = True
                openQuoteIndex = BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS.index( cleanText[0] )
            elif len(cleanText)>1 and cleanText[0]==' ' and cleanText[1] in BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS: # This can occur after a leading xref with an extra space after it
                startsWithOpen = True
                openQuoteIndex = BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS.index( cleanText[1] )

            #print( C, V, "nS =",newSection, "nP =",newParagraph, "nB =",newBit, "sWO =",startsWithOpen, "eWC = ",endedWithClose, openChars, marker, "'"+cleanText+"'" )
            if openChars:
                if newSection and closeQuotesAtSectionEnd \
                or newParagraph and closeQuotesAtParagraphEnd:
                    match = openChars if len(openChars)>1 else "{!r}".format( openChars[0] )
                    speechMarkErrors.append( lineLocationSpace + _("Unclosed speech marks matching {} before {} marker").format( match, bitMarker ) )
                    logging.error( _("Unclosed speech marks matching {} before {} marker at").format( match, bitMarker ) \
                                                            + " {} {}:{}".format( self.BBB, C, V ) )
                    self.addPriorityError( 56, C, V, _("Unclosed speech marks matching {} after {} marker").format( match, bitMarker ) )
                    openChars = []
                elif newParagraph and reopenQuotesAtParagraph and not startsWithOpen:
                    match = openChars if len(openChars)>1 else "{!r}".format( openChars[0] )
                    speechMarkErrors.append( lineLocationSpace \
                                                + _("Unclosed speech marks matching {} before {} marker or missing reopening quotes").format( match, originalMarker ) )
                    logging.error( _("Unclosed speech marks matching {} before {} marker or missing reopening quotes at").format( match, originalMarker ) \
                                                            + " {} {}:{}".format( self.BBB, C, V ) )
                    self.addPriorityError( 55, C, V, _("Unclosed speech marks matching {} after {} marker or missing reopening quotes").format( match, originalMarker ) )
                    openChars = []

            if newSection and startsWithOpen and endedWithClose and not closeQuotesAtSectionEnd:
                if openQuoteIndex == closeQuoteIndex:
                    speechMarkErrors.append( lineLocationSpace + _("Unnecessary closing of speech marks before section heading") )
                    logging.error( _("Unnecessary closing of speech marks before section heading") + " {} {}:{}".format( self.BBB, C, V ) )
                    self.addPriorityError( 50, C, V, _("Unnecessary closing of speech marks before section heading") )

            #print( C, V, openChars, newParagraph, marker, '<' + cleanText + '>' )
            for j,char in enumerate(cleanText): # Go through each character handling speech marks
                if char in BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS:
                    if reopenQuotesAtParagraph and newParagraph and (j==0 or (j==1 and cleanText[0]==' ')) and openChars and char==openChars[-1]:
                        # This above also handles cross-references with an extra space at the beginning of a verse causing the opening quote(s) to be the second character
                        #print( C, V, "Ignored (restarting new paragraph quotation)", char, "with", openChars )
                        pass
                    else:
                        #print( "here0 with ", char, C, V, openChars )
                        if openChars and char==openChars[-1]:
                            if newBit:
                                speechMarkErrors.append( lineLocationSpace \
                                                                            + _("Seemed to reopen {!r} speech marks after {}").format( char, bitMarker ) )
                                logging.warning( _("Seemed to reopen {!r} speech marks after {} at").format( char, bitMarker ) \
                                                                            + " {} {}:{}".format( self.BBB, C, V ) )
                                self.addPriorityError( 43, C, V, _("Seemed to reopen {!r} speech marks after {}").format( char, bitMarker ) )
                                openChars.pop()
                            else:
                                speechMarkErrors.append( lineLocationSpace \
                                                                            + _("Unclosed {!r} speech marks (or improperly nested speech marks) after {}").format( char, openChars ) )
                                logging.error( _("Unclosed {!r} speech marks (or improperly nested speech marks) after {} at {}").format( char, openChars, self.__makeErrorRef(C,V) ) )
                                self.addPriorityError( 53, C, V, _("Unclosed {!r} speech marks (or improperly nested speech marks) after {}").format( char, openChars ) )
                        openChars.append( char )
                    if len(openChars)>4:
                        speechMarkErrors.append( lineLocationSpace + _("Excessive nested speech marks {}").format( openChars ) )
                        logging.error( _("Excessive nested speech marks {} at").format( openChars ) + " {} {}:{}".format( self.BBB, C, V ) )
                        self.addPriorityError( 50, C, V, _("Excessive nested speech marks {}").format( openChars ) )
                    elif len(openChars)>3:
                        speechMarkErrors.append( lineLocationSpace + _("Lots of nested speech marks {}").format( openChars ) )
                        logging.warning( _("Lots of nested speech marks {} at").format( openChars ) + " {} {}:{}".format( self.BBB, C, V ) )
                        self.addPriorityError( 40, C, V, _("Lots of nested speech marks {}").format( openChars ) )
                elif char in BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS:
                    closeIndex = BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS.index( char )
                    if not openChars:
                        #print( "here1 with ", char, C, V, openChars )
                        if char not in '?!': # Ignore the dual purpose punctuation characters
                            if goodNow:
                                speechMarkErrors.append( lineLocationSpace + _("Unexpected {!r} speech closing character").format( char ) )
                                logging.error( _("Unexpected {!r} speech closing character at {}").format( char, self.__makeErrorRef(C,V) ) )
                                self.addPriorityError( 52, C, V, _("Unexpected {!r} speech closing character").format( char ) )
                    elif closeIndex==BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS.index(openChars[-1]): # A good closing match
                        #print( "here2 with ", char, C, V )
                        openChars.pop()
                    elif char not in '?!': # Ignore the dual purpose punctuation characters
                        # We have closing marker that doesn't match
                        #print( "here3 with ", char, C, V, openChars )
                        if goodNow:
                            speechMarkErrors.append( lineLocationSpace + _("Mismatched {!r} speech closing character after {}").format( char, openChars ) )
                            logging.error( _("Mismatched {!r} speech closing character after {} at {}").format( char, openChars, self.__makeErrorRef(C,V) ) )
                            self.addPriorityError( 51, C, V, _("Mismatched {!r} speech closing character after {}").format( char, openChars ) )

            # End of processing clean-up
            endedWithClose = cleanText[-1] in BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS
            if endedWithClose: closeQuoteIndex = BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS.index( cleanText[-1] )
            newSection = newParagraph = newBit = False
            bitMarker = ''

            #if C=='9': halt
            extras = entry.getExtras()
            if extras: # Check the notes also -- each note is complete in itself so it's much simpler
                for extraType, extraIndex, extraText, cleanExtraText in extras: # Now process the characters in the notes
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #print( "InternalBibleBook:doCheckSpeechMarks {} {}:{} ".format( self.BBB, C, V ), extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert extraIndex >= 0
                        #assert 0 <= extraIndex <= len(text)+3
                        assert extraType in BOS_EXTRA_TYPES
                        assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the contents of these fields should be in extras
                    extraOpenChars = []
                    for char in extraText:
                        if char in BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS:
                            if extraOpenChars and char==extraOpenChars[-1]:
                                speechMarkErrors.append( lineLocationSpace + _("Improperly nested speech marks {} after {} in note").format( char, extraOpenChars ) )
                                logging.error( _("Improperly nested speech marks {} after {} in note in").format( char, extraOpenChars ) \
                                                                        + " {} {}:{}".format( self.BBB, C, V ) )
                                self.addPriorityError( 45, C, V, _("Improperly nested speech marks {} after {} in note").format( char, extraOpenChars ) )
                            extraOpenChars.append( char )
                        elif char in BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS:
                            closeIndex = BibleOrgSysGlobals.CLOSING_SPEECH_CHARACTERS.index( char )
                            if not extraOpenChars:
                                #print( "here1 with ", char, C, V, extraOpenChars )
                                if char not in '?!': # Ignore the dual purpose punctuation characters
                                    speechMarkErrors.append( lineLocationSpace + _("Unexpected {!r} speech closing character in note").format( char ) )
                                    logging.error( _("Unexpected {!r} speech closing character in note in").format( char ) + " {} {}:{}".format( self.BBB, C, V ) )
                                    self.addPriorityError( 43, C, V, _("Unexpected {!r} speech closing character in note").format( char ) )
                            elif closeIndex==BibleOrgSysGlobals.OPENING_SPEECH_CHARACTERS.index(extraOpenChars[-1]): # A good closing match
                                #print( "here2 with ", char, C, V )
                                extraOpenChars.pop()
                            elif char not in '?!': # Ignore the dual purpose punctuation characters
                                #print( "here3 with ", char, C, V, extraOpenChars )
                                speechMarkErrors.append( lineLocationSpace + _("Mismatched {!r} speech closing character after {} in note").format( char, extraOpenChars ) )
                                logging.error( _("Mismatched {!r} speech closing character after {} in note in").format( char, extraOpenChars ) \
                                                                            + " {} {}:{}".format( self.BBB, C, V ) )
                                self.addPriorityError( 42, C, V, _("Mismatched {!r} speech closing character after {} in note").format( char, extraOpenChars ) )
                    if extraOpenChars: # We've finished the note but some things weren't closed
                        speechMarkErrors.append( lineLocationSpace + _("Unclosed {} speech marks at end of note").format( extraOpenChars ) )
                        logging.error( _("Unclosed {} speech marks at end of note in").format( extraOpenChars ) + " {} {}:{}".format( self.BBB, C, V ) )
                        self.addPriorityError( 47, C, V, _("Unclosed {} speech marks at end of note").format( extraOpenChars ) )

        if openChars: # We've finished the book but some things weren't closed
            #print( "here9 with ", openChars )
            speechMarkErrors.append( lineLocationSpace + _("Unclosed {} speech marks at end of book").format( openChars ) )
            logging.error( _("Unclosed {} speech marks at end of book after").format( openChars ) + " {} {}:{}".format( self.BBB, C, V ) )
            self.addPriorityError( 54, C, V, _("Unclosed {} speech marks at end of book").format( openChars ) )

        # Add up the totals
        if (speechMarkErrors) and 'Speech Marks' not in self.errorDictionary: self.errorDictionary['Speech Marks'] = {}
        if speechMarkErrors: self.errorDictionary['Speech Marks']['Possible Matching Errors'] = speechMarkErrors
    # end of InternalBibleBook.doCheckSpeechMarks


    def doCheckWords( self ):
        """
        Runs a number of checks on the words used.
        """

        def countWords( marker, segment, lastWordTuple=None ):
            """Breaks the segment into words and counts them.
                Also checks for repeated words.
                If lastWordTuple is given, checks for words repeated across segments (and returns the new value).
            """

            def stripWordPunctuation( word ):
                """Removes leading and trailing punctuation from a word.
                    Returns the "clean" word."""
                while word and word[0] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS:
                    word = word[1:] # Remove leading punctuation
                while word and word[-1] in BibleOrgSysGlobals.TRAILING_WORD_PUNCT_CHARS:
                    word = word[:-1] # Remove trailing punctuation
                return word
            # end of stripWordPunctuation

            words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            if lastWordTuple is None: ourLastWord = ourLastRawWord = '' # No need to check words repeated across segment boundaries
            else: # Check in case a word has been repeated (e.g., at the end of one verse and then again at the beginning of the next verse)
                if BibleOrgSysGlobals.debugFlag:
                    assert isinstance( lastWordTuple, tuple )
                    assert len(lastWordTuple) == 2
                ourLastWord, ourLastRawWord = lastWordTuple
            for j,rawWord in enumerate(words):
                if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                word = rawWord
                for internalMarker in BibleOrgSysGlobals.internal_SFMs_to_remove: word = word.replace( internalMarker, '' )
                word = stripWordPunctuation( word )
                if word and not word[0].isalnum():
                    #print( word, stripWordPunctuation( word ) )
                    #print( lineLocationSpace + _("Have unexpected character starting word {!r}").format( word ) )
                    wordErrors.append( lineLocationSpace + _("Have unexpected character starting word {!r}").format( word ) )
                    word = word[1:]
                if word: # There's still some characters remaining after all that stripping
                    if BibleOrgSysGlobals.verbosityLevel > 3: # why???
                        for k,char in enumerate(word):
                            if not char.isalnum() and (k==0 or k==len(word)-1 or char not in BibleOrgSysGlobals.MEDIAL_WORD_PUNCT_CHARS):
                                wordErrors.append( lineLocationSpace + _("Have unexpected {!r} in word {!r}").format( char, word ) )
                    lcWord = word.lower()
                    isAReferenceOrNumber = True
                    for char in word:
                        if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                    if not isAReferenceOrNumber:
                        wordCounts[word] = 1 if word not in wordCounts else wordCounts[word] + 1
                        caseInsensitiveWordCounts[lcWord] = 1 if lcWord not in caseInsensitiveWordCounts else caseInsensitiveWordCounts[lcWord] + 1
                    #else: print( "excluded reference or number", word )

                    # Check for repeated words (case insensitive comparison)
                    if lcWord==ourLastWord.lower(): # Have a repeated word (might be across sentences)
                        repeatedWordErrors.append( lineLocationSpace + _("Have possible repeated word with {} {}").format( ourLastRawWord, rawWord ) )
                    ourLastWord, ourLastRawWord = word, rawWord
            return ourLastWord, ourLastRawWord
        # end of countWords


        # Count all the words
        wordCounts, caseInsensitiveWordCounts = {}, {}
        wordErrors, repeatedWordErrors = [], []
        lastTextWordTuple = ('','')
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V = text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if text and BibleOrgSysGlobals.loadedUSFMMarkers.isPrinted(marker): # process this main text
                lastTextWordTuple = countWords( marker, cleanText, lastTextWordTuple )

            extras = entry.getExtras()
            if extras:
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert extraIndex >= 0
                        #assert 0 <= extraIndex <= len(text)+3
                        assert extraType in BOS_EXTRA_TYPES
                        assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the contents of these fields should be in extras
                    #cleanExtraText = extraText
                    #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    #    cleanExtraText = cleanExtraText.replace( sign, '' )
                    #for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                    #    cleanExtraText = cleanExtraText.replace( marker, '' )
                    countWords( extraType, cleanExtraText )

        # Add up the totals
        if (wordErrors or wordCounts or caseInsensitiveWordCounts) and 'Words' not in self.errorDictionary: self.errorDictionary['Words'] = {} # So we hopefully get the errors first
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
        """
        Runs a number of checks on headings and section cross-references.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'doCheckFileControls'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines

        IDList, encodingList = [], []
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V = text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker1!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            if marker == 'id': IDList.append( "{} '{}'".format( self.BBB, text ) )
            elif marker == 'ide': encodingList.append( "{} '{}'".format( self.BBB, text ) )

        if (IDList or encodingList) and 'Controls' not in self.errorDictionary: self.errorDictionary['Controls'] = {} # So we hopefully get the errors first
        if IDList: self.errorDictionary['Controls']['ID Lines'] = IDList
        if encodingList: self.errorDictionary['Controls']['Encoding Lines'] = encodingList
    # end of InternalBibleBook.doCheckFileControls


    def doCheckHeadings( self, discoveryDict ):
        """
        Runs a number of checks on headings and section cross-references.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'doCheckHeadings'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines

        titleList, sectionHeadingList, sectionReferenceList, descriptiveTitleList, headingErrors = [], [], [], [], []
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()
            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V = text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if marker.startswith('mt'):
                titleList.append( "{} {}:{} Main Title {}: '{}'".format( self.BBB, C, V, marker[2:], text ) )
                if not text:
                    headingErrors.append( lineLocationSpace + _("Missing title text for marker {}").format( marker ) )
                    self.addPriorityError( 59, C, V, _("Missing title text") )
                elif text[-1] in '.።':
                    headingErrors.append( lineLocationSpace + _("{} title ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 69, C, V, _("Title ends with a period") )
            elif marker in ('s1','s2','s3','s4', 'qa'):
                if marker=='s1': sectionHeadingList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                else: sectionHeadingList.append( "{} {}:{} ({}) '{}'".format( self.BBB, C, V, marker, text ) )
                if not text:
                    headingErrors.append( lineLocationSpace + _("Missing heading text for marker {}").format( marker ) )
                    priority = 58
                    if discoveryDict:
                        if 'partlyDone' in discoveryDict and discoveryDict['partlyDone']>0: priority = 28
                        if 'notStarted' in discoveryDict and discoveryDict['notStarted']>0: priority = 18
                    self.addPriorityError( priority, C, V, _("Missing heading text") )
                elif text[-1] in '.።':
                    headingErrors.append( lineLocationSpace + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 68, C, V, _("Heading ends with a period") )
            elif marker=='r':
                sectionReferenceList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                if not text:
                    headingErrors.append( lineLocationSpace + _("Missing section cross-reference text for marker {}").format( marker ) )
                    self.addPriorityError( 57, C, V, _("Missing section cross-reference text") )
                else: # We have a section reference with text
                    if discoveryDict and 'sectionReferencesParenthesisFlag' in discoveryDict and discoveryDict['sectionReferencesParenthesisFlag']==False:
                        if text[0]=='(' or text[-1]==')':
                            headingErrors.append( lineLocationSpace + _("Section cross-reference not expected to have parenthesis: {}").format( text ) )
                            self.addPriorityError( 67, C, V, _("Section cross-reference not expected to have parenthesis") )
                    else: # assume that parenthesis are required
                        if text[0]!='(' or text[-1]!=')':
                            headingErrors.append( lineLocationSpace + _("Section cross-reference not in parenthesis: {}").format( text ) )
                            self.addPriorityError( 67, C, V, _("Section cross-reference not in parenthesis") )
            elif marker=='d':
                descriptiveTitleList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                if not text:
                    headingErrors.append( lineLocationSpace + _("Missing heading text for marker {}").format( marker ) )
                    priority = 57
                    if discoveryDict:
                        if 'partlyDone' in discoveryDict and discoveryDict['partlyDone']>0: priority = 27
                        if 'notStarted' in discoveryDict and discoveryDict['notStarted']>0: priority = 17
                    self.addPriorityError( priority, C, V, _("Missing heading text") )
                elif text[-1] != ':' and not hasClosingPunctuation( text ):
                    headingErrors.append( lineLocationSpace + _("{} heading should have closing punctuation (period): {}").format( marker, text ) )
                    self.addPriorityError( 67, C, V, _("Heading should have closing punctuation (period)") )

        if (headingErrors or titleList or sectionHeadingList or sectionReferenceList or descriptiveTitleList) and 'Headings' not in self.errorDictionary:
            self.errorDictionary['Headings'] = {} # So we hopefully get the errors first
        if headingErrors: self.errorDictionary['Headings']['Possible Heading Errors'] = headingErrors
        if titleList: self.errorDictionary['Headings']['Title Lines'] = titleList
        if sectionHeadingList: self.errorDictionary['Headings']['Section Heading Lines'] = sectionHeadingList
        if descriptiveTitleList: self.errorDictionary['Headings']['Descriptive Heading Lines'] = descriptiveTitleList
        if sectionReferenceList: self.errorDictionary['Headings']['Section Cross-reference Lines'] = sectionReferenceList
    # end of InternalBibleBook.doCheckHeadings


    def doCheckIntroduction( self ):
        """
        Runs a number of checks on introductory parts.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'doCheckIntroduction'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines

        mainTitleList, headingList, titleList, outlineList, introductionErrors = [], [], [], [], []
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V = text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            if marker in ('imt1','imt2','imt3','imt4',):
                if marker=='imt1': mainTitleList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                else: mainTitleList.append( "{} {}:{} ({}) '{}'".format( self.BBB, C, V, marker, text ) )
                if not cleanText:
                    introductionErrors.append( lineLocationSpace + _("Missing heading text for marker {}").format( marker ) )
                    self.addPriorityError( 39, C, V, _("Missing heading text") )
                elif cleanText[-1] in '.።':
                    introductionErrors.append( lineLocationSpace + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 49, C, V, _("Heading ends with a period") )
            elif marker in ('is1','is2','is3','is4',):
                if marker=='is1': headingList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                else: headingList.append( "{} {}:{} ({}) '{}'".format( self.BBB, C, V, marker, text ) )
                if not cleanText:
                    introductionErrors.append( lineLocationSpace + _("Missing heading text for marker {}").format( marker ) )
                    self.addPriorityError( 39, C, V, _("Missing heading text") )
                elif cleanText[-1] in '.።':
                    introductionErrors.append( lineLocationSpace + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 49, C, V, _("Heading ends with a period") )
            elif marker=='iot':
                titleList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                if not cleanText:
                    introductionErrors.append( lineLocationSpace + _("Missing outline title text for marker {}").format( marker ) )
                    self.addPriorityError( 38, C, V, _("Missing outline title text") )
                elif cleanText[-1] in '.።':
                    introductionErrors.append( lineLocationSpace + _("{} heading ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 48, C, V, _("Heading ends with a period") )
            elif marker in ('io1','io2','io3','io4',):
                if marker=='io1': outlineList.append( "{} {}:{} '{}'".format( self.BBB, C, V, text ) )
                else: outlineList.append( "{} {}:{} ({}) '{}'".format( self.BBB, C, V, marker, text ) )
                if not cleanText:
                    introductionErrors.append( lineLocationSpace + _("Missing outline text for marker {}").format( marker ) )
                    self.addPriorityError( 37, C, V, _("Missing outline text") )
                elif cleanText[-1] in '.።':
                    introductionErrors.append( lineLocationSpace + _("{} outline entry ends with a period: {}").format( marker, text ) )
                    self.addPriorityError( 47, C, V, _("Outline entry ends with a period") )
            elif marker in ('ip','ipi','im','imi',):
                if not cleanText:
                    introductionErrors.append( lineLocationSpace + _("Missing introduction text for marker {}").format( marker ) )
                    self.addPriorityError( 36, C, V, _("Missing introduction text") )
                elif cleanText[-1] != ':' and not hasClosingPeriod( cleanText ):
                #and not cleanText.endswith('.\\it*') and not text.endswith('.&quot;') and not text.endswith('.&#39;'):
                    if cleanText.endswith(')') or cleanText.endswith(']'): # do we still need this
                        introductionErrors.append( lineLocationSpace + _("{} introduction text possibly does not have closing punctuation (period): {}").format( marker, text ) )
                        self.addPriorityError( 26, C, V, _("Introduction text possibly ends without closing punctuation (period)") )
                    else:
                        introductionErrors.append( lineLocationSpace + _("{} introduction text does not have closing punctuation (period): {}").format( marker, text ) )
                        self.addPriorityError( 46, C, V, _("Introduction text ends without closing punctuation (period)") )

        if (introductionErrors or mainTitleList or headingList or titleList or outlineList) and 'Introduction' not in self.errorDictionary:
            self.errorDictionary['Introduction'] = {} # So we hopefully get the errors first
        if introductionErrors: self.errorDictionary['Introduction']['Possible Introduction Errors'] = introductionErrors
        if mainTitleList: self.errorDictionary['Introduction']['Main Title Lines'] = mainTitleList
        if headingList: self.errorDictionary['Introduction']['Section Heading Lines'] = headingList
        if titleList: self.errorDictionary['Introduction']['Outline Title Lines'] = titleList
        if outlineList: self.errorDictionary['Introduction']['Outline Entry Lines'] = outlineList
    # end of InternalBibleBook.doCheckIntroduction


    def doCheckNotes( self, discoveryDict ):
        """
        Runs a number of checks on footnotes and cross-references.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'doCheckNotes'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines

        allAvailableCharacterMarkers = BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList( includeBackslash=True )

        footnoteList, xrefList = [], []
        footnoteLeaderList, xrefLeaderList, CVSeparatorList = [], [], []
        footnoteErrors, xrefErrors, noteMarkerErrors = [], [], []
        leaderCounts = {}
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for entry in self._processedLines:
            marker, text = entry.getMarker(), entry.getText()

            # Keep track of where we are for more helpful error messages
            if marker=='c' and text: C, V = text.split()[0], '0'
            elif marker=='v' and text: V = text.split()[0]
            elif C == '-1' and marker!='intro': V = str( int(V) + 1 ) # first/id line will be 0:0

            lineLocation = '{} {}:{}'.format( self.BBB, C, V )
            lineLocationSpace = lineLocation + ' '

            extras = entry.getExtras()
            if extras:
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    if BibleOrgSysGlobals.debugFlag:
                        assert extraText # Shouldn't be blank
                        #assert extraText[0] != '\\' # Shouldn't start with backslash code
                        assert extraText[-1] != '\\' # Shouldn't end with backslash code
                        #assert 0 <= extraIndex <= len(text) -- not necessarily true for multiple notes
                        assert extraType in BOS_EXTRA_TYPES
                        assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the CONTENTS of these fields should be in extras

                    # Get a copy of the note text without any formatting
                    #cleanExtraText = extraText
                    #for sign in ('- ', '+ '): # Remove common leader characters (and the following space)
                    #    cleanExtraText = cleanExtraText.replace( sign, '' )
                    #for marker in ('\\xo*','\\xo ','\\xt*','\\xt ','\\xdc*','\\xdc ','\\fr*','\\fr ','\\ft*','\\ft ','\\fq*','\\fq ','\\fv*','\\fv ','\\fk*','\\fk ',):
                    #    cleanExtraText = cleanExtraText.replace( marker, '' )

                    if extraType in ('fn', 'en', 'xr', ):
                        # Create a list of markers in the note and their contents
                        status, myString, lastCode, lastString, extraList = 0, '', '', '', []
                        #print( extraText )
                        adjExtraText = extraText
                        for chMarker in allAvailableCharacterMarkers:
                            adjExtraText = adjExtraText.replace( chMarker, '__' + chMarker[1:].upper() + '__' ) # Change character formatting
                        for char in adjExtraText:
                            if status==0: # waiting for leader char
                                if char==' ' and myString:
                                    extraList.append( ('leader',myString,) )
                                    status, myString = 1, ''
                                else: myString += char
                            elif status==1: # waiting for a backslash code
                                if BibleOrgSysGlobals.debugFlag: assert not lastCode
                                if char=='\\':
                                    if myString and myString!=' ':
                                        #print( "Something funny in", extraText, extraList, myString ) # Perhaps a fv field embedded in another field???
                                        #assert len(extraList)>=2 and extraList[-2][1] == '' # If so, the second to last field is often blank
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
                                            footnoteErrors.append( lineLocationSpace + _("Footnote markers don't match: {!r} and {!r}").format( lastCode, myString+'*' ) )
                                            self.addPriorityError( 32, C, V, _("Mismatching footnote markers") )
                                        elif extraType == 'xr':
                                            xrefErrors.append( lineLocationSpace + _("Cross-reference don't match: {!r} and {!r}").format( lastCode, myString+'*' ) )
                                            self.addPriorityError( 31, C, V, _("Mismatching cross-reference markers") )
                                        #print( "checkNotes: error with", lastCode, extraList, myString, self.BBB, C, V, ); halt
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
                        extract = (extraText[:70] + '…' + extraText[-5:]) if len(extraText)>80 else extraText
                        line = "{} {}:{} '{}'".format( self.BBB, C, V, extract )
                        if extraType == 'fn':
                            haveFinalPeriod = True
                            footnoteList.append( line )
                            if cleanExtraText.endswith(' '):
                                footnoteErrors.append( lineLocationSpace + _("Footnote seems to have an extra space at end: {!r}").format( extraText ) )
                                self.addPriorityError( 32, C, V, _("Extra space at end of footnote") )
                            elif cleanExtraText and not hasClosingPunctuation( cleanExtraText ):
                            #and not cleanExtraText.endswith('.&quot;') and not text.endswith('.&#39;'):
                                haveFinalPeriod = False
                            if discoveryDict and 'footnotesPeriodFlag' in discoveryDict:
                                if discoveryDict['footnotesPeriodFlag']==True and not haveFinalPeriod:
                                    footnoteErrors.append( lineLocationSpace + _("Footnote seems to be missing closing punctuation (period): {!r}").format( extraText ) )
                                    self.addPriorityError( 33, C, V, _("Missing closing punctuation (period) at end of footnote") )
                                if discoveryDict['footnotesPeriodFlag']==False and haveFinalPeriod:
                                    footnoteErrors.append( lineLocationSpace + _("Footnote seems to include possible unnecessary closing punctuation (period): {!r}").format( extraText ) )
                                    self.addPriorityError( 32, C, V, _("Possible unnecessary closing punctuation (period) at end of footnote") )
                        elif extraType == 'xr':
                            haveFinalPeriod = True
                            xrefList.append( line )
                            if cleanExtraText.endswith(' '):
                                xrefErrors.append( lineLocationSpace + _("Cross-reference seems to have an extra space at end: {!r}").format( extraText ) )
                                self.addPriorityError( 30, C, V, _("Extra space at end of cross-reference") )
                            elif cleanExtraText and not hasClosingPunctuation( cleanExtraText ):
                            #and not cleanExtraText.endswith('.&quot;') and not text.endswith('.&#39;'):
                                haveFinalPeriod = False
                            if discoveryDict and 'crossReferencesPeriodFlag' in discoveryDict:
                                if discoveryDict['crossReferencesPeriodFlag']==True and not haveFinalPeriod:
                                    xrefErrors.append( lineLocationSpace + _("Cross-reference seems to be missing closing punctuation (period): {!r}").format( extraText ) )
                                    self.addPriorityError( 31, C, V, _("Missing closing punctuation (period) at end of cross-reference") )
                                if discoveryDict['crossReferencesPeriodFlag']==False and haveFinalPeriod:
                                    xrefErrors.append( lineLocationSpace + _("Cross-reference seems to include possible unnecessary closing punctuation (period): {!r}").format( extraText ) )
                                    self.addPriorityError( 32, C, V, _("Possible unnecessary closing punctuation (period) at end of cross-reference") )

                        # Check for two identical fields in a row
                        lastNoteMarker = None
                        for noteMarker,noteText in extraList:
                            if noteMarker == lastNoteMarker: # Have two identical fields in a row
                                if extraType == 'fn':
                                    footnoteErrors.append( lineLocationSpace + _("Consecutive {} fields in footnote: {!r}").format( noteMarker, extraText ) )
                                    self.addPriorityError( 35, C, V, _("Consecutive {} fields in footnote").format( noteMarker ) )
                                elif extraType == 'xr':
                                    xrefErrors.append( lineLocationSpace + _("Consecutive {} fields in cross-reference: {!r}").format( noteMarker, extraText ) )
                                    self.addPriorityError( 35, C, V, _("Consecutive {} fields in cross-reference").format( noteMarker ) )
                                #print( "Consecutive fields in {!r}".format( extraText ) )
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
                                leaderName = "Footnote leader {!r}".format( leader )
                                leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                if leader not in footnoteLeaderList: footnoteLeaderList.append( leader )
                            elif extraType == 'xr':
                                leaderCounts['Cross-References'] = 1 if 'Cross-References' not in leaderCounts else (leaderCounts['Cross-References'] + 1)
                                leaderName = "Cross-reference leader {!r}".format( leader )
                                leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                if leader not in xrefLeaderList: xrefLeaderList.append( leader )
                        else: noteMarkerErrors.append( lineLocationSpace + _("{} seems to be missing a leader character in {}").format( extraType, extraText ) )

                        # Find, count and check CVSeparators
                        #  and also check that the references match
                        fnCVSeparator = xrCVSeparator = fnTrailer = xrTrailer = ''
                        haveAnchor = False
                        for noteMarker,noteText in extraList:
                            if noteMarker=='fr':
                                haveAnchor = True
                                if 1: # new code
                                    anchor = BibleAnchorReference( self.BBB, C, V )
                                    #print( "here at BibleAnchorReference", self.BBB, C, V, anchor )
                                    if not anchor.matchesAnchorString( noteText, 'footnote' ):
                                        footnoteErrors.append( lineLocationSpace + _("Footnote anchor reference seems not to match: {!r}").format( noteText ) )
                                        logging.error( _("Footnote anchor reference seems not to match after {} {}:{} in {!r}").format( self.BBB, C, V, noteText ) )
                                        self.addPriorityError( 42, C, V, _("Footnote anchor reference mismatch") )
                                        #print( self.BBB, C, V, 'FN0', '"'+noteText+'"' )
                                else: # old code
                                    for j,char in enumerate(noteText):
                                        if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                            fnCVSeparator = char
                                            leaderName = "Footnote CV separator {!r}".format( char )
                                            leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                            if char not in CVSeparatorList: CVSeparatorList.append( char )
                                            break
                                    if not noteText[-1].isdigit(): fnTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                                    myV = V # Temporary copy
                                    if myV.isdigit() and marker=='s1': myV=str(int(myV)+1) # Assume that a section heading goes with the next verse (bad assumption if the break is in the middle of a verse)
                                    CV1 = (C + fnCVSeparator + myV) if fnCVSeparator and fnCVSeparator in noteText else myV # Make up our own reference string
                                    CV2 = CV1 + fnTrailer # Make up our own reference string
                                    if CV2 != noteText:
                                        if CV1 not in noteText and noteText not in CV2: # This crudely handles a range in either the verse number or the anchor (as long as the individual one is at the start of the range)
                                            #print( "{} fn m={!r} V={} myV={} CV1={!r} CV2={!r} nT={!r}".format( self.BBB, marker, V, myV, CV1, CV2, noteText ) )
                                            footnoteErrors.append( lineLocationSpace + _("Footnote anchor reference seems not to match: {!r}").format( noteText ) )
                                            self.addPriorityError( 42, C, V, _("Footnote anchor reference mismatch") )
                                            print( self.BBB, 'FN1', '"'+noteText+'"', "'"+fnCVSeparator+"'", "'"+fnTrailer+"'", CV1, CV2 )
                                        else:
                                            footnoteErrors.append( lineLocationSpace + _("Footnote anchor reference possibly does not match: {!r}").format( noteText ) )
                                            print( self.BBB, 'FN2', '"'+noteText+'"', "'"+fnCVSeparator+"'", "'"+fnTrailer+"'", CV1, CV2 )
                                break # Only process the first fr field
                            elif noteMarker=='xo':
                                haveAnchor = True
                                if 1: # new code
                                    anchor = BibleAnchorReference( self.BBB, C, V )
                                    if not anchor.matchesAnchorString( noteText, 'cross-reference' ):
                                        footnoteErrors.append( lineLocationSpace + _("Cross-reference anchor reference seems not to match: {!r}").format( noteText ) )
                                        logging.error( _("Cross-reference anchor reference seems not to match after {} {}:{} in {!r}").format( self.BBB, C, V, noteText ) )
                                        self.addPriorityError( 41, C, V, _("Cross-reference anchor reference mismatch") )
                                        #print( self.BBB, C, V, 'XR0', '"'+noteText+'"' )
                                else: # old code
                                    for j,char in enumerate(noteText):
                                        if not char.isdigit() and j<len(noteText)-1: # Got a non-digit and it's not at the end of the reference
                                            xrCVSeparator = char
                                            leaderName = "Cross-reference CV separator {!r}".format( char )
                                            leaderCounts[leaderName] = 1 if leaderName not in leaderCounts else (leaderCounts[leaderName] + 1)
                                            if char not in CVSeparatorList: CVSeparatorList.append( char )
                                            break
                                    if not noteText[-1].isalnum(): xrTrailer = noteText[-1] # Sometimes these references end with a trailer character like a colon
                                    elif len(noteText)>3 and noteText[-2:]==' a' and not noteText[-3].isalnum(): xrTrailer = noteText[-3:] # This is a hack to handle something like "12:5: a"
                                    CV1 = (C + xrCVSeparator + V) if xrCVSeparator and xrCVSeparator in noteText else V # Make up our own reference string
                                    CV2 = CV1 + xrTrailer # Make up our own reference string
                                    if CV2 != noteText:
                                        #print( "V={!r}  xrT={!r}  CV1={!r}  CV2={!r}  NT={!r}".format( V, xrTrailer, CV1, CV2, noteText ) )
                                        if CV1 not in noteText and noteText not in CV2: # This crudely handles a range in either the verse number or the anchor (as long as the individual one is at the start of the range)
                                            #print( 'xr', CV1, noteText )
                                            xrefErrors.append( lineLocationSpace + _("Cross-reference anchor reference seems not to match: {!r}").format( noteText ) )
                                            self.addPriorityError( 41, C, V, _("Cross-reference anchor reference mismatch") )
                                            print( self.BBB, 'XR1', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                                        elif noteText.startswith(CV2) or noteText.startswith(CV1+',') or noteText.startswith(CV1+'-'):
                                            #print( "  ok" )
                                            pass # it seems that the reference is contained there in the anchor
                                            #print( self.BBB, 'XR2', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                                        else:
                                            xrefErrors.append( lineLocationSpace + _("Cross-reference anchor reference possibly does not match: {!r}").format( noteText ) )
                                            print( self.BBB, 'XR3', '"'+noteText+'"', "'"+xrCVSeparator+"'", "'"+xrTrailer+"'", CV1, CV2 )
                                break # Only process the first xo field
                        if not haveAnchor:
                            if extraType == 'fn':
                                if discoveryDict and 'haveFootnoteOrigins' in discoveryDict and discoveryDict['haveFootnoteOrigins']>0:
                                    footnoteErrors.append( lineLocationSpace + _("Footnote seems to have no anchor reference: {!r}").format( extraText ) )
                                    self.addPriorityError( 39, C, V, _("Missing anchor reference for footnote") )
                            elif extraType == 'xr':
                                if discoveryDict and 'haveCrossReferenceOrigins' in discoveryDict and discoveryDict['haveCrossReferenceOrigins']>0:
                                    xrefErrors.append( lineLocationSpace + _("Cross-reference seems to have no anchor reference: {!r}").format( extraText ) )
                                    self.addPriorityError( 38, C, V, _("Missing anchor reference for cross-reference") )

                    # much more yet to be written …

        if (footnoteErrors or xrefErrors or noteMarkerErrors or footnoteList or xrefList or leaderCounts) and 'Notes' not in self.errorDictionary:
            self.errorDictionary['Notes'] = {} # So we hopefully get the errors first
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
        """
        Runs a number of checks on the book and returns the error dictionary.
        """
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'check'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines

        # Ignore the result of these next ones -- just use any errors collected
        #self.getVersification() # This checks CV ordering, etc. at the same time
        # Further checks
        self.doCheckSFMs( discoveryDict )
        self.doCheckCharacters()
        self.doCheckSpeechMarks()
        self.doCheckWords()
        self.doCheckHeadings( discoveryDict )
        self.doCheckIntroduction()
        self.doCheckNotes( discoveryDict ) # footnotes and cross-references

        if self.checkAddedUnitsFlag: # This code is temporary XXXXXXXXXXXXXXXXXXXXXXXX …
            if typicalAddedUnitData is None: # Get our recommendations for added units
                import pickle
                folder = os.path.join( os.path.dirname(__file__), 'DataFiles/', 'ScrapedFiles/' ) # Relative to module, not cwd
                filepath = os.path.join( folder, "AddedUnitData.pickle" )
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( _("Importing from {}…").format( filepath ) )
                with open( filepath, 'rb' ) as pickleFile:
                    typicalAddedUnitData = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            self.doCheckAddedUnits( typicalAddedUnitData )
    # end of InternalBibleBook.check


    def getErrors( self ):
        """
        Returns the error dictionary for the book.
        """
        if 'Priority Errors' in self.errorDictionary and not self.errorDictionary['Priority Errors']:
            self.errorDictionary.pop( 'Priority Errors' ) # Remove empty dictionary entry if unused
        return self.errorDictionary
    # end of InternalBibleBook.getErrors


    def getNumChapters( self ):
        """
        Returns the number of chapters (int) in this book.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "getNumChapters()" )

        self.getVersificationIfNecessary()
        #print( self.getVersification() )
        lastChapterNumberString =  self.versificationList[-1][0] # The last chapter number
        #print( "NumChapters", lastChapterNumberString )
        return int( lastChapterNumberString )
    # end of InternalBibleBook.getNumChapters


    def getNumVerses( self, C ):
        """
        Returns the number of verses (int) in the given chapter.

        Also works for chapter zero (the book introduction).

        Returns None if there is no such chapter.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "getNumVerses( {!r} )".format( C ) )

        if isinstance( C, int ): # Just double-check the parameter
            logging.debug( "getNumVerses was passed an integer chapter instead of a string with {} {}".format( self.BBB, C ) )
            C = str( C )
        self.getVersificationIfNecessary()
        for thisC,thisNumVerses in self.versificationList:
            if thisC == C:
                #print( "NumVerses", thisNumVerses )
                return int( thisNumVerses )
    # end of InternalBibleBook.getNumVerses


    def getContextVerseData( self, BCVReference ):
        """
        Returns an InternalBibleEntryListObject plus a list containing the context of the verse.

        Raises a KeyError if the C:V reference is not found
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule:
                print( "InternalBibleBook.getContextVerseData( {} ) for {}".format( BCVReference, self.BBB ) )
            assert self._processedFlag
            assert self._indexedCVFlag

        if isinstance( BCVReference, tuple ): assert BCVReference[0] == self.BBB
        else: assert BCVReference.getBBB() == self.BBB
        if not self._processedFlag:
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "InternalBibleBook {} {!r}: processing lines called from 'getContextVerseData'".format( self.BBB, self.workName ) )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag:
            assert self._processedLines
            assert self._indexedCVFlag
        if isinstance( BCVReference, tuple ): C, V = BCVReference[1], BCVReference[2]
        else: # assume it's a SimpleVerseKey or similar
            C,V = BCVReference.getCV()
        return self._CVIndex.getEntriesWithContext( (C,V,) ) # Gives a KeyError if not found
    # end of InternalBibleBook.getContextVerseData


    def writeBOSBCVFiles( self, bookFolderPath ):
        """
        Write the internal pseudoUSFM out directly with one file per verse in one folder for the book.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( '  writeBOSBCVFiles: ' + _("Writing {!r} as BCV…").format( self.BBB ) )

        # Write the data out with the introduction in one file, and then each verse in a separate file
        introLines = verseLines = ''
        CVList = []
        for CVKey in self._CVIndex:
            C, V = CVKey
            #print( 'writeBOSBCVFiles: {} {}:{}'.format( self.BBB, C, V ) )

            # Put all of the pseudoUSFM lines for the entry at CVKey into
            for entry in self._CVIndex.getEntries( CVKey ):
                #print( entry )
                marker, originalMarker = entry.getMarker(), entry.getOriginalMarker()
                line = '\\'+marker
                if originalMarker and originalMarker!=marker and (marker,originalMarker) not in (('c#','c'),('v~','v'),):
                    line += '<<'+originalMarker
                content = entry.getOriginalText()
                if content: line += '='+content
                line += '\n'
                if C == '-1':
                    introLines += line # collect all of the intro parts
                else: verseLines += line

            # Write file, but don't write intro until we get to the first chapter marker (usually chapter 1 but could be 0)
            if C != '-1':
                if introLines:
                    # Double underline in filename for better dir sorting/display
                    with open( os.path.join( bookFolderPath, self.BBB+'__Intro.txt' ), 'wt', encoding='utf-8' ) as myFile:
                        myFile.write( introLines )
                    introLines = None # Will now cause an error if we try to do more introduction bits -- should only be one intro
                    CVList.append( ('-1',) )
                elif verseLines:
                    with open( os.path.join( bookFolderPath, self.BBB+'_C'+C+'V'+V+'.txt' ), 'wt', encoding='utf-8' ) as myFile:
                        myFile.write( verseLines )
                    verseLines = '' # Empty ready for the next verse
                    CVList.append( CVKey )
        if introLines: # handle left-overs for books without chapters
            assert not CVList
            with open( os.path.join( bookFolderPath, self.BBB+'_C0.txt' ), 'wt', encoding='utf-8' ) as myFile:
                myFile.write( introLines )
            CVList.append( ('-1',) )
        if verseLines: print( f"verseLines = {verseLines}" )
        assert not verseLines

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Writing BCV book metadata…") )
        metadataLines = 'BCVVersion = {}\n'.format( BCV_VERSION )
        if self.workName: metadataLines += 'WorkName = {}\n'.format( self.workName )
        metadataLines += 'CVList = {}\n'.format( CVList )
         # Double underline in filename for better dir sorting/display
        with open( os.path.join( bookFolderPath, self.BBB+'__BookMetadata.txt' ), 'wt', encoding='utf-8' ) as metadataFile:
            metadataFile.write( metadataLines )
    # end of InternalBibleBook.writeBOSBCVFiles
# end of class InternalBibleBook


def demo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    print( "Since this is only designed to be a base class, it can't actually do much at all." )
    print( "  Try running USFMBibleBook or USXXMLBibleBook which use this class." )

    IBB = InternalBibleBook( 'Dummy', 'GEN' )
    # The following fields would normally be filled in a by "load" routine in the derived class
    IBB.objectNameString = 'Dummy test Internal Bible Book object'
    IBB.objectTypeString = 'DUMMY'
    IBB.sourceFilepath = 'Nowhere'
    if BibleOrgSysGlobals.verbosityLevel > 0: print( IBB )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleBook.py
