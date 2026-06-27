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
from pathlib import Path
import logging

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Formats.ESFMBibleBook import ESFMBibleBook
from bible_organisational_system import InternalBibleEntryList, InternalBibleEntry, \
    InternalBibleBookCVIndex, InternalBibleBookSectionIndex


LAST_MODIFIED_DATE = '2026-06-27' # by RJH
SHORT_PROGRAM_NAME = "test_OET_RV_HAG_indexes"
PROGRAM_NAME = "Test OET-RV HAG CV and section indexes"
PROGRAM_VERSION = '0.11.3'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

USE_ONLINE_DATA = False # Uses the latest online data (vs. the static local copy in this repo)
BBB = 'HAG'



def load_OET_RV_Haggai() -> ESFMBible|None:
    """
    Load the OET-RV Haggai (two-chapter) ESFM file (from GitHub)
        in order to get test data to help the AI agents duplicate the Python code in Rust
    """
    fnPrint( DEBUGGING_THIS_MODULE, "load_OET_RV_Haggai()" )

    if USE_ONLINE_DATA:
        folderURL = 'https://raw.githubusercontent.com/Freely-Given-org/OpenEnglishTranslation--OET/refs/heads/main/translatedTexts/ReadersVersion'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Looking for ESFM Bible at {folderURL}" )
        EsfmBib = ESFMBible( folderURL, 'Open English Translation Readers’ Version', 'OET-RV' )
    else: # use local path
        relativePath = Path( 'Tests/DataFilesForTests/OET-RV/' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Looking for ESFM Bible at {relativePath}" )
        EsfmBib = ESFMBible( relativePath, 'Open English Translation Readers’ Version', 'OET-RV' )
    # EsfmBib.preload()

    # We copied this function inline here so we could get an more internals (before processLines() gets called)
    filename = 'OET-RV_HAG.ESFM'
    # EsfmBib.loadBook( BBB, filename )
    fnPrint( DEBUGGING_THIS_MODULE, f"ESFMBible.loadBook( {BBB}, {filename} )" )
    if BBB in EsfmBib.books: return # Already loaded
    if BBB in EsfmBib.dontLoadBook: return # Must be a dictionary that's already loaded
    if BBB in EsfmBib.triedLoadingBook:
        logging.warning( f"We had already tried loading ESFM {BBB} for {EsfmBib.name}" )
        return # We've already attempted to load this book
    EsfmBib.triedLoadingBook[BBB] = True

    if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  ESFMBible: Loading {BBB} from {EsfmBib.name} from {EsfmBib.sourceFolder}…" )
    try:
        if filename is None and BBB in self.possibleFilenameDict:
            filename = EsfmBib.possibleFilenameDict[BBB]
    except AttributeError as e:
        logging.critical( f"Was a preload() done on this {EsfmBib.abbreviation} ESFMBible? Or is folder {self.sourceFolder} empty? (Can't find any possible filenames.)" )
        # raise ValueError( f"ESFMBible.loadBook: Unable to load {BBB}{' '+filename if filename else ''} for {self.abbreviation} ESFM Bible" )
    if filename is None:
        raise FileNotFoundError( f"ESFMBible.loadBook: Unable to find file for {BBB}" )

    EBB = ESFMBibleBook( EsfmBib, BBB )
    EBB.load( filename, EsfmBib.sourceFolder )
    if EBB._rawLines:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{len(EBB._rawLines)=}" )# expected 83
        for ee, entry in enumerate( EBB._rawLines ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {ee} Raw {entry=}" )

        EBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        EsfmBib.stashBook( EBB )
    else: logging.info( "ESFM book {BBB} was completely blank" )
    """
    Should now have the following 81 _rawLines entries:
        0 Raw entry=('id', "HAG - Open English Translation—Readers' Version (OET-RV) v0.1.03")
        1 Raw entry=('usfm', '3.0')
        2 Raw entry=('ide', 'UTF-8')
        3 Raw entry=('rem', 'ESFM v0.6 HAG')
        4 Raw entry=('rem', 'WORDTABLE OET-LV_OT_word_table.tsv')
        5 Raw entry=('h', 'Haggai')
        6 Raw entry=('toc1', 'Haggai')
        7 Raw entry=('toc2', 'Haggai')
        8 Raw entry=('toc3', 'Hag.')
        9 Raw entry=('mt1', 'Haggai')
        10 Raw entry=('is1', 'Introduction')
        11 Raw entry=('ip', "This document contains a number of messages from Yahweh that the prophet Haggai passed on to the people in Yerushalem (Jerusalem). These events happened around 520 before Yeshua/Jesus (B.C.), after many of God's people had gone back to Yerushalem after being taken into captivity in Babylon. However, even though they'd been back for a considerable time, they hadn't worked on rebuilding the temple. Therefore, these messages from Yahweh encourage the people to change their priorities and obey God and rebuild the temple. God then promised to prosper the people and bless their living situation.")
        12 Raw entry=('iot', 'Main components of this account')
        13 Raw entry=('io1', "God's command to rebuild the temple \\ior 1:1-15\\ior*")
        14 Raw entry=('io1', 'Stories of comfort and hope \\ior 2:1-23\\ior*')
        15 Raw entry=('rem', 'This is still a very early look into the unfinished text of the Open English Translation of the Bible. Please double-check the text in advance before using in public.')
        16 Raw entry=('ie', '')
        17 Raw entry=('c', '1')
        18 Raw entry=('s1', "God's command to rebuild the temple")
        19 Raw entry=('rem', "/s1 The Lord's Command to Rebuild the Temple; A Call to Rebuild the Temple; Zerubbabel restorer of the temple; A Call to Build the House of the Lord; The Command to Rebuild the Temple")
        20 Raw entry=('p', '')
        21 Raw entry=('v', "1 In Dareyavesh's \\add (Darius's¦375563)\\add* second year¦375561 as king¦375564 \\add of Persia\\add*, on¦375565 the 1st of the sixth¦375566 month, the prophet¦375577 Haggai¦375576 brought Yahweh's¦375573 message¦375571 to the governor¦375584 of Yehudah¦375585, Zerubavel¦375580 (Shealtiyel's¦375583 son), and to the high¦375593 priest¦375592, Yehoshua (Yehotsadak's¦375591 son), telling \\add them that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*")
        22 Raw entry=('v', "2 Commander-in-chief Yahweh says, “These people¦375601 say that \\add ≈it's not the right\\add* time to rebuild¦375612 Yahweh's¦375598 \\add ≈residence\\add*.”")
        23 Raw entry=('p', '')
        24 Raw entry=('v', '3 Then Yahweh¦375618 \\add ≈gave this message¦375616\\add* to the prophet¦375622 Haggai¦375621 \\add to tell the people\\add*:')
        25 Raw entry=('m', '')
        26 Raw entry=('v', "4 Is it a time¦375625 for all of you to live in your panelled¦375630 houses¦375629, while \\add ≈Yahweh's temple lies in ruins\\add*?")
        27 Raw entry=('v', "5 \\add ≈So¦375635\\add* now Commander-in-chief Yahweh¦375638 says¦375637: “\\add ≈Decide what you're all going to do\\add*.")
        28 Raw entry=('v', "6 You've all planted a lot, \\add ≈but only harvested¦375648 a little¦375649. You've eaten¦375650, but it never fills you. You all drink, but never enough to satisfy¦375653 you. You put on clothes, but never feel warm enough. You earn wages¦375664, but your pockets seem to be full of holes\\add*.”")
        29 Raw entry=('p', '')
        30 Raw entry=('v', "7 \\add ≈So\\add* Commander-in-chief Yahweh¦375673 says¦375672 \\add again\\add*: “\\add ≈Decide what you're all going to do\\add*.")
        31 Raw entry=('v', '8 Go up into the hills¦375682 and bring¦375683 back timber to build¦375685 the \\add ≈temple\\add*. This will please¦375687 and honour¦375690 me,” says¦375692 Yahweh¦375693.')
        32 Raw entry=('p', '')
        33 Raw entry=('v', "9 “You \\add ≈expected\\add* much, but¦375699 \\add gained\\add* little¦375700. Anything you brought¦375701 home¦375702, I blew away \\add again\\add*. Why? Commander-in-chief Yahweh¦375708 says it's because my residence is still in ruins, while you're all \\add busy\\add* \\add ≈working on\\add* your own houses.")
        34 Raw entry=('v', "10 That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops.")
        35 Raw entry=('v', "11 I've¦375735 \\add ≈summoned¦375735\\add* a drought¦375736 onto the land and into the hills¦375742, onto the grain¦375745 and the new wine, onto the oil and crops from the ground, onto \\add both\\add* people and livestock, and onto \\add ≈everything you all do\\add*.”")
        36 Raw entry=('s1', 'The people start rebuilding')
        37 Raw entry=('rem', "/s1 The People Obey the Lord's Command; Obedience to God's Call")
        38 Raw entry=('p', '')
        39 Raw entry=('v', "12 Then Shealtiyel's son Zerubavel and Yehotsadak's son Yehoshua, the high priest¦375779, and all the rest of the people listened¦375769 to the voice¦375785 of their god Yahweh \\add ≈via\\add* the words¦375790 of the prophet¦375792 Haggai¦375791, because Yahweh their god had sent him, and the people \\add ≈respected\\add* Yahweh.")
        40 Raw entry=('v', "13 Then¦375802 Yahweh's¦375805 messenger¦375804 Haggai¦375803 passed this message¦375806 from Yahweh onto the people¦375808, “Yahweh declares that I'm with¦375806 you¦375811 all.”")
        41 Raw entry=('v', "14 Then¦375816 Yahweh \\add ≈inspired\\add* Shealtiyel's son Zerubavel, the governor¦375825 of Yehudah¦375826, \\add ≈inspired\\add* Yehotsadak's son Yehoshua, the high¦375835 priest¦375834, and \\add ≈inspired\\add* all the rest of the people¦375841, and they came¦375842 and \\add ≈started\\add* work¦375844 on the \\add ≈temple\\add* for their¦375849 god¦375849, Commander-in-chief Yahweh,")
        42 Raw entry=('v', '15 on¦375856 the twenty-fourth day¦375852 of the sixth¦375856 month¦375855 of the second year¦375857 of Dareyavesh the king¦375860 \\add of Persia\\add*.')
        43 Raw entry=('c', '2')
        44 Raw entry=('s1', 'The splendour of the new temple')
        45 Raw entry=('rem', "/s1 The Future Glory of the Temple; The New Temple's Splendour; The Splendour of the New Temple; The Promised Glory of the New House")
        46 Raw entry=('p', '')
        47 Raw entry=('v', '1 On the 21st of the seventh¦375862 month \\add (about a month later)\\add*, Yahweh¦375869 \\add ≈spoke\\add* \\add again\\add* through the prophet¦375873 Haggai¦375872:')
        48 Raw entry=('v', "2 Please \\add ≈ask\\add* Shealtiyel's son Zerubavel, the governor¦375885 of Yehudah¦375886, and \\add ≈ask\\add* Yehotsadak's son Yehoshua, the high¦375894 priest¦375893, and \\add ≈ask\\add* the rest of the people¦375898,")
        49 Raw entry=('v', '3 “\\add ≈Are there any of you still alive who saw¦375905 the splendour¦375910 of the former¦375911 temple\\add*? How does it look to you now? \\add ≈It must now seem pretty much like \\+em nothing¦375919\\+em* in¦375902 comparison\\add*.\\x + \\xo 2:3: \\xt Ezr 3:12.\\x*')
        50 Raw entry=('v', "4 Yahweh is telling you now, Zerubavel, to be strong. And be strong, high¦375935 priest¦375934 Yehoshua, and¦375922 be strong all you people¦375939 of the land. Commander-in-chief Yahweh declares that I'm with you \\add ≈as you work¦375944\\add*.")
        51 Raw entry=('v', "5 \\add ≈That's what I promised¦375955 your¦375964 ancestors when they\\add* came¦375960 out of Egypt¦375961,\\x + \\xo 2:5: \\xt Exo 29:45-46.\\x* and¦375962 my spirit¦375962 remains \\add ≈among¦375964 you¦375960\\add*. Don't¦375965 be afraid¦375967,")
        52 Raw entry=('v', "6 because¦375970 Commander-in-chief Yahweh¦375973 says¦375972 that in a little¦375977 while, I'll¦375979 shake¦375980 the heavens¦375983 and the earth¦375986, the sea¦375989 and the dry land, once more.\\x + \\xo 2:6: \\xt Heb 12:26.\\x*")
        53 Raw entry=('v', "7 I'll shake¦375994 all the nations, and¦375994 they'll come \\add here bringing\\add* their treasure. Then¦375994 I'll fill this \\add ≈temple\\add* with \\add my\\add* splendour¦376010, says Commander-in-chief Yahweh¦376012.")
        54 Raw entry=('v', '8 Commander-in-chief Yahweh¦376020 declares that the gold¦376018 and¦376017 silver¦376016 \\add belong¦376017\\add* to me.')
        55 Raw entry=('v', '9 \\add *I\\add* declare that this \\add ≈temple\\add* will be \\add ≈greater in the future than it¦376024 was in the past\\add*, and \\add also\\add* that I will give¦376037 peace¦376038 and prosperity to this place¦376035.”')
        56 Raw entry=('s1', 'Haggai consults the priests')
        57 Raw entry=('rem', '/s1 Blessings Promised for Obedience; Blessings for a Defiled People; A Rebuke and a Promise; The Prophet Consults the Priests')
        58 Raw entry=('p', '')
        59 Raw entry=('v', "10 On the 24th of the ninth¦376046 month in¦376044 \\add King\\add* Dareyavesh's second year¦376047 \\add (about two¦376048 months later)\\add*, Yahweh¦376053 \\add ≈gave a message¦376051\\add* to the prophet¦376057 Haggai¦376056:")
        60 Raw entry=('v', "11 Commander-in-chief Yahweh¦376062 says¦376061, “Ask the priests¦376069 about \\add Mosheh's\\add* \\add ≈instructions¦376070\\add*.")
        61 Raw entry=('v', '12 ‘\\add ≈If a priest took some meat¦376078 that had been offered to God and carried it wrapped in¦376081 a piece of clothing, then if the clothing touched¦376083 some other food, would that other food \\add* become¦376102 holy?’ ”')
        62 Raw entry=('p', "“No, it wouldn't,” the priests¦376104 \\add ≈replied\\add*.")
        63 Raw entry=('p', '')
        64 Raw entry=('v', '13 Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\add* if a person became unclean by touching a corpse¦376115 and¦376108 then¦376108 touched any of that \\add food\\add*, would it become unclean?”\\x + \\xo 2:13: \\xt Num 19:11-22.\\x*')
        65 Raw entry=('p', '“\\add Yes,\\add* it would become unclean,” the priests¦376121 answered¦376120.')
        66 Raw entry=('p', '')
        67 Raw entry=('v', "14 “\\add ≈That's what Yahweh¦376139 declares about you\\add* people¦376129,” Haggai¦376126 \\add ≈continued¦376125\\add*. “\\add He says that\\add* \\add ≈that's how this country¦376134 acts towards him\\add*. \\add ≈Your actions are dishonourable, and¦376125 then¦376125 that same disrespect transfers to your offerings\\add*.")
        68 Raw entry=('rem', '/s1 The Lord Promises His Blessing')
        69 Raw entry=('v', "15 So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple.")
        70 Raw entry=('v', '16 \\add ≈During that time\\add*, when someone went to get twenty \\add containers of grain\\add*, there were \\add only\\add* ten¦376178 there, and when someone went to fill fifty¦376184 \\add jars of wine\\add* from the vat, there was \\add only enough for\\add* twenty.')
        71 Raw entry=('v', "17 Yahweh¦376205 declares that he \\add ≈caused\\add* blight¦376191 and mildew¦376192 and hail to affect your work¦376197, \\add ≈but¦376192\\add* you \\add still\\add* didn't¦376199 turn to him.")
        72 Raw entry=('v', "18 Think back to the time from when the foundation¦376225 of Yahweh's¦376228 temple¦376226 was laid, until today (this 24th of the ninth¦376219 month¦376219). Consider that.")
        73 Raw entry=('v', "19 Is \\add any grain\\add* left in¦376234 the storehouse for seed? \\add What's more,\\add* the vines, and the fig¦376238 trees and pomegranate¦376239 trees and olive trees, haven't produced fruit. \\add However,\\add* Yahweh will bless you from today onwards.”")
        74 Raw entry=('s1', "God's promise to Zerubavel")
        75 Raw entry=('rem', "/s1 The Lord's Promise to Zerubbabel; God's Promise to Zerubbabel; Promises for Zerubbabel; Zerubbabel the Lord's Signet Ring")
        76 Raw entry=('p', '')
        77 Raw entry=('v', '20 Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:')
        78 Raw entry=('v', "21 Tell Zerubavel, the governor¦376269 of Yehudah¦376271, “I'm \\add about¦376274 to\\add* shake¦376274 the heavens¦376277 and the earth¦376280.")
        79 Raw entry=('v', "22 I'll overthrow the thrones¦376283 of kingdoms¦376288, and destroy¦376285 the strength¦376286 of the nations¦376288. I'll overthrow chariots¦376290 and riders—horses¦376293 and their¦376294 riders will fall and \\add related tribes\\add* \\add ≈will kill¦376285 each other\\add*.")
        80 Raw entry=('v', "23 Commander-in-chief Yahweh declares that on that day¦376299 he will take¦376305 Shealtiyel's son Zerubavel and \\add ≈cause him to place Yahweh's¦376303 mark on the nation\\add* like a signet¦376315 ring, because¦376316 he's been chosen¦376319.”")
    """

    """
    NOT UP-TO-DATE
    After _processLine( marker, text ) is called on each rawLine
        (by splitting text off paragraph markers like 'v','p', etc. and adding 'v~' and 'XXXp~' markers containing the Biblical text)
        which is then placed in _processedLines, we expect:
    processLines for HAG with len(self._rawLines)=81 initially got len(self._processedLines)=123
      0 entryWithPreliminaryProcessing=InternalBibleEntry object:
    id = "HAG - Open English Translation—Readers' Version (OET-RV) v0.1.03"
      1 entryWithPreliminaryProcessing=InternalBibleEntry object:
    usfm = '3.0'
      2 entryWithPreliminaryProcessing=InternalBibleEntry object:
    ide = 'UTF-8'
      3 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = 'ESFM v0.6 HAG'
      4 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = 'WORDTABLE OET-LV_OT_word_table.tsv'
      5 entryWithPreliminaryProcessing=InternalBibleEntry object:
    h = 'Haggai'
      6 entryWithPreliminaryProcessing=InternalBibleEntry object:
    toc1 = 'Haggai'
      7 entryWithPreliminaryProcessing=InternalBibleEntry object:
    toc2 = 'Haggai'
      8 entryWithPreliminaryProcessing=InternalBibleEntry object:
    toc3 = 'Hag.'
      9 entryWithPreliminaryProcessing=InternalBibleEntry object:
    mt1 = 'Haggai'
      10 entryWithPreliminaryProcessing=InternalBibleEntry object:
    is1 = 'Introduction'
      11 entryWithPreliminaryProcessing=InternalBibleEntry object:
    ip = 'This document contains a number of messages from Y…osper the people and bless their living situation.'
      12 entryWithPreliminaryProcessing=InternalBibleEntry object:
    iot = 'Main components of this account'
      13 entryWithPreliminaryProcessing=InternalBibleEntry object:
    io1 = "God's command to rebuild the temple 1:1-15"  from Original io1 = "God's command to rebuild the temple \\ior 1:1-15\\ior*"
      14 entryWithPreliminaryProcessing=InternalBibleEntry object:
    io1 = 'Stories of comfort and hope 2:1-23'  from Original io1 = 'Stories of comfort and hope \\ior 2:1-23\\ior*'
      15 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = 'This is still a very early look into the unfinishe…-check the text in advance before using in public.'
      16 entryWithPreliminaryProcessing=InternalBibleEntry object:
    ie = ''
      17 entryWithPreliminaryProcessing=InternalBibleEntry object:
    c = '1'
      18 entryWithPreliminaryProcessing=InternalBibleEntry object:
    s1 = "God's command to rebuild the temple"
      19 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = "/s1 The Lord's Command to Rebuild the Temple; A Ca…use of the Lord; The Command to Rebuild the Temple"
      20 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      21 entryWithPreliminaryProcessing=InternalBibleEntry object:
    c# = '1'  from Original c = '1'
      22 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '1'
      23 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "In Dareyavesh's (Darius's¦375563) second year¦3755…oshua (Yehotsadak's¦375591 son), telling them that"  from Original v = "In Dareyavesh's \\add (Darius's¦375563)\\add* second… that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*"
          adjusted to "In Dareyavesh's \\add (Darius's¦375563)\\add* second…otsadak's¦375591 son), telling \\add them that\\add*"
         with InternalBibleExtraList object:
  1 xr @ 403 = '+ \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.'
      24 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '2'
      25 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh says, “These people¦3756…ime to rebuild¦375612 Yahweh's¦375598 ≈residence.”"  from Original v = "Commander-in-chief Yahweh says, “These people¦3756…uild¦375612 Yahweh's¦375598 \\add ≈residence\\add*.”"
      26 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      27 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '3'
      28 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Then Yahweh¦375618 ≈gave this message¦375616 to th…e prophet¦375622 Haggai¦375621 to tell the people:'  from Original v = 'Then Yahweh¦375618 \\add ≈gave this message¦375616\\…375622 Haggai¦375621 \\add to tell the people\\add*:'
      29 entryWithPreliminaryProcessing=InternalBibleEntry object:
    m = ''
      30 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '4'
      31 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Is it a time¦375625 for all of you to live in your…uses¦375629, while ≈Yahweh's temple lies in ruins?"  from Original v = "Is it a time¦375625 for all of you to live in your…9, while \\add ≈Yahweh's temple lies in ruins\\add*?"
      32 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '5'
      33 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "≈So¦375635 now Commander-in-chief Yahweh¦375638 says¦375637: “≈Decide what you're all going to do."  from Original v = "\\add ≈So¦375635\\add* now Commander-in-chief Yahweh…7: “\\add ≈Decide what you're all going to do\\add*."
      34 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '6'
      35 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "You've all planted a lot, ≈but only harvested¦3756…75664, but your pockets seem to be full of holes.”"  from Original v = "You've all planted a lot, \\add ≈but only harvested…, but your pockets seem to be full of holes\\add*.”"
      36 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      37 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '7'
      38 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "≈So Commander-in-chief Yahweh¦375673 says¦375672 again: “≈Decide what you're all going to do."  from Original v = "\\add ≈So\\add* Commander-in-chief Yahweh¦375673 say…*: “\\add ≈Decide what you're all going to do\\add*."
      39 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '8'
      40 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'  from Original v = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'
      41 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      42 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '9'
      43 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "“You ≈expected much, but¦375699 gained little¦3757…while you're all busy ≈working on your own houses."  from Original v = '“You \\add ≈expected\\add* much, but¦375699 \\add gai…d busy\\add* \\add ≈working on\\add* your own houses.'
      44 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '10'
      45 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."  from Original v = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."
      46 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '11'
      47 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "I've¦375735 ≈summoned¦375735 a drought¦375736 onto…e and livestock, and onto ≈everything you all do.”"  from Original v = "I've¦375735 \\add ≈summoned¦375735\\add* a drought¦3…stock, and onto \\add ≈everything you all do\\add*.”"
      48 entryWithPreliminaryProcessing=InternalBibleEntry object:
    s1 = 'The people start rebuilding'
      49 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = "/s1 The People Obey the Lord's Command; Obedience to God's Call"
      50 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      51 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '12'
      52 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…od had sent him, and the people ≈respected Yahweh."  from Original v = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…t him, and the people \\add ≈respected\\add* Yahweh."
      53 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '13'
      54 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"  from Original v = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"
      55 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '14'
      56 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Then¦375816 Yahweh ≈inspired Shealtiyel's son Zeru…heir¦375849 god¦375849, Commander-in-chief Yahweh,"  from Original v = "Then¦375816 Yahweh \\add ≈inspired\\add* Shealtiyel'…heir¦375849 god¦375849, Commander-in-chief Yahweh,"
      57 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '15'
      58 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'on¦375856 the twenty-fourth day¦375852 of the sixt…ar¦375857 of Dareyavesh the king¦375860 of Persia.'  from Original v = 'on¦375856 the twenty-fourth day¦375852 of the sixt…of Dareyavesh the king¦375860 \\add of Persia\\add*.'
      59 entryWithPreliminaryProcessing=InternalBibleEntry object:
    c = '2'
      60 entryWithPreliminaryProcessing=InternalBibleEntry object:
    s1 = 'The splendour of the new temple'
      61 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = '/s1 The Future Glory of the Temple; The New Temple…he New Temple; The Promised Glory of the New House'
      62 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      63 entryWithPreliminaryProcessing=InternalBibleEntry object:
    c# = '2'  from Original c = '2'
      64 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '1'
      65 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'On the 21st of the seventh¦375862 month (about a m…ke again through the prophet¦375873 Haggai¦375872:'  from Original v = 'On the 21st of the seventh¦375862 month \\add (abou…ain\\add* through the prophet¦375873 Haggai¦375872:'
      66 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '2'
      67 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Please ≈ask Shealtiyel's son Zerubavel, the govern…st¦375893, and ≈ask the rest of the people¦375898,"  from Original v = "Please \\add ≈ask\\add* Shealtiyel's son Zerubavel, … and \\add ≈ask\\add* the rest of the people¦375898,"
      68 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '3'
      69 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = '“≈Are there any of you still alive who saw¦375905 …tty much like nothing¦375919 in¦375902 comparison.'  from Original v = '“\\add ≈Are there any of you still alive who saw¦37…902 comparison\\add*.\\x + \\xo 2:3: \\xt Ezr 3:12.\\x*'
          adjusted to '“\\add ≈Are there any of you still alive who saw¦37…+em nothing¦375919\\+em* in¦375902 comparison\\add*.'
         with InternalBibleExtraList object:
  1 xr @ 230 = '+ \\xo 2:3: \\xt Ezr 3:12.'
      70 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '4'
      71 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Yahweh is telling you now, Zerubavel, to be strong…eh declares that I'm with you ≈as you work¦375944."  from Original v = "Yahweh is telling you now, Zerubavel, to be strong…s that I'm with you \\add ≈as you work¦375944\\add*."
      72 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '5'
      73 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "≈That's what I promised¦375955 your¦375964 ancesto…¦375964 you¦375960. Don't¦375965 be afraid¦375967,"  from Original v = "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
          adjusted to "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
         with InternalBibleExtraList object:
  1 xr @ 105 = '+ \\xo 2:5: \\xt Exo 29:45-46.'
      74 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '6'
      75 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'  from Original v = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…ry land, once more.\\x + \\xo 2:6: \\xt Heb 12:26.\\x*'
          adjusted to 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'
         with InternalBibleExtraList object:
  1 xr @ 200 = '+ \\xo 2:6: \\xt Heb 12:26.'
      76 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '7'
      77 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."  from Original v = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."
      78 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '8'
      79 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Commander-in-chief Yahweh¦376020 declares that the…6018 and¦376017 silver¦376016 belong¦376017 to me.'  from Original v = 'Commander-in-chief Yahweh¦376020 declares that the…76017 silver¦376016 \\add belong¦376017\\add* to me.'
      80 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '9'
      81 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = '*I declare that this ≈temple will be ≈greater in t…peace¦376038 and prosperity to this place¦376035.”'  from Original v = '\\add *I\\add* declare that this \\add ≈temple\\add* w…peace¦376038 and prosperity to this place¦376035.”'
      82 entryWithPreliminaryProcessing=InternalBibleEntry object:
    s1 = 'Haggai consults the priests'
      83 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = '/s1 Blessings Promised for Obedience; Blessings fo…ke and a Promise; The Prophet Consults the Priests'
      84 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      85 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '10'
      86 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'On the 24th of the ninth¦376046 month in¦376044 Ki…essage¦376051 to the prophet¦376057 Haggai¦376056:'  from Original v = 'On the 24th of the ninth¦376046 month in¦376044 \\a…e¦376051\\add* to the prophet¦376057 Haggai¦376056:'
      87 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '11'
      88 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…riests¦376069 about Mosheh's ≈instructions¦376070."  from Original v = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…\\add Mosheh's\\add* \\add ≈instructions¦376070\\add*."
      89 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '12'
      90 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = '‘≈If a priest took some meat¦376078 that had been …ood, would that other food  become¦376102 holy?’ ”'  from Original v = '‘\\add ≈If a priest took some meat¦376078 that had …would that other food \\add* become¦376102 holy?’ ”'
      91 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      92 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p~ = "“No, it wouldn't,” the priests¦376104 ≈replied."  from Original p = "“No, it wouldn't,” the priests¦376104 \\add ≈replied\\add*."
      93 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      94 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '13'
      95 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Then¦376108 Haggai¦376109 asked, “But¦376108 if a …ouched any of that food, would it become unclean?”'  from Original v = 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\…ecome unclean?”\\x + \\xo 2:13: \\xt Num 19:11-22.\\x*'
          adjusted to 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\… of that \\add food\\add*, would it become unclean?”'
         with InternalBibleExtraList object:
  1 xr @ 194 = '+ \\xo 2:13: \\xt Num 19:11-22.'
      96 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      97 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p~ = '“Yes, it would become unclean,” the priests¦376121 answered¦376120.'  from Original p = '“\\add Yes,\\add* it would become unclean,” the priests¦376121 answered¦376120.'
      98 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      99 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '14'
      100 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "“≈That's what Yahweh¦376139 declares about you peo… that same disrespect transfers to your offerings."  from Original v = "“\\add ≈That's what Yahweh¦376139 declares about yo… same disrespect transfers to your offerings\\add*."
      101 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = '/s1 The Lord Promises His Blessing'
      102 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '15'
      103 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."  from Original v = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."
      104 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '16'
      105 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = '≈During that time, when someone went to get twenty…ne from the vat, there was only enough for twenty.'  from Original v = '\\add ≈During that time\\add*, when someone went to …e vat, there was \\add only enough for\\add* twenty.'
      106 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '17'
      107 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Yahweh¦376205 declares that he ≈caused blight¦3761…, ≈but¦376192 you still didn't¦376199 turn to him."  from Original v = "Yahweh¦376205 declares that he \\add ≈caused\\add* b…dd* you \\add still\\add* didn't¦376199 turn to him."
      108 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '18'
      109 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'  from Original v = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'
      110 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '19'
      111 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Is any grain left in¦376234 the storehouse for see…owever, Yahweh will bless you from today onwards.”'  from Original v = 'Is \\add any grain\\add* left in¦376234 the storehou…r,\\add* Yahweh will bless you from today onwards.”'
      112 entryWithPreliminaryProcessing=InternalBibleEntry object:
    s1 = "God's promise to Zerubavel"
      113 entryWithPreliminaryProcessing=InternalBibleEntry object:
    rem = "/s1 The Lord's Promise to Zerubbabel; God's Promis… for Zerubbabel; Zerubbabel the Lord's Signet Ring"
      114 entryWithPreliminaryProcessing=InternalBibleEntry object:
    p = ''
      115 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '20'
      116 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'  from Original v = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'
      117 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '21'
      118 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'  from Original v = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'
      119 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '22'
      120 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "I'll overthrow the thrones¦376283 of kingdoms¦3762…l and related tribes ≈will kill¦376285 each other."  from Original v = "I'll overthrow the thrones¦376283 of kingdoms¦3762…ribes\\add* \\add ≈will kill¦376285 each other\\add*."
      121 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v = '23'
      122 entryWithPreliminaryProcessing=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"  from Original v = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"
    """


    """
    Then _addNestingMarkers reprocesses those 123 lines to get 194 lines
        by inserting end markers like '¬v', '¬p', and many more.

    NOT UP-TO-DATE
    _addNestingMarkers for HAG finishing with len(self._rawLines)=81 len(self._processedLines)=183
      0 entryWithNestingMarkers=InternalBibleEntry object:
    id = "HAG - Open English Translation—Readers' Version (OET-RV) v0.1.03"
      1 entryWithNestingMarkers=InternalBibleEntry object:
    usfm = '3.0'
      2 entryWithNestingMarkers=InternalBibleEntry object:
    ide = 'UTF-8'
      3 entryWithNestingMarkers=InternalBibleEntry object:
    rem = 'ESFM v0.6 HAG'
      4 entryWithNestingMarkers=InternalBibleEntry object:
    rem = 'WORDTABLE OET-LV_OT_word_table.tsv'
      5 entryWithNestingMarkers=InternalBibleEntry object:
    headers = ''  from Original None = None
      6 entryWithNestingMarkers=InternalBibleEntry object:
    h = 'Haggai'
      7 entryWithNestingMarkers=InternalBibleEntry object:
    toc1 = 'Haggai'
      8 entryWithNestingMarkers=InternalBibleEntry object:
    toc2 = 'Haggai'
      9 entryWithNestingMarkers=InternalBibleEntry object:
    toc3 = 'Hag.'
      10 entryWithNestingMarkers=InternalBibleEntry object:
    mt1 = 'Haggai'
      11 entryWithNestingMarkers=InternalBibleEntry object:
    ¬headers = ''  from Original None = None
      12 entryWithNestingMarkers=InternalBibleEntry object:
    intro = ''  from Original None = None
      13 entryWithNestingMarkers=InternalBibleEntry object:
    is1 = 'Introduction'
      14 entryWithNestingMarkers=InternalBibleEntry object:
    ip = 'This document contains a number of messages from Y…osper the people and bless their living situation.'
      15 entryWithNestingMarkers=InternalBibleEntry object:
    iot = 'Main components of this account'
      16 entryWithNestingMarkers=InternalBibleEntry object:
    io1 = "God's command to rebuild the temple 1:1-15"  from Original io1 = "God's command to rebuild the temple \\ior 1:1-15\\ior*"
      17 entryWithNestingMarkers=InternalBibleEntry object:
    io1 = 'Stories of comfort and hope 2:1-23'  from Original io1 = 'Stories of comfort and hope \\ior 2:1-23\\ior*'
      18 entryWithNestingMarkers=InternalBibleEntry object:
    ¬iot = ''  from Original None = None
      19 entryWithNestingMarkers=InternalBibleEntry object:
    rem = 'This is still a very early look into the unfinishe…-check the text in advance before using in public.'
      20 entryWithNestingMarkers=InternalBibleEntry object:
    ie = ''
      21 entryWithNestingMarkers=InternalBibleEntry object:
    ¬intro = ''  from Original None = None
      22 entryWithNestingMarkers=InternalBibleEntry object:
    chapters = ''  from Original None = None
      23 entryWithNestingMarkers=InternalBibleEntry object:
    c = '1'
      24 entryWithNestingMarkers=InternalBibleEntry object:
    s1 = "God's command to rebuild the temple"
      25 entryWithNestingMarkers=InternalBibleEntry object:
    rem = "/s1 The Lord's Command to Rebuild the Temple; A Ca…use of the Lord; The Command to Rebuild the Temple"
      26 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      27 entryWithNestingMarkers=InternalBibleEntry object:
    c# = '1'  from Original c = '1'
      28 entryWithNestingMarkers=InternalBibleEntry object:
    v = '1'
      29 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "In Dareyavesh's (Darius's¦375563) second year¦3755…oshua (Yehotsadak's¦375591 son), telling them that"  from Original v = "In Dareyavesh's \\add (Darius's¦375563)\\add* second… that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*"
          adjusted to "In Dareyavesh's \\add (Darius's¦375563)\\add* second…otsadak's¦375591 son), telling \\add them that\\add*"
         with InternalBibleExtraList object:
  1 xr @ 403 = '+ \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.'
      30 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '1'  from Original None = None
      31 entryWithNestingMarkers=InternalBibleEntry object:
    v = '2'
      32 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh says, “These people¦3756…ime to rebuild¦375612 Yahweh's¦375598 ≈residence.”"  from Original v = "Commander-in-chief Yahweh says, “These people¦3756…uild¦375612 Yahweh's¦375598 \\add ≈residence\\add*.”"
      33 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '2'  from Original None = None
      34 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      35 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      36 entryWithNestingMarkers=InternalBibleEntry object:
    v = '3'
      37 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Then Yahweh¦375618 ≈gave this message¦375616 to th…e prophet¦375622 Haggai¦375621 to tell the people:'  from Original v = 'Then Yahweh¦375618 \\add ≈gave this message¦375616\\…375622 Haggai¦375621 \\add to tell the people\\add*:'
      38 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '3'  from Original None = None
      39 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      40 entryWithNestingMarkers=InternalBibleEntry object:
    m = ''
      41 entryWithNestingMarkers=InternalBibleEntry object:
    v = '4'
      42 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Is it a time¦375625 for all of you to live in your…uses¦375629, while ≈Yahweh's temple lies in ruins?"  from Original v = "Is it a time¦375625 for all of you to live in your…9, while \\add ≈Yahweh's temple lies in ruins\\add*?"
      43 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '4'  from Original None = None
      44 entryWithNestingMarkers=InternalBibleEntry object:
    v = '5'
      45 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "≈So¦375635 now Commander-in-chief Yahweh¦375638 says¦375637: “≈Decide what you're all going to do."  from Original v = "\\add ≈So¦375635\\add* now Commander-in-chief Yahweh…7: “\\add ≈Decide what you're all going to do\\add*."
      46 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '5'  from Original None = None
      47 entryWithNestingMarkers=InternalBibleEntry object:
    v = '6'
      48 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "You've all planted a lot, ≈but only harvested¦3756…75664, but your pockets seem to be full of holes.”"  from Original v = "You've all planted a lot, \\add ≈but only harvested…, but your pockets seem to be full of holes\\add*.”"
      49 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '6'  from Original None = None
      50 entryWithNestingMarkers=InternalBibleEntry object:
    ¬m = ''  from Original None = None
      51 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      52 entryWithNestingMarkers=InternalBibleEntry object:
    v = '7'
      53 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "≈So Commander-in-chief Yahweh¦375673 says¦375672 again: “≈Decide what you're all going to do."  from Original v = "\\add ≈So\\add* Commander-in-chief Yahweh¦375673 say…*: “\\add ≈Decide what you're all going to do\\add*."
      54 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '7'  from Original None = None
      55 entryWithNestingMarkers=InternalBibleEntry object:
    v = '8'
      56 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'  from Original v = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'
      57 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '8'  from Original None = None
      58 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      59 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      60 entryWithNestingMarkers=InternalBibleEntry object:
    v = '9'
      61 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "“You ≈expected much, but¦375699 gained little¦3757…while you're all busy ≈working on your own houses."  from Original v = '“You \\add ≈expected\\add* much, but¦375699 \\add gai…d busy\\add* \\add ≈working on\\add* your own houses.'
      62 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '9'  from Original None = None
      63 entryWithNestingMarkers=InternalBibleEntry object:
    v = '10'
      64 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."  from Original v = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."
      65 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '10'  from Original None = None
      66 entryWithNestingMarkers=InternalBibleEntry object:
    v = '11'
      67 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "I've¦375735 ≈summoned¦375735 a drought¦375736 onto…e and livestock, and onto ≈everything you all do.”"  from Original v = "I've¦375735 \\add ≈summoned¦375735\\add* a drought¦3…stock, and onto \\add ≈everything you all do\\add*.”"
      68 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '11'  from Original None = None
      69 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      70 entryWithNestingMarkers=InternalBibleEntry object:
    s1 = 'The people start rebuilding'
      71 entryWithNestingMarkers=InternalBibleEntry object:
    rem = "/s1 The People Obey the Lord's Command; Obedience to God's Call"
      72 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      73 entryWithNestingMarkers=InternalBibleEntry object:
    v = '12'
      74 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…od had sent him, and the people ≈respected Yahweh."  from Original v = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…t him, and the people \\add ≈respected\\add* Yahweh."
      75 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '12'  from Original None = None
      76 entryWithNestingMarkers=InternalBibleEntry object:
    v = '13'
      77 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"  from Original v = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"
      78 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '13'  from Original None = None
      79 entryWithNestingMarkers=InternalBibleEntry object:
    v = '14'
      80 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Then¦375816 Yahweh ≈inspired Shealtiyel's son Zeru…heir¦375849 god¦375849, Commander-in-chief Yahweh,"  from Original v = "Then¦375816 Yahweh \\add ≈inspired\\add* Shealtiyel'…heir¦375849 god¦375849, Commander-in-chief Yahweh,"
      81 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '14'  from Original None = None
      82 entryWithNestingMarkers=InternalBibleEntry object:
    v = '15'
      83 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'on¦375856 the twenty-fourth day¦375852 of the sixt…ar¦375857 of Dareyavesh the king¦375860 of Persia.'  from Original v = 'on¦375856 the twenty-fourth day¦375852 of the sixt…of Dareyavesh the king¦375860 \\add of Persia\\add*.'
      84 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '15'  from Original None = None
      85 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      86 entryWithNestingMarkers=InternalBibleEntry object:
    ¬c = '1'  from Original None = None
      87 entryWithNestingMarkers=InternalBibleEntry object:
    c = '2'
      88 entryWithNestingMarkers=InternalBibleEntry object:
    s1 = 'The splendour of the new temple'
      89 entryWithNestingMarkers=InternalBibleEntry object:
    rem = '/s1 The Future Glory of the Temple; The New Temple…he New Temple; The Promised Glory of the New House'
      90 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      91 entryWithNestingMarkers=InternalBibleEntry object:
    c# = '2'  from Original c = '2'
      92 entryWithNestingMarkers=InternalBibleEntry object:
    v = '1'
      93 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'On the 21st of the seventh¦375862 month (about a m…ke again through the prophet¦375873 Haggai¦375872:'  from Original v = 'On the 21st of the seventh¦375862 month \\add (abou…ain\\add* through the prophet¦375873 Haggai¦375872:'
      94 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '1'  from Original None = None
      95 entryWithNestingMarkers=InternalBibleEntry object:
    v = '2'
      96 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Please ≈ask Shealtiyel's son Zerubavel, the govern…st¦375893, and ≈ask the rest of the people¦375898,"  from Original v = "Please \\add ≈ask\\add* Shealtiyel's son Zerubavel, … and \\add ≈ask\\add* the rest of the people¦375898,"
      97 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '2'  from Original None = None
      98 entryWithNestingMarkers=InternalBibleEntry object:
    v = '3'
      99 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = '“≈Are there any of you still alive who saw¦375905 …tty much like nothing¦375919 in¦375902 comparison.'  from Original v = '“\\add ≈Are there any of you still alive who saw¦37…902 comparison\\add*.\\x + \\xo 2:3: \\xt Ezr 3:12.\\x*'
          adjusted to '“\\add ≈Are there any of you still alive who saw¦37…+em nothing¦375919\\+em* in¦375902 comparison\\add*.'
         with InternalBibleExtraList object:
  1 xr @ 230 = '+ \\xo 2:3: \\xt Ezr 3:12.'
      100 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '3'  from Original None = None
      101 entryWithNestingMarkers=InternalBibleEntry object:
    v = '4'
      102 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Yahweh is telling you now, Zerubavel, to be strong…eh declares that I'm with you ≈as you work¦375944."  from Original v = "Yahweh is telling you now, Zerubavel, to be strong…s that I'm with you \\add ≈as you work¦375944\\add*."
      103 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '4'  from Original None = None
      104 entryWithNestingMarkers=InternalBibleEntry object:
    v = '5'
      105 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "≈That's what I promised¦375955 your¦375964 ancesto…¦375964 you¦375960. Don't¦375965 be afraid¦375967,"  from Original v = "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
          adjusted to "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
         with InternalBibleExtraList object:
  1 xr @ 105 = '+ \\xo 2:5: \\xt Exo 29:45-46.'
      106 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '5'  from Original None = None
      107 entryWithNestingMarkers=InternalBibleEntry object:
    v = '6'
      108 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'  from Original v = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…ry land, once more.\\x + \\xo 2:6: \\xt Heb 12:26.\\x*'
          adjusted to 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'
         with InternalBibleExtraList object:
  1 xr @ 200 = '+ \\xo 2:6: \\xt Heb 12:26.'
      109 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '6'  from Original None = None
      110 entryWithNestingMarkers=InternalBibleEntry object:
    v = '7'
      111 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."  from Original v = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."
      112 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '7'  from Original None = None
      113 entryWithNestingMarkers=InternalBibleEntry object:
    v = '8'
      114 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Commander-in-chief Yahweh¦376020 declares that the…6018 and¦376017 silver¦376016 belong¦376017 to me.'  from Original v = 'Commander-in-chief Yahweh¦376020 declares that the…76017 silver¦376016 \\add belong¦376017\\add* to me.'
      115 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '8'  from Original None = None
      116 entryWithNestingMarkers=InternalBibleEntry object:
    v = '9'
      117 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = '*I declare that this ≈temple will be ≈greater in t…peace¦376038 and prosperity to this place¦376035.”'  from Original v = '\\add *I\\add* declare that this \\add ≈temple\\add* w…peace¦376038 and prosperity to this place¦376035.”'
      118 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '9'  from Original None = None
      119 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      120 entryWithNestingMarkers=InternalBibleEntry object:
    s1 = 'Haggai consults the priests'
      121 entryWithNestingMarkers=InternalBibleEntry object:
    rem = '/s1 Blessings Promised for Obedience; Blessings fo…ke and a Promise; The Prophet Consults the Priests'
      122 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      123 entryWithNestingMarkers=InternalBibleEntry object:
    v = '10'
      124 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'On the 24th of the ninth¦376046 month in¦376044 Ki…essage¦376051 to the prophet¦376057 Haggai¦376056:'  from Original v = 'On the 24th of the ninth¦376046 month in¦376044 \\a…e¦376051\\add* to the prophet¦376057 Haggai¦376056:'
      125 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '10'  from Original None = None
      126 entryWithNestingMarkers=InternalBibleEntry object:
    v = '11'
      127 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…riests¦376069 about Mosheh's ≈instructions¦376070."  from Original v = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…\\add Mosheh's\\add* \\add ≈instructions¦376070\\add*."
      128 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '11'  from Original None = None
      129 entryWithNestingMarkers=InternalBibleEntry object:
    v = '12'
      130 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = '‘≈If a priest took some meat¦376078 that had been …ood, would that other food  become¦376102 holy?’ ”'  from Original v = '‘\\add ≈If a priest took some meat¦376078 that had …would that other food \\add* become¦376102 holy?’ ”'
      131 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      132 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      133 entryWithNestingMarkers=InternalBibleEntry object:
    p~ = "“No, it wouldn't,” the priests¦376104 ≈replied."  from Original p = "“No, it wouldn't,” the priests¦376104 \\add ≈replied\\add*."
      134 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      135 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '12'  from Original None = None
      136 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      137 entryWithNestingMarkers=InternalBibleEntry object:
    v = '13'
      138 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Then¦376108 Haggai¦376109 asked, “But¦376108 if a …ouched any of that food, would it become unclean?”'  from Original v = 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\…ecome unclean?”\\x + \\xo 2:13: \\xt Num 19:11-22.\\x*'
          adjusted to 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\… of that \\add food\\add*, would it become unclean?”'
         with InternalBibleExtraList object:
  1 xr @ 194 = '+ \\xo 2:13: \\xt Num 19:11-22.'
      139 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      140 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      141 entryWithNestingMarkers=InternalBibleEntry object:
    p~ = '“Yes, it would become unclean,” the priests¦376121 answered¦376120.'  from Original p = '“\\add Yes,\\add* it would become unclean,” the priests¦376121 answered¦376120.'
      142 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      143 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '13'  from Original None = None
      144 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      145 entryWithNestingMarkers=InternalBibleEntry object:
    v = '14'
      146 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "“≈That's what Yahweh¦376139 declares about you peo… that same disrespect transfers to your offerings."  from Original v = "“\\add ≈That's what Yahweh¦376139 declares about yo… same disrespect transfers to your offerings\\add*."
      147 entryWithNestingMarkers=InternalBibleEntry object:
    rem = '/s1 The Lord Promises His Blessing'
      148 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '14'  from Original None = None
      149 entryWithNestingMarkers=InternalBibleEntry object:
    v = '15'
      150 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."  from Original v = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."
      151 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '15'  from Original None = None
      152 entryWithNestingMarkers=InternalBibleEntry object:
    v = '16'
      153 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = '≈During that time, when someone went to get twenty…ne from the vat, there was only enough for twenty.'  from Original v = '\\add ≈During that time\\add*, when someone went to …e vat, there was \\add only enough for\\add* twenty.'
      154 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '16'  from Original None = None
      155 entryWithNestingMarkers=InternalBibleEntry object:
    v = '17'
      156 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Yahweh¦376205 declares that he ≈caused blight¦3761…, ≈but¦376192 you still didn't¦376199 turn to him."  from Original v = "Yahweh¦376205 declares that he \\add ≈caused\\add* b…dd* you \\add still\\add* didn't¦376199 turn to him."
      157 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '17'  from Original None = None
      158 entryWithNestingMarkers=InternalBibleEntry object:
    v = '18'
      159 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'  from Original v = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'
      160 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '18'  from Original None = None
      161 entryWithNestingMarkers=InternalBibleEntry object:
    v = '19'
      162 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Is any grain left in¦376234 the storehouse for see…owever, Yahweh will bless you from today onwards.”'  from Original v = 'Is \\add any grain\\add* left in¦376234 the storehou…r,\\add* Yahweh will bless you from today onwards.”'
      163 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '19'  from Original None = None
      164 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      165 entryWithNestingMarkers=InternalBibleEntry object:
    s1 = "God's promise to Zerubavel"
      166 entryWithNestingMarkers=InternalBibleEntry object:
    rem = "/s1 The Lord's Promise to Zerubbabel; God's Promis… for Zerubbabel; Zerubbabel the Lord's Signet Ring"
      167 entryWithNestingMarkers=InternalBibleEntry object:
    p = ''
      168 entryWithNestingMarkers=InternalBibleEntry object:
    v = '20'
      169 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'  from Original v = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'
      170 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '20'  from Original None = None
      171 entryWithNestingMarkers=InternalBibleEntry object:
    v = '21'
      172 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'  from Original v = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'
      173 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '21'  from Original None = None
      174 entryWithNestingMarkers=InternalBibleEntry object:
    v = '22'
      175 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "I'll overthrow the thrones¦376283 of kingdoms¦3762…l and related tribes ≈will kill¦376285 each other."  from Original v = "I'll overthrow the thrones¦376283 of kingdoms¦3762…ribes\\add* \\add ≈will kill¦376285 each other\\add*."
      176 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '22'  from Original None = None
      177 entryWithNestingMarkers=InternalBibleEntry object:
    v = '23'
      178 entryWithNestingMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"  from Original v = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"
      179 entryWithNestingMarkers=InternalBibleEntry object:
    ¬v = '23'  from Original None = None
      180 entryWithNestingMarkers=InternalBibleEntry object:
    ¬p = ''  from Original None = None
      181 entryWithNestingMarkers=InternalBibleEntry object:
    ¬c = '2'  from Original None = None
      182 entryWithNestingMarkers=InternalBibleEntry object:
    ¬chapters = ''
    """

    """
    Then addVerseStartMarker() is called on this 183 lines but after adding 'v=' pseudolines
        it finishes with 188 lines.

   addVerseStartMarkers for HAG finishing with len(self._rawLines)=81 len(self._processedLines)=188

      0 entryWithVerseStartMarkers=InternalBibleEntry object:
    id = "HAG - Open English Translation—Readers' Version (OET-RV) v0.1.03"
      1 entryWithVerseStartMarkers=InternalBibleEntry object:
    usfm = '3.0'
      2 entryWithVerseStartMarkers=InternalBibleEntry object: ide = 'UTF-8'
      3 entryWithVerseStartMarkers=InternalBibleEntry object: rem = 'ESFM v0.6 HAG'
      4 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = 'WORDTABLE OET-LV_OT_word_table.tsv'
      5 entryWithVerseStartMarkers=InternalBibleEntry object:
    headers = '' from Original None = None = None
      6 entryWithVerseStartMarkers=InternalBibleEntry object: h = 'Haggai'
      7 entryWithVerseStartMarkers=InternalBibleEntry object: toc1 = 'Haggai'
      8 entryWithVerseStartMarkers=InternalBibleEntry object: toc2 = 'Haggai'
      9 entryWithVerseStartMarkers=InternalBibleEntry object: toc3 = 'Hag.'
      10 entryWithVerseStartMarkers=InternalBibleEntry object: mt1 = 'Haggai'
      11 entryWithVerseStartMarkers=InternalBibleEntry object: ¬headers = '' from Original None = None = None
      12 entryWithVerseStartMarkers=InternalBibleEntry object:
    intro = '' from Original None = None = None
      13 entryWithVerseStartMarkers=InternalBibleEntry object: is1 = 'Introduction'
      14 entryWithVerseStartMarkers=InternalBibleEntry object:
    ip = 'This document contains a number of messages from Y…osper the people and bless their living situation.'
      15 entryWithVerseStartMarkers=InternalBibleEntry object:
    iot = 'Main components of this account'
      16 entryWithVerseStartMarkers=InternalBibleEntry object:
    io1 = "God's command to rebuild the temple 1:1-15"
  from Original io1 = "God's command to rebuild the temple \\ior 1:1-15\\ior*"
      17 entryWithVerseStartMarkers=InternalBibleEntry object:
    io1 = 'Stories of comfort and hope 2:1-23'
  from Original io1 = 'Stories of comfort and hope \\ior 2:1-23\\ior*'
      18 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬iot = '' from Original None = None = None
      19 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = 'This is still a very early look into the unfinishe…-check the text in advance before using in public.'
      20 entryWithVerseStartMarkers=InternalBibleEntry object:
    ie = ''
      21 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬intro = '' from Original None = None = None
      22 entryWithVerseStartMarkers=InternalBibleEntry object:
    chapters = '' from Original None = None = None
      23 entryWithVerseStartMarkers=InternalBibleEntry object: c = '1'
      24 entryWithVerseStartMarkers=InternalBibleEntry object: v= = '1'
  from Original v = '1'
      25 entryWithVerseStartMarkers=InternalBibleEntry object:
    s1 = "God's command to rebuild the temple"
      26 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = "/s1 The Lord's Command to Rebuild the Temple; A Ca…use of the Lord; The Command to Rebuild the Temple"
      27 entryWithVerseStartMarkers=InternalBibleEntry object: p = ''
      28 entryWithVerseStartMarkers=InternalBibleEntry object: c# = '1'
  from Original c = '1'
      29 entryWithVerseStartMarkers=InternalBibleEntry object: v = '1'
      30 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "In Dareyavesh's (Darius's¦375563) second year¦3755…oshua (Yehotsadak's¦375591 son), telling them that"
  from Original v = "In Dareyavesh's \\add (Darius's¦375563)\\add* second… that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*"
          adjusted to "In Dareyavesh's \\add (Darius's¦375563)\\add* second…otsadak's¦375591 son), telling \\add them that\\add*"
         with InternalBibleExtraList object:
  1 xr @ 403 = '+ \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.'
      31 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '1' from Original None = None = None
      32 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '2'
      33 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh says, “These people¦3756…ime to rebuild¦375612 Yahweh's¦375598 ≈residence.”"
  from Original v = "Commander-in-chief Yahweh says, “These people¦3756…uild¦375612 Yahweh's¦375598 \\add ≈residence\\add*.”"
      34 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '2' from Original None = None = None
      35 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      36 entryWithVerseStartMarkers=InternalBibleEntry object: p = ''
      37 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '3'
      38 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Then Yahweh¦375618 ≈gave this message¦375616 to th…e prophet¦375622 Haggai¦375621 to tell the people:'
  from Original v = 'Then Yahweh¦375618 \\add ≈gave this message¦375616\\…375622 Haggai¦375621 \\add to tell the people\\add*:'
      39 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '3' from Original None = None = None
      40 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      41 entryWithVerseStartMarkers=InternalBibleEntry object: m = ''
      42 entryWithVerseStartMarkers=InternalBibleEntry object: v = '4'
      43 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Is it a time¦375625 for all of you to live in your…uses¦375629, while ≈Yahweh's temple lies in ruins?"
  from Original v = "Is it a time¦375625 for all of you to live in your…9, while \\add ≈Yahweh's temple lies in ruins\\add*?"
      44 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '4' from Original None = None = None
      45 entryWithVerseStartMarkers=InternalBibleEntry object: v = '5'
      46 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "≈So¦375635 now Commander-in-chief Yahweh¦375638 says¦375637: “≈Decide what you're all going to do."
  from Original v = "\\add ≈So¦375635\\add* now Commander-in-chief Yahweh…7: “\\add ≈Decide what you're all going to do\\add*."
      47 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '5' from Original None = None = None
      48 entryWithVerseStartMarkers=InternalBibleEntry object: v = '6'
      49 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "You've all planted a lot, ≈but only harvested¦3756…75664, but your pockets seem to be full of holes.”"
  from Original v = "You've all planted a lot, \\add ≈but only harvested…, but your pockets seem to be full of holes\\add*.”"
      50 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '6' from Original None = None = None
      51 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬m = '' from Original None = None = None
      52 entryWithVerseStartMarkers=InternalBibleEntry object: p = ''
      53 entryWithVerseStartMarkers=InternalBibleEntry object: v = '7'
      54 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "≈So Commander-in-chief Yahweh¦375673 says¦375672 again: “≈Decide what you're all going to do."
  from Original v = "\\add ≈So\\add* Commander-in-chief Yahweh¦375673 say…*: “\\add ≈Decide what you're all going to do\\add*."
      55 entryWithVerseStartMarkers=InternalBibleEntry object: ¬v = '7' from Original None = None = None
      56 entryWithVerseStartMarkers=InternalBibleEntry object: v = '8'
      57 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'
  from Original v = 'Go up into the hills¦375682 and bring¦375683 back … and honour¦375690 me,” says¦375692 Yahweh¦375693.'
      58 entryWithVerseStartMarkers=InternalBibleEntry object: ¬v = '8' from Original None = None = None
      59 entryWithVerseStartMarkers=InternalBibleEntry object: ¬p = '' from Original None = None = None
      60 entryWithVerseStartMarkers=InternalBibleEntry object: p = ''
      61 entryWithVerseStartMarkers=InternalBibleEntry object: v = '9'
      62 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "“You ≈expected much, but¦375699 gained little¦3757…while you're all busy ≈working on your own houses."
  from Original v = '“You \\add ≈expected\\add* much, but¦375699 \\add gai…d busy\\add* \\add ≈working on\\add* your own houses.'
      63 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '9' from Original None = None = None
      64 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '10'
      65 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."
  from Original v = "That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops."
      66 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '10' from Original None = None = None
      67 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '11'
      68 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "I've¦375735 ≈summoned¦375735 a drought¦375736 onto…e and livestock, and onto ≈everything you all do.”"
  from Original v = "I've¦375735 \\add ≈summoned¦375735\\add* a drought¦3…stock, and onto \\add ≈everything you all do\\add*.”"
      69 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '11' from Original None = None = None
      70 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      71 entryWithVerseStartMarkers=InternalBibleEntry object:
    v= = '12'
  from Original v = '12'
      72 entryWithVerseStartMarkers=InternalBibleEntry object:
    s1 = 'The people start rebuilding'
      73 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = "/s1 The People Obey the Lord's Command; Obedience to God's Call"
      74 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      75 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '12'
      76 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…od had sent him, and the people ≈respected Yahweh."
  from Original v = "Then Shealtiyel's son Zerubavel and Yehotsadak's s…t him, and the people \\add ≈respected\\add* Yahweh."
      77 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '12' from Original None = None = None
      78 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '13'
      79 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"
  from Original v = "Then¦375802 Yahweh's¦375805 messenger¦375804 Hagga…weh declares that I'm with¦375806 you¦375811 all.”"
      80 entryWithVerseStartMarkers=InternalBibleEntry object: ¬v = '13' from Original None = None = None
      81 entryWithVerseStartMarkers=InternalBibleEntry object: v = '14'
      82 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Then¦375816 Yahweh ≈inspired Shealtiyel's son Zeru…heir¦375849 god¦375849, Commander-in-chief Yahweh,"
  from Original v = "Then¦375816 Yahweh \\add ≈inspired\\add* Shealtiyel'…heir¦375849 god¦375849, Commander-in-chief Yahweh,"
      83 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '14' from Original None = None = None
      84 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '15'
      85 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'on¦375856 the twenty-fourth day¦375852 of the sixt…ar¦375857 of Dareyavesh the king¦375860 of Persia.'
  from Original v = 'on¦375856 the twenty-fourth day¦375852 of the sixt…of Dareyavesh the king¦375860 \\add of Persia\\add*.'
      86 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '15' from Original None = None = None
      87 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      88 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬c = '1' from Original None = None = None
      89 entryWithVerseStartMarkers=InternalBibleEntry object:
    c = '2'
      90 entryWithVerseStartMarkers=InternalBibleEntry object:
    v= = '1'
  from Original v = '1'
      91 entryWithVerseStartMarkers=InternalBibleEntry object:
    s1 = 'The splendour of the new temple'
      92 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = '/s1 The Future Glory of the Temple; The New Temple…he New Temple; The Promised Glory of the New House'
      93 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      94 entryWithVerseStartMarkers=InternalBibleEntry object:
    c# = '2'
  from Original c = '2'
      95 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '1'
      96 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'On the 21st of the seventh¦375862 month (about a m…ke again through the prophet¦375873 Haggai¦375872:'
  from Original v = 'On the 21st of the seventh¦375862 month \\add (abou…ain\\add* through the prophet¦375873 Haggai¦375872:'
      97 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '1' from Original None = None = None
      98 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '2'
      99 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Please ≈ask Shealtiyel's son Zerubavel, the govern…st¦375893, and ≈ask the rest of the people¦375898,"
  from Original v = "Please \\add ≈ask\\add* Shealtiyel's son Zerubavel, … and \\add ≈ask\\add* the rest of the people¦375898,"
      100 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '2' from Original None = None = None
      101 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '3'
      102 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = '“≈Are there any of you still alive who saw¦375905 …tty much like nothing¦375919 in¦375902 comparison.'
  from Original v = '“\\add ≈Are there any of you still alive who saw¦37…902 comparison\\add*.\\x + \\xo 2:3: \\xt Ezr 3:12.\\x*'
          adjusted to '“\\add ≈Are there any of you still alive who saw¦37…+em nothing¦375919\\+em* in¦375902 comparison\\add*.'
         with InternalBibleExtraList object:
  1 xr @ 230 = '+ \\xo 2:3: \\xt Ezr 3:12.'
      103 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '3' from Original None = None = None
      104 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '4'
      105 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Yahweh is telling you now, Zerubavel, to be strong…eh declares that I'm with you ≈as you work¦375944."
  from Original v = "Yahweh is telling you now, Zerubavel, to be strong…s that I'm with you \\add ≈as you work¦375944\\add*."
      106 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '4' from Original None = None = None
      107 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '5'
      108 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "≈That's what I promised¦375955 your¦375964 ancesto…¦375964 you¦375960. Don't¦375965 be afraid¦375967,"
  from Original v = "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
          adjusted to "\\add ≈That's what I promised¦375955 your¦375964 an…64 you¦375960\\add*. Don't¦375965 be afraid¦375967,"
         with InternalBibleExtraList object:
  1 xr @ 105 = '+ \\xo 2:5: \\xt Exo 29:45-46.'
      109 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '5' from Original None = None = None
      110 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '6'
      111 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'
  from Original v = 'because¦375970 Commander-in-chief Yahweh¦375973 sa…ry land, once more.\\x + \\xo 2:6: \\xt Heb 12:26.\\x*'
          adjusted to 'because¦375970 Commander-in-chief Yahweh¦375973 sa…75986, the sea¦375989 and the dry land, once more.'
         with InternalBibleExtraList object:
  1 xr @ 200 = '+ \\xo 2:6: \\xt Heb 12:26.'
      112 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '6' from Original None = None = None
      113 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '7'
      114 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."
  from Original v = "I'll shake¦375994 all the nations, and¦375994 they…our¦376010, says Commander-in-chief Yahweh¦376012."
      115 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '7' from Original None = None = None
      116 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '8'
      117 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Commander-in-chief Yahweh¦376020 declares that the…6018 and¦376017 silver¦376016 belong¦376017 to me.'
  from Original v = 'Commander-in-chief Yahweh¦376020 declares that the…76017 silver¦376016 \\add belong¦376017\\add* to me.'
      118 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '8' from Original None = None = None
      119 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '9'
      120 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = '*I declare that this ≈temple will be ≈greater in t…peace¦376038 and prosperity to this place¦376035.”'
  from Original v = '\\add *I\\add* declare that this \\add ≈temple\\add* w…peace¦376038 and prosperity to this place¦376035.”'
      121 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '9' from Original None = None = None
      122 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      123 entryWithVerseStartMarkers=InternalBibleEntry object:
    v= = '10'
  from Original v = '10'
      124 entryWithVerseStartMarkers=InternalBibleEntry object:
    s1 = 'Haggai consults the priests'
      125 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = '/s1 Blessings Promised for Obedience; Blessings fo…ke and a Promise; The Prophet Consults the Priests'
      126 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      127 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '10'
      128 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'On the 24th of the ninth¦376046 month in¦376044 Ki…essage¦376051 to the prophet¦376057 Haggai¦376056:'
  from Original v = 'On the 24th of the ninth¦376046 month in¦376044 \\a…e¦376051\\add* to the prophet¦376057 Haggai¦376056:'
      129 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '10' from Original None = None = None
      130 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '11'
      131 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…riests¦376069 about Mosheh's ≈instructions¦376070."
  from Original v = "Commander-in-chief Yahweh¦376062 says¦376061, “Ask…\\add Mosheh's\\add* \\add ≈instructions¦376070\\add*."
      132 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '11' from Original None = None = None
      133 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '12'
      134 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = '‘≈If a priest took some meat¦376078 that had been …ood, would that other food  become¦376102 holy?’ ”'
  from Original v = '‘\\add ≈If a priest took some meat¦376078 that had …would that other food \\add* become¦376102 holy?’ ”'
      135 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      136 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      137 entryWithVerseStartMarkers=InternalBibleEntry object:
    p~ = "“No, it wouldn't,” the priests¦376104 ≈replied."
  from Original p = "“No, it wouldn't,” the priests¦376104 \\add ≈replied\\add*."
      138 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      139 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '12' from Original None = None = None
      140 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      141 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '13'
      142 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Then¦376108 Haggai¦376109 asked, “But¦376108 if a …ouched any of that food, would it become unclean?”'
  from Original v = 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\…ecome unclean?”\\x + \\xo 2:13: \\xt Num 19:11-22.\\x*'
          adjusted to 'Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\… of that \\add food\\add*, would it become unclean?”'
         with InternalBibleExtraList object:
  1 xr @ 194 = '+ \\xo 2:13: \\xt Num 19:11-22.'
      143 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      144 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      145 entryWithVerseStartMarkers=InternalBibleEntry object:
    p~ = '“Yes, it would become unclean,” the priests¦376121 answered¦376120.'
  from Original p = '“\\add Yes,\\add* it would become unclean,” the priests¦376121 answered¦376120.'
      146 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      147 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '13' from Original None = None = None
      148 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      149 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '14'
      150 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "“≈That's what Yahweh¦376139 declares about you peo… that same disrespect transfers to your offerings."
  from Original v = "“\\add ≈That's what Yahweh¦376139 declares about yo… same disrespect transfers to your offerings\\add*."
      151 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = '/s1 The Lord Promises His Blessing'
      152 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '14' from Original None = None = None
      153 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '15'
      154 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."
  from Original v = "So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple."
      155 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '15' from Original None = None = None
      156 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '16'
      157 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = '≈During that time, when someone went to get twenty…ne from the vat, there was only enough for twenty.'
  from Original v = '\\add ≈During that time\\add*, when someone went to …e vat, there was \\add only enough for\\add* twenty.'
      158 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '16' from Original None = None = None
      159 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '17'
      160 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Yahweh¦376205 declares that he ≈caused blight¦3761…, ≈but¦376192 you still didn't¦376199 turn to him."
  from Original v = "Yahweh¦376205 declares that he \\add ≈caused\\add* b…dd* you \\add still\\add* didn't¦376199 turn to him."
      161 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '17' from Original None = None = None
      162 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '18'
      163 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'
  from Original v = 'Think back to the time from when the foundation¦37… of the ninth¦376219 month¦376219). Consider that.'
      164 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '18' from Original None = None = None
      165 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '19'
      166 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Is any grain left in¦376234 the storehouse for see…owever, Yahweh will bless you from today onwards.”'
  from Original v = 'Is \\add any grain\\add* left in¦376234 the storehou…r,\\add* Yahweh will bless you from today onwards.”'
      167 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '19' from Original None = None = None
      168 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      169 entryWithVerseStartMarkers=InternalBibleEntry object:
    v= = '20'
  from Original v = '20'
      170 entryWithVerseStartMarkers=InternalBibleEntry object:
    s1 = "God's promise to Zerubavel"
      171 entryWithVerseStartMarkers=InternalBibleEntry object:
    rem = "/s1 The Lord's Promise to Zerubbabel; God's Promis… for Zerubbabel; Zerubbabel the Lord's Signet Ring"
      172 entryWithVerseStartMarkers=InternalBibleEntry object:
    p = ''
      173 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '20'
      174 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'
  from Original v = 'Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:'
      175 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '20' from Original None = None = None
      176 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '21'
      177 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'
  from Original v = 'Tell Zerubavel, the governor¦376269 of Yehudah¦376…ke¦376274 the heavens¦376277 and the earth¦376280.'
      178 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '21' from Original None = None = None
      179 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '22'
      180 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "I'll overthrow the thrones¦376283 of kingdoms¦3762…l and related tribes ≈will kill¦376285 each other."
  from Original v = "I'll overthrow the thrones¦376283 of kingdoms¦3762…ribes\\add* \\add ≈will kill¦376285 each other\\add*."
      181 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '22' from Original None = None = None
      182 entryWithVerseStartMarkers=InternalBibleEntry object:
    v = '23'
      183 entryWithVerseStartMarkers=InternalBibleEntry object:
    v~ = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"
  from Original v = "Commander-in-chief Yahweh declares that on that da…315 ring, because¦376316 he's been chosen¦376319.”"
      184 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬v = '23' from Original None = None = None
      185 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬p = '' from Original None = None = None
      186 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬c = '2' from Original None = None = None
      187 entryWithVerseStartMarkers=InternalBibleEntry object:
    ¬chapters = '' from Original None = None = None

    188 originalMarkerList=['id', 'usfm', 'ide', 'rem', 'rem', None, 'h', 'toc1', 'toc2', 'toc3', 'mt1', None, None, 'is1', 'ip', 'iot', 'io1', 'io1', None, 'rem', 'ie', None, None, 'c', 'v', 's1', 'rem', 'p', 'c', 'v', 'v', None, 'v', 'v', None, None, 'p', 'v', 'v', None, None, 'm', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, 'p', 'v', 'v', None, 'v', 'v', None, None, 'p', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, 'v', 's1', 'rem', 'p', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, None, 'c', 'v', 's1', 'rem', 'p', 'c', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, 'v', 's1', 'rem', 'p', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'p', 'p', None, None, 'p', 'v', 'v', None, 'p', 'p', None, None, 'p', 'v', 'v', 'rem', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, 'v', 's1', 'rem', 'p', 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, 'v', 'v', None, None, None, None]
    188 adjustedMarkerList=['id', 'usfm', 'ide', 'rem', 'rem', 'headers', 'h', 'toc1', 'toc2', 'toc3', 'mt1', '¬headers', 'intro', 'is1', 'ip', 'iot', 'io1', 'io1', '¬iot', 'rem', 'ie', '¬intro', 'chapters', 'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', '¬p', 'm', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬m', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c', 'c', 'v=', 's1', 'rem', 'p', 'c#', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬p', 'p', 'XXXp~', '¬p', '¬v', 'p', 'v', 'v~', '¬p', 'p', 'XXXp~', '¬p', '¬v', 'p', 'v', 'v~', 'rem', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', 'v=', 's1', 'rem', 'p', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', 'v', 'v~', '¬v', '¬p', '¬c', '¬chapters']
    """
    
    if 1: # Check that it loaded correctly
        from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
        from bible_organisational_system import InternalBibleEntry
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "Displaying ESFM text from some given references…" )
        for thisBBB,C,V in ( (BBB,'1','1'),(BBB,'1','2'),(BBB,'1','3'),(BBB,'1','4'),(BBB,'1','5'),(BBB,'1','6'),(BBB,'2','1'),(BBB,'2','23') ):
            svk = SimpleVerseKey( thisBBB, C, V )
            shortText = svk.getShortText()
            verseDataList = EsfmBib.getVerseDataList( svk )
            if BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n{shortText}\n{verseDataList}" )
            if verseDataList is None: continue
            for verseDataEntry in verseDataList:
                # This loop is used for several types of data
                assert isinstance( verseDataEntry, InternalBibleEntry )
                marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                adjustedText, original_text = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                fullText = verseDataEntry.getFullText()
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "marker={} cleanText={!r}{}".format( marker, cleanText,
                                            f" extras={extras}" if extras else '' ) )
                    if adjustedText and adjustedText!=cleanText:
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), f"adjustedText={adjustedText!r}" )
                    if fullText and fullText!=cleanText:
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), f"fullText={fullText!r}" )
                    if original_text and original_text!=cleanText:
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' '*(len(marker)+4), f"original_text={original_text!r}" )

    bookObject = EsfmBib[BBB]

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._processedLines=}" )
    assert len(bookObject._processedLines) > 183 # after 'v=' markers added to 183 lines

    return EsfmBib
# end of load_OET_RV_Haggai

def test_CV_index( thisBible:ESFMBible ):
    """
    63 index entries created from 188 data entries
    3.0 average data entries per index entry

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
    24 ('1', '1') InternalBibleBookCVIndexEntry object: ix=24 cnt=8 ixE=32 ctxt=['chapters', 'c']
    25 ('1', '2') InternalBibleBookCVIndexEntry object: ix=32 cnt=4 ixE=36 ctxt=['chapters', 'c', 'p']
    26 ('1', '3') InternalBibleBookCVIndexEntry object: ix=36 cnt=5 ixE=41 ctxt=['chapters', 'c']
    27 ('1', '4') InternalBibleBookCVIndexEntry object: ix=41 cnt=4 ixE=45 ctxt=['chapters', 'c']
    28 ('1', '5') InternalBibleBookCVIndexEntry object: ix=45 cnt=3 ixE=48 ctxt=['chapters', 'c', 'm']
    29 ('1', '6') InternalBibleBookCVIndexEntry object: ix=48 cnt=4 ixE=52 ctxt=['chapters', 'c', 'm']
    30 ('1', '7') InternalBibleBookCVIndexEntry object: ix=52 cnt=4 ixE=56 ctxt=['chapters', 'c']
    31 ('1', '8') InternalBibleBookCVIndexEntry object: ix=56 cnt=4 ixE=60 ctxt=['chapters', 'c', 'p']
    32 ('1', '9') InternalBibleBookCVIndexEntry object: ix=60 cnt=4 ixE=64 ctxt=['chapters', 'c']
    33 ('1', '10') InternalBibleBookCVIndexEntry object: ix=64 cnt=3 ixE=67 ctxt=['chapters', 'c', 'p']
    34 ('1', '11') InternalBibleBookCVIndexEntry object: ix=67 cnt=4 ixE=71 ctxt=['chapters', 'c', 'p']
    35 ('1', '12') InternalBibleBookCVIndexEntry object: ix=71 cnt=7 ixE=78 ctxt=['chapters', 'c']
    36 ('1', '13') InternalBibleBookCVIndexEntry object: ix=78 cnt=3 ixE=81 ctxt=['chapters', 'c', 'p']
    37 ('1', '14') InternalBibleBookCVIndexEntry object: ix=81 cnt=3 ixE=84 ctxt=['chapters', 'c', 'p']
    38 ('1', '15') InternalBibleBookCVIndexEntry object: ix=84 cnt=5 ixE=89 ctxt=['chapters', 'c', 'p']
    39 ('2', '0') InternalBibleBookCVIndexEntry object: ix=89 cnt=1 ixE=90 ctxt=['chapters']
    40 ('2', '1') InternalBibleBookCVIndexEntry object: ix=90 cnt=8 ixE=98 ctxt=['chapters', 'c']
    41 ('2', '2') InternalBibleBookCVIndexEntry object: ix=98 cnt=3 ixE=101 ctxt=['chapters', 'c', 'p']
    42 ('2', '3') InternalBibleBookCVIndexEntry object: ix=101 cnt=3 ixE=104 ctxt=['chapters', 'c', 'p']
    43 ('2', '4') InternalBibleBookCVIndexEntry object: ix=104 cnt=3 ixE=107 ctxt=['chapters', 'c', 'p']
    44 ('2', '5') InternalBibleBookCVIndexEntry object: ix=107 cnt=3 ixE=110 ctxt=['chapters', 'c', 'p']
    45 ('2', '6') InternalBibleBookCVIndexEntry object: ix=110 cnt=3 ixE=113 ctxt=['chapters', 'c', 'p']
    46 ('2', '7') InternalBibleBookCVIndexEntry object: ix=113 cnt=3 ixE=116 ctxt=['chapters', 'c', 'p']
    47 ('2', '8') InternalBibleBookCVIndexEntry object: ix=116 cnt=3 ixE=119 ctxt=['chapters', 'c', 'p']
    48 ('2', '9') InternalBibleBookCVIndexEntry object: ix=119 cnt=4 ixE=123 ctxt=['chapters', 'c', 'p']
    49 ('2', '10') InternalBibleBookCVIndexEntry object: ix=123 cnt=7 ixE=130 ctxt=['chapters', 'c']
    50 ('2', '11') InternalBibleBookCVIndexEntry object: ix=130 cnt=3 ixE=133 ctxt=['chapters', 'c', 'p']
    51 ('2', '12') InternalBibleBookCVIndexEntry object: ix=133 cnt=7 ixE=140 ctxt=['chapters', 'c', 'p']
    52 ('2', '13') InternalBibleBookCVIndexEntry object: ix=140 cnt=8 ixE=148 ctxt=['chapters', 'c']
    53 ('2', '14') InternalBibleBookCVIndexEntry object: ix=148 cnt=5 ixE=153 ctxt=['chapters', 'c']
    54 ('2', '15') InternalBibleBookCVIndexEntry object: ix=153 cnt=3 ixE=156 ctxt=['chapters', 'c', 'p']
    55 ('2', '16') InternalBibleBookCVIndexEntry object: ix=156 cnt=3 ixE=159 ctxt=['chapters', 'c', 'p']
    56 ('2', '17') InternalBibleBookCVIndexEntry object: ix=159 cnt=3 ixE=162 ctxt=['chapters', 'c', 'p']
    57 ('2', '18') InternalBibleBookCVIndexEntry object: ix=162 cnt=3 ixE=165 ctxt=['chapters', 'c', 'p']
    58 ('2', '19') InternalBibleBookCVIndexEntry object: ix=165 cnt=4 ixE=169 ctxt=['chapters', 'c', 'p']
    59 ('2', '20') InternalBibleBookCVIndexEntry object: ix=169 cnt=7 ixE=176 ctxt=['chapters', 'c']
    60 ('2', '21') InternalBibleBookCVIndexEntry object: ix=176 cnt=3 ixE=179 ctxt=['chapters', 'c', 'p']
    61 ('2', '22') InternalBibleBookCVIndexEntry object: ix=179 cnt=3 ixE=182 ctxt=['chapters', 'c', 'p']
    62 ('2', '23') InternalBibleBookCVIndexEntry object: ix=182 cnt=6 ixE=188 ctxt=['chapters', 'c', 'p']
    """
    fnPrint( DEBUGGING_THIS_MODULE, "test_CV_index()" )

    thisBible.doPostLoadProcessing() # Makes the CV index as part of this
    bookObject = thisBible[BBB]
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookObject._CVIndex=}" )
    assert len(bookObject._CVIndex) == 64 # 2 chapters + 38 verses + 18(+6 extras) header/intro lines
    # for ee,(CV,thisCVIndexEntry) in enumerate( bookObject._CVIndex.items() ):
    #     print( f"  {ee} {CV} {thisCVIndexEntry}" )

    C, V = '1', '1'
    c, v = int( C ), int( V )
    verseEntryList, contextList = thisBible.getContextVerseData( (BBB,C) if c==-1 else (BBB, C, V) )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"For {BBB} {C}:{V}\n  {contextList=}" )
    assert contextList == ['chapters', 'c']
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {verseEntryList=}" )
    assert isinstance( verseEntryList, InternalBibleEntryList ) # A list with ESFM line entries (InternalBibleEntry)
    assert len(verseEntryList) == 8
    assert verseEntryList[0].getMarker() == 'v='; assert verseEntryList[0].getCleanText() == '1'
    assert verseEntryList[1].getOriginalMarker() == 's1'
    assert verseEntryList[1].getOriginalText() == "God's command to rebuild the temple"
    assert verseEntryList[2].getOriginalMarker() == 'rem'
    assert verseEntryList[3].getOriginalMarker() == 'p'
    assert verseEntryList[3].getOriginalText() == ''
    assert verseEntryList[4].getMarker() == 'c#'
    assert verseEntryList[4].getOriginalText() == C
    assert verseEntryList[5].getOriginalMarker() == 'v'
    assert verseEntryList[5].getOriginalText() == V
    assert verseEntryList[6].getMarker() == 'v~'
    assert verseEntryList[7].getMarker() == '¬v'
    assert verseEntryList[7].getCleanText() == V
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"OET-RV CV index for {BBB} matches expectations." )
# end of test_CV_index

def test_section_index( thisBible:ESFMBible ):
    """
    7 index entries created from 188 data entries
    26.9 average data entries per index entry

    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG'
    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction'

    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=25–71 (cnt=47) s1='God's command to rebuild the temple' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=25–71 (cnt=47) s1='God's command to rebuild the temple'
    3 1:12 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=72–90 (cnt=19) s1='The people start rebuilding' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=72–90 (cnt=19) s1='The people start rebuilding'
    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=91–123 (cnt=33) s1='The splendour of the new temple' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=91–123 (cnt=33) s1='The splendour of the new temple'
    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=124–169 (cnt=46) s1='Haggai consults the priests' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=124–169 (cnt=46) s1='Haggai consults the priests'
    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=170–187 (cnt=18) s1='God's promise to Zerubavel' sectionIndexEntry=InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=170–187 (cnt=18) s1='God's promise to Zerubavel'
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
    HAG_endCV_list   = ( ('-1','11'), ('-1','22'), ('1','11'), ('1','15'), ('2','9'), ('2','19'), ('2','23') )
    HAG_indices      = ( (0,11), (13,22), (24,72), (73,91), (92,126), (127,173), (174,192) )
    HAG_reasons     = ( 'Headers', 'is1', 's1/c', 's1', 's1/c', 's1', 's1' )
    HAG_contexts     = ( [], [], ['chapters','c'], ['chapters','c'], ['chapters','c'], ['chapters','c'], ['chapters','c'] )
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

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    # set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    # Export option allows the two indexes to be created as files in the current folder
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False ) # TODO: not implemented yet (save indexes to .txt files)

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, PROGRAM_NAME_VERSION )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of test_OET_RV_HAG_indexes.py
