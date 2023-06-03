#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodes.py
#
# Module handling BibleBooksCodes functions
#
# Copyright (C) 2010-2023 Robert Hunt
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
Module handling BibleBooksCodes functions.

BibleOrgSys uses a three-character book code to identify books.
    These referenceAbbreviations are nearly always represented as BBB in the program code
            (although formally named referenceAbbreviation
                and possibly still represented as that in some of the older code),
        and in a sense, this is the centre of the BibleOrgSys.
    The referenceAbbreviation/BBB always starts with a letter, and letters are always UPPERCASE
        so 2 Corinthians is 'CO2' not '2Co' or anything.
        This was because early versions of HTML ID fields used to need
                to start with a letter (not a digit),
            (and most identifiers in computer languages still require that).
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2023-06-03' # by RJH
SHORT_PROGRAM_NAME = "BibleBooksCodes"
PROGRAM_NAME = "Bible Books Codes handler"
PROGRAM_VERSION = '0.93'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BOOKLIST_OT39 = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', 'CH1', 'CH2', \
        'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZE', 'DAN', \
        'HOS', 'JOL', 'AMO', 'OBA', 'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL' )
assert len( BOOKLIST_OT39 ) == 39
BOOKLIST_NT27 = ( 'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', \
        'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV' )
assert len( BOOKLIST_NT27 ) == 27
BOOKLIST_66 = BOOKLIST_OT39 + BOOKLIST_NT27
assert len( BOOKLIST_66 ) == 66


@singleton # Can only ever have one instance
class BibleBooksCodes:
    """
    Class for handling BibleBooksCodes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ) -> None: # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__DataDicts = None # We'll import into this in loadData
    # end of BibleBooksCodes.__init__


    def loadData( self, XMLFileOrFilepath=None ):
        """
        Loads the JSON or pickle or XML data file (in that order unless the parameter is given)
            and imports it to dictionary format (if not done already).
        """
        if not self.__DataDicts: # We need to load them once -- don't do this unnecessarily
            if XMLFileOrFilepath is None:
                # See if we can load from the pickle file (faster than loading from the XML)
                standardXMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes.xml' )
                standardPickleFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes_Tables.pickle' )
                try:
                    pickleIsNewer = os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                                and os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime
                except FileNotFoundError as e:
                    pickleIsNewer = 'xml' in str(e) # Couldn't find xml file -- these aren't included in PyPI package
                # if os.access( standardPickleFilepath, os.R_OK ) \
                # and os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                # and os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                if pickleIsNewer:
                    import pickle
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading pickle file {standardPickleFilepath}…" )
                    with open( standardPickleFilepath, 'rb') as pickleFile:
                        self.__DataDicts = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    return self # So this command can be chained after the object creation
                elif DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "BibleBooksCodes pickle file can't be loaded!" )
                standardJsonFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes_Tables.json' )
                if os.access( standardJsonFilepath, os.R_OK ) \
                and os.stat(standardJsonFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                and os.stat(standardJsonFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                    import json
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading json file {standardJsonFilepath}…" )
                    with open( standardJsonFilepath, 'rb') as JsonFile:
                        self.__DataDicts = json.load( JsonFile )
                    # NOTE: We have to convert str referenceNumber keys back to ints
                    self.__DataDicts['referenceNumberDict'] = { int(key):value \
                                for key,value in self.__DataDicts['referenceNumberDict'].items() }
                    return self # So this command can be chained after the object creation
                elif DEBUGGING_THIS_MODULE:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "BibleBooksCodes JSON file can't be loaded!" )
            # else: # We have to load the XML (much slower)
            from BibleOrgSys.Reference.Converters.BibleBooksCodesConverter import BibleBooksCodesConverter
            if XMLFileOrFilepath is not None:
                logging.warning( _("Bible books codes are already loaded -- your given filepath of {!r} was ignored").format(XMLFileOrFilepath) )
            bbcc = BibleBooksCodesConverter()
            bbcc.loadAndValidate( XMLFileOrFilepath ) # Load the XML (if not done already)
            self.__DataDicts = bbcc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self # So this command can be chained after the object creation
    # end of BibleBooksCodes.loadData


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleBooksCodes object"
        result += ('\n' if result else '') + ' '*indent + _("Number of entries = {:,}").format( len(self.__DataDicts['referenceAbbreviationDict']) )
        return result
    # end of BibleBooksCodes.__str__


    def __len__( self ):
        """
        Return the number of available codes.
        """
        assert len(self.__DataDicts['referenceAbbreviationDict']) == len(self.__DataDicts['referenceNumberDict'])
        return len(self.__DataDicts['referenceAbbreviationDict'])
    # end of BibleBooksCodes.__len__


    def __contains__( self, BBB:str ) -> bool:
        """
        Returns True or False.
        """
        return BBB in self.__DataDicts['referenceAbbreviationDict']


    def __iter__( self ) -> str:
        """
        Yields the next BBB.
        
        This gives the BBBs with the OT39 and NT27 first.
            (This isn't always the order that you want -- see getSequenceList() below.)
        """
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            yield BBB


    def isValidBBB( self, BBB:str ) -> bool:
        """
        Returns True or False.
        """
        return BBB in self.__DataDicts['referenceAbbreviationDict']


    def getBBBFromReferenceNumber( self, referenceNumber ) -> str:
        """
        Return the referenceAbbreviation for the given book number (referenceNumber).

        This is probably only useful in the range 1..66 (GEN..REV).
            (After that, it specifies our arbitrary order.)
        """
        if isinstance( referenceNumber, str ): referenceNumber = int( referenceNumber ) # Convert str to int if necessary
        if not 1 <= referenceNumber <= 999: raise ValueError
        return self.__DataDicts['referenceNumberDict'][referenceNumber]['referenceAbbreviation']
    # end of BibleBooksCodes.getBBBFromReferenceNumber


    def getAllReferenceAbbreviations( self ) -> List[str]:
        """
        Returns a list of all possible BBB codes.
        """
        return [BBB for BBB in self.__DataDicts['referenceAbbreviationDict']]
        #return self.__DataDicts['referenceAbbreviationDict'].keys() # Why didn't this work?


    def getReferenceNumber( self, BBB:str ) -> int:
        """
        Return the referenceNumber 1..999 for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['referenceNumber']


    def getSequenceList( self, myList=None ) -> List[str]:
        """
        Return a list of BBB codes in a sequence that could be used for the print order if no further information is available.
            If you supply a list of books, it puts your actual book codes into the default order.
                Your list can simply be a list of BBB strings, or a list of tuples with the BBB as the first entry in the tuple.
        """
        if myList is None: return self.__DataDicts['sequenceList']
        # They must have given us their list of books
        assert isinstance( myList, (list,tuple,set) )
        if not myList: return [] # Return an empty list if that's what they gave
        for something in myList: # Something can be a BBB string or a tuple
            BBB = something if isinstance( something, str ) else something[0] # If it's a tuple, assume that the BBB is the first item in the tuple
            assert self.isValidBBB( BBB ) # Check the supplied list
        resultList = []
        for BBB1 in self.__DataDicts['sequenceList']:
            for something in myList:
                BBB2 = something if isinstance( something, str ) else something[0] # If it's a tuple, assume that the BBB is the first item in the tuple
                if BBB2 == BBB1:
                    resultList.append( something )
                    break
        assert len(resultList) == len(myList)
        #if resultList == myList: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getSequenceList made no change to the order" )
        #else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "getSequenceList: {} produced {}".format( myList, resultList ) )
        return resultList
    # end of BibleBooksCodes.getSequenceList


    def _getFullEntry( self, BBB:str ) -> dict:
        """
        Return the full dictionary for the given book (code).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]


    def getCCELNumber( self, BBB:str ) -> int:
        """
        Return the CCEL number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['CCELNumberString']


    def getShortAbbreviation( self, BBB:str ) -> str:
        """
        Return the short abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['shortAbbreviation']


    def getSBLAbbreviation( self, BBB:str ) -> str:
        """
        Return the SBL abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['SBLAbbreviation']


    def getOSISAbbreviation( self, BBB:str ) -> str:
        """
        Return the OSIS abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['OSISAbbreviation']


    def getSwordAbbreviation( self, BBB:str ) -> str:
        """
        Return the Sword abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['SwordAbbreviation']


    def getUSFMAbbreviation( self, BBB:str ) -> str:
        """
        Return the USFM abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USFMAbbreviation']


    def getUSFMNumStr( self, BBB:str ) -> str:
        """
        Return the two-digit USFM number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USFMNumberString']


    def getUSXNumStr( self, BBB:str ) -> str:
        """
        Return the three-digit USX number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USXNumberString']


    def getUnboundBibleCode( self, BBB:str ) -> str:
        """
        Return the three character (two-digits and one uppercase letter) Unbound Bible code
            for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['UnboundCodeString']


    def getBibleditNumStr( self, BBB:str ) -> str:
        """
        Return the one or two-digit Bibledit number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['BibleditNumberString']


    def getLogosNumStr( self, BBB:str ) -> str:
        """
        Return the one to three digit Logos number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['LogosNumberString']


    def getNETBibleAbbreviation( self, BBB:str ) -> str:
        """
        Return the NET Bible abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['NETBibleAbbreviation']


    def getDrupalBibleAbbreviation( self, BBB:str ) -> str:
        """
        Return the DrupalBible abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['DrupalBibleAbbreviation']


    def getByzantineAbbreviation( self, BBB:str ) -> str:
        """
        Return the Byzantine abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['ByzantineAbbreviation']


    def getBBBFromShortAbbreviation( self, shortAbbreviation:str, strict:bool=False ) -> str:
        """
        Return the reference abbreviation string for the given short book code string.
            NOTE: This tends to be more forgiving than more specific Bible code systems.

        Also tries adding spaces in codes like 1Sa unless strict is set to True.
        Also tries the SBL and NET book codes unless strict is set to True.
        """
        if strict:
            return self.__DataDicts['shortAbbreviationDict'][shortAbbreviation.upper()][1]
        # else: # not strict
        try: return self.__DataDicts['shortAbbreviationDict'][shortAbbreviation.upper()][1]
        except KeyError: # Maybe it has a space in it
            try: return self.__DataDicts['shortAbbreviationDict'][shortAbbreviation.upper().replace(' ','')][1]
            except KeyError: # try SBL
                try: return self.__DataDicts['SBLAbbreviationDict'][shortAbbreviation.upper()][1]
                except KeyError: # try NET for last desperate attempt
                    return self.__DataDicts['NETBibleAbbreviationDict'][shortAbbreviation.upper()][1]


    def getBBBFromOSISAbbreviation( self, osisAbbreviation:str, strict:bool=False ) -> str:
        """
        Return the reference abbreviation string for the given OSIS book code string.

        Also tries the Sword book codes unless strict is set to True.
        """
        if strict:
            return self.__DataDicts['OSISAbbreviationDict'][osisAbbreviation.upper()][1]
        # else: # not strict
        try: return self.__DataDicts['OSISAbbreviationDict'][osisAbbreviation.upper()][1]
        except KeyError: # Maybe Sword has an informal abbreviation???
            return self.__DataDicts['SwordAbbreviationDict'][osisAbbreviation.upper()][1]


    def getBBBFromUSFMAbbreviation( self, USFMAbbreviation:str, strict:bool=False ) -> str:
        """
        Return the reference abbreviation string for the given USFM (Paratext) book code string.
        """
        assert len(USFMAbbreviation) == 3, f"{USFMAbbreviation=} {strict=}"
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, USFMAbbreviation, self.__DataDicts['USFMAbbreviationDict'][USFMAbbreviation.upper()] )
        result = self.__DataDicts['USFMAbbreviationDict'][USFMAbbreviation.upper()][1] # Can be a string or a list
        if isinstance( result, str ): return result
        if strict: logging.warning( "getBBBFromUSFMAbbreviation is assuming that the best fit for USFM ID {!r} is the first entry in {}".format( USFMAbbreviation, result ) )
        return result[0] # Assume that the first entry is the best pick


    def getBBBFromUnboundBibleCode( self, UnboundBibleCode:str ) -> str:
        """
        Return the reference abbreviation string for the given Unbound Bible book code string.
        """
        return self.__DataDicts['UnboundCodeDict'][UnboundBibleCode.upper()][1]
    # end of BibleBooksCodes.getBBBFromUnboundBibleCode


    def getBBBFromDrupalBibleCode( self, DrupalBibleCode:str ) -> str:
        """
        Return the reference abbreviation string for the given DrupalBible book code string.
        """
        return self.__DataDicts['DrupalBibleAbbreviationDict'][DrupalBibleCode.upper()][1]
    # end of BibleBooksCodes.getBBBFromDrupalBibleCode


    def getBBBFromText( self, someText:str ) -> str:
        """
        Attempt to return the BBB reference abbreviation string for the given book information (text).

        Only works for English.
        TODO: This DEFINITELY NEEDS IMPROVING !!!
        Ah, BibleBooksNames.py has a more generic version.

        Returns BBB or None.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "BibleBooksCodes.getBBBFromText( {} )".format( someText ) )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert someText and isinstance( someText, str )

        SomeUppercaseText = someText.upper()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\nrAD', len(self.__DataDicts['referenceAbbreviationDict']), [BBB for BBB in self.__DataDicts['referenceAbbreviationDict']] )
        if SomeUppercaseText in self.__DataDicts['referenceAbbreviationDict']:
            return SomeUppercaseText # it's already a BBB code
        #if someText.isdigit() and 1 <= int(someText) <= 999:
            #return self.__DataDicts['referenceNumberDict'][int(someText)]['referenceAbbreviation']
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\naAD1', len(self.__DataDicts['allAbbreviationsDict']), sorted([BBB for BBB in self.__DataDicts['allAbbreviationsDict']]) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '\naAD2', len(self.__DataDicts['allAbbreviationsDict']), self.__DataDicts['allAbbreviationsDict'] )
        if SomeUppercaseText in self.__DataDicts['allAbbreviationsDict']:
            return self.__DataDicts['allAbbreviationsDict'][SomeUppercaseText]

        # TODO: We need to find a way to add these into the table
        if SomeUppercaseText == 'EPJER': return 'LJE' # Fails below because both 'LJE' and 'PJE' are valid BBBs
        if SomeUppercaseText == 'DEUTERONOMY': return 'DEU' # Fails below because 'EUT' is also a valid BBB
        if SomeUppercaseText == 'JUDGES': return 'JDG' # Fails below because 'GES' is also a valid BBB
        if SomeUppercaseText == '1 SAMUEL': return 'SA1' # Fails below because 'SAM' is also a valid BBB
        if SomeUppercaseText == '2 SAMUEL': return 'SA2' # Fails below because 'SAM' is also a valid BBB
        if SomeUppercaseText == '1 CHRONICLES': return 'CH1' # Fails below because 'CHR' is also a valid BBB
        if SomeUppercaseText == '2 CHRONICLES': return 'CH2' # Fails below because 'CHR' is also a valid BBB
        if SomeUppercaseText == 'ECCLESIASTES': return 'ECC' # Fails below because 'LES' is also a valid BBB
        if SomeUppercaseText == 'LAMENTATIONS': return 'LAM' # Fails below because 'TAT' is also a valid BBB
        if SomeUppercaseText == 'HABAKKUK': return 'HAB' # Fails below because 'BAK' is also a valid BBB
        if SomeUppercaseText == 'ZEPHANIAH': return 'ZEP' # Fails below because 'EPH' is also a valid BBB
        if SomeUppercaseText == 'ZECHARIAH': return 'ZEC' # Fails below because 'ARI' is also a valid BBB
        if SomeUppercaseText == 'ROMANS': return 'ROM' # Fails below because 'MAN' is also a valid BBB
        if SomeUppercaseText == '1 CORINTHIANS': return 'CO1' # Fails below because 'INT' is also a valid BBB
        if SomeUppercaseText == '2 CORINTHIANS': return 'CO2' # Fails below because 'INT' is also a valid BBB
        if SomeUppercaseText == '1 TIMOTHY': return 'TI1' # Fails below because 'OTH' is also a valid BBB
        if SomeUppercaseText == '2 TIMOTHY': return 'TI2' # Fails below because 'OTH' is also a valid BBB
        if SomeUppercaseText == '1 KINGS': return 'KI1'
        if SomeUppercaseText == '2 KINGS': return 'KI2'
        if SomeUppercaseText == 'SONG OF SONGS' or SomeUppercaseText == 'SONG OF SOLOMON': return 'SNG'
        if SomeUppercaseText == 'MK': return 'MRK'
        if SomeUppercaseText == 'PHILIPPIANS': return 'PHP'
        if SomeUppercaseText == '1 THESSALONIANS' or SomeUppercaseText == '1THS': return 'TH1'
        if SomeUppercaseText == '2 THESSALONIANS' or SomeUppercaseText == '2THS': return 'TH2'
        if SomeUppercaseText == 'PHILEMON': return 'PHM'
        if SomeUppercaseText == '1 PETER': return 'PE1'
        if SomeUppercaseText == '2 PETER': return 'PE2'
        if SomeUppercaseText == 'PS151': return 'PS2' # Special case

        # Ok, let's try guessing
        matchCount, foundBBB = 0, None
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            if BBB in SomeUppercaseText:
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"getBBB1: {BBB=} {SomeUppercaseText=}" )
                matchCount += 1
                foundBBB = BBB
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"getBBB2: {someText=} {matchCount=} {foundBBB=}" )
        if matchCount == 1: return foundBBB # it's non-ambiguous
        dPrint( 'Never', DEBUGGING_THIS_MODULE, sorted(self.__DataDicts['allAbbreviationsDict']) )
    # end of BibleBooksCodes.getBBBFromText


    def getExpectedChaptersList( self, BBB:str ) -> List[str]:
        """
        Gets a list with the number of expected chapters for the given book code (referenceAbbreviation).
        The number(s) of expected chapters is left in string form (not int).

        Why is it a list?
            Because some books have alternate possible numbers of chapters depending on the Biblical tradition.
        """
        #if BBB not in self.__DataDicts['referenceAbbreviationDict'] \
        #or "numExpectedChapters" not in self.__DataDicts['referenceAbbreviationDict'][BBB] \
        #or self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is None:
        if 'numExpectedChapters' not in self.__DataDicts['referenceAbbreviationDict'][BBB] \
        or self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is None:
            return []

        eC = self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters']
        if eC: return [v for v in eC.split(',')]
    # end of BibleBooksCodes.getExpectedChaptersList


    def getMaxChapters( self, BBB:str ) -> int:
        """
        Returns an integer with the maximum number of chapters to be expected for this book.
        """
        maxChapters = -1
        for numChapters in self.getExpectedChaptersList( BBB ):
            try: intNC = int( numChapters )
            except ValueError: intNC = -1
            if intNC > maxChapters: maxChapters = intNC
        return maxChapters
    # end of getMaxChapters


    def getSingleChapterBooksList( self ) -> List[str]:
        """
        Makes up and returns a list of single chapter book codes (BBB).
        """
        results = []
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            if self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is not None \
            and self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] == '1':
                results.append( BBB )
        return results
    # end of BibleBooksCodes.getSingleChapterBooksList


    def isSingleChapterBook( self, BBB:str ) -> bool:
        """
        Returns True or False if the number of chapters for the book is only one.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] == '1'


    def isChapterVerseBook( self, BBB:str ) -> bool:
        """
        Returns True or False if this book is expected to have chapters and verses.
        """
        return 'numExpectedChapters' in self.__DataDicts['referenceAbbreviationDict'][BBB] \
            and self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is not None


    def getOSISSingleChapterBooksList( self ) -> List[str]:
        """
        Gets a list of OSIS single chapter book abbreviations.
        """
        results = []
        for BBB in self.getSingleChapterBooksList():
            osisAbbrev = self.getOSISAbbreviation(BBB)
            if osisAbbrev is not None: results.append( osisAbbrev )
        return results
    # end of BibleBooksCodes.getOSISSingleChapterBooksList


    def getAllOSISBooksCodes( self ) -> List[str]:
        """
        Return a list of all available OSIS book codes (in no particular order).
        """
        return [bk for bk in self.__DataDicts['OSISAbbreviationDict']]
    #end of BibleBooksCodes.getAllOSISBooksCodes


    def getAllUSFMBooksCodes( self, toUpper:bool=False ) -> List[str]:
        """
        Return a list of all available USFM book codes.
        """
        result = []
        for BBB, values in self.__DataDicts['referenceAbbreviationDict'].items():
            pA = values['USFMAbbreviation']
            if pA is not None:
                if toUpper: pA = pA.upper()
                if pA not in result: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( pA )
        return result
    # end of BibleBooksCodes.getAllUSFMBooksCodes


    def getAllUSFMBooksCodeNumberTriples( self ) -> List[Tuple[str,int,str]]:
        """
        Return a list of all available USFM book codes.

        The list contains tuples of:
            USFMAbbreviation, USFMNumber, referenceAbbreviation/BBB
        """
        found, result = [], []
        for BBB, values in self.__DataDicts['referenceAbbreviationDict'].items():
            pA = values['USFMAbbreviation']
            pN = values['USFMNumberString']
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of BibleBooksCodes.getAllUSFMBooksCodeNumberTriples


    def getAllUSXBooksCodeNumberTriples( self ):
        """
        Return a list of all available USX book codes.

        The list contains tuples of: USFMAbbreviation, USXNumber, referenceAbbreviation
        """
        found, result = [], []
        for BBB, values in self.__DataDicts['referenceAbbreviationDict'].items():
            pA = values['USFMAbbreviation']
            pN = values['USXNumberString']
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of BibleBooksCodes.getAllUSXBooksCodeNumberTriples


    #def getAllUnboundBibleBooksCodePairs( self ):
        #"""
        #Return a list of all available Unbound Bible book codes.

        #The list contains tuples of: UnboundCode, referenceAbbreviation
        #"""
        #result = []
        #for BBB, values in self.__DataDicts['referenceAbbreviationDict'].items():
            #uBC = values['UnboundCodeString']
            #if uBC is not None:
                #result.append( (uBC, BBB,) )
        #return result
    ## end of BibleBooksCodes.getAllUnboundBibleBooksCodePairs


    def getAllBibleditBooksCodeNumberTriples( self ):
        """
        Return a list of all available Bibledit book codes.

        The list contains tuples of: USFMAbbreviation, BibleditNumber, referenceAbbreviation
        """
        found, result = [], []
        for BBB, values in self.__DataDicts['referenceAbbreviationDict'].items():
            pA = values['USFMAbbreviation']
            pN = values['BibleditNumberString']
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of BibleBooksCodes.getAllBibleditBooksCodeNumberTriples


    def getPossibleAlternativeBooksCodes( self, BBB:str ):
        """
        Return a list of any book reference codes for possible similar alternative books.

        Returns None (rather than an empty list) if there's none.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['possibleAlternativeBooks']
    # end of BibleBooksCodes.getPossibleAlternativeBooksCodes


    def getTypicalSection( self, BBB:str ):
        """
        Return typical section abbreviation.
            OT, OT+, NT, NT+, DC, PS, FRT, BAK

        Returns None (rather than an empty list) if there's none.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['typicalSection']
    # end of BibleBooksCodes.getPossibleAlternativeBooksCodes


    def continuesThroughChapters( self, BBB:str ):
        """
        Returns True if the storyline of the book continues through chapters,
            i.e., the chapter divisions are artificial.

        Returns False for books like Psalms where chapters are actual units.

        Note that this is a bit of a hack,
            because ideally this information should be encoded in the XML file, not here in the code.
            TODO: Fix this
        """
        if BBB in ('PSA','PS2','LAM',): return False
        return True
    # end of BibleBooksCodes.continuesThroughChapters


    def BCVReferenceToInt( self, BCVReferenceTuple ) -> int:
        """
        Convert a BCV or BCVS reference to an integer
            especially so that references can be sorted.

        If a V is a verse span with a hyphen (e.g., '3-4'),
            it uses the value before the hyphen.
        """
        try:
            BBB, C, V = BCVReferenceTuple
            S = ''
        except:
            BBB, C, V, S = BCVReferenceTuple
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BCVReferenceTuple ); halt # Need to finish handling BCVReferenceTuple
        result = self.getReferenceNumber( BBB )

        try:
            intC = int( C )
        except ValueError:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(C) ); halt # Need to finish handling C
        result = result * 100 + intC

        try:
            intV = int( V.split('-')[0] ) # If it's a verse span e.g., 3-4, just take the first part
        except ValueError:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(V) ); halt # Need to finish handling V
        result = result * 150 + intV

        try:
            intS = {'a':0, 'b':1}[S.lower()] if S else 0
        except ValueError:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(S) ); halt # Need to finish handling S
        result = result * 10 + intS

        return result
    # end of BibleBooksCodes.BCVReferenceToInt


    def sortBCVReferences( self, referencesList ) -> List[Tuple[str,str,str]]:
        """
        Sort an iterable containing 3-tuples of BBB,C,V strings
            or 4-tuples of BBB,C,V,S strings
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"sortBCVReferences( ({len(referencesList)}) {referencesList} )…" )
        sortedList = sorted( referencesList, key=self.BCVReferenceToInt )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  sortBCVReferences returning ({len(sortedList)}) {sortedList}" )
        # assert len(sortedList) == len(referencesList)
        return sortedList
    # end of BibleBooksCodes.sortBCVReferences


    def getBookName( self, BBB:str ):
        """
        Returns the original language name for a book.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['bookName']
    # end of BibleBooksCodes.getEnglishName_NR


    # NOTE: The following functions are all not recommended (NR) because they rely on assumed information that may be incorrect
    #           i.e., they assume English language or European book order conventions
    #       They are included because they might be necessary for error messages or similar uses
    #           (where the precisely correct information is unknown)
    def getEnglishName_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns the first English name for a book. (Options are separated by forward slashes.)

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['bookNameEnglishGuide'].split('/',1)[0].strip()
    # end of BibleBooksCodes.getEnglishName_NR

    def getEnglishNameList_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns a list of possible English names for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        return [name.strip() for name in self.__DataDicts['referenceAbbreviationDict'][BBB]['bookNameEnglishGuide'].split('/')]
    # end of BibleBooksCodes.getEnglishNameList_NR

    def isOldTestament_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns True if the given referenceAbbreviation indicates a European Protestant Old Testament book (39).
            NOTE: This is not truly international so it's not a recommended function.
        """
        return 1 <= self.getReferenceNumber(BBB) <= 39
    # end of BibleBooksCodes.isOldTestament_NR

    def isNewTestament_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns True if the given referenceAbbreviation indicates a European Protestant New Testament book (27).
            NOTE: This is not truly international so it's not a recommended function.
        """
        return 40 <= self.getReferenceNumber(BBB) <= 66
    # end of BibleBooksCodes.isNewTestament_NR

    def isDeuterocanon_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns True if the given referenceAbbreviation indicates a European Deuterocanon/Apocrypha book (15).
            NOTE: This is not truly international so it's not a recommended function.
        """
        return BBB in ('TOB','JDT','ESG','WIS','SIR','BAR','LJE','PAZ','SUS','BEL','MA1','MA2','GES','LES','MAN',)
    # end of BibleBooksCodes.isDeuterocanon_NR

    def createLists( self, outputFolder=None ):
        """
        Writes a list of Bible Books Codes to a text file in the BOSOutputFiles folder
            and also to an HTML-formatted table.
        """
        if not outputFolder: outputFolder = "BOSOutputFiles/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        with open( os.path.join( outputFolder, "BOS_Books_Codes.txt" ), 'wt', encoding='utf-8' ) as txtFile, \
             open( os.path.join( outputFolder, "BOS_Books_Codes.html" ), 'wt', encoding='utf-8' ) as htmlFile:
                txtFile.write( "NUM BBB English name\n" )
                htmlFile.write( '<html><body><table border="1">\n<tr><th>NUM</th><th>BBB</th><th>English name</th></tr>\n' )
                for BBB in self.__DataDicts['referenceAbbreviationDict']:
                    txtFile.write( "{:3} {} {}\n".format( self.getReferenceNumber(BBB), BBB, self.getEnglishName_NR(BBB) ) )
                    htmlFile.write( '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format( self.getReferenceNumber(BBB), BBB, self.getEnglishName_NR(BBB) ) )
                htmlFile.write( "</table></body></html>\n" )
    # end of BibleBooksCodes.createLists


    @staticmethod
    def tidyBBB( BBB:str, titleCase=False ) -> str:
        """
        Change book codes like SA1 to the conventional 1SA
            (or 1Sa using the titleCase flag).

        BBB is always three characters starting with an UPPERCASE LETTER.
        """
        assert BBB in BibleBooksCodes(), f"BibleBooksCodes.tidyBBB {BBB=}"
        if titleCase:
            return f'{BBB[2]}{BBB[0]}{BBB[1].lower()}' if BBB[2].isdigit() else f'{BBB[0]}{BBB[1:].lower()}'
        # else: # leave as UPPERCASE
        return f'{BBB[2]}{BBB[:2]}' if BBB[2].isdigit() else BBB
    # end of BibleBooksCodes.tidyBBB

    @staticmethod
    def tidyBBBs( BBBs:List[str], titleCase=False ) -> List[str]:
        """
        Change a list of book codes like SA1 to the conventional 1SA
            (or 1Sa using the titleCase flag).
        """
        assert all([BBB in BibleBooksCodes() for BBB in BBBs]), f"BibleBooksCodes,tidyBBBs {BBBs=}"
        return [BibleBooksCodes().tidyBBB( BBB, titleCase ) for BBB in BBBs]
    # end of BibleBooksCodes.tidyBBBs
# end of BibleBooksCodes class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the BibleBooksCodes object
    bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbc ) # Just print a summary
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Psalms has {} expected chapters".format(bbc.getMaxChapters("PSA")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All BBBs:", len(bbc.getAllReferenceAbbreviations()), bbc.getAllReferenceAbbreviations() )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All BBBs in a print sequence", len(bbc.getSequenceList()), bbc.getSequenceList() )
    myBBBs = ['GEN','EXO','PSA','ISA','MAL','MAT','REV','GLS']
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    myBBBs = ['REV','CO2','GEN','PSA','CO1','ISA','SA2','MAT','GLS','JOB']
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    assert bbc.getUSFMNumStr( 'MAT' ) == '41'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "USFM triples:", len(bbc.getAllUSFMBooksCodeNumberTriples()), bbc.getAllUSFMBooksCodeNumberTriples() )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "USX triples:", len(bbc.getAllUSXBooksCodeNumberTriples()), bbc.getAllUSXBooksCodeNumberTriples() )
    assert bbc.getBibleditNumStr( 'MAT' ) == '40'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Bibledit triples:", len(bbc.getAllBibleditBooksCodeNumberTriples()), bbc.getAllBibleditBooksCodeNumberTriples() )
    assert bbc.getLogosNumStr( 'MAT' ) == '61'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Single chapter books (and OSIS):\n  {}\n  {}".format( bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList() ) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Possible alternative  books to Esther: {}".format( bbc.getPossibleAlternativeBooksCodes('EST') ) )
    for someString,expectedBBB in (('PE2','PE2'), ('2Pe','PE2'), ('2 Pet','PE2'), ('2Pet','PE2'), ('Job','JOB'), ('Deut','DEU'), ('Deuteronomy','DEU'), ('EpJer','LJE'), ('1 Kings','KI1'), ('2 Samuel','SA2')):
        BBB = bbc.getBBBFromText( someString )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{someString=} -> {BBB=} ({expectedBBB=})" )
        assert BBB==expectedBBB, f"{someString=} -> {BBB=} ({expectedBBB=})"
    myOSIS = ( 'Gen', '1Kgs', 'Ps', 'Mal', 'Matt', '2John', 'Rev', 'EpLao', '3Meq', )
    for osisCode in myOSIS:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Osis {!r} -> {}".format( osisCode, bbc.getBBBFromOSISAbbreviation( osisCode ) ) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{BibleBooksCodes().tidyBBBs(['GEN','SA1','CO2','JN3','XXA'])=}" )

    sections:Dict[str,List[str]] = {}
    for BBB in bbc:
        section = bbc.getTypicalSection( BBB )
        if section not in sections: sections[section] = []
        sections[section].append( BBB )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{} book codes in {} sections".format( len(bbc), len(sections) ) )
    for section in sections: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  {} section: {} {}".format( section, len(sections[section]), sections[section] ) )
# end of BibleBooksCodes.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the BibleBooksCodes object
    bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbc ) # Just print a summary
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Psalms has {} expected chapters".format(bbc.getMaxChapters("PSA")) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All BBBs:", len(bbc.getAllReferenceAbbreviations()), bbc.getAllReferenceAbbreviations() )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "All BBBs in a print sequence", len(bbc.getSequenceList()), bbc.getSequenceList() )
    myBBBs = ['GEN','EXO','PSA','ISA','MAL','MAT','REV','GLS']
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    myBBBs = ['REV','CO2','GEN','PSA','CO1','ISA','SA2','MAT','GLS','JOB']
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    assert bbc.getUSFMNumStr( 'MAT' ) == '41'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "USFM triples:", len(bbc.getAllUSFMBooksCodeNumberTriples()), bbc.getAllUSFMBooksCodeNumberTriples() )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "USX triples:", len(bbc.getAllUSXBooksCodeNumberTriples()), bbc.getAllUSXBooksCodeNumberTriples() )
    assert bbc.getBibleditNumStr( 'MAT' ) == '40'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Bibledit triples:", len(bbc.getAllBibleditBooksCodeNumberTriples()), bbc.getAllBibleditBooksCodeNumberTriples() )
    assert bbc.getLogosNumStr( 'MAT' ) == '61'
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Single chapter books (and OSIS):\n  {}\n  {}".format( bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList() ) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Possible alternative  books to Esther: {}".format( bbc.getPossibleAlternativeBooksCodes('EST') ) )
    for someString,expectedBBB in (('PE2','PE2'), ('2Pe','PE2'), ('2 Pet','PE2'), ('2Pet','PE2'), ('Job','JOB'), ('Deut','DEU'), ('Deuteronomy','DEU'), ('EpJer','LJE'), ('1 Kings','KI1'), ('2 Samuel','SA2')):
        BBB = bbc.getBBBFromText( someString )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{someString=} -> {BBB=} ({expectedBBB=})" )
        assert BBB==expectedBBB, f"{someString=} -> {BBB=} ({expectedBBB=})"
    myOSIS = ( 'Gen', '1Kgs', 'Ps', 'Mal', 'Matt', '2John', 'Rev', 'EpLao', '3Meq', )
    for osisCode in myOSIS:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Osis {!r} -> {}".format( osisCode, bbc.getBBBFromOSISAbbreviation( osisCode ) ) )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{BibleBooksCodes().tidyBBBs(['GEN','SA1','CO2','JN3','XXA'])=}" )

    sections:Dict[str,List[str]] = {}
    for BBB in bbc:
        section = bbc.getTypicalSection( BBB )
        if section not in sections: sections[section] = []
        sections[section].append( BBB )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\n{} book codes in {} sections".format( len(bbc), len(sections) ) )
    for section in sections: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  {} section: {} {}".format( section, len(sections[section]), sections[section] ) )
# end of BibleBooksCodes.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleBooksCodes.py
