#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InternalBibleInternals.py
#
# Module handling the internal objects for Bible books
#
# Copyright (C) 2010-2018 Robert Hunt
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

    InternalBibleIndexEntry
    InternalBibleIndex
        Everything before chapter 1 is considered chapter 0.
        The first line in chapter 0 is considered verse 0
            and each successive line has a successive verse number.
        Everything before verse 1 in regular chapters
            is considered as verse 0, e.g., many section headings, etc.

Some notes about internal formats:
    The BibleOrgSys internal format is based on
        ESFM (see http://Freely-Given.org/Software/BibleDropBox/ESFMBibles.html )
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
"""

from gettext import gettext as _

LastModifiedDate = '2018-01-11' # by RJH
ShortProgName = "BibleInternals"
ProgName = "Bible internals handler"
ProgVersion = '0.71'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False
MAX_NONCRITICAL_ERRORS_PER_BOOK = 4


import logging
from collections import OrderedDict

import BibleOrgSysGlobals
from USFMMarkers import USFM_TITLE_MARKERS, USFM_INTRODUCTION_MARKERS, \
                        USFM_SECTION_HEADING_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS # OFTEN_IGNORED_USFM_HEADER_MARKERS
#from BibleReferences import BibleAnchorReference



BOS_ADDED_CONTENT_MARKERS = ( 'c~', 'c#', 'v~', 'p~', 'cl¤', 'vp#', )
"""
    c~  anything after the chapter number on a \c line is split off into here --
            note that it can be blank (but have extras) if the chapter number is footnoted
    c#  the chapter number in the correct position to be printed
            This is usually a duplicate of the c field, but may have come from the cp field instead
            Usually only one of c or c# is used for exports
    v~  verse text -- anything after the verse number on a \v line is split off into here
    p~  verse text -- anything that was on a paragraph line (e.g., \p, \q, \q2, etc.) is split off into here
    cl¤ used to rename cl markers BEFORE the '\c 1' marker --
                            represents the text for "chapter" (e.g., Psalm) to be used throughout the book
        cl markers AFTER the '\c 1' marker remain unchanged (the text for the individual chapter/psalm heading)
    vp# used for the vp (character field) when it is copied and converted to a separate (newline) field
            This is inserted BEFORE the v (and v~) marker(s) that contained the vp (character) field.

    NOTE: Don't use any of the following symbols here: = ¬ or slashes.
"""
BOS_PRINTABLE_MARKERS = USFM_TITLE_MARKERS + USFM_INTRODUCTION_MARKERS + USFM_SECTION_HEADING_MARKERS + ('v~', 'p~', ) # Should c~ and c# be in here???

BOS_REGULAR_NESTING_MARKERS = USFM_SECTION_HEADING_MARKERS + ('c','v' )

BOS_ADDED_NESTING_MARKERS = ( 'intro', 'ilist', 'chapters', 'list', )
"""
    intro       Inserted at the start of book introductions
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""
BOS_ALL_ADDED_MARKERS = BOS_ADDED_CONTENT_MARKERS + BOS_ADDED_NESTING_MARKERS

BOS_ALL_ADDED_NESTING_MARKERS = BOS_ADDED_NESTING_MARKERS + ('iot',)
"""
    intro       Inserted at the start of book introductions
    iot         Inserted before introduction outline (io markers) IF IT'S NOT ALREADY IN THE FILE
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""

BOS_NESTING_MARKERS = BOS_REGULAR_NESTING_MARKERS + BOS_ALL_ADDED_NESTING_MARKERS + USFM_BIBLE_PARAGRAPH_MARKERS

#BOS_END_MARKERS = ['¬intro', '¬iot', '¬ilist', '¬chapters', '¬c', '¬v', '¬list', ]
#for marker in USFM_BIBLE_PARAGRAPH_MARKERS: BOS_END_MARKERS.append( '¬'+marker )
#print( len(BOS_END_MARKERS), BOS_END_MARKERS )
BOS_END_MARKERS = [ '¬'+marker for marker in BOS_NESTING_MARKERS]
#print( len(BOS_END_MARKERS), BOS_END_MARKERS );halt

#BOS_MARKERS = BOS_ADDED_CONTENT_MARKERS + BOS_ALL_ADDED_NESTING_MARKERS + BOS_END_MARKERS

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

BOS_NON_CHAPTER_BOOKS = ( 'FRT', 'PRF', 'ACK', 'INT', 'TOC', 'GLS', 'CNC', 'NDX', 'TDX', 'BAK', 'OTH',
                          'XXA','XXB','XXC','XXD','XXE','XXF','XXG',
                          'UNK', '???', )



#def exp( messageString ):
    #"""
    #Expands the message string in debug mode.
    #Prepends the module name to a error or warning message string
        #if we are in debug mode.
    #Returns the new string.
    #"""
    #try: nameBit, errorBit = messageString.split( ': ', 1 )
    #except ValueError: nameBit, errorBit = '', messageString
    #if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        #nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    #return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
## end of exp



def parseWordAttributes( workName, BBB, C, V, wordAttributeString, errorList=None ):
    """
    Take the attributes of a USFM3 \w field (the attributes include the first pipe/vertical-bar symbol)
        and analyze them.

    Returns a dictionary of attributes.

    NOTE: No error messages added yet ................... XXXXXXXXXXXXXXXXXXXXXXX
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "parseWordAttributes( {}, {} {}:{}, {!r}, {} )".format( workName, BBB, C, V, wordAttributeString, errorList ) )
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
        assert isinstance( workName, str )
        assert isinstance( BBB, str )
        assert isinstance( wordAttributeString, str )
        assert wordAttributeString.count( '|' ) == 1
        assert errorList is None or isinstance( errorList, list )

    word, attributeString = wordAttributeString.split( '|', 1 )
    resultDict = { 'word':word }
    if '=' not in attributeString: # Assume it's a single (unnamed) lemma
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
            assert '"' not in attributeString and "'" not in attributeString
        resultDict['lemma'] = attributeString
        #print( "Returning1: {}".format( resultDict ) )
        return resultDict

    # Else most likely have named attributes
    # Use a state machine rather than regular expressions coz better for giving human-readable error messages
    state = 0
    name = value = quote = ''
    for j, char in enumerate( attributeString ):
        #print( "{} char={!r} state={} name={!r} value={!r} quote={!r}".format( j, char, state, name, value, quote ) )
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
                #print( "name", name )
                assert name in ('lemma','strong') or name.startswith( 'x-' )
                if name.startswith( 'x-' ): name = name[2:] # Remove x- prefix for convenience
                state = 2
            else: halt
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
    #print( "Returning2: {}".format( resultDict ) )
    return resultDict
# end of parseWordAttributes



# 2 and 3 below refer to USFM2 and USFM3 standards for \fig entries
figureAttributeNames3 = ( 'alt', 'src', 'size', 'loc', 'copy', 'ref' )
betterAttributeNames3 = ( 'altDescription', 'sourceFilename', 'relativeSize', 'locationOrRange', 'copyrightOrRightsHolder', 'referenceCV' )
# The names for USFM2 are determined by position
figureAttributeNames2 = ( betterAttributeNames3[0], betterAttributeNames3[1], betterAttributeNames3[2], betterAttributeNames3[3], betterAttributeNames3[4], 'caption', betterAttributeNames3[5] )

def parseFigureAttributes( workName, BBB, C, V, figureAttributeString, errorList=None ):
    """
    Take the contents of a USFM2 or USFM3 \fig field and analyze them.

    In USFM2, the up-to-seven attributes are separated by vertical bars,
        i.e., \fig DESC|FILE|SIZE|LOC|COPY|CAP|REF\fig*

    In USFM3, the caption text comes first, then other parameters after a vertical bar,
        i.e., \fig caption text|src="filename" size="size" ref="reference"\fig*
        e.g., \fig At once they left their nets.|src="avnt016.jpg" size="span" ref="1.18"\fig*
        and, \fig Took her by the hand, and the fever left her.|src="avnt017.tif" size="col" ref="1.31"\fig*

    Returns a dictionary of attributes.

    NOTE: No error messages added yet ................... XXXXXXXXXXXXXXXXXXXXXXX
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "parseFigureAttributes( {}, {} {}:{}, {!r}, {} )".format( workName, BBB, C, V, figureAttributeString, errorList ) )
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
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
            #print( "{} char={!r} state={} name={!r} value={!r} quote={!r}".format( j, char, state, name, value, quote ) )
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

    #print( "Returning: {}".format( resultDict ) )
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

    def __init__( self, myType, indexToAdjText, noteText, cleanNoteText, location ):
        """
        Accept the parameters and double-check them if requested.

        location parameter is just for better error messages and is not currently stored.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            if debuggingThisModule:
                print( "InternalBibleExtra.__init__( {}, {}, {!r}, {!r}, {} )".format( myType, indexToAdjText, noteText, cleanNoteText, location ) )
            assert myType and isinstance( myType, str ) and myType in BOS_EXTRA_TYPES # Mustn't be blank
            assert '\\' not in myType and ' ' not in myType and '*' not in myType
            assert isinstance( indexToAdjText, int ) and indexToAdjText >= 0
            assert noteText and isinstance( noteText, str ) # Mustn't be blank
            assert '\n' not in noteText and '\r' not in noteText
            for letters in ( 'f', 'x', 'fe', 'ef' ): # footnote, cross-ref, endnotes, studynotes
                assert '\\'+letters+' ' not in noteText
                assert '\\'+letters+'*' not in noteText
            assert isinstance( cleanNoteText, str )
            if debuggingThisModule: assert cleanNoteText # Mustn't be blank
            assert '\\' not in cleanNoteText and '\n' not in cleanNoteText and '\r' not in cleanNoteText
        self.myType, self.index, self.noteText, self.cleanNoteText = myType, indexToAdjText, noteText, cleanNoteText
    # end of InternalBibleExtra.__init__


    #def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        #return False
    #def __ne__(self, other): return not self.__eq__(other)


    def __str__( self ):
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

    def __init__( self, initialData=None ):
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


    def __str__( self ):
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
            #print( "ki2", keyIndex )
            #assert keyIndex.step is None
            #print( "param", *keyIndex.indices(len(self)) )
            return InternalBibleExtraList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        return self.data[keyIndex]
    # end of InternalBibleExtraList.__getitem__


    def summary( self ):
        """
        Like __str__ but just returns a one-line string summary.
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
        #print( "checkForIndex( {} ) resultList = {}".format( stringIndex, resultList ) )
        if resultList:
            if len(resultList) == 1: return resultList[0]
            return resultList
        return None
# end of class InternalBibleExtraList



class InternalBibleEntry:
    """
    This class represents an entry in the InternalBibleEntryList (_processedLines).

    Each entry holds the original and adjusted markers (e.g., \s will be adjusted to \s1)
        plus the cleanText with notes, etc. removed and stored in the "extras" list.
    """

    def __init__( self, marker, originalMarker, adjustedText, cleanText, extras, originalText ):
        """
        Accept the parameters and double-check them if requested.

        Normally all of the parameters are strings.
        But for end markers, only the marker parameter and cleanText are strings
            and the other parameters must all be None.
        """
        if cleanText is not None and '\\' in cleanText:
            logging.error( "InternalBibleEntry expects clean text not {}={}".format( marker, repr(cleanText) ) )
        #if 'it*' in originalText and 'it*' not in adjustedText:
            #print( "InternalBibleEntry constructor had problem with it* (probably in a footnote) in {} {} {}".format( marker, repr(originalText), repr(adjustedText) ) )
            #halt
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            #print( "InternalBibleEntry.__init__( {}, {}, {!r}, {!r}, {}, {!r} )" \
                    #.format( marker, originalMarker, adjustedText[:35]+('…' if len(adjustedText)>35 else ''), \
                        #cleanText[:35]+('…' if len(cleanText)>35 else ''), extras, \
                        #originalText[:35]+('…' if len(originalText)>35 else '') ) )
            assert marker and isinstance( marker, str ) # Mustn't be blank
            assert '\\' not in marker and ' ' not in marker and '*' not in marker
            assert isinstance( cleanText, str )
            assert '\n' not in cleanText and '\r' not in cleanText

            if marker[0] == '¬' \
            or marker in BOS_ALL_ADDED_NESTING_MARKERS and originalMarker is None: # It's an end marker or an added marker
                assert originalMarker is None and adjustedText is None and extras is None and originalText is None
            else: # it's not an end marker
                assert originalMarker and isinstance( originalMarker, str ) # Mustn't be blank
                assert '\\' not in originalMarker and ' ' not in originalMarker and '*' not in originalMarker
                assert isinstance( adjustedText, str )
                assert '\n' not in adjustedText and '\r' not in adjustedText
                if '\\' in cleanText:
                    logging.critical( "Clean text {!r} at {} from {!r}".format( cleanText, marker, originalText ) )
                assert '\\' not in cleanText
                assert extras is None or isinstance( extras, InternalBibleExtraList )
                assert isinstance( originalText, str )
                assert '\n' not in originalText and '\r' not in originalText
                #assert marker in BibleOrgSysGlobals.USFMMarkers or marker in BOS_ADDED_CONTENT_MARKERS
                if marker not in BibleOrgSysGlobals.USFMMarkers and marker not in BOS_ADDED_CONTENT_MARKERS:
                    logging.warning( "InternalBibleEntry doesn't handle {!r} marker yet.".format( marker ) )
        self.marker, self.originalMarker, self.adjustedText, self.cleanText, self.extras, self.originalText = marker, originalMarker, adjustedText, cleanText, extras, originalText

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule \
        and self.originalText is not None and self.getFullText() != self.originalText.strip():
            print( "InternalBibleEntry.Full", repr(self.getFullText()) ) # Has footnote in wrong place on verse numbers (before instead of after)
            print( "InternalBibleEntry.Orig", repr(self.originalText.strip()) ) # Has missing footnotes on verse numbers
            #halt # When does this happen?
    # end of InternalBibleEntry.__init__


    def __eq__( self, other ): # If we don't have this defined, a==b does a is b.
        #print( repr(self) )
        #print( repr(other) )
        #print( isinstance( other, self.__class__ ) )
        #print( self.__dict__ == other.__dict__ )
        #for someKey, someItem in sorted( self.__dict__.items() ):
            #print( 'self', someKey, repr(someItem) )
        #for someKey, someItem in sorted( other.__dict__.items() ):
            #print( 'other', someKey, repr(someItem) )
        #halt
        return isinstance( other, self.__class__ ) and self.__dict__ == other.__dict__
    def __ne__( self, other ):
        return not self.__eq__( other )


    def __str__( self ):
        """
        Just display a very abbreviated form of the entry.
        """
        abbreviatedCleanText = self.cleanText if len(self.cleanText)<100 else (self.cleanText[:50]+'…'+self.cleanText[-50:])
        return 'InternalBibleEntry object: {} = {!r}{}'.format( self.marker, abbreviatedCleanText, '+extras' if self.extras else '' )
    # end of InternalBibleEntry.__str__


    def __repr__( self ):
        """
        Display a fuller form of the entry.
        """
        abbreviatedAdjText = self.adjustedText if len(self.adjustedText)<100 else (self.adjustedText[:50]+'…'+self.adjustedText[-50:])
        abbreviatedCleanText = self.cleanText if len(self.cleanText)<100 else (self.cleanText[:50]+'…'+self.cleanText[-50:])
        abbreviatedOrigText = self.originalText if len(self.originalText)<100 else (self.originalText[:50]+'…'+self.originalText[-50:])
        return 'InternalBibleEntry object:' \
            + '\n    {} = {!r}'.format( self.marker, abbreviatedCleanText ) \
            + ('\n  from Original {} = {!r}'.format( self.originalMarker, abbreviatedOrigText ) if self.originalMarker!=self.marker or self.originalText!=self.cleanText else '' ) \
            + ('\n          adjusted to {!r}'.format( abbreviatedAdjText ) if self.adjustedText!=self.originalText else '' ) \
            + ('\n         with {}'.format( self.extras ) if self.extras else '' )
    # end of InternalBibleEntry.__repr__


    def __len__( self ): return 5
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

        Note that some spaces may not be recovered,
            e.g., in 'lamb\f + \fr 18.9 \ft Sheep \f* more text here'
            the space before the close of the footnote is not restored!
        Otherwise it should be identical to the original text.
        """
        result = self.adjustedText
        offset = 0
        if self.extras:
            for extraType, extraIndex, extraText, cleanExtraText in self.extras: # do any footnotes and cross-references
                #print( "getFullText: {} at {} = {!r} ({})".format( extraType, extraIndex, extraText, cleanExtraText ) )
                #print( "getFullText:  was {!r}".format( result ) )
                ix = extraIndex + offset
                if extraType == 'fn': USFM, lenUSFM = 'f', 1
                elif extraType == 'en': USFM, lenUSFM = 'fe', 2
                elif extraType == 'xr': USFM, lenUSFM = 'x', 1
                elif extraType == 'fig': USFM, lenUSFM = 'fig', 3
                elif extraType == 'str': USFM, lenUSFM = 'str', 3
                elif extraType == 'sem': USFM, lenUSFM = 'sem', 3
                elif extraType == 'ww': USFM, lenUSFM = 'ww', 2
                elif extraType == 'vp': USFM, lenUSFM = 'vp', 2
                elif BibleOrgSysGlobals.debugFlag: halt # Unknown extra field type!!!
                if USFM:
                    result = '{}\\{} {}\\{}*{}'.format( result[:ix], USFM, extraText, USFM, result[ix:] )
                #print( "getFullText:  now {!r}".format( result ) )
                offset += len(extraText ) + 2*lenUSFM + 4
            result = result.replace( '\\w*\\ww ', '' ).replace( '\\ww*', '\\w*' ) # Put attributes back inside \w field

        #if result != self.adjustedText:
            #if len(self.extras) > 1:
                #print( "\nWas {!r}".format( self.cleanText ) )
                #print( "And {!r}".format( self.adjustedText ) )
                #print( "Orig{!r}".format( self.originalText ) )
                #print( "Now {!r}".format( result ) )
                #print( "Extras are {}".format( self.extras ) )
        #if result != self.originalText.strip():
            #print( "\nWe're giving {!r}".format( result ) )
            #print( "   Should be {!r}".format( self.originalText.strip() ) )
            #print( "        From {!r}".format( self.originalText ) )
        #if BibleOrgSysGlobals.debugFlag: assert result == self.originalText.strip()
        return result
    # end of InternalBibleEntry.getFullText
# end of class InternalBibleEntry



class InternalBibleEntryList:
    """
    This class is a specialised list for holding InternalBibleEntries
        so _processedLines is one of these.

    (It's mainly here for extra data validation and the str function for debugging.)
    """

    def __init__( self, initialData=None ):
        """
        """
        self.data = []
        if initialData is not None:
            if isinstance( initialData, list ) or isinstance( initialData, InternalBibleEntryList ):
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


    def __str__( self ):
        """
        Just display a simplified view of the list of entries.

        Only prints the first maxPrinted lines.
        """
        maxPrinted = 50 if debuggingThisModule else 20
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
                                    j if debuggingThisModule else j+1,
                                    entry.marker,
                                    repr(cleanAbbreviation),
                                    " + extras" if entry.extras else '' )
                if j+1>=maxPrinted and dataLen>maxPrinted:
                    result += "\n  … ({} total Bible index entries)".format( dataLen )
                    break
        return result
    # end of InternalBibleEntryList.__str__


    def __len__( self ): return len( self.data )
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            #print( "ki2", keyIndex )
            #assert keyIndex.step is None
            #print( "param", *keyIndex.indices(len(self)) )
            return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        return self.data[keyIndex]
    # end of InternalBibleEntryList.__getitem__


    def append( self, newBibleEntry ):
        """
        Append the newBibleEntry to the InternalBibleEntryList.
        """
        #print( "InternalBibleEntryList.append( {} )".format( newBibleEntry ) )
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

    def extend( self, newList ):
        """
        Extend the InternalBibleEntryList with the newList given.
        """
        assert isinstance( newList, InternalBibleEntryList )
        self.data.extend( newList )
    # end of InternalBibleEntryList.extend


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



class InternalBibleIndexEntry:
    """
    Holds the following information:
        1/ index: the index into the BibleEntryList
            indexNext: the index of the next BibleEntry (do we really need this????)
        2/ entryCount: the number of BibleEntries
        3/ context: a list containing contextual markers which still apply to this entry.
    """
    def __init__( self, entryIndex, entryCount, context=None ):
        """
        """
        #if context: print( "XXXXXXXX", entryIndex, entryCount, context )
        if context is None: context = []
        self.entryIndex, self.entryCount, self.context = entryIndex, entryCount, context
        #self.indexNext = self.entryIndex + entryCount
    # end of InternalBibleIndexEntry.__init__

    def __str__( self ):
        """
        Just display a simplified view of the index entry.
        """
        result = "InternalBibleIndexEntry object: ix={} cnt={} ixE={}{}" \
            .format( self.entryIndex, self.entryCount, self.entryIndex + self.entryCount,
                    " ctxt={}".format(self.context) if self.context else '' )
        return result
    # end of InternalBibleIndexEntry.__str__

    def __len__( self ): return 3
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            halt # not done yet
            #print( "ki2", keyIndex )
            #assert keyIndex.step is None
            #print( "param", *keyIndex.indices(len(self)) )
            #return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        if keyIndex == 0: return self.entryIndex
        elif keyIndex == 1: return self.entryCount
        #elif keyIndex == 2: return self.indexNext
        elif keyIndex == 2: return self.context
        else: raise IndexError
    # end of InternalBibleIndexEntry.__getitem__

    def getEntryIndex( self ): return self.entryIndex
    def getNextEntryIndex( self ): return self.entryIndex + self.entryCount # self.indexNext
    def getEntryCount( self ): return self.entryCount
    def getContext( self ): return self.context
# end of class InternalBibleIndexEntry



class InternalBibleIndex:
    """
    Handles the C:V index for an internal Bible.
    """
    def __init__( self, name, BBB ):
        """
        Creates the index object for a Bible book.

        The book code is stored to enable better error messages.
        """
        self.name, self.BBB = name, BBB
    # end of InternalBibleIndex.__init__


    def __str__( self ):
        """
        Just display a simplified view of the list of entries.
        """
        result = "InternalBibleIndex object for {}:".format( self.BBB )
        try: result += "\n  {} index entries".format( len( self.__indexData ) )
        except AttributeError: result += "\n  Index is empty"
        try: result += " created from {} data entries".format( len( self.givenBibleEntries ) )
        except AttributeError: pass # ignore it
        if BibleOrgSysGlobals.verbosityLevel > 2:
            try: result += "\n  {} average data entries per index entry".format( round( len(self.givenBibleEntries)/len(self.__indexData), 1 ) )
            except ( AttributeError, ZeroDivisionError ): pass # ignore it
        #try:
            #for j, key in enumerate( sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) ) ):
                #C, V = key
                #indexEntry = self.__indexData[key]
                #entries = self.getEntries( key )
                #result += "\n{} {} {} {}".format( j, key, indexEntry, entries )
                #if j>10: break
        #except: pass # ignore it
        return result
    # end of InternalBibleIndex.__str__


    def __len__( self ): len( self.__indexData )
    #def __getitem__( self, keyIndex ):
        #print( "IBI.gi", keyIndex, len(self.__indexData)); halt
        #if keyIndex == 0: return None
        #return self.__indexData[keyIndex]


    def __iter__( self ):
        """
        Yields the next index entry CV key.
        """
        for CVKey in self.__indexData:
            yield CVKey
    # end of InternalBibleIndex.__iter__


    def getEntries( self, CVkey ):
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()]
    # end of InternalBibleIndex.getEntries


    def getEntriesWithContext( self, CVkey ):
        """
        Given C:V, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this verse,
            along with the context for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()], indexEntry.getContext()
    # end of InternalBibleIndex.getEntriesWithContext


    def makeCVIndex( self, givenBibleEntries ):
        """
        Index the Bible book lines for faster reference.

        The parameter is a InternalBibleEntryList(), i.e., self._processedLines
            i.e., a specialised list of InternalBibleEntry objects.

        The keys to the index dictionary for each Bible book are (C,V,) 2-tuples.
            Chapter 0 is the book introduction
                Each line in chapter 0 is a successive 'verse' number (usually the id line is 'verse' 0)
            For each proper chapter (usually starting with 1), verse 0 is the chapter introduction.
                Often this contains only the 'c' entry.
                Section headings are put with the following text / verse.

        The created dictionary entries are (ix,indexEntryLineCount,contextMarkerList) 3-tuples where
            ix is the index into givenBibleEntries,
            indexEntryLineCount is the number of entries for this verse, and
            contextMarkerList is a list containing contextual markers which still apply to this entry.
        """
        if debuggingThisModule: print( "\nInternalBibleIndex.makeCVIndex( {} )".format( givenBibleEntries ) )
        #if self.BBB == 'EXO': halt
        self.givenBibleEntries = givenBibleEntries # Keep a pointer to the original Bible entries
        #if self.BBB=='PHM':
        #print( self.givenBibleEntries )
        self.__indexData = OrderedDict()
        errorData = []


        def printIndexEntry( ie ):
            result = str( ie )
            for j in range( ie.getEntryIndex(), ie.getNextEntryIndex() ):
                result += "\n  {}".format( givenBibleEntries[j] )
            return result
        # end of printIndexEntry


        def saveAnythingOutstanding():
            """
            Save the outstanding index entry if any
                into self.__indexData (an OrderedDict).
            """
            nonlocal saveCV, saveJ, indexEntryLineCount, errorData
            if saveCV and saveJ is not None:
                if debuggingThisModule:
                    print( "    saveAnythingOutstanding", self.BBB, saveCV, saveJ, indexEntryLineCount )
                #if saveCV == ('0','0'): halt
                #assert 1 <= indexEntryLineCount <= 120 # Could potentially be even higher for bridged verses (e.g., 1Chr 11:26-47, Ezra 2:3-20) and where words are stored individually
                if saveCV in self.__indexData: # we already have an index entry for this C:V
                    #print( "makeIndex.saveAnythingOutstanding: already have an index entry @ {} {}:{}".format( self.BBB, strC, strV ) )
                    errorData.append( ( self.BBB,strC,strV,) )
                    if BibleOrgSysGlobals.debugFlag and (debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2):
                        print( '      saveAnythingOutstanding @ ', self.BBB, saveCV )
                        try: # printing the previous index entry
                            ix, lc = self.__indexData[(saveCV[0],str(int(saveCV[1])-1))]
                            logging.error( "  mI:sAO previous {} {}".format( ix, lc ) )
                            for ixx in range( ix, ix+lc ):
                                logging.error( "   mI:sAO prev {}".format( self.givenBibleEntries[ixx] ) )
                        except (KeyError,ValueError): pass
                        logging.error( "  mI:sAO was {}".format( self.__indexData[saveCV] ) )
                        ix, lc = self.__indexData[saveCV]
                        for ixx in range( ix, ix+lc ):
                            logging.error( "   mI:sAO {}".format( self.givenBibleEntries[ixx] ) )
                        logging.error( "  mI:sAO now {}".format( (saveJ,indexEntryLineCount) ) )
                        for ixx in range( saveJ, saveJ+indexEntryLineCount ):
                            logging.error( "   mI:sAO {}".format( self.givenBibleEntries[ixx] ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            C, V = saveCV
                            if C != '0' and V != '0': # intros aren't so important
                                halt # This is a serious error that is losing Biblical text
                    # Let's combine the entries
                    ix, lc = self.__indexData[saveCV]
                    if debuggingThisModule:
                        print( "      About to save UPDATED index entry for {} {}:{}".format( self.BBB, saveCV[0], saveCV[1] ) )
                        print( "        ix={} count={}".format( ix, lc+indexEntryLineCount ) )
                    self.__indexData[saveCV] = ( ix, lc+indexEntryLineCount )
                    if BibleOrgSysGlobals.debugFlag and (debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2):
                        logging.error( "  mI:sAO combined {}".format( (ix,lc+indexEntryLineCount) ) )
                        for ixx in range( ix, ix+lc+indexEntryLineCount ):
                            logging.error( "   mI:sAO {}".format( self.givenBibleEntries[ixx] ) )
                else: # no pre-existing duplicate
                    if debuggingThisModule:
                        print( "      About to save NEW index entry for {} {}:{}".format( self.BBB, saveCV[0], saveCV[1] ) )
                        print( "        ix={} count={}".format( saveJ, indexEntryLineCount ) )
                        for pqr in range( saveJ, saveJ+indexEntryLineCount ):
                            print( "       {}".format( self.givenBibleEntries[pqr] ) )
                    self.__indexData[saveCV] = (saveJ, indexEntryLineCount)
                #print( 'sAO', printIndexEntry( self.__indexData[saveCV] ) )
                saveCV = saveJ = None
                indexEntryLineCount = 0
        # end of saveAnythingOutstanding


        # Main code of InternalBibleIndex.makeIndex
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "    " + _("Indexing {} {} {} entries…").format( len(self.givenBibleEntries), self.name, self.BBB ) )

        # Firstly create the CV index keys with pointers to the actual lines
        if self.BBB in BOS_NON_CHAPTER_BOOKS:
            # It's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            saveCV = saveJ = None
            indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            strC, strV = '0', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                #print( "  makeIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                marker = entry.getMarker()
                if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()
                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    saveAnythingOutstanding()
                    # Save anything before the first verse number as verse 'zero'
                    strC, strV = entry.getCleanText(), '0'
                    assert strC != '0'
                    #saveCV, saveJ = (strC,strV,), j
                    indexEntryLineCount += 1
                elif marker == 'v':
                    assert strC != '0' # Should be in a chapter by now
                    logging.warning( "makeIndex: Why do we have a verse number in a {} {} book without chapters?".format( self.name, self.BBB ) )
                    if debuggingThisModule:
                        print( "  makeIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =",
                            entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                    saveAnythingOutstanding() # with the adjusted indexEntryLineCount
                    #if 0:
                        ## Remove verse ranges, etc. and then save the verse number
                        #strV = entry.getCleanText()
                        #digitV = ''
                        #for char in strV:
                            #if char.isdigit(): digitV += char
                            #else: # the first non-digit in the verse "number"
                                #if BibleOrgSysGlobals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                                #break # ignore the rest
                        ##assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                        #saveCV, saveJ = (strC,digitV,), revertToJ
                elif strC == '0': # Still in the introduction
                    # Each line is considered a new "verse" entry in chapter "zero"
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1)
                    #print( "makeIndexIntro", printIndexEntry( self.__indexData[(strC,strV)] ) )
                    Vi = int( strV )
                    assert Vi == j
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert indexEntryLineCount == 0
                else: # All the other lines don't cause a new index entry to be made
                    indexEntryLineCount += 1
            saveAnythingOutstanding()

        else: # Assume it's a normal C/V book
            saveCV = saveJ = None
            indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            strC, strV = '0', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                if debuggingThisModule:
                    print( "  makeIndex1", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                marker = entry.getMarker()
                if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    # All text should have been moved into the following p~ marker
                    assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()

                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    if debuggingThisModule: print( "    Handle c {}".format( entry.getCleanText() ) )
                    saveAnythingOutstanding()
                    # Save anything before the first verse number as verse 'zero'
                    strC, strV = entry.getCleanText(), '0'
                    assert strC != '0'
                    saveCV, saveJ = (strC,strV,), j
                    indexEntryLineCount += 1

                elif marker == 'v': # This bit of indexing code is quite complex!
                    if debuggingThisModule: print( "    Handle v {}".format( entry.getCleanText() ) )
                    assert strC != '0' # Should be in a chapter by now

                    # Go back and look what we passed that might actually belong with this verse
                    #   e.g., section headings, new paragraphs, etc.
                    revertToJ = j
                    if revertToJ >= 1: # we have a processedLine to go back to
                        aPreviousMarker,thisCleanText = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                        while revertToJ >= 1 and aPreviousMarker not in ('c','v', 'v~','p~') and not aPreviousMarker.startswith('¬'):
                            # Anything else gets pulled down into this next verse
                            #   especially all p & q type markers, and section heading & references
                            revertToJ -= 1
                            assert indexEntryLineCount > 0
                            indexEntryLineCount -= 1
                            if revertToJ==0: print( "InternalBibleIndex.makeIndex: Get out of here" ); break
                            aPreviousMarker,thisCleanText = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                    saveAnythingOutstanding() # with the adjusted indexEntryLineCount
                    # Remove verse ranges, etc. and then save the verse number
                    strV = entry.getCleanText()
                    digitV = ''
                    for char in strV:
                        if char.isdigit(): digitV += char
                        else: # the first non-digit in the verse "number"
                            if BibleOrgSysGlobals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                            break # ignore the rest
                    #assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                    saveCV, saveJ = (strC,digitV,), revertToJ
                    indexEntryLineCount += (j-revertToJ) + 1 # For the v
                    #if 0 and BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        ## Double-check that each entry contains only ONE v field
                        ##print( "  makeIndex check at {} {}".format( j, entry ) )
                        ##print( "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                        #vCount = 0
                        #for scj in range( 0, indexEntryLineCount ):
                            #thisEntry = self.givenBibleEntries[ j + scj ] # This is an InternalBibleEntry
                            ##print( "      {}".format( thisEntry ) )
                            #if thisEntry.getMarker() == 'v': vCount += 1
                        ##print( "    vCount={}".format( vCount ) )
                        #if vCount > 1: # Should never happen -- verses should all have their own separate index entries
                            #print( "  makeIndex check for {} {} {}:{} at ({}) {}".format( self.name, self.BBB, strC, strV, j, entry ) )
                            #print( "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                            #for scj in range( 0, indexEntryLineCount ):
                                #print( "      {}".format( self.givenBibleEntries[ j + scj ] ) ) # This is an InternalBibleEntry
                            #print( "    vCount={}".format( vCount ) )
                            ##halt
                        ## Actually this seems to be fixed up down below somewhere (so doesn't seem to matter)
                    if debuggingThisModule:
                        if strV == '4':
                            halt
                        else: print( "Temp index currently ({}) {}".format( len(self.__indexData), self.__indexData ) )

                elif strC == '0': # Still in the introduction
                    # Each line is considered a new 'verse' entry in chapter 'zero'
                    #   (usually the id line is 'verse' 0, i.e., 0:0)
                    if debuggingThisModule: print( "    Handle intro {}".format( entry.getCleanText() ) )
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1 )
                    #print( "makeIndex", printIndexEntry( self.__indexData[(strC,strV)] ) )
                    Vi = int( strV )
                    assert Vi == j
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert indexEntryLineCount == 0

                else: # All the other lines don't cause a new index entry to be made
                    indexEntryLineCount += 1
            saveAnythingOutstanding()

        if errorData: # We got some overwriting errors
            lastBBB = None
            errorDataString = ''
            for BBB,C,V in errorData:
                assert BBB == self.BBB # We didn't really need to save this
                if BBB != lastBBB:
                    errorDataString += (' ' if errorDataString else '') + BBB
                    lastBBB, lastC = BBB, None
                if C != lastC:
                    errorDataString += (' ' if lastC is None else '; ') + C + ':'
                    lastC = C
                errorDataString += ('' if errorDataString[-1]==':' else ',') + V
            logging.warning( "makeIndex.saveAnythingOutstanding: Needed to combine multiple index entries for {}".format( errorDataString ) )

        # Now calculate the contextMarkerList for each CV entry and create the proper (full) InternalBibleIndexEntries
        contextMarkerList = []
        for (C,V), (indexStart,count) in self.__indexData.items():
            if debuggingThisModule:
                print( "makeIndex for {} {} {}:{} {} {} {}".format( self.name, self.BBB, C, V, indexStart, count, contextMarkerList ) )
            # Replace the existing (temporary) index entry to include a copy of the previous contextMarkerList
            #   e.g., a typical verse might be inside a paragraph in a section
            #            thus getting the contextMarkerList: ['chapters','c','s1','p']
            self.__indexData[(C,V)] = InternalBibleIndexEntry( indexStart, count, contextMarkerList[:] )
            for j in range( indexStart, indexStart+count ):
                entry = self.givenBibleEntries[j]
                marker = entry.getMarker()
                if debuggingThisModule: print( "  makeIndex {} marker: {} {}".format( j, marker, entry.getCleanText() ) )
                if marker[0]=='¬' and marker != '¬v': # We're closing a paragraph marker
                    originalMarker = marker[1:]
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        # Should be exactly one of these markers (open) in the contextMarkerList
                        # XXXXXXXXX Gets messed up by GNT Mrk 16:9 has two \s headings in a row !!!!!!!!!!!!!!!!!!!
                        if contextMarkerList.count(originalMarker)!=1:
                            print( "    makeIndex originalMarker: {!r} contextMarkerList={}".format( originalMarker, contextMarkerList ) )
                            logging.critical( "makeIndex found a nesting error for {} {} around {}:{}".format( self.name, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            assert contextMarkerList.count( originalMarker ) == 1
                    try: # Remove first open occurence of the marker just closed (e.g., s1 can occur after c and still be open)
                        if debuggingThisModule:
                            print( "    makeIndex: Removing {} from contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
                        contextMarkerList.remove( originalMarker )
                    except ValueError: # oops something went wrong
                        #print( 'makeIndex: marker = {}'.format( marker ) )
                        #print( 'makeIndex: entry = {}'.format( entry ) )
                        #print( 'makeIndex: contextMarkerList = {}'.format( contextMarkerList ) )
                        logging.critical( "makeIndex found an unknown nesting error for {} {} around {}:{}".format( self.name, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        assert contextMarkerList.count( originalMarker ) == 0
                if marker in BOS_NESTING_MARKERS and marker!='v':
                    if debuggingThisModule:
                        print( "    makeIndex: Adding {} to contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
                    contextMarkerList.append( marker )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
            assert not contextMarkerList # Should be empty at end if nesting for the book is correct

        self._indexedFlag = True
        #if 0:
            #print( self )
            #print( ' ', self.__indexData )
            #for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                #print( " {:3} {}: {}".format( j, iKey, iEntry ) )
            #halt

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            self.checkIndex() # Make sure our code above worked properly
    # end of InternalBibleIndex.makeIndex


    def checkIndex( self ):
        """
        Just run a quick internal check on the index.
        """
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print(  "  " + _("Checking {} {} {} index entries…").format( len(self.__indexData), self.name, self.BBB ) )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
            print( self )

        # Check that all C,V entries (the index to the index) are digits
        for ixKey in self.__indexData:
            #print( ixKey ); halt
            C, V = ixKey
            if not C.isdigit():
                logging.critical( "InternalBibleIndex.checkIndex: Non-digit C entry in {} {} {}:{}".format( self.name, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleIndex.checkIndex: Non-digit V entry in {} {} {}:{}".format( self.name, self.BBB, repr(C), repr(V) ) )

        # Copy the index (OrderedDict) into a (sorted) list so that we can access entries sequentially for testing
        try: sortedIndex = sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleIndex.checkIndex: Unable to sort index for {} {}".format( self.name, self.BBB ) )
            sortedIndex = self.__indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.__indexData[key]
            #entries = self.getEntries( key )
            #print( "checkIndex display", j, key, indexEntry, entries )
            #if self.BBB!='FRT' and j>30: break

        # Now go through the index entries (in order) and do the actual checks
        lastKey = nextKey = nextNextKey = None
        for k, key in enumerate( sortedIndex ):
            # Try getting the next couple of keys also (if they exist)
            try: nextKey = sortedIndex[k+1]
            except IndexError: nextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                print( "nextKeyError1", k, len(sortedIndex), repr(key) ); nextKey = None
            try: nextNextKey = sortedIndex[k+2]
            except IndexError: nextNextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                print( "nextKeyError2", k, len(sortedIndex), repr(key) ); nextKey = None
            C, V = key

            indexEntry = self.__indexData[key]
            entries = self.getEntries( key ) # Gets the list of index entries for this one CV index
            foundMarkers = []
            anyText = anyExtras = False
            vCount = 0
            for entry in entries:
                marker = entry.getMarker()
                foundMarkers.append( marker )
                if marker[0]=='¬': assert marker in BOS_END_MARKERS
                if marker == 'v': vCount += 1
                if marker not in ('c','v'): # These always have to have text
                    if entry.getCleanText(): anyText = True
                    if entry.getExtras(): anyExtras = True
            if vCount > 1:
                logging.critical( "InternalBibleIndex.checkIndex: Probable index or encoding error (multiple v entries) in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                assert vCount <= 1

            #print( "InternalBibleIndex.checkIndex line", self.BBB, key, indexEntry, entries, foundMarkers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '0': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in foundMarkers:
                        logging.critical( "InternalBibleIndex.checkIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert 'c' in foundMarkers
                else: assert 'v' in foundMarkers
                if 'p' in foundMarkers:
                    if 'p~' not in foundMarkers and 'v' not in foundMarkers:
                        logging.critical( "InternalBibleIndex.checkIndex: Probable (early in chapter) p encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        assert 'p~' in foundMarkers or 'v' in foundMarkers
                if 'q1' in foundMarkers or 'q2' in foundMarkers:
                    if 'v' not in foundMarkers and 'p~' not in foundMarkers:
                        logging.critical( "InternalBibleIndex.checkIndex: Probable q1/q2 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        assert 'v' in foundMarkers or 'p~' in foundMarkers

                previousMarker = nextMarker = None # But these skip over rem (remark markers)
                for j, marker in enumerate( foundMarkers ):
                    #print( 'CheckIndex2 {} {}:{} {}/ m={!r} pM={!r} nM={!r}'.format( self.BBB, C, V, j, marker, previousMarker, nextMarker ) )

                    # Work out the next marker (skipping over rem markers)
                    offset = 1
                    while True:
                        try: nextMarker = foundMarkers[j+offset]
                        except IndexError: nextMarker = None
                        if nextMarker != 'rem': break
                        offset += 1

                    # Check the various series of markers
                    if marker == 'cp':
                        if self.BBB not in ('ESG','SIR'):
                            assert previousMarker in ('c','c~',None) # WEB Ps 151 gives None -- not totally sure why yet?
                    elif marker == 'c#': assert nextMarker in ( 'v', 'vp#', )
                    elif marker == 'v':
                        if foundMarkers[-1] != 'v' and nextMarker not in ('v~','¬v',): # end marker if verse is blank
                            logging.critical( "InternalBibleIndex.checkIndex: Probable v encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    elif marker == 'vp#':
                        #print( "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.name ) )
                        if debuggingThisModule:
                            if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleIndex.checkIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.name, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','vp#','c#','¬p'):
                            if lastKey and debuggingThisModule: print( "InternalBibleIndex.checkIndex: lastKey1", self.BBB, lastKey, self.getEntries( lastKey ) )
# NOTE: temporarily down-graded from critical …
                            logging.error( "InternalBibleIndex.checkIndex: Probable p encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleIndex.checkIndex: nextKey1", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleIndex.checkIndex: nextNextKey1", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: print( "InternalBibleIndex.checkIndex: lastKey2", self.BBB, lastKey, self.getEntries( lastKey ) )
                            logging.critical( "InternalBibleIndex.checkIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleIndex.checkIndex: nextKey2", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleIndex.checkIndex: nextNextKey2", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                            logging.critical( "InternalBibleIndex.checkIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q3' and nextMarker not in ('v','p~', '¬q3'):
                            logging.critical( "InternalBibleIndex.checkIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                            logging.critical( "InternalBibleIndex.checkIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '0': # the book introduction
                pass
            else: # not the book introduction
                if  V=='0': # chapter introduction
                    #print( self.BBB, C, V, foundMarkers, entries )
                    #newKey = (C, '1')
                    #try:
                        #iE = self.__indexData[newKey]
                        #iD, ct = self.getEntries( newKey )
                    #except KeyError: pass
                    #print( self
                    #print( " ", newKey, iD, ct )
                    if self.BBB=='ACT' and C=='8':
                        if 'p' in foundMarkers:
                            logging.critical( "InternalBibleIndex.checkIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.name ) )
                        #else:
                            #if 's1'  in foundMarkers or 'r' in foundMarkers or 'p' in foundMarkers or 'q1' in foundMarkers:
                                #print( "xyz", key, entries )
                            #if self.name != '1974_TB':
                                #assert 's1' not in foundMarkers and 'r' not in foundMarkers and 'p' not in foundMarkers and 'q1' not in foundMarkers

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleIndex.checkIndex: wrong {} {} chapter number {!r} expected {!r}".format( self.name, self.BBB, cleanText, C ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleIndex.checkIndex: wrong {} {} {} verse number {!r} expected {!r}".format( self.name, self.BBB, C, cleanText, V ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
            lastKey = key

        if debuggingThisModule: # Just print the beginning part of the index to view
            if self.BBB in ('GEN','MAT'):
                print( self )
                print( ' ', self.__indexData )
                for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                    print( " {:3} {}: {}".format( j, iKey, iEntry ) )
                    if iEntry.entryCount > 1:
                        for scj in range( 0, iEntry.entryCount ):
                            print( "      {}".format( self.givenBibleEntries[ iEntry.entryIndex + scj ] ) ) # This is an InternalBibleEntry
                    if j > 40: break
                halt
        #if self.BBB=='FRT': halt
    # end of InternalBibleIndex.checkIndex
# end of class InternalBibleIndex



def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    print( "Since these are only helper classes, they can't actually do much at all." )
    print( "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #if BibleOrgSysGlobals.verbosityLevel > 0: print( IBB )
# end of demo


if __name__ == '__main__':
    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of InternalBibleInternals.py
