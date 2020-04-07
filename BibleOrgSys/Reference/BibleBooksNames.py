#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBooksNames.py
#
# Module handling BibleBooksNames
#
# Copyright (C) 2010-2019 Robert Hunt
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
Module handling BibleBooksNames.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-09-19' # by RJH
SHORT_PROGRAM_NAME = "BibleBooksNames"
PROGRAM_NAME = "Bible Books Names Systems handler"
PROGRAM_VERSION = '0.40'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals



def expandBibleNamesInputs ( systemName, divisionsNamesDict, booknameLeadersDict, bookNamesDict, bookList ):
    """
    This is a helper function to expand the inputAbbreviation fields to include all unambiguous shorter abbreviations.

    It is best to do this for a specific publication since there will be less ambiguities if there are less actual books included.

    Returns divisions name and book name ordered dictionaries, all UPPER CASE, sorted with longest first.
    """

    def expandAbbrevs( UCString, value, originalDict, tempDict, theAmbigSet ):
        """
        Progressively remove characters off the end of the (UPPER CASE) UCString, plus also remove internal spaces.
            trying to find unambiguous shortcuts which the user could use.
        """
        assert UCString
        assert originalDict

        # Drop off final letters and remove internal spaces
        tempString = UCString
        while tempString:
            if not tempString.isdigit() and tempString[-1]!=' ': # Don't allow single digits (even if unambiguous) and gnore any truncated strings that end in a space
                if tempString in originalDict:
                    if originalDict[tempString] == value:
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            logging.debug( "{!r} is superfluous: won't add to tempDict".format(tempString) )
                        theAmbigSet.add( tempString )
                    else: # it's a different value
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            logging.debug( "{!r} is ambiguous: won't add to tempDict".format(tempString) )
                        theAmbigSet.add( tempString )
                elif tempString in tempDict and tempDict[tempString]!=value:
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        logging.info( "{!r} is ambiguous: will remove from tempDict".format(tempString) )
                    theAmbigSet.add( tempString )
                else:
                    tempDict[tempString] = value
                tempTempString = tempString
                while ' ' in tempTempString:
                    tempTempString = tempTempString.replace( " ", "", 1 ) # Remove the first space
                    if tempTempString in originalDict:
                        if originalDict[tempTempString] == value:
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                logging.debug( "{!r} (spaces removed) is superfluous: won't add to tempDict".format(tempTempString) )
                            theAmbigSet.add( tempTempString )
                        else: # it's a different value
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                logging.debug( "{!r} (spaces removed) is ambiguous: won't add to tempDict".format(tempTempString) )
                            theAmbigSet.add( tempTempString )
                    elif tempTempString in tempDict and tempDict[tempTempString]!=value:
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            logging.info( "{!r} (spaces removed) is ambiguous: will remove from tempDict".format(tempTempString) )
                        theAmbigSet.add( tempTempString )
                    else:
                        tempDict[tempTempString] = value
            tempString = tempString[:-1] # Drop off another letter
    # end of expandAbbrevs

    assert systemName
    assert divisionsNamesDict and booknameLeadersDict and bookNamesDict
    assert bookList

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Expanding {} input abbreviations (for {} books)…").format( systemName, len(bookList) ) )

    # Firstly, make a new UPPER CASE leaders dictionary., e.g., Saint/Snt goes to SAINT/SNT
    UCBNLeadersDict = {}
    #print( "bnLD", len(booknameLeadersDict), booknameLeadersDict )
    for leader in booknameLeadersDict:
        UCLeader = leader.upper()
        assert UCLeader not in UCBNLeadersDict
        UCBNLeadersDict[UCLeader] = [x.upper() for x in booknameLeadersDict[leader]]
        #UCBNLeadersDict[UCLeader].append( UCLeader ) # We have to add ourselves to this list
    #print( "UCbnl", len(UCBNLeadersDict), UCBNLeadersDict )

    # Secondly make a set of the given allowed names
    divNameInputDict, bkNameInputDict, ambigSet = {}, {}, set()
    for divAbbrev in divisionsNamesDict.keys():
        for field in divisionsNamesDict[divAbbrev]['inputFields']:
            UCField = field.upper()
            if UCField in divNameInputDict or UCField in bkNameInputDict:
                logging.warning( _("Have duplicate entries of {!r} in divisionsNames for {}").format( UCField, systemName ) )
                ambigSet.add( UCField )
            divNameInputDict[UCField] = divAbbrev # Store the index into divisionsNamesDict
    for refAbbrev in bookNamesDict.keys():
        if refAbbrev in bookList and isinstance(bookNamesDict[refAbbrev], dict) :
            for field in bookNamesDict[refAbbrev]['inputFields']: # inputFields include the defaultName, defaultAbbreviation, and inputAbbreviations
                UCField = field.upper()
                if UCField in divNameInputDict or UCField in bkNameInputDict:
                    logging.warning( _("Have duplicate entries of {!r} in divisions and book names for {}").format( UCField, systemName ) )
                    ambigSet.add( UCField )
                bkNameInputDict[UCField] = refAbbrev # Store the index to the book
    #print( 'amb', len(ambigSet), ambigSet )

    # Now expand the divisions names
    #
    # We do this by replacing "2 " with alternatives like "II " and "Saint" with "Snt" and "St" (as entered in the XML file)
    #   At the same time, we progressively drop letters off the end until the (UPPER CASE) name becomes ambiguous
    #       We also remove internal spaces
    #
    # We add all unambiguous names to tempDict
    # We list ambiguous names in ambigSet so that they can be removed from tempDict after all entries have been processed
    #   (This is because we might not discover the ambiguity until later in processing the list)
    #
    # NOTE: In this code, division names and book names share a common ambiguous list
    #           If they are only ever entered into separate fields, the ambiguous list could be split into two
    #               i.e., they wouldn't be ambiguous in context
    #
    #print( "\ndivNameInputDict", len(divNameInputDict), divNameInputDict )
    tempDNDict = {}
    for UCField in divNameInputDict.keys():
        expandAbbrevs( UCField, divNameInputDict[UCField], divNameInputDict, tempDNDict, ambigSet  )
        for leader in UCBNLeadersDict: # Note that the leader here includes a trailing space
            if UCField.startswith( leader ):
                for replacementLeader in UCBNLeadersDict[leader]:
                    expandAbbrevs( UCField.replace(leader,replacementLeader), divNameInputDict[UCField], divNameInputDict, tempDNDict, ambigSet )
    #print ( '\ntempDN', len(tempDNDict), tempDNDict )
    #print( '\namb2', len(ambigSet), ambigSet )

    #print( "\nbkNameInputDict", len(bkNameInputDict), bkNameInputDict )
    tempBNDict = {}
    #print( bkNameInputDict.keys(), UCBNLeadersDict )
    for UCField in bkNameInputDict.keys():
        expandAbbrevs( UCField, bkNameInputDict[UCField], bkNameInputDict, tempBNDict, ambigSet  )
        for leader in UCBNLeadersDict: # Note that the leader here includes a trailing space
            if UCField.startswith( leader ):
                for replacementLeader in UCBNLeadersDict[leader]:
                    expandAbbrevs( UCField.replace(leader,replacementLeader), bkNameInputDict[UCField], bkNameInputDict, tempBNDict, ambigSet )
    #print ( '\ntempBN', len(tempBNDict) )
    #print( '\namb3', len(ambigSet), ambigSet )

    # Add the unambiguous shortcuts and abbreviations to get all of our allowed options
    for field in tempDNDict:
        if field not in ambigSet:
            assert field not in divNameInputDict
            divNameInputDict[field] = tempDNDict[field]
    #print( "\ndivNameInputDict--final", len(divNameInputDict), divNameInputDict )
    for field in tempBNDict:
        if field not in ambigSet:
            assert field not in bkNameInputDict
            bkNameInputDict[field] = tempBNDict[field]
        #else: print( "Didn't add {!r}", field )
    #print( "\nbkNameInputDict--final", len(bkNameInputDict) )

    # Now sort both dictionaries to be longest string first
    sortedDNDict = dict( sorted(divNameInputDict.items(), key=lambda s: -len(s[0])) )
    sortedBNDict = dict( sorted( bkNameInputDict.items(), key=lambda s: -len(s[0])) )

    # Finally, return the expanded input fields
    return sortedDNDict, sortedBNDict
# end of expandBibleNamesInputs



@singleton # Can only ever have one instance
class BibleBooksNamesSystems:
    """
    Class for handling Bible books names systems.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__DataDicts, self.__ExpandedDicts = None, None # We'll import into this in loadData
    # end of BibleBooksNamesSystems.__init__

    def loadData( self, XMLFolder=None ):
        """
        Loads the XML data file and imports it to dictionary format (if not done already).
        """
        if not self.__DataDicts: # Don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            picklesGood = False
            standardPickleFilepath = BibleOrgSysGlobals.BOS_DERIVED_DATA_FILES_FOLDERPATH.joinpath( "BibleBooksNames_Tables.pickle" )
            if XMLFolder is None and os.access( standardPickleFilepath, os.R_OK ):
                standardXMLFolder = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( "BookNames/" )
                pickle8, pickle9 = os.stat(standardPickleFilepath)[8:10]
                picklesGood = True
                for filename in os.listdir( standardXMLFolder ):
                    filepart, extension = os.path.splitext( filename )
                    XMLFileOrFilepath = os.path.join( standardXMLFolder, filename )
                    if extension.upper() == '.XML' and filepart.upper().startswith("BIBLEBOOKSNAMES_"):
                        if pickle8 <= os.stat( XMLFileOrFilepath ).st_mtime \
                        or pickle9 <= os.stat( XMLFileOrFilepath ).st_ctime: # The pickle file is older
                            picklesGood = False; break
            if picklesGood:
                import pickle
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}…".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    self.__DataDicts = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    #self.__ExpandedDicts = pickle.load( pickleFile )
            else: # We have to load the XML (much slower)
                from BibleOrgSys.Reference.Converters.BibleBooksNamesConverter import BibleBooksNamesConverter
                if XMLFolder is not None:
                    logging.warning( _("Bible books names are already loaded -- your given folder of {!r} was ignored").format(XMLFolder) )
                bbnsc = BibleBooksNamesConverter()
                bbnsc.loadSystems( XMLFolder ) # Load the XML (if not done already)
                self.__DataDicts, self.__ExpandedDicts = bbnsc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self
    # end of BibleBooksNamesSystems.loadData

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesSystems object"
        if self.__ExpandedDicts: assert len(self.__DataDicts) == len(self.__ExpandedDicts)
        result += ('\n' if result else '') + '  ' + _("Number of loaded bookname systems = {}").format( len(self.__DataDicts) )
        return result
    # end of BibleBooksNamesSystems.__str__


    def __len__( self ):
        """
        Returns the number of book names systems loaded.
        """
        return len( self.__DataDicts )
    # end of BibleBooksNamesSystems.__len__


    def __contains__( self, name ):
        """
        Returns True/False if the name is in this system.
        """
        return name in self.__DataDicts
    # end of BibleBooksNamesSystems.__contains__


    def getAvailableBooksNamesSystemNames( self, languageCode=None ):
        """
        Returns a list of available system name strings.
        """
        if languageCode is None:
            return [systemName for systemName in self.__DataDicts]
        # else -- we were given a language code
        assert len(languageCode) == 3 # ISO 639-3
        search = languageCode + '_'
        result = []
        for systemName in self.__DataDicts:
            if systemName==languageCode: result.append( '' )
            if systemName.startswith( search ): result.append( systemName[4:] ) # Get the bit after the underline
        return result
    # end of BibleBooksNamesSystems.getAvailableBooksNamesSystemNames


    def getAvailableLanguageCodes( self ):
        """
        Returns a list of available ISO 639-3 language code strings.
        """
        result = set()
        for systemName in self.__DataDicts:
            assert len(systemName) >= 3
            languageCode = systemName[:3]
            result.add( languageCode )
        return result
    # end of BibleBooksNamesSystems.getAvailableLanguageCodes


    def getBBBFromText( self, bookNameOrAbbreviation ):
        """
        Get the referenceAbbreviation from the given book name or abbreviation.
                (Automatically converts to upper case before comparing strings.)

        Tries all the known Bible Books Names systems.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleBooksNamesSystems.getBBBFromText( {} )".format( bookNameOrAbbreviation ) )
            assert bookNameOrAbbreviation

        upperCaseBookNameOrAbbreviation = bookNameOrAbbreviation.upper()

        for systemName in self.__DataDicts:
            #print( '\n'+repr(systemName) )
            #print( self.__DataDicts[systemName] )
            #for j in range( len(self.__DataDicts[systemName]) ):
                #print( '\nHere1', j, self.__DataDicts[systemName][j] )
            #for BBB in self.__DataDicts[systemName][2]:
                #print( 'Here2', BBB, self.__DataDicts[systemName][2][BBB] )
            divisionsNamesDict, booknameLeadersDict, bookNamesDict, sortedDivisionNamesDict, sortedBookNamesDict = self.getBooksNamesSystem( systemName )
            #print( '\nHere3 '+systemName, sortedBookNamesDict )
            if sortedBookNamesDict:
                if upperCaseBookNameOrAbbreviation in sortedBookNamesDict:
                    return sortedBookNamesDict[upperCaseBookNameOrAbbreviation]
            else:
                for BBB in self.__DataDicts[systemName][2]:
                    for possibility in self.__DataDicts[systemName][2][BBB]['inputFields']:
                        #print( possibility )
                        if possibility.upper().startswith( upperCaseBookNameOrAbbreviation ):
                            return BBB

            if self.__ExpandedDicts: print( self.__ExpandedDicts[systemName] ); halt # nothing written here yet
    # end of BibleBooksNamesSystems.getBBBFromText


    def getBooksNamesSystem( self, systemName, bookList=None ):
        """
        Returns two dictionaries and a list object.
        """
        if bookList is not None:
            for BBB in bookList: # Just check this list is valid
                if not BibleOrgSysGlobals.loadedBibleBooksCodes.isValidBBB( BBB ):
                    logging.error( _("Invalid {!r} in booklist requested for {} books names system").format( BBB, systemName ) )

        if systemName in self.__DataDicts:
            assert len(self.__DataDicts[systemName]) == 3
            divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__DataDicts[systemName] # unpack it so it's clearer what we're doing here
            if bookList is None:
                if self.__ExpandedDicts:
                    assert len(self.__ExpandedDicts[systemName]) == 2
                    return divisionsNamesDict, booknameLeadersDict, bookNamesDict, self.__ExpandedDicts[systemName][0], self.__ExpandedDicts[systemName][1]
                # else we haven't done any previous input abbreviation expansion
                return divisionsNamesDict, booknameLeadersDict, bookNamesDict, {}, {}

            # Else we were given a booklist so we need to expand the input abbreviations here now
            if self.__ExpandedDicts:
                logging.warning( _("This {} book names system was already expanded, but never mind :)").format( systemName ) )

            # Let's make copies without unneeded entries
            divisionsNamesDictCopy = {}
            for divAbbrev in divisionsNamesDict.keys():
                divBookList = divisionsNamesDict[divAbbrev]['includedBooks']
                found = False
                for divBook in divBookList:
                    if divBook in bookList: found = True; break
                if found: divisionsNamesDictCopy[divAbbrev] = divisionsNamesDict[divAbbrev]
            bookNamesDictCopy = {}
            for BBB in bookList:
                try: bookNamesDictCopy[BBB] = bookNamesDict[BBB]
                except KeyError: # We don't have a name for this book
                    logging.error( "Bookname for {} is missing in {} bookname system".format( BBB, systemName ) )
                    bookNamesDictCopy[BBB] = BBB

            if BibleOrgSysGlobals.strictCheckingFlag: # check that this system contains all the books we need
                missingList = []
                for BBB in bookList:
                    if BBB not in bookNamesDictCopy: missingList.append( BBB )
                if missingList:
                    logging.error( "The following book(s) have no information in {} bookname system: {}".format( systemName, missingList ) )

            # Now expand to get unambiguous input abbreviations for a publication only containing the books we specified
            sortedDNDict, sortedBNDict = expandBibleNamesInputs( systemName, divisionsNamesDictCopy, booknameLeadersDict, bookNamesDictCopy, bookList )
            #print( sortedBNDict )
            #print( sortedDNDict )
            #print( len(divisionsNamesDict), len(divisionsNamesDictCopy), len(booknameLeadersDict), len(bookNamesDict), len(bookNamesDictCopy), len(sortedDNDict), len(sortedBNDict) )
            return divisionsNamesDictCopy, booknameLeadersDict, bookNamesDictCopy, sortedDNDict, sortedBNDict

        # else we couldn't find the requested system name
        logging.error( _("No {!r} system in Bible Books Names Systems").format( systemName ) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            logging.error( _("Available systems are {}").format(self.getAvailableBooksNamesSystemNames()) )
    # end of BibleBooksNamesSystems.getBooksNamesSystem
# end of BibleBooksNamesSystems class



class BibleBooksNamesSystem:
    """
    Class for handling a particular Bible book names system.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self, systemName, bookList=None ):
        """
        Grabs a particular BibleBooksNames system from the singleton object
                            which contains all of the known books names systems.
            The optional (but highly recommended) book list is used for automatically
                                    determining non-ambiguous bookname abbreviations.
                i.e., if you just have English Old Testament, G could automatically represent Genesis,
                    but if you have an entire Bible, G would be ambiguous (Genesis or Galatians).
                    NOTE: However, of course, you can manually specify in the data file that you want G to be an inputAbbreviation for say, Genesis.
        """
        self.__systemName = systemName
        self.__languageCode = systemName.split('_',1)[0]
        self.__bnss = BibleBooksNamesSystems().loadData() # Doesn't reload the XML unnecessarily :)
        self.__bookList = bookList
        result = self.__bnss.getBooksNamesSystem( self.__systemName, bookList )
        if result is not None:
            self.__divisionsNamesDict, self.__booknameLeadersDict, self.__bookNamesDict, self.__sortedDivisionNamesDict, self.__sortedBookNamesDict = result
    # end of BibleBooksNamesSystem.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible books names system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesSystem object"
        result += ('\n' if result else '') + "  " + _("{} Bible books names system").format( self.__systemName )
        result += ('\n' if result else '') + "  " + _("Language code = {}").format( self.__languageCode )
        if BibleOrgSysGlobals.verbosityLevel > 2: # Make it verbose
            result += ('\n' if result else '') + "    " + _("Number of divisions = {}").format( len(self.__divisionsNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of bookname leaders = {}").format( len(self.__booknameLeadersDict) )
            result += ('\n' if result else '') + "    " + _("Number of books = {}").format( len(self.__bookNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of expanded division name abbreviations = {}").format( len(self.__sortedDivisionNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of expanded book name abbreviations = {}").format( len(self.__sortedBookNamesDict) )
        return result
    # end of BibleBooksNamesSystem.__str__


    def getBooksNamesSystemName( self ):
        """ Return the book names system name. """
        return self.__systemName
    # end of BibleBooksNamesSystem.getBooksNamesSystemName


    def getBookName( self, BBB ):
        """
        Get the default book name from the given referenceAbbreviation.
        """
        if BibleOrgSysGlobals.debugFlag: assert len(BBB) == 3
        #print( self.__systemName )
        return self.__bookNamesDict[BBB]['defaultName']
    # end of BibleBooksNamesSystem.getBookName


    def getBookAbbreviation( self, BBB ):
        """
        Get the default book abbreviation from the given referenceAbbreviation.
        """
        if BibleOrgSysGlobals.debugFlag: assert len(BBB) == 3
        return self.__bookNamesDict[BBB]['defaultAbbreviation']
    # end of BibleBooksNamesSystem.getBookAbbreviation


    def getBBBFromText( self, bookNameOrAbbreviation ):
        """
        Get the referenceAbbreviation from the given book name or abbreviation.
                (Automatically converts to upper case before comparing strings.)

        If it fails, tries BibleBooksCodes
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleBooksNamesSystem.getBBBFromText( {} )".format( bookNameOrAbbreviation ) )
            assert bookNameOrAbbreviation

        upperCaseBookNameOrAbbreviation = bookNameOrAbbreviation.upper()
        try:
            if upperCaseBookNameOrAbbreviation in self.__sortedBookNamesDict:
                return self.__sortedBookNamesDict[upperCaseBookNameOrAbbreviation]
        except AttributeError:
            logging.critical( "No bookname dictionary in {} BibleBooksNamesSystem".format( self.__systemName ) )
            return None
        if BibleOrgSysGlobals.debugFlag:
            # It failed so print what the closest alternatives were
            print( "BibleBooksNamesSystem.getBBBFromText( {} ) {}".format( repr(bookNameOrAbbreviation), upperCaseBookNameOrAbbreviation ) )
            #print( self.__sortedBookNamesDict )
            myList, thisLen = [], len(upperCaseBookNameOrAbbreviation)
            #for key in self.__sortedBookNamesDict.keys():
                #if key.startswith('L'): print( key )
            for key in self.__sortedBookNamesDict.keys():
                if key.startswith( upperCaseBookNameOrAbbreviation[0] ) and len(key)==thisLen: myList.append( key )
            print( "Possibility list is", myList )

        return BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( bookNameOrAbbreviation )
    # end of BibleBooksNamesSystem.getBBBFromText


    def getDivisionAbbreviation( self, divisionNameOrAbbreviation ):
        """
        Get the division standardAbbreviation from the given division name or abbreviation.
                (Automatically converts to upper case before comparing strings.)
        """
        if BibleOrgSysGlobals.debugFlag: assert divisionNameOrAbbreviation
        upperCaseDivisionNameOrAbbreviation = divisionNameOrAbbreviation.upper()
        if upperCaseDivisionNameOrAbbreviation in self.__sortedDivisionNamesDict:
            #print( self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation], self.__divisionsNamesDict[self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation]]['defaultAbbreviation'] )
            return self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation]
        if BibleOrgSysGlobals.debugFlag:
            # It failed so print what the closest alternatives were
            print( "getDivisionAbbrev", divisionNameOrAbbreviation, upperCaseDivisionNameOrAbbreviation )
            myList, thisLen = [], len(upperCaseDivisionNameOrAbbreviation)
            for key in self.__sortedDivisionNamesDict.keys():
                if key.startswith( upperCaseDivisionNameOrAbbreviation[0] ) and len(key)==thisLen: myList.append( key )
            print( "Possibility list is", myList )
    # end of BibleBooksNamesSystem.getDivisionAbbreviation


    def getDivisionBooklist( self, divisionAbbreviation ):
        """
        Returns the booklist for the division given the division standardAbbreviation
                                                or else given a vernacular inputAbbreviation.
        """
        if BibleOrgSysGlobals.debugFlag: assert divisionAbbreviation
        if divisionAbbreviation in self.__divisionsNamesDict:
            return self.__divisionsNamesDict[divisionAbbreviation]['includedBooks']
        # else it might be a vernacular value
        standardDivisionAbbreviation = self.getDivisionAbbreviation( divisionAbbreviation )
        if standardDivisionAbbreviation is not None:
            return self.__divisionsNamesDict[standardDivisionAbbreviation]['includedBooks']
    # end of BibleBooksNamesSystem.getDivisionBooklist
# end of BibleBookNamesSystem class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA4','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','PE1','PE2','JDE','REV']
    #sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA1','MA2']
    #sampleBookList = ['MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','PE1','PE2','JDE','REV']

    # Demo the BibleBooksNamesSystems object
    bbnss = BibleBooksNamesSystems().loadData() # Doesn't reload the XML unnecessarily :)
    print( bbnss ) # Just print a summary
    print( "Available system names are:", bbnss.getAvailableBooksNamesSystemNames() )
    print( "Available eng system names are:", bbnss.getAvailableBooksNamesSystemNames( 'eng' ) ) # Just get the ones for this language code
    print( "Available mbt system names are:", bbnss.getAvailableBooksNamesSystemNames( languageCode='mbt' ) )
    print( "Available language codes are:", bbnss.getAvailableLanguageCodes() )
    for bookName in ( 'Genesis', 'Genèse', 'Génesis', 'Gênesis', '1 John' ):
        print( "From {!r} got {}".format( bookName, bbnss.getBBBFromText( bookName ) ) )

    # Demo the BibleBooksNamesSystem object
    bbns1 = BibleBooksNamesSystem("eng_traditional") # Doesn't reload the XML unnecessarily :)
    print( bbns1 ) # Just print a summary

    # Demo the BibleBooksNamesSystem object with a book list
    bbns2 = BibleBooksNamesSystem("eng_traditional",sampleBookList) # Doesn't reload the XML unnecessarily :)
    print( bbns2 ) # Just print a summary
    print( "Checking book name inputs…" )
    for bookAbbrevInput in ('Gen', 'GEN', 'Gn', 'Exo', 'Judges','1 Samuel', '1Samuel', '1Sam', '1 Sam', '1 Sml', '1Sml', '1 S', '1S','II Sa','IIS','1Kgs', '1 Kgs', '1K', '1 K', 'IK', 'I K', '1M', 'IV Mac', 'Mt', 'Jude', 'Rvl' ):
        # NOTE: '1S' is ambiguous with '1st' :(
        print( "  Searching for {!r} got {}".format(bookAbbrevInput, bbns2.getBBBFromText(bookAbbrevInput)) )
    print( "Checking division name inputs…" )
    for divisionAbbrevInput in ('OT','NewTest', 'Paul', 'Deutero', 'Gn', 'Exo' ): # Last two should always fail
        print( "  Searching for {!r} got {}".format(divisionAbbrevInput, bbns2.getDivisionAbbreviation(divisionAbbrevInput)) )
    print( "Getting division booklists…" )
    for divisionAbbrevInput in ('OT','NT', 'NewTest', 'Paul', 'Deutero', 'Gn', 'Exo', '1 Samuel' ):
        print( "  Searching for {!r} got {}".format(divisionAbbrevInput, bbns2.getDivisionBooklist(divisionAbbrevInput)) )
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    parser.add_argument("-p", "--expandDemo", action="store_true", dest="expandDemo", default=False, help="expand the input abbreviations to include all unambiguous shorter forms")
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleBooksNames.py
