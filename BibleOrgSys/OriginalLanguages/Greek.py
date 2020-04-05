#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Greek.py
#
# Module handling Greek language
#
# Copyright (C) 2012-2016 Robert Hunt
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
Module handling Greek language particularities.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2016-06-07' # by RJH
SHORT_PROGRAM_NAME = "GreekLanguageHandler"
PROGRAM_NAME = "Greek language handler"
PROGRAM_VERSION = '0.02'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import unicodedata


if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


# Consonants
alpha = 'α'
beta = 'β'
gamma = ''
normalConsonants = ( alpha, beta, gamma, )
assert len(normalConsonants) == 3
#finalConsonants = ( memFinal, nunFinal, tsadiFinal, qofFinal, )
#consonants = normalConsonants + finalConsonants
#allFinalConsonants = ( alef, bet, gimel, dalet, he, waw, zayin, het, tet, yod, kaf, lamed, memFinal, nunFinal, samekh, ayin, pe, tsadiFinal, qofFinal, resh, sinShin, taw, )


# Other marks
#dageshOrMapiq = 'ּ'
#rafe = 'ֿ'
#paseq = '׀'
#shinDot = 'ׁ'
#sinDot = 'ׂ'
#upperDot = 'ׄ'
#lowerDot = 'ׅ'
#qamatzQatan = 'ׇ'
#otherMarks = ( dageshOrMapiq, rafe, paseq, shinDot, sinDot, upperDot, lowerDot, qamatzQatan, )


if 0 and BibleOrgSysGlobals.debugFlag: # Check that our tables have no obvious errors
    for j,letter in enumerate( normalConsonants ):
        #print( j, letter )
        assert normalConsonants.count(letter)==1
        assert letter not in vowelPoints
        assert letter not in otherMarks
        assert letter not in cantillationMarks
    for j,mark in enumerate( vowelPoints ):
        #print( j, mark )
        assert vowelPoints.count(mark)==1
        assert mark not in normalConsonants
        assert mark not in otherMarks
        assert mark not in cantillationMarks
    for j,mark in enumerate( otherMarks ):
        #print( j, mark )
        assert otherMarks.count(mark)==1
        assert mark not in normalConsonants
        assert mark not in vowelPoints
        assert mark not in cantillationMarks
    for j,mark in enumerate( cantillationMarks ):
        #print( j, mark )
        assert cantillationMarks.count(mark)==1
        assert mark not in normalConsonants
        assert mark not in vowelPoints
        assert mark not in otherMarks


# Filenames for morphgnt
morphgntBookList = ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', \
                    'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', \
                    'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV' ]

morphgntFilenameList = [ ('MAT','61-Mt-morphgnt.txt'), ('MRK','62-Mk-morphgnt.txt'), ('LUK','63-Lk-morphgnt.txt'),
                        ('JHN','64-Jn-morphgnt.txt'), ('ACT','65-Ac-morphgnt.txt'), ('ROM','66-Ro-morphgnt.txt'),
                        ('CO1','67-1Co-morphgnt.txt'), ('CO2','68-2Co-morphgnt.txt'), ('GAL','69-Ga-morphgnt.txt'),
                        ('EPH','70-Eph-morphgnt.txt'), ('PHP','71-Php-morphgnt.txt'), ('COL','72-Col-morphgnt.txt'),
                        ('TH1','73-1Th-morphgnt.txt'), ('TH2','74-2Th-morphgnt.txt'), ('TI1','75-1Ti-morphgnt.txt'),
                        ('TI2','76-2Ti-morphgnt.txt'), ('TIT','77-Tit-morphgnt.txt'), ('PHM','78-Phm-morphgnt.txt'),
                        ('HEB','79-Heb-morphgnt.txt'), ('JAM','80-Jas-morphgnt.txt'), ('PE1','81-1Pe-morphgnt.txt'),
                        ('PE2','82-2Pe-morphgnt.txt'), ('JN1','83-1Jn-morphgnt.txt'), ('JN2','84-2Jn-morphgnt.txt'),
                        ('JN3','85-3Jn-morphgnt.txt'), ('JDE','86-Jud-morphgnt.txt'), ('REV','87-Re-morphgnt.txt' )
                      ]
morphgntFilenameDict = {}
for BBB,fn in morphgntFilenameList: morphgntFilenameDict[BBB] = fn

# Codes for morphgnt
# e.g., 180101 N- ----NSM- Παῦλος Παῦλος Παῦλος Παῦλος
#       180102 N- ----DSF- ⸀ἀδελφῇ ἀδελφῇ ἀδελφῇ ἀδελφή
#       180102 P- -------- κατ’ κατ’ κατά κατά
#       180102 N- ----DSF- ἐκκλησίᾳ· ἐκκλησίᾳ ἐκκλησίᾳ ἐκκλησία

# There are seven space-separated columns:
#   0 book/chapter/verse
#   1 part of speech (POS)
#   2 parsing code
#   3 text (including punctuation)
#   4 word (with punctuation stripped)
#   5 normalized word
#   6 lemma

POSCodes = { 'A-':'???', 'C-':'conjunction', 'D-':'???', 'I-':'???', 'N-':'noun', 'P-':'particle', \
            'RA':'???', 'RD':'???', 'RI':'???', 'RP':'???', 'RR':'???', \
            'V-':'verb', 'X-':'???' }

# Parsing Code (eight characters long)
#   0 person
#   1 tense
#   2 voice
#   3 mood
#   4 case
#   5 number
#   6 gender
#   7 degree

parsingCodes = ( '-123', '-AFIPXY', '-AMP', '-DINOPS', '-ADGNV', '-PS', '-FMN', '-CS' )

personCodes = { '-':None, '1':'1st', '2':'2nd', '3':'3rd' }
tenseCodes = { '-':None, 'A':'???', 'F':'future', 'I':'???', 'P':'???', 'X':'???', 'Y':'???' }
voiceCodes = { '-':None, 'A':'active', 'M':'middle', 'P':'passive' }
modeCodes = { '-':None, 'D':'???', 'I':'???', 'N':'???', 'O':'???', 'P':'???', 'S':'???' }
caseCodes = { '-':None, 'A':'active', 'D':'dative', 'G':'genitive', 'N':'nominative', 'V':'vocative' }
numberCodes = { '-':None, 'P':'plural', 'S':'singular' }
genderCodes = { '-':None, 'F':'female', 'M':'male', 'N':'neuter' }
degreeCodes = { '-':None, 'C':'???', 'S':'???' }



class Greek():
    """
    Class for handling a Greek string.
    """
    def __init__( self, text ):
        """ Create an new Greek object. """
        self.originalText = text
        self.currentText = text
    # end of __init__

    def __str__( self ):
        """
        This method returns the string representation of the Greek object.

        @return: the name of a Greek object formatted as a string
        @rtype: string
        """
        result = "Greek object"
        result += ('\n' if result else '') + "  " + _("Original = {!r}").format( self.originalText )
        if self.currentText != self.originalText:
            result += ('\n' if result else '') + "  " + _("Current  = {!r}").format( self.currentText )
        return result
    # end of __str__

    def printUnicodeData( self, text=None ):
        if text is None: text = self.currentText
        print( "unicodedata", unicodedata.unidata_version )
        #def printUnicodeInfo( text, description ):
            #print( "{}:".format( description ) )
            #for j,char in enumerate(text):
                #print( "{:2} {:04x} {} {!r}   (cat={} bid={} comb={} mirr={})" \
                    #.format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )
    # end of printUnicodeData

    def removeOtherMarks( self, text=None ):
        """ Return the text with other marks (like sin/shin marks) and any remaining metegOrSiluq removed. """
        if text is None: # Use our own text
            self.currentText = self.removeOtherMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        #for otherMark in otherMarks: text = text.replace(otherMark, '')
        return text
# end of Greek class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    # Demonstrate the Greek class
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    dan12 = "וַיִּתֵּן֩ אֲדֹנָ֨י בְּיָד֜וֹ אֶת־יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים וַיְבִיאֵ֥ם אֶֽרֶץ־שִׁנְעָ֖ר בֵּ֣ית אֱלֹהָ֑יו וְאֶת־הַכֵּלִ֣ים הֵבִ֔יא בֵּ֖ית אוֹצַ֥ר אֱלֹהָֽיו ׃"
    dan13 = "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו לְהָבִ֞יא מִבְּנֵ֧י יִשְׂרָאֵ֛ל וּמִזֶּ֥רַע הַמְּלוּכָ֖ה וּמִן־הַֽפַּרְתְּמִֽים ׃"
    dan14 = "יְלָדִ֣ים אֲשֶׁ֣ר אֵֽין־בָּהֶ֣ם כָּל־מאום וְטוֹבֵ֨י מַרְאֶ֜ה וּמַשְׂכִּילִ֣ים בְּכָל־חָכְמָ֗ה וְיֹ֤דְעֵי דַ֙עַת֙ וּמְבִינֵ֣י מַדָּ֔ע וַאֲשֶׁר֙ כֹּ֣חַ בָּהֶ֔ם לַעֲמֹ֖ד בְּהֵיכַ֣ל הַמֶּ֑לֶךְ וּֽלֲלַמְּדָ֥ם סֵ֖פֶר וּלְשׁ֥וֹן כַּשְׂדִּֽים ׃"
    dan15 = "וַיְמַן֩ לָהֶ֨ם הַמֶּ֜לֶךְ דְּבַר־י֣וֹם בְּיוֹמ֗וֹ מִפַּת־בַּ֤ג הַמֶּ֙לֶךְ֙ וּמִיֵּ֣ין מִשְׁתָּ֔יו וּֽלְגַדְּלָ֖ם שָׁנִ֣ים שָׁל֑וֹשׁ וּמִ֨קְצָתָ֔ם יַֽעַמְד֖וּ לִפְנֵ֥י הַמֶּֽלֶךְ ׃"
    for string in ( dan11, dan12, dan13, dan14, dan15 ):
        print()
        h = Greek( string )
        print( h )
        print()
        h.removeOtherMarks()
        print( "Removed other marks" )
        print( h )
        print()
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Greek.py
