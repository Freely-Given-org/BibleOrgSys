#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# InternalBibleBook.py
#
# Module handling the internal markers for individual Bible books
#
# Copyright (C) 2010-2025 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
    Finally, call makeBookCVIndex() to index _processedLines by CV.

CHANGELOG:
    2022-06-05 reduced surplus "_addNestingMarkers ignored" messages
    2023-03-20 added "haveTables", "haveLists', and "figuresCount" discovery flags
                plus fix versification tables for introduction (chapter -1)
    2023-08-15 make more robust for handling uW encoding errors
    2023-10-14 allow more footnote and xref internal markers
    2024-01-24 add getContextVerseDataRange() function
    2024-11-13 Added a warning if text is appended to an existing line with no apparent space between words
    2025-02-25 Don't add 'intro' section if 'iex' occurs under 'c'
    2025-03-04 Insert space if it appears that we might be appending text to the end of a verse number
    2025-11-19 Give better error info for an invalid chapter number
    2026-04-22 Fixed addVerse
"""
import os
from pathlib import Path
import logging
import re
import unicodedata
import bos_books_codes_py

# BibleOrgSys imports
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, LARGE_DUMMY_VALUE
from bible_organisational_system import InternalBibleEntryList, InternalBibleEntry, InternalBibleExtra, InternalBibleExtraList, \
                                            getSmallLeadingInt
from bible_organisational_system import InternalBibleBookCVIndex, InternalBibleBookSectionIndex
from BibleOrgSys.Reference.BibleReferences import BibleAnchorReference
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

# Rust imports
from bible_organisational_system import processLines, ProcessLinesOptions, ObjectType
import usfm_markers_py


LAST_MODIFIED_DATE = '2026-04-29' # by RJH
SHORT_PROGRAM_NAME = "InternalBibleBook"
PROGRAM_NAME = "Internal Bible book handler"
PROGRAM_VERSION = '1.00'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BCV_VERSION = '1.0'

MAX_NONCRITICAL_ERRORS_PER_BOOK_NORMAL = 3
MAX_NONCRITICAL_ERRORS_PER_BOOK_VERBOSE = 5


BOS_CUSTOM_CONTENT_MARKERS = [ 'c~', 'c#', 'v=', 'v~', 'p~', 'cl¤', 'vp#' ]
"""
    c~  anything after the chapter number on a \\c line is split off into here --
            note that it can be blank (but have extras) if the chapter number is footnoted
    c#  the chapter number in the correct position to be printed
            This is usually a duplicate of the c field, but may have come from the cp field instead
            Usually only one of c or c# is used for exports
    v= the verse number (not to be printed)
            that the next field(s) (usually a section heading) logically belong together with
    v~  verse text -- anything after the verse number on a \\v line is split off into here
    p~  verse text -- anything that was on a paragraph line (e.g., \\p, \\q, \\q2, etc.) is split off into here
    cl¤ used to rename cl markers BEFORE the '\\c 1' marker --
                            represents the text for "chapter" (e.g., Psalm) to be used throughout the book
        cl markers AFTER the '\\c 1' marker remain unchanged (the text for the individual chapter/psalm heading)
    vp# used for the vp (character field) when it is copied and converted to a separate (newline) field
            This is inserted BEFORE the v (and v~) marker(s) that contained the vp (character) field.
"""

# NOTE: Don't use any of the following symbols here: = ¬ or backslashes.
BOS_PRINTABLE_MARKERS = usfm_markers_py.USFM_ALL_TITLE_MARKERS + usfm_markers_py.USFM_ALL_INTRODUCTION_MARKERS + usfm_markers_py.USFM_ALL_SECTION_HEADING_MARKERS + ['v~', 'p~'] # Should c~ and c# be in here???

# BOS_REGULAR_NESTING_MARKERS = USFM_ALL_SECTION_HEADING_MARKERS + ('c','v' ) # No need to nest s1 type markers (one line only expected)
BOS_REGULAR_NESTING_MARKERS = ['c','v']

BOS_CUSTOM_NESTING_MARKERS = [ 'headers', 'intro', 'ilist', 'chapters', 'list' ]
"""
    intro       Inserted at the start of book introductions
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""
BOS_ALL_CUSTOM_MARKERS = BOS_CUSTOM_CONTENT_MARKERS + BOS_CUSTOM_NESTING_MARKERS

BOS_ALL_CUSTOM_NESTING_MARKERS = BOS_CUSTOM_NESTING_MARKERS + ['iot']
"""
    intro       Inserted at the start of book introductions
    iot         Inserted before introduction outline (io markers) IF IT'S NOT ALREADY IN THE FILE
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""

BOS_NESTING_MARKERS = BOS_REGULAR_NESTING_MARKERS + BOS_ALL_CUSTOM_NESTING_MARKERS \
                            + usfm_markers_py.USFM_BIBLE_PARAGRAPH_MARKERS + ['ms1','ms2','ms3']

#BOS_END_MARKERS = ['¬intro', '¬iot', '¬ilist', '¬chapters', '¬c', '¬v', '¬list', ]
#for marker in USFM_BIBLE_PARAGRAPH_MARKERS: BOS_END_MARKERS.append( '¬'+marker )
#dPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(BOS_END_MARKERS), BOS_END_MARKERS )
BOS_END_MARKERS = [ f'¬{marker}' for marker in BOS_NESTING_MARKERS]
#dPrint( 'Quiet', DEBUGGING_THIS_MODULE, len(BOS_END_MARKERS), BOS_END_MARKERS );halt
# (46) ['¬c', '¬v', '¬headers', '¬intro', '¬ilist', '¬chapters', '¬list', '¬iot', '¬p', '¬pc', '¬pr',
#       '¬m', '¬mi', '¬pm', '¬pmo', '¬pmc', '¬pmr', '¬cls',
#       '¬pi','¬pi1','¬pi2','¬pi3','¬pi4', '¬ph','¬ph1','¬ph2','¬ph3','¬ph4',
#       '¬q','¬q1','¬q2','¬q3','¬q4', '¬qr', '¬qm','¬qm1','¬qm2','¬qm3','¬qm4',
#       '¬li','¬li1','¬li2','¬li3','¬li4', '¬ms1','¬ms2','¬ms3']


#BOS_MARKERS = BOS_CUSTOM_CONTENT_MARKERS + BOS_ALL_CUSTOM_NESTING_MARKERS + BOS_END_MARKERS

# "EXTRA" here means footnote type fields that are not part of the main line of text.
BOS_EXTRA_TYPES = ( 'fn', 'en', 'xr', 'fig', 'str', 'sem', 'ww', 'vp', )
BOS_EXTRA_MARKERS = ( 'f', 'fe', 'x', 'fig', 'str', 'sem', 'ww', 'vp', )
"""
    fn  footnote
    en  endnote
    xr  cross-reference
    fig figure
    str Strongs' number
    sem semantic and other translation-related markers
    vp  published verse number
"""
assert len(BOS_EXTRA_TYPES) == len(BOS_EXTRA_MARKERS)



def hasClosingPeriod( text:str ) -> bool:
    """
    Return True if the text ends with a period or something like '.)'
    """
    if not text: return False
    for period in '.።':
        if text[-1] == period: return True
        for closingPunctuation in ''')]"'”’»›''':
            if text.endswith( f'{period}{closingPunctuation}' ):
                return True
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
            if text.endswith( f'{period}{closingPunctuation}' ):
                return True
    return False
# end of hasClosingPunctuation


def cleanUWalignments( workAbbreviation:str, BBB:str, originalAlignments:list[tuple[str,str,str,str,str]] ) \
                        -> list[tuple[str,str,list[tuple[str,str,str,str,str,str,str]],str,list[tuple[str,str,str]]]]:
    """
    Cleans up the unfoldingWord alignment info for the given book

    Typical input data is:
cleanUWalignmentsL 140 TI1 1:11 'x-strong="G25960" x-lemma="κατά" x-morph="Gr,P,,,,,A,,," x-occurrence="1" x-occurrences="1" x-content="κατὰ"'
    = ' \\v 11 \\w according|x-occurrence="1" x-occurrences="1"\\w* \\w to|x-occurrence="1" x-occurrences="1"\\w*'
cleanUWalignmentsL 141 TI1 1:11 'x-strong="G35880" x-lemma="ὁ" x-morph="Gr,EA,,,,ANS," x-occurrence="1" x-occurrences="1" x-content="τὸ"'
    = '\\w the|x-occurrence="1" x-occurrences="2"\\w*'
cleanUWalignmentsL 142 TI1 1:11 'x-strong="G20980" x-lemma="εὐαγγέλιον" x-morph="Gr,N,,,,,ANS," x-occurrence="1" x-occurrences="1" x-content="εὐαγγέλιον"'
    = '\\w gospel|x-occurrence="1" x-occurrences="1"\\w*'
cleanUWalignmentsL 143 TI1 1:11 'x-strong="G35880" x-lemma="ὁ" x-morph="Gr,EA,,,,GFS," x-occurrence="1" x-occurrences="1" x-content="τῆς"|x-strong="G13910" x-lemma="δόξα" x-morph="Gr,N,,,,,GFS," x-occurrence="1" x-occurrences="1" x-content="δόξης"'
    = '\\w of|x-occurrence="1" x-occurrences="2"\\w* \\w glory|x-occurrence="1" x-occurrences="1"\\w*'
cleanUWalignmentsL 144 TI1 1:11 'x-strong="G35880" x-lemma="ὁ" x-morph="Gr,EA,,,,GMS," x-occurrence="1" x-occurrences="1" x-content="τοῦ"'
    = '\\w of|x-occurrence="2" x-occurrences="2"\\w* \\w the|x-occurrence="2" x-occurrences="2"\\w*'

    Extracts the actual data fields and gets rid of the USFM fluff.

    Returns the cleaned-up list of 5-tuples: (C,V, textList, translatedWordsString,wordsList)
        where textList contains 6-tuples: (origWord, lemma, strongs, morph, occurrence,occurrences)
        and wordsList contains 3-tuples: (transWord, occurrence,occurrences).
    """
    debuggingThisFunction = DEBUGGING_THIS_MODULE or False #(99 if BBB=='TI1' else False)
    fnPrint( debuggingThisFunction, f"cleanUWalignments( {workAbbreviation}, {BBB}, … )" )

    vPrint( 'Verbose', debuggingThisFunction, f"Cleaning {len(originalAlignments):,} {workAbbreviation} alignments…" )
    assert originalAlignments
    assert isinstance( originalAlignments, list )

    maxOriginalWords = maxTranslatedWords = 0
    cleanedAlignmentList:list[tuple[str,str,str,str]] = []
    for j, (C,V, originalLanguageTextString,translatedWordsString) in enumerate( originalAlignments, start=1 ):
        if C == '1':
            dPrint( 'Never', debuggingThisFunction, f"cleanUWalignmentsL {j} {BBB} {C}:{V} '{originalLanguageTextString}'\n    = '{translatedWordsString}'" )

        assert isinstance( C, str ) and C
        assert isinstance( V, str ) and V

        assert isinstance( originalLanguageTextString, str ) and originalLanguageTextString
        assert originalLanguageTextString.startswith( 'x-strong="' ), f"cleanUWalignmentsL {j} {BBB} {C}:{V} expected {originalLanguageTextString=} to start with x-strong="
        assert '\\w' not in originalLanguageTextString
        assert 'x-strong="' in originalLanguageTextString
        if 'x-lemma="' not in originalLanguageTextString: logging.critical( f"cleanUWalignments expected 'x-lemma' field in {workAbbreviation} {BBB} {C}:{V} {j} {originalLanguageTextString=}" )
        assert 'x-morph="' in originalLanguageTextString
        assert 'x-occurrence="' in originalLanguageTextString
        assert 'x-occurrences="' in originalLanguageTextString
        assert 'x-content="' in originalLanguageTextString

        assert isinstance( translatedWordsString, str ) and translatedWordsString
        #dPrint( 'Quiet', debuggingThisFunction, f"translatedWordsString1='{translatedWordsString}'" )
        #assert not translatedWordsString.startswith( ' ' )
        translatedWordsString = translatedWordsString.lstrip()
        assert not translatedWordsString.endswith( ' ' )

        # Remove (unnecessary here) USFM paragraph markers
        for _safetyCount in range(9999): # Keep looping as long as there's changes
            changedSomething = False
            for paragraphMarker in ('q','q1','q2','q3', 'p','m','pi','pi1'):
                if translatedWordsString.startswith( f'\\{paragraphMarker} ' ):
                    # vPrint( 'Never', debuggingThisFunction, f"             cleanUWalignments1 {BBB} {C}:{V}: Removing \\{paragraphMarker} number from '{translatedWordsString}'" )
                    translatedWordsString = translatedWordsString[len(paragraphMarker)+2:] # Remove the unwanted paragraph formatting
                    changedSomething = True
                    break
            if not changedSomething: break
        translatedWordsString = translatedWordsString.lstrip()

        while '\\v ' in translatedWordsString: # Remove the verse number
            ix = translatedWordsString.find( '\\v ' )
            assert ix != -1
            # vPrint( 'Never', debuggingThisFunction, f"             cleanUWalignments2 {BBB} {C}:{V}: Removing verse number from '{translatedWordsString}'" )
            assert translatedWordsString[ix+3].isdigit()
            ixSpace = translatedWordsString[ix+3:].find( ' ' )
            assert ixSpace != -1
            translatedWordsString = translatedWordsString[:ix] + translatedWordsString[ix+ixSpace+4:]
            # vPrint( 'Never', debuggingThisFunction, f"               cleanUWalignments3 {BBB} {C}:{V}: Removed verse number now '{translatedWordsString[:20]}'…" )
        assert '\\v' not in translatedWordsString

        if translatedWordsString.startswith( '\\q '): translatedWordsString = translatedWordsString[3:] # Handle a bug in ULT Acts 4:25

        #dPrint( 'Quiet', debuggingThisFunction, f"translatedWordsString2='{translatedWordsString}'" )
        # Note the following code fails with two leading punct chars at Rev 16:15 ("\wLook …
        if 0 and debuggingThisFunction or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
            assert translatedWordsString.startswith( '\\w ' ) \
                or ( translatedWordsString[0] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS + '—-”' # Last two to cope with bad ULT data
                        and translatedWordsString[1:].startswith( '\\w ' ) ) \
                or ( translatedWordsString[0] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS + '—-' # To cope with bad ULT data
                        and translatedWordsString[1] in BibleOrgSysGlobals.LEADING_WORD_PUNCT_CHARS + '—-'
                        and translatedWordsString[2:].startswith( '\\w ' ) )
        assert 'x-occurrence="' in translatedWordsString
        assert 'x-occurrences="' in translatedWordsString

        textCount = originalLanguageTextString.count( '|' ) + 1 # Our separator character
        if textCount > maxOriginalWords: maxOriginalWords = textCount
        #if textCount > 1 and debuggingThisFunction:
            #dPrint( 'Quiet', debuggingThisFunction, f"  This one has {textCount} original language words" )
        # Allow for x-strong, x-lemma and x-morph to be empty (originally it was just x-lemma)
        #   x-strong may or may not contain digits, e.g., 'b', 'G12345', 'H1234', 'H1234e', 'c:d:H1234'
        # When a translation has a verse bridge, x-ref tells which verse the particular source word is from
        textRE = re.compile( r'x-strong="(.*?)" x-lemma="(.*?)" x-morph="(.*?)" x-occurrence="(\d{1,3})" x-occurrences="(\d{1,3})" x-content="(.+?)"(?: x-ref="(\d{1,3}[:]\d{1,3})")?' )
        textList = []
        match =  textRE.search( originalLanguageTextString )
        while match:
            # Convert occurrence and occurrences to ints (from digit strings) as we go
            # Note that we change the order, e.g., move the word from the end to the beginning and then the lemma
            textList.append( (match.group(6), match.group(2), match.group(1),match.group(3),int(match.group(4)),int(match.group(5)),match.group(7)) )
            for xx in range(1,7): # 1..6 are expected fields (0 is entire match, 7 (x-ref) only occurs sometimes)
                if not match.group(xx):
                    logging.warning( f"Got an empty uW {workAbbreviation} alignment field at {BBB} {C}:{V} in {originalLanguageTextString}" )
            originalLanguageTextString = f'{originalLanguageTextString[:match.start()]}{originalLanguageTextString[match.end():]}'
            match =  textRE.search( originalLanguageTextString )
        if originalLanguageTextString.replace( '|', '' ):
            logging.critical( f"Got an unexpected uW {workAbbreviation} alignment field at {BBB} {C}:{V} in {originalLanguageTextString}" )
        else: assert len(textList) == textCount

        wordsCount = translatedWordsString.count( '\\w ' )
        if wordsCount > maxTranslatedWords: maxTranslatedWords = wordsCount
        twsCount = translatedWordsString.count( '\\w*' )
        if twsCount != wordsCount:
            logging.critical( f"Programming error at {BBB} {C}:{V}: {twsCount} doesn't match {wordsCount} with '{translatedWordsString}'" )
        assert twsCount == wordsCount # else mismatch between \\w and \\w* counts in string
        #dPrint( 'Never', debuggingThisFunction, f"  This one has {wordsCount} translated words" )
        wordRE = re.compile( r'\\w (.+?)\|x-occurrence="(\d{1,3})" x-occurrences="(\d{1,3})"\\w\*' )
        wordsList = []
        match =  wordRE.search( translatedWordsString )
        while match:
            for xx in range(1,4): assert match.group(xx)
            # Convert occurrence and occurrences to ints (from digit strings) as we go
            wordsList.append( (match.group(1),int(match.group(2)),int(match.group(3))) )
            #index = match.end()
            translatedWordsString = f'{translatedWordsString[:match.start()]}{match.group(1)}{translatedWordsString[match.end():]}'
            match =  wordRE.search( translatedWordsString )
        assert len(wordsList) == wordsCount

        cleanedAlignmentList.append( (C,V, textList, translatedWordsString,wordsList) )

    vPrint( 'Info', debuggingThisFunction,
f'''\nInternalBibleBook cleanUWalignments: Have {len(cleanedAlignmentList):,} alignment entries for {workAbbreviation} {BBB}
  Maximum of {maxOriginalWords} original language words in one {workAbbreviation} {BBB} entry
  Maximum of {maxTranslatedWords} translated words in one {workAbbreviation} {BBB} entry''' )
    if DEBUGGING_THIS_MODULE:
        for j, (C,V, textList, translatedWordsString,wordsList) in enumerate( cleanedAlignmentList, start=1 ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{j} {BBB} {C}:{V} {textList} '{translatedWordsString}' {wordsList}" )
            if j > 8: break

    return cleanedAlignmentList
# end of cleanUWalignments function



OUR_HEADING_MARKERS = ( 's','s1','s2','s3','s4', 'sr', 'is','is1','is2','is3','is4', 'mr', 'qa', 'qc' ) # Usually only one line
OUR_HEADING_BLOCK_MARKERS = ( 'ms','ms1','ms2','ms3','ms4' ) # Stay open for many chapters/verses
OUR_INTRO_OUTLINE_MARKERS = ( 'io','io1','io2','io3','io4' )
OUR_INTRO_LIST_MARKERS = ( 'ili','ili1','ili2','ili3','ili4' )
OUR_MAIN_TEXT_LIST_MARKERS = ( 'li','li1','li2','li3','li4' )


class InternalBibleBook:
    """
    Class to create and manipulate a single internal Bible file / book.
    The load routine (which populates self._rawLines) by calling addLine must be provided by the superclass.
    """

    def __init__( self, parameter1, BBB:str ) -> None:
        """
        Create the internal Bible book object.

        Parameters are:
            parameter1: owner of the work (e.g., My English Bible)
                but can be a string (usually only for testing)
            BBB: book reference code
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.__init__( {BBB} )" )
        self.doExtraChecking = DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag
        if isinstance( parameter1, str ):
            (logging.warning if parameter1.startswith('NoneYet') else logging.critical)( f"InternalBibleBook.constructor( {BBB!r}, {parameter1} ): Not passed a containing Bible object" )
            self.containerBibleObject = None
            self.workName = parameter1
        else:
            from BibleOrgSys.Bible import Bible
            assert isinstance( parameter1, Bible )
            self.containerBibleObject = parameter1
            #dPrint( 'Info', DEBUGGING_THIS_MODULE, f"set {BBB} cBO to {id(parameter1)} for {id(self)}" )
            self.workName = self.containerBibleObject.getAName( abbrevFirst=True )
        assert isinstance( BBB, str ), f"InternalBibleBook.__init__ {type(BBB)=} {BBB=}"
        self.BBB = BBB
        if self.doExtraChecking: assert bos_books_codes_py.is_valid_bos_book_code( self.BBB )
        self.isSingleChapterBook = bos_books_codes_py.is_single_chapter_book( self.BBB )


        self._rawLines = [] # Contains 2-tuples (marker,text) which contain the actual Bible text -- see addLine below
        self._processedFlag = self._indexedCVFlag = self._indexedSectionsFlag = False
        self.notices = [] # Contains 6-tuples (priority, message, BBB, C, V, options)
        self.checkResultsDictionary = {}
        self.checkResultsDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
        self.givenAngleBracketWarning = self.givenDoubleQuoteWarning = False

        # Options
        self.checkAddedUnitsFlag = False
        self.checkUSFMSequencesFlag = False
        self.replaceAngleBracketsFlag, self.replaceStraightDoubleQuotesFlag = True, False

        self.badMarkers, self.badMarkerCounts = [], []
        self.versificationList = self.omittedVersesList = self.combinedVersesList = self.reorderedVersesList = None
        self.versificationDict = None
        self.pntsCount = 0

        self.maxNoncriticalErrorsPerBook = MAX_NONCRITICAL_ERRORS_PER_BOOK_VERBOSE \
                        if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE \
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
            if self.sourceFilepath: result += ('\n' if result else '') + "  " + "From: " + self.sourceFilepath
        except AttributeError: pass # Not all Bibles have a separate filepath per book
        if self._processedFlag: result += ('\n' if result else '') + "  " + "Number of processed lines = " + str(len(self._processedLines))
        else: result += ('\n' if result else '') + "  " + "Number of raw lines = " + str(len(self._rawLines))
        if self.BBB and (self._processedFlag or self._rawLines) and BibleOrgSysGlobals.verbosityLevel > 1:
            result += ('\n' if result else '') + "  " + f"Deduced short book name(s) are {self.getAssumedBookNames()}"

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            if self._processedFlag: result += '\n' + str( self._processedLines )
            if self._indexedCVFlag: result += '\n' + str( self._CVIndex )
        return result
    # end of InternalBibleBook.__str__


    def __len__( self ) -> int:
        """ This method returns the number of lines in the internal Bible book object. """
        return len( self._processedLines if self._processedFlag else self._rawLines )
    # end of InternalBibleBook.__len__


    def __iter__( self ) -> InternalBibleEntry:
        """
        Yields the next processed line.

        Returns an InternalBibleEntry object.
        """
        assert self._processedFlag
        for line in self._processedLines:
            yield line
    # end of InternalBibleBook.__iter__


    def addNotice( self, priority:int, message:str, C:str, V:str, options:dict[str,any] ) -> None:
        """
        Adds a notice to self.notices and then logs it at an appropriate level.

        We use the term notice as there's not a clear distinction between errors and warnings.

        Typical fields in options (dict) include:
            type: 'load'
            filename:
            lineNumber: 1-based line number
            characterIndex: 0-character index
            excerpt:
            logger: logging.critical, logging.error, logging.warning
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.addNotice( {priority} {message} {C}:{V} {options} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert isinstance( priority, int ) and ( 0 <= priority <= 1000 )
            assert isinstance( message, str ) and message
            assert isinstance( C, str ) and C
            assert isinstance( V, str ) and V

        # Save a 6-tuple with the compulsory parameters as the first five values
        #   followed by the options dict
        self.notices.append( (priority, message, self.BBB, C, V, options) )

        if 'logger' in options and options['logger']:
            loggingFunction = options['logger']
        elif priority >= 900:
            loggingFunction = logging.critical
        elif priority >= 700:
            loggingFunction = logging.error
        else: loggingFunction = logging.warning

        logString = f"{self.BBB}_{C}:{V} {message}"
        if options: logString = f'{logString} with {options}'
        loggingFunction( logString )
    # end of InternalBibleBook.addNotice


    def addPriorityError( self, priority:int, C:str, V:str, errorString:str ) -> None:
        """
        Adds a priority error to self.checkResultsDictionary.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.addPriorityError( {priority} {C}:{V} {errorString} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert isinstance( priority, int ) and ( 0 <= priority <= 100 )
            assert isinstance( errorString, str ) and errorString
        if 'Priority Errors' not in self.checkResultsDictionary:
            self.checkResultsDictionary['Priority Errors'] = [] # Just in case getCheckResults() deleted it

        # TODO: Why did we ever have this code ???
        # Maybe to reduce data structure size, but it was confusing
        # BBB = self.BBB
        # if self.checkResultsDictionary['Priority Errors']:
        #     LastPriority, lastString, (lastBBB,lastC,lastV) = self.checkResultsDictionary['Priority Errors'][-1]
        #     if priority==LastPriority and errorString==lastString and BBB==lastBBB: # Remove unneeded repetitive information
        #         BBB = ''
        #         if C==lastC: C = ''

        self.checkResultsDictionary['Priority Errors'].append( (priority,errorString,(self.BBB,C,V)) )
    # end of InternalBibleBook.addPriorityError


    def __makeErrorRef( self, C:str, V:str ) -> str:
        """
        Makes up an error reference string consisting of the BCV reference,
            and if verbose enough, preceded by the work name.

        Returns a string.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: # includes the work name
            return f'{V!r} {self.workName} {self.BBB}:{C}'
        # else verbosityLevel is 0 or 1
        return f'{self.BBB} {C}:{V}'
    # end of InternalBibleBook.__makeErrorRef


    def addLine( self, marker:str, text:str ) -> None:
        """
        Append a (USFM-based) 2-tuple to self._rawLines.
            This is a very simple function,
                but having it allows us to have a single point in order to catch particular bugs or errors.
        """
        forceDebugHere = False
        vPrint( 'Never', forceDebugHere or DEBUGGING_THIS_MODULE,
                f"InternalBibleBook.addLine( {marker}= '{text}' ) for {self.objectTypeString} '{self.workName} …" )
        assert marker and isinstance( marker, str )

        if text and ( '\n' in text or '\r' in text ):
            (logging.warning if self.objectTypeString=='uW Notes' else logging.critical)( f"InternalBibleBook.addLine found newLine in {self.objectTypeString} text: {marker}='{text}'" )
            if forceDebugHere or BibleOrgSysGlobals.debugFlag: halt
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert not self._processedFlag
            assert marker and isinstance( marker, str )
            assert marker[0] != '\\'
            if text:
                assert isinstance( text, str )
                assert '\n' not in text and '\r' not in text

        if not ( marker in usfm_markers_py.get_newline_markers_list('Numbered') or marker in BOS_CUSTOM_CONTENT_MARKERS ):
            logging.critical( f"InternalBibleBook.addLine marker for {self.objectTypeString} not in USFM/BOS lists: {marker}={text!r}" )
            if marker in self.badMarkers:
                ix = self.badMarkers.index( marker )
                assert 0 <= ix < len(self.badMarkers)
                self.badMarkerCounts[ix] += 1
            else:
                self.badMarkers.append( marker )
                self.badMarkerCounts.append( 1 )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert marker in usfm_markers_py or marker in BOS_CUSTOM_CONTENT_MARKERS

        if marker not in BOS_CUSTOM_CONTENT_MARKERS and not usfm_markers_py.is_newline_marker( marker ):
            logging.warning( f"IBB.addLine: Not a NL marker: {marker}={text!r}" )
            if 1 or marker != 'w': # This can happen with unfoldingWord aligned Bibles
                dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self, repr(marker), repr(text) )
                if DEBUGGING_THIS_MODULE: halt # How did this happen?

        if text is None:
            (logging.warning if marker in ('b',) else logging.critical)( f"InternalBibleBook.addLine: Received {self.objectTypeString} {self.BBB} {marker}={text!r}" )
            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: halt # Programming error in the calling routine, sorry
            text = '' # Try to recover

        if text.strip() != text:
            if marker=='v' and len(text)<=4 and self.objectTypeString in ('USX',): pass
            else:
                if self.pntsCount != -1:
                    self.pntsCount += 1
                    stripLogger = logging.warning if DEBUGGING_THIS_MODULE else logging.info
                    if self.pntsCount <= self.maxNoncriticalErrorsPerBook:
                        stripLogger( f"InternalBibleBook.addLine: Possibly needed to strip whitespace {self.objectTypeString} {self.BBB} {marker}={text!r}" )
                    else: # we've reached our limit
                        stripLogger( f'Additional "Possibly needed to strip whitespace" messages suppressed for {self.workName} {self.BBB}' )
                        self.pntsCount = -1 # So we don't do this again (for this book)

        self._rawLines.append( (marker, text) )
    # end of InternalBibleBook.addLine


    def appendToLastLine( self, additionalText:str, expectedLastMarker:str|None=None ) -> None:
        """
        Append some extra text to the previous line in self._rawLines
            Doesn't add any additional spaces.
            (Used by USXXMLBibleBook.py)

        No return value.
        """
        forceDebugHere = False
        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f" InternalBibleBook.appendToLastLine( {additionalText!r}, {expectedLastMarker!r} )" )
            assert not self._processedFlag
            assert self._rawLines # Must be an existing line to append to
        if additionalText and ( '\n' in additionalText or '\r' in additionalText ):
            logging.critical( f"InternalBibleBook.appendToLastLine found newLine in {self.objectTypeString} additionalText: {expectedLastMarker}='{additionalText}'" )
            if forceDebugHere or BibleOrgSysGlobals.debugFlag: halt
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert not self._processedFlag
            assert additionalText and isinstance( additionalText, str )
            if additionalText: assert '\n' not in additionalText and '\r' not in additionalText
            if expectedLastMarker: assert isinstance( expectedLastMarker, str )

        marker, text = self._rawLines[-1] # Get the current existing line
        insertSpace = False
        if text and text[-1] not in ' *“‘(⌊—/' \
        and additionalText[0] not in ' .,?!;:”’ )⌋/\\':
            if marker=='v' and text and text.isdigit(): # Must be a verse number
                # TODO: Should we ALWAYS be inserting that space??? Probably better to fix at source
                #   Also, remember, might be appending a closing quote mark or an em dash or something that SHOULD be attached
                logging.critical( f"InternalBibleBook.appendToLastLine() inserted space where appears to be joining text after {self.workName} {self.BBB} verse number {marker} {text=} plus {additionalText=}" )
                insertSpace = True
            else:
                logging.critical( f"InternalBibleBook.appendToLastLine() appears to be joining words {self.BBB} {marker} {text=} plus {additionalText=}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"additionalText for {marker} {text!r} is {additionalText!r}" )
        if expectedLastMarker and marker!=expectedLastMarker: # Not what we were expecting
            logging.critical( f"InternalBibleBook.appendToLastLine: expected \\{expectedLastMarker} but got \\{marker}" )
        if expectedLastMarker and BibleOrgSysGlobals.debugFlag: assert marker == expectedLastMarker
        #if marker in ('v','c') and ' ' not in text: text += ' ' # Put a space after the verse or chapter number
        text = f"{text}{' ' if insertSpace else ''}{additionalText}"
        if forceDebugHere: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  newText for {marker!r} is {text!r}" )
        self._rawLines[-1] = (marker, text)
    # end of InternalBibleBook.appendToLastLine


    def addVerseSegments( self, V:str, text:str, location:str|None=None ) -> None:
        """
        Takes a text line that might optionally include
            \\NL** markers to indicate a new line.
        Splits the line at those markers, and adds the individual lines to the book.

        The optional location parameter is for better error messages.

        Currently only used by SwordBible.py

        No return value.
        """
        forceDebugHere = False
        fnPrint( DEBUGGING_THIS_MODULE, f"\nInternalBibleBook.addVerseSegments( {V!r}, {text!r}, {location!r} )" )
        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
            assert not self._processedFlag
        ourText = text # Work on a copy so we can still print the original for error messages

        for loopCounter in range( 10 ): # Do this a few times to iron every thing out
            if forceDebugHere: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, loopCounter, "LOOPSTART", repr(ourText) )
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

            for marker in usfm_markers_py.getCharacterMarkersList( expand_numberable_markers=True ):
                if f'\\{marker}' in ourText:
                    ourText = ourText.replace( f'\\{marker} \\{marker} ',f'\\{marker} ' ) # Remove double start markers
                    ourText = ourText.replace( f'\\{marker} \\NL**', f'\\NL**\\{marker} ' ) # Put character start markers after NL
                    ourText = ourText.replace( f'\\{marker}*\\{marker}*',f'\\{marker}*' ) # Remove double end markers
                    ourText = ourText.replace( f'\\NL**\\{marker}*', f'\\{marker}*\\NL**' ) # Put character end markers before NL
                    ourText = ourText.replace( f'\\p\\{marker}*', f'\\{marker}*\\p' ) # Put character end markers before NL

            for marker in usfm_markers_py.get_newline_markers_list( 'Combined' ):
                if f'\\{marker}' in ourText:
                    #ourText = ourText.replace( f' \\{marker}', f'\\{marker}' ) # Delete useless spaces at ends of lines
                    ourText = ourText.replace( f'\\{marker} \\p', '\\p' ) # Delete useless markers
                    ourText = ourText.replace( f'\\{marker}\\p', '\\p' ) # Delete useless markers

            #ourText = ourText.replace( '\\s1 \\p', '\\p' ) # Delete useless s1 heading marker
            ourText = ourText.replace( '\\wj\\NL**\\p\\NL**', '\\NL**\\p\\NL**\\wj ' ) # Start wj AFTER paragraph marker
            ourText = ourText.replace( '\\wj\\NL**\\q1 ', '\\NL**\\q1 \\wj ' ) # Start wj AFTER paragraph marker
            ourText = ourText.replace( '\\wj\\NL**\\q2 ', '\\NL**\\q2 \\wj ' ) # Start wj AFTER paragraph marker
            #ourText = ourText.replace( '\\NL**\\wj*', '\\wj*\\NL**' )
            #ourText = ourText.replace( '\\tl \\tl ','\\tl ' ).replace( '\\tl*\\tl*','\\tl*' ) # From both highlight and foreign fields
            if forceDebugHere: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "GGGGGGGGGG", repr(ourText) )
            ourText = ourText.strip()
            if ourText == savedText: break # we didn't change anything
        if forceDebugHere: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "HHHHHHHH", repr(ourText) )

        writtenV = False
        if '\\NL**' in ourText: # We need to break the original line into different USFM markers
            if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nMessing with segments: {ourText!r}\n  from {text!r}{('\n  from '+location) if location else ''}" )
            segments = ourText.split( '\\NL**' )
            if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
                assert len(segments) >= 2
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nSegments (split by \\NL**):", segments )

            leftovers = ''
            for segment in segments:
                if segment and segment[0] == '\\':
                    bits = segment.split( None, 1 )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " bits", bits )
                    marker = bits[0][1:]
                    if len(bits) == 1:
                        #if bits[0] in ('\\p','\\b'):
                        if usfm_markers_py.is_newline_marker( marker ):
                            #if C==1 and V==1 and not appendedCFlag: self.addLine( 'c', str(C) ); appendedCFlag = True
                            self.addLine( marker, '' )
                        else:
                            logging.error( f"It seems that we had a blank {bits[0]!r} field \nin {ourText!r}" )
                            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: halt
                    else:
                        assert len(bits) == 2
                        if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
                            if location: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nHere @ {location}" )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ourText", repr(ourText) )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "seg", repr(segment) )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "segments:", segments )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bits", bits )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "marker", marker )
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "leftovers", repr(leftovers) )
                            #if marker[-1] == '*': marker = marker[:-1]
                            assert marker in ( 'id', 'toc1','toc2','toc3', 'mt1','mt2','mt3', 'ip', 'iot','io1','io2','io3','io4',
                                            's1','s2','s3','s4', 'qa', 'r','sr','sp','d', 'q1','q2','q3','q4', 'v', 'li1','li2','li3','li4', 'pc', ) \
                                or marker in ( 'f','x', 'bk', 'wj', 'nd', 'add', 'k','tl','sig', 'bd','bdit','it','em','sc', 'str', ) # These ones are character markers which can start a new line
                        if usfm_markers_py.is_newline_marker( marker ):
                            self.addLine( marker, bits[1] )
                        elif not writtenV:
                            self.addLine( 'v', f'{V} {segment}' )
                            writtenV = True
                        else: leftovers += segment
                else: # What is segment is blank (\\NL** at end of ourText)???
                    #if C==1 and V==1 and not appendedCFlag: self.addLine( 'c', str(C) ); appendedCFlag = True
                    if not writtenV:
                        self.addLine( 'v', f'{V} {leftovers+segment}' )
                        writtenV = True
                    else:
                        self.addLine( 'v~', leftovers+segment )
                    leftovers = ''

            if leftovers:
                if forceDebugHere or ( BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE ):
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nOriginalText", repr(text) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nourText", repr(ourText) )
                #logging.critical( f"Had leftovers {repr(leftovers)}" )
                self.appendToLastLine( leftovers )

        elif ourText: # No newlines in result -- just add the simple line
            self.addLine( 'v', V + ' ' + ourText )
    # end of InternalBibleBook.addVerseSegments


    # (Removed _processLineFix as it is now implemented in Rust)
    # (Removed addVerseStartMarkers as it is now implemented in Rust)


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
        newLines:list[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
        lastMarker = lastText = None
        C, V = '-1', '-1' # So first/id line starts at -1:0
        for j,(marker,text) in enumerate( self._rawLines ):
            # Keep track of where we are
            #if marker == 'c': C, V = text, '0'
            #elif marker == 'v': V = text

            if lastMarker in USFM_BIBLE_PARAGRAPH_MARKERS and not lastText and marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                #if self.BBB=='JHN':
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"zap: {self.BBB} {C}:{V} lines: {lastMarker}={lastText} {marker}={text}" )
                lastMarker = None

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None: newLines.append( (lastMarker,lastText) ) # Save the very last line
        self._rawLines = newLines # replace the old set
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'RO-1', len(self._rawLines) )

        # For OSIS, change lines like:
        #    1/ v = 2 Text of verse 2.
        #    2/ v = 3
        #    3/ p = Text of verse 3.
        # to
        #    1/ v = 2 Text of verse 2.
        #    2/ p = ''
        #    2/ v = 3
        #    3/ v~ = Text of verse 3.
        newLines:list[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
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

            #nextMarker, nextText = self._rawLines[j+1] if j<lastJ else (None,None)

            if lastMarker=='v' and marker in USFM_BIBLE_PARAGRAPH_MARKERS and text:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"increase: {self.BBB} {C}:{V} lines: {lastMarker}={lastText} {marker}={text}" )
                newLines.append( (marker,'') ) # Put the new blank paragraph marker before the v
                marker = 'v~' # Change the p marker to v~

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None: newLines.append( (lastMarker,lastText) ) # Save the very last line
        self._rawLines = newLines # replace the old set
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'RO-2', len(self._rawLines) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.BBB, "RL" )
        #for j in range( 50 ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "", j, self._rawLines[j] )

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
        newLines:list[InternalBibleEntry] = [] # Contains more-processed tuples which contain the actual Bible text -- see below
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

            #nextMarker, nextText = self._rawLines[j+1] if j<lastJ else (None,None)

            if lastMarker in USFM_BIBLE_PARAGRAPH_MARKERS and not lastText:
                if marker in USFM_BIBLE_PARAGRAPH_MARKERS and not text:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"reduce: {self.BBB} {C}:{V} lines: {lastMarker}={lastText} {marker}={text}" )
                    lastMarker = None
                if marker=='c':
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"remove: {self.BBB} {C}:{V} lines: {lastMarker}={lastText} {marker}={text}" )
                    lastMarker = None

            # Always save one line behind
            if lastMarker is not None: newLines.append( (lastMarker,lastText) )
            lastMarker, lastText = marker, text

        if lastMarker is not None \
        and (lastText or lastMarker not in USFM_BIBLE_PARAGRAPH_MARKERS): # Don't write a blank p type marker at the end of the book
            newLines.append( (lastMarker,lastText) )
        self._rawLines = newLines # replace the old set
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'RO-3', len(self._rawLines) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.BBB, "RL" )
        #for j in range( 50 ): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "", j, self._rawLines[j] )
    # end of InternalBibleBook.processLines.reorderRawOsisLines


    def displayProcessedLines( self, heading:str="displayProcessedLines" ) -> None:
        """
        This function is mostly used for debugging.
        """
        print( f"{heading} -- have {len(self._processedLines)} processLines:" )
        for n,processedBibleEntry in enumerate( self._processedLines, start=1 ):
            marker, originalMarker, text, _extras = processedBibleEntry.getMarker(), processedBibleEntry.getOriginalMarker(), processedBibleEntry.getCleanText(), processedBibleEntry.getExtras()
            print(f" {n:4} {marker=} {originalMarker=} {text=}")
        print("-------------")
    # end of InternalBibleBook.processLines.displayProcessedLines


    def processLines( self ) -> None:
        """
        Move notes out of the text into a separate area.
            Also, splits lines if a paragraph marker appears within a line.

            Uses self._rawLines and fills self._processedLines.

        Also creates the CV index (but NOT the section index)
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"Processing {self.objectNameString} {self.objectTypeString} {self.workName!r} {self.BBB} {len(self._rawLines):,} lines…" )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
            assert self._rawLines # or else the book was totally blank
            assert not self._processedFlag # Can only do it once

        if self.objectTypeString == 'OSIS': self.reorderRawOsisLines()

        objectTypeMap = {
            'USFM2': ObjectType.Usfm2,
            'USFM3': ObjectType.Usfm3,
            'USX': ObjectType.Usx,
            'OSIS': ObjectType.Osis,
            'SwordBibleModule': ObjectType.Sword,
        }
        rustObjectType = objectTypeMap.get(self.objectTypeString, ObjectType.Other)

        options = ProcessLinesOptions(
            replace_angle_brackets=self.replaceAngleBracketsFlag,
            replace_straight_double_quotes=self.replaceStraightDoubleQuotesFlag,
            strict_checking=BibleOrgSysGlobals.strictCheckingFlag,
            object_type=rustObjectType
        )

        # Call Rust implementation
        self._processedLines = processLines(self._rawLines, self.BBB, self.workName, options)

        # # Create files for tests for new Rust implementation
        # if 'OET' in self.workName:
        #     with open( f'{self.workName}_summary.text', 'at', encoding='utf-8') as debugOutputFile:
        #         debugOutputFile.write( f"{self.BBB} {len(self._rawLines)=} {len(self._processedLines)=}\n" )
        #     with open( f'{self.workName}_{self.BBB}_rawLines.txt', 'wt', encoding='utf-8' ) as debugOutputFile:
        #         debugOutputFile.write( f"{self.workName} {self.BBB} {len(self._rawLines)}\n" )
        #         for n, (marker,text) in enumerate( self._rawLines ):
        #             debugOutputFile.write( f"{n} {marker=} {text=}\n")
        #     with open( f'{self.workName}_{self.BBB}_processedLines.txt', 'wt', encoding='utf-8' ) as debugOutputFile:
        #         debugOutputFile.write( f"{self.workName} {self.BBB} {len(self._processedLines)}\n" )
        #         for n, processedLine in enumerate( self._processedLines ):
        #             debugOutputFile.write( f"{n} {processedLine}\n")

        # Get rid of data that we don't need
        del self._rawLines # if short of memory
        try: del self.XMLTree # for xml Bible types (some Bible books caused a segfault when pickled with this data)
        except AttributeError: pass # we didn't have an xml tree to delete

        self._processedFlag = True
        self.makeBookCVIndex()
    # end of InternalBibleBook.processLines

    def makeBookCVIndex( self ) -> None:
        """
        Index the InternalBibleBook processed lines InternalBibleEntryList for faster reference.

        Works by calling the Rust implementation
            to update self._CVIndex
        """
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert self._processedFlag
            assert not self._indexedCVFlag
        if self._indexedCVFlag: return # Can only do it once

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"Indexing {self.objectNameString} {self.BBB!r} {self.workName} text…" )
        self._CVIndex = InternalBibleBookCVIndex( self.workName, self.BBB )
        self._CVIndex.makeBookCVIndex( self._processedLines )

        #if self.BBB=='GEN':
            #for j, entry in enumerate( self._processedLines):
                #cleanText = entry.getCleanText()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, entry.getMarker(), cleanText[:60] + ('' if len(cleanText)<60 else '…') )
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
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{C}:{V}={ALX.getEntryIndex()},{ALX.getEntryCount()},{ALX.getContextList()}", end='  ' )

        self._indexedCVFlag = True
    # end of InternalBibleBook.makeBookCVIndex


    def _makeBookSectionIndex( self ) -> None:
        """
        Index the InternalBibleBook processed lines InternalBibleEntryList for faster reference.

        Works by calling the Rust implementation
            to update self._SectionIndex

        Most of the time it's straightforward, but we also consolidate some of the headings.
        """
        from BibleOrgSys.Bible import Bible
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook._makeBookSectionIndex() for {self.BBB}" )
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "_makeBookSectionIndex", id(self.containerBibleObject) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert self._processedFlag
            assert not self._indexedSectionsFlag
        if self._indexedSectionsFlag:
            #dPrint( 'Info', DEBUGGING_THIS_MODULE, "Already done InternalBibleBook._makeBookSectionIndex!" )
            return # Can only do it once

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"Indexing {self.objectNameString} {self.BBB!r} {self.workName} text…" )
        assert isinstance( self.containerBibleObject, Bible )
        assert len(self.containerBibleObject.books)
        self._SectionIndex = InternalBibleBookSectionIndex( self.workName, self.BBB )
        self._SectionIndex.makeBookSectionIndex( self._processedLines )

        self._indexedSectionsFlag = True
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Finished InternalBibleBook._makeBookSectionIndex() for {self.BBB}" )
    # end of InternalBibleBook._makeBookSectionIndex


    def debugPrint( self ) -> None:
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.debugPrint: {self.BBB}" )
        numLines = 50
        if '_rawLines' in self.__dict__:
            for j in range( min( numLines, len(self._rawLines) ) ):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f" Raw {j}: {self._rawLines[j][0]} = {self._rawLines[j][1]!r}" )
        for j in range( min( numLines, len(self._processedLines) ) ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f" Proc {j}: {self._processedLines[j][0]}{f'({self._processedLines[j][1]})' if self._processedLines[j][1]!=self._processedLines[j][0] else ''} = {self._processedLines[j][2]!r}" )
    # end of InternalBibleBook.debugPrint


    def validateMarkers( self ) -> None:
        """
        Validate the loaded book.
        This is usually called from loadBook() in the various Bible importers.

        This does a quick check for major SFM errors. It is not as thorough as checkSFMs below.
        """
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'validateMarkers'" )
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            assert self._processedLines

        # Call Rust implementation
        from bible_organisational_system import validateMarkers
        rustResults = validateMarkers(self._processedLines, self.BBB, self.workName, BibleOrgSysGlobals.strictCheckingFlag)

        validationErrors = rustResults['validation_errors']
        for p, msg, (b, c, v) in rustResults['priority_errors']:
            self.addPriorityError(p, c, v, msg)

        if validationErrors:
            if 'Validation Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Validation Errors'] = []
            self.checkResultsDictionary['Validation Errors'].extend(validationErrors)
    # end of InternalBibleBook.validateMarkers


    def getField( self, fieldName:str ) -> str:
        """
        Extract a SFM field contents from the loaded book.

        Returns the contents of the first field in the book with a marker match.
        """
        if not self._processedFlag:
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"InternalBibleBook {self.BBB}: calling processLines from 'getField'" )
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            assert self._processedLines
            assert fieldName and isinstance( fieldName, str )
        adjFieldName = fieldName if fieldName in ('cl¤',) else usfm_markers_py.to_standard_marker( fieldName )

        for entry in self._processedLines:
            if entry.getMarker() == adjFieldName:
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert not entry.getExtras() # We're maybe losing some info here
                return entry.getText()
    # end of InternalBibleBook.getField


    def setField( self, fieldName:str, newValue:str ) -> bool:
        """
        Replace the contents of an existing SFM field in the loaded book.
        """
        if not self._processedFlag:
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"InternalBibleBook {self.BBB}: calling processLines from 'setField'" )
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            assert self._processedLines
            assert fieldName and isinstance( fieldName, str )
        adjFieldName = fieldName if fieldName in ('cl¤',) else usfm_markers_py.to_standard_marker( fieldName )

        for entry in self._processedLines:
            assert isinstance( entry, InternalBibleEntry )
            if entry.getMarker() == adjFieldName:
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert not entry.getExtras() # We're maybe losing some info here
                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"InternalBibleBook.setField replace {self.BBB} '{entry.getText()}' with '{newValue}'" )
                entry.setCleanText( newValue )
                return True
        return False
    # end of InternalBibleBook.setField


    def getAssumedBookNames( self ) -> list[str]:
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
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBook.getAssumedBookNames()" )
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'getAssumedBookNames'" ) # This is usually the first call from the Bible Drop Box
            self.processLines()
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            assert self._processedLines
        results = []

        toc1Field = self.getField( 'toc1' ) # Long table of contents text
        if toc1Field:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got toc1 of", repr(toc1Field) )
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
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got mt1 of", repr(mt1) )
                if mt1 not in results: results.append( mt1 )

        toc2Field = self.getField( 'toc2' ) # Short table of contents text
        if toc2Field:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got toc2 of", repr(toc2Field) )
            #if toc2Field.isupper(): field = toc2Field.title()
            results.append( toc2Field )
            self.shortTOCName = toc2Field
        elif self.containerBibleObject is not None and self.BBB+'ShortName' in self.containerBibleObject.settingsDict:
            self.shortTOCName = self.containerBibleObject.settingsDict[self.BBB+'ShortName']
            results.append( self.shortTOCName )

        toc3Field = self.getField( 'toc3' ) # Bookname abbreviation
        if toc3Field:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got toc3 of", repr(toc3Field) )
            #if toc3Field.isupper(): toc3Field = toc3Field.title()
            results.append( toc3Field )
            self.booknameAbbreviation = toc3Field
        elif self.containerBibleObject is not None and self.BBB+'Abbreviation' in self.containerBibleObject.settingsDict:
            self.booknameAbbreviation = self.containerBibleObject.settingsDict[self.BBB+'Abbreviation']
            results.append( self.booknameAbbreviation )

        clField = self.getField( 'cl¤' ) # Chapter label for whole book (cl before ch.1 -> cl¤ in _processLine)
        if clField:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got cl of", repr(clField) )
            self.chapterLabel = clField

        if not results: # no helpful fields in file -- just use an English name
            results.append( bos_books_codes_py.get_english_name_nr( self.BBB ) )
        self.assumedBookName = results[0]
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Got assumedBookName of", repr(self.assumedBookName) )

        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 3: # Print our level of confidence
        #    if header is not None and header==mt1: assert bookName == header; vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getBookName: header and main title are both {bookName!r}" )
        #    elif header is not None and mt1 is not None: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getBookName: header {header!r} and main title {mt1!r} are both different so selected {bookName!r}" )
        #    elif header is not None or mt1 is not None: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getBookName: only have one of header {header!r} or main title {mt1!r}" )
        #    else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getBookName: no header or main title so used English book name {bookName!r}" )
        if (BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel > 3: # Print our level of confidence
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Assumed bookname(s) of {results} for {self.BBB}" )

        return results
    # end of InternalBibleBook.getAssumedBookNames


    def getVersification( self ):
        """
        Get the versification of the book into four lists of (C, V) tuples.
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
            The third list contains an entry for all combined verses in the book.
            The fourth list contains an entry for all reordered verse in the book.
        Note that all chapter and verse values are returned as strings not integers
            (to copy with weird CV schemes in some of the less common Bible books)
        """
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'getVersification'" )
            self.processLines()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert self._processedLines

        # Call Rust implementation
        from bible_organisational_system import getVersification
        rustResults = getVersification(self._processedLines, self.BBB, self.workName)

        versification, omittedVerses, combinedVerses, reorderedVerses = rustResults['versification']
        versificationErrors = rustResults['errors']

        if versificationErrors: self.checkResultsDictionary['Versification Errors'] = versificationErrors
        return versification, omittedVerses, combinedVerses, reorderedVerses
    # end of InternalBibleBook.getVersification


    def getVersificationIfNecessary( self ) -> None:
        """
        Obtain the versification for this book if we haven't done it already.

        Stores it in self.versification and self.missingVersesList
        """
        fnPrint( DEBUGGING_THIS_MODULE, "getVersificationIfNecessary()" )
        if self.versificationList is None:
            assert self.omittedVersesList is None and self.combinedVersesList is None and self.reorderedVersesList is None # also
            versificationResult = self.getVersification()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.BBB, versificationResult )
            if versificationResult is None:
                logging.critical( "getVersificationIfNecessary() got nothing!" )
                if DEBUGGING_THIS_MODULE: why_no_versification_result
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
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"_discover() for {self.BBB}" )
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'discover'" )
            self.processLines()
        if BibleOrgSysGlobals.debugFlag: assert self._processedLines
        if not self._indexedCVFlag:
            self.makeBookCVIndex()

        vPrint( 'Never', DEBUGGING_THIS_MODULE, f"InternalBibleBook._discover() for {self.BBB} using Rust…" )
        
        rustResults = self._CVIndex.discover()
        bkDict = rustResults.to_dict()

        return bkDict
    # end of InternalBibleBook._discover
    # end of InternalBibleBook._discover


    def getAddedUnits( self ):
        """
        Get the units added to the text of the book including paragraph breaks, section headings, and section references.
        Note that all chapter and verse values are returned as strings not integers.
        """
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'getAddedUnits'" )
            self.processLines()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert self._processedLines

        # Call Rust implementation
        from bible_organisational_system import getAddedUnits
        rustResults = getAddedUnits(self._processedLines, self.BBB)

        paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = rustResults['added_units']
        addedUnitErrors = rustResults['errors']

        if addedUnitErrors: self.checkResultsDictionary['Added Unit Errors'] = addedUnitErrors
        # paragraphReferences is now a list of 3-tuples (chapter, verse, suffix) - convert back if needed, 
        # but the current Python logic seems to handle them fine.
        return paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus
    # end of InternalBibleBook.getAddedUnits


    def doCheckAddedUnits( self, typicalAddedUnitData, severe:bool=False ) -> None:
        """
        Checkthe units added to the text of the book including paragraph breaks, section headings, and section references.
        """
        typicalParagraphs, typicalQParagraphs, typicalSectionHeadings, typicalSectionReferences, typicalWordsOfJesus = typicalAddedUnitData
        paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = self.getAddedUnits() # For this object

        addedUnitNotices = []
        if self.BBB in typicalParagraphs:
            for reference in typicalParagraphs[self.BBB]:
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalParagraphs[self.BBB][reference]
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in paragraphReferences:
                    if typical == 'F':
                        addedUnitNotices.append( f"{self.BBB} {C} Paragraph break is less common after v{V}" )
                        logging.info( f"Paragraph break is less common after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 17, C, V, "Less common to have a paragraph break after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, "Less common to have a paragraph break after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( f"{self.BBB} {C} Paragraph break normally inserted after v{V}" )
                        logging.info( f"Paragraph break normally inserted after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 27, C, V, "Paragraph break normally inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, "Paragraph break often inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Most", self.BBB, reference, typical, present )
            for reference in paragraphReferences: # now check for ones in this book but not typically there
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalParagraphs[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( f"{self.BBB} {C} Paragraph break is unusual after v{V}" )
                    logging.info( f"Paragraph break is unusual after v{V} in chapter {C} of {self.BBB}" )
                    self.addPriorityError( 37, C, V, "Unusual to have a paragraph break after field" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Weird paragraph after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( f"{self.BBB} has no paragraph info available" )
            logging.info( f"{self.BBB} No paragraph info available" )
            self.addPriorityError( 3, '-', '-', f"No paragraph info for {self.BBB!r} book" )
        if addedUnitNotices:
            if 'Added Formatting' not in self.checkResultsDictionary: self.checkResultsDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.checkResultsDictionary['Added Formatting']['Possible Paragraphing Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalQParagraphs:
            for entry in typicalQParagraphs[self.BBB]:
                reference, level = entry
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalQParagraphs[self.BBB][entry]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, C, V, level, typical )
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in qReferences:
                    if typical == 'F':
                        addedUnitNotices.append( f"{self.BBB} {C} Quote Paragraph is less common after v{V}" )
                        logging.info( f"Quote Paragraph is less common after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 17, C, V, "Less common to have a Quote Paragraph after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, "Less common to have a Quote Paragraph after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( f"{self.BBB} {C} Quote Paragraph normally inserted after v{V}" )
                        logging.info( f"Quote Paragraph normally inserted after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 27, C, V, "Quote Paragraph normally inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, "Quote Paragraph often inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Most", self.BBB, reference, typical, present )
            for reference in qReferences: # now check for ones in this book but not typically there
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalQParagraphs[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( f"{self.BBB} {C} Quote Paragraph is unusual after v{V}" )
                    logging.info( f"Quote Paragraph is unusual after v{V} in chapter {C} of {self.BBB}" )
                    self.addPriorityError( 37, C, V, "Unusual to have a Quote Paragraph after field" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Weird qParagraph after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( f"{self.BBB} has no quote paragraph info available" )
            logging.info( f"{self.BBB} No quote paragraph info available" )
            self.addPriorityError( 3, '-', '-', f"No quote paragraph info for {self.BBB!r} book" )
        if addedUnitNotices:
            if 'Added Formatting' not in self.checkResultsDictionary: self.checkResultsDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.checkResultsDictionary['Added Formatting']['Possible Indenting Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalSectionHeadings:
            for entry in typicalSectionHeadings[self.BBB]:
                reference, level = entry
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalSectionHeadings[self.BBB][entry]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, C, V, level, typical )
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in sectionHeadings:
                    if typical == 'F':
                        addedUnitNotices.append( f"{self.BBB} {C} Section Heading is less common after v{V}" )
                        logging.info( f"Section Heading is less common after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 17, C, V, "Less common to have a Section Heading after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, "Less common to have a Section Heading after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( f"{self.BBB} {C} Section Heading normally inserted after v{V}" )
                        logging.info( f"Section Heading normally inserted after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 27, C, V, "Section Heading normally inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, "Section Heading often inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Most", self.BBB, reference, typical, present )
            for entry in sectionHeadings: # now check for ones in this book but not typically there
                reference, level, text = entry
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if (reference,level) not in typicalSectionHeadings[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( f"{self.BBB} {C} Section Heading is unusual after v{V}" )
                    logging.info( f"Section Heading is unusual after v{V} in chapter {C} of {self.BBB}" )
                    self.addPriorityError( 37, C, V, "Unusual to have a Section Heading after field" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Weird section heading after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( f"{self.BBB} has no section heading info available" )
            logging.info( f"{self.BBB} No section heading info available" )
            self.addPriorityError( 3, '-', '-', f"No section heading info for {self.BBB!r} book" )
        if addedUnitNotices:
            if 'Added Formatting' not in self.checkResultsDictionary: self.checkResultsDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.checkResultsDictionary['Added Formatting']['Possible Section Heading Errors'] = addedUnitNotices

        addedUnitNotices = []
        if self.BBB in typicalSectionReferences:
            for reference in typicalSectionReferences[self.BBB]:
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                C, V = reference[0], reference[1]
                if len(reference)==3: V += reference[2] # append the suffix
                typical = typicalSectionReferences[self.BBB][reference]
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, C, V, typical )
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert typical in ('A','S','M','F')
                if reference in sectionReferences:
                    if typical == 'F':
                        addedUnitNotices.append( f"{self.BBB} {C} Section Reference is less common after v{V}" )
                        logging.info( f"Section Reference is less common after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 17, C, V, "Less common to have a Section Reference after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Surprise", self.BBB, reference, typical, present )
                    elif typical == 'S' and severe:
                        self.addPriorityError( 3, C, V, "Less common to have a Section Reference after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Yeah", self.BBB, reference, typical, present )
                else: # we didn't have it
                    if typical == 'A':
                        addedUnitNotices.append( f"{self.BBB} {C} Section Reference normally inserted after v{V}" )
                        logging.info( f"Section Reference normally inserted after v{V} in chapter {C} of {self.BBB}" )
                        self.addPriorityError( 27, C, V, "Section Reference normally inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All", self.BBB, reference, typical, present )
                    elif typical == 'M' and severe:
                        self.addPriorityError( 15, C, V, "Section Reference often inserted after field" )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Most", self.BBB, reference, typical, present )
            for entry in sectionReferences: # now check for ones in this book but not typically there
                reference, text = entry
                if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert 2 <= len(reference) <= 3
                if reference not in typicalSectionReferences[self.BBB]:
                    C, V = reference[0], reference[1]
                    if len(reference)==3: V += reference[2] # append the suffix
                    addedUnitNotices.append( f"{self.BBB} {C} Section Reference is unusual after v{V}" )
                    logging.info( f"Section Reference is unusual after v{V} in chapter {C} of {self.BBB}" )
                    self.addPriorityError( 37, C, V, "Unusual to have a Section Reference after field" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Weird Section Reference after", self.BBB, reference )
        else: # We don't have any info for this book
            addedUnitNotices.append( f"{self.BBB} has no section reference info available" )
            logging.info( f"{self.BBB} No section reference info available" )
            self.addPriorityError( 3, '-', '-', f"No section reference info for {self.BBB!r} book" )
        if addedUnitNotices:
            if 'Added Formatting' not in self.checkResultsDictionary: self.checkResultsDictionary['Added Formatting'] = {} # So we hopefully get the most important errors first
            self.checkResultsDictionary['Added Formatting']['Possible Section Reference Errors'] = addedUnitNotices
    # end of InternalBibleBook.doCheckAddedUnits


    def doCheckSFMs( self, discoveryDict ) -> None:
        """
        Runs a number of comprehensive checks on the USFM codes in this Bible book.
        """
        from bible_organisational_system import checkBook, CheckOptions, DiscoveryFlags
        
        discoveryFlags = DiscoveryFlags(
            partly_done=discoveryDict.get('partlyDone', False) if discoveryDict else False,
            percentage_progress=discoveryDict.get('percentageProgress', 0.0) if discoveryDict else 0.0,
            seems_finished=discoveryDict.get('seemsFinished', False) if discoveryDict else False,
            have_main_headings=discoveryDict.get('haveMainHeadings', False) if discoveryDict else False,
            have_introductory_text=discoveryDict.get('haveIntroductoryText', False) if discoveryDict else False
        )
        
        options = CheckOptions()
        options.check_sfms = True
        options.check_words = True
        options.check_headings = True
        options.check_introduction = True
        options.check_notes = True
        options.check_speech_marks = True
        
        rustResults = checkBook(self._processedLines, self.BBB, self.workName, options, discoveryFlags)
        
        # Process results
        for p, msg, (b, c, v) in rustResults['priority_errors']:
            self.addPriorityError(p, c, v, msg)
            
        if rustResults['newline_marker_errors']:
            if 'Newline Marker Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Newline Marker Errors'] = []
            self.checkResultsDictionary['Newline Marker Errors'].extend(rustResults['newline_marker_errors'])
            
        if rustResults['internal_marker_errors']:
            if 'Internal Marker Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Internal Marker Errors'] = []
            self.checkResultsDictionary['Internal Marker Errors'].extend(rustResults['internal_marker_errors'])
            
        if rustResults['speech_mark_errors']:
            if 'Speech Mark Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Speech Mark Errors'] = []
            self.checkResultsDictionary['Speech Mark Errors'].extend(rustResults['speech_mark_errors'])
            
        if rustResults['word_errors']:
            if 'Word Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Word Errors'] = []
            self.checkResultsDictionary['Word Errors'].extend(rustResults['word_errors'])
            
        if rustResults['heading_errors']:
            if 'Heading Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Heading Errors'] = []
            self.checkResultsDictionary['Heading Errors'].extend(rustResults['heading_errors'])
            
        if rustResults['introduction_errors']:
            if 'Introduction Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Introduction Errors'] = []
            self.checkResultsDictionary['Introduction Errors'].extend(rustResults['introduction_errors'])
            
        if rustResults['note_marker_errors']:
            if 'Note Marker Errors' not in self.checkResultsDictionary:
                self.checkResultsDictionary['Note Marker Errors'] = []
            self.checkResultsDictionary['Note Marker Errors'].extend(rustResults['note_marker_errors'])

        if rustResults['newline_marker_counts']:
            if 'USFMs' not in self.checkResultsDictionary: self.checkResultsDictionary['USFMs'] = {}
            self.checkResultsDictionary['USFMs']['All Newline Marker Counts'] = rustResults['newline_marker_counts']
            self.checkResultsDictionary['USFMs']['All Newline Marker Counts']['Total'] = sum(rustResults['newline_marker_counts'].values())
            
        if rustResults['internal_marker_counts']:
            if 'USFMs' not in self.checkResultsDictionary: self.checkResultsDictionary['USFMs'] = {}
            self.checkResultsDictionary['USFMs']['All Text Internal Marker Counts'] = rustResults['internal_marker_counts']
            self.checkResultsDictionary['USFMs']['All Text Internal Marker Counts']['Total'] = sum(rustResults['internal_marker_counts'].values())
            
        if rustResults['note_marker_counts']:
            if 'USFMs' not in self.checkResultsDictionary: self.checkResultsDictionary['USFMs'] = {}
            self.checkResultsDictionary['USFMs']['All Footnote and Cross-Reference Internal Marker Counts'] = rustResults['note_marker_counts']
            self.checkResultsDictionary['USFMs']['All Footnote and Cross-Reference Internal Marker Counts']['Total'] = sum(rustResults['note_marker_counts'].values())
            
        if rustResults['functional_counts']:
            if 'USFMs' not in self.checkResultsDictionary: self.checkResultsDictionary['USFMs'] = {}
            self.checkResultsDictionary['USFMs']['Functional Marker Counts'] = rustResults['functional_counts']

    def doCheckCharacters( self, discoveryDict=None ) -> None:
        pass # Consolidated into doCheckSFMs
        
    def doCheckSpeechMarks( self ) -> None:
        pass # Consolidated into doCheckSFMs
        
    def doCheckWords( self, discoveryDict=None ) -> None:
        pass # Consolidated into doCheckSFMs
        
    def doCheckHeadings( self, discoveryDict ) -> None:
        pass # Consolidated into doCheckSFMs
        
    def doCheckIntroduction( self ) -> None:
        pass # Consolidated into doCheckSFMs
        
    def doCheckNotes( self, discoveryDict ) -> None:
        pass # Consolidated into doCheckSFMs

    def checkBook( self, discoveryDict=None, typicalAddedUnitData=None ) -> None:
        """
        Runs a number of checks on the book and returns the error dictionary.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "checkBook()" )
        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'checkBook'" )
            self.processLines()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: assert self._processedLines

        # Call the consolidated check which uses Rust
        self.doCheckSFMs( discoveryDict )

        if self.checkAddedUnitsFlag:
            if typicalAddedUnitData is None: # Get our recommendations for added units
                import pickle
                folder = os.path.join( os.path.dirname(__file__), 'DataFiles/', 'ScrapedFiles/' ) # Relative to module, not cwd
                filepath = os.path.join( folder, "AddedUnitData.pickle" )
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Importing from {filepath}…" )
                with open( filepath, 'rb' ) as pickleFile:
                    typicalAddedUnitData = pickle.load( pickleFile )
            self.doCheckAddedUnits( typicalAddedUnitData )
    # end of InternalBibleBook.checkBook


    def getCheckResults( self ) -> dict:
        """
        Returns the checklist dictionary for the book.
        """
        if 'Priority Errors' in self.checkResultsDictionary and not self.checkResultsDictionary['Priority Errors']:
            self.checkResultsDictionary.pop( 'Priority Errors' ) # Remove empty dictionary entry if unused
        return self.checkResultsDictionary
    # end of InternalBibleBook.getCheckResults


    def getNumChapters( self ) -> int:
        """
        Returns the number of chapters (int) in this book.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "getNumChapters()" )

        self.getVersificationIfNecessary()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.getVersification() )
        lastChapterNumberString =  self.versificationList[-1][0] # The last chapter number
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "NumChapters", lastChapterNumberString )
        return int( lastChapterNumberString )
    # end of InternalBibleBook.getNumChapters


    def getNumVerses( self, C:str|int ) -> int:
        """
        Returns the number of verses (int) in the given chapter.

        Also works for chapter zero (the book introduction).

        Returns None if there is no such chapter.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.getNumVerses( {C=} )" )

        if isinstance( C, int ): # Just double-check the parameter
            logging.debug( f"InternalBibleBook.getNumVerses() was passed an integer chapter instead of a string with {self.BBB} {C}" )
            C = str( C )
        self.getVersificationIfNecessary()
        if self.versificationDict is None:
            self.versificationDict = { k:v for (k,v) in self.versificationList }
        try: return int( self.versificationDict[C] )
        except KeyError: # C not in versification
            return None
        except ValueError: # not an int
            logging.critical( f"InternalBibleBook.getNumVerses( {C=} )  got {self.versificationDict[C]=}" )
            return 0
        # for thisC,thisNumVerses in self.versificationList:
        #     # print( f"InternalBibleBook.getNumVerses( {C=} ) got {thisC=} {thisNumVerses=}" )
        #     if thisC == C:
        #         try: return int( thisNumVerses )
        #         except ValueError:
        #             logging.critical( f"InternalBibleBook.getNumVerses( {C=} )  got {thisC=} {thisNumVerses=}" )
        #             return 0
    # end of InternalBibleBook.getNumVerses


    def getContextVerseData( self, BCVReference:SimpleVerseKey|tuple[str,str,str,str], strict:bool|None=False, complete:bool|None=False ) -> tuple[InternalBibleEntryList,list[str]]:
        """
        Returns an InternalBibleEntryList plus a list containing the context of the verse.

        Raises a KeyError if the C:V reference is not found

        If the strict flag is not set, we try to remove any letter suffix
            and/or to search verse ranges for a match.

        If complete flag is set, try to find every reference with that verse.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.getContextVerseData( {BCVReference} ) for {self.workName} {self.BBB}" )
        assert self.BBB == BCVReference[0] if isinstance( BCVReference, tuple ) else BCVReference.getBBB()

        if not self._processedFlag:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook '{self.workName}' {self.BBB}: processing lines called from 'getContextVerseData'" )
            self.processLines()
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag:
            assert self._processedLines
            assert self._indexedCVFlag

        if isinstance( BCVReference, tuple ) and len(BCVReference)==2: # no verse number specified
            # We need an entire chapter of verses
            return self._CVIndex.getChapterEntriesWithContext( BCVReference[1] ) # Gives a KeyError if not found
        if isinstance( BCVReference, tuple ) and len(BCVReference)==1: # no chapter number specified
            # We need an entire book
            assert isinstance( self._CVIndex.givenBibleEntries, InternalBibleEntryList )
            return self._CVIndex.givenBibleEntries, [] # Whole book, empty context

        # else we only need one verse
        if isinstance( BCVReference, tuple ):
            assert len(BCVReference) == 3
            C, V = BCVReference[1], BCVReference[2]
        else: # assume it's a SimpleVerseKey or similar
            C,V = BCVReference.getCV()
        # try:
        verseEntryList, contextList = self._CVIndex.getVerseEntriesWithContext( (C,V), strict, complete ) # Gives a KeyError if not found
        assert isinstance( verseEntryList, InternalBibleEntryList )

        # # Check that we don't have any duplicated verses in the section that we're about to return
        # lastV = None
        # for entry in verseEntryList:
        #     marker, text = entry.getMarker(), entry.getFullText()
        #     print( f"InternalBibleBook.getContextVerseData {BCVReference} {marker}={text}" )
        #     if marker == 'v':
        #         assert text != lastV
        #         lastV = text
    
        return verseEntryList, contextList
        # NOTE: The following (and more) is now done by the index get function
        # except KeyError: # Maybe V is something like '4b' so try again just with the leading digits
        #     logging.warning( f"InternalBibleBook '{self.workName}' {self.BBB} unable to find {C}:{V} in CV index (will retry by trying only taking digits from V in case there's a suffix)")
        #     return self._CVIndex.getVerseEntriesWithContext( (C,str(getSmallLeadingInt(V))) ) # Gives a KeyError if not found
    # end of InternalBibleBook.getContextVerseData


    def getContextVerseDataRange( self, startBCVReference:SimpleVerseKey|tuple[str,str,str,str], endBCVReference:SimpleVerseKey|tuple[str,str,str,str], strict=True ) -> tuple[InternalBibleEntryList,list[str]]:
        """
        Returns an InternalBibleEntryList for an inclusive range of consecutive verses
            plus a list containing the context of the verses.

        Raises a KeyError if the starting C:V reference is not found

        If strict is true, only returns a value if every verse is found.
        If strict is false, logs a critical error and
            returns whatever we have when we fail to find a verse (perhaps because inadequate handling of bridged verses)
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBook.getContextVerseData( {startBCVReference} to {endBCVReference}) {strict=} for {self.workName} {self.BBB}" )
        assert self.BBB == startBCVReference[0] if isinstance( startBCVReference, tuple ) else startBCVReference.getBBB()
        assert self.BBB == endBCVReference[0] if isinstance( endBCVReference, tuple ) else endBCVReference.getBBB()
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  InternalBibleBook.getContextVerseData  {startBCVReference} to {endBCVReference}) {strict=} for {self.workName} {self.BBB}" )

        verseEntryList, contextList = self.getContextVerseData( startBCVReference, strict=True )
        assert isinstance( verseEntryList, InternalBibleEntryList )

        # Now concatenate the verse lists for the following verses
        startC = startBCVReference[1] if isinstance( startBCVReference, tuple ) else startBCVReference.getC()
        startV = startBCVReference[2] if isinstance( startBCVReference, tuple ) else startBCVReference.getV()
        endC = endBCVReference[1] if isinstance( endBCVReference, tuple ) else endBCVReference.getC()
        endV = endBCVReference[2] if isinstance( endBCVReference, tuple ) else endBCVReference.getV()

        # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"InternalBibleBook.getContextVerseData concatenating {self.workName} {self.BBB} from {startC}:{startV} to {endC}:{endV} {strict=}" )
        intC = int(startC)
        intV = getSmallLeadingInt(startV) + 1 # Handles strings like '4b'
        endVint = getSmallLeadingInt(endV)
        for _safetyCount in range( 1000 ): # Maximum number of expected verses in this chunk -- might be something big like '1Sam 16:1–1Ki 2:11'
            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  InternalBibleBook.getContextVerseData looking for {intC}:{intV}" )
            if intC > int(endC) \
            or (intC==int(endC) and intV > endVint):
                break
            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    InternalBibleBook.getContextVerseData adding {intC}:{intV}" )
            strC, strV = str(intC), str(intV)
            try:
                thisVerseEntryList = self._CVIndex.getVerseEntries( (strC,strV), strict=False )
                assert isinstance( thisVerseEntryList, InternalBibleEntryList )
                verseEntryList += thisVerseEntryList
            except KeyError as kerr:
                # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    InternalBibleBook.getContextVerseData got KeyError with {strC}:{strV}" )
                if startC == '-1': # This is expected, because LV doesn't have intros, so endV will be excessive
                    assert endC == '-1'
                    assert intV > 0, f"{self.workName} {self.BBB} {startC}:{startV} {intV=}" # We should have got some lines
                    break
                else:
                    # We're in a chapter and may have reached the end
                    if startC != endC:
                        numVerses = self.getNumVerses( strC )
                        if intV > numVerses:
                            intC += 1
                            intV = 0
                            # Try again with the first verse of the next chapter
                            thisVerseEntryList = self._CVIndex.getVerseEntries( (str(intC),'0'), strict=True )
                            assert isinstance( thisVerseEntryList, InternalBibleEntryList )
                            verseEntryList += thisVerseEntryList
                        else:
                            if not strict:
                                logging.critical( f"InternalBibleBook.getContextVerseData( {startBCVReference} to {endBCVReference}) for {self.workName} {self.BBB} failed at {strC}:{strV}")
                                halt
                                break # return what we've got
                            raise kerr
                    else: # we're only doing one chapter
                        if strict:
                            raise kerr
                        else: # Log it, but continue looping
                            logging.critical( f"InternalBibleBook.getContextVerseData( {startBCVReference} to {endBCVReference}, {strict=}) for {self.workName} {self.BBB} failed to find {strC}:{strV}")
            intV += 1
        else:
            loop_safety_counter_too_small

        if DEBUGGING_THIS_MODULE:
            assert isinstance( verseEntryList, InternalBibleEntryList )
            assert isinstance( contextList, list )
            # Check that we don't have any duplicated verses in the section that we're about to return
            lastV = None
            for entry in verseEntryList:
                if entry.getMarker() == 'v':
                    text = entry.getFullText()
                    print( f"InternalBibleBook.getContextVerseData( {startBCVReference} to {endBCVReference}, {strict=}) for {self.workName} {self.BBB} v={text}" )
                    assert text != lastV, f"InternalBibleBook.getContextVerseData( {startBCVReference} to {endBCVReference}, {strict=}) for {self.workName} {self.BBB} REPEATED v={text}"
                    lastV = text

        return verseEntryList, contextList
    # end of InternalBibleBook.getContextVerseDataRange


    def writeBOSBCVFiles( self, bookFolderpath ) -> None:
        """
        Write the internal pseudoUSFM out directly with one file per verse in one folder for the book.
        """
        fnPrint( DEBUGGING_THIS_MODULE, '  writeBOSBCVFiles: ' + f"Writing {self.BBB!r} as BCV…" )

        # Write the data out with the introduction in one file, and then each verse in a separate file
        introLines = verseLines = ''
        CVList = []
        for CVKey in self._CVIndex:
            C, V = CVKey
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'writeBOSBCVFiles: {self.BBB} {C}:{V}' )

            # Put all of the pseudoUSFM lines for the entry at CVKey into
            for entry in self._CVIndex.getVerseEntries( CVKey ):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, entry )
                marker, originalMarker = entry.getMarker(), entry.getOriginalMarker()
                line = '\\'+marker
                if originalMarker and originalMarker!=marker and (marker,originalMarker) not in (('c#','c'),('v~','v')):
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
                    with open( os.path.join( bookFolderpath, self.BBB+'__Intro.txt' ), 'wt', encoding='utf-8' ) as myFile:
                        if BibleOrgSysGlobals.prependBOMFlag:
                            myFile.write( BibleOrgSysGlobals.BOM )
                        myFile.write( introLines )
                    introLines = None # Will now cause an error if we try to do more introduction bits -- should only be one intro
                    CVList.append( ('-1',) )
                elif verseLines:
                    with open( os.path.join( bookFolderpath, self.BBB+'_C'+C+'V'+V+'.txt' ), 'wt', encoding='utf-8' ) as myFile:
                        if BibleOrgSysGlobals.prependBOMFlag:
                            myFile.write( BibleOrgSysGlobals.BOM )
                        myFile.write( verseLines )
                    verseLines = '' # Empty ready for the next verse
                    CVList.append( CVKey )
        if introLines: # handle left-overs for books without chapters
            assert not CVList
            with open( os.path.join( bookFolderpath, self.BBB+'_C0.txt' ), 'wt', encoding='utf-8' ) as myFile:
                if BibleOrgSysGlobals.prependBOMFlag:
                    myFile.write( BibleOrgSysGlobals.BOM )
                myFile.write( introLines )
            CVList.append( ('-1',) )
        if verseLines: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"verseLines = {verseLines}" )
        assert not verseLines

        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + "Writing BCV book metadata…" )
        metadataLines = f'BCVVersion = {BCV_VERSION}\n'
        if self.workName: metadataLines += f'WorkName = {self.workName}\n'
        metadataLines += f'CVList = {CVList}\n'
         # Double underline in filename for better dir sorting/display
        with open( os.path.join( bookFolderpath, self.BBB+'__BookMetadata.txt' ), 'wt', encoding='utf-8' ) as metadataFile:
            if BibleOrgSysGlobals.prependBOMFlag:
                metadataFile.write( BibleOrgSysGlobals.BOM )
            metadataFile.write( metadataLines )
    # end of InternalBibleBook.writeBOSBCVFiles
# end of class InternalBibleBook



def briefDemo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since this is only designed to be a base class, it can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use this class." )

    IBB = InternalBibleBook( 'Dummy', 'GEN' )
    # The following fields would normally be filled in a by "load" routine in the derived class
    IBB.objectNameString = 'Dummy test Internal Bible Book object'
    IBB.objectTypeString = 'DUMMY'
    IBB.sourceFilepath = 'Nowhere'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )
# end of InternalBibleBook.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since this is only designed to be a base class, it can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use this class." )

    IBB = InternalBibleBook( 'Dummy', 'GEN' )
    # The following fields would normally be filled in a by "load" routine in the derived class
    IBB.objectNameString = 'Dummy test Internal Bible Book object'
    IBB.objectTypeString = 'DUMMY'
    IBB.sourceFilepath = 'Nowhere'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    from BibleOrgSys.Formats.USFMBibleBook import USFMBibleBook
    def demoFile( name, filename, folder, BBB ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Loading {} from {}{}…".format( BBB, filename, f" from {folder}" if BibleOrgSysGlobals.verbosityLevel > 2 else '' ) )
        UBB = USFMBibleBook( name, BBB )
        UBB.load( filename, folder, encoding )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  ID is {UBB.getField( 'id' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Header is {UBB.getField( 'h' )!r}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Main titles are {UBB.getField( 'mt1' )!r} and {UBB.getField( 'mt2' )!r}" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UBB )
        UBB.validateMarkers()
        UBBVersification = UBB.getVersification()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBVersification )
        UBBAddedUnits = UBB.getAddedUnits()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBBAddedUnits )
        discoveryDict = UBB._discover()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "discoveryDict", discoveryDict )
        UBB.checkBook()
        UBErrors = UBB.getCheckResults()
        vPrint( 'Info', DEBUGGING_THIS_MODULE, UBErrors )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, UBErrors['Priority Errors'] )
    # end of demoFile

    from BibleOrgSys.InputOutput import USFMFilenames
    if 1: # Test a whole folder full of files
        name, encoding, testFolder = "Matigsalug", 'utf-8', Path( '/mnt/HDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
        #name, encoding, testFolder = "WEB", 'utf-8', Path( '/srv/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/' ) # You can put your test folder here
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Scanning {name} from {testFolder}…" )
            fileList = USFMFilenames.USFMFilenames( testFolder ).getMaximumPossibleFilenameTuples()
            for BBB,filename in fileList:
                demoFile( name, filename, testFolder, BBB )
                if BBB == 'GEN': break
        else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )
# end of InternalBibleBook.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleBook.py
