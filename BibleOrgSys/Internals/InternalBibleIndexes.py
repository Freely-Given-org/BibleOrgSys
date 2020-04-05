#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InternalBibleIndexes.py
#
# Module handling the internal objects for Bible books
#
# Copyright (C) 2010-2019 Robert Hunt
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
TODO: Rewrite makeCVIndex to take advantage of the new v= fields.

Module for defining and manipulating Bible indexes including:

    InternalBibleCVIndexEntry
    InternalBibleCVIndex
        Everything before chapter 1 is considered chapter -1.
        The first line in chapter -1 is considered verse 0
            and each successive line has a successive verse number.
        Everything before verse 1 in regular chapters
            is considered as verse 0, e.g., many section headings, etc.

    InternalBibleSectionIndexEntry
    InternalBibleSectionIndex

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

    The introduction is stored as chapter '-1'. (All our chapter and verse "numbers" are stored as strings.)
        (We allow for some rare printed Roman Catholic Bibles that have an actual chapter 0.)
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-13' # by RJH
SHORT_PROGRAM_NAME = "BibleIndexes"
PROGRAM_NAME = "Bible indexes handler"
PROGRAM_VERSION = '0.77'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False
MAX_NONCRITICAL_ERRORS_PER_BOOK = 4


from typing import Dict, List, Tuple, Optional
import logging
import re

if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Internals.InternalBibleInternals import BOS_NESTING_MARKERS, BOS_END_MARKERS
from BibleOrgSys.Reference.USFM3Markers import USFM_ALL_TITLE_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, \
                        USFM_ALL_SECTION_HEADING_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS # OFTEN_IGNORED_USFM_HEADER_MARKERS



BOS_NON_CHAPTER_BOOKS = ( 'FRT', 'PRF', 'ACK', 'INT', 'TOC', 'GLS', 'CNC', 'NDX', 'TDX', 'BAK', 'OTH',
                          'XXA','XXB','XXC','XXD','XXE','XXF','XXG',
                          'UNK', '???', )



class InternalBibleCVIndexEntry:
    """
    Holds the following information:
        1/ entryIndex: the index into the BibleEntryList
            REMOVED: indexNext: the index of the next BibleEntry
        2/ entryCount: the number of BibleEntries
        3/ context: a list containing contextual markers which still apply to this entry.
    """
    def __init__( self, entryIndex:str, entryCount:int, context:Optional[List[str]]=None ) -> None:
        """
        """
        #if context: print( "XXXXXXXX", entryIndex, entryCount, context )
        if context is None: context:List[str] = []
        self.entryIndex, self.entryCount, self.context = entryIndex, entryCount, context
        #self.indexNext = self.entryIndex + entryCount
    # end of InternalBibleCVIndexEntry.__init__

    def __str__( self ) -> str:
        """
        Just display a simplified view of the index entry.
        """
        result = "InternalBibleCVIndexEntry object: ix={} cnt={} ixE={}{}" \
            .format( self.entryIndex, self.entryCount, self.entryIndex + self.entryCount,
                    " ctxt={}".format(self.context) if self.context else '' )
        return result
    # end of InternalBibleCVIndexEntry.__str__

    def __len__( self ) -> int: return 3
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
    # end of InternalBibleCVIndexEntry.__getitem__

    def getEntryIndex( self ) -> int: return self.entryIndex
    def getNextEntryIndex( self ) -> int: return self.entryIndex + self.entryCount # self.indexNext
    def getEntryCount( self ) -> int: return self.entryCount
    def getContext( self ) -> Optional[List[str]]: return self.context
# end of class InternalBibleCVIndexEntry



class InternalBibleCVIndex:
    """
    Handles the C:V index for an internal Bible.
    """
    def __init__( self, workName, BBB ):
        """
        Creates the index object for a Bible book.

        The book code is stored to enable better error messages.
        """
        self.workName, self.BBB = workName, BBB
    # end of InternalBibleCVIndex.__init__


    def __str__( self ):
        """
        Just display a simplified view of the list of entries.
        """
        result = "InternalBibleCVIndex object for {}:".format( self.BBB )
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
    # end of InternalBibleCVIndex.__str__


    def __len__( self ) -> int: len( self.__indexData )
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
    # end of InternalBibleCVIndex.__iter__


    def getEntries( self, CVkey:Tuple[str,str] ):
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()]
    # end of InternalBibleCVIndex.getEntries


    def getEntriesWithContext( self, CVkey:Tuple[str,str] ):
        """
        Given C:V, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this verse,
            along with the context for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()], indexEntry.getContext()
    # end of InternalBibleCVIndex.getEntriesWithContext


    def makeCVIndex( self, givenBibleEntries ) -> None:
        """
        Index the Bible book lines for faster reference.

        The parameter is a InternalBibleEntryList(), i.e., self._processedLines (from InternalBibleBook)
            i.e., a specialised list of InternalBibleEntry objects.

        The keys to the index dictionary for each Bible book are (C,V,) 2-tuples.
            Chapter -1 is the book introduction
                Each line in chapter -1 is a successive 'verse' number (usually the id line is 'verse' 0)
            For each proper chapter (usually starting with 1), verse 0 is the chapter introduction.
                Often this contains only the 'c' entry.
                Section headings are put with the following text / verse.

        The created dictionary entries are (ix,indexEntryLineCount,contextMarkerList) 3-tuples where
            ix is the index into givenBibleEntries,
            indexEntryLineCount is the number of entries for this verse, and
            contextMarkerList is a list containing contextual markers which still apply to this entry.
        """
        if debuggingThisModule: print( "\nInternalBibleCVIndex.makeCVIndex( {} )".format( givenBibleEntries ) )
        self.givenBibleEntries = givenBibleEntries # Keep a pointer to the original Bible entries
        self.__indexData:Dict[Tuple[str,str],InternalBibleCVIndexEntry] = {}
        errorData:List[str] = []


        def printIndexEntry( ie ):
            result = str( ie )
            for j in range( ie.getEntryIndex(), ie.getNextEntryIndex() ):
                result += "\n  {}".format( givenBibleEntries[j] )
            return result
        # end of printIndexEntry


        def saveAnythingOutstanding():
            """
            Save the outstanding index entry if any
                into self.__indexData (a dict).
            """
            nonlocal saveCV, saveJ, indexEntryLineCount, errorData
            if saveCV and saveJ is not None:
                if debuggingThisModule:
                    print( "    saveAnythingOutstanding", self.BBB, saveCV, saveJ, indexEntryLineCount )
                #if saveCV == ('0','0'): halt
                #assert 1 <= indexEntryLineCount <= 120 # Could potentially be even higher for bridged verses (e.g., 1Chr 11:26-47, Ezra 2:3-20) and where words are stored individually
                if saveCV in self.__indexData: # we already have an index entry for this C:V
                    #print( "makeCVIndex.saveAnythingOutstanding: already have an index entry @ {} {}:{}".format( self.BBB, strC, strV ) )
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


        # Main code of InternalBibleCVIndex.makeCVIndex
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "    " + _("Indexing {} {} {} entries…").format( len(self.givenBibleEntries), self.workName, self.BBB ) )

        # Firstly create the CV index keys with pointers to the actual lines
        if self.BBB in BOS_NON_CHAPTER_BOOKS:
            # It's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            saveCV = saveJ = None
            indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            strC, strV = '0', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                #print( "  makeCVIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
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
                    logging.warning( "makeCVIndex: Why do we have a verse number in a {} {} book without chapters?".format( self.workName, self.BBB ) )
                    if debuggingThisModule:
                        print( "  makeCVIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =",
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
                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new "verse" entry in chapter '-1'
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1)
                    #print( "makeCVIndexIntro", printIndexEntry( self.__indexData[(strC,strV)] ) )
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
            strC, strV = '-1', '0'
            for j, entry in enumerate( self.givenBibleEntries):
                if debuggingThisModule:
                    print( "  makeCVIndex1", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                marker = entry.getMarker()
                if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    # All text should have been moved into the following p~ marker
                    assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()

                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    if debuggingThisModule: print( "    Handle c {}".format( entry.getCleanText() ) )
                    saveAnythingOutstanding()
                    # Save anything before the first verse number as verse '-1'
                    strC, strV = entry.getCleanText(), '0'
                    assert strC != '-1'
                    saveCV, saveJ = (strC,strV,), j
                    indexEntryLineCount += 1

                elif marker == 'v': # This bit of indexing code is quite complex!
                    if debuggingThisModule: print( "    Handle v {}".format( entry.getCleanText() ) )
                    assert strC != '-1' # Should be in a chapter by now

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
                            if revertToJ==0: print( "InternalBibleCVIndex.makeCVIndex: Get out of here" ); break
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
                        ##print( "  makeCVIndex check at {} {}".format( j, entry ) )
                        ##print( "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                        #vCount = 0
                        #for scj in range( indexEntryLineCount ):
                            #thisEntry = self.givenBibleEntries[ j + scj ] # This is an InternalBibleEntry
                            ##print( "      {}".format( thisEntry ) )
                            #if thisEntry.getMarker() == 'v': vCount += 1
                        ##print( "    vCount={}".format( vCount ) )
                        #if vCount > 1: # Should never happen -- verses should all have their own separate index entries
                            #print( "  makeCVIndex check for {} {} {}:{} at ({}) {}".format( self.workName, self.BBB, strC, strV, j, entry ) )
                            #print( "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                            #for scj in range( indexEntryLineCount ):
                                #print( "      {}".format( self.givenBibleEntries[ j + scj ] ) ) # This is an InternalBibleEntry
                            #print( "    vCount={}".format( vCount ) )
                            ##halt
                        ## Actually this seems to be fixed up down below somewhere (so doesn't seem to matter)
                    if 0 and debuggingThisModule:
                        #if strV == '4':
                            #halt
                        print( "Temp index currently ({}) {}".format( len(self.__indexData), self.__indexData ) )

                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new 'verse' entry in chapter '-1'
                    #   (usually the id line is 'verse' 0, i.e., -1:0)
                    if debuggingThisModule: print( "    Handle intro {}".format( entry.getCleanText() ) )
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1 )
                    #print( "makeCVIndex", printIndexEntry( self.__indexData[(strC,strV)] ) )
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
            logging.warning( "makeCVIndex.saveAnythingOutstanding: Needed to combine multiple index entries for {}".format( errorDataString ) )

        # Now calculate the contextMarkerList for each CV entry and create the proper (full) InternalBibleCVIndexEntries
        contextMarkerList = []
        for (C,V), (indexStart,count) in self.__indexData.items():
            if debuggingThisModule:
                print( "makeCVIndex for {} {} {}:{} {} {} {}".format( self.workName, self.BBB, C, V, indexStart, count, contextMarkerList ) )
            # Replace the existing (temporary) index entry to include a copy of the previous contextMarkerList
            #   e.g., a typical verse might be inside a paragraph in a section
            #            thus getting the contextMarkerList: ['chapters','c','s1','p']
            self.__indexData[(C,V)] = InternalBibleCVIndexEntry( indexStart, count, contextMarkerList[:] )
            for j in range( indexStart, indexStart+count ):
                entry = self.givenBibleEntries[j]
                marker = entry.getMarker()
                if debuggingThisModule: print( "  makeCVIndex {} marker: {} {}".format( j, marker, entry.getCleanText() ) )
                if marker[0]=='¬' and marker != '¬v': # We're closing a paragraph marker
                    originalMarker = marker[1:]
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        # Should be exactly one of these markers (open) in the contextMarkerList
                        # XXXXXXXXX Gets messed up by GNT Mrk 16:9 has two \s headings in a row !!!!!!!!!!!!!!!!!!!
                        if contextMarkerList.count(originalMarker)!=1:
                            print( "    makeCVIndex originalMarker: {!r} contextMarkerList={}".format( originalMarker, contextMarkerList ) )
                            logging.critical( "makeCVIndex found a nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            assert contextMarkerList.count( originalMarker ) == 1
                    try: # Remove first open occurrence of the marker just closed (e.g., s1 can occur after c and still be open)
                        if debuggingThisModule:
                            print( "    makeCVIndex: Removing {} from contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
                        contextMarkerList.remove( originalMarker )
                    except ValueError: # oops something went wrong
                        #print( 'makeCVIndex: marker = {}'.format( marker ) )
                        #print( 'makeCVIndex: entry = {}'.format( entry ) )
                        #print( 'makeCVIndex: contextMarkerList = {}'.format( contextMarkerList ) )
                        logging.critical( "makeCVIndex found an unknown nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        if contextMarkerList.count( originalMarker ):
                            print( "{}/ {} {}:{} {!r} {}".format( j, self.BBB, C, V, originalMarker, contextMarkerList ) )
                        assert contextMarkerList.count( originalMarker ) == 0
                if marker in BOS_NESTING_MARKERS and marker!='v':
                    if debuggingThisModule:
                        print( "    makeCVIndex: Adding {} to contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
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
            self.checkCVIndex() # Make sure our code above worked properly
    # end of InternalBibleCVIndex.makeCVIndex


    def checkCVIndex( self ):
        """
        Just run a quick internal check on the index.
        """
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print(  "  " + _("Checking {} {} {} CV index entries…").format( len(self.__indexData), self.workName, self.BBB ) )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
            print( self )

        # Check that all C,V entries (the index to the index) are digits
        for ixKey in self.__indexData:
            #print( ixKey ); halt
            C, V = ixKey
            if C!='-1' and not C.isdigit():
                logging.critical( "InternalBibleCVIndex.checkCVIndex: Non-digit C entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleCVIndex.checkCVIndex: Non-digit V entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )

        # Copy the index (dict) into a (sorted) list so that we can access entries sequentially for testing
        try: sortedIndex = sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleCVIndex.checkCVIndex: Unable to sort index for {} {}".format( self.workName, self.BBB ) )
            sortedIndex = self.__indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.__indexData[key]
            #entries = self.getEntries( key )
            #print( "checkCVIndex display", j, key, indexEntry, entries )
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
                logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable index or encoding error (multiple v entries) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                assert vCount <= 1

            #print( "InternalBibleCVIndex.checkCVIndex line", self.BBB, key, indexEntry, entries, foundMarkers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in foundMarkers:
                        logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert 'c' in foundMarkers
                else: assert 'v' in foundMarkers
                if 'p' in foundMarkers:
                    if 'p~' not in foundMarkers and 'v' not in foundMarkers:
                        logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable (early in chapter) p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        assert 'p~' in foundMarkers or 'v' in foundMarkers
                if 'q1' in foundMarkers or 'q2' in foundMarkers:
                    if 'v' not in foundMarkers and 'p~' not in foundMarkers:
                        logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable q1/q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
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
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable v encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    elif marker == 'vp#':
                        #print( "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.workName ) )
                        if debuggingThisModule:
                            if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','vp#','c#','¬p'):
                            if lastKey and debuggingThisModule: print( "InternalBibleCVIndex.checkCVIndex: lastKey1", self.BBB, lastKey, self.getEntries( lastKey ) )
# NOTE: temporarily down-graded from critical …
                            logging.error( "InternalBibleCVIndex.checkCVIndex: Probable p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleCVIndex.checkCVIndex: nextKey1", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleCVIndex.checkCVIndex: nextNextKey1", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: print( "InternalBibleCVIndex.checkCVIndex: lastKey2", self.BBB, lastKey, self.getEntries( lastKey ) )
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleCVIndex.checkCVIndex: nextKey2", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleCVIndex.checkCVIndex: nextNextKey2", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q3' and nextMarker not in ('v','p~', '¬q3'):
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '-1': # the book introduction
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
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.workName ) )
                        #else:
                            #if 's1'  in foundMarkers or 'r' in foundMarkers or 'p' in foundMarkers or 'q1' in foundMarkers:
                                #print( "xyz", key, entries )
                            #if self.workName != '1974_TB':
                                #assert 's1' not in foundMarkers and 'r' not in foundMarkers and 'p' not in foundMarkers and 'q1' not in foundMarkers

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleCVIndex.checkCVIndex: wrong {} {} chapter number {!r} expected {!r}".format( self.workName, self.BBB, cleanText, C ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleCVIndex.checkCVIndex: wrong {} {} {} verse number {!r} expected {!r}".format( self.workName, self.BBB, C, cleanText, V ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
            lastKey = key

        if 0 and debuggingThisModule: # Just print the beginning part of the index to view
            if self.BBB in ('GEN','MAT'):
                print( self )
                print( ' ', self.__indexData )
                for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                    print( " {:3} {}: {}".format( j, iKey, iEntry ) )
                    if iEntry.entryCount > 1:
                        for scj in range( iEntry.entryCount ):
                            print( "      {}".format( self.givenBibleEntries[ iEntry.entryIndex + scj ] ) ) # This is an InternalBibleEntry
                    if j > 40: break
                halt
        #if self.BBB=='FRT': halt
    # end of InternalBibleCVIndex.checkCVIndex
# end of class InternalBibleCVIndex



class InternalBibleSectionIndexEntry:
    """
    Holds the following information:
        1/ startCV:
        2/ endCV:
        3/ entryIndex: the index into the BibleEntryList
        4/ entryCount: the number of BibleEntries
        5/ context: a list containing contextual markers which still apply to this entry.
    """
    def __init__( self, startC:str, startV:str, endC:str, endV:str, startIx:int, endIx:int,
                            reasonMarker:str, sectionName:str, context:Optional[List[str]]=None ) -> None:
                 #startCV:str, endCV:str, entryIndex:int, entryCount:int, context:Optional[List[str]]=None ) -> None:
        """
        """
        #if context: print( "XXXXXXXX", entryIndex, entryCount, context )
        if context is None: context:List[str] = []
        self.startC, self.startV, self.endC, self.endV = startC, startV, endC, endV
        self.startIx, self.endIx, self.reasonMarker, self.sectionName = startIx, endIx, reasonMarker, sectionName
        self.context = context
    # end of InternalBibleSectionIndexEntry.__init__

    def __str__( self ):
        """
        Just display a simplified view of the index entry.
        """
        result = f"InternalBibleSectionIndexEntry object: CV={self.startC}:{self.startV}–{self.endC}:{self.endV}" \
                 f" ix={self.startIx}–{self.endIx} (cnt={self.endIx + 1 - self.startIx})" \
                 f" {self.reasonMarker}='{self.sectionName}'" \
                 f"{' ctxt={}'.format(self.context) if self.context else ''}"
        return result
    # end of InternalBibleSectionIndexEntry.__str__

    def __len__( self ): return 9
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            halt # not done yet
            #print( "ki2", keyIndex )
            #assert keyIndex.step is None
            #print( "param", *keyIndex.indices(len(self)) )
            #return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        if keyIndex == 0: return self.startC
        elif keyIndex == 1: return self.startV
        elif keyIndex == 2: return self.endC
        elif keyIndex == 3: return self.endV
        elif keyIndex == 4: return self.startIx
        elif keyIndex == 5: return self.endIx
        elif keyIndex == 6: return self.reasonMarker
        elif keyIndex == 7: return self.sectionName
        elif keyIndex == 8: return self.context
        else: raise IndexError
    # end of InternalBibleSectionIndexEntry.__getitem__

    #def getStartC( self ): return self.startC
    #def getEndC( self ): return self.endC
    #def getEntryIndex( self ): return self.entryIndex
    #def getNextEntryIndex( self ): return self.entryStartIndex + self.entryCount # self.indexNext
    #def getEntryCount( self ): return self.entryCount
    #def getContext( self ): return self.context

    def getNumLines( self ) -> int:
        return self.endIx + 1 - self.startIx
# end of class InternalBibleSectionIndexEntry



class InternalBibleSectionIndex:
    """
    Handles the C:V index for an internal Bible.
    """
    def __init__( self, bookObject, BibleObject ) -> None:
        """
        Creates the index object for a Bible book.

        The book code is stored to enable better error messages.
        """
        self.BBB = bookObject.BBB
        self.bookObject, self.BibleObject = bookObject, BibleObject # Can be deleted once index is created
        self.workName = bookObject.workName
    # end of InternalBibleSectionIndex.__init__


    def __str__( self ) -> str:
        """
        Just display a simplified view of the list of entries.
        """
        result = "InternalBibleSectionIndex object for {}:".format( self.BBB )
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
    # end of InternalBibleSectionIndex.__str__


    def __len__( self ) -> int:
        len( self.__indexData )
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
    # end of InternalBibleSectionIndex.__iter__


    def getEntries( self, CVkey ):
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()]
    # end of InternalBibleSectionIndex.getEntries


    def getEntriesWithContext( self, CVkey ):
        """
        Given C:V, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this verse,
            along with the context for this verse.

        Raises a KeyError if the CV key doesn't exist.
        """
        indexEntry = self.__indexData[CVkey]
        return self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()], indexEntry.getContext()
    # end of InternalBibleSectionIndex.getEntriesWithContext


    def makeSectionIndex( self ):
        """
        Index the Bible book lines for faster reference.

        The parameter is a InternalBibleEntryList(), i.e., self._processedLines (from InternalBibleBook)
            i.e., a specialised list of InternalBibleEntry objects.

        The keys to the index dictionary for each Bible book are (C,V,) 2-tuples.
            Chapter -1 is the book introduction
                Each line in chapter -1 is a successive 'verse' number (usually the id line is 'verse' 0)
            For each proper chapter (usually starting with 1), verse 0 is the chapter introduction.
                Often this contains only the 'c' entry.
                Section headings are put with the following text / verse.

        The created dictionary entries are (ix,indexEntryLineCount,contextMarkerList) 3-tuples where
            ix is the index into self.bookObject._processedLines,
            indexEntryLineCount is the number of entries for this verse, and
            contextMarkerList is a list containing contextual markers which still apply to this entry.
        """
        if debuggingThisModule: print( "\nInternalBibleSectionIndex.makeSectionIndex()…" )
        self.__indexData:Dict[str,Tuple[str,str,str,str,int,int,str]] = {}
        errorData = []

        if 'discoveryResults' not in self.BibleObject.__dict__:
            if debuggingThisModule: print( f"Need to discover results!!!" )
            self.BibleObject.discover()
        # The following line can give a KeyError if the BBB doesn't exist in the discoveryResults
        haveSectionHeadingsForBook = self.BibleObject.discoveryResults[self.BBB]['haveSectionHeadings']
        if debuggingThisModule: print( f"\nhaveSectionHeadingsForBook {self.BBB}={haveSectionHeadingsForBook}" ) #, self.discoveryResults[BBB] )
        needToSaveByChapter = not haveSectionHeadingsForBook \
                                or not BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(self.BBB)
        if debuggingThisModule: print( f"{self.BBB} needToSaveByChapter={needToSaveByChapter} since haveSectionHeadingsForBook={haveSectionHeadingsForBook} continuesThroughChapters={BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(self.BBB)}" )
        bookName = self.bookObject.getAssumedBookNames()[0]
        if debuggingThisModule: print( f"Got '{bookName}' for {self.BBB}" )

        def printIndexEntry( ie ):
            result = str( ie )
            for j in range( ie.getEntryIndex(), ie.getNextEntryIndex() ):
                result += "\n  {}".format( givenBibleEntries[j] )
            return result
        # end of printIndexEntry


        def saveAnythingOutstanding( startC:str, startV:str, endC:str, endV:str,
                                     startIx:int, endIx:int, reasonMarker:str, sectionName:str ) -> None:
            """
            Save the outstanding index entry if any
                into self.__indexData (a dict).

            start and end index numbers are inclusive, i.e., both those lines should be included!
            """
            if debuggingThisModule:
                print( f"         saveAnythingOutstanding( {startC}:{startV}-{endC}:{endV}"
                       f" {startIx}-{endIx} {reasonMarker}='{sectionName}' ) for {self.BBB}…" )
                assert isinstance( startC, str ) and isinstance( startV, str )
                assert isinstance( endC, str ) and isinstance( endV, str )
                assert isinstance( startIx, int ) and isinstance( endIx, int )
                assert isinstance( reasonMarker, str ) and isinstance( sectionName, str )

            # Handle any verse bridges
            if '-' in startV:
                if debuggingThisModule:
                    print( f"Adjusting startV={startV} verse bridge to {startV[:startV.find('-')]!r}" )
                startV = startV[:startV.find('-')]
            if '-' in endV:
                if debuggingThisModule:
                    print( f"Adjusting endV={endV} verse bridge to {endV[endV.find('-')+1:]!r}" )
                endV = endV[endV.find('-')+1:]

            # HAndle \ms1 specifics (v= doesn't occur before this)
            if reasonMarker=='ms1' and startC==endC:
                startV = str( int(startV) + 1 )
                if int(endV) < int(startV): endV = startV

            # Do some basic checking here
            if reasonMarker != 'c': assert endV != '0'
            assert int(endC) >= int(startC)
            if endC==startC: assert int(endV) >= int(startV) # Verse ranges shouldn't go backwards

            # If the last entry was very small, we might need to combine it with this one
            if self.__indexData:
                lastIndexEntryKey = list(self.__indexData.keys())[-1]
                lastIndexEntry = self.__indexData[lastIndexEntryKey]
                if lastIndexEntry.getNumLines() < 4:
                    if debuggingThisModule:
                        print( f"           Got a short index entry: {lastIndexEntry}" )
                    lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                    assert lStartC == lEndC
                    if reasonMarker == 's1' and lastIndexEntry.reasonMarker in ('c','ms1'):
                        if debuggingThisModule:
                            print( "           COMBINING index entries" )
                        startV, startIx = lastIndexEntry.startV, lastIndexEntry.startIx
                        reasonMarker = f'{lastIndexEntry.reasonMarker}/{reasonMarker}'
                        sectionName = f'{lastIndexEntry.sectionName}/{sectionName}'
                        del self.__indexData[lastIndexEntryKey] # Just to be sure

            # Since startV is the current verse number when a section heading or something is encountered,
            #   it may need to be adjusted
            #if startC == '-1' and reasonMarker == 'is1':
                #if debuggingThisModule:
                    #print( f"           Incrementing startV from {startV} to {str( int(startV) + 1 )} with {reasonMarker}" )
                #startV = str( int(startV) + 1 )
            #else:
            for entry in self.bookObject._processedLines[startIx:endIx]:
                marker, text = entry.getMarker(), entry.getCleanText()
                if debuggingThisModule: print( f"                  {marker}={text}" )
                if marker == 'v': # e.g., if we encountered section heading but hadn't encountered the verse number yet
                    if text != startV and '-' not in text: # Don't want to undo verse bridge work from above
                        if debuggingThisModule or startV != '0':
                            print( f"           Adjusting startV from {startV} to {text}" )
                        startV = text
                    break
                elif marker in ('v~','p~'): # e.g., if we encountered a section heading that's in the middle of a verse
                    if debuggingThisModule:
                        assert startV.isdigit()
                        print( f"           Adjusting startV from {startV} to {startV}b" )
                    # So the previous entry should end with 'a'
                    lastIndexEntryKey = list(self.__indexData.keys())[-1]
                    lastIndexEntry = self.__indexData[lastIndexEntryKey]
                    lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                    assert lEndC==startC and lEndV==startV
                    lEndV += 'a'
                    self.__indexData[(lStartC,lStartV)] = InternalBibleSectionIndexEntry(
                                                            lStartC, lStartV, lEndC, lEndV,
                                                            lStartIx, lEndIx, lReasonMarker, lSectionName, lContext)
                    startV += 'b'
                    break

            # Check that we don't overlap with the last entry
            if self.__indexData:
                lastIndexEntryKey = list(self.__indexData.keys())[-1]
                lastIndexEntry = self.__indexData[lastIndexEntryKey]
                lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                #if debuggingThisModule:
                    #print( f"          Got previous index entry: {lStartC}:{lStartV}–{lEndC}:{lEndV} {lStartIx}–{lEndIx} {lReasonMarker}={lSectionName} {lContext}" )
                if startC==lEndC and startV==lEndV: # We have overlapping entries
                    if startV.isdigit(): startV = f'{startV}a'
                    else: halt # Not sure how to handle overlapping entries

            # Save this new index entry
            if debuggingThisModule and (startC,startV) in self.__indexData:
                print( f"           About to rewrite {startC}:{startV} in section index" )
            self.__indexData[(startC,startV)] = InternalBibleSectionIndexEntry(startC, startV, endC, endV,
                                                                    startIx, endIx, reasonMarker, sectionName)
        # end of saveAnythingOutstanding


        # Main code of InternalBibleSectionIndex.makeSectionIndex
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( "    " + _("Indexing {} {} {} entries…").format( len(self.bookObject._processedLines), self.workName, self.BBB ) )

        # Firstly create the CV index keys with pointers to the actual lines
        if self.BBB in BOS_NON_CHAPTER_BOOKS:
            return
            ## It's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            #lastC = lastV = saveCV = saveJ = None
            #indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            #strC, strV = '0', '0'
            #for j, entry in enumerate( self.bookObject._processedLines ):
                ##print( "  makeSectionIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                #marker = entry.getMarker()
                #if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    #assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()
                #if marker == 'c': # A new chapter always means that it's a clean new index entry
                    #saveAnythingOutstanding()
                    ## Save anything before the first verse number as verse '-1'
                    #strC, strV = entry.getCleanText(), '0'
                    #assert strC != '0'
                    ##saveCV, saveJ = (strC,strV,), j
                    #indexEntryLineCount += 1
                #elif marker == 'v':
                    #assert strC != '0' # Should be in a chapter by now
                    #logging.warning( "makeSectionIndex: Why do we have a verse number in a {} {} book without chapters?".format( self.workName, self.BBB ) )
                    #if debuggingThisModule:
                        #print( "  makeSectionIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =",
                            #entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                    #saveAnythingOutstanding() # with the adjusted indexEntryLineCount
                    ##if 0:
                        ### Remove verse ranges, etc. and then save the verse number
                        ##strV = entry.getCleanText()
                        ##digitV = ''
                        ##for char in strV:
                            ##if char.isdigit(): digitV += char
                            ##else: # the first non-digit in the verse "number"
                                ##if BibleOrgSysGlobals.verbosityLevel > 3: print( "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                                ##break # ignore the rest
                        ###assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                        ##saveCV, saveJ = (strC,digitV,), revertToJ
                #elif strC == '-1': # Still in the introduction
                    ## Each line is considered a new "verse" entry in chapter '-1'
                    #assert saveCV is None and saveJ is None
                    ##print( "makeSectionIndexIntro", printIndexEntry( self.__indexData[(strC,strV)] ) )
                    #Vi = int( strV )
                    #assert Vi == j
                    #strV = str( Vi + 1 ) # Increment the verse number
                    #lastJ = j
                    #assert indexEntryLineCount == 0
                #else: # All the other lines don't cause a new index entry to be made
                    #indexEntryLineCount += 1
            #saveAnythingOutstanding()

        else: # Assume it's a normal C/V book
            lastC, lastV = '-1', ''
            strC, strV = '-1', '-1' # First line (id line) will be -1:0
            startC, startV = '-1', '0'
            lastMarkerReason, lastSectionName = 'Intro', self.BBB
            savedJ = 0
            for j, entry in enumerate( self.bookObject._processedLines ):
                assert isinstance(lastC, str) and isinstance(lastV, str)
                assert isinstance(strC, str) and isinstance(strV, str)
                assert isinstance(startC, str) and isinstance(startV, str)

                marker, text = entry.getMarker(), entry.getCleanText()
                if debuggingThisModule:
                    print( f"  makeSectionIndexLoop {self.BBB} {j}({savedJ}) str={strC}:{strV} {marker}={text} after last={lastC}:{lastV} '{lastMarkerReason}' with start={startC}:{startV}" )

                if marker == 'c':
                    if debuggingThisModule: print( f"    GotC {j:,} {self.BBB} c={text!r} after last={lastC}:{lastV} with start={startC}:{startV}" )
                    if strC == '-1': # The first chapter always means that it's a clean new index entry
                        if debuggingThisModule: print( f"    HandleC1 {j:,} {self.BBB} {strC}:{strV} c={text!r}" )
                        endC, endV = strC, strV
                        assert startC=='-1' and endC=='-1'
                        assert int(startV) == savedJ
                        assert int(endV) == j-1
                        assert j-1 > savedJ
                        saveAnythingOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                        savedJ = j
                        startC, startV = text, '0'
                        lastMarkerReason, lastSectionName = marker, None
                    # Save anything before the first verse number as verse '0'
                    strC, strV = text, '0'
                    assert strC != '-1'
                    if (needToSaveByChapter
                        or (self.BBB == 'PRO'
                            and text in ('11','12','13','14','15','16','17','18','19','20','21','22','26','27','28','29'))
                        ): # These chapters are often part of a large section
                        if debuggingThisModule: print( f"      HandleC {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                        endC, endV = lastC, lastV
                        if lastSectionName:
                            saveAnythingOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                            lastMarkerReason = marker
                        savedJ = j
                        startC, startV = strC, strV
                        lastMarkerReason, lastSectionName = marker, f'{bookName} {strC}'
                elif marker in  ('v','v='):
                    # NOTE: The v= marker comes before the section headings
                    #if debuggingThisModule: print( f"    Handle {j:,} {self.BBB} c={strC}:v='{text}'" )
                    assert strC != '-1' # Must be in a chapter by now
                    strV = text
                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new 'verse' entry in chapter '-1'
                    #   (usually the id line is 'verse' 0, i.e., -1:0)
                    lastV = strV
                    strV = str( j ) # Increment the verse number
                    if debuggingThisModule: print( f"      Got {j:,} intro: {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )

                if marker in ('s1','ms1','is1'):
                    if debuggingThisModule: print( f"      HandleSH {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                    #print( f"lastC={lastC!r} lastV={lastV!r}" )
                    endC, endV = lastC, lastV
                    #print( f"endC={endC!r} endV={endV!r}" )
                    assert endV != '0'
                    if lastSectionName:
                        if j-1 == savedJ \
                        or int(endC) < int(startC):# There's only one entry line
                            if debuggingThisModule:
                                print(f"        FIXING1 end={endC}:{endV} to {startC}:{startV}" )
                            endC, endV = startC, startV
                        #if lastMarkerReason=='c' and marker=='ms1':
                            #print(f"        FIXING2 lastMarkerReason={lastMarkerReason} to {marker}" )
                            #lastMarkerReason = marker
                        saveAnythingOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                    savedJ = j
                    startC, startV = strC, str(j) if strC=='-1' else strV
                    #if marker == 'ms1': # v= markers don't precede these
                        #startV = str( int(startV) + 1 )
                    lastMarkerReason, lastSectionName = marker, text
                #elif marker == 'c':
                    #if (needToSaveByChapter
                        #or (self.BBB == 'PRO'
                            #and cleanText in ('11','12','13','14','15','16','17','18','19','20','21','22','26','27','28','29'))
                        #):
                        #if debuggingThisModule: print( f"      HandleC {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                        #endC, endV = lastC, lastV
                        #if lastSectionName:
                            #saveAnythingOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                            #lastMarkerReason = marker
                        #savedJ = j
                        #startC, startV = strC, strV
                        #lastSectionName = f'{bookName} {strC}'
                elif marker in ('v~','p~'): # We have verse data
                    if not lastSectionName:
                        if debuggingThisModule: print( f"Setting lastSectionName for verse info found at {strC}:{strV}" )
                        lastSectionName = f"{bookName} {strC}"
                # else: # All the other lines don't cause a new index entry to be made

                if marker == 'v': # Don't update lastC/lastV too often -- only for actual verses
                    lastC, lastV = strC, strV

            endC, endV = strC, strV
            saveAnythingOutstanding( startC, startV, endC, endV, savedJ, j, lastMarkerReason, lastSectionName )

        if debuggingThisModule:
            print( f"We got {len(self.__indexData)} index entries for {self.BBB}." )
            for j, (key,value) in enumerate(self.__indexData.items(), start=1):
                print( f"  {j:2}/ {key} = {value}" )
        return

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
            logging.warning( "makeSectionIndex.saveAnythingOutstanding: Needed to combine multiple index entries for {}".format( errorDataString ) )

        # Now calculate the contextMarkerList for each CV entry and create the proper (full) InternalBibleSectionIndexEntries
        contextMarkerList = []
        for (C,V), (indexStart,count) in self.__indexData.items():
            if debuggingThisModule:
                print( "makeSectionIndex for {} {} {}:{} {} {} {}".format( self.workName, self.BBB, C, V, indexStart, count, contextMarkerList ) )
            # Replace the existing (temporary) index entry to include a copy of the previous contextMarkerList
            #   e.g., a typical verse might be inside a paragraph in a section
            #            thus getting the contextMarkerList: ['chapters','c','s1','p']
            self.__indexData[(C,V)] = InternalBibleSectionIndexEntry( indexStart, count, contextMarkerList[:] )
            for j in range( indexStart, indexStart+count ):
                entry = self.givenBibleEntries[j]
                marker = entry.getMarker()
                if debuggingThisModule: print( "  makeSectionIndex {} marker: {} {}".format( j, marker, entry.getCleanText() ) )
                if marker[0]=='¬' and marker != '¬v': # We're closing a paragraph marker
                    originalMarker = marker[1:]
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        # Should be exactly one of these markers (open) in the contextMarkerList
                        # XXXXXXXXX Gets messed up by GNT Mrk 16:9 has two \s headings in a row !!!!!!!!!!!!!!!!!!!
                        if contextMarkerList.count(originalMarker)!=1:
                            print( "    makeSectionIndex originalMarker: {!r} contextMarkerList={}".format( originalMarker, contextMarkerList ) )
                            logging.critical( "makeSectionIndex found a nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            assert contextMarkerList.count( originalMarker ) == 1
                    try: # Remove first open occurrence of the marker just closed (e.g., s1 can occur after c and still be open)
                        if debuggingThisModule:
                            print( "    makeSectionIndex: Removing {} from contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
                        contextMarkerList.remove( originalMarker )
                    except ValueError: # oops something went wrong
                        #print( 'makeSectionIndex: marker = {}'.format( marker ) )
                        #print( 'makeSectionIndex: entry = {}'.format( entry ) )
                        #print( 'makeSectionIndex: contextMarkerList = {}'.format( contextMarkerList ) )
                        logging.critical( "makeSectionIndex found an unknown nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        if contextMarkerList.count( originalMarker ):
                            print( "{}/ {} {}:{} {!r} {}".format( j, self.BBB, C, V, originalMarker, contextMarkerList ) )
                        assert contextMarkerList.count( originalMarker ) == 0
                if marker in BOS_NESTING_MARKERS and marker!='v':
                    if debuggingThisModule:
                        print( "    makeSectionIndex: Adding {} to contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
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
            self.checkSectionIndex() # Make sure our code above worked properly
    # end of InternalBibleSectionIndex.makeSectionIndex


    def checkSectionIndex( self ):
        """
        Just run a quick internal check on the index.
        """
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            print(  "  " + _("Checking {} {} {} section index entries…").format( len(self.__indexData), self.workName, self.BBB ) )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
            print( self )

        # Check that all C,V entries (the index to the index) are digits
        for ixKey in self.__indexData:
            #print( ixKey ); halt
            C, V = ixKey
            if C!='-1' and not C.isdigit():
                logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Non-digit C entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Non-digit V entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )

        # Copy the index (dict) into a (sorted) list so that we can access entries sequentially for testing
        try: sortedIndex = sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleSectionIndex.checkSectionIndex: Unable to sort index for {} {}".format( self.workName, self.BBB ) )
            sortedIndex = self.__indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.__indexData[key]
            #entries = self.getEntries( key )
            #print( "checkSectionIndex display", j, key, indexEntry, entries )
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
                logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable index or encoding error (multiple v entries) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                assert vCount <= 1

            #print( "InternalBibleSectionIndex.checkSectionIndex line", self.BBB, key, indexEntry, entries, foundMarkers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in foundMarkers:
                        logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert 'c' in foundMarkers
                else: assert 'v' in foundMarkers
                if 'p' in foundMarkers:
                    if 'p~' not in foundMarkers and 'v' not in foundMarkers:
                        logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable (early in chapter) p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        assert 'p~' in foundMarkers or 'v' in foundMarkers
                if 'q1' in foundMarkers or 'q2' in foundMarkers:
                    if 'v' not in foundMarkers and 'p~' not in foundMarkers:
                        logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable q1/q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
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
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable v encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    elif marker == 'vp#':
                        #print( "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.workName ) )
                        if debuggingThisModule:
                            if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','vp#','c#','¬p'):
                            if lastKey and debuggingThisModule: print( "InternalBibleSectionIndex.checkSectionIndex: lastKey1", self.BBB, lastKey, self.getEntries( lastKey ) )
# NOTE: temporarily down-graded from critical …
                            logging.error( "InternalBibleSectionIndex.checkSectionIndex: Probable p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleSectionIndex.checkSectionIndex: nextKey1", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleSectionIndex.checkSectionIndex: nextNextKey1", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: print( "InternalBibleSectionIndex.checkSectionIndex: lastKey2", self.BBB, lastKey, self.getEntries( lastKey ) )
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if debuggingThisModule:
                                if nextKey: print( "  InternalBibleSectionIndex.checkSectionIndex: nextKey2", self.BBB, nextKey, self.getEntries( nextKey ) )
                                if nextNextKey: print( "  InternalBibleSectionIndex.checkSectionIndex: nextNextKey2", self.BBB, nextNextKey, self.getEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q3' and nextMarker not in ('v','p~', '¬q3'):
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '-1': # the book introduction
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
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.workName ) )
                        #else:
                            #if 's1'  in foundMarkers or 'r' in foundMarkers or 'p' in foundMarkers or 'q1' in foundMarkers:
                                #print( "xyz", key, entries )
                            #if self.workName != '1974_TB':
                                #assert 's1' not in foundMarkers and 'r' not in foundMarkers and 'p' not in foundMarkers and 'q1' not in foundMarkers

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleSectionIndex.checkSectionIndex: wrong {} {} chapter number {!r} expected {!r}".format( self.workName, self.BBB, cleanText, C ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleSectionIndex.checkSectionIndex: wrong {} {} {} verse number {!r} expected {!r}".format( self.workName, self.BBB, C, cleanText, V ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
            lastKey = key

        if debuggingThisModule: # Just print the beginning part of the index to view
            if self.BBB in ('GEN','MAT'):
                print( self )
                print( ' ', self.__indexData )
                for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                    print( " {:3} {}: {}".format( j, iKey, iEntry ) )
                    if iEntry.entryCount > 1:
                        for scj in range( iEntry.entryCount ):
                            print( "      {}".format( self.givenBibleEntries[ iEntry.entryIndex + scj ] ) ) # This is an InternalBibleEntry
                    if j > 40: break
                halt
        #if self.BBB=='FRT': halt
    # end of InternalBibleSectionIndex.checkSectionIndex
# end of class InternalBibleSectionIndex



def demo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    if BibleOrgSysGlobals.verbosityLevel > 0: print()
    ICVE = InternalBibleCVIndexEntry( 0, 1, ['abc'] )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( f"ICVE={ICVE}" )
    ISE = InternalBibleSectionIndexEntry( '1', '1', '1', '5', 0, 1, 's1', 'Section Name', ['abc'] )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( f"ISE={ISE}" )

    #IBB = InternalBibleIndexes( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #if BibleOrgSysGlobals.verbosityLevel > 0: print( IBB )

    global debuggingThisModule
    if 1: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
        import os
        from BibleOrgSys.Formats.USFMBible import USFMBible

        testData = ( # name, abbreviation, folderpath for USFM files
                ("Matigsalug", 'MBTV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( f"\nInternalBibleIndexes B{j+1}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                #debuggingThisModule = True # Just for the index creation
                if 0:
                    UB.makeSectionIndex()
                else: # old code
                    for BBB,bookObject in UB.books.items():
                        #bookObject._SectionIndex = InternalBibleSectionIndex( bookObject, UB )
                        #bookObject._SectionIndex.makeSectionIndex()
                        bookObject.makeSectionIndex()
                        #if BBB=='PSA': halt
            else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleIndexes.py
