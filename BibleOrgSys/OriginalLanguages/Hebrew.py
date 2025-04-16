#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Hebrew.py
#
# Module handling Hebrew language
#
# Copyright (C) 2011-2024 Robert Hunt
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
Module handling Hebrew language particularities.
"""
from gettext import gettext as _
import unicodedata

if __name__ == '__main__':
    import os
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2024-05-27' # by RJH
SHORT_PROGRAM_NAME = "Hebrew"
PROGRAM_NAME = "Hebrew language handler"
PROGRAM_VERSION = '0.15'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Consonants
alef = 'א'
bet = 'ב'
gimel = 'ג'
dalet = 'ד'
he = 'ה'
waw = vav = 'ו'
zayin = 'ז'
het = 'ח'
tet = 'ט'
yod = 'י'
kaf = 'כ'
lamed = 'ל'
mem = 'מ'; memFinal = 'ם'
nun = 'נ'; nunFinal = 'ן'
samekh = 'ס'
ayin = 'ע'
pe = 'פ'
tsadi = 'צ'; tsadiFinal = 'ץ'
qof = 'ק'; qofFinal = 'ך'
resh = 'ר'
sinShin = 'ש'
taw = 'ת'
normalConsonants = ( alef, bet, gimel, dalet, he, waw, zayin, het, tet, yod, kaf, lamed, mem, nun, samekh, ayin, pe, tsadi, qof, resh, sinShin, taw, )
assert len(normalConsonants) == 22
finalConsonants = ( memFinal, nunFinal, tsadiFinal, qofFinal, )
consonants = normalConsonants + finalConsonants
allFinalConsonants = ( alef, bet, gimel, dalet, he, waw, zayin, het, tet, yod, kaf, lamed, memFinal, nunFinal, samekh, ayin, pe, tsadiFinal, qofFinal, resh, sinShin, taw, )


# Vowel points
sheva = shewa = 'ְ'
hatafSegol = 'ֱ'
hatafPatah = 'ֲ'
hatafQamats = 'ֳ'
hiriq = 'ִ'
tsere = 'ֵ'
segol = 'ֶ'
patah = 'ַ'
qamats = 'ָ'
holam = 'ֹ'
holamHaserForVav = 'ֺ'
qubuts = 'ֻ'
metegOrSiluq = 'ֽ' # But this is not ALWAYS a vowel point -- can also be a cantillation mark
vowelPoints = ( sheva, hatafSegol, hatafPatah, hatafQamats, hiriq, tsere, segol, patah, qamats, holam, holamHaserForVav, qubuts, )


# Other marks
dageshOrMapiq = 'ּ'
rafe = 'ֿ'
paseq = '׀'
shinDot = 'ׁ'
sinDot = 'ׂ'
upperDot = 'ׄ'
lowerDot = 'ׅ'
qamatzQatan = 'ׇ'
otherMarks = ( dageshOrMapiq, rafe, paseq, shinDot, sinDot, upperDot, lowerDot, qamatzQatan, )


# Cantillation marks
etnahta = '֑'
segolAccent = '֒'
shalshelet = '֓'
zaqefQatan = '֔'
zaqefGadol = '֕'
tipeha = '֖'
revia = '֗'
zarqa = '֘'
pashta = '֙'
yetiv = '֚'
tevir = '֛'
geresh = '֜'
gereshMuqdam = '֝'
gershayim = '֞'
qarneyPara = '֟'
telishaGedola = '֠'
pazer = '֡'
atnahHafukh = '֢'
munah = '֣'
mahapakh = '֤'
merkha = '֥'
merkhaKefula = '֦'
darga = '֧'
qadma = '֨'
telishaQetana = '֩'
yerahBenYomo = '֪'
ole = '֫'
iluy = '֬'
dehi = '֭'
zinor = '֮'
masoraCircle = '֯'
cantillationMarks = ( etnahta, segolAccent, shalshelet, zaqefQatan, zaqefGadol, tipeha, revia, zarqa, pashta, yetiv, tevir, \
                        geresh, gereshMuqdam, gershayim, qarneyPara, telishaGedola, pazer, atnahHafukh, munah, mahapakh, merkha, \
                        merkhaKefula, darga, qadma, telishaQetana, yerahBenYomo, ole, iluy, dehi, zinor, masoraCircle )

maqaf = '־'
sofPasuq = '׃'


# These substitutions are executed in the order given
#   (so longer sequences should precede shorter ones)
BOS_HEBREW_TRANSLITERATION = (
            (alef,''), (bet+dageshOrMapiq,'b'),(bet,'ⱱ'), (gimel+dageshOrMapiq,'g'),(gimel,'g'),
            (dalet+dageshOrMapiq,'dd'),(dalet,'d'),
            (he+dageshOrMapiq,'h'),(he+qamats,'āh'),(he,'h'),
            (waw+dageshOrMapiq,'u'),(waw+dageshOrMapiq,'ō'),(waw,'v'),
            (zayin+dageshOrMapiq,'zz'),(zayin,'z'),
            (het+dageshOrMapiq,'ħ'),(het,'ħ'), (tet+dageshOrMapiq,'ŧ'),(tet,'ŧ'),
            (yod+dageshOrMapiq,'u'),(yod,'y'), (kaf+dageshOrMapiq,'kk'),(kaf,'k'),
            (lamed+dageshOrMapiq,'ll'),(lamed,'l'),
            (mem+dageshOrMapiq,'mm'),(mem,'m'), (memFinal+dageshOrMapiq,'mm'),(memFinal,'m'),
            (nun+dageshOrMapiq,'nn'),(nun,'n'), (nunFinal+dageshOrMapiq,'nn'),(nunFinal,'n'),
            (samekh+dageshOrMapiq,'ş'),(samekh,'ş'), (ayin+dageshOrMapiq,''),(ayin,''),
            (pe+dageshOrMapiq,'p'),(pe,'f'),
            (tsadi+dageshOrMapiq,'ʦʦ'),(tsadi,'ʦ'), (tsadiFinal+dageshOrMapiq,'ʦʦ'),(tsadiFinal,'ʦ'),
            (qof+dageshOrMapiq,'qq'),(qof,'q'), (qofFinal+dageshOrMapiq,'qq'),(qofFinal,'q'),
            (resh+dageshOrMapiq,'rr'),(resh,'r'),
            (sinShin+shinDot,'sh'),(sinShin+sinDot,'s'), (taw+dageshOrMapiq,'tt'),(taw,'t'),
            (sheva,'(ə)'),(hatafSegol,'e'),(segol,'e'),(hiriq,'i'),(tsere,'ē'),(patah,'a'),(qamats,'ā'),(holam,'o'),(qubuts,'u'),
            #sheva = 'ְ'
            #hatafSegol = 'ֱ'
            #hatafPatah = 'ֲ'
            #hatafQamats = 'ֳ'
            #hiriq = 'ִ'
            #tsere = 'ֵ'
            #segol = 'ֶ'
            #patah = 'ַ'
            #qamats = 'ָ'
            #holam = 'ֹ'
            #holamHaserForVav = 'ֺ'
            #qubuts = 'ֻ'
            #metegOrSiluq = 'ֽ'
            (metegOrSiluq,''),
            (maqaf,'-'), (sofPasuq,'.'),
            )
STANDARD_HEBREW_TRANSLITERATION = (
            (alef,'ʾ'), (bet+dageshOrMapiq,'b'),(bet,'v'), (gimel+dageshOrMapiq,'g'),(gimel,'g'),
            (dalet+dageshOrMapiq,'d'),(dalet,'d'),
            (he+dageshOrMapiq,'h'),(he+qamats,'āh'),(he,'h'),
            (waw+dageshOrMapiq,'u'),(waw+dageshOrMapiq,'ō'),(waw,'w'),
            (zayin+dageshOrMapiq,'z'),(zayin,'z'),
            (het+dageshOrMapiq,'ḥḥ'),(het,'ḥ'), (tet+dageshOrMapiq,'ŧ'),(tet,'ŧ'),
            (yod+dageshOrMapiq,'yy'),(yod,'y'), (kaf+dageshOrMapiq,'k'),(kaf,'k'),
            (lamed+dageshOrMapiq,'ll'),(lamed,'l'),
            (mem+dageshOrMapiq,'mm'),(mem,'m'), (memFinal+dageshOrMapiq,'m'),(memFinal,'m'),
            (nun+dageshOrMapiq,'nn'),(nun,'n'), (nunFinal+dageshOrMapiq,'n'),(nunFinal,'n'),
            (samekh+dageshOrMapiq,'ş'),(samekh,'ş'), (ayin+dageshOrMapiq,''),(ayin,''),
            (pe+dageshOrMapiq,'p'),(pe,'̄p'),
            (tsadi+dageshOrMapiq,'ṣṣ'),(tsadi,'ṣ'), (tsadiFinal+dageshOrMapiq,'ṣṣ'),(tsadiFinal,'ṣ'),
            (qof+dageshOrMapiq,'q'),(qof,'q'), (qofFinal+dageshOrMapiq,'q'),(qofFinal,'q'),
            (resh+dageshOrMapiq,'r'),(resh,'r'),
            (sinShin+shinDot,'š'),(sinShin+sinDot,'s'), (taw+dageshOrMapiq,'t'),(taw,'t'),
            (resh+dageshOrMapiq,'r'),(resh,'r'),
            (sheva,'(ə)'),(hatafSegol,'e'),(segol,'e'),(hiriq,'i'),(tsere,'ē'),(patah,'a'),
                (qamats,'ā'),(holam,'o'),(qubuts,'u'),
            #sheva = 'ְ'
            #hatafSegol = 'ֱ'
            #hatafPatah = 'ֲ'
            #hatafQamats = 'ֳ'
            #hiriq = 'ִ'
            #tsere = 'ֵ'
            #segol = 'ֶ'
            #patah = 'ַ'
            #qamats = 'ָ'
            #holam = 'ֹ'
            #holamHaserForVav = 'ֺ'
            #qubuts = 'ֻ'
            #metegOrSiluq = 'ֽ'
            (metegOrSiluq,''),
            (maqaf,'-'), (sofPasuq,'.'),
            )
BOS_NAMES_HEBREW_TRANSLITERATION = (
            (alef,''), (bet+dageshOrMapiq,'b'),(bet,'ⱱ'), (gimel+dageshOrMapiq,'g'),(gimel,'g'),
            (dalet+dageshOrMapiq,'d'),(dalet,'d'),
            (he+dageshOrMapiq,'h'),(he+qamats,'ah'),(he,'h'),
            (waw+dageshOrMapiq,'u'),(waw+dageshOrMapiq,'ō'),(waw,'v'),
            (zayin+dageshOrMapiq,'z'),(zayin,'z'),
            (het+dageshOrMapiq,'ħ'),(het,'ħ'), (tet+dageshOrMapiq,'ŧ'),(tet,'ŧ'),
            (yod+dageshOrMapiq,'u'),(yod,'y'), (kaf+dageshOrMapiq,'k'),(kaf,'k'),
            (lamed+dageshOrMapiq,'l'),(lamed,'l'),
            (mem+dageshOrMapiq,'m'),(mem,'m'), (memFinal+dageshOrMapiq,'m'),(memFinal,'m'),
            (nun+dageshOrMapiq,'n'),(nun,'n'), (nunFinal+dageshOrMapiq,'n'),(nunFinal,'n'),
            (samekh+dageshOrMapiq,'ş'),(samekh,'ş'), (ayin+dageshOrMapiq,''),(ayin,''),
            (pe+dageshOrMapiq,'p'),(pe,'f'),
            (tsadi+dageshOrMapiq,'ʦ'),(tsadi,'ʦ'), (tsadiFinal+dageshOrMapiq,'ʦ'),(tsadiFinal,'ʦ'),
            (qof+dageshOrMapiq,'q'),(qof,'q'), (qofFinal+dageshOrMapiq,'q'),(qofFinal,'q'),
            (resh+dageshOrMapiq,'r'),(resh,'r'),
            (sinShin+shinDot,'sh'),(sinShin+sinDot,'s'), (taw+dageshOrMapiq,'t'),(taw,'t'),
            (resh+dageshOrMapiq,'r'),(resh,'r'),
            (sheva,'(ə)'),(hatafSegol,'e'),(segol,'e'),(hiriq,'i'),(tsere,'e'),(patah,'a'),(qamats,'a'),(holam,'o'),(qubuts,'u'),
            #sheva = 'ְ'
            #hatafSegol = 'ֱ'
            #hatafPatah = 'ֲ'
            #hatafQamats = 'ֳ'
            #hiriq = 'ִ'
            #tsere = 'ֵ'
            #segol = 'ֶ'
            #patah = 'ַ'
            #qamats = 'ָ'
            #holam = 'ֹ'
            #holamHaserForVav = 'ֺ'
            #qubuts = 'ֻ'
            #metegOrSiluq = 'ֽ'
            (metegOrSiluq,''),
            (maqaf,'-'), (sofPasuq,'.'),
            )
transliterationSchemes = { 'Default':BOS_HEBREW_TRANSLITERATION, 'Standard':STANDARD_HEBREW_TRANSLITERATION, 'Names':BOS_NAMES_HEBREW_TRANSLITERATION }



if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Check that our tables have no obvious errors
    for j,letter in enumerate( consonants ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, letter )
        assert consonants.count(letter)==1
        assert letter not in vowelPoints
        assert letter not in otherMarks
        assert letter not in cantillationMarks
    for j,mark in enumerate( vowelPoints ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, mark )
        assert vowelPoints.count(mark)==1
        assert mark not in consonants
        assert mark not in otherMarks
        assert mark not in cantillationMarks
    for j,mark in enumerate( otherMarks ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, mark )
        assert otherMarks.count(mark)==1
        assert mark not in consonants
        assert mark not in vowelPoints
        assert mark not in cantillationMarks
    for j,mark in enumerate( cantillationMarks ):
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, j, mark )
        assert cantillationMarks.count(mark)==1
        assert mark not in consonants
        assert mark not in vowelPoints
        assert mark not in otherMarks

    BibleOrgSysGlobals.printUnicodeInfo( vowelPoints, "Vowel points" )
    BibleOrgSysGlobals.printUnicodeInfo( cantillationMarks, "Cantillation marks" )



class Hebrew():
    """
    Class for handling a Hebrew string.
    """
    def __init__( self, text ) -> None:
        """
        Create an new Hebrew object.
        """
        self.originalText = self.currentText = text
    # end of Hebrew.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Hebrew string.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew object"
        result += ('\n' if result else '') + "  " + _("Original = {!r}").format( self.originalText )
        if self.currentText != self.originalText:
            result += ('\n' if result else '') + "  " + _("Current  = {!r}").format( self.currentText )
        return result
    # end of Hebrew.__str__


    def printUnicodeData( self, text:str|None=None ) -> None:
        """
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "unicodedata", unicodedata.unidata_version )

        if text is None: text = self.currentText

        #def printUnicodeInfo( text, description ):
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{}:".format( description ) )
        for j,char in enumerate(text):
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{:2} {:04x} {} {!r}   (cat={} bid={} comb={} mirr={})" \
                .format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )
    # end of Hebrew.printUnicodeData


    def verifyConsonantsOnly( self, text:str|None=None ) -> bool:
        """
        Check that we only have consonants left
        """
        if text is None: text = self.currentText
        haveError = False
        textLength = len( text )
        this = ( ' ', '־', )
        for j,letter in enumerate(text):
            if letter not in consonants and letter not in this:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Found unexpected {!r} ({}) non-consonant at index {} in {!r}".format( letter, unicodedata.name(letter), j, text ) )
                haveError = True
            if letter in finalConsonants and j<textLength-1:
                nextLetter = text[j+1]
                if nextLetter not in this:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Found unexpected {!r} ({}) final consonant before {!r} ({}) at index {} in {!r}".format( letter, unicodedata.name(letter), nextLetter, unicodedata.name(nextLetter), j, text ) )
                    haveError = True
        return haveError
    # end of Hebrew.verifyConsonantsOnly


    def removeAllMetegOrSiluq( self, text:str|None=None ) -> str:
        """
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "removeAllMetegOrSiluq( {!r} )".format( text ) )

        if text is None: # Use our own text
            self.currentText = self.removeAllMetegOrSiluq( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        text = text.replace( metegOrSiluq, '' )
        return text
    # end of Hebrew.removeAllMetegOrSiluq


    def _removeMetegOrSiluq( self, text:str, asVowel:bool ) -> str:
        """
        It's actually often impossible to tell automatically which purpose this Unicode mark has.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "_removeMetegOrSiluq( {!r}, {} )".format( text, asVowel ) )

        while text:
            textLength = len( text )
            madeChanges = False
            for j,mark in enumerate(text):
                if mark != metegOrSiluq: continue
                previousMark = text[j-1] if j>0 else ''
                nextMark = text[j+1] if j<textLength-1 else ''
                if previousMark in ( patah, segol ) or nextMark in (): # Assume it's a vowel point meteg
                    if asVowel:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Deleting (vowel point) meteg after {previousMark!r} ({unicodedata.name(previousMark) if previousMark else ''}) and before {nextMark!r} ({unicodedata.name(nextMark) if nextMark else ''})" )
                        text = text[:j] + text[j+1:]
                        madeChanges = True
                        break
                    else:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Ignoring (vowel point) meteg/siluq after {previousMark!r} ({unicodedata.name(previousMark) if previousMark else ''}) and before {nextMark!r} ({unicodedata.name(nextMark) if nextMark else ''})" )
                else: # it doesn't appear to be a vowel point meteg
                    if not asVowel:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Deleting (cantillation mark) siluq after {previousMark!r} ({unicodedata.name(previousMark) if previousMark else ''}) and before {nextMark!r} ({unicodedata.name(nextMark) if nextMark else ''})" )
                        text = text[:j] + text[j+1:]
                        madeChanges = True
                        break
                    else:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Ignoring (cantillation mark) meteg/siluq after {previousMark!r} ({unicodedata.name(previousMark) if previousMark else ''}) and before {nextMark!r} ({unicodedata.name(nextMark) if nextMark else ''})" )
            if not madeChanges: break # Check for another meteg if we made any changes
        return text
    # end of Hebrew._removeMetegOrSiluq


    def removeCantillationMarks( self, givenText=None, removeMetegOrSiluq=False ) -> str:
        """
        Return the text with cantillation marks removed.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "removeMetegOrSiluq( {!r}, {} )".format( text, removeMetegOrSiluq ) )

        if givenText is None: # Use our own text
            self.currentText = self.removeCantillationMarks( self.currentText, removeMetegOrSiluq ) # recursive call
            if 1 or BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                for char in self.currentText:
                    # print( f"{ord(char)=} {unicodedata.name(char)=} {char=} {unicodedata.category(char)=} {unicodedata.bidirectional(char)=} {unicodedata.combining(char)=} {unicodedata.mirrored(char)=}" )
                    assert 'ACCENT' not in unicodedata.name(char), f"{unicodedata.name(char)=}"
            return self.currentText

        # else we were given some text to process
        adjustedText = givenText
        if removeMetegOrSiluq: adjustedText = self._removeMetegOrSiluq( adjustedText, asVowel=False )
        for cantillationMark in cantillationMarks:
            adjustedText = adjustedText.replace(cantillationMark, '')
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
            for char in adjustedText:
                # print( f"{ord(char)=} {unicodedata.name(char)=} {char=} {unicodedata.category(char)=} {unicodedata.bidirectional(char)=} {unicodedata.combining(char)=} {unicodedata.mirrored(char)=}" )
                assert 'ACCENT' not in unicodedata.name(char), f"{unicodedata.name(char)=} {givenText=} {adjustedText=}"
        return adjustedText
    # end of Hebrew.removeCantillationMarks


    def removeVowelPointing( self, text=None, removeMetegOrSiluq=False ) -> str:
        """
        Return the text with vowel pointing removed.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "removeVowelPointing( {!r}, {} )".format( text, removeMetegOrSiluq ) )

        if text is None: # Use our own text
            self.currentText = self.removeVowelPointing( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        if removeMetegOrSiluq: text = self._removeMetegOrSiluq( text, asVowel=True )
        for vowelPoint in vowelPoints: text = text.replace(vowelPoint, '') # Remove the easy vowel points
        return text
    # end of Hebrew.removeVowelPointing


    def removeOtherMarks( self, text=None, removeSinShinDots=True ) -> str:
        """
        Return the text with other marks (like dagesh and sin/shin marks if required)
            and any remaining metegOrSiluq removed.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "removeOtherMarks( {!r} )".format( text ) )

        if text is None: # Use our own text
            self.currentText = self.removeOtherMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        text = self.removeAllMetegOrSiluq( text )
        for otherMark in otherMarks:
            if removeSinShinDots or otherMark not in (sinDot, shinDot):
                text = text.replace(otherMark, '')
        return text
    # end of Hebrew.removeOtherMarks


    def transliterate( self, text=None, scheme=None ) -> str:
        """
        Return a (roughly) transliterated version of the current text.
        """
        if text is None: # Use our own text
            outputText = self.transliterate( self.currentText, scheme=scheme )
            return outputText
        # else we were given some text to process
        outputText = text
        if scheme is None: scheme = 'Default'
        assert scheme in ('Default','Standard','Names')
        for h,tr in transliterationSchemes[scheme]: outputText = outputText.replace( h, tr )
        return outputText
# end of Hebrew class


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demonstrate the Hebrew class
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    dan12 = "וַיִּתֵּן֩ אֲדֹנָ֨י בְּיָד֜וֹ אֶת־יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים וַיְבִיאֵ֥ם אֶֽרֶץ־שִׁנְעָ֖ר בֵּ֣ית אֱלֹהָ֑יו וְאֶת־הַכֵּלִ֣ים הֵבִ֔יא בֵּ֖ית אוֹצַ֥ר אֱלֹהָֽיו ׃"
    dan13 = "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו לְהָבִ֞יא מִבְּנֵ֧י יִשְׂרָאֵ֛ל וּמִזֶּ֥רַע הַמְּלוּכָ֖ה וּמִן־הַֽפַּרְתְּמִֽים ׃"
    dan14 = "יְלָדִ֣ים אֲשֶׁ֣ר אֵֽין־בָּהֶ֣ם כָּל־מאום וְטוֹבֵ֨י מַרְאֶ֜ה וּמַשְׂכִּילִ֣ים בְּכָל־חָכְמָ֗ה וְיֹ֤דְעֵי דַ֙עַת֙ וּמְבִינֵ֣י מַדָּ֔ע וַאֲשֶׁר֙ כֹּ֣חַ בָּהֶ֔ם לַעֲמֹ֖ד בְּהֵיכַ֣ל הַמֶּ֑לֶךְ וּֽלֲלַמְּדָ֥ם סֵ֖פֶר וּלְשׁ֥וֹן כַּשְׂדִּֽים ׃"
    dan15 = "וַיְמַן֩ לָהֶ֨ם הַמֶּ֜לֶךְ דְּבַר־י֣וֹם בְּיוֹמ֗וֹ מִפַּת־בַּ֤ג הַמֶּ֙לֶךְ֙ וּמִיֵּ֣ין מִשְׁתָּ֔יו וּֽלְגַדְּלָ֖ם שָׁנִ֣ים שָׁל֑וֹשׁ וּמִ֨קְצָתָ֔ם יַֽעַמְד֖וּ לִפְנֵ֥י הַמֶּֽלֶךְ ׃"
    for string in ( dan11, dan12, dan13, dan14, dan15 ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h = Hebrew( string )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeCantillationMarks()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed cantillation marks" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeVowelPointing()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed vowel pointing" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeOtherMarks()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed other marks" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.verifyConsonantsOnly()
        h = Hebrew( string )
        h.removeCantillationMarks()
        #h.printUnicodeData()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Transliterated: {}".format( h.transliterate() ) )
# end of Hebrew.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demonstrate the Hebrew class
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    dan12 = "וַיִּתֵּן֩ אֲדֹנָ֨י בְּיָד֜וֹ אֶת־יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים וַיְבִיאֵ֥ם אֶֽרֶץ־שִׁנְעָ֖ר בֵּ֣ית אֱלֹהָ֑יו וְאֶת־הַכֵּלִ֣ים הֵבִ֔יא בֵּ֖ית אוֹצַ֥ר אֱלֹהָֽיו ׃"
    dan13 = "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו לְהָבִ֞יא מִבְּנֵ֧י יִשְׂרָאֵ֛ל וּמִזֶּ֥רַע הַמְּלוּכָ֖ה וּמִן־הַֽפַּרְתְּמִֽים ׃"
    dan14 = "יְלָדִ֣ים אֲשֶׁ֣ר אֵֽין־בָּהֶ֣ם כָּל־מאום וְטוֹבֵ֨י מַרְאֶ֜ה וּמַשְׂכִּילִ֣ים בְּכָל־חָכְמָ֗ה וְיֹ֤דְעֵי דַ֙עַת֙ וּמְבִינֵ֣י מַדָּ֔ע וַאֲשֶׁר֙ כֹּ֣חַ בָּהֶ֔ם לַעֲמֹ֖ד בְּהֵיכַ֣ל הַמֶּ֑לֶךְ וּֽלֲלַמְּדָ֥ם סֵ֖פֶר וּלְשׁ֥וֹן כַּשְׂדִּֽים ׃"
    dan15 = "וַיְמַן֩ לָהֶ֨ם הַמֶּ֜לֶךְ דְּבַר־י֣וֹם בְּיוֹמ֗וֹ מִפַּת־בַּ֤ג הַמֶּ֙לֶךְ֙ וּמִיֵּ֣ין מִשְׁתָּ֔יו וּֽלְגַדְּלָ֖ם שָׁנִ֣ים שָׁל֑וֹשׁ וּמִ֨קְצָתָ֔ם יַֽעַמְד֖וּ לִפְנֵ֥י הַמֶּֽלֶךְ ׃"
    for string in ( dan11, dan12, dan13, dan14, dan15 ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h = Hebrew( string )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeCantillationMarks()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed cantillation marks" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeVowelPointing()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed vowel pointing" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.removeOtherMarks()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Removed other marks" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} meteg or siluq marks remaining".format( msCount ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        h.verifyConsonantsOnly()
        h = Hebrew( string )
        h.removeCantillationMarks()
        #h.printUnicodeData()
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Transliterated: {}".format( h.transliterate() ) )
# end of Hebrew.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Hebrew.py
