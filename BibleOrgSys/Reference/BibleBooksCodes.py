#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodes.py
#
# Module handling BibleBooksCodes functions
#
# Copyright (C) 2010-2020 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module handling BibleBooksCodes functions.
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


LAST_MODIFIED_DATE = '2020-04-20' # by RJH
SHORT_PROGRAM_NAME = "BibleBooksCodes"
PROGRAM_NAME = "Bible Books Codes handler"
PROGRAM_VERSION = '0.83'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False



@singleton # Can only ever have one instance
class BibleBooksCodes:
    """
    Class for handling BibleBooksCodes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
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
                    vPrint( 'Info', debuggingThisModule, f"Loading pickle file {standardPickleFilepath}…" )
                    with open( standardPickleFilepath, 'rb') as pickleFile:
                        self.__DataDicts = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    return self # So this command can be chained after the object creation
                elif debuggingThisModule:
                    vPrint( 'Quiet', debuggingThisModule, "BibleBooksCodes pickle file can't be loaded!" )
                standardJsonFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATAFILES_FOLDERPATH.joinpath( 'BibleBooksCodes_Tables.json' )
                if os.access( standardJsonFilepath, os.R_OK ) \
                and os.stat(standardJsonFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                and os.stat(standardJsonFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                    import json
                    vPrint( 'Info', debuggingThisModule, f"Loading json file {standardJsonFilepath}…" )
                    with open( standardJsonFilepath, 'rb') as JsonFile:
                        self.__DataDicts = json.load( JsonFile )
                    # NOTE: We have to convert str referenceNumber keys back to ints
                    self.__DataDicts['referenceNumberDict'] = { int(key):value \
                                for key,value in self.__DataDicts['referenceNumberDict'].items() }
                    return self # So this command can be chained after the object creation
                elif debuggingThisModule:
                    vPrint( 'Quiet', debuggingThisModule, "BibleBooksCodes JSON file can't be loaded!" )
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


    def __contains__( self, BBB:str ):
        """ Returns True or False. """
        return BBB in self.__DataDicts['referenceAbbreviationDict']


    def __iter__( self ):
        """ Yields the next BBB. """
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            yield BBB


    def isValidBBB( self, BBB:str ):
        """ Returns True or False. """
        return BBB in self.__DataDicts['referenceAbbreviationDict']


    def getBBBFromReferenceNumber( self, referenceNumber ):
        """
        Return the referenceAbbreviation for the given book number (referenceNumber).

        This is probably only useful in the range 1..66 (GEN..REV).
            (After that, it specifies our arbitrary order.)
        """
        if isinstance( referenceNumber, str ): referenceNumber = int( referenceNumber ) # Convert str to int if necessary
        if not 1 <= referenceNumber <= 999: raise ValueError
        return self.__DataDicts['referenceNumberDict'][referenceNumber]['referenceAbbreviation']
    # end of BibleBooksCodes.getBBBFromReferenceNumber


    def getAllReferenceAbbreviations( self ):
        """ Returns a list of all possible BBB codes. """
        return [BBB for BBB in self.__DataDicts['referenceAbbreviationDict']]
        #return self.__DataDicts['referenceAbbreviationDict'].keys() # Why didn't this work?


    def getReferenceNumber( self, BBB:str ):
        """ Return the referenceNumber 1..999 for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['referenceNumber']


    def getSequenceList( self, myList=None ):
        """
        Return a list of BBB codes in a sequence that could be used for the print order if no further information is available.
            If you supply a list of books, it puts your actual book codes into the default order.
                Your list can simply be a list of BBB strings, or a list of tuples with the BBB as the first entry in the tuple.
        """
        if myList is None: return self.__DataDicts['sequenceList']
        # They must have given us their list of books
        assert isinstance( myList, list )
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
        #if resultList == myList: vPrint( 'Quiet', debuggingThisModule, "getSequenceList made no change to the order" )
        #else: vPrint( 'Quiet', debuggingThisModule, "getSequenceList: {} produced {}".format( myList, resultList ) )
        return resultList
    # end of BibleBooksCodes.getSequenceList


    def _getFullEntry( self, BBB:str ):
        """
        Return the full dictionary for the given book (code).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]


    def getCCELNumber( self, BBB:str ):
        """ Return the CCEL number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['CCELNumberString']


    def getSBLAbbreviation( self, BBB:str ):
        """ Return the SBL abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['SBLAbbreviation']


    def getOSISAbbreviation( self, BBB:str ):
        """ Return the OSIS abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['OSISAbbreviation']


    def getSwordAbbreviation( self, BBB:str ):
        """ Return the Sword abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['SwordAbbreviation']


    def getUSFMAbbreviation( self, BBB:str ):
        """ Return the USFM abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USFMAbbreviation']


    def getUSFMNumber( self, BBB:str ):
        """ Return the two-digit USFM number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USFMNumberString']


    def getUSXNumber( self, BBB:str ):
        """ Return the three-digit USX number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['USXNumberString']


    def getUnboundBibleCode( self, BBB:str ):
        """
        Return the three character (two-digits and one uppercase letter) Unbound Bible code
            for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['UnboundCodeString']


    def getBibleditNumber( self, BBB:str ):
        """
        Return the one or two-digit Bibledit number string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['BibleditNumberString']


    def getNETBibleAbbreviation( self, BBB:str ):
        """
        Return the NET Bible abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['NETBibleAbbreviation']


    def getDrupalBibleAbbreviation( self, BBB:str ):
        """
        Return the DrupalBible abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['DrupalBibleAbbreviation']


    def getByzantineAbbreviation( self, BBB:str ):
        """
        Return the Byzantine abbreviation string for the given book code (referenceAbbreviation).
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['ByzantineAbbreviation']


    def getBBBFromOSISAbbreviation( self, osisAbbreviation:str, strict=False ):
        """
        Return the reference abbreviation string for the given OSIS book code string.

        Also tries the Sword book codes unless strict is set to True.
        """
        if strict: return self.__DataDicts['OSISAbbreviationDict'][osisAbbreviation.upper()][1]
        else:
            try: return self.__DataDicts['OSISAbbreviationDict'][osisAbbreviation.upper()][1]
            except KeyError: # Maybe Sword has an informal abbreviation???
                return self.__DataDicts['SwordAbbreviationDict'][osisAbbreviation.upper()][1]

    def getBBBFromUSFMAbbreviation( self, USFMAbbreviation:str, strict=False ):
        """
        Return the reference abbreviation string for the given USFM (Paratext) book code string.
        """
        assert len(USFMAbbreviation) == 3
        #dPrint( 'Quiet', debuggingThisModule, USFMAbbreviation, self.__DataDicts['USFMAbbreviationDict'][USFMAbbreviation.upper()] )
        result = self.__DataDicts['USFMAbbreviationDict'][USFMAbbreviation.upper()][1] # Can be a string or a list
        if isinstance( result, str ): return result
        if strict: logging.warning( "getBBBFromUSFMAbbreviation is assuming that the best fit for USFM ID {!r} is the first entry in {}".format( USFMAbbreviation, result ) )
        return result[0] # Assume that the first entry is the best pick


    def getBBBFromUnboundBibleCode( self, UnboundBibleCode:str ):
        """
        Return the reference abbreviation string for the given Unbound Bible book code string.
        """
        return self.__DataDicts['UnboundCodeDict'][UnboundBibleCode.upper()][1]
    # end of BibleBooksCodes.getBBBFromUnboundBibleCode


    def getBBBFromDrupalBibleCode( self, DrupalBibleCode:str ):
        """
        Return the reference abbreviation string for the given DrupalBible book code string.
        """
        return self.__DataDicts['DrupalBibleAbbreviationDict'][DrupalBibleCode.upper()][1]
    # end of BibleBooksCodes.getBBBFromDrupalBibleCode


    def getBBBFromText( self, someText:str ):
        """
        Attempt to return the BBB reference abbreviation string for the given book information (text).

        Only works for English.
        BibleBooksNames.py has a more generic version.

        Returns BBB or None.
        """
        fnPrint( debuggingThisModule, "BibleBooksCodes.getBBBFromText( {} )".format( someText ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert someText and isinstance( someText, str )

        SomeUppercaseText = someText.upper()
        #dPrint( 'Quiet', debuggingThisModule, '\nrAD', len(self.__DataDicts['referenceAbbreviationDict']), [BBB for BBB in self.__DataDicts['referenceAbbreviationDict']] )
        if SomeUppercaseText in self.__DataDicts['referenceAbbreviationDict']:
            return SomeUppercaseText # it's already a BBB code
        #if someText.isdigit() and 1 <= int(someText) <= 999:
            #return self.__DataDicts['referenceNumberDict'][int(someText)]['referenceAbbreviation']
        #dPrint( 'Quiet', debuggingThisModule, '\naAD1', len(self.__DataDicts['allAbbreviationsDict']), sorted([BBB for BBB in self.__DataDicts['allAbbreviationsDict']]) )
        #dPrint( 'Quiet', debuggingThisModule, '\naAD2', len(self.__DataDicts['allAbbreviationsDict']), self.__DataDicts['allAbbreviationsDict'] )
        if SomeUppercaseText in self.__DataDicts['allAbbreviationsDict']:
            return self.__DataDicts['allAbbreviationsDict'][SomeUppercaseText]

        # Ok, let's try guessing
        matchCount, foundBBB = 0, None
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            if BBB in SomeUppercaseText:
                #dPrint( 'Quiet', debuggingThisModule, 'getBBB1', BBB, SomeUppercaseText )
                matchCount += 1
                foundBBB = BBB
        #dPrint( 'Quiet', debuggingThisModule, 'getBBB2', repr(someText), matchCount, foundBBB )
        if matchCount == 1: return foundBBB # it's non-ambiguous
        #dPrint( 'Quiet', debuggingThisModule, sorted(self.__DataDicts['allAbbreviationsDict']) )
    # end of BibleBooksCodes.getBBBFromText


    def getExpectedChaptersList( self, BBB:str ):
        """
        Gets a list with the number of expected chapters for the given book code (referenceAbbreviation).
        The number(s) of expected chapters is left in string form (not int).

        Why is it a list?
            Because some books have alternate possible numbers of chapters depending on the Biblical tradition.
        """
        #if BBB not in self.__DataDicts['referenceAbbreviationDict'] \
        #or "numExpectedChapters" not in self.__DataDicts['referenceAbbreviationDict'][BBB] \
        #or self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is None:
        if "numExpectedChapters" not in self.__DataDicts['referenceAbbreviationDict'][BBB] \
        or self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is None:
            return []

        eC = self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters']
        if eC: return [v for v in eC.split(',')]
    # end of BibleBooksCodes.getExpectedChaptersList


    def getMaxChapters( self, BBB:str ):
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


    def getSingleChapterBooksList( self ):
        """
        Makes up and returns a list of single chapter book codes.
        """
        results = []
        for BBB in self.__DataDicts['referenceAbbreviationDict']:
            if self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] is not None \
            and self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] == '1':
                results.append( BBB )
        return results
    # end of BibleBooksCodes.getSingleChapterBooksList


    def isSingleChapterBook( self, BBB:str ):
        """ Returns True or False if the number of chapters for the book is only one. """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['numExpectedChapters'] == '1'


    def getOSISSingleChapterBooksList( self ):
        """ Gets a list of OSIS single chapter book abbreviations. """
        results = []
        for BBB in self.getSingleChapterBooksList():
            osisAbbrev = self.getOSISAbbreviation(BBB)
            if osisAbbrev is not None: results.append( osisAbbrev )
        return results
    # end of BibleBooksCodes.getOSISSingleChapterBooksList


    def getAllOSISBooksCodes( self ):
        """
        Return a list of all available OSIS book codes (in no particular order).
        """
        return [bk for bk in self.__DataDicts['OSISAbbreviationDict']]
    #end of BibleBooksCodes.getAllOSISBooksCodes


    def getAllUSFMBooksCodes( self, toUpper=False ):
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


    def getAllUSFMBooksCodeNumberTriples( self ):
        """
        Return a list of all available USFM book codes.

        The list contains tuples of: USFMAbbreviation, USFMNumber, referenceAbbreviation
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
        """
        try:
            BBB, C, V = BCVReferenceTuple
            S = ''
        except:
            BBB, C, V, S = BCVReferenceTuple
            vPrint( 'Quiet', debuggingThisModule, BCVReferenceTuple ); halt # Need to finish handling BCVReferenceTuple
        result = self.getReferenceNumber( BBB )

        try:
            intC = int( C )
        except ValueError:
            vPrint( 'Quiet', debuggingThisModule, repr(C) ); halt # Need to finish handling C
        result = result * 100 + intC

        try:
            intV = int( V )
        except ValueError:
            vPrint( 'Quiet', debuggingThisModule, repr(V) ); halt # Need to finish handling V
        result = result * 150 + intV

        try:
            intS = {'a':0, 'b':1}[S.lower()] if S else 0
        except ValueError:
            vPrint( 'Quiet', debuggingThisModule, repr(S) ); halt # Need to finish handling S
        result = result * 10 + intS

        return result
    # end of BibleBooksCodes.BCVReferenceToInt


    def sortBCVReferences( self, referencesList ) -> List[Tuple[str,str,str]]:
        """
        Sort an iterable containing 3-tuples of BBB,C,V
            or 4-tuples of BBB,C,V,S
        """
        # dPrint( 'Quiet', debuggingThisModule, f"sortBCVReferences( ({len(referencesList)}) {referencesList} )…" )
        sortedList = sorted( referencesList, key=self.BCVReferenceToInt )
        # dPrint( 'Quiet', debuggingThisModule, f"  sortBCVReferences returning ({len(sortedList)}) {sortedList}" )
        # assert len(sortedList) == len(referencesList)
        return sortedList
    # end of BibleBooksCodes.sortBCVReferences


    # NOTE: The following functions are all not recommended (NR) because they rely on assumed information that may be incorrect
    #           i.e., they assume English language or European book order conventions
    #       They are included because they might be necessary for error messages or similar uses
    #           (where the precisely correct information is unknown)
    def getEnglishName_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns the first English name for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        return self.__DataDicts['referenceAbbreviationDict'][BBB]['nameEnglish'].split('/',1)[0].strip()
    # end of BibleBooksCodes.getEnglishName_NR

    def getEnglishNameList_NR( self, BBB:str ): # NR = not recommended (because not completely general/international)
        """
        Returns a list of possible English names for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        names = self.__DataDicts['referenceAbbreviationDict'][BBB]['nameEnglish']
        return [name.strip() for name in names.split('/')]
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
# end of BibleBooksCodes class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Demo the BibleBooksCodes object
    bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
    vPrint( 'Quiet', debuggingThisModule, bbc ) # Just print a summary
    vPrint( 'Quiet', debuggingThisModule, "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
    vPrint( 'Quiet', debuggingThisModule, "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
    vPrint( 'Quiet', debuggingThisModule, "Psalms has {} expected chapters".format(bbc.getMaxChapters("PSA")) )
    vPrint( 'Quiet', debuggingThisModule, "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
    vPrint( 'Quiet', debuggingThisModule, "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
    vPrint( 'Quiet', debuggingThisModule, "All BBBs:", len(bbc.getAllReferenceAbbreviations()), bbc.getAllReferenceAbbreviations() )
    vPrint( 'Quiet', debuggingThisModule, "All BBBs in a print sequence", len(bbc.getSequenceList()), bbc.getSequenceList() )
    myBBBs = ['GEN','EXO','PSA','ISA','MAL','MAT','REV','GLS']
    vPrint( 'Quiet', debuggingThisModule, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', debuggingThisModule, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    myBBBs = ['REV','CO2','GEN','PSA','CO1','ISA','SA2','MAT','GLS','JOB']
    vPrint( 'Quiet', debuggingThisModule, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', debuggingThisModule, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    vPrint( 'Quiet', debuggingThisModule, "USFM triples:", len(bbc.getAllUSFMBooksCodeNumberTriples()), bbc.getAllUSFMBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "USX triples:", len(bbc.getAllUSXBooksCodeNumberTriples()), bbc.getAllUSXBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "Bibledit triples:", len(bbc.getAllBibleditBooksCodeNumberTriples()), bbc.getAllBibleditBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "Single chapter books (and OSIS):\n  {}\n  {}".format( bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList() ) )
    vPrint( 'Quiet', debuggingThisModule, "Possible alternative  books to Esther: {}".format( bbc.getPossibleAlternativeBooksCodes('EST') ) )
    for something in ('PE2', '2Pe', '2 Pet', '2Pet', 'Job', ):
        vPrint( 'Quiet', debuggingThisModule, '{!r} -> {}'.format( something, bbc.getBBBFromText( something ) ) )
    myOSIS = ( 'Gen', '1Kgs', 'Ps', 'Mal', 'Matt', '2John', 'Rev', 'EpLao', '3Meq', )
    for osisCode in myOSIS:
        vPrint( 'Quiet', debuggingThisModule, "Osis {!r} -> {}".format( osisCode, bbc.getBBBFromOSISAbbreviation( osisCode ) ) )

    sections:Dict[str,List[str]] = {}
    for BBB in bbc:
        section = bbc.getTypicalSection( BBB )
        if section not in sections: sections[section] = []
        sections[section].append( BBB )
    vPrint( 'Quiet', debuggingThisModule, "\n{} book codes in {} sections".format( len(bbc), len(sections) ) )
    for section in sections: vPrint( 'Quiet', debuggingThisModule, "  {} section: {} {}".format( section, len(sections[section]), sections[section] ) )
# end of BibleBooksCodes.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Demo the BibleBooksCodes object
    bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
    vPrint( 'Quiet', debuggingThisModule, bbc ) # Just print a summary
    vPrint( 'Quiet', debuggingThisModule, "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
    vPrint( 'Quiet', debuggingThisModule, "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
    vPrint( 'Quiet', debuggingThisModule, "Psalms has {} expected chapters".format(bbc.getMaxChapters("PSA")) )
    vPrint( 'Quiet', debuggingThisModule, "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
    vPrint( 'Quiet', debuggingThisModule, "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
    vPrint( 'Quiet', debuggingThisModule, "All BBBs:", len(bbc.getAllReferenceAbbreviations()), bbc.getAllReferenceAbbreviations() )
    vPrint( 'Quiet', debuggingThisModule, "All BBBs in a print sequence", len(bbc.getSequenceList()), bbc.getSequenceList() )
    myBBBs = ['GEN','EXO','PSA','ISA','MAL','MAT','REV','GLS']
    vPrint( 'Quiet', debuggingThisModule, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', debuggingThisModule, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    myBBBs = ['REV','CO2','GEN','PSA','CO1','ISA','SA2','MAT','GLS','JOB']
    vPrint( 'Quiet', debuggingThisModule, "My BBBs in sequence", len(myBBBs), myBBBs, "now", len(bbc.getSequenceList(myBBBs)), bbc.getSequenceList(myBBBs) )
    for BBB in myBBBs:
        vPrint( 'Quiet', debuggingThisModule, "{} is typically in {} section".format( BBB, bbc.getTypicalSection( BBB ) ) )
    vPrint( 'Quiet', debuggingThisModule, "USFM triples:", len(bbc.getAllUSFMBooksCodeNumberTriples()), bbc.getAllUSFMBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "USX triples:", len(bbc.getAllUSXBooksCodeNumberTriples()), bbc.getAllUSXBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "Bibledit triples:", len(bbc.getAllBibleditBooksCodeNumberTriples()), bbc.getAllBibleditBooksCodeNumberTriples() )
    vPrint( 'Quiet', debuggingThisModule, "Single chapter books (and OSIS):\n  {}\n  {}".format( bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList() ) )
    vPrint( 'Quiet', debuggingThisModule, "Possible alternative  books to Esther: {}".format( bbc.getPossibleAlternativeBooksCodes('EST') ) )
    for something in ('PE2', '2Pe', '2 Pet', '2Pet', 'Job', ):
        vPrint( 'Quiet', debuggingThisModule, '{!r} -> {}'.format( something, bbc.getBBBFromText( something ) ) )
    myOSIS = ( 'Gen', '1Kgs', 'Ps', 'Mal', 'Matt', '2John', 'Rev', 'EpLao', '3Meq', )
    for osisCode in myOSIS:
        vPrint( 'Quiet', debuggingThisModule, "Osis {!r} -> {}".format( osisCode, bbc.getBBBFromOSISAbbreviation( osisCode ) ) )

    sections:Dict[str,List[str]] = {}
    for BBB in bbc:
        section = bbc.getTypicalSection( BBB )
        if section not in sections: sections[section] = []
        sections[section].append( BBB )
    vPrint( 'Quiet', debuggingThisModule, "\n{} book codes in {} sections".format( len(bbc), len(sections) ) )
    for section in sections: vPrint( 'Quiet', debuggingThisModule, "  {} section: {} {}".format( section, len(sections[section]), sections[section] ) )
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
