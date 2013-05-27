#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Hebrew.py
#   Last modified: 2013-05-27 (also update versionString below)
#
# Module handling Hebrew language
#
# Copyright (C) 2011-2013 Robert Hunt
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
Module handling Hebrew language particularities.
"""

progName = "Hebrew language handler"
versionString = "0.04"

import os, unicodedata
from gettext import gettext as _

import Globals


# Consonants
alef = 'א'
bet = 'ב'
gimel = 'ג'
dalet = 'ד'
he = 'ה'
waw = 'ו'
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
assert( len(normalConsonants) == 22 )
finalConsonants = ( memFinal, nunFinal, tsadiFinal, qofFinal, )
consonants = normalConsonants + finalConsonants
allFinalConsonants = ( alef, bet, gimel, dalet, he, waw, zayin, het, tet, yod, kaf, lamed, memFinal, nunFinal, samekh, ayin, pe, tsadiFinal, qofFinal, resh, sinShin, taw, )


# Vowel points
sheva = 'ְ'
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
sofPasuq = '׃'


if Globals.debugFlag: # Check that our tables have no obvious errors
    for j,letter in enumerate( consonants ):
        #print( j, letter )
        assert( consonants.count(letter)==1 )
        assert( letter not in vowelPoints )
        assert( letter not in otherMarks )
        assert( letter not in cantillationMarks )
    for j,mark in enumerate( vowelPoints ):
        #print( j, mark )
        assert( vowelPoints.count(mark)==1 )
        assert( mark not in consonants )
        assert( mark not in otherMarks )
        assert( mark not in cantillationMarks )
    for j,mark in enumerate( otherMarks ):
        #print( j, mark )
        assert( otherMarks.count(mark)==1 )
        assert( mark not in consonants )
        assert( mark not in vowelPoints )
        assert( mark not in cantillationMarks )
    for j,mark in enumerate( cantillationMarks ):
        #print( j, mark )
        assert( cantillationMarks.count(mark)==1 )
        assert( mark not in consonants )
        assert( mark not in vowelPoints )
        assert( mark not in otherMarks )

    printUnicodeInfo( vowelPoints, "Vowel points" )
    printUnicodeInfo( cantillationMarks, "Cantillation marks" )



class Hebrew():
    """
    Class for handling a Hebrew string.
    """
    def __init__( self, text ):
        """ Create an new Hebrew object. """
        self.originalText = text
        self.currentText = text
    # end of Hebrew.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Hebrew object"
        result += ('\n' if result else '') + "  " + _("Original = '{}'").format( self.originalText )
        if self.currentText != self.originalText:
            result += ('\n' if result else '') + "  " + _("Current  = '{}'").format( self.currentText )
        return result
    # end of Hebrew.__str__


    def printUnicodeData( self, text=None ):
        if text is None: text = self.currentText
        print( "unicodedata", unicodedata.unidata_version )
        def printUnicodeInfo( text, description ):
            print( "{}:".format( description ) )
            for j,char in enumerate(text):
                print( "{:2} {:04x} {} '{}'   (cat={} bid={} comb={} mirr={})" \
                    .format(j, ord(char), unicodedata.name(char), char, unicodedata.category(char), unicodedata.bidirectional(char), unicodedata.combining(char), unicodedata.mirrored(char) ) )
    # end of Hebrew.printUnicodeData


    def verifyConsonantsOnly( self, text=None ):
        """ Check that we only have consonants left """
        if text is None: text = self.currentText
        haveError = False
        textLength = len( text )
        this = ( ' ', '־', )
        for j,letter in enumerate(text):
            if letter not in consonants and letter not in this:
                print( "Found unexpected '{}' ({}) non-consonant at index {} in '{}'".format( letter, unicodedata.name(letter), j, text ) )
                haveError = True
            if letter in finalConsonants and j<textLength-1:
                nextLetter = text[j+1]
                if nextLetter not in this:
                    print( "Found unexpected '{}' ({}) final consonant before '{}' ({}) at index {} in '{}'".format( letter, unicodedata.name(letter), nextLetter, unicodedata.name(nextLetter), j, text ) )
                    haveError = True
        return haveError
    # end of Hebrew.verifyConsonantsOnly


    def removeAllMetegOrSiluq( self, text=None ):
        if text is None: # Use our own text
            self.currentText = self.removeAllMetegOrSiluq( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        text = text.replace( metegOrSiluq, '' )
        return text
    # end of Hebrew.removeAllMetegOrSiluq


    def _removeMetegOrSiluq( self, text, asVowel ):
        """ It's actually often impossible to tell automatically which purpose this Unicode mark has. """
        while text:
            textLength = len( text )
            madeChanges = False
            for j,mark in enumerate(text):
                if mark != metegOrSiluq: continue
                previousMark = text[j-1] if j>0 else ''
                nextMark = text[j+1] if j<textLength-1 else ''
                if previousMark in ( patah, segol ) or nextMark in (): # Assume it's a vowel point meteg
                    if asVowel:
                        print( "Deleting (vowel point) meteg after '{}' ({}) and before '{}' ({})".format( previousMark, unicodedata.name(previousMark), nextMark, unicodedata.name(nextMark) ) )
                        text = text[:j] + text[j+1:]
                        madeChanges = True
                        break
                    else: print( "Ignoring (vowel point) meteg/siluq after '{}' ({}) and before '{}' ({})".format( previousMark, unicodedata.name(previousMark), nextMark, unicodedata.name(nextMark) ) )
                else: # it doesn't appear to be a vowel point meteg
                    if not asVowel:
                        print( "Deleting (cantillation mark) siluq after '{}' ({}) and before '{}' ({})".format( previousMark, unicodedata.name(previousMark), nextMark, unicodedata.name(nextMark) ) )
                        text = text[:j] + text[j+1:]
                        madeChanges = True
                        break
                    else: print( "Ignoring (cantillation mark) meteg/siluq after '{}' ({}) and before '{}' ({})".format( previousMark, unicodedata.name(previousMark), nextMark, unicodedata.name(nextMark) ) )
            if not madeChanges: break # Check for another meteg if we made any changes
        return text
    # end of Hebrew._removeMetegOrSiluq


    def removeCantillationMarks( self, text=None, removeMetegOrSiluq=False ):
        """ Return the text with cantillation marks removed. """
        if text is None: # Use our own text
            self.currentText = self.removeCantillationMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        if removeMetegOrSiluq: text = self._removeMetegOrSiluq( text, asVowel=False )
        for cantillationMark in cantillationMarks: text = text.replace(cantillationMark, '')
        return text
    # end of Hebrew.removeCantillationMarks


    def removeVowelPointing( self, text=None, removeMetegOrSiluq=False ):
        """ Return the text with cantillation marks removed. """
        if text is None: # Use our own text
            self.currentText = self.removeVowelPointing( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        if removeMetegOrSiluq: text = self._removeMetegOrSiluq( text, asVowel=True )
        for vowelPoint in vowelPoints: text = text.replace(vowelPoint, '') # Remove the easy vowel points
        return text
    # end of Hebrew.removeVowelPointing


    def removeOtherMarks( self, text=None ):
        """ Return the text with other marks (like sin/shin marks) and any remaining metegOrSiluq removed. """
        if text is None: # Use our own text
            self.currentText = self.removeOtherMarks( self.currentText ) # recursive call
            return self.currentText
        # else we were given some text to process
        text = self.removeAllMetegOrSiluq( text )
        for otherMark in otherMarks: text = text.replace(otherMark, '')
        return text
    # end of Hebrew.removeOtherMarks
# end of Hebrew class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    # Demonstrate the Hebrew class
    print( "These all display left-to-right in the terminal unfortunately  :-(" )
    dan11 = "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה בָּ֣א נְבוּכַדְנֶאצַּ֧ר מֶֽלֶךְ־בָּבֶ֛ל יְרוּשָׁלִַ֖ם וַיָּ֥צַר עָלֶֽיהָ ׃"
    dan12 = "וַיִּתֵּן֩ אֲדֹנָ֨י בְּיָד֜וֹ אֶת־יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֗ה וּמִקְצָת֙ כְּלֵ֣י בֵית־הָֽאֱלֹהִ֔ים וַיְבִיאֵ֥ם אֶֽרֶץ־שִׁנְעָ֖ר בֵּ֣ית אֱלֹהָ֑יו וְאֶת־הַכֵּלִ֣ים הֵבִ֔יא בֵּ֖ית אוֹצַ֥ר אֱלֹהָֽיו ׃"
    dan13 = "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו לְהָבִ֞יא מִבְּנֵ֧י יִשְׂרָאֵ֛ל וּמִזֶּ֥רַע הַמְּלוּכָ֖ה וּמִן־הַֽפַּרְתְּמִֽים ׃"
    dan14 = "יְלָדִ֣ים אֲשֶׁ֣ר אֵֽין־בָּהֶ֣ם כָּל־מאום וְטוֹבֵ֨י מַרְאֶ֜ה וּמַשְׂכִּילִ֣ים בְּכָל־חָכְמָ֗ה וְיֹ֤דְעֵי דַ֙עַת֙ וּמְבִינֵ֣י מַדָּ֔ע וַאֲשֶׁר֙ כֹּ֣חַ בָּהֶ֔ם לַעֲמֹ֖ד בְּהֵיכַ֣ל הַמֶּ֑לֶךְ וּֽלֲלַמְּדָ֥ם סֵ֖פֶר וּלְשׁ֥וֹן כַּשְׂדִּֽים ׃"
    dan15 = "וַיְמַן֩ לָהֶ֨ם הַמֶּ֜לֶךְ דְּבַר־י֣וֹם בְּיוֹמ֗וֹ מִפַּת־בַּ֤ג הַמֶּ֙לֶךְ֙ וּמִיֵּ֣ין מִשְׁתָּ֔יו וּֽלְגַדְּלָ֖ם שָׁנִ֣ים שָׁל֑וֹשׁ וּמִ֨קְצָתָ֔ם יַֽעַמְד֖וּ לִפְנֵ֥י הַמֶּֽלֶךְ ׃"
    for string in ( dan11, dan12, dan13, dan14, dan15 ):
        print()
        h = Hebrew( string )
        print( h )
        print()
        h.removeCantillationMarks()
        print( "Removed cantillation marks" )
        print( h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: print( "{} meteg or siluq marks remaining".format( msCount ) )
        print()
        h.removeVowelPointing()
        print( "Removed vowel pointing" )
        print( h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: print( "{} meteg or siluq marks remaining".format( msCount ) )
        print()
        h.removeOtherMarks()
        print( "Removed other marks" )
        print( h )
        msCount = h.currentText.count(metegOrSiluq)
        if msCount: print( "{} meteg or siluq marks remaining".format( msCount ) )
        print()
        h.verifyConsonantsOnly()
# end of demo

if __name__ == '__main__':
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    demo()
# end of Hebrew.py