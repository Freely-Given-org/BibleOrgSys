#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBibleInternals.py
#   Last modified: 2014-06-22 by RJH (also update ProgVersion below)
#
# Module handling the internal markers for Bible books
#
# Copyright (C) 2010-2014 Robert Hunt
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
    self.objectTypeString (with "OSIS", "USFM", "USX" or "XML", etc.)
    self.objectNameString (with a description of the type of BibleBook object)
It also needs to provide a "load" routine that sets one or more of:
    self.sourceFolder
    self.sourceFilename
    self.sourceFilepath = os.path.join( sourceFolder, sourceFilename )
and then calls
    self.appendLine (in order to fill self._rawLines)
"""

ProgName = "Bible internals handler"
ProgVersion = "0.43"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False
MAX_NONCRITICAL_ERRORS_PER_BOOK = 5


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from BibleReferences import BibleAnchorReference


# Define allowed punctuation
LEADING_WORD_PUNCT_CHARS = """“«"‘‹'([{<"""
MEDIAL_WORD_PUNCT_CHARS = '-'
DASH_CHARS = '—–' # em-dash and en-dash
TRAILING_WORD_PUNCT_CHARS = """,.”»"’›'?)!;:]}>"""
ALL_WORD_PUNCT_CHARS = LEADING_WORD_PUNCT_CHARS + MEDIAL_WORD_PUNCT_CHARS + DASH_CHARS + TRAILING_WORD_PUNCT_CHARS


BOS_CONTENT_MARKERS = ( 'c~', 'c#', 'v~', 'p~', 'cl=', 'vp~', )
"""
    c~  anything after the chapter number on a \c line
    c#  the chapter number in the correct position to be printed
            This is usually a duplicate of the c field, but may have come from the cp field instead
            Usually only one of c or c# is used for exports
    v~  verse text -- anything after the verse number on a \v line
    p~  verse text -- anything that was on a paragraph line (e.g., \p, \q, \q2, etc.)
    cl= used for cl markers BEFORE the '\c 1' marker -- represents the text for "chapter" to be used throughout the book
    vp~ used for the vp (character field) when it is converted to a separate (newline) field
            This is inserted BEFORE the v (and v~) marker(s)
"""

BOS_ADDED_MARKERS = ( 'intro', 'iot', 'ilist', 'chapters', 'list', )
"""
    intro       Inserted at the start of book introductions
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""

BOS_ALL_ADDED_MARKERS = BOS_ADDED_MARKERS + ('iot',)
"""
    intro       Inserted at the start of book introductions
    iot         Inserted before introduction outline (io markers) IF IT'S NOT ALREADY IN THE FILE
    ilist       Inserted at the start of introduction lists (before ili markers)
    chapters    Inserted after the introduction (if any) and before the first Bible content (usually immediately before chapter 1 marker)
    list       Inserted at the start of lists (before li markers)
"""

BOS_END_MARKERS = ('¬intro', '¬iot', '¬ilist', '¬chapters', '¬c', '¬v', '¬list', )

#BOS_MARKERS = BOS_CONTENT_MARKERS + BOS_ALL_ADDED_MARKERS + BOS_END_MARKERS

EXTRA_TYPES = ( 'fn', 'en', 'xr', 'fig', 'str', 'vp', )
"""
    fn  footnote
    en  endnote
    xr  cross-reference
    fig figure
    str Strongs' number
    vp  published verse number
"""



class InternalBibleExtra:
    """
    This class represents an entry in the _processedLines list.
    """

    def __init__( self, myType, index, noteText, cleanNoteText ):
        """
        Accept the parameters and double-check them if requested.
        """
        if Globals.debugFlag or Globals.strictCheckingFlag:
            #print( "InternalBibleExtra.__init__( {}, {}, {}, {} )".format( myType, index, repr(noteText), repr(cleanNoteText) ) )
            assert( myType and isinstance( myType, str ) and myType in EXTRA_TYPES ) # Mustn't be blank
            assert( '\\' not in myType and ' ' not in myType and '*' not in myType )
            assert( isinstance( index, int ) and index >= 0 )
            assert( noteText and isinstance( noteText, str ) ) # Mustn't be blank
            assert( '\n' not in noteText and '\r' not in noteText )
            for letters in ( 'f', 'x', 'fe', 'ef' ): # footnote, cross-ref, endnotes, studynotes
                assert( '\\'+letters+' ' not in noteText )
                assert( '\\'+letters+'*' not in noteText )
            assert( cleanNoteText and isinstance( cleanNoteText, str ) ) # Mustn't be blank
            assert( '\\' not in cleanNoteText and '\n' not in cleanNoteText and '\r' not in cleanNoteText )
        self.myType, self.index, self.noteText, self.cleanNoteText = myType, index, noteText, cleanNoteText
    # end of InternalBibleExtra.__init__


    #def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        #return False
    #def __ne__(self, other): return not self.__eq__(other)


    def __str__( self ):
        """
        Just display a very abbreviated form of the entry.
        """
        return "InternalBibleExtra object: {} = {}".format( self.myType, repr(self.noteText) )
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
        if initialData: assert( len(self.data) == len(initialData) )
        else: assert( not self.data )
    # end of InternalBibleExtraList.__init__


    #def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        #return False
    #def __ne__(self, other): return not self.__eq__(other)


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
                if Globals.debugFlag: assert( isinstance( entry, InternalBibleExtra ) )
                result += "\n  {} {} @ {} = {}".format( ' ' if j<9 and dataLen>=10 else '', j+1, entry.myType, entry.index, repr(entry.noteText) )
                if j>=maxPrinted and dataLen>maxPrinted:
                    result += "\n  ... ({} total entries)".format( dataLen )
                    break
        return result
    # end of InternalBibleExtraList.__str__

    def __len__( self ): return len( self.data )

    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            #print( "ki2", keyIndex )
            #assert( keyIndex.step is None )
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
        assert( isinstance( newExtraEntry, InternalBibleExtra ) )
        self.data.append( newExtraEntry )
    # end of InternalBibleExtraList.append

    def pop( self ): # Doesn't allow a parameter
        try: return self.data.pop()
        except: return None
    # end of InternalBibleExtraList.append

    def extend( self, newExtraList ):
        assert( isinstance( newExtraList, InternalBibleExtraList ) )
        self.data.extend( newExtraList )
    # end of InternalBibleExtraList.extend
# end of class InternalBibleExtraList



class InternalBibleEntry:
    """
    This class represents an entry in the _processedLines list.
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
        if Globals.debugFlag or Globals.strictCheckingFlag:
            #print( "InternalBibleEntry.__init__( {}, {}, '{}', '{}', {}, '{}' )" \
                    #.format( marker, originalMarker, adjustedText[:35]+('...' if len(adjustedText)>35 else ''), \
                        #cleanText[:35]+('...' if len(cleanText)>35 else ''), extras, \
                        #originalText[:35]+('...' if len(originalText)>35 else '') ) )
            assert( marker and isinstance( marker, str ) ) # Mustn't be blank
            assert( '\\' not in marker and ' ' not in marker and '*' not in marker )
            assert( isinstance( cleanText, str ) )
            assert( '\n' not in cleanText and '\r' not in cleanText )

            if marker[0] == '¬' \
            or marker in BOS_ALL_ADDED_MARKERS and originalMarker is None: # It's an end marker or an added marker
                assert( originalMarker is None and adjustedText is None and extras is None and originalText is None )
            else: # it's not an end marker
                assert( originalMarker and isinstance( originalMarker, str ) ) # Mustn't be blank
                assert( '\\' not in originalMarker and ' ' not in originalMarker and '*' not in originalMarker )
                assert( isinstance( adjustedText, str ) )
                assert( '\n' not in adjustedText and '\r' not in adjustedText )
                assert( '\\' not in cleanText )
                assert( extras is None or isinstance( extras, InternalBibleExtraList ) )
                assert( isinstance( originalText, str ) )
                assert( '\n' not in originalText and '\r' not in originalText )
                #assert( marker in Globals.USFMMarkers or marker in BOS_CONTENT_MARKERS )
                if marker not in Globals.USFMMarkers and marker not in BOS_CONTENT_MARKERS:
                    logging.warning( "InternalBibleEntry doesn't handle '{}' marker yet.".format( marker ) )
        self.marker, self.originalMarker, self.adjustedText, self.cleanText, self.extras, self.originalText = marker, originalMarker, adjustedText, cleanText, extras, originalText

        if Globals.debugFlag and debuggingThisModule \
        and self.originalText is not None and self.getFullText() != self.originalText.strip():
            print( "InternalBibleEntry.Full", repr(self.getFullText()) ) # Has footnote in wrong place on verse numbers (before instead of after)
            print( "InternalBibleEntry.Orig", repr(self.originalText.strip()) ) # Has missing footnotes on verse numbers
            #halt # When does this happen?
    # end of InternalBibleEntry.__init__


    #def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        #return False
    #def __ne__(self, other): return not self.__eq__(other)


    def __str__( self ):
        """
        Just display a very abbreviated form of the entry.
        """
        cleanAbbreviation = self.cleanText if len(self.cleanText)<100 else (self.cleanText[:50]+'...'+self.cleanText[-50:])
        return "InternalBibleEntry object: {} = {}{}".format( self.marker, repr(cleanAbbreviation), '+extras' if self.extras else '' )
    # end of InternalBibleEntry.__str__


    def __len__( self ): return 5
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.marker
        elif keyIndex==1: return self.originalMarker
        elif keyIndex==2: return self.adjustedText
        elif keyIndex==3: return self.cleanText
        elif keyIndex==4: return self.extras
        elif keyIndex==5: return self.originalText
        else: raise IndexError
    # end of InternalBibleEntry.__getitem__

    def getMarker( self ): return self.marker
    def getOriginalMarker( self ): return self.originalMarker
    def getAdjustedText( self ): return self.adjustedText # Notes are removed
    def getText( self ): return self.adjustedText # Notes are removed
    def getCleanText( self ): return self.cleanText
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
                #print( "getFullText: {} at {} = '{}' ({})".format( extraType, extraIndex, extraText, cleanExtraText ) )
                #print( "getFullText:  was '{}'".format( result ) )
                ix = extraIndex + offset
                if extraType == 'fn': USFM, lenUSFM = 'f', 1
                elif extraType == 'en': USFM, lenUSFM = 'fe', 2
                elif extraType == 'xr': USFM, lenUSFM = 'x', 1
                elif extraType == 'fig': USFM, lenUSFM = 'fig', 3
                elif extraType == 'str': USFM, lenUSFM = 'str', 3 # Ignore Strong's numbers since no way to encode them in USFM
                elif extraType == 'vp': USFM, lenUSFM = 'vp', 2
                elif Globals.debugFlag: halt
                if USFM:
                    result = '{}\\{} {}\\{}*{}'.format( result[:ix], USFM, extraText, USFM, result[ix:] )
                #print( "getFullText:  now '{}'".format( result ) )
                offset += len(extraText ) + 2*lenUSFM + 4

        #if result != self.adjustedText:
            #if len(self.extras) > 1:
                #print( "\nWas '{}'".format( self.cleanText ) )
                #print( "And '{}'".format( self.adjustedText ) )
                #print( "Orig'{}'".format( self.originalText ) )
                #print( "Now '{}'".format( result ) )
                #print( "Extras are {}".format( self.extras ) )
        #if result != self.originalText.strip():
            #print( "\nWe're giving '{}'".format( result ) )
            #print( "   Should be '{}'".format( self.originalText.strip() ) )
            #print( "        From '{}'".format( self.originalText ) )
        #if Globals.debugFlag: assert( result == self.originalText.strip() )
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
        if initialData: assert( len(self.data) == len(initialData) )
        else: assert( not self.data )
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
        maxPrinted = 20
        result = "InternalBibleEntryList object:"
        if not self.data: result += "\n  Empty."
        else:
            dataLen = len( self.data )
            for j, entry in enumerate( self.data ):
                if Globals.debugFlag: assert( isinstance( entry, InternalBibleEntry ) )
                cleanAbbreviation = entry.cleanText if entry.cleanText is None or len(entry.cleanText)<100 \
                                                    else (entry.cleanText[:50]+'...'+entry.cleanText[-50:])
                result += "\n  {}{}/ {} = {}{}".format( ' ' if j<9 and dataLen>=10 else '', j+1, entry.marker, repr(cleanAbbreviation), " + extras" if entry.extras else '' )
                if j>=maxPrinted and dataLen>maxPrinted:
                    result += "\n  ... ({} total entries)".format( dataLen )
                    break
        return result
    # end of InternalBibleEntryList.__str__


    def __len__( self ): return len( self.data )
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            #print( "ki2", keyIndex )
            #assert( keyIndex.step is None )
            #print( "param", *keyIndex.indices(len(self)) )
            return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        return self.data[keyIndex]


    def append( self, newBibleEntry ):
        assert( isinstance( newBibleEntry, InternalBibleEntry ) )
        self.data.append( newBibleEntry )
    # end of InternalBibleEntryList.append

    def pop( self ): # Doesn't allow a parameter
        try: return self.data.pop()
        except: return None
    # end of InternalBibleEntryList.append

    def extend( self, newList ):
        assert( isinstance( newList, InternalBibleEntryList ) )
        self.data.extend( newList )
    # end of InternalBibleEntryList.extend
# end of class InternalBibleEntryList



class InternalBibleIndexEntry:
    """
    Holds a 3-tuple that gives:
        1/ index: the index into the BibleEntryList
        2/ entryCount: the number of BibleEntries
        3/ context: a list containing contextual markers which still apply to this entry.
    """
    def __init__( self, entryIndex, entryCount, context=None ):
        if context is None: context = []
        self.entryIndex, self.entryCount, self.context = entryIndex, entryCount, context
        self.indexNext = self.entryIndex + entryCount
    # end of InternalBibleIndexEntry.__init__

    def __str__( self ):
        """
        Just display a simplified view of the index entry.
        """
        result = "InternalBibleIndexEntry object: ix={} cnt={} ixE={}{}" \
            .format( self.entryIndex, self.entryCount, self.indexNext, " ctxt={}".format(self.context) if self.context else '' )
        return result
    # end of InternalBibleIndexEntry.__str__

    def getEntryIndex( self ): return self.entryIndex
    def getNextEntryIndex( self ): return self.indexNext
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
        try: result += "\n  {} index entries".format( len( self.indexData ) )
        except: result += "\n  Index is empty"
        try: result += " created from {} data entries".format( len( self.givenBibleEntries ) )
        except: pass # ignore it
        if Globals.verbosityLevel > 2:
            try: result += "\n  {} average data entries per index entry".format( round( len(self.givenBibleEntries)/len(self.indexData), 1 ) )
            except: pass # ignore it
        #try:
            #for j, key in enumerate( sorted( self.indexData, key=lambda s: int(s[0])*1000+int(s[1]) ) ):
                #C, V = key
                #indexEntry = self.indexData[key]
                #entries, context = self.getEntries( key )
                #result += "\n{} {} {} {}".format( j, key, indexEntry, entries )
                #if j>10: break
        #except: pass # ignore it
        return result
    # end of InternalBibleIndex.__str__


    def __len__( self ): len( self.indexData )
    #def __getitem__( self, keyIndex ):
        #print( "IBI.gi", keyIndex, len(self.indexData)); halt
        #if keyIndex == 0: return None
        #return self.indexData[keyIndex]


    def getEntries( self, CVkey ):
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this verse,
            along with the context for this verse.

        Raises a KeyError if the CV key doesn't exist
        """
        indexEntry = self.indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()], indexEntry.getContext()
    # end of InternalBibleIndex.getEntries


    def makeIndex( self, givenBibleEntries ):
        """
        Index the lines for faster reference.

        The keys to the index dictionary for each Bible book are (C,V,) 2-tuples.
            Chapter 0 is the book introduction
                Each line is a successive "verse" number (usually the id line is "verse" 0)
            For each chapter, verse 0 is the chapter introduction.
                Normally this contains only the 'c' entry.

        The created dictionary entries are (ix,lineCount,context) 3-tuples where
            ix is the index into givenBibleEntries,
            lineCount is the number of entries for this verse, and
            context is a list containing contextual markers which still apply to this entry.
        """
        #print( "InternalBibleIndex.makeIndex( {} )".format( givenBibleEntries ) )
        self.givenBibleEntries = givenBibleEntries # Keep a pointer to the original Bible entries
        #if self.BBB=='PHM':
        #print( self.givenBibleEntries )
        self.indexData = {}


        def saveAnythingOutstanding():
            """
            Save the outstanding index entry if any.
            """
            nonlocal saveCV, saveJ, lineCount, context
            if saveCV and saveJ is not None:
                #print( "saveAnythingOutstanding", self.BBB, saveCV, saveJ, lineCount, context )
                #if saveCV == ('0','0'): halt
                #assert( 1 <= lineCount <= 120 ) # Could potentially be even higher for bridged verses (e.g., 1Chr 11:26-47, Ezra 2:3-20) and where words are stored individually
                if saveCV in self.indexData:
                    logging.critical( "makeIndex.saveAnythingOutstanding: losing Biblical text by replacing index entry {} {}:{}".format( self.BBB, strC, strV ) )
                    if Globals.verbosityLevel > 2:
                        print( saveCV )
                        try:
                            iep = self.indexData[(saveCV[0],str(int(saveCV[1])-1))]
                            logging.error( "  mI:sAO previous {}".format( iep ) )
                            ix,lc,ct = iep.getEntryIndex(), iep.getEntryCount(), iep.getContext()
                            for ixx in range( ix, ix+lc ):
                                logging.error( "   mI:sAO prev {} {}".format( self.givenBibleEntries[ixx], ct ) )
                        except: pass
                        logging.error( "  mI:sAO was {}".format( self.indexData[saveCV] ) )
                        ie = self.indexData[saveCV]
                        ix,lc,ct = ie.getEntryIndex(), ie.getEntryCount(), ie.getContext()
                        for ixx in range( ix, ix+lc ):
                            logging.error( "   mI:sAO {} {}".format( self.givenBibleEntries[ixx], ct ) )
                        logging.error( "  mI:sAO now {}".format( (saveJ,lineCount,context) ) )
                        for ixx in range( saveJ, saveJ+lineCount ):
                            logging.error( "   mI:sAO {} {}".format( self.givenBibleEntries[ixx], context ) )
                        if Globals.debugFlag and debuggingThisModule: halt # This is a serious error that is losing Biblical text
                self.indexData[saveCV] = InternalBibleIndexEntry( saveJ, lineCount, context )
                saveCV = saveJ = None
                lineCount = 0
        # end of saveAnythingOutstanding


        if Globals.verbosityLevel > 3: print( "    " + _("Indexing {} {} {} entries...").format( len(self.givenBibleEntries), self.name, self.BBB ) )
        if self.BBB not in ('FRT','PRF','ACK','INT','TOC','GLS','CNC','NDX','TDX','BAK','OTH', \
                                                'XXA','XXB','XXC','XXD','XXE','XXF','XXG',):
            # Assume it's a C/V book
            saveCV = saveJ = None
            lineCount, context = 0, None # lineCount is the number of datalines pointed to by this index entry
            strC, strV = '0', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                #print( "  makeIndex1", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '...') )
                marker = entry.getMarker()
                if Globals.debugFlag and marker in Globals.USFMParagraphMarkers:
                    assert( not entry.getText() and not entry.getCleanText() and not entry.getExtras() )
                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    saveAnythingOutstanding()
                    # Save anything before the first verse number as verse "zero"
                    strC, strV = entry.getCleanText(), '0'
                    assert( strC != '0' )
                    saveCV, saveJ = (strC,strV,), j
                    lineCount += 1
                elif marker == 'v':
                    assert( strC != '0' ) # Should be in a chapter by now
                    # Go back and look what we passed that might actually belong with this verse
                    revertToJ = j
                    if revertToJ >= 1: # we have a processedLine to go back to
                        aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                        if 1: # new code
                            while revertToJ >= 1 and aM not in ('c','v', 'v~','p~'):
                                # Anything else gets pulled down into this next verse
                                #   especially p & q markers and section heading & references
                                revertToJ -= 1
                                assert( lineCount > 0 )
                                lineCount -= 1
                                if revertToJ==0: print( "InternalBibleIndex.makeIndex: Get out of here" ); break
                                aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                        else: # old code
                            if aM == 'c#':
                                assert( cT ) # Should have a chapter number here
                                revertToJ -= 1
                                assert( lineCount > 0 )
                                lineCount -= 1
                                #print( "going to", revertToJ-1 )
                                aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                            if revertToJ >= 1 and aM in Globals.USFMParagraphMarkers and not cT:
                                # These markers apply to the next line, i.e., to our current v line
                                revertToJ -= 1
                                assert( lineCount > 0 )
                                lineCount -= 1
                                aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                                while revertToJ >= 1 and aM not in ('c','v~','p~'): # was in ('s1','s2','s3','r','p','q1','p~',):
                                    #assert( cT ) # Should have text (for a completed Bible at least)
                                    revertToJ -= 1
                                    assert( lineCount > 0 )
                                    lineCount -= 1
                                    if revertToJ==0: print( "InternalBibleIndex.makeIndex: Get out of here" ); break
                                    aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                            elif aM not in ('c','v~','p~'): # was in ('s1','s2','s3','r','p','q1','p~',): # Shouldn't happen but just in case
                                if Globals.debugFlag: print( "InternalBibleIndex.makeIndex: just in case", aM, self.BBB, strC, strV )
                                revertToJ = j - 1
                                assert( lineCount > 0 )
                                lineCount -= 1
                    saveAnythingOutstanding() # with the adjusted lineCount
                    # Remove verse ranges, etc. and then save the verse number
                    strV = entry.getCleanText()
                    digitV = ''
                    for char in strV:
                        if char.isdigit(): digitV += char
                        else: # the first non-digit in the verse "number"
                            if Globals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                            break # ignore the rest
                    #assert( strV != '0' or self.BBB=='PSA' ) # Not really handled properly yet
                    saveCV, saveJ = (strC,digitV,), revertToJ
                    lineCount += (j-revertToJ) + 1 # For the v
                elif strC == '0': # Still in the introduction
                    # Each line is considered a new "verse" entry in chapter "zero"
                    assert( saveCV is None and saveJ is None )
                    self.indexData[(strC,strV)] = InternalBibleIndexEntry( j, 1, context )
                    Vi = int( strV )
                    assert( Vi == j )
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert( lineCount == 0 )
                else: # All the other lines don't cause a new index entry to be made
                    lineCount += 1
                #if j > 10: break
            saveAnythingOutstanding()
        else: # it's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            saveCV = saveJ = None
            lineCount, context = 0, None # lineCount is the number of datalines pointed to by this index entry
            strC, strV = '0', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                #print( "  makeIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '...') )
                marker = entry.getMarker()
                if Globals.debugFlag and marker in Globals.USFMParagraphMarkers:
                    assert( not entry.getText() and not entry.getCleanText() and not entry.getExtras() )
                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    saveAnythingOutstanding()
                    # Save anything before the first verse number as verse "zero"
                    strC, strV = entry.getCleanText(), '0'
                    assert( strC != '0' )
                    #saveCV, saveJ = (strC,strV,), j
                    lineCount += 1
                elif marker == 'v':
                    assert( strC != '0' ) # Should be in a chapter by now
                    print( "Why do we have a verse number in a {} book?".format( self.BBB ) )
                    print( "  makeIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '...') )
                    saveAnythingOutstanding() # with the adjusted lineCount
                    if 0:
                        # Remove verse ranges, etc. and then save the verse number
                        strV = entry.getCleanText()
                        digitV = ''
                        for char in strV:
                            if char.isdigit(): digitV += char
                            else: # the first non-digit in the verse "number"
                                if Globals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                                break # ignore the rest
                        #assert( strV != '0' or self.BBB=='PSA' ) # Not really handled properly yet
                        saveCV, saveJ = (strC,digitV,), revertToJ
                elif strC == '0': # Still in the introduction
                    # Each line is considered a new "verse" entry in chapter "zero"
                    assert( saveCV is None and saveJ is None )
                    self.indexData[(strC,strV)] = InternalBibleIndexEntry( j, 1, context )
                    Vi = int( strV )
                    assert( Vi == j )
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert( lineCount == 0 )
                else: # All the other lines don't cause a new index entry to be made
                    lineCount += 1
            saveAnythingOutstanding()

        self._indexedFlag = True
        if Globals.strictCheckingFlag or Globals.debugFlag: self.checkIndex()
    # end of InternalBibleIndex.makeIndex


    def checkIndex( self ):
        """
        Just run a quick internal check on the index.
        """
        if Globals.verbosityLevel > 2: print(  "  " + _("Checking {} {} {} index entries...").format( len(self.indexData), self.name, self.BBB ) )
        if Globals.verbosityLevel > 3: print( self )

        for ixKey in self.indexData:
            #print( ixKey ); halt
            C, V = ixKey
            if not C.isdigit():
                logging.critical( "InternalBibleIndex.checkIndex: Non-digit C entry in {} {} {}:{}".format( self.name, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleIndex.checkIndex: Non-digit V entry in {} {} {}:{}".format( self.name, self.BBB, repr(C), repr(V) ) )

        try: sortedIndex = sorted( self.indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleIndex.checkIndex: Unable to sort index for {} {}".format( self.name, self.BBB ) )
            sortedIndex = self.indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.indexData[key]
            #entries, context = self.getEntries( key )
            #print( "checkIndex display", j, key, indexEntry, entries )
            #if self.BBB!='FRT' and j>30: break


        lastKey = nextKey = nextNextKey = None
        for k, key in enumerate( sortedIndex ):
            # Try getting the next couple of keys also (if they exist)
            try: nextKey = sortedIndex[k+1]
            except IndexError: nextKey = None
            except KeyError: print( "nextKeyError1", k, len(sortedIndex), repr(key) ); nextKey = None
            try: nextNextKey = sortedIndex[k+2]
            except IndexError: nextNextKey = None
            except KeyError: print( "nextKeyError2", k, len(sortedIndex), repr(key) ); nextKey = None
            C, V = key

            indexEntry = self.indexData[key]
            entries, context = self.getEntries( key )
            markers = []
            anyText = anyExtras = False
            for entry in entries:
                marker = entry.getMarker()
                markers.append( marker )
                if marker not in ('c','v'): # These always have to have text
                    if entry.getCleanText(): anyText = True
                    if entry.getExtras(): anyExtras = True

            #print( "InternalBibleIndex.checkIndex line", self.BBB, key, indexEntry, entries, markers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '0': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in markers:
                        logging.critical( "InternalBibleIndex.checkIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                    if Globals.debugFlag and debuggingThisModule: assert( 'c' in markers )
                else: assert( 'v' in markers )
                if 'p' in markers: assert( 'p~' in markers or 'v' in markers )
                if 'q1' in markers or 'q2' in markers: assert( 'v' in markers or 'p~' in markers )

                previousMarker = nextMarker = None # But these skip over rem (remark markers)
                for j, marker in enumerate( markers ):
                    #print( self.BBB, C, V, j, marker, previousMarker, nextMarker )

                    # Work out the next marker (skipping over rem markers)
                    offset = 1
                    while True:
                        try: nextMarker = markers[j+offset]
                        except: nextMarker = None
                        if nextMarker != 'rem': break
                        offset += 1

                    # Check the various series of markers
                    if marker == 'cp': assert( previousMarker in ('c','c~',None) ) # WEB Ps 151 gives None -- not totally sure why yet?
                    elif marker == 'c#': assert( nextMarker in ( 'v', 'vp~', ) )
                    elif marker == 'v':
                        if markers[-1] != 'v' and nextMarker not in ('v~','¬v',): # end marker if verse is blank
                            logging.critical( "InternalBibleIndex.checkIndex: Probable v encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if Globals.debugFlag and debuggingThisModule: halt
                    elif marker == 'vp~': assert( nextMarker == 'v' )
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleIndex.checkIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.name, self.BBB, C, V, entries ) )
                            if Globals.debugFlag and debuggingThisModule: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','c#','¬p'):
                            if lastKey: print( "InternalBibleIndex.checkIndex: lastKey1", self.BBB, lastKey, self.getEntries( lastKey )[0] )
                            logging.critical( "InternalBibleIndex.checkIndex: Probable p encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if nextKey: print( "  InternalBibleIndex.checkIndex: nextKey1", self.BBB, nextKey, self.getEntries( nextKey )[0] )
                            if nextNextKey: print( "  InternalBibleIndex.checkIndex: nextNextKey1", self.BBB, nextNextKey, self.getEntries( nextNextKey )[0] )
                            if Globals.debugFlag and debuggingThisModule: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: print( "InternalBibleIndex.checkIndex: lastKey2", self.BBB, lastKey, self.getEntries( lastKey )[0] )
                            logging.critical( "InternalBibleIndex.checkIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                            if nextKey: print( "  InternalBibleIndex.checkIndex: nextKey2", self.BBB, nextKey, self.getEntries( nextKey )[0] )
                            if nextNextKey: print( "  InternalBibleIndex.checkIndex: nextNextKey2", self.BBB, nextNextKey, self.getEntries( nextNextKey )[0] )
                            if Globals.debugFlag and debuggingThisModule: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                                logging.critical( "InternalBibleIndex.checkIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                                if Globals.debugFlag and debuggingThisModule: halt
                        elif marker=='q3' and nextMarker not in ('p~', '¬q3'):
                                logging.critical( "InternalBibleIndex.checkIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                                if Globals.debugFlag and debuggingThisModule: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                                logging.critical( "InternalBibleIndex.checkIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.name, self.BBB, C, V, entries ) )
                                if Globals.debugFlag and debuggingThisModule: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '0': # the book introduction
                pass
            else: # not the book introduction
                if  V=='0': # chapter introduction
                    #print( self.BBB, C, V, markers, entries )
                    #newKey = (C, '1')
                    #try:
                        #iE = self.indexData[newKey]
                        #iD, ct = self.getEntries( newKey )
                    #except KeyError: pass
                    #print( self
                    #print( " ", newKey, iD, ct )
                    if self.BBB=='ACT' and C=='8':
                        if 'p' in markers:
                            logging.critical( "InternalBibleIndex.checkIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.name ) )
                        else:
                            if 's1'  in markers or 'r' in markers or 'p' in markers or 'q1' in markers:
                                print( "xyz", key, entries )
                            assert( 's1' not in markers and 'r' not in markers and 'p' not in markers and 'q1' not in markers )

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleIndex.checkIndex: wrong {} {} chapter number '{}' expected '{}'".format( self.name, self.BBB, cleanText, C ) )
                        #if Globals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleIndex.checkIndex: wrong {} {} {} verse number '{}' expected '{}'".format( self.name, self.BBB, C, cleanText, V ) )
                            #if Globals.debugFlag: halt
            lastKey = key
        #if self.BBB=='FRT': halt
    # end of InternalBibleIndex.checkIndex
# end of class InternalBibleIndex



def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    print( "Since these are only helper classes, they can't actually do much at all." )
    print( "  Try running USFMBibleBook or USXXMLBibleBook which use these classes." )

    #IBB = InternalBibleInternals( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = "Dummy test Internal Bible Book object"
    #IBB.objectTypeString = "DUMMY"
    #IBB.sourceFilepath = "Nowhere"
    #if Globals.verbosityLevel > 0: print( IBB )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of InternalBibleInternals.py