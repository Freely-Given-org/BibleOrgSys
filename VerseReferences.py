#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# VerseReferences.py
#
# Class handling Bible verse references
#
# Copyright (C) 2013-2015 Robert Hunt
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
Class for creating and manipulating our internal Bible verse references.

This module recognises and handles only our internal Bible references.

The native Bible reference string format in this system is tightly defined
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
    6/ No spaces are ever allowed.

Internally, we represent it as a Bible reference tuple (BBB,C,V,S,) where
    BBB is the three-character UPPERCASE reference abbreviation
    C is the chapter number string (There are some examples of letters being used for chapter "numbers")
    V is the verse number string
    S is the single lowercase letter suffix (see above)

Our ranges are inclusive
    e.g., Gen_1:1-Gen_1:2 but Gen_1:1–Gen_2:3
    i.e., using a hyphen for a verse span but en-dash (–) for a span that crosses chapters or books.
"""

from gettext import gettext as _

LastModifiedDate = '2015-01-19' # by RJH
ShortProgName = "VerseReferences"
ProgName = "Bible verse reference handler"
ProgVersion = '0.18'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
import re

import BibleOrgSysGlobals


BBB_RE = '([A-Z][A-Z][A-Z,1-6])'
C_RE = '([1-9][0-9]{0,2})'
V_RE = '([1-9][0-9]{0,2})'
S_RE = '([a-f]?)'
# The following all include beginning and end markers, i.e., only match entire strings
VERSE_RE = '^{}_{}:{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE )
VERSES2_RE = '^{}_{}:{}{},{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, V_RE, S_RE )
VERSES2C_RE = '^{}_{}:{}{};{}:{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, C_RE, V_RE, S_RE )
VERSES3_RE = '^{}_{}:{}{},{}{},{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, V_RE, S_RE, V_RE, S_RE )
VERSES3C_RE = '^{}_{}:{}{};{}:{}{};{}:{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, C_RE, V_RE, S_RE, C_RE, V_RE, S_RE )
CHAPTER_RE = '^{}_{}$'.format( BBB_RE, C_RE )
VERSE_RANGE_RE = '^{}_{}:{}{}-{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, V_RE, S_RE )
CHAPTER_RANGE_RE = '^{}_{}:{}{}–{}:{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, C_RE, V_RE, S_RE )
# Special cases
VERSE_RANGE_PLUS_RE = '^{}_{}:{}{}-{}{},{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, V_RE, S_RE, V_RE, S_RE )
VERSE_PLUS_RANGE_RE = '^{}_{}:{}{},{}{}-{}{}$'.format( BBB_RE, C_RE, V_RE, S_RE, V_RE, S_RE, V_RE, S_RE )


def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}: {}'.format( nameBit, _(errorBit) )
# end of t



class SimpleVerseKey():
    """
    Handles individual verse references (no ranges, etc. allowed) in the internal BCVS form
        where   B is the BBB reference code
                C is the chapter number string
                V is the verse number string
                S is the optional suffix string
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid book code
        and no checking is done on the validity of the CV values.

    A string to be parsed can also be passed as the first (and only) parameter.
        e.g. "SA2_12:9b"
    """
    def __init__( self, BBB, C=None, V=None, S=None, ignoreParseErrors=False ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("__init__( {!r}, {!r}, {!r}, {!r} )").format( BBB, C, V, S ) )
        self.ignoreParseErrors = ignoreParseErrors
        if C is None and V is None and S is None: # assume it's a string to be parsed
            #if BibleOrgSysGlobals.debugFlag:
            #    assert( isinstance( BBB, str ) and 7<=len(BBB)<=16 )
            if not self.parseReferenceString( BBB ):
                raise TypeError
        else: # assume it's a BBB/C/V/(S) call
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
            self.keyType = 'AssignedBVCS'
    # end of SimpleVerseKey.__init__

    def __eq__( self, other ):
        #if type( other ) is type( self ): return self.__dict__ == other.__dict__
        if type( other ) is type( self ):
            return self.BBB==other.BBB and self.C==other.C and self.V==other.V and self.S==other.S
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __repr__(self): return self.__str__()
    def __str__( self ): return "SimpleVerseKey object: {}".format( self.getShortText() )
    def getShortText( self ):
        return "{} {}:{}{}".format( self.BBB, self.C, self.V, self.S )
        #except AttributeError: return 'Invalid'
    def getVerseKeyText( self ):
        return "{}_{}:{}{}".format( self.BBB, self.C, self.V, self.S )

    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}{}:{}{}".format( self.BBB, self.C, self.V, self.S )
    def __hash__( self ): return hash( self.makeHash() )

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
        except ValueError:
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
        except ValueError:
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

    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("parseReferenceString( {!r} )").format( referenceString ) )
        match = re.search( VERSE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            self.BBB, self.C, self.V, self.S = match.group(1), match.group(2), match.group(3), match.group(4)
            if self.BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( self.BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.keyType = 'ParsedBVCS'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of SimpleVerseKey.parseReferenceString

    def getIncludedVerses( self ):
        yield self
    # end of SimpleVerseKey.getIncludedVerses
# end of class SimpleVerseKey



class SimpleVersesKey():
    """
    Handles individual verse references (no ranges, etc. allowed) in the internal BCVS form
        where   B is the BBB reference code
                C is the chapter number string
                V is the verse number string
                S is the optional suffix string
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid book code
        and no checking is done on the validity of the CV values.

    A string to be parsed can also be passed as the first (and only) parameter.
        e.g. "SA2_12:9b"
    """
    def __init__( self, referenceString, ignoreParseErrors=False ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("__init__( {!r} )").format( referenceString ) )
        self.ignoreParseErrors = ignoreParseErrors
        #if BibleOrgSysGlobals.debugFlag:
        #    assert( isinstance( referenceString, str ) and 7<=len(referenceString)<=16 )
        self.verseKeysList = []
        if not self.parseReferenceString( referenceString ):
            raise TypeError
    # end of SimpleVersesKey.__init__

    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __repr__(self): return self.__str__()
    def __str__( self ): return "SimpleVersesKey object: {}".format( self.getShortText() )
    def getShortText( self ):
        resultStr = ''
        for svk in self.verseKeysList:
            if resultStr: resultStr += ', '
            resultStr += svk.getShortText()
        return resultStr    
        #if self.keyType=='2V': return "{} {}:{}{},{}{}".format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2 )
        #if self.keyType=='2CV': return "{} {}:{}{};{}:{}{}".format( self.BBB, self.C1, self.V1, self.S1, self.C2, self.V2, self.S2 )
        #print( self.keyType ); halt

    """
    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}{}:{}{}".format( self.BBB, self.C, self.V, self.S )
    def __hash__( self ): return hash( self.makeHash() )

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
        except ValueError:
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
        except ValueError:
            logging.warning( t("getVerseNumberInt: Unusual V value: {}").format( repr(self.V) ) )
            if self.V and self.V[0].isdigit():
                digitCount = 0
                for char in self.V:
                    if char.isdigit(): digitCount += 1
                return( int( self.V[:digitCount] ) )
            return None
    # end of SimplesVerseKey.getVerseNumberInt

    def getOSISBookAbbreviation( self ):
        return BibleOrgSysGlobals.BibleBooksCodes.getOSISAbbreviation( self.BBB )
    def getOSISReference( self ):
        return "{}.{}.{}".format( self.getOSISBookAbbreviation(), self.C, self.V )
    """
    
    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("parseReferenceString( {!r} )").format( referenceString ) )
        match = re.search( VERSES2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4)
            V2, S2 = match.group(5), match.group(6)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2)]
            self.keyType = '2V'
            return True
        match = re.search( VERSES2C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4)
            C2, V2, S2 = match.group(5), match.group(6), match.group(7)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.verseKeysList = [SimpleVerseKey(BBB,C1,V1,S1), SimpleVerseKey(BBB,C2,V2,S2)]
            self.keyType = '2CV'
            return True
        match = re.search( VERSES3_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4)
            V2, S2 = match.group(5), match.group(6)
            V3, S3 = match.group(7), match.group(8)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.keyType = '3V'
            return True
        match = re.search( VERSES3C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4)
            C2, V2, S2 = match.group(5), match.group(6), match.group(7)
            C3, V3, S3 = match.group(8), match.group(9), match.group(10)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.keyType = '3CV'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of SimpleVersesKey.parseReferenceString

    def getIncludedVerses( self ):
        for iv in self.verseKeysList:
            yield iv
    # end of SimpleVerseKey.getIncludedVerses
# end of class SimpleVersesKey



class VerseRangeKey():
    """
    Handles verse ranges in the internal BCVS form
        where   B is the BBB reference code
                C is the chapter number string
                V is the verse number string
                S is the optional suffix string
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid book code
        and no checking is done on the validity of the CV values.

    A string to be parsed can also be passed as the first (and only) parameter.
        e.g. "SA2_12:2-3"
            "SA2_12:22–13:2" (with en-dash)
            "GEN 18"
    """
    def __init__( self, referenceString, ignoreParseErrors=False ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("__init__( {!r} )").format( referenceString ) )
        self.ignoreParseErrors = ignoreParseErrors
        #if BibleOrgSysGlobals.debugFlag:
        #    assert( isinstance( referenceString, str ) and 7<=len(referenceString)<=16 )
        #self.verseKeysList = []
        if not self.parseReferenceString( referenceString ):
            raise TypeError
    # end of VerseRangeKey.__init__

    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __repr__(self): return self.__str__()
    def __str__( self ): return "VerseRangeKey object: {}".format( self.getShortText() )
    def getShortText( self ):
        return '{}-{}'.format( self.rangeStart.getShortText(), self.rangeEnd.getShortText() )
        #if self.keyType=='V-V': return "{} {}:{}{}-{}{}".format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2 )
        #if self.keyType=='CV-CV': return "{} {}:{}{}-{}:{}{}".format( self.BBB, self.C, self.V1, self.S1, self.C2, self.V2, self.S2 )
        #if self.keyType=='C': return "{} {}".format( self.BBB, self.C )
        #print( self.keyType ); halt

    """
    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}{}:{}{}".format( self.BBB, self.C, self.V, self.S )
    def __hash__( self ): return hash( self.makeHash() )

    def __len__( self ): return 4
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.BBB
        elif keyIndex==1: return self.C
        elif keyIndex==2: return self.V1
        elif keyIndex==3: return self.S1
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
        except ValueError:
            logging.warning( t("getChapterNumberInt: Unusual C value: {}").format( repr(self.C) ) )
            if self.C and self.C[0].isdigit():
                digitCount = 0
                for char in self.C:
                    if char.isdigit(): digitCount += 1
                return( int( self.C[:digitCount] ) )
            return None
    # end of VerseRangeKey.getChapterNumberInt

    def getVerseNumberInt( self ):
        try: return( int( self.V ) )
        except ValueError:
            logging.warning( t("getVerseNumberInt: Unusual V value: {}").format( repr(self.V) ) )
            if self.V and self.V[0].isdigit():
                digitCount = 0
                for char in self.V:
                    if char.isdigit(): digitCount += 1
                return( int( self.V[:digitCount] ) )
            return None
    # end of VerseRangeKey.getVerseNumberInt
    """
    
    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("parseReferenceString( {!r} )").format( referenceString ) )
        match = re.search( VERSE_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4)
            V2, S2 = match.group(5), match.group(6)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.rangeStart = SimpleVerseKey( BBB, C, V1, S1 )
            self.rangeEnd = SimpleVerseKey( BBB, C, V2, S2 )
            self.verseKeysList = []
            V, S = V1, S1
            while True:
                if V==V2:
                    self.verseKeysList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
                    break
                self.verseKeysList.append( SimpleVerseKey( BBB, C, V ) )
                V = str( int(V) + 1 )
            self.keyType = 'V-V'
            return True
        match = re.search( CHAPTER_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4)
            C2, V2, S2 = match.group(5), match.group(6), match.group(7)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.rangeStart = SimpleVerseKey( BBB, C1, V1, S1 )
            self.rangeEnd = SimpleVerseKey( BBB, C2, V2, S2 )
            self.verseKeysList = []
            V, S = V1, S1
            while True:
                if V==V2:
                    self.verseKeysList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
                    break
                self.verseKeysList.append( SimpleVerseKey( BBB, C, V ) )
                C, V = str( int(C) + 1), str( int(V) + 1 )
            self.keyType = 'CV-CV'
            return True
        match = re.search( CHAPTER_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.rangeStart = SimpleVerseKey( BBB, C, '1' )
            self.rangeEnd = SimpleVerseKey( BBB, C, '999' )
            self.keyType = 'C'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "VerseRangeKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of VerseRangeKey.parseReferenceString

    def getIncludedVerses( self ):
        for iv in self.verseKeysList:
            yield iv
    # end of SimpleVerseKey.getIncludedVerses
# end of class VerseRangeKey



class FlexibleVersesKey():
    """
    Handles verse ranges in the internal BCVS form
        where   B is the BBB reference code
                C is the chapter number string
                V is the verse number string
                S is the optional suffix string
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid book code
        and no checking is done on the validity of the CV values.

    A string to be parsed can also be passed as the first (and only) parameter.
        e.g. "SA2_12:2-3"
            "SA2_12:22–13:2" (with en-dash)
            "GEN 18"
    """
    def __init__( self, referenceString ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("__init__( {!r} )").format( referenceString ) )
        if BibleOrgSysGlobals.debugFlag:
            assert( isinstance( referenceString, str ) and 5<=len(referenceString)<=20 )
        self.verseKeyObjectList = []
        if not self.parseReferenceString( referenceString ):
            raise TypeError
    # end of FlexibleVersesKey.__init__

    def __eq__( self, other ):
        if type( other ) is type( self ): return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other): return not self.__eq__(other)

    def __repr__(self): return self.__str__()
    def __str__( self ): return "FlexibleVersesKey object: {}".format( self.getShortText() )
    def getShortText( self ):
        resultText = ''
        for verseKeyObject in self.verseKeyObjectList:
            resultText += verseKeyObject.getShortText()
        return resultText
        #if self.keyType=='RESULT': return self.result.getShortText()
        #if self.keyType=='V-V,V': return '{} {}:{}{}-{}{},{}{}'.format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2, self.V3, self.S3 )
        #if self.keyType=='V,V-V': return '{} {}:{}{},{}{}-{}{}'.format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2, self.V3, self.S3 )
        #halt

    """
    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}{}:{}{}".format( self.BBB, self.C, self.V, self.S )
    def __hash__( self ): return hash( self.makeHash() )

    def __len__( self ): return len(self.result)
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.BBB
        elif keyIndex==1: return self.C
        elif keyIndex==2: return self.V
        elif keyIndex==3: return self.S
        else: raise IndexError

    def getBBB( self ): return self.result.getBBB()
    def getChapterNumber( self ): return self.result.getChapterNumber()
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
        except ValueError:
            logging.warning( t("getChapterNumberInt: Unusual C value: {}").format( repr(self.C) ) )
            if self.C and self.C[0].isdigit():
                digitCount = 0
                for char in self.C:
                    if char.isdigit(): digitCount += 1
                return( int( self.C[:digitCount] ) )
            return None
    # end of VerseRangeKey.getChapterNumberInt

    def getVerseNumberInt( self ):
        try: return( int( self.V ) )
        except ValueError:
            logging.warning( t("getVerseNumberInt: Unusual V value: {}").format( repr(self.V) ) )
            if self.V and self.V[0].isdigit():
                digitCount = 0
                for char in self.V:
                    if char.isdigit(): digitCount += 1
                return( int( self.V[:digitCount] ) )
            return None
    # end of VerseRangeKey.getVerseNumberInt
    """
    
    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("parseReferenceString( {!r} )").format( referenceString ) )
        try:
            resultKey = SimpleVerseKey( referenceString, ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            #self.keyType = 'RESULT'
            return True
        except TypeError: pass
        try:
            resultKey = SimpleVersesKey( referenceString, ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            #self.keyType = 'RESULT'
            return True
        except TypeError: pass
        try:
            self.resultKey = VerseRangeKey( referenceString, ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            #self.keyType = 'RESULT'
            return True
        except TypeError: pass

        match = re.search( VERSE_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4)
            V2, S2 = match.group(5), match.group(6)
            V3, S3 = match.group(7), match.group(8)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            self.resultKey = VerseRangeKey( '{}_{}:{}{}-{}{}'.format( BBB, C, V1, S1, V2, S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            resultKey = SimpleVerseKey( '{}_{}:{}{}'.format( BBB, C, V3, S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V-V,V'
            return True
        match = re.search( VERSE_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4)
            V2, S2 = match.group(5), match.group(6)
            V3, S3 = match.group(7), match.group(8)
            if BBB not in BibleOrgSysGlobals.BibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
            resultKey = SimpleVerseKey( '{}_{}:{}{}'.format( BBB, C, V1, S1 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.resultKey = VerseRangeKey( '{}_{}:{}{}-{}{}'.format( BBB, C, V2, S2, V3, S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V,V-V'
            return True

        logging.error( "FlexibleVersesKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of FlexibleVersesKey.parseReferenceString


    def getIncludedVerses( self ):
        #print( self.keyType )
        if self.keyType=='RESULT':
            #print( self.result )
            return self.result.getIncludedVerses()
    # end of FlexibleVersesKey.getIncludedVerses
# end of class FlexibleVersesKey



def demo():
    """
    Short program to demonstrate/test the above class(es).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    badStrings = ( 'Gn_1:1', '2KI_3:17', 'MAL_1234:1', 'MAT_1:1234', )
    
    goodVerseStrings = ( 'SA2_19:12', 'REV_11:12b', )
    badVerseStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', '2SA_19:12', 'REV_11:12z', )
    if 1: # test SimpleVerseKey
        print( "\n\nTesting SimpleVerseKey..." )
        for something in ( ('GEN','1','1'), ('GEN','1','1','a'), ):
            print( "  Testing SimpleVerseKey with {}".format( something ) )
            vK = SimpleVerseKey( *something )
            print( '  ', vK, "and", vK.getOSISReference() )
            print( '  ',vK == SimpleVerseKey( 'GEN', '1', '1' ), "then", vK == SimpleVerseKey( 'EXO', '1', '1' ) )
        for someGoodString in goodVerseStrings:
            vK = SimpleVerseKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            assert( vK.getVerseKeyText() == someGoodString )
        print( '  BAD STUFF...' )
        for someBadString in badVerseStrings:
            try: print( '  ', repr(someBadString), SimpleVerseKey( someBadString ) )
            except TypeError: pass

    goodVersesStrings = ( 'SA2_19:12,19', 'REV_11:2b,6a', )
    badVersesStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV_3', 'NUM_1:1', '2SA_19:12', 'REV_11:12z', )
    if 1: # test SimpleVersesKey
        print( "\n\nTesting SimpleVersesKey..." )
        for someGoodString in goodVersesStrings:
            vK = SimpleVersesKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            #assert( vK.getVerseKeyText() == someGoodString )
        print( '  BAD STUFF...' )
        for someBadString in badVersesStrings:
            try: print( '  ', repr(someBadString), SimpleVersesKey( someBadString ) )
            except TypeError: pass

    goodRangeStrings = ( 'SA2_19:12-19', 'REV_11:2b-6a', )
    badRangeStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', 'NUM_1:1', '2SA_19:12', 'REV_11:12z', )
    if 1: # test VerseRangeKey
        print( "\n\nTesting VerseRangeKey..." )
        for someGoodString in goodRangeStrings:
            vK = VerseRangeKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            assert( vK.getShortText().replace(' ','_',1) == someGoodString )
        print( '  BAD STUFF...' )
        for someBadString in badRangeStrings:
            try: print( '  ', repr(someBadString), VerseRangeKey( someBadString ) )
            except TypeError: pass

    goodFlexibleStrings = goodVerseStrings + goodVersesStrings + goodRangeStrings \
                          + ( 'GEN_1:1,3-4', 'GEN_1:1-3,4', )
    badFlexibleStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', 'NUM_1234:1', '2SA_19:12', 'REV_11:12z', )
    if 1: # test FlexibleVersesKey
        print( "\n\nTesting FlexibleVersesKey..." )
        for someGoodString in goodFlexibleStrings:
            vK = FlexibleVersesKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            assert( vK.getShortText().replace(' ','_',1) == someGoodString )
        print( '  BAD STUFF...' )
        for someBadString in badFlexibleStrings:
            try: print( '  ', repr(someBadString), FlexibleVersesKey( someBadString ) )
            except TypeError: pass
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of VerseReferences.py
