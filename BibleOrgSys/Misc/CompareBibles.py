#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CompareBibles.py
#
# Module to check and compare two closely related Bibles
#   e.g., a book and its back-translation.
#
# Copyright (C) 2016-2020 Robert Hunt
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
Module to check and compare two closely related Bibles
   e.g., a book and its back-translation.

In this context COMPLETE_LINE (completeLine) means a text line
    WITH THE NOTES, etc. STILL IN PLACE.
    cf. TEXT_ONLY (textOnly) means after the notes, etc., have been removed.

Includes:
    loadWordCompares( folder, filename )
    compareBooksPedantic( book1, book2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalCleanTextOnlyStrings1=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR, # For book1 -- case sensitive
                        illegalCleanTextOnlyStrings2=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
                        illegalCompleteLineStrings1=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR, # For book1 -- case sensitive
                        illegalCompleteLineStrings2=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
                        legalPairs1=DEFAULT_LEGAL_PAIRS_VERNACULAR, # For book1 for both clean text and complete lines
                        legalPairs2=DEFAULT_LEGAL_PAIRS_BACK_TRANSLATION, # For book2 for both clean text and complete lines
                        matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
                        illegalCompleteLineRegexes1=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR, # For book1
                        illegalCompleteLineRegexes2=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_BACK_TRANSLATION, # For book2
                        breakOnOne=False )
    _doCompare( parameters ) # for multiprocessing
    segmentizeLine( line, segmentEndPunctuation='.?!;' )
    segmentizeBooks( book1, book2 )
    analyzeWords( segmentList, dict12=None, dict21=None )
    analyzeBibles( Bible1, Bible2 )
    compareBibles( Bible1, Bible2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalCleanTextOnlyStrings1=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR, # For Bible1 -- case sensitive
                        illegalCleanTextOnlyStrings2=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION, # For Bible2 -- case sensitive
                        illegalCompleteLineStrings1=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR, # For book1 -- case sensitive
                        illegalCompleteLineStrings2=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
                        legalPairs1=DEFAULT_LEGAL_PAIRS_VERNACULAR, # For book1 for both clean text and complete lines
                        legalPairs2=DEFAULT_LEGAL_PAIRS_BACK_TRANSLATION, # For book2 for both clean text and complete lines
                        matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
                        illegalCompleteLineRegexes1=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR, # For book1
                        illegalCompleteLineRegexes2=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_BACK_TRANSLATION, # For book2
                        breakOnOne=False )
    fullDemo()
    main()

REGEX stuff:
    \\w for Unicode (str) patterns:
        Matches Unicode word characters; this includes most characters that can be part of a word in any language,
        as well as numbers and the underscore. If the ASCII flag is used, only [a-zA-Z0-9_] is matched.
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os.path
import logging
import re
import unicodedata
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import Bible, BibleBook


LAST_MODIFIED_DATE = '2020-04-17' # by RJH
SHORT_PROGRAM_NAME = "CompareBibles"
PROGRAM_NAME = "Bible compare analyzer"
PROGRAM_VERSION = '0.26'
programNameVersion = '{} v{}'.format( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
programNameVersionDate = '{} {} {}'.format( programNameVersion, _("last modified"), LAST_MODIFIED_DATE )

debuggingThisModule = False


MAX_MISMATCHED_MARKERS = 4
DEFAULT_COMPARE_QUOTES =  '“”‘’«»‹›"¿¡' # Doesn't include apostrophe
DEFAULT_COMPARE_PUNCTUATION = '.,:;—?!–…' # Doesn't include illegal punctuation or () [] and hyphen, so these can vary
DEFAULT_COMPARE_DIGITS = '0123456789'
DEFAULT_MATCHING_PAIRS = ( ('[',']'), ('(',')'), ('_ ',' _'), )

DEFAULT_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_COMMON = ( '  ','"',"''", "‘‘","’’", '““','””',
                                  '“ ', ' ”', '‘ ', ' ’',
                                  ',“', '.“', '!“', '?“', ':“', ';“',
                                  ',‘', '.‘', '!‘', '?‘', ':‘', ';‘',
                                  '""', "''", # straight quotes (doubled)
                                  '««','»»', '‹‹','››', '¿¿', '¡¡',
                                  ',,', '..', '!!', '??', '::', ';;',
                                  ' ,', ' .', ' !', ' ?', ' :', ' ;',
                                  ', ,', '. .', '! !', '? ?', ': :', '; ;',
                                  '<','>', '+','*',
                                  '&','%','$','#','@','~','`','|','^','\\',
                                  ' -','- ','--', '__',
                                  ' _ ', # underscore
                                  ' –','– ','––', ' —','— ','——', # en-dash and em-dash
                                  '-–','-—', '–-','–—', '—-','—–', # hyphen and dash combinations
                                  '&#x2011;', # non-breaking hyphen
                                  'XXX','ALT','NEW', )
DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_COMMON = ( '=', '{','}', '_ _', ) \
                                                        + DEFAULT_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_COMMON
DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR = ( "'", '/', ) \
                                                        + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_COMMON
DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION = ( ) \
                                                        + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_COMMON
DEFAULT_ILLEGAL_ESFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR = ( "'", ' =','_=','= ','=_' ) \
                                                        + DEFAULT_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_COMMON
DEFAULT_ILLEGAL_ESFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION = ( ) \
                                                        + DEFAULT_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_COMMON

DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_COMMON = ( '  ',"''", "‘‘","’’", '““','””',
                                  '“ ', ' ”', '‘ ', ' ’',
                                  '""', "''", # straight quotes (doubled)
                                  '««','»»', '‹‹','››', '¿¿', '¡¡',
                                   ',,', '..', '!!', '??', '::', ';;',
                                   ' ,', ' .', ' !', ' ?', ' :', ' ;', ' *',
                                  ' -','- ','--', '__', '_ _',
                                  ' _ ', # underscore
                                  ' –','– ','––', ' —','— ','——', # en-dash and em-dash
                                  '-–','-—', '–-','–—', '—-','—–', # hyphen and dash combinations
                                  '&#x2011;', # non-breaking hyphen
                                  'f*,','f*.','f*?','f*!','f*:','f*”','f*’','f*\\wj*', # footnote at end of sentence
                                  'fe*,','fe*.','fe*?','fe*!','fe*:','fe*”','fe*’','fe*\\wj*', # endnote at end of sentence
                                  'x*,','x*.','x*?','x*!','x*:','x*”','x*’','x*\\wj*', # cross-reference at end of sentence
                                  '”\\wj*',
                                  )
DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR = ( ) + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_COMMON
DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION = ( ) + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_COMMON

DEFAULT_LEGAL_PAIRS_COMMON = ( ('“ ','“ ‘'), (' ”','’ ”'), (' ’','” ’'), ) # First field in tuple can be repeated in other tuples
DEFAULT_LEGAL_PAIRS_VERNACULAR = () + DEFAULT_LEGAL_PAIRS_COMMON
DEFAULT_LEGAL_PAIRS_BACK_TRANSLATION = () + DEFAULT_LEGAL_PAIRS_COMMON

DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_COMMON = (
                    r'\\f [^+][^ ]', # Footnote that doesn't start with +
                    r'\\f \\+ [^\\][^f][^r][^ ]', # Footnote that doesn't start with \fr
                    r'\\fr [0-9]{1,3}:[0-9]{1,3} [^\\][^f][^t][^ ]', # Footnote that doesn't start with \ft
                    r'\\fr [0-9]{1,3}:[0-9]{1,3}-[0-9]{1,3} [^\\][^f][^t][^ ]', # Bridged footnote that doesn't start with \ft
                    r'[^.?!)”*]\\f\*', # Footnote that doesn't end with period, etc.
                    r'\\x [^+][^ ]', # Cross-reference that doesn't start with +
                    r'\\x \\+ [^\\][^x][^o][^ ]', # Cross-reference that doesn't start with \ft
                    r'\\xo [0-9]{1,3}:[0-9]{1,3}(-[0-9]{1,3})? ', # Cross-reference (incl. bridged) that doesn't end with colon
                    r'\\xo [0-9]{1,3}:[0-9]{1,3}: a [^\\][^x][^t][^ ]', # Cross-reference that doesn't start with \xt
                    r'\\xo [0-9]{1,3}:[0-9]{1,3}-[0-9]{1,3}: a [^\\][^x][^t][^ ]', # Bridged cross-reference that doesn't start with \xt
                    r'[^.]\\x\*', # Cross-reference that doesn't end with period
                    r'\\x\* ', # Cross-reference followed by a space
                    r' \\[a-z]{1,3}\*', # Closing marker after a space
                    r'^\([1-4][A-Z].*?\)$', # \r reference without space e.g. 2Ki instead of 2 Ki
                    r'[a-z]\\[^fx][a-z]? ', # character marker (not footnote or cross-reference) not preceded by space
                    r'”\w', r'’\w', # Closing quote followed by a character
                    r'»\w', r'›\w', # Closing quote followed by a character
                    '=[^AGLOPQS]', # for ESFM tags only, but doesn't normally cause other problems
                    '=S[^GH]', # for ESFM Strongs tags only, but doesn't normally cause other problems
                    )
DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR = ( ) + DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_COMMON
DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_BACK_TRANSLATION = ( ) + DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_COMMON

# DEFAULT_ILLEGAL_CONSECUTIVE_LINE_PAIRS = (
#             ('q1','','q1')
#             )


def loadWordCompares( folder, filename ):
    """
    Returns two dicts (longest entries first)
    """
    vPrint( 'Verbose', debuggingThisModule, f"loadWordCompares( {folder}, {filename} )…" )

    dict12, dict21 = {}, {} # Not worried about sorting yet

    filepath = os.path.join( folder, filename )
    vPrint( 'Normal', debuggingThisModule, "Loading word compares from {}…".format( filepath ) )

    lineCount = 0
    with open( filepath, 'rt', encoding='utf-8' ) as inputFile:
        for line in inputFile:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF or \ufeff
                logging.info( "loadWordCompares: Detected Unicode Byte Order Marker (BOM) in {}".format( filepath ) )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            #vPrint( 'Quiet', debuggingThisModule, 'SFM file line is "' + line + '"' )
            if line[0]=='#': continue # Just discard comment lines

            if debuggingThisModule: assert '=' in line
            if '=>' in line: # this line only works from Bible1 => Bible2
                mid, use = '=>', 12
            elif '<=' in line: # this line only works from Bible1 <= Bible2
                mid, use = '<=', 21
            else: # it works both ways
                mid, use = '=', 1221

            bitl, bitr = line.split( mid, 1 )
            lBits, rBits = bitl.strip().split( '\\' ), bitr.strip().split( '\\' )
            #vPrint( 'Quiet', debuggingThisModule, '{!r}={} <> {!r}={}'.format( bitl, lBits, bitr, rBits ) )
            if use in (12,1221):
                for lBit in lBits:
                    if lBit in dict12:
                        #vPrint( 'Quiet', debuggingThisModule, "  We already had {!r} = {} (now got {}) in dict12 ({})".format( lBit, dict12[lBit], rBits, use ) )
                        dict12[lBit].extend( rBits )
                    else: dict12[lBit] = rBits
                    #if lBit.title() != lBit:
                        #dict12[lBit.title()] = rBits
            if use in (21,1221):
                for rBit in rBits:
                    if rBit in dict21:
                        #vPrint( 'Quiet', debuggingThisModule, "  We already had {!r} = {} (now got {}) in dict21 ({})".format( rBit, dict21[rBit], lBits, use ) )
                        dict21[rBit].extend( lBits )
                    else: dict21[rBit] = lBits
                    #if rBit.title() != rBit:
                        #dict21[rBit.title()] = lBits

    #vPrint( 'Quiet', debuggingThisModule, '\ndict12', len(dict12), sorted(dict12.items()) )
    #vPrint( 'Quiet', debuggingThisModule, '\ndict21', len(dict21), sorted(dict21.items()) )

    # Now sort the dictionaries with the longest entries first
    dict12s, dict21s = {}, {}
    for dKey in sorted(dict12, key=len, reverse=True):
        dict12s[dKey] = dict12[dKey]
    for dKey in sorted(dict21, key=len, reverse=True):
        dict21s[dKey] = dict21[dKey]
    return dict12s, dict21s
# end of loadWordCompares



# def checkBookPedantic( bookObject,
#                         compareQuotes=DEFAULT_COMPARE_QUOTES,
#                         comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
#                         compareDigits=DEFAULT_COMPARE_DIGITS,
#                         illegalCleanTextOnlyStrings=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR, # For book1 -- case sensitive
#                         illegalCompleteLineStrings=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR, # For book1 -- case sensitive
#                         legalPairs=DEFAULT_LEGAL_PAIRS_VERNACULAR, # For book1 for both clean text and complete lines
#                         matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
#                         illegalCompleteLineRegexes=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR, # For book1
#                         breakOnOne=False ):
#     """
#     Given a Bible book object, check it carefully
#     and return results.

#     The returned list is sorted by C:V
#     Each list entry is a 2-tuple, being 3-tuple C/V/marker and error message.
#     """
#     vPrint( 'Verbose', debuggingThisModule, f"checkBookPedantic( {bookObject}, "
#                     f"{compareQuotes!r}, {comparePunctuation!r}, {compareDigits}, "
#                     f"{illegalCleanTextOnlyStrings}, {matchingPairs}, "
#                     f"{breakOnOne} ) for {bookObject.BBB}" )

#     bcResults = []

#     len1 = len(bookObject)

#     ix1 = 0
#     C, V = '-1', '-1' # So first/id line starts at -1:0
#     while ix1<len1:
#         entry1 = bookObject._processedLines[ix1] # InternalBibleEntry objects
#         #vPrint( 'Quiet', debuggingThisModule, 'entry', entry1 )
#         marker1, line1 = entry1.getMarker(), entry1.getOriginalText()

#         if marker1 == 'c': C, V = line1.split()[0], '0'
#         elif marker1 == 'v':
#             if C == '-1': C = '1' # Some one chapter books might not have a C marker
#             V = line1.split()[0]
#         elif C == '-1' and marker1!='intro': V = str( int(V) + 1 )
#         #vPrint( 'Quiet', debuggingThisModule, '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
#         #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getOriginalText() )
#         #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getAdjustedText() )
#         #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getCleanText() )
#         originalMarker = entry1.getOriginalMarker()
#         reference = (C,V,' ' if originalMarker is None else originalMarker)

#         numMismatchedMarkers = 0
#         if line1:
#             line1len = len(line1)
#             for left,right in matchingPairs:
#                 hadMatchingError1 = hadMatchingError2 = False
#                 ixl = -1
#                 while True:
#                     ixl = line1.find( left, ixl+1 )
#                     if ixl == -1: break
#                     ixr = line1.find( right, ixl+2 )
#                     if ixr == -1:
#                         contextStart, contextEnd = max(0,ixl-5), ixl+7
#                         context = line1[contextStart:contextEnd]
#                         if contextStart > 0 and context[0]!=' ': context = '…' + context
#                         if contextEnd < line1len and context[-1]!=' ': context = context + '…'
#                         bcResults.append( (reference,"Missing second part of pair in Bible1: {!r} after {!r}".format( right, context )) )
#                         hadMatchingError1 = True
#                 ixl = -1
#                 ixr = 9999
#                 while True:
#                     ixr = line1.rfind( right, 0, ixr )
#                     if ixr == -1: break
#                     ixl = line1.rfind( left, 0, ixr )
#                     if ixl == -1:
#                         contextStart, contextEnd = max(0,ixr-6), ixr+6
#                         context = line1[contextStart:contextEnd]
#                         if contextStart > 0 and context[0]!=' ': context = '…' + context
#                         if contextEnd < line1len and context[-1]!=' ': context = context + '…'
#                         bcResults.append( (reference,"Missing first part of pair in Bible1: {!r} before {!r}".format( left, context )) )
#                         hadMatchingError1 = True
#                 # The above doesn't detect ( ) ) so we do it here
#                 if not hadMatchingError1: # already
#                     l1cl, l1cr = line1.count( left ), line1.count( right )
#                     if l1cl > l1cr:
#                         bcResults.append( (reference,"Too many {!r} in Bible1".format( left )) )
#                     elif l1cr > l1cl:
#                         bcResults.append( (reference,"Too many {!r} in Bible".format( right )) )

#             entryCleanText = entry1.getCleanText() # So markers don't confuse things
#             entryFullText = entry1.getFullText() # So can check AROUND markers also
#             extras1 = entry1.getExtras()
#             if marker1 in ( 'id','ide','rem', ): # Don't do illegal strings in these non-Bible-text fields
#                 assert not extras1
#             else:
#                 if extras1 is None: extras1 = () # So it's always iterable
#                 for iString in illegalCleanTextOnlyStrings:
#                     iCount = entryCleanText.count( iString )
#                     if iCount:
#                         for illegalString,legalString in legalPairs:
#                             if illegalString==iString:
#                                 iCount -= entryCleanText.count( legalString )
#                         if iCount > 0:
#                             if BibleOrgSysGlobals.verbosityLevel > 2:
#                                 bcResults.append( (reference,"Illegal string in Bible main text: {!r} in {!r}".format( iString, entryCleanText )) )
#                             else:
#                                 bcResults.append( (reference,"Illegal string in Bible main text: {!r}".format( iString )) )
#                     for extra in extras1:
#                         #vPrint( 'Quiet', debuggingThisModule, extra )
#                         #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getType() )
#                         #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getIndex() )
#                         #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getText() )
#                         #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getCleanText() )
#                         if iString in extra.getCleanText(): # So markers don't confuse things
#                             bcResults.append( (reference,"Illegal string in Bible note main text: {!r}".format( iString )) )
#                 for iString in illegalCompleteLineStrings:
#                     iCount = entryFullText.count( iString )
#                     if iCount:
#                         for illegalString,legalString in legalPairs:
#                             if illegalString==iString:
#                                 iCount -= entryFullText.count( legalString )
#                         if iCount > 0:
#                             bcResults.append( (reference,"Illegal string in Bible: {!r}".format( iString )) )
#                     for extra in extras1:
#                         if iString in extra.getText(): # with all markers
#                             bcResults.append( (reference,"Illegal string in Bible note: {!r}".format( iString )) )
#                 for iRegex in illegalCompleteLineRegexes:
#                     reMatch = re.search( iRegex, entryFullText )
#                     if reMatch:
#                         bcResults.append( (reference,"Illegal {!r} regex string in Bible: {!r}".format( iRegex, reMatch.group(0) )) )
#                         break # Stop at one

#         ix1 += 1

#     return bcResults
# # end of checkBookPedantic



def compareBooksPedantic( book1, book2,
        compareQuotes=DEFAULT_COMPARE_QUOTES,
        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
        compareDigits=DEFAULT_COMPARE_DIGITS,
        illegalCleanTextOnlyStrings1=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR, # For book1 -- case sensitive
        illegalCleanTextOnlyStrings2=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
        illegalCompleteLineStrings1=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR, # For book1 -- case sensitive
        illegalCompleteLineStrings2=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
        legalPairs1=DEFAULT_LEGAL_PAIRS_VERNACULAR, # For book1 for both clean text and complete lines
        legalPairs2=DEFAULT_LEGAL_PAIRS_BACK_TRANSLATION, # For book2 for both clean text and complete lines
        matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
        illegalCompleteLineRegexes1=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR, # For book1
        illegalCompleteLineRegexes2=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_BACK_TRANSLATION, # For book2
        breakOnOne=False ) -> List[Tuple[Tuple[str,str,str],str]]:
    """
    Given two Bible book objects, compare the two carefully
        and return differences.

    This is typically used to compare a translation and a matching back-translation
        for pedantic things like quote-marks and punctuation.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being 3-tuple C/V/marker and error message.
    """
    vPrint( 'Verbose', debuggingThisModule, "compareBooksPedantic( {}, {}, {!r}, {!r}, {}, {}, {}, {}, {} ) for {}" \
                    .format( book1, book2, compareQuotes, comparePunctuation, compareDigits,
                                        illegalCleanTextOnlyStrings1, illegalCleanTextOnlyStrings2, matchingPairs,
                                        breakOnOne, book1.BBB ) )
    assert book1.BBB == book2.BBB
    assert book1.workName != book2.workName

    bcResults:List[Tuple[Tuple[str,str,str],str]] = []

    len1, len2 = len(book1), len(book2)
    #vPrint( 'Quiet', debuggingThisModule, 'len', len1, len2 )
    if len1 != len2:
        bcResults.append( (('0','0',' '),
                    f"Book lengths don't match: {len1} vs {len2} newline markers") )

    ix1 = ix2 = offset1 = offset2 = 0
    # marker1 = marker2 = line1 = line2 = None
    numMismatchedMarkers = 0
    C, V = '-1', '-1' # So first/id line starts at -1:0
    while (ix1+offset1)<len1 and (ix2+offset2)<len2:
        entry1 = book1._processedLines[ix1+offset1] # InternalBibleEntry object
        entry2 = book2._processedLines[ix2+offset2] # InternalBibleEntry object
        #vPrint( 'Quiet', debuggingThisModule, 'entry', entry1, entry2 )

        # lastMarker1, lastLine1 = marker1, line1
        # lastMarker2, lastLine2 = marker1, line2
        marker1, line1 = entry1.getMarker(), entry1.getOriginalText()
        marker2, line2 = entry2.getMarker(), entry2.getOriginalText()

        if marker1 == 'c': C, V = line1.split()[0], '0'
        elif marker1 == 'v':
            if C == '-1': C = '1' # Some one chapter books might not have a C marker
            V = line1.split()[0]
        elif C == '-1' and marker1!='intro': V = str( int(V) + 1 )
        #vPrint( 'Quiet', debuggingThisModule, '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getOriginalText() )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getAdjustedText() )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getCleanText() )
        originalMarker = entry1.getOriginalMarker()
        reference = (C,V,' ' if originalMarker is None else originalMarker)

        if marker1 == marker2: # ok, formats of both books match
            numMismatchedMarkers = 0
            if line1 or line2:
                line1len, line2len = len(line1), len(line2)
                for quoteChar in compareQuotes:
                    c1, c2 = line1.count( quoteChar ), line2.count( quoteChar )
                    if c1 != c2:
                        try: quoteName = unicodedata.name( quoteChar )
                        except ValueError: quoteName = quoteChar
                        bcResults.append( (reference,"Mismatched quote: {} vs {} {}".format( c1, c2, quoteName )) )
                        if breakOnOne: break
                for punctChar in comparePunctuation:
                    c1, c2 = line1.count( punctChar ), line2.count( punctChar )
                    if c1 != c2:
                        try: punctName = unicodedata.name( punctChar )
                        except ValueError: punctName = punctChar
                        bcResults.append( (reference,"Mismatched punctuation: {} vs {} {}".format( c1, c2, punctName )) )
                        if breakOnOne: break
                for digit in compareDigits:
                    c1, c2 = line1.count( digit ), line2.count( digit )
                    if c1 != c2:
                        bcResults.append( (reference,"Mismatched digit: {} vs {} {!r}".format( c1, c2, digit )) )
                        if breakOnOne: break
                for left,right in matchingPairs:
                    hadMatchingError1 = hadMatchingError2 = False
                    ixl = -1
                    while True:
                        ixl = line1.find( left, ixl+1 )
                        if ixl == -1: break
                        ixr = line1.find( right, ixl+2 )
                        if ixr == -1:
                            contextStart, contextEnd = max(0,ixl-5), ixl+7
                            context = line1[contextStart:contextEnd]
                            if contextStart > 0 and context[0]!=' ': context = '…' + context
                            if contextEnd < line1len and context[-1]!=' ': context = context + '…'
                            bcResults.append( (reference,"Missing second part of pair in Bible1: {!r} after {!r}".format( right, context )) )
                            hadMatchingError1 = True
                    ixl = -1
                    while True:
                        ixl = line2.find( left, ixl+1 )
                        if ixl == -1: break
                        ixr = line2.find( right, ixl+2 )
                        if ixr == -1:
                            contextStart, contextEnd = max(0,ixl-5), ixl+7
                            context = line2[contextStart:contextEnd]
                            if contextStart > 0 and context[0]!=' ': context = '…' + context
                            if contextEnd < line2len and context[-1]!=' ': context = context + '…'
                            bcResults.append( (reference,"Missing second part of pair in Bible2: {!r} after {!r}".format( right, context )) )
                            hadMatchingError2 = True
                    ixr = 9999
                    while True:
                        ixr = line1.rfind( right, 0, ixr )
                        if ixr == -1: break
                        ixl = line1.rfind( left, 0, ixr )
                        if ixl == -1:
                            contextStart, contextEnd = max(0,ixr-6), ixr+6
                            context = line1[contextStart:contextEnd]
                            if contextStart > 0 and context[0]!=' ': context = '…' + context
                            if contextEnd < line1len and context[-1]!=' ': context = context + '…'
                            bcResults.append( (reference,"Missing first part of pair in Bible1: {!r} before {!r}".format( left, context )) )
                            hadMatchingError1 = True
                    ixr = 9999
                    while True:
                        ixr = line2.rfind( right, 0, ixr )
                        if ixr == -1: break
                        ixl = line2.rfind( left, 0, ixr )
                        if ixl == -1:
                            contextStart, contextEnd = max(0,ixr-6), ixr+6
                            context = line2[contextStart:contextEnd]
                            if contextStart > 0 and context[0]!=' ': context = '…' + context
                            if contextEnd < line2len and context[-1]!=' ': context = context + '…'
                            bcResults.append( (reference,"Missing first part of pair in Bible2: {!r} before {!r}".format( left, context )) )
                            hadMatchingError2 = True
                    # The above doesn't detect ( ) ) so we do it here
                    if not hadMatchingError1: # already
                        l1cl, l1cr = line1.count( left ), line1.count( right )
                        if l1cl > l1cr:
                            bcResults.append( (reference,"Too many {!r} in Bible1".format( left )) )
                        elif l1cr > l1cl:
                            bcResults.append( (reference,"Too many {!r} in Bible1".format( right )) )
                    if not hadMatchingError2: # already
                        l2cl, l2cr = line2.count( left ), line2.count( right )
                        if l2cl > l2cr:
                            bcResults.append( (reference,"Too many {!r} in Bible2".format( left )) )
                        elif l2cr > l2cl:
                            bcResults.append( (reference,"Too many {!r} in Bible2".format( right )) )

                entryCleanText1, entryCleanText2 = entry1.getCleanText(), entry2.getCleanText() # So markers don't confuse things
                entryFullText1, entryFullText2 = entry1.getFullText(), entry2.getFullText() # So can check AROUND markers also
                extras1, extras2 = entry1.getExtras(), entry2.getExtras()
                if marker1 in ( 'id','ide','rem', ): # Don't do illegal strings in these non-Bible-text fields
                    assert not extras1
                    assert not extras2
                else:
                    if extras1 is None: extras1 = () # So it's always iterable
                    if extras2 is None: extras2 = () # So it's always iterable
                    if len(extras1) != len(extras2):
                        bcResults.append( (reference,"Differing numbers of extras/notes: {} vs {}".format( len(extras1), len(extras2) )) )
                    for iString in illegalCleanTextOnlyStrings1:
                        iCount = entryCleanText1.count( iString )
                        if iCount:
                            for illegalString,legalString in legalPairs1:
                                if illegalString==iString:
                                    iCount -= entryCleanText1.count( legalString )
                            if iCount > 0:
                                bcResults.append( (reference,"Illegal string in Bible1 main text: {!r}".format( iString )) )
                        for extra in extras1:
                            #vPrint( 'Quiet', debuggingThisModule, extra )
                            #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getType() )
                            #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getIndex() )
                            #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getText() )
                            #vPrint( 'Quiet', debuggingThisModule, ' ', extra.getCleanText() )
                            if iString in extra.getCleanText(): # So markers don't confuse things
                                bcResults.append( (reference,"Illegal string in Bible1 note main text: {!r}".format( iString )) )
                    for iString in illegalCompleteLineStrings1:
                        iCount = entryFullText1.count( iString )
                        if iCount:
                            for illegalString,legalString in legalPairs1:
                                if illegalString==iString:
                                    iCount -= entryFullText1.count( legalString )
                            if iCount > 0:
                                bcResults.append( (reference,"Illegal string in Bible1: {!r}".format( iString )) )
                        for extra in extras1:
                            if iString in extra.getText(): # with all markers
                                bcResults.append( (reference,"Illegal string in Bible1 note: {!r}".format( iString )) )
                    for iRegex in illegalCompleteLineRegexes1:
                        reMatch = re.search( iRegex, entryFullText1 )
                        if reMatch:
                            bcResults.append( (reference,"Illegal {!r} regex string in Bible1: {!r}".format( iRegex, reMatch.group(0) )) )
                            break # Stop at one
                    for iString in illegalCleanTextOnlyStrings2:
                        iCount = entryCleanText2.count( iString )
                        if iCount:
                            for illegalString,legalString in legalPairs1:
                                if illegalString==iString:
                                    iCount -= entryCleanText2.count( legalString )
                            if iCount > 0:
                                bcResults.append( (reference,"Illegal string in Bible2 main text: {!r}".format( iString )) )
                        for extra in extras2:
                            if iString in extra.getCleanText(): # So markers don't confuse things
                                bcResults.append( (reference,"Illegal string in Bible2 note main text: {!r}".format( iString )) )
                    for iString in illegalCompleteLineStrings2:
                        iCount = entryFullText2.count( iString )
                        if iCount:
                            for illegalString,legalString in legalPairs2:
                                if illegalString==iString:
                                    iCount -= entryFullText2.count( legalString )
                            if iCount > 0:
                                bcResults.append( (reference,"Illegal string in Bible2: {!r}".format( iString )) )
                        for extra in extras2:
                            if iString in extra.getText(): # with all markers
                                bcResults.append( (reference,"Illegal string in Bible2 note: {!r}".format( iString )) )
                    for iRegex in illegalCompleteLineRegexes2:
                        reMatch = re.search( iRegex, entryFullText2 )
                        if reMatch:
                            bcResults.append( (reference,"Illegal {!r} regex string in Bible2: {!r}".format( iRegex, reMatch.group(0) )) )
                            break # Stop at one

        else: # markers are different in the two given books
            numMismatchedMarkers += 1
            if numMismatchedMarkers < MAX_MISMATCHED_MARKERS:
                bcResults.append( (reference,"Mismatched markers: {!r} vs {!r}".format( marker1, marker2 )) )
                # See if we can skip a marker in book1
                if (ix1+offset1)<len1-1 and book1._processedLines[ix1+offset1+1].getMarker()==marker2:
                    offset1 += 1
                    bcResults.append( (reference,"Skipping book1 marker: {!r}".format( marker1 )) )
                    continue # Doesn't advance ix1 and ix2
                # Otherwise, see if we can skip a marker in book2
                if (ix2+offset2)<len2-1 and book2._processedLines[ix2+offset2+1].getMarker()==marker1:
                    offset2 += 1
                    bcResults.append( (reference,"Skipping book2 marker: {!r}".format( marker2 )) )
                    continue # Doesn't advance ix1 and ix2
            else:
                bcResults.append( (reference,"Mismatched markers: {!r} vs {!r}—aborted checking of {} now!".format( marker1, marker2, book1.BBB )) )
                break # things are too bad -- not worth continuing
        ix1 += 1; ix2 += 1

    return bcResults
# end of compareBooksPedantic

def _doCompare( parameters:List[Tuple[str,Bible,Bible]] ) -> List[Tuple[Tuple[str,str,str],str]]: # for multiprocessing
    BBB, Bible1, Bible2 = parameters
    return compareBooksPedantic( Bible1[BBB], Bible2[BBB] )


def segmentizeLine( line:str, segmentEndPunctuation:str='.?!;:' ) -> List[List[str]]:
    """
    Break the line into segments (like sentences that should match across the translations)
        and then break each segment into words.

    If you want case folding, convert line to lowerCase before calling.

    Set segmentEndPunctuation to None if you don't want the lines further divided.

    Returns a list of lists of words.
    """
    vPrint( 'Verbose', debuggingThisModule, "segmentizeLine( {!r} )".format( line ) )

    if segmentEndPunctuation:
        for segmentEndChar in segmentEndPunctuation:
            line = line.replace( segmentEndChar, 'SsSsSsS' )
    line = line.replace('—',' ').replace('–',' ') # Treat em-dash and en-dash as word break characters


    lineList:List[List[str]] = []
    for segment in line.split( 'SsSsSsS' ):
        segmentList = []
        for rawWord in segment.split():
            word = rawWord
            for internalMarker in BibleOrgSysGlobals.internal_SFMs_to_remove: word = word.replace( internalMarker, '' )
            word = BibleOrgSysGlobals.stripWordPunctuation( word )
            if word and not word[0].isalnum():
                #vPrint( 'Quiet', debuggingThisModule, "not alnum", repr(rawWord), repr(word) )
                if len(word) > 1:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        vPrint( 'Quiet', debuggingThisModule, "segmentizeLine: {} {}:{} ".format( self.BBB, C, V ) \
                                            + _("Have unexpected character starting word {!r}").format( word ) )
                    word = word[1:]
            if word: # There's still some characters remaining after all that stripping
                #vPrint( 'Quiet', debuggingThisModule, "here", repr(rawWord), repr(word) )
                if 1 or BibleOrgSysGlobals.verbosityLevel > 3: # why???
                    for k,char in enumerate(word):
                        if not char.isalnum() and (k==0 or k==len(word)-1 or char not in BibleOrgSysGlobals.MEDIAL_WORD_PUNCT_CHARS):
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                vPrint( 'Quiet', debuggingThisModule, "segmentizeLine: {} {}:{} ".format( self.BBB, C, V ) + _("Have unexpected {!r} in word {!r}").format( char, word ) )
                lcWord = word.lower()
                isAReferenceOrNumber = True
                for char in word:
                    if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                if not isAReferenceOrNumber:
                    segmentList.append( word )
                    #lDict['allWordCounts'][word] = 1 if word not in lDict['allWordCounts'] else lDict['allWordCounts'][word] + 1
                    #lDict['allCaseInsensitiveWordCounts'][lcWord] = 1 if lcWord not in lDict['allCaseInsensitiveWordCounts'] else lDict['allCaseInsensitiveWordCounts'][lcWord] + 1
        lineList.append( segmentList )

    #vPrint( 'Quiet', debuggingThisModule, '  lineList', lineList )
    return lineList
# end of segmentizeLine


def segmentizeBooks( book1:BibleBook, book2:BibleBook ) -> Tuple[list,list]:
    """
    Given two Bible book objects,
        break them into a list of segments
            as well as a list of left-overs if the segments don't match.

    Each segment list entry is a 3-tuple:
        1/ 3-tuple being C, V, optional marker
        2/ Segment list for book1
        3/ Segment list for book2

    Each left-over list entry is a 2-tuple:
        1/ 3-tuple being C, V, optional marker
        2/ Error message string
    """
    vPrint( 'Verbose', debuggingThisModule, f"segmentizeBooks( {book1}, {book2}, … ) for {book1.BBB}" )
    assert isinstance( book1, BibleBook )
    assert isinstance( book2, BibleBook )
    assert book1.BBB == book2.BBB
    assert book1.workName != book2.workName

    abResults, segmentList = [], []
    #if 'allWordCounts' not in dict1: dict1['allWordCounts'] = {}
    #if 'allWordCounts' not in dict2: dict2['allWordCounts'] = {}
    #if 'allCaseInsensitiveWordCounts' not in dict1: dict1['allCaseInsensitiveWordCounts'] = {}
    #if 'allCaseInsensitiveWordCounts' not in dict2: dict2['allCaseInsensitiveWordCounts'] = {}

    len1, len2 = len(book1), len(book2)
    #vPrint( 'Quiet', debuggingThisModule, 'len', len1, len2 )
    if len1 != len2:
        abResults.append( (('0','0',' '),"Book lengths don't match: {} vs {} newline markers".format( len1, len2 )) )

    ix1 = ix2 = offset1 = offset2 = 0
    numMismatchedMarkers = 0
    C, V = '-1', '-1' # So first/id line starts at -1:0
    while (ix1+offset1)<len1 and (ix2+offset2)<len2:
        entry1, entry2 = book1._processedLines[ix1+offset1], book2._processedLines[ix2+offset2] # InternalBibleEntry objects
        #vPrint( 'Quiet', debuggingThisModule, 'entry', entry1, entry2 )
        marker1, line1 = entry1.getMarker(), entry1.getOriginalText()
        marker2, line2 = entry2.getMarker(), entry2.getOriginalText()

        if marker1 == 'c': C, V = line1.split()[0], '0'
        elif marker1 == 'v':
            if C == '-1': C = '1' # Some one chapter books might not have a C marker
            V = line1.split()[0]
        elif C == '-1' and marker1!='intro': V = str( int(V) + 1 )
        #vPrint( 'Quiet', debuggingThisModule, '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getOriginalText() )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getAdjustedText() )
        #vPrint( 'Quiet', debuggingThisModule, ' ', entry1.getCleanText() )
        originalMarker = entry1.getOriginalMarker()
        reference = (C,V,' ' if originalMarker is None else originalMarker)

        if marker1 == marker2:
            numMismatchedMarkers = 0
            if (line1 or line2) and marker1 not in ( 'id','ide','rem', 'c','v', ): # Don't count these non-Bible-text fields
                wordList1 = segmentizeLine( line1 )
                wordList2 = segmentizeLine( line2 )
                if len(wordList1) == len(wordList2): # both had the same number of segments
                    for segment1List,segment2List in zip( wordList1, wordList2 ):
                        if segment1List and segment2List:
                            segmentList.append( (reference,segment1List,segment2List) )
        else: # markers are different
            numMismatchedMarkers += 1
            if numMismatchedMarkers < MAX_MISMATCHED_MARKERS:
                abResults.append( (reference,"Mismatched markers: {!r} vs {!r}".format( marker1, marker2 )) )
                # See if we can skip a marker in book1
                if (ix1+offset1)<len1-1 and book1._processedLines[ix1+offset1+1].getMarker()==marker2:
                    offset1 += 1
                    abResults.append( (reference,"Skipping book1 marker to continue: {!r}".format( marker1 )) )
                    continue # Doesn't advance ix1 and ix2
                # Otherwise, see if we can skip a marker in book2
                if (ix2+offset2)<len2-1 and book2._processedLines[ix2+offset2+1].getMarker()==marker1:
                    offset2 += 1
                    abResults.append( (reference,"Skipping book2 marker to continue: {!r}".format( marker2 )) )
                    continue # Doesn't advance ix1 and ix2
            else:
                abResults.append( (reference,"Mismatched markers: {!r} vs {!r}—aborted checking of {} now!".format( marker1, marker2, book1.BBB )) )
                break # things are too bad -- not worth continuing
        ix1 += 1; ix2 += 1

    if (ix1+offset1)<len1:
        remaining = len1 - (ix1+offset1)
        assert remaining >= 1
        abResults.append( (reference,"Extra marker{} remaining in book1: {!r}{}" \
                                .format( '' if remaining==1 else 's ({})'.format( remaining ),
                                    book1._processedLines[ix1+offset1].getMarker(), '…' if remaining>1 else '' )) )
    if (ix2+offset2)<len2:
        remaining = len2 - (ix2+offset2)
        assert remaining >= 1
        abResults.append( (reference,"Extra marker{} remaining in book2: {!r}{}" \
                                .format( '' if remaining==1 else 's ({})'.format( remaining ),
                                    book1._processedLines[ix2+offset2].getMarker(), '…' if remaining>1 else '' )) )

    #vPrint( 'Quiet', debuggingThisModule, '\nsegmentList', len(segmentList), segmentList )
    #vPrint( 'Quiet', debuggingThisModule, '\nabResults', len(abResults), abResults )
    return segmentList, abResults
# end of segmentizeBooks



def analyzeWordsInSegment( reference, segmentAList, segmentBList, dictAB, resultsList ):
    """
    """
    #vPrint( 'Quiet', debuggingThisModule, "\nanalyzeWordsInSegment( {}, {}, {}, {}, … )".format( reference, segmentAList, segmentBList, len(dictAB) ) )
    #vPrint( 'Quiet', debuggingThisModule, 'segmentBList {}'.format( segmentBList ) )
    #vPrint( 'Quiet', debuggingThisModule, 'segmentAList {}'.format( segmentAList ) )
    assert isinstance( reference, tuple )
    assert isinstance( segmentAList, list )
    assert isinstance( segmentBList, list )
    assert isinstance( dictAB, dict )
    assert isinstance( resultsList, list )

    foundLPhrases = []
    for lEntry,rEntryList in dictAB.items():
        assert isinstance( lEntry, str )
        assert isinstance( rEntryList, list )

        # First count how many times the lEntry occurs in segmentAList
        if ' ' in lEntry: # lEntry is multiple words -- requires extra handling
            #vPrint( 'Quiet', debuggingThisModule, 'multiple lEntry {!r}'.format( lEntry ) ) # lEntry is language2
            lWords = lEntry.split()
            #vPrint( 'Quiet', debuggingThisModule, 'lWords (split) =', lWords )
            numLSearchWords = len( lWords )
            seglenA = len( segmentAList )
            ix = -1
            lCount = 0
            while True:
                #vPrint( 'Quiet', debuggingThisModule, lWords, ix, lCount, segmentAList )
                try: ix = segmentAList.index( lWords[0], ix+1 )
                except ValueError: break # none / no more found
                matched = True
                for iy in range( 1, numLSearchWords ):
                    if ix+iy >= seglenA: matched = False; break # Too near the end
                    if segmentAList[ix+iy] != lWords[iy]: matched = False; break
                if matched:
                    #vPrint( 'Quiet', debuggingThisModule, "lMatched" ); halt
                    lCount += 1
                    #if lCount > 1: vPrint( 'Quiet', debuggingThisModule, "multiple lMatches" ); halt
                #else: vPrint( 'Quiet', debuggingThisModule, "not lMatched" )
            if lCount: foundLPhrases.extend( lWords )
        else: # lEntry is a single word -- easy
            lCount = segmentAList.count( lEntry )

        if lCount:
            #vPrint( 'Quiet', debuggingThisModule, 'lEntry {!r}'.format( lEntry ) ) # lEntry is a string
            #vPrint( 'Quiet', debuggingThisModule, 'lCount', lCount )
            #vPrint( 'Quiet', debuggingThisModule, 'rEntryList {}'.format( rEntryList ) ) # rEntryList is a list
            # Now count how many times the rEntries occur in segmentBList
            rCount = 0
            for rEntry in rEntryList:
                #vPrint( 'Quiet', debuggingThisModule, 'rEntry {!r}'.format( rEntry ) ) # rEntry is language1 string
                assert isinstance( rEntry, str )
                if ' ' in rEntry: # lEntry is multiple words -- requires extra handling
                    rWords = rEntry.split()
                    #vPrint( 'Quiet', debuggingThisModule, 'rWords (split) =', rWords )
                    numRSearchWords = len( rWords )
                    seglenB = len( segmentBList )
                    ix = -1
                    while True:
                        #vPrint( 'Quiet', debuggingThisModule, rWords, ix, rCount, segmentBList )
                        try: ix = segmentBList.index( rWords[0], ix+1 )
                        except ValueError: break # none / no more found
                        matched = True
                        for iy in range( 1, numRSearchWords ):
                            if ix+iy >= seglenB: matched = False; break # Too near the end
                            if segmentBList[ix+iy] != rWords[iy]: matched = False; break
                        if matched:
                            #vPrint( 'Quiet', debuggingThisModule, "rMatched" ); halt
                            rCount += 1
                            #if rCount > 1: vPrint( 'Quiet', debuggingThisModule, "multiple rMatches", lEntry ); halt
                        #else: vPrint( 'Quiet', debuggingThisModule, "not rMatched" )
                else: # rEntry is a single word -- easy
                    rCount += segmentBList.count( rEntry )
            #vPrint( 'Quiet', debuggingThisModule, 'rCount', rCount )

            # Now check the results
            if lCount > rCount:
                if ' ' not in lEntry and lEntry in foundLPhrases:
                    #vPrint( 'Quiet', debuggingThisModule, lEntry, foundLPhrases ); halt
                      vPrint( 'Info', debuggingThisModule, "  analyzeWordsInSegment: Skipping {!r} because already found in {}".format( lEntry, foundLPhrases ) )
                else:
                    resultsList.append( (reference,"{!r} from {}\n   not enough ({}/{}) in {}".format( lEntry, segmentAList, lCount, rCount, segmentBList )) )
                    #resultsList.append( ((' ',' ',' '), rEntry) )
                    #vPrint( 'Quiet', debuggingThisModule, (reference,"{!r} from {}\n   not enough ({}/{}) in {}".format( lEntry, segmentAList, lCount, rCount, segmentBList )) )
                    #vPrint( 'Quiet', debuggingThisModule, "   {!r}:{}".format( lEntry, rEntry ) )
            #elif lCount < rCount:
                #resultsList.append( (reference,"Word matches for {!r} exceeded ({}/{}) in {!r}".format( word, wordCount, rCount, segmentAList )) )
# end of analyzeWordsInSegment


def analyzeWords( segmentList, dict12=None, dict21=None ):
    """
    Given a list of segments (mostly sentences) from two different but closely related versions,
        use the given dictionaries to check that the corresponding word(s) are in the related version.

    Returns a list of results.
    """
    vPrint( 'Verbose', debuggingThisModule, "analyzeWords( … )" )
    assert isinstance( segmentList, list )
    #vPrint( 'Quiet', debuggingThisModule, "\ndict12", dict12 )
    #vPrint( 'Quiet', debuggingThisModule, "\ndict21", dict21 )

    awResults = []
    for j,(reference,segment1,segment2) in enumerate( segmentList ):
        if dict12: analyzeWordsInSegment( reference, segment1, segment2, dict12, awResults )
        if dict21: analyzeWordsInSegment( reference, segment2, segment1, dict21, awResults )

    #vPrint( 'Quiet', debuggingThisModule, '\nawResults', len(awResults), awResults )
    return awResults

    wordDict1, wordDict2 = {}, {}
    for j,(segment1,segment2) in enumerate( segmentList ):
        for word1 in segment1:
            if word1 not in wordDict1:
                vPrint( 'Quiet', debuggingThisModule, "Processing {} {!r}…".format( j, word1 ) )
                #wordDict1[word1] = []
                options = {}
                wordSet = set( segment2 )
                for segment1b,segment2b in segmentList[j+1:]:
                    if word1 in segment1b:
                        wordSet = wordSet.intersection( segment2b )
                        if len(wordSet) == 1:
                            vPrint( 'Quiet', debuggingThisModule, word1, wordSet )
                            wordDict1[word1] = wordSet.pop()
                            break
        #if j > 5: break
    vPrint( 'Quiet', debuggingThisModule, len(wordDict1), wordDict1 )
    halt
# end of CompareBibles.analyzeWords


def analyzeBibles( Bible1:Bible, Bible2:Bible ) -> Dict[str,list]:
    """
    Given two Bible objects, break the two into words
        and return a dictionary.

    This is typically used to compare a translation and a matching back-translation.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being BCV and error message.
    """
    vPrint( 'Verbose', debuggingThisModule, "analyzeBibles( {}, {} )".format( Bible1, Bible2 ) )
    assert isinstance( Bible1, Bible )
    assert isinstance( Bible2, Bible )
    assert Bible1.abbreviation != Bible2.abbreviation or Bible1.name != Bible2.name
    assert Bible1.discoveryResults
    assert Bible2.discoveryResults
    vPrint( 'Quiet', debuggingThisModule, _("Running analyzeBibles…") )

    bSegmentList, bResults = {}, {}

    len1, len2 = len(Bible1), len(Bible2)
    commonBooks = []
    for bBook in Bible1:
        if bBook.BBB in Bible2: commonBooks.append( bBook.BBB )
    numBooks = len( commonBooks )

    vPrint( 'Info', debuggingThisModule, _("Running segmentizeBooks on both Bibles…") )
    if BibleOrgSysGlobals.maxProcesses > 1: # Check all the books as quickly as possible
        vPrint( 'Normal', debuggingThisModule, _("Comparing {} books using {} processes…").format( numBooks, BibleOrgSysGlobals.maxProcesses ) )
        vPrint( 'Normal', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
        BibleOrgSysGlobals.alreadyMultiprocessing = True
        with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            results = pool.map( _doCompare, [(BBB,Bible1,Bible2) for BBB in commonBooks] ) # have the pool do our loads
            assert len(results) == numBooks
            for j,BBB in enumerate( commonBooks ):
                bResults[BBB] = results[j] # Saves them in the correct order
        BibleOrgSysGlobals.alreadyMultiprocessing = False
    else: # Just single threaded
        for BBB in commonBooks: # Do individual book prechecks
            vPrint( 'Verbose', debuggingThisModule, "  " + _("Comparing {}…").format( BBB ) )
            bSegmentList[BBB], bResults[BBB] = segmentizeBooks( Bible1[BBB], Bible2[BBB] ) #, abResults1, abResults2 )
            vPrint( 'Quiet', debuggingThisModule, BBB, bSegmentList[BBB] )
            vPrint( 'Quiet', debuggingThisModule, BBB, bResults[BBB] )
    return bResults
# end of CompareBibles.analyzeBibles



def compareBibles( Bible1, Bible2,
        compareQuotes=DEFAULT_COMPARE_QUOTES,
        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
        compareDigits=DEFAULT_COMPARE_DIGITS,
        illegalCleanTextOnlyStrings1=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR, # For Bible1 -- case sensitive
        illegalCleanTextOnlyStrings2=DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION, # For Bible2 -- case sensitive
        illegalCompleteLineStrings1=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR, # For book1 -- case sensitive
        illegalCompleteLineStrings2=DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION, # For book2 -- case sensitive
        legalPairs1=DEFAULT_LEGAL_PAIRS_VERNACULAR, # For book1 for both clean text and complete lines
        legalPairs2=DEFAULT_LEGAL_PAIRS_BACK_TRANSLATION, # For book2 for both clean text and complete lines
        matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
        illegalCompleteLineRegexes1=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_VERNACULAR, # For book1
        illegalCompleteLineRegexes2=DEFAULT_ILLEGAL_COMPLETE_LINE_REGEXES_BACK_TRANSLATION, # For book2
        breakOnOne=False ):
    """
    Runs a series of checks and count on each book of the Bible
        in order to try to determine what are the normal standards.
    """
    vPrint( 'Verbose', debuggingThisModule, "compareBibles( {}, {} )".format( Bible1, Bible2 ) )
    assert isinstance( Bible1, Bible )
    assert isinstance( Bible2, Bible )
    assert Bible1.abbreviation != Bible2.abbreviation or Bible1.name != Bible2.name
    vPrint( 'Quiet', debuggingThisModule, _("Running compareBibles…") )

    len1, len2 = len(Bible1), len(Bible2)
    commonBooks = []
    for bBook in Bible1:
        if bBook.BBB in Bible2: commonBooks.append( bBook.BBB )
    numBooks = len( commonBooks )

    vPrint( 'Info', debuggingThisModule, _("Running compareBooksPedantic on both Bibles…") )
    bResults = {}
    if BibleOrgSysGlobals.maxProcesses > 1: # Check all the books as quickly as possible
        vPrint( 'Normal', debuggingThisModule, _("Comparing {} books using {} processes…").format( numBooks, BibleOrgSysGlobals.maxProcesses ) )
        vPrint( 'Normal', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
        BibleOrgSysGlobals.alreadyMultiprocessing = True
        with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            results = pool.map( _doCompare, [(BBB,Bible1,Bible2) for BBB in commonBooks] ) # have the pool do our loads
            assert len(results) == numBooks
            for j,BBB in enumerate( commonBooks ):
                bResults[BBB] = results[j] # Saves them in the correct order
        BibleOrgSysGlobals.alreadyMultiprocessing = False
    else: # Just single threaded
        for BBB in commonBooks: # Do individual book prechecks
            vPrint( 'Verbose', debuggingThisModule, "  " + _("Comparing {}…").format( BBB ) )
            bResults[BBB] = compareBooksPedantic( Bible1[BBB], Bible2[BBB], compareQuotes=compareQuotes,
                                                comparePunctuation=comparePunctuation, compareDigits=compareDigits,
                                                illegalCleanTextOnlyStrings1=illegalCleanTextOnlyStrings1, illegalCleanTextOnlyStrings2=illegalCleanTextOnlyStrings2,
                                                illegalCompleteLineStrings1=illegalCompleteLineStrings1, illegalCompleteLineStrings2=illegalCompleteLineStrings2,
                                                legalPairs1=legalPairs1, legalPairs2=legalPairs2,
                                                matchingPairs=matchingPairs,
                                                illegalCompleteLineRegexes1=illegalCompleteLineRegexes1, illegalCompleteLineRegexes2=illegalCompleteLineRegexes2,
                                                breakOnOne=breakOnOne )
    return bResults
# end of CompareBibles.compareBibles



def briefDemo() -> None:
    """
    Demonstration program to handle command line parameters and then run what they want.
    """
    from BibleOrgSys.Formats.USFMBible import USFMBible

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Load a USFM Bible and BT
    vPrint( 'Quiet', debuggingThisModule, "\nLoading USFM Bible…" )
    name1, encoding1, testFolder1 = "MBTV", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
    name2, encoding2, testFolder2 = "MS-BT", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTBT/' ) # You can put your test folder here
    MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1 = ( 'c','f','j','o','q','v','x','z', ) + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR
    MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2 = ( 'We ',' we ',' us ',' us.',' us,',' us:',' us;',' us!',' us?',' us–',' us—',
                             'Our ',' our ','You ','you ','you.','you,','you:','you;','you!','you?','you–','you—',
                             'Your ','your ','yours ',' the the ', ) + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION
    MS_ILLEGAL_COMPLETE_LINE_STRINGS_1 = () + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR
    MS_ILLEGAL_COMPLETE_LINE_STRINGS_2 = () + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION
    MS_LEGAL_PAIRS = ( ('/',' 1/ '), ('/',' 2/ '), ('/',' 3/ '), ('/',' 4/ '), ) + DEFAULT_LEGAL_PAIRS_COMMON

    if os.access( testFolder1, os.R_OK ):
        UB1 = USFMBible( testFolder1, name1, encoding1 )
        UB1.load()
        vPrint( 'Quiet', debuggingThisModule, UB1 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB1.check()
        #UB1.doAllExports( "BOSOutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder {!r} is not readable on this computer.".format( testFolder1 ) )

    if os.access( testFolder2, os.R_OK ):
        UB2 = USFMBible( testFolder2, name2, encoding2 )
        UB2.load()
        vPrint( 'Quiet', debuggingThisModule, UB2 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB2.check()
        #UB2.doAllExports( "BOSOutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder {!r} is not readable on this computer.".format( testFolder2 ) )

    if 0: # Test one book
        vPrint( 'Quiet', debuggingThisModule, "\nTesting one book only…" )
        BBB = 'JDE'
        result = compareBooksPedantic( UB1[BBB], UB2[BBB],
                                        illegalCleanTextOnlyStrings1=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1, illegalCleanTextOnlyStrings2=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2,
                                        illegalCompleteLineStrings1=MS_ILLEGAL_COMPLETE_LINE_STRINGS_1, illegalCompleteLineStrings2=MS_ILLEGAL_COMPLETE_LINE_STRINGS_2,
                                        legalPairs1=MS_LEGAL_PAIRS, legalPairs2=MS_LEGAL_PAIRS )
        vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
        vPrint( 'Normal', debuggingThisModule, ' ', result )

    if 1: # Test the whole Bibles
        vPrint( 'Quiet', debuggingThisModule, "\nTesting for whole Bible…" )
        results = compareBibles( UB1, UB2,
                                        illegalCleanTextOnlyStrings1=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1, illegalCleanTextOnlyStrings2=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2,
                                        illegalCompleteLineStrings1=MS_ILLEGAL_COMPLETE_LINE_STRINGS_1, illegalCompleteLineStrings2=MS_ILLEGAL_COMPLETE_LINE_STRINGS_2,
                                        legalPairs1=MS_LEGAL_PAIRS, legalPairs2=MS_LEGAL_PAIRS )
        totalCount = resultsBooksCount = 0
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    resultsBooksCount += 1
                    totalCount += len( bookResults )
                    vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                    for (C,V,marker),resultString in bookResults:
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            vPrint( 'Quiet', debuggingThisModule, "{} total results in {} books (out of {})".format( totalCount, resultsBooksCount, len(UB1) ) )

    if 0: # Compare one book
        vPrint( 'Quiet', debuggingThisModule, "\nAnalyzing one book only…" )
        BBB = 'JDE'
        segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
        vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
        #vPrint( 'Quiet', debuggingThisModule, ' 1s', len(segmentResult), segmentResult )
        vPrint( 'Quiet', debuggingThisModule, ' 2o', len(otherResult), otherResult )
        dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'MSBTCheckWords.txt' )
        awResult = analyzeWords( segmentResult, dict12, dict21 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
            vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
            for (C,V,marker),resultString in awResult:
                resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            vPrint( 'Quiet', debuggingThisModule, "{:,} results in {}".format( len(awResult), BBB ) )

    if 0: # Compare the whole Bibles
        vPrint( 'Quiet', debuggingThisModule, "\nAnalyzing whole Bible…" )
        totalSegments = totalCount = 0
        for BBB in UB1.getBookList():
            segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
            totalSegments += len( segmentResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
                #vPrint( 'Quiet', debuggingThisModule, ' 1s', len(segmentResult), segmentResult )
                vPrint( 'Quiet', debuggingThisModule, ' 2o', len(otherResult), otherResult )
            dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'MSBTCheckWords.txt' )
            awResult = analyzeWords( segmentResult, dict12, dict21 )
            totalCount += len( awResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                for (C,V,marker),resultString in awResult:
                    resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                    vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
                vPrint( 'Quiet', debuggingThisModule, "  {:,} results in {}".format( len(awResult), BBB ) )
            break
        vPrint( 'Quiet', debuggingThisModule, "{:,} total results in {} books ({:,} segments)".format( totalCount, len(UB1), totalSegments ) )
# end of CompareBibles.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    from BibleOrgSys.Formats.USFMBible import USFMBible

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Load a USFM Bible and BT
    vPrint( 'Quiet', debuggingThisModule, "\nLoading USFM Bible…" )
    name1, encoding1, testFolder1 = "MBTV", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/' ) # You can put your test folder here
    name2, encoding2, testFolder2 = "MS-BT", 'utf-8', Path( '/mnt/SSDs/Matigsalug/Bible/MBTBT/' ) # You can put your test folder here
    MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1 = ( 'c','f','j','o','q','v','x','z', ) + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_VERNACULAR
    MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2 = ( 'We ',' we ',' us ',' us.',' us,',' us:',' us;',' us!',' us?',' us–',' us—',
                             'Our ',' our ','You ','you ','you.','you,','you:','you;','you!','you?','you–','you—',
                             'Your ','your ','yours ',' the the ', ) + DEFAULT_ILLEGAL_USFM_CLEAN_TEXT_ONLY_STRINGS_BACK_TRANSLATION
    MS_ILLEGAL_COMPLETE_LINE_STRINGS_1 = () + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_VERNACULAR
    MS_ILLEGAL_COMPLETE_LINE_STRINGS_2 = () + DEFAULT_ILLEGAL_COMPLETE_LINE_STRINGS_BACK_TRANSLATION
    MS_LEGAL_PAIRS = ( ('/',' 1/ '), ('/',' 2/ '), ('/',' 3/ '), ('/',' 4/ '), ) + DEFAULT_LEGAL_PAIRS_COMMON

    if os.access( testFolder1, os.R_OK ):
        UB1 = USFMBible( testFolder1, name1, encoding1 )
        UB1.load()
        vPrint( 'Quiet', debuggingThisModule, UB1 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB1.check()
        #UB1.doAllExports( "BOSOutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder {!r} is not readable on this computer.".format( testFolder1 ) )

    if os.access( testFolder2, os.R_OK ):
        UB2 = USFMBible( testFolder2, name2, encoding2 )
        UB2.load()
        vPrint( 'Quiet', debuggingThisModule, UB2 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB2.check()
        #UB2.doAllExports( "BOSOutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: vPrint( 'Quiet', debuggingThisModule, "Sorry, test folder {!r} is not readable on this computer.".format( testFolder2 ) )

    if 0: # Test one book
        vPrint( 'Quiet', debuggingThisModule, "\nTesting one book only…" )
        BBB = 'JDE'
        result = compareBooksPedantic( UB1[BBB], UB2[BBB],
                                        illegalCleanTextOnlyStrings1=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1, illegalCleanTextOnlyStrings2=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2,
                                        illegalCompleteLineStrings1=MS_ILLEGAL_COMPLETE_LINE_STRINGS_1, illegalCompleteLineStrings2=MS_ILLEGAL_COMPLETE_LINE_STRINGS_2,
                                        legalPairs1=MS_LEGAL_PAIRS, legalPairs2=MS_LEGAL_PAIRS )
        vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
        vPrint( 'Normal', debuggingThisModule, ' ', result )

    if 1: # Test the whole Bibles
        vPrint( 'Quiet', debuggingThisModule, "\nTesting for whole Bible…" )
        results = compareBibles( UB1, UB2,
                                        illegalCleanTextOnlyStrings1=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_1, illegalCleanTextOnlyStrings2=MS_ILLEGAL_CLEAN_TEXT_ONLY_STRINGS_2,
                                        illegalCompleteLineStrings1=MS_ILLEGAL_COMPLETE_LINE_STRINGS_1, illegalCompleteLineStrings2=MS_ILLEGAL_COMPLETE_LINE_STRINGS_2,
                                        legalPairs1=MS_LEGAL_PAIRS, legalPairs2=MS_LEGAL_PAIRS )
        totalCount = resultsBooksCount = 0
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    resultsBooksCount += 1
                    totalCount += len( bookResults )
                    vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                    for (C,V,marker),resultString in bookResults:
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            vPrint( 'Quiet', debuggingThisModule, "{} total results in {} books (out of {})".format( totalCount, resultsBooksCount, len(UB1) ) )

    if 0: # Compare one book
        vPrint( 'Quiet', debuggingThisModule, "\nAnalyzing one book only…" )
        BBB = 'JDE'
        segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
        vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
        #vPrint( 'Quiet', debuggingThisModule, ' 1s', len(segmentResult), segmentResult )
        vPrint( 'Quiet', debuggingThisModule, ' 2o', len(otherResult), otherResult )
        dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'MSBTCheckWords.txt' )
        awResult = analyzeWords( segmentResult, dict12, dict21 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
            vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
            for (C,V,marker),resultString in awResult:
                resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            vPrint( 'Quiet', debuggingThisModule, "{:,} results in {}".format( len(awResult), BBB ) )

    if 0: # Compare the whole Bibles
        vPrint( 'Quiet', debuggingThisModule, "\nAnalyzing whole Bible…" )
        totalSegments = totalCount = 0
        for BBB in UB1.getBookList():
            segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
            totalSegments += len( segmentResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', debuggingThisModule, "Comparing {} gave:".format( BBB ) )
                #vPrint( 'Quiet', debuggingThisModule, ' 1s', len(segmentResult), segmentResult )
                vPrint( 'Quiet', debuggingThisModule, ' 2o', len(otherResult), otherResult )
            dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'MSBTCheckWords.txt' )
            awResult = analyzeWords( segmentResult, dict12, dict21 )
            totalCount += len( awResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', debuggingThisModule, '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                for (C,V,marker),resultString in awResult:
                    resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                    vPrint( 'Quiet', debuggingThisModule, '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
                vPrint( 'Quiet', debuggingThisModule, "  {:,} results in {}".format( len(awResult), BBB ) )
        vPrint( 'Quiet', debuggingThisModule, "{:,} total results in {} books ({:,} segments)".format( totalCount, len(UB1), totalSegments ) )
# end of CompareBibles.fullDemo


def main() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    from BibleOrgSys.UnknownBible import UnknownBible

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    fp1, fp2 = BibleOrgSysGlobals.commandLineArguments.Bible1, BibleOrgSysGlobals.commandLineArguments.Bible2
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Bible1 filepath {!r} is invalid—aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Bible2 filepath {!r} is invalid—aborting".format( fp2 ) ); allOkay = False

    if allOkay:
        UnkB1 = UnknownBible( fp1 )
        result1 = UnkB1.search( autoLoadAlways=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "Bible1 loaded", result1 )
        if isinstance( result1, Bible ):
            Bible1 = result1
        else:
            logging.critical( f"Unable to load Bible1 from {fp1!r}—aborting" ); allOkay = False
    if allOkay:
        UnkB2 = UnknownBible( fp2 )
        result2 = UnkB2.search( autoLoadAlways=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "Bible2 loaded", result2 )
        if isinstance( result2, Bible ):
            Bible2 = result2
        else:
            logging.critical( f"Unable to load Bible2 from {fp2!r}—aborting" ); allOkay = False

    if allOkay:
        results = compareBibles( Bible1, Bible2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            name1 = Bible1.abbreviation if Bible1.abbreviation else Bible1.getAName()
            name2 = Bible2.abbreviation if Bible2.abbreviation else Bible2.getAName()
            vPrint( 'Quiet', debuggingThisModule, "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    vPrint( 'Quiet', debuggingThisModule, f'\n{BBB}:' )
                    for result in bookResults:
                        C, V, resultString = result[0][0], result[0][1], result[1]
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        vPrint( 'Quiet', debuggingThisModule, f'{C}:{V} {resultString}' )
            #vPrint( 'Quiet', debuggingThisModule, results )
# end of CompareBibles.main

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
    #parser.add_argument('Bible1', help="Bible folder or file path 1" )
    #parser.add_argument('Bible2', help="Bible folder or file path 2" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of CompareBibles.py
