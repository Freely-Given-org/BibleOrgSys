#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Greek.py
#
# Module handling Greek language
#
# Copyright (C) 2012-2023 Robert Hunt
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
Module handling Greek language particularities.
"""

from gettext import gettext as _
import unicodedata
from typing import Optional

if __name__ == '__main__':
    import os
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2023-12-16' # by RJH
SHORT_PROGRAM_NAME = "GreekLanguageHandler"
PROGRAM_NAME = "Greek language handler"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Lower-case letters
alpha = 'α'
beta = 'β'
gamma = 'γ'
delta = 'δ'
epsilon = 'ε'
zeta = 'ζ'
eta = 'η'
theta = 'θ'
iota = 'ι'
kappa = 'κ'
Lambda = 'λ'
mu = 'μ'
nu = 'ν'
xi = 'ξ'
omicron = 'ο'
pi = 'π'
rho = 'ρ'
sigma = 'σ'; sigmaFinal = 'ς'
tau = 'τ'
upsilon = 'υ'
phi = 'φ'
chi = 'χ'
psi = 'ψ'
omega = 'ω'
normalConsonants = ( beta, gamma, delta, zeta, theta, kappa, Lambda, mu, nu, xi, pi, rho, sigma, tau, phi, chi, psi )
vowels = ( alpha, epsilon, eta, iota, omicron, upsilon, omega )
normalLetters = normalConsonants + vowels
assert len(normalLetters) == 24
finalConsonants = ( sigmaFinal, )
consonants = normalConsonants + finalConsonants
allFinalConsonants = ( beta, gamma, delta, zeta, theta, kappa, Lambda, mu, nu, xi, pi, rho, sigmaFinal, tau, phi, chi, psi )

# UPPER-CASE letters
ALPHA = 'α'
BETA = 'β'
GAMMA = 'γ'
DELTA = 'δ'
EPSILON = 'ε'
ZETA = 'ζ'
ETA = 'η'
THETA = 'θ'
IOTA = 'ι'
KAPPA = 'κ'
LAMBDA = 'λ'
MU = 'μ'
NU = 'ν'
XI = 'ξ'
OMICRON = 'ο'
PI = 'π'
RHO = 'ρ'
SIGMA = 'σ'; SIGMA_FINAL = 'ς'
TAU = 'τ'
UPSILON = 'υ'
PHI = 'φ'
CHI = 'χ'
PSI = 'ψ'
OMEGA = 'ω'
NORMAL_CONSONANTS = ( BETA, GAMMA, DELTA, ZETA, THETA, KAPPA, LAMBDA, MU, NU, XI, PI, RHO, SIGMA, TAU, PHI, CHI, PSI )
VOWELS = ( ALPHA, EPSILON, ETA, IOTA, OMICRON, UPSILON, OMEGA )
NORMAL_LETTERS = NORMAL_CONSONANTS + VOWELS
assert len(NORMAL_LETTERS) == len(normalLetters)
FINAL_CONSONANTS = ( SIGMA_FINAL, )
CONSONANTS = NORMAL_CONSONANTS + FINAL_CONSONANTS
ALL_CONSONANTS = ( BETA, GAMMA, DELTA, ZETA, THETA, KAPPA, LAMBDA, MU, NU, XI, PI, RHO, SIGMA_FINAL, TAU, PHI, CHI, PSI )
ALL_LETTERS = NORMAL_LETTERS + FINAL_CONSONANTS

GREEK_ACCENT_DICT = { 
    # Lowercase composed-Unicode accented characters
    '᾽':'', # Koronis -- not strictly an accent
    'Ἀ':'Α', 'Ἄ':'Α', 'Ἆ':'Α', 'Ἁ':'Α', 'Ἅ':'Α', 'Ἃ':'Α', 'ᾍ':'Α',
    'ά':'α', 'ὰ':'α', 'ἀ':'α', 'ἁ':'α', 'ᾳ':'α', 'ἄ':'α', 'ᾶ':'α', 'ἅ':'α', 'ἃ':'α', 'ἆ':'α', 'ἂ':'α', 'ᾷ':'α',
             'ᾅ':'α', 'ᾴ':'α', 'ᾄ':'α',
    'έ':'ε', 'ὲ':'ε', 'ἐ':'ε', 'ἑ':'ε', 'ἔ':'ε', 'ἓ':'ε', 'ἕ':'ε',
    'ή':'η', 'ὴ':'η', 'ἡ':'η', 'ῆ':'η', 'ἦ':'η', 'ῇ':'η', 'ἤ':'η', 'ῃ':'η', 'ἠ':'η', 'ἥ':'η', 'ᾔ':'η', 'ἢ':'η',
             'ᾖ':'η', 'ᾐ':'η', 'ᾗ':'η', 'ἧ':'η', 'ἣ':'η', 'ῄ':'η', 'ᾑ':'η',
    'ί':'ι', 'ί':'ι', 'ὶ':'ι', 'ἰ':'ι', 'ἱ':'ι', 'ῖ':'ι', 'ἷ':'ι', 'ἶ':'ι', 'ΐ':'ι', 'ῒ':'ι', 'ἵ':'ι', 'ἴ':'ι',
             'ἳ':'ι', 'ϊ':'ι', 'ΐ':'ι',
    'ό':'ο', 'ὸ':'ο', 'ὀ':'ο', 'ὁ':'ο', 'ὃ':'ο', 'ὅ':'ο', 'ὄ':'ο', 'ὂ':'ο',
    'ώ':'ω', 'ὼ':'ω', 'ὠ':'ω', 'ὡ':'ω', 'ῶ':'ω', 'ῷ':'ω', 'ῳ':'ω', 'ᾧ':'ω', 'ὥ':'ω', 'ὦ':'ω', 'ὧ':'ω', 'ῴ':'ω',
             'ὤ':'ω', 'ᾠ':'ω', 'ὢ':'ω',
    'ύ':'υ', 'ὺ':'υ', 'ὐ':'υ', 'ὑ':'υ', 'ῦ':'υ', 'ὕ':'υ', 'ὖ':'υ', 'ὗ':'υ', 'ϋ':'υ', 'ὓ':'υ', 'ὔ':'υ', 'ὒ':'υ',
             'ΰ':'υ', 'ῢ':'υ',
    'ῥ':'ρ',
    }

if BibleOrgSysGlobals.debugFlag: # Check that our tables have no obvious errors
    for j,letter in enumerate( normalConsonants ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, letter )
        assert normalConsonants.count(letter)==1
        assert letter not in vowels
    for j,letter in enumerate( vowels ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, letter )
        assert vowels.count(letter)==1
        assert letter not in normalConsonants


# Filenames for morphgnt
MORPHGNT_BOOKLIST = ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', \
                    'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', \
                    'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV' ]

MORPHGNT_FILENAME_LIST = [ ('MAT','61-Mt-morphgnt.txt'), ('MRK','62-Mk-morphgnt.txt'), ('LUK','63-Lk-morphgnt.txt'),
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
for BBB,fn in MORPHGNT_FILENAME_LIST: morphgntFilenameDict[BBB] = fn

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
    def __init__( self, text ) -> None:
        """
        Create an new Greek object.
        """
        self.originalText = self.currentText = text
    # end of __init__

    def __str__( self ) -> str:
        """
        This method returns the string representation of the Greek string.

        @return: the name of a Greek object formatted as a string
        @rtype: string
        """
        result = "Greek object"
        result += ('\n' if result else '') + "  " + _("Original = {!r}").format( self.originalText )
        if self.currentText != self.originalText:
            result += ('\n' if result else '') + "  " + _("Current  = {!r}").format( self.currentText )
        return result
    # end of __str__

    def printUnicodeData( self, text:Optional[str]=None ):
        if text is None: text = self.currentText
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "unicodedata", unicodedata.unidata_version )
        #def printUnicodeInfo( text, description ):
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{}:".format( description ) )
            #for j,char in enumerate(text):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{:2} {:04x} {} {!r}   (cat={} bid={} comb={} mirr={})" \
                    #.format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )
    # end of Greek.printUnicodeData


    def removeAccents( self, text:Optional[str]=None ) -> str:
        """
        Remove accents from the string and return it (used for fuzzy matching)

        Currently only works for lowercase accented Greek characters

        Doesn't cope with punctuation characters yet.
        """
        if text is None: text = self.currentText
        resultText = ''.join( GREEK_ACCENT_DICT[someChar] if someChar in GREEK_ACCENT_DICT
                                        else someChar for someChar in text )
        for char in resultText:
            if char != ' ':
                assert char in ALL_LETTERS, f"Greek accent not removed by removeAccents: {char=} from {text=}"
        return resultText
    # end of Greek.removeAccents


    def removeOtherMarks( self, text=None ):
        """
        Return the text with other marks (like sin/shin marks) and any remaining metegOrSiluq removed.
        """
        if text is None: # Use our own text
            self.currentText = self.removeOtherMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        #for otherMark in otherMarks: text = text.replace(otherMark, '')
        return text
# end of Greek class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demonstrate the Greek class
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    dan12 = "וַיִּתֵּן֩ אֲדֹנָ֨י בְּיָד֜וֹ אֶת־יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים וַיְבִיאֵ֥ם אֶֽרֶץ־שִׁנְעָ֖ר בֵּ֣ית אֱלֹהָ֑יו וְאֶת־הַכֵּלִ֣ים הֵבִ֔יא בֵּ֖ית אוֹצַ֥ר אֱלֹהָֽיו ׃"
    dan13 = "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו לְהָבִ֞יא מִבְּנֵ֧י יִשְׂרָאֵ֛ל וּמִזֶּ֥רַע הַמְּלוּכָ֖ה וּמִן־הַֽפַּרְתְּמִֽים ׃"
    dan14 = "יְלָדִ֣ים אֲשֶׁ֣ר אֵֽין־בָּהֶ֣ם כָּל־מאום וְטוֹבֵ֨י מַרְאֶ֜ה וּמַשְׂכִּילִ֣ים בְּכָל־חָכְמָ֗ה וְיֹ֤דְעֵי דַ֙עַת֙ וּמְבִינֵ֣י מַדָּ֔ע וַאֲשֶׁר֙ כֹּ֣חַ בָּהֶ֔ם לַעֲמֹ֖ד בְּהֵיכַ֣ל הַמֶּ֑לֶךְ וּֽלֲלַמְּדָ֥ם סֵ֖פֶר וּלְשׁ֥וֹן כַּשְׂדִּֽים ׃"
    dan15 = "וַיְמַן֩ לָהֶ֨ם הַמֶּ֜לֶךְ דְּבַר־י֣וֹם בְּיוֹמ֗וֹ מִפַּת־בַּ֤ג הַמֶּ֙לֶךְ֙ וּמִיֵּ֣ין מִשְׁתָּ֔יו וּֽלְגַדְּלָ֖ם שָׁנִ֣ים שָׁל֑וֹשׁ וּמִ֨קְצָתָ֔ם יַֽעַמְד֖וּ לִפְנֵ֥י הַמֶּֽלֶךְ ׃"
    for string in ( dan11, dan12, dan13, dan14, dan15 ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h = Greek( string )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeOtherMarks()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed other marks" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
# end of fullDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Greek.py
