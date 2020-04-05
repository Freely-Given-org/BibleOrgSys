#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# VerseReferences.py
#
# Class handling internal BOS Bible verse references
#
# Copyright (C) 2013-2019 Robert Hunt
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
    e.g., GEN_1:1 or EXO_20:10 or CH2_7:6 or JDE_1:2!b or REV_9:1!7
    i.e., BBB_C:V or BBB_C:V   or BBB_C:V or BBB_C:V!S or BBB_C:V!I
We can see that
    1/ The Bible book code is always 3-characters, starting with a letter
        All letters are UPPERCASE
    2/ We use an underline character as the book / chapter separator
    3/ We use a colon as the chapter / verse separator
    4/ We treat all chapter and verse fields as strings
    5/ Verse numbers can include a lowercase letter suffix a..d preceded by !
        representing very approximate portions of a verse
            a = first half of a verse
            b = second half of a verse
            c = final third of a verse
            d = final quarter of a verse
    6/ No spaces are ever allowed.

Internally, we represent it as a Bible reference tuple (BBB,C,V,S,) or (BBB,C,V,I)
also called BCVS or BCVI where
    BBB is the three-character UPPERCASE reference abbreviation
    C is the chapter number string (There are some examples of letters being used for chapter "numbers")
    V is the verse number string
    S is the single lowercase letter suffix (see above)
    I is the index into the verse (0=first letter of verse, maximum of 2-digits)

Our ranges are inclusive
    e.g., Gen_1:1-Gen_1:2 but Gen_1:1–Gen_2:3
    i.e., using a hyphen for a verse span but en-dash (–) for a span that crosses chapters or books.

We have four classes here:
    SimpleVerseKey (accepts 'GEN_1:1' or 'GEN','1','1')
    SimpleVersesKey (accepts 'MAT_6:1,4')
    VerseRangeKey (accepts 'JNA_2:1-7')
    FlexibleVersesKey (accepts all of the above plus more)

Each class can return
    getVerseKeyText which returns strings in our easily-parsed internal format, e.g. 'EXO_17:4!b'
    getShortText which returns a human readable format, e.g., 'EXO 17:4b'
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-29' # by RJH
SHORT_PROGRAM_NAME = "VerseReferences"
PROGRAM_NAME = "Bible verse reference handler"
PROGRAM_VERSION = '0.39'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import re
import logging


if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


# Regular expressions to be searched for
#       \d      Matches any decimal digit; this is equivalent to the class [0-9].
#       \D      Matches any non-digit character; this is equivalent to the class [^0-9].
#       \s      Matches any whitespace character; this is equivalent to the class [ \t\n\r\f\v].
#       \S      Matches any non-whitespace character; this is equivalent to the class [^ \t\n\r\f\v].
#       \w      Matches any alphanumeric character; this is equivalent to the class [a-zA-Z0-9_].
#       \W      Matches any non-alphanumeric character; this is equivalent to the class [^a-zA-Z0-9_].
#
#       ?       Matches sequence zero or once (i.e., for something that's optional) -- same as {0,1}
#       *       Matches sequence zero or more times (greedy) -- same as {0,}
#       +       Matches sequence one or more times -- same as {1,}
#       {m,n}   Matches at least m repetitions, and at most n
#
#       |       Alternation, or "or" operator
#
#       (?:…) Non-capturing group (matched substring can't be retrieved)
#
#       All metacharacters (which must be escaped to search for literals): . ^ $ * + ? { } [ ] \ | ( )
#
BBB_RE = '([A-PR-XZ][A-EG-VX-Z1][A-WYZ1-6])' # Finds BBB codes only (as strict as possible) -- see Apps/TestBooksCodesRE.py
C_RE = '([1-9][0-9]?|[1][0-9][0-9])' #  Chapter numbers 1..199 (doesn't handle chapters -1 or 0)
V_RE = '([1-9][0-9]?|[1][0-9][0-9])' #  Verse numbers 1..199 (doesn't handle verse 0)
S_RE = '!([a-d]?)'
I_RE = '!([0-9]{1,3})' #  Index numbers 0..999 (maybe ! should be \\.)

# Derived REs
CV_RE = '{}:{}'.format( C_RE, V_RE )
VS_RE = '{}(?:{})?'.format( V_RE, S_RE ) # Subscript (with !) is optional
VI_RE = '{}(?:{})?'.format( V_RE, I_RE ) # Subscript (with .) is optional
CVS_RE = '{}:{}'.format( C_RE, VS_RE )
CVI_RE = '{}:{}'.format( C_RE, VI_RE )
BCVS_RE = '{}_{}'.format( BBB_RE, CVS_RE )
BCVI_RE = '{}_{}'.format( BBB_RE, CVI_RE )
BCVSI_RE = '{}_{}(?:(?:{})|(?:{}))?'.format( BBB_RE, CV_RE, S_RE, I_RE )

# The following all include beginning and end markers, i.e., only match entire strings
BCVS1_RE = re.compile( '^{}$'.format( BCVS_RE ) )
BCVI1_RE = re.compile( '^{}$'.format( BCVI_RE ) )
BCVS2_RE = re.compile( '^{},{}$'.format( BCVS_RE, VS_RE ) )
BCVS2C_RE = re.compile( '^{};{}$'.format( BCVS_RE, CVS_RE ) )
BCVS3_RE = re.compile( '^{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE ) )
BCVS3C_RE = re.compile( '^{};{};{}$'.format( BCVS_RE, CVS_RE, CVS_RE ) )
BCVS4_RE = re.compile( '^{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS5_RE = re.compile( '^{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS6_RE = re.compile( '^{},{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS7_RE = re.compile( '^{},{},{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS8_RE = re.compile( '^{},{},{},{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS9_RE = re.compile( '^{},{},{},{},{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
CHAPTER_RE = re.compile( '^{}_{}$'.format( BBB_RE, C_RE ) )
BCVS_RANGE_RE = re.compile( '^{}-{}$'.format( BCVS_RE, VS_RE ) )
CHAPTER_RANGE_RE = re.compile( '^{}–{}$'.format( BCVS_RE, CVS_RE ) )
# Special cases
BCVS_RANGE_PLUS_RE = re.compile( '^{}-{},{}$'.format( BCVS_RE, VS_RE, VS_RE ) )
BCVS_RANGE_PLUS2_RE = re.compile( '^{}-{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGE_PLUS3_RE = re.compile( '^{}-{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGE_PLUS4_RE = re.compile( '^{}-{},{},{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_PLUS_RANGE_RE = re.compile( '^{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE ) )
BCVS_PLUS_RANGES2_RE = re.compile( '^{},{}-{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS2_PLUS_RANGES2_RE = re.compile( '^{},{},{}-{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGE_PLUS_RANGE_RE = re.compile( '^{}-{},{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGE_PLUS2_RANGE_RE = re.compile( '^{}-{},{},{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS2_PLUS_RANGE_RE = re.compile( '^{},{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS3_PLUS_RANGE_RE = re.compile( '^{},{},{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS4_PLUS_RANGE_RE = re.compile( '^{},{},{},{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_PLUS_RANGE_PLUS_RE = re.compile( '^{},{}-{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS2_PLUS_RANGE_PLUS_RE = re.compile( '^{},{},{}-{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGES2_RE = re.compile( '^{}-{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGES2_PLUS_RE = re.compile( '^{}-{},{}-{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGES2_PLUS2_RE = re.compile( '^{}-{},{}-{},{},{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGES3_RE = re.compile( '^{}-{},{}-{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )
BCVS_RANGES4_RE = re.compile( '^{}-{},{}-{},{}-{},{}-{}$'.format( BCVS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE, VS_RE ) )

# OSIS
OSIS_BOOK_RE = re.compile( '([1-5A-EG-JL-PRSTVWZ][BCEJKMPSTa-ehimoprsuxz](?:[AJMa-eghik-pr-v](?:[DEPacdeghklmnrstuvz](?:[Gachnrsz](?:[nrst][ah]?)?)?)?)?)' ) # Finds OSIS book codes
OSIS_C_RE = re.compile( '([1-9][0-9]?|[1][0-9][0-9])' ) #  Chapter numbers 1..199
OSIS_V_RE = re.compile( '([1-9][0-9]?|[1][0-9][0-9])' ) #  Verse numbers 1..199
OSIS_S_RE = re.compile( '([a-f]?)' )
# Derived REs
OSIS_VS_RE = '{}(?:!{})?'.format( OSIS_V_RE, OSIS_S_RE )
OSIS_CVS_RE = r'{}\.{}'.format( OSIS_C_RE, OSIS_VS_RE )
OSIS_BCVS_RE = '{}_{}'.format( OSIS_BOOK_RE, OSIS_CVS_RE )
# The following all include beginning and end markers, i.e., only match entire strings
OSIS_BCVS1_RE = re.compile( '^{}$'.format( OSIS_BCVS_RE ) )
OSIS_BCVS2_RE = re.compile( r'^{}\.{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE ) )
OSIS_BCVS2C_RE = re.compile( '^{};{}$'.format( OSIS_BCVS_RE, OSIS_CVS_RE ) )
OSIS_BCVS3_RE = re.compile( r'^{}\.{}\.{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE, OSIS_VS_RE ) )
OSIS_BCVS3C_RE = re.compile( '^{};{};{}$'.format( OSIS_BCVS_RE, OSIS_CVS_RE, OSIS_CVS_RE ) )
OSIS_CHAPTER_RE = re.compile( '^{}_{}$'.format( OSIS_BOOK_RE, OSIS_C_RE ) )
OSIS_BCVS_RANGE_RE = re.compile( '^{}-{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE ) )
OSIS_CHAPTER_RANGE_RE = re.compile( '^{}–{}$'.format( OSIS_BCVS_RE, OSIS_CVS_RE ) )
# Special cases
OSIS_BCVS_RANGE_PLUS_RE = re.compile( r'^{}-{}\.{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE, OSIS_VS_RE ) )
OSIS_BCVS_PLUS_RANGE_RE = re.compile( r'^{}\.{}-{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE, OSIS_VS_RE ) )
OSIS_BCVS_PLUS_RANGE_PLUS_RE = re.compile( r'^{}\.{}-{}\.{}$'.format( OSIS_BCVS_RE, OSIS_VS_RE, OSIS_VS_RE, OSIS_VS_RE ) )



class SimpleVerseKey():
    """
    Handles individual verse references (no ranges, etc. allowed) in the internal BCVS or BCVI form
        where   B is the BBB reference code
                C is the chapter number string (-1 for book intro)
                V is the verse number string
                S is the optional suffix string
                I is the optional index into the verse
    The name or organisational system of the work is not specified
        so we can only check that BBB is a valid book code
        and no checking is done on the validity of the CV values.

    A BCVS string to be parsed can also be passed as the first (and only) parameter.
        e.g. 'SA2_12:9b'
    """
    def __init__( self, BBB, C=None, V=None, SI=None, OSIS=False, ignoreParseErrors=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SimpleVerseKey.__init__( {!r}, {!r}, {!r}, {!r} )".format( BBB, C, V, SI ) )

        self.ignoreParseErrors = ignoreParseErrors

        if C is None and V is None and SI is None: # assume it's a string to be parsed
            #if BibleOrgSysGlobals.debugFlag:
            #    assert isinstance( BBB, str ) and 7<=len(BBB)<=16
            parseFunction = self.parseOSISString if OSIS else self.parseReferenceString
            if not parseFunction( BBB ):
                raise TypeError

        else: # assume it's a BBB/C/V/(S/I) call
            if SI is None: SI = ''
            if isinstance( C, int ): C = str( C ) # Make sure we have strings
            if isinstance( V, int ): V = str( V )
            if isinstance( SI, int ): SI = str( SI )
            #if BibleOrgSysGlobals.debugFlag:
            if not isinstance( BBB, str ) or len(BBB) != 3 \
            or not BBB in BibleOrgSysGlobals.loadedBibleBooksCodes and BBB!='   ':
                logging.error( "SimpleVerseKey: bad {!r} BBB in {}".format( BBB, (BBB,C,V,SI) ) ); raise TypeError
            if not isinstance( C, str ) or not 1<=len(C)<=3:
                logging.error( "SimpleVerseKey: bad {!r} C in {}".format( C, (BBB,C,V,SI) ) ); raise TypeError
            if not isinstance( V, str ) or not 1<=len(V)<=3:
                logging.error( "SimpleVerseKey: bad {!r} V in {}".format( V, (BBB,C,V,SI) ) ); raise TypeError
            if not isinstance( SI, str ) or not ( len(SI)<2 or (SI.isdigit() and len(SI)<=4) ):
                logging.error( "SimpleVerseKey: bad {!r} S/I in {}".format( SI, (BBB,C,V,SI) ) ); raise TypeError
            for checkChar in ' -,.:':
                if checkChar in BBB \
                or (checkChar in C and C!='-1') \
                or checkChar in SI \
                or checkChar in V and ( C=='-1' and V=='-1' ): # -1:-1 means the last bit of the book intro
                    raise TypeError
            if SI and SI.isdigit():
                self.BBB, self.C, self.V, self.I, self.S = BBB, C, V, SI, None
                self.keyType = 'AssignedBCVI'
            else:
                self.BBB, self.C, self.V, self.S, self.I = BBB, C, V, SI, None
                self.keyType = 'AssignedBCVS'
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
        return "{} {}:{}{}".format( self.BBB, self.C, self.V, self.S if self.I is None else ('!'+self.I) )
        #except AttributeError: return 'Invalid'
    def getVerseKeyText( self ):
        return "{}_{}:{}{}{}".format( self.BBB, self.C, self.V, '!' if self.S or self.I else '', self.S if self.I is None else self.I )

    def makeHash( self ): # return a short, unambiguous string suitable for use as a key in a dictionary
        return "{}_{}:{}!{}".format( self.BBB, self.C, self.V, self.S if self.I is None else self.I )
    def __hash__( self ): return hash( self.makeHash() )

    def __len__( self ): return 4
    def __getitem__( self, keyIndex ):
        if keyIndex==0: return self.BBB
        elif keyIndex==1: return self.C
        elif keyIndex==2: return self.V
        elif keyIndex==3: return self.S if self.I is None else self.I
        else: raise IndexError

    def getBBB( self ): return self.BBB
    def getChapterNumber( self ): return self.C
    def getChapterNumberStr( self ): return self.C
    def getVerseNumber( self ): return self.V
    def getVerseNumberStr( self ): return self.V
    def getVerseSuffix( self ): return self.S
    def getVerseIndex( self ): return self.I

    def getBCV( self ): return self.BBB, self.C, self.V
    def getBCVS( self ): return self.BBB, self.C, self.V, self.S
    def getBCVI( self ): return self.BBB, self.C, self.V, self.I
    def getCV( self ): return self.C, self.V
    def getCVS( self ): return self.C, self.V, self.S
    def getCVI( self ): return self.C, self.V, self.I

    def getChapterNumberInt( self ):
        try: return int( self.C )
        except ValueError:
            logging.warning( "getChapterNumberInt: " + _("Unusual C value: {}").format( repr(self.C) ) )
            if self.C and self.C[0].isdigit():
                digitCount = 0
                for char in self.C:
                    if char.isdigit(): digitCount += 1
                return int( self.C[:digitCount] )
            return None
    # end of SimpleVerseKey.getChapterNumberInt

    def getVerseNumberInt( self ):
        try: return int( self.V )
        except ValueError:
            logging.warning( "getVerseNumberInt: " + _("Unusual V value: {}").format( repr(self.V) ) )
            if self.V and self.V[0].isdigit():
                digitCount = 0
                for char in self.V:
                    if char.isdigit(): digitCount += 1
                return int( self.V[:digitCount] )
            return None
    # end of SimpleVerseKey.getVerseNumberInt

    def getOSISBookAbbreviation( self ):
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( self.BBB )
    def getOSISReference( self ):
        return '{}.{}.{}'.format( self.getOSISBookAbbreviation(), self.C, self.V )

    def __iter__( self ):
        """
        Yields self (for compatibility with the more complex classes.
        """
        yield self
    # end of SimpleVerseKey.__iter__

    def getIncludedVerses( self ):
        """
        Yields self (for compatibility with the more complex classes.
        """
        yield self
    # end of SimpleVerseKey.getIncludedVerses


    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseOSISString( {!r} )".format( referenceString ) )

        match = re.search( BCVS1_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)) )
            self.BBB, self.C, self.V, self.S, self.I = match.group(1), match.group(2), match.group(3), (match.group(4) if match.group(4) else ''), None
            if self.BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert self.BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.keyType = 'ParsedBCVS'
            #print( self.getShortText() )
            return True

        match = re.search( BCVI1_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)) )
            self.BBB, self.C, self.V, self.I, self.S = match.group(1), match.group(2), match.group(3), (match.group(4) if match.group(4) else ''), None
            if self.BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert self.BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.keyType = 'ParsedBCVI'
            #print( self.getShortText() )
            return True

        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of SimpleVerseKey.parseReferenceString


    def parseOSISString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseReferenceString( {!r} )".format( referenceString ) )

        match = re.search( OSIS_BCVS1_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)) )
            bk, self.C, self.V, self.S, self.I = match.group(1), match.group(2), match.group(3), (match.group(4) if match.group(4) else ''), None
            self.BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( bk )
            if self.BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVerseKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert self.BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.keyType = 'ParsedBCVS'
            #print( self.getShortText() )
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse OSIS {!r}".format( referenceString ) )
        return False
    # end of SimpleVerseKey.parseOSISString
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
    def __init__( self, referenceString, OSIS=False, ignoreParseErrors=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "SimpleVersesKey.__init__( {!r} )".format( referenceString ) )

        self.ignoreParseErrors = ignoreParseErrors
        #if BibleOrgSysGlobals.debugFlag:
        #    assert isinstance( referenceString, str ) and 7<=len(referenceString)<=16
        self.keyType, self.verseKeysList = None, []
        parseFunction = self.parseOSISString if OSIS else self.parseReferenceString
        if not parseFunction( referenceString ):
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
        #if self.keyType=='2V': return "{} {}:{}(?:!{})?,{}(?:!{})?".format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2 )
        #if self.keyType=='2CV': return "{} {}:{}(?:!{})?;{}:{}(?:!{})?".format( self.BBB, self.C1, self.V1, self.S1, self.C2, self.V2, self.S2 )
        #print( self.keyType ); halt

    def getVerseKeyText( self ):
        resultStr = ''
        for j,svk in enumerate(self.verseKeysList):
            if j == 0:
                resultStr += svk.getVerseKeyText()
                lastBBB, lastC = svk.getBBB(), svk.getChapterNumberStr()
            else:
                BBB, C, V, S = svk.getBCVS()
                if BBB == lastBBB:
                    if C == lastC: resultStr += ',{}{}{}'.format( V, '!' if S else '', S )
                    else: resultStr += ';{}:{}{}{}'.format( C,V, '!' if S else '', S )
                else: resultStr += ';{}_{}:{}{}{}'.format( BBB, C,V, '!' if S else '', S )
                lastBBB, lastC = BBB, C
        return resultStr
    # end of SimpleVersesKey.getVerseKeyText

    def __iter__( self ):
        """
        Yields the verse keys one by one.
        """
        for verseKey in self.verseKeysList:
            yield verseKey
    # end of SimpleVersesKey.__iter__


    def getIncludedVerses( self ):
        for iv in self.verseKeysList:
            yield iv
    # end of SimpleVersesKey.getIncludedVerses


    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseReferenceString( {!r} )".format( referenceString ) )

        match = re.search( BCVS2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                print( "QWEQW", referenceString )
                assert int(V2)>int(V1)+1 or S2!=S1
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2)]
            self.keyType = '2V'
            return True
        match = re.search( BCVS2C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.verseKeysList = [SimpleVerseKey(BBB,C1,V1,S1), SimpleVerseKey(BBB,C2,V2,S2)]
            self.keyType = '2CV'
            return True
        match = re.search( BCVS3_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                print( "SDADQ", referenceString )
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3)]
            self.keyType = '3V'
            return True
        match = re.search( BCVS3C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            C3, V3, S3 = match.group(8), match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.verseKeysList = [SimpleVerseKey(BBB,C1,V1,S1), SimpleVerseKey(BBB,C2,V2,S2), SimpleVerseKey(BBB,C3,V3,S3)]
            self.keyType = '3CV'
            return True
        match = re.search( BCVS4_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                print( "CCVSD", referenceString )
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4)]
            self.keyType = '4V'
            return True
        match = re.search( BCVS5_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4), SimpleVerseKey(BBB,C,V5,S5)]
            self.keyType = '5V'
            return True
        match = re.search( BCVS6_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(12), match.group(13) if match.group(13) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4), SimpleVerseKey(BBB,C,V5,S5), SimpleVerseKey(BBB,C,V6,S6)]
            self.keyType = '6V'
            return True
        match = re.search( BCVS7_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            V7, S7 = match.group(15), match.group(16) if match.group(16) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
                assert int(V7)>int(V6)+1 or S7!=S6
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4), SimpleVerseKey(BBB,C,V5,S5), SimpleVerseKey(BBB,C,V6,S6),
                                  SimpleVerseKey(BBB,C,V7,S7)]
            self.keyType = '7V'
            return True
        match = re.search( BCVS8_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(12), match.group(13) if match.group(13) else ''
            V7, S7 = match.group(14), match.group(15) if match.group(15) else ''
            V8, S8 = match.group(16), match.group(17) if match.group(17) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
                assert int(V7)>int(V6)+1 or S7!=S6
                assert int(V8)>int(V7)+1 or S8!=S7
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4), SimpleVerseKey(BBB,C,V5,S5), SimpleVerseKey(BBB,C,V6,S6),
                                  SimpleVerseKey(BBB,C,V7,S7), SimpleVerseKey(BBB,C,V8,S8)]
            self.keyType = '8V'
            return True
        match = re.search( BCVS9_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(12), match.group(13) if match.group(13) else ''
            V7, S7 = match.group(14), match.group(15) if match.group(15) else ''
            V8, S8 = match.group(16), match.group(17) if match.group(17) else ''
            V9, S9 = match.group(18), match.group(19) if match.group(19) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
                assert int(V7)>int(V6)+1 or S7!=S6
                assert int(V8)>int(V7)+1 or S8!=S7
                assert int(V9)>int(V8)+1 or S9!=S8
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2), SimpleVerseKey(BBB,C,V3,S3),
                                  SimpleVerseKey(BBB,C,V4,S4), SimpleVerseKey(BBB,C,V5,S5), SimpleVerseKey(BBB,C,V6,S6),
                                  SimpleVerseKey(BBB,C,V7,S7), SimpleVerseKey(BBB,C,V8,S8), SimpleVerseKey(BBB,C,V9,S9)]
            self.keyType = '9V'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of SimpleVersesKey.parseReferenceString


    def parseOSISString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseOSISString( {!r} )".format( referenceString ) )

        match = re.search( OSIS_BCVS2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
            self.verseKeysList = [SimpleVerseKey(BBB,C,V1,S1), SimpleVerseKey(BBB,C,V2,S2)]
            self.keyType = '2V'
            return True
        match = re.search( OSIS_BCVS2C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            bk = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.verseKeysList = [SimpleVerseKey(BBB,C1,V1,S1), SimpleVerseKey(BBB,C2,V2,S2)]
            self.keyType = '2CV'
            return True
        match = re.search( OSIS_BCVS3_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
            self.keyType = '3V'
            return True
        match = re.search( OSIS_BCVS3C_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)) )
            bk = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            C3, V3, S3 = match.group(8), match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "SimpleVersesKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.keyType = '3CV'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "SimpleVerseKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of SimpleVersesKey.parseOSISString
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
    def __init__( self, referenceString, OSIS=False, ignoreParseErrors=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "VerseRangeKey.__init__( {!r} )".format( referenceString ) )

        self.ignoreParseErrors = ignoreParseErrors
        #if BibleOrgSysGlobals.debugFlag:
        #    assert isinstance( referenceString, str ) and 7<=len(referenceString)<=16
        self.keyType = None
        parseFunction = self.parseOSISString if OSIS else self.parseReferenceString
        if not parseFunction( referenceString ):
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
        #if self.keyType=='V-V': return "{} {}:{}(?:!{})?-{}(?:!{})?".format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2 )
        #if self.keyType=='CV-CV': return "{} {}:{}(?:!{})?-{}:{}(?:!{})?".format( self.BBB, self.C, self.V1, self.S1, self.C2, self.V2, self.S2 )
        #if self.keyType=='C': return "{} {}".format( self.BBB, self.C )
        #print( self.keyType ); halt


    def getVerseKeyText( self ):
        resultStr = self.rangeStart.getVerseKeyText()
        BBB, C, V, S = self.rangeEnd.getBCVS()
        if BBB == self.rangeStart.getBBB():
            if C == self.rangeStart.getChapterNumberStr(): resultStr += '-{}{}{}'.format( V, '!' if S else '', S )
            else: resultStr += '–{}:{}{}{}'.format( C,V, '!' if S else '', S )
        else: resultStr += '–{}_{}:{}{}{}'.format( BBB, C,V, '!' if S else '', S )
        return resultStr
    # end of VerseRangeKey.getVerseKeyText


    def __iter__( self ):
        """
        Yields the verse keys one by one.
        """
        for verseKey in self.verseKeysList:
            yield verseKey
    # end of VerseRangeKey.__iter__


    def getIncludedVerses( self ):
        for iv in self.verseKeysList:
            yield iv
    # end of SimpleVerseKey.getIncludedVerses


    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseReferenceString( {!r} )".format( referenceString ) )

        match = re.search( BCVS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
            self.rangeStart = SimpleVerseKey( BBB, C, V1, S1 )
            self.rangeEnd = SimpleVerseKey( BBB, C, V2, S2 )
            self.verseKeysList = []
            self.verseKeysList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            V = V1
            if BibleOrgSysGlobals.debugFlag:
                print( "  Expanding range from {} to {}…".format( self.rangeStart.getShortText(), self.rangeEnd.getShortText() ) )
            assert int(V2)>int(V1) or S2!=S1
            while True:
                V = str( int(V) + 1 )
                if V==V2:
                    self.verseKeysList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
                    break
                self.verseKeysList.append( SimpleVerseKey( BBB, C, V ) )
            self.keyType = 'V-V'
            return True
        match = re.search( CHAPTER_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.rangeStart = SimpleVerseKey( BBB, C1, V1, S1 )
            self.rangeEnd = SimpleVerseKey( BBB, C2, V2, S2 )
            self.verseKeysList = []
            C, V, S = C1, V1, S1
            while True:
                if C==C2 and V==V2:
                    self.verseKeysList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
                    break
                self.verseKeysList.append( SimpleVerseKey( BBB, C, V ) )
                V = str( int(V) + 1 )
                if int(V)>222:
                    C,V = str( int(C) + 1 ), '1'
            self.keyType = 'CV-CV'
            return True
        match = re.search( CHAPTER_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
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


    def parseOSISString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseOSISString( {!r} )".format( referenceString ) )

        match = re.search( OSIS_BCVS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
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
        match = re.search( OSIS_CHAPTER_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk = match.group(1)
            C1, V1, S1 = match.group(2), match.group(3), match.group(4) if match.group(4) else ''
            C2, V2, S2 = match.group(5), match.group(6), match.group(7) if match.group(7) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.rangeStart = SimpleVerseKey( BBB, C1, V1, S1 )
            self.rangeEnd = SimpleVerseKey( BBB, C2, V2, S2 )
            self.verseKeysList = []
            C, V, S = C1, V1, S1
            while True:
                if C==C2 and V==V2:
                    self.verseKeysList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
                    break
                self.verseKeysList.append( SimpleVerseKey( BBB, C, V ) )
                V = str( int(V) + 1 )
                if int(V)>222:
                    C,V = str( int(C) + 1 ), '1'
            self.keyType = 'CV-CV'
            return True
        match = re.search( OSIS_CHAPTER_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk, C = match.group(1), match.group(2)
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "VerseRangeKey: Invalid {!r} book code".format( self.BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
            self.rangeStart = SimpleVerseKey( BBB, C, '1' )
            self.rangeEnd = SimpleVerseKey( BBB, C, '999' )
            self.keyType = 'C'
            return True
        # else:
        #print( "Didn't match" )
        if not self.ignoreParseErrors:
            logging.error( "VerseRangeKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of VerseRangeKey.parseOSISString
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
    def __init__( self, referenceString, OSIS=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "FlexibleVersesKey.__init__( {!r} )".format( referenceString ) )
        if BibleOrgSysGlobals.debugFlag:
            assert isinstance( referenceString, str ) and 5<=len(referenceString)<=20

        self.keyType, self.verseKeyObjectList = None, []
        parseFunction = self.parseOSISString if OSIS else self.parseReferenceString
        if not parseFunction( referenceString ):
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
            if resultText: resultText += ', '
            resultText += verseKeyObject.getShortText()
        return resultText
        #if self.keyType=='RESULT': return self.result.getShortText()
        #if self.keyType=='V-V,V': return '{} {}:{}(?:!{})?-{}(?:!{})?,{}(?:!{})?'.format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2, self.V3, self.S3 )
        #if self.keyType=='V,V-V': return '{} {}:{}(?:!{})?,{}(?:!{})?-{}(?:!{})?'.format( self.BBB, self.C, self.V1, self.S1, self.V2, self.S2, self.V3, self.S3 )
        #halt


    def getVerseKeyText( self ):
        if self.keyType=='V-V,V':
            vRange, vSingle = self.verseKeyObjectList[0], self.verseKeyObjectList[1]
            #print( "here", vRange, vSingle, "'{},{}'".format( vRange.getVerseKeyText(), vSingle.getVerseNumber() ) )
            S = vSingle.getVerseSuffix()
            return '{},{}{}{}'.format( vRange.getVerseKeyText(), vSingle.getVerseNumber(), '!' if S else '', S )
        resultText = ''
        for verseKeyObject in self.verseKeyObjectList:
            if resultText: resultText += ', '
            resultText += verseKeyObject.getVerseKeyText()
        return resultText


    def __iter__( self ):
        """
        Yields the next verses object.
        """
        for someVerseObject in self.verseKeyObjectList:
            yield someVerseObject
    # end of FlexibleVersesKey.__iter__


    def getIncludedVerses( self ):
        """
        """
        resultList = []
        for verseKeyObject in self.verseKeyObjectList:
            resultList.extend( verseKeyObject.getIncludedVerses() )
        return resultList
    # end of FlexibleVersesKey.getIncludedVerses


    def parseReferenceString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseReferenceString( {!r} )".format( referenceString ) )
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
            resultKey = VerseRangeKey( referenceString, ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            #self.keyType = 'RESULT'
            return True
        except TypeError: pass

        match = re.search( BCVS_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.keyType = 'V-V,V'
            return True
        match = re.search( BCVS_RANGE_PLUS2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            self.keyType = 'V-V,2V'
            return True
        match = re.search( BCVS_RANGE_PLUS3_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V5, S5 ) )
            self.keyType = 'V-V,3V'
            return True
        match = re.search( BCVS_RANGE_PLUS4_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V5, S5 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V6, S6 ) )
            self.keyType = 'V-V,3V'
            return True
        match = re.search( BCVS_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V2, '!' if S2 else '', S2, V3, '!' if S3 else '', S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V,V-V'
            return True
        match = re.search( BCVS_PLUS_RANGES2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4) or S5!=S4
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V2, '!' if S2 else '', S2, V3, '!' if S3 else '', S3 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V4, '!' if S4 else '', S4, V5, '!' if S5 else '', S5 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.keyType = 'V,V-V,V-V'
            return True
        match = re.search( BCVS2_PLUS_RANGES2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5) or S6!=S5
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V5, '!' if S5 else '', S5, V6, '!' if S6 else '', S6 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.keyType = 'V,V,V-V,V-V'
            return True
        match = re.search( BCVS_RANGE_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4) or S5!=S4
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V4, '!' if S4 else '', S4, V5, '!' if S5 else '', S5 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V-V,V,V-V'
            return True
        match = re.search( BCVS_RANGE_PLUS2_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5) or S6!=S5
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V5, '!' if S5 else '', S5, V6, '!' if S6 else '', S6 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V-V,2V,V-V'
            return True
        match = re.search( BCVS2_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V2,V-V'
            return True
        match = re.search( BCVS3_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4) or S5!=S4
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V4, '!' if S4 else '', S4, V5, '!' if S5 else '', S5 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V3,V-V'
            return True
        match = re.search( BCVS4_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4) or S5!=S4
                assert int(V6)>int(V5) or S6!=S5
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V5, '!' if S5 else '', S5, V6, '!' if S6 else '', S6 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V4,V-V'
            return True
        match = re.search( BCVS_PLUS_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V2, '!' if S2 else '', S2, V3, '!' if S3 else '', S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            self.keyType = 'V,V-V,V'
            return True
        match = re.search( BCVS2_PLUS_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V2, S2 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V5, S5 ) )
            self.keyType = 'V,V,V-V,V'
            return True
        match = re.search( BCVS_RANGES2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.keyType = 'V-V,V-V'
            return True
        match = re.search( BCVS_RANGES2_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V5, S5 ) )
            self.keyType = 'V-V,V-V,V'
            return True
        match = re.search( BCVS_RANGES2_PLUS2_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5)+1 or S6!=S5
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V5, S5 ) )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V6, S6 ) )
            self.keyType = 'V-V,V-V,2V'
            return True

        match = re.search( BCVS_RANGES3_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5) or S6!=S5
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            resultKey3 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V5, '!' if S5 else '', S5, V6, '!' if S6 else '', S6 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.verseKeyObjectList.append( resultKey3 )
            self.keyType = 'V-Vx3'
            return True
        match = re.search( BCVS_RANGES4_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            BBB, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            V5, S5 = match.group(11), match.group(12) if match.group(12) else ''
            V6, S6 = match.group(13), match.group(14) if match.group(14) else ''
            V7, S7 = match.group(15), match.group(16) if match.group(16) else ''
            V8, S8 = match.group(17), match.group(18) if match.group(18) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
                assert int(V4)>int(V3) or S4!=S3
                assert int(V5)>int(V4)+1 or S5!=S4
                assert int(V6)>int(V5) or S6!=S5
                assert int(V7)>int(V6)+1 or S7!=S6
                assert int(V8)>int(V7) or S8!=S7
            resultKey1 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            resultKey2 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V3, '!' if S3 else '', S3, V4, '!' if S4 else '', S4 ), ignoreParseErrors=True )
            resultKey3 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V5, '!' if S5 else '', S5, V6, '!' if S6 else '', S6 ), ignoreParseErrors=True )
            resultKey4 = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V7, '!' if S7 else '', S7, V8, '!' if S8 else '', S8 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey1 )
            self.verseKeyObjectList.append( resultKey2 )
            self.verseKeyObjectList.append( resultKey3 )
            self.verseKeyObjectList.append( resultKey4 )
            self.keyType = 'V-Vx4'
            return True

        logging.error( "FlexibleVersesKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of FlexibleVersesKey.parseReferenceString


    def parseOSISString( self, referenceString ):
        """
        Parses a string, expecting something like "SA2_19:5b"

        Returns True or False on success
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseOSISString( {!r} )".format( referenceString ) )
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
            resultKey = VerseRangeKey( referenceString, ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            #self.keyType = 'RESULT'
            return True
        except TypeError: pass

        match = re.search( OSIS_BCVS_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1) or S2!=S1
                assert int(V3)>int(V2)+1 or S3!=S2
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V1, '!' if S1 else '', S1, V2, '!' if S2 else '', S2 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V3, S3 ) )
            self.keyType = 'V-V,V'
            return True
        match = re.search( OSIS_BCVS_PLUS_RANGE_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V2, '!' if S2 else '', S2, V3, '!' if S3 else '', S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.keyType = 'V,V-V'
            return True
        match = re.search( OSIS_BCVS_PLUS_RANGE_PLUS_RE, referenceString )
        if match:
            #print( "Matched", match.start(), match.end() )
            #print( repr(match.group(0)), repr(match.group(1)), repr(match.group(2)), repr(match.group(3)), repr(match.group(4)), repr(match.group(5)), repr(match.group(6)) )
            bk, C = match.group(1), match.group(2)
            V1, S1 = match.group(3), match.group(4) if match.group(4) else ''
            V2, S2 = match.group(5), match.group(6) if match.group(6) else ''
            V3, S3 = match.group(7), match.group(8) if match.group(8) else ''
            V4, S4 = match.group(9), match.group(10) if match.group(10) else ''
            if BBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
                logging.error( "FlexibleVersesKey: Invalid {!r} book code".format( BBB ) )
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
                assert int(V2)>int(V1)+1 or S2!=S1
                assert int(V3)>int(V2) or S3!=S2
                assert int(V4)>int(V3)+1 or S4!=S3
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V1, S1 ) )
            resultKey = VerseRangeKey( '{}_{}:{}{}{}-{}{}{}'.format( BBB, C, V2, '!' if S2 else '', S2, V3, '!' if S3 else '', S3 ), ignoreParseErrors=True )
            self.verseKeyObjectList.append( resultKey )
            self.verseKeyObjectList.append( SimpleVerseKey( BBB, C, V4, S4 ) )
            self.keyType = 'V,V-V,V'
            return True

        logging.error( "FlexibleVersesKey was unable to parse {!r}".format( referenceString ) )
        return False
    # end of FlexibleVersesKey.parseOSISString
# end of class FlexibleVersesKey



def demo() -> None:
    """
    Short program to demonstrate/test the above class(es).
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    badStrings = ( 'Gn_1:1', '2KI_3:17', 'MAL_1234:1', 'MAT_1:1234', 'MRK_3:6:!ab', 'LUK_2:2!1234', )

    goodVerseStrings = ( 'SA2_19:12', 'REV_11:12!b', 'EXO_17:9!5', 'PRO_31:2!101', )
    badVerseStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', '2SA_19:12', 'JNA_2:3b', 'REV_11:12!z', )
    if 1: # test SimpleVerseKey
        print( "\n\nTesting SimpleVerseKey…" )
        for somethingGood in ( ('GEN','1','1'), ('GEN','1','1','a'), ('GEN','1','1','123'), ):
            print( "  Testing SimpleVerseKey with good {!r}".format( somethingGood ) )
            vK = SimpleVerseKey( *somethingGood )
            print( '   ', vK, "({}) and".format(vK.keyType), vK.getOSISReference() )
            print( '   ',vK == SimpleVerseKey( 'GEN', '1', '1' ), "then", vK == SimpleVerseKey( 'EXO', '1', '1' ) )
        for somethingBad in ( ('GEN','1234','1'), ('GEN','1','1','ab'), ('GEN','1','1','123'), ):
            print( "  Testing SimpleVerseKey with bad {!r}".format( somethingBad ) )
            try: vK = SimpleVerseKey( *somethingBad )
            except TypeError: pass
            else:
                print( '   ', vK, "({}) and".format(vK.keyType), vK.getOSISReference() )
                print( '   ',vK == SimpleVerseKey( 'GEN', '1', '1' ), "then", vK == SimpleVerseKey( 'EXO', '1', '1' ) )
        for someGoodString in goodVerseStrings:
            print( "  Testing SimpleVerseKey with good {!r}".format( someGoodString ) )
            vK = SimpleVerseKey( someGoodString )
            print( '    ', vK )
            assert vK.getVerseKeyText() == someGoodString
        print( '  BAD STUFF…' )
        for someBadString in badVerseStrings:
            print( "  Testing SimpleVerseKey with bad {!r}".format( someBadString ) )
            try: print( '    ', repr(someBadString), SimpleVerseKey( someBadString ) )
            except TypeError: pass #print( '    TypeError' )

    goodVersesStrings = ( 'SA2_19:12,19', 'REV_11:2!b,6!a', )
    badVersesStrings = badStrings + ( 'GEN.1.1,3', 'EXO 2:2,4', 'LEV_3,9', 'NUM_1:1', '2SA_19:12,321', 'JNA_2:3b,6a', 'REV_11:12!a,!c', )
    if 1: # test SimpleVersesKey
        print( "\n\nTesting SimpleVersesKey…" )
        for someGoodString in goodVersesStrings:
            print( "  Testing SimpleVersesKey with good {!r}".format( someGoodString ) )
            vK = SimpleVersesKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            #assert vK.getVerseKeyText() == someGoodString
        print( '  BAD STUFF…' )
        for someBadString in badVersesStrings:
            print( "  Testing SimpleVersesKey with bad {!r}".format( someBadString ) )
            try: print( '  ', repr(someBadString), SimpleVersesKey( someBadString ) )
            except TypeError: pass # print( '    TypeError' )

    goodRangeStrings = ( 'SA2_19:12-19', 'REV_11:2!b-6!a', )
    badRangeStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', 'NUM_1:1', '2SA_19:12', 'JNA_2:3b', 'REV_11:12!z', )
    if 1: # test VerseRangeKey
        print( "\n\nTesting VerseRangeKey…" )
        for someGoodString in goodRangeStrings:
            print( "  Testing VerseRangeKey with good {!r}".format( someGoodString ) )
            vK = VerseRangeKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            #assert vK.getVerseKeyText() == someGoodString
        print( '  BAD STUFF…' )
        for someBadString in badRangeStrings:
            print( "  Testing VerseRangeKey with bad {!r}".format( someBadString ) )
            try: print( '  ', repr(someBadString), VerseRangeKey( someBadString ) )
            except TypeError: pass

    goodFlexibleStrings = goodVerseStrings + goodVersesStrings + goodRangeStrings \
                          + ( 'GEN_1:1,3-4', 'GEN_1:1-3,4', 'EXO_1:1!b,3-4', 'EXO_1:1-3!a,4!c', )
    badFlexibleStrings = badStrings + ( 'GEN.1.1', 'EXO 2:2', 'LEV 3', 'NUM_1234:1', '2SA_19:12', 'JNA_2:3b', 'REV_11:12!z', )
    if 1: # test FlexibleVersesKey
        print( "\n\nTesting FlexibleVersesKey…" )
        for someGoodString in goodFlexibleStrings:
            print( "  Testing FlexibleVersesKey with good {!r}".format( someGoodString ) )
            vK = FlexibleVersesKey( someGoodString )
            print( '  ', repr(someGoodString), vK )
            #assert vK.getVerseKeyText() == someGoodString
        print( '  BAD STUFF…' )
        for someBadString in badFlexibleStrings:
            print( "  Testing FlexibleVersesKey with bad {!r}".format( someBadString ) )
            try: print( '  ', repr(someBadString), FlexibleVersesKey( someBadString ) )
            except TypeError: pass
# end of demo

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of VerseReferences.py
