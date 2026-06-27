#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# EvaluateBibleLiteralness.py
#
# Command-line app to load OET Hebrew and Greek files,
#   and then load any English Bible translation
#   and do some automated comparisons of the texts
#   in order to determine a literalness score for the English translation.
#
# Copyright (C) 2019-2025 Robert Hunt
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
A command-line app as part of BibleOrgSys (Bible Organisational System or BOS) demos.
This app downloads both a Greek New Testament and a literal English translation
    and then compares the texts of the two versions verse by verse.

Of course, you must already have Python3 installed on your system.
    (Probably installed by default on most modern Linux systems.)

Note that this app can be run from your BibleOrgSys folder,
    e.g., using the command:
        Apps/EvaluateBibleLiteralness.py

You can discover the version with
        Apps/EvaluateBibleLiteralness.py --version

You can discover the available command line parameters with
        Apps/EvaluateBibleLiteralness.py --help

    e.g., for verbose mode
        Apps/EvaluateBibleLiteralness.py --verbose
    or
        Apps/EvaluateBibleLiteralness.py -v

This app also demonstrates how little actual code is required to use the BibleOrgSys to load an online Bible
    and then to process it verse by verse.

The BibleOrgSys is developed and well-tested on Linux (Ubuntu)
    but also runs on Windows and OS-X (although not so well tested).

Note that the standard verbosityLevel is 2:
    -s (silent) is 0
    -q (quiet) is 1
    -i (information) is 3
    -v (verbose) is 4.


RESULTS OF EARLY VERSION (before updating old English spelling):
    Versions with LOWEST NT literalness scores were: 1ST @ 0.0, TPT @ 0.0, MSG @ 1.3, UST @ 2.3, Wycl @ 2.8
    Versions with HIGHEST NT literalness scores were: OET-LV @ 9.3, ULT @ 6.5, BLB @ 6.2, LEB @ 6.2, LSV @ 6.2

    All versions with NT literalness scores were: OET-LV @ 9.3, ULT @ 6.5, BLB @ 6.2, LEB @ 6.2, LSV @ 6.2, LSB @ 5.9, YLT @ 5.9, ASV @ 5.9, RV @ 5.8, NASB @ 5.8, ESV @ 5.7, CSB @ 5.6, WEBBE @ 5.6, NAB @ 5.5, KJB-1769 @ 5.4, NRSV @ 5.4, NKJV @ 5.4, NET @ 5.2, NIV @ 5.1, BSB @ 4.9, 2DT @ 4.7, OEB @ 4.3, Gnva @ 4.2, JQT @ 4.1, OET-RV @ 3.9, NLT @ 3.8, Bshps @ 3.5, TNT @ 3.4, Cvdl @ 3.2, CEV @ 3.0, Wycl @ 2.8, UST @ 2.3, MSG @ 1.3, TPT @ 0.0, 1ST @ 0.0

    NOTE: The highest 10.0 score above is for the most LITERAL version.
    You should note that it's not an indication that it's a GOOD, READABLE, or UNDERSTANDABLE English translation!

    Check literalness of English Bible translations vs Hebrew & Greek v0.11 finished at 23:21 after 84 minutes.


CHANGELOG:
    2025-03-21 Handle obsolete pickle in OET-LV which has OT and NT in separate folders
"""
from pathlib import Path
from csv import DictReader
from collections import defaultdict
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, BOOKLIST_OT39, BOOKLIST_NT27, BOOKLIST_66
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
from BibleOrgSys.OriginalLanguages import Hebrew, Greek
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.USXXMLBible as USXXMLBible
import BibleOrgSys.Formats.ZefaniaXMLBible as ZefaniaXMLBible
import BibleOrgSys.Formats.CSVBible as CSVBible
import BibleOrgSys.Formats.LEBXMLBible as LEBXMLBible
import BibleOrgSys.Formats.VPLBible as VPLBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Reference.OldBiblicalEnglish import moderniseEnglishWords


LAST_MODIFIED_DATE = '2025-03-22' # by RJH
SHORT_PROGRAM_NAME = "EvaluateBibleLiteralness"
PROGRAM_NAME = "Check literalness of English Bible translations vs Hebrew & Greek"
PROGRAM_VERSION = '0.14'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'


DEBUGGING_THIS_MODULE = False



class State:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    EnglishTranslations = ['OET-LV','OET-RV', 'ULT','UST', 'BLB','BSB', 'OEB', 'NET', 'LSV', 'WEBBE', 'LEB',
                                'CSB','NLT','NIV','CEV','ESV','NASB','LSB','JQT','2DT','1ST','TPT','MSG','NRSV','NKJV','NAB', # Selected verses only versions
                                'ASV','YLT','RV',
                                'KJB-1769', # Compulsory if we include selected-verses-only versions
                                'Bshps','Gnva','Cvdl','TNT','Wycl',
                            ]
    referenceVersionAbbreviation = 'KJB-1769' # For getting the number of chapters and verses if we don't know
    OTOnlyTranslations = ['1ST']
    NTOnlyTranslations = ['BLB','2DT']

    OET_base_filepath = Path( '/srv/FreelyGiven/OpenEnglishTranslation--OET/' )
    NT_word_filepath = OET_base_filepath.joinpath( 'translatedTexts/ReadersVersion/OET-LV_NT_word_table.tsv' )

    preloadedBibles = {}
    GreekRows = HebrewRows = None
    likelyGreekGlosses = likelyHebrewGlosses = None

    foundGlosses, versionResults = {}, {}

    selectedVersesOnlyVersions = ('CSB','NLT','NIV','CEV','ESV','MSG','NASB','LSB','JQT','2DT','1ST','TPT','NRSV','NKJV','NAB', 'NETS' ) # These ones have .tsv sources (and don't produce Bible objects)
    BibleLocations = {
        'OET-RV': '../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',
        'OET-LV': '../../OpenEnglishTranslation--OET/intermediateTexts/', # Only .pickle here
        'OET-LV-OT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_OT_ESFM/', # No NT here
        'OET-LV-NT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_ESFM/', # No OT here
        'SR-GNT': '../../Forked/CNTR-SR/SR usfm/', # We moved these up in the list because they're now compulsory
        'UHB': '../../OpenBibleData/copiedBibles/Original/unfoldingWord.org/UHB/',
        # NOTE: The program will still run if some of these below are commented out or removed
        # (e.g., this can be done quickly for a faster test run)
        'ULT': '../../OpenBibleData/copiedBibles/English/unfoldingWord.org/ULT/',
        'UST': '../../OpenBibleData/copiedBibles/English/unfoldingWord.org/UST/',
        'BSB': '../../OpenBibleData/copiedBibles/English/Berean.Bible/BSB/',
        'BLB': '../../OpenBibleData/copiedBibles/English/Berean.Bible/BLB/blb.modified.txt', # NT only so far
        # However, if they're all commented out, 'assert doneHideablesDiv' will fail in createParallelVersePages.py if not in test mode
        'AICNT': '../../OpenBibleData/copiedBibles/English/AICNT/', # NT only
        'OEB': '../../OpenBibleData/copiedBibles/English/OEB/',
        # 'ISV': '',
        'CSB': '../../OpenBibleData/copiedBibles/English/CSB_verses.tsv',
        'NLT': '../../OpenBibleData/copiedBibles/English/NLT_verses.tsv',
        'NIV': '../../OpenBibleData/copiedBibles/English/NIV_verses.tsv',
        'CEV': '../../OpenBibleData/copiedBibles/English/CEV_verses.tsv',
        'ESV': '../../OpenBibleData/copiedBibles/English/ESV_verses.tsv',
        'NASB': '../../OpenBibleData/copiedBibles/English/NASB_verses.tsv',
        'LSB': '../../OpenBibleData/copiedBibles/English/LSB_verses.tsv',
        'JQT': '../../OpenBibleData/copiedBibles/English/JQT_verses.tsv',
        '2DT': '../../OpenBibleData/copiedBibles/English/2DT_verses.tsv',
        '1ST': '../../OpenBibleData/copiedBibles/English/1ST_verses.tsv',
        'TPT': '../../OpenBibleData/copiedBibles/English/TPT_verses.tsv',
        'WEBBE': '../../OpenBibleData/copiedBibles/English/eBible.org/WEBBE/', # British spelling
        # 'WEB': '../../OpenBibleData/copiedBibles/English/eBible.org/WEB/', # USA spelling
        'WMBB': '../../OpenBibleData/copiedBibles/English/eBible.org/WMBB/', # British spelling
        # 'WMB': '../../OpenBibleData/copiedBibles/English/eBible.org/WMB/', #USA spelling
        'MSG': '../../OpenBibleData/copiedBibles/English/MSG_verses.tsv',
        'NET': '../../OpenBibleData/copiedBibles/English/eBible.org/NET/',
        # 'NET': '../../OpenBibleData/copiedBibles/English/NET/'
        'LSV': '../../OpenBibleData/copiedBibles/English/eBible.org/LSV/',
        'FBV': '../../OpenBibleData/copiedBibles/English/eBible.org/FBV/',
        'TCNT': '../../OpenBibleData/copiedBibles/English/eBible.org/TCNT/',
        'T4T': '../../OpenBibleData/copiedBibles/English/eBible.org/T4T/',
        'LEB': '../../OpenBibleData/copiedBibles/English/LogosBibleSoftware/LEB/LEB.xml', # not OSIS
        'NRSV': '../../OpenBibleData/copiedBibles/English/NRSV_verses.tsv',
        'NKJV': '../../OpenBibleData/copiedBibles/English/NKJV_verses.tsv',
        'NAB': '../../OpenBibleData/copiedBibles/English/NAB_verses.tsv',
        'BBE': '../../OpenBibleData/copiedBibles/English/eBible.org/BBE/',
        'Moff': '../../OpenBibleData/copiedBibles/English/Moffat/',
        'JPS': '../../OpenBibleData/copiedBibles/English/eBible.org/JPS/',
        'Wymth': '../Bibles/English/Weymouth_NT-1903/',
        'ASV': '../../OpenBibleData/copiedBibles/English/eBible.org/ASV/',
        'DRA': '../../OpenBibleData/copiedBibles/English/eBible.org/DRA/',
        'YLT': '../../OpenBibleData/copiedBibles/English/eBible.org/YLT/',
        'Drby': '../../OpenBibleData/copiedBibles/English/eBible.org/DBY/',
        'RV': '../../OpenBibleData/copiedBibles/English/eBible.org/RV/', # with deuterocanon
        'Wbstr': '../../OpenBibleData/copiedBibles/English/eBible.org/WBS/',
        'KJB-1769': '../../OpenBibleData/copiedBibles/English/eBible.org/KJB/', # with deuterocanon -- ALWAYS NEEDED if KJB-1611 and some others are included
        'KJB-1611': '../Bibles/English/KJB-1611/', # with deuterocanon
        'Bshps': '../../OpenBibleData/copiedBibles/English/BibleSuperSearch/BB/bishops.txt',
        'Gnva': '../../OpenBibleData/copiedBibles/English/eBible.org/GNV/',
        'Cvdl': '../../OpenBibleData/copiedBibles/English/BibleSuperSearch/CB/coverdale.txt',
        'TNT': '../../OpenBibleData/copiedBibles/English/eBible.org/TNT/',
        'Wycl': '../../OpenBibleData/copiedBibles/English/Zefania/WYC/SF_2009-01-20_ENG_BIBLE_WYCLIFFE_(JOHN WYCLIFFE BIBLE).xml',
        'UGNT': '../../OpenBibleData/copiedBibles/Original/unfoldingWord.org/UGNT/',
        'SBL-GNT': '../../Forked/SBLGNT/data/sblgnt/text/',
        'TC-GNT': '../../OpenBibleData/copiedBibles/Greek/eBible.org/TC-GNT/',
        'NETS': '../../OpenBibleData/copiedBibles/English/NETS_verses.tsv',
        'BrTr': '../../OpenBibleData/copiedBibles/English/eBible.org/Brenton/', # with deuterocanon and OTH,XXA,XXB,XXC,
        'BrLXX': '../../OpenBibleData/copiedBibles/Greek/eBible.org/BrLXX/',
        }
    BibleNames = {
        'OET': 'Open English Translation (2030)',
        'OET-RV': 'Open English Translation—Readers’ Version (2030)',
        'OET-LV': 'Open English Translation—Literal Version (2025)',
        'ULT': 'unfoldingWord® Literal Text (2023)',
        'UST': 'unfoldingWord® Simplified Text (2023)',
        'BSB': 'Berean Study/Standard Bible (2020)',
        'BLB': 'Berean Literal Bible NT (2022)',
        'AICNT': 'AI Critical NT (2023)',
        'OEB': 'Open English Bible (in progress)',
        'ISV': 'International Standard Version (2020?)',
        'CSB': 'Christian Standard Bible (2017)',
        'NLT': 'New Living Translation (2015)',
        'NIV': 'New International Version (2011)',
        'CEV': 'Contemporary English Version (2006)',
        'ESV': 'English Standard Version (2001)',
        'NASB': 'New American Standard Bible (1995)',
        'LSB': 'Legacy Standard Bible (2021)',
        'JQT': 'James Quiggle Translation New Testament (2023)',
        '2DT': 'The Second Testament (2023)',
        '1ST': 'The First Testament (2018)',
        'TPT': 'The Passion Translation (2017)',
        'WEBBE': 'World English Bible (2023) British Edition',
        'WEB': 'World English Bible (2023)',
        'WMBB': 'World Messianic Bible (2023) British Edition / Hebrew Names Version (HNV)',
        'WMB': 'World Messianic Bible (2023) / Hebrew Names Version (HNV)',
        'MSG': 'The Message (2018)',
        'NET': 'New English Translation (2016)',
        'LSV': 'Literal Standard Version (2020)',
        'FBV': 'Free Bible Version (2018)',
        'TCNT': 'Text-Critical New Testament (2022, Byzantine)',
        'T4T': 'Translation for Translators (2017)',
        'LEB': 'Lexham English Bible (2010, 2012)',
        'NRSV': 'New Revised Standard Version (1989)',
        'NKJV': 'New King James Version (1982)',
        'NAB': 'New American Bible (1970, revised 2010)',
        'BBE': 'Bible in Basic English (1965)',
        'Moff': 'The Moffatt Translation of the Bible (1922)',
        'JPS': 'Jewish Publication Society TaNaKH (1917)',
        'Wymth': 'Weymouth New Testament (1903)',
        'ASV': 'American Standard Version (1901)',
        'DRA': 'Douay-Rheims American Edition (1899)',
        'YLT': 'Youngs Literal Translation (1898)',
        'Drby': 'Darby Translation (1890)',
        'RV': 'English Revised Version (1885)',
        'Wbstr': 'Webster Bible (American, 1833)',
        'KJB-1769': 'King James Bible (1769)',
        'KJB-1611': 'King James Bible (1611)',
        'Bshps': 'Bishops Bible (1568, 1602)',
        'Gnva': 'Geneva Bible (1557-1560, 1599)',
        'Great': 'Great Bible (1539)', # Not in OBD yet
        'Cvdl': 'Coverdale Bible (1535-1553)',
        'TNT': 'Tyndale New Testament (1526)',
        'Wycl': 'Wycliffe Bible (middle-English, 1382)',
        'Luth': 'Luther Bible (German, 1545)',
        'ClVg': 'Clementine Vulgate (Latin, 1592)',
        'SR-GNT': 'Statistical Restoration Greek New Testament (2022)',
        'UGNT': 'unfoldingWord® Greek New Testament (2022)',
        'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2010)',
        'TC-GNT': 'Text-Critical Greek New Testament (2010, Byzantine)',
        'NETS': 'New English Translation of the Septuagint (2009,2014)',
        'BrTr': 'Brenton Septuagint Translation (1851)',
        'BrLXX': '(Brenton’s) Ancient Greek translation of the Hebrew Scriptures (~250 BC)',
        'UHB': 'unfoldingWord® Hebrew Bible (2022)',
        'TOSN': 'Tyndale Open Study Notes (2022)',
        'TOBD': 'Tyndale Open Bible Dictionary (2023)',
        'UTN': 'unfoldingWord® Translation Notes (2023)',
        'UBS': 'United Bible Societies open-licenced resources (2023)',
        'THBD': 'Theographic Bible Database',
        'BMM': 'BibleMapper.com Maps',
        }
# end of EvaluateBibleLiteralness.State class


def main() -> None:
    """
    This is the main program for the app
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    state = State()
    if loadHebrewData( state ) and loadGreekData( state ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nHebrew and Greek resources loaded.\n" )
        for EnglishTranslationAbbreviation in state.EnglishTranslations:
            if not loadBible( EnglishTranslationAbbreviation, state ):
                bible_not_loaded
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n{len(state.EnglishTranslations)} English translations loaded.\n" )

        state.referenceBible = state.preloadedBibles[state.referenceVersionAbbreviation]
        for EnglishTranslationAbbreviation in state.EnglishTranslations:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nProcessing {EnglishTranslationAbbreviation}…" )
            state.foundGlosses[EnglishTranslationAbbreviation], state.versionResults[EnglishTranslationAbbreviation] = {}, {}
            if EnglishTranslationAbbreviation not in state.NTOnlyTranslations:
                checkOT( EnglishTranslationAbbreviation, state )
            if EnglishTranslationAbbreviation not in state.OTOnlyTranslations:
                checkNT( EnglishTranslationAbbreviation, state )
            publishResult( EnglishTranslationAbbreviation, state )
        publishSummary( state )
# end of EvaluateBibleLiteralness.main


def loadHebrewData( state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, "loadHebrewData()" )

    loadBible( 'UHB', state )

    return True
# end of EvaluateBibleLiteralness.loadHebrewData()


NUM_EXPECTED_GREEK_COLUMNS = 12
def loadGreekData( state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadGreekData() from {state.NT_word_filepath}" )

    if 'ULT' in state.EnglishTranslations or 'UST' in state.EnglishTranslations:
        loadBible( 'UGNT', state )

    if 'OET-LV' in state.EnglishTranslations or 'OET-RV' in state.EnglishTranslations:
        loadBible( 'SR-GNT', state )

        # Now load the Greek word file
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading SR-GNT Greek word file from {state.NT_word_filepath}…" )
        with open( state.NT_word_filepath, 'rt', encoding='utf-8' ) as tsv_file:
            tsv_lines = tsv_file.readlines()

        # Remove any BOM
        if tsv_lines[0].startswith("\ufeff"):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Handling Byte Order Marker (BOM) at start of Greek tsv file…")
            tsv_lines[0] = tsv_lines[0][1:]

        # Get the headers before we start
        Greek_tsv_header_line = tsv_lines[0].strip()
        assert Greek_tsv_header_line == 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags', f"{Greek_tsv_header_line=}"
        Greek_tsv_column_headers = [header for header in Greek_tsv_header_line.split('\t')]
        dPrint('Info', DEBUGGING_THIS_MODULE, f"Column headers: ({len(Greek_tsv_column_headers)}): {Greek_tsv_column_headers}")
        assert len(Greek_tsv_column_headers) == NUM_EXPECTED_GREEK_COLUMNS


        # Read, check the number of columns, and summarise row contents all in one go
        state.GreekRows = []
        likelyGreekGlosses = defaultdict( set )
        for n, row in enumerate( DictReader(tsv_lines, delimiter='\t') ):
            if len(row) != NUM_EXPECTED_GREEK_COLUMNS:
                logging.error(f"Line {n} has {len(row)} columns instead of {NUM_EXPECTED_GREEK_COLUMNS}!!!")
            state.GreekRows.append( row )
            greekWord, vltGloss, oetGloss = row['GreekWord'], row['VLTGlossWords'], row['OETGlossWords']
            # vltGloss = ( vltGloss
            #             .replace('˱','').replace('˲','') # gloss pre
            #             .replace('˓','').replace('˒','') # gloss helper
            #             .replace('‹','').replace('›','') # gloss post (some of these aren't fantastic, e.g., 'ἡ' -> 'the_woman' or 'the_mother')
            #             .replace('¬','') # untranslated
            #             .replace(' ','_') )
            # # print( f"  {greekWord=} {vltGloss=}" )
            # for vltSubgloss in vltGloss.split( '/' ): # get all alternatives (or just the entire gloss if no alternatives separated by /)
            #     state.likelyGreekGlosses[greekWord].add( vltSubgloss )
            # if oetGloss != vltGloss:
            if '/(' in oetGloss and oetGloss[-1]==')': # used for names with Heb/Grk forms
                partWithFirstName = ( oetGloss.split('/(')[0]
                        .replace('¬/anxiety/','¬anxiety') # Why? LUK_18:8w17
                        .replace('˱','').replace('˲','') # gloss pre
                        .replace('˓','').replace('˒','') # gloss helper
                        .replace('‹','').replace('›','') # gloss post
                        .replace('¬','') # untranslated
                        .replace(' ','_') )
                assert ' ' not in partWithFirstName, f"{n} {greekWord} {partWithFirstName=} {vltGloss=} {oetGloss=}"
                # print( f"{firstName}" ); assert False, "We want to stop here"
                # for oetSubgloss in firstName.split( '_' ):
                #     assert oetSubgloss, f"{n} {greekWord} {vltGloss=} {oetGloss=}"
                #     likelyGreekGlosses[greekWord].add( oetSubgloss[1:-1] if oetSubgloss[0]=='(' and oetSubgloss[-1]==')' else oetSubgloss )
                likelyGreekGlosses[greekWord].add( partWithFirstName ) # Add the first word(s) by itself
                oetGloss = oetGloss[:-1].replace('/(','_') # So can also split into two words below
            oetGloss = ( oetGloss
                        .replace('\\sup ','').replace('\\sup*','') # We superscript yah and el in names (in the second part)
                        .replace('¬/anxiety/','¬anxiety') # Why? LUK_18:8w17
                        .replace('˱','').replace('˲','') # gloss pre
                        .replace('˓','').replace('˒','') # gloss helper
                        .replace('‹','').replace('›','') # gloss post
                        .replace('¬','') # untranslated
                        .replace(' ','_') )
            # print( f"  {greekWord=} {oetGloss=}" )
            if '/' in oetGloss:
                # assert '_' not in oetGloss, f"{n} {greekWord} {oetGloss=}" # How can we make this work: 3 Χριστοῦ oetGloss='chosen_one/messiah
                likelyGreekGlosses[greekWord].add( oetGloss.replace( '/', '_' ) )
                for oetSubgloss in oetGloss.split( '/' ):
                    assert oetSubgloss, f"{n} {greekWord} {vltGloss=} {oetGloss=}"
                    likelyGreekGlosses[greekWord].add( oetSubgloss[1:-1] if oetSubgloss[0]=='(' and oetSubgloss[-1]==')' else oetSubgloss )
            else: # no / alternatives
                likelyGreekGlosses[greekWord].add( oetGloss[1:-1] if oetGloss[0]=='(' and oetGloss[-1]==')' else oetGloss )
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    likelyGreekGlosses[{greekWord}] = {likelyGreekGlosses[greekWord]}" )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded {len(state.GreekRows):,} data rows from {state.NT_word_filepath}." )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded glosses for {len(likelyGreekGlosses):,} Greek words." )

        # Now tidy-up those glosses -- we split multiple words like 'to_cry' and put into a list, with the longest first
        state.likelyGreekGlosses = {}
        for grkWrd, glossSet in likelyGreekGlosses.items():
            glossList = []
            for wordOrWords in glossSet:
                assert wordOrWords
                assert isinstance( wordOrWords, str )
                # print( f"{grkWrd} {wordOrWords} from {glossSet}")
                if '_' in wordOrWords: # Make this into a sub-list
                    wordOrWordsList = wordOrWords.split( '_' )
                    glossList.append( wordOrWordsList )
                    if wordOrWordsList[0] == 'of': # special case for genitive -- we also remove the 'of'
                        if len(wordOrWordsList) == 2:
                            glossList.append( wordOrWordsList[1] ) # str
                        else: # 2 or more words after the 'of'
                            glossList.append( wordOrWordsList[1:] ) # list
                else:
                    glossList.append( wordOrWords )
            # Sort so longest sublists are first, then longest single words, finishing with the shortest single word
            state.likelyGreekGlosses[grkWrd] = sorted( glossList, key = lambda x: 100+len(x) if isinstance(x,list) else len(x), reverse=True )
            # print( f"\n{grkWrd} {state.likelyGreekGlosses[grkWrd]} from {glossSet}")
            # if len(state.likelyGreekGlosses[grkWrd])> 5: assert False, "We want to stop here"
    return True
# end of EvaluateBibleLiteralness.loadGreekData()


PICKLE_FILENAME_END = '.OBD_Bible.pickle'
def loadBible( versionAbbreviation:str, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadBible( {versionAbbreviation} )" )

    # See if a pickled version is available for a MUCH faster load time
    folderOrFileLocationPath = Path( state.BibleLocations[versionAbbreviation] )
    pickleFilename = f'{versionAbbreviation}{PICKLE_FILENAME_END}'
    pickleFolderPath = folderOrFileLocationPath if folderOrFileLocationPath.is_dir() else folderOrFileLocationPath.parent
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLooking for a pickle for ‘{versionAbbreviation}’{f' in {pickleFolderPath}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}…" )
    pickleFilePath = pickleFolderPath.joinpath( pickleFilename )
    dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{folderOrFileLocationPath=} {pickleFilename=} {pickleFolderPath=} {pickleFilePath=}" )
    if pickleFilePath.is_file():
        pickleIsObsolete = False
        pickleMTime = pickleFilePath.stat().st_mtime # A large integer
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"preloadVersions found {pickleFilename=}" )
        for somePath in pickleFolderPath.iterdir():
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Checking file-times in {pickleFolderPath=} {somePath=} {type(somePath)=}" )
            if somePath.is_file() and not str(somePath).endswith( PICKLE_FILENAME_END ):
                fileMTime = somePath.stat().st_mtime # A large integer
                if fileMTime > pickleMTime:
                    pickleIsObsolete = True
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} pickle is obsolete because {somePath.name} is more recent." )
                    break
            elif versionAbbreviation == 'OET-LV': # This one has the OT and the NT in separate folders
                if str(somePath).endswith ('intermediateTexts/auto_edited_OT_ESFM') or str(somePath).endswith ('intermediateTexts/auto_edited_VLT_ESFM'):
                    for someSubPath in somePath.iterdir():
                        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Checking file-times in {somePath=} {someSubPath=} {type(someSubPath)=}" )
                        if someSubPath.is_file() and not str(someSubPath).endswith( PICKLE_FILENAME_END ):
                            fileMTime = someSubPath.stat().st_mtime # A large integer
                            if fileMTime > pickleMTime:
                                pickleIsObsolete = True
                                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} pickle is obsolete because {someSubPath.name} is more recent." )
                                break
            else:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Ignoring pickle file or folder {somePath=} {somePath.name=}")
        if not pickleIsObsolete:
            try:
                newBibleObj = BibleOrgSysGlobals.unpickleObject( pickleFilename, pickleFolderPath )
                # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"newObj is {newBibleObj}" )
                # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loaded {versionAbbreviation} {type(newBibleObj)} pickle file: {pickleFilename}." )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"preloadVersions() loaded pickled {newBibleObj if BibleOrgSysGlobals.verbosityLevel>=2 else versionAbbreviation}" )
                assert 'discoveryResults' in newBibleObj.__dict__ # .discover() should have been called before it was saved
                state.preloadedBibles[versionAbbreviation] = newBibleObj
                return True
            except EOFError:
                logging.critical( f"Failed to load {versionAbbreviation} pickle file: Ran out of input from {pickleFilename} in {pickleFolderPath}")
    else:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  No pickle file for {versionAbbreviation}." )

    if versionAbbreviation == 'OET-LV':
        # Load the OT and NT from separate folders, and then combine them into one ESFM Bible object
        thisBibleOT = preloadVersion( versionAbbreviation, state.BibleLocations['OET-LV-OT'], state )
        assert isinstance( thisBibleOT, ESFMBible.ESFMBible )
        thisBibleNT = preloadVersion( versionAbbreviation, state.BibleLocations['OET-LV-NT'], state )
        assert isinstance( thisBibleNT, ESFMBible.ESFMBible )
        # print( f"{len(thisBibleOT)=} {len(thisBibleNT)=}" )
        thisBible = thisBibleOT
        for bookObject in thisBibleNT:
            # print( type(bookObject), bookObject.BBB )
            assert bookObject.BBB not in thisBible.books
            thisBible.books[bookObject.BBB] = bookObject
        # print( f"{len(thisBibleOT)=}" )
        # print( f"{len(thisBibleOT.ESFMWordTables)=}" )
        for wordTableID,wordTable in thisBibleNT.ESFMWordTables.items():
            # print( f"{wordTableID=} {type(wordTable)=}")
            thisBible.ESFMWordTables[wordTableID] = wordTable
        # print( f"{len(thisBible.ESFMWordTables)=}" )
        # For now, use add custom OT and NT sourceFolder variables so that we can load the two different word files
        thisBible.OTsourceFolder = thisBibleOT.sourceFolder
        thisBible.NTsourceFolder = thisBibleNT.sourceFolder
        thisBible.sourceFolder = None
        state.preloadedBibles['OET-LV'] = thisBible
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nDoing discovery for {thisBible.abbreviation} ({thisBible.name})…" )
        thisBible.discover()
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"preloadVersions() loaded {thisBible}" )

        pickleFilename = f"{versionAbbreviation}{PICKLE_FILENAME_END}"
        pickleFolderPath = state.BibleLocations['OET-LV']
        thisBible.pickle( pickleFilename, pickleFolderPath )

    else: # Everything other than OET-LV
        thisBible = preloadVersion( versionAbbreviation, state.BibleLocations[versionAbbreviation], state )
        if isinstance(thisBible, Bible) \
        or versionAbbreviation in state.selectedVersesOnlyVersions:
            state.preloadedBibles[versionAbbreviation] = thisBible
        else:
            assert False, "We want to stop here" # preloadVersion failed

    return True
# end of EvaluateBibleLiteralness.loadEnglishTranslation()


def preloadVersion( versionAbbreviation:str, folderOrFileLocation:str, state:State ) -> Bible:
    """
    Loads the requested Bible into memory
        and return the Bible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( ‘{versionAbbreviation}’, '{folderOrFileLocation}', … )" )
    versionName = state.BibleNames[versionAbbreviation]

    # if versionAbbreviation in ('BSB',): # Single TSV .txt file
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} CSV/TSV Bible…" )
    #     thisBible = CSVBible.CSVBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='iso-8859-1' )
    #     thisBible.load()
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    if versionAbbreviation in ('BLB','SBL-GNT'): # Single (BLB) or multiple (SBL-GNT) TSV .txt file(s)
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ CSV/TSV Bible…" )
        thisBible = CSVBible.CSVBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MRK', '10', '45') )
        # print( f"Mrk 10:45 {verseEntryList=} {contextList=}" )
    # elif versionAbbreviation in ('SBL-GNT',): # .txt file(s)
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} VPL Bible…" )
    #     thisBible = VPLBible.VPLBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='utf-8' )
    #     thisBible.loadBooks() # So we can iterate through them all later
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    elif versionAbbreviation == 'LEB': # Custom XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ XML Bible…" )
        thisBible = LEBXMLBible.LEBXMLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif versionAbbreviation in ('Cvdl','Bshps'): # Custom VPL
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ VPL Bible…" )
        thisBible = VPLBible.VPLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.load() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MRK', '1', '1') )
        # print( f"Mrk 1:1 {verseEntryList=} {contextList=}" )
    elif 'Zefania' in folderOrFileLocation: # Zefania XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ Zefania XML Bible…" )
        thisBible = ZefaniaXMLBible.ZefaniaXMLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{versionAbbreviation} {thisBible.suppliedMetadata=}" )
        # print( f"{versionAbbreviation} {thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"{versionAbbreviation} Mat 2:1 {verseEntryList=} {contextList=}" )
        # if versionAbbreviation=='Luth': assert False, "We want to stop here"
    elif 'OET' in versionAbbreviation or 'ESFM' in folderOrFileLocation: # ESFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ ESFM Bible…" )
        thisBible = ESFMBible.ESFMBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation )
        thisBible.loadAuxiliaryFiles = True
        # if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
        #     thisBible.uWencoded = True # TODO: Shouldn't be required ???
        thisBible.loadBooks() # So we can iterate through them all later
    elif versionAbbreviation in state.selectedVersesOnlyVersions: # small numbers of sample verses
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ sample verses…" )
        thisBible = loadSelectedVersesFile( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        # NOTE: thisBible is NOT a Bible object here!!!
        # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
    elif versionAbbreviation in ('NET',) and 'eBible.org' not in folderOrFileLocation: # USX
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ USX Bible…" )
        thisBible = USXXMLBible.USXXMLBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if state.booksToLoad[versionAbbreviation] in (['ALL'],['OT'],['NT']):
            # We assume that we can load all books, even for OT and NT
            #  i.e., we assume (but don't check) that only those books will exist (plus maybe intro, etc.)
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
    else: # USFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ USFM Bible…" )
        thisBible = USFMBible.USFMBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
            thisBible.uWencoded = True # TODO: Shouldn't be required ???
        thisBible.loadBooks() # So we can iterate through them all later
        # else: # only load the specific books as we need them
        #     thisBible.preload()
        #     for BBB in state.booksToLoad[versionAbbreviation]:
        #         thisBible.loadBookIfNecessary( BBB )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  preloadVersion() loaded {len(thisBible):,} {versionAbbreviation} verses" if versionAbbreviation in state.selectedVersesOnlyVersions else f"preloadVersion() loaded {thisBible}" )

    if ( versionAbbreviation not in state.selectedVersesOnlyVersions
    #and 'Zefania' not in folderOrFileLocation # TODO: these don't work for some reason
    and versionAbbreviation != 'OET-LV' # This one is handled by the calling function because it's more complex (uses two folders)
    and versionAbbreviation != 'TOSN' # This one has different complexities coz it loads various other bits
    ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nDoing discovery for {thisBible.abbreviation} ({thisBible.name})…" )
        thisBible.discover()

        pickleFilename = f"{versionAbbreviation}{PICKLE_FILENAME_END}"
        pickleFolderPath = folderOrFileLocation if os.path.isdir( folderOrFileLocation ) else Path( folderOrFileLocation ).parent
        thisBible.pickle( pickleFilename, pickleFolderPath )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Saved pickle file: {pickleFilename}." )

    return thisBible
# end of Bibles.preloadVersion


def loadSelectedVersesFile( fileLocation, givenName:str, givenAbbreviation:str, encoding='utf-8' ) -> Bible:
    """
    These are loaded from simple two-column TSV files
        with reference and verse text.

    Usually they only contain some small number of verses, e.g., 200 - 500 (cf NT. = 8,000, Bible = 31,000)
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadSelectedVersesFile( {fileLocation}, {givenName}, {givenAbbreviation}, {encoding} )" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadSelectedVersesFile() loading {givenAbbreviation} ({givenName}) verse entries from {fileLocation}…" )
    # assert givenAbbreviation in state.selectedVersesOnlyVersions

    verseTable = {}
    with open ( fileLocation, 'rt', encoding=encoding ) as tsv_file:
        for j,line in enumerate( tsv_file ):
            line = line.rstrip( '\n' )
            # print( f"{j}: {line}" )
            if j == 0:
                assert line == 'Reference\tVerseText'
            else:
                ref,verseText = line.split( '\t' )
                assert ref.strip() == ref
                assert verseText.strip() == verseText, f"Unexpected leading or trailing space in {givenAbbreviation} {j} {ref=} '{verseText[:6]}…{verseText[-6:]}'"
                BBB, CV = ref.split( '_' )
                C, V = CV.split( ':' )
                ourRef = (BBB,C,V)
                assert ourRef not in verseTable
                assert verseText
                # TODO: How should this really work (distinguish \\n from \\nd)???
                verseTable[ourRef] = ( verseText.replace('\\\\nd','__ND__')
                                        .replace('\\n','\n').replace('\\\\','\\') # See https://en.wikipedia.org/wiki/Tab-separated_values
                                        .replace('__ND__','\\nd') )

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    loadSelectedVersesFile() loaded {len(verseTable):,} {givenAbbreviation} verse entries from {fileLocation}." )
    return verseTable
# end of Bibles.loadSelectedVersesFile


def checkOT( EnglishVersionAbbreviation:str, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"checkOT( {EnglishVersionAbbreviation} )" )

    HebrewVersionAbbreviation = 'UHB'

    referenceBible = state.referenceBible if EnglishVersionAbbreviation in state.selectedVersesOnlyVersions else state.preloadedBibles[EnglishVersionAbbreviation]
    for BBB in BOOKLIST_OT39:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Processing {EnglishVersionAbbreviation} {BBB}…" )

        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        if numChapters is None: return False

        for c in range( 1, numChapters+1 ):
            C = str( c )
            numVerses = referenceBible.getNumVerses( BBB, C )
            if numVerses is None: # something unusual
                logging.error( f"checkOT: no verses found for {BBB} {C}" )
                assert False, "We want to stop here"
                continue
            for v in range( 1, numVerses+1 ):
                V = str( v )
                verseResult = checkOTVerse( HebrewVersionAbbreviation, EnglishVersionAbbreviation, BBB, C, V, state )
                state.versionResults[EnglishVersionAbbreviation][f'{BBB}_{C}:{V}'] = verseResult

    return True
# end of EvaluateBibleLiteralness.checkOT function


def checkNT( EnglishVersionAbbreviation:str, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"checkNT( {EnglishVersionAbbreviation} )" )

    GreekVersionAbbreviation = 'UGNT' if EnglishVersionAbbreviation=='ULT' else 'SR-GNT'

    referenceBible = state.referenceBible if EnglishVersionAbbreviation in state.selectedVersesOnlyVersions else state.preloadedBibles[EnglishVersionAbbreviation]
    for BBB in BOOKLIST_NT27:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Processing {EnglishVersionAbbreviation} {BBB}…" )

        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        for c in range( 1, numChapters+1 ):
            C = str( c )
            numVerses = referenceBible.getNumVerses( BBB, C )
            if numVerses is None: # something unusual
                logging.error( f"checkNT: no verses found for {BBB} {C}" )
                assert False, "We want to stop here"
                continue
            for v in range( 1, numVerses+1 ):
                V = str( v )
                verseResult = checkNTVerse( GreekVersionAbbreviation, EnglishVersionAbbreviation, BBB, C, V, state )
                if verseResult is not None:
                    state.versionResults[EnglishVersionAbbreviation][f'{BBB}_{C}:{V}'] = verseResult

    return True
# end of EvaluateBibleLiteralness.checkNT()


OET_LV_NT_MAJOR_TERM_LISTS = (
    (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Yaʸsous','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
        ['master','Master','Masters'], ['Sir','sir','lord','Lord','mastering']),
    (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι', 'Μεσσίας','Μεσσίαν'],['messiah','messiahs'],['Christian']),
    # (['Καὶ','καὶ'],['And'],[]),
    )
OET_RV_NT_MAJOR_TERM_LISTS = (
    (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Yeshua','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
        ['master','Master','Masters'], ['Sir','sir','lord','Lord','mastering']),
    (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι' 'Μεσσίας','Μεσσίαν'],['messiah','messiahs'],['Christian']),
    # (['Καὶ','καὶ'],['And'],[]),
    )
NON_OET_NT_MAJOR_TERM_LISTS = (
    (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Jesus','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
        ['lord','Lord','Lords'], ['Sir','sir','master','Master','lording']),
    (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι'],['Christ','Christs'],['Christian']),
    # (['Καὶ','καὶ'],['And'],[]),
    )
def checkNTVerse( GreekVersionAbbreviation:str, EnglishVersionAbbreviation:str, BBB:str, C:str, V:str, state:State ) -> float|None:
    """
    """
    refStr, refKey = f'{BBB}_{C}:{V}', SimpleVerseKey( BBB, C, V )
    fnPrint( DEBUGGING_THIS_MODULE, f"checkNTVerse( {GreekVersionAbbreviation}, {EnglishVersionAbbreviation}, {refStr} )" )

    GreekReferenceBible, EnglishBible = state.preloadedBibles[GreekVersionAbbreviation], state.preloadedBibles[EnglishVersionAbbreviation]
    GreekVerseDictionaryRows = []
    if GreekVersionAbbreviation == 'SR-GNT':
        for row in state.GreekRows:
            if row['Ref'].startswith( f'{refStr}w' ):
                GreekVerseDictionaryRows.append( row )
            elif GreekVerseDictionaryRows:
                break # Stop once we've finished all that verse
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{refStr} has {len(GreekVerseDictionaryRows)} dict rows" )

    try:
        grkVrsTxt = GreekReferenceBible.getVerseText( refKey, fullTextFlag=False, includeNonCanonical=False )
        if not grkVrsTxt:
            logging.error( f"Blank text at {refKey.getShortText()} in {GreekVersionAbbreviation}" )
    except KeyError:
        logging.error( f"Can't find {refKey.getShortText()} in {GreekVersionAbbreviation}" )
        grkVrsTxt = ''
    if EnglishVersionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
        try:
            engVrsTxt = EnglishBible[(BBB,C,V)]
            if engVrsTxt.startswith( '(' ) and engVrsTxt[1].isdigit(): # then it's probably a verse range, e.g., (21-23), esp. in MSG
                _prefix, engVrsTxt = engVrsTxt.split( ' ', 1 )
        except KeyError:
            return None
    else: # a proper Bible object
        try:
            engVrsTxt = EnglishBible.getVerseText( refKey, fullTextFlag=False, includeNonCanonical=False )
            if not engVrsTxt:
                logging.error( f"Blank text at {refKey.getShortText()} in {EnglishVersionAbbreviation}" )
            elif EnglishVersionAbbreviation in ('ASV','DRA','YLT','Drby','RV','Wbstr','KJB-1769','KJB-1611','Bshps','Gnva','Cvdl','Wycl'):
                engVrsTxt = moderniseEnglishWords( engVrsTxt, allowOptions=False )
        except KeyError:
            logging.error( f"Can't find {refKey.getShortText()} in {EnglishVersionAbbreviation}" )
            engVrsTxt = ''

    grkWordCount = grkVrsTxt.count(' ') + 1
    engWordCount = engVrsTxt.replace('—',' ').count(' ') + 1 # So things like 'he_said' is only counted as one word
    try:
        ratio = engWordCount / grkWordCount
        # if ratio < 0.95 or ratio > 1.5:
        #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"       {EnglishVersionAbbreviation} {refStr} {engWordCount}/{grkWordCount}={ratio:.2f} {grkVrsTxt=} {engVrsTxt=}" )
    except ZeroDivisionError: ratio = None
    if EnglishVersionAbbreviation == 'OET-LV':
        engWordCount2 = engVrsTxt.replace('_',' ').replace('—',' ').count(' ') + 1 # So things like 'you_all_heard' and 'it_was_said' are counted as three words
        try:
            ratio2 = engWordCount2 / grkWordCount
            # if ratio2 < 0.95 or ratio2 > 2.6:
            #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"       OET-LV individual_words {refStr} {engWordCount2}/{grkWordCount}={ratio2:.2f} {grkVrsTxt=} {engVrsTxt=}" )
        except ZeroDivisionError: ratio = None

    grkWords1 = removePunctuation( grkVrsTxt
                                .replace('θεόπνευστος','θεό πνευστος').replace('θεοδίδακτοί','θεο δίδακτοί').replace('θεοστυγεῖς','θεο στυγεῖς')
                                .replace('θεοσέβειαν','θεο σέβειαν').replace('θεοσεβὴς','θεο σεβὴς')
                                .replace('ἄθεοι','ἄ θεοι').replace('φιλόθεοι','φιλό θεοι')
                                .replace('ψευδόχριστοι','ψευδό χριστοι').replace('ἀντίχριστοι','ἀντί χριστοι')
                                ).split()
    engWords1 = removePunctuation( engVrsTxt.replace('God-','God ').replace('god-','god ')
                                        .replace('\\sup ','').replace('\\sup*','') # We superscript yah and el in names
                                        .replace('_',' ').replace('/',' ')
                                        ).split()
    grkWords, engWords = grkWords1, engWords1
    if GreekVersionAbbreviation == 'SR-GNT':
        grkWords = [removeWordNumber(GreekVersionAbbreviation, refStr, w) for w in grkWords1]
    if 'OET' in EnglishVersionAbbreviation:
        engWords = [removeWordNumber(EnglishVersionAbbreviation, refStr, w) for w in engWords1]
    # print( f"{grkVrsTxt=} ({len(grkWords1)}) {mgrkWords1=} ({len(grkWords)}) {grkWords=}" )
    # print( f"{engVrsTxt=} ({len(engWords1)}) {engWords1=} ({len(engWords)}) {engWords=}" )

    # Now that we have text1 and text2 for the verse specified in ref, do our analysis/comparison now
    verseScore = 10.0
    if not grkWords and not engWords: # it's a verse that's not in the original
        pass # use verseScore default above
    elif not grkWords or not engWords: # verse isn't included in the version
        if engWords:
            verseScore = 0.0
    else:
        alignedList = alignNTVerse( refStr, GreekVersionAbbreviation, EnglishVersionAbbreviation, grkWords, engWords, state, breakAtUnderline=True )
        assert len(alignedList) == len(grkWords)
        verseScore *= ( len(alignedList) - alignedList.count( None ) ) / len(alignedList)
        #except ZeroDivisionError: pass # on an empty list, i.e., non-existing verse
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {refStr} score 1 = {verseScore:.1f}")
    
    # Check a handful of major terms
    for origWordList,engWordList,altEngWordList in OET_LV_NT_MAJOR_TERM_LISTS if EnglishVersionAbbreviation=='OET-LV' else OET_RV_NT_MAJOR_TERM_LISTS if EnglishVersionAbbreviation=='OET-RV' else NON_OET_NT_MAJOR_TERM_LISTS:
        grkCount, engCount = checkImportantWord( refStr, GreekVersionAbbreviation, EnglishVersionAbbreviation, grkWords, engWords, origWordList, engWordList, altEngWordList )
        if grkCount < engCount:
            verseScore *= grkCount / engCount
        elif engCount < grkCount:
            verseScore *= engCount / grkCount
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {refStr} score 2 = {verseScore:.1f}\n")

    return verseScore
# end of EvaluateBibleLiteralness.checkNTVerse function


def removePunctuation( input:str ) -> str:
    """
    Including special marks
    """
    return ( input
        .replace(',','').replace('.','').replace(';','').replace(':','').replace('?','').replace('!','')
        .replace('·','')
        .replace('˓','').replace('˒','') # Gloss helper (but why's it here???)
        .replace('(','').replace(')','')
        .replace('{','').replace('}','') # ULT Heb 12:5
        .replace('[','').replace(']','') # ULT Act 8:37
        .replace('“','').replace('”','').replace('‘','').replace('’','')
        .replace('˚','') # SR-GNT nomina sacra marker
        .replace('…','')
        .replace('—',' ') # This one becomes space
        .replace('₁',' ').replace('₂',' ').replace('₃',' ').replace('₄',' ') # These are /q1,/q2 etc markers, e.g., in ULT Rev 4:11
        .replace('+','')
        .replace('¶',' ').replace('§',' ').replace('⌂',' ').replace('◊',' ') # /p, /m, /d, and /mi (Neh 13:22) become spaces
        .replace('•',' ') # List bullet (/li1) Exo 31:9, etc.
        .replace('  ',' ').replace('  ',' ') # Clean-up any doubled-spaces
        )
# end of EvaluateBibleLiteralness.removePunctuation function


def removeWordNumber( versionAbbreviation:str, refStr:str, inputWord:str ) -> str:
    """
    """
    try: ix = inputWord.index( '¦' )
    except ValueError: return inputWord
    assert inputWord[ix+1:].isdigit(), f"Should be a word number: {versionAbbreviation} {refStr} {inputWord=} {ix=}"
    return inputWord[:ix]
# end of EvaluateBibleLiteralness.removeWordNumber function


def checkImportantWord( refStr:str, GreekVersionAbbreviation:str, EnglishVersionAbbreviation:str, grkWordList:str, engWordList:str, possibleGrkWrdLst:list[str], possibleEngWrdLst:list[str], alternativeEngWrdLst:list[str] ) -> tuple[int,int]:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"checkImportantWord( {refStr}, {GreekVersionAbbreviation}, {EnglishVersionAbbreviation}, ..., {possibleGrkWrdLst}, {possibleEngWrdLst}, {alternativeEngWrdLst} )" )
    # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"checkImportantWord( {refStr}, {GreekVersionAbbreviation}, {EnglishVersionAbbreviation}, ({len(grkWordList)}) {grkWordList}, ({len(engWordList)}) {engWordList}, ({len(possibleGrkWrdLst)}) {possibleGrkWrdLst}, ({len(possibleEngWrdLst)}) {possibleEngWrdLst} )" )

    grkCount = engCount = altCount = 0
    for possibleGrkWrd in possibleGrkWrdLst:
        grkCount += grkWordList.count( possibleGrkWrd )
    for possibleEngWrd in possibleEngWrdLst:
        engCount += engWordList.count( possibleEngWrd )
    for possibleAltEngWrd in alternativeEngWrdLst:
        altCount += engWordList.count( possibleAltEngWrd )

    # for grkWord in grkWordList:
    #     for grkWordBit in grkWord.split( '/' ):
    #         grkCount += possibleGrkWrdLst.count(grkWordBit)
    #         # print( f"  Now {grkCount=} with {grkWordBit=}" )
    # for engWord in engWordList:
    #     for engWordBit in engWord.split( '/' ):
    #         engCount += possibleEngWrdLst.count(engWordBit)
    #         # print( f"  Now {engCount=} with {engWordBit=}" )

    if engCount > grkCount:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"GRK Couldn't find {engCount} {EnglishVersionAbbreviation} ‘{possibleEngWrdLst[0]}’ in {GreekVersionAbbreviation} {refStr}: {grkWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found '{possibleEngWrdLst[0]}' ({engCount}) vs ({grkCount}) in {EnglishVersionAbbreviation} {refStr}: {engWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"                              {grkWordList}" )
    # elif engCount+altCount > grkCount:
    #     vPrint( 'Info', DEBUGGING_THIS_MODULE, f"GRK With {alternativeEngWrdLst}, couldn't find {engCount} {altCount} {EnglishVersionAbbreviation} ‘{possibleEngWrdLst[0]}’ in {GreekVersionAbbreviation} {refStr}: {grkWordList}" )
    #     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found '{possibleEngWrdLst[0]}' ({engCount}) vs ({grkCount}) in {EnglishVersionAbbreviation} {refStr}: {engWordList}" )
    #     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"                              {grkWordList}" )
    elif grkCount > engCount+altCount:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{f'Even with {alternativeEngWrdLst}, c' if alternativeEngWrdLst else 'C'}ouldn't find {grkCount} ‘{possibleEngWrdLst[0]}’ in {EnglishVersionAbbreviation} {refStr}: {engWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found '{possibleEngWrdLst[0]}' ({grkCount}) vs ({engCount}) in {GreekVersionAbbreviation} {refStr}: {grkWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"                              {engWordList}" )
    elif grkCount > engCount:
        if grkCount == engCount+altCount:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"With {alternativeEngWrdLst}, found {grkCount} ‘{possibleEngWrdLst[0]}’ in {EnglishVersionAbbreviation} {refStr}: {engWordList}" )
        else:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"ENG Couldn't find {grkCount} ‘{possibleEngWrdLst[0]}’ in {EnglishVersionAbbreviation} {refStr}: {engWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found '{possibleEngWrdLst[0]}' ({grkCount}) vs ({engCount}) in {GreekVersionAbbreviation} {refStr}: {grkWordList}" )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"                              {engWordList}" )

    return grkCount, engCount
# end of EvaluateBibleLiteralness.checkImportantWord()


def alignNTVerse( refStr:str, GreekVersionAbbreviation:str, EnglishVersionAbbreviation:str, grkWordList:str, engWordList:str, state:State, breakAtUnderline:bool=False ) -> list[str|None]:
    """
    Try to match English glosses to Greek words.
    Return a list (the same length as the grkWordList) with the (zero-based) index of the matching words, i.e., a list of lists.
        It can contain None instead of a list if a Greek word can't be aligned.

    Has a side-effect of updating state.foundGlosses[EnglishVersionAbbreviation]
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"alignNTVerse( {refStr}, {GreekVersionAbbreviation}, {EnglishVersionAbbreviation}, ..., {breakAtUnderline=} )" )
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"alignNTVerse( {refStr}, {GreekVersionAbbreviation}, {EnglishVersionAbbreviation}, ({len(grkWordList)}) {grkWordList}, ({len(engWordList)}) {engWordList} {breakAtUnderline=} )" )

    alignedList = []
    unalignedEnglishWordList = engWordList.copy() # We'll replace words with None as we match them
    firstEnglishWordCaps = engWordList[0][0].isupper()
    for gg, grkWord in enumerate( grkWordList ):
        processEnglishWordCaps = grkWord[0].isupper() or ( firstEnglishWordCaps and gg == 0 )
        try: possibleEnglishGlossesList = state.likelyGreekGlosses[grkWord]
        except KeyError:
            try: possibleEnglishGlossesList = state.likelyGreekGlosses[grkWord.lower()]
            except KeyError:
                logger = logging.critical if EnglishVersionAbbreviation=='OET-LV' else logging.error
                logger( f"Why couldn't we find {grkWord=} in dict for {EnglishVersionAbbreviation} {refStr} w{gg+1} {grkWordList}" )
                possibleEnglishGlossesList = ['NONE']
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\n    {refStr} {gg} {grkWord=} {processEnglishWordCaps=} ({len(possibleEnglishGlossesList)}) {possibleEnglishGlossesList=}")
        assert possibleEnglishGlossesList
        alignedWords = []
        for possibleEnglishGlossOrGlosses in possibleEnglishGlossesList: # This can be a list or a string -- in both cases with the longest first
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      {possibleEnglishGlossOrGlosses=}")
            if isinstance( possibleEnglishGlossOrGlosses, list ):
                matchedParts = []
                for pp,possibleEnglishSubgloss in enumerate( possibleEnglishGlossOrGlosses ):
                    searchWord = possibleEnglishSubgloss.title() if processEnglishWordCaps and pp==0 else  possibleEnglishSubgloss
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {pp}/{len(possibleEnglishGlossOrGlosses)} {possibleEnglishSubgloss=} {searchWord=}" )
                    try:
                        if not matchedParts:
                            ix = unalignedEnglishWordList.index( searchWord )
                        else: # we've already started so it should be the next word
                            ix = matchedParts[-1] + 1
                            try:
                                if unalignedEnglishWordList[ix] != searchWord:
                                    raise ValueError
                            except IndexError: break # gone past end of words
                        if matchedParts and ix != matchedParts[-1]+1: # not in order
                            break
                        matchedParts.append( ix )
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"          Matched A {pp}/{len(possibleEnglishGlossOrGlosses)} {possibleEnglishSubgloss=}" )
                        # alignedWords.append( ix )
                        # removed = unalignedEnglishWordList[ix]; 
                        # unalignedEnglishWordList[ix] = None
                        # print( f"      C ALIGNED {ix} {removed=} now {unalignedEnglishWordList=}")
                    except ValueError:
                        searchWord = possibleEnglishSubgloss if processEnglishWordCaps and pp==0 else possibleEnglishSubgloss.title()
                        try:
                            if not matchedParts:
                                ix = unalignedEnglishWordList.index( searchWord )
                            else: # we've already started so it should be the next word
                                ix = matchedParts[-1] + 1
                                try:
                                    if unalignedEnglishWordList[ix] != searchWord:
                                        raise ValueError
                                except IndexError: break # gone past end of words
                            if matchedParts and ix != matchedParts[-1]+1: # not in order
                                break
                            matchedParts.append( ix )
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"          Matched B {pp}/{len(possibleEnglishGlossOrGlosses)} {possibleEnglishSubgloss=}" )
                            # alignedWords.append( ix )
                            # removed = unalignedEnglishWordList[ix]; 
                            # unalignedEnglishWordList[ix] = None
                            # print( f"      D ALIGNED {ix} {removed=} now {unalignedEnglishWordList=}")
                        except ValueError:
                            break
                if len(matchedParts) == len(possibleEnglishGlossOrGlosses):
                    for ix in matchedParts:
                        alignedWords.append( ix )
                        removed, unalignedEnglishWordList[ix] = unalignedEnglishWordList[ix], None
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"            ALIGNED MULTI_WORD {ix} {matchedParts=} now {unalignedEnglishWordList=}")
                    break # no need to try more English glosses for this Greek word
            else: # it's a string that we're trying to match
                assert isinstance( possibleEnglishGlossOrGlosses, str )
                try:
                    ix = unalignedEnglishWordList.index( possibleEnglishGlossOrGlosses.title() if processEnglishWordCaps else possibleEnglishGlossOrGlosses )
                    alignedWords.append( ix )
                    removed, unalignedEnglishWordList[ix] = unalignedEnglishWordList[ix], None
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        A ALIGNED {ix} {removed=} now {unalignedEnglishWordList=}")
                    break # no need to try more English glosses for this Greek word
                except ValueError:
                    try:
                        ix = unalignedEnglishWordList.index( possibleEnglishGlossOrGlosses if processEnglishWordCaps else possibleEnglishGlossOrGlosses.title() )
                        alignedWords.append( ix )
                        removed, unalignedEnglishWordList[ix] = unalignedEnglishWordList[ix], None
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        B ALIGNED {ix} {removed=} now {unalignedEnglishWordList=}")
                        break # no need to try more English glosses for this Greek word
                    except ValueError:
                        pass
        if alignedWords:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Got {alignedWords=} for {gg} {grkWord=}")
            alignedList.append( alignedWords )
        else:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Got no matches for {gg} {grkWord=}")
            alignedList.append( None )

    if not any( unalignedEnglishWordList ): # then we aligned everything
        dPrint( 'Info', DEBUGGING_THIS_MODULE, "  Aligned ALL words!!!" )
    else:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Returning ({len(alignedList)}) {alignedList=} leaving {unalignedEnglishWordList=}")
        assert len(alignedList) == len(grkWordList)

    return alignedList
# end of EvaluateBibleLiteralness.alignNTVerse function


OET_LV_OT_MAJOR_TERM_LISTS = (
    # (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Yaʸsous','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    # (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
    #     ['master','Master','Masters'], ['Sir','sir','lord','Lord','mastering']),
    # (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    # (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι', 'Μεσσίας','Μεσσίαν'],['messiah','messiahs'],['Christian']),
    )
OET_RV_OT_MAJOR_TERM_LISTS = (
    # (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Yeshua','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    # (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
    #     ['master','Master','Masters'], ['Sir','sir','lord','Lord','mastering']),
    # (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    # (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι' 'Μεσσίας','Μεσσίαν'],['messiah','messiahs'],['Christian']),
    )
NON_OET_NT_MAJOR_TERM_LISTS = (
    # (['Ἰησοῦς','Ἰησοῦ','Ἰησοῦν'],['Jesus','JESUS'],['Joshua']), # JESUS is in sign on cross, Joshua is at Heb 4:8
    # (['Κύριός','Κύριος','κύριος','κύριός','Κύριον','κύριον','Κύριόν','Κυρίου','κυρίου','Κύριοι','κύριοι','κυρίῳ','Κυρίῳ','Κύριε','κύριε','κύριέ','Κύριέ','κυριεύει','κυριεύσει',  'Δεσπότης','Δεσπότην','Δέσποτα','Δεσπότῃ', 'Ἐπιστάτα'],
    #     ['lord','Lord','Lords'], ['Sir','sir','master','Master','lording']),
    # (['Θεὸς','Θεός','θεὸς','θεοὺς','Θεόν','Θεὸν','θεὸν','θεόν','Θεοῦ','θεοῦ','Θεοί','θεοι','θεοί','θεοὶ','θεοῖς','Θεῷ','θεᾶς','Θεέ', 'θεο','θεό'],['God','god','gods','Gods','goddess','godly','godliness','godless'],[]),
    # (['Χριστός','Χριστὸς','Χριστόν','Χριστὸν','Χριστοῦ','χριστοῦ','Χριστῷ','Χριστέ','Χριστιανός','Χριστιανὸν','Χριστιανούς', 'χριστοι'],['Christ','Christs'],['Christian']),
    )
def checkOTVerse( HebrewVersionAbbreviation:str, EnglishVersionAbbreviation:str, BBB:str, C:str, V:str, state:State ) -> float|None:
    """
    """
    refStr, refKey = f'{BBB}_{C}:{V}', SimpleVerseKey( BBB, C, V )
    fnPrint( DEBUGGING_THIS_MODULE, f"checkOTVerse( {HebrewVersionAbbreviation}, {EnglishVersionAbbreviation}, {refStr} )" )

    HebrewReferenceBible, EnglishBible = state.preloadedBibles[HebrewVersionAbbreviation], state.preloadedBibles[EnglishVersionAbbreviation]
    HebrewVerseDictionaryRows = []
    if HebrewVersionAbbreviation == 'SR-GNT':
        for row in state.HebrewRows:
            if row['Ref'].startswith( f'{refStr}w' ):
                HebrewVerseDictionaryRows.append( row )
            elif HebrewVerseDictionaryRows:
                break # Stop once we've finished all that verse
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{refStr} has {len(HebrewVerseDictionaryRows)} dict rows" )

    try:
        hebVrsTxt = HebrewReferenceBible.getVerseText( refKey, fullTextFlag=False, includeNonCanonical=False )
        if not hebVrsTxt:
            logging.error( f"Blank text at {refKey.getShortText()} in {HebrewVersionAbbreviation}" )
    except KeyError:
        logging.error( f"Can't find {refKey.getShortText()} in {HebrewVersionAbbreviation}" )
        hebVrsTxt = ''
    if EnglishVersionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
        try:
            engVrsTxt = EnglishBible[(BBB,C,V)]
            if engVrsTxt.startswith( '(' ) and engVrsTxt[1].isdigit(): # then it's probably a verse range, e.g., (21-23), esp. in MSG
                _prefix, engVrsTxt = engVrsTxt.split( ' ', 1 )
        except KeyError:
            return None
    else: # a proper Bible object
        try:
            engVrsTxt = EnglishBible.getVerseText( refKey, fullTextFlag=False, includeNonCanonical=False )
            if not engVrsTxt:
                logging.error( f"Blank text at {refKey.getShortText()} in {EnglishVersionAbbreviation}" )
            elif EnglishVersionAbbreviation in ('ASV','DRA','YLT','Drby','RV','Wbstr','KJB-1769','KJB-1611','Bshps','Gnva','Cvdl','Wycl'):
                engVrsTxt = moderniseEnglishWords( engVrsTxt, allowOptions=False )
        except KeyError:
            logging.error( f"Can't find {refKey.getShortText()} in {EnglishVersionAbbreviation}" )
            engVrsTxt = ''

    hebWordCount = hebVrsTxt.count(' ') + 1
    engWordCount = engVrsTxt.replace('—',' ').count(' ') + 1 # So things like 'he_said' is only counted as one word
    try:
        ratio = engWordCount / hebWordCount
        # if ratio < 0.95 or ratio > 1.5:
        #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"       {EnglishVersionAbbreviation} {refStr} {engWordCount}/{grkWordCount}={ratio:.2f} {grkVrsTxt=} {engVrsTxt=}" )
    except ZeroDivisionError: ratio = None
    if EnglishVersionAbbreviation == 'OET-LV':
        engWordCount2 = engVrsTxt.replace('_',' ').replace('—',' ').count(' ') + 1 # So things like 'you_all_heard' and 'it_was_said' are counted as three words
        try:
            ratio2 = engWordCount2 / hebWordCount
            # if ratio2 < 0.95 or ratio2 > 2.6:
            #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"       OET-LV individual_words {refStr} {engWordCount2}/{grkWordCount}={ratio2:.2f} {grkVrsTxt=} {engVrsTxt=}" )
        except ZeroDivisionError: ratio = None

    hebWords1 = removePunctuation( hebVrsTxt
                                # .replace('θεόπνευστος','θεό πνευστος').replace('θεοδίδακτοί','θεο δίδακτοί').replace('θεοστυγεῖς','θεο στυγεῖς')
                                # .replace('θεοσέβειαν','θεο σέβειαν').replace('θεοσεβὴς','θεο σεβὴς')
                                # .replace('ἄθεοι','ἄ θεοι').replace('φιλόθεοι','φιλό θεοι')
                                # .replace('ψευδόχριστοι','ψευδό χριστοι').replace('ἀντίχριστοι','ἀντί χριστοι')
                                ).split()
    engWords1 = removePunctuation( engVrsTxt.replace('God-','God ').replace('god-','god ')
                                        .replace( '0-', '0 ').replace( '1-', '1 ').replace( '2-', '2 ').replace( '3-', '3 ').replace( '4-', '4 ').replace( '5-', '5 ').replace( '6-', '6 ').replace( '7-', '7 ').replace( '8-', '8 ').replace( '9-', '9 ') # Assume these are word-numbers before hyphens
                                        # .replace( '-Cain', ' Cain' ) # Tubal-Cain inputWord='Tubal¦1713-Cain¦1714'
                                        # .replace( '-Ir', ' Ir' ) # Rehobot-Ir inputWord='Rehobot¦4005-Ir'
                                        # .replace( '-Karnaim', ' Karnaim' ) # Ashteroth-Karnaim inputWord='Ashteroth¦5474-Karnaim'
                                        # .replace( '-Roi', ' Roi' ) # Gen_24:62 inputWord="Be'er-Lahai¦10812-Roi"
                                        .replace('\\sup ','').replace('\\sup*','') # We superscript yah and el in names
                                        .replace('_',' ').replace('/',' ').replace('=',' ').replace('÷',' ')
                                        ).split()
    hebWords, engWords = hebWords1, engWords1
    if HebrewVersionAbbreviation == 'UHB':
        hebWords = [removeWordNumber(HebrewVersionAbbreviation, refStr, w) for w in hebWords1]
    if 'OET' in EnglishVersionAbbreviation:
        engWords = [removeWordNumber(EnglishVersionAbbreviation, refStr, w) for w in engWords1]
    # print( f"{hebVrsTxt=} ({len(hebWords1)}) {hebWords1=} ({len(hebWords)}) {hebWords=}" )
    # print( f"{engVrsTxt=} ({len(engWords1)}) {engWords1=} ({len(engWords)}) {engWords=}" )

    # Now that we have text1 and text2 for the verse specified in ref, do our analysis/comparison now
    verseScore = 10.0
    if not hebWords and not engWords: # it's a verse that's not in the original
        pass # use verseScore default above
    elif not hebWords or not engWords: # verse isn't included in the version
        if engWords:
            verseScore = 0.0
    else:
        alignedList = alignNTVerse( refStr, HebrewVersionAbbreviation, EnglishVersionAbbreviation, hebWords, engWords, state, breakAtUnderline=True )
        assert len(alignedList) == len(hebWords)
        verseScore *= ( len(alignedList) - alignedList.count( None ) ) / len(alignedList)
        #except ZeroDivisionError: pass # on an empty list, i.e., non-existing verse
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {refStr} score 1 = {verseScore:.1f}")
    
    # Check a handful of major terms
    for origWordList,engWordList,altEngWordList in OET_LV_NT_MAJOR_TERM_LISTS if EnglishVersionAbbreviation=='OET-LV' else OET_RV_NT_MAJOR_TERM_LISTS if EnglishVersionAbbreviation=='OET-RV' else NON_OET_NT_MAJOR_TERM_LISTS:
        grkCount, engCount = checkImportantWord( refStr, HebrewVersionAbbreviation, EnglishVersionAbbreviation, hebWords, engWords, origWordList, engWordList, altEngWordList )
        if grkCount < engCount:
            verseScore *= grkCount / engCount
        elif engCount < grkCount:
            verseScore *= engCount / grkCount
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {refStr} score 2 = {verseScore:.1f}\n")

    return verseScore
# end of EvaluateBibleLiteralness.checkOTVerse function


def publishResult( EnglishVersionAbbreviation:str, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"publishResult( {EnglishVersionAbbreviation} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "" ) # Blank line

    EnglishBible = state.preloadedBibles[EnglishVersionAbbreviation]
    referenceBible = state.referenceBible if EnglishVersionAbbreviation in state.selectedVersesOnlyVersions else EnglishBible
    missingBooksList = list( BOOKLIST_66 )
    bibleTotalScores = bibleVerseCount = 0
    bibleMissingVersesCount = bibleMissingChaptersCount = 0
    hugeBibleVerseScoreList = []
    bookScoresList = []
    state.versionResults[EnglishVersionAbbreviation]['bookScores'] = {}
    for BBB in BOOKLIST_66:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Processing {EnglishVersionAbbreviation} {BBB}…" )

        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        if not numChapters:
            continue # This book musn't be in this version

        missingBookChaptersList = [f'{BBB}_{c}' for c in range( 1, numChapters+1 )]
        missingBookVersesList = []
        bookTotalScores = bookVerseCount = 0
        largeBookVerseScoreList = []
        for c in range( 1, numChapters+1 ):
            C = str( c )
            numVerses = referenceBible.getNumVerses( BBB, C )
            if numVerses is None: # something unusual
                logging.error( f"checkNT: no verses found for {BBB} {C}" )
                continue
            for v in range( 1, numVerses+1 ):
                V = str( v )
                refStr = f'{BBB}_{C}:{V}'
                try:
                    verseResult = state.versionResults[EnglishVersionAbbreviation][refStr]
                    if verseResult is None:
                        print( f"      Why did publishResult get None for {EnglishVersionAbbreviation} {refStr}???")
                        continue
                    try: missingBooksList.remove( BBB )
                    except ValueError: pass # on consecutive attempts
                    try: missingBookChaptersList.remove( f'{BBB}_{c}')
                    except ValueError: pass # on consecutive attempts
                    bookTotalScores += verseResult; bibleTotalScores += verseResult
                    bookVerseCount += 1; bibleVerseCount += 1
                    largeBookVerseScoreList.append( ( f'{C}:{V}',verseResult) ); hugeBibleVerseScoreList.append( (refStr,verseResult) )
                except KeyError:
                    missingBookVersesList.append( refStr )
                    continue
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Overall result for {EnglishVersionAbbreviation} {BBB}:" )
        if missingBookChaptersList:
            bibleMissingChaptersCount += len( missingBookChaptersList )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Have {len(missingBookChaptersList)} missing chapters" )
        elif missingBookVersesList:
            bibleMissingVersesCount += len( missingBookVersesList )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Have {len(missingBookVersesList)} missing verses" )
        try:
            bookScore = bookTotalScores / bookVerseCount
        except ZeroDivisionError: bookScore = 0.0 # i.e., non-existing book
        state.versionResults[EnglishVersionAbbreviation]['bookScores'][BBB] = bookScore
        if bookScore > 0.0: bookScoresList.append( (BBB,bookScore) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Average literalness score = {bookScore:.1f} (out of ten)")
        largeBookVerseScoreList.sort( key = lambda x: x[1] )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Verses with LOWEST literalness scores were: {BBB} {str([f'{ref} @ {score:.1f}' for (ref,score) in largeBookVerseScoreList[:21]]).replace("'",'').replace('[','').replace(']','')}''' )
        if any([score < 10.0 for (_ref,score) in largeBookVerseScoreList[-8:]]):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Verses with HIGHEST literalness scores were: {BBB} {str([f'{ref} @ {score:.1f}' for (ref,score) in reversed(largeBookVerseScoreList[-8:])]).replace("'",'').replace('[','').replace(']','')}''' )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nOverall result for {EnglishVersionAbbreviation}:" )
    if missingBooksList:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Have {len(missingBooksList)} missing books" )
    try:
        bibleScore = bibleTotalScores / bibleVerseCount
    except ZeroDivisionError: bibleScore = 0.0 # i.e., non-existing book
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Total number of verses scored = {bibleVerseCount:,}")
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Average literalness score = {bibleScore:.1f} (out of ten) with {bibleVerseCount:,} verses scored")
    bookScoresList.sort( key = lambda x: x[1] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Books with LOWEST literalness scores were: {str([f'{BBB} @ {score:.1f}' for (BBB,score) in bookScoresList[:7]]).replace("'",'').replace('[','').replace(']','')}''' )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Books with HIGHEST literalness scores were: {str([f'{BBB} @ {score:.1f}' for (BBB,score) in reversed(bookScoresList[-7:])]).replace("'",'').replace('[','').replace(']','')}''' )
    hugeBibleVerseScoreList.sort( key = lambda x: x[1] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Verses with LOWEST literalness scores were: {str([f'{ref} @ {score:.1f}' for (ref,score) in hugeBibleVerseScoreList[:20]]).replace("'",'').replace('[','').replace(']','')}''' )
    if any([score < 10.0 for (_ref,score) in hugeBibleVerseScoreList[-8:]]):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Verses with HIGHEST literalness scores were: {str([f'{ref} @ {score:.1f}' for (ref,score) in reversed(hugeBibleVerseScoreList[-8:])]).replace("'",'').replace('[','').replace(']','')}''' )

    state.versionResults[EnglishVersionAbbreviation]['totalVersesScored'] = bibleVerseCount
    state.versionResults[EnglishVersionAbbreviation]['literalnessScore'] = bibleScore
    state.versionResults[EnglishVersionAbbreviation]['bookScoresList'] = bookScoresList

    return True
# end of EvaluateBibleLiteralness.publishResult()


def publishSummary( state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"publishSummary()" )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n\nSummary results:" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    (A typical OT has just over 23,200 verses, NT has just under 8,000 verses, whole Bible has just over 31,000 verses.)\n" )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Note: The OT is NOT YET PROPERLY EVALUATED for literalness!\n" )

    versionsScoreSummaryList = []
    for EnglishVersionAbbreviation in state.EnglishTranslations:
        numVersesScored = state.versionResults[EnglishVersionAbbreviation]['totalVersesScored']
        bibleScore = state.versionResults[EnglishVersionAbbreviation]['literalnessScore']
        versionsScoreSummaryList.append( (EnglishVersionAbbreviation,bibleScore) )
        bookScoresList = state.versionResults[EnglishVersionAbbreviation]['bookScoresList']
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{EnglishVersionAbbreviation} literalness summary results:" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Average literalness score for {numVersesScored:,} {EnglishVersionAbbreviation} verses = {bibleScore:.1f} (out of ten)")
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Books with LOWEST literalness scores were: {str([f'{BBB} @ {score:.1f}' for (BBB,score) in bookScoresList[:7]]).replace("'",'').replace('[','').replace(']','')}''' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''  Books with HIGHEST literalness scores were: {str([f'{BBB} @ {score:.1f}' for (BBB,score) in reversed(bookScoresList[-7:])]).replace("'",'').replace('[','').replace(']','')}''' )

    versionsScoreSummaryList.sort( key = lambda x: x[1] )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''\nVersions with LOWEST literalness scores were: {str([f'{vers} @ {score:.1f}' for (vers,score) in versionsScoreSummaryList[:5]]).replace("'",'').replace('[','').replace(']','')}''' )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''Versions with HIGHEST literalness scores were: {str([f'{vers} @ {score:.1f}' for (vers,score) in reversed(versionsScoreSummaryList[-5:])]).replace("'",'').replace('[','').replace(']','')}''' )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''\nAll versions with literalness scores were: {str([f'{vers} @ {score:.1f}' for (vers,score) in reversed(versionsScoreSummaryList)]).replace("'",'').replace('[','').replace(']','')}''' )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nNOTE: The highest 10.0 score above is for the most LITERAL version.\n  You should note that it's not an indication that it's a GOOD, READABLE, or UNDERSTANDABLE English translation!\n" )

    return True
# end of EvaluateBibleLiteralness.publishSummary()


def briefDemo() -> None:
    """
    Fast demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
# end of briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    # Do the BOS close-down stuff
    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of EvaluateBibleLiteralness.py
