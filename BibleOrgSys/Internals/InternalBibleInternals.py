#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InternalBibleInternals.py
#
# Module handling the internal objects for Bible books
#
# Copyright (C) 2010-2024 Robert Hunt
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
Module for defining and manipulating internal Bible objects including:

    InternalBibleExtra
    InternalBibleExtraList
        A list of InternalBibleExtras
            with internal data validation functions
            and with a str() function useful for debugging.

    InternalBibleEntry
    InternalBibleEntryList
        A list of InternalBibleEntries
            with internal data validation functions
            and with a str() function useful for debugging.

Some notes about internal formats:
    The BibleOrgSys internal format is based on
        ESFM (see https://Freely-Given.org/Software/BibleDropBox/ESFMBibles.html )
        which is turn is based on USFM 3 (see https://ubsicap.github.io/usfm/index.html).
    Each Bible book (including front and back matter) is stored in
        a separate InternalBibleBook object.
    Each "new line" type field is considered a separate line in
        a list of "lines" inside the book object.
        These are stored as InternalBible Entry fields
            inside the InternalBibleEntryList in the Bible book object.

        Three types of text fields can be retrieved from the InternalBibleEntry:
            1/ The full and complete ESFM/USFM text of the "line"
            2/ The adjusted text which has "note" fields
                (e.g., footnotes and cross-references) removed
            3/ The clean text which also has inline formatting
                (e.g., bold, bookname, word-of-Jesus) removed

        Notes are removed from the text and placed into a list of "extras"
            stored in an InternalBibleExtraList object.
        Each InternalBibleExtra contains an index back to the adjusted text
            (and hence that index must be adjusted if the text string is edited).

    The introduction is stored as chapter '-1'. (All our chapter and verse "numbers" are stored as strings.)
        (We allow for some rare printed Roman Catholic Bibles that have an actual chapter 0.)
"""
from gettext import gettext as _
from typing import Dict, List, Optional
import logging
import re

if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.USFM3Markers import USFM_ALL_TITLE_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, \
                        USFM_ALL_SECTION_HEADING_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS # OFTEN_IGNORED_USFM_HEADER_MARKERS
#from BibleReferences import BibleAnchorReference


LAST_MODIFIED_DATE = '2024-04-19' # by RJH
SHORT_PROGRAM_NAME = "BibleInternals"
PROGRAM_NAME = "Bible internals handler"
PROGRAM_VERSION = '0.88'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False
MAX_NONCRITICAL_ERRORS_PER_BOOK = 4


BOS_CUSTOM_CONTENT_MARKERS = ( 'c~', 'c#', 'v=', 'v~', 'p~', 'cl¤', 'vp#', )
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
BOS_PRINTABLE_MARKERS = USFM_ALL_TITLE_MARKERS + USFM_ALL_INTRODUCTION_MARKERS + USFM_ALL_SECTION_HEADING_MARKERS + ('v~', 'p~', ) # Should c~ and c# be in here???

# BOS_REGULAR_NESTING_MARKERS = USFM_ALL_SECTION_HEADING_MARKERS + ('c','v' ) # No need to nest s1 type markers (one line only expected)
BOS_REGULAR_NESTING_MARKERS = ('c','v')

BOS_CUSTOM_NESTING_MARKERS = ( 'headers', 'intro', 'ilist', 'chapters', 'list' )
"""
    intro       Inserted at the start of book introductions
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""
BOS_ALL_CUSTOM_MARKERS = BOS_CUSTOM_CONTENT_MARKERS + BOS_CUSTOM_NESTING_MARKERS

BOS_ALL_CUSTOM_NESTING_MARKERS = BOS_CUSTOM_NESTING_MARKERS + ('iot',)
"""
    intro       Inserted at the start of book introductions
    iot         Inserted before introduction outline (io markers) IF IT'S NOT ALREADY IN THE FILE
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""

BOS_NESTING_MARKERS = BOS_REGULAR_NESTING_MARKERS + BOS_ALL_CUSTOM_NESTING_MARKERS \
                            + USFM_BIBLE_PARAGRAPH_MARKERS + ('ms1','ms2','ms3')

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


def getLeadingInt( someString:str ) -> int:
    """
    Especially used for verse numbers like '17a' and ranges like 17-25

    Raises ValueError if no int found at the beginning of the string
    """
    # print( f"getLeadingInt( '{someString}' )…")
    reMatch = re.search( '^-?[0-9]*', someString ) # Can return None
    # print( f"{reMatch=}")
    return int(reMatch.group())
# end of getLeadingInt function


def parseWordAttributes( workName, BBB:str, C:str, V:str, wordAttributeString, errorList=None ) -> Dict[str,str]:
    """
    Take the attributes of a USFM3 \\w field (the attributes include the first pipe/vertical-bar symbol)
        and analyze them.

    Returns a dictionary of attributes.

    TODO: No error messages added yet ………………. XXXXXXXXXXXXXXXXXXXXXXX
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"parseWordAttributes( {workName}, {BBB} {C}:{V}, {wordAttributeString!r}, {errorList} )…" )
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE:
        assert isinstance( workName, str )
        assert isinstance( BBB, str )
        assert isinstance( wordAttributeString, str )
        assert wordAttributeString.count( '|' ) == 1
        assert errorList is None or isinstance( errorList, list )

    # if 1:
    #     import ctypes
    #     libInternals = ctypes.CDLL("./libInternals.so")

    #     #call C function to check connection
    #     libInternals.connect()

    #     #calling randNum() C function
    #     #it returns random number
    #     varRand = libInternals.randNum()
    #     print( "Random Number:", varRand, type(varRand) )

    #     #calling addNum() C function
    #     #it returns addition of two numbers
    #     varAdd = libInternals.addNum(20,30)
    #     print( "Addition : ", varAdd )

    #     libInternals.parseWordAttributes.restype = ctypes.c_wchar_p
    #     resultDict = libInternals.parseWordAttributes( ctypes.c_wchar_p(workName), ctypes.c_wchar_p(BBB), ctypes.c_wchar_p(C), ctypes.c_wchar_p(V), ctypes.c_wchar_p(wordAttributeString), ctypes.c_wchar_p(errorList) )
    # else:
    word, attributeString = wordAttributeString.split( '|', 1 )
    resultDict = { 'word':word }
    if '=' not in attributeString: # Assume it's a single (unnamed) lemma
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE:
            assert '"' not in attributeString and "'" not in attributeString
        resultDict['lemma'] = attributeString
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Returning1: {}".format( resultDict ) )
        return resultDict

    # Else most likely have named attributes
    # Use a state machine rather than regular expressions coz better for giving human-readable error messages
    state = 0
    name = value = quote = ''
    for j, char in enumerate( attributeString ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{j} char={char!r} state={state} name='{name}' value={value!r} quote={quote!r}" )
        if state == 0: # Ready to get attribute name
            if not char.isspace():
                if name:
                    assert value
                    resultDict[name] = value
                name = char
                value = quote = ''
                state = 1
        elif state == 1: # Getting attribute name
            if char.isalpha() or char in '-':
                name += char
            elif char == '=':
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "name", name )
                if name not in ('lemma','strong') \
                and not name.startswith( 'x-' ):
                    logging.error( f"{BBB} {C}:{V} unexpected '{name}' attribute for '{word}'" )
                if name.startswith( 'x-' ): name = name[2:] # Remove x- prefix for convenience
                state = 2
            else:
                logging.error( f"{BBB} {C}:{V} attribute '{name+char}' for '{word}' is invalid" )
        elif state == 2: # Ready to get attribute value
            if char=='"':
                quote = char
                state = 3
            else:
                value += char
                state = 3
        elif state == 3: # Getting attribute value -- stop at matching quote or space
            if char == quote \
            or ( quote=='' and char.isspace() ):
                assert name
                if not value:
                    logging.warning( f"{BBB} {C}:{V} attribute '{name}' for '{word}' is blank" )
                resultDict[name] = value
                name = value = quote = ''
                state = 0
            else:
                value += char
    if state == 3:
        assert name
        assert value
        resultDict[name] = value
        state = 0
    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        assert state == 0

    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"parseWordAttributes() returning: {resultDict}" )
    return resultDict
# end of parseWordAttributes



# 2 and 3 below refer to USFM2 and USFM3 standards for \fig entries
figureAttributeNames3 = ( 'alt', 'src', 'size', 'loc', 'copy', 'ref' )
betterAttributeNames3 = ( 'altDescription', 'sourceFilename', 'relativeSize', 'locationOrRange', 'copyrightOrRightsHolder', 'referenceCV' )
# The names for USFM2 are determined by position
figureAttributeNames2 = ( betterAttributeNames3[0], betterAttributeNames3[1], betterAttributeNames3[2], betterAttributeNames3[3], betterAttributeNames3[4], 'caption', betterAttributeNames3[5] )

def parseFigureAttributes( workName, BBB:str, C:str, V:str, figureAttributeString, errorList=None ):
    """
    Take the contents of a USFM2 or USFM3 \fig field and analyze them.

    In USFM2, the up-to-seven attributes are separated by vertical bars,
        i.e., \fig DESC|FILE|SIZE|LOC|COPY|CAP|REF\fig*

    In USFM3, the caption text comes first, then other parameters after a vertical bar,
        i.e., \fig caption text|src="filename" size="size" ref="reference"\fig*
        e.g., \fig At once they left their nets.|src="avnt016.jpg" size="span" ref="1.18"\fig*
        and, \fig Took her by the hand, and the fever left her.|src="avnt017.tif" size="col" ref="1.31"\fig*

    Returns a dictionary of attributes.

    NOTE: No error messages added yet ………………. XXXXXXXXXXXXXXXXXXXXXXX
    """
    fnPrint( DEBUGGING_THIS_MODULE, "parseFigureAttributes( {}, {} {}:{}, {!r}, {} )".format( workName, BBB, C, V, figureAttributeString, errorList ) )
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or DEBUGGING_THIS_MODULE:
        assert isinstance( workName, str )
        assert isinstance( BBB, str )
        assert isinstance( figureAttributeString, str )
        #assert figureAttributeString[0] == '|'
        assert errorList is None or isinstance( errorList, list )

    if figureAttributeString.count('|')==1 and '=' in figureAttributeString:
        # We'll assume USFM3
        caption, attributeString = figureAttributeString.split( '|', 1 )
        resultDict = { 'USFM':3, 'caption':caption }
        # Must have named attributes (src,size,ref are compulsory; alt,loc,copy are optional)
        # Use a state machine rather than regular expressions coz better for giving human-readable error messages
        state = 0
        name = value = quote = ''
        for j, char in enumerate( attributeString ):
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} char={!r} state={} name={!r} value={!r} quote={!r}".format( j, char, state, name, value, quote ) )
            if state == 0: # Ready to get attribute name
                if not char.isspace():
                    if name:
                        assert value
                        resultDict[name] = value
                    name = char
                    value = quote = ''
                    state = 1
            elif state == 1: # Getting attribute name
                if char.isalpha():
                    name += char
                elif char == '=':
                    assert name in figureAttributeNames3
                    name = betterAttributeNames3[figureAttributeNames3.index( name )] # Convert to better names
                    state = 2
            elif state == 2: # Ready to get attribute value
                if char=='"':
                    quote = char
                    state = 3
                else:
                    value += char
                    state = 3
            elif state == 3: # Getting attribute value -- stop at matching quote or space
                if char == quote \
                or ( quote==' ' and char.isspace() ):
                    assert name
                    assert value
                    resultDict[name] = value
                    name = value = quote = ''
                    state = 0
                else:
                    value += char
        if state == 3:
            assert name
            assert value
            resultDict[name] = value
            state = 0
        assert state == 0

    else: # we'll assume USFM2
        resultDict = {'USFM':2}
        bits = figureAttributeString.split( '|' )
        assert len(bits) <= len(figureAttributeNames2)
        for j, bit in enumerate( bits ):
            resultDict[figureAttributeNames2[j]] = bit

    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Returning: {}".format( resultDict ) )
    return resultDict
# end of parseFigureAttributes



class InternalBibleExtra:
    """
    This class represents an entry in the InternalBibleExtraList.

    Each object/entry represents a note or cross-reference or other inserted object
        not normally printed in-line in the mainstream verse text.

    Each object/entry contains an index back to the adjusted text
        (and hence that index must be adjusted if the text string is edited).
    """
    __slots__ = ('myType', 'index', 'noteText', 'cleanNoteText') # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, myType, indexToAdjText, noteText, cleanNoteText, location ) -> None:
        """
        Accept the parameters and double-check them if requested.

        location parameter is just for better error messages and is not currently stored.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "InternalBibleExtra.__init__( {}, {}, {!r}, {!r}, {} )".format( myType, indexToAdjText, noteText, cleanNoteText, location ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert myType and isinstance( myType, str ) and myType in BOS_EXTRA_TYPES # Mustn't be blank
            assert '\\' not in myType and ' ' not in myType and '*' not in myType
            assert isinstance( indexToAdjText, int ) and indexToAdjText >= 0
            assert noteText and isinstance( noteText, str ) # Mustn't be blank
            assert '\n' not in noteText and '\r' not in noteText
            for letters in ( 'f', 'x', 'fe', 'ef' ): # footnote, cross-ref, endnotes, studynotes
                assert '\\'+letters+' ' not in noteText
                assert '\\'+letters+'*' not in noteText
            assert isinstance( cleanNoteText, str )
            if DEBUGGING_THIS_MODULE: assert cleanNoteText # Mustn't be blank
            assert '\\' not in cleanNoteText and '\n' not in cleanNoteText and '\r' not in cleanNoteText
        self.myType, self.index, self.noteText, self.cleanNoteText = myType, indexToAdjText, noteText, cleanNoteText
    # end of InternalBibleExtra.__init__


    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a very abbreviated form of the entry.
        """
        return "InternalBibleExtra object: {} @ {} = {}".format( self.myType, self.index, repr(self.noteText) )
    # end of InternalBibleExtra.__str__


    def __len__( self ): return 4
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.myType
        elif keyIndex==1: return self.index
        elif keyIndex==2: return self.noteText
        elif keyIndex==3: return self.cleanNoteText
        else: raise IndexError
    # end of InternalBibleExtra.__getitem__

    def getType( self ): return self.myType
    def getIndex( self ): return self.index
    def getText( self ): return self.noteText
    def getCleanText( self ): return self.cleanNoteText
# end of class InternalBibleExtra



class InternalBibleExtraList:
    """
    This class is a specialised list for holding InternalBibleExtras

    (It's mainly here for extra data validation and the str function for debugging.)
    """
    __slots__ = ('data',) # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, initialData=None ) -> None:
        """
        """
        self.data = []
        if initialData is not None:
            if isinstance( initialData, list ) or isinstance( initialData, InternalBibleExtraList ):
                for something in initialData:
                    self.append( something )
            else: logging.critical( "InternalBibleExtraList.__init__: Programming error -- unknown parameter type {}".format( repr(initialData) ) )
        if initialData: assert len(self.data) == len(initialData)
        else: assert not self.data
    # end of InternalBibleExtraList.__init__


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the list of entries.

        Only prints the first maxPrinted lines.
        """
        maxPrinted = 20
        result = "InternalBibleExtraList object:"
        if not self.data: result += "\n  Empty."
        else:
            dataLen = len( self.data )
            for j, entry in enumerate( self.data ):
                if BibleOrgSysGlobals.debugFlag: assert isinstance( entry, InternalBibleExtra )
                result += "\n  {}{} {} @ {} = {}".format( ' ' if j<9 and dataLen>=10 else '', j+1, entry.myType, entry.index, repr(entry.noteText) )
                if j>=maxPrinted and dataLen>maxPrinted:
                    result += "\n  … ({} total entries)".format( dataLen )
                    break
        return result
    # end of InternalBibleExtraList.__str__

    def __len__( self ): return len( self.data )
    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ki2", keyIndex )
            #assert keyIndex.step is None
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "param", *keyIndex.indices(len(self)) )
            return InternalBibleExtraList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        return self.data[keyIndex]
    # end of InternalBibleExtraList.__getitem__


    def summary( self ):
        """
        Like __str__ but just returns a (possibly abbreviated) one-line string summary.
        """
        if not self.data: return "NO_EXTRAS"
        if len( self.data ) == 1:
            entry = self.data[0]
            return "EXTRA( {} @ {} = {})".format( entry.myType, entry.index, repr(entry.noteText) )
        # Multiple extras
        resultString = "EXTRAS( "
        for j, entry in enumerate( self.data ):
            resultString += "{}{} @ {}".format( ", " if j>0 else "", entry.myType, entry.index )
        return resultString + " )"
    # end of InternalBibleExtraList.summary

    def fullSummary( self ):
        """
        Like __str__ and summary, but returns a long one-line string summary.
        """
        if not self.data: return "NO_EXTRAS"
        if len( self.data ) == 1:
            entry = self.data[0]
            return "EXTRA( {} @ {} = {})".format( entry.myType, entry.index, repr(entry.noteText) )
        # Multiple extras
        resultString = "EXTRAS( "
        for j, entry in enumerate( self.data ):
            resultString += "{}{}@{}={}".format( ", " if j>0 else "", entry.myType, entry.index, repr(entry.noteText) )
        return resultString + " )"
    # end of InternalBibleExtraList.summary

    def append( self, newExtraEntry ):
        assert isinstance( newExtraEntry, InternalBibleExtra )
        self.data.append( newExtraEntry )
    # end of InternalBibleExtraList.append

    def pop( self ): # Doesn't allow a parameter
        try: return self.data.pop()
        except IndexError: return None
    # end of InternalBibleExtraList.append

    def extend( self, newExtraList ):
        assert isinstance( newExtraList, InternalBibleExtraList )
        self.data.extend( newExtraList )
    # end of InternalBibleExtraList.extend

    def checkForIndex( self, stringIndex ):
        """
        See if there's an extra at this point in the source string

        If more than one, returns a list.
        If only one, return the extra
        If none, return None.
        """
        resultList = []
        for extra in self.data:
            if extra.getIndex() == stringIndex: resultList.append( extra )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "checkForIndex( {} ) resultList = {}".format( stringIndex, resultList ) )
        if resultList:
            if len(resultList) == 1: return resultList[0]
            return resultList
        return None
# end of class InternalBibleExtraList



class InternalBibleEntry:
    """
    This class represents an entry in the InternalBibleEntryList (_processedLines).

    Each entry holds the original and adjusted markers (e.g., \\s will be adjusted to \\s1)
        plus the cleanText with notes, etc. removed and stored in the "extras" list.
    """
    __slots__ = ('marker', 'originalMarker', 'adjustedText', 'cleanText', 'extras', 'originalText') # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, marker:str, originalMarker:str,
                        adjustedText:str, cleanText:str,
                        extras:Optional[InternalBibleExtraList], originalText:str ) -> None:
        """
        Accept the parameters and double-check them if requested.

        Normally all of the parameters are strings.
        But for end markers, only the marker parameter and cleanText are strings
            and the other parameters must all be None.
        """
        if cleanText is not None and '\\' in cleanText:
            logging.error( "InternalBibleEntry expects clean text not {}={}".format( marker, repr(cleanText) ) )
        #if 'it*' in originalText and 'it*' not in adjustedText:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleEntry constructor had problem with it* (probably in a footnote) in {} {} {}".format( marker, repr(originalText), repr(adjustedText) ) )
            #halt
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleEntry.__init__( {}, {}, {!r}, {!r}, {}, {!r} )" \
                    #.format( marker, originalMarker, adjustedText[:35]+('…' if len(adjustedText)>35 else ''), \
                        #cleanText[:35]+('…' if len(cleanText)>35 else ''), extras, \
                        #originalText[:35]+('…' if len(originalText)>35 else '') ) )
            assert marker and isinstance( marker, str ) # Mustn't be blank
            assert '\\' not in marker and ' ' not in marker and '*' not in marker
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, marker, "cleanText", repr(cleanText) )
            assert isinstance( cleanText, str )
            assert '\n' not in cleanText and '\r' not in cleanText

            if marker[0] == '¬' \
            or marker in BOS_ALL_CUSTOM_NESTING_MARKERS and originalMarker is None: # It's an end marker or an added marker
                assert originalMarker is None and adjustedText is None and extras is None and originalText is None
            else: # it's not an end marker
                assert originalMarker and isinstance( originalMarker, str ) # Mustn't be blank
                assert '\\' not in originalMarker and ' ' not in originalMarker and '*' not in originalMarker
                assert isinstance( adjustedText, str ), f"{type(adjustedText)=} {adjustedText=}"
                assert '\n' not in adjustedText and '\r' not in adjustedText
                if '\\' in cleanText:
                    logging.critical( "Clean text {!r} at {} from {!r}".format( cleanText, marker, originalText ) )
                assert '\\' not in cleanText
                assert extras is None or isinstance( extras, InternalBibleExtraList )
                assert isinstance( originalText, str )
                assert '\n' not in originalText and '\r' not in originalText
                #assert marker in BibleOrgSysGlobals.loadedUSFMMarkers or marker in BOS_CUSTOM_CONTENT_MARKERS
                if marker not in BibleOrgSysGlobals.loadedUSFMMarkers and marker not in BOS_CUSTOM_CONTENT_MARKERS:
                    logging.warning( "InternalBibleEntry doesn't handle {!r} marker yet.".format( marker ) )
        self.marker, self.originalMarker, self.adjustedText, self.cleanText, self.extras, self.originalText = marker, originalMarker, adjustedText, cleanText, extras, originalText

        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE \
        and self.originalText is not None and self.getFullText() != self.originalText.strip():
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleEntry.Full", repr(self.getFullText()) ) # Has footnote in wrong place on verse numbers (before instead of after)
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleEntry.Orig", repr(self.originalText.strip()) ) # Has missing footnotes on verse numbers
            #halt # When does this happen?
    # end of InternalBibleEntry.__init__


    def __eq__( self, other ): # If we don't have this defined, a==b does a is b.
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(self) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(other) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, isinstance( other, self.__class__ ) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.__dict__ == other.__dict__ )
        #for someKey, someItem in sorted( self.__dict__.items() ):
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'self', someKey, repr(someItem) )
        #for someKey, someItem in sorted( other.__dict__.items() ):
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'other', someKey, repr(someItem) )
        #halt
        return isinstance( other, self.__class__ ) and self.__dict__ == other.__dict__
    def __ne__( self, other ):
        return not self.__eq__( other )


    def __str__( self ) -> str:
        """
        Just display a very abbreviated form of the entry.
        """
        abbreviatedCleanText = self.cleanText if len(self.cleanText)<100 else (self.cleanText[:50]+'…'+self.cleanText[-50:])
        return 'InternalBibleEntry object: {} = {!r}{}'.format( self.marker, abbreviatedCleanText, '+extras' if self.extras else '' )
    # end of InternalBibleEntry.__str__


    def __repr__( self ) -> str:
        """
        Display a fuller form of the entry.
        """
        abbreviatedAdjText = self.adjustedText if self.adjustedText is None or len(self.adjustedText)<100 \
                                else (self.adjustedText[:50]+'…'+self.adjustedText[-50:])
        abbreviatedCleanText = self.cleanText if self.cleanText is None or len(self.cleanText)<100 \
                                else (self.cleanText[:50]+'…'+self.cleanText[-50:])
        abbreviatedOrigText = self.originalText if self.originalText is None or len(self.originalText)<100 \
                                else (self.originalText[:50]+'…'+self.originalText[-50:])
        return 'InternalBibleEntry object:' \
            + '\n    {} = {!r}'.format( self.marker, abbreviatedCleanText ) \
            + ('\n  from Original {} = {!r}'.format( self.originalMarker, abbreviatedOrigText ) if self.originalMarker!=self.marker or self.originalText!=self.cleanText else '' ) \
            + ('\n          adjusted to {!r}'.format( abbreviatedAdjText ) if self.adjustedText!=self.originalText else '' ) \
            + ('\n         with {}'.format( self.extras ) if self.extras else '' )
    # end of InternalBibleEntry.__repr__


    def __len__( self ) -> int: return 6 # marker, originalMarker, adjustedText, cleanText, extras, originalText
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.marker
        elif keyIndex==1: return self.originalMarker
        elif keyIndex==2: return self.adjustedText
        elif keyIndex==3: return self.cleanText
        elif keyIndex==4: return self.extras
        elif keyIndex==5: return self.originalText
        else: raise IndexError( 'Invalid {} index number'.format( keyIndex ) )
    # end of InternalBibleEntry.__getitem__

    def getMarker( self ): return self.marker
    def getOriginalMarker( self ): return self.originalMarker
    def getAdjustedText( self ): return self.adjustedText # Notes are removed
    def getText( self ): return self.adjustedText # Notes are removed
    def getCleanText( self, removeESFMUnderlines=False ): # Notes and character formats are removed
        if removeESFMUnderlines:
            return self.cleanText.replace('_ _',' ').replace('_ ',' ').replace(' _',' ').replace('_',' ')
        else: return self.cleanText # Notes and formatting are removed
    def getExtras( self ): return self.extras
    def getOriginalText( self ): return self.originalText


    def getFullText( self ):
        """
        Returns the full text with footnotes and cross-references reinserted.
        Also has figures, word attributes and vp fields reinserted.

        Note that some spaces may not be recovered,
            e.g., in 'lamb\f + \fr 18.9 \ft Sheep \f* more text here'
            the space before the close of the footnote is not restored!
        Otherwise it should be identical to the original text.
        """
        return self.originalText
        # else: # re-create it
        #     result = self.adjustedText # Can be None for our inserted end markers, e.g., ¬v
        #     dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getFullText() got adjustedText: {!r}".format( self.adjustedText ) )
        #     dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  (Clean text is {!r})".format( self.cleanText ) )
        #     offset = 0
        #     if self.extras:
        #         for extraType, extraIndex, extraText, cleanExtraText in self.extras: # do any footnotes and cross-references
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getFullText: {} at {} = {!r} ({})".format( extraType, extraIndex, extraText, cleanExtraText ) )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getFullText:  was {!r}".format( result ) )
        #             ix = extraIndex + offset
        #             if extraType == 'fn': USFM, lenUSFM = 'f', 1
        #             elif extraType == 'en': USFM, lenUSFM = 'fe', 2
        #             elif extraType == 'xr': USFM, lenUSFM = 'x', 1
        #             elif extraType == 'fig': USFM, lenUSFM = 'fig', 3
        #             elif extraType == 'str': USFM, lenUSFM = 'str', 3
        #             elif extraType == 'sem': USFM, lenUSFM = 'sem', 3
        #             elif extraType == 'ww': USFM, lenUSFM = 'ww', 2
        #             elif extraType == 'vp': USFM, lenUSFM = 'vp', 2
        #             elif BibleOrgSysGlobals.debugFlag: halt # Unknown extra field type!!!
        #             if USFM:
        #                 result = '{}\\{} {}\\{}*{}'.format( result[:ix], USFM, extraText, USFM, result[ix:] )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getFullText:  now {!r}".format( result ) )
        #             offset += len(extraText ) + 2*lenUSFM + 4
        #         # The following code is WRONG coz the word ends up getting reduplicated (coz it's also repeated inside the \ww field)
        #         #result = result.replace( '\\w*\\ww ', '' ).replace( '\\ww*', '\\w*' ) # Put attributes back inside \w field
        #         result = re.sub( '\\\\w (.+?)\\\\w\\*', '', result ) # Remove all \w …\w* fields
        #         result = result.replace( '\\ww ', '\\w ' ).replace( '\\ww*', '\\w*' ) # Convert full \ww fields back to \w fields now

        #     if result != self.adjustedText:
        #         if len(self.extras) > 1:
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nWas {!r}".format( self.cleanText ) )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "And {!r}".format( self.adjustedText ) )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Orig{!r}".format( self.originalText ) )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Now {!r}".format( result ) )
        #             dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Extras are {}".format( self.extras ) )
        #     if result is not None and result != self.originalText.strip():
        #         dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nWe're giving {!r}".format( result ) )
        #         dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "   Should be {!r}".format( self.originalText.strip() ) )
        #         dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "        From {!r}".format( self.originalText ) )
        #     if BibleOrgSysGlobals.debugFlag and self.originalText is not None: assert result == self.originalText.strip()
        #     return result
    # end of InternalBibleEntry.getFullText


    def setCleanText( self, newValue:str ) -> None:
        """
        Allows the entry to be changed
            if it has no extras
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleEntry.setCleanText( {newValue} ) for {self.marker}" )
        assert not self.extras
        self.cleanText = self.adjustedText = self.originalText = newValue
    # end of InternalBibleEntry.setCleanText
# end of class InternalBibleEntry



class InternalBibleEntryList:
    """
    This class is a specialised list for holding InternalBibleEntries
        so _processedLines is one of these.

    (It's mainly here for extra data validation and the str function for debugging.)
    """
    __slots__ = ('data',) # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, initialData=None ) -> None:
        """
        """
        self.data = []
        if initialData is not None:
            if isinstance( initialData, list ) or isinstance( initialData, InternalBibleEntryList ):
                # TODO: Can this be more efficient with self.data.extend ???
                for something in initialData:
                    self.append( something )
            else: logging.critical( "InternalBibleEntryList.__init__: Programming error -- unknown parameter type {}".format( repr(initialData) ) )
        if initialData: assert len(self.data) == len(initialData)
        else: assert not self.data
    # end of InternalBibleEntryList.__init__


    #def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        #return False
    #def __ne__(self, other): return not self.__eq__(other)


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the list of entries.

        Only prints the first maxPrinted lines.
        """
        maxPrinted = 50 if DEBUGGING_THIS_MODULE else 20
        result = "InternalBibleEntryList object:"
        if not self.data: result += "\n  Empty."
        else:
            dataLen = len( self.data )
            for j, entry in enumerate( self.data ):
                if BibleOrgSysGlobals.debugFlag: assert isinstance( entry, InternalBibleEntry )
                cleanAbbreviation = entry.cleanText if entry.cleanText is None or len(entry.cleanText)<100 \
                                                    else (entry.cleanText[:50]+'…'+entry.cleanText[-50:])
                result += "\n  {}{}/ {} = {}{}" \
                            .format( ' ' if j<9 and dataLen>=10 else '',
                                    j,
                                    entry.marker,
                                    repr(cleanAbbreviation),
                                    " + extras" if entry.extras else '' )
                if j+1>=maxPrinted and dataLen>maxPrinted:
                    result += "\n  … ({:,} total Bible index entries)".format( dataLen )
                    break
        return result
    # end of InternalBibleEntryList.__str__


    def __len__( self ): return len( self.data )
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ki2", keyIndex )
            #assert keyIndex.step is None
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "param", *keyIndex.indices(len(self)) )
            return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        return self.data[keyIndex]
    # end of InternalBibleEntryList.__getitem__


    def append( self, newBibleEntry ) -> None:
        """
        Append the newBibleEntry to the InternalBibleEntryList.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleEntryList.append( {newBibleEntry} )" )
        assert isinstance( newBibleEntry, InternalBibleEntry )
        self.data.append( newBibleEntry )
    # end of InternalBibleEntryList.append

    def pop( self ): # Doesn't allow a parameter
        """
        Return the last InternalBibleEntry from the InternalBibleEntryList
            or None if the InternalBibleEntryList is empty.
        """
        try: return self.data.pop()
        except IndexError: return None
    # end of InternalBibleEntryList.pop

    def extend( self, additionalList ) -> None:
        """
        Extend the InternalBibleEntryList with the newList given.
        """
        assert isinstance( additionalList, InternalBibleEntryList )
        self.data.extend( additionalList )
    # end of InternalBibleEntryList.extend
    def __add__( self, listToAppend ):
        """
        So we can use Python + operator to add lists (e.g., to combine verses)
        """
        assert isinstance( listToAppend, InternalBibleEntryList ), f"__add__ {type(listToAppend)=} {listToAppend=}"
        self.data.extend( listToAppend )
        return self
    # end of InternalBibleEntryList.__add__


    def contains( self, searchMarker, maxLines=None ):
        """
        Search some or all of the entries and return the index of the first line containing the given marker.

        maxLines is the integer maxLines to search
            or None to search them all (very slow).

        Returns None if no match is found
        """
        for j,entry in enumerate( self.data ):
            if entry.marker == searchMarker: return j
            if maxLines is not None:
                if j >= maxLines: break
    # end of InternalBibleEntryList.contains
# end of class InternalBibleEntryList



def briefDemo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    # from pathlib import Path
    global DEBUGGING_THIS_MODULE

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since these are only helper classes, they can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    # if 0: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
    #     import os
    #     from BibleOrgSys.Formats.USFMBible import USFMBible

    #     testData = ( # name, abbreviation, folderpath for USFM files
    #             ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
    #             ) # You can put your USFM test folder here

    #     for j, (name, abbrev, testFolder) in enumerate( testData ):
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleInternals B{j+1}/ {abbrev} from {testFolder}…" )
    #         if os.access( testFolder, os.R_OK ):
    #             UB = USFMBible( testFolder, name, abbrev )
    #             UB.load()
    #             UB.discover() # Why does this only help if -1 flag is enabled???
    #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
    #             if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
    #             #DEBUGGING_THIS_MODULE = False
    #             for BBB,bookObject in UB.books.items():
    #                 bookObject._SectionIndex = InternalBibleBookSectionIndex( bookObject )
    #                 bookObject._SectionIndex.makeBookSectionIndex()
    #                 if BBB=='GEN': halt
    #         else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleInternals.briefDemo


def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    global DEBUGGING_THIS_MODULE

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Since these are only helper classes, they can't actually do much at all." )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    resultDict = parseWordAttributes('testWork', 'GEN','1','2', 'word|x=pos="noun"')
    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"resultDict = {resultDict}" )
    assert resultDict == {'word': 'word', 'x': 'pos="noun"'}

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    # if 0: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
    #     import os
    #     from BibleOrgSys.Formats.USFMBible import USFMBible

    #     testData = ( # name, abbreviation, folderpath for USFM files
    #             ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
    #             ) # You can put your USFM test folder here

    #     for j, (name, abbrev, testFolder) in enumerate( testData ):
    #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleInternals B{j+1}/ {abbrev} from {testFolder}…" )
    #         if os.access( testFolder, os.R_OK ):
    #             UB = USFMBible( testFolder, name, abbrev )
    #             UB.load()
    #             UB.discover() # Why does this only help if -1 flag is enabled???
    #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
    #             if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
    #             #DEBUGGING_THIS_MODULE = False
    #             for BBB,bookObject in UB.books.items():
    #                 bookObject._SectionIndex = InternalBibleBookSectionIndex( bookObject )
    #                 bookObject._SectionIndex.makeBookSectionIndex()
    #                 if BBB=='GEN': halt
    #         else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleInternals.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleInternals.py
