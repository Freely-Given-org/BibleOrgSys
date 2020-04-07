#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBookOrders.py
#
# Module handling BibleBookOrderSystems
#
# Copyright (C) 2010-2020 Robert Hunt
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
Module handling BibleBookOrder systems.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-07' # by RJH
SHORT_PROGRAM_NAME = "BibleBookOrders"
PROGRAM_NAME = "Bible Book Order Systems handler"
PROGRAM_VERSION = '0.91'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False



import os
import logging
#from BibleOrgSys.Misc.singleton import singleton

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals



#@singleton # Can only ever have one instance (but doesn't work for multiprocessing)
class BibleBookOrderSystems:
    """
    Class for handling Bible book order systems.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "BibleBookOrderSystems:__init__()" )
        self.__DataDicts = self.__DataLists = None # We'll import into these in loadData
    # end of BibleBookOrderSystems.__init__


    def loadData( self, XMLFileOrFilepath=None ):
        """ Loads the XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDicts or not self.__DataLists: # Don't do this unnecessarily
            if XMLFileOrFilepath is None:
                # See if we can load from the pickle file (faster than loading from the XML)
                standardXMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'BibleBookOrders.xml' )
                standardPickleFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATA_FILES_FOLDERPATH.joinpath( 'BibleBookOrders_Tables.pickle' )
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
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( f"Loading pickle file {standardPickleFilepath}…" )
                    with open( standardPickleFilepath, 'rb') as pickleFile:
                        self.__DataDicts = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                        self.__DataLists = pickle.load( pickleFile )
                    return self # So this command can be chained after the object creation
                elif debuggingThisModule:
                    print( "BibleBookOrders pickle file can't be loaded!" )
                standardJsonFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATA_FILES_FOLDERPATH.joinpath( 'BibleBookOrders_Tables.json' )
                if os.access( standardJsonFilepath, os.R_OK ) \
                and os.stat(standardJsonFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
                and os.stat(standardJsonFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                    import json
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( f"NOT TESTED -- CODE MAY NEED ADJUSTING -- Loading json file {standardJsonFilepath}…" )
                    with open( standardJsonFilepath, 'rb') as JsonFile:
                        self.__DataDicts = json.load( JsonFile )
                        self.__DataLists = json.load( JsonFile )
                    # # NOTE: We have to convert str referenceNumber keys back to ints
                    # self.__DataDicts['referenceNumberDict'] = { int(key):value \
                    #             for key,value in self.__DataDicts['referenceNumberDict'].items() }
                    return self # So this command can be chained after the object creation
                elif debuggingThisModule:
                    print( "BibleBookOrders JSON file can't be loaded!" )
            # else: # We have to load the XML (much slower)
            from BibleOrgSys.Reference.Converters.BibleBookOrdersConverter import BibleBookOrdersConverter
            if XMLFileOrFilepath is not None:
                logging.warning( _("Bible book orders are already loaded -- your given filepath of {!r} was ignored").format(XMLFileOrFilepath) )
            bboc = BibleBookOrdersConverter()
            bboc.loadAndValidate( XMLFileOrFilepath ) # Load the XML (if not done already)
            self.__DataDicts, self.__DataLists = bboc.importDataToPython() # Get the various dictionaries organised for quick lookup
            assert len(self.__DataDicts) == len(self.__DataLists)
            if (BibleOrgSysGlobals.debugFlag and debuggingThisModule) or BibleOrgSysGlobals.verbosityLevel > 3:
                print( "BibleBookOrderSystems:loadData({}) loaded {} systems".format( XMLFolder, len(self.__DataDicts) ) )
        return self # So this command can be chained after the object creation
    # end of BibleBookOrderSystems.loadData


    def __str__( self ):
        """
        This method returns the string representation of a Bible book order.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBookOrders object"
        result += ('\n' if result else '') + "  Number of systems = {}".format( len(self.__DataDicts) )
        return result
    # end of BibleBookOrderSystems.__str__


    def __len__( self ):
        """ Returns the number of systems loaded. """
        assert len(self.__DataDicts) == len(self.__DataLists)
        return len( self.__DataDicts )
    # end of BibleBookOrderSystems.__len__


    def __contains__( self, name ):
        """ Returns True/False if the name is in this system. """
        return name in self.__DataLists
    # end of BibleBookOrderSystems.__contains__


    def getAvailableBookOrderSystemNames( self ):
        """ Returns a list of available system name strings. """
        return [x for x in self.__DataLists]
    # end of BibleBookOrderSystems.getAvailableBookOrderSystemNames


    def getBookOrderSystem( self, systemName ):
        """ Returns two dictionaries and a list object."""
        if systemName in self.__DataDicts:
            return self.__DataDicts[systemName][0], self.__DataDicts[systemName][1], self.__DataLists[systemName]
        # else
        logging.error( _("No {!r} system in Bible Book Orders").format( systemName ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: logging.error( _("Available systems are {}").format( self.getAvailableBookOrderSystemNames() ) )
    # end of BibleBookOrderSystems.getBookOrderSystem


    def numBooks( self, systemName ):
        """ Returns the number of books in this system. """
        return len( self.__DataLists[systemName] )
    # end of BibleBookOrderSystems.numBooks


    def containsBook( self, systemName, BBB ):
        """ Return True if the book is in this system. """
        return BBB in self.__DataLists[systemName]
    # end of BibleBookOrderSystems.containsBook


    def getBookOrderList( self, systemName ):
        """ Returns the list of BBB book reference abbreviations in the correct order. """
        return self.__DataLists[systemName]
    # end of BibleBookOrderSystems.getBookOrderList


    def checkBookOrderSystem( self, thisSystemName, bookOrderSchemeToCheck ):
        """
        Check the given book order scheme against all the loaded systems.
        Create a new book order file if it doesn't match any.
        Returns the number of matched systems (which can also be used as a True/False "matched" flag).
        """
        assert thisSystemName
        assert bookOrderSchemeToCheck
        assert self.__DataLists
        #print( thisSystemName, bookOrderSchemeToCheck )
        for BBB in bookOrderSchemeToCheck:
            if not BibleOrgSysGlobals.loadedBibleBooksCodes.isValidBBB( BBB ): 
                logging.error( f"Invalid '{BBB}' book code" )

        matchedBookOrderSystemCodes = []
        exactMatchCount, subsetMatchCount, systemMismatchCount, allErrors, errorSummary = 0, 0, 0, '', ''
        for bookOrderSystemCode in self.__DataLists: # Step through the various reference schemes
            if self.__DataLists[bookOrderSystemCode] == bookOrderSchemeToCheck:
                #print( "  {} exactly matches {!r} book order system".format( thisSystemName, bookOrderSystemCode ) )
                exactMatchCount += 1
                matchedBookOrderSystemCodes.append( bookOrderSystemCode )
            else: # it's not an exact match
                if len(self.__DataLists[bookOrderSystemCode]) == len(bookOrderSchemeToCheck): # They're both contain the same NUMBER of books
                    for BBB1,BBB2 in zip(self.__DataLists[bookOrderSystemCode],bookOrderSchemeToCheck):
                        if BBB1 != BBB2: break
                    thisError = "    " + _("Doesn't match '{0}' system (Both have {1} books, but {0} has {2} where {3} has {4})").format( bookOrderSystemCode, len(bookOrderSchemeToCheck), BBB1, thisSystemName, BBB2 )
                    errorSummary += ("\n" if errorSummary else "") + thisError
                else:
                    thisError = "    " + _("Doesn't exactly match '{0}' system ({0} has {1} books whereas {2} has {3})").format( bookOrderSystemCode, len(self.__DataLists[bookOrderSystemCode]), thisSystemName, len(bookOrderSchemeToCheck) )
                    allErrors += ("\n" if allErrors else "") + thisError
                    #systemMismatchCount += 1
                # look for a subset
                lastIndex, isSubset = -1, True
                for BBB in bookOrderSchemeToCheck:
                    if not BBB in self.__DataLists[bookOrderSystemCode]: # This book isn't even in the other system
                        thisError = "    " + _("Can't match '{0}' system ({0} doesn't even have {1})").format( bookOrderSystemCode, BBB )
                        allErrors += ("\n" if allErrors else "") + thisError
                        isSubset=False
                        break
                    index = self.__DataLists[bookOrderSystemCode].index( BBB )
                    #print( BBB, index, lastIndex )
                    if index < lastIndex: # they must be in a different order
                        thisError = "    " + _("Can't match '{0}' system ({0} has {1} in a different place)").format( bookOrderSystemCode, BBB )
                        allErrors += ("\n" if allErrors else "") + thisError
                        isSubset=False
                        break
                    lastIndex = index
                if isSubset:
                    #print( "  {} is a subset of {!r} book order system".format( thisSystemName, bookOrderSystemCode ) )
                    subsetMatchCount += 1
                    matchedBookOrderSystemCodes.append( bookOrderSystemCode )

        systemMatchCount = exactMatchCount + subsetMatchCount # seems like we could improve this whole section of code
        systemMismatchCount = len(self.__DataLists) - systemMatchCount
        if systemMatchCount == 1: # What we hope for
            print("  " + _("{} matched {} book order (with these {} books)").format( thisSystemName, matchedBookOrderSystemCodes[0], len(bookOrderSchemeToCheck) ) )
            if BibleOrgSysGlobals.debugFlag: print( errorSummary )
        elif systemMatchCount == 0: # No matches
            print( "  " + _("{} mismatched {} book order systems (with these {} books)").format( thisSystemName, systemMismatchCount, len(bookOrderSchemeToCheck) ) )
            print( allErrors if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2 else errorSummary )
        else: # Multiple matches
            print( "  " + _("{} matched {} book order system(s): {} (with these {} books)").format( thisSystemName, systemMatchCount, matchedBookOrderSystemCodes, len(bookOrderSchemeToCheck) ) )
            if BibleOrgSysGlobals.debugFlag: print( errorSummary )

        if BibleOrgSysGlobals.commandLineArguments.export and not systemMatchCount: # Write a new file
            outputFilepath = os.path.join( os.path.dirname(__file__), 'DataFiles/', 'ScrapedFiles/', "BibleBookOrder_"+thisSystemName + '.xml' )
            print( _("Writing {} {} books to {}…").format( len(bookOrderSchemeToCheck), thisSystemName, outputFilepath ) )
            with open( outputFilepath, 'wt', encoding='utf-8' ) as myFile:
                for n,BBB in enumerate(bookOrderSchemeToCheck):
                    myFile.write( '  <book id="{}">{}</book>\n'.format( n+1,BBB ) )
                myFile.write( "</BibleBookOrderSystem>" )

        return systemMatchCount
    # end of BibleBookOrderSystems.checkBookOrderSystem
# end of BibleBookOrderSystems class



class BibleBookOrderSystem:
    """
    Class for handling an individual Bible book order system.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self, systemName ):
        """
        Constructor:
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "BibleBookOrderSystem:__init__({})".format( systemName ) )
        self.__systemName = systemName
        self.__bbos = BibleBookOrderSystems().loadData() # Doesn't reload the XML unnecessarily :)
        results = self.__bbos.getBookOrderSystem( self.__systemName )
        if results is None:
            print( "BibleBookOrderSystem:__init__({}) failed!".format( systemName ) )
            self.__BookOrderBookDict = self.__BookOrderNumberDict = self.__BookOrderList = None
        else: self.__BookOrderBookDict, self.__BookOrderNumberDict, self.__BookOrderList = results
    # end of BibleBookOrderSystem.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book order.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBookOrder object"
        result += ('\n' if result else '') + " {} book order system".format( self.__systemName )
        result += ('\n' if result else '') + "  Number of books = {}".format( self.numBooks() )
        return result
    # end of BibleBookOrderSystem.__str__


    def __len__( self ):
        """ Returns the number of books in this system. """
        try: return len( self.__BookOrderList )
        except AttributeError: return None
    # end of BibleBookOrderSystem.__len__


    def numBooks( self ):
        """ Returns the number of books in this system. """
        return len( self.__BookOrderList )
    # end of BibleBookOrderSystem.numBooks


    def __contains__( self, BBB ):
        """ Returns True/False if the book is in this system. """
        assert len(BBB) == 3
        return BBB in self.__BookOrderList
    # end of BibleBookOrderSystem.__contains__


    def containsBook( self, BBB ):
        """ Return True/False if the book is in this system. """
        assert len(BBB) == 3
        return BBB in self.__BookOrderList
    # end of BibleBookOrderSystem.containsBook


    def getBookOrderSystemName( self ):
        """ Return the book order system name. """
        return self.__systemName
    # end of BibleBookOrderSystem.getBookOrderSystemName

    def getBookOrderPosition( self, BBB ):
        """ Returns the book position number (1..n). """
        assert len(BBB) == 3
        return self.__BookOrderBookDict[BBB]
    # end of BibleBookOrderSystem.getBookOrderPosition


    def getBookAtOrderPosition( self, n ):
        """ Returns the BBB book reference abbreviation for the position number (1..n). """
        return self.__BookOrderNumberDict[n]
    # end of BibleBookOrderSystem.getBookAtOrderPosition


    def getBookOrderList( self ):
        """ Returns the list of BBB book reference abbreviations in the correct order. """
        return self.__BookOrderList
    # end of BibleBookOrderSystem.getBookOrderList


    def getPreviousBookCode( self, BBB ):
        """
        Returns the book (if any) before the given one.
        Otherwise returns None.
        """
        assert len(BBB)==3
        previousPosition = self.__BookOrderBookDict[BBB] - 1
        if previousPosition in self.__BookOrderNumberDict: return self.__BookOrderNumberDict[previousPosition]
    # end of BibleBookOrderSystem.getNextBookCode


    def getNextBookCode( self, BBB ):
        """ Returns the book (if any) after the given one. """
        assert len(BBB)==3
        nextPosition = self.__BookOrderBookDict[BBB] + 1
        if nextPosition in self.__BookOrderNumberDict: return self.__BookOrderNumberDict[nextPosition]
    # end of BibleBookOrderSystem.getNextBookCode


    def correctlyOrdered( self, BBB1, BBB2 ):
        """ Returns True/False if the two books are in the correct order. """
        assert BBB1 and len(BBB1)==3
        assert BBB2 and len(BBB2)==3
        return self.__BookOrderBookDict[BBB1] < self.__BookOrderBookDict[BBB2]
    # end of BibleBookOrderSystem.correctlyOrdered
# end of BibleBookOrderSystem class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    # Demo the BibleBookOrders object
    bboss = BibleBookOrderSystems().loadData() # Doesn't reload the XML unnecessarily :)
    print( bboss ) # Just print a summary
    print( _("Number of loaded systems: {}").format( len(bboss) ) )
    print( _("Available system names are: {}").format( bboss.getAvailableBookOrderSystemNames() ) )
    systemName = "VulgateBible"
    print( "Number of books in {} is {}".format( systemName, bboss.numBooks(systemName) ) )
    systemName = "Septuagint"; BBB="ROM"
    print( "{} is in {}:{}".format( BBB, systemName, bboss.containsBook(systemName,BBB) ) )
    for systemName in ("ModernJewish", "EuropeanBible", ):
        print( "Booklist for {} is {}".format( systemName, bboss.getBookOrderList(systemName) ) )
    bboss.checkBookOrderSystem( "myTest1", ['MAT', 'MRK', 'LUK', 'JHN', 'ACT'] )
    bboss.checkBookOrderSystem( "myTest2", ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV'] )

    # Demo a BibleBookOrder object -- this is the one most likely to be wanted by a user
    bbos = BibleBookOrderSystem( "EuropeanBible" )
    if bbos is not None:
        print( bbos ) # Just print a summary
        print( "Number of books is {} or {}".format(len(bbos), bbos.numBooks()) )
        print( "The 3rd book is {}".format( bbos.getBookAtOrderPosition(3) ) )
        print( "Contains Psalms: {}".format( bbos.containsBook("PSA") ) )
        print( "Contains Judith: {}".format( bbos.containsBook("JDT") ) )
        print( "Luke is book #{}".format( bbos.getBookOrderPosition("LUK") ) )
        print( "Book order list is: {}".format( bbos.getBookOrderList() ) )
        BBB = "TI1"
        while True: # Step through the next books until the end of the publication
            BBB2 = bbos.getNextBookCode( BBB )
            if BBB2 is None: break
            print( " Next book after {} is {}".format(BBB,BBB2) )
            BBB = BBB2
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleBookOrders.py
