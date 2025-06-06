#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# InternalBibleIndexes.py
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
TODO: Rewrite makeBookCVIndex to take advantage of the new v= fields.

Module for defining and manipulating Bible indexes including:

    InternalBibleBookCVIndexEntry
    InternalBibleBookCVIndex
        Everything before chapter 1 is considered chapter -1.
        The first line in chapter -1 is considered verse 0
            and each successive line has a successive verse number.
        Everything before verse 1 in regular chapters
            is considered as verse 0, e.g., many section headings, etc.

    InternalBibleBookSectionIndexEntry
    InternalBibleBookSectionIndex

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
    Books (like FRT) that don't have chapters (or verses) store the information in chapter '0'.

CHANGELOG:
    2022-06-05 Quieten makeBookCVIndex print statement
    2022-07-31 Added items() methods to indexes
    2023-02-03 Improved indexing of non-chapter books
    2023-03-02 Improved section index
    2023-04-13 Put verse ranges and suffixes back into CV index entries -- this might be a breaking change for some applications???
    2023-06-02 Allow finding all verses and verse ranges (esp. for notes, commentaries)
    2025-05-21 Combine c/ms1/s1 section headings in section heading index for Psalms
"""
from gettext import gettext as _
from pathlib import Path
import logging

if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, BOS_NESTING_MARKERS, BOS_END_MARKERS, getLeadingInt


LAST_MODIFIED_DATE = '2025-05-22' # by RJH
SHORT_PROGRAM_NAME = "BibleIndexes"
PROGRAM_NAME = "Bible indexes handler"
PROGRAM_VERSION = '0.94'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


MAX_NONCRITICAL_ERRORS_PER_BOOK = 4



class InternalBibleBookCVIndexEntry:
    """
    Holds the following information:
        1/ entryIndex: the index into the BibleEntryList
            REMOVED: indexNext: the index of the next BibleEntry
        2/ entryCount: the number of BibleEntries
        3/ context: a list containing contextual markers which still apply to this entry.
    """
    __slots__ = ('entryIndex','entryCount','context') # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, entryIndex:str, entryCount:int, context:list[str]|None=None ) -> None:
        """
        """
        #if context: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "XXXXXXXX", entryIndex, entryCount, context )
        if context is None: context:list[str] = []
        self.entryIndex, self.entryCount, self.context = entryIndex, entryCount, context
        #self.indexNext = self.entryIndex + entryCount
    # end of InternalBibleBookCVIndexEntry.__init__


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the index entry.
        """
        result = "InternalBibleBookCVIndexEntry object: ix={} cnt={} ixE={}{}" \
            .format( self.entryIndex, self.entryCount, self.entryIndex + self.entryCount,
                    " ctxt={}".format(self.context) if self.context else '' )
        return result
    # end of InternalBibleBookCVIndexEntry.__str__


    def __len__( self ) -> int:
        return 3
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            halt # not done yet
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ki2", keyIndex )
            #assert keyIndex.step is None
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "param", *keyIndex.indices(len(self)) )
            #return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        if keyIndex == 0: return self.entryIndex
        elif keyIndex == 1: return self.entryCount
        #elif keyIndex == 2: return self.indexNext
        elif keyIndex == 2: return self.context
        else: raise IndexError
    # end of InternalBibleBookCVIndexEntry.__getitem__

    def getEntryIndex( self ) -> int:
        return self.entryIndex
    def getNextEntryIndex( self ) -> int:
        return self.entryIndex + self.entryCount # exclusive
    def getEntryCount( self ) -> int:
        return self.entryCount
    def getContextList( self ) -> list[str]:
        return self.context
# end of class InternalBibleBookCVIndexEntry



class InternalBibleBookCVIndex:
    """
    Handles the C:V index for an internal Bible book.
    """
    __slots__ = ('workName','BBB','__indexData','givenBibleEntries',
                 '_indexedFlag') # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, workName, BBB ) -> None:
        """
        Creates the index object for a Bible book.

        The book code is stored to enable better error messages.
        """
        self.workName, self.BBB = workName, BBB
    # end of InternalBibleBookCVIndex.__init__


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the list of entries.
        """
        result = "InternalBibleBookCVIndex object for {}:".format( self.BBB )
        try: result += "\n  {:,} index entries".format( len( self.__indexData ) )
        except AttributeError: result += "\n  Index is empty"
        try: result += " created from {:,} data entries".format( len( self.givenBibleEntries ) )
        except AttributeError: pass # ignore it
        if BibleOrgSysGlobals.verbosityLevel > 2:
            try: result += "\n  {} average data entries per index entry".format( round( len(self.givenBibleEntries)/len(self.__indexData), 1 ) )
            except ( AttributeError, ZeroDivisionError ): pass # ignore it
        #try:
            #for j, key in enumerate( sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) ) ):
                #C, V = key
                #indexEntry = self.__indexData[key]
                #entries = self.getVerseEntries( key )
                #result += "\n{} {} {} {}".format( j, key, indexEntry, entries )
                #if j>10: break
        #except: pass # ignore it
        return result
    # end of InternalBibleBookCVIndex.__str__


    def __len__( self ) -> int:
        return len( self.__indexData )

    def __contains__( self, keyStartCVDuple:tuple[str,str] ) -> bool:
        return keyStartCVDuple in self.__indexData
    def __getitem__( self, keyStartCVDuple:tuple[str,str] ) -> InternalBibleBookCVIndexEntry:
        return self.__indexData[keyStartCVDuple]

    def __iter__( self ) -> tuple[str,str]:
        """
        Yields the next index entry CV key.
        """
        for CVKey in self.__indexData:
            yield CVKey
    # end of InternalBibleBookCVIndex.__iter__

    def items( self ) -> tuple[tuple[str,str],InternalBibleBookCVIndexEntry]:
        """
        Yields the next index entry CV key and its value
        """
        for itemTuple in self.__indexData.items():
            yield itemTuple
    # end of InternalBibleBookCVIndex.items


    def getVerseEntries( self, CVkey:tuple[str,str], strict=True ) -> InternalBibleEntryList:
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this verse.

        Raises a KeyError if the CV key doesn't exist.

        If strict is false, after failing a dictionary lookup,
            it will also loop through the index looking for bridged verses starting with that verse

        TODO: What if the searched verse number is a middle or the last verse of the bridged verses?
        """
        # print( f"getVerseEntries( {CVkey}, {strict=} )..." )
        try:
            indexEntry = self.__indexData[CVkey]
        except KeyError as k:
            if strict: raise k
            # print( "  Trying a search for bridged verses..." )
            strCVkey = str(CVkey)
            searchCVString = f'{strCVkey[:-2]}-' # Drop of the final two characters (closing bracket and closing quote), and then add hyphen
            for someCVkey in self.__indexData:
                # print( f"    Have {someCVkey} trying to find {self.BBB} {strCVkey} -> {searchCVString=}" )
                if str(someCVkey).startswith( searchCVString ): # Yes, it's there but bridged
                    indexEntry = self.__indexData[someCVkey]
                    break
            else: raise k
        result = self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()]
        assert isinstance( result, InternalBibleEntryList )
        return result
    # end of InternalBibleBookCVIndex.getVerseEntries


    def getChapterEntries( self, C:str ) -> InternalBibleEntryList:
        """
        Given C, return the InternalBibleEntryList containing the InternalBibleEntries for this chapter.

        Raises a KeyError if the C key doesn't exist.
        """
        firstIndexEntry = self.__indexData[(C,'0')]
        try:
            nextIndexEntry = self.__indexData[(str(int(C)+1),'0')]
            return self.givenBibleEntries[firstIndexEntry.getEntryIndex():nextIndexEntry.getEntryIndex()]
        except KeyError: # presumably no more chapters
            return self.givenBibleEntries[firstIndexEntry.getEntryIndex():]
    # end of InternalBibleBookCVIndex.getChapterEntries


    def getVerseEntriesWithContext( self, CVkey:tuple[str,str], strict:bool|None=False, complete:bool|None=False ) -> tuple[InternalBibleEntryList,list[str]]:
        """
        Given C:V, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this verse,
            along with the context for this verse.

        Raises a KeyError if the CV key doesn't exist.

        However, even if C:V can't be found, there might be a prior verse range (C:v1-v2) that we could/should? return.

        If the strict flag is not set, we try to remove any letter suffix
            and/or to search verse ranges for a match.

        If complete flag is set, try to find every reference with that verse.
        """
        # print( f"{self.__indexData.keys()}" )
        desiredCint = int( CVkey[0] )
        desiredVint = getLeadingInt( CVkey[1] )
        indexEntries = []

        if complete: # First look for all verse ranges that would match (they probably precede any specific verse entries)
            for ixCVkey in self.__indexData.keys():
                ixC, ixV = ixCVkey
                if ixC==CVkey[0]:
                    if '-' in ixV: # must include a verse range
                        # See if our desired verse is within the range
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextA {self.workName} {self.BBB} searching for {CVkey}: have {ixC}:{ixV}")
                        V1,V2 = ixV.split( '-' )
                        if getLeadingInt(V1) <= desiredVint <= getLeadingInt(V2):
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextA {self.workName} {self.BBB} found {CVkey} in range {ixC}:{ixV}" )
                            # We found a range that includes the verse we're looking for
                            indexEntries.append( self.__indexData[ixCVkey] )
                    elif ',' in ixV:
                        for ixVx in ixV.split( ',' ):
                            if desiredVint == int(ixVx):
                                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextA {self.workName} {self.BBB} found {CVkey} in list {ixC}:{ixV}" )
                                # We found a list of verses that includes the verse we're looking for
                                indexEntries.append( self.__indexData[ixCVkey] )
                    elif not ixV.isdigit(): # not a verse range, so might be something like '50a'
                        try:
                            if desiredVint == getLeadingInt(ixV):
                                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextA {self.workName} {self.BBB} found {CVkey} in partial {ixC}:{ixV}" )
                                # We found a partial verse that includes the verse we're looking for
                                indexEntries.append( self.__indexData[ixCVkey] )
                                # NOTE: There still might be a second half, e.g., '50a' and '50b'
                        except ValueError: # no int there but which one
                            # It likely means a verse number error which we should have repaired at load time, e.g. '\\v 7Afterwards, …' or maybe '\\v Afterwards. …'
                            logging.critical( f"getVerseEntriesWithContextA {self.workName} {self.BBB} couldn't find a verse number integer in either {CVkey=} or in {ixC}:{ixV} from index entry" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: bad_verse_number_in_CV_index
                    # else:
                    #     dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContext {self.workName} {self.BBB} was confused trying to find {CVkey=} at {ixC}:{ixV}" )
                    #     halt

        # Now look for specific verses that match
        try:
            indexEntries.append( self.__indexData[CVkey] )
        except KeyError:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextB {self.workName} was unable to immediately find {self.BBB} {CVkey=}")
            if strict or CVkey[0]=='-1': # strict selection or else in the introduction (no verse ranges there)
                raise KeyError
            # else: # Look for a verse range that contains our verse
            # print( f"{self.__indexData.keys()=}" )
            if not CVkey[1].isdigit():
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextB {self.workName} {self.BBB} searching for non-digit {CVkey}" )
                try:
                    indexEntries.append( self.__indexData[ (CVkey[0],str(desiredVint)) ] )
                except KeyError: # no, that didn't work either
                    pass

            if not indexEntries and not complete: # look for a verse range that would match
                for ixCVkey in self.__indexData.keys():
                    ixC, ixV = ixCVkey
                    if ixC==CVkey[0]:
                        if '-' in ixV: # must include a verse range
                            # See if our desired verse is within the range
                            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextC {self.workName} {self.BBB} searching for {CVkey}: have {ixC}:{ixV}")
                            V1,V2 = ixV.split( '-' )
                            if getLeadingInt(V1) <= desiredVint <= getLeadingInt(V2):
                                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextC {self.workName} {self.BBB} found {CVkey} in range {ixC}:{ixV}" )
                                indexEntries.append( self.__indexData[ixCVkey] )
                                break # we found a range that includes the verse we're looking for
                        elif ',' in ixV:
                            for ixVx in ixV.split( ',' ):
                                if desiredVint == int(ixVx):
                                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextC {self.workName} {self.BBB} found {CVkey} in list {ixC}:{ixV}" )
                                    indexEntries.append( self.__indexData[ixCVkey] )
                                    break # we found a list of verses that includes the verse we're looking for
                        elif not ixV.isdigit(): # not a verse range, so might be something like '50a'
                            try:
                                if desiredVint == getLeadingInt(ixV):
                                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContextC {self.workName} {self.BBB} found {CVkey} in partial {ixC}:{ixV}" )
                                    indexEntries.append( self.__indexData[ixCVkey] )
                                    break # we found a partial verse that includes the verse we're looking for
                                    # NOTE: There still might be a second half, e.g., '50a' and '50b'
                            except ValueError: # no int there but which one
                                # It likely means a verse number error which we should have repaired at load time, e.g. '\\v 7Afterwards, …' or maybe '\\v Afterwards. …'
                                logging.critical( f"getVerseEntriesWithContextC {self.workName} {self.BBB} couldn't find a verse number integer in either {CVkey=} or in {ixC}:{ixV} from index entry" )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: bad_verse_number_in_CV_index
                        # else:
                        #     dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"getVerseEntriesWithContext {self.workName} {self.BBB} was confused trying to find {CVkey=} at {ixC}:{ixV}" )
                        #     halt
                # else: # No, we just couldn't find it anywhere
                #     raise KeyError
                
        if not indexEntries: # we just couldn't find it anywhere
            raise KeyError
        
        # if len(indexEntries) > 1:
        #     print( f"InternalBibleBookCVIndex.getVerseEntriesWithContext {self.workName} {self.BBB} got {len(indexEntries)} results for {CVkey} {strict=} {complete=}")
        #     print( f"{indexEntries}" )
        verseEntryList = InternalBibleEntryList()
        for ii,indexEntry in enumerate( indexEntries ):       
            # print( f"{ii}: {indexEntry}" )
            verseEntryList += InternalBibleEntryList( self.givenBibleEntries[indexEntry.getEntryIndex():indexEntry.getNextEntryIndex()] )

        # Just clean up if we have a single meaningless entry
        # Hmmh, doesn't work well -- we don't want to return an empty list
        #   but if we raise a KeyError, it might be interpreted as reaching the end of the introduction (when it's not)
        # if len(verseEntryList) == 1:
        #     verseEntry = verseEntryList[0]
        #     if not verseEntry.getFullText() \
        #     and verseEntry.getMarker() in ('chapters','headers','¬headers','intro'):
        #         raise KeyError # Don't return just useless stuff
        #         # TODO: Check back why the useless stuff is getting this far -- probably should be prevented earlier (in the indexing function)
        #     else:
        #         # print( f"{CVkey=} {strict=} {verseEntry=}" )
        #         if verseEntry.getMarker() not in ('id','usfm','ide','rem','h','toc1','toc2','toc3','mt1','mt2','mt3','c'): halt

        assert verseEntryList # We don't want to return an empty list
        assert isinstance( verseEntryList, InternalBibleEntryList ), f"{type(verseEntryList)=} {verseEntryList=}"
        return verseEntryList, indexEntries[0].getContextList()
    # end of InternalBibleBookCVIndex.getVerseEntriesWithContext


    def getChapterEntriesWithContext( self, C:str ) -> tuple[InternalBibleEntryList,list[str]]:
        """
        Given C, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this chapter,
            along with the context for this chapter.

        Raises a KeyError if the C key doesn't exist.
        """
        assert isinstance( C, str )
        try: firstIndexEntry = self.__indexData[(C,'0')]
        except KeyError as err:
            (logging.warning if C=='0' else logging.error)( f"getChapterEntriesWithContext {self.workName} couldn't get {self.BBB} ({C},0){f' from {self.__indexData.keys()}' if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag else ''}")
            raise err
        try:
            nextIndexEntry = self.__indexData[(str(int(C)+1),'0')]
            return InternalBibleEntryList( self.givenBibleEntries[firstIndexEntry.getEntryIndex():nextIndexEntry.getEntryIndex()] ), firstIndexEntry.getContextList()
        except KeyError: # Couldn't find the next chapter
            if C != '-1': # presumably no more chapters
                return InternalBibleEntryList( self.givenBibleEntries[firstIndexEntry.getEntryIndex():] ), firstIndexEntry.getContextList()
            # else it's a bit more complicated finding the introduction because mostly there's no chapter zero
            try:
                nextIndexEntry = self.__indexData[('1','0')]
                return InternalBibleEntryList( self.givenBibleEntries[firstIndexEntry.getEntryIndex():nextIndexEntry.getEntryIndex()] ), firstIndexEntry.getContextList()
            except KeyError: # give up and just return everything
                return InternalBibleEntryList( self.givenBibleEntries[firstIndexEntry.getEntryIndex():] ), firstIndexEntry.getContextList()
    # end of InternalBibleBookCVIndex.getChapterEntriesWithContext


    def makeBookCVIndex( self, givenBibleEntries ) -> None:
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
        from BibleOrgSys.Internals.InternalBibleBook import OUR_HEADING_BLOCK_MARKERS

        fnPrint( DEBUGGING_THIS_MODULE, "\nInternalBibleBookCVIndex.makeBookCVIndex( {} )".format( givenBibleEntries ) )
        assert givenBibleEntries, f"{self.workName} {self.BBB} {givenBibleEntries=}"
        self.givenBibleEntries = givenBibleEntries # Keep a pointer to the original Bible entries
        self.__indexData:dict[tuple[str,str],InternalBibleBookCVIndexEntry] = {}
        errorData:list[str] = []


        # def _printIndexEntry( ie ):
        #     result = str( ie )
        #     for j in range( ie.getEntryIndex(), ie.getNextEntryIndex() ):
        #         result += "\n  {}".format( givenBibleEntries[j] )
        #     return result
        # # end of _printIndexEntry


        def _saveAnyOutstandingCV():
            """
            Save the outstanding index entry, if any
                into self.__indexData (a dict).
            """
            nonlocal saveCV, saveJ, indexEntryLineCount, errorData
            if saveCV and saveJ is not None:
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    _saveAnyOutstandingCV", self.BBB, saveCV, saveJ, indexEntryLineCount )
                #if saveCV == ('0','0'): halt
                #assert 1 <= indexEntryLineCount <= 120 # Could potentially be even higher for bridged verses (e.g., 1Chr 11:26-47, Ezra 2:3-20) and where words are stored individually
                if saveCV in self.__indexData: # we already have an index entry for this C:V
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "makeBookCVIndex._saveAnyOutstandingCV: already have an index entry @ {} {}:{}".format( self.BBB, strC, strV ) )
                    errorData.append( ( self.BBB,strC,strV,) )
                    if BibleOrgSysGlobals.debugFlag and (DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.verbosityLevel > 2):
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, '      _saveAnyOutstandingCV @ ', self.BBB, saveCV )
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
                        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                            C, V = saveCV
                            if C != '0' and V != '0': # intros aren't so important
                                halt # This is a serious error that is losing Biblical text
                    # Let's combine the entries
                    ix, lc = self.__indexData[saveCV]
                    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "      About to save UPDATED index entry for {} {}:{}".format( self.BBB, saveCV[0], saveCV[1] ) )
                    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "        ix={} count={}".format( ix, lc+indexEntryLineCount ) )
                    self.__indexData[saveCV] = ( ix, lc+indexEntryLineCount )
                    if BibleOrgSysGlobals.debugFlag and (DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.verbosityLevel > 2):
                        logging.error( "  mI:sAO combined {}".format( (ix,lc+indexEntryLineCount) ) )
                        for ixx in range( ix, ix+lc+indexEntryLineCount ):
                            logging.error( "   mI:sAO {}".format( self.givenBibleEntries[ixx] ) )
                else: # no pre-existing duplicate
                    if DEBUGGING_THIS_MODULE:
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "      About to save NEW index entry for {} {}:{}".format( self.BBB, saveCV[0], saveCV[1] ) )
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "        ix={} count={}".format( saveJ, indexEntryLineCount ) )
                        for pqr in range( saveJ, saveJ+indexEntryLineCount ):
                            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "       {}".format( self.givenBibleEntries[pqr] ) )
                    self.__indexData[saveCV] = (saveJ, indexEntryLineCount)
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'sAO', _printIndexEntry( self.__indexData[saveCV] ) )
                saveCV = saveJ = None
                indexEntryLineCount = 0
        # end of _saveAnyOutstandingCV


        # Main code of InternalBibleBookCVIndex.makeBookCVIndex
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    " + _("Indexing {:,} {} {} entries…").format( len(self.givenBibleEntries), self.workName, self.BBB ) )

        # Firstly create the CV index keys with pointers to the actual lines
        if not BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( self.BBB ):
            # It's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            saveCV = saveJ = None
            indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            strC, strV = '-1', '0'
            for j, entry in enumerate( self.givenBibleEntries ):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookCVIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                marker = entry.getMarker()
                if marker in ('c','v'):
                    logging.critical( f"makeBookCVIndex unexpected 'c' or 'v' in non-chapter book: {self.BBB} {strC}:{strV} {marker}='{entry.getOriginalText()}'" )
                if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()
                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    _saveAnyOutstandingCV()
                    # Save anything before the first verse number as verse 'zero'
                    strC, strV = entry.getCleanText(), '0'
                    assert strC != '0'
                    #saveCV, saveJ = (strC,strV,), j
                    indexEntryLineCount += 1
                elif marker == 'v':
                    assert strC != '0' # Should be in a chapter by now
                    logging.warning( "makeBookCVIndex: Why do we have a verse number in a {} {} book without chapters?".format( self.workName, self.BBB ) )
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookCVIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =",
                        marker, entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                    _saveAnyOutstandingCV() # with the adjusted indexEntryLineCount
                    #if 0:
                        ## Remove verse ranges, etc. and then save the verse number
                        #strV = entry.getCleanText()
                        #digitV = ''
                        #for char in strV:
                            #if char.isdigit(): digitV += char
                            #else: # the first non-digit in the verse "number"
                                #dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                                #break # ignore the rest
                        ##assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                        #saveCV, saveJ = (strC,digitV,), revertToJ
                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new "verse" entry in chapter '-1'
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1)
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "makeBookCVIndexIntro", _printIndexEntry( self.__indexData[(strC,strV)] ) )
                    Vi = int( strV )
                    assert Vi == j
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert indexEntryLineCount == 0
                else: # All the other lines don't cause a new index entry to be made
                    indexEntryLineCount += 1
            _saveAnyOutstandingCV()

        else: # Assume it's a normal C/V book
            saveCV = saveJ = None
            indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            strC, strV = '-1', '0'
            for j, entry in enumerate( self.givenBibleEntries ):
                if DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookCVIndex1", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                marker = entry.getMarker()
                if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    # All text should have been moved into the following p~ marker
                    assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()

                if marker == 'c': # A new chapter always means that it's a clean new index entry
                    vPrint( 'Never', DEBUGGING_THIS_MODULE, "    Handle c {}".format( entry.getCleanText() ) )
                    _saveAnyOutstandingCV()
                    # Save anything before the first verse number as verse '0'
                    strC, strV = entry.getCleanText(), '0'
                    assert strC != '-1'
                    saveCV, saveJ = (strC,strV,), j
                    indexEntryLineCount += 1

                elif marker == 'v': # This bit of indexing code is quite complex!
                    vPrint( 'Never', DEBUGGING_THIS_MODULE, "    Handle v {}".format( entry.getCleanText() ) )
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
                            if revertToJ==0: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookCVIndex.makeBookCVIndex: Get out of here" ); break
                            aPreviousMarker,thisCleanText = self.givenBibleEntries[revertToJ-1].getMarker(), self.givenBibleEntries[revertToJ-1].getCleanText()
                    _saveAnyOutstandingCV() # with the adjusted indexEntryLineCount
                    # Remove verse ranges, etc. and then save the verse number
                    strV = entry.getCleanText()
                    assert '–' not in strV, f"en-dash in {self.BBB} {strC}:{strV}" # that's an en-dash -- it MUST be a hyphen here for a verse range
                    # # TODO: We don't need this next little section now
                    # digitV = ''
                    # for char in strV:
                    #     if char.isdigit(): digitV += char
                    #     else: # the first non-digit in the verse "number"
                    #         logging.warning( f"InternalBibleBookCVIndex.makeBookCVIndex() ignored non-digits in verse for index: {self.BBB} {strC}:{strV}" )
                    #         break # ignore the rest
                    # #assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                    # NEXT LINE CHANGED 2023-04-13
                    # saveCV, saveJ = (strC,digitV,), revertToJ
                    saveCV, saveJ = (strC,strV,), revertToJ
                    indexEntryLineCount += (j-revertToJ) + 1 # For the v
                    #if 0 and BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        ## Double-check that each entry contains only ONE v field
                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookCVIndex check at {} {}".format( j, entry ) )
                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                        #vCount = 0
                        #for scj in range( indexEntryLineCount ):
                            #thisEntry = self.givenBibleEntries[ j + scj ] # This is an InternalBibleEntry
                            ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "      {}".format( thisEntry ) )
                            #if thisEntry.getMarker() == 'v': vCount += 1
                        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    vCount={}".format( vCount ) )
                        #if vCount > 1: # Should never happen -- verses should all have their own separate index entries
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookCVIndex check for {} {} {}:{} at ({}) {}".format( self.workName, self.BBB, strC, strV, j, entry ) )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    indexEntryLineCount is {} thus including:".format( indexEntryLineCount ) )
                            #for scj in range( indexEntryLineCount ):
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "      {}".format( self.givenBibleEntries[ j + scj ] ) ) # This is an InternalBibleEntry
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    vCount={}".format( vCount ) )
                            ##halt
                        ## Actually this seems to be fixed up down below somewhere (so doesn't seem to matter)
                    if 0 and DEBUGGING_THIS_MODULE:
                        #if strV == '4':
                            #halt
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Temp index currently ({}) {}".format( len(self.__indexData), self.__indexData ) )

                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new 'verse' entry in chapter '-1'
                    #   (usually the id line is 'verse' 0, i.e., -1:0)
                    vPrint( 'Never', DEBUGGING_THIS_MODULE, "    Handle intro {}".format( entry.getCleanText() ) )
                    assert saveCV is None and saveJ is None
                    self.__indexData[(strC,strV)] = ( j, 1 )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "makeBookCVIndex", _printIndexEntry( self.__indexData[(strC,strV)] ) )
                    Vi = int( strV )
                    assert Vi == j
                    strV = str( Vi + 1 ) # Increment the verse number
                    lastJ = j
                    assert indexEntryLineCount == 0

                else: # All the other lines don't cause a new index entry to be made
                    indexEntryLineCount += 1
            _saveAnyOutstandingCV()

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
            (logging.warning if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag else logging.info)( f"makeBookCVIndex._saveAnyOutstandingCV: Needed to combine multiple index entries for {errorDataString}" )

        # Now calculate the contextMarkerList for each CV entry and create the proper (full) InternalBibleBookCVIndexEntries
        contextMarkerList = []
        for (C,V), (indexStart,count) in self.__indexData.items():
            dPrint( 'Never', DEBUGGING_THIS_MODULE, "makeBookCVIndex for {} {} {}:{} {} {} {}".format( self.workName, self.BBB, C, V, indexStart, count, contextMarkerList ) )
            # Replace the existing (temporary) index entry to include a copy of the previous contextMarkerList
            #   e.g., a typical verse might be inside a paragraph in a section
            #            thus getting the contextMarkerList: ['chapters','c','s1','p'] or ['chapters','ms1','c','v','q1']
            self.__indexData[(C,V)] = InternalBibleBookCVIndexEntry( indexStart, count, contextMarkerList.copy() )
            for j in range( indexStart, indexStart+count ):
                entry = self.givenBibleEntries[j]
                marker = entry.getMarker()
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"  makeBookCVIndex {self.workName} {self.BBB} {C}:{V} {j=} {marker=} {entry.getCleanText()}" )
                if marker[0]=='¬' and marker != '¬v': # We're closing a paragraph or heading block (ms1) marker
                    originalMarker = marker[1:]
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                        # Should be exactly one of these markers (open) in the contextMarkerList
                        # XXXXXXXXX Gets messed up by GNT Mrk 16:9 has two \s headings in a row !!!!!!!!!!!!!!!!!!!
                        if contextMarkerList.count(originalMarker)!=1:
                            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    makeBookCVIndex originalMarker: {!r} contextMarkerList={}".format( originalMarker, contextMarkerList ) )
                            logging.critical( "makeBookCVIndex found a nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                            assert contextMarkerList.count( originalMarker ) == 1
                    try: # Remove first open occurrence of the marker just closed (e.g., s1 can occur after c and still be open)
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    makeBookCVIndex: Removing {marker=} {originalMarker=} from {contextMarkerList=} at {self.BBB}_{C}:{V}" )
                        contextMarkerList.remove( originalMarker )
                    except ValueError: # oops something went wrong
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookCVIndex: marker = {}'.format( marker ) )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookCVIndex: entry = {}'.format( entry ) )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookCVIndex: contextMarkerList = {}'.format( contextMarkerList ) )
                        logging.critical( "makeBookCVIndex found an unknown nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                    if contextMarkerList.count( originalMarker ) > 0:
                        # TODO: Is this a code error or a data error???
                        logging.warning( f"makeBookCVIndex( {self.workName} {self.BBB} ) why does {contextMarkerList} for {C}:{V} have '{originalMarker}' in it?")
                    # TODO: Not sure what is happening here -- needs further detailed debugging
                    if 0 and DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag and BibleOrgSysGlobals.debugFlag:
                        if contextMarkerList.count( originalMarker ):
                            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{}/ {} {}:{} {!r} {}".format( j, self.BBB, C, V, originalMarker, contextMarkerList ) )
                        assert contextMarkerList.count( originalMarker ) == 0, f"{self.BBB} {C}:{V} {j=} {originalMarker} {contextMarkerList} cnt={contextMarkerList.count( originalMarker )}"
                if (marker in BOS_NESTING_MARKERS or marker in OUR_HEADING_BLOCK_MARKERS) \
                and marker!='v':
                    if DEBUGGING_THIS_MODULE:
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    makeBookCVIndex: Adding {} to contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
                    contextMarkerList.append( marker )
        if contextMarkerList:
            logging.critical( f"makeBookCVIndex: Why did we have contextMarkers {contextMarkerList} left over in {self.workName} {self.BBB}???" )
            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag and BibleOrgSysGlobals.debugFlag:
                assert not contextMarkerList # Should be empty at end if nesting for the book is correct

        assert self.__indexData, f"{self.workName} {self.BBB} {givenBibleEntries=} {self.__indexData=}"
        self._indexedFlag = True
        #if 0:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', self.__indexData )
            #for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " {:3} {}: {}".format( j, iKey, iEntry ) )
            #halt

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
            self.checkBookCVIndex() # Make sure our code above worked properly
    # end of InternalBibleBookCVIndex.makeBookCVIndex


    def checkBookCVIndex( self ) -> None:
        """
        Just run a quick internal check on the index.
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + _("Checking {:,} {} {} CV index entries…").format( len(self.__indexData), self.workName, self.BBB ) )
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, self )

        # Check that all C,V entries (the index to the index) are digits
        for ixKey in self.__indexData:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ixKey ); halt
            C, V = ixKey
            if C!='-1' and not C.isdigit():
                logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Non-digit C entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Non-digit V entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )

        # Copy the index (dict) into a (sorted) list so that we can access entries sequentially for testing
        try: sortedIndex = sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleBookCVIndex.checkBookCVIndex: Unable to sort index for {} {}".format( self.workName, self.BBB ) )
            sortedIndex = self.__indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.__indexData[key]
            #entries = self.getVerseEntries( key )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "checkBookCVIndex display", j, key, indexEntry, entries )
            #if self.BBB!='FRT' and j>30: break

        # Now go through the index entries (in order) and do the actual checks
        lastKey = nextKey = nextNextKey = None
        for k, key in enumerate( sortedIndex ):
            # Try getting the next couple of keys also (if they exist)
            try: nextKey = sortedIndex[k+1]
            except IndexError: nextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "nextKeyError1", k, len(sortedIndex), repr(key) ); nextKey = None
            try: nextNextKey = sortedIndex[k+2]
            except IndexError: nextNextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "nextKeyError2", k, len(sortedIndex), repr(key) ); nextKey = None
            C, V = key

            indexEntry = self.__indexData[key]
            entries = self.getVerseEntries( key ) # Gets the list of index entries for this one CV index
            foundMarkers = []
            anyText = anyExtras = False
            vCount = 0
            for entry in entries:
                marker = entry.getMarker()
                foundMarkers.append( marker )
                if marker[0]=='¬': assert marker in BOS_END_MARKERS, f"InternalBibleBookCVIndex.checkBookCVIndex: '{marker}' not in ({len(BOS_END_MARKERS)}) {BOS_END_MARKERS}"
                if marker == 'v': vCount += 1
                if marker not in ('c','v'): # These always have to have text
                    if entry.getCleanText(): anyText = True
                    if entry.getExtras(): anyExtras = True
            if vCount > 1:
                logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable index or encoding error (multiple v entries) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                assert vCount <= 1

            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookCVIndex.checkBookCVIndex line", self.BBB, key, indexEntry, entries, foundMarkers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in foundMarkers:
                        logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert 'c' in foundMarkers
                else: assert 'v' in foundMarkers
                if 'p' in foundMarkers:
                    if 'p~' not in foundMarkers and 'v' not in foundMarkers:
                        logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable (early in chapter) p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        assert 'p~' in foundMarkers or 'v' in foundMarkers
                if 'q1' in foundMarkers or 'q2' in foundMarkers:
                    if 'v' not in foundMarkers and 'p~' not in foundMarkers:
                        logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable q1/q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        assert 'v' in foundMarkers or 'p~' in foundMarkers

                previousMarker = nextMarker = None # But these skip over rem (remark markers)
                for j, marker in enumerate( foundMarkers ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'CheckIndex2 {} {}:{} {}/ m={!r} pM={!r} nM={!r}'.format( self.BBB, C, V, j, marker, previousMarker, nextMarker ) )

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
                    elif marker == 'c#':
                        if nextMarker not in ( 'v', 'vp#', ):
                            logging.critical( f"InternalBibleBookCVIndex.checkBookCVIndex: Probable encoding error with unexpected '{nextMarker}' following '{marker}' in {self.workName} {self.BBB} {C}:{V} {entries}" )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                    elif marker == 'v':
                        if foundMarkers[-1] != 'v' and nextMarker not in ('v~','¬v',): # end marker if verse is blank
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable v encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                    elif marker == 'vp#':
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.workName ) )
                        if DEBUGGING_THIS_MODULE:
                            if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','vp#','c#','¬p'):
                            if lastKey and DEBUGGING_THIS_MODULE: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookCVIndex.checkBookCVIndex: lastKey1", self.BBB, lastKey, self.getVerseEntries( lastKey ) )
# NOTE: temporarily down-graded from critical …
                            logging.error( "InternalBibleBookCVIndex.checkBookCVIndex: Probable p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if DEBUGGING_THIS_MODULE:
                                if nextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookCVIndex.checkBookCVIndex: nextKey1", self.BBB, nextKey, self.getVerseEntries( nextKey ) )
                                if nextNextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookCVIndex.checkBookCVIndex: nextNextKey1", self.BBB, nextNextKey, self.getVerseEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookCVIndex.checkBookCVIndex: lastKey2", self.BBB, lastKey, self.getVerseEntries( lastKey ) )
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if DEBUGGING_THIS_MODULE:
                                if nextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookCVIndex.checkBookCVIndex: nextKey2", self.BBB, nextKey, self.getVerseEntries( nextKey ) )
                                if nextNextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookCVIndex.checkBookCVIndex: nextNextKey2", self.BBB, nextNextKey, self.getVerseEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q3' and nextMarker not in ('v','p~', '¬q3'):
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if  V=='0': # chapter introduction
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.BBB, C, V, foundMarkers, entries )
                    #newKey = (C, '1')
                    #try:
                        #iE = self.__indexData[newKey]
                        #iD, ct = self.getVerseEntries( newKey )
                    #except KeyError: pass
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " ", newKey, iD, ct )
                    if self.BBB=='ACT' and C=='8':
                        if 'p' in foundMarkers:
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.workName ) )
                        #else:
                            #if 's1'  in foundMarkers or 'r' in foundMarkers or 'p' in foundMarkers or 'q1' in foundMarkers:
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "xyz", key, entries )
                            #if self.workName != '1974_TB':
                                #assert 's1' not in foundMarkers and 'r' not in foundMarkers and 'p' not in foundMarkers and 'q1' not in foundMarkers

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: wrong {} {} chapter number {!r} expected {!r}".format( self.workName, self.BBB, cleanText, C ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleBookCVIndex.checkBookCVIndex: wrong {} {} {} verse number {!r} expected {!r}".format( self.workName, self.BBB, C, cleanText, V ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
            lastKey = key

        if 0 and DEBUGGING_THIS_MODULE: # Just print the beginning part of the index to view
            if self.BBB in ('GEN','MAT'):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, self )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', self.__indexData )
                for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " {:3} {}: {}".format( j, iKey, iEntry ) )
                    if iEntry.entryCount > 1:
                        for scj in range( iEntry.entryCount ):
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "      {}".format( self.givenBibleEntries[ iEntry.entryIndex + scj ] ) ) # This is an InternalBibleEntry
                    if j > 40: break
                halt
        #if self.BBB=='FRT': halt
    # end of InternalBibleBookCVIndex.checkBookCVIndex
# end of class InternalBibleBookCVIndex



class InternalBibleBookSectionIndexEntry:
    """
    Holds the following information:
        1/ endCV:
        2/ entryIndex: the index into the BibleEntryList
        3/ entryCount: the number of BibleEntries
        4/ contextList: a list containing contextual markers which still apply to this entry.
    """
    __slots__ = ('endC', 'endV',
                 'startIx', 'endIx', 'reasonMarker', 'sectionName',
                 'contextList') # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, endC:str, endV:str, startIx:int, endIx:int,
                            reasonMarker:str, sectionName:str, contextList:list[str]|None=None ) -> None:
                 #startCV:str, endCV:str, entryIndex:int, entryCount:int, context:list[str]|None=None ) -> None:
        """
        """
        #if context: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "XXXXXXXX", entryIndex, entryCount, context )
        if contextList is None: contextList:list[str] = []
        self.endC, self.endV = endC, endV
        self.startIx, self.endIx, self.reasonMarker, self.sectionName = startIx, endIx, reasonMarker, sectionName
        self.contextList = contextList
    # end of InternalBibleBookSectionIndexEntry.__init__


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the index entry.
        """
        result = f"InternalBibleBookSectionIndexEntry object: (inclusive) endCV={self.endC}:{self.endV}" \
                 f" ix={self.startIx}–{self.endIx} (cnt={self.endIx + 1 - self.startIx})" \
                 f" {self.reasonMarker}='{self.sectionName}'" \
                 f"{' ctxt={}'.format(self.contextList) if self.contextList else ''}"
        return result
    # end of InternalBibleBookSectionIndexEntry.__str__


    def __len__( self ):
        return len(__slots__)
    def __getitem__( self, keyIndex ):
        if isinstance( keyIndex, slice ): # Get the start, stop, and step from the slice
            cannot_handle_slice_yet # not done yet
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "ki2", keyIndex )
            #assert keyIndex.step is None
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "param", *keyIndex.indices(len(self)) )
            #return InternalBibleEntryList( [self.data[ii] for ii in range(*keyIndex.indices(len(self)))] )
        # Otherwise assume keyIndex is an int
        elif keyIndex == 0: return self.endC
        elif keyIndex == 1: return self.endV
        elif keyIndex == 2: return self.startIx
        elif keyIndex == 3: return self.endIx
        elif keyIndex == 4: return self.reasonMarker
        elif keyIndex == 5: return self.sectionName
        elif keyIndex == 6: return self.contextList
        else: raise IndexError
    # end of InternalBibleBookSectionIndexEntry.__getitem__

    def getEndCV( self ) -> tuple[str,str]:
        return self.endC,self.endV
    def getStartIndex( self ) -> int:
        return self.startIx
    def getEndIndex( self ) -> int:
        return self.endIx # inclusive
    # def getStartNextIndexes( self ) -> tuple[int,int]:
    #     return self.startIx,self.endIx
    def getEntryCount( self ) -> int:
        return self.endIx + 1 - self.startIx
    def getContextList( self ) -> list[str]|None:
        return self.contextList
    def getSectionNameReason( self ) -> tuple[str,str]:
        return self.sectionName,self.reasonMarker
# end of class InternalBibleBookSectionIndexEntry



class InternalBibleBookSectionIndex:
    """
    Handles the section index for an internal Bible book.

    Index keys are startC,startV string 2-tuples
    Index entries are 7-tuples of   endC, endV, (strings, inclusive)
                                    startIx, endIx, (int indexes to processedLines)
                                    reasonMarker, sectionName, (strings)
                                    context (list).
    """
    __slots__ = ('BBB', 'bookObject', 'BibleObject', 'workName',
                 '__indexData', '_givenBibleEntries'
                 ) # Define allowed self variables (more efficient than a dict when have many instances)


    def __init__( self, bookObject, BibleObject ) -> None:
        """
        Creates the index object for a Bible book.

        The book code is stored to enable better error messages.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBookSectionIndex.__init__( {bookObject}, {BibleObject} )" )
        self.BBB = bookObject.BBB
        self.bookObject, self.BibleObject = bookObject, BibleObject # Can be deleted once index is created
        self.workName = bookObject.workName
    # end of InternalBibleBookSectionIndex.__init__


    def __repr__( self ) -> str:
        return self.__str__()
    def __str__( self ) -> str:
        """
        Just display a simplified view of the list of entries.
        """
        result = f"InternalBibleBookSectionIndex object for {self.BBB}:"
        try: result = f"{result}\n  {len( self.__indexData )} index entries"
        except AttributeError: result = f"{result}\n  Index is empty"
        try: result = f"{result} created from {len( self._givenBibleEntries )} data entries"
        except AttributeError: pass # just ignore it
        if BibleOrgSysGlobals.verbosityLevel > 2:
            try: result = f"{result}\n  {round( len(self._givenBibleEntries)/len(self.__indexData), 1 )} average data entries per index entry"
            except ( AttributeError, ZeroDivisionError ): pass # just ignore it
        #try:
            #for j, key in enumerate( sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) ) ):
                #C, V = key
                #indexEntry = self.__indexData[key]
                #entries = self.getVerseEntries( key )
                #result += "\n{} {} {} {}".format( j, key, indexEntry, entries )
                #if j>10: break
        #except: pass # ignore it
        return result
    # end of InternalBibleBookSectionIndex.__str__


    def __len__( self ) -> int:
        return len( self.__indexData )

    def __contains__( self, keyStartCVDuple:tuple[str,str] ) -> bool:
        return keyStartCVDuple in self.__indexData
    def __getitem__( self, keyStartCVDuple:tuple[str,str] ) -> InternalBibleBookSectionIndexEntry:
        return self.__indexData[keyStartCVDuple]

    def __iter__( self ) -> tuple[str,str]:
        """
        Yields the next index entry CV key.
        """
        for startCVDuple in self.__indexData:
            yield startCVDuple
    # end of InternalBibleBookSectionIndex.__iter__

    def items( self ) -> tuple[tuple[str,str],InternalBibleBookSectionIndexEntry]:
        """
        Yields the next index entry CV key and its value
        """
        for keyEntryDuple in self.__indexData.items():
            yield keyEntryDuple
    # end of InternalBibleBookSectionIndex.items


    def getSectionEntries( self, keyStartCVDuple:tuple[str,str] ) -> InternalBibleEntryList:
        """
        Given C:V, return the InternalBibleEntryList containing the InternalBibleEntries for this section.

        Raises a KeyError if the startCV key doesn't exist.
        """
        indexEntry = self.__indexData[keyStartCVDuple]
        return self._givenBibleEntries[indexEntry.getStartIndex():indexEntry.getEndIndex()+1]
    # end of InternalBibleBookSectionIndex.getVerseEntries


    def getSectionEntriesWithContext( self, keyStartCVDuple:tuple[str,str] ) -> tuple[InternalBibleEntryList,list[str]]:
        """
        Given C:V, return a 2-tuple containing
            the InternalBibleEntryList containing the InternalBibleEntries for this section,
            along with the context for this verse.

        Raises a KeyError if the startCV key doesn't exist.
        """
        indexEntry = self.__indexData[keyStartCVDuple]
        # print( f"start={keyStartCVDuple[0]}:{keyStartCVDuple[1]} {indexEntry.getStartIndex()} end={indexEntry.getEndCV()[0]}:{indexEntry.getEndCV()[1]} {indexEntry.getEndIndex}")
        # print( f" start={self._givenBibleEntries[indexEntry.getStartIndex()]}")
        # print( f" start+1={self._givenBibleEntries[indexEntry.getStartIndex()+1]}")
        # print( f" end-1={self._givenBibleEntries[indexEntry.getEndIndex()-1]}")
        # print( f" end={self._givenBibleEntries[indexEntry.getEndIndex()]}")
        # print( f" end+1={self._givenBibleEntries[indexEntry.getEndIndex()+1]}")
        # print( f"{self._givenBibleEntries[indexEntry.getStartIndex():indexEntry.getEndIndex()]}")
        verseEntryList,contextList = self._givenBibleEntries[indexEntry.getStartIndex():indexEntry.getEndIndex()+1], indexEntry.getContextList()

        if DEBUGGING_THIS_MODULE:
            # Check that we don't have any duplicated verses in the section that we're about to return
            lastV = None
            for entry in verseEntryList:
                if entry.getMarker() == 'v':
                    vText = entry.getFullText()
                    print( f"getSectionEntriesWithContext v={vText}" )
                    assert vText != lastV
                    lastV = vText
    
        return verseEntryList,contextList
    # end of InternalBibleBookSectionIndex.getVerseEntriesWithContext


    def makeBookSectionIndex( self, givenBibleEntries:InternalBibleEntryList ) -> None:
        """
        Index the Bible book sections for faster reference.

        The parameter is a InternalBibleEntryList(), i.e., self._processedLines (from InternalBibleBook)
            i.e., a specialised list of InternalBibleEntry objects.

        The keys to the index dictionary for each Bible book are (C,V,) 2-tuples.
            Chapter -1 is the book introduction
                Each line in chapter -1 is a successive 'verse' number (usually the id line is 'verse' 0)
            For each proper chapter (usually starting with 1), verse 0 is the chapter introduction.
                Often this contains only the 'c' entry.
                Section headings are put with the following text / verse.

        Most of the time it's straightforward, but we also consolidate some of the headings.

        The created dictionary entries are (ix,indexEntryLineCount,contextMarkerList) 3-tuples where
            ix is the index into self.bookObject._processedLines,
            indexEntryLineCount is the number of entries for this verse, and
            contextMarkerList is a list containing contextual markers which still apply to this entry.

        For BSB PSA was
            0: PSA_('-1', '0') object: (inclusive) endCV=-1:7 ix=0–7 (cnt=8) Headers='PSA'
            1: PSA_('1', '0') object: (inclusive) endCV=1:0 ix=8–8 (cnt=1) c='Psalms 1'
            2: PSA_('1', '1') object: (inclusive) endCV=1:6 ix=9–77 (cnt=69) ms1/s1='BOOK I/The Two Paths'
            3: PSA_('2', '1') object: (inclusive) endCV=2:12 ix=78–201 (cnt=124) c/s1='Psalms 2/The Triumphant Messiah'
            4: PSA_('3', '1') object: (inclusive) endCV=3:8 ix=202–288 (cnt=87) c/s1='Psalms 3/Deliver Me, O LORD!'
        """
        from BibleOrgSys.Bible import Bible

        # DEBUGGING_THIS_MODULE = 99 if self.workName=='BSB' and self.BBB=='PSA' else False

        fnPrint( DEBUGGING_THIS_MODULE, f"InternalBibleBookSectionIndex.makeBookSectionIndex( {len(givenBibleEntries)} ) for {self.BBB}" )
        assert isinstance( self.BibleObject, Bible )
        assert givenBibleEntries, f"{self.workName} {self.BBB} {givenBibleEntries=}"
        self._givenBibleEntries = givenBibleEntries # Keep a pointer to the original Bible entries
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "makeBookSectionIndex-BibleObject", self.BBB, self.BibleObject.getAName(), len(self.BibleObject.books) )
        assert 'discoveryResults' in self.BibleObject.__dict__

        tempIndexData:dict[tuple[str,str],tuple[str,str,str,str,int,int,str,str,str]] = {}
        errorData = []

        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "self.BBB", self.BBB )
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "DR", self.BibleObject.discoveryResults.keys() )
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, "book DR", self.BibleObject.discoveryResults[self.BBB].keys() )
        # The following line can give a KeyError if the BBB doesn't exist in the discoveryResults
        haveSectionHeadingsForBook = self.BibleObject.discoveryResults[self.BBB]['haveSectionHeadings']
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Make section heading index for {self.workName} {self.BBB} ({haveSectionHeadingsForBook=})…" )
        needToSaveByChapter = not haveSectionHeadingsForBook \
                                or not BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(self.BBB)
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{self.BBB} needToSaveByChapter={needToSaveByChapter} since haveSectionHeadingsForBook={haveSectionHeadingsForBook} continuesThroughChapters={BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(self.BBB)}" )
        bookName = self.bookObject.getAssumedBookNames()[0]
        # TODO: The following line is a hack! (We should use the \cl field if there is one)
        if bookName in ('Psalms','Songs'): bookName = bookName[:-1] # Drop the plural
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Got '{bookName}' for {self.BBB}" )

        # def _printIndexEntry( ie ):
        #     result = str( ie )
        #     for j in range( ie.getEntryIndex(), ie.getNextEntryIndex() ):
        #         result += "\n  {}".format( givenBibleEntries[j] )
        #     return result
        # # end of _printIndexEntry


        def _saveAnySectionOutstanding( startC:str, startV:str, endC:str, endV:str,
                                     startIx:int, endIx:int, reasonMarker:str, sectionName:str ) -> None:
            """
            Save the outstanding index entry, if any
                into tempIndexData (a dict).

            start and end index numbers are inclusive, i.e., both those lines should be included!
            TODO: Is that really true about end index markers ???
            """
            # fnPrint( DEBUGGING_THIS_MODULE, f"         _saveAnySectionOutstanding( {startC}:{startV}-{endC}:{endV}"
            #         f" {startIx}-{endIx} {reasonMarker}='{sectionName}' ) for {self.BBB}…" )
            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag:
                assert isinstance( startC, str ) and isinstance( startV, str )
                assert isinstance( endC, str ) and isinstance( endV, str )
                assert isinstance( startIx, int ) and isinstance( endIx, int )
                assert isinstance( reasonMarker, str ) and isinstance( sectionName, str )

            # Handle any verse bridges
            if '-' in startV:
                if DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Adjusting startV={startV} verse bridge to {startV[:startV.find('-')]!r}" )
                startV = startV[:startV.find('-')]
            if '-' in endV:
                if DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Adjusting endV={endV} verse bridge to {endV[endV.find('-')+1:]!r}" )
                endV = endV[endV.find('-')+1:]

            # HAndle \ms1 specifics (v= doesn't occur before this)
            if reasonMarker=='ms1' and startC==endC:
                startV = str( int(startV) + 1 )
                if int(endV) < int(startV): endV = startV

            # Do some basic checking here
            if reasonMarker != 'c':
                if endV == '0':
                    logging.warning( f"makeBookSectionIndex: seems that {self.workName} {self.BBB} has a zero-length section at {startC}:0" )
                # if self.workName != 'LEB':
                #     assert endV != '0', f"Section index failed {self.workName} {self.BBB} _saveAnySectionOutstanding( {startC}:{startV} {endC}:{endV} {startIx=} {endIx=} {reasonMarker=} {sectionName=} ) Could this be a zero-length section???"
            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag:
                assert getLeadingInt(endC) >= getLeadingInt(startC), f"Expected a higher ending chapter number: {self.workName} {self.BBB} {startC=} {endC=} {reasonMarker=} {sectionName=}"
                if endC==startC:
                    assert getLeadingInt(endV) >= getLeadingInt(startV), f"Expected a higher ending verse number: {self.workName} {self.BBB} {startC}:{startV} {endV=} {reasonMarker=} {sectionName=}" # Verse ranges shouldn't go backwards

            # If the last entry was very small, we might need to combine it with this one
            #   e.g., if a section heading immediately follows a chapter break
            if tempIndexData:
                lastIndexEntryKey = list(tempIndexData.keys())[-1]
                lastIndexEntry = tempIndexData[lastIndexEntryKey]
                if (lastIndexEntry[5] + 1 - lastIndexEntry[4]) < 4: # Less than four pseudo-USFM lines in the entry
                    if DEBUGGING_THIS_MODULE:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"           Got a short index entry: {lastIndexEntry}" )
                    lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                    if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag:
                        assert lStartC == lEndC, f"Expected to be in the same chapter: {self.workName} {self.BBB} {lStartC=} {lEndC=} {reasonMarker=} {sectionName=}"
                    if (reasonMarker == 'ms1' and lastIndexEntry[6] == 'c') \
                    or (reasonMarker == 's1' and lastIndexEntry[6] in ('c','ms1','ms1/c')):
                        if DEBUGGING_THIS_MODULE:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "           COMBINING index entries" )
                        startV, startIx = lastIndexEntry[1], lastIndexEntry[4]
                        reasonMarker = f'{reasonMarker}/{lastIndexEntry[6]}' if reasonMarker=='ms1' and lastIndexEntry[6]=='c' else f'{lastIndexEntry[6]}/{reasonMarker}'
                        sectionName = f'{sectionName}/{lastIndexEntry[7]}' if reasonMarker=='ms1/c' and lastIndexEntry[6]=='c' else f'{lastIndexEntry[7]}/{sectionName}'
                        del tempIndexData[lastIndexEntryKey] # Just to be sure

            # Since startV is the current verse number when a section heading or something is encountered,
            #   it may need to be adjusted
            #if startC == '-1' and reasonMarker == 'is1':
                #if DEBUGGING_THIS_MODULE:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"           Incrementing startV from {startV} to {str( int(startV) + 1 )} with {reasonMarker}" )
                #startV = str( int(startV) + 1 )
            #else:
            for entry in self.bookObject._processedLines[startIx:endIx]:
                marker, text = entry.getMarker(), entry.getCleanText()
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"                  {marker}={text}" )
                if marker == 'v': # e.g., if we encountered section heading but hadn't encountered the verse number yet
                    if text != startV and '-' not in text: # Don't want to undo verse bridge work from above
                        if DEBUGGING_THIS_MODULE or startV != '0':
                            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"           Adjusting startV from {startV} to {text}" )
                        startV = text
                    break
                elif marker in ('v~','p~'): # e.g., if we encountered a section heading that's in the middle of a verse
                    # or could it mean that our nesting markers aren't inserted correctly ???
                    if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag:
                        assert startV.isdigit()
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"           Adjusting startV from {startV} to {startV}b" )
                    # So the previous entry should end with 'a'
                    lastIndexEntryKey = list(tempIndexData.keys())[-1]
                    lastIndexEntry = tempIndexData[lastIndexEntryKey]
                    lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                    if lEndC!=startC or lEndV!=startV:
                        logging.warning( f"makeBookSectionIndex: missing section? {self.workName} {self.BBB} section index start={startC}:{startV} lEnd={lEndC}:{lEndV}" )
                    # if self.workName not in ('LEB','ULT','BSB','WEB'): # Why ??? ULT Psa 24:10 to Psa 25:0 , BSB Psa 1:1 ???, WEB SIR 51:0
                    #     assert lEndC==startC and lEndV==startV, f"makeBookSectionIndex: missing section? {self.workName} {self.BBB} section index start={startC}:{startV} lEnd={lEndC}:{lEndV}"
                    lEndV += 'a'
                    tempIndexData[(lStartC,lStartV)] = (lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx,
                                                            lReasonMarker, lSectionName, lContext)
                    startV += 'b'
                    break

            # Check that we don't overlap with the last entry
            if tempIndexData:
                lastIndexEntryKey = list(tempIndexData.keys())[-1]
                lastIndexEntry = tempIndexData[lastIndexEntryKey]
                lStartC, lStartV, lEndC, lEndV, lStartIx, lEndIx, lReasonMarker, lSectionName, lContext = lastIndexEntry
                #if DEBUGGING_THIS_MODULE:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"          Got previous index entry: {lStartC}:{lStartV}–{lEndC}:{lEndV} {lStartIx}–{lEndIx} {lReasonMarker}={lSectionName} {lContext}" )
                if startC==lEndC and startV==lEndV: # We have overlapping entries
                    if startV.isdigit(): startV = f'{startV}a'
                    else: halt # Not sure how to handle overlapping entries

            # Save this new index entry
            if DEBUGGING_THIS_MODULE and (startC,startV) in tempIndexData:
                dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"           About to rewrite {startC}:{startV} in section index" )
            tempIndexData[(startC,startV)] = (startC,startV, endC,endV, startIx,endIx, reasonMarker, sectionName, None)
        # end of _saveAnySectionOutstanding


        # Main code of InternalBibleBookSectionIndex.makeBookSectionIndex
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    " + _("Indexing {:,} {} {} entries…").format( len(self.bookObject._processedLines), self.workName, self.BBB ) )

        # Firstly create the CV index keys with pointers to the actual lines
        self.__indexData:dict[tuple[str,str],tuple[str,str,int,int,str,str,str]] = {}
        if not BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( self.BBB ):
            return
            ## It's a front or back book (which may or may not have a c=1 and possibly a v=1 line in it)
            #lastC = lastV = saveCV = saveJ = None
            #indexEntryLineCount = 0 # indexEntryLineCount is the number of datalines pointed to by this index entry
            #strC, strV = '0', '0'
            #for j, entry in enumerate( self.bookObject._processedLines ):
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookSectionIndex2", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =", entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                #marker = entry.getMarker()
                #if BibleOrgSysGlobals.debugFlag and marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                    #assert not entry.getText() and not entry.getCleanText() and not entry.getExtras()
                #if marker == 'c': # A new chapter always means that it's a clean new index entry
                    #_saveAnySectionOutstanding()
                    ## Save anything before the first verse number as verse '-1'
                    #strC, strV = entry.getCleanText(), '0'
                    #assert strC != '0'
                    ##saveCV, saveJ = (strC,strV,), j
                    #indexEntryLineCount += 1
                #elif marker == 'v':
                    #assert strC != '0' # Should be in a chapter by now
                    #logging.warning( "makeBookSectionIndex: Why do we have a verse number in a {} {} book without chapters?".format( self.workName, self.BBB ) )
                    #if DEBUGGING_THIS_MODULE:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  makeBookSectionIndex3", j, "saveCV =", saveCV, "saveJ =", saveJ, "this =",
                            #entry.getMarker(), entry.getCleanText()[:20] + ('' if len(entry.getCleanText())<20 else '…') )
                    #_saveAnySectionOutstanding() # with the adjusted indexEntryLineCount
                    ##if 0:
                        ### Remove verse ranges, etc. and then save the verse number
                        ##strV = entry.getCleanText()
                        ##digitV = ''
                        ##for char in strV:
                            ##if char.isdigit(): digitV += char
                            ##else: # the first non-digit in the verse "number"
                                ##dPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Ignored non-digits in verse for index: {} {}:{}".format( self.BBB, strC, strV ) )
                                ##break # ignore the rest
                        ###assert strV != '0' or self.BBB=='PSA' # Not really handled properly yet
                        ##saveCV, saveJ = (strC,digitV,), revertToJ
                #elif strC == '-1': # Still in the introduction
                    ## Each line is considered a new "verse" entry in chapter '-1'
                    #assert saveCV is None and saveJ is None
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "makeBookSectionIndexIntro", _printIndexEntry( tempIndexData[(strC,strV)] ) )
                    #Vi = int( strV )
                    #assert Vi == j
                    #strV = str( Vi + 1 ) # Increment the verse number
                    #lastJ = j
                    #assert indexEntryLineCount == 0
                #else: # All the other lines don't cause a new index entry to be made
                    #indexEntryLineCount += 1
            #_saveAnySectionOutstanding()

        else: # Assume it's a normal C/V book
            lastC, lastV = '-1', ''
            strC, strV = '-1', '-1' # First line (id line) will be -1:0
            startC, startV = '-1', '0'
            lastMarkerReason, lastSectionName = 'Headers', self.BBB
            savedJ = 0
            for j, entry in enumerate( self.bookObject._processedLines ):
                assert isinstance(lastC, str) and isinstance(lastV, str)
                assert isinstance(strC, str) and isinstance(strV, str)
                assert isinstance(startC, str) and isinstance(startV, str)

                marker, text = entry.getMarker(), entry.getCleanText()
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"  makeBookSectionIndexLoop {self.workName} {self.BBB} {j}({savedJ}) str={strC}:{strV} {marker}={text} after last={lastC}:{lastV} '{lastMarkerReason}' with start={startC}:{startV}" )

                if marker == 'c':
                    dPrint( 'Never', DEBUGGING_THIS_MODULE, f"    GotC {j:,} {self.BBB} c='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                    if strC == '-1': # The first chapter always means that it's a clean new index entry
                        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"    HandleC1 {j:,} {self.BBB} {strC}:{strV} c={text!r}" )
                        endC, endV = strC, strV
                        assert startC=='-1' and endC=='-1'
                        assert int(startV) == savedJ
                        assert int(endV) == j-1
                        if j-1 <= savedJ:
                            logging.warning( f"makeBookSectionIndex: weird or missing section in {self.workName} {self.BBB} c='{text}' after last={lastC}:{lastV} with start={startC}:{startV} end={endC}:{endV} {j=} {savedJ=}" )
                        # if self.workName not in ('OEB','LEB','ULT','NET'): # Why is this failing at OEB CH1 c='10' -- ah, no prior chapters! ULT fails at PSA 1 (c 1 directly after ms1) NET JOB -1:9
                        #     assert j-1 > savedJ, f"makeBookSectionIndex: weird or missing section in {self.workName} {self.BBB} c='{text}' after last={lastC}:{lastV} with start={startC}:{startV} end={endC}:{endV} {j=} {savedJ=}"
                        _saveAnySectionOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
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
                        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"      HandleC {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                        endC, endV = lastC, lastV
                        if lastSectionName:
                            _saveAnySectionOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                            lastMarkerReason = marker
                        savedJ = j
                        startC, startV = strC, strV
                        lastMarkerReason, lastSectionName = marker, f'{bookName} {strC}'
                elif marker in  ('v','v='):
                    # NOTE: The v= marker comes before the section headings
                    #dPrint( 'Never', DEBUGGING_THIS_MODULE, f"    Handle {j:,} {self.BBB} c={strC}:v='{text}'" )
                    assert strC != '-1' # Must be in a chapter by now
                    strV = text
                elif strC == '-1': # Still in the introduction
                    # Each line is considered a new 'verse' entry in chapter '-1'
                    #   (usually the id line is 'verse' 0, i.e., -1:0)
                    lastV = strV
                    strV = str( j ) # Increment the verse number
                    dPrint( 'Never', DEBUGGING_THIS_MODULE, f"      Got {j:,} intro: {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )

                if marker in ('s1','ms1','is1'):
                    vPrint( 'Never', DEBUGGING_THIS_MODULE, f"      HandleSH {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"lastC={lastC!r} lastV={lastV!r}" )
                    endC, endV = lastC, lastV
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"endC={endC!r} endV={endV!r}" )
                    if self.workName not in ('LEB',):
                        assert endV != '0', f"{self.workName} {self.BBB} section index {endC=} zero endV"
                    if lastSectionName:
                        if j-1 == savedJ \
                        or int(endC) < int(startC):# There's only one entry line
                            if DEBUGGING_THIS_MODULE:
                                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"        FIXING1 end={endC}:{endV} to {startC}:{startV}" )
                            endC, endV = startC, startV
                        #if lastMarkerReason=='c' and marker=='ms1':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"        FIXING2 lastMarkerReason={lastMarkerReason} to {marker}" )
                            #lastMarkerReason = marker
                        _saveAnySectionOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
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
                        #dPrint( 'Never', DEBUGGING_THIS_MODULE, f"      HandleC {j:,} {self.BBB} {strC}:{strV} {marker}='{text}' after last={lastC}:{lastV} with start={startC}:{startV}" )
                        #endC, endV = lastC, lastV
                        #if lastSectionName:
                            #_saveAnySectionOutstanding( startC, startV, endC, endV, savedJ, j-1, lastMarkerReason, lastSectionName )
                            #lastMarkerReason = marker
                        #savedJ = j
                        #startC, startV = strC, strV
                        #lastSectionName = f'{bookName} {strC}'
                elif marker in ('v~','p~'): # We have verse data
                    if not lastSectionName:
                        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Setting lastSectionName for verse info found at {strC}:{strV}" )
                        lastSectionName = f"{bookName} {strC}"
                # else: # All the other lines don't cause a new index entry to be made

                if marker == 'v': # Don't update lastC/lastV too often -- only for actual verses
                    lastC, lastV = strC, strV

            endC, endV = strC, strV
            _saveAnySectionOutstanding( startC, startV, endC, endV, savedJ, j, lastMarkerReason, lastSectionName )

        # Now copy the info into our real dict (we don't include startC and startV in the actual entries coz they're the key)
        for key,(startC,startV, endC,endV, startIx,endIx, reasonMarker, sectionName, contextList) in tempIndexData.items():
            assert key[0]==startC and key[1]==startV
            self.__indexData[key] = InternalBibleBookSectionIndexEntry( endC,endV, startIx,endIx, reasonMarker, sectionName, contextList )

        if DEBUGGING_THIS_MODULE:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"We got {len(tempIndexData)} index entries for {self.BBB}." )
            for j, (key,value) in enumerate(self.__indexData.items(), start=1):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {j:2}/ {key} = {value}" )
        # if self.workName=='BSB' and self.BBB=='PSA':
        #     dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  makeBookSectionIndex() for {self.BBB} finished." )
        #     halt
        return

        # if errorData: # We got some overwriting errors
        #     lastBBB = None
        #     errorDataString = ''
        #     for BBB,C,V in errorData:
        #         assert BBB == self.BBB # We didn't really need to save this
        #         if BBB != lastBBB:
        #             errorDataString += (' ' if errorDataString else '') + BBB
        #             lastBBB, lastC = BBB, None
        #         if C != lastC:
        #             errorDataString += (' ' if lastC is None else '; ') + C + ':'
        #             lastC = C
        #         errorDataString += ('' if errorDataString[-1]==':' else ',') + V
        #     thisLogger = logging.warning if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag else logging.info
        #     thisLogger( f"makeBookSectionIndex._saveAnySectionOutstanding: Needed to combine multiple index entries for {errorDataString}" )

        # # Now calculate the contextMarkerList for each CV entry and create the proper (full) InternalBibleBookSectionIndexEntries
        # contextMarkerList = []
        # for (C,V), (indexStart,count) in self.__indexData.items():
        #     if DEBUGGING_THIS_MODULE:
        #         vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "makeBookSectionIndex for {} {} {}:{} {} {} {}".format( self.workName, self.BBB, C, V, indexStart, count, contextMarkerList ) )
        #     # Replace the existing (temporary) index entry to include a copy of the previous contextMarkerList
        #     #   e.g., a typical verse might be inside a paragraph in a section
        #     #            thus getting the contextMarkerList: ['chapters','c','s1','p']
        #     self.__indexData[(C,V)] = InternalBibleBookSectionIndexEntry( indexStart, count, contextMarkerList.copy() )
        #     for j in range( indexStart, indexStart+count ):
        #         entry = self.givenBibleEntries[j]
        #         marker = entry.getMarker()
        #         vPrint( 'Never', DEBUGGING_THIS_MODULE, "  makeBookSectionIndex {} marker: {} {}".format( j, marker, entry.getCleanText() ) )
        #         if marker[0]=='¬' and marker != '¬v': # We're closing a paragraph marker
        #             originalMarker = marker[1:]
        #             if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
        #                 # Should be exactly one of these markers (open) in the contextMarkerList
        #                 # XXXXXXXXX Gets messed up by GNT Mrk 16:9 has two \s headings in a row !!!!!!!!!!!!!!!!!!!
        #                 if contextMarkerList.count(originalMarker)!=1:
        #                     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    makeBookSectionIndex originalMarker: {!r} contextMarkerList={}".format( originalMarker, contextMarkerList ) )
        #                     logging.critical( "makeBookSectionIndex found a nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
        #                 if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
        #                     assert contextMarkerList.count( originalMarker ) == 1
        #             try: # Remove first open occurrence of the marker just closed (e.g., s1 can occur after c and still be open)
        #                 if DEBUGGING_THIS_MODULE:
        #                     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    makeBookSectionIndex: Removing {} from contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
        #                 contextMarkerList.remove( originalMarker )
        #             except ValueError: # oops something went wrong
        #                 #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookSectionIndex: marker = {}'.format( marker ) )
        #                 #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookSectionIndex: entry = {}'.format( entry ) )
        #                 #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'makeBookSectionIndex: contextMarkerList = {}'.format( contextMarkerList ) )
        #                 logging.critical( "makeBookSectionIndex found an unknown nesting error for {} {} around {}:{}".format( self.workName, self.BBB, C, V ) )
        #                 if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
        #             if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
        #                 if contextMarkerList.count( originalMarker ):
        #                     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{}/ {} {}:{} {!r} {}".format( j, self.BBB, C, V, originalMarker, contextMarkerList ) )
        #                 assert contextMarkerList.count( originalMarker ) == 0
        #         if marker in BOS_NESTING_MARKERS and marker!='v':
        #             if DEBUGGING_THIS_MODULE:
        #                 vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    makeBookSectionIndex: Adding {} to contextMarkerList at {} {}:{}".format( marker, self.BBB, C, V ) )
        #             contextMarkerList.append( marker )
        # if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
        #     assert not contextMarkerList # Should be empty at end if nesting for the book is correct

        # self._indexedFlag = True
        # #if 0:
        #     #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self )
        #     #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', self.__indexData )
        #     #for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
        #         #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " {:3} {}: {}".format( j, iKey, iEntry ) )
        #     #halt

        # if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        #     self.checkBookSectionIndex() # Make sure our code above worked properly
        #dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  makeBookSectionIndex() for {self.BBB} finished." )
    # end of InternalBibleBookSectionIndex.makeBookSectionIndex


    def checkBookSectionIndex( self ) -> None:
        """
        Just run a quick internal check on the index.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "InternalBibleBookSectionIndex.checkBookSectionIndex()")
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + _("Checking {} {} {} section index entries…").format( len(self.__indexData), self.workName, self.BBB ) )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, self )

        # Check that all C,V entries (the index to the index) are digits
        for ixKey in self.__indexData:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ixKey ); halt
            C, V = ixKey
            if C!='-1' and not C.isdigit():
                logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Non-digit C entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )
            if not V.isdigit():
                logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Non-digit V entry in {} {} {}:{}".format( self.workName, self.BBB, repr(C), repr(V) ) )

        # Copy the index (dict) into a (sorted) list so that we can access entries sequentially for testing
        try: sortedIndex = sorted( self.__indexData, key=lambda s: int(s[0])*1000+int(s[1]) )
        except ValueError: # non-numbers in C or V -- should already have received notification above
            logging.error( "InternalBibleBookSectionIndex.checkBookSectionIndex: Unable to sort index for {} {}".format( self.workName, self.BBB ) )
            sortedIndex = self.__indexData # for now
        #for j, key in enumerate( sortedIndex ):
            #C, V = key
            #indexEntry = self.__indexData[key]
            #entries = self.getVerseEntries( key )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "checkBookSectionIndex display", j, key, indexEntry, entries )
            #if self.BBB!='FRT' and j>30: break

        # Now go through the index entries (in order) and do the actual checks
        lastKey = nextKey = nextNextKey = None
        for k, key in enumerate( sortedIndex ):
            # Try getting the next couple of keys also (if they exist)
            try: nextKey = sortedIndex[k+1]
            except IndexError: nextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "nextKeyError1", k, len(sortedIndex), repr(key) ); nextKey = None
            try: nextNextKey = sortedIndex[k+2]
            except IndexError: nextNextKey = None
            except KeyError: # Happens if the sortedIndex is still a dict (rather than a list)
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "nextKeyError2", k, len(sortedIndex), repr(key) ); nextKey = None
            C, V = key

            indexEntry = self.__indexData[key]
            entries = self.getVerseEntries( key ) # Gets the list of index entries for this one CV index
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
                logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable index or encoding error (multiple v entries) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                assert vCount <= 1

            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookSectionIndex.checkBookSectionIndex line", self.BBB, key, indexEntry, entries, foundMarkers )
            #if self.BBB!='FRT': halt

            # Check the order of the markers
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if V == '0':
                    if 'c' not in foundMarkers:
                        logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable v0 encoding error (no chapter?) in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: assert 'c' in foundMarkers
                else: assert 'v' in foundMarkers
                if 'p' in foundMarkers:
                    if 'p~' not in foundMarkers and 'v' not in foundMarkers:
                        logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable (early in chapter) p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        assert 'p~' in foundMarkers or 'v' in foundMarkers
                if 'q1' in foundMarkers or 'q2' in foundMarkers:
                    if 'v' not in foundMarkers and 'p~' not in foundMarkers:
                        logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable q1/q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                        assert 'v' in foundMarkers or 'p~' in foundMarkers

                previousMarker = nextMarker = None # But these skip over rem (remark markers)
                for j, marker in enumerate( foundMarkers ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'CheckIndex2 {} {}:{} {}/ m={!r} pM={!r} nM={!r}'.format( self.BBB, C, V, j, marker, previousMarker, nextMarker ) )

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
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable v encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                    elif marker == 'vp#':
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "After ({}) vp#: {!r} {} {}:{} in {}".format( previousMarker, nextMarker, self.BBB, C, V, self.workName ) )
                        if DEBUGGING_THIS_MODULE:
                            if self.BBB!='ESG': assert nextMarker in ('v','p',) # after vp#
                    elif marker in ('v~','p~',):
                        if nextMarker in ('v~','p~',): # These don't usually follow each other
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable {} encoding error in {} {} {}:{} {}".format( marker, self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt

                    if anyText or anyExtras: # Mustn't be a blank (unfinished) verse
                        if marker=='p' and nextMarker not in ('v','p~','vp#','c#','¬p'):
                            if lastKey and DEBUGGING_THIS_MODULE: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookSectionIndex.checkBookSectionIndex: lastKey1", self.BBB, lastKey, self.getVerseEntries( lastKey ) )
# NOTE: temporarily down-graded from critical …
                            logging.error( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable p encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if DEBUGGING_THIS_MODULE:
                                if nextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookSectionIndex.checkBookSectionIndex: nextKey1", self.BBB, nextKey, self.getVerseEntries( nextKey ) )
                                if nextNextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookSectionIndex.checkBookSectionIndex: nextNextKey1", self.BBB, nextNextKey, self.getVerseEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q1' and nextMarker not in ('v','p~','c#','¬q1',):
                            if lastKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "InternalBibleBookSectionIndex.checkBookSectionIndex: lastKey2", self.BBB, lastKey, self.getVerseEntries( lastKey ) )
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable q1 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if DEBUGGING_THIS_MODULE:
                                if nextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookSectionIndex.checkBookSectionIndex: nextKey2", self.BBB, nextKey, self.getVerseEntries( nextKey ) )
                                if nextNextKey: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  InternalBibleBookSectionIndex.checkBookSectionIndex: nextNextKey2", self.BBB, nextNextKey, self.getVerseEntries( nextNextKey ) )
                                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q2' and nextMarker not in ('v','p~', '¬q2' ):
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable q2 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q3' and nextMarker not in ('v','p~', '¬q3'):
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt
                        elif marker=='q4' and nextMarker not in ('p~', '¬q3'):
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Probable q3 encoding error in {} {} {}:{} {}".format( self.workName, self.BBB, C, V, entries ) )
                            if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: halt

                    # Set the previous marker (but skipping over rem markers)
                    if marker != 'rem': previousMarker = marker

            # Now check them
            if C == '-1': # the book introduction
                pass
            else: # not the book introduction
                if  V=='0': # chapter introduction
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.BBB, C, V, foundMarkers, entries )
                    #newKey = (C, '1')
                    #try:
                        #iE = self.__indexData[newKey]
                        #iD, ct = self.getVerseEntries( newKey )
                    #except KeyError: pass
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " ", newKey, iD, ct )
                    if self.BBB=='ACT' and C=='8':
                        if 'p' in foundMarkers:
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: Check that text in {} Acts 8:0 gets processed correctly!".format( self.workName ) )
                        #else:
                            #if 's1'  in foundMarkers or 'r' in foundMarkers or 'p' in foundMarkers or 'q1' in foundMarkers:
                                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "xyz", key, entries )
                            #if self.workName != '1974_TB':
                                #assert 's1' not in foundMarkers and 'r' not in foundMarkers and 'p' not in foundMarkers and 'q1' not in foundMarkers

            # Check that C,V entries match
            for entry in entries:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker in ( 'c','c#' ):
                    if cleanText != C:
                        logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: wrong {} {} chapter number {!r} expected {!r}".format( self.workName, self.BBB, cleanText, C ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                elif marker == 'v':
                    if cleanText != V:
                        if '-' not in cleanText and ',' not in cleanText: # Handle verse ranges
                            logging.critical( "InternalBibleBookSectionIndex.checkBookSectionIndex: wrong {} {} {} verse number {!r} expected {!r}".format( self.workName, self.BBB, C, cleanText, V ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
            lastKey = key

        if DEBUGGING_THIS_MODULE: # Just print the beginning part of the index to view
            if self.BBB in ('GEN','MAT'):
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, self )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', self.__indexData )
                for j, (iKey,iEntry) in enumerate( self.__indexData.items() ):
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, " {:3} {}: {}".format( j, iKey, iEntry ) )
                    if iEntry.entryCount > 1:
                        for scj in range( iEntry.entryCount ):
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "      {}".format( self._givenBibleEntries[ iEntry.entryIndex + scj ] ) ) # This is an InternalBibleEntry
                    if j > 40: break
                halt
        #if self.BBB=='FRT': halt
    # end of InternalBibleBookSectionIndex.checkBookSectionIndex
# end of class InternalBibleBookSectionIndex



def briefDemo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
    ICVE = InternalBibleBookCVIndexEntry( 0, 1, ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ICVE={ICVE}" )
    ISE = InternalBibleBookSectionIndexEntry( '1', '1', '1', '5', 0, 1, 's1', 'Section Name', ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ISE={ISE}" )

    #IBB = InternalBibleIndexes( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    if 1: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
        import os
        from BibleOrgSys.Formats.USFMBible import USFMBible

        testData = ( # name, abbreviation, folderpath for USFM files
                ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData, start=1 ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleIndexes B{j}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                UB.discover()
                UB.makeSectionIndex()
                break
            else: logging.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleIndexes.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
    ICVE = InternalBibleBookCVIndexEntry( 0, 1, ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ICVE={ICVE}" )
    ISE = InternalBibleBookSectionIndexEntry( '1', '1', '1', '5', 0, 1, 's1', 'Section Name', ['abc'] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"ISE={ISE}" )

    #IBB = InternalBibleIndexes( 'GEN' )
    ## The following fields would normally be filled in a by "load" routine in the derived class
    #IBB.objectNameString = 'Dummy test Internal Bible Book object'
    #IBB.objectTypeString = 'DUMMY'
    #IBB.sourceFilepath = 'Nowhere'
    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, IBB )

    if 1: # Test reading and writing a USFM Bible (with MOST exports -- unless debugging)
        import os
        from BibleOrgSys.Formats.USFMBible import USFMBible

        testData = ( # name, abbreviation, folderpath for USFM files
                ("Matigsalug", 'MBTV', Path( '/mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData, start=1 ):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nInternalBibleIndexes B{j}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                UB.discover()
                UB.makeSectionIndex()
            else: logging.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of InternalBibleIndexes.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBibleIndexes.py
