#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# VerseReferences.py
#   Last modified: 2014-11-10 (also update ProgVersion below)
#
# Module handling Bible verse references
#
# Copyright (C) 2013-2014 Robert Hunt
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
Module for creating and manipulating our internal Bible verse references.

This module recognises and handles only our internal Bible references.

OSIS Bible references are of the form bookAbbreviation.chapterNumber.verseNumber
        e.g., Gen.1.1 or Exod.20.10 or 2Chr.7.6 or Jude.1.2
    Note that the book abbreviation is not a constant length
            and may also start with a digit
        and that the same separator is repeated.

However, the native Bible reference string format in this system is more tightly defined
    e.g., GEN_1:1 or EXO_20:10 or CH2_7:6 or JDE_1:2b
We can see that
    1/ The Bible book code is always 3-characters, starting with a letter
        All letters are UPPERCASE
    2/ We use an underline character as the book / chapter separator
    3/ We use a colon as the chapter / verse separator
    4/ We treat all chapter and verse fields as strings
    5/ Verse numbers can include a lowercase letter suffix a..d
        representing very approximate portions of a verse
            a = first half of a verse
            b = second half of a verse
            c = final third of a verse
            d = final quarter of a verse

Internally, we represent it as a Bible reference tuple (BBB,C,V,S,) where
    BBB is the three-character UPPERCASE reference abbreviation
    C is the chapter number string (There are some examples of letters being used for chapter "numbers")
    V is the verse number string
    S is the single lowercase letter suffix (see above)

OSIS defines reference ranges
    e.g., Gen.1.1-Gen.1.2 or Gen.1.1-Gen.2.3 (inclusive)

Our ranges are slightly different (also inclusive)
    e.g., Gen_1:1-Gen_1:2 but Gen_1:1–Gen_2:3
    i.e., using a hyphen for a verse span but en-dash (–) for a span that crosses chapters or books.

OXES is different again and tends to remove the second (redundant) book identifier
    e.g., Gen.1.1-1.2 (if I remember correctly)
"""

ShortProgName = "VerseReferences"
ProgName = "Bible verse reference handler"
ProgVersion = "0.12"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _

import BibleOrgSysGlobals



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



class SimpleVerseKey():
    """
    Handles individual verse references (no ranges, etc. allowed) in the BCVS form
        where   B is the BBB reference code
                C is the chapter number string
                V is the verse number string
                S is the optional suffix string
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid abbreviation
        and no checking is done on the validity of the CV values.
    """
    def __init__( self, BBB, C, V, S=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("__init__( {} {} {} {} )").format( BBB, repr(C), repr(V), repr(S) ) )
        if S is None: S = ''
        if isinstance( C, int ): C = str( C ) # Make sure we have strings
        if isinstance( V, int ): V = str( V )
        if BibleOrgSysGlobals.debugFlag:
            assert( isinstance( BBB, str ) and len(BBB) == 3 )
            assert( isinstance( C, str ) and 1<=len(C)<=3 )
            assert( isinstance( V, str ) and 1<=len(V)<=3 )
            assert( isinstance( S, str ) and len(S)<3 )
            assert( BBB in BibleOrgSysGlobals.BibleBooksCodes or BBB=='   ' )
            for checkChar in ( ' -,.:' ):
                assert( checkChar not in BBB )
                assert( checkChar not in C )
                assert( checkChar not in V or ( C=='0' and V=='-1' ) ) # 0:-1 means the last bit of the book intro
                assert( checkChar not in S )
        self.BBB, self.C, self.V, self.S = BBB, C, V, S
    # end of SimpleVerseKey.__init__

    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __str__( self ): return "SimpleVerseKey object: {}".format( self.getShortText() )
    def getShortText( self ): return "{} {}:{}{}".format( self.BBB, self.C, self.V, self.S )
    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}{}:{}{}".format( self.BBB, self.C, self.V, self.S )

    def __len__( self ): return 4
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.BBB
        elif keyIndex==1: return self.C
        elif keyIndex==2: return self.V
        elif keyIndex==3: return self.S
        else: raise IndexError

    def getBBB( self ): return self.BBB
    def getChapterNumber( self ): return self.C
    def getChapterNumberStr( self ): return self.C
    def getVerseNumber( self ): return self.V
    def getVerseNumberStr( self ): return self.V
    def getVerseSuffix( self ): return self.S

    def getBCV( self ): return self.BBB, self.C, self.V
    def getBCVS( self ): return self.BBB, self.C, self.V, self.S
    def getCV( self ): return self.C, self.V
    def getCVS( self ): return self.C, self.V, self.S

    def getChapterNumberInt( self ):
        try: return( int( self.C ) )
        except:
            logging.warning( t("getChapterNumberInt: Unusual C value: {}").format( repr(self.C) ) )
            if self.C and self.C[0].isdigit():
                digitCount = 0
                for char in self.C:
                    if char.isdigit(): digitCount += 1
                return( int( self.C[:digitCount] ) )
            return None
    # end of SimpleVerseKey.getChapterNumberInt

    def getVerseNumberInt( self ):
        try: return( int( self.V ) )
        except:
            logging.warning( t("getVerseNumberInt: Unusual V value: {}").format( repr(self.V) ) )
            if self.V and self.V[0].isdigit():
                digitCount = 0
                for char in self.V:
                    if char.isdigit(): digitCount += 1
                return( int( self.V[:digitCount] ) )
            return None
    # end of SimpleVerseKey.getVerseNumberInt

    def getOSISBookAbbreviation( self ):
        return BibleOrgSysGlobals.BibleBooksCodes.getOSISAbbreviation( self.BBB )
    def getOSISReference( self ):
        return "{}.{}.{}".format( self.getOSISBookAbbreviation(), self.C, self.V )
# end of class SimpleVerseKey



def demo():
    """
    Short program to demonstrate/test the above class(es).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    vK = SimpleVerseKey( 'GEN', '1', '1' )
    print( vK, "and", vK.getOSISReference() )
    print( vK == SimpleVerseKey( 'GEN', '1', '1' ), "then", vK == SimpleVerseKey( 'EXO', '1', '1' ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of VerseReferences.py