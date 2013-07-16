#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBibleInternals.py
#   Last modified: 2013-07-15 by RJH (also update ProgVersion below)
#
# Module handling the internal markers for Bible books
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

ProgName = "Bible internals handler"
ProgVersion = "0.02"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
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



class InternalBibleEntry:
    """
    This class represents an entry in the _processedLines list.
    """

    def __init__( self, marker, originalMarker, adjustedText, cleanText, extras ):
        """
        Accept the parameters and double-check them if requested.
        """
        if Globals.debugFlag or Globals.strictCheckingFlag:
            #print( "InternalBibleEntry.__init__( {}, {}, {}, {}, {} )".format( marker, originalMarker, adjustedText[:35], cleanText[:35], extras ) )
            assert( marker and isinstance( marker, str ) ) # Mustn't be blank
            assert( originalMarker and isinstance( originalMarker, str ) ) # Mustn't be blank
            assert( isinstance( adjustedText, str ) )
            assert( isinstance( cleanText, str ) )
            assert( '\\' not in cleanText )
            assert( isinstance( extras, list ) )
            if extras:
                #print( "extras:", extras )
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    assert( isinstance( extraType, str ) and extraType in ('fn','xr','sr','sn',) )
                    assert( isinstance( extraIndex, int ) and extraIndex >= 0 )
                    assert( isinstance( extraText, str ) and extraText ) # Mustn't be blank
                    assert( isinstance( cleanExtraText, str ) and cleanExtraText ) # Shouldn't be blank
                    if '\\' in cleanExtraText: print( "How does a backslash remain in cleanExtraText '{}".format( cleanExtraText ) )
                    assert( '\\' not in cleanExtraText )
                    assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                    for letters in ( 'f', 'x', 'fe', 'ef' ): # footnote, cross-ref, endnotes, studynotes
                        assert( '\\'+letters+' ' not in extraText )
                        assert( '\\'+letters+'*' not in extraText )
            #assert( marker in Globals.USFMMarkers or marker in NON_USFM_MARKERS )
            if marker not in Globals.USFMMarkers and marker not in NON_USFM_MARKERS:
                print( "InternalBibleEntry doesn't handle '{}' marker yet.".format( marker ) )
        self.marker, self.originalMarker, self.adjustedText, self.cleanText, self.extras = marker, originalMarker, adjustedText, cleanText, extras
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
        else: raise IndexError
    # end of InternalBibleEntry.__getitem__

    def getMarker( self ): return self.marker
    def getOriginalMarker( self ): return self.originalMarker
    def getText( self ): return self.adjustedText
    def getCleanText( self ): return self.cleanText
    def getExtras( self ): return self.extras


    def getFullText( self ):
        """
        Returns the full text with footnotes and cross-references reinserted.
        """
        result = self.adjustedText
        offset = 0
        for extraType, extraIndex, extraText, cleanExtraText in self.extras: # do any footnotes and cross-references
            #print( "{} at {} = '{}' ({})".format( extraType, extraIndex, extraText, cleanExtraText ) )
            #print( "  was '{}'".format( result ) )
            ix = extraIndex + offset
            result = '{}\\{} {}\\{}*{}'.format( result[:ix], extraType, extraText, extraType, result[ix:] )
            #print( "  now '{}'".format( result ) )
            offset += len(extraText ) + 2*len(extraType) + 4
        #if result != self.adjustedText:
            #if len(self.extras) > 1:
                #print( "Was '{}'".format( self.cleanText ) )
                #print( "And '{}'".format( self.adjustedText ) )
                #print( "Now '{}'".format( result ) )
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
        """
        result = "InternalBibleEntryList object:"
        if not self.data: result += "\n  Empty."
        else:
            dataLen = len( self.data )
            for j, entry in enumerate( self.data ):
                if Globals.debugFlag: assert( isinstance( entry, InternalBibleEntry ) )
                cleanAbbreviation = entry.cleanText if len(entry.cleanText)<100 else (entry.cleanText[:50]+'...'+entry.cleanText[-50:])
                result += "\n  {}{}/ {} = {}".format( ' ' if j<9 and dataLen>=10 else '', j+1, entry.marker, repr(cleanAbbreviation) )
                if j>=20 and dataLen>20:
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


    def append( self, something ):
        assert( isinstance( something, InternalBibleEntry ) )
        self.data.append( something )
    # end of InternalBibleEntryList.append

    def pop( self ): # Doesn't allow a parameter
        return self.data.pop()
    # end of InternalBibleEntryList.append
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
# end if class InternalBibleIndexEntry



class InternalBibleIndex:
    """
    Handles the C:V index for an internal Bible.
    """
    def __init__( self, bookReferenceCode ):
        """
        Creates the index for a Bible book.

        The book code is stored to enable better error messages.
        """
        self.bookReferenceCode = bookReferenceCode
    # end of InternalBibleIndex.__init__


    def __str__( self ):
        """
        Just display a simplified view of the list of entries.
        """
        result = "InternalBibleIndex object for {}:".format( self.bookReferenceCode )
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

        The keys to the dictionary are (C,V,) 2-tuples.
        The dictionary entries are (ix,lineCount,context) 3-tuples where
            ix is the index into givenBibleEntries,
            lineCount is the number of entries, and
            context is a list containing contextual markers which still apply to this entry.
        """
        #print( "InternalBibleIndex.makeIndex( {} )".format( givenBibleEntries ) )
        self.givenBibleEntries = givenBibleEntries # Keep a pointer to the original entries
        #if self.bookReferenceCode=='PHM': print( self.givenBibleEntries[:20] ); halt
        self.indexData = {}


        def saveAnythingOutstanding():
            """
            Save any outstanding index entries.
            """
            nonlocal saveCV, saveJ, lineCount, context
            if saveCV and saveJ is not None:
                #print( "saveAnythingOutstanding", self.bookReferenceCode, saveCV, saveJ, lineCount, context )
                #if saveCV == ('0','0'): halt
                #assert( 1 <= lineCount <= 120 ) # Could potentially be even higher for bridged verses (e.g., 1Chr 11:26-47, Ezra 2:3-20) and where words are stored individually
                if saveCV in self.indexData and Globals.verbosityLevel > 2:
                    logging.critical( "makeIndex.saveAnythingOutstanding: replacing index entry {} {}:{}".format( self.bookReferenceCode, C, V ) )
                    logging.error( "  mI:saO was", self.indexData[saveCV] )
                    ix,lc,ct = self.indexData[saveCV]
                    for ixx in range( ix, ix+lc ):
                        logging.error( "   mI:saO ", self.givenBibleEntries[ixx], ct )
                    logging.error( "  mI:saO now", (saveJ,lineCount,context) )
                    for ixx in range( saveJ, saveJ+lineCount ):
                        logging.error( "   mI:saO ", self.givenBibleEntries[ixx], context )
                self.indexData[saveCV] = InternalBibleIndexEntry( saveJ, lineCount, context )
                saveCV = saveJ = None
                lineCount = 0
        # end of saveAnythingOutstanding


        if Globals.verbosityLevel > 3: print( "    " + _("Indexing {} {} entries...").format( len(self.givenBibleEntries), self.bookReferenceCode ) )
        saveCV = saveJ = None
        lineCount, context = 0, None # lineCount is the number of datalines pointed to by this index entry
        C, V = '0', '0'
        for j, entry in enumerate( self.givenBibleEntries):
            #print( "  makeIndex", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '...') )
            if entry.getMarker() in ( 'p','q1','q2','q3','q4' ):
                assert( not entry.getText() and not entry.getCleanText() and not entry.getExtras() )
            if entry.getMarker() == 'c': # A new chapter always means that it's a clean new entry
                saveAnythingOutstanding()
                # Save anything before the first verse number as verse "zero"
                C, V = entry.getCleanText(), '0'
                assert( C != '0' )
                saveCV, saveJ = (C,V,), j
                lineCount += 1
            elif entry.getMarker() == 'v':
                assert( C != '0' ) # Should be in a chapter by now
                # Go back and look what we passed that might actually belong with this verse
                revertToJ = j
                if revertToJ >= 1: # we have a processedLine to go back to
                    aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                    if aM == 'c#':
                        assert( cT ) # Should have a chapter number here
                        revertToJ -= 1
                        assert( lineCount > 0 )
                        lineCount -= 1
                        #print( "going to", revertToJ-1 )
                        aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                    if revertToJ >= 1 and aM in ('p','q1','q2','q3',) and not cT: # These markers apply to the next line, i.e., to our current v line
                        revertToJ -= 1
                        assert( lineCount > 0 )
                        lineCount -= 1
                        aM,cT = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                        if revertToJ >= 1 and aM in ('s1','s2','s3',):
                            #assert( cT ) # Should have text (for a completed Bible at least)
                            revertToJ -= 1
                            assert( lineCount > 0 )
                            lineCount -= 1
                    elif aM in ('s1','s2','s3',): # Shouldn't happen but just in case
                        if Globals.debugFlag: print( "InternalBibleIndex.makeIndex: just in case", aM, self.bookReferenceCode, C, V )
                        revertToJ = j - 1
                        assert( lineCount > 0 )
                        lineCount -= 1
                saveAnythingOutstanding()
                # Remove verse ranges, etc. and then save the verse number
                V = entry.getCleanText()
                digitV = ''
                for char in V:
                    if char.isdigit(): digitV += char
                    else:
                        if Globals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.bookReferenceCode, C, V ) )
                        break # ignore the rest
                #assert( V != '0' or self.bookReferenceCode=='PSA' ) # Not really handled properly yet
                saveCV, saveJ = (C,digitV,), revertToJ
                lineCount += (j-revertToJ) + 1 # For the v
            elif C == '0': # Still in the introduction
                # Each line is considered a new "verse" entry in chapter "zero"
                assert( saveCV is None and saveJ is None )
                self.indexData[(C,V)] = InternalBibleIndexEntry( j, 1, context )
                Vi = int( V )
                assert( Vi == j )
                V = str( Vi + 1 ) # Increment the verse number
                lastJ = j
                assert( lineCount == 0 )
            else: # All the other lines don't cause a new index entry to be made
                lineCount += 1
            #if j > 10: break
        saveAnythingOutstanding()

        if 0:
            for j, entry in enumerate( self.givenBibleEntries):
                print( j, entry.getMarker(), entry.getCleanText()[:60] + ('' if len(entry.getCleanText())<60 else '...') )
                #if j>breakAt: break
            def getKey( CVALX ):
                CV, ALX = CVALX
                C, V = CV
                try: Ci = int(C)
                except: Ci = 300
                try: Vi = int(V)
                except: Vi = 300
                return Ci*1000 + Vi
            for CV,ALX in sorted(self.indexData.items(), key=getKey): #lambda s: int(s[0][0])*1000+int(s[0][1])): # Sort by C*1000+V
                C, V = CV
                #A, L, X = ALX
                print( "{}:{}={},{},{}".format( C, V, ALX.getEntryIndex(), ALX.getEntryCount(), ALX.getContext() ), end='  ' )
            halt
        self._indexedFlag = True

        if Globals.debugFlag: self.checkIndex()
    # end of InternalBibleIndex.makeIndex

    def checkIndex( self ):
        """
        Just run a quick internal check on the index.
        """
        if Globals.verbosityLevel > 2: print(  _("Checking {} {} index entries...").format( len(self.indexData), self.bookReferenceCode ) )
        if Globals.verbosityLevel > 3: print( self )

        #for j, key in enumerate( sorted( self.indexData, key=lambda s: int(s[0])*1000+int(s[1]) ) ):
            #C, V = key
            #indexEntry = self.indexData[key]
            #entries, context = self.getEntries( key )
            #print( "checkIndex display", j, key, indexEntry, entries )
            #if j>10: break

        for key in self.indexData:
            C, V = key
            indexEntry = self.indexData[key]
            entries, context = self.getEntries( key )
            #print( key, indexEntry, entries )
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleIndex.checkIndex: wrong {} chapter number '{}' expected '{}'".format( self.bookReferenceCode, cleanText, C ) )
                        #if Globals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleIndex.checkIndex: wrong {} {} verse number '{}' expected '{}'".format( self.bookReferenceCode, C, cleanText, V ) )
                            #if Globals.debugFlag: halt
        #halt
    # end if InternalBibleIndex.checkIndex
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