#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CompareBibles.py
#
# Module handling a internal Bible object
#
# Copyright (C) 2016 Robert Hunt
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
Module handling an internal Bible object.

A class which extends BibleWriter (which itself extends InternalBible).
"""

from gettext import gettext as _

LastModifiedDate = '2016-09-14' # by RJH
ShortProgName = "CompareBibles"
ProgName = "Bible compare analyzer"
ProgVersion = '0.06'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import os.path, logging
import unicodedata
import multiprocessing
from collections import OrderedDict

import BibleOrgSysGlobals
from Bible import Bible



MAX_MISMATCHED_MARKERS = 4
DEFAULT_COMPARE_QUOTES =  '“”‘’«»‹›"¿¡' # Doesn't include apostrophe
DEFAULT_COMPARE_PUNCTUATION = '.,:;—?!–' # Doesn't include illegal punctuation or () [] and hyphen, so these can vary
DEFAULT_COMPARE_DIGITS = '0123456789'
DEFAULT_ILLEGAL_STRINGS_COMMON = ( '  ','"',"''", "‘‘","’’", '<','=','>', '{','}',
                                  '&','%','$','#','@','~','`','|','^',
                                  ' -','- ','--', '__', '_ _',
                                  ' –','– ',' —','— ', # en-dash and em-dash
                                  '*,','*.','*?','*!', 'XXX','ALT','NEW', )
DEFAULT_ILLEGAL_STRINGS_1 = ( "'", '/', ) + DEFAULT_ILLEGAL_STRINGS_COMMON
DEFAULT_ILLEGAL_STRINGS_2 = ( ) + DEFAULT_ILLEGAL_STRINGS_COMMON
DEFAULT_MATCHING_PAIRS = ( ('[',']'), ('(',')'), ('_ ',' _'), )



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



def loadWordCompares( folder, filename ):
    """
    """
    if 1 or BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("loadWordCompares( {}, {} )").format( folder, filename ) )

    dict12, dict21 = {}, {}

    filepath = os.path.join( folder, filename )
    lineCount = 0
    with open( filepath, 'rt', encoding='utf-8' ) as inputFile:
        for line in inputFile:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF or \ufeff
                logging.info( "loadWordCompares: Detected Unicode Byte Order Marker (BOM) in {}".format( filepath ) )
                line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            if not line: continue # Just discard blank lines
            #print ( 'SFM file line is "' + line + '"' )
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
            #print( '{!r}={} <> {!r}={}'.format( bitl, lBits, bitr, rBits ) )
            if use in (12,1221):
                for lBit in lBits:
                    if lBit in dict12:
                        print( "  We already had {!r} in dict12".format( lBit ) )
                    dict12[lBit] = rBits
                    #if lBit.title() != lBit:
                        #dict12[lBit.title()] = rBits
            if use in (21,1221):
                for rBit in rBits:
                    if rBit in dict21:
                        print( "  We already had {!r} in dict21".format( rBit ) )
                    dict21[rBit] = lBits
                    #if rBit.title() != rBit:
                        #dict21[rBit.title()] = lBits

    #print( '\ndict12', len(dict12), sorted(dict12.items()) )
    #print( '\ndict21', len(dict21), sorted(dict21.items()) )
    return dict12, dict21
# end of loadWordCompares



def compareBooksPedantic( book1, book2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalStrings1=DEFAULT_ILLEGAL_STRINGS_1, # Case sensitive
                        illegalStrings2=DEFAULT_ILLEGAL_STRINGS_2, # Case sensitive
                        matchingPairs=DEFAULT_MATCHING_PAIRS, # For both Bibles
                        breakOnOne=False ):
    """
    Given two Bible book objects, compare the two carefully
        and return differences.

    This is typically used to compare a translation and a matching back-translation
        for pedantic things like quote-marks and punctuation.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being 3-tuple C/V/marker and error message.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("compareBooksPedantic( {}, {}, {!r}, {!r}, {}, {}, {}, {}, {} ) for {}") \
                    .format( book1, book2, compareQuotes, comparePunctuation, compareDigits,
                                        illegalStrings1, illegalStrings2, matchingPairs,
                                        breakOnOne, book1.BBB ) )
        assert book1.BBB == book2.BBB
        assert book1.workName != book2.workName

    bcResults = []

    len1, len2 = len(book1), len(book2)
    #print( 'len', len1, len2 )
    if len1 != len2:
        bcResults.append( (('0','0',' '),"Book lengths don't match: {} vs {}".format( len1, len2 )) )

    ix1 = ix2 = offset1 = offset2 = 0
    numMismatchedMarkers = 0
    C, V = '0', '-1' # id line should be 0:0
    while (ix1+offset1)<len1 and (ix2+offset2)<len2:
        entry1, entry2 = book1._processedLines[ix1+offset1], book2._processedLines[ix2+offset2] # InternalBibleEntry objects
        #print( 'entry', entry1, entry2 )
        marker1, line1 = entry1.getMarker(), entry1.getOriginalText()
        marker2, line2 = entry2.getMarker(), entry2.getOriginalText()

        if marker1 == 'c': C, V = line1.split()[0], '0'
        elif marker1 == 'v':
            if C == '0': C = '1' # Some one chapter books might not have a C marker
            V = line1.split()[0]
        elif C == '0' and marker1!='intro': V = str( int(V) + 1 )
        #print( '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
        #print( ' ', entry1.getOriginalText() )
        #print( ' ', entry1.getAdjustedText() )
        #print( ' ', entry1.getCleanText() )
        originalMarker = entry1.getOriginalMarker()
        reference = (C,V,' ' if originalMarker is None else originalMarker)

        if marker1 == marker2:
            numMismatchedMarkers = 0
            if line1 or line2:
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
                    # NOTE: Code below doesn't give error with ( ( )
                    ixl = -1
                    while True:
                        ixl = line1.find( left, ixl+1 )
                        if ixl == -1: break
                        ixr = line1.find( right, ixl+2 )
                        if ixr == -1:
                            bcResults.append( (reference,"Missing second part of pair in Bible1: {!r} after {!r}".format( right, left )) )
                    ixl = -1
                    while True:
                        ixl = line2.find( left, ixl+1 )
                        if ixl == -1: break
                        ixr = line2.find( right, ixl+2 )
                        if ixr == -1:
                            bcResults.append( (reference,"Missing second part of pair in Bible2: {!r} after {!r}".format( right, left )) )
                    ixr = 9999
                    while True:
                        ixr = line1.rfind( right, 0, ixr )
                        if ixr == -1: break
                        ixl = line1.rfind( left, 0, ixr )
                        if ixl == -1:
                            bcResults.append( (reference,"Missing first part of pair in Bible1: {!r} before {!r}".format( left, right )) )
                    ixr = 9999
                    while True:
                        ixr = line2.rfind( right, 0, ixr )
                        if ixr == -1: break
                        ixl = line2.rfind( left, 0, ixr )
                        if ixl == -1:
                            bcResults.append( (reference,"Missing first part of pair in Bible2: {!r} before {!r}".format( left, right )) )
                if marker1 not in ( 'id','ide','rem', ): # Don't do illegal strings in these non-Bible-text fields
                    extras = entry1.getExtras()
                    if extras is None: extras = () # So it's always iterable
                    for iString in illegalStrings1:
                        if iString in entry1.getCleanText(): # So markers don't confuse things
                            bcResults.append( (reference,"Illegal string in Bible1: {!r}".format( iString )) )
                        for extra in extras:
                            #print( extra )
                            #print( ' ', extra.getType() )
                            #print( ' ', extra.getIndex() )
                            #print( ' ', extra.getText() )
                            #print( ' ', extra.getCleanText() )
                            if iString in extra.getCleanText(): # So markers don't confuse things
                                bcResults.append( (reference,"Illegal string in Bible1 note: {!r}".format( iString )) )
                    extras = entry2.getExtras()
                    if extras is None: extras = () # So it's always iterable
                    for iString in illegalStrings2:
                        if iString in entry2.getCleanText(): # So markers don't confuse things
                            bcResults.append( (reference,"Illegal string in Bible2: {!r}".format( iString )) )
                        for extra in extras:
                            #print( extra )
                            #print( ' ', extra.getType() )
                            #print( ' ', extra.getIndex() )
                            #print( ' ', extra.getText() )
                            #print( ' ', extra.getCleanText() )
                            if iString in extra.getCleanText(): # So markers don't confuse things
                                bcResults.append( (reference,"Illegal string in Bible2 note: {!r}".format( iString )) )
        else: # markers are different
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

def _doCompare( parameters ): # for multiprocessing
    BBB, Bible1, Bible2 = parameters
    return compareBooksPedantic( Bible1[BBB], Bible2[BBB] )


def segmentizeLine( line, segmentEndPunctuation='.?!;:' ):
    """
    Break the line into segments (like sentences that should match across the translations)
        and then break each segment into words.

    If you want case folding, convert line to lowerCase before calling.

    Set segmentEndPunctuation to None if you don't want the lines further divided.

    Returns a list of lists of words.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("segmentizeLine( {!r} )").format( line ) )

    if segmentEndPunctuation:
        for segmentEndChar in segmentEndPunctuation:
            line = line.replace( segmentEndChar, 'SsSsSsS' )
    line = line.replace('—',' ').replace('–',' ') # Treat em-dash and en-dash as word break characters


    lineList = []
    for segment in line.split( 'SsSsSsS' ):
        segmentList = []
        for rawWord in segment.split():
            word = rawWord
            for internalMarker in BibleOrgSysGlobals.internal_SFMs_to_remove: word = word.replace( internalMarker, '' )
            word = BibleOrgSysGlobals.stripWordPunctuation( word )
            if word and not word[0].isalnum():
                #print( "not alnum", repr(rawWord), repr(word) )
                if len(word) > 1:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "segmentizeLine: {} {}:{} ".format( self.BBB, C, V ) \
                                            + _("Have unexpected character starting word {!r}").format( word ) )
                    word = word[1:]
            if word: # There's still some characters remaining after all that stripping
                #print( "here", repr(rawWord), repr(word) )
                if 1 or BibleOrgSysGlobals.verbosityLevel > 3: # why???
                    for k,char in enumerate(word):
                        if not char.isalnum() and (k==0 or k==len(word)-1 or char not in BibleOrgSysGlobals.MEDIAL_WORD_PUNCT_CHARS):
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                print( "segmentizeLine: {} {}:{} ".format( self.BBB, C, V ) + _("Have unexpected {!r} in word {!r}").format( char, word ) )
                lcWord = word.lower()
                isAReferenceOrNumber = True
                for char in word:
                    if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                if not isAReferenceOrNumber:
                    segmentList.append( word )
                    #lDict['allWordCounts'][word] = 1 if word not in lDict['allWordCounts'] else lDict['allWordCounts'][word] + 1
                    #lDict['allCaseInsensitiveWordCounts'][lcWord] = 1 if lcWord not in lDict['allCaseInsensitiveWordCounts'] else lDict['allCaseInsensitiveWordCounts'][lcWord] + 1
        lineList.append( segmentList )

    #print( '  lineList', lineList )
    return lineList
# end of segmentizeLine


def segmentizeBooks( book1, book2 ):
    """
    Given two Bible book objects, analyse the two carefully
        and return differences.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being CV and error message.
    """
    if 1 or BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("segmentizeBooks( {}, {}, … ) for {}").format( book1, book2, book1.BBB ) )
        assert book1.BBB == book2.BBB
        assert book1.workName != book2.workName

    abResults, segmentList = [], []
    #if 'allWordCounts' not in dict1: dict1['allWordCounts'] = {}
    #if 'allWordCounts' not in dict2: dict2['allWordCounts'] = {}
    #if 'allCaseInsensitiveWordCounts' not in dict1: dict1['allCaseInsensitiveWordCounts'] = {}
    #if 'allCaseInsensitiveWordCounts' not in dict2: dict2['allCaseInsensitiveWordCounts'] = {}

    len1, len2 = len(book1), len(book2)
    #print( 'len', len1, len2 )
    if len1 != len2:
        abResults.append( (('0','0',' '),"Book lengths don't match: {} vs {} newline markers".format( len1, len2 )) )

    ix1 = ix2 = offset1 = offset2 = 0
    numMismatchedMarkers = 0
    C, V = '0', '-1' # id line should be 0:0
    while (ix1+offset1)<len1 and (ix2+offset2)<len2:
        entry1, entry2 = book1._processedLines[ix1+offset1], book2._processedLines[ix2+offset2] # InternalBibleEntry objects
        #print( 'entry', entry1, entry2 )
        marker1, line1 = entry1.getMarker(), entry1.getOriginalText()
        marker2, line2 = entry2.getMarker(), entry2.getOriginalText()

        if marker1 == 'c': C, V = line1.split()[0], '0'
        elif marker1 == 'v':
            if C == '0': C = '1' # Some one chapter books might not have a C marker
            V = line1.split()[0]
        elif C == '0' and marker1!='intro': V = str( int(V) + 1 )
        #print( '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
        #print( ' ', entry1.getOriginalText() )
        #print( ' ', entry1.getAdjustedText() )
        #print( ' ', entry1.getCleanText() )
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

    #print( '\nsegmentList', len(segmentList), segmentList )
    #print( '\nabResults', len(abResults), abResults )
    return segmentList, abResults
# end of segmentizeBooks



def analyzeWords( segmentList, dict12=None, dict21=None ):
    """
    """
    if 1 or BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("analyzeWords( … )") )
        assert isinstance( segmentList, list )

    awResults = []

    for j,(reference,segment1,segment2) in enumerate( segmentList ):
        for word in dict12:
            if word in segment1:
                wordCount = segment1.count( word )
                foundCount = 0
                for rWord in dict12[word]:
                    foundCount += segment2.count( rWord )
                if wordCount > foundCount:
                    awResults.append( (reference,"Word matches for {!r} not enough ({}/{}) in {!r}".format( word, wordCount, foundCount, segment2 )) )
                #elif wordCount < foundCount:
                    #awResults.append( (reference,"Word matches for {!r} exceeded ({}/{}) in {!r}".format( word, wordCount, foundCount, segment2 )) )
        for word in dict21:
            if word in segment2:
                wordCount = segment2.count( word )
                foundCount = 0
                for rWord in dict21[word]:
                    foundCount += segment1.count( rWord )
                if wordCount > foundCount:
                    awResults.append( (reference,"Word matches for {!r} not enough ({}/{}) in {!r}".format( word, wordCount, foundCount, segment1 )) )
                #elif wordCount < foundCount:
                    #awResults.append( (reference,"Word matches for {!r} exceeded ({}/{}) in {!r}".format( word, wordCount, foundCount, segment2 )) )

    #print( '\nawResults', len(awResults), awResults )
    return awResults

    wordDict1, wordDict2 = {}, {}
    for j,(segment1,segment2) in enumerate( segmentList ):
        for word1 in segment1:
            if word1 not in wordDict1:
                print( "Processing {} {!r}…".format( j, word1 ) )
                #wordDict1[word1] = []
                options = {}
                wordSet = set( segment2 )
                for segment1b,segment2b in segmentList[j+1:]:
                    if word1 in segment1b:
                        wordSet = wordSet.intersection( segment2b )
                        if len(wordSet) == 1:
                            print( word1, wordSet )
                            wordDict1[word1] = wordSet.pop()
                            break
        #if j > 5: break
    print( len(wordDict1), wordDict1 )
    halt
# end of analyzeWords


def analyzeBibles( Bible1, Bible2 ):
    """
    Given two Bible objects, break the two into words
        and return a dictionary.

    This is typically used to compare a translation and a matching back-translation.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being BCV and error message.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("analyzeBibles( {}, {} )").format( Bible1, Bible2 ) )
        assert isinstance( Bible1, Bible )
        assert isinstance( Bible2, Bible )
        assert Bible1.abbreviation != Bible2.abbreviation or Bible1.name != Bible2.name
        assert Bible1.discoveryResults
        assert Bible2.discoveryResults
    if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Running analyzeBibles…") )

    bSegmentList, bResults = {}, {}

    len1, len2 = len(Bible1), len(Bible2)
    commonBooks = []
    for bBook in Bible1:
        if bBook.BBB in Bible2: commonBooks.append( bBook.BBB )
    numBooks = len( commonBooks )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( exp("Running segmentizeBooks on both Bibles…") )
    # TODO: Work out why multiprocessing is slower here -- yes, coz it has to pickle and unpickle entire Bible books
    if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Check all the books as quickly as possible
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( exp("Comparing {} books using {} CPUs…").format( numBooks, BibleOrgSysGlobals.maxProcesses ) )
            print( "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
        with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            results = pool.map( _doCompare, [(BBB,Bible1,Bible2) for BBB in commonBooks] ) # have the pool do our loads
            assert len(results) == numBooks
            for j,BBB in enumerate( commonBooks ):
                bResults[BBB] = results[j] # Saves them in the correct order
    else: # Just single threaded
        for BBB in commonBooks: # Do individual book prechecks
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + exp("Comparing {}…").format( BBB ) )
            bSegmentList[BBB], bResults[BBB] = segmentizeBooks( Bible1[BBB], Bible2[BBB] ) #, abResults1, abResults2 )
            print( BBB, bSegmentList[BBB] )
            print( BBB, bResults[BBB] )
    return bResults
# end of analyzeBibles



def compareBibles( Bible1, Bible2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalStrings1=DEFAULT_ILLEGAL_STRINGS_1, # Case sensitive
                        illegalStrings2=DEFAULT_ILLEGAL_STRINGS_2, # Case sensitive
                        matchingPairs=DEFAULT_MATCHING_PAIRS,
                        breakOnOne=False ):
    """
    Runs a series of checks and count on each book of the Bible
        in order to try to determine what are the normal standards.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule: print( exp("compareBibles( {}, {} )").format( Bible1, Bible2 ) )
        assert isinstance( Bible1, Bible )
        assert isinstance( Bible2, Bible )
        assert Bible1.abbreviation != Bible2.abbreviation or Bible1.name != Bible2.name
    if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Running compareBibles…") )

    len1, len2 = len(Bible1), len(Bible2)
    commonBooks = []
    for bBook in Bible1:
        if bBook.BBB in Bible2: commonBooks.append( bBook.BBB )
    numBooks = len( commonBooks )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( exp("Running compareBooksPedantic on both Bibles…") )
    bResults = OrderedDict()
    # TODO: Work out why multiprocessing is slower here -- yes, coz it has to pickle and unpickle entire Bible books
    if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Check all the books as quickly as possible
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( exp("Comparing {} books using {} CPUs…").format( numBooks, BibleOrgSysGlobals.maxProcesses ) )
            print( "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
        with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            results = pool.map( _doCompare, [(BBB,Bible1,Bible2) for BBB in commonBooks] ) # have the pool do our loads
            assert len(results) == numBooks
            for j,BBB in enumerate( commonBooks ):
                bResults[BBB] = results[j] # Saves them in the correct order
    else: # Just single threaded
        for BBB in commonBooks: # Do individual book prechecks
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + exp("Comparing {}…").format( BBB ) )
            bResults[BBB] = compareBooksPedantic( Bible1[BBB], Bible2[BBB], compareQuotes=compareQuotes,
                                                comparePunctuation=comparePunctuation, compareDigits=compareDigits,
                                                illegalStrings1=illegalStrings1, illegalStrings2=illegalStrings2,
                                                matchingPairs=matchingPairs, breakOnOne=breakOnOne )
    return bResults
# end of compareBibles



def demo():
    """
    Demonstration program to handle command line parameters and then run what they want.
    """
    from USFMBible import USFMBible
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} Demo".format( ProgNameVersion ) )

    # Load a USFM Bible and BT
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nLoading USFM Bible…" )
    name1, encoding1, testFolder1 = "MBTV", 'utf-8', "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your test folder here
    name2, encoding2, testFolder2 = "MS-BT", 'utf-8', "../../../../../Data/Work/Matigsalug/Bible/MBTBT/" # You can put your test folder here
    MS_ILLEGAL_STRINGS_1 = ( 'c','f','j','o','q','v','x','z', ) + DEFAULT_ILLEGAL_STRINGS_1
    MS_ILLEGAL_STRINGS_2 = ( 'We ',' we ',' us ',' us.',' us,',' us:',' us;',' us!',' us?',' us–',' us—',
                             'Our ',' our ','You ','you ','you.','you,','you:','you;','you!','you?','you–','you—',
                             'Your ','your ','yours ',' the the ', ) + DEFAULT_ILLEGAL_STRINGS_2

    if os.access( testFolder1, os.R_OK ):
        UB1 = USFMBible( testFolder1, name1, encoding1 )
        UB1.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( UB1 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB1.check()
        #UB1.doAllExports( "OutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testFolder1 ) )

    if os.access( testFolder2, os.R_OK ):
        UB2 = USFMBible( testFolder2, name2, encoding2 )
        UB2.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( UB2 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB2.check()
        #UB2.doAllExports( "OutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testFolder2 ) )

    if 0: # Test one book
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nTesting one book only…" )
        BBB = 'JDE'
        result = compareBooksPedantic( UB1[BBB], UB2[BBB], illegalStrings1=MS_ILLEGAL_STRINGS_1, illegalStrings2=MS_ILLEGAL_STRINGS_2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Comparing {} gave:".format( BBB ) )
            print( ' ', result )

    if 1: # Test the whole Bibles
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nTesting for whole Bible…" )
        results = compareBibles( UB1, UB2, illegalStrings1=MS_ILLEGAL_STRINGS_1, illegalStrings2=MS_ILLEGAL_STRINGS_2 )
        totalCount = resultsBooksCount = 0
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    resultsBooksCount += 1
                    totalCount += len( bookResults )
                    print( '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                    for (C,V,marker),resultString in bookResults:
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        print( '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            print( "{} total results in {} books (out of {})".format( totalCount, resultsBooksCount, len(UB1) ) )

    if 0: # Compare one book
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nAnalyzing one book only…" )
        BBB = 'JDE'
        segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Comparing {} gave:".format( BBB ) )
            #print( ' 1s', len(segmentResult), segmentResult )
            print( ' 2o', len(otherResult), otherResult )
        dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'BTCheckWords.txt' )
        awResult = analyzeWords( segmentResult, dict12, dict21 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Comparing {} gave:".format( BBB ) )
            print( '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
            for (C,V,marker),resultString in awResult:
                resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                print( '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
            print( "{:,} results in {}".format( len(awResult), BBB ) )

    if 0: # Compare the whole Bibles
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nAnalyzing whole Bible…" )
        totalSegments = totalCount = 0
        for BBB in UB1.getBookList():
            segmentResult, otherResult = segmentizeBooks( UB1[BBB], UB2[BBB] )
            totalSegments += len( segmentResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "Comparing {} gave:".format( BBB ) )
                #print( ' 1s', len(segmentResult), segmentResult )
                print( ' 2o', len(otherResult), otherResult )
            dict12, dict21 = loadWordCompares( 'Tests/DataFilesForTests', 'BTCheckWords.txt' )
            awResult = analyzeWords( segmentResult, dict12, dict21 )
            totalCount += len( awResult )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( '\n{} ({} vs {}):'.format( BBB, name1, name2 ) )
                for (C,V,marker),resultString in awResult:
                    resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                    print( '  {} {}:{} {} {}'.format( BBB, C, V, marker, resultString ) )
                print( "  {:,} results in {}".format( len(awResult), BBB ) )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "{:,} total results in {} books ({:,} segments)".format( totalCount, len(UB1), totalSegments ) )

# end of demo


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    from UnknownBible import UnknownBible
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.print( BibleOrgSysGlobals.commandLineArguments )

    fp1, fp2 = BibleOrgSysGlobals.commandLineArguments.Bible1, BibleOrgSysGlobals.commandLineArguments.Bible2
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Bible1 filepath {!r} is invalid—aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Bible2 filepath {!r} is invalid—aborting".format( fp2 ) ); allOkay = False

    if allOkay:
        UnkB1 = UnknownBible( fp1 )
        result1 = UnkB1.search( autoLoadAlways=True, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Bible1 loaded", result1 )
        if isinstance( result1, Bible ):
            Bible1 = result1
        else:
            logging.critical( "Unable to load Bible1 from {!r}—aborting".format( fp1 ) ); allOkay = False
    if allOkay:
        UnkB2 = UnknownBible( fp2 )
        result2 = UnkB2.search( autoLoadAlways=True, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Bible2 loaded", result2 )
        if isinstance( result2, Bible ):
            Bible2 = result2
        else:
            logging.critical( "Unable to load Bible2 from {!r}—aborting".format( fp2 ) ); allOkay = False

    if allOkay:
        results = compareBibles( Bible1, Bible2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            name1 = Bible1.abbreviation if Bible1.abbreviation else Bible1.name
            name2 = Bible2.abbreviation if Bible2.abbreviation else Bible2.name
            print( "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    print( '\n{}:'.format( BBB ) )
                    for result in bookResults:
                        C, V, resultString = result[0][0], result[0][1], result[1]
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        print( '{}:{} {}'.format( C, V, resultString ) )
            #print( results )
# end of main


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    #parser.add_argument('Bible1', help="Bible folder or file path 1" )
    #parser.add_argument('Bible2', help="Bible folder or file path 2" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of CompareBibles.py