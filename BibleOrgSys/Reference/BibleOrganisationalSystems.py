#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleOrganisationalSystems.py
#
# Module handling BibleOrganisationalSystems
#
# Copyright (C) 2010-2022 Robert Hunt
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
Module handling BibleOrganisationalSystems.

BibleOrganisationalSystems class:
    __init__( self ) # We can't give this parameters because of the singleton
    loadData( self, XMLFileOrFilepath=None )
    __str__( self )
    __len__( self )
    getAvailableOrganisationalSystemNames( self, extended=False )
    getOrganisationalSystem( self, systemName, suppressErrors=False )
    getOrganisationalSystemValue( self, systemName, valueName, suppressErrors=False )

BibleOrganisationalSystem class:
        based on: BibleBookOrderSystem, BibleVersificationSystem, BiblePunctuationSystem, BibleBooksNamesSystem
    __init__( self, systemName )
    __str__( self )
    getOrganisationalSystemName( self )
    getOrganisationalSystemType( self )
    getMoreBasicTypes( self )
    getOrganisationalSystemValue( self, valueName )
    getBookList( self )
    containsBook( self, BBB )
    getFirstBookCode( self )
    getPreviousBookCode( self, BBB )
    getNextBookCode( self, BBB )
    getAlternativeBBBIfNecessary( self, BBB )
    getNumVersesList( self, BBB:str, allowAlternatives=False )
    isValidBCVRef( self, referenceTuple, referenceString, extended=False )
    __makeAbsoluteVerseList( self )
    getAbsoluteVerseNumber( self, BBB:str, C, V )
    convertAbsoluteVerseNumber( self, avNumber )
"""
import logging
import os

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Reference.BibleBookOrders import BibleBookOrderSystem
from BibleOrgSys.Reference.BiblePunctuationSystems import BiblePunctuationSystem
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
from BibleOrgSys.Reference.BibleBooksNames import BibleBooksNamesSystem
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
import bos_books_codes_py


LAST_MODIFIED_DATE = '2026-05-06' # by RJH
SHORT_PROGRAM_NAME = "BibleOrganisationalSystems"
PROGRAM_NAME = "Bible Organisation Systems handler"
PROGRAM_VERSION = '0.35'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



#@singleton # Can only ever have one instance (but doesn't work for multiprocessing
class BibleOrganisationalSystems:
    """
    Class for handling BibleOrganisationalSystems.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self ) -> None: # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__dataDict = self.__indexDict = self.__combinedIndexDict = None # We'll import into this in loadData
    # end of BibleOrganisationalSystems.__init__

    def loadData( self, XMLFileOrFilepath=None ):
        """ Loads the pickle or XML data file and imports it to dictionary format (if not done already). """
        result = None
        if not self.__dataDict or not self.__indexDict: # Don't do this unnecessarily
            if XMLFileOrFilepath is None:
                # See if we can load from the pickle file (faster than loading from the XML)
                standardXMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( "BibleOrganisationalSystems.xml" )
                standardPickleFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATAFILES_FOLDERPATH.joinpath( "BibleOrganisationalSystems_Tables.pickle" )
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
                        result = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    self.__dataDict, self.__indexDict, self.__combinedIndexDict = result
                    return self # So this command can be chained after the object creation
            # else: # We have to load the XML (much slower)
            from BibleOrgSys.Reference.Converters.BibleOrganisationalSystemsConverter import BibleOrganisationalSystemsConverter
            if XMLFileOrFilepath is not None: logging.warning( f"Bible organisational systems are already loaded -- your given filepath of {XMLFileOrFilepath!r} was ignored" )
            bosc = BibleOrganisationalSystemsConverter()
            bosc.loadAndValidate( XMLFileOrFilepath ) # Load the XML (if not done already)
            result = bosc.importDataToPython() # Get the various dictionaries organised for quick lookup
        if result is not None:
            self.__dataDict, self.__indexDict, self.__combinedIndexDict = result
        return self # So this command can be chained after the object creation
    # end of BibleOrganisationalSystems.loadData


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible organisational system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleOrganisationalSystems object"
        result += ('\n' if result else '') + f"  Number of entries = {len(self.__dataDict)}"
        if BibleOrgSysGlobals.verbosityLevel > 1: # Do a bit of extra analysis
            counters = {}
            for possibleType in BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES: counters[possibleType] = 0
            for systemName, data in self.__dataDict.items():
                counters[data["type"]] += 1
            for possibleType in BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES:
                if counters[possibleType]: result += f"    {counters[possibleType]} {possibleType}(s)"
        return result
    # end of BibleOrganisationalSystems.__str__


    def __len__( self ):
        """
        Return the number of loaded systems.
        """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '1', len(self.__dataDict) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '2', len(self.__indexDict) )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '3', len(self.__combinedIndexDict) )
        return len( self.__dataDict )
    # end of BibleOrganisationalSystems.__len__


    def getAvailableOrganisationalSystemNames( self, extended=False ):
        """
        Returns a list of available system name strings.
        """
        if extended:
            result = []
            for x in self.__indexDict:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "sdf", x, self.__indexDict[x], self.__dataDict[self.__indexDict[x][0]] )
                result.append( f"{x} ({self.__dataDict[self.__indexDict[x][0]]['type']})" )
            return result
        # else:
        return [x for x in self.__indexDict]
    # end of BibleOrganisationalSystems.getAvailableOrganisationalSystemNames


    def getOrganisationalSystem( self, systemName, suppressErrors=False ):
        """
        Accepts combined names (like KJV-1611_edition) or basic names (like KJV-1611).

        Returns the system dictionary.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"getOrganisationalSystem( {repr(systemName)} )" )
        assert systemName
        assert isinstance( systemName, str )

        #for x in sorted(self.__dataDict): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "dD", repr(x) )
        if systemName in self.__dataDict: # we found the combined name
            return self.__dataDict[systemName]
        # else
        #for x in sorted(self.__indexDict): vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "iD", repr(x) )
        if systemName in self.__indexDict:
            index = self.__indexDict[systemName]
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'systemName', systemName, index )
            if len(index) == 1: # Must only be one (unique) entry
                return self.__dataDict[ index[0] ]
            # else it's an ambiguous name that has multiple matches
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'here' )
            for possibleType in BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES: # Steps through in priority order
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, possibleType )
                x = systemName + '_' + possibleType
                if x in self.__dataDict: return self.__dataDict[x]
        # else
        if not suppressErrors:
            logging.error( f"No {systemName!r} system in Bible Organisational Systems" )
            if BibleOrgSysGlobals.verbosityLevel>2: logging.error( f"Available systems are {self.getAvailableOrganisationalSystemNames( extended=True )}" )
    # end of BibleOrganisationalSystems.getOrganisationalSystem


    def getOrganisationalSystemValue( self, systemName, valueName, suppressErrors=False ):
        """
        Gets a value for the system.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"getOrganisationalSystemValue( {repr(systemName)}, {repr(valueName)} )" )
        assert systemName and isinstance( systemName, str )
        assert valueName and isinstance( valueName, str )
        thisSystem = self.getOrganisationalSystem( systemName, suppressErrors )
        #if systemName=='KJV-1611': vPrint( 'Quiet', DEBUGGING_THIS_MODULE, thisSystem ); assert False, "We want to stop here"
        if thisSystem is not None:
            assert thisSystem
            if valueName in thisSystem: return thisSystem[valueName]
            # else maybe we can find the value in a derived text
            if 'usesText' in thisSystem:
                trySystemNames = thisSystem['usesText']
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemNames is {repr(trySystemNames)}" )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "w1", f"{systemName} is trying usesText of {trySystemName}" )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nKeys:", self.__dataDict.keys() )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nindexDict", self.__indexDict )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\ncombinedIndexDict", self.__combinedIndexDict )
                assert isinstance( trySystemNames, list ) # Maybe this can also be a string???
                for possibleType in reversed( BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, 'possibleType', possibleType )
                    for trySystemName in trySystemNames:
                        if trySystemName == systemName: # Avoid infinite recursion
                            trySystemName += '_' + possibleType
                        result = self.getOrganisationalSystemValue( trySystemName, valueName, suppressErrors=True )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName result is {repr(result)}" ); assert False, "We want to stop here"
                        if result is not None: return result
            # else we couldn't find it anywhere
            logging.error( f"{systemName} Bible Organisational System has no {valueName} specified (a)" )
    # end of BibleOrganisationalSystems.getOrganisationalSystemValue
# end of BibleOrganisationalSystems class



class BibleOrganisationalSystem( BibleBookOrderSystem, BibleVersificationSystem, BiblePunctuationSystem, BibleBooksNamesSystem ):
    """
    Class for handling a BibleOrganisationalSystem.

    It is based on a number of system classes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self, systemName ) -> None:
        """
        Constructor:
        """
        def getOrganisationalSystemValue( valueName ):
            """ Gets a value for the system. """
            def getMoreBasicTypes():
                """ Returns a list of more basic (original) types. """
                ix = BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES.index( self.__dataDict["type"] )
                return BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES[ix+1:]
            # end of getMoreBasicTypes

            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q0", valueName )
            if valueName in self.__dataDict: return self.__dataDict[valueName]
            # else maybe we can find the value in a derived text
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q1", self.getOrganisationalSystemName() )
            for tryType in getMoreBasicTypes():
                if 'usesText' in self.__dataDict:
                    for trySystemName in self.__dataDict['usesText']:
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q2", f"{self.__systemName} is trying usesText of {trySystemName}" )
                        result = self.__boss.getOrganisationalSystemValue( trySystemName, valueName )
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  result is", result )
                        if result is not None: return result
                if 'derivedFrom' in self.__dataDict:
                    trySystemName = self.__dataDict['derivedFrom']
                    if isinstance( trySystemName, str ):
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'derivedFrom' is a string: {trySystemName!r}" )
                    elif isinstance( trySystemName, list ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'derivedFrom' is a list: {trySystemName!r}" )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q3", f"{self.__systemName} is trying derivedFrom of {trySystemName}" )
                    result = self.__boss.getOrganisationalSystemValue( trySystemName, valueName )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  result is", result )
                    if result is not None: return result
            # else we couldn't find it anywhere
            logging.error( f"{self.__systemName} Bible Organisational System has no {valueName} specified (b)" )
        # end of getOrganisationalSystemValue

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading {systemName!r} system" )
        assert systemName and isinstance( systemName, str )
        self.__boss = BibleOrganisationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        result = self.__boss.getOrganisationalSystem( systemName )
        if result is None:
            logging.critical( f"No {systemName!r} system in Bible Organisational Systems" )
            self.__dataDict = self.__systemName = None
            del self
            return

        # else:
        self.__dataDict = result
        self.__systemName = systemName
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.__dataDict )

        # Now initialize the inherited classes
        bookOrderSystemName = self.getOrganisationalSystemValue( 'bookOrderSystem' )
        versificationSystemName = self.getOrganisationalSystemValue( 'versificationSystem' )
        punctuationSystemName = self.getOrganisationalSystemValue( 'punctuationSystem' )
        booksNamesSystemName = self.getOrganisationalSystemValue( 'booksNamesSystem' )
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Got organisation bits: BOS={bookOrderSystemName}, VS={versificationSystemName}, PS={punctuationSystemName}, BNS={booksNamesSystemName}" )
        if bookOrderSystemName and bookOrderSystemName!='None' and bookOrderSystemName!='Unknown':
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Uses {bookOrderSystemName!r} book order system" )
            BibleBookOrderSystem.__init__( self, bookOrderSystemName )
        if versificationSystemName and versificationSystemName!='None' and versificationSystemName!='Unknown':
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Uses {versificationSystemName!r} versification system" )
            BibleVersificationSystem.__init__( self, versificationSystemName )
        if punctuationSystemName and punctuationSystemName!='None' and punctuationSystemName!='Unknown':
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Uses {punctuationSystemName!r} punctuation system" )
            BiblePunctuationSystem.__init__( self, punctuationSystemName )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown':
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Uses {booksNamesSystemName!r} books name system" )
            BibleBooksNamesSystem.__init__( self, booksNamesSystemName, getOrganisationalSystemValue( 'includesBooks' ) ) # Does one extra step To create the input abbreviations

        # Do some cross-checking
        myBooks = getOrganisationalSystemValue( 'includesBooks' )
        if myBooks is not None:
            for BBB in myBooks:
                if not BibleBookOrderSystem.containsBook( self, BBB ):
                    logging.error( f"Book {BBB!r} is included in {self.__systemName} system but missing from {BibleBookOrderSystem.getBookOrderSystemName( self )} book order system" )
    # end of BibleOrganisationalSystem.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible organisational system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleOrganisationalSystem object"
        if self.__systemName is not None: result += ('\n' if result else '') + f"  {self.__systemName} Bible organisational system"
        if self.__dataDict is not None:
            result += ('\n' if result else '') + f'  Type = {self.__dataDict["type"]}'
            result += ('\n' if result else '') + f'  Name(s) = {self.__dataDict["name"]}'
            result += ('\n' if result else '') + f"  Number of entry lines = {len(self.__dataDict)}"
            if BibleOrgSysGlobals.verbosityLevel > 3: result += ('\n' if result else '') + f"  Entries are: {self.__dataDict}"
        return result
    # end of BibleOrganisationalSystem.__str__


    def getOrganisationalSystemName( self ):
        """ Return the system name. """
        assert self.__systemName
        return self.__systemName
    # end of BibleOrganisationalSystem.getOrganisationalSystemName


    def getOrganisationalSystemType( self ):
        """ Return the system type. """
        assert self.__dataDict
        return self.__dataDict["type"]
    # end of BibleOrganisationalSystem.getOrganisationalSystemType


    def getMoreBasicTypes( self ):
        """ Returns a list of more basic (original) types. """
        ix = BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES.index( self.__dataDict["type"] )
        return BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES[ix+1:]
    # end of BibleOrganisationalSystem.getMoreBasicTypes


    def getOrganisationalSystemValue( self, valueName ):
        """ Gets a value for the system. """
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"getOrganisationalSystemValue( {repr(valueName)} )" )
        assert self.__dataDict
        assert valueName and isinstance( valueName, str )

        if valueName in self.__dataDict: return self.__dataDict[valueName]
        # else maybe we can find the value in a derived text
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q0", self.getOrganisationalSystemName() )
        for tryType in self.getMoreBasicTypes():
            if 'usesText' in self.__dataDict:
                for trySystemName in self.__dataDict['usesText']:
                    if isinstance( trySystemName, str ):
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'usesText' is a string: {trySystemName!r}" )
                    elif isinstance( trySystemName, list ):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'usesText' is a list: {trySystemName!r}" )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q1", f"{self.__systemName} is trying usesText of {trySystemName}" )
                    result = self.__boss.getOrganisationalSystemValue( trySystemName, valueName )
                    if result is not None: return result
            if 'derivedFrom' in self.__dataDict:
                trySystemName = self.__dataDict['derivedFrom']
                if isinstance( trySystemName, str ):
                    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'derivedFrom' is a string: {trySystemName!r}" )
                elif isinstance( trySystemName, list ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"trySystemName for 'derivedFrom' is a list: {trySystemName!r}" )
                    trySystemName = trySystemName[0] # Take the first string from the list
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "q2", f"{self.__systemName} is trying derivedFrom of {trySystemName}" )
                result = self.__boss.getOrganisationalSystemValue( trySystemName, valueName )
                if result is not None: return result
        # else we couldn't find it anywhere
        logging.error( f"{self.getOrganisationalSystemName()} Bible Organisational System has no {valueName} specified (c)" )
    # end of BibleOrganisationalSystem.getOrganisationalSystemValue


    def getBookList( self ):
        """
        Returns the list of book reference codes (BBB) for books in this system.
        Returns an empty list if there's no known books.
        """
        result = self.getOrganisationalSystemValue( 'includesBooks' )
        if result is None: return []
        else: return result
    # end of BibleOrganisationalSystem.getBookList


    def containsBook( self, BBB:str ):
        """
        Returns True or False if this book is in this system.
        """
        assert BBB and isinstance( BBB, str ) and len(BBB)==3
        return BBB in self.getBookList()
    # end of BibleOrganisationalSystem.containsBook


    def getFirstBookCode( self ):
        """
        Return the BBB code for the first book
            otherwise returns None.
        """
        if 1: return BibleBookOrderSystem.getBookAtOrderPosition( self, 1 )
        else: # I think this is wrong! Should use BookOrderSystem -- see next function
            bookList = self.getOrganisationalSystemValue( 'includesBooks' )
            if bookList is None: return None
            return bookList[0]
    # end of BibleOrganisationalSystem.getFirstBookCode


    def getPreviousBookCode( self, BBB:str ):
        """
        Returns the book (if any) before the given one.
        """
        while True:
            previousCode = BibleBookOrderSystem.getPreviousBookCode( self, BBB )
            if previousCode is None: return None
            if self.containsBook( previousCode ): return previousCode
            BBB = previousCode
    # end of BibleOrganisationalSystem.getNextBookCode


    def getNextBookCode( self, BBB:str ):
        """ Returns the book (if any) after the given one. """
        while True:
            nextCode = BibleBookOrderSystem.getNextBookCode( self, BBB )
            if nextCode is None: return None
            if self.containsBook( nextCode ): return nextCode
            BBB = nextCode
    # end of BibleOrganisationalSystem.getNextBookCode


    def getAlternativeBBBIfNecessary( self, BBB:str ):
        """
        If BBB is not in this BOS, try to return an alternative that is.

        If none, return None.
        """
        if self.containsBook( BBB ): return BBB
        # else
        # temp …. needs a try/except
        return bos_books_codes_py.get_possible_alternative_books( BBB )[0]
    # end of BibleOrganisationalSystem.getAlternativeBBBIfNecessary


    def getNumVersesList( self, BBB:str, allowAlternatives=False ):
        """
        Returns a list containing an integer for each chapter indicating the number of verses.

        The length of the list is the number of chapters in the book.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"getNumVersesList( {BBB} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert len(BBB) == 3

        if not allowAlternatives: return BibleVersificationSystem.getNumVersesList( self, BBB )

        # Well, we are allowed alternatives, but try the given BBB first anyway
        bookVersesList = None
        try: bookVersesList = BibleVersificationSystem.getNumVersesList( self, BBB )
        except KeyError: # BBB doesn't exist in this BOS -- try an alternative
            # Next line will raise an error if no alternatives (coz returns None)
            for altBBB in bos_books_codes_py.get_possible_alternative_books( BBB ):
                try: bookVersesList = BibleVersificationSystem.getNumVersesList( self, altBBB ); break
                except KeyError: continue # BBB doesn't exist in this BOS -- try an alternative
            if bookVersesList is not None:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Changed {BBB} to {altBBB} in {BibleVersificationSystem.getVersificationSystemName( self )!r} versification scheme" )
        return bookVersesList
    # end of BibleOrganisationalSystem.getNumVersesList


    def isValidBCVRef( self, referenceTuple, referenceString, extended=False ):
        """
        Returns True/False indicating if the given reference is valid in this system.
        Extended flag allows chapter and verse numbers of zero.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"isValidBCVRef( {referenceTuple}, {referenceString}, {extended} )" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            assert isinstance( referenceTuple, str ) or isinstance( referenceTuple, SimpleVerseKey )
        if isinstance( referenceTuple, SimpleVerseKey ): referenceTuple = referenceTuple.getBCVS()

        BBB, C, V, S = referenceTuple
        if BBB is None or not BBB: return False
        assert len(BBB) == 3
        if C and not C.isdigit() and C!='-1': # Should be no suffix on C (although it can be blank if the reference is for a whole book)
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"BibleOrganisationalSystem.isValidBCVRef( {referenceTuple}, {referenceString}, {extended} ) expected C to be digits" )
        assert not V or V.isdigit() # Should be no suffix on V (although it can be blank if the reference is for a whole chapter)
        assert not S or len(S)==1 and S.isalpha() # Suffix should be only one lower-case letter if anything
        if BBB and BibleBookOrderSystem.containsBook( self, BBB ):
            return BibleVersificationSystem.isValidBCVRef( self, referenceTuple, referenceString, extended=extended )
        logging.error( f"{BBB} {C}:{V} is invalid book for reference {referenceString!r} in {self.getBookOrderSystemName()} versification system for {self.getOrganisationalSystemName()}" )
        return False
    # end of BibleOrganisationalSystem.isValidBCVRef


    __absoluteVerseDict = {}
    def __makeAbsoluteVerseList( self ):
        """
        Make up a list of four-tuples containing
            BBB, chapterNumber, firstVerseNumber, lastVerseNumber
        """
        accumulatedCount = 0
        for BBB in self.getBookList():
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, BibleVersificationSystem.getNumVersesList( self, BBB ) )
            for j,numVerses in enumerate( BibleVersificationSystem.getNumVersesList( self, BBB ) ):
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, j, numVerses )
                BibleOrganisationalSystem.__absoluteVerseDict[(BBB,j+1)] = (accumulatedCount+1,accumulatedCount+numVerses)
                accumulatedCount += numVerses
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BibleOrganisationalSystem.__absoluteVerseDict )
    # end of BibleOrganisationalSystem.__makeAbsoluteVerseList


    def getAbsoluteVerseNumber( self, BBB:str, C:str, V ):
        """
        Convert the given reference (in this versification system)
            to an absolute verse number.

        Returns an integer in the range 1..31,102 (for KJV).

        Returns None for invalid or missing values.
        """
        C, V = int(C), int(V)
        if not BibleOrganisationalSystem.__absoluteVerseDict: self.__makeAbsoluteVerseList()
        rangeStart, rangeEnd = BibleOrganisationalSystem.__absoluteVerseDict[ (BBB,C) ]
        if 1 <= V <= rangeEnd-rangeStart+1:
            return rangeStart + V - 1
    # end of BibleOrganisationalSystem.getAbsoluteVerseNumber


    def convertAbsoluteVerseNumber( self, avNumber ):
        """
        Convert the given absolute verse number (in this versification system)
            to the reference versification.

        Returns a new BBB, C, V.

        Returns None for invalid or missing values.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: assert 1 <= avNumber <= 99999
        if not BibleOrganisationalSystem.__absoluteVerseDict: self.__makeAbsoluteVerseList()
        for (BBB,C),(rangeStart, rangeEnd) in BibleOrganisationalSystem.__absoluteVerseDict.items():
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, C, rangeStart, rangeEnd )
            if rangeStart <= avNumber <= rangeEnd:
                return BBB, str(C), str(avNumber - rangeStart + 1)
    # end of BibleOrganisationalSystem.convertAbsoluteVerseNumber
# end of BibleOrganisationalSystem class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Demo the BibleOrganisationalSystems object
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting load of ALL Bible organisational systems…" )
        boss = BibleOrganisationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, boss ) # Just print a summary
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Available system names are: {boss.getAvailableOrganisationalSystemNames()}" )

    if 1: # Demo a BibleOrganisationalSystem object -- this is the one most likely to be wanted by a user
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting varying Bible organisational systems…" )
        for testString in ( 'NIV', 'KJV-1611_edition', 'KJV-1638', ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying: {testString!r}" )
            bos = BibleOrganisationalSystem( testString )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, 'bos', bos ) # Just print a summary
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "First book", bos.getFirstBookCode() )
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Book order list ({len(bos.getBookOrderList())} entries) is {bos.getBookOrderList()}" )
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Book list ({len(bos.getBookList())} entries) is {bos.getBookList()}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"This type is {bos.getOrganisationalSystemType()}. More basic types are: {bos.getMoreBasicTypes()}" )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','JDE', 'TOB', ):
            #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Contains {test!r}: {bos.containsBook(test)}" )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','Jde', 'Ma1', ):
            #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{test!r} gives {bos.getBBBFromText(test)}" )

    if 1:
        version = 'KJV-1769_edition'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting absolute verse numbers for", version )
        bos = BibleOrganisationalSystem( version )
        for myRef in (('GEN','1','0'), ('GEN','1','1'), ('GEN','1','2'), ('GEN','2','1'), ('MAT','1','1'), ('CO1','2','3'), ('REV','22','21'), ('REV','22','32'), ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' ', myRef, '->', bos.getAbsoluteVerseNumber( myRef[0], myRef[1], myRef[2] ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for myNum in ( 1, 2, 3, 123, 23145, 23146, 31101, 31102, 31103 ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' ', myNum, '->', bos.convertAbsoluteVerseNumber( myNum ) )
# end of BibleOrganisationalSystem.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if 1: # Demo the BibleOrganisationalSystems object
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting load of ALL Bible organisational systems…" )
        boss = BibleOrganisationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, boss ) # Just print a summary
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Available system names are: {boss.getAvailableOrganisationalSystemNames()}" )

    if 1: # Demo a BibleOrganisationalSystem object -- this is the one most likely to be wanted by a user
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting varying Bible organisational systems…" )
        for testString in ( 'NIV', 'KJV-1611_edition', 'KJV-1638', ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying: {testString!r}" )
            bos = BibleOrganisationalSystem( testString )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, 'bos', bos ) # Just print a summary
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "First book", bos.getFirstBookCode() )
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Book order list ({len(bos.getBookOrderList())} entries) is {bos.getBookOrderList()}" )
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Book list ({len(bos.getBookList())} entries) is {bos.getBookList()}" )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"This type is {bos.getOrganisationalSystemType()}. More basic types are: {bos.getMoreBasicTypes()}" )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','JDE', 'TOB', ):
            #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Contains {test!r}: {bos.containsBook(test)}" )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','Jde', 'Ma1', ):
            #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{test!r} gives {bos.getBBBFromText(test)}" )

    if 1:
        version = 'KJV-1769_edition'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTesting absolute verse numbers for", version )
        bos = BibleOrganisationalSystem( version )
        for myRef in (('GEN','1','0'), ('GEN','1','1'), ('GEN','1','2'), ('GEN','2','1'), ('MAT','1','1'), ('CO1','2','3'), ('REV','22','21'), ('REV','22','32'), ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' ', myRef, '->', bos.getAbsoluteVerseNumber( myRef[0], myRef[1], myRef[2] ) )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
        for myNum in ( 1, 2, 3, 123, 23145, 23146, 31101, 31102, 31103 ):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, ' ', myNum, '->', bos.convertAbsoluteVerseNumber( myNum ) )
# end of BibleOrganisationalSystem.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleOrganisationalSystems.py
