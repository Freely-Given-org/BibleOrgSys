#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleReferences.py
#
# Module for handling Bible references including ranges
#
# Copyright (C) 2010-2018 Robert Hunt
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
Module for creating and manipulating Bible references.

This module recognises and handles generic/international Bible references.
    The expected/allowed format is controlled by the Bible organisational system,
        which includes vernacular booknames, and particular punctuation systems (including allowedVerseSuffixes).
    So in English 'Gen 1:26' or 'Jud 5' or '1 Jhn 3:1a' may be acceptable Bible references.
    In other languages, the book abbreviations and punctuation will vary.

This module recognises and handles OSIS Bible references.
    They are of the form bookAbbreviation.chapterNumber.verseNumber
        e.g., Gen.1.1 or Exod.20.10 or 2Chr.7.6 or Jude.1.2
    Note that the book abbreviation is not a constant length
            and may also start with a digit
        and that the same separator is repeated.

However, the native Bible reference string format in this system is more tightly defined
    e.g., GEN_1:1 or EXO_20:10 or CH2_7:6 or JDE_1:2!b
We can see that
    1/ The Bible book code is always 3-characters, starting with a letter
        All letters are UPPERCASE
    2/ We use an underline character as the book / chapter separator
    3/ We use a colon as the chapter / verse separator
    4/ We treat all chapter and verse "number" fields as strings
    5/ Verse numbers can include a lowercase letter suffix a..d preceded by !
        representing very approximate portions of a verse
            a = first half of a verse
            b = second half of a verse
            c = final third of a verse
            d = final quarter of a verse
    6/ No spaces are ever allowed.
These are parsed in the VerseReferences module.

Internally, we represent it as a Bible reference tuple (BBB,C,V,S,) also called BCVS where
    BBB is the three-character UPPERCASE reference abbreviation
    C is the chapter number string (There are some examples of letters being used for chapter "numbers")
    V is the verse number string
    S is the suffix --  this can be:
        a single lowercase letter a-d (see above)
        W with a word number (first word is W1) or WxWy for an inclusive range (not including the surrounding spaces)
        L with a letter number (first letter is L1) or LxLy for an inclusive range.

OSIS defines reference ranges with hyphens
    e.g., Gen.1.1-Gen.1.2 or Gen.1.1-Gen.2.3 (inclusive)

Our ranges are slightly different (also inclusive)
    e.g., Gen_1:1-Gen_1:2 but Gen_1:1–Gen_2:3
    i.e., using a hyphen for a verse span but en-dash (–) for a span that crosses chapters or books.

OXES is different again using hyphens but tends to remove the second (redundant) book identifier
    e.g., Gen.1.1-1.2 (if I remember correctly)

Technical note: Our Bible reference parsers use state machines rather than regular expressions.
    Although this is longer and harder to debug, I believe it's able to give more informative error messages.
    Also, I think it's easier to make it more generic/international this way.
    If I'm wrong, please show me.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2018-12-12' # by RJH
SHORT_PROGRAM_NAME = "BibleReferences"
PROGRAM_NAME = "Bible References handler"
PROGRAM_VERSION = '0.35'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging

if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem


# This is a hack because it's language dependant :-(
ignoredSuffixes = (' (LXX)',) # A hack to cope with these suffixes in cross-references and footnotes :(



class BibleReferenceBase:
    """
    Base class which provides some common functions for the others.
    """

    def __init__( self, BOSObject, BibleObject ): # The BibleObject passed by the superclass may be None
        """
        Initialize the object with necessary sub-systems.
            A Bible Organisation system, e.g., BibleOrganisationalSystem( 'RSV' )
                gives various things including:
                    a book order (useful for determining ranges that cross books)
                    a punctuation system
                    book names and deduced abbreviations
            Optional Bible object is a loaded Bible (based on InternalBible).
                We can use this to guess book names.
        """
        assert BOSObject
        self._BibleOrganisationalSystem = BOSObject
        if BibleOrgSysGlobals.debugFlag:
            print( "BibleReferenceBase: org={}".format( BOSObject.getOrganisationalSystemName() ) )

        # Handle things differently if we don't know the punctuation system
        punctuationSystemName = BOSObject.getOrganisationalSystemValue( 'punctuationSystem' )
        #print( 'pSN', punctuationSystemName )
        if punctuationSystemName and punctuationSystemName!='None' and punctuationSystemName!='Unknown': # default (if we know the punctuation system)
            assert BibleObject is None
            self.punctuationDict = self._BibleOrganisationalSystem.getPunctuationDict()
            if BibleOrgSysGlobals.debugFlag: print( "BibleReferenceBase: punct={}".format( BOSObject.getPunctuationSystemName() ) )
        else: # else use a very generic punctuation system
            assert BibleObject is not None
            self.punctuationDict = { 'spaceAllowedAfterBCS': 'E',
                                    'booknameCase': 'ME',
                                    'booknameLength': '3',
                                    'punctuationAfterBookAbbreviation': '',
                                    'allowedVerseSuffixes': 'ab',
                                    'bookBridgeCharacter': '-–', 'chapterBridgeCharacter': '-–', 'verseBridgeCharacter': '-–',
                                    'bookSeparator': ';', 'bookChapterSeparator': ' ', 'chapterSeparator': ';', 'chapterVerseSeparator': ':.', 'verseSeparator': ',',
                                    'startQuoteLevel1': '“', 'startQuoteLevel2': '‘', 'startQuoteLevel3': '“', 'startQuoteLevel4': '',
                                    'endQuoteLevel1': '”', 'endQuoteLevel2': '’', 'endQuoteLevel3': '”', 'endQuoteLevel4': '',
                                    'sentenceCapitalisation': 'Y', 'properNounCapitalisation': 'Y',
                                    'statementTerminator': '.', 'questionTerminator': '?', 'exclamationTerminator': '!',
                                    'commaPauseCharacter': ',', }
        # Handle things differently if we don't know the vernacular book names
        booksNamesSystemName = BOSObject.getOrganisationalSystemValue( 'booksNamesSystem' )
        #print( 'bNSN', booksNamesSystemName )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            #assert BibleObject is not None
            self.getBookNameFunction = self._BibleOrganisationalSystem.getBookName
            getBookAbbreviationFunction = self._BibleOrganisationalSystem.getBookAbbreviation
            self.getBBBFromText = self._BibleOrganisationalSystem.getBBBFromText # This is the function that finds a book code from the vernacular name or abbreviation
            if BibleOrgSysGlobals.debugFlag: print( "BibleReferenceBase: bns={}".format( BOSObject.getBooksNamesSystemName() ) )
        else: # else use our local functions from our deduced book names
            assert BibleObject is not None
            self.getBookNameFunction = BibleObject.getAssumedBookName # from InternalBible (which gets it from InternalBibleBook)
            getBookAbbreviationFunction = None
            self.getBBBFromText = BibleObject.guessXRefBBB
    # end of BibleReferenceBase:__init__
# end of class BibleReferenceBase



class BibleSingleReference( BibleReferenceBase ):
    """
    Class for creating and manipulating single Bible reference objects (no range allowed).
        Use this class only if a Bible reference must be just a single Bible verse.

    Uses a state-machine (rather than regular expressions) because I think it can give better error and warning messages.
        Not fully tested for all exceptional cases.

    This class is not so generally useful. Use the BibleReferenceList class for most cases (beause it also handles lists and ranges).
        Only use this class if you really want to enforce that it's only a reference to a single verse.
    """

    def __init__( self, BOSObject, BibleObject=None ):
        """ Initialize the object with necessary sub-systems. """
        assert BOSObject
        BibleReferenceBase.__init__( self, BOSObject, BibleObject ) # Initialise the base class
        self.objectNameString = 'Bible single reference object'
        self.objectTypeString = 'BibleSingleReference'
        self.reference = ()
    # end of BibleSingleReference:__init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Single Reference object"
        if self.reference: result += ('\n' if result else '') + "  {}".format( str(self.reference) )
        return result
    # end of BibleSingleReference:__str__

    def parseReferenceString( self, referenceString ):
        """
        Returns a 6-tuple with True/False result, haveWarnings, BBB, C, V, S
        """
        assert referenceString
        haveWarnings, haveErrors = False, False
        strippedReferenceString = referenceString.strip()
        if strippedReferenceString != referenceString:
            logging.warning( _("Reference string {!r} contains surrounding space(s)").format( referenceString ) )
            haveWarnings = True
        adjustedReferenceString = strippedReferenceString
        for value in ignoredSuffixes:
            adjustedReferenceString = adjustedReferenceString.replace( value, '' )
        #statusList = {0:"gettingBookname", 1:"gettingBCSeparator", 2:"gettingChapter", 3:"gettingVerse", 4:"gotCV", 5:"done", 9:"finished"}
        status, bookNameOrAbbreviation, BBB, C, V, S, spaceCount = 0, '', None, '', '', '', 0
        for nn, char in enumerate(adjustedReferenceString):
            nnn = referenceString.find( char, nn ) # Best guess of where this char might be in the original reference string (which we will display to users in error messages)
            if nnn!=nn: # Well the character wasn't exactly where we expected it
                assert adjustedReferenceString != referenceString # but this can happen if we messed with the string
                #print( "nnn!=nn", nn, nnn, "'"+referenceString+"'", "'"+adjustedReferenceString+"'" )
            #if referenceString.startswith('Num 22'):
            #print( "  BSR status: {}:{} -- got {!r}".format(status, statusList[status],char), haveErrors, haveWarnings )
            if status == 0: # Getting bookname (with or without punctuation after book abbreviation)
                if char.isalnum(): # doesn't include spaces
                    if char.isdigit() and bookNameOrAbbreviation: # Could this be the chapter number?
                        BBB = self.getBBBFromText( bookNameOrAbbreviation )
                        if BBB is None: # Don't seem to have a valid bookname yet
                            bookNameOrAbbreviation += char
                            continue
                        # else it seems we have a valid bookname -- let's assume this might be the chapter number
                        logging.error( _("It seems that the bookname might be joined onto the chapter number at position {} ({}) in Bible reference {!r}") \
                                                        .format( nnn, referenceString[nnn], referenceString ) )
                        status = 2 # Start getting the chapter number immediately (no "continue" here)
                    else:
                        bookNameOrAbbreviation += char
                        continue
                elif bookNameOrAbbreviation and char == ' ': # Could be something like 1 Cor
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None: # Don't seem to have a valid bookname yet
                        bookNameOrAbbreviation += char
                    else: # we have a valid bookname
                        status = 2 # Start getting the chapter number
                    continue
                elif 'punctuationAfterBookAbbreviation' in self.punctuationDict and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    status = 1 # Default to getting BCS
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname at position {} in Bible reference {!r}").format( bookNameOrAbbreviation, nnn, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                status = 2 # Just accept this as the BCS and go get the chapter number
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given at position {} in {!r}") \
                                        .format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                                haveWarnings = True
                    continue
                elif char in self.punctuationDict['bookChapterSeparator'] or char=='_':
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName != bookNameOrAbbreviation: # they didn't enter the full bookname -- we really expect the punctuationAfterBookAbbreviation
                            if 'punctuationAfterBookAbbreviation' in self.punctuationDict and self.punctuationDict['punctuationAfterBookAbbreviation']:
                                logging.warning( _("Missing {!r} punctuationAfterBookAbbreviation when the book name abbreviation was given at position {} ({}) in {!r}") \
                                        .format( self.punctuationDict['punctuationAfterBookAbbreviation'], nnn, referenceString[nnn], referenceString ) )
                                haveWarnings = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2 # getting chapter number
                    continue
                else:
                    if ' ' in bookNameOrAbbreviation:
                        if bookNameOrAbbreviation.startswith('1 ') or bookNameOrAbbreviation.startswith('2 ') \
                        or bookNameOrAbbreviation.startswith('I ') or bookNameOrAbbreviation.startswith('II '):
                            logging.warning( "BibleSingleReference.parseReferenceString " + _("Unexpected space after book number when getting book name in Bible reference {!r}").format( referenceString ) )
                            haveWarnings = True
                            ixSP = bookNameOrAbbreviation.index( ' ' )
                            bookNameOrAbbreviation = bookNameOrAbbreviation[0] + bookNameOrAbbreviation[ixSP+1:] # Remove the space
                    if ' ' in bookNameOrAbbreviation:
                        logging.error( "BibleSingleReference.parseReferenceString " + _("Unable to deduce book name from {!r} in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else:
                        logging.error( _("Unexpected {!r} character when getting book name at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                        haveErrors = True
                    if len(bookNameOrAbbreviation)>4: break # Best to break here I think since we've been unsuccessful at finding a book name
                    continue
            if status == 1: # Getting book chapter separator
                if char in self.punctuationDict['bookChapterSeparator']:
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2
                    continue
                elif char.isdigit(): # Must have missed the BCS
                    logging.warning( _("Missing {!r} book/chapter separator when the book name abbreviation was given in {!r}").format(self.punctuationDict['bookChapterSeparator'],referenceString) )
                    haveWarnings = True
                    status = 2 # Fall through below
                else:
                    logging.error( _("Unexpected {!r} character in Bible reference {!r} when getting book/chapter separator").format( char, referenceString ) )
                    haveErrors = True
                    continue
            if status == 2: # Getting chapter number (or could be the verse number of a one chapter book)
                if char==' ' and not C:
                    spaceCount += 1
                elif char.isdigit():
                    if self.punctuationDict['spaceAllowedAfterBCS']=='Y' and spaceCount<1:
                        logging.warning( _("Missing space after bookname in Bible reference {!r}").format( referenceString ) )
                        haveWarnings = True
                    elif self.punctuationDict['spaceAllowedAfterBCS']=='N' or spaceCount>1:
                        logging.warning( _("Extra space(s) after bookname in Bible reference {!r}").format( referenceString ) )
                        haveWarnings = True
                    C += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5b
                    S = char
                elif C and char in self.punctuationDict['chapterVerseSeparator']:
                    status = 3 # Start getting the verse number
                else:
                    logging.error( _("Unexpected {!r} character when getting chapter number in {} Bible reference {!r}").format( char, BBB, referenceString ) )
                    haveErrors = True
                continue
            if status == 3: # Getting verse number
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter in {} Bible reference {!r}").format( BBB, referenceString ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5b
                    S = char
                else:
                    logging.error( _("BSR: Unexpected {!r} character when getting verse number in {} {} Bible reference {!r}").format( char, BBB, C, referenceString ) )
                    haveErrors = True
                    if V: status = 4
                    else: break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
        if status == 3: # Got a C but still getting the V hopefully
            if V: status = 4
        if len(S) > 1:
            logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}").format( S, BBB, referenceString ) )
            haveErrors = True
            S = S[0] # Just take the first one
        if BBB is not None:
            if status==2 and C and self._BibleOrganisationalSystem.isSingleChapterBook( BBB ): # Have a single chapter book and what we were given is presumably the verse number
                V = C
                C = '1'
                status = 4
            if status>=4 and not haveErrors:
                if self._BibleOrganisationalSystem.isValidBCVRef( (BBB, C, V, S), referenceString ):
                    status = 9
        self.reference = (BBB, C, V, S,)
        #print( "BSR final status: {}:{} -- got {!r}from {!r}\n".format(status,statusList[status],self.referenceList,referenceString) )
        return status==9 and not haveErrors, haveWarnings, BBB, C, V, S
    # end of BibleSingleReference:parseReferenceString
# end of class BibleSingleReference



class BibleSingleReferences( BibleReferenceBase ):
    """
    Class for creating and manipulating a list of multiple Bible reference objects (no ranges allowed).
        Use this class only if a Bible reference must be just a list of single Bible verses.

    Uses a state-machine (rather than regular expressions) because I think it can give better error and warning messages.
        Not fully tested for all exceptional cases.

    This class is not so generally useful. Use the BibleReferenceList class for most cases (beause it also handles ranges).
        Only use this class if you really want to enforce that it's only references to single verses.
    """

    def __init__( self, BOSObject, BibleObject=None ):
        """ Initialize the object with necessary sub-systems. """
        assert BOSObject
        BibleReferenceBase.__init__( self, BOSObject, BibleObject ) # Initialise the base class
        self.objectNameString = 'Bible single references object'
        self.objectTypeString = 'BibleSingleReferences'
        self.referenceList = []
    # end of BibleSingleReferences:__init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Single References Object"
        if self.referenceList: result += ('\n' if result else '') + "  {}".format( self.referenceList )
        return result
    # end ofBibleSingleReferences: __str__

    def parseReferenceString( self, referenceString ):
        """
        Returns a tuple with True/False result, haveWarnings, list of (BBB, C, V, S) tuples
        """

        def saveReference( BBB, C, V, S, refList ):
            """ Checks the reference info then saves it as a referenceTuple in the refList. """
            nonlocal haveErrors, haveWarnings
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}").format( S, BBB, referenceString ) )
                haveErrors = True
                S = S[0] # Just take the first one
            refTuple = ( BBB, C, V, S, )
            if refTuple in refList:
                logging.warning( _("Reference {} is repeated in Bible reference {!r}").format( refTuple, referenceString ) )
                haveWarnings = True
            if BBB is None or not self._BibleOrganisationalSystem.isValidBCVRef( refTuple, referenceString ):
                haveErrors = True
            refList.append( refTuple )
        # end of saveReference

        #print( "Processing {!r}".format( referenceString ) )
        assert referenceString
        haveWarnings, haveErrors = False, False
        strippedReferenceString = referenceString.strip()
        if strippedReferenceString != referenceString:
            logging.warning( _("Reference string {!r} contains surrounding space(s)").format( referenceString ) )
            haveWarnings = True
        adjustedReferenceString = strippedReferenceString
        for value in ignoredSuffixes:
            adjustedReferenceString = adjustedReferenceString.replace( value, '' )
        #statusList = {0:"gettingBookname", 1:"gettingBCSeparator", 2:"gettingChapter", 3:"gettingVerse", 4:"gettingNextBorC", 5:"done", 9:"finished"}
        status, bookNameOrAbbreviation, BBB, C, V, S, spaceCount, refList = 0, '', None, '', '', '', 0, []
        for nn, char in enumerate(adjustedReferenceString):
            nnn = referenceString.find( char, nn ) # Best guess of where this char might be in the original reference string (which we will display to users in error messages)
            if nnn!=nn: # Well the character wasn't exactly where we expected it
                assert adjustedReferenceString != referenceString # but this can happen if we messed with the string
                #print( "nnn!=nn", nn, nnn, "'"+referenceString+"'", "'"+adjustedReferenceString+"'" )
            #if referenceString.startswith('Num 22'):
            #print( "  BSRs status: {}:{} -- got {!r}".format(status, statusList[status],char), haveErrors, haveWarnings )
            if status == 0: # Getting bookname (with or without punctuation after book abbreviation)
                if char.isalnum(): # doesn't include spaces
                    if char.isdigit() and bookNameOrAbbreviation: # Could this be the chapter number?
                        BBB = self.getBBBFromText( bookNameOrAbbreviation )
                        if BBB is None: # Don't seem to have a valid bookname yet
                            bookNameOrAbbreviation += char
                            continue
                        # else it seems we have a valid bookname -- let's assume this might be the chapter number
                        logging.error( _("It seems that the bookname might be joined onto the chapter number at position {} in Bible reference {!r}").format(nnn, referenceString) )
                        status = 2 # Start getting the chapter number immediately (no "continue" here)
                    else:
                        bookNameOrAbbreviation += char
                        continue
                elif bookNameOrAbbreviation and char == ' ': # Could be something like 1 Cor
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None: # Don't seem to have a valid bookname yet
                        bookNameOrAbbreviation += char
                    else: # we have a valid bookname
                        status = 2 # Start getting the chapter number
                    continue
                elif 'punctuationAfterBookAbbreviation' in self.punctuationDict and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    status = 1 # Default to getting BCS
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname at position {} in Bible reference {!r}").format( bookNameOrAbbreviation, nnn, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                status = 2 # Just accept this as the BCS and go get the chapter number
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given at position {} in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                                haveWarnings = True
                    continue
                elif char in self.punctuationDict['bookChapterSeparator'] or char=='_':
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName != bookNameOrAbbreviation: # they didn't enter the full bookname -- we really expect the punctuationAfterBookAbbreviation
                            if 'punctuationAfterBookAbbreviation' in self.punctuationDict and self.punctuationDict['punctuationAfterBookAbbreviation']:
                                logging.warning( _("Missing {!r} punctuationAfterBookAbbreviation when the book name abbreviation was given at position {} ({}) in {!r}") \
                                        .format( self.punctuationDict['punctuationAfterBookAbbreviation'], nnn, referenceString[nnn], referenceString ) )
                                haveWarnings = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2 # getting chapter number
                    continue
                else:
                    if ' ' in bookNameOrAbbreviation:
                        if bookNameOrAbbreviation.startswith('1 ') or bookNameOrAbbreviation.startswith('2 ') \
                        or bookNameOrAbbreviation.startswith('I ') or bookNameOrAbbreviation.startswith('II '):
                            logging.warning( "BibleSingleReferences.parseReferenceString " + _("Unexpected space after book number when getting book name in Bible reference {!r}").format( referenceString ) )
                            haveWarnings = True
                            ixSP = bookNameOrAbbreviation.index( ' ' )
                            bookNameOrAbbreviation = bookNameOrAbbreviation[0] + bookNameOrAbbreviation[ixSP+1:] # Remove the space
                    if ' ' in bookNameOrAbbreviation:
                        logging.error( "BibleSingleReferences.parseReferenceString " + _("Unable to deduce book name from {!r} in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else:
                        logging.error( _("Unexpected {!r} character when getting book name at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                        haveErrors = True
                    if len(bookNameOrAbbreviation)>4: break # Best to break here I think since we've been unsuccessful at finding a book name
                    continue
            if status == 1: # Getting book chapter separator
                if char in self.punctuationDict['bookChapterSeparator']:
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2
                    continue
                elif char.isdigit(): # Must have missed the BCS
                    logging.warning( _("Missing {!r} book/chapter separator when the book name abbreviation was given in {!r}").format(self.punctuationDict['bookChapterSeparator'],referenceString) )
                    haveWarnings = True
                    status = 2 # Fall through below
                else:
                    logging.error( _("Unexpected {!r} character in Bible reference {!r} when getting book/chapter separator").format( char, referenceString ) )
                    haveErrors = True
                    continue
            if status == 2: # Getting chapter number (or could be the verse number of a one chapter book)
                if char==' ' and not C:
                    spaceCount += 1
                elif char.isdigit():
                    if self.punctuationDict['spaceAllowedAfterBCS']=='Y' and spaceCount<1:
                        logging.warning( _("Missing space after bookname in Bible reference {!r}").format( referenceString ) )
                        haveWarnings = True
                    elif self.punctuationDict['spaceAllowedAfterBCS']=='N' or spaceCount>1:
                        logging.warning( _("Extra space(s) after bookname in Bible reference {!r}").format( referenceString ) )
                        haveWarnings = True
                    C += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5b
                    S = char
                elif C and char in self.punctuationDict['chapterVerseSeparator']:
                    status = 3 # Start getting the verse number
                else:
                    logging.error( _("Unexpected {!r} character when getting chapter number in {} Bible reference {!r}").format( char, BBB, referenceString ) )
                    haveErrors = True
                continue
            if status == 3: # Getting verse number
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter in {} Bible reference {!r}").format( BBB, referenceString ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5b
                    S = char
                elif V and char in self.punctuationDict['verseSeparator']:
                    saveReference( BBB, C, V, S, refList )
                    V, S = '', ''
                elif V and (char in self.punctuationDict['chapterSeparator'] or char in self.punctuationDict['bookSeparator']):
                    saveReference( BBB, C, V, S, refList )
                    V, S = '', ''
                    if self.punctuationDict['chapterSeparator'] == self.punctuationDict['bookSeparator']:
                        temp, spaceCount = '', 0
                        status = 4 # We don't know what to expect next
                    elif char in self.punctuationDict['chapterSeparator']:
                        C = ''
                        status = 2 # Get the next chapter number
                    elif char in self.punctuationDict['bookSeparator']:
                        bookNameOrAbbreviation, BBB, C = '', None, ''
                        status = 0 # Get the next book name abbreviation
                else:
                    logging.error( _("BSRs: Unexpected {!r} character when getting verse number in {} {} Bible reference {!r}").format( char, BBB, C, referenceString ) )
                    haveErrors = True
                    if V:
                        saveReference( BBB, C, V, S, refList )
                        V, S = '', ''
                    break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
            if status == 4: # Getting the next chapter number or book name (not sure which)
                if char == ' ' and not temp:
                    if spaceCount:
                        logging.warning( _("Extra space(s) after chapter or book separator in {} Bible reference {!r}").format( BBB, referenceString ) )
                        haveWarnings = True
                    spaceCount += 1
                elif char.isalnum():
                    temp += char
                elif 'punctuationAfterBookAbbreviation' in self.punctuationDict and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    bookNameOrAbbreviation = temp
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    C, status = '', 1 # Default to getting BCS
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                status = 2 # Just accept this as the BCS and go get the chapter number
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],referenceString) )
                                haveWarnings = True
                else:
                    #print( "Got {!r}".format( temp ) )
                    if char in self.punctuationDict['chapterVerseSeparator'] and temp and temp.isdigit(): # Assume it's a follow on chapter number
                        C = temp
                        status = 3 # Now get the verse number
                    elif char in self.punctuationDict['bookChapterSeparator']:
                        bookNameOrAbbreviation = temp
                        BBB = self.getBBBFromText( bookNameOrAbbreviation )
                        if BBB is None:
                            logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                            haveErrors = True
                        C, V, S = '', '', ''
                        spaceCount = 1 if char==' ' else 0
                        status = 2 # Start getting the chapter number
                    else:
                        logging.error( _("Unexpected {!r} character in Bible reference {!r} when getting book name").format( char, referenceString ) )
                        haveErrors = True
                continue
        if status==3: # Got a C but still getting the V hopefully
            if V: status = 4
        if BBB is not None:
            if status==2 and C and self._BibleOrganisationalSystem.isSingleChapterBook( BBB ): # Have a single chapter book and what we were given is presumably the verse number
                V = C
                C = '1'
                status = 4
            if status>=4 and not haveErrors:
                saveReference( BBB, C, V, S, refList )
                status = 9
        self.referenceList = refList
        #print( "BSRs final status: {}:{} -- got {!r}from {!r}\n".format(status,statusList[status],self.referenceList,referenceString) )
        return status==9 and not haveErrors, haveWarnings, self.referenceList
    # end of BibleSingleReferences:parseReferenceString
# end of class BibleSingleReferences



class BibleReferenceList( BibleReferenceBase ):
    """
    Class for creating and manipulating a list of multiple Bible reference objects including optional ranges.
        Use this class unless a Bible reference must be just a single Bible verse or a list of single verses.

    Uses a state-machine (rather than regular expressions) because I think it can give better error and warning messages.
        Not fully tested yet for all exceptional cases.

    __init__ creates the object
    __str__ gives a brief prose description of the object
    makeReferenceString makes a reference string out of a tuple
    parseReferenceString makes a tuple out of a reference string
    parseOSISReferenceString makes a tuple out of an OSIS reference string
    getReferenceList returns our internal reference list of tuples, optionally expanded across ranges
    getOSISRefList converts our internal reference list of tuples to an OSIS reference string
    parseToOSIS attempts to convert a vernacular reference string to an OSIS reference string
    containsReferenceTuple sees if the reference tuple is in our internal list
    containsReference see if the BBB,C,V,S reference is in our internal list
    """

    def __init__( self, BOSObject, BibleObject=None ):
        """ Initialize the object with necessary sub-systems.
                A Bible Organisation system, e.g., BibleOrganisationalSystem( 'RSV' )
                    gives various things including:
                        a book order (useful for determining ranges that cross books)
                        a punctuation system
                        book names and deduced abbreviations
                Optional Bible object is a loaded Bible (based on InternalBible).
                    We can use this to guess book names.
        """
        assert BOSObject
        BibleReferenceBase.__init__( self, BOSObject, BibleObject ) # Initialise the base class
        self.objectNameString = 'Bible reference list object'
        self.objectTypeString = 'BibleReferenceList'
        self.referenceList = []
    # end of BibleReferenceList.__init__

    def __str__( self ):
        """
        This method returns- the string representation of a Bible Range References object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Range References object"
        if self.referenceList: result += ('\n' if result else '') + "  {}".format( self.referenceList )
        return result
    # end of BibleReferenceList.__str__

    def makeReferenceString( self, refTuple, location=None ):
        """
        Makes a string out of a reference tuple
        """
        assert refTuple
        lenRef = len( refTuple )
        if lenRef == 2: (BBB, C), V, S = refTuple, '', ''
        elif lenRef == 3: (BBB, C, V), S = refTuple, ''
        elif lenRef == 4: BBB, C, V, S = refTuple
        else: logging.error( _("Unrecognized {} parameter to makeReferenceString").format( refTuple ) ); return None

        BnC = self.punctuationDict['booknameCase'] if isinstance(self.punctuationDict['booknameCase'],str) else self.punctuationDict['booknameCase'][0]
        BCS = self.punctuationDict['bookChapterSeparator'] if isinstance(self.punctuationDict['bookChapterSeparator'],str) else self.punctuationDict['bookChapterSeparator'][0]
        CVS = self.punctuationDict['chapterVerseSeparator'] if isinstance(self.punctuationDict['chapterVerseSeparator'],str) else self.punctuationDict['chapterVerseSeparator'][0]

        if BBB[0].isdigit(): # Have a book name like 1SA
            assert "Should never happen I think" == BBB
            BBBstr = BBB[0] + ( BBB[1:] if BnC=='U' else BBB[1:].lower() if BnC=='L' else BBB[1:].capitalize() )
        else:
            BBBstr = BBB if BnC=='U' else BBB.lower() if BnC=='L' else BBB.capitalize()
        if self._BibleOrganisationalSystem.isSingleChapterBook( BBB ):
            #print( "makeReferenceString-iSCB", refTuple, location )
            if C!='1': logging.error( _("makeReferenceString: Expected chapter number to be 1 (not {!r}) for this {} single chapter book (from {} at {})").format( C, BBB, refTuple, location ) )
            resultString = "{}{}{}{}".format( BBBstr, BCS, ' ' if self.punctuationDict['spaceAllowedAfterBCS']=='Y' else '', V )
        else: # it's a book with multiple chapters
            resultString = "{}{}{}{}{}{}".format( BBBstr, BCS, ' ' if self.punctuationDict['spaceAllowedAfterBCS']=='Y' else '', C, CVS, V )
        return resultString
    # end of BibleReferenceList.makeReferenceString

    def parseReferenceString( self, referenceString, location=None ):
        """
        A complex state machine that
        returns a tuple with True/False result, haveWarnings, list of (BBB, C, V, S) tuples.
            A range is expressed as a tuple containing a pair of (BBB, C, V, S) tuples.

        All parsed references are checked for validity against the versification system.
        The optional location is a string that helps in error/warning messages.

        We could rewrite this using RegularExpressions, but would it be able to give such precise formatting error messages?
        """

        def saveReference( BBB, C, V, S, refList ):
            """ Checks the reference info then saves it as a referenceTuple in the refList. """
            nonlocal haveErrors, haveWarnings, totalVerseList
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}").format( S, BBB, referenceString ) )
                haveErrors = True
                S = S[0] # Just take the first one
            refTuple = ( BBB, C, V, S, )
            if refTuple in refList:
                logging.warning( _("Reference {} is repeated in Bible reference {!r}").format( refTuple, referenceString ) )
                haveWarnings = True
            if BBB is None or not self._BibleOrganisationalSystem.isValidBCVRef( refTuple, referenceString ):
                haveErrors = True
            refList.append( refTuple )
            totalVerseList.append( refTuple )
        # end of saveReference


        def saveStartReference( BBB, C, V, S ):
            """ Checks the reference info then saves it as a referenceTuple. """
            nonlocal haveErrors, haveWarnings, startReferenceTuple
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}").format( S, BBB, referenceString ) )
                haveErrors = True
                S = S[0] # Just take the first one
            startReferenceTuple = ( BBB, C, V, S, )
            if BBB is None or not self._BibleOrganisationalSystem.isValidBCVRef( startReferenceTuple, referenceString ):
                haveErrors = True
        # end of saveStartReference


        def saveReferenceRange( startTuple, BBB, C, V, S, refList ):
            """
            Checks the reference info then saves it as a referenceTuple in the refList.
            """
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "BibleReferences.saveReferenceRange:", "startTuple =", startTuple, "BBB =", BBB, "C =", C, "V =", V, "S = ", S, "refList =", refList )
            if V and not S and V[-1] in ('a','b','c',): # Remove the suffix
                S = V[-1]; V = V[:-1]
            if V=='3O': V = '30' # Fix a bug in byr-w.usfm
            if not BBB:
                logging.error( _("saveReferenceRange: Missing BBB parameter from {} Bible reference {!r}").format( BBB, referenceString ) )
            if not C:
                logging.error( _("saveReferenceRange: Missing C parameter from {} Bible reference {!r}").format( BBB, referenceString ) )
            elif C!='-1' and not C.isdigit():
                logging.error( _("saveReferenceRange: Non-digit {} C parameter from {} Bible reference {!r}").format( repr(C), BBB, referenceString ) )
            if not V:
                logging.error( _("saveReferenceRange: Missing V parameter from {} Bible reference {!r}").format( BBB, referenceString ) )
            elif not V.isdigit():
                logging.error( _("saveReferenceRange: Non-digit {} V parameter from {} Bible reference {!r}").format( repr(V), BBB, referenceString ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                assert BBB is None or len(BBB) == 3
                assert not C or C.isdigit() # Should be no suffix on C (although it can be blank if the reference is for a whole book)
                assert not V or V.isdigit() # Should be no suffix on V (although it can be blank if the reference is for a whole chapter)
                assert not S or len(S)==1 and S.isalpha() # Suffix should be only one lower-case letter if anything

            nonlocal haveErrors, haveWarnings, totalVerseList
            if len(S) > 1:
                logging.error( _("saveReferenceRange: Unexpected long {!r} suffix in {} Bible reference {!r}").format( S, BBB, referenceString ) )
                haveErrors = True
                S = S[0] # Just take the first one
            finishTuple = ( BBB, C, V, S, )
            if BBB is None or not self._BibleOrganisationalSystem.isValidBCVRef( finishTuple, referenceString ): # No error messages here because it will be caught at expandCVRange below
                haveErrors = True # Just set this flag
            rangeTuple = (startTuple, finishTuple,)
            verseList = self._BibleOrganisationalSystem.expandCVRange( startTuple, finishTuple, referenceString, self._BibleOrganisationalSystem )
            if verseList is not None: totalVerseList.extend( verseList )
            if rangeTuple in refList:
                logging.warning( _("saveReferenceRange: Reference range {} is repeated in Bible reference {!r}").format( rangeTuple, referenceString ) )
                haveWarnings = True
            refList.append( rangeTuple )
        # end of saveReferenceRange


        if location is None: location = '(unknown)'
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleReferences.parseReferenceString {!r} from {}".format( referenceString, location ) )
        assert referenceString and isinstance( referenceString, str )
        assert location and isinstance( location, str )
        haveWarnings, haveErrors, totalVerseList = False, False, []
        strippedReferenceString = referenceString.strip()
        if strippedReferenceString != referenceString:
            logging.warning( _("Reference string {!r} contains surrounding space(s)").format( referenceString ) )
            haveWarnings = True
        adjustedReferenceString = strippedReferenceString
        for value in ignoredSuffixes:
            adjustedReferenceString = adjustedReferenceString.replace( value, '' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            statusList = {0:"gettingBookname", 1:"gettingBCSeparator", 2:"gettingChapter", 3:"gettingVerse", 4:"gettingNextBorC", 5:"gettingBorCorVRange", 6:"gettingBRange", 7:"gettingCRange", 8:"gettingVRange", 9:"finished"}
        status, bookNameOrAbbreviation, BBB, C, V, S, spaceCount, startReferenceTuple, self.referenceList = 0, '', None, '', '', '', 0, (), []
        for nn, char in enumerate(adjustedReferenceString):
            nnn = referenceString.find( char, nn ) # Best guess of where this char might be in the original reference string (which we will display to users in error messages)
            if nnn!=nn: # Well the character wasn't exactly where we expected it
                assert adjustedReferenceString != referenceString # but this can happen if we messed with the string
                #print( "nnn!=nn", nn, nnn, "'"+referenceString+"'", "'"+adjustedReferenceString+"'" )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #if referenceString.startswith('Num 22'):
                print( "  BRL status: {}:{} -- got {!r}".format(status, statusList[status],char), haveErrors, haveWarnings, self.referenceList, BBB )
            if status == 0: # Getting bookname (with or without punctuation after book abbreviation)
                if char.isalnum(): # doesn't include spaces
                    if char.isdigit() and bookNameOrAbbreviation: # Could this be the chapter number?
                        BBB = self.getBBBFromText( bookNameOrAbbreviation )
                        if BBB is None: # Don't seem to have a valid bookname yet
                            bookNameOrAbbreviation += char
                            continue
                        # else it seems we have a valid bookname -- let's assume this might be the chapter number
                        logging.error( _("It seems that the bookname might be joined onto the chapter number at position {} in Bible reference {!r}").format(nnn, referenceString) )
                        status = 2 # Start getting the chapter number immediately (no "continue" here)
                    else:
                        bookNameOrAbbreviation += char
                        continue
                elif bookNameOrAbbreviation and char == ' ': # Could be something like 1 Cor
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None: # Don't seem to have a valid bookname yet
                        bookNameOrAbbreviation += char
                    else: # we have a valid bookname
                        status = 2 # Start getting the chapter number
                    continue
                elif 'punctuationAfterBookAbbreviation' in self.punctuationDict and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    status = 1 # Default to getting BCS
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname at position {} in Bible reference {!r}").format( bookNameOrAbbreviation, nnn, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                status = 2 # Just accept this as the BCS and go get the chapter number
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given at position {} in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                                haveWarnings = True
                    continue
                elif char in self.punctuationDict['bookChapterSeparator'] or char=='_':
                    if bookNameOrAbbreviation:
                        BBB = self.getBBBFromText( bookNameOrAbbreviation )
                        if BBB is None:
                            logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                            haveErrors = True
                        else: # we found an unambiguous bookname
                            shortBookName = self.getBookNameFunction( BBB )
                            if shortBookName != bookNameOrAbbreviation: # they didn't enter the full bookname -- we really expect the punctuationAfterBookAbbreviation
                                if 'punctuationAfterBookAbbreviation' in self.punctuationDict and self.punctuationDict['punctuationAfterBookAbbreviation']:
                                    logging.warning( _("Missing {!r} punctuationAfterBookAbbreviation when the book name abbreviation was given at position {} ({}) in {!r}") \
                                            .format( self.punctuationDict['punctuationAfterBookAbbreviation'], nnn, referenceString[nnn], referenceString ) )
                                    haveWarnings = True
                    else:
                        logging.error( _("Missing bookname in Bible reference {!r}").format( referenceString ) )
                        haveErrors = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2 # getting chapter number
                    continue
                else:
                    if ' ' in bookNameOrAbbreviation:
                        if bookNameOrAbbreviation.startswith('1 ') or bookNameOrAbbreviation.startswith('2 ') \
                        or bookNameOrAbbreviation.startswith('I ') or bookNameOrAbbreviation.startswith('II '):
                            logging.warning( "BibleReferenceList.parseReferenceString " + _("Unexpected space after book number when getting book name in Bible reference {!r}").format( referenceString ) )
                            haveWarnings = True
                            ixSP = bookNameOrAbbreviation.index( ' ' )
                            bookNameOrAbbreviation = bookNameOrAbbreviation[0] + bookNameOrAbbreviation[ixSP+1:] # Remove the space
                    if ' ' in bookNameOrAbbreviation:
                        logging.error( "BibleReferenceList.parseReferenceString " + _("Unable to deduce book name from {!r} in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    elif char == '.':
                        logging.warning( "BibleReferenceList.parseReferenceString " + _("Unexpected period when getting book name at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                        haveWarnings = True
                    else:
                        logging.error( "BibleReferenceList.parseReferenceString " + _("Unexpected {!r} character when getting book name at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                        haveErrors = True
                    if len(bookNameOrAbbreviation)>4: break # Best to break here I think since we've been unsuccessful at finding a book name
                    continue
            if status == 1: # Getting book chapter separator
                if char in self.punctuationDict['bookChapterSeparator'] or char=='_':
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname at position {} in Bible reference {!r}").format( bookNameOrAbbreviation, nnn, referenceString ) )
                        haveErrors = True
                    spaceCount = 1 if char==' ' else 0
                    status = 2
                    continue
                elif char.isdigit(): # Must have missed the BCS
                    logging.warning( _("Missing {!r} book/chapter separator when the book name abbreviation was given at position {} ({}) in {!r}") \
                                .format( self.punctuationDict['bookChapterSeparator'], nnn, referenceString[nnn], referenceString ) )
                    haveWarnings = True
                    status = 2 # Fall through below
                else:
                    logging.error( _("Unexpected {!r} character when getting book/chapter separator at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                    haveErrors = True
                    continue
            if status == 2: # Getting chapter number (or could be the verse number of a one chapter book)
                if char==' ' and not C:
                    spaceCount += 1
                elif char.isdigit():
                    if self.punctuationDict['spaceAllowedAfterBCS']=='Y' and spaceCount<1:
                        logging.warning( _("Missing space after bookname at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                        haveWarnings = True
                    elif (self.punctuationDict['spaceAllowedAfterBCS']=='N' and spaceCount>0) or spaceCount>1:
                        logging.warning( _("Extra space(s) after bookname at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                        haveWarnings = True
                    C += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5b
                    S = char
                elif C and char in self.punctuationDict['chapterVerseSeparator']:
                    status = 3 # Start getting the verse number
                elif C and self._BibleOrganisationalSystem.isSingleChapterBook( BBB ):
                    V = C
                    C = '1'
                    if char in self.punctuationDict['verseSeparator']:
                        saveReference( BBB, C, V, S, self.referenceList )
                        status = 3 # Get the next verse number
                    elif char in self.punctuationDict['bookSeparator']:
                        saveReference( BBB, C, V, S, self.referenceList )
                        BBB, C = None, ''
                        status = 0
                    elif char in self.punctuationDict['verseBridgeCharacter']:
                        saveStartReference( BBB, C, V, S )
                        status = 8 # Getting verse range
                    else:
                        logging.error( _("Unexpected {!r} character when processing single chapter book {} at position {} in Bible reference {!r}").format( char, BBB, nnn, referenceString ) )
                        haveErrors = True
                    V, S = '', ''
                elif C and char in self.punctuationDict['chapterBridgeCharacter']:
                    saveStartReference( BBB, C, V, S )
                    status, C, V, S = 7, '', '', '' # Getting chapter range
                else:
                    logging.error( _("Unexpected {!r} character when getting chapter number at position {} in {} Bible reference {!r}").format( char, nnn, BBB, referenceString ) )
                    haveErrors = True
                continue
            if status == 3: # Getting verse number
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter at position {} in {} Bible reference {!r}").format( nnn, BBB, referenceString ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5a
                    S = char
                elif V and char in self.punctuationDict['verseSeparator']:
                    saveReference( BBB, C, V, S, self.referenceList )
                    V, S = '', ''
                elif V and (char in self.punctuationDict['chapterSeparator'] or char in self.punctuationDict['bookSeparator']):
                    saveReference( BBB, C, V, S, self.referenceList )
                    V = ''
                    if self.punctuationDict['chapterSeparator'] == self.punctuationDict['bookSeparator']:
                        temp, spaceCount = '', 0
                        status = 4 # We don't know what to expect next
                    elif char in self.punctuationDict['chapterSeparator']:
                        C = ''
                        status = 7
                    elif char in self.punctuationDict['bookSeparator']:
                        bookNameOrAbbreviation, BBB, C = '', None, ''
                        status = 0
                elif char in self.punctuationDict['bookBridgeCharacter']:
                    saveStartReference( BBB, C, V, S )
                    V, S = '', ''
                    if char not in self.punctuationDict['chapterBridgeCharacter'] and char not in self.punctuationDict['verseBridgeCharacter']: # Must be a chapter bridge
                        status, BBB, C = 6, None, ''
                    else: # We don't know what kind of bridge this is
                        status, X = 5, ''
                elif char in self.punctuationDict['chapterBridgeCharacter']:
                    saveStartReference( BBB, C, V, S )
                    V, S = '', ''
                    if char not in self.punctuationDict['verseBridgeCharacter']: # Must be a chapter bridge
                        status, C = 7, ''
                    else: # We don't know what kind of bridge this is
                        status, X = 5, ''
                elif char in self.punctuationDict['verseBridgeCharacter']:
                    saveStartReference( BBB, C, V, S )
                    status, V, S = 8, '', ''
                else:
                    logging.error( _("BRL1: Unexpected {!r} character when getting verse number at position {} in {} {} Bible reference {!r}").format( char, nnn, BBB, C, referenceString ) )
                    haveErrors = True
                    if V:
                        saveReference( BBB, C, V, S, self.referenceList )
                        V, S = '', ''
                    break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
            if status == 4: # Getting the next chapter number or book name (not sure which)
                if char == ' ' and not temp:
                    if spaceCount:
                        logging.warning( _("Extra space(s) after chapter or book separator at position {} in {} Bible reference {!r}").format( nnn, BBB, referenceString ) )
                        haveWarnings = True
                    spaceCount += 1
                elif char.isalnum():
                    temp += char
                elif 'punctuationAfterBookAbbreviation' in self.punctuationDict and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    bookNameOrAbbreviation = temp
                    BBB = self.getBBBFromText( bookNameOrAbbreviation )
                    status, C = 1, '' # Default to getting BCS
                    if BBB is None:
                        logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( bookNameOrAbbreviation, referenceString ) )
                        haveErrors = True
                    else: # we found an unambiguous bookname
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                status = 2 # Just accept this as the BCS and go get the chapter number
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given at position {} in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                                haveWarnings = True
                else:
                    #print( "Char is {!r}, Temp is {!r}".format(char,temp) )
                    if char in self.punctuationDict['chapterVerseSeparator'] and temp and temp.isdigit(): # Assume it's a follow on chapter number
                        C = temp
                        status = 3 # Now get the verse number
                    elif char in self.punctuationDict['bookChapterSeparator']: # but this is often a space which also occurs in things like 1 Thess
                        BBB = self.getBBBFromText( temp )
                        if BBB is not None: # Must have found a bookname
                            bookNameOrAbbreviation = temp
                            C, V, S = '', '', ''
                            spaceCount = 1 if char==' ' else 0
                            status = 2 # Start getting the chapter number
                        else: # Not a valid bookname
                            if char != ' ':
                                logging.error( _("Invalid {!r} bookname at position {} in Bible reference {!r}").format( temp, nnn, referenceString ) )
                                haveErrors = True
                    else:
                        if bookNameOrAbbreviation: logging.error( _("Unable to deduce chapter or book name from {!r} in Bible reference {!r}").format( temp, referenceString ) )
                        else: logging.error( _("Unexpected {!r} character when getting chapter or book name at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                        haveErrors = True
                continue
            if status == 5: # Get either book or chapter or verse range
                if char==' ' and not X:
                    logging.warning( _("Extra space(s) after range bridge at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                    haveWarnings = True
                elif char==' ' and BBB and C and X: # Assume it's the space after a book name
                    #print( "here with", BBB, C, X )
                    BBB2 = self.getBBBFromText( X )
                    if BBB2 is None: # it seems that we couldn't discover the book name
                        logging.error( _("Unrecognized {!r} second bookname in Bible reference {!r}").format( X, referenceString ) )
                        BBB2 = "???"
                    BBB = BBB2
                    C = V = S = X = ''
                    status = 7 # Getting chapter range
                    #else: # assume it's a verse
                    #    V = X
                    #    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    #    C = V = S = X = ''
                    #    status = 0 # done
                elif char.isalnum():
                    X += char
                elif X and char in self.punctuationDict['punctuationAfterBookAbbreviation']:
                    BBB = self.getBBBFromText( X )
                    if BBB is not None: # Must have found a bookname
                        bookNameOrAbbreviation = X
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName == bookNameOrAbbreviation: # they entered the full bookname -- we didn't really expect this punctuation
                            if char in self.punctuationDict['bookChapterSeparator']: # ok, they are the same character
                                pass
                            else:
                                logging.warning( _("Didn't expect {!r} punctuationAfterBookAbbreviation when the full book name was given at position {} in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                                haveWarnings = True
                        C, V, S = '', '', ''
                        spaceCount = 1 if char==' ' else 0
                        status = 7 # Start getting the chapter range
                    else: # Not a valid bookname
                        if char != ' ':
                            logging.error( _("Invalid second {!r} bookname in Bible reference {!r}").format( X, referenceString ) )
                            haveErrors = True
                elif X and char in self.punctuationDict['bookChapterSeparator']: # but this is often a space which also occurs in things like 1 Thess
                    BBB = self.getBBBFromText( X )
                    if BBB is not None: # Must have found a bookname
                        bookNameOrAbbreviation = X
                        shortBookName = self.getBookNameFunction( BBB )
                        if shortBookName != bookNameOrAbbreviation and self.punctuationDict['punctuationAfterBookAbbreviation']: # they didn't enter the full bookname -- we expect some punctuation
                            logging.warning( _("Expected {!r} punctuationAfterBookAbbreviation when the abbreviated book name was given at position {} in {!r}").format(self.punctuationDict['punctuationAfterBookAbbreviation'],nnn,referenceString) )
                            haveWarnings = True
                        C, V, S = '', '', ''
                        spaceCount = 1 if char==' ' else 0
                        status = 7 # Start getting the chapter range
                    else: # Not a valid bookname
                        if char != ' ':
                            logging.error( _("Invalid {!r} bookname in Bible reference {!r}").format( X, referenceString ) )
                            haveErrors = True
                elif X and char in self.punctuationDict['chapterVerseSeparator']: # This must have been a chapter range
                    C = X
                    status, V, S = 8, '', ''
                elif X and char in self.punctuationDict['verseSeparator']: # This must have been a verse range
                    V = X
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    status, V, S = 3, '', '' # Go get a verse number
                elif X and (char in self.punctuationDict['chapterSeparator'] or char in self.punctuationDict['bookSeparator']): # This must have been a verse range
                    V = X
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    V, S = '', ''
                    if self.punctuationDict['chapterSeparator'] == self.punctuationDict['bookSeparator']:
                        temp, spaceCount = '', 0
                        status = 4 # We don't know what to expect next
                    elif char in self.punctuationDict['chapterSeparator']:
                        status,C = 1, ''
                    elif char in self.punctuationDict['bookSeparator']:
                        bookNameOrAbbreviation, BBB, C = '', None, ''
                        status = 0
                    else: assert "Should never happen" == 123
                else:
                    logging.error( _("Unexpected {!r} character when getting second chapter/verse number at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                    haveErrors = True
                continue
            if status == 7: # Get chapter range
                if char==' ' and not C:
                    if self.punctuationDict['spaceAllowedAfterBCS']=='N' or spaceCount>1:
                        logging.warning( _("Extra space(s) after bridge character at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                        haveWarnings = True
                    spaceCount += 1
                elif char.isdigit():
                    if self.punctuationDict['spaceAllowedAfterBCS']=='Y' and spaceCount<1:
                        logging.warning( _("Missing space after bridge character at position {} in Bible reference {!r}").format( nnn, referenceString ) )
                        haveWarnings = True
                    C += char
                elif C and char in self.punctuationDict['chapterVerseSeparator']:
                    status = 8 # Start getting the verse number
                elif C and char in self.punctuationDict['verseSeparator'] and BBB!='???' and self._BibleOrganisationalSystem.isSingleChapterBook(BBB):
                    V = C
                    C = '1'
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    status, V, S = 8, '', ''
                elif C and char in self.punctuationDict['bookSeparator'] and BBB!='???' and self._BibleOrganisationalSystem.isSingleChapterBook(BBB):
                    V = C
                    C = '1'
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    status, BBB, C, V, S = 0, None, '', '', ''
                elif C and (char in self.punctuationDict['chapterSeparator'] or char in self.punctuationDict['bookSeparator']):
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    C, V, S = '', '', ''
                    if self.punctuationDict['chapterSeparator'] == self.punctuationDict['bookSeparator']:
                        temp, spaceCount = '', 0
                        status = 4 # We don't know what to expect next
                    elif char in self.punctuationDict['chapterSeparator']:
                        status = 1
                    elif char in self.punctuationDict['bookSeparator']:
                        bookNameOrAbbreviation, BBB = '', None
                        status = 0
                else:
                    logging.error( _("Unexpected {!r} character when getting second chapter number at position {} in Bible reference {!r}").format( char, nnn, referenceString ) )
                    haveErrors = True
                continue
            if status == 8: # Get verse range
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter in range at position {} in {} Bible reference {!r}").format( nnn, BBB, referenceString ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif char in self.punctuationDict['allowedVerseSuffixes'] and not S: # Could be like verse 5a
                    S = char
                elif V and char in self.punctuationDict['verseSeparator']:
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    status, V, S = 3, '', '' # Go get a verse number
                elif V and (char in self.punctuationDict['chapterSeparator'] or char in self.punctuationDict['bookSeparator']):
                    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
                    V, S = '', ''
                    if self.punctuationDict['chapterSeparator'] == self.punctuationDict['bookSeparator']:
                        temp, spaceCount = '', 0
                        status = 4 # We don't know what to expect next
                    elif char in self.punctuationDict['chapterSeparator']:
                        status, C = 1, ''
                    elif char in self.punctuationDict['bookSeparator']:
                        bookNameOrAbbreviation, BBB, C = '', None, ''
                        status = 0
                else:
                    logging.error( _("BRL2: Unexpected {!r} character when getting verse number for range at position {} in {} {} Bible reference {!r}").format( char, nnn, BBB, C, referenceString ) )
                    haveErrors = True
                    if V:
                        saveReference( BBB, C, V, S, self.referenceList )
                        V, S = '', ''
                    break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
        if status==2 and C: # Getting chapter number
            if self._BibleOrganisationalSystem.isSingleChapterBook( BBB ): # Have a single chapter book and what we were given is presumably the verse number
                V = C
                C = '1'
                status = 4
            else: # it must be specifying an entire chapter (like Gen. 3)
                saveReference( BBB, C, V, S, self.referenceList )
                status = 9
        elif status==3: # Got a C but still getting the V hopefully
            if V: status = 4
        elif status==4: # Must have ended with a separator character
            logging.warning( _("Bible reference {!r} ended with a separator character").format( referenceString ) )
            haveWarnings = True
            status = 9
        elif status==5 and X: # Getting C or V range
            V = X
            saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
            status = 9
        #elif status==6 and C: # Getting book range
        #    saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
        #    status = 9
        elif status==7 and C: # Getting C range
            saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
            status = 9
        elif status==8 and V: # Getting V range
            saveReferenceRange( startReferenceTuple, BBB, C, V, S, self.referenceList )
            status = 9
        if status==4 and not haveErrors:
            saveReference( BBB, C, V, S, self.referenceList )
            status = 9

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleReferences.parseReferenceString BRL final status: {}:{} -- got {!r}from {!r}\n".format(status,statusList[status],self.referenceList,referenceString) )
            print( "BibleReferences.parseReferenceString here", len(totalVerseList), totalVerseList )

        singleVerseSet = set( totalVerseList )
        if len(singleVerseSet) < len(totalVerseList):
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "BibleReferences.parseReferenceString Final status: {} -- got {!r}from {!r}\n".format(statusList[status],self.referenceList,referenceString) )
                print( "BibleReferences.parseReferenceString totalVerseList is {}, singleVerseSet is {}".format(totalVerseList, singleVerseSet) )
            for entry in singleVerseSet:
                if totalVerseList.count(entry) > 1:
                    #print( entry )
                    logging.warning( _("Have duplicate or overlapping range at {} in Bible references {!r}").format( self.makeReferenceString(entry), referenceString ) )
            haveWarnings = True
        return status==9 and not haveErrors, haveWarnings, self.referenceList
    # end of BibleReferenceList.parseReferenceString


    def getFirstReference( self, referenceString, location=None ):
        """
        Just return the first reference, even if given a range.

        Basically just returns the first result (if any) from parseReferenceString.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "BibleReferences.getFirstReference( {}, {} )".format( repr(referenceString), location ) )
        hE, hW, refList = self.parseReferenceString( referenceString, location )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "gFR", hE, hW, refList )
        for something in refList: # Just return the first one
            if isinstance( something, tuple ):
                if len(something)==4: return something
                if len(something)==2 and isinstance( something[0], tuple ) and len(something[0])==4: return something[0]
    # end of BibleReferenceList.getFirstReference


    def parseOSISReferenceString( self, referenceString ):
        """
        Returns a tuple with True/False result, haveWarnings, list of (BBB, C, V, S) tuples.
            A range is expressed as a tuple containing a pair of (BBB, C, V, S) tuples.

        All parsed references are checked for validity against the versification system.

        Assumes that the book names and punctuation are OSIS standard.
        """
        # Set things up for OSIS system e.g., 1Cor.3.5-1Cor.3.9
        self.punctuationDict = {'booknameCase': 'M', 'booknameLength': 'M', 'spaceAllowedAfterBCS': 'N', 'punctuationAfterBookAbbreviation': '', 'chapterVerseSeparator': '.', 'bookChapterSeparator': '.', 'chapterSeparator': ';', 'bookBridgeCharacter': '-', 'chapterBridgeCharacter': '-', 'verseBridgeCharacter': '-', 'bookSeparator': ';', 'verseSeparator': ',', 'allowedVerseSuffixes': ''}
        OSISList = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes()
        #self.getBBBFromText = lambda s: BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation(s)
        self.getBBBFromText = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation

        # Now do the actual parsing using the standard routine
        sucessFlag, haveWarnings, resultList = self.parseReferenceString( referenceString )

        # Set things up again how they were
        self.punctuationDict = self._BibleOrganisationalSystem.getPunctuationDict()
        self.getBBBFromText = self._BibleOrganisationalSystem.getBBBFromText # This is the function that finds a book by name

        return sucessFlag, haveWarnings, resultList
    # end of BibleReferenceList.parseOSISReferenceString


    def getReferenceList( self, expanded=False ):
        """ Returns the internal list of Bible references.

            If expanded, fills out any ranges according to the specified versification system. """
        if expanded:
            expandedList = []
            for refTuple in self.referenceList:
                if len(refTuple) == 2: # it's a range
                    startRefTuple, endRefTuple = refTuple
                    expandedRange = self._BibleOrganisationalSystem.expandCVRange( startRefTuple, endRefTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                    if expandedRange is not None: expandedList.extend( expandedRange )
                else: expandedList.append( refTuple )
            return expandedList
        else:
            return self.referenceList
    # end of BibleReferenceList.getReferenceList


    def getOSISRefList( self ):
        """ Converts our internal reference list to OSIS format.
                OSIS defines reference ranges
                    e.g., Gen.1.1-Gen.1.2 or Gen.1.1-Gen.2.3 (inclusive).

            We simply ignore the single lower-case letter verse suffixes. """
        assert self.referenceList

        result = ''
        lastBk, lastC, lastV = '', '', ''
        for refOrRefRange in self.referenceList:
            if result: result += self.punctuationDict['bookSeparator'] + ' ' # The separator between multiple references
            if len(refOrRefRange) == 2: # it must be a range (start and end tuples)
                (BBB1, C1, V1, S1), (BBB2, C2, V2, S2) = refOrRefRange
                Bk1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB1 )
                Bk2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB2 )
                if V1 and V2: result += "{}.{}.{}-{}.{}.{}".format(Bk1,C1,V1,Bk2,C2,V2)
                elif not V1 and not V2: result += "{}.{}-{}.{}".format(Bk1,C1,Bk2,C2)
                elif V2: result += "{}.{}.1-{}.{}.{}".format(Bk1,C1,Bk2,C2,V2)
                else: halt
                lastBk, lastC, lastV = Bk2, C2, V2
            else: # It must be a single reference
                BBB, C, V, S = refOrRefRange
                Bk = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
                if V: result += "{}.{}.{}".format(Bk,C,V)
                else: result += "{}.{}".format(Bk,C)
                lastBk, lastC, lastV = Bk, C, V
        return result
    # end of BibleReferenceList.getOSISRefList

    def parseToOSIS( self, referenceString, location=None ):
        """ Just combines the two above routines.
                Parses a vernacular reference string and returns an OSIS reference string
                    or None if a valid reference cannot be parsed. """
        #print( "parseToOSIS:", "'"+referenceString+"'", "'"+location+"'" )
        successFlag, haveWarnings, refList = self.parseReferenceString( referenceString, location )
        if successFlag: return self.getOSISRefList()
        #logging.error( "You should already have an error above for {!r}".format( referenceString ) ) # temp
    # end of BibleReferenceList.parseToOSIS

    #def XXXUnusedXXXMaybeUntestedXXXcontainsReferenceTuple( self, refTuple ):
        #""" Returns True/False if the internal reference list contains the given reference tuple. """
        #assert refTuple and len(refTuple)==4
        #if not self._BibleOrganisationalSystem.isValidBCVRef( refTuple, "{} {}:{}{}".format(refTuple[0],refTuple[1],refTuple[2],refTuple[3]) ):
            #haveErrors = True

        ## See if we can find this reference in our internal list
        #for refTuple in self.referenceList:
            #if len(refTuple) == 2: # it's a range
                #startRefTuple, endRefTuple = refTuple
                #expandedList = self._BibleOrganisationalSystem.expandCVRange( startRefTuple, endRefTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                #if refTuple in expandedList: return True
            #elif refTuple == refTuple: return True
        #return False
    ## end of BibleReferenceList.containsReferenceTuple


    def containsReference( self, BBB, C, V, S=None ):
        """ Returns True/False if the internal reference list contains the given reference. """
        #if BibleOrgSysGlobals.verbosityLevel > 3: print( "BibleReferenceList.containsReference( {}, {}, {}, {} )".format( BBB, C, V, S ) )
        assert BBB and len(BBB)==3
        assert C
        if not C.isdigit(): print( "BibleReferenceList.containsReference( {}, {}, {}, {} ) expected C to be digits".format( BBB, C, V, S ) )
        assert V # May contain a list or range here

        # First find out what we were given
        if V.isdigit(): # it's simple
            myTuple = (BBB, C, V, S)
            if not self._BibleOrganisationalSystem.isValidBCVRef( myTuple, "{} {}:{}{}".format(BBB,C,V,S) ):
                haveErrors = True
            myList = [ myTuple, ]
        else: # Must have a list or range
            status, myList = 0, []
            myV = ''
            for char in V+self.punctuationDict['verseSeparator'][0]: # Adds something like a comma at the end to force collecting the final verse digit(s)
                if status == 0: # Getting a verse number
                    if char.isdigit(): myV += char
                    elif myV and char in self.punctuationDict['verseSeparator']: # Just got a verse number
                        myTuple = (BBB, C, myV, S)
                        if not self._BibleOrganisationalSystem.isValidBCVRef( myTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            haveErrors = True
                        myList.append( myTuple )
                        myV = ''
                    elif myV and char in self.punctuationDict['verseBridgeCharacter']: # Just got the start verse of a range
                        startTuple = (BBB, C, myV, S)
                        if not self._BibleOrganisationalSystem.isValidBCVRef( startTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            haveErrors = True
                        status, myV = 1, ''
                    logging.error( _("Invalid {!r} verse list/range given with {} {}:{}{}").format( V, BBB, C, V, S ) )
                elif status == 1: # Getting the end of a verse range
                    assert startTuple
                    if char.isdigit(): myV += char
                    elif myV and char in self.punctuationDict['verseSeparator']: # Just got the end of the range
                        endTuple = (BBB, C, myV, S)
                        if not self._BibleOrganisationalSystem.isValidBCVRef( endTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            haveErrors = True
                        verseList = self._BibleOrganisationalSystem.expandCVRange( startTuple, endTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                        if verseList is not None: myList.extend( verseList )
                        status, myV = 0, ''
            if status>0 or myV: logging.error( _("Invalid {!r} verse list/range given with {} {}:{}{}").format( V, BBB, C, V, S ) )
            #print( "myList", myList )

        # Now see if we can find any of these references in our internal list
        for myRefTuple in myList:
            for refTuple in self.referenceList:
                if len(refTuple) == 2: # it's a range
                    startRefTuple, endRefTuple = refTuple
                    expandedList = self._BibleOrganisationalSystem.expandCVRange( startRefTuple, endRefTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                    if not expandedList: return False
                    if myRefTuple in expandedList: return True
                    elif S is None:
                        for refTuple in expandedList:
                            if myRefTuple[0]==refTuple[0] and myRefTuple[1]==refTuple[1] and myRefTuple[2]==refTuple[2]: return True # Just compare BBB,C,V (not S)
                elif myRefTuple == refTuple: return True
                elif S is None and myRefTuple[0]==refTuple[0] and myRefTuple[1]==refTuple[1] and myRefTuple[2]==refTuple[2]: return True # Just compare BBB,C,V (not S)
        return False
    # end of BibleReferenceList.containsReference
# end of class BibleReferenceList



class BibleAnchorReference:
    """
    Class for creating and manipulating Bible anchor references (such as used inside footnotes or cross-references).
        Unlike the above classes, it's not based on the BibleReferenceBase class
            and it doesn't require any other objects to be passed to it. (They are mostly used for determining book names.)

    It assumes that we know the book, chapter, and verse being processed
        and that the book name is NOT part of the reference.
    It can handle single verses, a list of verses, or a range.
    It understands that single-chapter books might not include the chapter number (which is always 1).

    Uses a state-machine (rather than regular expressions) because I think it can give better error and warning messages.
        Not fully tested yet for all exceptional cases.

    __init__ creates the object
    __str__ gives a brief prose description of the object
    makeReferenceString makes a reference string out of a tuple
    parseAnchorString makes a tuple out of an anchor string
    getReferenceList returns our internal reference list of tuples, optionally expanded across ranges
    containsReferenceTuple sees if the reference tuple is in our internal list
    containsReference see if the BBB,C,V,S reference is in our internal list
    """

    def __init__( self, BBB, chapterString, verseString, suffixString=None ):
        """ Initialize the object with known information.
        """
        self.objectNameString = 'Bible anchor reference object'
        self.objectTypeString = 'BibleAnchorReference'
        assert BBB
        self.BBB = BBB
        assert chapterString
        self.chapterString = chapterString
        assert verseString
        self.verseString = verseString
        self.suffixString = '' if suffixString is None else suffixString
        self.homeTuple = (self.BBB,self.chapterString,self.verseString,self.suffixString,)

        assert BibleOrgSysGlobals.loadedBibleBooksCodes.isValidBBB( BBB )
        self.isSingleChapterBook = BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getSingleChapterBooksList()
        self.allowedVerseSuffixes = ( 'a', 'b', 'c', 'd', 'e', )
        self.allowedCVSeparators = ( ':', '.', )
        self.allowedVerseSeparators = ( ',', '-', )
        self.allowedBridgeCharacters = ( '-', )
        self.allowedChapterSeparators = ( ';', )

        self.referenceList = [] # Will be filled in when we get a string to parse
    # end of BibleAnchorReference:__init__

    def __str__( self ):
        """
        This method returns- the string representation of a Bible Anchor Reference object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        result += ('\n' if result else '') + "  BBB, chapter, verse = {} {!r} {!r}".format( self.BBB, self.chapterString, self.verseString )
        #result += ('\n' if result else '') + "  Anchor = {!r}".format( self.anchorString )
        if self.referenceList: result += ('\n' if result else '') + "  {}".format( self.referenceList )
        return result
    # end of BibleAnchorReference:__str__


    def parseAnchorString( self, anchorString, location=None ):
        """
        A complex state machine that
        returns a tuple with True/False result, haveWarnings, list of (BBB, C, V, S) tuples.
            A range is expressed as a tuple containing a pair of (BBB, C, V, S) tuples.

        All parsed references are checked for validity against the versification system.
        The optional location is a string that helps in error/warning messages.

        We could rewrite this using RegularExpressions, but would it be able to give such precise formatting error messages?
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "parseAnchorString: {} passed {!r}".format( self.homeTuple, anchorString ) )
        if location is None: location = '(unknown)'
        #print( "Processing {!r} from {}".format( anchorString, location ) )
        assert anchorString and isinstance( anchorString, str )
        assert location and isinstance( location, str )


        def saveReference( BBB, C, V, S, refList ):
            """ Checks the reference info then saves it as a referenceTuple in the refList. """
            #print( "saveReference:", BBB, C, V, S, refList )
            nonlocal haveErrors, haveWarnings, totalVerseList
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}{}").format( S, BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                haveErrors = True
                S = S[0] # Just take the first one
            refTuple = ( BBB, C, V, S, )
            if refTuple in refList:
                logging.warning( _("Reference {} is repeated in Bible reference {!r}{}").format( refTuple, anchorString, '' if location is None else " at {}".format(location) ) )
                haveWarnings = True
            if BBB is None: # or not self._BibleOrganisationalSystem.isValidBCVRef( refTuple, referenceString ):
                haveErrors = True
            refList.append( refTuple )
            totalVerseList.append( refTuple )
        # end of saveReference


        def saveStartReference( BBB, C, V, S ):
            """ Checks the reference info then saves it as a referenceTuple. """
            nonlocal haveErrors, haveWarnings, startReferenceTuple
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}{}").format( S, BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                haveErrors = True
                S = S[0] # Just take the first one
            startReferenceTuple = ( BBB, C, V, S, )
            if BBB is None: # or not self._BibleOrganisationalSystem.isValidBCVRef( startReferenceTuple, referenceString ):
                haveErrors = True
        # end of saveStartReference


        def saveReferenceRange( startTuple, BBB, C, V, S, refList ):
            """
            Checks the reference info then saves it as a referenceTuple in the refList.
            """
            if BibleOrgSysGlobals.debugFlag:
                print( "saveReferenceRange( {}, {} {}:{} {!r}, {} )".format( startTuple, BBB, C, V, S, refList ) )
                #print( startTuple, BBB, C, V, S, refList )
                assert len(BBB) == 3
                assert not C or C.isdigit() # Should be no suffix on C (although it can be blank if the reference is for a whole book)
                if V and not S and V[-1] in ('a','b','c',): # Remove the suffix
                    S = V[-1]; V = V[:-1]
                assert not V or V.isdigit() # Should be no suffix on V (although it can be blank if the reference is for a whole chapter)
                assert not S or len(S)==1 and S.isalpha() # Suffix should be only one lower-case letter if anything

            nonlocal haveErrors, haveWarnings, totalVerseList
            if len(S) > 1:
                logging.error( _("Unexpected long {!r} suffix in {} Bible reference {!r}{}").format( S, BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                haveErrors = True
                S = S[0] # Just take the first one
            finishTuple = ( BBB, C, V, S, )
            if BBB is None: # or not self._BibleOrganisationalSystem.isValidBCVRef( finishTuple, referenceString ): # No error messages here because it will be caught at expandCVRange below
                haveErrors = True # Just set this flag
            rangeTuple = (startTuple, finishTuple,)
            #verseList = self._BibleOrganisationalSystem.expandCVRange( startTuple, finishTuple, referenceString, self._BibleOrganisationalSystem )
            print( "How do we expand the verse list without a reference system???" ); verseList = None
            if verseList is not None: totalVerseList.extend( verseList )
            if rangeTuple in refList:
                logging.warning( _("Reference range {} is repeated in Bible reference {!r}{}").format( rangeTuple, anchorString, '' if location is None else " at {}".format(location) ) )
                haveWarnings = True
            refList.append( rangeTuple )
        # end of saveReferenceRange


        # Start of main code for parseAnchorString
        haveWarnings, haveErrors, totalVerseList = False, False, []
        strippedAnchorString = anchorString.strip()
        if strippedAnchorString != anchorString:
            logging.warning( _("Anchor string {!r}{} contains surrounding space(s)").format( anchorString, '' if location is None else " at {}".format(location) ) )
            haveWarnings = True
        adjustedAnchorString = strippedAnchorString
        for value in ignoredSuffixes:
            adjustedAnchorString = adjustedAnchorString.replace( value, '' )
        C = V = S = ''
        status, spaceCount, startReferenceTuple, self.referenceList = 0, 0, (), []
        #statusList = {0:"gettingChapter", 1:"gettingVerse", 2:"gettingNextC", 3:"gettingCorVRange", 4:"gettingCRange", 5:"gettingVRange", 6:"finished"}
        for nn, char in enumerate(adjustedAnchorString):
            nnn = anchorString.find( char, nn ) # Best guess of where this char might be in the original anchor string (which we will display to users in error messages)
            if nnn!=nn: # Well the character wasn't exactly where we expected it
                assert adjustedAnchorString != anchorString # but this can happen if we messed with the string
                #print( "nnn!=nn", nn, nnn, "'"+anchorString+"'", "'"+adjustedAnchorString+"'" )
            #if referenceString.startswith('Num 22'):
            #print( "  BAR status: {}:{} -- got {!r}".format(status, statusList[status],char), haveErrors, haveWarnings, self.referenceList )
            if status == 0: # Getting chapter number (or could be the verse number of a one chapter book)
                if char==' ' and not C:
                    spaceCount += 1
                elif char.isdigit():
                    C += char
                elif (C or V) and char in self.allowedVerseSuffixes and not S: # Could be like verse 5b
                    S = char
                elif C and char in self.allowedCVSeparators:
                    status = 1 # Start getting the verse number
                elif C and self.isSingleChapterBook:
                    V = C
                    C = '1'
                    if char in self.allowedVerseSeparators:
                        saveReference( self.BBB, C, V, S, self.referenceList )
                        status = 1 # Get the next verse number
                    elif char in self.allowedBridgeCharacters:
                        saveStartReference( self.BBB, C, V, S )
                        status = 5 # Getting verse range
                    else:
                        logging.error( _("Unexpected {!r} character when processing single chapter book {} at position {} in Bible reference {!r}{}").format( char, self.BBB, nnn, anchorString, '' if location is None else " at {}".format(location) ) )
                        haveErrors = True
                    V = S = ''
                elif C and char in self.allowedBridgeCharacters:
                    saveStartReference( self.BBB, C, V, S )
                    C = V = S = ''
                    status = 4 # Getting chapter range
                else:
                    logging.error( _("Unexpected {!r} character when getting chapter number at position {} in {} Bible reference {!r}{}").format( char, nnn, self.BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveErrors = True
                continue
            if status == 1: # Getting verse number
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter at position {} in {} Bible reference {!r}{}").format( nnn, self.BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif V and char in self.allowedVerseSuffixes and not S: # Could be like verse 5a
                    S = char
                elif V and char in self.allowedVerseSeparators:
                    saveReference( self.BBB, C, V, S, self.referenceList )
                    V, S = '', ''
                elif V and char in self.allowedChapterSeparators:
                    saveReference( self.BBB, C, V, S, self.referenceList )
                    V = ''
                    if char in self.allowedChapterSeparators:
                        C = ''
                        status = 4
                elif char in self.allowedBridgeCharacters:
                    saveStartReference( self.BBB, C, V, S )
                    V = S = ''
                    # We don't know what kind of bridge this is
                    status, X = 3, ''
                elif char in self.allowedBridgeCharacters:
                    saveStartReference( self.BBB, C, V, S )
                    V = S = ''
                    status = 5
                else:
                    logging.error( _("BRL1: Unexpected {!r} character when getting verse number at position {} in {} {} Bible reference {!r}{}").format( char, nnn, self.BBB, C, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveErrors = True
                    if V:
                        saveReference( self.BBB, C, V, S, self.referenceList )
                        V = S = ''
                    break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
            if status == 2: # Getting the next chapter numberXXXXXXXXXXXXXXXXXXXXX
                if char == ' ' and not temp:
                    if spaceCount:
                        logging.warning( _("Extra space(s) after chapter or book separator at position {} in {} Bible reference {!r}{}").format( nnn, self.BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                        haveWarnings = True
                    spaceCount += 1
                elif char.isalnum():
                    temp += char
                else:
                    #print( "Char is {!r}, Temp is {!r}".format(char,temp) )
                    if char in self.chapterVerseSeparators and temp and temp.isdigit(): # Assume it's a follow on chapter number
                        C = temp
                        status = 1 # Now get the verse number
                    else:
                        if bookNameOrAbbreviation: logging.error( _("Unable to deduce chapter or book name from {!r} in Bible reference {!r}{}").format( temp, anchorString, '' if location is None else " at {}".format(location) ) )
                        else: logging.error( _("Unexpected {!r} character when getting chapter or book name at position {} in Bible reference {!r}{}").format( char, nnn, anchorString, '' if location is None else " at {}".format(location) ) )
                        haveErrors = True
                continue
            if status == 3: # Get either chapter or verse range
                if char==' ' and not X:
                    logging.warning( _("Extra space(s) after range bridge at position {} in Bible reference {!r}{}").format( nnn, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveWarnings = True
                elif char==' ' and self.BBB and C and X:
                    #print( "here with", self.BBB, C, X )
                    V = X
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    C = V = S = X = ''
                    status = 0 # done
                elif char.isalnum():
                    X += char
                elif X and char in self.chapterVerseSeparators: # This must have been a chapter range
                    C = X
                    V = S = ''
                    status = 5
                elif X and char in self.allowedVerseSeparators: # This must have been a verse range
                    V = X
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    V = S = ''
                    status = 1 # Go get a verse number
                elif X and char in self.allowedChapterSeparators: # This must have been a verse range
                    V = X
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    V = S = ''
                    if char in self.allowedChapterSeparators:
                        status,C = 1, ''
                    else: assert "Should never happen" == 123
                else:
                    logging.error( _("Unexpected {!r} character when getting second chapter/verse number at position {} in Bible reference {!r}{}").format( char, nnn, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveErrors = True
                continue
            if status == 4: # Get chapter range
                if char==' ' and not C:
                    spaceCount += 1
                elif char.isdigit():
                    C += char
                elif C and char in self.allowedCVSeparators:
                    status = 5 # Start getting the verse number
                elif C and self.isSingleChapterBook and char in self.allowedVerseSeparators:
                    V = C
                    C = '1'
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    V = S = ''
                    status = 5
                elif C and char in self.allowedChapterSeparators:
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    C = V = S = ''
                    if char in self.allowedChapterSeparators:
                        status = 1
                else:
                    logging.error( _("Unexpected {!r} character when getting second chapter number at position {} in Bible reference {!r}{}").format( char, nnn, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveErrors = True
                continue
            if status == 5: # Get verse range
                if char == ' ' and not V:
                    logging.warning( _("Extra space(s) after chapter in range at position {} in {} Bible reference {!r}{}").format( nnn, self.BBB, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveWarnings = True
                elif char.isdigit():
                    V += char
                elif char in self.allowedVerseSuffixes and not S: # Could be like verse 5a
                    S = char
                elif V and char in self.allowedVerseSeparators:
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    status, V, S = 1, '', '' # Go get a verse number
                elif V and char in self.allowedChapterSeparators:
                    saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
                    V = S = ''
                    if char in self.allowedChapterSeparators:
                        status, C = 1, ''
                else:
                    logging.error( _("BRL2: Unexpected {!r} character when getting verse number for range at position {} in {} {} Bible reference {!r}{}").format( char, nnn, self.BBB, C, anchorString, '' if location is None else " at {}".format(location) ) )
                    haveErrors = True
                    if V:
                        saveReference( self.BBB, C, V, S, self.referenceList )
                        V = S = ''
                    break # Seems better to break on this one or else we get lots of errors (e.g., if a fr is left open in a footnote)
                continue
        if status==0 and C: # Getting chapter number
            if self.isSingleChapterBook: # Have a single chapter book and what we were given is presumably the verse number
                V = C
                C = '1'
                status = 2
            else: # it must be specifying an entire chapter (like Gen. 3)
                saveReference( self.BBB, C, V, S, self.referenceList )
                status = 6
        elif status==1: # Got a C but still getting the V hopefully
            if V: status = 2
        elif status==2: # Must have ended with a separator character
            logging.warning( _("Bible reference {!r}{} ended with a separator character").format( anchorString, '' if location is None else " at {}".format(location) ) )
            haveWarnings = True
            status = 6
        elif status==3 and X: # Getting C or V range
            V = X
            saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
            status = 6
        elif status==4 and C: # Getting C range
            saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
            status = 6
        elif status==5 and V: # Getting V range
            saveReferenceRange( startReferenceTuple, self.BBB, C, V, S, self.referenceList )
            status = 6
        if status==2 and not haveErrors:
            saveReference( self.BBB, C, V, S, self.referenceList )
            status = 6

        #print( "BRL final status: {}:{} -- got {!r}from {!r}\n".format(status,statusList[status],self.referenceList,anchorString) )
        #print( "here", len(totalVerseList), totalVerseList )

        singleVerseSet = set( totalVerseList )
        if len(singleVerseSet) < len(totalVerseList):
            #print( "Final status: {} -- got {!r}from {!r}\n".format(statusList[status],self.referenceList,anchorString) )
            #print( "totalVerseList is {}, singleVerseSet is {}".format(totalVerseList, singleVerseSet) )
            for entry in singleVerseSet:
                if totalVerseList.count(entry) > 1:
                    #print( entry )
                    logging.warning( _("Have duplicate or overlapping range at {} in Bible references {!r}{}").format( self.makeReferenceString(entry), anchorString, '' if location is None else " at {}".format(location) ) )
            haveWarnings = True
        return status==6 and not haveErrors, haveWarnings, self.referenceList
    # end of BibleAnchorReference:parseAnchorString


    def getReferenceList( self, expanded=False ):
        """ Returns the internal list of Bible references.

            If expanded, fills out any ranges according to the specified versification system. """
        if expanded:
            expandedList = []
            for refTuple in self.referenceList:
                if len(refTuple) == 2: # it's a range
                    startRefTuple, endRefTuple = refTuple
                    #expandedRange = self._BibleOrganisationalSystem.expandCVRange( startRefTuple, endRefTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                    print( "How do we expand the range without a reference system???" ); expandedRange = None
                    if expandedRange is not None: expandedList.extend( expandedRange )
                else: expandedList.append( refTuple )
            return expandedList
        else:
            return self.referenceList
    # end of BibleAnchorReference:getReferenceList


    #def xxxcontainsReference( self, BBB, C, V, S=None ):
        #""" Returns True/False if the internal reference list contains the given reference. """
        #assert BBB and len(BBB)==3
        #assert C and C.isdigit()
        #assert V # May contain a list or range here

        ## First find out what we were given
        #if V.isdigit(): # it's simple
            #myTuple = (BBB, C, V, S)
            #if not self._BibleOrganisationalSystem.isValidBCVRef( myTuple, "{} {}:{}{}".format(BBB,C,V,S) ):
                #haveErrors = True
            #myList = [ myTuple, ]
        #else: # Must have a list or range
            #status, myList = 0, []
            #myV = ''
            #for char in V+self.punctuationDict['verseSeparator'][0]: # Adds something like a comma at the end to force collecting the final verse digit(s)
                #if status == 0: # Getting a verse number
                    #if char.isdigit(): myV += char
                    #elif myV and char in self.punctuationDict['verseSeparator']: # Just got a verse number
                        #myTuple = (BBB, C, myV, S)
                        #if not self._BibleOrganisationalSystem.isValidBCVRef( myTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            #haveErrors = True
                        #myList.append( myTuple )
                        #myV = ''
                    #elif myV and char in self.allowedBridgeCharacters: # Just got the start verse of a range
                        #startTuple = (BBB, C, myV, S)
                        #if not self._BibleOrganisationalSystem.isValidBCVRef( startTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            #haveErrors = True
                        #status, myV = 1, ''
                    #logging.error( _("Invalid {!r} verse list/range given with {} {}:{}{}").format( V, BBB, C, V, S ) )
                #elif status == 1: # Getting the end of a verse range
                    #assert startTuple
                    #if char.isdigit(): myV += char
                    #elif myV and char in self.punctuationDict['verseSeparator']: # Just got the end of the range
                        #endTuple = (BBB, C, myV, S)
                        #if not self._BibleOrganisationalSystem.isValidBCVRef( endTuple, "{} {}:{}{}".format(BBB,C,myV,S) ):
                            #haveErrors = True
                        #verseList = self._BibleOrganisationalSystem.expandCVRange( startTuple, endTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                        #if verseList is not None: myList.extend( verseList )
                        #status, myV = 0, ''
            #if (status>0 or myV): logging.error( _("Invalid {!r} verse list/range given with {} {}:{}{}").format( V, BBB, C, V, S ) )
            ##print( "myList", myList )

        ## Now see if we can find any of these references in our internal list
        #for myRefTuple in myList:
            #for refTuple in self.referenceList:
                #if len(refTuple) == 2: # it's a range
                    #startRefTuple, endRefTuple = refTuple
                    #expandedList = self._BibleOrganisationalSystem.expandCVRange( startRefTuple, endRefTuple, bookOrderSystem=self._BibleOrganisationalSystem )
                    #if myRefTuple in expandedList: return True
                    #elif S is None:
                        #for refTuple in expandedList:
                            #if myRefTuple[0]==refTuple[0] and myRefTuple[1]==refTuple[1] and myRefTuple[2]==refTuple[2]: return True # Just compare BBB,C,V (not S)
                #elif myRefTuple == refTuple: return True
                #elif S is None and myRefTuple[0]==refTuple[0] and myRefTuple[1]==refTuple[1] and myRefTuple[2]==refTuple[2]: return True # Just compare BBB,C,V (not S)
        #return False
    ## end of BibleAnchorReference:containsReference


    def matchesAnchorString( self, anchorString, location=None ):
        """
        Compares the given footnote or cross-reference anchor string, and sees if it matches where we are in the text.

        Returns True or False.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "matchesAnchorString: {} passed {!r}".format( self.homeTuple, anchorString ) )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule:
            assert anchorString
        elif not anchorString: return False

        adjAnchorString = anchorString.strip()
        if adjAnchorString[-2:]==' a': adjAnchorString = adjAnchorString[:-2] # Remove any trailing subnote letter
        if adjAnchorString[-1]==':': adjAnchorString = adjAnchorString[:-1] # Remove any trailing punctuation
        assert adjAnchorString # Make sure there's still something left
        #print( "  Parsing {!r}".format( adjAnchorString ) )
        haveErrors, haveWarnings, resultList = self.parseAnchorString( adjAnchorString, location )
        #print( "  From {!r} got {} {} {}".format( anchorString, haveErrors, haveWarnings, resultList ) )
        result = self.getReferenceList( expanded=True )
        #print( "  From {!r} got {}".format( adjAnchorString, result ) )
        for rBBB, rC, rV, rS in result:
            assert rBBB == self.BBB
            if rC == self.chapterString:
                if rV == self.verseString: # the easy case -- an exact match
                    return True # We don't care about suffixes
                # We could have been passed a list or a range
                if '-' in self.verseString:
                    bits = self.verseString.split( '-' )
                    if rV in bits: return True
                if ',' in self.verseString:
                    bits = self.verseString.split( ',' )
                    if rV in bits: return True
        if 0: # for debugging
            print( "matchesAnchorString: {} passed {!r}".format( self.homeTuple, anchorString ) )
            print( "  Parsing {!r}".format( adjAnchorString ) )
            print( "  From {!r} got {} {} {}".format( anchorString, haveErrors, haveWarnings, resultList ) )
            print( "  From {!r} got {}".format( adjAnchorString, result ) )
        return False
    # end of BibleAnchorReference:matchesAnchorString
# end of class BibleAnchorReference



def demo() -> None:
    """
    Demonstrate parsing some Bible reference strings.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    ourBOS = BibleOrganisationalSystem( 'RSV' )
    printProcessingMessages = True

    if 1: # test BibleSingleReference
        print()
        BSR = BibleSingleReference( ourBOS )
        print( BSR ) # Just print a summary
        print( "\nSingle Reference (good)" )
        for ref in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b"):
            if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
            print( "  From {!r} BSR got {}".format(ref, BSR.parseReferenceString(ref)) )
        print( "\nSingle Reference (bad)" )
        for ref in ("Mat 0:3","Mat.7:0","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mt. 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
            if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
            print( "  From {!r} BSR got {}".format(ref, BSR.parseReferenceString(ref)) )

    if 1: # test BibleSingleReferences
        print()
        BSRs = BibleSingleReferences( ourBOS )
        print( BSRs ) # Just print a summary
        print( "\nSingle References (good)" )
        for ref in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b"):
            if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
            print( "  From {!r} BSRs got {}".format(ref, BSRs.parseReferenceString(ref)) )
        for ref in ("Mat. 7:3,7","Mat. 7:3; 4:7","Mat. 7:3,7; 4:7","Mat. 7:3,7; 4:7,9,11","Mat. 7:3; Heb. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2,9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4:4,7; Rev. 1:1; 1:1","Mrk. 7:3a,7b,8"):
            if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
            print( "  From {!r} BSRs got {}".format(ref, BSRs.parseReferenceString(ref)) )
        print( "\nSingle References (bad)" )
        for ref in ("Mat 0:3","Mat.7:0","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mt. 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
            if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
            print( "  From {!r} BSRs got {}".format(ref, BSRs.parseReferenceString(ref)) )

    if 1: # test BibleReferenceList
        print()
        BRL = BibleReferenceList( ourBOS )
        print( BRL ) # Just print a summary
        print( BRL.makeReferenceString(("MAT",'7','3')), BRL.makeReferenceString(("PHM",'1','3')), BRL.makeReferenceString(("CO1",'2','1','a')), BRL.makeReferenceString(("CO2",'7')) )
        if 1:
            print( "\n\nSingle References for Ranges (good)" )
            for ref in ("Mat 7:3","Mat.7:3","Mat. 7:3","Mt. 7:3","Mt.7:3","Jde 7","Jde. 7","Jde 1:7","Jde. 1:7","Job 8:4","Job. 8:4","Job8:4","Job  8:4","Lev. 8:4b", \
                        "Mat. 7:3,7","Mat. 7:3; 4:7","Mat. 7:3,7; 4:7","Mat. 7:3,7; 4:7,9,11","Mat. 7:3; Heb. 2:2; Rev. 1:1","Mat. 7:3,7; Heb 2:2,9; Rev. 1:1","Mat. 7:3,7; 8:17; Heb 2:2,9; 4:4,7; Rev. 1:1; 1:1","Mrk. 7:3a,7b,8"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got {}".format(ref, BRL.parseReferenceString(ref)) )
            print( "\nSingle References for Ranges (bad)" )
            for ref in ("Mat 0:3","Mat.7:0","Mat. 77:3","Mt. 7:93","M 7:3","Mit 7:3","Mt. 7:3","Mit. 7:3","Mat. 7:3ab","Mat, 7:3","Mat. 7:3xyz5"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BSRs got {}".format(ref, BRL.parseReferenceString(ref)) )
            print( "\n\nSingle Ranges (good)" )
            for ref in ("Mat 7:3-7","Mat.7:3-11","Mat. 7:13-8:2","Mt. 7:3,5-9","Mt.7:3-4,6-9","Jde 7-8","Jde. 1-3","Jde 1:7-8","Jud. 1:1-3,5,7-9","EXO.4:14,27c-30;  5:1,4,20; 6:13,20,23,25-27a; 7:1,2,6b-10a,10,12,19,20; 8:1,2,4,8,12,13,21;"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got {}".format(ref, BRL.parseReferenceString(ref)) )
                print( "OSIS result is {!r}".format( BRL.getOSISRefList() ) )
            print( "\nSingle Ranges (bad)" )
            for ref in ("EXO.4:14-12; NUM.3:12-1:5; JOS.4:5-5","Mt. 7:7;"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got {}".format(ref, BRL.parseReferenceString(ref)) )
            print( "\n\nNow some chapter Ranges (good)" )
            for ref in ("Dan. 5","Gen. 1-11","Act.4-7; Mat.5-7"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got {}".format(ref, BRL.parseReferenceString(ref)) )
                #print( "OSIS result is {!r}".format( BRL.getOSISRefList() ) )
            print( "\nNow some chapter Ranges (bad)" )
            for ref in ("Tit. 1:2; 1:2-7","Jer. 95","Exo. 23-99","1 Cor.9-7; 1Tim.5-7:2"):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got {}".format(ref, BRL.parseReferenceString(ref)) )
            for ref in ("Jhn. 3:16", "Rev. 2:1-3" ):
                if printProcessingMessages: print( "Processing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got OSIS {!r}".format(ref, BRL.parseToOSIS(ref)) )
        if 1:
            for ref in ("Mat. 27:15a-Mrk. 2:4b", "1Sml. 16:1-1Kngs. 2:11", "Eze. 27:12-13,22", ):
                if printProcessingMessages: print( "\nProcessing {!r} reference string…".format( ref ) )
                print( "  From {!r} BRL got OSIS {!r}".format(ref, BRL.parseToOSIS(ref)) )
                l1, l2 = BRL.getReferenceList(), BRL.getReferenceList( expanded=True )
                print( "List is: ", l1 )
                if l2!=l1: print( "Expanded:", l2 )
        if 1:
            originalRefs = ( \
                    #"Mt 3:2; 4:17;  9:35; 10:7; 11:12,13; 12:28; 13:11, 19, 44, 45, 47, 52; 18:23; 19:12; 20:1; 22:2; 24:14, 25:1, 14, 31; Mk 1:15; 4:11; 9:1; 10:15; 11:10; 15:43; Lk 1:32, 33; 3:1,2; 4:43; 8:1, 10; 9:1,2, 11, 27, 60, 62; 10:9, 11; 16:16; 17:19, 20, 22; 18:17, 29; 19:11, 15; 21:31; 22:18, 28-29; 23:43, 50-52; Jn 18:36; Ac 1:2,3,30; 7:18; 8:12; 13:22; 19:8; 20:25; 28:23, 31; Rm 15:12; Col 4:10,11; 2 Ti 4:1; Rev 11:17; 12:10", \
                    #"Mt 5:3, 10, 19, 20; 11:11; 13:24, 31, 33 41; 18:1, 3, 4; 19:14, 23, 24; 21:31, 43; 23:13; Mk 4:30; 10:14, 23, 24, 25; 12:34; Lk 6:20; 7:28; 12:32; 13:18,20, 18:16, 24,25; 19:14, 27; John 3:3, 3:5; Ac 1:6; 7:10; Ac 1 Co 6:9, 10; 15:24-25, 50; Gal 5:21; Eph 5:5; Col 1:12", \
                    #"Mt 7:21; 8:11; 11:12,13; 13:43; 16:19; 24:7; 25:34; 26:29; Mk 6:23; 9:47; 10:37; 13:8; 14:25; Lk 13:21, 24-25; 13:28, 29; 14:15; 17:21; 21:10; 22:16, 30; Ac 1:6; 7:10; 14:22; 15:16,50; Col 1:12; 1 Th 2:11,12; 2 Th 1:5; 4:18; Heb 12:28; Jas 2:5; 2 Pe 1:11; Rev 3:7; 16:10", \
                )
            fixedRefs = ( \
                    "Mt. 3:2; 4:17; 9:35; 10:7; 11:12,13; 12:28; 13:11,19,44,45,47,52; 18:23; 19:12; 20:1; 22:2; 24:14; 25:1,14,31; Mk. 1:15; 4:11; 9:1; 10:15; 11:10; 15:43; Lk. 1:32,33; 3:1,2; 4:43; 8:1,10; 9:1,2,11,27,60,62; 10:9,11; 16:16; 17:19,20,22; 18:17,29; 19:11,15; 21:31; 22:18,28-29; 23:43,50-52; Jn 18:36; Ac. 1:2,3,30; 7:18; 8:12; 13:22; 19:8; 20:25; 28:23,31; Rm. 15:12; Col. 4:10,11; 2 Ti. 4:1; Rev. 11:17; 12:10", \
                    "Mt. 5:3,10,19,20; 11:11; 13:24,31,33,41; 18:1,3,4; 19:14,23,24; 21:31,43; 23:13; Mk. 4:30; 10:14,23,24,25; 12:34; Lk 6:20; 7:28; 12:32; 13:18,20; 18:16,24,25; 19:14,27; John 3:3; 3:5; Ac. 1:6; 7:10; 1 Co. 6:9,10; 15:24-25,50; Gal. 5:21; Eph. 5:5; Col. 1:12", \
                    "Mt. 7:21; 8:11; 11:12,13; 13:43; 16:19; 24:7; 25:34; 26:29; Mk. 6:23; 9:47; 10:37; 13:8; 14:25; Lk 13:21,24-25; 13:28,29; 14:15; 17:21; 21:10; 22:16,30; Ac 1:6; 7:10; 14:22; 15:16,50; Col. 1:12; 1 Th. 2:11,12; 2 Th. 1:5; 4:18; Heb. 12:28; Jas. 2:5; 2 Pe. 1:11; Rev. 3:7; 16:10", \
                )
            for ref in fixedRefs:
                if printProcessingMessages: print( "\nProcessing {!r} reference string…".format( ref ) )
                oL = BRL.parseToOSIS( ref )
                print( "From {!r}\n  BRL got OSIS {!r}".format(ref, oL) )
                l1, l2 = BRL.getReferenceList(), BRL.getReferenceList( expanded=True )
                print( "List is: ", l1 )
                #if l2!=l1: print( "Expanded:", l2 )
                if oL is not None:
                    sucessFlag, hvWarnings, l3 = BRL.parseOSISReferenceString( oL )
                    print( "Now got: ", l3 )
        if 1:
            for ref in ( "1Cor.3.5-1Cor.3.9", ):
                if printProcessingMessages: print( "\nProcessing {!r} OSIS reference string…".format( ref ) )
                sucessFlag, hvWarnings, resultList = BRL.parseOSISReferenceString( ref )
                print( "From {!r}\n  BRL got {!r}".format(ref, resultList) )
                l1, l2 = BRL.getReferenceList(), BRL.getReferenceList( expanded=True )
                print( "List is: ", l1 )
                if l2!=l1: print( "Expanded:", l2 )

    if 1: # test BibleAnchorReference
        print()
        for ourBBB, ourC, ourV, ourAnchor in ( ('GEN','17','25', '17:25'), \
                                            ('EXO','12','17-18', '12:17'), ('LEV','12','17-18', '12:18'), ('NUM','12','17', '12:17-18'), ('DEU','12','18', '12:17-18'), \
                                            ('JOS','12','17,18', '12:17'), ('JDG','12','17,18', '12:18'), ('SA1','12','17', '12:17,18'), ('SA2','12','18', '12:17,18'), \
                                            ('CH1','12','17-19', '12:18'), ('CH2','12','18', '12:17-19'), ):
            BAR = BibleAnchorReference( ourBBB, ourC, ourV )
            print( BAR ) # Just print a summary
            result = BAR.matchesAnchorString( ourAnchor )
            if result: print( "  Matched {!r}".format( ourAnchor ) )
            else: print( "  DIDN'T MATCH {!r} <--------------------- Oops!".format( ourAnchor ) )

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleReferences.py
