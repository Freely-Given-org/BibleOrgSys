#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleOrganizationalSystems.py
#
# Module handling BibleOrganizationalSystems
#
# Copyright (C) 2010-2016 Robert Hunt
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
Module handling BibleOrganizationalSystems.

BibleOrganizationalSystems class:
    __init__( self ) # We can't give this parameters because of the singleton
    loadData( self, XMLFilepath=None )
    __str__( self )
    __len__( self )
    getAvailableOrganizationalSystemNames( self, extended=False )
    getOrganizationalSystem( self, systemName, suppressErrors=False )
    getOrganizationalSystemValue( self, systemName, valueName, suppressErrors=False )

BibleOrganizationalSystem class:
    __init__( self, systemName )
    __str__( self )
    getOrganizationalSystemName( self )
    getOrganizationalSystemType( self )
    getMoreBasicTypes( self )
    getOrganizationalSystemValue( self, valueName )
    getBookList( self )
    containsBook( self, BBB )
    getFirstBookCode( self )
    getPreviousBookCode( self, BBB )
    getNextBookCode( self, BBB )
    isValidBCVRef( self, referenceTuple, referenceString, extended=False )
    __makeAbsoluteVerseList( self )
    getAbsoluteVerseNumber( self, BBB, C, V )
    convertAbsoluteVerseNumber( self, avNumber )
"""

from gettext import gettext as _

LastModifiedDate = '2016-02-13' # by RJH
ShortProgName = "BibleOrganizationalSystems"
ProgName = "Bible Organization Systems handler"
ProgVersion = '0.31'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os
from collections import OrderedDict
#from singleton import singleton

import BibleOrgSysGlobals
from BibleOrganizationalSystemsConverter import BibleOrganizationalSystemsConverter, allowedTypes
from BibleBookOrders import BibleBookOrderSystem
from BiblePunctuationSystems import BiblePunctuationSystem
from BibleVersificationSystems import BibleVersificationSystem
from BibleBooksNames import BibleBooksNamesSystem
from VerseReferences import SimpleVerseKey



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', _(errorBit) )
# end of exp



#@singleton # Can only ever have one instance (but doesn't work for multiprocessing
class BibleOrganizationalSystems:
    """
    Class for handling BibleOrganizationalSystems.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__dataDict = self.__indexDict = self.__combinedIndexDict = None # We'll import into this in loadData
    # end of BibleOrganizationalSystems.__init__

    def loadData( self, XMLFilepath=None ):
        """ Loads the pickle or XML data file and imports it to dictionary format (if not done already). """
        result = None
        if not self.__dataDict or not self.__indexDict: # Don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            dataFilepath = os.path.join( os.path.dirname(__file__), "DataFiles/" )
            standardXMLFilepath = os.path.join( dataFilepath, "BibleOrganizationalSystems.xml" )
            standardPickleFilepath = os.path.join( dataFilepath, "DerivedFiles", "BibleOrganizationalSystems_Tables.pickle" )
            if XMLFilepath is None \
            and os.access( standardPickleFilepath, os.R_OK ) \
            and os.stat(standardPickleFilepath)[8] > os.stat(standardXMLFilepath)[8] \
            and os.stat(standardPickleFilepath)[9] > os.stat(standardXMLFilepath)[9]: # There's a newer pickle file
                import pickle
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}...".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    result = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            else: # We have to load the XML (much slower)
                from BibleOrganizationalSystemsConverter import BibleOrganizationalSystemsConverter
                if XMLFilepath is not None: logging.warning( _("Bible organisational systems are already loaded -- your given filepath of {!r} was ignored").format(XMLFilepath) )
                bosc = BibleOrganizationalSystemsConverter()
                bosc.loadAndValidate( XMLFilepath ) # Load the XML (if not done already)
                result = bosc.importDataToPython() # Get the various dictionaries organised for quick lookup
        if result is not None:
            self.__dataDict, self.__indexDict, self.__combinedIndexDict = result
        return self
    # end of BibleOrganizationalSystems.loadData


    def __str__( self ):
        """
        This method returns the string representation of a Bible organisational system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleOrganizationalSystems object"
        result += ('\n' if result else '') + "  Number of entries = {}".format( len(self.__dataDict) )
        if BibleOrgSysGlobals.verbosityLevel > 1: # Do a bit of extra analysis
            counters = {}
            for possibleType in allowedTypes: counters[possibleType] = 0
            for systemName, data in self.__dataDict.items():
                counters[data["type"]] += 1
            for possibleType in allowedTypes:
                if counters[possibleType]: result += "    {} {}(s)".format( counters[possibleType], possibleType )
        return result
    # end of BibleOrganizationalSystems.__str__


    def __len__( self ):
        """
        Return the number of loaded systems.
        """
        #print( '1', len(self.__dataDict) )
        #print( '2', len(self.__indexDict) )
        #print( '3', len(self.__combinedIndexDict) )
        return len( self.__dataDict )
    # end of BibleOrganizationalSystems.__len__


    def getAvailableOrganizationalSystemNames( self, extended=False ):
        """
        Returns a list of available system name strings.
        """
        if extended:
            result = []
            for x in self.__indexDict:
                print( "sdf", x, self.__indexDict[x], self.__dataDict[self.__indexDict[x][0]] )
                result.append( "{} ({})".format(x, self.__dataDict[self.__indexDict[x][0]]['type'] ) )
            return result
        # else:
        return [x for x in self.__indexDict]
    # end of BibleOrganizationalSystems.getAvailableOrganizationalSystemNames


    def getOrganizationalSystem( self, systemName, suppressErrors=False ):
        """
        Accepts combined names (like KJV-1611_edition) or basic names (like KJV-1611).

        Returns the system dictionary.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "getOrganizationalSystem( {} )".format( repr(systemName) ) )
        assert systemName
        assert isinstance( systemName, str )

        #for x in sorted(self.__dataDict): print( "dD", repr(x) )
        if systemName in self.__dataDict: # we found the combined name
            return self.__dataDict[systemName]
        # else
        #for x in sorted(self.__indexDict): print( "iD", repr(x) )
        if systemName in self.__indexDict:
            index = self.__indexDict[systemName]
            #print( 'systemName', systemName, index )
            if len(index) == 1: # Must only be one (unique) entry
                return self.__dataDict[ index[0] ]
            # else it's an ambiguous name that has multiple matches
            #print( 'here' )
            for possibleType in allowedTypes: # Steps through in priority order
                #print( possibleType )
                x = systemName + '_' + possibleType
                if x in self.__dataDict: return self.__dataDict[x]
        # else
        if not suppressErrors:
            logging.error( _("No {!r} system in Bible Organisational Systems").format( systemName ) )
            if BibleOrgSysGlobals.verbosityLevel>2: logging.error( _("Available systems are {}").format( self.getAvailableOrganizationalSystemNames( extended=True ) ) )
    # end of BibleOrganizationalSystems.getOrganizationalSystem


    def getOrganizationalSystemValue( self, systemName, valueName, suppressErrors=False ):
        """
        Gets a value for the system.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "getOrganizationalSystemValue( {}, {} )".format( repr(systemName), repr(valueName) ) )
        assert systemName and isinstance( systemName, str )
        assert valueName and isinstance( valueName, str )
        thisSystem = self.getOrganizationalSystem( systemName, suppressErrors )
        #if systemName=='KJV-1611': print( thisSystem ); halt
        if thisSystem is not None:
            assert thisSystem
            if valueName in thisSystem: return thisSystem[valueName]
            # else maybe we can find the value in a derived text
            if 'usesText' in thisSystem:
                trySystemNames = thisSystem['usesText']
                #print( "trySystemNames is {}".format( repr(trySystemNames) ) )
                #print( "w1", "{} is trying usesText of {}".format(systemName,trySystemName) )
                #print( "\nKeys:", self.__dataDict.keys() )
                #print( "\nindexDict", self.__indexDict )
                #print( "\ncombinedIndexDict", self.__combinedIndexDict )
                assert isinstance( trySystemNames, list ) # Maybe this can also be a string???
                for possibleType in reversed( allowedTypes ):
                    #print( 'possibleType', possibleType )
                    for trySystemName in trySystemNames:
                        if trySystemName == systemName: # Avoid infinite recursion
                            trySystemName += '_' + possibleType
                        result = self.getOrganizationalSystemValue( trySystemName, valueName, suppressErrors=True )
                        #print( "trySystemName result is {}".format( repr(result) ) ); halt
                        if result is not None: return result
            # else we couldn't find it anywhere
            logging.error( _("{} Bible Organizational System has no {} specified (a)").format( systemName, valueName ) )
    # end of BibleOrganizationalSystems.getOrganizationalSystemValue
# end of BibleOrganizationalSystems class



class BibleOrganizationalSystem( BibleBookOrderSystem, BibleVersificationSystem, BiblePunctuationSystem, BibleBooksNamesSystem ):
    """
    Class for handling a BibleOrganizationalSystem.

    It is based on a number of system classes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self, systemName ):
        """
        Constructor:
        """
        def getOrganizationalSystemValue( valueName ):
            """ Gets a value for the system. """
            def getMoreBasicTypes():
                """ Returns a list of more basic (original) types. """
                ix = allowedTypes.index( self.__dataDict["type"] )
                return allowedTypes[ix+1:]
            # end of getMoreBasicTypes

            #print( "q0", valueName )
            if valueName in self.__dataDict: return self.__dataDict[valueName]
            # else maybe we can find the value in a derived text
            #print( "q1", self.getOrganizationalSystemName() )
            for tryType in getMoreBasicTypes():
                if 'usesText' in self.__dataDict:
                    for trySystemName in self.__dataDict['usesText']:
                        #print( "q2", "{} is trying usesText of {}".format(self.__systemName,trySystemName) )
                        result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                        #print( "  result is", result )
                        if result is not None: return result
                if 'derivedFrom' in self.__dataDict:
                    trySystemName = self.__dataDict['derivedFrom']
                    if isinstance( trySystemName, str ):
                        if BibleOrgSysGlobals.debugFlag: print( "trySystemName for 'derivedFrom' is a string: {!r}".format( trySystemName ) )
                    elif isinstance( trySystemName, list ):
                        #print( "trySystemName for 'derivedFrom' is a list: {!r}".format( trySystemName ) )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #print( "q3", "{} is trying derivedFrom of {}".format(self.__systemName,trySystemName) )
                    result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                    #print( "  result is", result )
                    if result is not None: return result
            # else we couldn't find it anywhere
            logging.error( _("{} Bible Organizational System has no {} specified (b)").format(self.__systemName,valueName) )
        # end of getOrganizationalSystemValue

        if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading {!r} system".format( systemName ) )
        assert systemName and isinstance( systemName, str )
        self.__boss = BibleOrganizationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        result = self.__boss.getOrganizationalSystem( systemName )
        if result is None:
            self.__dataDict = self.__systemName = None
            del self
            return

        # else:
        self.__dataDict = result
        self.__systemName = systemName
        #print( self.__dataDict )

        # Now initialize the inherited classes
        bookOrderSystemName = self.getOrganizationalSystemValue( 'bookOrderSystem' )
        versificationSystemName = self.getOrganizationalSystemValue( 'versificationSystem' )
        punctuationSystemName = self.getOrganizationalSystemValue( 'punctuationSystem' )
        booksNamesSystemName = self.getOrganizationalSystemValue( 'booksNamesSystem' )
        if BibleOrgSysGlobals.debugFlag: print( "Got organisation bits: BOS={}, VS={}, PS={}, BNS={}".format( bookOrderSystemName, versificationSystemName, punctuationSystemName, booksNamesSystemName ) )
        if bookOrderSystemName and bookOrderSystemName!='None' and bookOrderSystemName!='Unknown':
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Uses {!r} book order system".format( bookOrderSystemName ) )
            BibleBookOrderSystem.__init__( self, bookOrderSystemName )
        if versificationSystemName and versificationSystemName!='None' and versificationSystemName!='Unknown':
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Uses {!r} versification system".format( versificationSystemName ) )
            BibleVersificationSystem.__init__( self, versificationSystemName )
        if punctuationSystemName and punctuationSystemName!='None' and punctuationSystemName!='Unknown':
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Uses {!r} punctuation system".format( punctuationSystemName ) )
            BiblePunctuationSystem.__init__( self, punctuationSystemName )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown':
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Uses {!r} books name system".format( booksNamesSystemName ) )
            BibleBooksNamesSystem.__init__( self, booksNamesSystemName, getOrganizationalSystemValue( "includesBooks" ) ) # Does one extra step To create the input abbreviations

        # Do some cross-checking
        myBooks = getOrganizationalSystemValue( "includesBooks" )
        if myBooks is not None:
            for BBB in myBooks:
                if not BibleBookOrderSystem.containsBook( self, BBB ):
                    logging.error( _("Book {!r} is included in {} system but missing from {} book order system").format( BBB, self.__systemName, BibleBookOrderSystem.getBookOrderSystemName( self ) ) )
    # end of BibleOrganizationalSystem.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible organisational system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleOrganizationalSystem object"
        if self.__systemName is not None: result += ('\n' if result else '') + "  {} Bible organisational system".format( self.__systemName )
        if self.__dataDict is not None:
            result += ('\n' if result else '') + "  Type = {}".format( self.__dataDict["type"] )
            result += ('\n' if result else '') + "  Name(s) = {}".format( self.__dataDict["name"] )
            result += ('\n' if result else '') + "  Number of entry lines = {}".format( len(self.__dataDict) )
            if BibleOrgSysGlobals.verbosityLevel > 3: result += ('\n' if result else '') + "  Entries are: {}".format( self.__dataDict )
        return result
    # end of BibleOrganizationalSystem.__str__


    def getOrganizationalSystemName( self ):
        """ Return the system name. """
        assert self.__systemName
        return self.__systemName
    # end of BibleOrganizationalSystem.getOrganizationalSystemName


    def getOrganizationalSystemType( self ):
        """ Return the system type. """
        assert self.__dataDict
        return self.__dataDict["type"]
    # end of BibleOrganizationalSystem.getOrganizationalSystemType


    def getMoreBasicTypes( self ):
        """ Returns a list of more basic (original) types. """
        ix = allowedTypes.index( self.__dataDict["type"] )
        return allowedTypes[ix+1:]
    # end of BibleOrganizationalSystem.getMoreBasicTypes


    def getOrganizationalSystemValue( self, valueName ):
        """ Gets a value for the system. """
        #print( "getOrganizationalSystemValue( {} )".format( repr(valueName) ) )
        assert self.__dataDict
        assert valueName and isinstance( valueName, str )

        if valueName in self.__dataDict: return self.__dataDict[valueName]
        # else maybe we can find the value in a derived text
        #print( "q0", self.getOrganizationalSystemName() )
        for tryType in self.getMoreBasicTypes():
            if 'usesText' in self.__dataDict:
                for trySystemName in self.__dataDict['usesText']:
                    if isinstance( trySystemName, str ):
                        if BibleOrgSysGlobals.debugFlag: print( "trySystemName for 'usesText' is a string: {!r}".format( trySystemName ) )
                    elif isinstance( trySystemName, list ):
                        #print( "trySystemName for 'usesText' is a list: {!r}".format( trySystemName ) )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #print( "q1", "{} is trying usesText of {}".format(self.__systemName,trySystemName) )
                    result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                    if result is not None: return result
            if 'derivedFrom' in self.__dataDict:
                trySystemName = self.__dataDict['derivedFrom']
                if isinstance( trySystemName, str ):
                    if BibleOrgSysGlobals.debugFlag: print( "trySystemName for 'derivedFrom' is a string: {!r}".format( trySystemName ) )
                elif isinstance( trySystemName, list ):
                    #print( "trySystemName for 'derivedFrom' is a list: {!r}".format( trySystemName ) )
                    trySystemName = trySystemName[0] # Take the first string from the list
                #print( "q2", "{} is trying derivedFrom of {}".format(self.__systemName,trySystemName) )
                result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                if result is not None: return result
        # else we couldn't find it anywhere
        logging.error( _("{} Bible Organizational System has no {} specified (c)").format(self.getOrganizationalSystemName(),valueName) )
    # end of BibleOrganizationalSystem.getOrganizationalSystemValue


    def getBookList( self ):
        """
        Returns the list of book reference codes (BBB) for books in this system.
        Returns an empty list if there's no known books.
        """
        result = self.getOrganizationalSystemValue( "includesBooks" )
        if result is None: return []
        else: return result
    # end of BibleOrganizationalSystem.getBookList


    def containsBook( self, BBB ):
        """ Returns True or False if this book is in this system. """
        assert BBB and isinstance( BBB, str ) and len(BBB)==3
        return BBB in self.getBookList()
    # end of BibleOrganizationalSystem.containsBook


    def getFirstBookCode( self ):
        """
        Return the BBB code for the first book
            otherwise returns None.
        """
        if 1: return BibleBookOrderSystem.getBookAtOrderPosition( self, 1 )
        else: # I think this is wrong! Should use BookOrderSystem -- see next function
            bookList = self.getOrganizationalSystemValue( "includesBooks" )
            if bookList is None: return None
            return bookList[0]
    # end of BibleOrganizationalSystem.getFirstBookCode


    def getPreviousBookCode( self, BBB ):
        """ Returns the book (if any) before the given one. """
        while True:
            previousCode = BibleBookOrderSystem.getPreviousBookCode( self, BBB )
            if previousCode is None: return None
            if self.containsBook( previousCode ): return previousCode
            BBB = previousCode
    # end of BibleOrganizationalSystem.getNextBookCode


    def getNextBookCode( self, BBB ):
        """ Returns the book (if any) after the given one. """
        while True:
            nextCode = BibleBookOrderSystem.getNextBookCode( self, BBB )
            if nextCode is None: return None
            if self.containsBook( nextCode ): return nextCode
            BBB = nextCode
    # end of BibleOrganizationalSystem.getNextBookCode


    def isValidBCVRef( self, referenceTuple, referenceString, extended=False ):
        """
        Returns True/False indicating if the given reference is valid in this system.
        Extended flag allows chapter and verse numbers of zero.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("isValidBCVRef( {}, {}, {} )").format( referenceTuple, referenceString, extended ) )
            assert isinstance( referenceTuple, str ) or isinstance( referenceTuple, SimpleVerseKey )
        if isinstance( referenceTuple, SimpleVerseKey ): referenceTuple = referenceTuple.getBCVS()

        BBB, C, V, S = referenceTuple
        if BBB is None or not BBB: return False
        assert len(BBB) == 3
        if C and not C.isdigit(): # Should be no suffix on C (although it can be blank if the reference is for a whole book)
            print( "BibleOrganizationalSystem.isValidBCVRef( {}, {}, {} ) expected C to be digits".format( referenceTuple, referenceString, extended ) )
        assert not V or V.isdigit() # Should be no suffix on V (although it can be blank if the reference is for a whole chapter)
        assert not S or len(S)==1 and S.isalpha() # Suffix should be only one lower-case letter if anything
        if BBB and BibleBookOrderSystem.containsBook( self, BBB ):
            return BibleVersificationSystem.isValidBCVRef( self, referenceTuple, referenceString, extended=extended )
        logging.error( _("{} {}:{} is invalid book for reference {!r} in {} versification system for {}").format(BBB,C,V,referenceString, self.getBookOrderSystemName(),self.getOrganizationalSystemName()) )
        return False
    # end of BibleOrganizationalSystem.isValidBCVRef


    __absoluteVerseDict = OrderedDict()
    def __makeAbsoluteVerseList( self ):
        """
        Make up a list of four-tuples containing
            BBB, chapterNumber, firstVerseNumber, lastVerseNumber
        """
        accumulatedCount = 0
        for BBB in self.getBookList():
            #print( BBB, BibleVersificationSystem.getNumVersesList( self, BBB ) )
            for j,numVerses in enumerate( BibleVersificationSystem.getNumVersesList( self, BBB ) ):
                #print( BBB, j, numVerses )
                BibleOrganizationalSystem.__absoluteVerseDict[(BBB,j+1)] = (accumulatedCount+1,accumulatedCount+numVerses)
                accumulatedCount += numVerses
        #print( BibleOrganizationalSystem.__absoluteVerseDict )
    # end of BibleOrganizationalSystem.__makeAbsoluteVerseList


    def getAbsoluteVerseNumber( self, BBB, C, V ):
        """
        Convert the given reference (in this versification system)
            to an absolute verse number.

        Returns an integer in the range 1..31,102 (for KJV).

        Returns None for invalid or missing values.
        """
        C, V = int(C), int(V)
        if not BibleOrganizationalSystem.__absoluteVerseDict: self.__makeAbsoluteVerseList()
        rangeStart, rangeEnd = BibleOrganizationalSystem.__absoluteVerseDict[ (BBB,C) ]
        if 1 <= V <= rangeEnd-rangeStart+1:
            return rangeStart + V - 1
    # end of BibleOrganizationalSystem.getAbsoluteVerseNumber


    def convertAbsoluteVerseNumber( self, avNumber ):
        """
        Convert the given absolute verse number (in this versification system)
            to the reference versification.

        Returns a new BBB, C, V.

        Returns None for invalid or missing values.
        """
        if BibleOrgSysGlobals.debugFlag: assert 1 <= avNumber <= 99999
        if not BibleOrganizationalSystem.__absoluteVerseDict: self.__makeAbsoluteVerseList()
        for (BBB,C),(rangeStart, rangeEnd) in BibleOrganizationalSystem.__absoluteVerseDict.items():
            #print( BBB, C, rangeStart, rangeEnd )
            if rangeStart <= avNumber <= rangeEnd:
                return BBB, str(C), str(avNumber - rangeStart + 1)
    # end of BibleOrganizationalSystem.convertAbsoluteVerseNumber
# end of BibleOrganizationalSystem class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ProgNameVersion )

    if 1: # Demo the BibleOrganizationalSystems object
        print( "\nTesting system load..." )
        boss = BibleOrganizationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        print( boss ) # Just print a summary
        print( _("Available system names are: {}").format( boss.getAvailableOrganizationalSystemNames() ) )

    if 1: # Demo a BibleOrganizationalSystem object -- this is the one most likely to be wanted by a user
        print( "\nTesting varying systems..." )
        for testString in ( 'NIV', 'KJV-1611_edition', 'KJV-1638', ):
            print( "\nTrying: {!r}".format( testString ) )
            bos = BibleOrganizationalSystem( testString )
            print( 'bos', bos ) # Just print a summary
            print( "First book", bos.getFirstBookCode() )
            #print( "Book order list ({} entries) is {}".format( len(bos.getBookOrderList()), bos.getBookOrderList() ) )
            #print( "Book list ({} entries) is {}".format( len(bos.getBookList()), bos.getBookList() ) )
            print( "This type is {}. More basic types are: {}".format(bos.getOrganizationalSystemType(),bos.getMoreBasicTypes()) )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','JDE', 'TOB', ):
            #    print( "Contains {!r}: {}".format(test, bos.containsBook(test) ) )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','Jde', 'Ma1', ):
            #    print( "{!r} gives {}".format(test,bos.getBBB(test) ) )

    if 1:
        version = 'KJV-1769_edition'
        print( "\nTesting absolute verse numbers for", version )
        bos = BibleOrganizationalSystem( version )
        for myRef in (('GEN','1','0'), ('GEN','1','1'), ('GEN','1','2'), ('GEN','2','1'), ('MAT','1','1'), ('CO1','2','3'), ('REV','22','21'), ('REV','22','32'), ):
            print( ' ', myRef, '->', bos.getAbsoluteVerseNumber( myRef[0], myRef[1], myRef[2] ) )
        print()
        for myNum in ( 0, 1, 2, 3, 123, 23145, 23146, 31101, 31102, 31103 ):
            print( ' ', myNum, '->', bos.convertAbsoluteVerseNumber( myNum ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of BibleOrganizationalSystems.py