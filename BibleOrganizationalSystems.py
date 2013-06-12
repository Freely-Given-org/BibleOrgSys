#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleOrganizationalSystems.py
#   Last modified: 2013-06-11 by RJH (also update versionString below)
#
# Module handling BibleOrganizationalSystems
#
# Copyright (C) 2010-2013 Robert Hunt
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
Module handling BibleOrganizationalSystems.
"""

progName = "Bible Organization Systems handler"
versionString = "0.24"


import logging, os
from gettext import gettext as _
#from singleton import singleton

import Globals
from BibleOrganizationalSystemsConverter import BibleOrganizationalSystemsConverter, allowedTypes
from BibleBookOrders import BibleBookOrderSystem
from BiblePunctuationSystems import BiblePunctuationSystem
from BibleVersificationSystems import BibleVersificationSystem
from BibleBooksNames import BibleBooksNamesSystem



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
                if Globals.verbosityLevel > 2: print( "Loading pickle file {}...".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    result = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            else: # We have to load the XML (much slower)
                from BibleOrganizationalSystemsConverter import BibleOrganizationalSystemsConverter
                if XMLFilepath is not None: logging.warning( _("Bible organisational systems are already loaded -- your given filepath of '{}' was ignored").format(XMLFilepath) )
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
        if Globals.verbosityLevel > 1: # Do a bit of extra analysis
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
        """ Returns a list of available system name strings. """
        if extended:
            result = []
            for x in self.__indexDict:
                result.append( "{} ({})".format(x, self.__dataDict[self.indexDict[x]]['type'] ) )
            return result
        # else:
        return [x for x in self.__indexDict]
    # end of BibleOrganizationalSystems.getAvailableOrganizationalSystemNames

    def getOrganizationalSystem( self, systemName ):
        """ Returns the system dictionary.
            Accepts combined names (like KJV-1611_edition) or basic names (like KJV-1611).
        """
        #print( "getOrganizationalSystem( {} )".format( repr(systemName) ) )
        assert( systemName )
        assert( isinstance( systemName, str ) )

        if systemName in self.__dataDict: # we found the combined name
            return self.__dataDict[systemName]
        # else
        if systemName in self.__indexDict:
            index = self.__indexDict[systemName]
            if len(index) == 1: # Must only be one (unique) entry
                return self.__dataDict[ index[0] ]
            # else it's an ambiguous name that has multiple matches
            for possibleType in allowedTypes: # Steps through in priority order
                x = systemName + '_' + possibleType
                if x in self.__dataDict: return self.__dataDict[x]
        # else
        logging.error( _("No '{}' system in Bible Organisational Systems").format( systemName ) )
        if Globals.verbosityLevel>2: logging.error( _("Available systems are {}").format( self.getAvailableOrganizationalSystemNames( extended=True ) ) )
    # end of BibleOrganizationalSystems.getOrganizationalSystem

    def getOrganizationalSystemValue( self, systemName, valueName ):
        """ Gets a value for the system. """
        #print( "getOrganizationalSystemValue( {}, {} )".format( repr(systemName), repr(valueName) ) )
        assert( systemName and isinstance( systemName, str ) )
        assert( valueName and isinstance( valueName, str ) )
        thisSystem = self.getOrganizationalSystem( systemName )
        if thisSystem is not None:
            assert( thisSystem )
            if valueName in thisSystem: return thisSystem[valueName]
            # else maybe we can find the value in a derived text
            if 'usesText' in thisSystem:
                trySystemNames = thisSystem['usesText']
                #print( "trySystemNames is {}".format( repr(trySystemNames) ) )
                #print( "w1", "{} is trying usesText of {}".format(systemName,trySystemName) )
                #print( "\nKeys:", self.__dataDict.keys() )
                #print( "\nindexDict", self.__indexDict )
                #print( "\ncombinedIndexDict", self.__combinedIndexDict )
                assert( isinstance( trySystemNames, list ) ) # Maybe this can also be a string???
                for trySystemName in trySystemNames:
                    if trySystemName != systemName: # Avoid infinite recursion
                        result = self.getOrganizationalSystemValue( trySystemName, valueName )
                        #print( "trySystemName result is {}".format( repr(result) ) )
                        if result is not None: return result
            # else we couldn't find it anywhere
            logging.error( _("{} Bible Organizational System has no {} specified").format( systemName, valueName ) )
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
                    if isinstance( trySystemName, str ): print( "trySystemName for 'derivedFrom' is a string: '{}'".format( trySystemName ) )
                    elif isinstance( trySystemName, list ):
                        #print( "trySystemName for 'derivedFrom' is a list: '{}'".format( trySystemName ) )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #print( "q3", "{} is trying derivedFrom of {}".format(self.__systemName,trySystemName) )
                    result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                    #print( "  result is", result )
                    if result is not None: return result
            # else we couldn't find it anywhere
            if Globals.logErrorsFlag: logging.error( _("{} Bible Organizational System has no {} specified").format(self.__systemName,valueName) )
        # end of getOrganizationalSystemValue

        assert( systemName and isinstance( systemName, str ) )
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
        if Globals.debugFlag: print( "Got organisation bits: BOS={}, VS={}, PS={}, BNS={}".format( bookOrderSystemName, versificationSystemName, punctuationSystemName, booksNamesSystemName ) )
        if bookOrderSystemName and bookOrderSystemName!='None' and bookOrderSystemName!='Unknown': BibleBookOrderSystem.__init__( self, bookOrderSystemName )
        if versificationSystemName and versificationSystemName!='None' and versificationSystemName!='Unknown': BibleVersificationSystem.__init__( self, versificationSystemName )
        if punctuationSystemName and punctuationSystemName!='None' and punctuationSystemName!='Unknown': BiblePunctuationSystem.__init__( self, punctuationSystemName )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': BibleBooksNamesSystem.__init__( self, booksNamesSystemName, getOrganizationalSystemValue( "includesBooks" ) ) # Does one extra step To create the input abbreviations

        # Do some cross-checking
        myBooks = getOrganizationalSystemValue( "includesBooks" )
        if myBooks is not None:
            for BBB in myBooks:
                if not BibleBookOrderSystem.containsBook( self, BBB ):
                    if Globals.logErrorsFlag: logging.error( _("Book '{}' is included in {} system but missing from {} book order system").format( BBB, self.__systemName, BibleBookOrderSystem.getBookOrderSystemName( self ) ) )
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
            if Globals.verbosityLevel > 3: result += ('\n' if result else '') + "  Entries are: {}".format( self.__dataDict )
        return result
    # end of BibleOrganizationalSystem.__str__

    def getOrganizationalSystemName( self ):
        """ Return the system name. """
        assert( self.__systemName )
        return self.__systemName
    # end of BibleOrganizationalSystem.getOrganizationalSystemName

    def getOrganizationalSystemType( self ):
        """ Return the system type. """
        assert( self.__dataDict )
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
        assert( self.__dataDict )
        assert( valueName and isinstance( valueName, str ) )

        if valueName in self.__dataDict: return self.__dataDict[valueName]
        # else maybe we can find the value in a derived text
        #print( "q0", self.getOrganizationalSystemName() )
        for tryType in self.getMoreBasicTypes():
            if 'usesText' in self.__dataDict:
                for trySystemName in self.__dataDict['usesText']:
                    if isinstance( trySystemName, str ): print( "trySystemName for 'usesText' is a string: '{}'".format( trySystemName ) )
                    elif isinstance( trySystemName, list ):
                        #print( "trySystemName for 'usesText' is a list: '{}'".format( trySystemName ) )
                        trySystemName = trySystemName[0] # Take the first string from the list
                    #print( "q1", "{} is trying usesText of {}".format(self.__systemName,trySystemName) )
                    result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                    if result is not None: return result
            if 'derivedFrom' in self.__dataDict:
                trySystemName = self.__dataDict['derivedFrom']
                if isinstance( trySystemName, str ): print( "trySystemName for 'derivedFrom' is a string: '{}'".format( trySystemName ) )
                elif isinstance( trySystemName, list ):
                    #print( "trySystemName for 'derivedFrom' is a list: '{}'".format( trySystemName ) )
                    trySystemName = trySystemName[0] # Take the first string from the list
                #print( "q2", "{} is trying derivedFrom of {}".format(self.__systemName,trySystemName) )
                result = self.__boss.getOrganizationalSystemValue( trySystemName, valueName )
                if result is not None: return result
        # else we couldn't find it anywhere
        if Globals.logErrorsFlag: logging.error( _("{} Bible Organizational System has no {} specified").format(self.getOrganizationalSystemName(),valueName) )
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
        assert( BBB and isinstance( BBB, str ) and len(BBB)==3 )
        return BBB in self.getBookList()
    # end of BibleOrganizationalSystem.containsBook

    def getFirstBookCode( self ):
        """
        Return the BBB code for the first book
            otherwise returns None.
        """
        bookList = self.getOrganizationalSystemValue( "includesBooks" )
        if bookList is None: return None
        return bookList[0]
    # end of BibleOrganizationalSystem.getFirstBookCode

    def isValidBCVRef( self, referenceTuple, referenceString, extended=False ):
        """
        Returns True/False indicating if the given reference is valid in this system.
        Extended flag allows chapter and verse numbers of zero.
        """
        #print( "BibleOrganizationalSystem.isValidBCVRef( {}, {}, {}, {} )".format( referenceTuple, referenceString, extended ) )
        BBB, C, V, S = referenceTuple
        if BBB is None or not BBB: return False
        assert( len(BBB) == 3 )
        if C and not C.isdigit(): # Should be no suffix on C (although it can be blank if the reference is for a whole book)
            print( "BibleOrganizationalSystem.isValidBCVRef( {}, {}, {} ) expected C to be digits".format( referenceTuple, referenceString, extended ) )
        assert( not V or V.isdigit() ) # Should be no suffix on V (although it can be blank if the reference is for a whole chapter)
        assert( not S or len(S)==1 and S.isalpha() ) # Suffix should be only one lower-case letter if anything
        if BBB and BibleBookOrderSystem.containsBook( self, BBB ):
            return BibleVersificationSystem.isValidBCVRef( self, referenceTuple, referenceString, extended=extended )
        elif Globals.logErrorsFlag: logging.error( _("{} {}:{} is invalid book for reference '{}' in {} versification system for {}").format(BBB,C,V,referenceString, self.getBookOrderSystemName(),self.getOrganizationalSystemName()) )
        return False
    # end of BibleOrganizationalSystem.isValidBCVRef
# end of BibleOrganizationalSystem class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    if 0: # Demo the BibleOrganizationalSystems object
        print()
        boss = BibleOrganizationalSystems().loadData() # Doesn't reload the XML unnecessarily :)
        print( boss ) # Just print a summary
        print( _("Available system names are: {}").format( boss.getAvailableOrganizationalSystemNames() ) )

    if 1: # Demo a BibleOrganizationalSystem object -- this is the one most likely to be wanted by a user
        for testString in ( 'NIV', 'KJV-1611_edition', 'KJV-1638', ):
            print( "\nTrying: '{}'".format( testString ) )
            bos = BibleOrganizationalSystem( testString )
            print( 'bos', bos ) # Just print a summary
            #print( "Book order list ({} entries) is {}".format( len(bos.getBookOrderList()), bos.getBookOrderList() ) )
            #print( "Book list ({} entries) is {}".format( len(bos.getBookList()), bos.getBookList() ) )
            print( "This type is {}. More basic types are: {}".format(bos.getOrganizationalSystemType(),bos.getMoreBasicTypes()) )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','JDE', 'TOB', ):
            #    print( "Contains '{}': {}".format(test, bos.containsBook(test) ) )
            #for test in ('GEN','Gen','MAT','Mat','Mt1','JUD','Jud','Jde', 'Ma1', ):
            #    print( "'{}' gives {}".format(test,bos.getBBB(test) ) )
# end of demo

if __name__ == '__main__':
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    demo()
# end of BibleOrganizationalSystems.py