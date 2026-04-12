#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# test_OET_RV_HAG_indexes.py
#   Last modified: 2026-02-12 (also update PROGRAM_VERSION below)
#
# Module testing InternalBibleIndexes.py
#
# Copyright (C) 2026 Robert Hunt
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
Module testing BibleBookOrdersConverter.py and BibleBookOrders.py.
"""
import requests
import os.path
import unittest
import sys

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry
from BibleOrgSys.Internals.InternalBibleIndexes import InternalBibleBookCVIndex, InternalBibleBookSectionIndex


LAST_MODIFIED_DATE = '2026-04-13' # by RJH
SHORT_PROGRAM_NAME = "test_OET_RV_HAG_indexes"
PROGRAM_NAME = "Test OET-RV HAG CV and section indexes"
PROGRAM_VERSION = '0.02'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BBB = 'HAG'
def load_OET_RV_Haggai() -> ESFMBible|None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, "load_OET_RV_Haggai()" )

    folderURL = 'https://raw.githubusercontent.com/Freely-Given-org/OpenEnglishTranslation--OET/refs/heads/main/translatedTexts/ReadersVersion'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Looking for ESFM Bible at {folderURL}" )
    EsfmBib = ESFMBible( folderURL, 'Open English Translation Readers’ Version', 'OET-RV' )
    # EsfmBib.preload()
    EsfmBib.loadBook( BBB, 'OET-RV_HAG.ESFM' )

    if 0: # Check that it loaded correctly
        from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
        from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntry
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Displaying ESFM text from some given references…" )
        for thisBBB,C,V in ( (BBB,'1','1'),(BBB,'1','2'),(BBB,'1','3'),(BBB,'1','4'),(BBB,'1','5'),(BBB,'1','6'),(BBB,'2','1'),(BBB,'2','23') ):
            svk = SimpleVerseKey( thisBBB, C, V )
            shortText = svk.getShortText()
            verseDataList = EsfmBib.getVerseDataList( svk )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{}\n{}".format( shortText, verseDataList ) )
            if verseDataList is None: continue
            for verseDataEntry in verseDataList:
                # This loop is used for several types of data
                assert isinstance( verseDataEntry, InternalBibleEntry )
                marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                fullText = verseDataEntry.getFullText()
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "marker={} cleanText={!r}{}".format( marker, cleanText,
                                            " extras={}".format( extras ) if extras else '' ) )
                    if adjustedText and adjustedText!=cleanText:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), "adjustedText={!r}".format( adjustedText ) )
                    if fullText and fullText!=cleanText:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), "fullText={!r}".format( fullText ) )
                    if originalText and originalText!=cleanText:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), "originalText={!r}".format( originalText ) )

    bookObject = EsfmBib[BBB]
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._processedLines=}" )
    assert len(bookObject._processedLines) == 183

    return EsfmBib
# end of load_OET_RV_Haggai

def test_CV_index( thisBible:ESFMBible ):
    """
    0 ('-1', '0') InternalBibleBookCVIndexEntry object: ix=0 cnt=1 ixE=1
    1 ('-1', '1') InternalBibleBookCVIndexEntry object: ix=1 cnt=1 ixE=2
    2 ('-1', '2') InternalBibleBookCVIndexEntry object: ix=2 cnt=1 ixE=3
    3 ('-1', '3') InternalBibleBookCVIndexEntry object: ix=3 cnt=1 ixE=4
    4 ('-1', '4') InternalBibleBookCVIndexEntry object: ix=4 cnt=1 ixE=5
    5 ('-1', '5') InternalBibleBookCVIndexEntry object: ix=5 cnt=1 ixE=6
    6 ('-1', '6') InternalBibleBookCVIndexEntry object: ix=6 cnt=1 ixE=7 ctxt=['headers']
    7 ('-1', '7') InternalBibleBookCVIndexEntry object: ix=7 cnt=1 ixE=8 ctxt=['headers']
    8 ('-1', '8') InternalBibleBookCVIndexEntry object: ix=8 cnt=1 ixE=9 ctxt=['headers']
    9 ('-1', '9') InternalBibleBookCVIndexEntry object: ix=9 cnt=1 ixE=10 ctxt=['headers']
    10 ('-1', '10') InternalBibleBookCVIndexEntry object: ix=10 cnt=1 ixE=11 ctxt=['headers']
    11 ('-1', '11') InternalBibleBookCVIndexEntry object: ix=11 cnt=1 ixE=12 ctxt=['headers']
    12 ('-1', '12') InternalBibleBookCVIndexEntry object: ix=12 cnt=1 ixE=13
    13 ('-1', '13') InternalBibleBookCVIndexEntry object: ix=13 cnt=1 ixE=14 ctxt=['intro']
    14 ('-1', '14') InternalBibleBookCVIndexEntry object: ix=14 cnt=1 ixE=15 ctxt=['intro']
    15 ('-1', '15') InternalBibleBookCVIndexEntry object: ix=15 cnt=1 ixE=16 ctxt=['intro']
    16 ('-1', '16') InternalBibleBookCVIndexEntry object: ix=16 cnt=1 ixE=17 ctxt=['intro', 'iot']
    17 ('-1', '17') InternalBibleBookCVIndexEntry object: ix=17 cnt=1 ixE=18 ctxt=['intro', 'iot']
    18 ('-1', '18') InternalBibleBookCVIndexEntry object: ix=18 cnt=1 ixE=19 ctxt=['intro', 'iot']
    19 ('-1', '19') InternalBibleBookCVIndexEntry object: ix=19 cnt=1 ixE=20 ctxt=['intro']
    20 ('-1', '20') InternalBibleBookCVIndexEntry object: ix=20 cnt=1 ixE=21 ctxt=['intro']
    21 ('-1', '21') InternalBibleBookCVIndexEntry object: ix=21 cnt=1 ixE=22 ctxt=['intro']
    22 ('-1', '22') InternalBibleBookCVIndexEntry object: ix=22 cnt=1 ixE=23

    23 ('1', '0') InternalBibleBookCVIndexEntry object: ix=23 cnt=1 ixE=24 ctxt=['chapters']
    24 ('1', '1') InternalBibleBookCVIndexEntry object: ix=24 cnt=7 ixE=31 ctxt=['chapters', 'c']
    25 ('1', '2') InternalBibleBookCVIndexEntry object: ix=31 cnt=4 ixE=35 ctxt=['chapters', 'c', 'p']
    26 ('1', '3') InternalBibleBookCVIndexEntry object: ix=35 cnt=5 ixE=40 ctxt=['chapters', 'c']
    27 ('1', '4') InternalBibleBookCVIndexEntry object: ix=40 cnt=4 ixE=44 ctxt=['chapters', 'c']
    28 ('1', '5') InternalBibleBookCVIndexEntry object: ix=44 cnt=3 ixE=47 ctxt=['chapters', 'c', 'm']
    29 ('1', '6') InternalBibleBookCVIndexEntry object: ix=47 cnt=4 ixE=51 ctxt=['chapters', 'c', 'm']
    30 ('1', '7') InternalBibleBookCVIndexEntry object: ix=51 cnt=4 ixE=55 ctxt=['chapters', 'c']
    31 ('1', '8') InternalBibleBookCVIndexEntry object: ix=55 cnt=4 ixE=59 ctxt=['chapters', 'c', 'p']
    32 ('1', '9') InternalBibleBookCVIndexEntry object: ix=59 cnt=4 ixE=63 ctxt=['chapters', 'c']
    33 ('1', '10') InternalBibleBookCVIndexEntry object: ix=63 cnt=3 ixE=66 ctxt=['chapters', 'c', 'p']
    34 ('1', '11') InternalBibleBookCVIndexEntry object: ix=66 cnt=4 ixE=70 ctxt=['chapters', 'c', 'p']
    35 ('1', '12') InternalBibleBookCVIndexEntry object: ix=70 cnt=6 ixE=76 ctxt=['chapters', 'c']
    36 ('1', '13') InternalBibleBookCVIndexEntry object: ix=76 cnt=3 ixE=79 ctxt=['chapters', 'c', 'p']
    37 ('1', '14') InternalBibleBookCVIndexEntry object: ix=79 cnt=3 ixE=82 ctxt=['chapters', 'c', 'p']
    38 ('1', '15') InternalBibleBookCVIndexEntry object: ix=82 cnt=5 ixE=87 ctxt=['chapters', 'c', 'p']

    39 ('2', '0') InternalBibleBookCVIndexEntry object: ix=87 cnt=1 ixE=88 ctxt=['chapters']
    40 ('2', '1') InternalBibleBookCVIndexEntry object: ix=88 cnt=7 ixE=95 ctxt=['chapters', 'c']
    41 ('2', '2') InternalBibleBookCVIndexEntry object: ix=95 cnt=3 ixE=98 ctxt=['chapters', 'c', 'p']
    42 ('2', '3') InternalBibleBookCVIndexEntry object: ix=98 cnt=3 ixE=101 ctxt=['chapters', 'c', 'p']
    43 ('2', '4') InternalBibleBookCVIndexEntry object: ix=101 cnt=3 ixE=104 ctxt=['chapters', 'c', 'p']
    44 ('2', '5') InternalBibleBookCVIndexEntry object: ix=104 cnt=3 ixE=107 ctxt=['chapters', 'c', 'p']
    45 ('2', '6') InternalBibleBookCVIndexEntry object: ix=107 cnt=3 ixE=110 ctxt=['chapters', 'c', 'p']
    46 ('2', '7') InternalBibleBookCVIndexEntry object: ix=110 cnt=3 ixE=113 ctxt=['chapters', 'c', 'p']
    47 ('2', '8') InternalBibleBookCVIndexEntry object: ix=113 cnt=3 ixE=116 ctxt=['chapters', 'c', 'p']
    48 ('2', '9') InternalBibleBookCVIndexEntry object: ix=116 cnt=4 ixE=120 ctxt=['chapters', 'c', 'p']
    49 ('2', '10') InternalBibleBookCVIndexEntry object: ix=120 cnt=6 ixE=126 ctxt=['chapters', 'c']
    50 ('2', '11') InternalBibleBookCVIndexEntry object: ix=126 cnt=3 ixE=129 ctxt=['chapters', 'c', 'p']
    51 ('2', '12') InternalBibleBookCVIndexEntry object: ix=129 cnt=7 ixE=136 ctxt=['chapters', 'c', 'p']
    52 ('2', '13') InternalBibleBookCVIndexEntry object: ix=136 cnt=8 ixE=144 ctxt=['chapters', 'c']
    53 ('2', '14') InternalBibleBookCVIndexEntry object: ix=144 cnt=5 ixE=149 ctxt=['chapters', 'c']
    54 ('2', '15') InternalBibleBookCVIndexEntry object: ix=149 cnt=3 ixE=152 ctxt=['chapters', 'c', 'p']
    55 ('2', '16') InternalBibleBookCVIndexEntry object: ix=152 cnt=3 ixE=155 ctxt=['chapters', 'c', 'p']
    56 ('2', '17') InternalBibleBookCVIndexEntry object: ix=155 cnt=3 ixE=158 ctxt=['chapters', 'c', 'p']
    57 ('2', '18') InternalBibleBookCVIndexEntry object: ix=158 cnt=3 ixE=161 ctxt=['chapters', 'c', 'p']
    58 ('2', '19') InternalBibleBookCVIndexEntry object: ix=161 cnt=4 ixE=165 ctxt=['chapters', 'c', 'p']
    59 ('2', '20') InternalBibleBookCVIndexEntry object: ix=165 cnt=6 ixE=171 ctxt=['chapters', 'c']
    60 ('2', '21') InternalBibleBookCVIndexEntry object: ix=171 cnt=3 ixE=174 ctxt=['chapters', 'c', 'p']
    61 ('2', '22') InternalBibleBookCVIndexEntry object: ix=174 cnt=3 ixE=177 ctxt=['chapters', 'c', 'p']
    62 ('2', '23') InternalBibleBookCVIndexEntry object: ix=177 cnt=6 ixE=183 ctxt=['chapters', 'c', 'p']
    """
    fnPrint( DEBUGGING_THIS_MODULE, "test_CV_index()" )

    thisBible.doPostLoadProcessing() # Makes the CV index as part of this
    bookObject = thisBible[BBB]
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._CVIndex=}" )
    assert len(bookObject._CVIndex) == 63 # 2 chapters + 38 verses + 17(+6 extras) header/intro lines
    # for ee,(CV,thisCVIndexEntry) in enumerate( bookObject._CVIndex.items() ):
    #     print( f"  {ee} {CV} {thisCVIndexEntry}" )

    C, V = '1', '1'
    c, v = int( C ), int( V )
    verseEntryList, contextList = thisBible.getContextVerseData( (BBB,C) if c==-1 else (BBB, C, V) )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"For {BBB} {C}:{V}\n  {contextList=}" )
    assert contextList == ['chapters', 'c']
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {verseEntryList=}" )
    assert isinstance( verseEntryList, InternalBibleEntryList ) # A list with ESFM line entries (InternalBibleEntry)
    assert len(verseEntryList) == 7
    assert verseEntryList[0].getOriginalMarker() == 's1'
    assert verseEntryList[0].getOriginalText() == "God's command to rebuild the temple"
    assert verseEntryList[1].getOriginalMarker() == 'rem'
    assert verseEntryList[2].getOriginalMarker() == 'p'
    assert verseEntryList[2].getOriginalText() == ''
    assert verseEntryList[3].getMarker() == 'c#'
    assert verseEntryList[3].getOriginalText() == C
    assert verseEntryList[4].getOriginalMarker() == 'v'
    assert verseEntryList[4].getOriginalText() == V
    assert verseEntryList[5].getMarker() == 'v~'
    assert verseEntryList[6].getMarker() == '¬v'
    assert verseEntryList[6].getCleanText() == V
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"OET-RV CV index for {BBB} matches expectations." )
# end of test_CV_index

def test_section_index( thisBible:ESFMBible ):
    """
    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG'
    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction'

    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=24–69 (cnt=46) s1='God's command to rebuild the temple'
    3 1:12 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=70–87 (cnt=18) s1='The people start rebuilding'
    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=88–119 (cnt=32) s1='The splendour of the new temple'
    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=120–164 (cnt=45) s1='Haggai consults the priests'
    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=165–182 (cnt=18) s1='God's promise to Zerubavel'
    """
    fnPrint( DEBUGGING_THIS_MODULE, "test_section_index()" )

    thisBible.discover()
    assert 'discoveryResults' in thisBible.__dict__
    thisBible.makeSectionIndex()
    bookObject = thisBible[BBB]
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._SectionIndex=}" )
    assert isinstance( bookObject._SectionIndex, InternalBibleBookSectionIndex ) # A dict with (C,V) keys
    assert len(bookObject._SectionIndex) == 7
    HAG_startCV_list = ( ('-1','0'),  ('-1','13'), ('1','1'),  ('1','12'), ('2','1'), ('2','10'), ('2','20') )
    HAG_endCV_list   = ( ('-1','12'), ('-1','22'), ('1','11'), ('1','15'), ('2','9'), ('2','19'), ('2','23') )
    HAG_indices      = ( (0,12), (13,22), (24,69), (70,87), (88,119), (120,164), (165,182) )
    HAG_reasons     = ( 'Headers', 'is1', 's1', 's1', 's1', 's1', 's1' )
    HAG_contexts     = ( [], [], [], [], [], [], [] )
    for n,((C,V),sectionIndexEntry) in enumerate( bookObject._SectionIndex.items() ):
        # print( f"  {n} {C}:{V} {sectionIndexEntry}")
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{sectionIndexEntry=}" )
        if n==0: assert sectionIndexEntry.sectionName == BBB, f"{sectionIndexEntry.sectionName} vs {BBB}"
        assert (C,V) == HAG_startCV_list[n], f"{n} {C}:{V} vs {HAG_startCV_list[n]}"
        assert (sectionIndexEntry.endC,sectionIndexEntry.endV) == HAG_endCV_list[n], f"{n} {sectionIndexEntry.endC}:{sectionIndexEntry.endV} vs {HAG_endCV_list[n]}"
        assert (sectionIndexEntry.startIx,sectionIndexEntry.endIx) == HAG_indices[n], f"{n} {sectionIndexEntry.startIx}:{sectionIndexEntry.endIx} vs {HAG_indices[n]}"
        assert sectionIndexEntry.reasonMarker == HAG_reasons[n], f"{n} {sectionIndexEntry.reasonMarker} vs {HAG_reasons[n]}"
        assert sectionIndexEntry.contextList == HAG_contexts[n], f"{n} {sectionIndexEntry.contextList} vs {HAG_contexts[n]}"
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"OET-RV section index for {BBB} matches expectations." )
# end of test_section_index


def fullDemo() -> None:
    """
    Full demo to check module is working
    """
    loadedESFMBible = load_OET_RV_Haggai()
    if loadedESFMBible:
        test_CV_index( loadedESFMBible )
        test_section_index( loadedESFMBible )
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    # Export option allows the two indexes to be created as files in the current folder
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False ) # TODO: not implemented yet (save indexes to .txt files)

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, PROGRAM_NAME_VERSION )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of test_OET_RV_HAG_indexes.py
