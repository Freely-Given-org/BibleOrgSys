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


LAST_MODIFIED_DATE = '2026-04-12' # by RJH
SHORT_PROGRAM_NAME = "test_OET_RV_HAG_indexes"
PROGRAM_NAME = "Test OET-RV HAG CV and section indexes"
PROGRAM_VERSION = '0.01'
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

    if 0: # Not for briefDemo()
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
    """
    fnPrint( DEBUGGING_THIS_MODULE, "test_CV_index()" )

    thisBible.doPostLoadProcessing() # Makes the CV index as part of this
    bookObject = thisBible[BBB]
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._CVIndex=}" )
    assert len(bookObject._CVIndex) == 63

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
